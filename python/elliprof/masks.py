"""Mask files: 0 = masked (bad) pixel, 1 = good pixel.

The sky-subtracted image is multiplied by the mask, so masked pixels
become exactly 0, which ELLIPROF skips as missing data.

Besides ordinary FITS images, masks may use a legacy bitmap format:
FITS-like files with ``BITPIX = 1`` (for example ``*.dmask``), which
standard FITS readers (CFITSIO, astropy) reject.  The layout, from the
original reader and writer (routines ``bitfp_``, ``fpbit_`` and
``FITSorder``):

* the data start at the first 2880-byte block after the ``END`` card
  and are ``2*((npix+15)//16)`` bytes long, bits packed continuously
  across rows (no row padding);
* the bytes are swapped in pairs (the bitmap is a sequence of
  little-endian 16-bit words);
* after that swap, pixel ``i`` (0-based, row-major) is bit ``i % 8``,
  lowest bit first, of byte ``i // 8``; a set bit is 1.0 (good);
* in a final partial byte holding ``r`` pixels, the pixels sit in the
  top ``r`` bits: the writer shifts each new pixel in from the top, and
  the reader starts on that byte without shifting.

The native backend decodes these files with its own transcription of
``bitfp_`` (src/shim/maskio.f); the tests check that both agree.
"""

from __future__ import annotations

import os
from typing import Dict, Optional, Tuple

import numpy as np

FITS_BLOCK = 2880


def _raw_header(path: str) -> Tuple[Dict[str, str], int]:
    """Parse a primary FITS header without validating BITPIX.

    Returns the keyword values (raw strings) and the byte offset of the
    data.
    """
    cards: Dict[str, str] = {}
    with open(path, "rb") as f:
        first = f.read(80)
        if not first.startswith(b"SIMPLE  ="):
            raise ValueError(f"{path} is not a FITS file")
        n = 1
        while True:
            card = f.read(80)
            if len(card) < 80:
                raise ValueError(f"{path} has no END card")
            n += 1
            key = card[:8].decode("ascii", "replace").strip()
            if key == "END":
                break
            if card[8:10] == b"= ":
                value = card[10:].decode("ascii", "replace").split("/")[0]
                cards[key] = value.strip()
    return cards, ((n * 80 + FITS_BLOCK - 1) // FITS_BLOCK) * FITS_BLOCK


def _int_card(cards: Dict[str, str], key: str, default: Optional[int] = None) -> int:
    if key not in cards:
        if default is None:
            raise ValueError(f"missing {key} keyword")
        return default
    return int(float(cards[key]))


def bitmap_nbytes(npix: int) -> int:
    """Length of the data of a BITPIX = 1 image with ``npix`` pixels."""
    return 2 * ((npix + 15) // 16)


def decode_bitmap(data: bytes, npix: int) -> np.ndarray:
    """Decode legacy bitmap data to a flat float32 array of 0.0/1.0.

    ``data`` are the raw file bytes after the header.  This reproduces
    ``FITSorder(1, npix, data)`` (pair swap) followed by ``bitfp_``.
    """
    nbytes = bitmap_nbytes(npix)
    if len(data) < nbytes:
        raise ValueError(
            f"bitmap data too short: {len(data)} bytes, need {nbytes}")
    b = np.frombuffer(data[:nbytes], dtype=np.uint8).copy()
    b[0::2], b[1::2] = b[1::2].copy(), b[0::2].copy()
    bits = np.unpackbits(b, bitorder="little")[:npix].astype(np.float32)
    r = npix % 8
    if r:
        # bitfp_ starts on the last byte unshifted: pixel npix-1 reads
        # bit 7, npix-2 bit 6, ...
        last = int(b[(npix - 1) // 8])
        for k in range(r):
            bits[npix - r + k] = (last >> (8 - r + k)) & 1
    return bits


def encode_bitmap(values: np.ndarray) -> bytes:
    """Encode a flat array (nonzero = good) as legacy bitmap data.

    A transcription of ``fpbit_`` (shift each pixel in from the top of
    the current byte, move on after 8) and ``FITSorder`` (pair swap).
    Used to make test files and by :func:`write_bitmap_mask`.
    """
    flat = np.asarray(values).ravel()
    npix = flat.size
    out = bytearray(bitmap_nbytes(npix))
    dp = 0
    byte = 0
    for i, v in enumerate(flat):
        byte = (byte >> 1) | (0x80 if v != 0 else 0)
        if i % 8 == 7:
            out[dp] = byte
            dp += 1
            byte = 0
    if npix % 8:
        out[dp] = byte
    out[0::2], out[1::2] = out[1::2], out[0::2]
    return bytes(out)


def _card(key: str, value: str, comment: str = "") -> bytes:
    text = f"{key:<8}= {value:>20}"
    if comment:
        text += f" / {comment}"
    return text[:80].ljust(80).encode("ascii")


def write_bitmap_mask(path: str, mask: np.ndarray,
                      cnpix: Optional[Tuple[int, int]] = None) -> None:
    """Write a 2-D mask (rows, cols) in the legacy BITPIX = 1 format."""
    mask = np.asarray(mask)
    if mask.ndim != 2:
        raise ValueError("mask must be 2-D")
    nrow, ncol = mask.shape
    cards = [_card("SIMPLE", "T"), _card("BITPIX", "1"),
             _card("NAXIS", "2"), _card("NAXIS1", str(ncol)),
             _card("NAXIS2", str(nrow))]
    if cnpix is not None:
        cards += [_card("CNPIX1", str(cnpix[0])),
                  _card("CNPIX2", str(cnpix[1]))]
    cards.append(b"END".ljust(80))
    header = b"".join(cards)
    header += b" " * (-len(header) % FITS_BLOCK)
    data = encode_bitmap(mask)
    data += b"\0" * (-len(data) % FITS_BLOCK)
    with open(path, "wb") as f:
        f.write(header + data)


def mask_info(path: str) -> Dict[str, int]:
    """BITPIX, size and origin of a mask, from its primary header."""
    cards, offset = _raw_header(path)
    naxis = _int_card(cards, "NAXIS")
    if naxis < 2 or (naxis > 2 and _int_card(cards, "NAXIS3", 1) > 1):
        raise ValueError(f"{path} is not a single 2-D image")
    return {"bitpix": _int_card(cards, "BITPIX"),
            "ncol": _int_card(cards, "NAXIS1"),
            "nrow": _int_card(cards, "NAXIS2"),
            "cnpix1": _int_card(cards, "CNPIX1", 0),
            "cnpix2": _int_card(cards, "CNPIX2", 0),
            "offset": offset}


def load_mask(path: str) -> np.ndarray:
    """Read a mask as float32 (rows, cols), as the backend sees it.

    BITPIX = 1 bitmaps are decoded here.  Other masks are read with
    astropy (install it for this helper) and keep their values, which
    multiply the image.
    """
    if not os.path.exists(path):
        raise FileNotFoundError(path)
    info = mask_info(path)
    if info["bitpix"] == 1:
        npix = info["ncol"] * info["nrow"]
        with open(path, "rb") as f:
            f.seek(info["offset"])
            data = f.read(bitmap_nbytes(npix))
        return decode_bitmap(data, npix).reshape(info["nrow"], info["ncol"])
    try:
        from astropy.io import fits
    except ImportError:  # pragma: no cover
        raise ImportError("reading a standard FITS mask in Python needs "
                          "astropy (pip install astropy); the elliprof "
                          "command itself does not") from None
    return np.asarray(fits.getdata(path), dtype=np.float32)
