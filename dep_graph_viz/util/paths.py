import importlib
import os
import re
import warnings
import importlib.metadata
import json

MODULE_NAME_REGEX: re.Pattern = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def normalize_path(path: str) -> str:
	"convert any path to a posix path"
	return path.replace("\\", "/")


def path_to_module(path: str, strict_names: bool = True) -> str:
	"convert a path to a python file to a module name"
	# First normalize the path
	norm_path: str = normalize_path(path).removesuffix(".py").removeprefix("/")

	if not norm_path:
		raise ValueError(f"empty path: '{path}'")

	# Check for dots in path components (not allowed)
	if "." in norm_path:
		# root path is a special case
		if norm_path == ".":
			return norm_path
		else:
			raise ValueError(f"path contains '.', invalid: '{path}'")

	try:
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
	except ValueError as e:
		if strict_names:
			raise ValueError(f"invalid path: '{path}'. If you think this is a mistake, set `graph.strict_names` to `False` in the config. see error:\n\t{e}") from e
		else:
			warnings.warn(f"invalid path: '{path}', continuing because `graph.strict_names` is set to `False` in the config. see error:\n\t{e}")

	return norm_path.replace("/", ".")



def get_module_directory(module_name: str) -> str:
    """Get the directory containing a module's source code.
    
    Args:
        module_name: Name of module as you would use in an import statement
        
    Returns:
        Absolute path to the directory containing the module
        
    Raises:
        ImportError: If module cannot be imported
        AttributeError: If module does not have a __file__ attribute
    """
    module = importlib.import_module(module_name)
    
    # Get the module's file path
    if not hasattr(module, '__file__'):
        raise AttributeError(f"Module {module_name} has no __file__ attribute")
        
    module_file = module.__file__
    
    # Get directory containing the module
    module_dir = os.path.dirname(os.path.abspath(module_file))
    
    return module_dir


def get_package_repository_url(package_name: str) -> str|None:
    """Get the repository URL for a Python package.
    
    Tries multiple methods:
    1. package metadata "project_urls" under Repository/Source/Code keys
    2. package metadata "home_page" 
    3. package metadata "download_url"
    
    Args:
        package_name: Name of the installed package
        
    Returns:
        Repository URL if found, None otherwise
    
    Raises:
        importlib.metadata.PackageNotFoundError: If package is not installed
    """
    metadata = importlib.metadata.metadata(package_name)
    
    # Check project_urls first
    if "project_urls" in metadata:
        urls = json.loads(metadata["project_urls"])
        repo_keys = ["Repository", "Source", "Code", "Source Code", "Homepage"]
        for key in repo_keys:
            if key in urls:
                return urls[key]
    
    # Try home_page
    if "home-page" in metadata:
        return metadata["home-page"]
            
    # Try download_url
    if "download-url" in metadata:
        return metadata["download-url"]
    
    return None