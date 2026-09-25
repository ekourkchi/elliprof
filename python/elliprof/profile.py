"""Reading ELLIPROF profiles (.prf and CSV).

Column meanings, as ELLIPROF stores them in ``PARAM_PRF(J,K)`` at the
end of the fit and as MONSTA's ``PRINT EPROF`` prints them (the comments
in the legacy ``profile.inc`` describe an older layout and are wrong):

====  =====  =============================================================
J     name   meaning
====  =====  =============================================================
1     Rmaj   semi-major axis a of the isophote [pixels]
2     x0     isophote centre x, ELLIPROF convention + CNPIX1 [pixels]
3     y0     isophote centre y, ELLIPROF convention + CNPIX2 [pixels]
4     I0     mean surface brightness on the isophote [image units]
5     alpha  position angle as MONSTA stores it [deg]; the major axis
             lies at ``alpha + 90`` degrees counter-clockwise from +x
6     ellip  ellipticity ``1 - b/a``
7     I3     cos/sin 3x amplitude relative to I0 (6x if COS3X < 0)
8     A3     phase of the 3x (6x) term [deg]
9     I4     cos/sin 4x amplitude relative to I0
10    A4     phase of the 4x term [deg]
11    slope  d log I / d log r
====  =====  =============================================================

Row 12 holds the 17 run flags (x0, y0, r0, r1, nr, niter, rlaw, ...),
not a contour.
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

import numpy as np
import pandas as pd

COLUMNS = ["Rmaj", "x0", "y0", "I0", "alpha", "ellip", "I3", "A3", "I4",
           "A4", "slope"]
FLAG_NAMES = ["x0", "y0", "r0", "r1", "nr", "niter", "rlaw", "fitlog",
              "fixctr", "terplaw", "rmstar", "old", "tie", "avg", "cos3x",
              "ellip", "gain"]
NPROFILE = 250  # PARAMETER NPROFILE in profile.inc


def read_prf(path: str) -> Dict[str, object]:
    """Read a MONSTA ``SAVE ELLIPROF=file ASCII`` profile.

    The file holds, list-directed: ``N_PRF, PRF_SC, PARAM_PRF(12,250)``
    (Fortran column order) and the FITS header text.  Returns ``n``,
    ``scale``, ``params`` (array (250, 12), row k = contour k+1) and
    ``header`` (the header text).
    """
    with open(path) as f:
        text = f.read()
    tokens = text.split(None, 2 + 12 * NPROFILE)
    need = 2 + 12 * NPROFILE
    if len(tokens) < need:
        raise ValueError(f"{path} is not an ELLIPROF .prf file "
                         f"({len(tokens)} values, need {need})")
    try:
        n = int(tokens[0])
        scale = float(tokens[1])
        # 9 significant digits identify a REAL*4 value exactly; round
        # through float32 so the result is the value ELLIPROF computed.
        values = np.array([float(t) for t in tokens[2:need]],
                          dtype=np.float32).astype(np.float64)
    except ValueError as exc:
        raise ValueError(f"{path} is not an ELLIPROF .prf file: {exc}") \
            from None
    if not 0 <= n <= NPROFILE:
        raise ValueError(f"{path}: invalid contour count {n}")
    header = tokens[need] if len(tokens) > need else ""
    return {"n": n, "scale": scale,
            "params": values.reshape(NPROFILE, 12),
            "header": header}


def read_profile(path: str) -> pd.DataFrame:
    """The fitted profile from a .prf file as a DataFrame with columns
    ``Rmaj, x0, y0, I0, alpha, ellip, I3, A3, I4, A4, slope`` (exact
    REAL*4 values).  ``df.attrs`` holds ``scale`` and the run ``flags``.
    """
    prf = read_prf(path)
    params = prf["params"]
    df = pd.DataFrame(params[:prf["n"], :11], columns=COLUMNS)
    df.attrs["scale"] = prf["scale"]
    df.attrs["flags"] = dict(zip(FLAG_NAMES, params[:17, 11].tolist()))
    return df


_META = re.compile(r"^#\s*([A-Za-z][A-Za-z ]*?):\s*(.*)$")


def parse_elliprof_csv(path: str) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """Read a ``--csv`` profile: returns (DataFrame, header metadata such
    as ``Input``, ``Mask``, ``Sky``, ``Center source``)."""
    meta: Dict[str, str] = {}
    with open(path) as f:
        for line in f:
            if not line.startswith("#"):
                break
            m = _META.match(line.strip())
            if m and m.group(1) not in ("Columns", "Units"):
                meta[m.group(1).strip()] = m.group(2).strip()
    df = pd.read_csv(path, comment="#", header=None, names=COLUMNS,
                     skipinitialspace=True)
    return df.astype(np.float64), meta
