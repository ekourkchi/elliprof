"""Profile outputs: .prf, CSV and the PRINT EPROF table agree, with the
PARAM_PRF column mapping established from elliprof.f."""

import re

import numpy as np
import pytest

from elliprof.profile import (COLUMNS, parse_elliprof_csv, read_prf,
                              read_profile)

pytestmark = pytest.mark.native

ARGS = ["X0=127.3", "Y0=121.6", "R0=3", "R1=90", "NR=30", "--sky", "100"]


@pytest.fixture(scope="module")
def outputs(tmp_path_factory, native, galaxy_fits):
    import subprocess
    d = tmp_path_factory.mktemp("prof")
    proc = subprocess.run([str(native), str(galaxy_fits), *ARGS,
                           "-o", str(d / "g.prf"), "--csv", str(d / "g.csv"),
                           "--reg", str(d / "g.reg")],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, check=True)
    return d, proc.stdout


def test_prf_structure(outputs):
    d, _ = outputs
    prf = read_prf(str(d / "g.prf"))
    assert prf["n"] == 30
    assert prf["scale"] == 1.0
    assert prf["params"].shape == (250, 12)
    assert prf["header"].startswith("SIMPLE")
    # contours beyond N_PRF are empty
    assert np.all(prf["params"][30:, :11] == 0)


def test_prf_flags_row(outputs):
    d, _ = outputs
    flags = read_profile(str(d / "g.prf")).attrs["flags"]
    assert flags["x0"] == pytest.approx(127.3, abs=1e-4)
    assert flags["y0"] == pytest.approx(121.6, abs=1e-4)
    assert (flags["r0"], flags["r1"], flags["nr"]) == (3.0, 90.0, 30.0)


def test_csv_matches_prf(outputs):
    d, _ = outputs
    exact = read_profile(str(d / "g.prf"))
    df, meta = parse_elliprof_csv(str(d / "g.csv"))
    assert list(df.columns) == COLUMNS
    assert len(df) == len(exact) == 30
    # CSV rounding: 4 decimals (Rmaj, x0, y0, alpha, A3, A4), 6 decimals
    # (ellip, slope), 8 significant digits (I0, I3, I4)
    for col in COLUMNS:
        if col in ("I0", "I3", "I4"):
            np.testing.assert_allclose(df[col], exact[col], rtol=1e-7)
        else:
            tol = 5.01e-7 if col in ("ellip", "slope") else 5.01e-5
            np.testing.assert_allclose(df[col], exact[col], atol=tol)
    assert meta["Input"].endswith("synthetic_galaxy.fits")
    assert meta["Sky"].startswith("scalar 100")
    assert meta["Mask"] == "none"
    assert meta["Parameters"] == "X0=127.3 Y0=121.6 R0=3 R1=90 NR=30"
    assert "Center source" not in meta
    from elliprof import __version__
    assert meta["elliprof version"] == __version__


def test_csv_is_aligned_and_commented(outputs):
    d, _ = outputs
    lines = (d / "g.csv").read_text().splitlines()
    header = [l for l in lines if l.startswith("#")]
    rows = [l for l in lines if not l.startswith("#")]
    assert header[0] == "# ELLIPROF surface photometry profile"
    assert len({len(r) for r in rows}) == 1        # fixed width
    assert all(r.count(",") == 10 for r in rows)
    # the column-name line lines up with the data
    names = header[-1]
    assert len(names) == len(rows[0])


def test_print_eprof_table_matches(outputs, run_native, galaxy_fits):
    """The table printed when no profile file is written (as PRINT EPROF
    does) agrees with the .prf; with -o/--csv it is not printed."""
    d, stdout = outputs
    assert "SURFACE PHOTOMETRY PROFILE COMPUTATION:" not in stdout
    stdout = run_native(galaxy_fits, *ARGS, check=True).stdout
    exact = read_profile(str(d / "g.prf"))
    table = stdout.split("SURFACE PHOTOMETRY PROFILE COMPUTATION:")[1]
    rows = [l for l in table.splitlines()[2:] if l.strip()]
    assert len(rows) == 30
    # FORMAT (F6.1,2F8.2,F9.1,F7.2,F6.3,2(F7.4,F7.2),F6.2)
    widths = [6, 8, 8, 9, 7, 6, 7, 7, 7, 7, 6]
    decimals = [1, 2, 2, 1, 2, 3, 4, 2, 4, 2, 2]
    for k, row in enumerate(rows):
        pos = 0
        for j, (w, dec) in enumerate(zip(widths, decimals)):
            value = float(row[pos:pos + w])
            pos += w
            assert value == pytest.approx(exact.iloc[k, j],
                                          abs=0.51 * 10 ** -dec)


def test_read_prf_rejects_other_files(tmp_path):
    bad = tmp_path / "x.prf"
    bad.write_text("1 2 3\n")
    with pytest.raises(ValueError, match="not an ELLIPROF"):
        read_prf(str(bad))
