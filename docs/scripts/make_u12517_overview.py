"""Real-data figures from the u12517 example (HST WFC3/IR F110W image of
UGC 12517): the hero sequence, the preparation chain, the model harmonic
comparison and the WCS alignment of the products.

    python docs/scripts/make_u12517_overview.py
"""

import warnings

import matplotlib.pyplot as plt
import numpy as np

import common as C

plt.rcParams.update(C.STYLE)
P = C.products()
SCI, GOOD = P["science"] - 3246.0, P["good"]
MODEL, RES, PREP = P["model"], P["residual"], P["prepared"]
PROF = P["profile"]
# display: the same stretch for science, prepared and model
LO, HI = 0.0, np.nanpercentile(MODEL, 99.9)
RLIM = np.nanpercentile(np.abs(RES[GOOD]), 95.0)
NBAD = int((~GOOD).sum())


def show(ax, img, title, cmap="gray", **kw):
    ax.imshow(img, cmap=cmap, interpolation="nearest", **kw)
    ax.set_title(title)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)
    for s in ax.spines.values():
        s.set_visible(False)


def ellipses(ax, every=2, **kw):
    for _, row in PROF.iloc[1::every].iterrows():
        x, y = C.ellipse_xy(row)
        ax.plot(x, y, lw=0.8, color=C.ACCENT, **kw)


def residual_panel(ax, img, title):
    show(ax, np.where(GOOD, img, np.nan), title, cmap="RdBu_r",
         vmin=-RLIM, vmax=RLIM)
    ax.set_facecolor("#9a9a9a")                   # masked pixels: grey


def hero():
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.6))
    show(axes[0], C.stretch(SCI, LO, HI), "Observed galaxy")
    show(axes[1], C.stretch(SCI, LO, HI), "Fitted isophotes")
    ellipses(axes[1])
    show(axes[2], C.stretch(MODEL, LO, HI), "ELLIPROF model")
    residual_panel(axes[3], RES, "Residual")
    fig.text(0.5, 0.02, "UGC 12517, HST WFC3/IR F110W (examples/u12517). "
             "Residual = mask x (science - sky - model); grey = masked.",
             ha="center", fontsize=9, color="#555555")
    fig.subplots_adjust(bottom=0.1, wspace=0.05)
    C.save(fig, "hero_u12517.png")


def hero_profiles():
    prof = PROF.iloc[1:]                # r = 9 lies in the masked nucleus
    fig, axes = plt.subplots(1, 4, figsize=(13, 2.6))
    r = prof.Rmaj
    axes[0].semilogy(r, prof.I0, "o-", ms=3, color=C.INK)
    axes[0].set_ylabel("I0 [image units]")
    axes[1].plot(r, prof.ellip, "o-", ms=3, color=C.INK)
    axes[1].set_ylabel("ellip = 1 - b/a")
    # alpha is an axis direction (0-180); 3 deg and 176 deg differ by only
    # 7 deg, so unwrap for display
    alpha = np.degrees(np.unwrap(np.radians(2 * prof.alpha))) / 2
    axes[2].plot(r, alpha, "o-", ms=3, color=C.INK)
    axes[2].set_ylabel("alpha [deg, unwrapped]")
    axes[3].plot(r, prof.I4, "o-", ms=3, color=C.INK)
    axes[3].set_ylabel("I4 (fraction of I0)")
    for ax in axes:
        ax.set_xlabel("Rmaj [pixels]")
        C.logx(ax)
    fig.tight_layout()
    C.save(fig, "hero_profiles.png")


def preparation():
    fig, axes = plt.subplots(1, 4, figsize=(13, 3.6))
    show(axes[0], C.stretch(SCI, LO, HI), "1. science - sky")
    show(axes[1], GOOD.astype(float), "2. mask (white = good)", vmin=0,
         vmax=1)
    show(axes[2], C.stretch(PREP, LO, HI), "3. prepared = mask x (science - sky)")
    residual_panel(axes[3], RES, "4. residual")
    fig.text(0.5, 0.02, "Real u12517 products written by elliprof "
             f"(--prepared, --residual). {NBAD:,} pixels "
             f"({NBAD / GOOD.size:.1%}) are masked: stars, background "
             "galaxies and image edges.",
             ha="center", fontsize=9, color="#555555")
    C.save(fig, "preparation_chain.png")


def model_vs_science():
    fig, axes = plt.subplots(1, 2, figsize=(8, 4))
    show(axes[0], C.stretch(SCI, LO, HI), "science - sky")
    show(axes[1], C.stretch(MODEL, LO, HI), "MODEL (-m), same stretch")
    fig.text(0.5, 0.02, "The model is smooth and also covers masked "
             "regions (it is never masked).", ha="center", fontsize=9,
             color="#555555")
    C.save(fig, "model_vs_science.png")


def residual_zoom():
    """Centre of the residual: large-scale structure vs pixel noise."""
    cy, cx, h = 562, 567, 160
    cut = np.s_[cy - h:cy + h, cx - h:cx + h]
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 4.2))
    residual_panel(axes[0], RES, "residual (whole image)")
    axes[0].add_patch(plt.Rectangle((cx - h, cy - h), 2 * h, 2 * h,
                                    fill=False, color="k", lw=1))
    lim = np.nanpercentile(np.abs(RES[cut][GOOD[cut]]), 97)
    show(axes[1], np.where(GOOD[cut], RES[cut], np.nan),
         "central 320 x 320 pixels", cmap="RdBu_r", vmin=-lim, vmax=lim)
    axes[1].set_facecolor("#9a9a9a")
    C.save(fig, "residual_zoom.png")


def model_harmonics():
    base = P["model_none"]
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    show(axes[0], C.stretch(base, LO, HI), "--model-harmonics none")
    d4 = P["model_h4"] - base
    d34 = P["model_h34"] - base
    lim = np.nanpercentile(np.abs(d34), 99.5)
    show(axes[1], d4, "model(4) - model(none)", cmap="RdBu_r", vmin=-lim,
         vmax=lim)
    show(axes[2], d34, "model(3,4) - model(none)", cmap="RdBu_r",
         vmin=-lim, vmax=lim)
    fig.text(0.5, 0.02, "Real u12517 models: the 3rd/4th-order terms change"
             " only the model image; the fitted profile is identical.",
             ha="center", fontsize=9, color="#555555")
    C.save(fig, "model_harmonics.png")


def wcs_alignment():
    from astropy.io import fits
    from astropy.wcs import WCS
    names = ("science", "model", "residual")
    files = (C.IMAGE, C.WORK / "u12517j_model.fits",
             C.WORK / "u12517j_residual.fits")
    fig = plt.figure(figsize=(13, 4.4))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for k, (name, f) in enumerate(zip(names, files)):
            h = fits.getheader(f)
            ax = fig.add_subplot(1, 3, k + 1, projection=WCS(h))
            img = fits.getdata(f).astype(float)
            if name == "residual":
                ax.imshow(np.where(GOOD, img, np.nan), cmap="RdBu_r",
                          vmin=-RLIM, vmax=RLIM)
                ax.set_facecolor("#9a9a9a")
            else:
                ax.imshow(C.stretch(img - (3246.0 if name == "science"
                                           else 0), LO, HI), cmap="gray")
            ax.coords.grid(color="#f4a261", alpha=0.7, ls=":")
            ax.coords[0].set_axislabel("RA")
            if k == 0:
                ax.coords[1].set_axislabel("Dec")
            else:
                ax.coords[1].set_ticklabel_visible(False)
                ax.coords[1].set_axislabel("")
            ax.set_title(f"{name}  ({f.name})", fontsize=9)
    fig.text(0.5, 0.02, "The same RA/Dec grid, drawn from each file's own "
             "header: the products carry the science image's WCS.",
             ha="center", fontsize=9, color="#555555")
    C.save(fig, "wcs_alignment.png")


def sbf_residual():
    """What an SBF analysis starts from (illustration, not a measurement)."""
    cy, cx, h = 562, 567, 120
    cut = np.s_[cy - h:cy + h, cx - h:cx + h]
    norm = np.where(GOOD & (MODEL > 0), RES / np.sqrt(np.clip(MODEL, 1, None)),
                    np.nan)
    fig, axes = plt.subplots(1, 2, figsize=(8.5, 4.2))
    lim = np.nanpercentile(np.abs(RES[cut][GOOD[cut]]), 97)
    show(axes[0], np.where(GOOD[cut], RES[cut], np.nan),
         "residual (central region)", cmap="RdBu_r", vmin=-lim, vmax=lim)
    lim2 = np.nanpercentile(np.abs(norm[cut]), 99)
    show(axes[1], norm[cut], "residual / sqrt(model)", cmap="gray",
         vmin=-lim2, vmax=lim2)
    for ax in axes:
        ax.set_facecolor("#9a9a9a")
    fig.text(0.5, 0.02, "Real u12517 residual. Normalising by sqrt(model)"
             " is one step of an SBF analysis; this is NOT an SBF "
             "measurement.", ha="center", fontsize=9, color="#555555")
    C.save(fig, "sbf_residual_illustration.png")


if __name__ == "__main__":
    hero()
    hero_profiles()
    preparation()
    model_vs_science()
    residual_zoom()
    model_harmonics()
    wcs_alignment()
    sbf_residual()
