# FAQ

**What kinds of galaxies is ELLIPROF for?**
Smooth light distributions: elliptical and lenticular galaxies, bulges,
and other early-type systems. It describes a galaxy as nested ellipses,
so it is not the right tool for irregular galaxies or strongly
structured light (spiral arms, bars, bright clumps).

**Does elliprof find the galaxy centre?**
No. You give the initial centre (`X0`, `Y0`). ELLIPROF then fits a centre
for every isophote.

**Does elliprof estimate the sky?**
No. Give it with `--sky` or `--sky-image`.

**Does elliprof make masks?**
No. It uses a mask you make. See
[Sky and masks](../concepts/sky-and-masks.md#masks).

**Why is my first isophote unchanged, with I3 = I4 = 0?**
It had too few usable samples (for example, it lies inside a masked
nucleus), so it kept its starting values. elliprof prints a note. Start
at a larger `R0`.

**What units is `I0` in?**
The image's units per pixel, after the sky is subtracted. See
[Galaxy surface photometry](../science/surface-photometry.md) to
convert to mag/arcsec².

**Are there uncertainties on the profile?**
No. Estimate them from repeated fits with different skies, masks or
starting values, or from simulations.

**Why does `alpha` jump from ~2° to ~178°?**
It is an axis direction, 0–180°, so 2° and 178° are only 4° apart.
Unwrap it before plotting (see [The profile](../outputs/profile.md#plotting-conventions)).

**Is `A4` = 0 the same as `A4` = 90?**
Yes. Both mean extra light along the axes: disky.

**Do `--model-harmonics` and `COS3X`/`COS4X` change the fit?**
No, only the model image (and so the residual). The exception is
`--sixth-order` (`COS3X` < 0), which changes the fit.

**Can I get the profile as an image?**
The profile is a table. The model image (`MODEL -m`) is the profile
turned into an image. Plot the profile from the CSV or with
`read_profile`.

**Does the model have the WCS of my image?**
Yes. The model, residual and prepared images carry the header of the
science HDU, WCS included.

**Can I fit an image in a FITS extension?**
Yes: `'galaxy.fits[SCI]'` or `'galaxy.fits[1]'`, quoted.

**Can elliprof measure SBF distances?**
No. It provides the model and residual an SBF analysis starts from.
See [ELLIPROF's role in SBF](../sbf/elliprof-role.md).

**How is elliprof related to the original ELLIPROF?**
The fitting code *is* the original ELLIPROF, compiled unchanged. See
[How elliprof is built](../reference/architecture.md).

**How should I cite it?**
Cite the software with its version and repository
(<https://github.com/ekourkchi/elliprof>). State that ELLIPROF was
originally developed by John Tonry as part of MONSTA. Report the
parameters you used.

**Where do I report a problem?**
<https://github.com/ekourkchi/elliprof/issues>. Include the output of
`elliprof --diagnostics`.
