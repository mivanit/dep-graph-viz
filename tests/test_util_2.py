# import pytest
# import os
# import networkx as nx
# import tempfile
# from pathlib import Path
# import shutil
# import subprocess
# from unittest.mock import patch, MagicMock
# from typing import Generator

# # Import the module under test
# from dep_graph_viz.dep_graph_viz import (
#     normalize_path,
#     path_to_module,
#     get_imports,
#     get_python_files,
#     get_relevant_directories,
#     add_node,
#     _process_config,
#     Node,
#     CONFIG,
# )

# @pytest.fixture
# def temp_project_dir() -> Generator[str, None, None]:
#     """Create a temporary directory with a sample project structure."""
#     with tempfile.TemporaryDirectory() as tmpdir:
#         # Create a typical Python project structure
#         project_structure = {
#             "__init__.py": "",
#             "main.py": "import utils\nfrom . import helpers",
#             "utils/__init__.py": "",
#             "utils/helper.py": "from ..main import something",
#             "scripts/standalone.py": "import os\nimport sys",
#             "empty_dir/": None,
#             "nested/deep/directory/__init__.py": "",
#             "nested/deep/directory/module.py": "import pandas",
#         }
        
#         for path, content in project_structure.items():
#             full_path = os.path.join(tmpdir, path)
#             if content is None:  # Directory
#                 os.makedirs(full_path, exist_ok=True)
#             else:  # File
#                 os.makedirs(os.path.dirname(full_path), exist_ok=True)
#                 with open(full_path, "w") as f:
#                     f.write(content)
        
#         yield tmpdir

# class TestPathUtils:
#     def test_normalize_path(self):
#         assert normalize_path(r"path\to\file") == "path/to/file"
#         assert normalize_path("path/to/file") == "path/to/file"
#         assert normalize_path("") == ""
#         assert normalize_path(r"C:\Windows\Path") == "C:/Windows/Path"

#     def test_path_to_module(self):
#         assert path_to_module("path/to/file.py") == "path.to.file"
#         assert path_to_module("file.py") == "file"
#         assert path_to_module("") == ""
#         assert path_to_module("no_extension") == "no_extension"
#         assert path_to_module("path/with/../file.py") == "path.with...file"

# class TestImportParsing:
#     def test_get_imports_simple(self):
#         code = """
#         import os
#         import sys as system
#         from pathlib import Path
#         """
#         imports = get_imports(code)
#         assert set(imports) == {"os", "sys", "pathlib"}

#     def test_get_imports_complex(self):
#         code = """
#         from ..relative import module
#         from .local import thing
#         from __future__ import annotations
#         import pkg1, pkg2
#         """
#         imports = get_imports(code)
#         assert set(imports) == {"relative", "local", "__future__", "pkg1", "pkg2"}

#     def test_get_imports_empty(self):
#         assert get_imports("") == []
#         assert get_imports("# just a comment") == []
#         assert get_imports("x = 5") == []

#     def test_get_imports_syntax_error(self):
#         with pytest.raises(SyntaxError):
#             get_imports("import from")

# class TestFileDiscovery:
#     def test_get_python_files(self, temp_project_dir):
#         files = get_python_files(temp_project_dir)
#         expected_files = {
#             "__init__.py",
#             "main.py",
#             "utils/__init__.py",
#             "utils/helper.py",
#             "scripts/standalone.py",
#             "nested/deep/directory/__init__.py",
#             "nested/deep/directory/module.py"
#         }
#         assert {os.path.relpath(f, temp_project_dir) for f in files} == {
#             normalize_path(f) for f in expected_files
#         }

#     def test_get_python_files_nonexistent_dir(self):
#         with pytest.raises(FileNotFoundError):
#             get_python_files("/nonexistent/directory")

#     def test_get_python_files_empty_dir(self, tmp_path):
#         assert get_python_files(tmp_path) == []

# class TestDirectoryDiscovery:
#     def test_get_relevant_directories(self, temp_project_dir):
#         dirs = get_relevant_directories(temp_project_dir)
#         expected_dirs = {
#             ".",
#             "utils",
#             "scripts",
#             "nested",
#             "nested/deep",
#             "nested/deep/directory"
#         }
#         assert {normalize_path(d) for d in dirs} == expected_dirs

#     def test_get_relevant_directories_empty(self, tmp_path):
#         dirs = get_relevant_directories(tmp_path)
#         assert dirs == {"."}

#     def test_get_relevant_directories_nonexistent(self):
#         with pytest.raises(FileNotFoundError):
#             get_relevant_directories("/nonexistent/directory")

# class TestGraphOperations:
#     @pytest.fixture
#     def sample_graph(self):
#         return nx.MultiDiGraph()

#     def test_add_node(self, sample_graph):
#         node = Node(
#             path="test/module.py",
#             node_type="module_file",
#             url="http://example.com/test/module.py"
#         )
#         add_node(sample_graph, node)
#         assert node in sample_graph
#         assert sample_graph.nodes[node]["URL"] == '"http://example.com/test/module.py"'

#     def test_add_duplicate_node(self, sample_graph):
#         node = Node(
#             path="test/module.py",
#             node_type="module_file"
#         )
#         add_node(sample_graph, node)
#         with pytest.raises(ValueError):
#             add_node(sample_graph, node)

# class TestConfigProcessing:
#     def setup_method(self):
#         self.original_config = CONFIG.copy()

#     def teardown_method(self):
#         global CONFIG
#         CONFIG = self.original_config

#     @patch('subprocess.check_output')
#     def test_process_config_with_git(self, mock_check_output):
#         mock_check_output.side_effect = [
#             "https://github.com/user/repo.git\n",
#             "main\n"
#         ]
#         CONFIG["url_prefix"] = None
#         CONFIG["auto_url_format"] = "{git_remote_url}/blob/{git_branch}/"
#         _process_config(".")
#         assert CONFIG["url_prefix"] == "https://github.com/user/repo/blob/main/"

#     @patch('subprocess.check_output')
#     def test_process_config_git_error(self, mock_check_output):
#         mock_check_output.side_effect = subprocess.CalledProcessError(1, "git")
#         CONFIG["url_prefix"] = None
#         CONFIG["auto_url_format"] = "{git_remote_url}/blob/{git_branch}/"
#         _process_config(".")
#         assert CONFIG["url_prefix"] is None

#     def test_process_config_null_values(self):
#         CONFIG["edge"] = {"style": "none", "color": "null"}
#         CONFIG["node"] = {"shape": "NULL"}
#         _process_config(None)
#         assert CONFIG["edge"]["style"] is None
#         assert CONFIG["edge"]["color"] is None
#         assert CONFIG["node"]["shape"] is None

# class TestIntegration:
#     def test_full_workflow(self, temp_project_dir):
#         # Test the entire workflow from file discovery to graph creation
#         files = get_python_files(temp_project_dir)
#         assert len(files) > 0
        
#         dirs = get_relevant_directories(temp_project_dir)
#         assert len(dirs) > 0
        
#         # Create a graph with some nodes and check imports
#         G = nx.MultiDiGraph()
#         for file in files:
#             with open(file) as f:
#                 imports = get_imports(f.read())
#             assert isinstance(imports, list)
            
#             node = Node(
#                 path=os.path.relpath(file, temp_project_dir),
#                 node_type="module_file"
#             )
#             add_node(G, node)
        
#         assert len(G.nodes) == len(files)