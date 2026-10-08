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


# ---- R6, k > 0 ----------------------------------------------------------

def winged():
    """The ordinary galaxy with its wing beyond a = 60 made 1e30 times
    fainter: the model's far wing goes below 1e-308 of the median."""
    img = fits.getdata(GAL).astype(np.float64)
    j, i = np.indices(img.shape)
    return np.where(np.hypot(i + 0.5 - 100.3, j + 0.5 - 99.6) > 60,
                    img * 1e-30, img)


def test_model_positive_k_physical_range(run_native, tmp_path):
    """x 2**300 (k = 202) and x 2**900 (k = 802): the same internal fit.
    Model pixels representable in physical units are no longer zero
    because the normalized model underflowed (before R6: 30246 zeros at
    every scale); wherever both are normal they scale exactly; the
    counts describe physical underflow and subnormal values."""
    img = winged()
    res = {}
    for m in (300, 900):
        p, out = run(run_native, tmp_path, np.ldexp(img, m), name=f"w{m}")
        assert p.returncode == 0, p.stderr
        check_units(out)
        model = fits.getdata(out["m"]).astype(np.float64)
        lines = model_lines(p.stdout)
        zeros = int(lines[0].split()[1])
        subn = int(lines[1].split()[1])
        # every counted subnormal is in the file, every counted zero too
        assert subn == ((model != 0) & (np.abs(model) < TINY)).sum()
        assert zeros <= (model == 0).sum()
        res[m] = (model, zeros, subn, out)
    a, b = res[300][0], res[900][0]
    both = (np.abs(a) >= TINY) & (np.abs(b) >= TINY)
    assert both.sum() > 10000
    assert np.array_equal(np.ldexp(a[both], 600), b[both])
    # a larger physical scale: fewer pixels below the physical range
    assert res[900][1] < res[300][1] < 30246
    # the zeros that remain at x 2**900 are below the smallest subnormal
    # there: nonzero at x 2**300 nowhere
    assert not ((b == 0) & (a != 0)).any()
    csv = res[900][3]["csv"].read_text()
    assert f"# Model underflow to zero: {res[900][1]} pixel(s)" in csv
    assert f"# Model subnormal (nonzero): {res[900][2]} pixel(s)" in csv
    hist = [str(c) for c in fits.getheader(res[900][3]["m"])["HISTORY"]]
    assert f"elliprof model subnormal (nonzero): {res[900][2]} pixel(s)" \
        in hist


def test_subnormal_and_zero_are_distinguished(run_native, tmp_path):
    """k < 0 (the image as is): physical underflow is genuine; zeros and
    subnormal values are counted separately, also by Python."""
    from elliprof import run_elliprof
    fits.PrimaryHDU(winged()).writeto(tmp_path / "w.fits")
    r = run_elliprof(tmp_path / "w.fits", 100.3, 99.6, r0=3, r1=80, nr=25,
                     model=True, output_dir=tmp_path, precision="double")
    assert r.ok
    model = fits.getdata(r.model_path).astype(np.float64)
    assert r.model_underflow_zero_count > 0
    assert r.model_subnormal_count == \
        ((model != 0) & (np.abs(model) < TINY)).sum() > 0
    assert r.model_underflow_zero_count <= (model == 0).sum()


# ---- R6, k < 0 ----------------------------------------------------------

def masked_nucleus(peak):
    """A bright galaxy whose nucleus (r < 8) is masked -- the fit starts
    outside it (R0 = 10) and the model extrapolates inward -- on a
    background of ~1e-300 covering most of the image, so that the
    normalization exponent is clamped near its lower limit."""
    g = fits.getdata(GAL).astype(np.float64)
    j, i = np.indices(g.shape)
    r = np.hypot(i + 0.5 - 100.3, j + 0.5 - 99.6)
    img = g / g.max() * peak
    img[r > 50] = 1e-300 * (1 + 0.01 * np.sin(r[r > 50]))
    return img, (r >= 8).astype(np.int16)


@pytest.mark.parametrize("peak", [1e10, 1e300])
def test_model_negative_k_physical_range(run_native, tmp_path, peak):
    """The inward extrapolation exceeds DBL_MAX in normalized units
    (exp(712) there): before R6 an error ("the model at pixel ... is
    exp(7.10E+002), beyond the double range"); the physical model is
    representable and is now returned."""
    img, mask = masked_nucleus(peak)
    fit = ["X0=100.3", "Y0=99.6", "R0=10", "R1=45", "NR=15", "NITER=5"]
    p, out = run(run_native, tmp_path, img, name="n", fit=fit, mask=mask)
    assert p.returncode == 0, p.stderr
    assert "k = -" in p.stdout
    model = fits.getdata(out["m"]).astype(np.float64)
    assert np.isfinite(model).all()
    assert model.max() > img[mask.astype(bool)].max()   # extrapolated
    check_units(out, mask)


def test_ordinary_products_in_physical_units(run_native, tmp_path):
    p, out = run(run_native, tmp_path, fits.getdata(GAL).astype(np.float64),
                 name="o")
    assert p.returncode == 0, p.stderr
    check_units(out)
    assert model_lines(p.stdout) == []


# ---- R7 -----------------------------------------------------------------

def annuli():
    """Three flat annuli matching a coarse log grid (radii 4, 10, 25:
    ratio 2.5, so |r/(r(k-1)-r(k+1))| = 0.48 < 1 at the middle one):
    I(k-1)/I(k) ~ 2e308 overflows, the slope (~ -9.5e307) does not."""
    j, i = np.indices((120, 120))
    r = np.hypot(i + 0.5 - 60.3, j + 0.5 - 59.6)
    return np.where(r < 6, 1e300, np.where(r < 15, 5e-9, 1e-300)) * (
        1 + 0.001 * np.cos(3 * np.arctan2(j - 59.6, i - 60.3)))


R7FIT = ["X0=60.3", "Y0=59.6", "R0=4", "R1=25", "NR=3", "NITER=5",
         "RLAW=1"]


def test_slope_with_overflowing_intermediate(run_native, tmp_path):
    """Before R7: "the slope dlnI/dlnr of isophote 2 is beyond the
    double range", exit 1.  Now the slope, exactly as recomputed in
    rational arithmetic from the printed I0 and radii.  (With -m the run
    then stops at the model, genuinely beyond DBL_MAX at the centre.)"""
    from fractions import Fraction as F
    fits.PrimaryHDU(annuli()).writeto(tmp_path / "r7.fits")
    # profile only: the model of this profile, extrapolated inward from
    # r = 4 (ln I falls by ~710 between r = 4 and 10), is genuinely
    # beyond DBL_MAX at the centre (ln I ~ 3448) -- a model range error
    p = run_native(tmp_path / "r7.fits", *R7FIT, "--precision", "double",
                   "-o", tmp_path / "r7.dat")
    assert p.returncode == 0, p.stderr
    v = read_dat(tmp_path / "r7.dat")
    rad, i0, slope = v[:, 0], v[:, 3], v[:, 10]
    exact = float((F(i0[0]) - F(i0[2])) / F(i0[1]) * F(rad[1])
                  / (F(rad[0]) - F(rad[2])))
    assert -DMAX < exact < -1e307
    assert abs(slope[1] - exact) <= 4 * np.spacing(abs(exact))
