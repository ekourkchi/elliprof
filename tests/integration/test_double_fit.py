"""The double backend's fit (--precision double): agreement with the
single backend where the fit is well conditioned, exact scale
invariance over the whole double range, and the profile file."""

import re

import numpy as np
import pytest

from helpers import DATA, EXAMPLE

fits = pytest.importorskip("astropy.io.fits")

GAL = DATA / "regression" / "rotated.fits"
FIT = ["X0=100.3", "Y0=99.6", "R0=3", "R1=80", "NR=25", "NITER=5"]
U12517 = ["--mask", EXAMPLE / "u12517j.dmask", "--sky", "3246.0",
          "X0=567", "Y0=562", "R0=9", "R1=347", "NR=23", "NITER=10",
          "RMSTAR"]


def read_dat(path):
    """The -o profile without any float32 rounding."""
    text = open(path).read()
    tok = text.split(None, 2 + 3000)
    n = int(tok[0])
    v = np.array([float(t) for t in tok[2:3002]]).reshape(250, 12)
    return n, float(tok[1]), v, tok[3002] if len(tok) > 3002 else ""


def fit(run_native, tmp_path, image, *args, prec="double", name="o"):
    out = tmp_path / f"{name}_{prec}.dat"
    p = run_native(image, *args, "--precision", prec, "-o", out)
    assert p.returncode == 0, p.stderr
    return read_dat(out), p


def test_dat_layout_and_marker(run_native, tmp_path):
    (n, sc, v, head), _ = fit(run_native, tmp_path, GAL, *FIT)
    assert n == 25 and sc == 1.0
    lines = open(tmp_path / "o_double.dat").read().splitlines()
    assert lines[0] == " 25"
    # every number: 18 significant digits, E and a 3-digit exponent
    num = re.compile(r"^-?\d\.\d{17}E[+-]\d{3}$")
    for line in lines[1:752]:
        assert all(num.match(t) for t in line.split()), line
    assert "HISTORY elliprof profile precision: double (IEEE-754 " \
        "binary64)" in head
    assert "HISTORY elliprof profile normalization: k=" in head
    assert head.rstrip().endswith("END")


@pytest.mark.parametrize("image", ["rotated", "elliptical", "offcenter",
                                   "const_sky", "noisy"])
def test_double_agrees_with_single(run_native, tmp_path, image):
    """On well-conditioned synthetic galaxies the two backends differ
    only by float32 rounding."""
    args = list(FIT)
    if image == "offcenter":
        args = ["X0=70.4", "Y0=120.9", "R0=3", "R1=60", "NR=25",
                "NITER=5"]
    if image in ("const_sky", "noisy"):
        args += ["--sky", "250.0" if image == "const_sky" else "50.0"]
    path = DATA / "regression" / f"{image}.fits"
    (n, _, d, _), _ = fit(run_native, tmp_path, path, *args)
    (_, _, s, _), _ = fit(run_native, tmp_path, path, *args,
                          prec="single")
    d, s = d[:n], s[:n]
    tol = 5e-3 if image == "noisy" else 1e-4
    assert np.abs(d[:, 1:3] - s[:, 1:3]).max() < tol           # x0, y0
    assert np.abs(d[:, 5] - s[:, 5]).max() < tol / 10          # ellip
    assert np.abs(d[:, 3] / s[:, 3] - 1).max() < 2e-5          # I0
    assert np.abs(d[:, 10] - s[:, 10]).max() < tol             # slope


def test_u12517_well_conditioned_isophotes_agree(run_native, tmp_path):
    """UGC 12517: isophotes 1-19 agree to float32 rounding; from 20 on
    (R > 240 px) the fit is ill-conditioned (a 1e-4 change of the sky
    moves isophotes 21-23 by more than single and double differ) and
    they only need to exist."""
    img = EXAMPLE / "u12517j.fits"
    (n, _, d, _), _ = fit(run_native, tmp_path, img, *U12517)
    (_, _, s, _), _ = fit(run_native, tmp_path, img, *U12517,
                          prec="single")
    assert n == 23
    assert np.all(np.isfinite(d[:n, :11]))
    d, s = d[:19], s[:19]
    # (single's float32 results vary a little between platforms' libm:
    # isophote 2 differs by 2.5e-4 px on macOS arm64, 1.6e-3 on Linux)
    assert np.abs(d[:, 1:3] - s[:, 1:3]).max() < 5e-3
    assert np.abs(d[:, 3] / s[:, 3] - 1).max() < 1e-5
    assert np.abs(d[:, 5] - s[:, 5]).max() < 1e-4
    assert np.abs(d[:, 4] - s[:, 4]).max() < 2e-3


@pytest.mark.parametrize("linear", [False, True])
@pytest.mark.parametrize("m", [-1000, -600, -200, 200, 600, 1000])
def test_exact_scale_invariance(run_native, tmp_path, m, linear):
    """image x 2**m: the normalized image is the same, so the geometry
    is identical bit for bit and I0 is exactly 2**m times larger."""
    data = fits.getdata(GAL).astype(np.float64)
    fits.PrimaryHDU(np.ldexp(data, m)).writeto(tmp_path / "s.fits")
    extra = ["LINEAR"] if linear else []
    (n, _, ref, _), _ = fit(run_native, tmp_path, GAL, *FIT, *extra,
                            name="ref")
    (n2, _, v, _), _ = fit(run_native, tmp_path, tmp_path / "s.fits",
                           *FIT, *extra, name="s")
    assert n2 == n
    geometry = [0, 1, 2, 4, 5, 6, 7, 8, 9, 10]
    assert np.array_equal(v[:n, geometry], ref[:n, geometry])
    assert np.array_equal(v[:n, 3], np.ldexp(ref[:n, 3], m))
    assert np.array_equal(v[:17, 11], ref[:17, 11])            # flags


def test_sky_keyword_in_physical_units(run_native, tmp_path):
    """SKY= is converted to internal units: the same result for the
    image x 2**m with SKY= x 2**m."""
    data = fits.getdata(DATA / "regression" / "const_sky.fits")
    data = data.astype(np.float64)
    for m in (0, 700):
        fits.PrimaryHDU(np.ldexp(data, m)).writeto(tmp_path / f"{m}.fits")
    (n, _, a, _), pa = fit(run_native, tmp_path, tmp_path / "0.fits",
                           *FIT, "SKY=250", name="a")
    (_, _, b, _), pb = fit(run_native, tmp_path, tmp_path / "700.fits",
                           *FIT, f"SKY={float(np.ldexp(250.0, 700))!r}",
                           name="b")
    assert np.array_equal(a[:n, [0, 1, 2, 4, 5]], b[:n, [0, 1, 2, 4, 5]])
    assert np.array_equal(np.ldexp(a[:n, 3], 700), b[:n, 3])
    # the de Vaucouleurs line is printed in physical units
    ie_a = float(re.search(r"Ie =\s*(\S+)", pa.stdout).group(1))
    ie_b = float(re.search(r"Ie =\s*(\S+)", pb.stdout).group(1))
    assert ie_b / ie_a == pytest.approx(2.0 ** 700, rel=1e-7)


def test_fallback_i0_without_positive_samples(run_native, tmp_path):
    """An isophote whose starting ring has no positive pixel starts from
    I0 = 1000 in physical units, as in single: both backends agree."""
    data = fits.getdata(GAL).astype(np.float64)
    j, i = np.indices(data.shape)
    r = np.hypot(i + 0.5 - 100.3, j + 0.5 - 99.6)
    data[(r > 70) & (r < 90)] = -5.0
    fits.PrimaryHDU(data.astype(np.float32)).writeto(tmp_path / "f.fits")
    args = ["X0=100.3", "Y0=99.6", "R0=3", "R1=80", "NR=25", "NITER=1"]
    (n, _, d, _), _ = fit(run_native, tmp_path, tmp_path / "f.fits",
                          *args)
    (_, _, s, _), _ = fit(run_native, tmp_path, tmp_path / "f.fits",
                          *args, prec="single")
    # the outer isophotes lie in the negative ring
    assert np.all(d[:n, 0][-2:] > 70)
    assert np.all(np.isfinite(d[:n, :11]))
    np.testing.assert_allclose(d[:n, 3], s[:n, 3], rtol=1e-4, atol=1e-3)
