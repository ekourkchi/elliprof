"""The real example: UGC 12517 (HST WFC3/IR F110W) with its .dmask.

Checks the whole chain on real data.  This is not a reproduction of the
historical SBF pipeline, which used additional masks and filled masked
pixels with a previous model."""

import json

import numpy as np
import pytest

from cases import BASELINE, U12517
from elliprof import load_mask
from elliprof.io import image_info
from elliprof.masks import mask_info
from elliprof.profile import parse_elliprof_csv, read_profile
from elliprof.regions import read_ds9_regions
from runner import csv_rows, platform_id, run_case, same_platform

IMAGE = U12517["image"]
MASK = U12517["run"]["mask"]

pytestmark = [pytest.mark.native,
              pytest.mark.skipif(not IMAGE.is_file(),
                                 reason="example data missing")]


@pytest.fixture(scope="module")
def run(tmp_path_factory):
    out = tmp_path_factory.mktemp("u12517") / "u12517"
    res = run_case("u12517", IMAGE, U12517["run"], out)
    return res, out


def test_inputs():
    assert image_info(str(IMAGE))[0] == (1025, 1022)
    info = mask_info(str(MASK))
    assert (info["bitpix"], info["ncol"], info["nrow"]) == (1, 1025, 1022)
    m = load_mask(str(MASK))
    assert set(np.unique(m)) == {0.0, 1.0}
    assert int((m == 0).sum()) == 103402


def test_fit_completes(run):
    res, out = run
    assert res.returncode == 0
    assert res.center == (567.0, 562.0)
    assert "Sky: subtracted scalar" in res.stdout
    assert "103402 pixels masked" in res.stdout
    for name in ("profile.prf", "profile.csv", "profile.reg"):
        assert (out / name).is_file()


def test_output_counts_agree(run):
    _, out = run
    prof = read_profile(str(out / "profile.prf"))
    assert len(prof) == 23
    assert len(csv_rows(out / "profile.csv")) == 23
    finite = prof.dropna()
    assert len(read_ds9_regions(out / "profile.reg")) == len(finite)
    _, meta = parse_elliprof_csv(out / "profile.csv")
    assert meta["Mask"].endswith("u12517j.dmask")
    assert meta["Sky"].startswith("scalar 3246")


def test_profile_is_plausible(run):
    """Loose physical sanity: brightness falls outward and the centre
    stays near the nucleus."""
    _, out = run
    prof = read_profile(str(out / "profile.prf")).dropna()
    outer = prof[prof.Rmaj >= 20]
    assert (np.diff(outer.I0.to_numpy()) < 0).all()
    assert np.abs(outer.x0 - 567).max() < 3
    assert np.abs(outer.y0 - 562).max() < 3
    assert (outer.ellip.between(0.05, 0.4)).all()


def test_matches_baseline(run):
    _, out = run
    ref = BASELINE / "u12517"
    if not (ref / "profile.prf").exists():
        pytest.skip("no baseline yet (make update-baselines)")
    meta = json.loads((ref / "meta.json").read_text())
    if not same_platform(meta, platform_id()):
        pytest.skip("baseline from another platform; compared by "
                    "compare_platforms.py")
    assert (out / "profile.prf").read_bytes() == \
        (ref / "profile.prf").read_bytes()
