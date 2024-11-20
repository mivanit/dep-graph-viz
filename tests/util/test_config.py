import pytest
from copy import deepcopy
import subprocess
from unittest.mock import patch

from dep_graph_viz.config import _DEFAULT_CONFIG, _process_config, NULL_STRINGS


def test_process_config_convert_none():
	CONFIG = deepcopy(_DEFAULT_CONFIG)
	CONFIG["edge"]["thing"] = {"color": "none", "style": "dashed"}
	CONFIG["node"]["otherthing"] = {"shape": "null", "label": "Node"}

	_process_config(config=CONFIG)

	assert CONFIG["edge"]["thing"]["style"] == "dashed"
	assert CONFIG["edge"]["thing"]["color"] is None
	assert CONFIG["node"]["otherthing"]["label"] == "Node"
	assert CONFIG["node"]["otherthing"]["shape"] is None


def test_process_config_no_auto_url_format():
	CONFIG = deepcopy(_DEFAULT_CONFIG)
	CONFIG["url_prefix"] = None
	CONFIG["auto_url_format"] = None

	_process_config(CONFIG)

	assert CONFIG["url_prefix"] is None


def test_process_config_root_none():
	CONFIG = deepcopy(_DEFAULT_CONFIG)
	CONFIG["url_prefix"] = None
	CONFIG["auto_url_format"] = "{git_remote_url}/blob/{git_branch}/"

	_process_config(CONFIG, root=None)

	assert CONFIG["url_prefix"] is None


def test_process_config_preserve_url_prefix():
	CONFIG = deepcopy(_DEFAULT_CONFIG)
	CONFIG["url_prefix"] = "https://example.com/repo/"

	_process_config(CONFIG)

	assert CONFIG["url_prefix"] == "https://example.com/repo/"


@pytest.mark.parametrize(
	"config_update, expected_changes",
	[
		# Edge configurations
		(
			{
				"edge": {
					"custom_edge": {"color": "none", "style": "solid", "weight": 1}
				},
				"node": {},
			},
			{
				"edge": {"custom_edge": {"color": None, "style": "solid", "weight": 1}},
				"node": {},
			},
		),
		(
			{
				"edge": {"test": {"color": "NULL", "style": "NONE", "width": "null"}},
				"node": {},
			},
			{
				"edge": {"test": {"color": None, "style": None, "width": None}},
				"node": {},
			},
		),
		(
			{
				"edge": {"mixed": {"color": "none", "style": "solid", "width": "NULL"}},
				"node": {},
			},
			{
				"edge": {"mixed": {"color": None, "style": "solid", "width": None}},
				"node": {},
			},
		),
		# Node configurations
		(
			{"node": {"custom_node": {"shape": "none", "color": "black"}}, "edge": {}},
			{"node": {"custom_node": {"shape": None, "color": "black"}}, "edge": {}},
		),
		(
			{
				"node": {"test": {"shape": "NULL", "color": "NONE", "size": "null"}},
				"edge": {},
			},
			{
				"node": {"test": {"shape": None, "color": None, "size": None}},
				"edge": {},
			},
		),
		# Mixed edge and node configurations
		(
			{"edge": {"e1": {"color": "none"}}, "node": {"n1": {"shape": "null"}}},
			{"edge": {"e1": {"color": None}}, "node": {"n1": {"shape": None}}},
		),
		# String value node/edge configurations
		(
			{"edge": {"direct_value": "none"}, "node": {}},
			{"edge": {"direct_value": None}, "node": {}},
		),
		(
			{"node": {"direct_value": "NULL"}, "edge": {}},
			{"node": {"direct_value": None}, "edge": {}},
		),
		# Case sensitivity tests
		(
			{
				"edge": {
					"case_test": {"color": "NoNe", "style": "NULL", "width": "nUlL"}
				},
				"node": {},
			},
			{
				"edge": {"case_test": {"color": None, "style": None, "width": None}},
				"node": {},
			},
		),
		# Empty configurations
		({"edge": {}, "node": {}}, {"edge": {}, "node": {}}),
		# Non-null values should remain unchanged
		(
			{
				"edge": {"keep": {"color": "red", "style": "none", "width": "2"}},
				"node": {"preserve": {"shape": "box", "color": "null"}},
			},
			{
				"edge": {"keep": {"color": "red", "style": None, "width": "2"}},
				"node": {"preserve": {"shape": "box", "color": None}},
			},
		),
	],
)
def test_process_config_null_conversion(config_update, expected_changes):
	"""Test conversion of null string values to None"""
	test_config = {"edge": {}, "node": {}, "url_prefix": None, "auto_url_format": None}
	test_config.update(deepcopy(config_update))
	_process_config(root=None, config=test_config)

	for section in ["edge", "node"]:
		assert test_config[section] == expected_changes[section]


@pytest.mark.parametrize(
	"url_prefix, auto_url_format, root, git_remote, git_branch, expected_url",
	[
		# Basic URL generation
		(
			None,
			"{git_remote_url}/blob/{git_branch}/",
			".",
			"https://github.com/user/repo.git",
			"main",
			"https://github.com/user/repo/blob/main/",
		),
		# Custom format
		(
			None,
			"https://custom.com/{git_branch}/{git_remote_url}/",
			".",
			"repo",
			"dev",
			"https://custom.com/dev/repo/",
		),
		# Preserve existing URL
		(
			"https://existing.com/",
			"{git_remote_url}/blob/{git_branch}/",
			".",
			"https://github.com/user/repo.git",
			"main",
			"https://existing.com/",
		),
		# No auto URL generation
		(None, None, ".", "https://github.com/user/repo.git", "main", None),
		# Root is None
		(
			None,
			"{git_remote_url}/blob/{git_branch}/",
			None,
			"https://github.com/user/repo.git",
			"main",
			None,
		),
	],
)
def test_process_config_url_generation(
	url_prefix, auto_url_format, root, git_remote, git_branch, expected_url
):
	"""Test URL generation with different configurations"""
	test_config = deepcopy(_DEFAULT_CONFIG)
	test_config["url_prefix"] = url_prefix
	test_config["auto_url_format"] = auto_url_format

	with patch("subprocess.check_output") as mock_subprocess:
		mock_subprocess.side_effect = [git_remote, git_branch]
		_process_config(root=root, config=test_config)

	assert test_config["url_prefix"] == expected_url


@pytest.mark.parametrize(
	"auto_url_replace, git_remote, expected_url",
	[
		(
			{".git": ""},
			"https://github.com/user/repo.git",
			"https://github.com/user/repo/blob/main/",
		),
		(
			{"gitlab.com": "gl.alternate.com"},
			"https://gitlab.com/user/repo",
			"https://gl.alternate.com/user/repo/blob/main/",
		),
		(
			{".git": "", "github.com": "gh.custom.com"},
			"https://github.com/user/repo.git",
			"https://gh.custom.com/user/repo/blob/main/",
		),
		(
			{},
			"https://github.com/user/repo.git",
			"https://github.com/user/repo.git/blob/main/",
		),
	],
)
def test_process_config_url_replacement(auto_url_replace, git_remote, expected_url):
	"""Test URL replacement patterns"""
	test_config = deepcopy(_DEFAULT_CONFIG)
	test_config["url_prefix"] = None
	test_config["auto_url_format"] = "{git_remote_url}/blob/{git_branch}/"
	test_config["auto_url_replace"] = auto_url_replace

	with patch("subprocess.check_output") as mock_subprocess:
		mock_subprocess.side_effect = [git_remote, "main"]
		_process_config(root=".", config=test_config)

	assert test_config["url_prefix"] == expected_url


def test_process_config_git_error_handling():
	"""Test handling of git command errors"""
	test_config = deepcopy(_DEFAULT_CONFIG)
	test_config["url_prefix"] = None
	test_config["auto_url_format"] = "{git_remote_url}/blob/{git_branch}/"

	with patch("subprocess.check_output") as mock_subprocess:
		mock_subprocess.side_effect = subprocess.CalledProcessError(1, "cmd")
		_process_config(root=".", config=test_config)

	assert test_config["url_prefix"] is None


@pytest.mark.parametrize(
	"cwd, root, expected_cwd_after",
	[
		("/original/path", ".", "/original/path"),
		("/original/path", "/other/path", "/original/path"),
		("/original/path", "../relative/path", "/original/path"),
	],
)
def test_process_config_directory_handling(cwd, root, expected_cwd_after):
	"""Test directory changes during git operations"""
	test_config = deepcopy(_DEFAULT_CONFIG)
	test_config["url_prefix"] = None
	test_config["auto_url_format"] = "{git_remote_url}/blob/{git_branch}/"

	with (
		patch("os.getcwd") as mock_getcwd,
		patch("os.chdir") as mock_chdir,
		patch("subprocess.check_output") as mock_subprocess,
	):
		mock_getcwd.return_value = cwd
		mock_subprocess.side_effect = ["https://github.com/user/repo.git", "main"]

		_process_config(root=root, config=test_config)

		# Verify we return to original directory
		mock_chdir.assert_called_with(expected_cwd_after)


@pytest.mark.parametrize("null_value", NULL_STRINGS)
def test_null_strings_consistency(null_value):
	"""Test that all null string values are properly recognized"""
	test_config = deepcopy(_DEFAULT_CONFIG)
	test_config["edge"]["test"] = {"color": null_value}
	test_config["node"]["test"] = {"shape": null_value}

	_process_config(root=None, config=test_config)

	assert test_config["edge"]["test"]["color"] is None
	assert test_config["node"]["test"]["shape"] is None


def test_config_immutability():
	"""Test that original config is not modified when using a custom config"""
	CONFIG = deepcopy(_DEFAULT_CONFIG)
	original_config = deepcopy(_DEFAULT_CONFIG)
	test_config = deepcopy(_DEFAULT_CONFIG)
	test_config["edge"]["custom"] = {"color": "none"}

	_process_config(root=None, config=test_config)

	assert CONFIG == original_config
	assert "custom" not in CONFIG["edge"]
