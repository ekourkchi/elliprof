# Galaxy surface photometry

ELLIPROF measures the intensity `I0` of each isophote in the **image's
own units per pixel**, after the sky is subtracted. To compare galaxies,
or to compare with models, you convert this to **surface brightness** in
magnitudes per square arcsecond. ELLIPROF does not do that conversion
for you.

## From I0 to mag/arcsec²

You need:

1. the **pixel scale** $s$, in arcseconds per pixel;
2. a **photometric zeropoint**: the magnitude $m_1$ of one unit of image
   flux (for example, of 1 electron, or of 1 electron per second if the
   image is in e/s).

Then

$$ \mu = m_1 - 2.5\log_{10}\!\left(\frac{I_0}{s^2}\right) \quad [\text{mag arcsec}^{-2}] $$

Dividing by $s^2$ converts "per pixel" into "per square arcsecond".

**Check the image units**

The zeropoint must match the units of the pixel values. If the image
is in electrons per second, use the zeropoint for 1 e/s. If it is in
total electrons, add $2.5\log_{10}(t_\mathrm{exp})$ to that zeropoint.

For publication-quality photometry you would also correct for Galactic
extinction and, for distant galaxies, apply a K-correction and the
$(1+z)^4$ cosmological surface-brightness dimming.

### The UGC 12517 example

On this site, the UGC 12517 profile is shown in the image's own units:
`I0` per pixel, exactly as ELLIPROF reports it. To express it in
mag/arcsec², use the formula above with the zeropoint for the image's
units and $s$ = 0.128″/pixel.

## The outer isophotes

The outskirts of galaxies carry information about their assembly: haloes,
shells, tidal debris. They are also where isophote fitting is least
reliable.

- **The sky dominates.** A small sky error changes the outer profile
  strongly; see [Why the sky matters](../concepts/sky-and-masks.md#why-the-sky-matters).
- **Few good pixels.** Large ellipses cross many masked sources and the
  image edges, and the fit then has fewer samples.
- **The image edge.** An isophote that runs off the image is sampled only
  on one side. Its centre and shape then become unreliable.
- **Noise per sample is large**, so centres, ellipticities and angles
  scatter more. Watch for sudden jumps in the outer profile.

!!! beginner "How far out can I trust the profile?"
    A practical rule: trust the outer profile only while the galaxy is
    clearly brighter than the uncertainty of the sky, and while the
    ellipse stays inside the image with most of its samples unmasked.
    Repeat the fit with the sky changed by its uncertainty. Where the
    profiles disagree by more than you can accept, stop.

## Other derived quantities

From the profile you can compute, for example:

- **total magnitudes** and **half-light radii**, by integrating the
  intensity over the area of the elliptical annuli (the area of an
  ellipse is $\pi a^2 (1-\epsilon)$);
- **Sérsic** or **de Vaucouleurs** fits to $\mu(a)$;
- **colour profiles**, by comparing two filters at matched semi-major
  axes (the same `R0`, `R1`, `NR`, `RLAW` and centre). Fit each filter,
  check that the geometries agree, and difference the surface
  brightnesses. (elliprof, as of 0.1.4, cannot impose the geometry of one fit on
  another. `FIXCTR=1` fixes the centre, and `ELLIP=` fixes one
  ellipticity for all isophotes.)

With `--verbose`, ELLIPROF also prints its own de Vaucouleurs fit at the
end of a run (a line starting `Re =`, in pixels and image units). It uses
the separate `SKY=` keyword and is intended as a quick look.
