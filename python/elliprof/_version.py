"""Package version, from the single VERSION file at the project root.

Installed packages get it from their metadata (scikit-build-core reads
VERSION at build time); a source checkout reads VERSION directly.
"""

from __future__ import annotations

from pathlib import Path


def _read_version() -> str:
    root = Path(__file__).resolve().parents[2]
    source = root / "VERSION"
    if source.is_file() and (root / "src" / "original").is_dir():
        return source.read_text().strip()
    try:
        from importlib.metadata import version
        return version("elliprof")
    except Exception:  # pragma: no cover - not installed, no VERSION
        return "0+unknown"


__version__ = _read_version()
__maintainer__ = "Ehsan Kourkchi (Edwin Kay)"
__email__ = "ekourkchi@gmail.com"
