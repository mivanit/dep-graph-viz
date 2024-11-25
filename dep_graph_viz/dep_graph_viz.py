from copy import deepcopy
import json
import os
import subprocess
from dataclasses import dataclass
from typing import Any, Literal
import warnings

import networkx as nx
import pydot
from muutils.dictmagic import kwargs_to_nested_dict, update_with_nested_dict
from networkx.drawing.nx_pydot import to_pydot

from dep_graph_viz.config import _DEFAULT_CONFIG, _process_config
from dep_graph_viz.util.paths import get_module_directory, get_package_repository_url, normalize_path, path_to_module
from dep_graph_viz.util.util import (
	get_imports,
	get_python_files,
	get_relevant_directories,
)

# ORIG_DIR: str = os.getcwd()
# # *absolute* path of the root directory
# ROOT: str | None = None

# PACKAGE_NAME: str
# ROOT_NODE_NAME: str = "ROOT"

NodeType = Literal[
	"module_root",  # root if __init__.py is present
	"root",  # root if no __init__.py
	"module_dir",  # non-root directory with __init__.py
	"dir",  # non-root directory without __init__.py
	"module_file",  # file in a module (in a directory with __init__.py)
	"script",  # standalone file (in a directory without __init__.py)
]

def augment_module_name(module_name: str, config: dict) -> str:
	"augment module name with prefix if not stripping"
	if (
		config["graph"]["strip_module_prefix"] 
		or module_name in (".", "ROOT")
	):
		return module_name
	else:
		return f"{config['PACKAGE_NAME']}.{module_name}"


def add_node(G: nx.MultiDiGraph, node: "Node", config: dict) -> None:
	"""Add a node to the graph with the given type and optional URL."""
	# if node is not present, add it
	if node not in G:
		# add the node
		G.add_node(
			node,  # `Node` object, `str(node)` will be the key
			rank=node.get_rank(),  # for ranking/ordering of the nodes
			**config["node"][
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
	config: dict
	url: str | None = None
	node_type: NodeType | None = None
	parent_dir: str | None = None

	@classmethod
	def get_node(
		cls,
		path: str,
		config: dict,
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
		display_name: str
		if node_type.startswith("module"):
			display_name = path_to_module(rel_path, strict_names=config["graph"]["strict_names"])
			# special case for when there is a file/module with the same name as the package
			if node_type != "module_root":
				display_name = augment_module_name(display_name, config)
		else:
			display_name = rel_path

		aliases.add(display_name)
		if node_type in {"module_root", "root"}:
			display_name = config["root_node_name"]
			parent_dir = None
			aliases.add(display_name)

		# get url if needed
		url: str | None = None
		url_prefix: str = config["url_prefix"]
		if url_prefix is not None:
			url = f"{url_prefix}{rel_path}"
			if config.get("auto_url_replace", None):
				for k, v in config["auto_url_replace"].items():
					url = url.replace(k, v)

		# assemble and return node
		node: Node = Node(
			orig_path=path,
			rel_path=rel_path,
			aliases=aliases,
			display_name=display_name,
			config=config,
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
				f'"{self.config["git_remote_url"]}"'
				if self.config.get("git_remote_url")
				else self.config["root_node_name"]
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
	root: str,
	config: dict,
) -> nx.MultiDiGraph:
	# process config
	# --------------------------------------------------
	include_local_imports: bool = config["graph"]["include_local_imports"]
	edge_config: dict[str, Any] = config["edge"]

	# create graph, get dirs and package name
	# --------------------------------------------------
	G: nx.MultiDiGraph = nx.MultiDiGraph()
	directories: set[str] = get_relevant_directories(root)
	package_name: str = os.path.basename(os.path.abspath(root))
	assert package_name == config["PACKAGE_NAME"], f"{package_name = }, {config['PACKAGE_NAME'] = }"

	# Add nodes for directories and root
	# --------------------------------------------------
	directory_nodes: dict[str, Node] = {
		augment_module_name(directory, config) : Node.get_node(directory, config=config)
		for directory in directories
	}
	for node in directory_nodes.values():
		add_node(G, node, config=config)

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
			augmented_module_name: str = augment_module_name(
				os.path.dirname(python_file) or ".",
				config,
			)
			node = directory_nodes[augmented_module_name]
		else:
			node = Node.get_node(python_file, config=config)
			add_node(G, node, config=config)

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
					if module_parent == config["root_node_name"]:
						module_parent = "."

					parent_node: Node
					try:
						parent_node = directory_nodes[module_parent]
					except KeyError as e:
						if config["graph"]["except_if_missing_edges"]:
							raise KeyError(
								f"missing parent node for {node.orig_path = }: '{module_parent}'. if you think this is a mistake, set `graph.except_if_missing_edges` to `False` in the config"
							) from e
						else:
							warnings.warn(
								f"missing parent node for {node.orig_path = }: '{module_parent}'"
							)

					G.add_edge(
						parent_node,
						node,
						**edge_config["hierarchy"],
					)

	# add import edges
	# --------------------------------------------------
	if include_local_imports:
		print("!!!!!!!!!! INCLUDING LOCAL IMPORTS")
		# init empty lists, cant modify while iterating
		# -------------------------
		nodes_to_add: list[dict] = []
		edges_to_add: list[dict] = []
		for node_key in G.nodes:

			# get and check the node
			# -------------------------
			node: Node
			if isinstance(node_key, Node):
				node = node_key
			else:
				raise ValueError(
					f"unknown node type: {node_key = }, {type(node_key) = }"
				)

			# Read source code
			# # -------------------------
			node_path: str = node.orig_path
			if os.path.isdir(node_path):
				node_path = os.path.join(node_path, "__init__.py")
			elif node_path == ".":
				node_path = "__init__.py"

			try:
				with open(node_path, "r", encoding="utf-8") as f:
					source_code: str = f.read()
			except FileNotFoundError as e:
				if config["graph"]["except_if_missing_edges"]:
					raise FileNotFoundError(
						f"could not read source code for {node_path = }. if you think this is a mistake, set `graph.except_if_missing_edges` to `False` in the config"
					) from e
				else:
					warnings.warn(f"could not read source code for {node_path = }, skipping")
					continue

			# Get imports, dedupe, and loop over them
			# -------------------------
			imported_modules: list[str] = list(set(
				get_imports(source_code, allow_missing_imports=not config["graph"]["except_if_missing_edges"])
			))

			for imported_module in imported_modules:
				# Convert import to module name
				imported_module_name = imported_module



				# if stripping module prefix, remove it
				if config["graph"]["strip_module_prefix"]:
					imported_module_name = imported_module_name.removeprefix(
						package_name
					).removeprefix(".")
					if not imported_module_name:
						# if empty string, it means we are looking for the root
						imported_module_name = config["root_node_name"]

				if imported_module_name in nodes_dict:
		
					# adding edge to local import
					# -------------------------
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
					# -------------------------
					if config["graph"]["include_externals"]:
						nodes_to_add.append(
							dict(
								node_for_adding=imported_module_name,
								rank=0,  # for ranking/ordering of the nodes
								**config["node"][
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

		# add the nodes and edges we were missing
		# -------------------------

		# these nodes should only be present if we are including external imports of other packages
		for x in nodes_to_add:
			G.add_node(**x)

		for x in edges_to_add:
			G.add_edge(**x)

	return G


def write_dot(G: nx.DiGraph, output_filename: str, dot_attrs: dict) -> None:
	"""Write graph to a DOT file"""
	P: pydot.Dot = to_pydot(G)
	P.obj_dict["attributes"].update(dot_attrs)
	P.write_raw(output_filename)


def main(
	root: str | None = None,
	module: str | None = None,
	output: str = "output",
	output_fmt: Literal["svg", "png"] = "svg",
	config_file: str | None = None,
	print_cfg: bool = False,
	verbose: bool = False,
	**kwargs,
) -> None:
	"""Main function to generate and render a graphviz DOT file representing module dependencies

	# Keyword-only arguments
	- `root: str` (this arg or `module` is REQUIRED)
	    root directory to search for Python files
	- `module: str` (this arg or `root` is REQUIRED)
		name of module to generate graph for -- must be importable in the current environment
	- `output: str`
	    output filename (without extension)
	    default: `"output"`
	- `output_fmt: Literal["svg", "png"]`
	    output format for running `dot`
	    default: `"svg"`
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

	# handle kwargs and config
	# --------------------------------------------------

	# handle module vs explicit path
	if root is None:
		assert module is not None, f"either root or module must be given, got values for both: {root = }, {module = }"
		root = get_module_directory(module)
	elif module is None:
		assert root is not None, f"either root or module must be given, got values for both: {root = }, {module = }"
	else:
		raise ValueError("either root or module must be given, got `None` for both")
	

	# update config from file if given

	CONFIG: dict = deepcopy(_DEFAULT_CONFIG)
	print(kwargs)
	print(CONFIG["graph"])
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
	print(CONFIG["graph"])

	# process by converting none types, auto-detecting url_prefix from git if needed
	# special config processing: if we are doing a module, then we try to get the url prefix from there
	url_prefix: str | None = None
	if module is not None and CONFIG["url_prefix"] is None:
		url_prefix = get_package_repository_url(module)
	_process_config(CONFIG, root=root)
	if url_prefix is not None:
		CONFIG["url_prefix"] = url_prefix

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
	
	# set up some other globals
	# --------------------------------------------------

	# get global package name, set root node name if neededME
	CONFIG["PACKAGE_NAME"] = os.path.basename(os.path.abspath(root))
	if not CONFIG["graph"]["strip_module_prefix"]:
		CONFIG["root_node_name"] = CONFIG["PACKAGE_NAME"]
	
	# move directory, build graph, move back
	# --------------------------------------------------

	# change directory
	orig_dir: str = os.getcwd()
	os.chdir(root)

	print("# building graph...")
	G: nx.MultiDiGraph = build_graph(
		# pass "." since we just moved to the root directory
		root=".",
		config = CONFIG,
	)
	print(f"\t built graph with {len(G.nodes)} nodes and {len(G.edges)} edges")

	# change back to original directory
	os.chdir(orig_dir)


	# output
	# --------------------------------------------------

	# write the dot file first
	output_file_dot: str = f"{output}.dot"
	print(f"# writing dot file: {output_file_dot}")
	write_dot(G, f"{output_file_dot}", dot_attrs=CONFIG["dot_attrs"])

	if output_fmt == "html":
		# if HTML, generate it and put the dotfile contents inline
		print("# generating html...")
		from dep_graph_viz.html import generate_html

		generate_html(output_file_dot, f"{output}.html")
	else:
		# otherwise, run dot/graphviz and convert to desired format
		print("# running dot...")
		print("\tcommand:")
		cmd: str = f"dot -T{output_fmt} {output_file_dot} -o {output}.{output_fmt} {'-v' if verbose else ''}"
		print(f"\t$ {cmd}")
		subprocess.run(cmd, check=True)

	print("# done!")


if __name__ == "__main__":
	import fire

	fire.Fire(main)
