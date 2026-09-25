"""FITS helpers: headers, image geometry checks, sky and mask arithmetic.

The fit itself always runs in the native backend.  The array helpers
here (:func:`subtract_sky`, :func:`apply_mask`) reproduce the backend's
REAL*4 preprocessing for inspection and plotting; the backend's own
result can be obtained exactly with ``run_elliprof(..., prepared=...)``.
"""

from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

import numpy as np

from .masks import mask_info

# Keywords that define where an image's pixels sit.  CNPIX is MONSTA's
# image origin; LTV/LTM define IRAF/DS9 physical coordinates.
_GEOMETRY_DEFAULTS = {"CNPIX1": 0, "CNPIX2": 0, "LTV1": 0.0, "LTV2": 0.0,
                      "LTM1_1": 1.0, "LTM2_2": 1.0, "LTM1_2": 0.0,
                      "LTM2_1": 0.0}


class GeometryError(ValueError):
    """A mask or sky image does not line up with the science image."""


def read_header(path: str):
    """Primary header of a FITS image, which must hold a 2-D image."""
    from astropy.io import fits
    if not os.path.exists(path):
        raise FileNotFoundError(f"image not found: {path}")
    try:
        header = fits.getheader(path, 0)
    except OSError as exc:
        raise ValueError(f"{path} is not a readable FITS file: {exc}") from exc
    naxis = header.get("NAXIS", 0)
    if naxis < 2 or (naxis > 2 and header.get("NAXIS3", 1) > 1):
        raise ValueError(f"{path} has no 2-D image in its primary HDU "
                         f"(NAXIS = {naxis})")
    return header


def image_shape(header) -> Tuple[int, int]:
    """(ncol, nrow) of an image header."""
    return int(header["NAXIS1"]), int(header["NAXIS2"])


def _geometry_cards(path: str) -> Tuple[Tuple[int, int], Dict[str, float]]:
    """Size and origin keywords of an image or mask file (any BITPIX)."""
    info = mask_info(path)
    from .masks import _raw_header
    cards, _ = _raw_header(path)
    present = {}
    for key in _GEOMETRY_DEFAULTS:
        if key in cards:
            try:
                present[key] = float(cards[key])
            except ValueError:
                pass
    return (info["ncol"], info["nrow"]), present


def check_same_geometry(image: str, other: str, what: str) -> None:
    """Require the same size and origin (CNPIX, and LTV/LTM where both
    files define them).  MONSTA would silently use the overlap; this
    package refuses instead."""
    if not os.path.exists(other):
        raise FileNotFoundError(f"{what} not found: {other}")
    size_a, cards_a = _geometry_cards(image)
    size_b, cards_b = _geometry_cards(other)
    if size_a != size_b:
        raise GeometryError(
            f"{what} {other} is {size_b[0]} x {size_b[1]} pixels but the "
            f"image is {size_a[0]} x {size_a[1]}")
    for key in ("CNPIX1", "CNPIX2"):
        a = cards_a.get(key, 0.0)
        b = cards_b.get(key, 0.0)
        if a != b:
            raise GeometryError(
                f"{what} {other} has {key} = {b:g} but the image has {a:g}")
    for key in ("LTV1", "LTV2", "LTM1_1", "LTM2_2", "LTM1_2", "LTM2_1"):
        if key in cards_a and key in cards_b and cards_a[key] != cards_b[key]:
            raise GeometryError(
                f"{what} {other} has {key} = {cards_b[key]:g} but the image "
                f"has {cards_a[key]:g}")


def subtract_sky(data: np.ndarray, sky: Optional[float] = None,
                 sky_image: Optional[np.ndarray] = None) -> np.ndarray:
    """``data - sky`` in float32, as the backend (MONSTA SC / SI) does."""
    out = np.asarray(data, dtype=np.float32)
    if sky is not None and sky_image is not None:
        raise ValueError("give either sky or sky_image, not both")
    if sky is not None:
        return out + np.float32(-np.float32(sky))
    if sky_image is not None:
        return out - np.asarray(sky_image, dtype=np.float32)
    return out.copy()


def apply_mask(data: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """``data * mask`` in float32 (MONSTA MI): masked pixels become 0."""
    data = np.asarray(data, dtype=np.float32)
    mask = np.asarray(mask, dtype=np.float32)
    if data.shape != mask.shape:
        raise GeometryError(f"mask shape {mask.shape} != image {data.shape}")
    return data * mask
