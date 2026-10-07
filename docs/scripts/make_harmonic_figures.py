"""Figures for the harmonic-analysis page (docs/concepts/harmonics.md).

    python docs/scripts/make_harmonic_figures.py

* harmonic_shapes.png        SCHEMATIC: isophotes with 3rd, 4th (two
                             phases) and 6th-order deviations
* harmonic_subtraction.png   SYNTHETIC images fitted by elliprof: the
                             residual without and with each term in the
                             model
* harmonic_profiles_u12517.png  REAL data: I3, A3, I4, A4, slope and
                             a4/a of the UGC 12517 example
* sixth_order_pa_wrap.png    SYNTHETIC: the original 6th-order model
                             synthesis beyond a position-angle wrap

The synthetic galaxies are r^(1/4) profiles whose isophotes are
r(E) = a (1 + k cos(n E)) in the eccentric angle E (the same construction
as tests/integration/test_harmonic_recovery.py).
"""

import subprocess
import sys

import matplotlib.pyplot as plt
import numpy as np
from astropy.io import fits

import common as C
from elliprof import read_profile

plt.rcParams.update(C.STYLE)
SYN = C.WORK / "harmonics"
X0, Y0, SIZE = 120.3, 119.6, 241
FIT = ["X0=120.3", "Y0=119.6", "R0=6", "R1=110", "NR=18", "NITER=10"]


def galaxy(n=0, k=0.0, pa=120.0, q=0.7, twist=None):
    j, i = np.indices((SIZE, SIZE), dtype=np.float64)
    x, y = i + 0.5 - X0, j + 0.5 - Y0
    if twist:
        frac = np.clip((np.hypot(x, y) - 10) / 80, 0, 1)
        t = np.radians(twist[0] + (twist[1] - twist[0]) * frac)
    else:
        t = np.radians(pa)
    u = x * np.cos(t) + y * np.sin(t)
    v = -x * np.sin(t) + y * np.cos(t)
    rho = np.hypot(u, v / q)
    e = np.arctan2(v / q, u)
    r = rho / (1 + k * np.cos(n * e)) if n else rho
    img = 500.0 * np.exp(-7.669 * ((np.maximum(r, 0.5) / 25.0) ** 0.25 - 1))
    return img.astype(np.float32), e, rho


def fit(name, img, *args):
    SYN.mkdir(parents=True, exist_ok=True)
    fits.PrimaryHDU(img).writeto(SYN / f"{name}.fits", overwrite=True)
    proc = subprocess.run(
        [sys.executable, "-m", "elliprof", f"{name}.fits", *FIT, *args,
         "-o", f"{name}.dat", "--residual", f"{name}_r.fits"],
        cwd=SYN, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True)
    if proc.returncode:
        raise RuntimeError(proc.stdout + proc.stderr)
    return (read_profile(str(SYN / f"{name}.dat")),
            fits.getdata(SYN / f"{name}_r.fits"), proc.stderr)


def component(img, e, rho, n, lo, hi):
    m = (rho >= lo) & (rho < hi) & np.isfinite(img)
    return np.sum(img[m] * np.cos(n * e[m])) / np.sum(np.cos(n * e[m]) ** 2)


def shapes():
    """Isophotes r(E) = a (1 + k cos(n (E - phase))), k exaggerated."""
    cases = [("Pure ellipse", 0, 0), ("3rd order (n = 3)", 3, 0),
             ("4th order, A4 = 0°: disky", 4, 0),
             ("4th order, A4 = 45°: boxy", 4, 45),
             ("6th order (n = 6)", 6, 0)]
    q, k = 0.6, 0.07
    e = np.linspace(0, 2 * np.pi, 721)
    fig, axes = plt.subplots(1, 5, figsize=(14, 2.5))
    for ax, (title, n, ph) in zip(axes, cases):
        ax.plot(np.cos(e), q * np.sin(e), ls="--", lw=1, color="0.6")
        d = 1 + (k * np.cos(n * (e - np.radians(ph))) if n else 0)
        ax.plot(d * np.cos(e), d * q * np.sin(e), lw=2, color=C.INK)
        ax.plot([1.0 + (k if n and ph == 0 else 0)], [0], "o",
                color=C.ACCENT, ms=6)
        ax.annotate("θ = 0", (1.05, 0.04), color=C.ACCENT, fontsize=9)
        ax.set_title(title, fontsize=10)
        ax.set_aspect("equal")
        ax.set_xlim(-1.3, 1.45)
        ax.set_ylim(-0.75, 0.75)
        ax.axis("off")
    fig.subplots_adjust(wspace=0.02, left=0.01, right=0.99, top=0.88,
                        bottom=0.02)
    fig.text(0.5, -0.06, "SCHEMATIC (deviations exaggerated, k = 0.07). "
             "Dashed: the best-fitting ellipse; solid: the isophote, "
             "r = a [1 + k cos n(θ − A_n)]; θ = eccentric angle from the "
             "dotted end of the major axis.", ha="center", fontsize=9,
             color="#555555")
    C.save(fig, "harmonic_shapes.png")


def subtraction():
    """Residuals of synthetic galaxies with the matching term left out
    of, and put into, the model."""
    cases = [(3, ["COS3X=0"], ["COS3X=2"], "COS3X=0", "COS3X=2"),
             (4, ["COS4X=0"], ["COS4X=2"], "COS4X=0", "COS4X=2"),
             (6, ["COS3X=-3"], ["COS3X=-2"], "COS3X=-3", "COS3X=-2")]
    fig, axes = plt.subplots(2, 3, figsize=(11, 7.6))
    sl = slice(SIZE // 2 - 75, SIZE // 2 + 75)
    for col, (n, out_args, in_args, out_lab, in_lab) in enumerate(cases):
        img, e, rho = galaxy(n, 0.02)
        _, r_out, _ = fit(f"sub{n}_out", img, *out_args)
        _, r_in, _ = fit(f"sub{n}_in", img, *in_args)
        ring = (rho > 15) & (rho < 70)
        lim = np.percentile(np.abs(r_out[ring]), 98)
        frac = []
        for lo, hi in ((15, 25), (30, 45), (50, 70)):
            frac.append(abs(component(r_in, e, rho, n, lo, hi)
                            / component(r_out, e, rho, n, lo, hi)))
        for row, (res, lab) in enumerate(((r_out, f"{out_lab}: "
                                           f"{n}θ term not in model"),
                                          (r_in, f"{in_lab}: {n}θ term "
                                           "in model"))):
            ax = axes[row, col]
            show = np.where(rho < 12, np.nan, res)    # centre: grey
            ax.set_facecolor("0.75")
            ax.imshow(show[sl, sl], cmap="RdBu_r", vmin=-lim, vmax=lim)
            ax.set_title(lab, fontsize=10)
            ax.set_xticks([])
            ax.set_yticks([])
            ax.grid(False)
        axes[1, col].set_xlabel(f"{n}θ left in residual: "
                                f"{100 * max(frac):.1f}% or less",
                                fontsize=9)
    fig.text(0.5, 0.01, "SYNTHETIC galaxies with a 2% radial deviation of "
             "order n = 3, 4, 6, fitted by elliprof. Residual = science − "
             "model; the same colour scale in each column; the central "
             "12 px (grey) are hidden.", ha="center", fontsize=9,
             color="#555555")
    fig.subplots_adjust(wspace=0.05, hspace=0.15, bottom=0.07)
    C.save(fig, "harmonic_subtraction.png")


def u12517():
    """The measured harmonic profile of the real example."""
    p = read_profile(str(C.WORK / "u12517j.prf")).iloc[1:]
    alpha = p.alpha.to_numpy()
    wrap = np.flatnonzero(np.abs(np.diff(alpha)) > 90)
    a4 = p.I4 * np.cos(np.radians(4 * p.A4)) / -p.slope
    panels = [("I3", "I3 (fraction of I0)", p.I3),
              ("A3", "A3 [deg] (0-120)", p.A3),
              ("I4", "I4 (fraction of I0)", p.I4),
              ("A4", "A4 [deg] (0-90)", p.A4),
              ("slope", "slope = d ln I / d ln r", p.slope),
              ("a4", "a4/a ≈ I4 cos 4A4 / (−slope)", a4)]
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.2), sharex=True)
    for ax, (key, label, y) in zip(axes.ravel(), panels):
        ax.plot(p.Rmaj, y, "o-", ms=3.5, color=C.INK)
        C.logx(ax)
        ax.set_ylabel(label)
        for w in wrap:
            r = np.sqrt(p.Rmaj.iloc[w] * p.Rmaj.iloc[w + 1])
            ax.axvline(r, color=C.ACCENT, ls=":", lw=1.2)
        if key == "A4":
            ax.axhline(45, color="0.6", lw=0.8)
        if key == "a4":
            ax.axhline(0, color="0.6", lw=0.8)
    for ax in axes[1]:
        ax.set_xlabel("Rmaj [pixels]")
    fig.suptitle("REAL DATA: UGC 12517 (HST WFC3/IR F110W), the harmonic "
                 "columns of the elliprof profile", fontsize=11)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    fig.text(0.5, 0.005, "Dotted line: the fitted position angle wraps "
             "across 0/180° (the end of the major axis that A3 is measured "
             "from swaps there). Grey line in the A4 panel: 45° (boxy); "
             "in the a4/a panel: 0.", ha="center", fontsize=9,
             color="#555555")
    C.save(fig, "harmonic_profiles_u12517.png")


def pa_wrap():
    """The known 6th-order model limitation of the original code."""
    twist = (80.0, 100.0)
    rings = [(lo, lo + 10) for lo in range(20, 100, 10)]
    mid = [lo + 5 for lo, _ in rings]
    out = {}
    for n, args, lab in ((6, ["COS3X=-2"], "6th order, COS3X=-2 (in model)"),
                         (6, ["COS3X=-3"], "6th order, COS3X=-3 (measured "
                          "only)"),
                         (3, ["COS3X=2"], "3rd order, COS3X=2 (in model)")):
        img, e, rho = galaxy(n, 0.02, twist=twist)
        prof, res, _ = fit(f"wrap{n}{args[0][6:]}", img, *args)
        out[lab] = [component(res, e, rho, n, lo, hi)
                    / component(img, e, rho, n, lo, hi) for lo, hi in rings]
    alpha = prof.alpha.to_numpy()
    w = int(np.argmax(np.abs(np.diff(alpha)) > 90))
    rwrap = np.sqrt(prof.Rmaj.iloc[w] * prof.Rmaj.iloc[w + 1])
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 3.8),
                                 gridspec_kw={"width_ratios": [1, 1.6]})
    a1.plot(prof.Rmaj, prof.alpha, "o-", ms=3.5, color=C.INK)
    a1.axvline(rwrap, color=C.ACCENT, ls=":")
    a1.set(xlabel="Rmaj [pixels]", ylabel="fitted alpha [deg]",
           title="Position angle wraps from 180° to 0°")
    styles = {"6th order, COS3X=-2 (in model)": ("o-", C.ACCENT),
              "6th order, COS3X=-3 (measured only)": ("s--", "0.5"),
              "3rd order, COS3X=2 (in model)": ("^-", C.INK)}
    for lab, ys in out.items():
        fmt, col = styles[lab]
        a2.plot(mid, ys, fmt, color=col, label=lab, ms=4)
    a2.axhline(0, color="0.7", lw=0.8)
    a2.axhline(1, color="0.7", lw=0.8)
    a2.axvline(rwrap, color=C.ACCENT, ls=":")
    a2.set(xlabel="ring radius [pixels]",
           ylabel="harmonic left in residual\n(fraction of the injected)",
           title="Model subtraction across the wrap")
    a2.legend(fontsize=8, loc="upper left")
    fig.text(0.5, -0.03, "SYNTHETIC galaxy (2% radial deviation, major "
             "axis turning through the 0/180° boundary), fitted by "
             "elliprof. 0 = removed by the model, 1 = not modelled, "
             "2 = subtracted with the wrong sign.", ha="center", fontsize=9,
             color="#555555")
    fig.tight_layout()
    C.save(fig, "sixth_order_pa_wrap.png")


if __name__ == "__main__":
    C.products()
    shapes()
    subtraction()
    u12517()
    pa_wrap()
