import re

MODULE_NAME_REGEX: re.Pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def normalize_path(path: str) -> str:
	"convert any path to a posix path"
	return path.replace("\\", "/")


def path_to_module(path: str) -> str:
	"convert a path to a python file to a module name"
	# First normalize the path
	norm_path: str = normalize_path(path).removesuffix(".py").removeprefix("/")

	# Check for dots in path components (not allowed)
	if "." in norm_path:
		raise ValueError(f"path contains '.', invalid: '{path}'")

	# Validate each path component
	components = norm_path.split("/")
	for component in components:
		# Check empty components
		if not component:
			raise ValueError(f"empty path component in: '{path}'")

		# Check for invalid characters in module names
		if not re.match(MODULE_NAME_REGEX, component):
			raise ValueError(
				f"invalid module name component: '{component}' in path: '{path}'"
			)

		# Check for control characters
		if any(ord(c) < 32 or ord(c) == 127 for c in component):
			raise ValueError(f"control character in module name: '{path}'")

		# Check length
		if len(component) > 255:
			raise ValueError(f"module name component too long: '{component}'")

		# Windows reserved names (case-insensitive)
		reserved_names = {
			"con",
			"prn",
			"aux",
			"nul",
			"com1",
			"com2",
			"com3",
			"com4",
			"com5",
			"com6",
			"com7",
			"com8",
			"com9",
			"lpt1",
			"lpt2",
			"lpt3",
			"lpt4",
			"lpt5",
			"lpt6",
			"lpt7",
			"lpt8",
			"lpt9",
		}
		if component.lower() in reserved_names:
			raise ValueError(f"invalid Windows reserved name: '{component}'")

		# Special names like .hidden files
		if component.startswith("."):
			raise ValueError(f"module name cannot start with dot: '{component}'")

		# Numeric start check
		if component[0].isdigit():
			raise ValueError(f"module name cannot start with number: '{component}'")

	return norm_path.replace("/", ".")
