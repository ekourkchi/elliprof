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
