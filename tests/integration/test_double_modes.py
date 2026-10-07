"""Every ELLIPROF mode in the double backend, compared with the single
backend on well-conditioned data (they differ by float32 rounding
only), plus the harmonic modes, the 6th-order PA-wrap warning, and data
the single backend cannot fit: subnormal values and a galaxy below the
float32 resolution of its sky."""

import re

import numpy as np
import pytest

from helpers import DATA

fits = pytest.importorskip("astropy.io.fits")

GAL = DATA / "regression" / "rotated.fits"
STAR = DATA / "regression" / "star.fits"
FIT = ["X0=100.3", "Y0=99.6", "R0=3", "R1=80", "NR=25", "NITER=5"]


def read_dat(path):
    tok = open(path).read().split(None, 3002)
    n = int(tok[0])
    return np.array([float(t) for t in tok[2:3002]]).reshape(250, 12)[:n]


def both(run_native, tmp_path, image, *args, model=True):
    out = {}
    for prec in ("single", "double"):
        dat = tmp_path / f"{prec}.dat"
        extra = ["-m", tmp_path / f"{prec}.fits"] if model else []
        p = run_native(image, *args, "--precision", prec, "-o", dat,
                       *extra)
        assert p.returncode == 0, (prec, p.stderr)
        out[prec] = (read_dat(dat),
                     fits.getdata(tmp_path / f"{prec}.fits").astype(float)
                     if model else None, p)
    return out


def assert_close(out, xy=1e-3, rel=1e-4, model_rel=1e-3):
    (s, ms, _), (d, md, _) = out["single"], out["double"]
    # NaN exactly where the single backend has NaN (original behaviour,
    # e.g. the 6th-order amplitude of a tiny central isophote)
    assert np.array_equal(np.isfinite(d[:, :11]), np.isfinite(s[:, :11]))
    assert np.all(np.isfinite(d[:, :6]))
    # compare the well-defined isophotes (a NaN term marks a degenerate,
    # ill-conditioned fit: 6th order on a ring of ~11 samples)
    ok = np.isfinite(s[:, :11]).all(axis=1)
    s, d = s[ok], d[ok]
    assert np.abs(d[:, 1:3] - s[:, 1:3]).max() < xy
    assert np.abs(d[:, 3] / s[:, 3] - 1).max() < rel
    assert np.abs(d[:, 5] - s[:, 5]).max() < xy
    if md is not None:
        # NaN model pixels (original 6th-order limitation) must match;
        # the central pixels (r < 5) follow the ill-conditioned central
        # isophotes and are left out
        assert np.array_equal(np.isfinite(md), np.isfinite(ms))
        j, i = np.indices(md.shape)
        good = np.isfinite(md) & (np.hypot(i + 0.5 - 100.3,
                                           j + 0.5 - 99.6) >= 5)
        good &= np.abs(md) > 1e-3 * np.abs(md[good]).max()
        assert np.abs(ms[good] / md[good] - 1).max() < model_rel


@pytest.mark.parametrize("args", [
    [], ["RMSTAR"], ["AVG=1"], ["NITER=1"], ["NITER=10"], ["TIE=3"],
    ["TIE=-3"], ["FIXCTR=1"], ["GAIN=0.5"], ["RLAW=0"], ["RLAW=1"],
    ["ELLIP=0.4"], ["SKY=10"], ["SCALE=0.5"],
    ["COS3X=-3"], ["COS3X=-2"], ["COS3X=-1"], ["COS3X=0"], ["COS3X=1"],
    ["COS3X=2", "COS4X=0"], ["COS3X=2", "COS4X=1"],
], ids=lambda a: "_".join(a) or "default")
def test_mode_agrees_with_single(run_native, tmp_path, args):
    assert_close(both(run_native, tmp_path, GAL, *FIT, *args))


def test_linear_agrees_with_single(run_native, tmp_path):
    assert_close(both(run_native, tmp_path, GAL, *FIT, "LINEAR"),
                 rel=1e-3)


@pytest.mark.parametrize("convention", ["nonzero-good", "zero-good"])
def test_masks_agree_with_single(run_native, tmp_path, convention):
    mask = DATA / "regression" / "star.dmask"
    if convention == "zero-good":
        from elliprof.masks import load_mask
        good = load_mask(str(mask)).astype(bool)
        fits.PrimaryHDU((~good).astype(np.int16)).writeto(
            tmp_path / "zg.fits")
        mask = tmp_path / "zg.fits"
    out = both(run_native, tmp_path, STAR, *FIT, "--mask", mask,
               "--mask-convention", convention)
    assert_close(out)


def test_sky_scalar_and_image_agree_with_single(run_native, tmp_path):
    assert_close(both(run_native, tmp_path,
                      DATA / "regression" / "const_sky.fits", *FIT,
                      "--sky", "250"))
    assert_close(both(run_native, tmp_path,
                      DATA / "regression" / "sky_image.fits", *FIT,
                      "--sky-image",
                      DATA / "regression" / "sky_image_sky.fits"))


def test_sixth_order_and_pa_wrap_warning_in_double(run_native, tmp_path):
    from test_harmonic_recovery import K, TWIST, galaxy, shape
    img, _, _ = galaxy(6, K, twist=TWIST)
    fits.PrimaryHDU(img.astype(np.float64)).writeto(tmp_path / "t.fits")
    fit6 = ["X0=120.3", "Y0=119.6", "R0=6", "R1=90", "NR=15",
            "NITER=10"]
    p = run_native(tmp_path / "t.fits", *fit6, "COS3X=-2", "-o",
                   tmp_path / "t.dat", "-m", tmp_path / "t_m.fits")
    assert p.returncode == 0 and "Precision: double" in p.stdout
    m = re.search(r"warning: the fitted PA wraps across 0/180 deg at "
                  r"isophote (\d+) \(Rmaj = ([\d.]+)\)", p.stderr)
    assert m and 50 < float(m.group(2)) < 80
    prm = read_dat(tmp_path / "t.dat")
    wrap = int(np.argmax(np.abs(np.diff(prm[:, 4])) > 90)) + 1
    a6 = shape(prm, 6)
    assert np.all(np.abs(a6[4:wrap] - K) < 0.001)
    assert np.all(np.abs(a6[wrap:-1] - K) < 0.001)
    p = run_native(tmp_path / "t.fits", *fit6, "COS3X=-3", "-o",
                   tmp_path / "u.dat", "-m", tmp_path / "u_m.fits")
    assert p.returncode == 0 and "wraps across" not in p.stderr


def test_subnormal_galaxy(run_native, tmp_path):
    """A galaxy stored as float64 subnormals (values ~1e-316): read,
    normalized up exactly, fitted; geometry as for the normal galaxy
    to the precision the subnormals hold (~14 bits)."""
    data = fits.getdata(GAL).astype(np.float64)
    fits.PrimaryHDU(np.ldexp(data, -1060)).writeto(tmp_path / "s.fits")
    p = run_native(tmp_path / "s.fits", *FIT, "-o", tmp_path / "s.dat")
    assert p.returncode == 0, p.stderr
    assert "Precision: double" in p.stdout and "nonzero value(s) that " \
        "are 0 in float32" in p.stdout or "BITPIX -64" in p.stdout
    p = run_native(GAL, *FIT, "--precision", "double", "-o",
                   tmp_path / "r.dat")
    s, r = read_dat(tmp_path / "s.dat"), read_dat(tmp_path / "r.dat")
    assert np.abs(s[:, 1:3] - r[:, 1:3]).max() < 0.01
    assert np.abs(s[:, 5] - r[:, 5]).max() < 0.01
    np.testing.assert_allclose(s[:, 3], np.ldexp(r[:, 3], -1060),
                               rtol=1e-3)


def test_galaxy_below_the_float32_resolution_of_the_sky(run_native,
                                                        tmp_path):
    """Sky 1e9 (float32 spacing there: 64) under a galaxy of 1..6e5:
    double recovers the galaxy as without the sky; single cannot."""
    data = fits.getdata(GAL).astype(np.float64)
    fits.PrimaryHDU(data + 1e9).writeto(tmp_path / "c.fits")
    ref = tmp_path / "r.dat"
    run_native(GAL, *FIT, "--precision", "double", "-o", ref)
    p = run_native(tmp_path / "c.fits", *FIT, "--sky", "1e9", "-o",
                   tmp_path / "d.dat")
    assert p.returncode == 0 and "Precision: double" in p.stdout
    p = run_native(tmp_path / "c.fits", *FIT, "--sky", "1e9",
                   "--precision", "single", "-o", tmp_path / "s.dat")
    r, d = read_dat(ref), read_dat(tmp_path / "d.dat")
    np.testing.assert_allclose(d[:, :11], r[:, :11], rtol=1e-9,
                               atol=1e-6)
    if p.returncode == 0:
        s = read_dat(tmp_path / "s.dat")
        outer = slice(15, None)
        assert np.nanmax(np.abs(s[outer, 3] / r[outer, 3] - 1)) > 1e-2


def test_values_single_refuses_are_fitted(run_native, tmp_path):
    """1e40 in a 64-bit image: CFITSIO status 412 in single; auto and
    double fit it, with no float32-only message."""
    data = fits.getdata(GAL).astype(np.float64) * 1e35
    fits.PrimaryHDU(data).writeto(tmp_path / "h.fits")
    p = run_native(tmp_path / "h.fits", *FIT, "-o", tmp_path / "h.dat")
    assert p.returncode == 0, p.stderr
    for text in ("CFITSIO status", "converted to 32-bit", "set to 0"):
        assert text not in p.stdout + p.stderr
    p = run_native(tmp_path / "h.fits", *FIT, "--precision", "single",
                   "-o", tmp_path / "s.dat")
    assert p.returncode != 0 and "CFITSIO status" in p.stderr
