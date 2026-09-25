"""FITS headers, geometry checks, and the sky/mask arithmetic.

The fit itself always runs in the compiled backend.  The array helpers
here (:func:`subtract_sky`, :func:`apply_mask`) reproduce the backend's
REAL*4 preparation for inspection and plotting; the exact image the
backend fits can be saved with ``run_elliprof(..., prepared=...)``.
"""

import os
from typing import Dict, Tuple

import numpy as np

from .masks import _raw_header

# Keywords that define where an image's pixels sit: the image origin
# (CNPIX) and IRAF/DS9 physical-coordinate offsets (LTV/LTM).
_ORIGIN_KEYS = ("CNPIX1", "CNPIX2", "LTV1", "LTV2", "LTM1_1", "LTM2_2",
                "LTM1_2", "LTM2_1")


class GeometryError(ValueError):
    """A mask or sky image does not line up with the science image."""


def image_info(path: str) -> Tuple[Tuple[int, int], Dict[str, float]]:
    """``((ncol, nrow), origin keywords)`` of a FITS image or mask,
    read from its primary header (any BITPIX, including 1)."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"file not found: {path}")
    try:
        cards, _ = _raw_header(path)
    except ValueError as exc:
        raise ValueError(f"{path} is not a readable FITS file: {exc}") \
            from None
    try:
        naxis = int(float(cards.get("NAXIS", "0")))
        ncol = int(float(cards["NAXIS1"]))
        nrow = int(float(cards["NAXIS2"]))
        n3 = int(float(cards.get("NAXIS3", "1")))
    except (KeyError, ValueError):
        naxis, ncol, nrow, n3 = 0, 0, 0, 1
    if naxis < 2 or ncol <= 0 or nrow <= 0 or (naxis > 2 and n3 > 1):
        raise ValueError(f"{path} has no 2-D image in its primary HDU")
    origin = {}
    for key in _ORIGIN_KEYS:
        if key in cards:
            try:
                origin[key] = float(cards[key])
            except ValueError:
                pass
    return (ncol, nrow), origin


def check_same_geometry(image: str, other: str, what: str) -> None:
    """Require exactly the science image's dimensions (and origin: CNPIX,
    and LTV/LTM where both files define them).  Nothing is ever resized,
    cropped, padded, shifted or resampled."""
    (nx, ny), origin_a = image_info(image)
    (mx, my), origin_b = image_info(other)
    if (mx, my) != (nx, ny):
        raise GeometryError(
            f"{what} dimensions ({mx} x {my}) do not match science image "
            f"dimensions ({nx} x {ny})")
    for key in ("CNPIX1", "CNPIX2"):
        a, b = origin_a.get(key, 0.0), origin_b.get(key, 0.0)
        if a != b:
            raise GeometryError(f"{what} {key} = {b:g} does not match "
                                f"science image {key} = {a:g}")
    for key in _ORIGIN_KEYS[2:]:
        if key in origin_a and key in origin_b and \
                origin_a[key] != origin_b[key]:
            raise GeometryError(
                f"{what} {key} = {origin_b[key]:g} does not match science "
                f"image {key} = {origin_a[key]:g}")


def subtract_sky(data: np.ndarray, sky=None, sky_image=None) -> np.ndarray:
    """``data - sky`` in float32, as the backend does it."""
    out = np.asarray(data, dtype=np.float32)
    if sky is not None and sky_image is not None:
        raise ValueError("--sky and --sky-image cannot be used together")
    if sky is not None:
        return out + np.float32(-np.float32(sky))
    if sky_image is not None:
        sky_image = np.asarray(sky_image, dtype=np.float32)
        if sky_image.shape != out.shape:
            raise GeometryError(f"sky image shape {sky_image.shape} != "
                                f"image shape {out.shape}")
        return out - sky_image
    return out.copy()


def apply_mask(data: np.ndarray, mask: np.ndarray) -> np.ndarray:
    """``data * mask`` in float32: masked (0) pixels become 0."""
    data = np.asarray(data, dtype=np.float32)
    mask = np.asarray(mask, dtype=np.float32)
    if data.shape != mask.shape:
        raise GeometryError(f"mask shape {mask.shape} != image "
                            f"shape {data.shape}")
    return data * mask
