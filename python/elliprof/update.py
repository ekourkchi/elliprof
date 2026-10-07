"""Checking for, and installing, a newer elliprof from PyPI.

    elliprof --check-update   say whether a newer version exists
    elliprof --update, -u     install it with this Python's pip

Only the standard library is used (urllib, json, subprocess), so this
works on every supported Python and never loads numpy, pandas or the
backend.  Nothing is installed except by an explicit --update.

After an interactive fit, :func:`start_notice` may also look up the
latest version in the background, at most once a day, and
:func:`finish_notice` prints one line if a newer one exists.  This is
silent when offline, never delays a fit, never runs when the output is
not a terminal (scripts, pipes, batch jobs), and is switched off by the
environment variable ``ELLIPROF_NO_UPDATE_CHECK=1``.
"""

import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Optional, Tuple

from ._version import __version__

PYPI_URL = "https://pypi.org/pypi/elliprof/json"
PROJECT = "elliprof"
NOTICE_INTERVAL = 24 * 3600     # seconds between background checks
NOTICE_TIMEOUT = 2.0            # seconds for the background request
CHECK_TIMEOUT = 10.0            # seconds for --check-update / --update
ENV_OFF = "ELLIPROF_NO_UPDATE_CHECK"


class UpdateError(Exception):
    pass


def parse_version(text: str) -> Optional[Tuple[int, ...]]:
    """A plain release version ('0.1.4') as a tuple; None for anything
    else (pre-releases, dev builds, '0+unknown'), which is never offered
    as an update."""
    if not re.fullmatch(r"\d+(\.\d+)*", str(text).strip()):
        return None
    parts = [int(p) for p in str(text).strip().split(".")]
    while len(parts) > 1 and parts[-1] == 0:
        parts.pop()
    return tuple(parts)


def is_newer(latest: str, current: str) -> bool:
    a, b = parse_version(latest), parse_version(current)
    return a is not None and b is not None and a > b


def latest_version(timeout: float = CHECK_TIMEOUT) -> str:
    """The newest elliprof release on PyPI."""
    from urllib.request import Request, urlopen
    req = Request(PYPI_URL, headers={
        "Accept": "application/json",
        "User-Agent": "elliprof/" + __version__})
    try:
        with urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        version = str(data["info"]["version"])
    except Exception as exc:
        raise UpdateError("could not reach PyPI to check for a new "
                          f"version ({type(exc).__name__}: {exc})") \
            from None
    if parse_version(version) is None:
        raise UpdateError(f"PyPI reported an unexpected version {version!r}")
    return version


def source_checkout() -> Optional[Path]:
    """The project root if this elliprof runs from a source checkout or
    an editable install (pip must not replace it), else None."""
    root = Path(__file__).resolve().parents[2]
    if (root / "src" / "original").is_dir() and (root / "VERSION").is_file():
        return root
    return None


def upgrade_command(version: str):
    return [sys.executable, "-m", "pip", "install", "--upgrade",
            f"{PROJECT}=={version}"]


def check_update(out=None) -> int:
    """--check-update: report; install nothing.  Exit status 0, or 1 if
    PyPI could not be reached."""
    out = out or sys.stdout
    try:
        latest = latest_version()
    except UpdateError as exc:
        print(f"elliprof: {exc}", file=sys.stderr)
        return 1
    print(f"Installed: elliprof {__version__}", file=out)
    print(f"Latest:    elliprof {latest} (PyPI)", file=out)
    if is_newer(latest, __version__):
        print("A newer version is available. Update with:\n"
              "    elliprof --update\n"
              "or\n"
              "    " + " ".join(_quote(a) for a in
                                upgrade_command(latest)), file=out)
    else:
        print("elliprof is up to date.", file=out)
    return 0


def update(out=None) -> int:
    """--update / -u: install the newest release with this Python's pip.
    Returns pip's exit status (0 when already up to date)."""
    out = out or sys.stdout
    root = source_checkout()
    if root is not None:
        print("elliprof: this elliprof runs from a source checkout or an "
              f"editable install ({root}); update it with git (for "
              "example `git pull`, then `python -m pip install -e .`), "
              "not --update.", file=sys.stderr)
        return 1
    try:
        latest = latest_version()
    except UpdateError as exc:
        print(f"elliprof: {exc}", file=sys.stderr)
        return 1
    if not is_newer(latest, __version__):
        print(f"elliprof {__version__} is up to date (latest on PyPI: "
              f"{latest}).", file=out)
        return 0
    cmd = upgrade_command(latest)
    print(f"Updating elliprof {__version__} -> {latest} for this Python "
          f"({sys.executable}):", file=out)
    print("    " + " ".join(_quote(a) for a in cmd), file=out)
    out.flush()
    try:
        code = subprocess.call(cmd)
    except OSError as exc:
        print(f"elliprof: could not run pip: {exc}", file=sys.stderr)
        return 1
    if code == 0:
        print(f"elliprof updated to {latest}.", file=out)
        _write_cache(latest)
    else:
        print("elliprof: pip could not update elliprof (exit status "
              f"{code}); see its messages above.  In a conda environment "
              "or an 'externally managed' system Python, update elliprof "
              "the way it was installed.", file=sys.stderr)
    return code


def _quote(arg: str) -> str:
    return f'"{arg}"' if (" " in arg or not arg) else arg


# ---- the once-a-day notice

def _cache_file() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home())
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Caches"
    else:
        base = Path(os.environ.get("XDG_CACHE_HOME")
                    or Path.home() / ".cache")
    return base / "elliprof" / "update_check.json"


def _read_cache() -> dict:
    try:
        return json.loads(_cache_file().read_text())
    except Exception:
        return {}


def _write_cache(latest: str) -> None:
    try:
        path = _cache_file()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"checked": time.time(),
                                    "latest": latest}))
    except Exception:
        pass


def notice_enabled() -> bool:
    if os.environ.get(ENV_OFF, "").strip() not in ("", "0"):
        return False
    try:
        return sys.stdout.isatty() and sys.stderr.isatty()
    except Exception:
        return False


class _Notice:
    def __init__(self):
        self.latest = None
        self.thread = None


def start_notice() -> Optional[_Notice]:
    """Begin the background check (or use today's cached answer).
    Returns None when the notice is disabled."""
    if not notice_enabled():
        return None
    note = _Notice()
    cache = _read_cache()
    fresh = time.time() - float(cache.get("checked", 0)) < NOTICE_INTERVAL
    if fresh:
        note.latest = cache.get("latest")
        return note

    def work():
        try:
            note.latest = latest_version(timeout=NOTICE_TIMEOUT)
        except Exception:
            note.latest = None
        _write_cache(note.latest or cache.get("latest") or "")

    note.thread = threading.Thread(target=work, daemon=True)
    note.thread.start()
    return note


def finish_notice(note: Optional[_Notice]) -> None:
    """Print one line if a newer version is known; never waits long."""
    if note is None:
        return
    if note.thread is not None:
        note.thread.join(timeout=0.2)
        if note.thread.is_alive():
            return
    if note.latest and is_newer(note.latest, __version__):
        print(f"elliprof {note.latest} is available (you have "
              f"{__version__}). Update with: elliprof --update",
              file=sys.stderr)
