"""Constants and small helpers shared by the test suites."""

from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "u12517"
DATA = ROOT / "tests" / "data"


def write_fits(path, data, header=None, dtype=np.float32):
    """Write a 2-D image (rows, cols) as a primary-HDU FITS file."""
    from astropy.io import fits
    hdu = fits.PrimaryHDU(np.asarray(data, dtype=dtype))
    for key, value in (header or {}).items():
        hdu.header[key] = value
    hdu.writeto(path, overwrite=True)
    return Path(path)


def read_fits(path):
    from astropy.io import fits
    return fits.getdata(path)


def run_cli(*args, cwd=None, timeout=600):
    """Run ``python -m elliprof`` from this source tree as a separate
    process (the package need not be installed; the backend is the one
    the suite uses, see conftest.py)."""
    import os
    import subprocess
    import sys
    path = os.environ.get("PYTHONPATH")
    env = dict(os.environ, PYTHONPATH=str(ROOT / "python")
               + (os.pathsep + path if path else ""))
    return subprocess.run([sys.executable, "-m", "elliprof",
                           *map(str, args)], cwd=cwd, env=env,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=timeout)
