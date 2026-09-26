# Sky and masks

Before fitting, elliprof prepares the image:

$$ \text{prepared} = \text{mask} \times (\text{science} - \text{sky}) $$

ELLIPROF then **ignores every pixel that is exactly 0**. That is how
masked pixels drop out of the fit. It is also why the sky must be
subtracted *before* the mask is applied, and elliprof does it in that
order.

<figure markdown="span">
  ![Four panels for UGC 12517: the sky-subtracted image; the mask, white
  where pixels are good and black where they are masked, with holes at
  stars, galaxies and the image edges; the prepared image, which is the
  galaxy with those holes cut out; and the residual in red and blue with
  the masked areas grey.](../assets/preparation_chain.png)
  <figcaption>The preparation chain for UGC 12517 (real elliprof products).
  The prepared image (<code>--prepared</code>) is exactly what ELLIPROF
  fits.</figcaption>
</figure>

## The sky

**ELLIPROF never estimates the sky for you.** You supply it:

```sh
elliprof galaxy.fits --sky 1234.5 ...              # one constant level
elliprof galaxy.fits --sky-image background.fits ...  # a 2-D background
```

- `--sky VALUE` subtracts the same number from every pixel, in image
  units.
- `--sky-image FILE` subtracts a background image pixel by pixel. It must
  have exactly the same dimensions as the science image.
- Use one or the other, not both. Without either, nothing is subtracted.
  That is right only if your image is already sky-subtracted.

!!! warning "`SKY=` is not `--sky`"
    The original keyword `SKY=s` does **not** subtract anything. It is
    used only by the de Vaucouleurs fit that ELLIPROF prints at the end.
    To subtract a sky, use `--sky` or `--sky-image`.

### Why the sky matters

In the bright inner galaxy the sky is a small correction. In the faint
outskirts the galaxy can be fainter than the sky, so a small sky error
becomes a large fraction of the measured light. The outer profile comes
out too bright if the sky was underestimated, and too faint (falling
too steeply) if it was overestimated.

<figure markdown="span">
  ![Left: the isophote intensity of UGC 12517 against semi-major axis for
  five sky levels, 3096 to 3396 in image units; the curves lie on top of
  each other except at the largest radii. Right: the percentage change in
  intensity relative to the adopted sky; it is zero in the centre and
  grows to about plus or minus 10 percent at the outermost isophote for a
  sky change of 150.](../assets/sky_sensitivity.png)
  <figcaption>Real elliprof fits of UGC 12517 that differ only in the
  subtracted sky (measured intensities, no calibration). Changing the sky
  by 150 image units (4.6% of the sky level) changes the outermost
  isophote's intensity by about 10%, because there the sky is about twice
  as bright as the galaxy. The inner profile does not move.</figcaption>
</figure>

!!! researcher "Measure the sky carefully"
    Measure the sky far from the galaxy, with sources masked, or fit it
    together with the galaxy's outer profile. Where the galaxy fills the
    image, the sky is uncertain, and so is the outer profile. Report the
    sky you used. Check how sensitive your results are by repeating the
    fit with the sky changed by its uncertainty, as in the figure.

## Masks

A mask marks the pixels to ignore: stars, background galaxies, dust
lanes, bad columns, cosmic rays, image edges.

```sh
elliprof galaxy.fits --mask mask.fits --sky 1234.5 ...
```

- **The mask is logical.** 0 = bad (ignored). Any other finite value (1,
  2, −1, 0.5, ...) = good. NaN, ±Inf and undefined (`BLANK`) pixels =
  bad.
- **The values are never weights.** Bad pixels become exactly 0, and good
  pixels keep their value.
- The mask may be a FITS image of any type (`BITPIX` 8, 16, 32, 64, −32,
  −64), or a historical ELLIPROF `.dmask` bitmap (`BITPIX = 1`). The type
  is recognised from the file itself.
- It must have exactly the same dimensions as the science image. Nothing
  is ever resized, interpolated, cropped, shifted or reprojected.
- A mask in a FITS extension is chosen like an image:
  `--mask 'products.fits[MASK]'`.

!!! beginner "Making a mask"
    elliprof uses masks but does not make them. Common ways are a
    source-detection program (such as SExtractor or photutils) with the
    detected sources grown by a few pixels; hand-drawn DS9 regions turned
    into a mask; or both. Mask generously around bright stars, including
    their diffraction spikes.

!!! warning "A pixel that is exactly 0 is always ignored"
    ELLIPROF cannot tell a masked pixel from a good pixel whose
    sky-subtracted value happens to be exactly 0. With floating-point
    images this is rare. With integer images and an integer sky it can
    happen, so check the number of masked pixels that elliprof reports.

## The prepared image

`--prepared FILE` writes the image exactly as ELLIPROF fits it:
`mask × (science − sky)`, as float32 FITS with the science image's
header and WCS. Look at it whenever a fit behaves oddly. Most problems
(a wrong sky, a mask that is too small, an inverted mask) are obvious in
the prepared image.

See also [Model, residual and prepared images](../outputs/images.md).
