"""Harmonic analysis on controlled synthetic galaxies (0.1.4).

Each image is an r^(1/4) galaxy whose isophotes are distorted radially as
r(E) = a (1 + k cos(n E)), E the eccentric angle from the major axis.
To first order this puts an intensity term I_n cos(n (theta - A_n)) on
every ellipse with I_n cos(n A_n) / (-slope) = k (the conversion in
docs/concepts/harmonics.md), so the injected k is recovered from the
profile.  The images are built analytically for each test, so they are
the same on every platform.

Tolerances (k = 0.02):
* recovered k within 0.001 (5%): sampling the ellipse at discrete
  points and the finite-difference slope; the observed error is < 0.0002;
* cross-talk: any other order's amplitude below 5% of the injected one
  (observed < 1%);
* model subtraction: an included term removes at least 95% of that
  harmonic from the residual at intermediate radii (observed ~99%).
"""

import re

import numpy as np
import pytest

from elliprof import read_prf
from helpers import run_cli

fits = pytest.importorskip("astropy.io.fits")

X0, Y0, SIZE = 120.3, 119.6, 241
FIT = ["X0=120.3", "Y0=119.6", "R0=6", "R1=90", "NR=15", "NITER=10"]
K = 0.02
MID = slice(4, 12)          # intermediate isophotes, away from R0 and R1


def galaxy(n=0, k=0.0, pa=120.0, q=0.7, twist=None):
    """The synthetic image (float32) plus the analytic (E, rho) grid.
    pa: major axis in degrees CCW from +x; twist=(pa0, pa1) turns it
    from pa0 at r = 10 to pa1 at r = 90."""
    j, i = np.indices((SIZE, SIZE), dtype=np.float64)
    x, y = i + 0.5 - X0, j + 0.5 - Y0
    if twist:
        frac = np.clip((np.hypot(x, y) - 10) / 80, 0, 1)
        t = np.radians(twist[0] + (twist[1] - twist[0]) * frac)
    else:
        t = np.radians(pa)
    u = x * np.cos(t) + y * np.sin(t)
    v = -x * np.sin(t) + y * np.cos(t)
    rho = np.hypot(u, v / q)
    e = np.arctan2(v / q, u)
    r = rho / (1 + k * np.cos(n * e)) if n else rho
    img = 500.0 * np.exp(-7.669 * ((np.maximum(r, 0.5) / 25.0) ** 0.25 - 1))
    return img.astype(np.float32), e, rho


def fit(tmp_path, img, *args, name="g"):
    f = tmp_path / f"{name}.fits"
    if not f.exists():
        fits.PrimaryHDU(img).writeto(f)
    out = tmp_path / f"{name}{len(list(tmp_path.iterdir()))}"
    p = run_cli(f, *FIT, *args, "-o", f"{out}.dat", "-m", f"{out}_m.fits",
                "--residual", f"{out}_r.fits")
    assert p.returncode == 0, p.stderr
    prf = read_prf(f"{out}.dat")
    return (np.asarray(prf["params"])[:prf["n"], :11],
            fits.getdata(f"{out}_r.fits"), p)


def shape(params, order):
    """a_n/a = I cos(m A) / (-slope); for the 6th order the I3/A3 columns
    hold it, with A3 = 2 x the 6th-order phase, so m A = 3 A3."""
    i, a = (params[:, 8], params[:, 9]) if order == 4 else \
        (params[:, 6], params[:, 7])
    m = 4 if order == 4 else 3
    return i * np.cos(np.radians(m * a)) / -params[:, 10]


def component(img, e, rho, n, lo, hi):
    """Least-squares cos(nE) coefficient of an image in an elliptical
    ring (the injected pattern is a pure cosine)."""
    m = (rho >= lo) & (rho < hi) & np.isfinite(img)
    return np.sum(img[m] * np.cos(n * e[m])) / np.sum(np.cos(n * e[m]) ** 2)


# ---- recovery and cross-talk

def test_pure_ellipse_has_no_harmonics(tmp_path):
    img, _, _ = galaxy()
    for c3 in ("COS3X=2", "COS3X=-3"):
        p, _, _ = fit(tmp_path, img, c3)
        assert np.abs(p[MID, 6]).max() < 1e-3        # I3 (or I6)
        assert np.abs(p[MID, 8]).max() < 1e-3        # I4


@pytest.mark.parametrize("n, c3", [(3, "COS3X=2"), (4, "COS3X=2"),
                                   (6, "COS3X=-2")])
def test_injected_order_is_recovered(tmp_path, n, c3):
    img, _, _ = galaxy(n, K)
    p, _, _ = fit(tmp_path, img, c3)
    assert np.abs(np.median(shape(p[MID], n)) - K) < 0.001
    mine = p[MID, 8] if n == 4 else p[MID, 6]
    other = p[MID, 6] if n == 4 else p[MID, 8]
    assert np.median(mine) > 0.03                    # ~ k x |slope|
    assert np.abs(other).max() < 0.05 * np.median(mine)


@pytest.mark.parametrize("n, c3", [(6, "COS3X=2"), (3, "COS3X=-2")])
def test_orders_do_not_leak(tmp_path, n, c3):
    """A 6th-order pattern is invisible to the 3rd-order fit and vice
    versa (the I3 column holds whichever order is measured)."""
    img, _, _ = galaxy(n, K)
    p, _, _ = fit(tmp_path, img, c3)
    assert np.abs(p[MID, 6]).max() < 0.05 * 0.04
    assert np.abs(p[MID, 8]).max() < 0.05 * 0.04


@pytest.mark.parametrize("n, include, exclude", [
    (3, ["COS3X=2"], ["COS3X=0"]),
    (4, ["COS4X=2"], ["COS4X=0"]),
    (6, ["COS3X=-2"], ["COS3X=-3"]),
])
def test_model_term_removes_the_harmonic(tmp_path, n, include, exclude):
    img, e, rho = galaxy(n, K)
    _, res_in, _ = fit(tmp_path, img, *include)
    _, res_out, _ = fit(tmp_path, img, *exclude)
    for lo, hi in ((15, 25), (30, 45), (50, 70)):
        before = component(res_out, e, rho, n, lo, hi)
        after = component(res_in, e, rho, n, lo, hi)
        assert abs(before) > 1
        assert abs(after) < 0.05 * abs(before), (lo, hi, before, after)


# ---- modern and legacy syntax: identical runs

@pytest.mark.parametrize("modern, legacy", [
    ([], ["COS3X=2", "COS4X=2"]),
    (["--model-harmonics", "none"], ["COS3X=0", "COS4X=0"]),
    (["--model-harmonics", "3"], ["COS3X=2", "COS4X=0"]),
    (["--model-harmonics", "4"], ["COS3X=0", "COS4X=2"]),
    (["--harmonic-mode", "median"], ["COS3X=1", "COS4X=1"]),
    (["--sixth-order"], ["COS3X=-2", "COS4X=2"]),
    (["--sixth-order", "--harmonic-mode", "median"], ["COS3X=-1", "COS4X=1"]),
    (["--sixth-order", "--model-harmonics", "none"], ["COS3X=-3", "COS4X=0"]),
    (["--sixth-order", "--model-harmonics", "4"], ["COS3X=-3", "COS4X=2"]),
    (["--sixth-order", "--model-harmonics", "6"], ["COS3X=-2", "COS4X=0"]),
    (["--model-harmonics", "3", "--harmonic-mode", "median"],
     ["COS3X=1", "COS4X=0"]),
    (["--model-harmonics", "4", "--harmonic-mode", "median"],
     ["COS3X=0", "COS4X=1"]),
    (["--sixth-order", "--model-harmonics", "6", "--harmonic-mode",
      "median"], ["COS3X=-1", "COS4X=0"]),
    (["--sixth-order", "--model-harmonics", "4", "--harmonic-mode",
      "median"], ["COS3X=-3", "COS4X=1"]),
])
def test_modern_equals_legacy(tmp_path, modern, legacy):
    """Profile values, model and residual pixels are identical (every pair
    in the "Exact equivalences" table of docs/concepts/harmonics.md)."""
    img, _, _ = galaxy(4, K)
    d = {}
    for tag, args in (("m", modern), ("l", legacy)):
        f = tmp_path / "g.fits"
        if not f.exists():
            fits.PrimaryHDU(img).writeto(f)
        p = run_cli(f, *FIT, *args, "-o", tmp_path / f"{tag}.dat",
                    "-m", tmp_path / f"{tag}.prf",
                    "--residual", tmp_path / f"{tag}_r.fits")
        assert p.returncode == 0, p.stderr
        d[tag] = (read_prf(str(tmp_path / f"{tag}.dat"))["params"],
                  fits.getdata(tmp_path / f"{tag}.prf"),
                  fits.getdata(tmp_path / f"{tag}_r.fits"))
    for a, b in zip(d["m"], d["l"]):
        assert np.array_equal(a, b, equal_nan=True)


# ---- the known 6th-order model limitation (original code)

TWIST = (80.0, 100.0)       # alpha from 170 to 6 deg: wraps at ~65 px


def test_sixth_order_model_warns_at_a_pa_wrap(tmp_path):
    img, _, _ = galaxy(6, K, twist=TWIST)
    for c3 in ("COS3X=-2", "COS3X=-1"):
        _, _, p = fit(tmp_path, img, c3, name="t")
        m = re.search(r"warning: the fitted PA wraps across 0/180 deg at "
                      r"isophote (\d+) \(Rmaj = ([\d.]+)\)", p.stderr)
        assert m, p.stderr
        assert 50 < float(m.group(2)) < 80
        assert "measurements are valid" in p.stderr and "COS3X=-3" in p.stderr
    # no warning: measured only, 3rd order, no model, or no wrap
    for args in (["COS3X=-3"], ["COS3X=2"], ["COS3X=0"]):
        _, _, p = fit(tmp_path, img, *args, name="t")
        assert "wraps across" not in p.stderr, args
    f = tmp_path / "t.fits"
    p = run_cli(f, *FIT, "COS3X=-2", "-o", tmp_path / "nomodel.dat")
    assert p.returncode == 0 and "wraps across" not in p.stderr
    straight, _, _ = galaxy(6, K)
    _, _, p = fit(tmp_path, straight, "COS3X=-2", name="s")
    assert "wraps across" not in p.stderr


def test_sixth_order_measurement_is_right_beyond_the_wrap(tmp_path):
    """The measured 6th-order profile is correct on both sides of the PA
    wrap; only the original model synthesis is affected.  The residual
    test documents that historical model behaviour (it changes if the
    synthesis is ever corrected)."""
    img, e, rho = galaxy(6, K, twist=TWIST)
    p, res, _ = fit(tmp_path, img, "COS3X=-2", name="t")
    alpha = p[:, 4]
    wrap = int(np.argmax(np.abs(np.diff(alpha)) > 90)) + 1
    assert 8 < wrap < 14
    a6 = shape(p, 6)
    assert np.all(np.abs(a6[4:wrap] - K) < 0.001)
    assert np.all(np.abs(a6[wrap:-1] - K) < 0.001)
    inside = component(res, e, rho, 6, 20, 40)
    beyond = component(res, e, rho, 6, 70, 90)
    science = component(img, e, rho, 6, 70, 90)
    assert abs(inside) < 0.05 * abs(component(img, e, rho, 6, 20, 40))
    assert beyond / science > 1.5        # wrong sign: not removed, doubled


def test_a3_jumps_by_60_degrees_at_a_pa_wrap(tmp_path):
    """A3 is measured from the end of the major axis at angle alpha; when
    alpha wraps, that end swaps and the same 3rd-order pattern shows a
    60 deg jump in A3.  A4 and the 6th-order phase do not jump."""
    img, _, _ = galaxy(3, K, twist=TWIST)
    p, _, _ = fit(tmp_path, img, "COS3X=2", name="t3")
    wrap = int(np.argmax(np.abs(np.diff(p[:, 4])) > 90)) + 1
    before, after = np.median(p[4:wrap, 7]), np.median(p[wrap:-1, 7])
    jump = (after - before) % 120
    assert min(abs(jump - 60), abs(jump + 60 - 120)) < 3
    img6, _, _ = galaxy(6, K, twist=TWIST)
    p6, _, _ = fit(tmp_path, img6, "COS3X=-3", name="t6")
    jump6 = (np.median(p6[wrap:-1, 7]) - np.median(p6[4:wrap, 7])) % 120
    assert min(jump6, 120 - jump6) < 3


def test_csv_says_when_i3_is_sixth_order(tmp_path):
    """The column names stay I3/A3; a header line marks 6th-order mode."""
    img, _, _ = galaxy(6, K)
    fits.PrimaryHDU(img).writeto(tmp_path / "g.fits")
    for c3, expect in (("COS3X=-3", True), ("COS3X=-2", True),
                       ("COS3X=2", False), ("COS3X=0", False)):
        p = run_cli(tmp_path / "g.fits", *FIT, c3, "--csv",
                    tmp_path / "p.csv")
        assert p.returncode == 0, p.stderr
        text = (tmp_path / "p.csv").read_text()
        assert ("# Harmonic order: 6" in text) == expect, c3
        assert "Rmaj, x0, y0, I0, alpha, ellip, I3, A3, I4, A4, slope" \
            in text
