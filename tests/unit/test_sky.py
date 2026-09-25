"""Sky subtraction and its order with respect to the mask (native).

MONSTA semantics: --sky V is `SC 1 V` (A = A + (-V) in REAL*4),
--sky-image F is `SI 1 2` (A = A - B), --mask is `MI 1 2` (A = A * M),
applied in that order.  Results must be bit-exact.
"""

import numpy as np
import pytest

from helpers import write_fits
from elliprof.masks import write_bitmap_mask

pytestmark = pytest.mark.native

RNG = np.random.default_rng(7)


@pytest.fixture
def image(tmp_path):
    data = RNG.normal(1000.0, 30.0, (12, 17)).astype(np.float32)
    return write_fits(tmp_path / "img.fits", data), data


@pytest.mark.parametrize("sky", ["3246.0", "3246", "3246.6105834960936",
                                 "-12.5", "1e3", "0"])
def test_scalar_sky_is_exact(sky, image, prepare):
    path, data = image
    expect = data + np.float32(-np.float32(float(sky)))
    np.testing.assert_array_equal(prepare(path, "--sky", sky), expect)


def test_sc_alias_is_identical(image, prepare, run_native, tmp_path):
    path, _ = image
    a = prepare(path, "--sky", "123.25")
    out = tmp_path / "sc.fits"
    proc = run_native(path, "--prepare-only", "--prepared", out,
                      "--sc", "123.25")
    assert proc.returncode == 0
    assert "deprecated" in proc.stderr
    from helpers import read_fits
    np.testing.assert_array_equal(read_fits(out), a)


def test_sky_image_is_exact(image, prepare, tmp_path):
    path, data = image
    sky = RNG.normal(900.0, 5.0, data.shape).astype(np.float32)
    skyfile = write_fits(tmp_path / "sky.fits", sky)
    np.testing.assert_array_equal(prepare(path, "--sky-image", skyfile),
                                  data - sky)


def test_sky_before_mask_leaves_masked_pixels_zero(image, prepare,
                                                   tmp_path):
    path, data = image
    m = np.ones(data.shape)
    m[3:6, 4:9] = 0
    write_bitmap_mask(tmp_path / "m.dmask", m)
    got = prepare(path, "--sky", "1000", "--mask", tmp_path / "m.dmask")
    assert np.all(got[m == 0] == 0.0)
    np.testing.assert_array_equal(got[m == 1],
                                  (data + np.float32(-1000.0))[m == 1])


@pytest.mark.parametrize("shape,cnpix,message", [
    ((12, 18), None, "pixels but the image is"),
    ((12, 17), (3, 4), "has origin"),
])
def test_sky_image_registration(shape, cnpix, message, image, tmp_path,
                                run_native):
    path, _ = image
    hdr = {"CNPIX1": cnpix[0], "CNPIX2": cnpix[1]} if cnpix else None
    sky = write_fits(tmp_path / "sky.fits", np.zeros(shape), header=hdr)
    proc = run_native(path, "--prepare-only", "--prepared",
                      tmp_path / "p.fits", "--sky-image", sky)
    assert proc.returncode == 1
    assert message in proc.stderr


def test_origin_follows_cnpix(tmp_path, prepare):
    hdr = {"CNPIX1": 3, "CNPIX2": 4}
    img = write_fits(tmp_path / "img.fits", np.full((5, 6), 2.0), hdr)
    sky = write_fits(tmp_path / "sky.fits", np.full((5, 6), 0.5), hdr)
    np.testing.assert_array_equal(prepare(img, "--sky-image", sky), 1.5)


@pytest.mark.parametrize("args,message", [
    (["--sky", "1", "--sky-image", "x.fits"], "only one of"),
    (["--sc", "1", "--sky", "2"], "only one of"),
    (["--sky", "abc"], "needs one number"),
    (["--sky", "1 2"], "needs one number"),
])
def test_sky_option_errors(args, message, image, run_native, tmp_path):
    path, _ = image
    proc = run_native(path, "--prepare-only", "--prepared",
                      tmp_path / "p.fits", *args)
    assert proc.returncode == 1
    assert message in proc.stderr


def test_missing_sky_image(image, run_native, tmp_path):
    path, _ = image
    proc = run_native(path, "--prepare-only", "--prepared",
                      tmp_path / "p.fits", "--sky-image",
                      tmp_path / "nope.fits")
    assert proc.returncode == 1
    assert "cannot open" in proc.stderr
