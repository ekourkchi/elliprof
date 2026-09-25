"""Reading ELLIPROF profiles (.prf and CSV).

Column meanings, as ELLIPROF stores them in ``PARAM_PRF(J,K)`` at the
end of the fit and as the original profile printout shows them (the comments
in the legacy ``profile.inc`` describe an older layout and are wrong):

====  =====  =============================================================
J     name   meaning
====  =====  =============================================================
1     Rmaj   semi-major axis a of the isophote [pixels]
2     x0     isophote centre x, ELLIPROF convention + CNPIX1 [pixels]
3     y0     isophote centre y, ELLIPROF convention + CNPIX2 [pixels]
4     I0     mean surface brightness on the isophote [image units]
5     alpha  position angle as ELLIPROF stores it [deg]; the major axis
             lies at ``alpha + 90`` degrees counter-clockwise from +x
6     ellip  ellipticity ``1 - b/a``
7     I3     amplitude of the 3rd-order intensity variation along the
             ellipse, as a fraction of I0 (``exp(amplitude) - 1`` of the
             log-intensity fit); 6th-order term if COS3X < 0
8     A3     its phase [deg, 0-120]: intensity varies as
             ``cos(3 * (theta - A3))``; with COS3X < 0 the column holds
             ``atan2(s6, c6) / 3``, i.e. twice the 6th-order phase
9     I4     the same for the 4th-order term
10    A4     its phase [deg, 0-90]: ``cos(4 * (theta - A4))``
11    slope  d ln I / d ln r between neighbouring isophotes (set to -2
             where it would be positive)
====  =====  =============================================================

``theta`` is the eccentric angle along the ellipse, measured from the
major axis (x = a cos theta, y = b sin theta in the ellipse frame).  The
3rd- and 4th-order terms are always fitted, together with orders 0-2, but
they never change the ellipse; see :mod:`elliprof.harmonics`.

Row 12 holds the 17 run flags (x0, y0, r0, r1, nr, niter, rlaw, ...),
not a contour.
"""

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
    """Read a ``.prf`` profile (``-o``), the original profile file format.

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
