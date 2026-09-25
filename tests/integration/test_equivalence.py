"""Native CLI, Python API and Python CLI give the same fit.

On one machine the three routes run the same executable on the same
inputs, so the .prf files must be byte-identical and the CSV data rows
identical (the CSV header differs only in how the input path is shown).
"""

import os
import subprocess
import sys

import numpy as np
import pytest

from helpers import ROOT, write_fits
from elliprof import cli, run_elliprof
from elliprof.masks import write_bitmap_mask
from elliprof.profile import parse_elliprof_csv

pytestmark = pytest.mark.native


def csv_rows(path):
    return [l for l in open(path) if not l.startswith("#")]


def python_cli_subprocess(args, cwd):
    env = dict(os.environ)
    env["PYTHONPATH"] = str(ROOT / "python") + os.pathsep + \
        env.get("PYTHONPATH", "")
    return subprocess.run([sys.executable, "-m", "elliprof", *map(str, args)],
                          cwd=cwd, env=env, capture_output=True, text=True)


def three_ways(tmp_path, native, image, native_words, api_kwargs,
               cli_words):
    """Run all routes; return {route: (prf path, csv path, stdout)}."""
    out = {}
    d = tmp_path / "native"
    d.mkdir()
    proc = subprocess.run([str(native), str(image), *map(str, native_words),
                           "-o", d / "r.prf", "--csv", d / "r.csv",
                           "--reg", d / "r.reg"],
                          capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    out["native"] = (d / "r.prf", d / "r.csv", d / "r.reg", proc.stdout)

    res = run_elliprof(image, output_dir=tmp_path / "api", prefix="r",
                       **api_kwargs)
    out["api"] = (res.prf_path, res.csv_path, res.reg_path, res.stdout)

    d = tmp_path / "cli"
    d.mkdir()
    proc = python_cli_subprocess([image, *cli_words, "-o", d / "r.prf",
                                  "--csv", d / "r.csv", "--reg",
                                  d / "r.reg"], tmp_path)
    assert proc.returncode == 0, proc.stderr
    out["cli"] = (d / "r.prf", d / "r.csv", d / "r.reg", proc.stdout)
    return out, res


def assert_same(out):
    ref = out["native"]
    for route in ("api", "cli"):
        got = out[route]
        assert got[0].read_bytes() == ref[0].read_bytes(), route
        assert csv_rows(got[1]) == csv_rows(ref[1]), route
        assert got[2].read_bytes() == ref[2].read_bytes(), route


FIT = ["R0=3", "R1=90", "NR=30"]


def test_explicit_center_scalar_sky(tmp_path, native, galaxy_fits):
    out, res = three_ways(
        tmp_path, native, galaxy_fits,
        ["X0=127.3", "Y0=121.6", *FIT, "--sky", "100"],
        dict(x0=127.3, y0=121.6, r0=3, r1=90, nr=30, sky="100"),
        ["X0=127.3", "Y0=121.6", *FIT, "--sky", "100"])
    assert_same(out)
    assert res.center == (127.3, 121.6)




def test_mask_and_sky_image(tmp_path, native, galaxy_fits):
    from astropy.io import fits
    data = fits.getdata(galaxy_fits)
    yy, xx = np.indices(data.shape)
    sky = write_fits(tmp_path / "sky.fits",
                     100.0 + 0.001 * xx + 0.0005 * yy)
    m = np.ones(data.shape)
    m[(xx - 160) ** 2 + (yy - 140) ** 2 < 36] = 0
    write_bitmap_mask(tmp_path / "m.dmask", m)
    out, _ = three_ways(
        tmp_path, native, galaxy_fits,
        ["X0=127.3", "Y0=121.6", *FIT, "--sky-image", sky, "--mask",
         tmp_path / "m.dmask"],
        dict(x0=127.3, y0=121.6, r0=3, r1=90, nr=30, sky_image=sky,
             mask=tmp_path / "m.dmask"),
        ["X0=127.3", "Y0=121.6", *FIT, "--sky-image", sky, "--mask",
         tmp_path / "m.dmask"])
    assert_same(out)


def test_in_process_cli_equals_api(tmp_path, galaxy_fits, capsys):
    code = cli.main([str(galaxy_fits), "X0=127.3", "Y0=121.6", *FIT,
                     "--sky", "100", "-o", str(tmp_path / "c.prf")])
    assert code == 0
    res = run_elliprof(galaxy_fits, x0=127.3, y0=121.6, r0=3, r1=90,
                       nr=30, sky="100", output_dir=tmp_path / "a")
    assert (tmp_path / "c.prf").read_bytes() == res.prf_path.read_bytes()


def test_result_object(tmp_path, galaxy_fits):
    res = run_elliprof(galaxy_fits, x0=127.3, y0=121.6, r0=3, r1=90,
                       nr=30, sky=100, model=True, output_dir=tmp_path)
    assert res.ok and res.returncode == 0
    assert list(res.profile.columns) == ["Rmaj", "x0", "y0", "I0", "alpha",
                                         "ellip", "I3", "A3", "I4", "A4",
                                         "slope"]
    assert len(res.profile) == 30
    for p in (res.prf_path, res.csv_path, res.reg_path, res.model_path):
        assert p is not None and p.is_file()
    assert res.backend_path.is_file()
    assert res.command[0] == str(res.backend_path)
    df, meta = parse_elliprof_csv(res.csv_path)
    np.testing.assert_allclose(df["x0"], res.profile["x0"], atol=5.1e-5)
    assert meta["Parameters"].startswith("X0=127.3 Y0=121.6 R0=3 R1=90")
    assert meta["elliprof version"] == res.version


def test_failure_raises_with_output(tmp_path, galaxy_fits):
    # a failure only the backend detects: an output it cannot write
    from elliprof import ElliprofError
    bad = tmp_path / "no" / "dir" / "x.csv"
    with pytest.raises(ElliprofError, match="cannot write output") as info:
        run_elliprof(galaxy_fits, 128, 128, r0=3, r1=10, nr=4,
                     csv_path=bad, output_dir=tmp_path)
    assert info.value.result.returncode == 1
    res = run_elliprof(galaxy_fits, 128, 128, r0=3, r1=10, nr=4,
                       csv_path=bad, output_dir=tmp_path, check=False)
    assert not res.ok and res.profile is None


def test_prepared_image_matches_python_helpers(tmp_path, galaxy_fits):
    from astropy.io import fits
    from elliprof import apply_mask, subtract_sky
    m = np.ones((256, 256))
    m[10:20, 30:50] = 0
    write_bitmap_mask(tmp_path / "m.dmask", m)
    res = run_elliprof(galaxy_fits, x0=127.3, y0=121.6, r0=3, r1=90,
                       nr=30, sky=100.5, mask=tmp_path / "m.dmask",
                       prepared=tmp_path / "prep.fits",
                       output_dir=tmp_path)
    expect = apply_mask(subtract_sky(fits.getdata(galaxy_fits), sky=100.5),
                        m)
    np.testing.assert_array_equal(fits.getdata(res.prepared_path), expect)


