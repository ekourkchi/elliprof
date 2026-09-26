"""Surface brightness fluctuations explained with a SIMULATION (no real
galaxy): why fluctuations measure distance, and the power-spectrum fit
P(k) = P0 E(k) + P1.  None of this is done by ELLIPROF.

    python docs/scripts/make_sbf_power_spectrum_schematic.py

Model: every pixel holds a Poisson number of identical stars.  At distance
d a pixel holds Nbar stars of flux f; at 2d it holds 4 Nbar stars of flux
f/4.  The mean surface brightness is the same, but the pixel-to-pixel
variance / mean equals f, i.e. falls as 1/d^2.
"""

import matplotlib.pyplot as plt
import numpy as np

import common as C

plt.rcParams.update(C.STYLE)
RNG = np.random.default_rng(12517)
N = 512
PSF_SIGMA = 1.5            # pixels
NOISE = 0.02               # white noise, relative to the mean level


def psf_fft():
    k = np.fft.fftfreq(N)
    kx, ky = np.meshgrid(k, k)
    return np.exp(-2 * (np.pi * PSF_SIGMA) ** 2 * (kx ** 2 + ky ** 2))


def field(nbar, flux):
    """Mean level = nbar * flux, convolved with a unit-sum Gaussian PSF."""
    img = flux * RNG.poisson(nbar, (N, N)).astype(float)
    img = np.real(np.fft.ifft2(np.fft.fft2(img) * psf_fft()))
    mean = nbar * flux
    return img + RNG.normal(0, NOISE * mean, (N, N)), mean


def azimuthal(p2):
    k = np.fft.fftfreq(N)
    kx, ky = np.meshgrid(k, k)
    kr = np.hypot(kx, ky) * N                  # wavenumber in 1/N units
    bins = np.arange(1, N // 2)
    idx = np.digitize(kr.ravel(), bins)
    prof = np.bincount(idx, p2.ravel(), len(bins) + 1)
    cnt = np.bincount(idx, minlength=len(bins) + 1)
    kc = 0.5 * (bins[:-1] + bins[1:])
    return kc, (prof / np.maximum(cnt, 1))[1:len(bins)]


def power_spectrum(img, mean):
    """Normalise by sqrt(mean) as an SBF analysis does with sqrt(model)."""
    x = (img - mean) / np.sqrt(mean)
    p2 = np.abs(np.fft.fft2(x)) ** 2 / x.size
    return azimuthal(p2)


def fit(k, pk, ek, lo=16, hi=180):
    sel = (k > lo) & (k < hi)
    a = np.vstack([ek[sel], np.ones(sel.sum())]).T
    (p0, p1), *_ = np.linalg.lstsq(a, pk[sel], rcond=None)
    return p0, p1, sel


def main():
    kc, ek = azimuthal(np.abs(psf_fft()) ** 2)
    cases = ((50, 1.0, "distance d"), (200, 0.25, "distance 2d"),
             (800, 0.0625, "distance 4d"))
    fig = plt.figure(figsize=(12, 8.2))
    gs = fig.add_gridspec(2, 3, height_ratios=(1, 1.15))
    results = []
    for i, (nbar, flux, lab) in enumerate(cases):
        img, mean = field(nbar, flux)
        ax = fig.add_subplot(gs[0, i])
        cut = img[:96, :96] / mean
        ax.imshow(cut, cmap="gray", vmin=0.7, vmax=1.3,
                  interpolation="nearest")
        ax.set_title(f"{lab}: {nbar} stars/pixel, flux {flux:g} each\n"
                     f"mean = {mean:g}, rms/mean = {cut.std():.3f}",
                     fontsize=9)
        ax.set_xticks([])
        ax.set_yticks([])
        ax.grid(False)
        k, pk = power_spectrum(img, mean)
        p0, p1, sel = fit(k, pk, ek)
        results.append((lab, flux, p0, p1, k, pk, sel))
    ax = fig.add_subplot(gs[1, :2])
    lab, flux, p0, p1, k, pk, sel = results[0]
    ax.semilogy(k, pk, ".", color="#999999", ms=4, label="P(k) of the "
                "normalised image")
    ax.semilogy(k[sel], pk[sel], ".", color=C.INK, ms=5,
                label="points used in the fit")
    ax.semilogy(kc, p0 * ek + p1, color=C.ACCENT, lw=2,
                label=rf"fit: $P_0E(k)+P_1$, $P_0$ = {p0:.3f} (true {flux:g})")
    ax.semilogy(kc, p0 * ek, color=C.ACCENT, lw=1, ls="--",
                label=r"$P_0E(k)$: fluctuations, shaped by the PSF")
    ax.axhline(p1, color="#2a9d8f", lw=1, ls=":",
               label=rf"$P_1$: white noise ({p1:.4f})")
    ax.set_ylim(p1 / 5, 3 * p0)
    ax.set_xlabel("wavenumber k [cycles per 512 pixels]")
    ax.set_ylabel("power")
    ax.set_title("Power spectrum at distance d", fontsize=10)
    ax.legend(frameon=False, fontsize=8, loc="upper right")
    ax = fig.add_subplot(gs[1, 2])
    d = np.array([1, 2, 4])
    p0s = np.array([r[2] for r in results])
    mbar = -2.5 * np.log10(p0s)
    ax.plot(d, mbar - mbar[0], "o", color=C.INK, ms=7, label="fitted")
    dd = np.linspace(0.9, 4.4, 50)
    ax.plot(dd, 5 * np.log10(dd), color=C.ACCENT,
            label=r"$5\log_{10}(d/d_1)$")
    ax.set_xlabel("distance / d")
    ax.set_ylabel(r"$\bar m - \bar m(d)$ [mag]")
    ax.set_title(r"$\bar m = -2.5\log_{10}P_0$ + const", fontsize=10)
    ax.legend(frameon=False, fontsize=9)
    ax.invert_yaxis()
    fig.text(0.99, 0.0, "SIMULATION - identical stars, Gaussian PSF; not a "
             "measurement and not done by ELLIPROF", ha="right", fontsize=8,
             color="#888888", style="italic")
    fig.tight_layout()
    C.save(fig, "sbf_simulation.png")
    with open(C.WORK / "sbf_simulation.txt", "w") as f:
        for lab, flux, p0, p1, *_ in results:
            f.write(f"{lab}: true {flux:g}  P0 {p0:.4f}  P1 {p1:.5f}  "
                    f"mbar {-2.5 * np.log10(p0):.3f}\n")


if __name__ == "__main__":
    main()
