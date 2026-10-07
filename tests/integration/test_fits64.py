"""64-bit FITS science images (0.1.4): BITPIX = -64 and 64.

ELLIPROF computes in 32-bit floating point (REAL*4) and that is not
changed: CFITSIO converts the stored values (after BSCALE/BZERO) to the
nearest 32-bit float as it reads them.  So the same values stored with
different BITPIX give identical results, and a 64-bit value that a
32-bit float cannot hold exactly gives the result of its nearest 32-bit
float -- exactly what numpy's float32 conversion gives.  The products
(model, residual, prepared) stay 32-bit floating point."""

import subprocess

import numpy as np
import pytest

from elliprof import read_prf
from helpers import ROOT, run_cli

fits = pytest.importorskip("astropy.io.fits")

STAR = ROOT / "tests" / "data" / "regression" / "star.fits"
FIT = ["X0=100.3", "Y0=99.6", "R0=3", "R1=80", "NR=25", "NITER=5"]


def native_run(native, *args):
    return subprocess.run([str(native), *map(str, args)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, timeout=600)


def products(native, tmp_path, image, name, *extra):
    out = {k: tmp_path / f"{name}.{k}" for k in ("dat", "p", "m", "r")}
    p = native_run(native, image, *FIT, *extra, "-o", out["dat"],
                   "--prepared", out["p"], "-m", out["m"],
                   "--residual", out["r"])
    assert p.returncode == 0, (name, p.stderr)
    res = [read_prf(str(out["dat"]))]
    for k in ("p", "m", "r"):
        with fits.open(out[k]) as h:
            assert h[0].header["BITPIX"] == -32, (name, k)
            res.append(h[0].data.copy())
    return p, res


def _cards(header):
    """The science header copied into the profile, without BITPIX
    (which records how the input was stored)."""
    cards = [header[i:i + 80] for i in range(0, len(header), 80)]
    return [c for c in cards if not c.startswith("BITPIX")]


def identical(a, b, name, same_header=True):
    # every profile number exactly; the profile also carries a copy of
    # the science header, equal except for its BITPIX card
    pa, pb = a[0], b[0]
    assert pa["n"] == pb["n"] and pa["scale"] == pb["scale"], name
    assert np.array_equal(np.asarray(pa["params"]),
                          np.asarray(pb["params"]), equal_nan=True), name
    if same_header:
        assert _cards(pa["header"]) == _cards(pb["header"]), name
    for x, y, what in zip(a[1:], b[1:], ("prepared", "model", "residual")):
        assert np.array_equal(x, y, equal_nan=True), (name, what)


@pytest.fixture(scope="module")
def sci():
    return fits.getdata(STAR).astype(np.float32)


def test_float32_and_float64_storage_identical(native, tmp_path, sci):
    fits.PrimaryHDU(sci).writeto(tmp_path / "f32.fits")
    fits.PrimaryHDU(sci.astype(np.float64)).writeto(tmp_path / "f64.fits")
    p32, a = products(native, tmp_path, tmp_path / "f32.fits", "f32")
    p64, b = products(native, tmp_path, tmp_path / "f64.fits", "f64")
    identical(a, b, "float64")
    assert "BITPIX -64 converted to 32-bit" in p64.stdout
    assert "converted to 32-bit" not in p32.stdout


def test_float64_values_round_to_nearest_float32(native, tmp_path, sci):
    """Values that need 64 bits: the fit equals that of their nearest
    32-bit floats."""
    rng = np.random.default_rng(11)
    f64 = sci.astype(np.float64) * (1 + rng.uniform(-1e-7, 1e-7, sci.shape))
    assert not np.array_equal(f64, f64.astype(np.float32))
    fits.PrimaryHDU(f64).writeto(tmp_path / "f64.fits")
    fits.PrimaryHDU(f64.astype(np.float32)).writeto(tmp_path / "f32.fits")
    _, a = products(native, tmp_path, tmp_path / "f32.fits", "f32")
    _, b = products(native, tmp_path, tmp_path / "f64.fits", "f64")
    identical(a, b, "rounded float64")


def test_integer_bitpix_all_identical(native, tmp_path, sci):
    """The same integer image as BITPIX 16, 32, 64, -32 and -64."""
    ints = np.round(sci / 2).astype(np.int64)
    assert ints.min() > -32768 and ints.max() < 32767
    res = {}
    for name, dtype in (("i16", np.int16), ("i32", np.int32),
                        ("i64", np.int64), ("f32", np.float32),
                        ("f64", np.float64)):
        fits.PrimaryHDU(ints.astype(dtype)).writeto(tmp_path / f"{name}.fits")
        res[name] = products(native, tmp_path, tmp_path / f"{name}.fits",
                             name)[1]
    for name in res:
        identical(res["f32"], res[name], name)


def test_int64_beyond_float32_precision(native, tmp_path, sci):
    """64-bit integers above 2**24: nearest 32-bit float, as numpy."""
    big = (np.round(sci * 1e6).astype(np.int64) + 2 ** 40 + 1)
    fits.PrimaryHDU(big).writeto(tmp_path / "i64.fits")
    fits.PrimaryHDU(big.astype(np.float32)).writeto(tmp_path / "f32.fits")
    p, a = products(native, tmp_path, tmp_path / "i64.fits", "i64",
                    "--sky", str(float(np.float32(2 ** 40))))
    _, b = products(native, tmp_path, tmp_path / "f32.fits", "f32",
                    "--sky", str(float(np.float32(2 ** 40))))
    identical(a, b, "int64 > 2**24")
    assert "BITPIX 64 converted to 32-bit" in p.stdout


def test_scaled_integers(native, tmp_path, sci):
    """BSCALE/BZERO are applied before the conversion (here exactly)."""
    raw = np.round(sci * 4).astype(np.int64)
    h = fits.Header()
    h["BSCALE"] = 0.25
    h["BZERO"] = 100.0
    hdu = fits.PrimaryHDU(raw, header=h)
    hdu.header["BSCALE"] = 0.25
    hdu.header["BZERO"] = 100.0
    hdu.writeto(tmp_path / "scaled.fits")
    with fits.open(tmp_path / "scaled.fits", do_not_scale_image_data=True) \
            as f:
        assert f[0].header["BITPIX"] == 64 and f[0].header["BSCALE"] == 0.25
    phys = (raw * 0.25 + 100.0).astype(np.float32)
    fits.PrimaryHDU(phys).writeto(tmp_path / "phys.fits")
    _, a = products(native, tmp_path, tmp_path / "scaled.fits", "s")
    _, b = products(native, tmp_path, tmp_path / "phys.fits", "f")
    identical(a, b, "BSCALE/BZERO int64", same_header=False)


def test_float64_in_an_extension_and_compressed(native, tmp_path, sci):
    """'file.fits[SCI]' with a float64 extension, and a losslessly
    tile-compressed float64 image."""
    fits.PrimaryHDU(sci).writeto(tmp_path / "ref.fits")
    fits.HDUList([fits.PrimaryHDU(),
                  fits.ImageHDU(sci.astype(np.float64), name="SCI")]
                 ).writeto(tmp_path / "multi.fits")
    _, ref = products(native, tmp_path, tmp_path / "ref.fits", "ref")
    _, ext = products(native, tmp_path, f"{tmp_path}/multi.fits[SCI]",
                      "ext")
    identical(ref, ext, "[SCI] float64", same_header=False)
    comp = fits.CompImageHDU(sci.astype(np.float64), name="SCI",
                             compression_type="GZIP_1", quantize_level=0.0)
    fits.HDUList([fits.PrimaryHDU(), comp]).writeto(tmp_path / "comp.fits")
    with fits.open(tmp_path / "comp.fits") as f:
        assert np.array_equal(f["SCI"].data, sci.astype(np.float64))
    _, cmp_ = products(native, tmp_path, f"{tmp_path}/comp.fits[SCI]",
                       "cmp")
    identical(ref, cmp_, "compressed float64", same_header=False)


def test_float64_beyond_float32_range_is_refused(native, tmp_path, sci):
    img = sci.astype(np.float64)
    img[0, 0] = 1e40
    fits.PrimaryHDU(img).writeto(tmp_path / "huge.fits")
    p = native_run(native, tmp_path / "huge.fits", *FIT,
                   "-o", tmp_path / "x.dat")
    assert p.returncode != 0
    assert "CFITSIO status" in p.stderr
    assert not (tmp_path / "x.dat").exists()


def test_cli_summary_reports_the_conversion(tmp_path, sci):
    fits.PrimaryHDU(sci.astype(np.float64)).writeto(tmp_path / "f64.fits")
    p = run_cli(tmp_path / "f64.fits", *FIT, "-o", tmp_path / "a.dat")
    assert p.returncode == 0, p.stderr
    assert "BITPIX -64 read as 32-bit float" in p.stdout
