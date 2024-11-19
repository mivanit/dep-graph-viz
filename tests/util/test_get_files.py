import pytest
import os
import stat

# Import the functions to be tested
from dep_graph_viz.dep_graph_viz import get_python_files, get_relevant_directories


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
	assert directories == {"."}


def test_get_python_files_invalid_root():
	with pytest.raises(FileNotFoundError):
		get_python_files(root="non_existent_directory")


def test_get_relevant_directories_invalid_root():
	with pytest.raises(FileNotFoundError):
		get_relevant_directories(root="non_existent_directory")



# Import the functions to be tested


@pytest.fixture
def setup_fs_structure(tmp_path):
	"""Fixture to create various file system structures"""

	def create_structure(structure):
		for path, content in structure.items():
			full_path = tmp_path / path
			if content is None:  # Directory
				full_path.mkdir(parents=True, exist_ok=True)
			else:  # File
				full_path.parent.mkdir(parents=True, exist_ok=True)
				full_path.write_text(content)

	return create_structure


@pytest.mark.parametrize(
	"fs_structure, expected_files",
	[
		# Basic structure
		(
			{
				"file1.py": "print('hello')",
				"file2.txt": "not python",
				"subdir/file3.py": "def func(): pass",
			},
			["file1.py", "subdir/file3.py"],
		),
		# Empty directories
		(
			{
				"empty_dir": None,
				"file1.py": "",
			},
			["file1.py"],
		),
		# Deep nesting
		(
			{
				"a/b/c/d/e/deep.py": "",
				"a/b/sibling.py": "",
			},
			["a/b/c/d/e/deep.py", "a/b/sibling.py"],
		),
		# Multiple file types
		(
			{
				"script.py": "",
				"script.pyc": "",
				"script.pyo": "",
				"script.pyw": "",
				"script.py.bak": "",
			},
			["script.py"],
		),
		# Special characters in paths
		(
			{
				"with spaces/file.py": "",
				"with-hyphen/file.py": "",
				"with_underscore/file.py": "",
				"with.dot/file.py": "",
			},
			[
				"with spaces/file.py",
				"with-hyphen/file.py",
				"with_underscore/file.py",
				"with.dot/file.py",
			],
		),
		# Unicode paths
		(
			{
				"目录/文件.py": "",
				"καταγραφή/αρχείο.py": "",
				"디렉토리/파일.py": "",
			},
			["目录/文件.py", "καταγραφή/αρχείο.py", "디렉토리/파일.py"],
		),
		# Empty files and directories
		(
			{
				"empty.py": "",
				"empty_dir": None,
				"dir_with_empty/empty.py": "",
			},
			["empty.py", "dir_with_empty/empty.py"],
		),
		# Many files in one directory
		(
			{
				**{f"many_files/file{i}.py": "" for i in range(10)},
				"many_files/not_python.txt": "",
			},
			[f"many_files/file{i}.py" for i in range(10)],
		),
	],
)
def test_get_python_files_parametrized(
	tmp_path, setup_fs_structure, fs_structure, expected_files
):
	setup_fs_structure(fs_structure)
	found_files = get_python_files(root=str(tmp_path))
	assert set(found_files) == set(expected_files)


@pytest.mark.parametrize(
	"fs_structure, expected_dirs",
	[
		# Basic structure
		(
			{
				"file1.py": "",
				"subdir/file2.py": "",
				"subdir/nested/file3.py": "",
			},
			{".", "subdir", "subdir/nested"},
		),
		# Empty directories with no Python files
		(
			{
				"empty_dir": None,
				"file1.py": "",
				"empty_dir2/empty_subdir": None,
			},
			{"."},
		),
		# Deep nesting
		(
			{
				"a/b/c/d/e/deep.py": "",
				"a/b/sibling.py": "",
			},
			{".", "a", "a/b", "a/b/c", "a/b/c/d", "a/b/c/d/e"},
		),
		# Multiple directories at same level
		(
			{
				"dir1/file1.py": "",
				"dir2/file2.py": "",
				"dir3/file3.py": "",
			},
			{".", "dir1", "dir2", "dir3"},
		),
		# Mixed Python and non-Python files
		(
			{
				"dir1/file.py": "",
				"dir2/file.txt": "",
				"dir3/file.py": "",
			},
			{".", "dir1", "dir3"},
		),
		# Special characters in paths
		(
			{
				"with spaces/file.py": "",
				"with-hyphen/file.py": "",
				"with_underscore/file.py": "",
			},
			{".", "with spaces", "with-hyphen", "with_underscore"},
		),
		# Unicode paths
		(
			{
				"目录/文件.py": "",
				"καταγραφή/αρχείο.py": "",
			},
			{".", "目录", "καταγραφή"},
		),
	],
)
def test_get_relevant_directories_parametrized(
	tmp_path, setup_fs_structure, fs_structure, expected_dirs
):
	setup_fs_structure(fs_structure)
	found_dirs = get_relevant_directories(root=str(tmp_path))
	assert found_dirs == expected_dirs


@pytest.mark.parametrize(
	"bad_input",
	[
		"non_existent_directory",
		"",
		"/definitely/not/a/real/path/anywhere",
		"   ",
		"\x00invalid",  # Null character
		"COM1" if os.name == "nt" else "dummy",  # Windows reserved name
	],
)
def test_invalid_roots(bad_input):
	with pytest.raises((FileNotFoundError, OSError)):
		get_python_files(root=bad_input)
	with pytest.raises((FileNotFoundError, OSError)):
		get_relevant_directories(root=bad_input)


def test_permission_denied(tmp_path):
	"""Test handling of permission denied errors"""
	if os.name != "nt":  # Skip on Windows
		restricted_dir = tmp_path / "restricted"
		restricted_dir.mkdir()
		(restricted_dir / "file.py").write_text("")

		# Remove read permissions
		os.chmod(restricted_dir, 0)

		try:
			with pytest.raises(PermissionError):
				get_python_files(str(restricted_dir))
			with pytest.raises(PermissionError):
				get_relevant_directories(str(restricted_dir))
		finally:
			# Restore permissions to allow cleanup
			os.chmod(restricted_dir, stat.S_IRWXU)


def test_symlink_handling(tmp_path):
	"""Test handling of symbolic links"""
	# Create a directory with a Python file
	src_dir = tmp_path / "source"
	src_dir.mkdir()
	(src_dir / "file.py").write_text("")

	# Create a symlink to the directory
	link_dir = tmp_path / "link"
	if os.name == "nt":  # Windows requires special permissions for symlinks
		try:
			os.symlink(str(src_dir), str(link_dir))
		except OSError:
			pytest.skip("Symlink creation requires admin privileges on Windows")
	else:
		os.symlink(str(src_dir), str(link_dir))

	# Test both functions with the symlink
	assert "file.py" in get_python_files(str(link_dir))
	assert "." in get_relevant_directories(str(link_dir))


def test_case_sensitivity(tmp_path):
	"""Test handling of case-sensitive vs case-insensitive file systems"""
	setup_structure = {
		"UPPERCASE.py": "",
		"lowercase.py": "",
		"MiXeDcAsE.py": "",
		"UPPER_DIR/file.py": "",
		"lower_dir/file.py": "",
	}

	for path, content in setup_structure.items():
		full_path = tmp_path / path
		full_path.parent.mkdir(parents=True, exist_ok=True)
		full_path.write_text(content)

	files = get_python_files(str(tmp_path))
	dirs = get_relevant_directories(str(tmp_path))

	# Just verify we can handle both cases without error
	assert len(files) > 0
	assert len(dirs) > 0
