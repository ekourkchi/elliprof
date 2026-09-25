"""Environment report for bug reports (``elliprof --diagnostics``)."""

from __future__ import annotations

import platform
import subprocess
import sys
from typing import Dict

from ._native import BackendNotFoundError, backend_source, find_backend
from ._version import __version__


def diagnostics() -> Dict[str, str]:
    info = {
        "elliprof version": __version__,
        "Python": f"{platform.python_version()} ({sys.executable})",
        "OS": f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
    }
    try:
        exe = find_backend()
        info["native backend"] = f"{exe} [{backend_source()}]"
        proc = subprocess.run([str(exe), "--version"], capture_output=True,
                              text=True, timeout=30)
        info["backend version"] = (proc.stdout.strip() or
                                   f"failed: {proc.stderr.strip()}")
    except BackendNotFoundError as exc:
        info["native backend"] = f"not found ({exc})"
    except OSError as exc:
        info["backend version"] = f"cannot run backend: {exc}"
    for mod in ("numpy", "pandas", "astropy"):
        try:
            info[mod] = __import__(mod).__version__
        except Exception as exc:  # pragma: no cover
            info[mod] = f"unavailable ({exc})"
    return info


def format_diagnostics(info: Dict[str, str]) -> str:
    width = max(len(k) for k in info)
    return "\n".join(f"{k:<{width}} : {v}" for k, v in info.items())
