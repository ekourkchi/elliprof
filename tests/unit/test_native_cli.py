"""Argument handling and early, readable failures of elliprof_native."""

import numpy as np
import pytest

from helpers import ROOT, write_fits

pytestmark = pytest.mark.native

GOOD = ["X0=127.3", "Y0=121.6", "R0=3", "R1=90", "NR=30"]


def test_version(run_native):
    proc = run_native("--version")
    assert proc.returncode == 0
    version = (ROOT / "VERSION").read_text().strip()
    assert proc.stdout.startswith(f"elliprof_native {version} (CFITSIO ")


def test_help(run_native):
    proc = run_native("--help")
    assert proc.returncode == 0
    assert "usage: elliprof_native" in proc.stdout


def test_no_arguments(run_native):
    proc = run_native()
    assert proc.returncode == 1
    assert "usage" in proc.stderr


def test_missing_center_points_to_python_cli(galaxy_fits, run_native):
    proc = run_native(galaxy_fits, "R0=3", "R1=90", "NR=30")
    assert proc.returncode == 1
    assert "X0 and Y0 are required by elliprof_native." in proc.stderr
    assert "Python `elliprof` command" in proc.stderr
    assert "STOP" not in proc.stderr


@pytest.mark.parametrize("args,message", [
    (["X0=1", "R0=3", "R1=90", "NR=30"], "must be given together"),
    (["Y0=1", "R0=3", "R1=90", "NR=30"], "must be given together"),
    (["X0=1", "Y0=1", "R1=90", "NR=30"], "R0=, R1= and NR= are required"),
    (["X0=1", "Y0=1", "R0=3", "NR=30"], "R0=, R1= and NR= are required"),
    (["X0=1", "Y0=1", "R0=3", "R1=90"], "R0=, R1= and NR= are required"),
    (["X0=1", "Y0=1", "GC"], "GC needs NR="),
    (GOOD + ["--bogus"], "unknown option --bogus"),
    (GOOD + ["--csv"], "--csv needs a value"),
    (GOOD + ["--prepare-only"], "--prepare-only needs --prepared"),
    (GOOD + ["OLD"], "OLD needs a previous profile"),
    (GOOD + ["edit"], "EDIT needs a previous profile"),
])
def test_argument_errors(args, message, galaxy_fits, run_native):
    proc = run_native(galaxy_fits, *args)
    assert proc.returncode == 1
    assert message in proc.stderr


def test_missing_image(run_native, tmp_path):
    proc = run_native(tmp_path / "nope.fits", *GOOD)
    assert proc.returncode == 1
    assert "cannot open" in proc.stderr


def test_invalid_fits(run_native, tmp_path):
    bad = tmp_path / "bad.fits"
    bad.write_text("this is not FITS\n" * 200)
    proc = run_native(bad, *GOOD)
    assert proc.returncode == 1
    assert "cannot open" in proc.stderr


def test_one_dimensional_image(run_native, tmp_path):
    from astropy.io import fits
    fits.PrimaryHDU(np.ones(50, np.float32)).writeto(tmp_path / "1d.fits")
    proc = run_native(tmp_path / "1d.fits", *GOOD)
    assert proc.returncode == 1
    assert "no 2-D image" in proc.stderr


@pytest.mark.parametrize("flag", ["-o", "--csv", "--reg", "-m"])
def test_unwritable_output_fails_before_fit(flag, galaxy_fits, run_native,
                                            tmp_path):
    target = tmp_path / "no" / "such" / "dir" / "out"
    proc = run_native(galaxy_fits, *GOOD, flag, target)
    assert proc.returncode == 1
    assert "cannot write output file" in proc.stderr
    assert "SURFACE PHOTOMETRY" not in proc.stdout


def test_existing_output_is_not_deleted_by_check(galaxy_fits, run_native,
                                                 tmp_path):
    keep = tmp_path / "keep.csv"
    keep.write_text("old")
    # the fit itself then overwrites it
    proc = run_native(galaxy_fits, *GOOD, "--csv", keep)
    assert proc.returncode == 0
    assert keep.read_text().startswith("# ELLIPROF")


def test_no_output_file_left_by_failed_check(galaxy_fits, run_native,
                                             tmp_path):
    ok = tmp_path / "ok.prf"
    proc = run_native(galaxy_fits, *GOOD, "-o", ok, "--csv",
                      tmp_path / "missing" / "x.csv")
    assert proc.returncode == 1
    assert not ok.exists()


def test_legacy_symlink_name_still_works(galaxy_fits, tmp_path):
    import subprocess
    legacy = ROOT / "elliprof"
    if not legacy.exists():
        pytest.skip("./elliprof development link not built")
    proc = subprocess.run([str(legacy), str(galaxy_fits), *GOOD, "SKY=100",
                           "-o", str(tmp_path / "t.prf")],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
