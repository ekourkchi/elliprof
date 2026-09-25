"""Centre selection: every coordinate system is converted to ELLIPROF's
``X0``/``Y0`` here, before the native backend is called.

ELLIPROF image coordinates (the convention of ``X0=``/``Y0=``)
----------------------------------------------------------------
* x runs along columns (FITS axis 1), y along rows (axis 2);
* the centre of the pixel in FITS column ``i`` (1-based) is at
  ``x = i - 0.5``; the image covers ``0 <= x <= NCOL``.  This is the
  convention of ELLIPROF's contour sampler (``GETCONTOUR`` in
  elliprof.f: "Use X(Y) = IX(Y)-0.5 for exact center of pixel
  DATA(IX,IY)");
* ``X0``/``Y0`` are relative to the pixel array.  MONSTA's image origin
  (``CNPIX1``/``CNPIX2``) is *added* to the fitted ``x0``/``y0`` that
  ELLIPROF reports, but is not part of the input.

Conversions (all return array-relative ELLIPROF coordinates)
-------------------------------------------------------------
* FITS / DS9 *image* pixel ``(X, Y)`` (1-based, centres at integers):
  ``X0 = X - 0.5``.
* IRAF / DS9 *physical* coordinates, defined by ``LTV``/``LTM``:
  image = ``LTM * physical + LTV``, so ``X0 = LTM1_1*X + LTV1 - 0.5``.
* RA/DEC: astropy's ``WCS.world_to_pixel`` returns 0-based pixel
  coordinates (centre of the first pixel at 0), so ``X0 = x + 0.5``.
* geometric image centre: ``X0 = NCOL/2``, ``Y0 = NROW/2``.
"""

from __future__ import annotations

import math
import warnings
from dataclasses import dataclass
from typing import Any, Optional, Sequence, Tuple

SOURCE_IMAGE = "explicit image coordinates"
SOURCE_PHYSICAL = "physical coordinates"
SOURCE_RADEC = "RA/DEC"
SOURCE_AUTO = "image center"


class CenterError(ValueError):
    """The requested centre cannot be determined."""


@dataclass(frozen=True)
class Center:
    """A centre in ELLIPROF coordinates and where it came from."""
    x0: float
    y0: float
    source: str
    input: Optional[Tuple[Any, Any]] = None

    def describe(self) -> str:
        lines = [f"Center source: {self.source}"]
        if self.input is not None and self.source in (SOURCE_PHYSICAL,
                                                      SOURCE_RADEC):
            lines.append(f"Input: {self.input[0]} {self.input[1]}")
            lines.append(f"Converted center: X0={self.x0:.4f} "
                         f"Y0={self.y0:.4f}")
        else:
            lines.append(f"Center: X0={self.x0:.4f} Y0={self.y0:.4f}")
        return "\n".join(lines)


def _pair(value, name) -> Tuple[Any, Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence) \
            or len(value) != 2:
        raise CenterError(f"{name} must be a pair (x, y), got {value!r}")
    return value[0], value[1]


def _finite(value, name) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise CenterError(f"{name} must be a number, got {value!r}") from None
    if not math.isfinite(v):
        raise CenterError(f"{name} must be finite, got {value!r}")
    return v


def image_center(ncol: int, nrow: int) -> Tuple[float, float]:
    """Geometric centre of an ``ncol`` x ``nrow`` image, in ELLIPROF
    coordinates: ``(ncol/2, nrow/2)``."""
    return ncol / 2.0, nrow / 2.0


def physical_to_image(x: float, y: float, header) -> Tuple[float, float]:
    """IRAF/DS9 physical coordinates -> ELLIPROF ``X0``, ``Y0``.

    Uses ``LTV1/2`` (default 0) and ``LTM1_1``/``LTM2_2`` (default 1).
    Rotated or sheared LTM matrices are refused.
    """
    x = _finite(x, "physical x")
    y = _finite(y, "physical y")
    if header.get("LTM1_2", 0.0) or header.get("LTM2_1", 0.0):
        raise CenterError("physical coordinates with a rotated LTM matrix "
                          "(LTM1_2/LTM2_1 != 0) are not supported")
    ltm11 = float(header.get("LTM1_1", 1.0))
    ltm22 = float(header.get("LTM2_2", 1.0))
    if ltm11 == 0 or ltm22 == 0:
        raise CenterError("LTM1_1 / LTM2_2 must not be zero")
    xi = ltm11 * x + float(header.get("LTV1", 0.0))
    yi = ltm22 * y + float(header.get("LTV2", 0.0))
    return xi - 0.5, yi - 0.5


def parse_radec(ra, dec=None, frame="icrs"):
    """Build a SkyCoord from decimal degrees, sexagesimal strings
    (``"12:34:56.7"``/``"12h34m56.7s"`` for RA in hours, ``"-12:34:56"``
    for Dec in degrees), or an existing SkyCoord (returned unchanged).

    Plain numbers and strings are taken to be in ``frame``;
    :func:`radec_to_image` passes the image's own WCS frame (for example
    FK5 J2000 when the header has EQUINOX = 2000 and no RADESYS).
    """
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    if dec is None:
        if isinstance(ra, SkyCoord):
            return ra
        raise CenterError("center_radec needs (ra, dec) or a SkyCoord")
    try:
        return SkyCoord(float(ra), float(dec), unit=(u.deg, u.deg),
                        frame=frame)
    except (TypeError, ValueError):
        pass
    ra_s = str(ra).strip()
    ra_unit = u.hourangle if any(c in ra_s for c in ":hH ") else u.deg
    try:
        return SkyCoord(ra_s, str(dec).strip(), unit=(ra_unit, u.deg),
                        frame=frame)
    except Exception as exc:
        raise CenterError(f"cannot parse RA/DEC {ra!r} {dec!r}: {exc}") \
            from None


def radec_to_image(ra, dec, header) -> Tuple[float, float]:
    """RA/DEC -> ELLIPROF ``X0``, ``Y0`` using the image's FITS WCS
    (astropy).  Numbers and strings are read in the WCS's own celestial
    frame; a SkyCoord is transformed to it.  Fails if the header has no
    celestial WCS."""
    from astropy.wcs import FITSFixedWarning, WCS
    from astropy.wcs.utils import wcs_to_celestial_frame
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", FITSFixedWarning)
        try:
            wcs = WCS(header)
        except Exception as exc:
            raise CenterError(f"the image WCS cannot be read: {exc}") \
                from None
    if not wcs.has_celestial:
        raise CenterError("RA/DEC centre requested but the image has no "
                          "celestial WCS (CTYPE/CRVAL/CRPIX/CD keywords)")
    try:
        frame = wcs_to_celestial_frame(wcs)
    except ValueError:
        frame = "icrs"
    coord = parse_radec(ra, dec, frame=frame)
    x, y = wcs.celestial.world_to_pixel(coord)
    x, y = float(x), float(y)
    if not (math.isfinite(x) and math.isfinite(y)):
        raise CenterError("the RA/DEC position cannot be converted with "
                          "this WCS")
    return x + 0.5, y + 0.5


def resolve_center(header=None, center=None, center_physical=None,
                   center_radec=None) -> Center:
    """Pick the centre: explicit image coordinates, physical
    coordinates, RA/DEC, or else the geometric image centre.  Exactly one
    explicit mode may be given."""
    given = [name for name, value in (("center", center),
                                      ("center_physical", center_physical),
                                      ("center_radec", center_radec))
             if value is not None]
    if len(given) > 1:
        raise CenterError("give only one of " + ", ".join(given))
    if center is not None:
        x, y = _pair(center, "center")
        return Center(_finite(x, "X0"), _finite(y, "Y0"), SOURCE_IMAGE,
                      (x, y))
    if header is None:
        raise CenterError("the image header is needed to find the centre")
    if center_physical is not None:
        x, y = _pair(center_physical, "center_physical")
        return Center(*physical_to_image(x, y, header), SOURCE_PHYSICAL,
                      (x, y))
    if center_radec is not None:
        from astropy.coordinates import SkyCoord
        if isinstance(center_radec, SkyCoord):
            ra, dec = center_radec, None
            shown = (center_radec.frame.name, center_radec.to_string())
        else:
            ra, dec = _pair(center_radec, "center_radec")
            shown = (ra, dec)
        return Center(*radec_to_image(ra, dec, header), SOURCE_RADEC, shown)
    from .io import image_shape
    return Center(*image_center(*image_shape(header)), SOURCE_AUTO)
