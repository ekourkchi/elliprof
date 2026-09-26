"""FITS input and output of the backend: HDU selection, logical masks of
every type, and the model / prepared / residual images with the header
and WCS of the selected science HDU.  Everything here is done by the
backend (CFITSIO); astropy is used only to build and check files."""

import subprocess
import warnings

import numpy as np
import pytest

from elliprof import GeometryError, cli, read_prf, run_elliprof, \
    write_bitmap_mask
from helpers import ROOT

fits = pytest.importorskip("astropy.io.fits")
WCS = pytest.importorskip("astropy.wcs").WCS

FIT = ["X0=70.3", "Y0=60.6", "R0=3", "R1=40", "NR=12"]
SHAPE = (120, 140)                               # rows, cols


def galaxy(x0, y0, amp):
    yy, xx = np.mgrid[0:SHAPE[0], 0:SHAPE[1]]
    r = np.hypot(xx + 0.5 - x0, (yy + 0.5 - y0) / 0.7)
    return (amp * np.exp(-7.669 * ((np.maximum(r, 0.5) / 15.0) ** 0.25 - 1))
            + 50).astype(np.float32)


def wcs_header(crval1, crval2, crpix):
    h = fits.Header()
    h.update(CTYPE1="RA---TAN", CTYPE2="DEC--TAN", CRVAL1=crval1,
             CRVAL2=crval2, CRPIX1=crpix[0], CRPIX2=crpix[1],
             CD1_1=-2.0e-4, CD1_2=1.0e-5, CD2_1=1.5e-5, CD2_2=2.0e-4,
             RADESYS="ICRS", EQUINOX=2000.0, BUNIT="electrons/s",
             OBSERVER="test")
    return h


@pytest.fixture(scope="module")
def files(tmp_path_factory):
    d = tmp_path_factory.mktemp("fitsio")
    prim = fits.PrimaryHDU(header=wcs_header(10.0, -5.0, (1, 1)))
    sci = fits.ImageHDU(galaxy(70.3, 60.6, 300.0),
                        header=wcs_header(150.1, 2.2, (70, 60)), name="SCI")
    alt = fits.ImageHDU(galaxy(40.2, 50.1, 900.0),
                        header=wcs_header(33.3, 44.4, (10, 20)), name="ALT")
    tab = fits.BinTableHDU.from_columns(
        [fits.Column(name="a", format="E", array=np.arange(3.0))],
        name="TAB")
    fits.HDUList([prim, sci, alt, tab]).writeto(d / "multi.fits")
    fits.PrimaryHDU(galaxy(70.3, 60.6, 300.0),
                    header=wcs_header(150.1, 2.2, (70, 60))).writeto(
        d / "single.fits")
    m = np.ones(SHAPE, np.int16)
    m[10:20, 100:120] = 0
    fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(m, name="MASK"),
                  fits.ImageHDU(np.full(SHAPE, 50, np.float32), name="SKY"),
                  fits.ImageHDU(np.ones((100, 140), np.int16),
                                name="SMALL")]).writeto(d / "prod.fits")
    return d


def run(native, *args):
    return subprocess.run([str(native), *map(str, args)],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)


def profile(path):
    p = read_prf(str(path))
    return p["n"], np.asarray(p["params"])


def sky(header, pts):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return WCS(header).all_pix2world(pts, 0)


PTS = np.array([(3.2, 4.1), (70.0, 60.0), (135.5, 117.9)])


# ---- HDU selection

@pytest.mark.parametrize("selector", ["[SCI]", "[1]", "[sci]"])
def test_selected_hdu_is_fitted(native, files, tmp_path, selector):
    p = run(native, f"{files}/multi.fits{selector}", *FIT,
            "-o", tmp_path / "a.prf")
    assert p.returncode == 0, p.stderr
    assert "140 cols x   120 rows" in p.stdout
    q = run(native, files / "single.fits", *FIT, "-o", tmp_path / "b.prf")
    na, pa = profile(tmp_path / "a.prf")
    nb, pb = profile(tmp_path / "b.prf")
    assert na == nb == 12 and np.array_equal(pa, pb)   # the SCI pixels


def test_other_extension_is_a_different_galaxy(native, files, tmp_path):
    run(native, f"{files}/multi.fits[SCI]", *FIT, "-o", tmp_path / "s.prf")
    p = run(native, f"{files}/multi.fits[ALT]", "X0=40.2", "Y0=50.1",
            "R0=3", "R1=30", "NR=10", "-o", tmp_path / "a.prf")
    assert p.returncode == 0, p.stderr
    assert not np.array_equal(profile(tmp_path / "s.prf")[1][:10],
                              profile(tmp_path / "a.prf")[1][:10])


@pytest.mark.parametrize("selector,message", [
    ("", "the selected HDU has no 2-D image (NAXIS = 0)"),
    ("[TAB]", "the selected HDU is a table, not an image"),
    ("[NOPE]", "cannot open"),
    ("[9]", "cannot open"),
])
def test_bad_hdu_selection_fails_without_fallback(native, files, tmp_path,
                                                  selector, message):
    p = run(native, f"{files}/multi.fits{selector}", *FIT,
            "-o", tmp_path / "x.prf")
    assert p.returncode == 1 and message in p.stderr
    assert not (tmp_path / "x.prf").exists()


def test_mask_and_sky_image_hdu_selection(native, files, tmp_path):
    p = run(native, f"{files}/multi.fits[SCI]", *FIT,
            "--mask", f"{files}/prod.fits[MASK]",
            "--sky-image", f"{files}/prod.fits[SKY]",
            "--prepared", tmp_path / "p.fits", "-o", tmp_path / "x.prf")
    assert p.returncode == 0, p.stderr
    sci = fits.getdata(files / "multi.fits", "SCI")
    m = fits.getdata(files / "prod.fits", "MASK") != 0
    assert np.array_equal(fits.getdata(tmp_path / "p.fits"),
                          np.where(m, sci - np.float32(50), np.float32(0)))


def test_wrong_size_mask_hdu(native, files, tmp_path):
    p = run(native, f"{files}/multi.fits[SCI]", *FIT,
            "--mask", f"{files}/prod.fits[SMALL]", "-o", tmp_path / "x.prf")
    assert p.returncode == 1
    assert "mask dimensions (140 x 100) do not match science image " \
        "dimensions (140 x 120)" in p.stderr
    assert not (tmp_path / "x.prf").exists()


# ---- header / WCS of the generated images

@pytest.mark.parametrize("ext,center", [("SCI", ("70.3", "60.6")),
                                        ("ALT", ("40.2", "50.1"))])
def test_products_carry_the_selected_hdu_header(native, files, tmp_path,
                                                ext, center):
    p = run(native, f"{files}/multi.fits[{ext}]", f"X0={center[0]}",
            f"Y0={center[1]}", "R0=3", "R1=30", "NR=10", "MODEL",
            "-m", tmp_path / "m.fits", "--prepared", tmp_path / "p.fits",
            "--residual", tmp_path / "r.fits", "-o", tmp_path / "x.prf")
    assert p.returncode == 0, p.stderr
    src = fits.getheader(files / "multi.fits", ext)
    primary = fits.getheader(files / "multi.fits", 0)
    for name, product in (("m", "MODEL"), ("p", "PREPARED"),
                          ("r", "RESIDUAL")):
        with fits.open(tmp_path / f"{name}.fits") as hdul:
            hdul.verify("exception")                     # valid FITS
            h = hdul[0].header
        assert h["BITPIX"] == -32 and h["NAXIS"] == 2
        assert (h["NAXIS1"], h["NAXIS2"]) == (140, 120)
        for key in ("CTYPE1", "CTYPE2", "CRVAL1", "CRVAL2", "CRPIX1",
                    "CRPIX2", "CD1_1", "CD1_2", "CD2_1", "CD2_2", "RADESYS",
                    "EQUINOX", "BUNIT", "OBSERVER"):
            assert h[key] == src[key], key
        assert "XTENSION" not in h and "EXTNAME" not in h
        assert np.array_equal(sky(h, PTS), sky(src, PTS))
        assert not np.allclose(sky(h, PTS), sky(primary, PTS))
        assert any(product in str(c) for c in h["HISTORY"])


def test_integer_science_image_gives_float_products(native, tmp_path):
    img = np.round(galaxy(70.3, 60.6, 300.0)).astype(np.int16)
    h = wcs_header(150.1, 2.2, (70, 60))
    h["BSCALE"] = 1.0
    h["BZERO"] = 0.0
    h["BLANK"] = -32768
    h["DATAMIN"] = 0
    fits.PrimaryHDU(img, header=h).writeto(tmp_path / "int.fits")
    p = run(native, tmp_path / "int.fits", *FIT, "MODEL",
            "-m", tmp_path / "m.fits", "-o", tmp_path / "x.prf")
    assert p.returncode == 0, p.stderr
    out = fits.getheader(tmp_path / "m.fits")
    assert out["BITPIX"] == -32
    for key in ("BSCALE", "BZERO", "BLANK", "DATAMIN"):
        assert key not in out, key
    assert out["CRVAL1"] == 150.1


# ---- masks: logical, any representation

def _masks(tmp_path, bad):
    rng = np.random.default_rng(3)
    good_int = np.array([1, 2, -1, 7, 100])
    good_flt = np.array([1, 2, -1, 0.25, -3.7, 1e-30])
    pick = lambda v: v[rng.integers(0, len(v), bad.shape)]    # noqa: E731
    out = {}
    for name, dtype, vals in (("uint8", np.uint8, np.array([1, 2, 255])),
                              ("int16", np.int16, good_int),
                              ("int32", np.int32, good_int),
                              ("int64", np.int64,
                               np.array([1, -1, 2 ** 40]))):
        fits.PrimaryHDU(np.where(bad, 0, pick(vals)).astype(dtype)).writeto(
            tmp_path / f"{name}.fits")
        out[name] = tmp_path / f"{name}.fits"
    f32 = np.where(bad, 0, pick(good_flt)).astype(np.float32)
    f32[bad & (rng.random(bad.shape) < 0.5)] = np.nan
    f32[bad & (rng.random(bad.shape) < 0.2)] = -np.inf
    fits.PrimaryHDU(f32).writeto(tmp_path / "float32.fits")
    out["float32"] = tmp_path / "float32.fits"
    fits.PrimaryHDU(np.where(bad, np.nan, pick(good_flt))).writeto(
        tmp_path / "float64.fits")
    out["float64"] = tmp_path / "float64.fits"
    h = fits.Header()
    h["BLANK"] = -32768
    fits.PrimaryHDU(np.where(bad, -32768, pick(good_int)).astype(np.int16),
                    header=h).writeto(tmp_path / "blank.fits")
    out["int16 BLANK"] = tmp_path / "blank.fits"
    write_bitmap_mask(str(tmp_path / "m.dmask"), (~bad).astype(np.uint8))
    out["dmask"] = tmp_path / "m.dmask"
    return out


def test_all_mask_types_are_the_same_logical_mask(native, tmp_path):
    image = ROOT / "tests" / "data" / "regression" / "star.fits"
    shape = fits.getdata(image).shape
    bad = np.zeros(shape, bool)
    bad[50:66, 140:160] = True
    bad[np.random.default_rng(2).random(shape) < 0.03] = True
    results = {}
    for name, mfile in _masks(tmp_path, bad).items():
        p = run(native, image, "--mask", mfile, "X0=100.3", "Y0=99.6",
                "R0=3", "R1=80", "NR=25", "-o", tmp_path / f"{name}.prf",
                "--prepared", tmp_path / f"{name}_p.fits")
        assert p.returncode == 0, (name, p.stderr)
        assert f"{int(bad.sum())} pixels masked" in p.stdout, name
        results[name] = (profile(tmp_path / f"{name}.prf")[1],
                         fits.getdata(tmp_path / f"{name}_p.fits"))
    ref = results["dmask"]
    for name, (prf, prep) in results.items():
        assert np.array_equal(prf, ref[0]), name
        assert np.array_equal(prep, ref[1]), name


def test_unreadable_mask_names_the_supported_forms(native, tmp_path):
    img = tmp_path / "img.fits"
    fits.PrimaryHDU(np.ones((10, 10), np.float32)).writeto(img)
    (tmp_path / "junk.fits").write_text("not a FITS file")
    p = run(native, img, "X0=5", "Y0=5", "R0=1", "R1=3", "NR=2",
            "--mask", tmp_path / "junk.fits")
    assert p.returncode == 1
    assert "supported masks are a 2-D FITS image of any BITPIX" in p.stderr


# ---- prepared and residual arithmetic

@pytest.mark.parametrize("sky_opts", [[], ["--sky", "37.5"], ["sky-image"]])
def test_prepared_and_residual(native, files, tmp_path, sky_opts):
    sci = fits.getdata(files / "single.fits")
    m = fits.getdata(files / "prod.fits", "MASK") != 0
    if sky_opts == ["sky-image"]:
        skyimg = (np.arange(sci.size, dtype=np.float32).reshape(SHAPE)
                  / 1000 + 20).astype(np.float32)
        fits.PrimaryHDU(skyimg).writeto(tmp_path / "sky.fits")
        sky_opts = ["--sky-image", tmp_path / "sky.fits"]
        expect = sci - skyimg
    elif sky_opts:
        expect = sci + np.float32(-37.5)
    else:
        expect = sci
    p = run(native, files / "single.fits", *FIT, *sky_opts,
            "--mask", f"{files}/prod.fits[MASK]", "MODEL",
            "-m", tmp_path / "m.fits", "--prepared", tmp_path / "p.fits",
            "--residual", tmp_path / "r.fits", "-o", tmp_path / "x.prf")
    assert p.returncode == 0, p.stderr
    prep = fits.getdata(tmp_path / "p.fits")
    model = fits.getdata(tmp_path / "m.fits")
    res = fits.getdata(tmp_path / "r.fits")
    assert np.array_equal(prep, np.where(m, expect, np.float32(0)))
    assert np.array_equal(res[m], (expect - model)[m])
    assert np.all(res[~m] == 0) and not np.any(np.signbit(res[~m]))
    assert np.count_nonzero(model[~m]) == (~m).sum()      # model not masked


@pytest.mark.parametrize("harmonics", [[], ["COS3X=0", "COS4X=0"],
                                       ["COS3X=0", "COS4X=2"],
                                       ["COS3X=1", "COS4X=1"],
                                       ["COS3X=-2"]])
def test_residual_uses_the_saved_model(native, files, tmp_path, harmonics):
    """One model computation feeds -m and --residual, whatever the
    harmonic settings; --residual alone gives the same residual."""
    base = [files / "single.fits", *FIT, *harmonics,
            "--mask", f"{files}/prod.fits[MASK]"]
    p = run(native, *base, "MODEL", "-m", tmp_path / "m.fits",
            "--residual", tmp_path / "r1.fits", "--prepared",
            tmp_path / "p.fits", "-o", tmp_path / "a.prf")
    q = run(native, *base, "--residual", tmp_path / "r2.fits",
            "-o", tmp_path / "b.prf")
    assert p.returncode == q.returncode == 0, p.stderr + q.stderr
    assert "model image not saved" not in q.stderr
    m = fits.getdata(files / "prod.fits", "MASK") != 0
    prep = fits.getdata(tmp_path / "p.fits")
    model = fits.getdata(tmp_path / "m.fits")
    r1 = fits.getdata(tmp_path / "r1.fits")
    assert np.array_equal(r1, np.where(m, prep - model, np.float32(0)),
                          equal_nan=True)
    assert np.array_equal(r1, fits.getdata(tmp_path / "r2.fits"),
                          equal_nan=True)
    assert np.array_equal(profile(tmp_path / "a.prf")[1],
                          profile(tmp_path / "b.prf")[1])


def test_residual_needs_a_fit(native, files, tmp_path):
    p = run(native, files / "single.fits", "--prepare-only", "--prepared",
            tmp_path / "p.fits", "--residual", tmp_path / "r.fits")
    assert p.returncode == 1 and "--residual needs a fit" in p.stderr


# ---- Python API and command line

def test_api_passes_selectors_and_writes_the_residual(files, tmp_path):
    r = run_elliprof(f"{files}/multi.fits[SCI]", 70.3, 60.6, r0=3, r1=40,
                     nr=12, mask=f"{files}/prod.fits[MASK]",
                     sky_image=f"{files}/prod.fits[SKY]",
                     residual_path=tmp_path / "r.fits",
                     output_dir=tmp_path / "o")
    assert r.ok and len(r.profile) == 12
    assert r.residual_path == tmp_path / "r.fits"
    assert r.command[1].endswith("multi.fits[SCI]")
    assert any(c.endswith("prod.fits[MASK]") for c in r.command)
    with pytest.raises(GeometryError, match="mask dimensions"):
        run_elliprof(f"{files}/multi.fits[SCI]", 70.3, 60.6, r0=3, r1=40,
                     nr=12, mask=f"{files}/prod.fits[SMALL]",
                     output_dir=tmp_path / "o2")
    with pytest.raises(FileNotFoundError, match="nothere.fits"):
        run_elliprof(f"{files}/nothere.fits[SCI]", 1, 1, r0=1, r1=2, nr=2)


U12517 = ROOT / "examples" / "u12517"
CANONICAL = [str(U12517 / "u12517j.fits"), "--mask",
             str(U12517 / "u12517j.dmask"), "--sky", "3246.0", "X0=567",
             "Y0=562", "R0=9", "R1=347", "NR=23", "NITER=10", "RMSTAR"]


def test_default_output_is_concise(native, tmp_path, capsys):
    code = cli.main(CANONICAL + [
        "MODEL", "-m", str(tmp_path / "m.fits"), "--prepared",
        str(tmp_path / "p.fits"), "--residual", str(tmp_path / "r.fits"),
        "-o", str(tmp_path / "u.prf"), "--csv", str(tmp_path / "u.csv"),
        "--reg", str(tmp_path / "u.reg")])
    out, err = capsys.readouterr()
    assert code == 0, err
    lines = out.splitlines()
    assert len(lines) < 20, out
    for text in ("modelled", "SURFACE PHOTOMETRY", "FITCONTOUR", "Rmaj",
                 "Synthesize", "function evaluations"):
        assert text not in out + err, text
    for text in ("Image:", "(1025 x 1022)", "Sky:      scalar 3246.0",
                 "103402 pixels masked (9.871%)", "Fit complete: 23 isophotes",
                 "Model:", "Prepared:", "Residual:", "Profile:", "CSV:",
                 "Regions:", "Done."):
        assert text in out, text
    assert "note: 10 isophote fit(s) had too few usable samples" in err


def test_profile_table_shown_once_without_profile_files(tmp_path, capsys):
    assert cli.main(CANONICAL) == 0
    out = capsys.readouterr().out
    assert out.count("Rmaj") == 1 and len(out.splitlines()) < 40


@pytest.mark.parametrize("flag", ["--verbose", "VERBOSE"])
def test_verbose_shows_the_full_output(tmp_path, capsys, flag):
    assert cli.main(CANONICAL + [flag, "-o", str(tmp_path / "u.prf")]) == 0
    out = capsys.readouterr().out
    assert "FITCONTOUR" in out and "Re =" in out and "  r      x0" in out


def test_errors_are_never_hidden(tmp_path, capsys):
    code = cli.main([str(U12517 / "u12517j.fits"), "X0=567", "Y0=562",
                     "R0=9", "R1=347", "NR=23", "--mask",
                     str(U12517 / "u12517j.fits") + "[3]"])
    err = capsys.readouterr().err
    assert code == 1 and "cannot open" in err


# ---- tile-compressed science image

@pytest.mark.parametrize("ctype", ["RICE_1", "GZIP_1"])
def test_tile_compressed_science_image(native, tmp_path, ctype):
    """A tile-compressed image HDU (lossless: integer data) is read by
    CFITSIO like any image: same profile as the same pixels uncompressed,
    and the products carry its WCS but none of the compression-table
    cards."""
    img = np.round(galaxy(70.3, 60.6, 300.0)).astype(np.int32)
    h = wcs_header(150.1, 2.2, (70, 60))
    fits.HDUList([fits.PrimaryHDU(header=wcs_header(10.0, -5.0, (1, 1))),
                  fits.CompImageHDU(img, header=fits.ImageHDU(img, h).header,
                                    name="SCI", compression_type=ctype)
                  ]).writeto(
        tmp_path / "comp.fits")
    fits.PrimaryHDU(img, header=h).writeto(tmp_path / "plain.fits")
    with fits.open(tmp_path / "comp.fits", disable_image_compression=True) \
            as raw:
        assert raw[1].header["ZIMAGE"] and raw[1].header["ZCMPTYPE"] == ctype
    p = run(native, f"{tmp_path}/comp.fits[SCI]", *FIT, "MODEL",
            "-m", tmp_path / "m.fits", "--residual", tmp_path / "r.fits",
            "--prepared", tmp_path / "p.fits", "-o", tmp_path / "c.prf")
    assert p.returncode == 0, p.stderr
    assert "140 cols x   120 rows" in p.stdout
    q = run(native, tmp_path / "plain.fits", *FIT, "MODEL",
            "-m", tmp_path / "m0.fits", "-o", tmp_path / "u.prf")
    assert q.returncode == 0, q.stderr
    assert np.array_equal(profile(tmp_path / "c.prf")[1],
                          profile(tmp_path / "u.prf")[1])
    assert np.array_equal(fits.getdata(tmp_path / "m.fits"),
                          fits.getdata(tmp_path / "m0.fits"))
    assert np.array_equal(fits.getdata(tmp_path / "p.fits"),
                          img.astype(np.float32))
    for name in ("m", "p", "r"):
        with fits.open(tmp_path / f"{name}.fits") as hdul:
            hdul.verify("exception")
            out = hdul[0].header
        assert out["BITPIX"] == -32 and out["NAXIS"] == 2
        assert (out["NAXIS1"], out["NAXIS2"]) == (140, 120)
        assert not [k for k in out if k.startswith("Z") or
                    k in ("TFIELDS", "THEAP") or k.startswith(("TTYPE",
                                                                "TFORM"))]
        assert out["CRVAL1"] == 150.1 and out["BUNIT"] == "electrons/s"
        assert np.array_equal(sky(out, PTS), sky(h, PTS))
