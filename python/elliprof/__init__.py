"""elliprof: elliptical-isophote surface photometry of galaxies.

A packaged, standalone version of the ELLIPROF command of MONSTA
(John Tonry's descendant of Lick VISTA and Mongo).  The fit runs in a
compiled Fortran backend built from the unchanged legacy sources; this
package prepares the inputs, picks the centre, and reads the results.

>>> from elliprof import run_elliprof
>>> result = run_elliprof("galaxy.fits", sky=1234.5, center=(500, 500),
...                       r0=5, r1=200, nr=40)          # doctest: +SKIP
>>> result.profile                                        # doctest: +SKIP
"""

from ._native import BackendNotFoundError, find_backend
from ._version import __version__
from .coordinates import (Center, CenterError, image_center,
                          physical_to_image, radec_to_image, resolve_center)
from .core import ElliprofError, ElliprofResult, run_elliprof
from .io import GeometryError, apply_mask, check_same_geometry, subtract_sky
from .masks import load_mask, write_bitmap_mask
from .profile import COLUMNS, parse_elliprof_csv, read_prf, read_profile
from .regions import read_ds9_regions, write_ds9_regions

__all__ = [
    "__version__", "run_elliprof", "ElliprofResult", "ElliprofError",
    "resolve_center", "Center", "CenterError", "image_center",
    "physical_to_image", "radec_to_image", "load_mask",
    "write_bitmap_mask", "subtract_sky", "apply_mask",
    "check_same_geometry", "GeometryError", "read_prf", "read_profile",
    "parse_elliprof_csv", "COLUMNS", "write_ds9_regions",
    "read_ds9_regions", "find_backend", "BackendNotFoundError",
]
