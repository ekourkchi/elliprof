# ELLIPROF's role in SBF

## The scope boundary

<div class="scope-box" markdown>
**What ELLIPROF does:** it fits elliptical isophotes to the galaxy and
builds a smooth **model** of it. elliprof then writes the **residual**,
mask × (science − sky − model), with the science image's header and WCS.

**What ELLIPROF does not do:** estimate the sky; make the mask; detect
or correct for globular clusters and background galaxies; normalise the
residual; compute or fit the power spectrum; measure the PSF; apply a
calibration; or give a distance.
</div>

ELLIPROF is one component of an SBF measurement: the galaxy model, and
through it the residual. The rest is done by other software and by the
researcher, and needs judgement that no single program should hide.

## ELLIPROF in published SBF analyses

ELLIPROF has historically been used as the **galaxy-modelling component**
of surface brightness fluctuation analyses. It fits and subtracts the
smooth galaxy light distribution, producing the galaxy-subtracted image
used in the subsequent SBF processing. The power-spectrum measurement,
the contaminant corrections, the calibration and the distance
determination are separate, downstream steps.

The published record:

- **The I-band SBF Survey.** Tonry et al. (1997) describe the step as
  fitting "a galaxy model to the summed, cleaned, sky-subtracted galaxy
  image" and subtracting it. The ACS Virgo Cluster Survey papers identify
  that software as ELLIPROF. Jordán et al. (2004) write that "galaxies
  were modeled using the ELLIPROF program described in the SBF survey of
  Tonry et al. (1997)". Mei et al. (2005a) call ELLIPROF "the isophotal
  fitting software that has been used for the SBF survey by Tonry et al.
  1997".
- **The ACS Virgo Cluster Survey (HST/ACS).** Jordán et al. (2004) and
  Mei et al. (2005a) fitted a smooth model to each galaxy with ELLIPROF
  and subtracted it. They then removed the remaining large-scale
  residuals with a SExtractor background model before detecting sources
  and measuring the SBF.
- **Infrared SBF with HST/WFC3 (the MASSIVE and Type Ia supernova host
  galaxies).** Jensen et al. (2021) made an elliptical model of each
  galaxy "using the ELLIPROF routine", first to help determine the
  background level and then, after background subtraction, as the smooth
  galaxy model. They saved that model "for later use to normalize the SBF
  power spectrum", and list ELLIPROF among the software used.

In all of these, ELLIPROF supplies the galaxy model. The SBF measurement
itself is the downstream chain described on
[Power spectrum and distance](power-spectrum.md) and
[Workflow and cautions](workflow.md). The full references are on
[History and references](history.md#elliprof-in-sbf-analyses).

!!! note "The same program"
    The `elliprof` package runs the original ELLIPROF fitting and model
    code, compiled unchanged (see
    [How elliprof is built](../reference/architecture.md)). The published
    analyses above used ELLIPROF within their own pipelines and
    environments. This package makes the same fitting and model code
    available on its own. It does not reproduce those pipelines.

## Why the galaxy model matters

The fluctuations are tiny compared with the galaxy itself. In the
[simulation](index.md#the-idea-in-one-picture), the pixel-to-pixel rms
is only a few percent of the mean, and in real data it is often much
less. Before they can be measured, the smooth galaxy must be removed
**very accurately**:

- Any error in the model is a large-scale pattern in the residual. That
  puts power at **low wavenumbers** in the power spectrum, where the
  fluctuation signal is also measured.
- The model is also needed to **normalise** the residual. The fluctuation
  variance is proportional to the local galaxy brightness, so the
  residual is divided by $\sqrt{\text{model}}$ to make the fluctuation
  amplitude uniform across the image.

A model built from fitted isophotes follows the galaxy's changing
ellipticity, orientation and boxy/disky shape with radius, so it
removes the galaxy closely. The published analyses above also describe
where such models fall short: Jordán et al. (2004) report that for seven
galaxies with strong disk components ELLIPROF could not produce
acceptable models. Jensen et al. (2021) fitted the remaining residual
patterns (from neighbouring galaxies, dust lanes, shells, spiral
structure or bars) with a spline and avoided the affected regions and
low wavenumbers.

!!! advanced "Model harmonics and the residual"
    Include the 3rd- and 4th-order terms in the model (the default,
    `--model-harmonics 3,4`), so that boxy or disky isophotes do not
    leave a 4-fold pattern in the residual. Compare with
    `--model-harmonics none` to see how much they matter for your galaxy.
    See [Boxy and disky isophotes](../concepts/harmonics.md#the-harmonics-in-the-model-image).

## The residual ELLIPROF provides

<figure markdown="span">
  ![Left: the central 240 by 240 pixels of the UGC 12517 residual in red
  and blue, with masked regions grey. Right: the same region divided by
  the square root of the model, in grey, showing fine-grained
  mottling.](../assets/sbf_residual_illustration.png)
  <figcaption>The real UGC 12517 residual from elliprof (left) and the same
  residual divided by √model (right). The normalisation is a downstream
  step, shown here only for illustration. <strong>This is not an SBF
  measurement.</strong></figcaption>
</figure>

```sh
elliprof galaxy.fits --mask mask.fits --sky SKY \
    X0=... Y0=... R0=... R1=... NR=... NITER=10 \
    MODEL -m galaxy_model.fits --residual galaxy_residual.fits
```

What you get:

- `galaxy_model.fits`: the smooth model, relative to the sky, covering
  the whole image;
- `galaxy_residual.fits`: science − sky − model on good pixels, exactly
  0 on masked pixels;
- both in float32, with the science image's WCS, pixel for pixel aligned
  with it.

The [tutorial](../tutorials/sbf-residual.md) walks through this for
UGC 12517 and shows what to check before handing the residual on.

## What a residual is not ready for yet

An ELLIPROF residual still contains:

- **large-scale structure** that the model did not follow (a residual
  sky gradient, dust, faint disks). SBF analyses usually remove it with
  a further smoothing step;
- **point sources**: globular clusters and background galaxies. They add
  their own fluctuations and must be masked down to a limit, with the
  contribution of fainter, undetected ones estimated from their
  luminosity functions;
- the **noise** of the detector and the sky.

These are all downstream steps; see [Workflow and cautions](workflow.md).
