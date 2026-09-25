"""elliprof: fit elliptical isophotes to astronomical FITS images.

The fit is done by ELLIPROF, compiled unchanged from its original
Fortran source and run as a separate process; this package prepares
the inputs and reads the results.

>>> from elliprof import run_elliprof
>>> result = run_elliprof("galaxy.fits", x0=500, y0=500,
...                       r0=5, r1=200, nr=30)            # doctest: +SKIP
>>> result.profile                                        # doctest: +SKIP
"""

from ._native import BackendNotFoundError, find_backend
from ._version import __maintainer__, __email__, __version__
from .core import (ElliprofError, ElliprofResult, ElliprofTimeoutError,
                   run_elliprof)
from .io import GeometryError, apply_mask, subtract_sky
from .masks import load_mask, write_bitmap_mask
from .profile import COLUMNS, parse_elliprof_csv, read_prf, read_profile
from .regions import read_ds9_regions, write_ds9_regions

__all__ = [
    "__version__", "__maintainer__", "__email__", "run_elliprof",
    "ElliprofResult", "ElliprofError", "ElliprofTimeoutError", "load_mask",
    "write_bitmap_mask", "subtract_sky", "apply_mask", "GeometryError",
    "read_prf", "read_profile", "parse_elliprof_csv", "COLUMNS",
    "write_ds9_regions", "read_ds9_regions", "find_backend",
    "BackendNotFoundError",
]
