"""Smoke tests for an *installed* elliprof (a wheel in a clean
environment).  Run with the configuration next to this file so the
source tree is not importable:

    pytest -c tests/packaging/pytest.ini tests/packaging

cibuildwheel runs these against every wheel it builds.
"""

import os
import shutil
import subprocess
import sys
import sysconfig
from pathlib import Path

import numpy as np
import pytest

HERE = Path(__file__).resolve().parent
GALAXY = HERE.parent / "data" / "synthetic_galaxy.fits"
FIT = ["X0=127.3", "Y0=121.6", "R0=3", "R1=90", "NR=30"]


def elliprof_cmd():
    exe = shutil.which("elliprof")
    assert exe, "the elliprof command is not on PATH"
    return [exe]


def run(*args, cwd=None):
    return subprocess.run(elliprof_cmd() + [str(a) for a in args],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, cwd=cwd)


def test_imports_installed_package_not_source():
    import elliprof
    site = Path(sysconfig.get_paths()["purelib"]).resolve()
    plat = Path(sysconfig.get_paths()["platlib"]).resolve()
    where = Path(elliprof.__file__).resolve()
    assert site in where.parents or plat in where.parents, where


def test_backend_is_inside_installed_package():
    import elliprof
    from elliprof._native import backend_source
    exe = elliprof.find_backend()
    assert Path(elliprof.__file__).resolve().parent in exe.resolve().parents
    assert backend_source() == "installed package"
    assert "ELLIPROF_NATIVE" not in os.environ


def test_no_compiler_needed():
    """No Fortran compiler is available, and the backend only needs
    libraries shipped in the wheel or provided by the OS."""
    if os.environ.get("ELLIPROF_TEST_REQUIRE_NO_COMPILER") == "1":
        assert shutil.which("gfortran") is None, \
            "gfortran is visible: run this test without a compiler"
    elif shutil.which("gfortran"):
        pytest.skip("gfortran is on PATH here (e.g. inside the build "
                    "container); the clean-environment job checks this")
    import elliprof
    exe = elliprof.find_backend()
    proc = subprocess.run([str(exe), "--version"], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          universal_newlines=True)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith("elliprof_native ")


def test_help_version_diagnostics():
    import elliprof
    h = run("--help")
    assert h.returncode == 0 and "elliprof IMAGE.fits X0=x Y0=y" in h.stdout
    assert run("-h").stdout == h.stdout
    v = run("--version")
    assert v.returncode == 0
    assert v.stdout == (f"elliprof {elliprof.__version__}\n"
                        f"Maintained by {elliprof.__maintainer__}\n"
                        f"Email: {elliprof.__email__}\n")
    assert run("-v").stdout == v.stdout
    intro = run()
    assert intro.returncode == 0 and "elliprof -h" in intro.stdout
    d = run("--diagnostics")
    assert d.returncode == 0
    assert "installed package" in d.stdout
    assert "elliprof_native" in d.stdout and "CFITSIO" in d.stdout
    if sys.platform == "darwin":
        assert "backend minimum macOS" in d.stdout


def test_python_m_elliprof():
    proc = subprocess.run([sys.executable, "-m", "elliprof", "--version"],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)
    assert proc.returncode == 0 and proc.stdout.startswith("elliprof ")


def _profile_files(tmp_path, stem):
    return [tmp_path / f"{stem}.{ext}" for ext in ("prf", "csv", "reg")]


def _check_outputs(tmp_path, stem, n):
    from elliprof import parse_elliprof_csv, read_ds9_regions, read_profile
    prf, csv, reg = _profile_files(tmp_path, stem)
    assert len(read_profile(str(prf))) == n
    df, _ = parse_elliprof_csv(csv)
    assert len(df) == n and not df.isna().any().any()
    assert len(read_ds9_regions(reg)) == n


def test_explicit_center_scalar_sky(tmp_path):
    prf, csv, reg = _profile_files(tmp_path, "a")
    p = run(GALAXY, *FIT, "--sky", "100", "-o", prf, "--csv", csv,
            "--reg", reg)
    assert p.returncode == 0, p.stderr
    _check_outputs(tmp_path, "a", 30)
    from elliprof import read_profile
    last = read_profile(str(prf)).iloc[-1]
    assert abs(last.x0 - 127.3) < 0.05 and abs(last.y0 - 121.6) < 0.05
    assert abs(last.ellip - 0.3) < 0.01


def test_center_is_required(tmp_path):
    p = run(GALAXY, "R0=3", "R1=90", "NR=30", "--sky", "100")
    assert p.returncode == 2
    assert "error: X0 and Y0 are required" in p.stderr

def test_sky_image_and_mask(tmp_path):
    fits = pytest.importorskip("astropy.io.fits")   # test-only dependency
    from elliprof import write_bitmap_mask
    data = fits.getdata(GALAXY)
    fits.PrimaryHDU(np.full(data.shape, 100.0, np.float32)).writeto(
        tmp_path / "sky.fits")
    m = np.ones(data.shape)
    m[200:220, 20:40] = 0
    write_bitmap_mask(tmp_path / "m.dmask", m)
    prf, csv, reg = _profile_files(tmp_path, "c")
    p = run(GALAXY, *FIT, "--sky-image", tmp_path / "sky.fits", "--mask",
            tmp_path / "m.dmask", "-o", prf, "--csv", csv, "--reg", reg)
    assert p.returncode == 0, p.stderr
    assert "400 pixels masked" in p.stdout
    _check_outputs(tmp_path, "c", 30)
    # the same sky as a constant gives the same fit
    q = run(GALAXY, *FIT, "--sky", "100", "--mask", tmp_path / "m.dmask",
            "-o", tmp_path / "d.prf")
    assert q.returncode == 0
    assert (tmp_path / "d.prf").read_bytes() == prf.read_bytes()


def test_python_api(tmp_path):
    from elliprof import run_elliprof
    res = run_elliprof(GALAXY, 127.3, 121.6, sky=100, r0=3, r1=90,
                       nr=30, model=True, output_dir=tmp_path)
    assert res.ok and len(res.profile) == 30
    assert list(res.profile.columns)[:3] == ["Rmaj", "x0", "y0"]
    for p in (res.prf_path, res.csv_path, res.reg_path, res.model_path):
        assert p.is_file()
    # identical to the command line
    p = run(GALAXY, *FIT, "--sky", "100", "-o", tmp_path / "cli.prf")
    assert p.returncode == 0
    assert (tmp_path / "cli.prf").read_bytes() == res.prf_path.read_bytes()


def test_harmonic_selection(tmp_path):
    """The installed package exposes ELLIPROF's harmonic settings: the
    model-harmonic options change only the model image, the 6th-order
    option changes the fit, and the command line and the API agree."""
    from elliprof import read_prf, run_elliprof

    def fit(path):
        p = read_prf(str(path))
        return np.asarray(p["params"])[:p["n"], :11]

    runs = {}
    for name, opts, args in (
            ("default", {}, []),
            ("none", {"model_harmonics": ()}, ["--model-harmonics", "none"]),
            ("4 median", {"model_harmonics": (4,), "harmonic_mode": "median"},
             ["--model-harmonics", "4", "--harmonic-mode", "median"]),
            ("6th", {"sixth_order": True}, ["--sixth-order"])):
        d = tmp_path / name.replace(" ", "_")
        res = run_elliprof(GALAXY, 127.3, 121.6, sky=100, r0=3, r1=90,
                           nr=30, model=True, output_dir=d, **opts)
        p = run(GALAXY, *FIT, "MODEL", "--sky", "100", *args,
                "-o", d / "cli.prf", "-m", d / "cli.fits")
        assert p.returncode == 0, p.stderr
        assert (d / "cli.prf").read_bytes() == res.prf_path.read_bytes()
        runs[name] = res
    assert [w for w in runs["4 median"].command if w.startswith("COS")] == \
        ["COS3X=0", "COS4X=1"]
    assert [w for w in runs["6th"].command if w.startswith("COS")] == \
        ["COS3X=-2", "COS4X=2"]
    default = fit(runs["default"].prf_path)
    assert np.array_equal(fit(runs["none"].prf_path), default)
    assert np.array_equal(fit(runs["4 median"].prf_path), default)
    assert not np.array_equal(fit(runs["6th"].prf_path), default)
    models = {n: runs[n].model_path.read_bytes() for n in runs}
    assert len(set(models.values())) == 4
    bad = run(GALAXY, *FIT, "--model-harmonics", "5",
              "-o", tmp_path / "bad.prf")
    assert bad.returncode == 1 and "model harmonics must be" in bad.stderr


def test_paths_with_spaces_and_unicode(tmp_path):
    d = tmp_path / "dir with spaces"
    d.mkdir()
    img = d / "galaxy image.fits"
    shutil.copy(GALAXY, img)
    out = d / "out.csv"
    p = run(img, *FIT, "--sky", "100", "--csv", out)
    assert p.returncode == 0, p.stderr
    assert out.is_file()
    u = tmp_path / "gálaxy"
    u.mkdir()
    shutil.copy(GALAXY, u / "g.fits")
    p = run(u / "g.fits", *FIT, "--sky", "100", "--csv", u / "o.csv")
    if sys.platform == "win32" and p.returncode != 0:
        pytest.xfail("non-ASCII paths are not supported on Windows yet")
    assert p.returncode == 0, p.stderr


def test_runs_without_astropy(tmp_path):
    """astropy is only a test/notebook dependency: a full fit works with
    it blocked from import."""
    code = f"""
import sys
sys.modules["astropy"] = None
from elliprof import run_elliprof
res = run_elliprof({str(GALAXY)!r}, 127.3, 121.6, sky=100, r0=3, r1=90,
                   nr=30, output_dir={str(tmp_path)!r})
assert res.ok and len(res.profile) == 30
print("ok")
"""
    proc = subprocess.run([sys.executable, "-c", code], stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE,
                          universal_newlines=True)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "ok"
