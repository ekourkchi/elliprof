"""Precision in the Python API and command line: run_elliprof(precision=),
the result's precision fields, double profiles read without float32
rounding, and the float64 preparation helpers."""

import numpy as np
import pytest

from elliprof import read_prf, run_elliprof
from elliprof.io import apply_mask, subtract_sky
from elliprof.profile import parse_elliprof_csv, read_profile
from helpers import DATA, EXAMPLE, run_cli

fits = pytest.importorskip("astropy.io.fits")

GAL = DATA / "regression" / "rotated.fits"
KW = dict(r0=3, r1=80, nr=25, niter=5)


def fit(image, tmp_path, **kw):
    return run_elliprof(image, 100.3, 99.6, output_dir=tmp_path, **KW,
                        **kw)


def test_default_is_auto_and_single_for_float32(tmp_path):
    r = fit(GAL, tmp_path)
    assert r.precision == "single" and r.precision_requested == "auto"
    assert r.precision_reason == "every value is within float32"
    assert r.normalization_exponent is None
    assert r.profile.attrs["precision"] == "single"
    assert "--precision" in r.command and "auto" in r.command


def test_double_result_and_profile(tmp_path):
    r = fit(GAL, tmp_path, precision="double")
    assert r.precision == "double" and r.precision_requested == "double"
    assert r.precision_reason is None
    assert isinstance(r.normalization_exponent, int)
    p = r.profile
    assert p.attrs["precision"] == "double"
    assert p.attrs["normalization_exponent"] == r.normalization_exponent
    # genuine float64: not every value is a float32
    v = p[["x0", "y0", "I0", "ellip"]].to_numpy()
    assert not np.array_equal(v, v.astype(np.float32).astype(np.float64))
    # the CSV holds exactly the same numbers, and says how it was made
    df, meta = parse_elliprof_csv(str(r.csv_path))
    assert np.array_equal(df.to_numpy(), p.to_numpy(), equal_nan=True)
    assert meta["Precision"].startswith("double (IEEE-754 binary64)")
    assert meta["Normalization"].startswith(
        f"k={r.normalization_exponent} ")


def test_float64_image_goes_double_by_default(tmp_path):
    fits.PrimaryHDU(fits.getdata(GAL).astype(np.float64)).writeto(
        tmp_path / "g.fits")
    r = fit(tmp_path / "g.fits", tmp_path)
    assert r.precision == "double"
    assert r.precision_reason == "science image BITPIX -64"
    r = fit(tmp_path / "g.fits", tmp_path, precision="single")
    assert r.precision == "single"


def test_full_range_through_the_api(tmp_path):
    data = fits.getdata(GAL).astype(np.float64)
    fits.PrimaryHDU(data * 1e-300).writeto(tmp_path / "t.fits")
    r = fit(tmp_path / "t.fits", tmp_path, sky=1e-305)
    ref = fit(GAL, tmp_path, sky=1e-5, precision="double", prefix="ref")
    np.testing.assert_allclose(r.profile.I0, ref.profile.I0 * 1e-300,
                               rtol=1e-6)


def test_read_prf_keeps_single_rounding(tmp_path):
    r = run_elliprof(EXAMPLE / "u12517j.fits", 567, 562,
                     mask=EXAMPLE / "u12517j.dmask", sky=3246.0, r0=9,
                     r1=347, nr=23, niter=10, rmstar=True,
                     output_dir=tmp_path)
    prf = read_prf(str(r.prf_path))
    assert prf["precision"] == "single"
    assert prf["normalization_exponent"] is None
    v = prf["params"]
    assert np.array_equal(v, v.astype(np.float32).astype(np.float64))


def test_invalid_precision_and_gc():
    with pytest.raises(ValueError, match="precision must be"):
        run_elliprof(GAL, 1, 1, **KW, precision="quad")
    with pytest.raises(ValueError, match="GC mode is not yet supported"):
        run_elliprof(GAL, 1, 1, nr=3, gc=True, precision="double")


def test_io_helpers_in_double():
    data = np.array([[1e300, -2e-300], [3.0000000000000004, 0.0]])
    out = subtract_sky(data, sky=1e299, precision="double")
    assert out.dtype == np.float64
    assert np.array_equal(out, data - 1e299)
    sky = np.full((2, 2), 1e-310)
    assert np.array_equal(subtract_sky(data, sky_image=sky,
                                       precision="double"), data - sky)
    mask = np.array([[1, 0], [1, 1]])
    m = apply_mask(data, mask, precision="double")
    assert m.dtype == np.float64 and m[0, 1] == 0 and m[1, 0] == data[1, 0]
    # single: unchanged float32 behaviour, still the default
    assert subtract_sky(data[1:], sky=1.0).dtype == np.float32
    assert apply_mask(data[1:], mask[1:]).dtype == np.float32
    with pytest.raises(ValueError, match="precision must be"):
        subtract_sky(data, precision="auto")


def test_cli_precision(tmp_path):
    args = [GAL, "X0=100.3", "Y0=99.6", "R0=3", "R1=80", "NR=25",
            "-o", tmp_path / "a.dat"]
    p = run_cli(*args, "--precision", "double")
    assert p.returncode == 0, p.stderr
    assert "Precision: double (requested; fit on image x 2**-k, k = " \
        in p.stdout
    assert read_profile(str(tmp_path / "a.dat")).attrs["precision"] == \
        "double"
    p = run_cli(*args)
    assert "Precision: single (auto: every value is within float32)" in \
        p.stdout
    p = run_cli(*args, "--precision", "quad")
    assert p.returncode == 2 and "--precision must be auto, single or " \
        "double" in p.stderr
    fits.PrimaryHDU(fits.getdata(GAL).astype(np.float64)).writeto(
        tmp_path / "g.fits")
    p = run_cli(tmp_path / "g.fits", *args[1:], "--precision", "single")
    assert "BITPIX -64 read as 32-bit float" in p.stdout
    assert "Precision: single (requested)" in p.stdout


def test_help_documents_precision():
    p = run_cli("-h")
    assert "--precision auto|single|double" in p.stdout
    assert "PRECISION" in p.stdout
