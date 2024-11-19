import sys
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

		# Edge cases with multiple separators
        ("///triple/slash", "///triple/slash"),
        ("\\\\\\triple\\backslash", "///triple/backslash"),
        ("mixed///\\\\\\separators", "mixed//////separators"),
        
        # Special characters and spaces
        ("path with\ttabs", "path with\ttabs"),
        ("path with\nnewlines", "path with\nnewlines"),
        ("path with\rcarriage returns", "path with\rcarriage returns"),
        ("  path  with  multiple  spaces  ", "  path  with  multiple  spaces  "),
        ("!@#$%^&*()special/chars", "!@#$%^&*()special/chars"),
        ("パス/с-пътя/țcale", "パス/с-пътя/țcale"),
        
        # Windows specific
        ("C:", "C:"),
        ("C:\\", "C:/"),
        ("\\\\server\\share", "//server/share"),
        ("\\\\?\\C:\\Extended\\Path", "//?/C:/Extended/Path"),
        ("\\\\?\\UNC\\server\\share", "//?/UNC/server/share"),
        
        # URL-like paths
        ("file:///path/to/file", "file:///path/to/file"),
        ("http://example.com/path", "http://example.com/path"),
        
        # Crazy combinations
        ("C:\\Program Files (x86)\\Company\\App", "C:/Program Files (x86)/Company/App"),
        ("\\\\?\\C:\\Program Files\\Company Name\\App 1.0\\", "//?/C:/Program Files/Company Name/App 1.0/"),
        ("./../../relative/path/../complex/./././/path", "./../../relative/path/../complex/./././/path"),
        
        # Zero-width and special Unicode characters
        ("path/with\u200b/zero/width/space", "path/with\u200b/zero/width/space"),
        ("path/with\u2028/line/separator", "path/with\u2028/line/separator"),
        ("path/with\u2029/paragraph/separator", "path/with\u2029/paragraph/separator"),
        
        # Control characters
        ("path/with\x00/null", "path/with\x00/null"),
        ("path/with\x1f/unit/separator", "path/with\x1f/unit/separator"),
        ("path/with\x7f/delete", "path/with\x7f/delete"),
        
        # Maximum path components
        ("/".join(["a"] * 1000), "/".join(["a"] * 1000)),
        ("\\".join(["a"] * 1000), "/".join(["a"] * 1000)),
        
        # Empty components
        ("path//with//empty//components", "path//with//empty//components"),
        ("path\\\\with\\\\empty\\\\components", "path//with//empty//components"),
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
		("module/submodule/file", "module.submodule.file"),
		("/absolute/path/to/module.py", "absolute.path.to.module"),
		("module/submodule/__init__.py", "module.submodule.__init__"),
		("module/submodule/__main__.py", "module.submodule.__main__"),

        # Special module names
        ("__init__.py", "__init__"),
        ("__main__.py", "__main__"),
        ("__all__.py", "__all__"),
        ("__version__.py", "__version__"),
        
        # Complex paths
        ("very/deep/nested/module/structure/file.py", "very.deep.nested.module.structure.file"),
        ("single_file.py", "single_file"),
        ("_internal.py", "_internal"),
        ("_private/_utils.py", "_private._utils"),
                
        # Numbers in valid module names
        ("mod1/mod2/mod3.py", "mod1.mod2.mod3"),
        ("v1/v2/v3.py", "v1.v2.v3"),
        
        # Underscores
        ("my_module/my_submodule/my_file.py", "my_module.my_submodule.my_file"),
        ("__my_module__/__my_file__.py", "__my_module__.__my_file__"),
        
        # Maximum length valid paths
        ("/".join(["a"] * 100) + ".py", ".".join(["a"] * 100)),
	],
)
def test_path_to_module(path, expected):
	try:
		path_as_module = path_to_module(path)
	except ValueError as e:
		raise AssertionError(f"{path = }, {expected = }") from e
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
		("", ValueError),

		# Invalid characters in module names
        ("module-name/file.py", ValueError),  # Hyphens not allowed
        ("module name/file.py", ValueError),  # Spaces not allowed
        ("module+name/file.py", ValueError),  # Special chars not allowed
        ("123module/file.py", ValueError),    # Can't start with number
        
        # Invalid path patterns
        ("../relative/path.py", ValueError),
        ("./current/path.py", ValueError),
        ("/./dot/path.py", ValueError),
        ("/../dotdot/path.py", ValueError),
        
        # Other Python file extensions
        ("file.pyw", ValueError),
        ("file.pyo", ValueError),
        ("file.pyd", ValueError),
        
        # Hidden files and directories
        (".hidden_module.py", ValueError),
        (".hidden_dir/module.py", ValueError),
        ("module/.hidden_submodule/file.py", ValueError),
        
        # System-specific invalid paths
        ("CON.py", ValueError) if sys.platform == "win32" else ("dummy.py", ValueError),
        ("PRN.py", ValueError) if sys.platform == "win32" else ("dummy.py", ValueError),
        ("AUX.py", ValueError) if sys.platform == "win32" else ("dummy.py", ValueError),
        
        # Invalid Unicode characters
        ("module\x00name/file.py", ValueError),  # Null character
        ("module\x1fname/file.py", ValueError),  # Unit separator
        ("module\x7fname/file.py", ValueError),  # Delete character
        
        # Path traversal attempts
        ("../../../etc/passwd.py", ValueError),
        ("..\\..\\..\\windows\\system32\\file.py", ValueError),

		# unicode
		("módulo/submódulo/archivo.py", ValueError),
		("ываыва/фыва/фыва.py", ValueError),
		("module/サブモジュール/ファイル.py", ValueError),
		("module/子模块/文件.py", ValueError),		
        
        # Extra dots
        ("...py", ValueError),
        ("file..py", ValueError),
        ("module..name/file.py", ValueError),
        
        # Mixed path separators with dots
        ("module.name\\file.py", ValueError),
        ("module\\name.module\\file.py", ValueError),
        
        # Very long invalid paths
        (".".join(["a"] * 100) + ".py", ValueError),  # Too many dots
        ("/" + "/".join(["." + str(i) for i in range(100)]) + ".py", ValueError),  # Many hidden components
	],
)
def test_path_to_module_except(path, expected_exception):
	with pytest.raises(expected_exception):
		path_to_module(path)
