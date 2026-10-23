"""Collect the Tcl/Tk binaries and scripts missing from the build Python package."""
from pathlib import Path
import sys


PYTHON_ROOT = Path(sys.prefix)
TCL_ROOT = Path.cwd() / "build" / "tcl-runtime"


def hook(hook_api):
    dlls = PYTHON_ROOT / "DLLs"
    binaries = [
        (str(dlls / "_tkinter.pyd"), "."),
        (str(dlls / "tcl86t.dll"), "."),
        (str(dlls / "tk86t.dll"), "."),
    ]
    missing = [source for source, _ in binaries if not Path(source).is_file()]
    if missing:
        raise FileNotFoundError("Missing bundled Tcl/Tk binaries: " + ", ".join(missing))
    hook_api.add_binaries(binaries)

    data = []
    for dirname in ("_tcl_data", "_tk_data"):
        source_root = TCL_ROOT / dirname
        if not source_root.is_dir():
            raise FileNotFoundError(f"Missing Tcl/Tk scripts: {source_root}")
        for source in source_root.rglob("*"):
            if source.is_file():
                destination = str(Path(dirname) / source.relative_to(source_root).parent)
                data.append((str(source), destination))
    if not data:
        raise RuntimeError("Tcl/Tk script collection unexpectedly produced no files")
    hook_api.add_datas(data)
