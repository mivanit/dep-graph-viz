import ast
import glob
import os
from pathlib import Path
import warnings


from dep_graph_viz.util.paths import normalize_path


def pprint_ast_aliases(aliases: list[ast.alias]) -> str:
	"Pretty print a list of ast.alias objects"
	x: str = ", ".join([
		f"{alias.name} as {alias.asname} : {alias.lineno} - {alias.end_lineno} : {alias.col_offset} - {alias.end_col_offset}" 
		for alias in aliases
	])

	return f"[{x}]"

def get_imports(source_code: str, allow_missing_imports: bool = False) -> list[str]:
	"Get all the imports from a source code string"
	tree: ast.Module = ast.parse(source_code)
	imports: list[str] = []
	for node in ast.walk(tree):
		# Check if node is an import statement
		if isinstance(node, ast.Import):
			for alias in node.names:
				if alias.name is None:
					if allow_missing_imports:
						warnings.warn(f"node.names[alias].name is None: {node = } {alias = }, skipping it")
					else:
						raise ValueError(
							f"node.names[alias].name is None: {node = } {alias = }",
							"if you want to allow missing imports, set `graph.except_if_missing_edges` to `False`",
						)
				else:
					imports.append(alias.name)
		# Check if node is a from ... import ... statement
		elif isinstance(node, ast.ImportFrom):
			if node.module is None:
				if allow_missing_imports:
					warnings.warn(f"module name is None, skipping it: {node = }, {node.module = }, {pprint_ast_aliases(node.names) = }, {node.level = }")
				else:
					raise ValueError(
						f"module name is None: {node = }, {node.module = }, {pprint_ast_aliases(node.names) = }, {node.level = }",
						"if you want to allow missing imports, set `graph.except_if_missing_edges` to `False`",
					)
			else:
				imports.append(node.module)

	return imports

ast.alias

def get_python_files(root: str = ".") -> list[str]:
	"Get all Python files in a directory and its subdirectories"
	if not os.path.exists(root):
		raise FileNotFoundError(f"root directory not found: {root}")

	glob_pattern: str = Path(root).as_posix().rstrip("/") + "/**/*.py"
	files: list[str] = glob.glob(glob_pattern, recursive=True)
	files = [
		Path(os.path.relpath(file, os.path.abspath(root))).as_posix() for file in files
	]
	return files


def get_relevant_directories(root: str = ".") -> set[str]:
	"from a root, get a set of all directories with python files in them"
	if not os.path.exists(root):
		print(os.getcwd())
		raise FileNotFoundError(f"root directory not found: '{root}'")

	# get all directories with python files
	directories_with_py_files: set[str] = {
		os.path.dirname(file) for file in get_python_files(root)
	}
	directories_with_py_files = {
		x if x != "" else "."  # map empty string to root
		for x in directories_with_py_files
	}
	# allocate output
	all_directories: set[str] = set(directories_with_py_files)
	all_directories.add(".")

	# get every directory between root and root dir
	# since some directories might have no python files, but contain dirs with python files
	for directory in directories_with_py_files:
		while directory and os.path.abspath(directory) != os.path.abspath(root):
			parent_directory = os.path.dirname(directory)
			if parent_directory and parent_directory != directory:
				all_directories.add(parent_directory)
			directory = parent_directory

	if "" in all_directories:
		raise ValueError(f"empty string found in {all_directories = }")
	all_directories = set(map(normalize_path, all_directories))

	return all_directories
