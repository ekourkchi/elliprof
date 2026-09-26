"""Figures explaining what ELLIPROF measures on one isophote: the ellipse
geometry and angle conventions (schematic), the radial spacing laws
(exact), star rejection (RMSTAR) and the fitted centres (real u12517 data).

    python docs/scripts/make_isophote_diagram.py
"""

import matplotlib.pyplot as plt
import numpy as np

import common as C

plt.rcParams.update(C.STYLE)


def schematic_label(fig):
    fig.text(0.99, 0.01, C.SCHEMATIC, ha="right", va="bottom", fontsize=8,
             color="#888888", style="italic")


def geometry():
    a, ell, alpha = 3.0, 0.4, 30.0                 # alpha: CCW from +y
    b = a * (1 - ell)
    th = np.radians(alpha + 90)                    # major axis from +x
    u = np.array([np.cos(th), np.sin(th)])         # major-axis direction
    v = np.array([-np.sin(th), np.cos(th)])        # minor-axis direction
    t = np.linspace(0, 2 * np.pi, 400)
    pts = np.outer(a * np.cos(t), u) + np.outer(b * np.sin(t), v)

    fig, ax = plt.subplots(figsize=(6.4, 6.0))
    ax.plot(pts[:, 0], pts[:, 1], color=C.INK, lw=2)
    # axes of the image
    for d, lab in (((4.2, 0), "+x (columns)"), ((0, 4.2), "+y (rows)")):
        ax.annotate("", xy=d, xytext=(0, 0),
                    arrowprops=dict(arrowstyle="->", color="#777777"))
        ax.text(d[0] * 1.02, d[1] * 1.02 + 0.1, lab, color="#555555",
                fontsize=9)
    # semi-axes
    ax.plot([0, a * u[0]], [0, a * u[1]], color=C.ACCENT, lw=2)
    ax.text(*(0.7 * a * u + 0.3 * v), "a = Rmaj", color=C.ACCENT,
            fontsize=10, ha="right")
    ax.plot([0, b * v[0]], [0, b * v[1]], color="#2a9d8f", lw=2)
    ax.text(*(0.5 * b * v - 0.45 * u), "b", color="#2a9d8f", fontsize=11)
    # alpha arc from +y
    arc = np.radians(np.linspace(90, 90 + alpha, 40))
    ax.plot(1.3 * np.cos(arc), 1.3 * np.sin(arc), color="k", lw=1)
    ax.plot([0, 0], [0, 1.6], color="k", lw=0.8, ls=":")
    ax.text(-0.55, 1.45, r"alpha", fontsize=10)
    # samples at equal steps of the eccentric angle
    for k, tt in enumerate(np.radians(np.arange(0, 360, 20))):
        p = a * np.cos(tt) * u + b * np.sin(tt) * v
        ax.plot(*p, "o", ms=4, color=C.INK)
    ax.plot(0, 0, "+", ms=12, mew=2, color="k")
    ax.text(0.12, -0.35, "centre (x0, y0)", fontsize=9)
    ax.text(-4.3, -3.9, f"ellip = 1 - b/a = {ell:.1f}\n"
            f"alpha = {alpha:.0f} deg (counter-clockwise from +y)\n"
            "dots: samples at equal steps of the eccentric angle",
            fontsize=9, va="bottom")
    ax.set_aspect("equal")
    ax.set_xlim(-4.4, 4.6)
    ax.set_ylim(-4.0, 4.6)
    ax.axis("off")
    schematic_label(fig)
    C.save(fig, "isophote_geometry.png")


def eccentric_angle():
    """Eccentric angle: the angle on the auxiliary circle, not the polar
    angle of the point."""
    a, b = 3.0, 1.6
    t = np.linspace(0, 2 * np.pi, 400)
    fig, ax = plt.subplots(figsize=(6.4, 4.0))
    ax.plot(a * np.cos(t), b * np.sin(t), color=C.INK, lw=2, label="isophote")
    ax.plot(a * np.cos(t), a * np.sin(t), color="#999999", ls="--", lw=1,
            label="auxiliary circle, radius a")
    th = np.radians(50)
    q = np.array([a * np.cos(th), a * np.sin(th)])
    p = np.array([a * np.cos(th), b * np.sin(th)])
    ax.plot([0, q[0]], [0, q[1]], color="#999999", lw=1)
    ax.plot([q[0], p[0]], [q[1], p[1]], color="#999999", lw=1, ls=":")
    ax.plot(*p, "o", color=C.ACCENT, ms=7)
    ax.plot([0, p[0]], [0, p[1]], color=C.ACCENT, lw=1)
    arc = np.linspace(0, th, 30)
    ax.plot(0.8 * np.cos(arc), 0.8 * np.sin(arc), color="k", lw=1)
    ax.text(0.9, 0.35, r"$\theta$", fontsize=13)
    ax.text(p[0] + 0.12, p[1] - 0.25, r"$(a\cos\theta,\ b\sin\theta)$",
            fontsize=10, color=C.ACCENT)
    ax.plot([-3.3, 3.3], [0, 0], color="k", lw=0.6)
    ax.text(3.35, -0.1, "major axis", fontsize=9, va="top", ha="right")
    ax.set_aspect("equal")
    ax.axis("off")
    ax.legend(loc="lower left", frameon=False, fontsize=9)
    schematic_label(fig)
    C.save(fig, "eccentric_angle.png")


def rlaw():
    """Exact semi-major axes for R0=9, R1=347, NR=23 under each RLAW."""
    r0, r1, n = 9.0, 347.0, 23
    k = np.arange(n) / (n - 1)
    laws = {
        "RLAW=2  equal steps in r^(1/4)  (default)":
            (r0 ** 0.25 + k * (r1 ** 0.25 - r0 ** 0.25)) ** 4,
        "RLAW=1  equal steps in log r":
            r0 * (r1 / r0) ** k,
        "RLAW=0  equal steps in r":
            r0 + k * (r1 - r0),
    }
    fig, axes = plt.subplots(2, 1, figsize=(10, 4.6),
                             gridspec_kw=dict(height_ratios=(1, 1)))
    for ax, xs in zip(axes, ("linear", "log")):
        for i, (lab, r) in enumerate(laws.items()):
            y = 2 - i
            ax.plot(r, np.full(n, y), "|", ms=14, mew=1.6,
                    color=(C.ACCENT, C.INK, "#6c757d")[i])
            if xs == "linear":
                ax.text(r1 + 8, y, lab, va="center", fontsize=9)
        ax.set_yticks([])
        ax.set_ylim(-0.7, 2.7)
        ax.grid(False)
        ax.spines["left"].set_visible(False)
        if xs == "log":
            C.logx(ax)
            ax.set_xlabel("semi-major axis [pixels]  (log scale)")
        else:
            ax.set_xlabel("semi-major axis [pixels]  (linear scale)")
    axes[0].set_title("Where the 23 isophotes fall for R0=9, R1=347, NR=23",
                      fontsize=10)
    fig.tight_layout()
    C.save(fig, "rlaw_spacing.png")
    # the numbers, for the page
    with open(C.WORK / "rlaw_values.txt", "w") as f:
        for lab, r in laws.items():
            f.write(lab + ": " + " ".join(f"{x:.1f}" for x in r) + "\n")


def bilinear(img, x, y):
    """Sample a 2-D array at ELLIPROF coordinates (array index = x - 0.5)."""
    xi, yi = x - 0.5, y - 0.5
    i0, j0 = np.floor(xi).astype(int), np.floor(yi).astype(int)
    fx, fy = xi - i0, yi - j0
    return (img[j0, i0] * (1 - fx) * (1 - fy) + img[j0, i0 + 1] * fx * (1 - fy)
            + img[j0 + 1, i0] * (1 - fx) * fy + img[j0 + 1, i0 + 1] * fx * fy)


def rmstar():
    """The RMSTAR rule applied, in Python, to samples along one real
    u12517 isophote of the UNMASKED sky-subtracted image."""
    P = C.products()
    sci = P["science"] - 3246.0
    prof = P["profile"]
    best = None
    for idx in range(8, len(prof) - 1):
        row = prof.iloc[idx]
        t = np.radians(np.arange(360))
        a, b = row.Rmaj, row.Rmaj * (1 - row.ellip)
        th = np.radians(row.alpha + 90)
        x = row.x0 + a * np.cos(t) * np.cos(th) - b * np.sin(t) * np.sin(th)
        y = row.y0 + a * np.cos(t) * np.sin(th) + b * np.sin(t) * np.cos(th)
        s = bilinear(sci, x, y)
        med, q3 = np.median(s), np.percentile(s, 75)
        cut = med + 4 * (q3 - med)
        nrej = int((s > cut).sum())
        if best is None or nrej > best[0]:
            best = (nrej, idx, row, x, y, s, med, cut)
    nrej, idx, row, x, y, s, med, cut = best
    rej = s > cut
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.2),
                             gridspec_kw=dict(width_ratios=(1, 1.6)))
    h = row.Rmaj * 1.15
    cx, cy = row.x0 - 0.5, row.y0 - 0.5
    axes[0].imshow(C.stretch(sci, 0, np.nanpercentile(P["model"], 99.9)),
                   cmap="gray")
    axes[0].plot(x - 0.5, y - 0.5, color="#a8dadc", lw=0.8)
    axes[0].plot((x - 0.5)[rej], (y - 0.5)[rej], "o", ms=4, mfc="none",
                 color=C.ACCENT)
    axes[0].set_xlim(cx - h, cx + h)
    axes[0].set_ylim(cy - h, cy + h)
    axes[0].set_xticks([])
    axes[0].set_yticks([])
    axes[0].grid(False)
    axes[0].set_title(f"isophote a = {row.Rmaj:.0f} px, no mask")
    ang = np.arange(360)
    axes[1].plot(ang, s, color=C.INK, lw=1, label="samples along the ellipse")
    axes[1].plot(ang[rej], s[rej], "o", ms=4, color=C.ACCENT,
                 label=f"rejected ({rej.sum()} of 360)")
    axes[1].axhline(med, color="k", lw=0.8, ls=":", label="median")
    axes[1].axhline(cut, color=C.ACCENT, lw=1, ls="--",
                    label="median + 4 x (Q3 - median)")
    top = med + 8 * (cut - med)
    axes[1].set_ylim(np.percentile(s, 0.5) - (cut - med), top)
    axes[1].text(2, top, "  (bright peaks run off the top)", fontsize=8,
                 va="top", color="#555555")
    axes[1].set_xlabel("eccentric angle [deg]")
    axes[1].set_ylabel("science - sky [image units]")
    axes[1].set_xlim(0, 359)
    axes[1].legend(frameon=False, fontsize=8, loc="upper left",
                   bbox_to_anchor=(0, -0.14), ncol=4)
    fig.text(0.5, -0.1, "The RMSTAR rule re-computed in Python on one real "
             "u12517 isophote, WITHOUT the mask, to show what it catches. "
             "ELLIPROF applies it inside the fit.", ha="center", fontsize=9,
             color="#555555")
    fig.tight_layout()
    C.save(fig, "rmstar_illustration.png")


def centres():
    """Initial centre vs the centre ELLIPROF fits for each isophote."""
    P = C.products()
    prof = P["profile"].iloc[1:]
    sci = P["science"] - 3246.0
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.6))
    h = 6
    axes[0].imshow(C.stretch(sci, 0, np.nanpercentile(sci, 99.99)),
                   cmap="gray", extent=(0, sci.shape[1], 0, sci.shape[0]))
    # extent puts array index i at x = i..i+1; ELLIPROF x = FITS col - 0.5
    # = index + 0.5, i.e. pixel centres are at x = index + 0.5 here.
    axes[0].plot(567, 562, "+", ms=16, mew=2, color=C.ACCENT,
                 label="X0=567, Y0=562 (given)")
    axes[0].plot(prof.x0, prof.y0, "o", ms=4, mfc="none", color="#2a9d8f",
                 label="fitted x0, y0 per isophote")
    axes[0].set_xlim(567 - h, 567 + h)
    axes[0].set_ylim(562 - h, 562 + h)
    axes[0].set_xlabel("x [ELLIPROF pixels]")
    axes[0].set_ylabel("y [ELLIPROF pixels]")
    axes[0].grid(False)
    axes[0].legend(frameon=True, fontsize=8, loc="lower left")
    axes[0].set_title("centre of u12517 (12 x 12 pixels)")
    sc = axes[1].scatter(prof.x0 - 567, prof.y0 - 562, c=np.log10(prof.Rmaj),
                         cmap="viridis", s=28)
    axes[1].plot(0, 0, "+", ms=16, mew=2, color=C.ACCENT)
    axes[1].set_aspect("equal", adjustable="datalim")
    axes[1].set_xlabel("x0 - X0 [pixels]")
    axes[1].set_ylabel("y0 - Y0 [pixels]")
    axes[1].set_title("fitted centres (colour = log10 Rmaj)")
    fig.colorbar(sc, ax=axes[1], label="log10 Rmaj [pixels]")
    fig.tight_layout()
    C.save(fig, "centres_u12517.png")


if __name__ == "__main__":
    geometry()
    eccentric_angle()
    rlaw()
    rmstar()
    centres()
