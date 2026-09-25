"""Synthetic regression: known truth, and stability against baselines.

Truth checks use contours with 5 <= Rmaj <= 0.8 * R1 (ELLIPROF samples
by bilinear interpolation, which is least accurate on the steep centre
of an r^(1/4) profile).  Limits were set from measured recovery on the
noise-free images with a margin of ~3-5x (see TEST_PLAN.md).
"""

import json

import numpy as np
import pytest
from astropy.io import fits

from cases import BASELINE, CASES, image_path, run_kwargs
from runner import (csv_rows, parse_dvfit, platform_id, run_case,
                    same_platform)
from elliprof.profile import COLUMNS, read_profile
from elliprof.regions import read_ds9_regions

pytestmark = pytest.mark.native

TOL = dict(center=0.05, ellip=0.015, pa=0.5, i0=0.01, dv=0.03)
NOISY = dict(center=0.5, ellip=0.02, pa=2.0, i0=0.03, dv=0.05)


@pytest.fixture(scope="module")
def runs(tmp_path_factory):
    out = tmp_path_factory.mktemp("regression")
    cache = {}

    def get(name):
        if name not in cache:
            run_case(name, image_path(name), run_kwargs(name), out / name)
            cache[name] = out / name
        return cache[name]
    return get


def truth_subset(name, prof):
    t = CASES[name]["truth"]
    r1 = run_kwargs(name)["r1"]
    sel = (prof.Rmaj >= 5) & (prof.Rmaj <= 0.8 * r1)
    return t, prof[sel]


@pytest.mark.parametrize("name", [n for n in CASES
                                  if n not in ("star_nomask",)])
def test_recovers_truth(name, runs):
    d = runs(name)
    prof = read_profile(str(d / "profile.prf"))
    assert len(prof) == run_kwargs(name)["nr"]
    assert not prof.isna().any().any()
    t, q = truth_subset(name, prof)
    tol = NOISY if "noise" in t else TOL
    assert np.abs(q.x0 - t["x0"]).max() < tol["center"]
    assert np.abs(q.y0 - t["y0"]).max() < tol["center"]
    assert np.abs(q.ellip - (1 - t["q"])).max() < tol["ellip"]
    if t["q"] < 1:
        # stored alpha = major-axis angle - 90 (mod 180)
        err = ((q.alpha + 90 - t["pa"] + 90) % 180) - 90
        assert np.abs(err).max() < tol["pa"]
    model = t["ie"] * np.exp(-7.669 * ((q.Rmaj / t["re"]) ** 0.25 - 1))
    assert np.abs(q.I0 / model - 1).max() < tol["i0"]
    dv = json.loads((d / "meta.json").read_text())["dvfit"]
    assert dv["re"][0] == pytest.approx(t["re"], rel=tol["dv"])
    assert dv["ie"][0] == pytest.approx(t["ie"], rel=tol["dv"])
    # minor-axis Re = q * Re for an r^(1/4) law with constant q
    assert dv["re"][1] == pytest.approx(t["q"] * t["re"], rel=tol["dv"])


def test_sky_image_equals_constant_equivalent(runs):
    """Subtracting the exact sky image recovers the galaxy as well as a
    constant sky does for the constant-sky image."""
    a = read_profile(str(runs("sky_image") / "profile.prf"))
    b = read_profile(str(runs("const_sky") / "profile.prf"))
    # A3/A4 are phases of ~zero-amplitude terms here, i.e. noise
    cols = ["Rmaj", "x0", "y0", "I0", "alpha", "ellip", "slope"]
    np.testing.assert_allclose(a[cols].to_numpy(), b[cols].to_numpy(),
                               rtol=2e-4, atol=2e-3)
    np.testing.assert_allclose(a[["I3", "I4"]], b[["I3", "I4"]], atol=1e-4)


def test_mask_removes_the_star(runs):
    t = CASES["star_mask"]["truth"]
    masked = read_profile(str(runs("star_mask") / "profile.prf"))
    raw = read_profile(str(runs("star_nomask") / "profile.prf"))
    clean = read_profile(str(runs("const_sky") / "profile.prf"))

    def worst(p):
        sel = p.Rmaj >= 5
        model = t["ie"] * np.exp(-7.669 * ((p.Rmaj[sel] / t["re"]) ** 0.25
                                           - 1))
        return float(np.abs(p.I0[sel] / model - 1).max())
    assert worst(raw) > 3 * worst(masked)
    assert worst(masked) < 0.01
    # with the star masked, every contour matches the star-free galaxy
    np.testing.assert_allclose(masked.I0, clean.I0, rtol=2e-3)
    dv_masked = parse_dvfit((runs("star_mask") / "stdout.txt").read_text())
    dv_raw = parse_dvfit((runs("star_nomask") / "stdout.txt").read_text())
    assert abs(dv_masked["ie"][0] - t["ie"]) < abs(dv_raw["ie"][0] - t["ie"])




def test_model_image(runs):
    t = CASES["model"]["truth"]
    model = fits.getdata(runs("model") / "model.fits")
    j, i = np.indices(model.shape)
    x, y = i + 0.5, j + 0.5
    c, s = np.cos(np.radians(t["pa"])), np.sin(np.radians(t["pa"]))
    u = (x - t["x0"]) * c + (y - t["y0"]) * s
    v = -(x - t["x0"]) * s + (y - t["y0"]) * c
    r = np.sqrt(u ** 2 + (v / t["q"]) ** 2)
    truth = t["ie"] * np.exp(-7.669 * ((r / t["re"]) ** 0.25 - 1))
    sel = (r > 5) & (r < 60)
    assert np.abs(model[sel] / truth[sel] - 1).max() < 0.02


def test_outputs_are_consistent(runs):
    for name in CASES:
        d = runs(name)
        n = len(read_profile(str(d / "profile.prf")))
        assert len(csv_rows(d / "profile.csv")) == n
        assert len(read_ds9_regions(d / "profile.reg")) == n


# --- baselines -------------------------------------------------------------

def _compare_with_tolerance(ref, new):
    tol = json.loads((BASELINE.parent / "tolerances.json").read_text())
    a = read_profile(str(ref / "profile.prf"))
    b = read_profile(str(new / "profile.prf"))
    assert len(a) == len(b)
    for col in COLUMNS:
        x, y = a[col].to_numpy(), b[col].to_numpy()
        keep = np.ones(len(x), bool)
        if col in ("A3", "A4"):
            amp = a["I3" if col == "A3" else "I4"].to_numpy()
            keep &= amp > tol["min_amplitude"]
        if col == "alpha":
            keep &= a["ellip"].to_numpy() > tol["min_ellip"]
        lim = tol["columns"][col]
        d = np.abs(x - y)[keep]
        if col in ("A3", "A4"):
            period = 120.0 if col == "A3" else 90.0
            d = np.minimum(d, period - d)
        ok = (d <= lim["abs"]) | (d <= lim["rel"] * np.abs(x[keep]))
        if not ok.all():
            msg = f"{col}: max difference {d.max():g} from the baseline"
            if tol["_status"].startswith("PROVISIONAL"):
                # tolerances are not set yet: report, do not fail
                pytest.xfail(msg + " exceeds the provisional tolerance")
            raise AssertionError(msg)


@pytest.mark.parametrize("name", list(CASES))
def test_matches_baseline(name, runs):
    ref = BASELINE / name
    if not (ref / "profile.prf").exists():
        pytest.skip("no baseline yet (make update-baselines)")
    new = runs(name)
    meta = json.loads((ref / "meta.json").read_text())
    if same_platform(meta, platform_id()):
        # same OS, CPU and backend build: bit-for-bit
        assert (new / "profile.prf").read_bytes() == \
            (ref / "profile.prf").read_bytes()
        assert (new / "profile.reg").read_bytes() == \
            (ref / "profile.reg").read_bytes()
        assert csv_rows(new / "profile.csv") == csv_rows(ref / "profile.csv")
        new_meta = json.loads((new / "meta.json").read_text())
        assert new_meta.get("model_sha256") == meta.get("model_sha256")
    else:
        _compare_with_tolerance(ref, new)
