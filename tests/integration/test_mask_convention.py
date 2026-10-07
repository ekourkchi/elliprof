"""--mask-convention (0.1.4): the same logical mask written in the two
common conventions gives exactly the same fit.

    nonzero-good (default):  good = finite and value != 0
    zero-good:               good = finite and value == 0
    NaN, +-Inf, undefined:   bad in both
"""

import subprocess

import numpy as np
import pytest

from elliprof import read_prf, run_elliprof, write_bitmap_mask
from elliprof.io import apply_mask, logical_mask
from helpers import ROOT, run_cli

fits = pytest.importorskip("astropy.io.fits")

IMAGE = ROOT / "tests" / "data" / "regression" / "star.fits"
FIT = ["X0=100.3", "Y0=99.6", "R0=3", "R1=80", "NR=25"]


def cli(*args, cwd=None):
    """The user-facing command, as a separate process."""
    return run_cli(*args, cwd=cwd)


def native_run(native, *args):
    return subprocess.run([str(native), *map(str, args)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=600)


@pytest.fixture(scope="module")
def bad():
    shape = fits.getdata(IMAGE).shape
    b = np.zeros(shape, bool)
    b[50:66, 140:160] = True                     # the star
    b[np.random.default_rng(7).random(shape) < 0.03] = True
    return b


def fit(native, tmp_path, name, mask, *extra):
    """Profile, prepared, model and residual for one mask file."""
    out = {k: tmp_path / f"{name}.{k}" for k in ("dat", "p", "m", "r")}
    p = native_run(native, IMAGE, *FIT, "--mask", mask, *extra,
                   "-o", out["dat"], "--prepared", out["p"], "-m", out["m"],
                   "--residual", out["r"])
    assert p.returncode == 0, (name, p.stderr)
    return p, (out["dat"].read_bytes(), fits.getdata(out["p"]),
               fits.getdata(out["m"]), fits.getdata(out["r"]))


def same(a, b):
    assert a[0] == b[0]                          # profile, byte for byte
    for x, y in zip(a[1:], b[1:]):
        assert x.dtype == y.dtype and np.array_equal(x, y, equal_nan=True)


def test_primary_acceptance_one_zero(native, tmp_path, bad):
    """Mask A: good 1 / bad 0 (default).  Mask B: good 0 / bad 1
    (zero-good).  Identical results."""
    fits.PrimaryHDU((~bad).astype(np.int16)).writeto(tmp_path / "A.fits")
    fits.PrimaryHDU(bad.astype(np.int16)).writeto(tmp_path / "B.fits")
    pa, a = fit(native, tmp_path, "A", tmp_path / "A.fits")
    pb, b = fit(native, tmp_path, "B", tmp_path / "B.fits",
                "--mask-convention", "zero-good")
    same(a, b)
    n = int(bad.sum())
    assert f"{n} pixels masked" in pa.stdout
    assert f"{n} pixels masked" in pb.stdout
    assert "convention zero-good" in pb.stdout
    assert "convention zero-good" not in pa.stdout
    assert not np.any(a[1][bad]) and not np.any(a[3][bad])


def test_primary_acceptance_with_nans(native, tmp_path, bad):
    half = bad & (np.random.default_rng(8).random(bad.shape) < 0.5)
    ma = np.where(bad, 0.0, 1.0).astype(np.float32)
    ma[half] = np.nan
    mb = np.where(bad, 1.0, 0.0).astype(np.float32)
    mb[half] = np.nan
    fits.PrimaryHDU(ma).writeto(tmp_path / "A.fits")
    fits.PrimaryHDU(mb).writeto(tmp_path / "B.fits")
    pa, a = fit(native, tmp_path, "A", tmp_path / "A.fits")
    pb, b = fit(native, tmp_path, "B", tmp_path / "B.fits",
                "--mask-convention", "zero-good")
    same(a, b)
    nan = f"{int(half.sum())} of them NaN"
    assert nan in pa.stdout and nan in pb.stdout


@pytest.mark.parametrize("dtype", [np.uint8, np.int16, np.int32, np.int64,
                                   np.float32, np.float64])
def test_zero_good_any_type_and_nonzero_values(native, tmp_path, bad,
                                               dtype):
    """Bad pixels carry positive, negative and mixed nonzero values (and
    NaN/Inf for floats); all are bad with zero-good."""
    rng = np.random.default_rng(9)
    if np.dtype(dtype).kind == "f":
        vals = np.array([1, -1, 2.5, -7.25, 1e-30, 3e20])
    elif dtype == np.uint8:
        vals = np.array([1, 2, 255])
    elif dtype == np.int64:
        vals = np.array([1, -1, 9, -32768, 2 ** 40, -(2 ** 62)])
    else:
        vals = np.array([1, -1, 9, -300, 127])
    mb = np.where(bad, vals[rng.integers(0, len(vals), bad.shape)], 0)
    mb = mb.astype(dtype)
    if np.dtype(dtype).kind == "f":
        mb[bad & (rng.random(bad.shape) < 0.3)] = np.nan
        mb[bad & (rng.random(bad.shape) < 0.1)] = -np.inf
    fits.PrimaryHDU(mb).writeto(tmp_path / "B.fits")
    write_bitmap_mask(str(tmp_path / "A.dmask"), (~bad).astype(np.uint8))
    _, a = fit(native, tmp_path, "A", tmp_path / "A.dmask")
    _, b = fit(native, tmp_path, "B", tmp_path / "B.fits",
               "--mask-convention", "zero-good")
    same(a, b)


def test_64_bit_masks_are_classified_on_the_stored_value(native, tmp_path):
    """Tiny and huge 64-bit values are nonzero (and finite): good by
    default, bad with zero-good.  (A 32-bit copy would round 1e-300 to
    0 and 1e300 to Inf.)"""
    shape = fits.getdata(IMAGE).shape
    m = np.ones(shape)
    m[:, :20] = 1e-300
    m[:, 20:40] = -1e300
    m[:, 40:60] = 0.0
    fits.PrimaryHDU(m).writeto(tmp_path / "m.fits")
    p = native_run(native, IMAGE, "--mask", tmp_path / "m.fits",
                   "--prepare-only", "--prepared", tmp_path / "p.fits")
    q = native_run(native, IMAGE, "--mask", tmp_path / "m.fits",
                   "--mask-convention", "zero-good", "--prepare-only",
                   "--prepared", tmp_path / "q.fits")
    assert p.returncode == q.returncode == 0, p.stderr + q.stderr
    assert f"{20 * shape[0]} pixels masked" in p.stdout
    assert f"{180 * shape[0]} pixels masked" in q.stdout
    sci = fits.getdata(IMAGE)
    assert np.array_equal(fits.getdata(tmp_path / "p.fits")[:, :40],
                          sci[:, :40])
    assert not fits.getdata(tmp_path / "q.fits")[:, :40].any()
    big = np.zeros(shape, np.int64)
    big[:, :20] = 2 ** 62 + 1
    fits.PrimaryHDU(big).writeto(tmp_path / "i.fits")
    r = native_run(native, IMAGE, "--mask", tmp_path / "i.fits",
                   "--prepare-only", "--prepared", tmp_path / "r.fits")
    assert f"{180 * shape[0]} pixels masked" in r.stdout


def test_default_convention_unchanged(native, tmp_path, bad):
    """--mask-convention nonzero-good is the default, spelled out."""
    fits.PrimaryHDU(np.where(bad, 0, -3).astype(np.int32)).writeto(
        tmp_path / "A.fits")
    _, a = fit(native, tmp_path, "A", tmp_path / "A.fits")
    _, b = fit(native, tmp_path, "B", tmp_path / "A.fits",
               "--mask-convention", "nonzero-good")
    same(a, b)


def test_legacy_bitmap_refused_with_zero_good(native, tmp_path, bad):
    write_bitmap_mask(str(tmp_path / "m.dmask"), (~bad).astype(np.uint8))
    p = native_run(native, IMAGE, *FIT, "--mask", tmp_path / "m.dmask",
                   "--mask-convention", "zero-good", "-o", tmp_path / "x")
    assert p.returncode == 1
    assert "legacy BITPIX = 1" in p.stderr and "zero-good" in p.stderr
    assert not (tmp_path / "x").exists()


def test_cli_and_api(tmp_path, bad):
    fits.PrimaryHDU(bad.astype(np.uint8)).writeto(tmp_path / "B.fits")
    p = cli(IMAGE, *FIT, "--mask", tmp_path / "B.fits",
            "--mask-convention", "zero-good", "-o", tmp_path / "cli.dat")
    assert p.returncode == 0, p.stderr
    assert f"{int(bad.sum())} pixels masked" in p.stdout
    assert "; zero-good" in p.stdout
    r = run_elliprof(IMAGE, 100.3, 99.6, r0=3, r1=80, nr=25,
                     mask=tmp_path / "B.fits", mask_convention="zero-good",
                     output_dir=tmp_path, prf_path=tmp_path / "api.dat")
    i = r.command.index("--mask-convention")
    assert r.ok and r.command[i + 1] == "zero-good"
    assert (tmp_path / "api.dat").read_bytes() == \
        (tmp_path / "cli.dat").read_bytes()
    assert read_prf(str(tmp_path / "api.dat"))["n"] == 25
    for args, msg in (
            (["--mask-convention", "zero-good"], "needs --mask"),
            (["--mask", tmp_path / "B.fits", "--mask-convention",
              "inverted"], "nonzero-good or zero-good")):
        q = cli(IMAGE, *FIT, *args)
        assert q.returncode == 2 and msg in q.stderr, q.stderr
    with pytest.raises(ValueError, match="nonzero-good"):
        run_elliprof(IMAGE, 100.3, 99.6, r0=3, r1=80, nr=25,
                     mask=tmp_path / "B.fits", mask_convention="invert")


def test_python_helpers():
    m = np.array([0, 1, -2, np.nan, np.inf, 0.5])
    assert logical_mask(m).tolist() == [False, True, True, False, False,
                                        True]
    assert logical_mask(m, "zero-good").tolist() == [True, False, False,
                                                     False, False, False]
    i = np.array([0, 3, -1], np.int64)
    assert logical_mask(i, "zero-good").tolist() == [True, False, False]
    d = np.array([5.0, 6.0, 7.0])
    assert apply_mask(d, np.array([0, 1, 0]), "zero-good").tolist() == \
        [5.0, 0.0, 7.0]
    with pytest.raises(ValueError):
        logical_mask(m, "invert")
