"""Modern multi-extension images, with a synthetic JWST-like file (no
JWST software involved): PRIMARY (no data), SCI (float32, MJy/sr, WCS,
NaN no-data regions), ERR, DQ (uint32 bit flags), VAR_POISSON,
VAR_RNOISE, VAR_FLAT, a second SCI (EXTVER 2), a float64 SCI and a
BINTABLE standing in for the ASDF extension.

elliprof stays generic: it fits the HDU it is given, keeps BUNIT and
the WCS in its products, never uses ERR/VAR for weighting, and reads a
DQ extension only as an ordinary mask (any nonzero flag = bad, with
--mask-convention zero-good)."""

import subprocess
import sys

import numpy as np
import pytest

from helpers import DATA, ROOT

fits = pytest.importorskip("astropy.io.fits")

GAL = DATA / "regression" / "rotated.fits"
FIT = ["X0=100.3", "Y0=99.6", "R0=3", "R1=80", "NR=25", "NITER=5"]
WCS = {"CTYPE1": "RA---TAN", "CTYPE2": "DEC--TAN", "CRVAL1": 53.16,
       "CRVAL2": -27.79, "CRPIX1": 100.5, "CRPIX2": 100.5,
       "PC1_1": -8.7e-6, "PC1_2": 0.0, "PC2_1": 0.0, "PC2_2": 8.7e-6,
       "CUNIT1": "deg", "CUNIT2": "deg"}


def science():
    sci = fits.getdata(GAL).astype(np.float64) * 1e-3     # ~MJy/sr
    sci[:, :60] = np.nan                                  # no data
    sci[138:144, 126:133] = np.nan                        # on isophotes
    return sci


@pytest.fixture(scope="module")
def jwst(tmp_path_factory):
    d = tmp_path_factory.mktemp("jwst")
    sci = science()
    dq = np.zeros(sci.shape, np.uint32)
    dq[~np.isfinite(sci)] = 1 | 512                      # DO_NOT_USE|..
    dq[90:93, 150:153] = 4                                # a flagged spot
    hdr = fits.Header(WCS)
    hdr["BUNIT"] = "MJy/sr"

    def ext(data, name, ver=1, header=None):
        h = fits.ImageHDU(data, header=header, name=name)
        h.header["EXTVER"] = ver
        return h

    prim = fits.PrimaryHDU()
    prim.header["TELESCOP"] = "JWST"
    prim.header["INSTRUME"] = "NIRCAM"
    table = fits.BinTableHDU.from_columns(
        [fits.Column(name="ASDF_METADATA", format="10B",
                     array=np.zeros((1, 10), np.uint8))], name="ASDF")
    hdus = [prim, ext(sci.astype(np.float32), "SCI", header=hdr),
            ext(np.full(sci.shape, 0.01, np.float32), "ERR"),
            ext(dq, "DQ"),
            ext(np.full(sci.shape, 1e-4, np.float32), "VAR_POISSON"),
            ext(np.full(sci.shape, 2e-5, np.float32), "VAR_RNOISE"),
            ext(np.zeros(sci.shape, np.float32), "VAR_FLAT"),
            ext((2 * sci).astype(np.float32), "SCI", ver=2, header=hdr),
            ext(sci, "SCI64", header=hdr), table]
    fits.HDUList(hdus).writeto(d / "cal.fits")
    # the same SCI data and header, alone in a simple file
    fits.PrimaryHDU(sci.astype(np.float32), header=hdr).writeto(
        d / "plain.fits")
    return d


def read_dat(path):
    tok = open(path).read().split(None, 3002)
    n = int(tok[0])
    return np.array([float(t) for t in tok[2:3002]]).reshape(250, 12)[:n]


def fit(run_native, path, out, *args):
    p = run_native(path, *FIT, *args, "-o", out)
    assert p.returncode == 0, p.stderr
    return read_dat(out), p


def test_hdu_selection(run_native, jwst):
    cal = jwst / "cal.fits"
    by_name, p = fit(run_native, f"{cal}[SCI]", jwst / "a.dat",
                     "--nonfinite", "mask")
    assert "Precision: single" in p.stdout
    by_num, _ = fit(run_native, f"{cal}[1]", jwst / "b.dat", "--nonfinite",
                    "mask")
    by_ver, _ = fit(run_native, f"{cal}[SCI,1]", jwst / "c.dat",
                    "--nonfinite", "mask")
    assert np.array_equal(by_name, by_num, equal_nan=True)
    assert np.array_equal(by_name, by_ver, equal_nan=True)
    v2, _ = fit(run_native, f"{cal}[SCI,2]", jwst / "d.dat", "--nonfinite",
                "mask")
    np.testing.assert_allclose(v2[:, 3], 2 * by_name[:, 3], rtol=1e-5)
    v64, p = fit(run_native, f"{cal}[SCI64]", jwst / "e.dat",
                 "--nonfinite", "mask")
    assert "Precision: double (IEEE-754 binary64); requested auto " \
        "(auto: science image BITPIX -64)" in p.stdout
    np.testing.assert_allclose(v64[:, 1:3], by_name[:, 1:3], atol=1e-3)


@pytest.mark.parametrize("spec, msg", [
    ("[ASDF]", "is a table, not an image"),
    ("[0]", "has no 2-D image"),
])
def test_wrong_hdus_are_refused(run_native, jwst, spec, msg):
    p = run_native(f"{jwst / 'cal.fits'}{spec}", *FIT, "-o",
                   jwst / "x.dat")
    assert p.returncode == 1 and msg in p.stderr


def test_err_and_var_are_not_used(run_native, jwst):
    """The fit of cal.fits[SCI] equals that of the SCI data alone."""
    for prec in ("single", "double"):
        a, _ = fit(run_native, f"{jwst / 'cal.fits'}[SCI]", jwst / "a.dat",
                   "--precision", prec)
        b, _ = fit(run_native, jwst / "plain.fits", jwst / "b.dat",
                   "--precision", prec)
        assert np.array_equal(a, b, equal_nan=True)


def test_dq_as_a_mask(run_native, jwst):
    """DQ != 0 = bad (zero-good); NaN pixels carry DO_NOT_USE, so this
    equals --nonfinite mask plus the flagged spot."""
    cal = jwst / "cal.fits"
    a, p = fit(run_native, f"{cal}[SCI]", jwst / "a.dat", "--mask",
               f"{cal}[DQ]", "--mask-convention", "zero-good")
    assert "BITPIX 32" in p.stdout and "warning" not in p.stderr
    ok = np.ones(science().shape, np.int16)
    ok[90:93, 150:153] = 0
    fits.PrimaryHDU(ok).writeto(jwst / "spot.fits", overwrite=True)
    b, _ = fit(run_native, f"{cal}[SCI]", jwst / "b.dat", "--mask",
               jwst / "spot.fits", "--nonfinite", "mask")
    assert np.array_equal(a, b, equal_nan=True)


def test_nonfinite_policies(run_native, jwst):
    """--nonfinite auto (default): mask, except with an explicit
    --precision single (keep: the historical reproduction)."""
    cal = f"{jwst / 'cal.fits'}[SCI]"
    nan = int(np.isnan(science()).sum())
    auto, p = fit(run_native, cal, jwst / "a.dat", "--prepared",
                  jwst / "a.fits")
    assert f"Non-finite: policy mask (auto); NaN {nan}, +Inf 0, -Inf 0; " \
        f"masked {nan}" in p.stdout
    assert "not masked" not in p.stderr
    pa = fits.getdata(jwst / "a.fits")
    assert not np.isnan(pa).any() and (pa == 0).sum() >= nan
    mask, p = fit(run_native, cal, jwst / "m.dat", "--nonfinite", "mask")
    assert "policy mask;" in p.stdout
    assert np.array_equal(auto, mask, equal_nan=True)
    keep, p = fit(run_native, cal, jwst / "k.dat", "--prepared",
                  jwst / "k.fits", "--nonfinite", "keep")
    assert "NaN/Inf science pixel(s) are not masked" in p.stderr
    assert f"policy keep; NaN {nan}, +Inf 0, -Inf 0; masked 0" in p.stdout
    assert np.isnan(fits.getdata(jwst / "k.fits")).sum() == nan
    # log fit: ELLIPROF already skips NaN samples; only the products
    # differ between keep and mask
    assert np.array_equal(keep, mask, equal_nan=True)
    hist, p = fit(run_native, cal, jwst / "h.dat", "--precision",
                  "single")
    assert "policy keep (auto)" in p.stdout
    assert "are not masked" in p.stderr
    p = run_native(cal, *FIT, "--nonfinite", "error", "-o",
                   jwst / "e.dat")
    assert p.returncode == 1
    assert f"(single precision, preparation): {nan} non-finite science " \
        f"pixel(s) are not masked (NaN {nan}, +Inf 0, -Inf 0" in p.stderr


@pytest.mark.parametrize("prec", ["single", "double"])
def test_nonfinite_types_are_counted(run_native, tmp_path, prec):
    img = fits.getdata(GAL).astype(np.float64)
    img[5:7, 5:8] = np.nan
    img[10, 10:14] = np.inf
    img[12, 10] = -np.inf
    # float32 for single: CFITSIO refuses to convert a float64 Inf to
    # float32 (status 412), as before
    fits.PrimaryHDU(img.astype(np.float32 if prec == "single"
                               else np.float64)).writeto(tmp_path / "t.fits")
    p = run_native(tmp_path / "t.fits", *FIT, "--precision", prec, "-o",
                   tmp_path / "t.dat")
    assert p.returncode == 0, p.stderr
    # explicit --precision single: auto means keep (nothing masked)
    masked = 0 if prec == "single" else 11
    assert f"NaN 6, +Inf 4, -Inf 1; masked {masked}" in p.stdout


@pytest.mark.parametrize("prec", ["auto", "double"])
def test_linear_nan_failure_gone_by_default(run_native, tmp_path, prec):
    """LINEAR with NaN regions: with keep, NaN isophotes and a NaN model
    (the 0.1.4 behaviour, still there with --nonfinite keep); the
    default masks them: a finite profile and model."""
    img = science()
    fits.PrimaryHDU(img.astype(np.float32)).writeto(tmp_path / "n.fits")
    out = {}
    for policy in ("auto", "keep"):
        p = run_native(tmp_path / "n.fits", *FIT, "LINEAR", "--precision",
                       prec, "--nonfinite", policy, "-o",
                       tmp_path / f"{policy}.dat", "-m",
                       tmp_path / f"{policy}.fits")
        assert p.returncode == 0, p.stderr
        out[policy] = (read_dat(tmp_path / f"{policy}.dat"),
                       fits.getdata(tmp_path / f"{policy}.fits"))
    prof, model = out["auto"]
    assert np.isfinite(prof[:, :6]).all() and np.isfinite(model).all()
    prof, model = out["keep"]
    assert not np.isfinite(prof[:, :6]).all() and np.isnan(model).any()


@pytest.mark.parametrize("unit", ["electrons", "electrons/s", "DN/s",
                                  "MJy", "MJy/sr"])
@pytest.mark.parametrize("prec", ["single", "double"])
def test_bunit_and_wcs_kept(run_native, tmp_path, unit, prec):
    hdr = fits.Header(WCS)
    hdr["BUNIT"] = unit
    fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(
        fits.getdata(GAL), header=hdr, name="SCI")]).writeto(
        tmp_path / "u.fits")
    out = {k: tmp_path / f"{k}.fits" for k in ("m", "r", "p")}
    p = run_native(f"{tmp_path / 'u.fits'}[SCI]", *FIT, "--precision",
                   prec, "-m", out["m"], "--residual", out["r"],
                   "--prepared", out["p"])
    assert p.returncode == 0, p.stderr
    for path in out.values():
        h = fits.getheader(path)
        assert h["BUNIT"] == unit
        for k, v in WCS.items():
            assert h[k] == v, k
        assert h["BITPIX"] == (-32 if prec == "single" else -64)


def test_no_jwst_software_needed(tmp_path):
    code = (
        "import sys, elliprof\n"
        f"r = elliprof.run_elliprof({str(GAL)!r}, 100.3, 99.6, r0=3, "
        "r1=80, nr=10, load_profile=True)\n"
        "bad = [m for m in ('jwst', 'stdatamodels', 'asdf', 'gwcs', "
        "'crds') if m in sys.modules]\n"
        "assert not bad, bad\n")
    p = subprocess.run([sys.executable, "-c", code], cwd=tmp_path,
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True,
                       env=dict(__import__("os").environ,
                                PYTHONPATH=str(ROOT / "python")))
    assert p.returncode == 0, p.stderr
    deps = (ROOT / "pyproject.toml").read_text().split(
        "[project.optional-dependencies]")[0]
    for name in ("jwst", "stdatamodels", "asdf", "gwcs", "crds"):
        assert f'"{name}' not in deps.lower()


@pytest.mark.parametrize("prec", ["single", "double"])
def test_cubes_are_refused_planes_can_be_selected(run_native, tmp_path,
                                                  prec):
    g = fits.getdata(GAL).astype(np.float32)
    fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(
        np.stack([g, 2 * g, 3 * g]), name="SCI")]).writeto(
        tmp_path / "cube.fits")
    p = run_native(f"{tmp_path / 'cube.fits'}[SCI]", *FIT, "--precision",
                   prec, "-o", tmp_path / "x.dat")
    assert p.returncode == 1
    assert "is not a 2-D image (NAXIS = 3, NAXIS3 = 3)" in p.stderr
    assert not (tmp_path / "x.dat").exists()
    one, _ = fit(run_native, f"{tmp_path / 'cube.fits'}[SCI][*,*,1:1]",
                 tmp_path / "1.dat", "--precision", prec)
    two, _ = fit(run_native, f"{tmp_path / 'cube.fits'}[SCI][*,*,2:2]",
                 tmp_path / "2.dat", "--precision", prec)
    np.testing.assert_allclose(two[:, 3], 2 * one[:, 3], rtol=1e-5)
    # a degenerate third axis (NAXIS3 = 1) is a 2-D image
    fits.PrimaryHDU(g[None]).writeto(tmp_path / "deg.fits")
    deg, _ = fit(run_native, tmp_path / "deg.fits", tmp_path / "3.dat",
                 "--precision", prec)
    assert np.array_equal(deg, one)


def test_python_nonfinite(tmp_path, jwst):
    from elliprof import run_elliprof
    cal = f"{jwst / 'cal.fits'}[SCI]"
    r = run_elliprof(cal, 100.3, 99.6, r0=3, r1=80, nr=25,
                     nonfinite="mask", output_dir=tmp_path)
    assert "--nonfinite" in r.command and "mask" in r.command
    assert "Non-finite:" in r.stdout
    with pytest.raises(ValueError, match="nonfinite must be"):
        run_elliprof(cal, 100.3, 99.6, r0=3, r1=80, nr=25,
                     nonfinite="drop")
