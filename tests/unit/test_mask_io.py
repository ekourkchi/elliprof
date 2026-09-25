"""Legacy BITPIX = 1 mask decoding (Python and native) and mask checks.

The reference for every pattern is the array itself: it is written with
a transcription of the original *writer* (fpbit_), then decoded by the
Python transcription of the *reader* (bitfp_) and by the native decoder
(src/shim/maskio.f, seen through --prepare-only on an image of ones).
Hand-computed byte sequences pin down the byte-pair swap, the low-bit-
first order and the final-partial-byte rule independently of both.
"""

import os

import numpy as np
import pytest

from helpers import EXAMPLE, read_fits, write_fits
from elliprof.masks import (bitmap_nbytes, decode_bitmap, encode_bitmap,
                            load_mask, mask_info, write_bitmap_mask)

RNG = np.random.default_rng(12345)


def patterns():
    yield "all_good", np.ones((7, 16))
    yield "all_bad", np.zeros((7, 16))
    yield "alternating", (np.arange(8 * 16) % 2).reshape(8, 16)
    yield "checkerboard", np.indices((9, 10)).sum(axis=0) % 2
    yield "odd_width", RNG.integers(0, 2, (5, 13))
    yield "width_1", RNG.integers(0, 2, (11, 1))
    # rows not multiples of 8 pixels, npix % 16 != 0 (odd byte count)
    yield "non_byte_aligned", RNG.integers(0, 2, (3, 7))
    # npix % 8 = 1..7: the final partial byte, set bits at the very end
    for r in range(1, 8):
        m = RNG.integers(0, 2, (1, 8 * 3 + r))
        m[0, -r:] = 1
        yield f"partial_byte_{r}", m
    yield "random_large", RNG.integers(0, 2, (37, 53))


PATTERNS = list(patterns())


@pytest.mark.parametrize("name,mask", PATTERNS, ids=[p[0] for p in PATTERNS])
def test_python_roundtrip(name, mask):
    data = encode_bitmap(mask)
    assert len(data) == bitmap_nbytes(mask.size)
    np.testing.assert_array_equal(decode_bitmap(data, mask.size),
                                  mask.ravel().astype(np.float32))


@pytest.mark.native
@pytest.mark.parametrize("name,mask", PATTERNS, ids=[p[0] for p in PATTERNS])
def test_native_decoder_matches(name, mask, tmp_path, prepare):
    mfile = tmp_path / "m.dmask"
    write_bitmap_mask(mfile, mask)
    ones = write_fits(tmp_path / "ones.fits", np.ones(mask.shape))
    got = prepare(ones, "--mask", mfile)
    np.testing.assert_array_equal(got, mask.astype(np.float32))
    np.testing.assert_array_equal(load_mask(str(mfile)), mask)


# --- explicit bytes -------------------------------------------------------

def test_low_bit_first_and_pair_swap():
    # 16 pixels: only pixel 0 set.  After the pair swap pixel 0 is bit 0
    # of byte 0, so in the file it is bit 0 of byte 1.
    assert decode_bitmap(bytes([0x00, 0x01]), 16).tolist() == [1] + [0] * 15
    # pixel 9 set -> bit 1 of (swapped) byte 1 -> bit 1 of file byte 0
    expect = [0] * 16
    expect[9] = 1
    assert decode_bitmap(bytes([0x02, 0x00]), 16).tolist() == expect


def test_bits_run_continuously_across_rows():
    # 3 x 5 image: pixel 5 (row 1, col 0) is bit 5 of byte 0, not the
    # start of a new byte
    m = np.zeros((3, 5))
    m[1, 0] = 1
    assert encode_bitmap(m) == bytes([0x00, 0x20])


def test_final_partial_byte_is_top_aligned():
    # 3 pixels, all set: fpbit_ shifts them in from the top, so the
    # byte is 0b11100000, and bitfp_ reads them back from the top.
    assert encode_bitmap(np.ones(3)) == bytes([0x00, 0xE0])
    assert decode_bitmap(bytes([0x00, 0xE0]), 3).tolist() == [1, 1, 1]
    # 11 pixels: first 8 in a full byte, last 3 top-aligned in byte 1
    assert encode_bitmap(np.ones(11)) == bytes([0xE0, 0xFF])
    # reading bits 0..2 of that byte instead would give zeros here:
    assert decode_bitmap(bytes([0x80, 0x00]), 11).tolist() == [0] * 10 + [1]


# --- the real example mask -------------------------------------------------

DMASK = EXAMPLE / "u12517j.dmask"


@pytest.mark.skipif(not DMASK.is_file(), reason="example data missing")
def test_u12517_mask_statistics():
    info = mask_info(str(DMASK))
    assert (info["bitpix"], info["ncol"], info["nrow"]) == (1, 1025, 1022)
    assert (info["cnpix1"], info["cnpix2"]) == (0, 0)
    m = load_mask(str(DMASK))
    assert m.shape == (1022, 1025)
    assert set(np.unique(m)) == {0.0, 1.0}
    assert int((m == 0).sum()) == 103402
    assert int((m == 1).sum()) == 944148
    # the nucleus of UGC 12517 is masked: pixel (col 567, row 562)
    assert m[562 - 1, 567 - 1] == 0
    assert int((m[541:582, 546:587] == 0).sum()) == 301


@pytest.mark.native
@pytest.mark.skipif(not DMASK.is_file(), reason="example data missing")
def test_u12517_native_matches_python(tmp_path, prepare):
    ones = write_fits(tmp_path / "ones.fits", np.ones((1022, 1025)))
    got = prepare(ones, "--mask", DMASK)
    np.testing.assert_array_equal(got, load_mask(str(DMASK)))


@pytest.mark.native
def test_maskinfo_tool(maskinfo, tmp_path):
    import subprocess
    m = np.zeros((4, 9))
    m[1, 2] = 1
    write_bitmap_mask(tmp_path / "m.dmask", m)
    out = subprocess.run([str(maskinfo), str(tmp_path / "m.dmask")],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         universal_newlines=True, check=True).stdout
    assert "value 0 (masked): 35" in out
    assert "value 1 (good):   1" in out


# --- files the original software wrote (optional, outside the repo) ------

SBF = os.environ.get("ELLIPROF_SBF_DIR")


@pytest.mark.skipif(not SBF, reason="set ELLIPROF_SBF_DIR to the "
                    "u12517 pipeline output folder to run")
def test_against_masks_written_by_original_software():
    """mask.000 = common.mask * dmask and mask.002 (bitmap) were written
    by the original software in an earlier analysis."""
    from astropy.io import fits
    d = SBF
    common = load_mask(os.path.join(d, "common.mask"))
    dmask = load_mask(os.path.join(d, "u12517j.dmask"))
    np.testing.assert_array_equal(
        common * dmask, fits.getdata(os.path.join(d, "mask.000")))
    obj = fits.getdata(os.path.join(d, "objCheck.000")).astype(np.float32)
    np.testing.assert_array_equal(
        load_mask(os.path.join(d, "mask.002")) == 1, obj * common != 0)


# --- standard FITS masks and invalid files ---------------------------------

@pytest.mark.native
@pytest.mark.parametrize("dtype", [np.uint8, np.int16, np.float32])
def test_standard_fits_mask(dtype, tmp_path, prepare):
    m = (np.indices((6, 7)).sum(axis=0) % 3 != 0)
    write_fits(tmp_path / "m.fits", m, dtype=dtype)
    img = write_fits(tmp_path / "img.fits", np.full((6, 7), 5.0))
    got = prepare(img, "--mask", tmp_path / "m.fits")
    np.testing.assert_array_equal(got, 5.0 * m)


@pytest.mark.native
def test_non_binary_mask_values_multiply(tmp_path, run_native):
    write_fits(tmp_path / "m.fits", np.full((4, 4), 0.5))
    img = write_fits(tmp_path / "img.fits", np.full((4, 4), 8.0))
    out = tmp_path / "p.fits"
    proc = run_native(img, "--prepare-only", "--prepared", out,
                      "--mask", tmp_path / "m.fits")
    assert proc.returncode == 0
    assert "neither 0 nor 1" in proc.stderr
    np.testing.assert_array_equal(read_fits(out), 4.0)


@pytest.mark.native
@pytest.mark.parametrize("kind", ["truncated", "no_end", "not_fits",
                                  "missing"])
def test_invalid_mask_fails_clearly(kind, tmp_path, run_native):
    img = write_fits(tmp_path / "img.fits", np.ones((10, 10)))
    mfile = tmp_path / "bad.dmask"
    if kind != "missing":
        write_bitmap_mask(mfile, np.ones((10, 10)))
        raw = mfile.read_bytes()
        if kind == "truncated":
            mfile.write_bytes(raw[:2880 + 4])
        elif kind == "no_end":
            mfile.write_bytes(raw[:400])
        else:
            mfile.write_bytes(b"not a fits file" + raw[15:])
    proc = run_native(img, "--prepare-only", "--prepared",
                      tmp_path / "p.fits", "--mask", mfile)
    assert proc.returncode != 0
    assert "mask" in proc.stderr
    with pytest.raises((ValueError, FileNotFoundError)):
        load_mask(str(mfile))


@pytest.mark.native
@pytest.mark.parametrize("shape,cnpix,message", [
    ((10, 11), None, "mask dimensions (11 x 10) do not match science "
                     "image dimensions (10 x 10)"),
    ((10, 10), (5, 0), "mask origin (CNPIX1,CNPIX2) = (5,0)"),
])
def test_mask_registration(shape, cnpix, message, tmp_path, run_native):
    img = write_fits(tmp_path / "img.fits", np.ones((10, 10)))
    write_bitmap_mask(tmp_path / "m.dmask", np.ones(shape), cnpix=cnpix)
    proc = run_native(img, "--prepare-only", "--prepared",
                      tmp_path / "p.fits", "--mask", tmp_path / "m.dmask")
    assert proc.returncode == 1
    assert message in proc.stderr
