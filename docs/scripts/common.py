"""Shared settings for the documentation figures.

Every figure of the site is made by a script in this directory from the
real u12517 example (examples/u12517) and the released elliprof package,
or is a clearly labelled schematic.  Run all of them with

    python docs/scripts/make_all.py

which needs:  python -m pip install elliprof matplotlib astropy
"""

import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "examples" / "u12517"
WORK = HERE / "_work"                      # elliprof products (not tracked)
ASSETS = ROOT / "docs" / "assets"

IMAGE = DATA / "u12517j.fits"
MASK = DATA / "u12517j.dmask"
FIT = ["--mask", str(MASK), "--sky", "3246.0", "X0=567", "Y0=562",
       "R0=9", "R1=347", "NR=23", "NITER=10", "RMSTAR"]

# one consistent look for every figure
STYLE = {
    "font.size": 10, "axes.titlesize": 11, "axes.labelsize": 10,
    "axes.grid": True, "grid.alpha": 0.25, "figure.dpi": 110,
    "savefig.dpi": 150, "savefig.bbox": "tight", "image.origin": "lower",
    "axes.spines.top": False, "axes.spines.right": False,
}
INK = "#1d3557"        # main line colour
ACCENT = "#e76f51"     # highlights (ellipses, marks)
SCHEMATIC = "SCHEMATIC - illustration, not a measurement"


def run_elliprof(*args, sky=None):
    """Run elliprof (installed in this Python) in WORK (with the standard
    u12517 settings; `sky` replaces the adopted sky level)."""
    WORK.mkdir(exist_ok=True)
    fit = list(FIT)
    if sky is not None:
        fit[fit.index("--sky") + 1] = str(sky)
    cmd = [sys.executable, "-m", "elliprof", str(IMAGE), *fit,
           *map(str, args)]
    proc = subprocess.run(cmd,
                          cwd=WORK, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True)
    if proc.returncode:
        raise RuntimeError(proc.stdout + proc.stderr)
    return proc


def products():
    """The u12517 products used by the figures (made once)."""
    if not (WORK / "u12517j_residual.fits").exists():
        run_elliprof("MODEL", "-m", "u12517j_model.fits", "--prepared",
                     "u12517j_prepared.fits", "--residual",
                     "u12517j_residual.fits", "-o", "u12517j.prf",
                     "--csv", "u12517j.csv", "--reg", "u12517j.reg")
        for name, opts in (("none", ["--model-harmonics", "none"]),
                           ("h4", ["--model-harmonics", "4"]),
                           ("h34", ["--model-harmonics", "3,4"])):
            run_elliprof("MODEL", "-m", f"model_{name}.fits",
                         "-o", f"p_{name}.prf", *opts)
    from astropy.io import fits
    from elliprof import read_profile
    from elliprof.masks import load_mask
    out = {n: fits.getdata(WORK / f"u12517j_{n}.fits").astype(float)
           for n in ("model", "prepared", "residual")}
    out["science"] = fits.getdata(IMAGE).astype(float)
    out["header"] = fits.getheader(IMAGE)
    out["good"] = load_mask(str(MASK)) != 0
    out["profile"] = read_profile(str(WORK / "u12517j.prf"))
    for name in ("none", "h4", "h34"):
        out["model_" + name] = fits.getdata(WORK / f"model_{name}.fits")
    return out


def stretch(img, lo=None, hi=None, a=0.02):
    """asinh stretch to 0..1 for display."""
    lo = np.nanpercentile(img, 0.5) if lo is None else lo
    hi = np.nanpercentile(img, 99.8) if hi is None else hi
    x = np.clip((img - lo) / (hi - lo), 0, 1)
    return np.arcsinh(x / a) / np.arcsinh(1 / a)


def ellipse_xy(row, n=361):
    """Points of one fitted isophote in array (0-based pixel) coordinates.
    ELLIPROF: x = FITS column - 0.5 -> array index = x - 0.5; the major
    axis lies at alpha + 90 deg counter-clockwise from +x."""
    t = np.linspace(0, 2 * np.pi, n)
    a = row.Rmaj
    b = a * (1 - row.ellip)
    th = np.radians(row.alpha + 90)
    x = a * np.cos(t) * np.cos(th) - b * np.sin(t) * np.sin(th)
    y = a * np.cos(t) * np.sin(th) + b * np.sin(t) * np.cos(th)
    return x + row.x0 - 0.5, y + row.y0 - 0.5


def logx(ax):
    """Log x axis with plain-number tick labels (1, 10, 100 ...)."""
    from matplotlib.ticker import FuncFormatter, LogLocator
    ax.set_xscale("log")
    ax.xaxis.set_major_locator(LogLocator(subs=(1, 2, 5)))
    ax.xaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{v:g}"))
    ax.xaxis.set_minor_formatter(FuncFormatter(lambda v, _: ""))


def save(fig, name):
    ASSETS.mkdir(parents=True, exist_ok=True)
    fig.savefig(ASSETS / name)
    import matplotlib.pyplot as plt
    plt.close(fig)
    print("wrote", ASSETS / name)
