"""DS9 region files for fitted isophotes.

ELLIPROF puts the centre of pixel ``DATA(ix,iy)`` at ``ix - 0.5`` and
adds the image origin CNPIX to the reported ``x0``/``y0``; DS9 image
coordinates put that pixel's centre at ``ix``.  So an isophote maps to

    ellipse(x0 - CNPIX1 + 0.5, y0 - CNPIX2 + 0.5, a, b, angle)

with ``a = Rmaj``, ``b = Rmaj * (1 - ellip)`` and ``angle = alpha - 90``.
The major axis actually lies at ``alpha + 90`` degrees from +x; the two
angles differ by 180 degrees, which describes the same ellipse.  I3/A3
and I4/A4 are harmonic terms and are not used for the ellipse.

The native backend writes the same file with ``--reg``.
"""

import math
import re
from typing import List, Sequence, Tuple

Ellipse = Tuple[float, float, float, float, float]


def profile_ellipses(profile, cnpix: Sequence[int] = (0, 0)) -> List[Ellipse]:
    """DS9 ``(x, y, a, b, angle)`` for each row of a profile DataFrame.
    Rows with NaN are skipped, as in the native writer."""
    out = []
    for row in profile.itertuples(index=False):
        e = (row.x0 - cnpix[0] + 0.5, row.y0 - cnpix[1] + 0.5, row.Rmaj,
             row.Rmaj * (1.0 - row.ellip), row.alpha - 90.0)
        if all(math.isfinite(v) for v in e):
            out.append(e)
    return out


def write_ds9_regions(profile, path: str, cnpix: Sequence[int] = (0, 0),
                      color: str = "green", width: int = 1) -> int:
    """Write one ellipse per contour, image coordinates, no labels.
    Returns the number of ellipses written."""
    ellipses = profile_ellipses(profile, cnpix)
    with open(path, "w") as f:
        f.write("# Region file format: DS9 version 4.1\n")
        f.write(f"global color={color} width={width}\n")
        f.write("image\n")
        for e in ellipses:
            f.write("ellipse({:.4f},{:.4f},{:.4f},{:.4f},{:.4f})\n".format(*e))
    return len(ellipses)


_ELLIPSE = re.compile(r"^ellipse\(([^)]*)\)")


def read_ds9_regions(path: str) -> List[Ellipse]:
    """Ellipses of a region file written by :func:`write_ds9_regions` or
    by the backend's ``--reg``."""
    out = []
    with open(path) as f:
        for line in f:
            m = _ELLIPSE.match(line.strip())
            if m:
                out.append(tuple(float(v) for v in m.group(1).split(",")))
    return out
