# Common mistakes

**Opening the `.prf` file in DS9.**
The `.prf` is a table of numbers, not an image. Use `--reg` for the
ellipses on the image, and `MODEL -m` / `--residual` for images. See
[The profile](../outputs/profile.md).

**A centre off by half a pixel.**
ELLIPROF coordinates are FITS/DS9 pixel numbers minus 0.5. A galaxy at
DS9 pixel (567.5, 562.5) has `X0=567 Y0=562`. See
[How ELLIPROF fits a galaxy](../concepts/how-it-works.md#1-the-initial-centre-and-the-fitted-centres).

**Expecting ELLIPROF to find the galaxy.**
It does not. `X0`, `Y0` are required. Give the galaxy's peak; a centre on
a star or several pixels off makes the inner isophotes wander.

**Using `SKY=` to subtract the sky.**
`SKY=` only affects the de Vaucouleurs fit ELLIPROF prints. To subtract
a sky, use `--sky` or `--sky-image`. See
[Sky and masks](../concepts/sky-and-masks.md).

**Forgetting the sky.**
Without `--sky` or `--sky-image`, nothing is subtracted. The outer
profile is then wrong, and masked pixels (set to 0) are no longer
distinguishable from sky-level pixels.

**An inverted mask.**
In elliprof masks, **0 = bad**. If your mask has 1 for bad pixels,
invert it first. elliprof reports how many pixels are masked. If that
number is most of the image, the mask is probably inverted.

**Treating mask values as weights.**
The mask is logical. 0.5 means "good", not "half weight".

**A mask or sky image of a different size.**
They must match the science image exactly. elliprof never resizes or
reprojects. Cut them to the same pixels first.

**Forgetting quotes around an extension.**
`elliprof galaxy.fits[SCI] ...` fails in many shells, because the brackets
are a shell pattern. Write `'galaxy.fits[SCI]'`.

**Reading `A4` as a position angle.**
`A3`/`A4` are phases around the ellipse, measured from the major axis.
The position angle is `alpha`. See
[Boxy and disky isophotes](../concepts/harmonics.md).

**Comparing `I4` with a4/a from another program.**
`I4` is an intensity amplitude. Convert:
a4/a ≈ I4 cos(4 A4) / (−slope).

**Reading `alpha` as a sky position angle.**
`alpha` is counter-clockwise from the image +y axis. Use the WCS to
convert to east of north. Also, 2° and 178° are nearly the same
orientation; unwrap before plotting.

**Believing the outer isophotes.**
Far out, the sky and the mask dominate. Test the sky's effect and watch
for jumps. See [Galaxy surface photometry](../science/surface-photometry.md#the-outer-isophotes).

**Believing the model inside R0 or beyond R1.**
It is extrapolated there, not fitted.

**Treating `--model-harmonics` as a fitting option.**
It changes the model image, not the profile. Only `--sixth-order`
changes the fit.

**Calling the residual an SBF measurement.**
The residual is an input to an SBF analysis. See
[ELLIPROF's role in SBF](../sbf/elliprof-role.md).

**Using a residual that is 0 on masked pixels as data.**
Masked pixels in the residual are exactly 0, not measurements. Exclude
them with the mask in any statistics.
