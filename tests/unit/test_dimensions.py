"""Mask and sky image must match the science image exactly; a mismatch
stops everything before the science image is touched.  Checked in the
backend and in the Python layer."""

import numpy as np
import pytest

from elliprof import GeometryError, run_elliprof
from helpers import write_fits

FIT = ["X0=50", "Y0=50", "R0=3", "R1=30", "NR=5"]
SCI = (100, 100)  # (cols, rows)


def image(path, cols, rows, value=1.0):
    return write_fits(path, np.full((rows, cols), value))


@pytest.fixture
def sci(tmp_path):
    return image(tmp_path / "sci.fits", *SCI, value=5.0)


# (mask shape, sky shape, expected error or None); shapes are (cols, rows)
CASES = [
    ((100, 100), None, None),
    ((99, 100), None, "mask dimensions (99 x 100) do not match science "
                      "image dimensions (100 x 100)"),
    ((100, 99), None, "mask dimensions (100 x 99) do not match science "
                      "image dimensions (100 x 100)"),
    (None, (100, 100), None),
    (None, (99, 100), "sky image dimensions (99 x 100) do not match "
                      "science image dimensions (100 x 100)"),
    (None, (100, 99), "sky image dimensions (100 x 99) do not match "
                      "science image dimensions (100 x 100)"),
    ((100, 100), (99, 100), "sky image dimensions (99 x 100)"),
    ((99, 100), (100, 100), "mask dimensions (99 x 100)"),
    ((99, 100), (100, 99), "dimensions"),
]
IDS = ["mask-ok", "mask-cols", "mask-rows", "sky-ok", "sky-cols",
       "sky-rows", "mask-ok-sky-bad", "sky-ok-mask-bad", "both-bad"]


def args(tmp_path, mask, sky):
    out = []
    if mask:
        out += ["--mask", image(tmp_path / "mask.fits", *mask)]
    if sky:
        out += ["--sky-image", image(tmp_path / "sky.fits", *sky, 0.0)]
    return out


@pytest.mark.native
@pytest.mark.parametrize("mask,sky,error", CASES, ids=IDS)
def test_backend(mask, sky, error, sci, tmp_path, run_native):
    prepared = tmp_path / "prep.fits"
    proc = run_native(sci, "--prepare-only", "--prepared", prepared,
                      *args(tmp_path, mask, sky))
    if error is None:
        assert proc.returncode == 0, proc.stderr
    else:
        assert proc.returncode == 1
        assert proc.stderr.startswith("elliprof: error: ")
        assert error in proc.stderr
        # failed before anything was prepared or written
        assert not prepared.exists()


@pytest.mark.parametrize("mask,sky,error", CASES, ids=IDS)
def test_python(mask, sky, error, sci, tmp_path):
    kw = {}
    extra = args(tmp_path, mask, sky)
    for flag, value in zip(extra[::2], extra[1::2]):
        kw[{"--mask": "mask", "--sky-image": "sky_image"}[flag]] = value
    if error is None:
        pytest.importorskip("elliprof._native").find_backend()
        res = run_elliprof(sci, 50, 50, r0=3, r1=30, nr=5,
                           output_dir=tmp_path / "out", check=False, **kw)
        assert "dimensions" not in res.stderr
    else:
        with pytest.raises(GeometryError, match=error.replace("(", r"\(")
                           .replace(")", r"\)")):
            run_elliprof(sci, 50, 50, r0=3, r1=30, nr=5,
                         output_dir=tmp_path / "out", **kw)


@pytest.mark.native
def test_origin_mismatch(tmp_path, run_native):
    sci = write_fits(tmp_path / "sci.fits", np.ones((10, 10)),
                     header={"CNPIX1": 5, "CNPIX2": 0})
    mask = write_fits(tmp_path / "m.fits", np.ones((10, 10)))
    proc = run_native(sci, "--prepare-only", "--prepared",
                      tmp_path / "p.fits", "--mask", mask)
    assert proc.returncode == 1
    assert "mask origin (CNPIX1,CNPIX2) = (0,0) does not match science " \
        "image origin (5,0)" in proc.stderr
    with pytest.raises(GeometryError, match="CNPIX1"):
        run_elliprof(sci, 5, 5, r0=1, r1=3, nr=2, mask=mask,
                     output_dir=tmp_path / "o")
