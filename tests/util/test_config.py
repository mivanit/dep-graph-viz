from copy import deepcopy
import pytest

# Import the functions to be tested
from dep_graph_viz.dep_graph_viz import (
	_process_config,
	CONFIG,
)


@pytest.fixture(autouse=True)
def reset_config():
	"""Reset the CONFIG dictionary to its default state before each test."""
	global CONFIG
	original_config = deepcopy(CONFIG)
	yield
	CONFIG = deepcopy(original_config)


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
