"""Boxy and disky isophotes: what the shapes look like and what I4/A4
measure (schematic), and a real test: elliprof fits of synthetic galaxies
with known a4/a.

    python docs/scripts/make_boxy_disky_diagram.py
"""

import matplotlib.pyplot as plt
import numpy as np

import common as C

plt.rcParams.update(C.STYLE)
CASES = ((+0.05, "disky", C.ACCENT), (0.0, "pure ellipse", C.INK),
         (-0.05, "boxy", "#2a9d8f"))


def shapes():
    q, slope = 0.7, -2.0
    phi = np.linspace(0, 2 * np.pi, 721)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4),
                             gridspec_kw=dict(width_ratios=(1, 1.3)))
    for c, lab, col in CASES:
        r = 1 + c * np.cos(4 * phi)                # radial deviation a4/a
        axes[0].plot(r * np.cos(phi), q * r * np.sin(phi), color=col, lw=2,
                     label=f"{lab}  (a4/a = {c:+.2f})")
        # intensity along the reference ellipse: dI/I = -slope * dr/r
        axes[1].plot(np.degrees(phi), -slope * c * np.cos(4 * phi), color=col,
                     lw=2, label=lab)
    axes[0].set_aspect("equal")
    axes[0].axis("off")
    axes[0].legend(loc="upper center", bbox_to_anchor=(0.5, -0.02),
                   frameon=False, fontsize=9)
    axes[0].set_title("isophote shapes (deviation exaggerated)")
    for x in (0, 90, 180, 270, 360):
        axes[1].axvline(x, color="#bbbbbb", lw=0.8)
    for x in (45, 135, 225, 315):
        axes[1].axvline(x, color="#bbbbbb", lw=0.8, ls=":")
    axes[1].text(0, 0.115, "major\naxis", ha="center", fontsize=8)
    axes[1].text(90, 0.115, "minor\naxis", ha="center", fontsize=8)
    axes[1].text(45, 0.115, "diagonal", ha="center", fontsize=8)
    axes[1].set_xlim(0, 360)
    axes[1].set_ylim(-0.13, 0.14)
    axes[1].set_xticks(range(0, 361, 45))
    axes[1].set_xlabel("eccentric angle around the ellipse [deg]")
    axes[1].set_ylabel("(I - I0) / I0 along a pure ellipse")
    axes[1].set_title("disky: peaks at 0 and 90 deg (A4 = 0 or 90)\n"
                      "boxy: peaks at 45 deg (A4 = 45)", fontsize=10)
    axes[1].legend(frameon=False, fontsize=9, loc="lower right")
    fig.text(0.99, 0.0, C.SCHEMATIC + " (slope = -2, b/a = 0.7)",
             ha="right", fontsize=8, color="#888888", style="italic")
    fig.tight_layout()
    C.save(fig, "boxy_disky_shapes.png")


def synthetic(c4, n=401, q=0.7, pa=30.0, rc=4.0):
    """Noise-free galaxy, I ~ (1 + (A/rc)^2)^-1 in the isophote label A,
    whose isophotes are  m = A (1 + c4 cos 4 phi)  (m elliptical radius,
    phi eccentric angle).  Major axis at `pa` deg from +x."""
    y, x = np.mgrid[0:n, 0:n] - (n - 1) / 2.0
    t = np.radians(pa)
    xp = x * np.cos(t) + y * np.sin(t)
    yp = -x * np.sin(t) + y * np.cos(t)
    m = np.hypot(xp, yp / q)
    phi = np.arctan2(yp / q, xp)
    big_a = m / (1 + c4 * np.cos(4 * phi))
    return (1e4 / (1 + (big_a / rc) ** 2)).astype(np.float32)


def recovery():
    import subprocess
    import sys

    from astropy.io import fits
    from elliprof import read_profile
    C.WORK.mkdir(exist_ok=True)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2),
                             gridspec_kw=dict(width_ratios=(1, 1.5)))
    for c, lab, col in CASES[::-1]:
        tag = {0.05: "p", 0.0: "z", -0.05: "m"}[c]
        img = synthetic(0.6 * c)                       # a4/a = +-0.03
        f = C.WORK / f"synth_{tag}.fits"
        fits.writeto(f, img, overwrite=True)
        prf = C.WORK / f"synth_{tag}.prf"
        subprocess.run([sys.executable, "-m", "elliprof", str(f),
                        "X0=201", "Y0=201", "R0=8", "R1=150", "NR=15",
                        "NITER=20", "-o", str(prf)], check=True,
                       stdout=subprocess.DEVNULL)
        p = read_profile(str(prf))
        a4 = p.I4 * np.cos(np.radians(4 * p.A4)) / -p.slope
        axes[1].plot(p.Rmaj, a4, "o-", ms=4, color=col,
                     label=f"{lab}: injected a4/a = {0.6 * c:+.3f}")
        axes[1].axhline(0.6 * c, color=col, lw=0.8, ls="--")
        if c > 0:
            axes[0].imshow(np.log10(img), cmap="gray", origin="lower")
            for _, row in p.iloc[::3].iterrows():
                xx, yy = C.ellipse_xy(row)
                axes[0].plot(xx, yy, color=C.ACCENT, lw=0.8)
    axes[0].set_title("synthetic disky galaxy (a4/a = +0.03)\n"
                      "with elliprof's fitted ellipses", fontsize=10)
    axes[0].set_xticks([])
    axes[0].set_yticks([])
    axes[0].grid(False)
    axes[1].set_xlabel("Rmaj [pixels]")
    axes[1].set_ylabel("I4 cos(4 A4) / (-slope)")
    axes[1].set_title("recovered a4/a (dashed: injected)", fontsize=10)
    axes[1].set_ylim(-0.05, 0.05)
    axes[1].legend(frameon=False, fontsize=9, loc="upper center",
                   bbox_to_anchor=(0.5, -0.16), ncol=1)
    C.logx(axes[1])
    fig.text(0.5, -0.2, "Real elliprof fits of noise-free synthetic images "
             "made by this script. The first and last isophotes deviate: "
             "their slope is a one-sided difference.", ha="center",
             fontsize=9, color="#555555")
    fig.tight_layout()
    C.save(fig, "boxy_disky_recovery.png")


if __name__ == "__main__":
    shapes()
    recovery()
