"""Find tkinter in the bundled build Python even when its Tcl runtime is external."""
from pathlib import Path
import sys


def pre_find_module_path(hook_api):
    python_root = Path(sys.prefix)
    hook_api.search_dirs = [str(python_root / "Lib")]
