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

!!! warning "Check the image units"
    The zeropoint must match the units of the pixel values. If the image
    is in electrons per second, use the zeropoint for 1 e/s. If it is in
    total electrons, add $2.5\log_{10}(t_\mathrm{exp})$ to that zeropoint.
    The `BUNIT` keyword is not always right, so check it against the
    exposure time and a known sky or star brightness.

For publication-quality photometry you would also correct for Galactic
extinction and, for distant galaxies, apply a K-correction and the
$(1+z)^4$ cosmological surface-brightness dimming.

### Worked example: UGC 12517

The repository's `examples/u12517/calibrate.dat` holds the calibration
from the original analysis (elliprof does not read it):

| | |
|---|---|
| pixel scale $s$ | 0.128″ / pixel |
| $m_1$ for 1 electron (`M1STAR`) | 35.081 mag |
| sky (`SKY`) | 3250 e / pixel = 21.84 mag arcsec⁻² (`SKYMAG`) |

These are consistent with each other:
35.081 − 2.5 log₁₀(3250 / 0.128²) = 21.84. So the pixel values are
electrons, although the image's `BUNIT` says `ELECTRONS/S`. (Its
`M1_J` = 26.822 for 1 e/s plus 2.5 log₁₀ of the 2011.7 s exposure gives
the same 35.081.)

<figure markdown="span">
  ![Two plots of the surface brightness of UGC 12517 in magnitudes per
  square arcsecond, from about 16.5 at 1.5 arcseconds to 22.6 at 44
  arcseconds. Left against the logarithm of the radius, curving
  downwards. Right against the radius to the one-quarter power, very
  nearly a straight line. A dashed line marks the sky brightness, 21.84
  mag per square arcsecond, which the profile crosses at about 32
  arcseconds.](../assets/surface_brightness_u12517.png)
  <figcaption>The calibrated UGC 12517 profile. Against r<sup>1/4</sup> it is
  nearly straight, as for a de Vaucouleurs law. Beyond ~32″ the galaxy is
  fainter than the sky. No extinction or K-correction is applied.</figcaption>
</figure>

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
  brightnesses. (elliprof 0.1.3 cannot impose the geometry of one fit on
  another. `FIXCTR=1` fixes the centre, and `ELLIP=` fixes one
  ellipticity for all isophotes.)

With `--verbose`, ELLIPROF also prints its own de Vaucouleurs fit at the
end of a run (a line starting `Re =`, in pixels and image units). It uses
the separate `SKY=` keyword and is intended as a quick look.
