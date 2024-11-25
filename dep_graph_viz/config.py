import os
import subprocess
from copy import deepcopy
from typing import Any


_DEFAULT_CONFIG: dict = {
	# url stuff
	"url_prefix": None,
	"auto_url_format": "{git_remote_url}/tree/{git_branch}/",
	"auto_url_replace": {".git": ""},
	# graph configuration
	"graph": {
		"include_local_imports": True,
		"strip_module_prefix": True,
		"include_externals": False,
		"except_if_missing_edges": False,
		"strict_names": False,
	},
	# root node default name (only applies if `graph.strip_module_prefix` is True)
	"root_node_name": "ROOT",
	# passed to dot
	"dot_attrs": {
		# 'rankdir': 'TB',
		"rankdir": "LR",
	},
	# edge and node configurations
	"edge": {
		"module_hierarchy": {
			"color": "black",
			"penwidth": "3",
			"style": "solid",
		},
		"hierarchy": {
			"color": "black",
			"penwidth": "2",
			"style": "solid",
		},
		"uses": {
			"color": "red",
			"penwidth": "1",
			"style": "solid",
		},
		"inits": {
			"color": "blue",
			"penwidth": "1",
			"style": "dashed",
		},
		"external": {
			"color": "purple",
			"penwidth": "1",
			"style": "dotted",
		},
	},
	"node": {
		"module_root": {
			"shape": "folder",
			"color": "purple",
		},
		"root": {
			"shape": "folder",
			"color": "purple",
		},
		"module_dir": {
			"shape": "folder",
			"color": "black",
		},
		"dir": {
			"shape": "folder",
			"color": "blue",
		},
		"module_file": {
			"shape": "note",
			"color": "black",
		},
		"script": {
			"shape": "note",
			"color": "green",
		},
		"external": {
			"shape": "box3d",
			"color": "purple",
		},
	},
}

NULL_STRINGS: set[str] = {"none", "null"}


def _process_config(config: dict, root: str | None = ".") -> None:
	"""converts none types, auto-detects url_prefix from git if needed

	- mapping null values: in CONFIG, a value under the `CONFIG["edge"]` or `CONFIG["node"]` dicts that matches `NULL_STRINGS` will be converted to `None`
	- auto-generating url: if `CONFIG["url_prefix"]` is `None`, `CONFIG["auto_url_format"]` is not `None`, and `root` is not `None`, the git remote url and branch will be auto-detected and formatted into a URL

	# Parameters:
	 - `root : str`
	    place to look for git info. if `None`, will not try to auto-detect git info
	   (defaults to `"."`)

	# Returns:
	 - `None`

	# Modifies:
	global variable `CONFIG`, specifically:
	 - `CONFIG["edge"][*]` and `CONFIG["node"][*]` which match `NULL_STRINGS` will be converted to `None`
	 - `CONFIG["url_prefix"]` will be set to a formatted URL if it is `None` and `CONFIG["auto_url_format"]` is not `None`
	"""

	# convert none/null items
	for k_conv in ("edge", "node"):
		for key, value in config[k_conv].items():
			if isinstance(value, str):
				if value.lower() in NULL_STRINGS:
					config[k_conv][key] = None
			elif isinstance(value, dict):
				for sub_key, sub_value in value.items():
					if isinstance(sub_value, str) and sub_value.lower() in NULL_STRINGS:
						config[k_conv][key][sub_key] = None
						print(f"converted {k_conv}.{key}.{sub_key} to None")

	# get git url and branch
	if (
		(config["url_prefix"] is None)
		and (config["auto_url_format"] is not None)
		and (root is not None)
	):
		try:
			# navigate to root
			orig_dir: str = os.getcwd()
			os.chdir(root)
			# get git remote url
			git_remote_url: str = (
				subprocess.check_output(
					"git remote get-url origin",
					shell=True,
					encoding="utf-8",
				)
				.strip()
				.rstrip("/")
			)
			for rep_key, rep_val in config["auto_url_replace"].items():
				git_remote_url = git_remote_url.replace(rep_key, rep_val)
			# get branch
			git_branch: str = subprocess.check_output(
				"git rev-parse --abbrev-ref HEAD",
				shell=True,
				encoding="utf-8",
			).strip()
			config["url_prefix"] = config["auto_url_format"].format(
				git_remote_url=git_remote_url, git_branch=git_branch
			)
		except subprocess.CalledProcessError as e:
			print(f"could not get git info, not adding URLs: {e}")
			config["url_prefix"] = None
		finally:
			# go back to original directory
			os.chdir(orig_dir)
