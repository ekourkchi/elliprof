"""Image geometry is checked before anything is allocated or fitted.

An axis of length 0 is legal FITS, but there is no image to fit.  It is
also what a mis-sized CFITSIO Fortran wrapper returns: CFITSIO 4.7.0 on
riscv64 (without the f77_wrap.h fix in tools/ci/build_cfitsio.sh) read a
256 x 256 image as 256 x 0, and the backend then hung (single) or fitted
garbage (double).  Both dispatch paths must stop with a clean error.
"""

import subprocess

import numpy as np
import pytest

pytestmark = pytest.mark.native

GOOD = ["X0=127.3", "Y0=121.6", "R0=3", "R1=90", "NR=30"]
PRECISIONS = ["single", "double", "auto"]


def card(key, value):
    return f"{key:<8}= {value:>20}".ljust(80)


def header_only_fits(path, naxes, extension=False):
    """A FITS file whose image HDU has the given axes and no data.

    Written byte by byte (not with astropy) so that the axis lengths are
    exactly those asked for, zeros included.  With extension=True the
    image is an IMAGE extension behind an empty primary HDU.
    """
    def block(cards):
        text = "".join(cards) + "END".ljust(80)
        return text.ljust(-(-len(text) // 2880) * 2880).encode("ascii")

    axes = [card(f"NAXIS{i}", n) for i, n in enumerate(naxes, 1)]
    image = [card("BITPIX", -32), card("NAXIS", len(naxes)), *axes]
    if extension:
        primary = [card("SIMPLE", "T"), card("BITPIX", 8),
                   card("NAXIS", 0), card("EXTEND", "T")]
        ext = [card("XTENSION", "'IMAGE   '"), *image,
               card("PCOUNT", 0), card("GCOUNT", 1)]
        data = block(primary) + block(ext)
    else:
        data = block([card("SIMPLE", "T"), *image])
    # an empty axis means no data unit; otherwise fill it with zeros
    n = int(np.prod(naxes)) if naxes else 0
    if n:
        pix = np.zeros(n, ">f4").tobytes()
        data += pix + b"\0" * (-len(pix) % 2880)
    path.write_bytes(data)
    return path


def run(native, *args):
    # an invalid image must fail at once, never hang: a short timeout
    return subprocess.run([str(native), *map(str, args)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=60)


@pytest.mark.parametrize("prec", PRECISIONS)
@pytest.mark.parametrize("naxes,shown", [
    ((0, 256), "0 x 256"),
    ((256, 0), "256 x 0"),
    ((0, 0), "0 x 0"),
    ((256, 256, 0), "256 x 256 x 0"),
])
def test_empty_axes_are_refused(native, tmp_path, naxes, shown, prec):
    img = header_only_fits(tmp_path / "empty.fits", naxes)
    out = tmp_path / "x.prf"
    p = run(native, img, *GOOD, "--sky", 100, "-o", out, "-m",
            tmp_path / "m.fits", "--precision", prec)
    assert p.returncode == 1
    assert p.stderr.strip().endswith(
        f"selected FITS image has invalid dimensions ({shown})")
    assert "SURFACE PHOTOMETRY" not in p.stdout
    assert not out.exists() and not (tmp_path / "m.fits").exists()


@pytest.mark.parametrize("prec", PRECISIONS)
def test_empty_extension_is_refused(native, tmp_path, prec):
    img = header_only_fits(tmp_path / "ext.fits", (256, 0), extension=True)
    p = run(native, f"{img}[1]", *GOOD, "--precision", prec)
    assert p.returncode == 1
    assert "selected FITS image has invalid dimensions (256 x 0)" \
        in p.stderr


@pytest.mark.parametrize("prec", ["single", "double"])
def test_empty_sky_image_is_refused(native, galaxy_fits, tmp_path, prec):
    sky = header_only_fits(tmp_path / "sky.fits", (256, 0))
    p = run(native, galaxy_fits, *GOOD, "--sky-image", sky,
            "--precision", prec, "-o", tmp_path / "x.prf")
    assert p.returncode == 1
    assert "sky.fits: selected FITS image has invalid dimensions " \
        "(256 x 0)" in p.stderr


# The established dimensional rules still apply in every precision path.
@pytest.mark.parametrize("prec", PRECISIONS)
@pytest.mark.parametrize("naxes,message", [
    ((), "the selected HDU has no 2-D image (NAXIS = 0)"),
    ((50,), "the selected HDU has no 2-D image (NAXIS = 1)"),
    ((8, 6, 3), "is not a 2-D image (NAXIS = 3, NAXIS3 = 3)"),
])
def test_dimensional_rules(native, tmp_path, naxes, message, prec):
    img = header_only_fits(tmp_path / "img.fits", naxes)
    p = run(native, img, *GOOD, "--precision", prec)
    assert p.returncode == 1
    assert message in p.stderr
    assert "invalid dimensions" not in p.stderr


@pytest.mark.parametrize("prec", ["single", "double"])
def test_one_pixel_axes_are_accepted(native, tmp_path, prec):
    # the guard is >= 1, not > 1: a degenerate third axis stays a 2-D image
    img = header_only_fits(tmp_path / "deg.fits", (8, 6, 1))
    p = run(native, img, "X0=4", "Y0=3", "R0=1", "R1=2", "NR=2",
            "--precision", prec)
    assert "invalid dimensions" not in p.stderr
    assert "is not a 2-D image" not in p.stderr
