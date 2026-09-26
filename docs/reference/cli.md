# Command-line reference

This page documents **elliprof 0.1.3**. `elliprof -h` prints the same
information.

```text
elliprof IMAGE.fits X0=x Y0=y R0=r R1=r NR=n [KEYWORD=value ...] [options]
```

Keywords (`KEY=value`, case-insensitive) and options may follow the
image in any order. The output is a short summary (inputs, notes, files
written). The profile table is printed only if neither `-o` nor `--csv`
is given.

## Input image and initial centre

| Argument | Meaning |
|---|---|
| `IMAGE.fits` | 2-D FITS image (first argument). Select an extension with CFITSIO syntax, quoted: `'galaxy.fits[SCI]'`, `'galaxy.fits[1]'`. The selected HDU is fitted; there is no fallback to another |
| `X0=x Y0=y` | **required** initial centre, in pixels. ELLIPROF refines the centre of each isophote unless `FIXCTR=1`. The centre of the pixel in FITS column *i* is at x = *i* − 0.5 |

## Radial fitting parameters

| Keyword | Default | Meaning |
|---|---|---|
| `R0=r` | required | semi-major axis of the innermost isophote (pixels) |
| `R1=r` | required | semi-major axis of the outermost isophote; 0 < R0 < R1 |
| `NR=n` | required | number of isophotes, 2–100, including R0 and R1 |
| `RLAW=k` | 2 | spacing: 2 = equal steps in r^¼, 1 = in log r, 0 = in r |
| `NITER=n` | 5 | iterations (at most 1000) |
| `RMSTAR` | off | reject samples brighter than median + 4 × (Q3 − median) along each ellipse |
| `FIXCTR=k` | 0 | 0 = each isophote fits its centre; 1 = fixed at X0, Y0; 2 = median of fitted centres |
| `ELLIP=e` | fitted | hold the ellipticity (1 − b/a) fixed |
| `LINEAR` | off | fit intensities instead of their logarithms |
| `TIE=k` | −1 | smooth the parameters with radius: k ≥ 0 polynomial of order k in r^¼; k < −1 running binomial average over \|k\| isophotes; −1 none |
| `AVG=n` | 0 | sample with a weighted (2n+1)² box instead of bilinear interpolation; samples with > 20% masked weight are skipped |
| `GAIN=g` | 1 | fraction of each correction applied per iteration |
| `SCALE=s` | | image scale (arcsec/pixel), recorded in the profile only |
| `GC` | off | globular-cluster mode: circular annuli around a centre ELLIPROF finds (then only `NR` is required) |
| `VERBOSE` | off | print the parameters after every iteration (and the full output) |

Details: [How ELLIPROF fits a galaxy](../concepts/how-it-works.md).

## Sky and mask

| Option | Meaning |
|---|---|
| `--sky VALUE` | subtract one constant sky level (image units) |
| `--sky-image FILE` | subtract a sky image pixel by pixel; same dimensions as the science image. Not together with `--sky` |
| `--mask FILE` | logical mask: 0 = bad; other finite values = good; NaN, Inf, BLANK = bad. FITS of any BITPIX, or legacy BITPIX=1 `.dmask`. Same dimensions |
| `--sc VALUE` | deprecated alias of `--sky` |
| `SKY=s` | ELLIPROF's own sky, used **only** in the de Vaucouleurs fit it prints; does not change the image or profile |

`--mask` and `--sky-image` accept `'file.fits[EXT]'`. The image is
prepared as (science − sky) × mask. Pixels that are exactly 0 are
ignored. Images are never resized, interpolated, cropped, shifted or
reprojected. Details: [Sky and masks](../concepts/sky-and-masks.md).

## Model and harmonics

| Option | Meaning |
|---|---|
| `MODEL -m FILE` | build the model image and write it (both are needed) |
| `--residual FILE` | write mask × (science − sky − model); implies `MODEL` |
| `--model-harmonics none\|3\|4\|3,4` | harmonic terms in the model (default 3,4) |
| `--harmonic-mode each\|median` | each isophote's own terms (default) or the median over isophotes |
| `--sixth-order` | fit and model the 6th-order term in place of the 3rd (**changes the fit**) |
| `COS3X=k` | original switch: 0 none, 1 median, 2 each (default); −1/−2 = 6th order |
| `COS4X=k` | original switch: 0 none, 1 median, 2 each (default) |

Use either `COS3X`/`COS4X` or the options above, not both. Only the
6th-order setting changes the fitted profile. Details:
[Boxy and disky isophotes](../concepts/harmonics.md).

## Output files

| Option | Output |
|---|---|
| `-o FILE` | profile in ELLIPROF's native `.prf` format (a table, **not an image**) |
| `--csv FILE` | the profile as a commented CSV table |
| `--reg FILE` | the fitted ellipses as a DS9 region file |
| `-m FILE` | the model image (with `MODEL`) |
| `--residual FILE` | the residual image |
| `--prepared FILE` | mask × (science − sky), the image as fitted |

The images are float32 FITS with the header (and WCS) of the selected
science HDU. Details: [The profile](../outputs/profile.md),
[Model, residual and prepared images](../outputs/images.md).

## Runtime options

| Option | Meaning |
|---|---|
| `--timeout SECONDS` | maximum run time (default 1800). On timeout the backend is stopped, temporary files removed, and elliprof exits with status 124 |
| `--verbose` | show ELLIPROF's full output: iteration tables, model progress, every message |
| `--diagnostics` | versions, Python, OS, architecture and backend details, for bug reports |
| `-v`, `--version` | version, original developer and maintainer |
| `-h`, `--help` | full help |

Not supported: the interactive options `OLD`, `EDIT` and `TV` of the
original program.

## Examples

```sh
# basic fit, profile + CSV + DS9 regions
elliprof galaxy.fits X0=500 Y0=500 R0=5 R1=200 NR=30 \
    -o galaxy.prf --csv galaxy.csv --reg galaxy.reg

# mask and sky image
elliprof galaxy.fits --mask galaxy_mask.fits --sky-image background.fits \
    X0=500 Y0=500 R0=5 R1=200 NR=30

# model with the 4th-order (boxy/disky) term only
elliprof galaxy.fits X0=500 Y0=500 R0=5 R1=200 NR=30 \
    MODEL -m galaxy_model.fits --model-harmonics 4

# image in an extension; model, prepared image and residual
elliprof 'galaxy.fits[SCI]' --mask galaxy_mask.fits --sky 1234.5 \
    X0=500 Y0=500 R0=5 R1=200 NR=30 MODEL -m galaxy_model.fits \
    --prepared galaxy_prepared.fits --residual galaxy_residual.fits
```

## Limits

- `NR` ≤ 100.
- Isophotes smaller than about 3 pixels have too few samples.
- `GC` mode assumes images at most 2048 pixels on a side.
- The model image is relative to the subtracted sky.
