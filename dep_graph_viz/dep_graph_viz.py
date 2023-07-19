import ast
import glob
import os
from pathlib import Path
from typing import Literal, Any

import networkx as nx
from networkx.drawing.nx_pydot import to_pydot


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
    print(module_names)
    for python_file, module_name in zip(python_files, module_names):

        # Add node for module, with rank based on depth in hierarchy
        G.add_node(module_name, rank=module_name.count("."), shape='box')
        
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
            G.add_edge(module_parent, module_name, color="black", penwidth='3')

        # Get imports
        imported_modules: list[str] = get_imports(source_code)
        for imported_module in imported_modules:
            # Check if imported module exists
            if imported_module in module_names:
                # Add edge for import, with label and color
                if "__init__" in python_file:
                    G.add_edge(module_name, imported_module, color="blue", penwidth='1', style="dashed")
                else:
                    G.add_edge(module_name, imported_module, color="red", penwidth='2')
                
    return G


def write_dot(G: nx.DiGraph, output_filename: str) -> None:
    """Write graph to a DOT file"""
    P = to_pydot(G)
    # Set direction
    P.set('rankdir', 'TB')  
    P.write_raw(output_filename)


def get_python_files(root: str) -> list[str]:
    """Get all Python files in a directory and its subdirectories"""
    glob_pattern: str = Path(root).as_posix().rstrip("/") + "/**/*.py"
    return glob.glob(glob_pattern, recursive=True)


def main(
		root: str, 
        output: str, 
        output_fmt: Literal["svg", "png"] = "svg",
        
	) -> None:
    """Main function to generate a DOT file representing module dependencies"""
    python_files: list[str] = get_python_files(root)
    G = build_graph(python_files, root)
    output_file_dot: str = f"{output}.dot"
    write_dot(G, f"{output_file_dot}")
    os.system(f"dot -T{output_fmt} {output_file_dot} -o {output}.{output_fmt}")


if __name__ == "__main__":
    import fire

    fire.Fire(main)
