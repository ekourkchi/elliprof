"""elliprof: fit elliptical isophotes to astronomical FITS images.

The fit is done by ELLIPROF, compiled unchanged from its original
Fortran source and run as a separate process; this package prepares
the inputs and reads the results.

>>> from elliprof import run_elliprof
>>> result = run_elliprof("galaxy.fits", x0=500, y0=500,
...                       r0=5, r1=200, nr=30)            # doctest: +SKIP
>>> result.profile                                        # doctest: +SKIP

The public names are imported on first use, so ``import elliprof`` (and
the ``elliprof`` command's --help/--version) never loads numpy or pandas.
"""

import importlib
import sys
import types

from ._version import __maintainer__, __email__, __version__

# public name -> submodule that defines it
_LAZY = {
    "run_elliprof": ".core", "ElliprofResult": ".core",
    "ElliprofError": ".core", "ElliprofTimeoutError": ".core",
    "find_backend": "._native", "BackendNotFoundError": "._native",
    "harmonic_settings": ".harmonics",
    "GeometryError": ".io", "apply_mask": ".io", "subtract_sky": ".io",
    "load_mask": ".masks", "write_bitmap_mask": ".masks",
    "COLUMNS": ".profile", "parse_elliprof_csv": ".profile",
    "read_prf": ".profile", "read_profile": ".profile",
    "read_ds9_regions": ".regions", "write_ds9_regions": ".regions",
}

__all__ = [
    "__version__", "__maintainer__", "__email__", "run_elliprof",
    "ElliprofResult", "ElliprofError", "ElliprofTimeoutError", "load_mask",
    "write_bitmap_mask", "subtract_sky", "apply_mask", "GeometryError",
    "read_prf", "read_profile", "parse_elliprof_csv", "COLUMNS",
    "write_ds9_regions", "read_ds9_regions", "find_backend",
    "BackendNotFoundError", "harmonic_settings",
]


class _LazyModule(types.ModuleType):
    # a module subclass rather than a module-level __getattr__, which
    # Python 3.6 does not support
    def __getattr__(self, name):
        where = _LAZY.get(name)
        if where is None:
            raise AttributeError(
                "module 'elliprof' has no attribute {!r}".format(name))
        value = getattr(importlib.import_module(where, __name__), name)
        setattr(self, name, value)
        return value

    def __dir__(self):
        return sorted(set(super().__dir__()) | set(__all__))


sys.modules[__name__].__class__ = _LazyModule
