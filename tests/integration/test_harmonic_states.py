"""Every harmonic state, run through the backend, the Python API and the
CLI.  The reference is the original ELLIPROF itself: the backend given
the raw COS3X=/COS4X= keywords."""

import subprocess

import numpy as np
import pytest

from elliprof import cli, read_prf, run_elliprof
from helpers import ROOT, read_fits

IMAGE = ROOT / "tests" / "data" / "regression" / "star.fits"
FIT = ["X0=100.3", "Y0=99.6", "R0=3", "R1=80", "NR=25", "NITER=5",
       "MODEL"]

# name: (API/CLI options, CLI arguments, COS3X, COS4X)
STATES = {
    "default":     ({}, [], None, None),
    "none":        ({"model_harmonics": "none"},
                    ["--model-harmonics", "none"], 0, 0),
    "3":           ({"model_harmonics": (3,)},
                    ["--model-harmonics", "3"], 2, 0),
    "4":           ({"model_harmonics": (4,)},
                    ["--model-harmonics", "4"], 0, 2),
    "3,4":         ({"model_harmonics": (3, 4)},
                    ["--model-harmonics", "3,4"], 2, 2),
    "3,4 median":  ({"model_harmonics": (3, 4), "harmonic_mode": "median"},
                    ["--model-harmonics", "3,4", "--harmonic-mode",
                     "median"], 1, 1),
    "4 median":    ({"model_harmonics": (4,), "harmonic_mode": "median"},
                    ["--model-harmonics", "4", "--harmonic-mode", "median"],
                    0, 1),
    "6th":         ({"sixth_order": True}, ["--sixth-order"], -2, 2),
    "6th median":  ({"sixth_order": True, "harmonic_mode": "median"},
                    ["--sixth-order", "--harmonic-mode", "median"], -1, 1),
}


def _raw(cos3x, cos4x):
    return [f"{k}={v}" for k, v in (("COS3X", cos3x), ("COS4X", cos4x))
            if v is not None]


@pytest.fixture(scope="module")
def runs(native, tmp_path_factory):
    """Each state three ways: raw keywords to the backend, API, CLI."""
    out = {}
    for name, (opts, args, c3, c4) in STATES.items():
        d = tmp_path_factory.mktemp("h" + str(len(out)))
        ref = subprocess.run(
            [str(native), str(IMAGE), *FIT, *_raw(c3, c4),
             "-o", str(d / "ref.prf"), "-m", str(d / "ref.fits")],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True)
        assert ref.returncode == 0, ref.stderr
        api = run_elliprof(IMAGE, 100.3, 99.6, r0=3, r1=80, nr=25, niter=5,
                           model=True, output_dir=d / "api", **opts)
        code = cli.main([str(IMAGE), *FIT, *args,
                         "-o", str(d / "cli.prf"), "-m", str(d / "cli.fits"),
                         "--csv", str(d / "cli.csv")])
        assert code == 0
        out[name] = dict(dir=d, api=api, c3=c3, c4=c4)
    return out


def _fit(path):
    p = read_prf(str(path))
    return np.asarray(p["params"])[:p["n"], :11]


def _flag15(path):
    return np.asarray(read_prf(str(path))["params"])[14, 11]


@pytest.mark.parametrize("name", list(STATES))
def test_keywords_reach_backend(runs, name):
    r = runs[name]
    raw = _raw(r["c3"], r["c4"])
    assert [w for w in r["api"].command if w.startswith("COS")] == raw
    params = [l for l in open(r["dir"] / "cli.csv")
              if l.startswith("# Parameters:")][0]
    for w in raw:
        assert w in params.split()
    if r["c3"] is None:
        assert not any(w.startswith("COS") for w in params.split())
    # ELLIPROF stores COS3X in the profile's run flags (default 2)
    c3 = 2 if r["c3"] is None else r["c3"]
    assert _flag15(r["dir"] / "ref.prf") == c3


@pytest.mark.parametrize("name", list(STATES))
def test_api_and_cli_match_the_original_backend(runs, name):
    r = runs[name]
    d = r["dir"]
    ref = (d / "ref.prf").read_bytes()
    assert r["api"].prf_path.read_bytes() == ref
    assert (d / "cli.prf").read_bytes() == ref
    # equal_nan: the original code leaves a few NaN pixels at the very
    # centre of the 6th-order "each" model; they must match too
    model = read_fits(d / "ref.fits")
    assert np.array_equal(read_fits(r["api"].model_path), model,
                          equal_nan=True)
    assert np.array_equal(read_fits(d / "cli.fits"), model, equal_nan=True)
    assert len(r["api"].profile) == 25
    assert list(r["api"].profile.columns[:11]) == [
        "Rmaj", "x0", "y0", "I0", "alpha", "ellip", "I3", "A3", "I4", "A4",
        "slope"]


@pytest.mark.parametrize("name", [n for n in STATES if "6th" not in n])
def test_model_harmonics_do_not_change_the_fit(runs, name):
    """COS3X >= 0 and COS4X only shape the model image: the fitted
    profile is identical to the default one."""
    assert np.array_equal(_fit(runs[name]["dir"] / "ref.prf"),
                          _fit(runs["default"]["dir"] / "ref.prf"))


def test_model_images_follow_the_harmonic_setting(runs):
    m = {n: read_fits(runs[n]["dir"] / "ref.fits") for n in STATES}
    assert np.array_equal(m["3,4"], m["default"])      # default is 3,4 each
    distinct = ["none", "3", "4", "3,4", "3,4 median", "4 median", "6th",
                "6th median"]
    for i, a in enumerate(distinct):
        for b in distinct[i + 1:]:
            assert not np.array_equal(m[a], m[b]), (a, b)


def test_model_harmonic_terms_add_up(runs):
    """In the model, each included term multiplies the harmonic-free
    image by (1 + its correction), so (3,4) = (3) * (4) / none, up to
    rounding -- the terms are really added, not just labelled."""
    m = {n: read_fits(runs[n]["dir"] / "ref.fits").astype(float)
         for n in ("none", "3", "4", "3,4")}
    ok = m["none"] > 0
    c3 = m["3"][ok] / m["none"][ok] - 1
    c4 = m["4"][ok] / m["none"][ok] - 1
    both = m["3,4"][ok] / m["none"][ok] - 1
    assert np.abs(c3).max() > 1e-3 and np.abs(c4).max() > 1e-3
    np.testing.assert_allclose(both, c3 + c4, atol=1e-5)


def test_sixth_order_changes_the_fit(runs):
    default = _fit(runs["default"]["dir"] / "ref.prf")
    sixth = _fit(runs["6th"]["dir"] / "ref.prf")
    assert not np.array_equal(sixth[:, 6:8], default[:, 6:8])   # I3, A3
    assert np.all((sixth[:, 7] >= 0) & (sixth[:, 7] < 120))
    # the median mode only changes the model, not the 6th-order fit
    assert np.array_equal(_fit(runs["6th median"]["dir"] / "ref.prf"),
                          sixth)


@pytest.mark.parametrize("word,message", [
    ("COS3X=3", "COS3X must be an integer from -2 to 2"),
    ("COS4X=-1", "COS4X must be an integer from 0 to 2"),
    ("COS3X=1.5", "COS3X must be an integer from -2 to 2"),
])
def test_backend_rejects_other_values(native, tmp_path, word, message):
    proc = subprocess.run([str(native), str(IMAGE), *FIT[:5], word,
                           "-o", str(tmp_path / "x.prf")],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)
    assert proc.returncode == 1 and message in proc.stderr


def test_cli_rejects_mixed_and_invalid(tmp_path, capsys):
    base = [str(IMAGE), *FIT, "-o", str(tmp_path / "x.prf")]
    assert cli.main(base + ["--model-harmonics", "5"]) == 1
    assert cli.main(base + ["COS3X=1", "--model-harmonics", "3"]) == 1
    assert cli.main(base + ["--sixth-order", "--model-harmonics", "4"]) == 1
    err = capsys.readouterr().err
    assert "model harmonics must be" in err
    assert "given twice" in err
    assert "6th-order term takes the place" in err
    assert not (tmp_path / "x.prf").exists()
