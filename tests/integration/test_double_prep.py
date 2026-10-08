"""The double backend's image preparation (--precision double):
reading in double, --sky / --sky-image subtracted in double, the mask,
the prepared product (BITPIX -64, physical units) and the normalization
exponent.  Compared with independent float64 arithmetic (numpy)."""

import re

import numpy as np
import pytest

from helpers import EXAMPLE

fits = pytest.importorskip("astropy.io.fits")

NORM = re.compile(r"Normalization: fit on image x 2\*\*\(-k\), k = (-?\d+) "
                  r"\(preferred (-?\d+), safe (-?\d+) to (-?\d+)\)")


def write(path, data, dtype=np.float64, header=None):
    hdu = fits.PrimaryHDU(np.asarray(data, dtype=dtype))
    for k, v in (header or {}).items():
        hdu.header[k] = v
    hdu.writeto(path, overwrite=True)
    return path


def prepare(run_native, tmp_path, image, *extra, name="p"):
    out = tmp_path / f"{name}.fits"
    p = run_native(image, "--precision", "double", "--prepared", out,
                   "--prepare-only", *extra)
    assert p.returncode == 0, p.stderr
    with fits.open(out) as h:
        assert h[0].header["BITPIX"] == -64
        data = h[0].data.astype(np.float64)
        history = [str(c) for c in h[0].header["HISTORY"]]
    m = NORM.search(p.stdout)
    assert m, p.stdout
    return data, history, tuple(int(g) for g in m.groups()), p.stdout


def exponent(v):
    """Fortran EXPONENT: v = f * 2**e, 0.5 <= |f| < 1."""
    return int(np.frexp(v)[1])


def expected_k(prepared, linear=False):
    v = np.abs(prepared[np.isfinite(prepared) & (prepared != 0)])
    if v.size == 0:
        return 0, 0, 0, 0
    v = np.sort(v)
    kp = exponent(v[-1]) if linear else exponent(v[(v.size + 1) // 2 - 1])
    kmin = exponent(v[-1]) - 1024
    kmax = exponent(v[0]) + 1073
    return min(max(kp, kmin), kmax), kp, kmin, kmax


def test_u12517_prepared_is_exact(run_native, tmp_path):
    data, history, k, out = prepare(
        run_native, tmp_path, EXAMPLE / "u12517j.fits",
        "--mask", EXAMPLE / "u12517j.dmask", "--sky", "3246.0")
    raw = fits.getdata(EXAMPLE / "u12517j.fits").astype(np.float64)
    good = data != 0
    assert np.array_equal(data[good], raw[good] - 3246.0)
    assert (~good).sum() == 103402
    assert "elliprof precision: double (IEEE-754 binary64)" in history
    assert f"elliprof normalization: k={k[0]} preferred={k[1]} " \
        "clamped=no" in history
    assert k == expected_k(data)
    assert "Precision: double (IEEE-754 binary64); requested double" in out


@pytest.mark.parametrize("scale", [1e-300, 1e-200, 1e-100, 1e-50, 1.0,
                                   1e50, 1e100, 1e200, 1e300])
def test_full_range_values_and_sky(run_native, tmp_path, scale):
    rng = np.random.default_rng(1)
    img = scale * (1 + rng.random((40, 50)))
    sky = scale * 0.25
    path = write(tmp_path / "s.fits", img)
    data, _, k, _ = prepare(run_native, tmp_path, path, "--sky", repr(sky))
    assert np.array_equal(data, img - sky)
    assert k == expected_k(img - sky)
    # internal values near 1: the lower median lies in [0.5, 1)
    inner = np.abs(np.ldexp(data, -k[0]))
    assert 0.5 <= np.sort(inner.ravel())[(inner.size + 1) // 2 - 1] < 1


def test_sky_image_in_double(run_native, tmp_path):
    rng = np.random.default_rng(2)
    img = 1e250 * (1 + rng.random((30, 30)))
    sky = 1e249 * rng.random((30, 30))
    write(tmp_path / "s.fits", img)
    write(tmp_path / "b.fits", sky)
    data, _, _, out = prepare(run_native, tmp_path, tmp_path / "s.fits",
                              "--sky-image", tmp_path / "b.fits")
    assert np.array_equal(data, img - sky)
    assert "Sky: subtracted image" in out


def test_cancellation_is_that_of_float64(run_native, tmp_path):
    """sky ~1e200 with a galaxy ~1e195 on it: the difference is what
    binary64 gives (spacing of 1e200 is about 2.9e184)."""
    sky = 1e200
    img = sky + 1e195 * np.linspace(0, 1, 400).reshape(20, 20)
    data, _, _, _ = prepare(run_native, tmp_path,
                            write(tmp_path / "c.fits", img),
                            "--sky", repr(sky))
    assert np.array_equal(data, img - sky)
    assert np.spacing(sky) < 1e185


@pytest.mark.parametrize("values", [
    [2**31, 2**32, 2**53 - 1, 2**53, 2**53 + 1, -(2**62), 2**63 - 1,
     -(2**63)],
])
def test_int64_read_like_float64(run_native, tmp_path, values):
    img = np.array(values * 4, dtype=np.int64).reshape(4, len(values))
    path = write(tmp_path / "i.fits", img, dtype=np.int64)
    data, _, _, out = prepare(run_native, tmp_path, path)
    assert np.array_equal(data, img.astype(np.float64))
    assert "Image: BITPIX 64 read in double precision" in out


def test_int64_bscale_bzero_and_unsigned(run_native, tmp_path):
    # unsigned 64-bit convention (BZERO = 2**63) and a scaled image
    u = np.array([[0, 1, 2**53 + 1, 2**64 - 1]], dtype=np.uint64)
    fits.PrimaryHDU(u).writeto(tmp_path / "u.fits")
    data, _, _, _ = prepare(run_native, tmp_path, tmp_path / "u.fits")
    assert np.array_equal(data, u.astype(np.float64))
    raw = np.array([[1, -7, 2**40, -(2**50)]], dtype=np.int64)
    write(tmp_path / "b.fits", raw, dtype=np.int64,
          header={"BSCALE": 1e-250, "BZERO": 3.5e-249})
    data, _, _, _ = prepare(run_native, tmp_path, tmp_path / "b.fits",
                            name="b")
    with fits.open(tmp_path / "b.fits") as h:
        ref = h[0].data.astype(np.float64)     # astropy, in float64
    assert np.array_equal(data, ref)


def test_subnormal_values_survive(run_native, tmp_path):
    img = np.array([[5e-324, 1e-310, 2.2e-308, 1.0]])
    data, _, k, _ = prepare(run_native, tmp_path,
                            write(tmp_path / "d.fits", img))
    assert np.array_equal(data, img)
    assert k == expected_k(img)
    # no nonzero value becomes 0 or Inf internally
    inner = np.ldexp(data, -k[0])
    assert np.all(inner != 0) and np.all(np.isfinite(inner))


def test_clamping_keeps_every_value(run_native, tmp_path):
    """Values from 1e-320 to 1e308: the median exponent is not safe."""
    img = np.array([[1e-320] + [1e300] * 5 + [1.7e308]])
    data, _, k, out = prepare(run_native, tmp_path,
                              write(tmp_path / "x.fits", img))
    assert k == expected_k(img)
    assert k[0] != k[1]
    assert "clamped into the safe range" in out
    inner = np.ldexp(data, -k[0])
    assert np.all(inner != 0) and np.all(np.isfinite(inner))


def test_linear_prefers_the_largest_value(run_native, tmp_path):
    rng = np.random.default_rng(3)
    img = 1e40 * rng.random((20, 20)) + 1e40
    data, _, k, _ = prepare(run_native, tmp_path,
                            write(tmp_path / "l.fits", img), "LINEAR")
    assert k == expected_k(img, linear=True)
    assert np.abs(np.ldexp(data, -k[0])).max() < 1


def test_no_nonzero_pixel_means_k0(run_native, tmp_path):
    _, _, k, out = prepare(run_native, tmp_path,
                           write(tmp_path / "z.fits", np.zeros((8, 8))))
    assert k == (0, 0, 0, 0)
    assert "no finite nonzero pixel" in out


@pytest.mark.parametrize("sky, msg", [
    ("1e400", "outside the range of double precision"),
    ("1e-400", "outside the range of double precision"),
    ("abc", "needs one finite number"),
    ("1.5 junk", "needs one finite number"),
    ("nan", "needs one finite number"),
    ("inf", "needs one finite number"),
])
def test_sky_parsing_errors(run_native, tmp_path, sky, msg):
    path = write(tmp_path / "s.fits", np.ones((8, 8)))
    p = run_native(path, "--precision", "double", "--sky", sky,
                   "--prepared", tmp_path / "p.fits", "--prepare-only")
    assert p.returncode == 1
    assert "error (double precision, sky)" in p.stderr and msg in p.stderr


def test_sky_parsing_is_exact(run_native, tmp_path):
    path = write(tmp_path / "s.fits", np.zeros((4, 4)))
    for sky in ("0.1", "-1.5D-3", "2.4703282292062328e-323", "1e+300",
                "1.7976931348623157e308", "3246"):
        data, _, _, _ = prepare(run_native, tmp_path, path, "--sky", sky)
        assert np.all(data == -float(sky.replace("D", "e")))


def test_overflow_in_sky_subtraction_is_an_error(run_native, tmp_path):
    path = write(tmp_path / "s.fits", np.full((4, 4), 1.7e308))
    p = run_native(path, "--precision", "double", "--sky", "-1e308",
                   "--prepared", tmp_path / "p.fits", "--prepare-only")
    assert p.returncode == 1
    assert "error (double precision, sky)" in p.stderr
    assert "beyond the double range at 16 pixel(s)" in p.stderr


def test_mask_applied_in_double(run_native, tmp_path):
    img = np.full((6, 6), 1e-300)
    mask = np.ones((6, 6))
    mask[2, 3] = 0
    write(tmp_path / "s.fits", img)
    write(tmp_path / "m.fits", mask, dtype=np.int16)
    data, _, _, _ = prepare(run_native, tmp_path, tmp_path / "s.fits",
                            "--mask", tmp_path / "m.fits")
    assert data[2, 3] == 0 and (data != 0).sum() == 35
    assert np.all(data[data != 0] == 1e-300)


def test_gc_and_unknown_precision_refused(run_native, tmp_path):
    path = write(tmp_path / "s.fits", np.ones((8, 8)))
    p = run_native(path, "--precision", "double", "GC", "X0=4", "Y0=4",
                   "NR=3", "-o", tmp_path / "o.dat")
    assert p.returncode == 1
    assert "double-precision GC mode is not yet supported" in p.stderr
    p = run_native(path, "--precision", "quad", "X0=4", "Y0=4")
    assert p.returncode == 1 and "--precision must be" in p.stderr


def test_memory_estimate_with_verbose(run_native, tmp_path):
    """Per-pixel arrays: 8 (image) + 4 (mask; --nonfinite mask is the
    default) bytes, plus 8 for --residual and 12 while a mask file is
    read: 32 bytes per pixel with a mask and a residual."""
    path = write(tmp_path / "s.fits", np.ones((100, 200)))
    p = run_native(path, "--precision", "double", "--verbose",
                   "--prepared", tmp_path / "p.fits", "--prepare-only")
    assert p.returncode == 0
    assert "Memory: about 0.2 MiB for the per-pixel arrays (baseline; " \
        "peak use is higher)" in p.stdout                 # 12 B/pixel
    write(tmp_path / "m.fits", np.ones((100, 200)), dtype=np.int16)
    p = run_native(path, "--precision", "double", "--verbose", "--mask",
                   tmp_path / "m.fits", "X0=100", "Y0=50", "R0=3",
                   "R1=40", "NR=5", "--residual", tmp_path / "r.fits")
    assert p.returncode == 0, p.stderr
    assert "Memory: about 0.6 MiB" in p.stdout     # 20000 x 32 B
