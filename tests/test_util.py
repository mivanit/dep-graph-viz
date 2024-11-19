from copy import deepcopy
import os
import subprocess
from unittest import mock
import pytest
import tempfile
from pathlib import Path

# Import the functions to be tested
from dep_graph_viz.dep_graph_viz import (
    _process_config,
    normalize_path,
    path_to_module,
    get_imports,
    get_python_files,
    get_relevant_directories,
    CONFIG,
    NULL_STRINGS,
    _DEFAULT_CONFIG,
)

@pytest.fixture(autouse=True)
def reset_config():
    """Reset the CONFIG dictionary to its default state before each test."""
    global CONFIG
    original_config = deepcopy(CONFIG)
    yield
    CONFIG = deepcopy(original_config)

@pytest.mark.parametrize(
    "path, expected",
    [
        (r"C:\path\to\file", "C:/path/to/file"),
        ("/path/to/file", "/path/to/file"),
        ("path\\with/mixed\\separators", "path/with/mixed/separators"),
        ("", ""),
        ("relative\\path", "relative/path"),
    ],
)
def test_normalize_path(path, expected):
    normalized_path = normalize_path(path)
    assert normalized_path == expected, f"{path = }, {expected = }, {normalized_path = }"

@pytest.mark.parametrize(
    "path, expected",
    [
        ("module/submodule/file.py", "module.submodule.file"),
        (r"module\submodule\file.py", "module.submodule.file"),
        ("file.py", "file"),
        ("dir.with.dots/file.py", "dir.with.dots.file"),
        ("file", "file"),
        ("file.pyc", "file.pyc"),
        ("", ""),
    ],
)
def test_path_to_module(path, expected):
    path_as_module = path_to_module(path)
    assert path_as_module == expected, f"{path = }, {expected = }, {path_as_module = }"


@pytest.mark.parametrize(
    "source, expected",
    [
        ("import os", ["os"]),
        ("import os\nimport sys", ["os", "sys"]),
        ("from collections import defaultdict", ["collections"]),
        ("from math import sqrt", ["math"]),
        ("import module.submodule", ["module.submodule"]),
        (
            """
import os
import sys
from collections import defaultdict
from math import sqrt
""",
            ["os", "sys", "collections", "math"],
        ),
        (
            """
# No imports here
def foo():
    pass
""",
            [],
        ),
        (
            """
import os
import sys
from collections import defaultdict
from math import sqrt
import module.submodule
from package.module import Class
""",
            ["os", "sys", "collections", "math", "module.submodule", "package.module"],
        ),
        ("", []),
    ],
)
def test_get_imports(source, expected):
    assert get_imports(source) == expected, f"{expected = }\nsource = '''\n{source}'''"



@pytest.mark.parametrize(
    "source, expected_exception",
    [
        ("import", SyntaxError),
    ],
)
def test_get_imports_error(source, expected_exception):
    with pytest.raises(expected_exception):
        get_imports(source)


def test_get_python_files(tmp_path):
    # Create temporary directory structure
    (tmp_path / "file1.py").write_text("")
    (tmp_path / "file2.txt").write_text("")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "file3.py").write_text("")
    (tmp_path / "subdir" / "file4.pyc").write_text("")
    (tmp_path / "subdir" / "nested").mkdir()
    (tmp_path / "subdir" / "nested" / "file5.py").write_text("")

    python_files = get_python_files(root=str(tmp_path))
    expected_files = {
        "file1.py",
        "subdir/file3.py",
        "subdir/nested/file5.py",
    }
    assert set(python_files) == expected_files

    # Test with no python files
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    python_files = get_python_files(root=str(empty_dir))
    assert python_files == []

def test_get_relevant_directories(tmp_path):
    # Create temporary directory structure
    (tmp_path / "file1.py").write_text("")
    (tmp_path / "file2.txt").write_text("")
    (tmp_path / "subdir").mkdir()
    (tmp_path / "subdir" / "file3.py").write_text("")
    (tmp_path / "subdir" / "nested").mkdir()
    (tmp_path / "subdir" / "nested" / "file4.py").write_text("")

    directories = get_relevant_directories(root=str(tmp_path))
    expected_directories = {
        ".",
        "subdir",
        "subdir/nested",
    }
    assert set(directories) == expected_directories

    # Test with no python files
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    directories = get_relevant_directories(root=str(empty_dir))
    assert directories == set()

def test_process_config_convert_none():
    CONFIG["edge"]["thing"] = {"color": "none", "style": "dashed"}
    CONFIG["node"]["otherthing"] = {"shape": "null", "label": "Node"}

    _process_config(config=CONFIG)

    assert CONFIG["edge"]["thing"]["style"] == "dashed"
    assert CONFIG["edge"]["thing"]["color"] is None
    assert CONFIG["node"]["otherthing"]["label"] == "Node"
    assert CONFIG["node"]["otherthing"]["shape"] is None


def test_process_config_no_auto_url_format():
    CONFIG["url_prefix"] = None
    CONFIG["auto_url_format"] = None

    _process_config()

    assert CONFIG["url_prefix"] is None

def test_process_config_root_none():
    CONFIG["url_prefix"] = None
    CONFIG["auto_url_format"] = "{git_remote_url}/blob/{git_branch}/"

    _process_config(root=None)

    assert CONFIG["url_prefix"] is None

def test_process_config_preserve_url_prefix():
    CONFIG["url_prefix"] = "https://example.com/repo/"

    _process_config()

    assert CONFIG["url_prefix"] == "https://example.com/repo/"


def test_get_imports_syntax_error():
    source_code = "def func(:\n pass"
    with pytest.raises(SyntaxError):
        get_imports(source_code)

def test_get_python_files_invalid_root():
    with pytest.raises(FileNotFoundError):
        get_python_files(root="non_existent_directory")

def test_get_relevant_directories_invalid_root():
    with pytest.raises(FileNotFoundError):
        get_relevant_directories(root="non_existent_directory")
