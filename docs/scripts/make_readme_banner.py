"""The README header image: UGC 12517 read from left to right as the
galaxy, its fitted isophotes and the residual left by the model, next to
the name and a thin trace of the measured profile.  Everything shown is
real elliprof 0.1.3 output for examples/u12517.

    python docs/scripts/make_readme_banner.py
"""

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import colormaps
from matplotlib.collections import LineCollection
from matplotlib.colors import LinearSegmentedColormap, to_rgb

import common as C

BG = "#05070d"
GALAXY = LinearSegmentedColormap.from_list(
    "galaxy", ["#05070d", "#141b3a", "#3b3f8f", "#b06a8f", "#f2b880",
               "#fff4e0"])
GOLD = "#f4c26b"


def smoothstep(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def main():
    P = C.products()
    sci = P["science"] - 3246.0
    res, good, prof = P["residual"], P["good"], P["profile"].iloc[1:]
    y0, h = 562, 290                      # rows shown: the galaxy's core band
    rows = np.s_[y0 - h:y0 + h]
    img = sci[rows]
    ny, nx = img.shape

    # galaxy colours
    lo, hi = 0.0, np.nanpercentile(P["model"], 99.95)
    rgb_gal = GALAXY(C.stretch(img, lo, hi, a=0.01))[..., :3]
    # residual colours (dark-centred diverging map), masked pixels dark
    r = res[rows]
    lim = np.nanpercentile(np.abs(r[good[rows]]), 97)
    rgb_res = colormaps["berlin"](np.clip(r / lim, -1, 1) * 0.5 + 0.5)[..., :3]
    bad = ~good[rows]
    rgb_res[bad] = 0.3 * rgb_gal[bad]      # masked: a dim glow of the image
    # blend left -> right: galaxy, then residual beyond the centre
    x = np.arange(nx)[None, :, None]
    w = smoothstep(x, 640, 900)
    rgb = (1 - w) * rgb_gal + w * rgb_res

    fig = plt.figure(figsize=(16, 4.8), facecolor=BG)
    ax = fig.add_axes([0.0, 0.0, 0.56, 1.0])
    ax.imshow(rgb, origin="lower", interpolation="lanczos",
              extent=(0, nx, 0, ny))
    # fitted isophotes, glowing, fading in from the centre to the right
    cmap = LinearSegmentedColormap.from_list("iso", ["#ffe6a8", GOLD,
                                                     "#e76f51"])
    for k, (_, row) in enumerate(prof.iterrows()):
        xs, ys = C.ellipse_xy(row, n=1440)
        xs, ys = xs + 0.5, ys - (y0 - h) + 0.5
        pts = np.column_stack([xs, ys])
        seg = np.stack([pts[:-1], pts[1:]], axis=1)
        xm = 0.5 * (xs[:-1] + xs[1:])
        fade = smoothstep(xm, 470, 640) * (1 - smoothstep(xm, 870, 960))
        rgb_line = to_rgb(cmap(k / (len(prof) - 1)))
        for lw, amax in ((3.0, 0.14), (0.9, 0.95)):          # glow, line
            cols = np.column_stack([np.tile(rgb_line, (len(seg), 1)),
                                    amax * fade])
            ax.add_collection(LineCollection(seg, colors=cols, linewidths=lw,
                                             capstyle="round"))
    ax.set_xlim(0, nx)
    ax.set_ylim(0, ny)
    ax.axis("off")
    # soft fade into the background on the right edge
    fade = np.linspace(0, 1, 256)[None, :] ** 1.6
    ax.imshow(np.dstack([np.full((1, 256, 3), [5 / 255, 7 / 255, 13 / 255]),
                         fade[..., None]]),
              extent=(nx - 140, nx, 0, ny), aspect="auto", zorder=5)

    # text
    fig.text(0.60, 0.60, "ELLIPROF", color="#fff4e0", fontsize=64,
             fontweight="bold", family="DejaVu Sans")
    fig.text(0.603, 0.47, "galaxy isophote fitting", color=GOLD, fontsize=22,
             family="DejaVu Sans")
    fig.text(0.604, 0.37, "surface-brightness profiles  ·  shapes  ·  "
             "boxy / disky isophotes", color="#aab3cf", fontsize=12.5,
             family="DejaVu Sans")
    fig.text(0.604, 0.315, "model and residual images for SBF analyses",
             color="#aab3cf", fontsize=12.5, family="DejaVu Sans")
    # the measured profile, as a thin trace
    ax2 = fig.add_axes([0.605, 0.07, 0.36, 0.18], facecolor="none")
    ax2.loglog(prof.Rmaj, prof.I0, color=GOLD, lw=1.2, alpha=0.9)
    ax2.loglog(prof.Rmaj, prof.I0, "o", color="#fff4e0", ms=2.2, alpha=0.9)
    ax2.axis("off")
    fig.text(0.968, 0.035, "UGC 12517 · HST WFC3/IR · real elliprof output",
             color="#5c6380", fontsize=9, ha="right", family="DejaVu Sans")

    C.ASSETS.mkdir(parents=True, exist_ok=True)
    out = C.ASSETS / "elliprof_banner.png"
    fig.savefig(out, dpi=100, facecolor=BG)
    plt.close(fig)
    print("wrote", out)


if __name__ == "__main__":
    main()
