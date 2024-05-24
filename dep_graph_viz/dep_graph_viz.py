import ast
import glob
import os
import json
from pathlib import Path
import subprocess
from typing import Literal, Any

from muutils.dictmagic import update_with_nested_dict, kwargs_to_nested_dict
import networkx as nx
import pydot
from networkx.drawing.nx_pydot import to_pydot


CONFIG: dict[str, Any] = {
    "url_prefix": None,
    "auto_url_format": "{git_remote_url}/tree/{git_branch}/",
    "auto_url_replace": {".git": ""},
    "edge": {
        "module_hierarchy": {
            "color": "black",
            "penwidth": "3",
            "style": "solid",
        },
        "hierarchy": {
            "color": "black",
            "penwidth": "1",
            "style": "solid",
        },
        "uses": {
            "color": "red",
            "penwidth": "1",
            "style": "solid",
        },
        "inits": {
            "color": "blue",
            "penwidth": "1",
            "style": "dashed",
        },
    },
    "node": {
        "root": {
            "shape": "folder",
            "color": "purple",
        },
        "module_dir": {
            "shape": "folder",
            "color": "black",
        },
        "dir": {
            "shape": "folder",
            "color": "blue",
        },
        "module_file": {
            "shape": "note",
            "color": "black",
        },
        "script": {
            "shape": "note",
            "color": "green",
        },
    },
    "dot_attrs": {
        'rankdir': 'TB',
    },
}

NULL_STRINGS: set[str] = {"none", "null"}

def _process_config(root: str|None) -> None:
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
    if (CONFIG["url_prefix"] is None) and (CONFIG["auto_url_format"] is not None) and (root is not None):
        try:
            # navigate to root
            orig_dir: str = os.getcwd()
            os.chdir(root)
            # get git remote url
            git_remote_url: str = subprocess.check_output(
                "git remote get-url origin",
                shell=True,
                encoding="utf-8",
            ).strip().rstrip("/")
            for rep_key, rep_val in CONFIG["auto_url_replace"].items():
                git_remote_url = git_remote_url.replace(rep_key, rep_val)
            # get branch
            git_branch: str = subprocess.check_output(
                "git rev-parse --abbrev-ref HEAD",
                shell=True,
                encoding="utf-8",
            ).strip()
            CONFIG["url_prefix"] = CONFIG["auto_url_format"].format(git_remote_url=git_remote_url, git_branch=git_branch)
        except subprocess.CalledProcessError as e:
            print(f"could not get git info, not adding URLs: {e}")
            CONFIG["url_prefix"] = None
        finally:
            # go back to original directory
            os.chdir(orig_dir)


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

def get_relevant_directories(root: str) -> set[str]:
    root = os.path.abspath(root)
    directories_with_py_files: set[str] = {os.path.relpath(os.path.dirname(file), root) for file in get_python_files(root)}
    all_directories: set[str] = set(directories_with_py_files)
    
    for directory in directories_with_py_files:
        while directory and directory != '.':
            parent_directory = os.path.dirname(directory)
            if parent_directory and parent_directory != directory:
                all_directories.add(parent_directory)
            directory = parent_directory

    all_directories.add('.')  # Ensure the root directory is included
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

NodeTypes = Literal["root", "module_root", "module_dir", "dir", "module_file", "script"]


def classify_node(path: str, root: str) -> NodeTypes:
    path = path.replace("\\", "/")
    parent_dir: str = os.path.dirname(path)
    rel_path: str = os.path.relpath(path, root)
    if os.path.isdir(path):
        files: list[str] = os.listdir(path)
        # handle root
        if rel_path == '.':
            if '__init__.py' in files:
                return 'module_root'
            else:
                return 'root'
        else:
            return 'module_dir' if '__init__.py' in files else 'dir'
    elif rel_path.endswith('.py'):
        if '__init__.py' in os.listdir(parent_dir):
            return 'module_file'
        else:
            return 'script'
    else:
        raise ValueError(f"unknown path type: {path}")


def add_node(G: nx.MultiDiGraph, node_name: str, node_type: str, url: str = None) -> None:
    """Add a node to the graph with the given type and optional URL."""
    if node_name not in G:
        G.add_node(node_name, rank=node_name.count("."), **CONFIG["node"][node_type])
        if url:
            G.nodes[node_name]["URL"] = f'"{url}"'



def build_graph(python_files: list[str], root: str) -> nx.MultiDiGraph:
    G: nx.MultiDiGraph = nx.MultiDiGraph()
    module_names: list[str] = process_imports(python_files, root=root)
    directories: set[str] = get_relevant_directories(root)

    # Add nodes for directories and root
    for directory in directories:
        node_type: str = classify_node(os.path.join(root, directory), root)
        dir_module_name = directory.replace("/", ".").replace("\\", ".")
        add_node(G, dir_module_name, node_type)

    for python_file in python_files:
        module_name = process_imports([python_file], root=root)[0]
        python_file_rel: str = os.path.relpath(python_file, root).replace(os.sep, "/")
        node_type = classify_node(python_file, root)
        
        # Add node for module or script
        node_key = module_name if node_type != 'script' else python_file_rel
        add_node(G, node_key, node_type, f"{CONFIG['url_prefix']}{python_file_rel}" if CONFIG["url_prefix"] else None)

        # Read source code
        with open(python_file, "r", encoding="utf-8") as f:
            source_code: str = f.read()

        # Get hierarchy
        if node_type in {'module_file', 'module_dir'}:
            module_parents: list[str] = [
                x for x in list(G.nodes)
                if x != module_name and module_name.startswith(x)
            ]
            if module_parents:
                module_parent: str = sorted(module_parents, key=len)[-1]
                if CONFIG["edge"]["hierarchy"]:
                    G.add_edge(module_parent, module_name, **CONFIG["edge"]["hierarchy"])

        # Get imports
        imported_modules: list[str] = get_imports(source_code)
        for imported_module in imported_modules:
            # Convert import to module name
            imported_module_name = imported_module.replace("/", ".").replace("\\", ".")
            if imported_module_name in G:
                edge_type = "inits" if node_type == 'module_dir' else "uses"
                if CONFIG["edge"].get(edge_type):
                    G.add_edge(node_key, imported_module_name, **CONFIG["edge"][edge_type])

    return G





def write_dot(G: nx.DiGraph, output_filename: str) -> None:
    """Write graph to a DOT file"""
    P: pydot.Dot = to_pydot(G)
    P.obj_dict["attributes"].update(CONFIG["dot_attrs"])
    P.write_raw(output_filename)


def get_python_files(root: str) -> list[str]:
    """Get all Python files in a directory and its subdirectories"""
    glob_pattern: str = Path(root).as_posix().rstrip("/") + "/**/*.py"
    return glob.glob(glob_pattern, recursive=True)


def main(
        root: str|None = None,
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
            kwargs_to_nested_dict(kwargs, transform_key=lambda x: x.lstrip("-"), sep="."),
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

    print("# getting python files...")
    python_files: list[str] = get_python_files(root)
    print(f"\t found {len(python_files)} python files")
    
    print("# building graph...")
    G: nx.MultiDiGraph = build_graph(python_files, root)
    print(f"\t built graph with {len(G.nodes)} nodes and {len(G.edges)} edges")
    
    output_file_dot: str = f"{output}.dot"
    print(f"# writing dot file: {output_file_dot}")
    write_dot(G, f"{output_file_dot}")

    print(f"# running dot...")
    print(f"\tcommand:")
    cmd: str = f"dot -T{output_fmt} {output_file_dot} -o {output}.{output_fmt} {'-v' if verbose else ''}"
    print(f"\t$ {cmd}")
    os.system(cmd)

    print("# done!")


if __name__ == "__main__":
    import fire

    fire.Fire(main)
