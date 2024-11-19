import pytest

# Import the functions to be tested
from dep_graph_viz.dep_graph_viz import get_imports


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
		(
			"""
import os  # This is a comment
from sys import path  # Another comment
""",
			["os", "sys"],
		),
		(
			"""
def func():
    import math
    from collections import deque
""",
			["math", "collections"],
		),
		(
			"""
from ..parent import parent_module
""",
			["parent"],
		),
		(
			"""
import package.module.submodule
""",
			["package.module.submodule"],
		),
		(
			"""
import numpy as np
import pandas as pd
""",
			["numpy", "pandas"],
		),
		(
			"""
from package import *
""",
			["package"],
		),
		(
			"""
try:
    import optional_module
except ImportError:
    optional_module = None
""",
			["optional_module"],
		),
		(
			"""
if CONDITION:
    import conditional_module
""",
			["conditional_module"],
		),
		(
			"""
import 你好
""",
			["你好"],
		),
		(
			"""
from __future__ import print_function
""",
			["__future__"],
		),
	],
)
def test_get_imports(source, expected):
	assert get_imports(source) == expected, f"{expected = }\nsource = '''\n{source}'''"


@pytest.mark.parametrize(
	"source, expected_exception",
	[
		("import", SyntaxError),
		("def func(:\n pass", SyntaxError),
		("import os as", SyntaxError),
		("from math import", SyntaxError),
		("import $invalid_module", SyntaxError),
		("def func():\n    import", SyntaxError),
		(
			"""
import os
def broken():
    return (
""",
			SyntaxError,
		),
		("from . import sibling_module", ValueError),
	],
)
def test_get_imports_error(source, expected_exception):
	with pytest.raises(expected_exception):
		get_imports(source)
