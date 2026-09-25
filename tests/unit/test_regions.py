"""DS9 regions: geometry, coordinate conversion, no labels."""

import numpy as np
import pandas as pd
import pytest

from elliprof.profile import COLUMNS, read_profile
from elliprof.regions import (profile_ellipses, read_ds9_regions,
                              write_ds9_regions)


def _profile(rows):
    return pd.DataFrame(rows, columns=COLUMNS)


ROW = [10.0, 99.5, 49.5, 1000.0, 120.0, 0.3, 0, 0, 0, 0, -2.0]


def test_ellipse_geometry():
    (x, y, a, b, ang), = profile_ellipses(_profile([ROW]))
    assert (a, b) == (10.0, pytest.approx(7.0))       # b = a (1 - ellip)
    assert (x, y) == (100.0, 50.0)                     # +0.5 to DS9
    assert ang == 30.0                                 # alpha - 90


def test_center_uses_origin():
    (x, y, *_), = profile_ellipses(_profile([ROW]), cnpix=(40, 20))
    assert (x, y) == (60.0, 30.0)


def test_nan_rows_skipped():
    bad = list(ROW)
    bad[1] = np.nan
    assert len(profile_ellipses(_profile([ROW, bad, ROW]))) == 2


def test_write_and_read(tmp_path):
    n = write_ds9_regions(_profile([ROW, ROW]), tmp_path / "r.reg")
    text = (tmp_path / "r.reg").read_text().splitlines()
    assert text[:3] == ["# Region file format: DS9 version 4.1",
                        "global color=green width=1", "image"]
    assert n == 2
    assert read_ds9_regions(tmp_path / "r.reg") == \
        [(100.0, 50.0, 10.0, 7.0, 30.0)] * 2


@pytest.mark.native
def test_native_regions_match_profile(tmp_path, run_native, galaxy_fits):
    run_native(galaxy_fits, "X0=127.3", "Y0=121.6", "R0=3", "R1=90",
               "NR=30", "--sky", "100", "-o", tmp_path / "g.prf", "--reg",
               tmp_path / "g.reg", check=True)
    prof = read_profile(str(tmp_path / "g.prf"))
    native = read_ds9_regions(tmp_path / "g.reg")
    assert len(native) == len(prof) == 30
    np.testing.assert_allclose(native, profile_ellipses(prof), atol=5.1e-5)
    text = (tmp_path / "g.reg").read_text()
    assert "text=" not in text and "#" not in text.split("image", 1)[1]
    # the synthetic galaxy: centre (127.3, 121.6) -> DS9 (127.8, 122.1),
    # major axis 30 deg from +x, b/a = 0.7
    x, y, a, b, ang = native[-1]
    assert (x, y) == pytest.approx((127.8, 122.1), abs=0.01)
    assert b / a == pytest.approx(0.7, abs=0.001)
    assert ang % 180 == pytest.approx(30.0, abs=0.05)
