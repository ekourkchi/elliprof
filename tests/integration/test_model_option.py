"""-m FILE alone computes and writes the model image (0.1.4).

Before 0.1.4 the model needed both the keyword MODEL and -m FILE; -m by
itself was ignored.  Now -m FILE is the whole request; a bare legacy
MODEL is accepted and has no effect, and MODEL=value is refused.  File
names are free: the traditional n1234.prf (model) / n1234.dat (profile)
names are just names."""

import subprocess

import numpy as np
import pytest

from elliprof import read_prf, run_elliprof
from helpers import ROOT, run_cli

fits = pytest.importorskip("astropy.io.fits")

IMAGE = ROOT / "tests" / "data" / "regression" / "elliptical.fits"
FIT = ["X0=100.3", "Y0=99.6", "R0=3", "R1=80", "NR=25"]


def cli(*args, cwd=None):
    """The user-facing command, as a separate process."""
    return run_cli(*args, cwd=cwd)


def native_run(native, *args):
    return subprocess.run([str(native), *map(str, args)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=600)


def test_joe_command_writes_dat_and_prf(tmp_path):
    """The traditional command: -o n1234.dat (text profile) and
    -m n1234.prf (FITS model), no MODEL keyword."""
    img = tmp_path / "n1234j.fits"
    img.write_bytes(IMAGE.read_bytes())
    p = cli("n1234j.fits", "RMSTAR", "X0=100.3", "Y0=99.6", "R0=3",
            "R1=80", "NR=25", "NITER=5", "-o", "n1234.dat",
            "-m", "n1234.prf", cwd=tmp_path)
    assert p.returncode == 0, p.stderr
    assert "MODEL" not in p.stderr
    assert sorted(f.name for f in tmp_path.iterdir()) == \
        ["n1234.dat", "n1234.prf", "n1234j.fits"]
    # n1234.prf is a FITS image of the science size; n1234.dat the text
    # profile
    with fits.open(tmp_path / "n1234.prf") as hdul:
        assert hdul[0].header["BITPIX"] == -32
        assert hdul[0].data.shape == fits.getdata(img).shape
        assert np.isfinite(hdul[0].data).all() and hdul[0].data.max() > 0
    assert read_prf(str(tmp_path / "n1234.dat"))["n"] == 25
    assert "Model:    n1234.prf" in p.stdout
    assert "Profile:  n1234.dat" in p.stdout


def test_m_alone_equals_legacy_model_and_m(native, tmp_path):
    a = native_run(native, IMAGE, *FIT, "-m", tmp_path / "model1.prf",
                   "-o", tmp_path / "a.dat")
    b = native_run(native, IMAGE, *FIT, "MODEL", "-m",
                   tmp_path / "model2.prf", "-o", tmp_path / "b.dat")
    assert a.returncode == b.returncode == 0, a.stderr + b.stderr
    assert "MODEL" not in a.stderr
    assert "MODEL keyword is no longer needed" in b.stderr
    m1 = fits.getdata(tmp_path / "model1.prf")
    m2 = fits.getdata(tmp_path / "model2.prf")
    assert m1.dtype == m2.dtype and np.array_equal(m1, m2)
    assert (tmp_path / "a.dat").read_bytes() == \
        (tmp_path / "b.dat").read_bytes()


def test_no_m_writes_no_model(native, tmp_path):
    """Without -m (or --residual) no model is computed or written, also
    with the legacy MODEL keyword, and the profile is the same."""
    out = tmp_path / "out"
    out.mkdir()
    a = native_run(native, IMAGE, *FIT, "-o", out / "a.dat")
    b = native_run(native, IMAGE, *FIT, "MODEL", "-o", out / "b.dat")
    c = native_run(native, IMAGE, *FIT, "-o", out / "c.dat",
                   "-m", tmp_path / "c.prf")
    assert a.returncode == b.returncode == c.returncode == 0
    assert sorted(f.name for f in out.iterdir()) == \
        ["a.dat", "b.dat", "c.dat"]
    assert "Synthesize image" not in a.stdout + b.stdout
    assert "Synthesize image" in c.stdout
    # the model is computed after the profile: never changes it
    ref = (out / "a.dat").read_bytes()
    assert (out / "b.dat").read_bytes() == ref
    assert (out / "c.dat").read_bytes() == ref


def test_o_and_m_are_independent(tmp_path):
    p = cli(IMAGE, *FIT, "-m", tmp_path / "only_model.prf")
    assert p.returncode == 0, p.stderr
    assert (tmp_path / "only_model.prf").is_file()
    assert sorted(f.name for f in tmp_path.iterdir()) == ["only_model.prf"]
    # no -o: the profile table is shown instead
    assert "Fit complete: 25 isophotes." in p.stdout and "Rmaj" in p.stdout
    q = cli(IMAGE, *FIT, "-o", tmp_path / "only_profile.dat")
    assert q.returncode == 0, q.stderr
    assert sorted(f.name for f in tmp_path.iterdir()) == \
        ["only_model.prf", "only_profile.dat"]


@pytest.mark.parametrize("word", ["MODEL='n1234.prf'", "MODEL=n1234.prf",
                                  "model=x.fits"])
def test_model_with_a_value_is_refused(native, tmp_path, word):
    p = cli(IMAGE, *FIT, word, "-o", tmp_path / "x.dat", cwd=tmp_path)
    assert p.returncode == 1
    assert "MODEL takes no value" in p.stderr and "-m FILE" in p.stderr
    q = native_run(native, IMAGE, *FIT, word, "-o", tmp_path / "y.dat")
    assert q.returncode == 1
    assert "MODEL takes no value" in q.stderr
    assert list(tmp_path.iterdir()) == []      # nothing written


def test_paths_with_spaces(tmp_path):
    d = tmp_path / "my results"
    d.mkdir()
    p = cli(IMAGE, *FIT, "-o", d / "n 1234.dat", "-m", d / "n 1234.prf",
            "--residual", d / "n 1234 resid.fits")
    assert p.returncode == 0, p.stderr
    for name in ("n 1234.dat", "n 1234.prf", "n 1234 resid.fits"):
        assert (d / name).is_file(), name
    model = fits.getdata(d / "n 1234.prf")
    resid = fits.getdata(d / "n 1234 resid.fits")
    assert np.array_equal(resid, fits.getdata(IMAGE) - model)


def test_api_model_path_alone(tmp_path):
    r = run_elliprof(IMAGE, 100.3, 99.6, r0=3, r1=80, nr=25,
                     output_dir=tmp_path, model_path=tmp_path / "g.prf")
    assert r.model_path == tmp_path / "g.prf" and r.model_path.is_file()
    assert "MODEL" not in r.stderr
    assert "MODEL" not in r.command[5:]   # never sent as a keyword
    with pytest.raises(ValueError, match="MODEL takes no value"):
        run_elliprof(IMAGE, 100.3, 99.6, r0=3, r1=80, nr=25,
                     output_dir=tmp_path, extra=["MODEL=g.prf"])


def test_keyword_limit_counts_the_implied_model(tmp_path):
    """-m makes the backend add MODEL; the limit of 16 keywords is
    checked with it counted."""
    words = FIT + ["NITER=5", "RLAW=2", "FIXCTR=0", "TIE=-1", "AVG=0",
                   "GAIN=1", "SCALE=1", "SKY=0", "COS3X=2", "COS4X=2",
                   "LINEAR"]                                # 16 with X0/Y0
    assert len(words) == 16
    ok = cli(IMAGE, *words, "-o", tmp_path / "a.dat")
    assert ok.returncode == 0, ok.stderr
    p = cli(IMAGE, *words, "-m", tmp_path / "m.prf")
    assert p.returncode == 1
    assert "at most 16 keywords" in p.stderr and "MODEL" in p.stderr
