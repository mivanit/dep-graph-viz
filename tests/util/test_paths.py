import pytest

# Import the functions to be tested
from dep_graph_viz.dep_graph_viz import normalize_path, path_to_module


@pytest.mark.parametrize(
	"path, expected",
	[
		(r"C:\path\to\file", "C:/path/to/file"),
		("/path/to/file", "/path/to/file"),
		("path\\with/mixed\\separators", "path/with/mixed/separators"),
		("", ""),
		("relative\\path", "relative/path"),
		("C:\\\\path\\\\to\\\\file", "C://path//to//file"),
		("/path/with/trailing/slash/", "/path/with/trailing/slash/"),
		("\\path\\starting\\with\\backslash", "/path/starting/with/backslash"),
		("path/with/./dot", "path/with/./dot"),
		("path/with/../dotdot", "path/with/../dotdot"),
		("path with spaces\\file", "path with spaces/file"),
		("path/with/üñíçødé/characters", "path/with/üñíçødé/characters"),
		("\\", "/"),
		("//", "//"),
	],
)
def test_normalize_path(path, expected):
	normalized_path = normalize_path(path)
	assert (
		normalized_path == expected
	), f"{path = }, {expected = }, {normalized_path = }"


@pytest.mark.parametrize(
	"path, expected",
	[
		("module/submodule/file.py", "module.submodule.file"),
		(r"module\submodule\file.py", "module.submodule.file"),
		("file.py", "file"),
		("file", "file"),
		("", ""),
		("module/submodule/file", "module.submodule.file"),
		("/absolute/path/to/module.py", "absolute.path.to.module"),
		("module/submodule/__init__.py", "module.submodule.__init__"),
		("module/submodule/__main__.py", "module.submodule.__main__"),
	],
)
def test_path_to_module(path, expected):
	path_as_module = path_to_module(path)
	assert path_as_module == expected, f"{path = }, {expected = }, {path_as_module = }"


@pytest.mark.parametrize(
	"path, expected_exception",
	[
		("module/submodule/file.name.with.dots.py", ValueError),
		("module.with.dots/file.py", ValueError),
		("file.name.with.dots.py", ValueError),
		("file.tar.gz", ValueError),
		(".../file.py", ValueError),
		("module/.hidden/file.py", ValueError),
		("dir.with.dots/file.py", ValueError),
		("file.pyc", ValueError),
		("dir.with.dots/file.py", ValueError),
		(".file.py", ValueError),
		("./file.py", ValueError),
	],
)
def test_path_to_module_except(path, expected_exception):
	with pytest.raises(expected_exception):
		path_to_module(path)
