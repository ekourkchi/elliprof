"""Locate the compiled backend, ``elliprof_native``.

Search order:

1. the ``ELLIPROF_NATIVE`` environment variable (developers, custom
   builds);
2. the copy installed inside the package (``elliprof/_bin/``), which is
   where wheels and ``pip install`` put it;
3. a development build at the root of a source checkout
   (``make`` there produces ``elliprof_native``).

The package never looks in the current working directory.
"""

import os
import sys
from pathlib import Path
from typing import Optional

EXE_NAME = "elliprof_native.exe" if sys.platform == "win32" else "elliprof_native"


class BackendNotFoundError(RuntimeError):
    pass


def _packaged() -> Optional[Path]:
    try:
        from importlib.resources import files   # Python >= 3.9
    except ImportError:
        # Python < 3.9: wheels install _bin/ next to this file
        candidate = Path(__file__).parent / "_bin" / EXE_NAME
    else:
        try:
            candidate = files("elliprof") / "_bin" / EXE_NAME
        except (ModuleNotFoundError, TypeError):  # pragma: no cover
            return None
    path = Path(str(candidate))
    return path if path.is_file() else None


def _source_checkout() -> Optional[Path]:
    root = Path(__file__).resolve().parents[2]
    path = root / EXE_NAME
    if path.is_file() and (root / "src" / "original" / "elliprof.f").is_file():
        return path
    return None


def find_backend() -> Path:
    """Return the path of the ``elliprof_native`` executable."""
    override = os.environ.get("ELLIPROF_NATIVE")
    if override:
        path = Path(override)
        if not path.is_file():
            raise BackendNotFoundError(
                f"ELLIPROF_NATIVE={override} does not exist")
        return path
    for path in (_packaged(), _source_checkout()):
        if path is not None:
            return path
    raise BackendNotFoundError(
        "The compiled elliprof backend was not found.  Install a binary "
        "wheel (pip install elliprof), build from source with "
        "`pip install .`, or set ELLIPROF_NATIVE to an elliprof_native "
        "executable.")


def backend_source() -> str:
    """Where :func:`find_backend` found the backend (for diagnostics)."""
    if os.environ.get("ELLIPROF_NATIVE"):
        return "ELLIPROF_NATIVE"
    if _packaged() is not None:
        return "installed package"
    if _source_checkout() is not None:
        return "source checkout"
    return "not found"
