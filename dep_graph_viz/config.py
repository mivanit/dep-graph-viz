_DEFAULT_CONFIG: dict = {
    "url_prefix": None,
    "auto_url_format": "{git_remote_url}/tree/{git_branch}/",
    "auto_url_replace": {".git": ""},
    "edge": {
        "module_hierarchy": {
            "color": "black",
            "penwidth": "3",
            "style": "solid",
        },
        "hierarchy": {
            "color": "black",
            "penwidth": "3",
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
    },
    "dot_attrs": {
        # 'rankdir': 'TB',
        "rankdir": "LR",
    },
}
