"""Simple checks of the u12517 residual in elliptical annuli, as shown in
docs/tutorials/sbf-residual.md.  These are sanity checks of the galaxy
model, NOT an SBF measurement.

    python docs/scripts/residual_checks.py
"""

import numpy as np

import common as C

P = C.products()
RES, MODEL, GOOD = P["residual"], P["model"], P["good"]
PROF = P["profile"].iloc[2:]


def annuli():
    ny, nx = RES.shape
    y, x = np.mgrid[0:ny, 0:nx] + 0.5        # ELLIPROF pixel-centre coords
    x0, y0 = PROF.x0.median(), PROF.y0.median()
    eps = PROF.ellip.median()
    th = np.radians(PROF.alpha.median() + 90)
    xp = (x - x0) * np.cos(th) + (y - y0) * np.sin(th)
    yp = -(x - x0) * np.sin(th) + (y - y0) * np.cos(th)
    return np.hypot(xp, yp / (1 - eps))


def main():
    a = annuli()
    print("| annulus (a, pixels) | good pixels | median residual | "
          "median residual / median model | robust rms of residual/sqrt(model) |")
    print("|---|---|---|---|---|")
    for lo, hi in ((20, 40), (40, 80), (80, 160), (160, 320)):
        s = GOOD & (a >= lo) & (a < hi)
        r, m = RES[s], MODEL[s]
        n = r / np.sqrt(m)
        mad = 1.4826 * np.median(np.abs(n - np.median(n)))
        print(f"| {lo}-{hi} | {s.sum():,} | {np.median(r):.1f} | "
              f"{np.median(r) / np.median(m):+.4f} | {mad:.2f} |")


if __name__ == "__main__":
    main()
