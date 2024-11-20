from pathlib import Path
from itertools import product

import pytest

from dep_graph_viz import main

OUTPUT_DIR: Path = Path("examples")

TEST_PATHS: dict[str, str] = {
	"dep_graph_viz": "dep_graph_viz",
	".": "dep_graph_viz-tests",
}

TEST_MODULES: list[str] = [
	# "numpy",
	# "pytest",
	# "networkx",
	"muutils",
	# "fire",
	# "pdoc",
]

OUTPUT_FORMATS: list[str] = [
	"svg",
	"png",
	"html",
]

CONFIG_KEYS: list[str] = [
	"include_local_imports",
	"strip_module_prefix",
	"include_externals",
	"except_if_missing_edges",
	"strict_names",
]

CONFIGS: list[dict] = [
	dict(zip(CONFIG_KEYS, values)) 
	for values in product([True, False], repeat=len(CONFIG_KEYS))
]

OUTPUT_DIR.mkdir(exist_ok=True)

def id_func(val) -> str:

	if isinstance(val, tuple):
		# local path, use output path
		return val[1]
	elif isinstance(val, str):
		# module or format, return as is
		return val
	elif isinstance(val, dict):
		# config, use binary rep of key values
		return "".join([
			"1" if val[key] else "0"
			for key in CONFIG_KEYS
		])

@pytest.mark.parametrize(
	"paths, fmt, config",
	product(TEST_PATHS.items(), OUTPUT_FORMATS, CONFIGS),
	ids=id_func,
)
def test_generate_examples_local(paths: tuple[str, str], fmt: str, config: dict):
	root: str = paths[0]
	output: Path = OUTPUT_DIR / paths[1]
	output.mkdir(exist_ok=True)
	main(
		root=root,
		output=(output / id_func(config)).as_posix(),
		output_fmt=fmt,
		**config,
	)
	
@pytest.mark.parametrize(
	"module, fmt, config",
	product(TEST_MODULES, OUTPUT_FORMATS, CONFIGS),
	ids=id_func,
)
def test_generate_examples_modules(module: str, fmt: str, config: dict):
	output: Path = OUTPUT_DIR / module
	output.mkdir(exist_ok=True)
	main(
		module=module,
		output=(output / id_func(config)).as_posix(),
		output_fmt=fmt,
		**config,
	)