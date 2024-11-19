import pytest

# Import the functions to be tested
from dep_graph_viz.dep_graph_viz import (
	get_python_files,
	get_relevant_directories,
)


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


def test_get_python_files_invalid_root():
	with pytest.raises(FileNotFoundError):
		get_python_files(root="non_existent_directory")


def test_get_relevant_directories_invalid_root():
	with pytest.raises(FileNotFoundError):
		get_relevant_directories(root="non_existent_directory")
