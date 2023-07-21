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
    "edge": {
        "hierarchy": {
            "color": "black",
            "penwidth": "3",
            "style": "solid",
        },
        "uses": {
            "color": "red",
            "penwidth": "2",
            "style": "solid",
        },
        "inits": {
            "color": "blue",
            "penwidth": "1",
            "style": "dashed",
        },
    },
    "node": {
        "dir": {
            "shape": "folder",
            "color": "black",
        },
        "file": {
            "shape": "note",
            "color": "black",
        },
    },
    "dot_attrs": {
        'rankdir': 'TB',
    },
}

def _process_config(root: str, url_from_git: bool) -> None:
    """converts none types, auto-detects url_prefix from git if needed"""
    global CONFIG
    for key, value in CONFIG["edge"].items():
        if isinstance(value, str) and value.lower() in ["none", "null"]:
            CONFIG["edge"][key] = None
    for key, value in CONFIG["node"].items():
        if isinstance(value, str) and value.lower() in ["none", "null"]:
            CONFIG["node"][key] = None

    if CONFIG["url_prefix"] is None:
        if url_from_git:
            try:
                # navigate to root
                orig_dir: str = os.getcwd()
                os.chdir(root)
                # get git remote url
                git_remote_url: str = subprocess.check_output(
                    "git remote get-url origin",
                    shell=True,
                    encoding="utf-8",
                ).strip().rstrip("/").replace(".git", "")
                # get branch
                git_branch: str = subprocess.check_output(
                    "git rev-parse --abbrev-ref HEAD",
                    shell=True,
                    encoding="utf-8",
                ).strip()
                CONFIG["url_prefix"] = f"{git_remote_url}/tree/{git_branch}/"
            except subprocess.CalledProcessError as e:
                print(f"could not get git info, not adding URLs: {e}")
                CONFIG["url_prefix"] = None
            finally:
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

def process_imports(imports: list[str], root: str) -> list[str]:
    return [
        (
            x
            .replace("/", ".").replace("\\", ".") # turn path into module
            # remove root except the last part
            .removeprefix(".".join(
                root
                .replace("/", ".").replace("\\", ".")
                .split(".")[:-1]
            ))
            .removesuffix(".py") # remove extension
            .removeprefix(".") # ???
            .removesuffix(".__init__") # init becomes the module name
        )
        for x in imports
    ]

def build_graph(python_files: list[str], root: str) -> nx.DiGraph:
    """Build a directed graph where nodes represent modules and edges represent dependencies"""
    G: nx.MultiDiGraph = nx.MultiDiGraph()
    module_names: list[str] = process_imports(python_files, root=root)
    for python_file, module_name in zip(python_files, module_names):
        python_file_rel: str = module_name.replace(".", "/")
        # Add node for module, with rank based on depth in hierarchy
        if "__init__" in python_file:
            G.add_node(module_name, rank=module_name.count("."), **CONFIG["node"]["dir"])
        else:
            G.add_node(module_name, rank=module_name.count("."), **CONFIG["node"]["file"])
            python_file_rel += ".py"

        # add url
        if CONFIG["url_prefix"] is not None:
            # need to put quotes here because otherwise pydot throws:
            # ValueError: Node names and attributes should not contain ":" unless they are quoted with ""
            G.nodes[module_name]["URL"] = f'"{CONFIG["url_prefix"]}{python_file_rel}"'
        
        # Read source code
        with open(python_file, "r", encoding="utf-8") as f:
            source_code: str = f.read()
        
        # get hierarchy
        module_parents: list[str] = [
            x for x in module_names
            if x != module_name and module_name.startswith(x)
        ]
        if module_parents:
            module_parent: str = sorted(module_parents, key=len)[-1]
            if CONFIG["edge"]["hierarchy"] is not None:
                G.add_edge(module_parent, module_name, **CONFIG["edge"]["hierarchy"])

        # Get imports
        imported_modules: list[str] = get_imports(source_code)
        for imported_module in imported_modules:
            # Check if imported module exists
            if imported_module in module_names:
                # Add edge for import, with label and color
                if "__init__" in python_file:
                    if CONFIG["edge"]["inits"] is not None:
                        G.add_edge(module_name, imported_module, **CONFIG["edge"]["inits"])
                else:
                    if CONFIG["edge"]["uses"] is not None:
                        G.add_edge(module_name, imported_module, **CONFIG["edge"]["uses"])
                
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
        root: str, 
        output: str, 
        output_fmt: Literal["svg", "png"] = "svg",
        config_file: str | None = None,
        print_cfg: bool = False,
        verbose: bool = False,
        url_from_git: bool = True,
        **kwargs,
    ) -> None:
    """Main function to generate a DOT file representing module dependencies
    
    # Positional/keyword arguments
    - `root: str`
        root directory to search for Python files
    - `output: str`
        output filename (without extension)
    - `output_fmt: Literal["svg", "png"]`
        output format for running `dot`

    # Keyword-only arguments
    - `config_file: str | None = None`
        path to a JSON file containing configuration
    - `print_cfg: bool = False`
        whether to print the configuration after loading it -- if this is set, the program will exit after printing the config
    - `verbose: bool = False`
    - `h` or `help`
        print this help message
    
    # Configuration options
    either specify these in a json file, or separate levels with a dot. set to `None` to disable.
    - `node.dir` kwargs for directory nodes
    - `node.file` kwargs for file nodes
    - `edge.heirarchy` kwargs for hierarchy edges (i.e. file A is part of module B)
    - `edge.uses` kwargs for uses edges (i.e. file A imports module B for using it)
    - `edge.inits` kwargs for init edges (i.e. __init__.py file imports something from downstream of itself)
    """

    if config_file is not None:
        with open(config_file, "r", encoding="utf-8") as f:
            update_with_nested_dict(CONFIG, json.load(f))

    if len(kwargs) > 0:
        update_with_nested_dict(
            CONFIG, 
            kwargs_to_nested_dict(kwargs, transform_key=lambda x: x.lstrip("-"), sep="."),
        )

    _process_config(root=root, url_from_git=url_from_git)

    if "h" in CONFIG or "help" in CONFIG:
        print(main.__doc__)
        print("# current config:")
        print(json.dumps(CONFIG, indent=2))
        exit()
    
    if print_cfg:
        print(json.dumps(CONFIG, indent=2))
        exit()

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
