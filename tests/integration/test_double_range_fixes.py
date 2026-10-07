"""Range fixes of the double backend, on images with an enormous
dynamic range inside one image (not a global scale):

* contour/f0 beyond DBL_MAX for finite positive values: the logarithm
  is taken in the log domain, only on that path;
* the AVG box sum beyond DBL_MAX while its weighted average is finite:
  accumulated scaled, only on that path;
* an isophote intensity that still overflows: a clear error, never a
  silent NaN success;
* model pixels that underflow to zero: counted and reported.

Ordinary images never take the new paths: their double results are
bit-identical with and without them (verified with the previous build
for every regression case, AVG 0/1/2 and LINEAR; see the candidate
report)."""

import numpy as np
import pytest

from helpers import DATA

fits = pytest.importorskip("astropy.io.fits")

GAL = DATA / "regression" / "rotated.fits"
FIT = ["X0=100.3", "Y0=99.6", "R0=3", "R1=80", "NR=25", "NITER=5"]
C, S = np.cos(np.radians(55)), np.sin(np.radians(55))


def read_dat(path):
    tok = open(path).read().split(None, 3002)
    n = int(tok[0])
    return np.array([float(t) for t in tok[2:3002]]).reshape(250, 12)[:n]


def galaxy(scale=1e-300):
    return fits.getdata(GAL).astype(np.float64) * scale


def extreme():
    """A galaxy at ~1e-300..6e-295 with 1e300 sources: one pixel on the
    a = 40 isophote, a 3 x 3 block near a = 60, and a corner.  Its finite
    positive pixels span ~1e-301 .. 1e300."""
    img = galaxy()
    img[int(99.6 + 40 * S), int(100.3 + 40 * C)] = 1e300
    yb, xb = int(99.6 - 60 * S), int(100.3 - 60 * C)
    img[yb - 1:yb + 2, xb - 1:xb + 2] = 1e300
    img[:3, :3] = 1e300
    return img


def run(run_native, tmp_path, img, *args, name="x"):
    path = tmp_path / f"{name}.fits"
    fits.PrimaryHDU(img).writeto(path, overwrite=True)
    out = {k: tmp_path / f"{name}_{k}" for k in ("dat", "csv", "m", "r",
                                                  "p")}
    p = run_native(path, *FIT, *args, "-o", out["dat"], "--csv",
                   out["csv"], "-m", out["m"], "--residual", out["r"],
                   "--prepared", out["p"])
    return p, out


@pytest.mark.parametrize("args", [[], ["AVG=1"], ["AVG=2"],
                                  ["COS3X=-3"], ["COS4X=1", "COS3X=1"]],
                         ids=lambda a: "_".join(a) or "default")
def test_extreme_intra_image_range(run_native, tmp_path, args):
    """Before the fixes this gave NaN at isophotes 17-23 and a NaN model
    and residual, with exit status 0."""
    img = extreme()
    p, out = run(run_native, tmp_path, img, *args)
    assert p.returncode == 0, p.stderr
    assert "the preferred k was clamped" in p.stdout
    prof = read_dat(out["dat"])
    assert np.isfinite(prof[:, :6]).all()
    for k in ("m", "r"):
        assert np.isfinite(fits.getdata(out[k])).all()
    # normalization keeps every finite input value
    assert np.array_equal(fits.getdata(out["p"]), img)
    model = fits.getdata(out["m"])
    assert model[model > 0].min() < 1e-300       # no float32-era floor


def test_extreme_range_with_rmstar_matches_the_clean_galaxy(run_native,
                                                            tmp_path):
    """With the 1e300 sources rejected as stars, the profile is that of
    the galaxy alone; without RMSTAR the isophotes crossing a source
    10**600 times brighter follow it (fit behaviour, not numerics)."""
    for args in (["RMSTAR"], ["RMSTAR", "AVG=2"]):
        p, out = run(run_native, tmp_path, extreme(), *args)
        assert p.returncode == 0, p.stderr
        q, ref = run(run_native, tmp_path, galaxy(), *args, name="g")
        a, b = read_dat(out["dat"]), read_dat(ref["dat"])
        tol = 1e-5 if args == ["RMSTAR"] else 0.05
        assert np.abs(a[:, 1:3] - b[:, 1:3]).max() < tol


def test_log_ratio_beyond_dblmax_single_pixel(run_native, tmp_path):
    """One 1e300 pixel on an isophote of a 1e-300 galaxy: contour/f0 is
    about 1e600, not representable; its logarithm (~1381) is."""
    img = galaxy()
    img[int(99.6 + 40 * S), int(100.3 + 40 * C)] = 1e300
    p, out = run(run_native, tmp_path, img)
    assert p.returncode == 0, p.stderr
    assert np.isfinite(read_dat(out["dat"])[:, :11][:, :6]).all()


def test_avg_sum_beyond_dblmax(run_native, tmp_path):
    """extreme() puts a 3 x 3 block of 1e300 (internally ~1.3e308 after
    the clamped normalization) inside AVG boxes: the weighted sum would
    exceed DBL_MAX, the average does not.  Before the fix: NaN isophotes
    with exit 0 (see test_extreme_intra_image_range)."""
    for avg in ("AVG=1", "AVG=2"):
        p, out = run(run_native, tmp_path, extreme(), avg)
        assert p.returncode == 0, p.stderr
        assert np.isfinite(read_dat(out["dat"])[:, :11]).all()


def test_unrepresentable_slope_is_an_error(run_native, tmp_path):
    """A 5 x 5 block of 1.5e308 by the a = 30 isophote: the fit leaves
    the double range (an I0 underflowing to 0 in ALTER, a slope of
    ~1e606) -- a clear error, not a silent 0 / Inf / NaN."""
    img = galaxy()
    yb, xb = int(99.6 + 30 * S), int(100.3 + 30 * C)
    img[yb - 2:yb + 3, xb - 2:xb + 3] = 1.5e308
    p, out = run(run_native, tmp_path, img, "AVG=2")
    assert p.returncode == 1
    # isophote 15 is seeded on the block (I0 = 1.5e308); its neighbour's
    # f0 * exp(c) update underflows in exp(c) (c ~ -1400) to I0 = 0, and
    # the next slope is beyond the range: the first is reported
    assert "underflowed to zero during the fit" in p.stderr or \
        "the slope dlnI/dlnr of isophote" in p.stderr


def test_ordinary_avg_unchanged_by_the_scaled_path(run_native, tmp_path):
    """Ordinary images: AVG results are those of the scale invariance
    (bit-exact under 2**m), which the scaled path would break."""
    for m in (0, 500):
        p, out = run(run_native, tmp_path, np.ldexp(galaxy(1.0), m),
                     "AVG=2", name=f"a{m}")
        assert p.returncode == 0, p.stderr
    a, b = read_dat(tmp_path / "a0_dat"), read_dat(tmp_path / "a500_dat")
    assert np.array_equal(a[:, [0, 1, 2, 4, 5, 10]],
                          b[:, [0, 1, 2, 4, 5, 10]])
    assert np.array_equal(np.ldexp(a[:, 3], 500), b[:, 3])


def test_intensity_overflow_is_an_error_not_nan(run_native, tmp_path):
    """A core at 1.5e308 beside a 1e-300 background: the fit's iterate
    for the core-edge isophote leaves the double range.  A clear error
    (exit 1), never NaN isophotes with exit 0."""
    img = galaxy()
    j, i = np.indices(img.shape)
    img[np.hypot(i + 0.5 - 100.3, j + 0.5 - 99.6) < 4] = 1.5e308
    fits.PrimaryHDU(img).writeto(tmp_path / "b.fits")
    p = run_native(tmp_path / "b.fits", *FIT, "-o", tmp_path / "b.dat")
    assert p.returncode == 1
    assert "error (double precision, fit): the intensity I0 of isophote" \
        in p.stderr
    assert not (tmp_path / "b.dat").exists()


def test_model_underflow_is_counted(run_native, tmp_path):
    """A galaxy whose outer part is 1e-30 times fainter: the model's
    exponential underflows to zero in the far wings.  Counted, reported
    once, recorded in the CSV and FITS HISTORY; not an error."""
    img = galaxy(1.0)
    j, i = np.indices(img.shape)
    img = np.where(np.hypot(i + 0.5 - 100.3, j + 0.5 - 99.6) > 60,
                   img * 1e-30, img)
    p, out = run(run_native, tmp_path, img)
    assert p.returncode == 0, p.stderr
    lines = [l for l in p.stdout.splitlines() if "underflowed" in l]
    assert len(lines) == 1
    n = int(lines[0].split()[1])
    assert n > 0 and lines[0].strip() == \
        f"Model: {n} pixels underflowed to zero at double precision."
    assert f"# Model underflow to zero: {n} pixel(s)" in \
        out["csv"].read_text()
    hist = [str(c) for c in fits.getheader(out["m"])["HISTORY"]]
    assert f"elliprof model underflow to zero: {n} pixel(s)" in hist
    assert (fits.getdata(out["m"]) == 0).sum() >= n
    # an ordinary galaxy: nothing underflows, the count is recorded as 0
    p, out = run(run_native, tmp_path, galaxy(1.0), name="o")
    assert "underflowed" not in p.stdout
    assert "# Model underflow to zero: 0 pixel(s)" in out["csv"].read_text()


def test_python_reports_the_counts(tmp_path):
    from elliprof import run_elliprof
    img = galaxy(1.0)
    img[5:7, 5:8] = np.nan
    fits.PrimaryHDU(img).writeto(tmp_path / "n.fits")
    r = run_elliprof(tmp_path / "n.fits", 100.3, 99.6, r0=3, r1=80, nr=25,
                     output_dir=tmp_path, model=True)
    assert r.precision == "double"
    assert r.nonfinite_policy == "mask"
    assert r.nonfinite_counts == {"nan": 6, "posinf": 0, "neginf": 0,
                                  "masked": 6}
    assert r.model_underflow_zero_count == 0
    r = run_elliprof(GAL, 100.3, 99.6, r0=3, r1=80, nr=25,
                     output_dir=tmp_path, prefix="s",
                     precision="single")
    assert r.nonfinite_policy == "keep"
    assert r.model_underflow_zero_count is None
