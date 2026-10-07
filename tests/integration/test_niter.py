"""The iteration count: ELLIPROF's NITER (0.1.4 adds --niter).

NITER is the number of passes of the isophote fit (src/original/
elliprof.f, FITPROFILE: ``do 100 n = 1,niter``).  Its default, 5, is
ELLIPROF's own (``niter = 5`` for every new fit) and is unchanged.
--niter N is only another spelling of NITER=N.  ELLIPROF's other loops
(DVFIT, the de Vaucouleurs fit printed at the end) do not affect the
profile and are not parameters."""

import re

import numpy as np
import pytest

from elliprof import read_prf, run_elliprof
from elliprof.core import DEFAULT_NITER
from helpers import ROOT, run_cli

IMAGE = ROOT / "tests" / "data" / "regression" / "noisy.fits"
FIT = ["X0=100.3", "Y0=99.6", "R0=3", "R1=80", "NR=25", "--sky", "50"]


def cli(*args, cwd=None):
    """The user-facing command, as a separate process."""
    return run_cli(*args, cwd=cwd)


def iterations(stdout):
    """With the VERBOSE keyword, ELLIPROF prints its starting table and
    then one table per iteration: count them."""
    return len(re.findall(r"^\s+r\s+x0\s+y0\s+I0\s+alpha", stdout,
                          re.M)) - 1


def test_default_is_five_from_the_source():
    src = (ROOT / "src" / "original" / "elliprof.f").read_text()
    assert re.search(r"^\s+niter = 5\s*$", src, re.M)
    assert DEFAULT_NITER == 5


def test_default_equals_explicit_five(tmp_path):
    runs = {"default": [], "NITER=5": ["NITER=5"],
            "--niter 5": ["--niter", "5"]}
    out = {}
    for name, extra in runs.items():
        f = tmp_path / (name.replace(" ", "_").replace("=", "") + ".dat")
        p = cli(IMAGE, *FIT, *extra, "-o", f, "-m", f.with_suffix(".prf"))
        assert p.returncode == 0, p.stderr
        out[name] = (f.read_bytes(), f.with_suffix(".prf").read_bytes())
    assert out["default"] == out["NITER=5"] == out["--niter 5"]


@pytest.mark.parametrize("n", [1, 3, 12])
def test_value_reaches_the_backend(tmp_path, n):
    """The backend runs exactly N passes, and the profile records it."""
    a = cli(IMAGE, *FIT, f"NITER={n}", "VERBOSE", "-o", tmp_path / "a.dat")
    b = cli(IMAGE, *FIT, "--niter", n, "VERBOSE", "-o", tmp_path / "b.dat")
    assert a.returncode == b.returncode == 0, a.stderr + b.stderr
    assert iterations(a.stdout) == iterations(b.stdout) == n
    assert (tmp_path / "a.dat").read_bytes() == \
        (tmp_path / "b.dat").read_bytes()
    # the run settings (column 12 of PARAM_PRF) record NITER as flag 6
    params = np.asarray(read_prf(str(tmp_path / "a.dat"))["params"])
    assert params[5, 11] == n


def test_default_runs_five_passes():
    p = cli(IMAGE, *FIT, "VERBOSE")
    assert p.returncode == 0, p.stderr
    assert iterations(p.stdout) == 5


def test_non_default_values_change_the_fit(tmp_path):
    res = {}
    for n in (1, 5, 12):
        f = tmp_path / f"n{n}.dat"
        assert cli(IMAGE, *FIT, "--niter", n, "-o", f).returncode == 0
        res[n] = np.asarray(read_prf(str(f))["params"])[:25, :11]
    assert not np.array_equal(res[1], res[5])
    assert not np.array_equal(res[12], res[5])


def test_api_niter(tmp_path):
    kw = dict(r0=3, r1=80, nr=25, sky=50, load_profile=False,
              output_dir=tmp_path)
    a = run_elliprof(IMAGE, 100.3, 99.6, prf_path=tmp_path / "a.dat", **kw)
    b = run_elliprof(IMAGE, 100.3, 99.6, niter=5,
                     prf_path=tmp_path / "b.dat", **kw)
    assert a.ok and b.ok
    assert (tmp_path / "a.dat").read_bytes() == \
        (tmp_path / "b.dat").read_bytes()
    assert "NITER=5" in b.command


@pytest.mark.parametrize("args, msg", [
    (["NITER=5", "--niter", "5"], "give the iteration count once"),
    (["--niter", "0"], "NITER must be an integer between 1 and 1000"),
    (["--niter", "1001"], "NITER must be an integer between 1 and 1000"),
    (["--niter", "2.5"], "NITER must be an integer between 1 and 1000"),
])
def test_bad_values(args, msg):
    p = cli(IMAGE, *FIT, *args)
    assert p.returncode in (1, 2) and msg in p.stderr, p.stderr
