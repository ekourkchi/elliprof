# Model, residual and prepared images

Besides the [profile](profile.md), elliprof can write three images:

| Option | Image | Definition |
|---|---|---|
| `MODEL -m FILE` | **model** | the galaxy rebuilt from the fitted isophotes |
| `--residual FILE` | **residual** | mask × (science − sky − model) |
| `--prepared FILE` | **prepared** | mask × (science − sky): exactly what ELLIPROF fits |

```sh
elliprof galaxy.fits --mask mask.fits --sky 1234.5 \
    X0=500 Y0=500 R0=5 R1=200 NR=30 \
    MODEL -m galaxy_model.fits \
    --residual galaxy_residual.fits \
    --prepared galaxy_prepared.fits
```

`--residual` implies `MODEL`. It uses the same model as `-m`, and `-m`
is only needed if you also want the model itself.

## The model

<figure markdown="span">
  ![Left: the sky-subtracted image of UGC 12517 with stars and background
  galaxies. Right: the model, a smooth elliptical light distribution with
  no stars, shown with the same brightness scale.](../assets/model_vs_science.png)
  <figcaption>UGC 12517 and its ELLIPROF model, on the same brightness scale
  (real products).</figcaption>
</figure>

- The model follows the fitted intensity, centre, ellipticity and
  position angle with radius, plus the chosen
  [harmonic terms](../concepts/harmonics.md#the-harmonics-in-the-model-image).
- It is **relative to the subtracted sky**: add the sky back to compare
  with the raw image.
- It covers **the whole image, masked pixels included**. It is never
  masked.
- Inside R0 and beyond R1 it is extrapolated, not fitted.

## The residual

$$ \text{residual} = \text{mask}\times(\text{science} - \text{sky} - \text{model}) $$

On good pixels it is science − sky − model. On masked pixels it is
exactly 0.

<figure markdown="span">
  ![Left: the residual of UGC 12517 over the whole image, in red (positive)
  and blue (negative), with masked areas in grey and a box around the
  centre. Right: the central 320 by 320 pixels enlarged, showing
  fine-grained noise and a small structured pattern at the very
  centre.](../assets/residual_zoom.png)
  <figcaption>The UGC 12517 residual (real product; grey = masked). Away
  from the centre it is dominated by pixel-to-pixel noise and by faint
  sources that the mask did not cover. The pattern at the centre is where
  the smooth model fits worst.</figcaption>
</figure>

The residual shows the light that the smooth isophotal model does **not**
describe:

- **dust** lanes and patches (negative, absorbing light);
- embedded **disks**, bars and rings;
- **shells**, ripples and **tidal features**;
- **globular clusters** and background galaxies (positive point-like
  sources);
- **fitting problems**: a wrong sky, a poor centre, an isophote that did
  not converge, a region inside R0 or beyond R1.

!!! researcher "Interpret with care"
    The residual depends on the fit, the mask and the model settings. A
    feature that changes when you change the model harmonics, the radial
    sampling or the mask is not a property of the galaxy. Compare the
    residuals from `--model-harmonics none` and the default before
    interpreting 4-fold patterns.

The residual is also the starting point of a surface brightness
fluctuation analysis. See [ELLIPROF's role in SBF](../sbf/elliprof-role.md).

## The prepared image

`--prepared` writes `mask × (science − sky)`, the image exactly as
ELLIPROF fits it. Masked pixels are 0. It is the quickest way to check
the sky and the mask. See [Sky and masks](../concepts/sky-and-masks.md).

## Headers and WCS

All three images are **float32 FITS** and carry the **header of the
science image**, including its WCS (`CTYPE`, `CRPIX`, `CRVAL`,
`CD`/`PC`/`CDELT`, distortion terms), `BUNIT` and the other keywords. Only
the cards that describe how the science data were stored are left out,
such as `BITPIX`, `BSCALE`, `BZERO` and `BLANK`.

<figure markdown="span">
  ![Three panels, the science image, the model and the residual, each
  drawn with right ascension and declination axes read from its own FITS
  header. The coordinate grids are identical in all
  three.](../assets/wcs_alignment.png)
  <figcaption>Each panel's RA/Dec grid comes from that file's own header
  (real products). They are identical, so the images overlay exactly in
  DS9 and other WCS-aware software.</figcaption>
</figure>

In DS9, load the images in separate frames and use
**Frame → Lock → Frame → WCS**. Images are never resized, cropped,
shifted or reprojected, so pixel (i, j) of every product is pixel (i, j)
of the science image.

## Images in FITS extensions

Many archives store the science image in an extension (for example `SCI`
in HST files). Select it with CFITSIO syntax, quoted for the shell:

```sh
elliprof 'galaxy.fits[SCI]' X0=500 Y0=500 R0=5 R1=200 NR=30 \
    MODEL -m galaxy_model.fits
elliprof 'galaxy.fits[1]'   X0=500 Y0=500 R0=5 R1=200 NR=30
```

- Only the selected HDU is fitted, and its header and WCS go into the
  products.
- elliprof never falls back to another HDU. If the selected one is not a
  2-D image, it stops with an error.
- `--mask` and `--sky-image` take the same syntax:
  `--mask 'galaxy.fits[MASK]'`.
- Tile-compressed FITS images (as written by `fpack` or astropy's
  `CompImageHDU`) are read like any other extension.
