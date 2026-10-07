"""--precision auto (the default): the backend is chosen from the data.

double when (A) the science or (B) the sky image is stored with BITPIX
64/-64, or (C) a finite value of either, after BSCALE/BZERO, would be
Inf in float32 or nonzero but 0 in float32, or (D) --sky / SKY= would.
Otherwise single -- also for float32 subnormals that stay nonzero,
values that merely are not exact in float32, and 32-bit integers above
2**24.  Masks never count."""

import numpy as np
import pytest

from helpers import DATA, EXAMPLE

fits = pytest.importorskip("astropy.io.fits")

GAL = DATA / "regression" / "rotated.fits"
FIT = ["X0=100.3", "Y0=99.6", "R0=3", "R1=80", "NR=25", "NITER=5"]


def write(path, data, dtype, **header):
    hdu = fits.PrimaryHDU(np.asarray(data).astype(dtype))
    hdu.writeto(path, overwrite=True)
    if header:
        # set scaling keywords without astropy rescaling the data
        with fits.open(path, mode="update",
                       do_not_scale_image_data=True) as h:
            for k, v in header.items():
                h[0].header[k] = v
    return path


def chosen(run_native, tmp_path, image, *extra):
    p = run_native(image, *extra, "--prepared", tmp_path / "p.fits",
                   "--prepare-only")
    assert p.returncode == 0, p.stderr
    line = next(l for l in p.stdout.splitlines() if "Precision:" in l)
    prec = "double" if "Precision: double" in line else "single"
    assert "requested auto (auto: " in line, line
    return prec, line


def gal():
    return fits.getdata(GAL).astype(np.float64)


def test_float32_science_is_single(run_native, tmp_path):
    prec, line = chosen(run_native, tmp_path,
                        write(tmp_path / "a.fits", gal(), np.float32))
    assert prec == "single" and "every value is within float32" in line


@pytest.mark.parametrize("dtype, bitpix", [(np.float64, -64),
                                           (np.int64, 64)])
def test_64_bit_science_is_double(run_native, tmp_path, dtype, bitpix):
    prec, line = chosen(run_native, tmp_path,
                        write(tmp_path / "a.fits", gal(), dtype))
    assert prec == "double"
    assert f"science image BITPIX {bitpix})" in line


def test_int32_above_2_24_stays_single(run_native, tmp_path):
    img = np.round(gal()).astype(np.int64) + 2 ** 30
    prec, _ = chosen(run_native, tmp_path,
                     write(tmp_path / "a.fits", img, np.int32))
    assert prec == "single"


def test_unsigned_16_bit_stays_single(run_native, tmp_path):
    img = np.round(gal()).astype(np.uint16)
    fits.PrimaryHDU(img).writeto(tmp_path / "u.fits")
    prec, _ = chosen(run_native, tmp_path, tmp_path / "u.fits")
    assert prec == "single"


@pytest.mark.parametrize("bscale, why", [
    (1e40, "value(s) beyond the float32 range"),
    (1e-50, "nonzero value(s) that are 0 in float32"),
])
def test_scaled_values_beyond_float32_are_double(run_native, tmp_path,
                                                 bscale, why):
    raw = np.round(gal()).clip(1, 30000)
    path = write(tmp_path / "s.fits", raw, np.int16, BSCALE=bscale)
    prec, line = chosen(run_native, tmp_path, path)
    assert prec == "double" and "science image has" in line and \
        why in line


def test_float32_subnormals_stay_single(run_native, tmp_path):
    """BSCALE 1e-40 on values 1..30000: float32 subnormals, but none
    becomes 0, so single (with its subnormal precision)."""
    raw = np.round(gal()).clip(1, 30000)
    path = write(tmp_path / "s.fits", raw, np.int16, BSCALE=1e-40)
    assert np.all(raw * 1e-40 > np.finfo(np.float32).smallest_subnormal)
    prec, _ = chosen(run_native, tmp_path, path)
    assert prec == "single"


def test_datamax_is_not_trusted(run_native, tmp_path):
    path = write(tmp_path / "a.fits", gal(), np.float32, DATAMAX=1e300,
                 DATAMIN=-1e300)
    assert chosen(run_native, tmp_path, path)[0] == "single"


def test_sky_image_decides_too(run_native, tmp_path):
    sci = write(tmp_path / "a.fits", gal(), np.float32)
    sky = write(tmp_path / "b.fits", np.zeros((200, 200)), np.float64)
    prec, line = chosen(run_native, tmp_path, sci, "--sky-image", sky)
    assert prec == "double" and "sky image BITPIX -64" in line
    sky = write(tmp_path / "c.fits", np.ones((200, 200)), np.int16,
                BSCALE=1e45)
    prec, line = chosen(run_native, tmp_path, sci, "--sky-image", sky)
    assert prec == "double" and "sky image has" in line
    sky = write(tmp_path / "d.fits", np.ones((200, 200)), np.float32)
    assert chosen(run_native, tmp_path, sci, "--sky-image", sky)[0] == \
        "single"


@pytest.mark.parametrize("sky, prec", [("1e39", "double"),
                                       ("-1e-46", "double"),
                                       ("2.5e-30", "single"),
                                       ("250", "single")])
def test_sky_value_decides_too(run_native, tmp_path, sky, prec):
    sci = write(tmp_path / "a.fits", gal(), np.float32)
    got, line = chosen(run_native, tmp_path, sci, "--sky", sky)
    assert got == prec
    if prec == "double":
        assert "--sky value is beyond float32" in line


@pytest.mark.parametrize("sky", ["1e-40", "3.4e38"])
def test_single_parser_limit_is_kept(run_native, tmp_path, sky):
    """Values float32 holds (so auto keeps single) but whose decimal
    exponent the original parser (DISSECT) refuses beyond +-38: an
    error, as in 0.1.4; --precision double reads them."""
    sci = write(tmp_path / "a.fits", gal(), np.float32)
    p = run_native(sci, "--sky", sky, "--prepared", tmp_path / "p.fits",
                   "--prepare-only")
    assert p.returncode == 1 and "--sky needs one finite number" in p.stderr
    p = run_native(sci, "--sky", sky, "--precision", "double",
                   "--prepared", tmp_path / "p.fits", "--prepare-only")
    assert p.returncode == 0, p.stderr


def test_sky_keyword_decides_too(run_native, tmp_path):
    sci = write(tmp_path / "a.fits", gal(), np.float32)
    got, line = chosen(run_native, tmp_path, sci, "SKY=1e45")
    assert got == "double" and "SKY= is beyond float32" in line


def test_mask_never_counts(run_native, tmp_path):
    sci = write(tmp_path / "a.fits", gal(), np.float32)
    mask = write(tmp_path / "m.fits", np.full((200, 200), 1e300),
                 np.float64)
    assert chosen(run_native, tmp_path, sci, "--mask", mask)[0] == "single"


def test_u12517_is_single_and_unchanged(run_native, tmp_path):
    p = run_native(EXAMPLE / "u12517j.fits", "--mask",
                   EXAMPLE / "u12517j.dmask", "--sky", "3246.0", "X0=567",
                   "Y0=562", "R0=9", "R1=347", "NR=23", "NITER=10",
                   "RMSTAR", "-o", tmp_path / "a.dat", "--csv",
                   tmp_path / "a.csv")
    assert p.returncode == 0, p.stderr
    import hashlib
    assert hashlib.sha256((tmp_path / "a.dat").read_bytes()).hexdigest() \
        .startswith("95d3310f926cd034")
    assert "# Precision: single (REAL*4, the original ELLIPROF); " \
        "requested auto (auto: every value is within float32)" in \
        (tmp_path / "a.csv").read_text()


def test_explicit_choices_are_reported(run_native, tmp_path):
    sci = write(tmp_path / "a.fits", gal(), np.float32)
    for prec in ("single", "double"):
        p = run_native(sci, "--precision", prec, *FIT, "--csv",
                       tmp_path / "a.csv")
        assert p.returncode == 0, p.stderr
        csv = (tmp_path / "a.csv").read_text()
        assert f"# Precision: {prec} (" in csv
        assert f"; requested {prec}\n" in csv


def test_gc_with_auto(run_native, tmp_path):
    gc = ["GC", "X0=100.3", "Y0=99.6", "NR=5", "-m", tmp_path / "m.fits"]
    sci = write(tmp_path / "a.fits", gal(), np.float32)
    p = run_native(sci, *gc)
    assert p.returncode == 0, p.stderr                  # single: GC runs
    sci = write(tmp_path / "b.fits", gal(), np.float64)
    p = run_native(sci, *gc)
    assert p.returncode == 1
    assert "double-precision GC mode is not yet supported (auto: " \
        "science image BITPIX -64)" in p.stderr
