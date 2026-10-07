"""Products and profile output of the double backend, and the range of
its model synthesis: BITPIX -64 model/residual/prepared in physical
units, the CSV and .dat over the whole double range, and the model
beyond the REAL*4 limits of the original synthesis."""

import re

import numpy as np
import pytest

from helpers import DATA

fits = pytest.importorskip("astropy.io.fits")
pd = pytest.importorskip("pandas")

GAL = DATA / "regression" / "rotated.fits"
FIT = ["X0=100.3", "Y0=99.6", "R0=3", "R1=80", "NR=25", "NITER=5"]
COLS = ["Rmaj", "x0", "y0", "I0", "alpha", "ellip", "I3", "A3", "I4",
        "A4", "slope"]


def read_dat(path):
    tok = open(path).read().split(None, 2 + 3000)
    n = int(tok[0])
    return n, np.array([float(t) for t in tok[2:3002]]).reshape(250, 12)


def run(run_native, tmp_path, image, *args, prec="double", name="o"):
    out = {k: tmp_path / f"{name}_{prec}.{k}" for k in
           ("dat", "csv", "reg")}
    out.update({k: tmp_path / f"{name}_{prec}_{k}.fits" for k in
                ("model", "res", "prep")})
    p = run_native(image, *args, "--precision", prec, "-o", out["dat"],
                   "--csv", out["csv"], "--reg", out["reg"], "-m",
                   out["model"], "--residual", out["res"], "--prepared",
                   out["prep"])
    return p, out


def image(path):
    with fits.open(path) as h:
        return h[0].header, h[0].data.astype(np.float64)


def scaled(tmp_path, m=None, factor=None, name="s.fits", base=GAL):
    data = fits.getdata(base).astype(np.float64)
    data = np.ldexp(data, m) if m is not None else data * factor
    fits.PrimaryHDU(data).writeto(tmp_path / name, overwrite=True)
    return tmp_path / name


def test_products_are_64_bit_with_history(run_native, tmp_path):
    hdr = fits.Header()
    hdr["BUNIT"] = "MJy/sr"
    hdr["CTYPE1"] = "RA---TAN"
    hdr["CRVAL1"] = 12.5
    fits.PrimaryHDU(fits.getdata(GAL), hdr).writeto(tmp_path / "w.fits")
    p, out = run(run_native, tmp_path, tmp_path / "w.fits", *FIT)
    assert p.returncode == 0, p.stderr
    for k in ("model", "res", "prep"):
        h, d = image(out[k])
        assert h["BITPIX"] == -64
        assert h["BUNIT"] == "MJy/sr" and h["CTYPE1"] == "RA---TAN"
        assert h["CRVAL1"] == 12.5
        hist = [str(c) for c in h["HISTORY"]]
        assert any("product:" in c for c in hist)
        assert "elliprof precision: double (IEEE-754 binary64)" in hist
        assert any(c.startswith("elliprof normalization: k=") for c in hist)
    _, model = image(out["model"])
    _, res = image(out["res"])
    _, prep = image(out["prep"])
    assert np.array_equal(res, prep - model)          # no mask: all good


@pytest.mark.parametrize("m", [-1000, -500, 500, 1000])
def test_model_and_residual_scale_exactly(run_native, tmp_path, m):
    p, ref = run(run_native, tmp_path, GAL, *FIT, name="ref")
    assert p.returncode == 0, p.stderr
    p, new = run(run_native, tmp_path, scaled(tmp_path, m), *FIT)
    assert p.returncode == 0, p.stderr
    for k in ("model", "res", "prep"):
        assert np.array_equal(image(new[k])[1],
                              np.ldexp(image(ref[k])[1], m)), k


@pytest.mark.parametrize("factor", [1e-300, 1e-200, 1e-100, 1e-50, 1e50,
                                    1e100, 1e200, 1e300])
def test_extreme_scales_fit_model_residual(run_native, tmp_path, factor):
    """No 3.4e38, 1e-38 or ln 85 barrier: a galaxy at any scale of the
    double range gives the same profile and model, to rounding."""
    p, ref = run(run_native, tmp_path, GAL, *FIT, name="ref")
    p, new = run(run_native, tmp_path, scaled(tmp_path, factor=factor),
                 *FIT)
    assert p.returncode == 0, p.stderr
    n, a = read_dat(ref["dat"])
    _, b = read_dat(new["dat"])
    geo = [0, 1, 2, 4, 5, 10]
    np.testing.assert_allclose(b[:n, geo], a[:n, geo], rtol=1e-9,
                               atol=1e-9)
    np.testing.assert_allclose(b[:n, 3], a[:n, 3] * factor, rtol=1e-9)
    ma, mb = image(ref["model"])[1], image(new["model"])[1]
    assert np.all(np.isfinite(mb)) and np.count_nonzero(mb) == \
        np.count_nonzero(ma)
    np.testing.assert_allclose(mb, ma * factor, rtol=1e-8)
    assert np.all(np.isfinite(image(new["res"])[1]))


def test_bright_galaxy_beyond_float32_synthesis(run_native, tmp_path):
    """Peak ~6e37: the original synthesis (|ln I| < 85) sets model
    pixels to 0 in single; the double model has none of those holes."""
    data = fits.getdata(GAL).astype(np.float64)
    path = scaled(tmp_path, factor=6e37 / data.max())
    ps, single = run(run_native, tmp_path, path, *FIT, prec="single")
    pd_, double = run(run_native, tmp_path, path, *FIT)
    assert pd_.returncode == 0, pd_.stderr
    ms, md = image(single["model"])[1], image(double["model"])[1]
    holes = (ms == 0) & (md > 0)
    assert "set to 0" in ps.stdout and holes.sum() > 0      # single
    assert "set to 0" not in pd_.stdout
    assert np.all(md > 0)


def test_model_near_the_double_maximum(run_native, tmp_path):
    """Peak at 0.9 x DBL_MAX: either a finite model, or a clear model
    range error; never Inf or NaN in a product."""
    data = fits.getdata(GAL).astype(np.float64)
    path = scaled(tmp_path, factor=0.9 * np.finfo(float).max / data.max())
    p, out = run(run_native, tmp_path, path, *FIT)
    if p.returncode == 0:
        for k in ("model", "res"):
            assert np.all(np.isfinite(image(out[k])[1]))
    else:
        assert "error (double precision, model)" in p.stderr or \
            "error (double precision, residual)" in p.stderr


def test_csv_and_dat_hold_the_full_range(run_native, tmp_path):
    """Values near +-1e+-300: written with E and 3-digit exponents,
    never '*', and the CSV equals the .dat exactly."""
    for factor in (1e300, 1e-300):
        path = scaled(tmp_path, factor=factor)
        # LINEAR with the sky over-subtracted: negative outer I0
        data = fits.getdata(path)
        # 1.5 x the galaxy on its major axis (PA 55 deg) at a = 70
        sky = 1.5 * float(data[int(99.6 + 70 * np.sin(np.radians(55))),
                               int(100.3 + 70 * np.cos(np.radians(55)))])
        p, out = run(run_native, tmp_path, path, *FIT, "LINEAR",
                     "--sky", repr(sky))
        assert p.returncode == 0, p.stderr
        n, dat = read_dat(out["dat"])
        csvtext = open(out["csv"]).read()
        assert "*" not in csvtext.replace("2**(-k)", "")
        assert "*" not in open(out["dat"]).read()
        assert "# Precision: double (IEEE-754 binary64)" in csvtext
        assert re.search(r"# Normalization: k=-?\d+ preferred=-?\d+ "
                         r"clamped=(yes|no)", csvtext)
        df = pd.read_csv(out["csv"], comment="#", header=None,
                         names=COLS, skipinitialspace=True,
                         float_precision="round_trip")
        assert np.array_equal(df.to_numpy(), dat[:n, :11], equal_nan=True)
        assert (dat[:n, 3] < 0).any() and (dat[:n, 3] > 0).any()


def test_double_vs_single_products_on_normal_data(run_native, tmp_path):
    ps, s = run(run_native, tmp_path, GAL, *FIT, prec="single")
    pd_, d = run(run_native, tmp_path, GAL, *FIT)
    assert ps.returncode == 0 and pd_.returncode == 0
    ms, md = image(s["model"])[1], image(d["model"])[1]
    good = md > 1e-3 * md.max()
    assert np.abs(ms[good] / md[good] - 1).max() < 1e-4
    rs, rd = image(s["res"])[1], image(d["res"])[1]
    assert np.abs(rs - rd).max() < 1e-4 * md.max()
    # regions: same ellipses to the printed precision (4 decimals)
    a = open(s["reg"]).read().splitlines()
    b = open(d["reg"]).read().splitlines()
    assert a[:3] == b[:3] and len(a) == len(b)
