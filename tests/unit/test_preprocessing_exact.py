"""Exact preparation arithmetic on a tiny image, in the backend and in
the Python helpers:  prepared = (science - sky) * mask."""

import numpy as np
import pytest

from elliprof import apply_mask, subtract_sky, write_bitmap_mask
from helpers import write_fits

SCIENCE = np.array([[10, 20], [30, 40]], dtype=np.float32)
SKY_IMAGE = np.array([[1, 2], [3, 4]], dtype=np.float32)
MASK = np.array([[1, 0], [1, 1]], dtype=np.float32)


@pytest.fixture
def files(tmp_path):
    return (write_fits(tmp_path / "sci.fits", SCIENCE),
            write_fits(tmp_path / "sky.fits", SKY_IMAGE),
            write_fits(tmp_path / "mask.fits", MASK),
            tmp_path)


def test_python_helpers():
    got = apply_mask(subtract_sky(SCIENCE, sky_image=SKY_IMAGE), MASK)
    np.testing.assert_array_equal(got, [[9, 0], [27, 36]])
    np.testing.assert_array_equal(
        apply_mask(subtract_sky(SCIENCE, sky=5), MASK), [[5, 0], [25, 35]])
    np.testing.assert_array_equal(subtract_sky(SCIENCE), SCIENCE)


@pytest.mark.native
def test_sky_image_and_mask(files, prepare):
    sci, sky, mask, _ = files
    np.testing.assert_array_equal(
        prepare(sci, "--sky-image", sky, "--mask", mask),
        [[9, 0], [27, 36]])


@pytest.mark.native
def test_sky_image_and_bitmap_mask(files, prepare):
    sci, sky, _, tmp = files
    write_bitmap_mask(tmp / "m.dmask", MASK)
    np.testing.assert_array_equal(
        prepare(sci, "--sky-image", sky, "--mask", tmp / "m.dmask"),
        [[9, 0], [27, 36]])


@pytest.mark.native
def test_scalar_sky_and_mask(files, prepare):
    sci, _, mask, _ = files
    np.testing.assert_array_equal(prepare(sci, "--sky", "5", "--mask", mask),
                                  [[5, 0], [25, 35]])


@pytest.mark.native
def test_scalar_sky_alone(files, prepare):
    sci, _, _, _ = files
    np.testing.assert_array_equal(prepare(sci, "--sky", "5"),
                                  [[5, 15], [25, 35]])


@pytest.mark.native
def test_no_sky_leaves_science_unchanged(files, prepare):
    sci, _, _, _ = files
    np.testing.assert_array_equal(prepare(sci), SCIENCE)


@pytest.mark.native
def test_order_is_sky_then_mask(files, prepare):
    """Masked pixels are exactly 0, not -sky: the sky is removed first."""
    sci, sky, mask, _ = files
    got = prepare(sci, "--sky-image", sky, "--mask", mask)
    assert got[0, 1] == 0.0
    got = prepare(sci, "--sky", "100", "--mask", mask)
    assert got[0, 1] == 0.0 and got[0, 0] == -90.0
