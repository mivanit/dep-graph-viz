import ast
import glob
import os
from pathlib import Path


from dep_graph_viz.util.paths import normalize_path


def get_imports(source_code: str) -> list[str]:
	"Get all the imports from a source code string"
	tree: ast.Module = ast.parse(source_code)
	imports: list[str] = []
	for node in ast.walk(tree):
		# Check if node is an import statement
		if isinstance(node, ast.Import):
			for alias in node.names:
				if alias.name is None:
					raise ValueError(
						f"node.names[alias].name is None: {node = } {alias = }"
					)
				imports.append(alias.name)
		# Check if node is a from ... import ... statement
		elif isinstance(node, ast.ImportFrom):
			if node.module is None:
				raise ValueError(f"module name is None: {node = }")
			imports.append(node.module)

	return imports


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
