"""Generate the synthetic regression images (run once; the results are
stored in tests/data/regression and must not change afterwards).

    python tests/regression/make_synthetic.py [--force]
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "python"))

from cases import BASE, CASES, DATA, SIZE  # noqa: E402


def devauc(truth, ncol, nrow):
    j, i = np.indices((nrow, ncol), dtype=np.float64)
    x, y = i + 0.5, j + 0.5
    dx, dy = x - truth["x0"], y - truth["y0"]
    c, s = np.cos(np.radians(truth["pa"])), np.sin(np.radians(truth["pa"]))
    u = dx * c + dy * s
    v = -dx * s + dy * c
    r = np.sqrt(u ** 2 + (v / truth["q"]) ** 2)
    img = truth["ie"] * np.exp(-7.669 * ((r / truth["re"]) ** 0.25 - 1.0))
    return img, x, y


def gradient_sky(x, y):
    return 150.0 + 0.2 * x - 0.1 * y


def star(x, y, pos, amp=5000.0, sigma=1.5):
    return amp * np.exp(-((x - pos[0]) ** 2 + (y - pos[1]) ** 2) /
                        (2 * sigma ** 2))


def wcs_header(truth):
    from astropy.io import fits
    h = fits.Header()
    h["CTYPE1"], h["CTYPE2"] = "RA---TAN", "DEC--TAN"
    # FITS pixel (1-based) of the galaxy centre = ELLIPROF x0 + 0.5
    h["CRPIX1"], h["CRPIX2"] = truth["x0"] + 0.5, truth["y0"] + 0.5
    h["CRVAL1"], h["CRVAL2"] = 188.73658, -12.58242
    scale = 0.2 / 3600
    h["CD1_1"], h["CD1_2"], h["CD2_1"], h["CD2_2"] = -scale, 0.0, 0.0, scale
    h["RADESYS"] = "ICRS"
    return h


def write(path, data, header=None):
    from astropy.io import fits
    hdu = fits.PrimaryHDU(data.astype(np.float32), header=header)
    hdu.writeto(path, overwrite=True)


def main(force=False):
    from elliprof.masks import write_bitmap_mask
    DATA.mkdir(parents=True, exist_ok=True)
    ncol, nrow = SIZE
    for name, case in CASES.items():
        if case.get("image") == "star" and name != "star_nomask":
            continue
        base = case.get("image", name)
        path = DATA / f"{base}.fits"
        if path.exists() and not force:
            continue
        truth = case["truth"]
        img, x, y = devauc(truth, ncol, nrow)
        if truth["sky"] == "gradient":
            write(DATA / f"{name}_sky.fits", gradient_sky(x, y))
            img = img + gradient_sky(x, y).astype(np.float32)
        else:
            img = img + truth["sky"]
        if "star" in truth:
            img = img + star(x, y, truth["star"])
            mask = np.ones((nrow, ncol))
            mask[(x - truth["star"][0]) ** 2 +
                 (y - truth["star"][1]) ** 2 < 8.0 ** 2] = 0
            write_bitmap_mask(DATA / "star.dmask", mask)
        if "noise" in truth:
            img = img + np.random.default_rng(1).normal(0, truth["noise"],
                                                        img.shape)
        write(path, img, wcs_header(truth) if case.get("wcs") else None)
        print("wrote", path)


if __name__ == "__main__":
    main(force="--force" in sys.argv)
