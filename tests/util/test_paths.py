import sys
import pytest
import os
import sys
import pytest
from typing import Callable
import pytest
import importlib.metadata
from unittest.mock import patch, MagicMock



from dep_graph_viz.util.paths import normalize_path, path_to_module, get_module_directory, get_package_repository_url


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
		(
			"\\\\?\\C:\\Program Files\\Company Name\\App 1.0\\",
			"//?/C:/Program Files/Company Name/App 1.0/",
		),
		(
			"./../../relative/path/../complex/./././/path",
			"./../../relative/path/../complex/./././/path",
		),
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
		(
			"very/deep/nested/module/structure/file.py",
			"very.deep.nested.module.structure.file",
		),
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
		("123module/file.py", ValueError),  # Can't start with number
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
		(
			"/" + "/".join(["." + str(i) for i in range(100)]) + ".py",
			ValueError,
		),  # Many hidden components
	],
)
def test_path_to_module_except(path, expected_exception):
	with pytest.raises(expected_exception):
		path_to_module(path)





# Test data constants
STDLIB_MODULES = ['json', 'os', 'typing', 'pathlib']
DEPENDENCY_MODULES = ['networkx', 'pydot', 'pytest', 'fire']
BUILTIN_MODULES = ['builtins', '_thread', 'sys']
NESTED_MODULES = ['networkx.drawing', 'muutils.json_serialize']

def test_stdlib_modules() -> None:
    """Test that we can get directories for standard library modules"""
    for module_name in STDLIB_MODULES:
        path = get_module_directory(module_name)
        assert os.path.isdir(path), f"Path not a directory: {path}"
        assert os.path.exists(os.path.join(path, f"{module_name}.py")) or \
               os.path.exists(os.path.join(path, "__init__.py")), \
               f"No Python source found in {path}"

def test_dependency_modules() -> None:
    """Test that we can get directories for installed dependencies"""
    for module_name in DEPENDENCY_MODULES:
        path = get_module_directory(module_name)
        assert os.path.isdir(path), f"Path not a directory: {path}"
        assert os.path.exists(os.path.join(path, "__init__.py")) or \
               os.path.exists(os.path.join(path, f"{module_name}.py")), \
               f"No Python source found in {path}"

def test_builtin_modules_raise_properly() -> None:
    """Test that built-in modules without __file__ raise AttributeError"""
    for module_name in BUILTIN_MODULES:
        with pytest.raises(AttributeError) as excinfo:
            get_module_directory(module_name)
        assert "has no __file__ attribute" in str(excinfo.value)

def test_nonexistent_module() -> None:
    """Test that importing a non-existent module raises ImportError"""
    with pytest.raises(ImportError):
        get_module_directory('definitely_not_a_real_module_12345')

def test_nested_modules() -> None:
    """Test that we can get directories for nested modules"""
    for module_name in NESTED_MODULES:
        path = get_module_directory(module_name)
        assert os.path.isdir(path)
        assert os.path.exists(os.path.join(path, "__init__.py"))

def test_return_type() -> None:
    """Test that the function returns a string"""
    path = get_module_directory('json')
    assert isinstance(path, str)

def test_absolute_path() -> None:
    """Test that returned paths are absolute"""
    path = get_module_directory('json')
    assert os.path.isabs(path)

@pytest.mark.skipif(sys.platform != 'win32', reason="Windows-specific path test")
def test_windows_path_format() -> None:
    """Test Windows path formatting"""
    path = get_module_directory('json')
    assert ':' in path  # Windows paths have drive letter with colon
    assert '\\' in path  # Windows uses backslashes

@pytest.mark.skipif(sys.platform == 'win32', reason="Unix-specific path test")
def test_unix_path_format() -> None:
    """Test Unix path formatting"""
    path = get_module_directory('json')
    assert path.startswith('/')  # Unix absolute paths start with /
    assert '\\' not in path  # Unix doesn't use backslashes

def test_module_attributes() -> None:
    """Test that the function works with modules that have various attributes"""
    # Module with __path__ (package), without __path__ (single file), and with both
    TEST_MODULES = ['networkx', 'json', 'pytest']
    for module_name in TEST_MODULES:
        path = get_module_directory(module_name)
        assert os.path.isdir(path)

TEST_MODULES_AND_SUFFIXES = [
    ('json', 'json'),
    ('networkx', 'networkx'),
    ('pytest', 'pytest'),
]

@pytest.mark.parametrize("module_name,expected_suffix", TEST_MODULES_AND_SUFFIXES)
def test_directory_names(module_name: str, expected_suffix: str) -> None:
    """Test that directory names match expected patterns"""
    path = get_module_directory(module_name)
    assert os.path.basename(path) == expected_suffix or \
           os.path.basename(path) == 'site-packages'  # handle installed packages

def test_directory_permissions() -> None:
    """Test that we have read access to returned directories"""
    path = get_module_directory('json')
    assert os.access(path, os.R_OK), f"No read access to {path}"

def test_same_module_multiple_calls() -> None:
    """Test that multiple calls for the same module return the same path"""
    path1 = get_module_directory('json')
    path2 = get_module_directory('json')
    assert path1 == path2

INVALID_MODULE_NAMES = [
    "",  # empty string
    "   ",  # whitespace
    "\n",  # newline
    "module.name.",  # trailing dot
    "module..name",  # double dot
    "123invalid",  # starts with number
    "invalid!name",  # invalid characters
]

@pytest.mark.parametrize("invalid_input", INVALID_MODULE_NAMES)
def test_invalid_module_names(invalid_input: str) -> None:
    """Test that invalid module names raise appropriate errors"""
    with pytest.raises((ImportError, ValueError, SyntaxError)):
        get_module_directory(invalid_input)
        



KNOWN_PACKAGES = [
    "requests",
    "pytest",
    "networkx",
]

MOCK_METADATA = {
    "package1": {
        "project_urls": '{"Repository": "https://example.com/repo1"}',
    },
    "package2": {
        "home-page": "https://example.com/repo2",
    },
    "package3": {
        "download-url": "https://example.com/repo3",
    },
    "package4": {
        "project_urls": '{"Source Code": "https://example.com/repo4"}',
    },
    "package5": {  # No repo info at all
        "author": "Test Author",
        "version": "1.0.0"
    },
}

def test_known_packages():
    """Test getting repository URLs for known packages"""
    for package_name in KNOWN_PACKAGES:
        try:
            url = get_package_repository_url(package_name)
            assert url is not None
            assert url.startswith("http")  # Basic URL validation
        except importlib.metadata.PackageNotFoundError:
            pytest.skip(f"Package {package_name} not installed")

def test_nonexistent_package():
    """Test behavior with non-existent package"""
    with pytest.raises(importlib.metadata.PackageNotFoundError):
        get_package_repository_url("definitely_not_a_real_package_12345")

@pytest.mark.parametrize("package_name,metadata,expected", [
    ("package1", MOCK_METADATA["package1"], "https://example.com/repo1"),
    ("package2", MOCK_METADATA["package2"], "https://example.com/repo2"),
    ("package3", MOCK_METADATA["package3"], "https://example.com/repo3"),
    ("package4", MOCK_METADATA["package4"], "https://example.com/repo4"),
    ("package5", MOCK_METADATA["package5"], None),
])
def test_different_metadata_formats(package_name: str, metadata: dict, expected: str|None):
    """Test handling of different metadata formats"""
    mock_metadata = MagicMock()
    mock_metadata.__getitem__.side_effect = metadata.__getitem__
    mock_metadata.__contains__.side_effect = metadata.__contains__

    with patch('importlib.metadata.metadata', return_value=mock_metadata):
        url = get_package_repository_url(package_name)
        assert url == expected

def test_return_type():
    """Test return type is either str or None"""
    try:
        url = get_package_repository_url(KNOWN_PACKAGES[0])
        assert isinstance(url, str) or url is None
    except importlib.metadata.PackageNotFoundError:
        pytest.skip(f"Package {KNOWN_PACKAGES[0]} not installed")

def test_invalid_project_urls():
    """Test handling of invalid project_urls JSON"""
    mock_metadata = MagicMock()
    mock_metadata.__contains__.return_value = True
    mock_metadata.__getitem__.return_value = "not valid json"

    with patch('importlib.metadata.metadata', return_value=mock_metadata):
        url = get_package_repository_url("test-package")
        assert url is None