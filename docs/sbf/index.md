# Surface brightness fluctuations

**Surface brightness fluctuations (SBF)** are one of the most precise ways
to measure distances to early-type galaxies (ellipticals, lenticulars and
bulges). The method was introduced by John Tonry and Donald Schneider in
1988. Distances to individual galaxies are now measured with
uncertainties of about 4–5% out to around 100 Mpc (Jensen et al. 2021;
Cantiello & Blakeslee 2023).

This section explains the idea, what ELLIPROF contributes, and what
lies beyond it.

<div class="scope-box" markdown>
**ELLIPROF is not an SBF pipeline.** It supplies the smooth galaxy model
and the residual image that an SBF measurement starts from. Everything
after that (the power spectrum, the corrections for globular clusters
and background galaxies, the calibration and the distance) is done by
other software and by the researcher. See
[ELLIPROF's role in SBF](elliprof-role.md).
</div>

## The idea in one picture

A galaxy too distant for its stars to be resolved still looks slightly
**grainy**. Each pixel collects the light of a finite, random number of
stars, so neighbouring pixels differ in brightness even where the galaxy
is perfectly smooth on average.

The graininess depends on distance:

- a **nearby** galaxy puts **few** stars in each pixel, so the pixel
  values fluctuate strongly;
- a galaxy **twice as far away** puts **four times as many** stars in
  each pixel, each four times fainter. The average surface brightness is
  the same, but the image is **smoother**.

<figure markdown="span">
  ![Top: three simulated patches of a galaxy with the same average
  brightness. At distance d the patch is visibly mottled; at 2d it is
  smoother; at 4d it is smoother still. Bottom left: the power spectrum of
  the d patch, with the fitted fluctuation component shaped by the
  point-spread function and a flat white-noise floor. Bottom right: the
  fluctuation magnitude derived at d, 2d and 4d, lying on the curve five
  times the logarithm of distance.](../assets/sbf_simulation.png)
  <figcaption>SIMULATION, not a measurement. Identical stars with Poisson
  counts, blurred by a Gaussian PSF, with white noise. The fitted
  fluctuation amplitude P0 recovers the input star flux to 1–4%, and it
  dims by 5 log<sub>10</sub>2 = 1.5 mag for each doubling of distance.
  (<code>docs/scripts/make_sbf_power_spectrum_schematic.py</code>)</figcaption>
</figure>

## Why it works

Let a pixel at distance $d$ contain on average $\bar N$ stars, each of
flux $f$. The star count is Poisson-distributed, so

$$ \text{mean} = \bar N f, \qquad \text{variance} = \bar N f^2, \qquad \frac{\text{variance}}{\text{mean}} = f. $$

With distance, $\bar N \propto d^2$ (a pixel covers more of the galaxy)
and $f \propto d^{-2}$. The **mean** (the surface brightness) does not
depend on distance, but **variance / mean** falls as $1/d^2$. Measuring
the ratio of the fluctuation variance to the galaxy's mean brightness is
therefore measuring the flux of a "typical" star, and hence the
distance.

Real galaxies contain stars of many luminosities. The quantity measured
is then the **fluctuation flux**

$$ \bar f = \frac{\sum_i n_i f_i^2}{\sum_i n_i f_i}, $$

the ratio of the second to the first moment of the stellar luminosity
function ($n_i$ stars of flux $f_i$). It is dominated by the most luminous
stars: red giants, and in the infrared the asymptotic giant branch
(Tonry & Schneider 1988; Cantiello & Blakeslee 2023).

In magnitudes, the **apparent fluctuation magnitude** $\bar m$ and the
**absolute fluctuation magnitude** $\bar M$ give the distance modulus:

$$ \mu = \bar m - \bar M, \qquad d = 10^{(\mu + 5)/5}\ \text{pc}. $$

## The catch: the absolute fluctuation magnitude is not universal

$\bar M$ depends on the stellar population: its age, its metallicity,
and the filter. It is calibrated empirically as a function of galaxy
colour, from galaxies with distances measured by other methods (Cepheids,
the tip of the red giant branch). Stellar population models check it.
The calibration is different for every filter and camera. The infrared
fluctuations are brighter, but their calibration is more sensitive to
the population (Jensen et al. 2003, 2015; Blakeslee et al. 2010). See
[Power spectrum and distance](power-spectrum.md).

## Why distances matter

Distances turn observed quantities (brightness, angular size) into
physical ones (luminosity, size, mass). For galaxies beyond a few Mpc,
accurate distances are rare and precious. SBF distances have been used
to:

- map the **three-dimensional structure** of the Virgo cluster (Mei et
  al. 2007) and **large-scale flows** of galaxies (Tonry et al. 2000);
- measure the **Hubble constant**: $H_0 = 73.3 \pm 0.7 \pm 2.4$ km/s/Mpc
  from infrared SBF distances to 63 galaxies (Blakeslee et al. 2021);
- calibrate **Type Ia supernovae** in early-type hosts, and improve the
  **stellar and black-hole masses** of massive galaxies (Jensen et al.
  2021).

## In this section

- [ELLIPROF's role in SBF](elliprof-role.md): why the galaxy model
  matters, and where ELLIPROF stops.
- [Power spectrum and distance](power-spectrum.md): from the residual to
  $\bar m$, $\mu$ and $d$.
- [Workflow and cautions](workflow.md): the full chain, and what can go
  wrong.
- [History and references](history.md): from Tonry & Schneider (1988) to
  today, with verified references.
- Tutorial: [A residual for SBF work](../tutorials/sbf-residual.md).
