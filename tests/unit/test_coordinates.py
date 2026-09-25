"""Centre modes and conversions to ELLIPROF X0/Y0."""

import numpy as np
import pytest
from astropy.io import fits

from elliprof.coordinates import (SOURCE_AUTO, SOURCE_IMAGE, SOURCE_PHYSICAL,
                                  SOURCE_RADEC, CenterError, image_center,
                                  physical_to_image, radec_to_image,
                                  resolve_center)


def tan_header(ncol=200, nrow=150, crpix=(80.0, 60.0),
               crval=(188.73658, -12.58242), scale=0.2 / 3600, rot=30.0,
               radesys=None):
    h = fits.Header()
    h["NAXIS"] = 2
    h["NAXIS1"] = ncol
    h["NAXIS2"] = nrow
    h["CTYPE1"] = "RA---TAN"
    h["CTYPE2"] = "DEC--TAN"
    h["CRPIX1"], h["CRPIX2"] = crpix
    h["CRVAL1"], h["CRVAL2"] = crval
    c, s = np.cos(np.radians(rot)), np.sin(np.radians(rot))
    h["CD1_1"], h["CD1_2"] = -scale * c, scale * s
    h["CD2_1"], h["CD2_2"] = scale * s, scale * c
    if radesys:
        h["RADESYS"] = radesys
    return h


def plain_header(ncol=1025, nrow=1022, **cards):
    h = fits.Header()
    h["NAXIS"], h["NAXIS1"], h["NAXIS2"] = 2, ncol, nrow
    for k, v in cards.items():
        h[k] = v
    return h


# --- explicit image coordinates -------------------------------------------

def test_x0_y0_passthrough():
    c = resolve_center(plain_header(), center=(567, 562))
    assert (c.x0, c.y0, c.source) == (567.0, 562.0, SOURCE_IMAGE)


def test_explicit_center_needs_no_header():
    assert resolve_center(None, center=(1.5, 2.5)).x0 == 1.5


@pytest.mark.parametrize("bad", [(1,), (1, 2, 3), "12", (1, "x"),
                                 (float("nan"), 1)])
def test_bad_explicit_center(bad):
    with pytest.raises(CenterError):
        resolve_center(plain_header(), center=bad)


# --- geometric image centre -------------------------------------------------

@pytest.mark.parametrize("ncol,nrow,expect", [
    (1025, 1022, (512.5, 511.0)),   # u12517
    (256, 256, (128.0, 128.0)),
    (1, 1, (0.5, 0.5)),             # the only pixel's centre
])
def test_image_center(ncol, nrow, expect):
    assert image_center(ncol, nrow) == expect
    c = resolve_center(plain_header(ncol, nrow))
    assert (c.x0, c.y0, c.source) == (*expect, SOURCE_AUTO)


# --- physical (IRAF/DS9 LTV/LTM) --------------------------------------------

def test_physical_identity_without_ltv():
    # physical = image; FITS pixel 567.5 -> ELLIPROF 567.0
    assert physical_to_image(567.5, 562.5, plain_header()) == (567.0, 562.0)


def test_physical_subimage_offset():
    # a cut-out starting at physical pixel 101: LTV = -100
    h = plain_header(LTV1=-100.0, LTV2=-50.0)
    assert physical_to_image(150.0, 80.0, h) == (49.5, 29.5)


def test_physical_binned():
    # 2x2 binned image: LTM = 0.5, image = 0.5*phys + 0.5 (IRAF blkavg)
    h = plain_header(LTM1_1=0.5, LTM2_2=0.5, LTV1=0.5, LTV2=0.5)
    assert physical_to_image(10.0, 20.0, h) == (5.0, 10.0)


def test_physical_rotated_ltm_refused():
    with pytest.raises(CenterError, match="rotated"):
        physical_to_image(1, 1, plain_header(LTM1_2=0.1))


def test_physical_mode():
    c = resolve_center(plain_header(LTV1=-10.0),
                       center_physical=(20.5, 5.5))
    assert (c.x0, c.y0, c.source) == (10.0, 5.0, SOURCE_PHYSICAL)
    assert "Converted center: X0=10.0000 Y0=5.0000" in c.describe()


# --- RA/DEC ------------------------------------------------------------------

def test_radec_at_reference_pixel():
    h = tan_header()
    # CRPIX (FITS, 1-based) -> ELLIPROF X0 = CRPIX - 0.5
    x0, y0 = radec_to_image(188.73658, -12.58242, h)
    assert x0 == pytest.approx(79.5, abs=1e-9)
    assert y0 == pytest.approx(59.5, abs=1e-9)


def test_radec_roundtrip_offset_position():
    from astropy.wcs import WCS
    h = tan_header()
    ra, dec = WCS(h).pixel_to_world_values(140.25, 30.75)  # 0-based
    x0, y0 = radec_to_image(float(ra), float(dec), h)
    assert (x0, y0) == pytest.approx((140.75, 31.25), abs=1e-7)


def test_sexagesimal_equals_decimal():
    h = tan_header(crval=(188.73658, -12.58242))
    a = radec_to_image(188.73658, -12.58242, h)
    b = radec_to_image("12:34:56.7792", "-12:34:56.712", h)
    c = radec_to_image("12h34m56.7792s", "-12d34m56.712s", h)
    assert b == pytest.approx(a, abs=1e-6)
    assert c == pytest.approx(a, abs=1e-6)


def test_decimal_strings():
    h = tan_header()
    assert radec_to_image("188.73658", "-12.58242", h) == \
        pytest.approx((79.5, 59.5), abs=1e-9)


def test_numbers_use_the_wcs_frame():
    # EQUINOX 2000 without RADESYS is FK5: numbers are read in FK5, so
    # CRVAL maps to CRPIX exactly (ICRS input would be ~20 mas off).
    h = tan_header()
    h["EQUINOX"] = 2000.0
    assert radec_to_image(188.73658, -12.58242, h) == \
        pytest.approx((79.5, 59.5), abs=1e-9)


def test_skycoord_in_another_frame_is_transformed():
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    h = tan_header(radesys="ICRS")
    icrs = SkyCoord(188.73658 * u.deg, -12.58242 * u.deg, frame="icrs")
    gal = icrs.galactic
    assert radec_to_image(gal, None, h) == \
        pytest.approx((79.5, 59.5), abs=1e-6)
    c = resolve_center(h, center_radec=gal)
    assert c.source == SOURCE_RADEC


def test_radec_without_wcs_fails():
    with pytest.raises(CenterError, match="no celestial WCS"):
        resolve_center(plain_header(), center_radec=(10.0, 20.0))


def test_radec_invalid_string():
    with pytest.raises(CenterError, match="cannot parse"):
        radec_to_image("12:xx:00", "10", tan_header())


def test_radec_mode_describe():
    c = resolve_center(tan_header(), center_radec=("188.73658",
                                                   "-12.58242"))
    text = c.describe()
    assert "Center source: RA/DEC" in text
    assert "Input: 188.73658 -12.58242" in text
    assert "Converted center: X0=79.5000 Y0=59.5000" in text


# --- mode selection ----------------------------------------------------------

@pytest.mark.parametrize("kwargs", [
    dict(center=(1, 2), center_physical=(1, 2)),
    dict(center=(1, 2), center_radec=(1, 2)),
    dict(center_physical=(1, 2), center_radec=(1, 2)),
])
def test_only_one_mode(kwargs):
    with pytest.raises(CenterError, match="only one"):
        resolve_center(tan_header(), **kwargs)


def test_no_centers_dat_lookup(tmp_path, monkeypatch):
    # centers.dat has no special meaning, even next to the image
    (tmp_path / "centers.dat").write_text("img 10 20\n")
    monkeypatch.chdir(tmp_path)
    c = resolve_center(plain_header(100, 60))
    assert (c.x0, c.y0, c.source) == (50.0, 30.0, SOURCE_AUTO)
