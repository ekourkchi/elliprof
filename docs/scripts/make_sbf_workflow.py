"""The SBF distance workflow, showing which steps ELLIPROF performs and
which belong to downstream SBF software and to the researcher.

    python docs/scripts/make_sbf_workflow.py
"""

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

import common as C

plt.rcParams.update(C.STYLE)

USER = "#e9ecef"         # supplied by the researcher
ELLI = "#f4a261"         # done by ELLIPROF
DOWN = "#a8dadc"         # downstream SBF analysis (not ELLIPROF)

STEPS = [
    # (x, y, text, colour)
    (0, 9, "Calibrated image(s) of an early-type galaxy\n"
           "+ PSF + photometric zeropoint", USER),
    (0, 7.75, "Sky / background level\n(estimated by the researcher)", USER),
    (0, 6.5, "Mask: stars, background galaxies,\n"
             "dust, bad pixels (researcher)", USER),
    (0, 5.25, "ELLIPROF: fit elliptical isophotes\n"
             "(I0, centre, ellip, PA, I3/A3, I4/A4 per radius)", ELLI),
    (0, 4.0, "ELLIPROF: smooth galaxy MODEL image", ELLI),
    (0, 2.75, "ELLIPROF: RESIDUAL = mask x (science - sky - model)", ELLI),
    (0, 1.5, "profile, model, residual, prepared image\n"
             "(FITS with the science WCS)", ELLI),
    (7.4, 9, "Remove remaining large-scale residual\n"
             "(background, smooth structure)", DOWN),
    (7.4, 7.75, "Detect point sources (globular clusters,\n"
               "background galaxies); fit their luminosity\n"
               "function; mask them", DOWN),
    (7.4, 6.5, "Normalise: residual / sqrt(model)", DOWN),
    (7.4, 5.25, "Power spectrum of the masked, normalised\n"
               "residual; E(k) = PSF power spectrum\n"
               "convolved with the mask window", DOWN),
    (7.4, 4.0, "Fit  P(k) = P0 E(k) + P1 ;\n"
               "subtract the power Pr of undetected sources", DOWN),
    (7.4, 2.75, "mbar = -2.5 log10(P0 - Pr) + zeropoint\n"
               "(+ Galactic extinction, K-correction)", DOWN),
    (7.4, 1.5, "Calibration Mbar(colour)  ->  mu = mbar - Mbar\n"
               "->  d = 10^((mu + 5) / 5) pc", DOWN),
]
W, H = 6.4, 0.95


def box(ax, x, y, text, col):
    ax.add_patch(FancyBboxPatch((x, y - H / 2), W, H,
                                boxstyle="round,pad=0.02,rounding_size=0.12",
                                fc=col, ec="#555555", lw=0.8))
    ax.text(x + W / 2, y, text, ha="center", va="center", fontsize=8.6)


def arrow(ax, p, q, **kw):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=11,
                                 color="#444444", lw=1, **kw))


def main():
    fig, ax = plt.subplots(figsize=(12.5, 8.4))
    for x, y, text, col in STEPS:
        box(ax, x, y, text, col)
    left = [s for s in STEPS if s[0] == 0]
    right = [s for s in STEPS if s[0] > 0]
    for col in (left, right):
        for a, b in zip(col[:-1], col[1:]):
            arrow(ax, (a[0] + W / 2, a[1] - H / 2),
                  (b[0] + W / 2, b[1] + H / 2))
    # hand-over from ELLIPROF to the downstream analysis
    gx = W + 0.5
    ax.plot([W, gx, gx], [1.5, 1.5, 9], color="#444444", lw=1)
    arrow(ax, (gx, 9), (7.4, 9))
    # ELLIPROF scope frame
    ax.add_patch(FancyBboxPatch((-0.25, 0.85), W + 0.4, 4.9,
                                boxstyle="round,pad=0.02,rounding_size=0.2",
                                fc="none", ec=C.ACCENT, lw=2, ls="--"))
    ax.text(W + 0.1, 5.85, "ELLIPROF 0.1.3 does this", ha="right", color="#b5451b",
            fontsize=10, weight="bold")
    ax.text(7.4, 9.75, "Downstream SBF analysis - NOT ELLIPROF",
            color="#1d6f78", fontsize=10, weight="bold")
    ax.text(0, 9.75, "Inputs prepared by the researcher", color="#555555",
            fontsize=10, weight="bold")
    ax.set_xlim(-0.5, 14.1)
    ax.set_ylim(0.6, 10.1)
    ax.axis("off")
    fig.text(0.5, 0.02, "Simplified. Real SBF analyses add further steps "
             "and corrections (see the SBF references page).", ha="center",
             fontsize=9, color="#555555")
    C.save(fig, "sbf_workflow.png")


if __name__ == "__main__":
    main()
