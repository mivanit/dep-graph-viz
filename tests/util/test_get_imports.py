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
		# Basic imports
		("import os", ["os"]),
		("import sys", ["sys"]),
		("from collections import defaultdict", ["collections"]),
		("from math import sqrt", ["math"]),
		# Multiple imports
		("import os, sys", ["os", "sys"]),
		("import os, sys, pathlib", ["os", "sys", "pathlib"]),
		("from collections import defaultdict, deque", ["collections"]),
		# Submodule imports
		("import module.submodule", ["module.submodule"]),
		("import package.module.submodule", ["package.module.submodule"]),
		("from package.module import submodule", ["package.module"]),
		# Import aliases
		("import numpy as np", ["numpy"]),
		(
			"import pandas as pd, matplotlib.pyplot as plt",
			["pandas", "matplotlib.pyplot"],
		),
		("from collections import defaultdict as dd", ["collections"]),
		# Multiple imports on multiple lines
		(
			"""
import os
import sys
from collections import defaultdict
from math import sqrt
        """,
			["os", "sys", "collections", "math"],
		),
		# Complex nested imports
		(
			"""
def func():
	import math
	class Inner:
		from collections import deque
		def method():
			import json
        """,
			["math", "collections", "json"],
		),
		# Conditional imports
		(
			"""
try:
	import optional_module
except ImportError:
	pass
        """,
			["optional_module"],
		),
		(
			"""
if CONDITION:
	import conditional_module
elif OTHER_CONDITION:
	from other_module import thing
        """,
			["conditional_module", "other_module"],
		),
		# Comments and docstrings
		(
			"""
# Comment with fake import
'''
This is a docstring with import os
'''
import real_module  # Real import
        """,
			["real_module"],
		),
		# Empty or whitespace
		("", []),
		("   ", []),
		("\n\n\n", []),
		# Special module names
		("import __main__", ["__main__"]),
		("from __future__ import print_function", ["__future__"]),
		("import _internal", ["_internal"]),
		("from _private import thing", ["_private"]),
		# Unicode module names
		("import 你好", ["你好"]),
		("from 模块 import 函数", ["模块"]),
		("import صالح", ["صالح"]),
		# Multiple dots in module paths
		("import very.deep.module.path", ["very.deep.module.path"]),
		("from very.deep.module.path import thing", ["very.deep.module.path"]),
		# Star imports
		("from module import *", ["module"]),
		("from package.subpackage import *", ["package.subpackage"]),
		# Mixed imports
		(
			"""
import os
from sys import path
import module.submodule as msm
from package.module import *
        """,
			["os", "sys", "module.submodule", "package.module"],
		),
		# Imports in different scopes
		(
			"""
import global_module
def func():
	import func_module
	class Class:
		import class_module
		def method():
			import method_module
        """,
			["global_module", "func_module", "class_module", "method_module"],
		),
		# Imports in complex structures
		(
			"""
try:
	try:
		import deep_try
	except:
		import deep_except
finally:
	import deep_finally
        """,
			["deep_finally", "deep_try", "deep_except"],
		),
		# Async function imports
		(
			"""
async def async_func():
	import asyncio
	import aiohttp
        """,
			["asyncio", "aiohttp"],
		),
		# Generator function imports
		(
			"""
def generator():
	import itertools
	yield
        """,
			["itertools"],
		),
		# Imports with type annotations
		(
			"""
from typing import List, Dict
import dataclasses
        """,
			["typing", "dataclasses"],
		),
		# Relative imports (parent/sibling)
		("from ..parent import thing", ["parent"]),
		("from ...grandparent import thing", ["grandparent"]),
		# Mixed relative and absolute imports
		(
			"""
from ..parent import thing
import os
from ...other import module
        """,
			["parent", "os", "other"],
		),
		# additional specialized
		(
			"import    os   ;    import    sys   ;   from    collections   import   defaultdict",
			["os", "sys", "collections"],
		),
		("import モジュール  # Japanese module", ["モジュール"]),
		(
			"\n".join(
				[f"import module_{i}" for i in range(5)]
			),  # Reduced from 1000 for practicality
			[f"module_{i}" for i in range(5)],
		),
		(
			"""
def level1():
    def level2():
        def level3():
            def level4():
                def level5():
                    import deep_module
""",
			["deep_module"],
		),
		(
			"""
import os  # Comment
# Comment
from sys import path  # Comment
# Comment
import json
""",
			["os", "sys", "json"],
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
		("from .... import thing", ValueError),
		# Basic syntax errors
		("import", SyntaxError),
		("from", SyntaxError),
		("from import", SyntaxError),
		("import as", SyntaxError),
		("from math import as", SyntaxError),
		# Invalid module names
		("import 123invalid", SyntaxError),
		("import $invalid", SyntaxError),
		("import @wrong", SyntaxError),
		("from 123wrong import thing", SyntaxError),
		# Incomplete statements
		("import os as", SyntaxError),
		("from math import ", SyntaxError),
		("from . import", SyntaxError),
		# Invalid syntax in different contexts
		(
			"""
        def func():
            import
        """,
			SyntaxError,
		),
		(
			"""
        class Class:
            from
        """,
			SyntaxError,
		),
		# Unclosed parentheses/brackets
		(
			"""
        import os
        def broken():
            return (
        """,
			SyntaxError,
		),
		# Invalid relative imports
		("from . import module", ValueError),  # Current directory relative import
		# Mixed invalid syntax
		(
			"""
        import valid_module
        import @invalid
        """,
			SyntaxError,
		),
		# Unicode invalid syntax
		("import 你好@invalid", SyntaxError),
		# Null bytes
		("import os\x00", SyntaxError),
		# Invalid combinations
		("from .. import ... import", SyntaxError),
		("import from from import", SyntaxError),
		# Malformed relative imports
		("from ............ import thing", ValueError),  # Too many dots
		# Invalid whitespace
		# ("import \x0c os", SyntaxError),  # Form feed character
		# ("import \x1f os", SyntaxError),  # Unit separator
		# Empty module names
		("import ''", SyntaxError),
		('import ""', SyntaxError),
		# Invalid characters in module paths
		("import module/submodule", SyntaxError),
		("import module\\submodule", SyntaxError),
		("from module:submodule import thing", SyntaxError),
		# Invalid combinations with comments
		("import os # comment \n from", SyntaxError),
	],
)
def test_get_imports_error(source, expected_exception):
	print(f"{expected_exception = }")
	print(f"source = '''\n{source}'''")
	with pytest.raises(expected_exception):
		get_imports(source)
