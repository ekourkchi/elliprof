"""Profile figures from the real u12517 fit: the full set of profile
columns and the effect of the sky level on the outer profile.

    python docs/scripts/make_profile_plots.py

Everything is in the measured image units.  No photometric calibration is
applied: the units of the example image are unresolved (its header says
BUNIT = ELECTRONS/S, while examples/u12517/calibrate.dat is internally
consistent only with total electrons); see
docs/science/surface-photometry.md.
"""

import matplotlib.pyplot as plt
import numpy as np

import common as C
from elliprof import read_profile

plt.rcParams.update(C.STYLE)
PROF = C.products()["profile"].iloc[1:]     # r = 9 lies in the masked nucleus


def unwrap(alpha):
    return np.degrees(np.unwrap(np.radians(2 * np.asarray(alpha)))) / 2


def profile_panels():
    r = PROF.Rmaj
    fig, axes = plt.subplots(2, 3, figsize=(12, 6.4), sharex=True)
    ax = axes.flat
    ax[0].plot(r, PROF.I0, "o-", ms=3, color=C.INK)
    ax[0].set_yscale("log")
    ax[0].set_title("I0: isophote intensity")
    ax[0].set_ylabel("image units per pixel")
    ax[1].plot(r, PROF.ellip, "o-", ms=3, color=C.INK)
    ax[1].set_title("ellip = 1 - b/a")
    ax[2].plot(r, unwrap(PROF.alpha), "o-", ms=3, color=C.INK)
    ax[2].set_title("alpha: position angle")
    ax[2].set_ylabel("deg CCW from +y (unwrapped)")
    ax[3].plot(r, PROF.slope, "o-", ms=3, color=C.INK)
    ax[3].set_title("slope = d ln I / d ln r")
    a4 = PROF.I4 * np.cos(np.radians(4 * PROF.A4)) / -PROF.slope
    ax[4].axhline(0, color="k", lw=0.8)
    ax[4].plot(r, 100 * a4, "o-", ms=3, color=C.INK)
    ax[4].set_title("100 a4/a  ~  100 I4 cos(4 A4) / (-slope)")
    ax[4].text(0.03, 0.92, "> 0 disky", transform=ax[4].transAxes, fontsize=9)
    ax[4].text(0.6, 0.04, "< 0 boxy", transform=ax[4].transAxes, fontsize=9)
    ax[5].plot(r, PROF.x0 - 567, "o-", ms=3, color=C.INK, label="x0 - X0")
    ax[5].plot(r, PROF.y0 - 562, "s-", ms=3, color=C.ACCENT, label="y0 - Y0")
    ax[5].set_title("fitted centre - initial centre")
    ax[5].set_ylabel("pixels")
    ax[5].legend(frameon=False, fontsize=9)
    for a in axes[1]:
        a.set_xlabel("Rmaj [pixels]")
    for a in ax:
        C.logx(a)
    fig.suptitle("UGC 12517: the profile columns (examples/u12517, "
                 "22 fitted isophotes)", y=1.0)
    fig.tight_layout()
    C.save(fig, "profile_panels.png")


def sky_sensitivity():
    """Real re-fits with the subtracted sky changed by +-50 and +-150 image
    units (the adopted sky is 3246)."""
    skies = (3096.0, 3196.0, 3246.0, 3296.0, 3396.0)
    colours = ("#1d4e89", "#6a9fcb", "k", "#f4a582", "#b2182b")
    prof = {}
    for sky in skies:
        prf = C.WORK / f"sky_{sky:.0f}.prf"
        if not prf.exists():
            C.run_elliprof("-o", prf.name, sky=sky)
        prof[sky] = read_profile(str(prf)).iloc[1:]
    ref = prof[3246.0]
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.2))
    for sky, col in zip(skies, colours):
        p = prof[sky]
        d = sky - 3246.0
        lab = "adopted sky, 3246" if d == 0 else f"sky {d:+.0f}"
        axes[0].plot(p.Rmaj, p.I0, "o-", ms=3, color=col, label=lab,
                     lw=1.5 if d == 0 else 1)
        axes[1].plot(p.Rmaj, 100 * (p.I0 / ref.I0 - 1), "o-", ms=3,
                     color=col, label=lab)
    axes[0].set_yscale("log")
    axes[0].set_ylabel("I0 [image units per pixel]")
    axes[1].set_ylabel("change in I0 relative to the adopted sky [%]")
    axes[1].axhline(0, color="k", lw=0.6)
    for ax in axes:
        C.logx(ax)
        ax.set_xlabel("Rmaj [pixels]")
        ax.legend(frameon=False, fontsize=9)
    fig.text(0.5, -0.03, "Real elliprof fits of u12517 that differ only in "
             "the subtracted sky (3246 +- 50 and +- 150, image units). The "
             "inner profile does not move; the outer profile does.",
             ha="center", fontsize=9, color="#555555")
    fig.tight_layout()
    C.save(fig, "sky_sensitivity.png")


if __name__ == "__main__":
    profile_panels()
    sky_sensitivity()
