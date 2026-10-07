"""R4, R5 and R6 through the backend, on images built to reach them.

R4  bilinear samples near DBL_MAX: a faint galaxy (median < 1, so the
    normalization exponent is 0) with a block of exactly DBL_MAX on an
    isophote.  The historical sum rounded past DBL_MAX and gave NaN
    geometry with exit 0.
R5  the log-fit I0 update: see test_intensity_overflow_is_an_error_not_nan
    (test_double_range_fixes.py) and tests/unit/test_range_guards.py.
R6  the model in physical units: normalization alone must never turn a
    representable physical model into 0, a subnormal or Inf -- k > 0
    (a bright image with a faint extended wing) and k < 0 (a masked
    nucleus: the fit starts outside it, R0 >= 3, and the model is
    extrapolated inward above every unmasked pixel).

Ordinary images never take these paths (bit-identical to the previous
build for every regression case; see the candidate report).
"""

import numpy as np
import pytest

from helpers import DATA

fits = pytest.importorskip("astropy.io.fits")

GAL = DATA / "regression" / "rotated.fits"
SYN = DATA / "synthetic_galaxy.fits"
FIT = ["X0=100.3", "Y0=99.6", "R0=3", "R1=80", "NR=25", "NITER=5"]
TINY = np.finfo(float).tiny
DMAX = np.finfo(float).max


def read_dat(path):
    tok = open(path).read().split(None, 3002)
    n = int(tok[0])
    return np.array([float(t) for t in tok[2:3002]]).reshape(250, 12)[:n]


def run(run_native, tmp_path, img, *args, name="x", fit=FIT, mask=None):
    path = tmp_path / f"{name}.fits"
    fits.PrimaryHDU(img).writeto(path, overwrite=True)
    out = {k: tmp_path / f"{name}_{k}" for k in ("dat", "csv", "m", "r",
                                                  "p")}
    extra = []
    if mask is not None:
        fits.PrimaryHDU(mask.astype(np.int16)).writeto(
            tmp_path / f"{name}_mask.fits", overwrite=True)
        extra = ["--mask", tmp_path / f"{name}_mask.fits"]
    p = run_native(path, *fit, *args, *extra, "--precision", "double",
                   "-o", out["dat"], "--csv", out["csv"], "-m", out["m"],
                   "--residual", out["r"], "--prepared", out["p"])
    return p, out


def check_units(out, mask=None):
    """prepared, model and residual all in physical units:
    residual = prepared - model (binary64) where the mask is good, 0
    elsewhere."""
    prep = fits.getdata(out["p"]).astype(np.float64)
    model = fits.getdata(out["m"]).astype(np.float64)
    resid = fits.getdata(out["r"]).astype(np.float64)
    good = np.ones(prep.shape, bool) if mask is None else mask.astype(bool)
    with np.errstate(invalid="ignore", over="ignore"):
        expect = np.where(good, prep - model, 0.0)
    assert np.array_equal(resid, expect, equal_nan=True)


def model_lines(stdout):
    return [l.strip() for l in stdout.splitlines()
            if l.strip().startswith("Model:")]


# ---- R4 -----------------------------------------------------------------

def faint_with_block(value, half=8):
    img = (fits.getdata(SYN).astype(np.float64) - 100.0) * 1e-3
    yy, xx = int(121.6), int(127.3 + 40)
    img[yy - half:yy + half + 1, xx - half:xx + half + 1] = value
    return img


SYNFIT = ["X0=127.3", "Y0=121.6", "R0=3", "R1=90", "NR=30"]


def test_bilinear_at_dblmax_is_finite(run_native, tmp_path):
    """A 17 x 17 block of DBL_MAX (k = 0): finite geometry, and exactly
    the profile of the same block two ulp lower (where the historical
    sum never overflowed)."""
    p, out = run(run_native, tmp_path, faint_with_block(DMAX), name="a",
                 fit=SYNFIT)
    assert p.returncode == 0, p.stderr
    assert "k = 0 " in p.stdout
    a = read_dat(out["dat"])[:, :11]
    assert np.isfinite(a).all()
    below = np.nextafter(np.nextafter(DMAX, 0), 0)
    p, out = run(run_native, tmp_path, faint_with_block(below), name="b",
                 fit=SYNFIT)
    assert p.returncode == 0, p.stderr
    assert np.array_equal(a, read_dat(out["dat"])[:, :11])


def test_bilinear_at_minus_dblmax(run_native, tmp_path):
    p, out = run(run_native, tmp_path, faint_with_block(-DMAX), name="c",
                 fit=SYNFIT)
    assert p.returncode == 0, p.stderr
    assert np.isfinite(read_dat(out["dat"])[:, :11]).all()
