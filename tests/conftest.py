"""Shared fixtures for the elliprof test suites.

The suites under tests/unit, tests/integration and tests/regression run
against the source tree: the Python package from python/ (see
pyproject.toml) and the native backend found by
``elliprof._native.find_backend`` (ELLIPROF_NATIVE, the installed
copy, or ./elliprof_native built by ``make``).
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

from helpers import DATA, ROOT, read_fits  # noqa: F401

# Test the backend that `make` just built in this checkout, not a copy
# installed earlier (e.g. by `pip install -e .`, which is not rebuilt
# automatically when the Fortran changes).
_DEV = ROOT / ("elliprof_native.exe" if os.name == "nt" else "elliprof_native")
if not os.environ.get("ELLIPROF_NATIVE") and _DEV.is_file():
    os.environ["ELLIPROF_NATIVE"] = str(_DEV)


@pytest.fixture(scope="session")
def native():
    """Path of the elliprof_native executable (skip if not built)."""
    from elliprof._native import BackendNotFoundError, find_backend
    try:
        return find_backend()
    except BackendNotFoundError as exc:
        pytest.skip(str(exc))


@pytest.fixture(scope="session")
def maskinfo():
    path = ROOT / "build" / ("maskinfo.exe" if os.name == "nt" else "maskinfo")
    if not path.is_file():
        pytest.skip("build/maskinfo not built (run `make tools`)")
    return path


@pytest.fixture
def run_native(native):
    """Run the backend; returns the CompletedProcess."""
    def run(*args, cwd=None, check=False):
        proc = subprocess.run([str(native), *map(str, args)], cwd=cwd,
                              capture_output=True, text=True, timeout=600)
        if check and proc.returncode != 0:
            raise AssertionError(
                f"elliprof_native failed ({proc.returncode}):\n"
                f"{proc.stdout}\n{proc.stderr}")
        return proc
    return run


@pytest.fixture
def prepare(run_native, tmp_path):
    """Run --prepare-only and return the prepared image (rows, cols)."""
    def prep(image, *args):
        out = tmp_path / "prepared.fits"
        proc = run_native(image, "--prepare-only", "--prepared", out, *args)
        if proc.returncode != 0:
            raise AssertionError(proc.stderr)
        return read_fits(out)
    return prep


@pytest.fixture(scope="session")
def galaxy_fits(tmp_path_factory):
    """The long-standing synthetic smoke-test galaxy (tests/data)."""
    path = DATA / "synthetic_galaxy.fits"
    if not path.is_file():
        pytest.skip("tests/data/synthetic_galaxy.fits missing")
    return path
