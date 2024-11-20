import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Literal

import networkx as nx
import pydot
from muutils.dictmagic import kwargs_to_nested_dict, update_with_nested_dict
from networkx.drawing.nx_pydot import to_pydot

from dep_graph_viz.config import CONFIG, _process_config
from dep_graph_viz.util.paths import normalize_path, path_to_module
from dep_graph_viz.util.util import (
	get_imports,
	get_python_files,
	get_relevant_directories,
)

ORIG_DIR: str = os.getcwd()
# *absolute* path of the root directory
ROOT: str | None = None

NodeType = Literal[
	"module_root",  # root if __init__.py is present
	"root",  # root if no __init__.py
	"module_dir",  # non-root directory with __init__.py
	"dir",  # non-root directory without __init__.py
	"module_file",  # file in a module (in a directory with __init__.py)
	"script",  # standalone file (in a directory without __init__.py)
]


def add_node(G: nx.MultiDiGraph, node: "Node") -> None:
	"""Add a node to the graph with the given type and optional URL."""
	# if node is not present, add it
	if node not in G:
		# add the node
		G.add_node(
			node,  # `Node` object, `str(node)` will be the key
			rank=node.get_rank(),  # for ranking/ordering of the nodes
			**CONFIG["node"][
				node.node_type
			],  # attributes (color, shape, etc) for the node type
		)
		# add a URL -- doesn't work for images
		if node.url:
			G.nodes[node]["URL"] = f'"{node.url}"'
	else:
		# if it's already present, we have a key duplication
		raise ValueError(f"node {node.path} already exists in the graph!")


def classify_node(path: str, root: str = ".") -> NodeType:
	# posixify path
	path = normalize_path(path)
	# path relative to the root module
	rel_path: str = os.path.relpath(path, root)
	# parent directory (module it's directly in)
	parent_dir: str = os.path.dirname(rel_path)
	# if it's in the root, set the parent dir to "."
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
	rel_path: str
	aliases: set[str]
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
		if path == "":
			path = "."

		# set up aliases
		aliases: set[str] = {path}

		# path relative to root
		rel_path: str = normalize_path(os.path.relpath(path, root))
		aliases.add(rel_path)
		if os.path.basename(rel_path) == "__init__.py":
			rel_path = os.path.dirname(rel_path).removesuffix("/")
			aliases.add(rel_path)

		# node type for formatting
		node_type: NodeType = classify_node(path, root)

		# get parent dir
		parent_dir: str = normalize_path(os.path.dirname(rel_path))
		if not parent_dir:
			parent_dir = "."

		# unique display name
		display_name: str = (
			path_to_module(rel_path) if node_type.startswith("module") else rel_path
		)
		aliases.add(display_name)
		if node_type in {"module_root", "root"}:
			display_name = "ROOT"
			parent_dir = None
			aliases.add(display_name)

		# get url if needed
		url: str | None = None
		url_prefix: str = CONFIG["url_prefix"]
		if url_prefix:
			url = f"{url_prefix}{rel_path}"

		# assemble and return node
		node: Node = Node(
			orig_path=path,
			rel_path=rel_path,
			aliases=aliases,
			display_name=display_name,
			url=url,
			node_type=node_type,
			parent_dir=parent_dir,
		)

		return node

	def is_root(self) -> bool:
		return self.node_type in {"root", "module_root"}

	def is_module(self) -> bool:
		return self.node_type.startswith("module")

	def get_rank(self) -> int:
		return self.rel_path.count("/") + 11 if not self.is_root() else 10

	def __hash__(self) -> int:
		return hash(self.rel_path)

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
		# return self.__str__()
		kwargs: str = ", ".join(
			[
				(
					f"{k}='{self.__dict__[k]}'"
					if isinstance(self.__dict__[k], str)
					else f"{k}={self.__dict__[k]}"
				)
				for k in (
					"display_name",
					"node_type",
					# "rel_path",
					# "orig_path",
					# "aliases",
					# "parent_dir",
				)
			]
		)
		return f"Node({kwargs})"


def build_graph(
	root: str = ".",
	include_local_imports: bool = CONFIG["graph"]["include_local_imports"],
	edge_config: dict[str, Any] = CONFIG["edge"],
) -> nx.MultiDiGraph:
	# create graph, get dirs and package name
	# --------------------------------------------------
	G: nx.MultiDiGraph = nx.MultiDiGraph()
	directories: set[str] = get_relevant_directories(root)
	package_name: str = os.path.basename(os.path.abspath(root))

	# Add nodes for directories and root
	# --------------------------------------------------
	directory_nodes: dict[str, Node] = {
		directory: Node.get_node(directory) for directory in directories
	}
	for node in directory_nodes.values():
		add_node(G, node)

	# add folder hierarchy edges
	# --------------------------------------------------
	for directory, node in directory_nodes.items():
		# no parent of the root
		if node.is_root():
			continue

		# get parent node
		parent_node: Node = directory_nodes[node.parent_dir]

		# figure out edge type -- different styles for different categories
		edge_type: str
		if parent_node.is_module() and node.is_module():
			edge_type = "module_hierarchy"
		else:
			edge_type = "hierarchy"

		# add edge to graph
		G.add_edge(parent_node, node, **edge_config[edge_type])

	# get python files
	# --------------------------------------------------
	python_files: list[str] = get_python_files(root)

	# add files nodes and heirarchy edges to folders
	# --------------------------------------------------
	nodes_dict: dict[str, Node] = dict()
	for python_file in python_files:
		node: Node
		# special handling for init files
		is_init: bool = python_file.endswith("__init__.py") or python_file == "."
		if is_init:
			node = directory_nodes[os.path.dirname(python_file) or "."]
		else:
			node = Node.get_node(python_file)
			add_node(G, node)

		# this will add the directory node if it doesn't exist
		nodes_dict[node.display_name] = node

		# add file hierarchy
		if edge_config["hierarchy"]:
			if node.node_type not in {"root", "module_root"} and not is_init:
				parents: list[str] = [
					parent_node.display_name
					for parent_node in directory_nodes.values()
					if node.parent_dir == parent_node.rel_path
				]
				if parents:
					assert (
						len(parents) == 1
					), f"multiple parents found for {node.orig_path = }: {parents}"
					module_parent: str = sorted(parents, key=len)[-1]
					if module_parent == "ROOT":
						module_parent = "."
					G.add_edge(
						directory_nodes[module_parent],
						node,
						**edge_config["hierarchy"],
					)

	# add import edges
	# --------------------------------------------------
	if include_local_imports:
		nodes_to_add: list[dict] = []
		edges_to_add: list[dict] = []
		for node_key in G.nodes:
			node: Node
			if isinstance(node_key, Node):
				node = node_key
			else:
				raise ValueError(
					f"unknown node type: {node_key = }, {type(node_key) = }"
				)

			# Read source code
			node_path: str = node.orig_path
			if os.path.isdir(node_path):
				node_path = os.path.join(node_path, "__init__.py")
			elif node_path == ".":
				node_path = "__init__.py"

			with open(node_path, "r", encoding="utf-8") as f:
				source_code: str = f.read()

			# Get imports
			imported_modules: list[str] = get_imports(source_code)

			for imported_module in imported_modules:
				# Convert import to module name
				imported_module_name = imported_module

				if CONFIG["graph"]["strip_module_prefix"]:
					imported_module_name = imported_module_name.removeprefix(
						package_name
					).removeprefix(".")
					if not imported_module_name:
						# if empty string, it means we are looking for the root
						imported_module_name = "ROOT"

				if imported_module_name in nodes_dict:
					edge_type = (
						"inits"
						if node_path.endswith("__init__.py")
						else "uses"
					)
					if edge_config.get(edge_type):
						edges_to_add.append(
							dict(
								u_for_edge=nodes_dict[imported_module_name],
								v_for_edge=node,
								**edge_config[edge_type],
							)
						)
				else:
					# assume external module
					if CONFIG["graph"]["include_externals"]:
						nodes_to_add.append(
							dict(
								node_for_adding=imported_module_name,
								rank=0,  # for ranking/ordering of the nodes
								**CONFIG["node"][
									"external"
								],  # attributes (color, shape, etc) for the node type
							)
						)
						edges_to_add.append(
							dict(
								u_for_edge=imported_module_name,
								v_for_edge=node,
								**edge_config["external"],
							)
						)

		for x in nodes_to_add:
			G.add_node(**x)

		for x in edges_to_add:
			G.add_edge(**x)

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

	print("# building graph...")
	G: nx.MultiDiGraph = build_graph(
		root="."
	)  # pass "." since we just moved to the root directory
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
		cmd: str = f"dot -T{output_fmt} {output_file_dot} -o {output}.{output_fmt} {'-v' if verbose else ''}"
		print(f"\t$ {cmd}")
		subprocess.run(cmd, check=True)

	print("# done!")


if __name__ == "__main__":
	import fire

	fire.Fire(main)
