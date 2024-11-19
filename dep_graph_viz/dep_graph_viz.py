import ast
import glob
import json
import os
import subprocess
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import networkx as nx
import pydot
from muutils.dictmagic import kwargs_to_nested_dict, update_with_nested_dict
from networkx.drawing.nx_pydot import to_pydot

from dep_graph_viz.config import _DEFAULT_CONFIG

ORIG_DIR: str = os.getcwd()
# *absolute* path of the root directory
ROOT: str | None = None

NodeType = Literal["root", "module_root", "module_dir", "dir", "module_file", "script"]

NULL_STRINGS: set[str] = {"none", "null"}

CONFIG: dict[str, Any] = deepcopy(_DEFAULT_CONFIG)


def _process_config(root: str = ".") -> None:
    """converts none types, auto-detects url_prefix from git if needed"""
    global CONFIG
    # convert none/null items
    for key, value in CONFIG["edge"].items():
        if isinstance(value, str) and value.lower() in NULL_STRINGS:
            CONFIG["edge"][key] = None
    for key, value in CONFIG["node"].items():
        if isinstance(value, str) and value.lower() in NULL_STRINGS:
            CONFIG["node"][key] = None

    # get git url and branch
    if (
        (CONFIG["url_prefix"] is None)
        and (CONFIG["auto_url_format"] is not None)
        and (root is not None)
    ):
        try:
            # navigate to root
            orig_dir: str = os.getcwd()
            os.chdir(root)
            # get git remote url
            git_remote_url: str = (
                subprocess.check_output(
                    "git remote get-url origin",
                    shell=True,
                    encoding="utf-8",
                )
                .strip()
                .rstrip("/")
            )
            for rep_key, rep_val in CONFIG["auto_url_replace"].items():
                git_remote_url = git_remote_url.replace(rep_key, rep_val)
            # get branch
            git_branch: str = subprocess.check_output(
                "git rev-parse --abbrev-ref HEAD",
                shell=True,
                encoding="utf-8",
            ).strip()
            CONFIG["url_prefix"] = CONFIG["auto_url_format"].format(
                git_remote_url=git_remote_url, git_branch=git_branch
            )
        except subprocess.CalledProcessError as e:
            print(f"could not get git info, not adding URLs: {e}")
            CONFIG["url_prefix"] = None
        finally:
            # go back to original directory
            os.chdir(orig_dir)


def classify_node(path: str, root: str = ".") -> NodeType:
    # posixify path
    path = path.replace("\\", "/")
    rel_path: str = os.path.relpath(path, root)
    parent_dir: str = os.path.dirname(rel_path)
    if parent_dir == "":
        parent_dir = "."

    # error checking
    if not os.path.exists(path):
        raise FileNotFoundError(f"file not found: '{path}' for {path = } and {root = }")

    if not os.path.exists(parent_dir):
        raise FileNotFoundError(
            f"parent directory not found: '{parent_dir}' for {path = } and {root = }"
        )

    if not os.path.exists(rel_path):
        raise FileNotFoundError(
            f"relative path not found: '{rel_path}' for {path = } and {root = }"
        )

    # if directory
    if os.path.isdir(path):
        files: list[str] = os.listdir(path)
        # handle root
        if rel_path == ".":
            if "__init__.py" in files:
                return "module_root"
            else:
                return "root"
        else:
            # module or ordinary directory
            return "module_dir" if "__init__.py" in files else "dir"
    elif rel_path.endswith(".py"):
        # if a py file, module or script
        if "__init__.py" in os.listdir(parent_dir):
            return "module_file"
        else:
            return "script"
    else:
        raise ValueError(f"unknown path type: {path}")


@dataclass(frozen=True)
class Node:
    orig_path: str
    path: str
    display_name: str
    url: str | None = None
    node_type: NodeType | None = None
    parent_dir: str | None = None

    @classmethod
    def get_node(
        cls,
        path: str,
        root: str = ".",
    ) -> "Node":
        # rel_path: str = os.path.relpath(path, root).replace("\\", "/")
        if path == "":
            path = "."
        rel_path: str = normalize_path(os.path.relpath(path, root))
        # check for filename is __init__.py
        if os.path.basename(rel_path) == "__init__.py":
            rel_path = os.path.dirname(rel_path).removesuffix("/")

        node_type: NodeType = classify_node(path, root)
        display_name: str = (
            path_to_module(rel_path) if node_type.startswith("module") else rel_path
        )

        url: str | None = None
        url_prefix: str = CONFIG["url_prefix"]
        if url_prefix:
            url = f"{url_prefix}{rel_path}"

        return Node(
            orig_path=path,
            path=rel_path,
            display_name=display_name,
            url=url,
            node_type=node_type,
            parent_dir=os.path.dirname(rel_path),
        )

    def is_root(self) -> bool:
        return self.node_type in {"root", "module_root"}

    def is_module(self) -> bool:
        return self.node_type.startswith("module")

    def get_rank(self) -> int:
        return self.path.count("/")

    def __hash__(self) -> int:
        return hash(self.path)

    def __str__(self) -> str:
        if self.is_root():
            # absolute path of the root directory
            return (
                f'"{CONFIG["git_remote_url"]}"'
                if CONFIG.get("git_remote_url")
                else '"ROOT"'
            )
        else:
            return f'"{self.display_name}"'

    def __repr__(self) -> str:
        return str(self)


def get_imports(source_code: str) -> list[str]:
    """Get all the imports from a source code string"""
    tree: ast.Module = ast.parse(source_code)
    imports: list[str] = []
    for node in ast.walk(tree):
        # Check if node is an import statement
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        # Check if node is a from ... import ... statement
        elif isinstance(node, ast.ImportFrom):
            imports.append(node.module)
    return imports


def get_python_files(root: str = ".") -> list[str]:
    """Get all Python files in a directory and its subdirectories"""
    if not os.path.exists(root):
        raise FileNotFoundError(f"root directory not found: {root}")

    glob_pattern: str = Path(root).as_posix().rstrip("/") + "/**/*.py"
    return glob.glob(glob_pattern, recursive=True)


def get_relevant_directories(root: str = ".") -> set[str]:
    if not os.path.exists(root):
        raise FileNotFoundError(f"root directory not found: {root}")

    # get all directories with python files
    directories_with_py_files: set[str] = {
        os.path.dirname(os.path.relpath(file, root)) for file in get_python_files(root)
    }
    # allocate output
    all_directories: set[str] = set(directories_with_py_files)
    all_directories.add(root)

    # get every directory between root and known dir
    for directory in directories_with_py_files:
        while directory and directory != ".":
            parent_directory = os.path.dirname(directory)
            if parent_directory and parent_directory != directory:
                all_directories.add(parent_directory)
            directory = parent_directory

    all_directories.add(".")  # Ensure the root directory is included

    all_directories = set(map(normalize_path, all_directories))

    return all_directories


def normalize_path(path: str) -> str:
    return path.replace("\\", "/")


def path_to_module(path: str) -> str:
    return normalize_path(path).replace("/", ".").removesuffix(".py")


def process_imports(imports: list[str], root: str) -> list[str]:
    root_module_path = root.replace("/", ".").replace("\\", ".")
    return [
        (
            path_to_module(x)
            .removeprefix(root_module_path)
            .removeprefix(".")  # ???
            .removesuffix(".__init__")  # init becomes the module name
        )
        for x in imports
    ]


def add_node(G: nx.MultiDiGraph, node: Node) -> None:
    """Add a node to the graph with the given type and optional URL."""
    if node not in G:
        G.add_node(
            node,
            rank=node.get_rank(),
            **CONFIG["node"][node.node_type],
        )
        if node.url:
            G.nodes[node]["URL"] = f'"{node.url}"'
    else:
        raise ValueError(f"node {node.path} already exists in the graph!")


def build_graph(
    python_files: list[str],
    root: str = ".",
    only_heirarchy: bool = False,
) -> nx.MultiDiGraph:
    G: nx.MultiDiGraph = nx.MultiDiGraph()
    directories: set[str] = get_relevant_directories(root)

    # Add nodes for directories and root
    directory_nodes: dict[str, Node] = {
        directory: Node.get_node(directory) for directory in directories
    }
    for node in directory_nodes.values():
        add_node(G, node)

    # add folder hierarchy
    for directory, node in directory_nodes.items():
        if node.is_root():
            continue
        parent_path: str = normalize_path(os.path.dirname(directory))
        if not parent_path:
            parent_path = "."
        parent_node: Node = directory_nodes[parent_path]
        if parent_node.is_module() and node.is_module():
            G.add_edge(parent_node, node, **CONFIG["edge"]["module_hierarchy"])
        else:
            G.add_edge(parent_node, node, **CONFIG["edge"]["hierarchy"])

    for python_file in python_files:
        node: Node = Node.get_node(python_file)
        add_node(G, node)

        # Get hierarchy
        if node.node_type not in {"root", "module_root"}:
            parents: list[str] = [
                parent_node.display_name
                for parent_node in directory_nodes.values()
                if node.parent_dir == parent_node.path
            ]
            if parents:
                assert (
                    len(parents) == 1
                ), f"multiple parents found for {node.path}: {parents}"
                module_parent: str = sorted(parents, key=len)[-1]
                if CONFIG["edge"]["hierarchy"]:
                    G.add_edge(
                        module_parent, node.display_name, **CONFIG["edge"]["hierarchy"]
                    )

        if not only_heirarchy:
            # Read source code
            with open(python_file, "r", encoding="utf-8") as f:
                source_code: str = f.read()

            # Get imports
            imported_modules: list[str] = get_imports(source_code)
            for imported_module in imported_modules:
                # Convert import to module name
                imported_module_name = imported_module.replace("/", ".").replace(
                    "\\", "."
                )
                if imported_module_name in G:
                    edge_type = (
                        "inits"
                        if classify_node(python_file, root) == "module_dir"
                        else "uses"
                    )
                    if CONFIG["edge"].get(edge_type):
                        G.add_edge(
                            node.display_name,
                            imported_module_name,
                            **CONFIG["edge"][edge_type],
                        )

    return G


def write_dot(G: nx.DiGraph, output_filename: str) -> None:
    """Write graph to a DOT file"""
    P: pydot.Dot = to_pydot(G)
    P.obj_dict["attributes"].update(CONFIG["dot_attrs"])
    P.write_raw(output_filename)


def main(
    root: str | None = None,
    output: str = "output",
    output_fmt: Literal["svg", "png"] = "svg",
    config_file: str | None = None,
    print_cfg: bool = False,
    verbose: bool = False,
    **kwargs,
) -> None:
    """Main function to generate and render a graphviz DOT file representing module dependencies

    # Positional or keyword arguments
    - `root: str` (REQUIRED)
        root directory to search for Python files
    - `output: str`
        output filename (without extension)
        default: `"output"`
    - `output_fmt: Literal["svg", "png"]`
        output format for running `dot`
        default: `"svg"`

    # Keyword-only arguments
    - `config_file: str | None = None`
        path to a JSON file containing configuration options
    - `print_cfg: bool = False`
        whether to print the configuration after loading it -- if this is set, the program will exit after printing the config
    - `verbose: bool = False`
    - `h` or `help`
        print this help message and exit

    # Configuration options
    either specify these in a json file, or separate levels with a dot. set to `None` to disable.
    - `url_prefix: str|None`
        manually add a prefix to the url. if set to `None`, will try to auto-detect from git
    - `auto_url_format: str|None`
        how to format a url given the git remote url and branch name.
        default: "{git_remote_url}/tree/{git_branch}/" (which works for github)
        set to `None` to disable. if both this and `url_prefix` are none, the svg will not have URLs
    - `auto_url_replace: dict[str,str]`
        string-replace pairs to apply to the git remote url before formatting it
        note: trailing slashes are also stripped
        default: `{".git": ""}`
    - `node.dir: dict|None`
        kwargs for directory nodes
    - `node.file: dict|None`
        kwargs for file nodes
    - `edge.hierarchy: dict|None`
        kwargs for hierarchy edges (i.e. file A is part of module B)
    - `edge.uses: dict|None`
        kwargs for uses edges (i.e. file A imports module B for using it)
    - `edge.inits: dict|None`
        kwargs for init edges (i.e. __init__.py file imports something from downstream of itself)
    - `dot_attrs: dict`
        kwargs for the dot graph itself
        default: `{'rankdir': 'TB'}` (top to bottom)
        you can change it via `dot_attrs.rankdir=LR` for left to right, etc.

    To modify an element of a dict without specifying the whole dict, you can use "." as a level separator:
    ```
    --edge.uses.color=green
    ```

    """

    # update config from file if given
    if config_file is not None:
        with open(config_file, "r", encoding="utf-8") as f:
            update_with_nested_dict(CONFIG, json.load(f))

    # update config from kwargs
    if len(kwargs) > 0:
        update_with_nested_dict(
            CONFIG,
            kwargs_to_nested_dict(
                kwargs, transform_key=lambda x: x.lstrip("-"), sep="."
            ),
        )

    # process by converting none types, auto-detecting url_prefix from git if needed
    _process_config(root=root)

    # print help message and exit
    if "h" in CONFIG or "help" in CONFIG:
        print(main.__doc__)
        print("# current config:")
        print(json.dumps(CONFIG, indent=2))
        exit()

    # print config and exit
    if print_cfg:
        print(json.dumps(CONFIG, indent=2))
        exit()

    if root is None:
        raise ValueError("root is required")

    # change directory
    os.chdir(root)
    global ROOT
    ROOT = root

    print("# getting python files...")
    python_files: list[str] = get_python_files()
    print(f"\t found {len(python_files)} python files")

    print("# building graph...")
    G: nx.MultiDiGraph = build_graph(python_files)
    print(f"\t built graph with {len(G.nodes)} nodes and {len(G.edges)} edges")

    # change back to original directory
    os.chdir(ORIG_DIR)
    output_file_dot: str = f"{output}.dot"
    print(f"# writing dot file: {output_file_dot}")
    write_dot(G, f"{output_file_dot}")

    if output_fmt == "html":
        print("# generating html...")
        from dep_graph_viz.html import generate_html

        generate_html(output_file_dot, f"{output}.html")
    else:
        print("# running dot...")
        print("\tcommand:")
        cmd: str = (
            f"dot -T{output_fmt} {output_file_dot} -o {output}.{output_fmt} {'-v' if verbose else ''}"
        )
        print(f"\t$ {cmd}")
        os.system(cmd)

    print("# done!")


if __name__ == "__main__":
    import fire

    fire.Fire(main)
