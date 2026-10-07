# Command-line reference

This page documents **elliprof 0.1.4**. `elliprof -h` prints the same
information.

```text
elliprof IMAGE.fits X0=x Y0=y R0=r R1=r NR=n [KEYWORD=value ...] [options]
```

The common workflow, with the traditional ELLIPROF file names (`.dat` for
the text profile, `.prf` for the FITS model image):

```sh
elliprof n1234j.fits \
    RMSTAR \
    X0=514 Y0=514 \
    R0=10 R1=450 NR=25 NITER=5 \
    -o n1234.dat \
    -m n1234.prf
```

`-o FILE` writes the profile; `-m FILE` computes the model and writes
it. File names are free: elliprof never checks or adds extensions.

Keywords (`KEY=value`, case-insensitive) and options may follow the
image in any order. The output is a short summary (inputs, notes, files
written). The profile table is printed only if neither `-o` nor `--csv`
is given.

## Input image and initial centre

| Argument | Meaning |
|---|---|
| `IMAGE.fits` | 2-D FITS image (first argument), any BITPIX: 8, 16, 32, 64, −32, −64, read as 32-bit floats by the single backend and as 64-bit floats by the double one (`--precision`). Cubes are refused; one plane can be chosen with a CFITSIO section, `'cube.fits[SCI][*,*,2:2]'`. Select an extension with CFITSIO syntax, quoted: `'galaxy.fits[SCI]'`, `'galaxy.fits[1]'`. The selected HDU is fitted; there is no fallback to another |
| `X0=x Y0=y` | **required** initial centre, in pixels. ELLIPROF refines the centre of each isophote unless `FIXCTR=1`. The centre of the pixel in FITS column *i* is at x = *i* − 0.5 |

## Radial fitting parameters

| Keyword | Default | Meaning |
|---|---|---|
| `R0=r` | required | semi-major axis of the innermost isophote (pixels) |
| `R1=r` | required | semi-major axis of the outermost isophote; 0 < R0 < R1 |
| `NR=n` | required | number of isophotes, 2–100, including R0 and R1 |
| `RLAW=k` | 2 | spacing: 2 = equal steps in r^¼, 1 = in log r, 0 = in r |
| `NITER=n` | 5 | iterations of the fit (1–1000); `--niter n` is the same. See [Iterations](../concepts/how-it-works.md#5-iterations-niter) |
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
| `--mask FILE` | logical mask, by default: 0 = bad; other finite values = good; NaN, Inf, BLANK = bad. FITS of any BITPIX, or legacy BITPIX=1 `.dmask`. Same dimensions |
| `--nonfinite auto\|mask\|keep\|error` | science pixels that are NaN or ±Inf after the sky and the mask (no-data regions): `mask` excludes them like masked pixels; `keep` passes them to ELLIPROF, as 0.1.4 did, with a warning; `error` refuses the image. `auto` (default): `keep` with an explicit `--precision single`, `mask` otherwise |
| `--mask-convention nonzero-good\|zero-good` | how the mask values are read. `nonzero-good` (default): the rule above. `zero-good`: 0 = good; any nonzero value, NaN, Inf, BLANK = bad. Refused for a legacy `.dmask` (1 always means good) |
| `--sc VALUE` | deprecated alias of `--sky` |
| `SKY=s` | ELLIPROF's own sky, used **only** in the de Vaucouleurs fit it prints; does not change the image or profile |

`--mask` and `--sky-image` accept `'file.fits[EXT]'`. The image is
prepared as (science − sky) × mask. Pixels that are exactly 0 are
ignored. Images are never resized, interpolated, cropped, shifted or
reprojected. Details: [Sky and masks](../concepts/sky-and-masks.md).

## Model and harmonics

| Option | Meaning |
|---|---|
| `-m FILE` | compute the model image and write it as FITS (nothing else is needed) |
| `--residual FILE` | write mask × (science − sky − model); computes the same model, with or without `-m` |
| `MODEL` | no longer needed; accepted and ignored, with a note. `MODEL=value` is an error |
| `--model-harmonics none\|3\|4\|3,4` | measured terms put into the model (default 3,4); with `--sixth-order`: `none\|6\|4\|4,6`. Never changes the profile |
| `--harmonic-mode each\|median` | each isophote's own terms (default) or the median over isophotes |
| `--sixth-order` | measure the 6th-order term **instead of** the 3rd; `I3`/`A3` then hold the 6th-order amplitude and **twice** its phase |
| `COS3X=k` | original switch (see below) |
| `COS4X=k` | original switch (see below) |

Both interfaces are fully supported and run the same code; use one or
the other in a command, not both.

| Legacy | Measured | In the model | Modern equivalent of this value |
|---|---|---|---|
| `COS3X=2` | 3rd order | each isophote's term | 3 in `--model-harmonics` (default) |
| `COS3X=1` | 3rd order | median term | 3 in `--model-harmonics`, `--harmonic-mode median` |
| `COS3X=0` | 3rd order | none | 3 not in `--model-harmonics` |
| `COS3X=-2` | 6th order | each isophote's term ⚠ | `--sixth-order`, 6 in `--model-harmonics` (default) |
| `COS3X=-1` | 6th order | median term ⚠ | `--sixth-order`, 6 in `--model-harmonics`, `--harmonic-mode median` |
| `COS3X=-3` | 6th order | none | `--sixth-order`, 6 not in `--model-harmonics` |
| `COS4X=2` | 4th order | each isophote's term | 4 in `--model-harmonics` (default) |
| `COS4X=1` | 4th order | median term | 4 in `--model-harmonics`, `--harmonic-mode median` |
| `COS4X=0` | 4th order | none | 4 not in `--model-harmonics` |

The modern options set `COS3X` and `COS4X` together; a few legacy pairs
that mix "each" and "median" (such as `COS3X=2 COS4X=1`) have no modern
spelling. The full list of pairs:
[Exact equivalences](../concepts/harmonics.md#exact-equivalences).

⚠ A 6th-order term in the model is subject to a known limitation of
the original model synthesis when the fitted position angle wraps across
0°/180° (elliprof warns). The model settings never change the measured
profile; choosing the 6th order instead of the 3rd can change the fit
slightly where ellipses are poorly sampled. Details:
[Harmonic analysis](../concepts/harmonics.md#the-harmonic-modes).

## Output files

| Option | Output |
|---|---|
| `-o FILE` | the profile in ELLIPROF's native text format (a table, **not an image**); traditionally `n1234.dat` |
| `--csv FILE` | the profile as a commented CSV table |
| `--reg FILE` | the fitted ellipses as a DS9 region file |
| `-m FILE` | the model image (FITS); traditionally `n1234.prf` |
| `--residual FILE` | the residual image |
| `--prepared FILE` | mask × (science − sky), the image as fitted |

The images are floating-point FITS, 32-bit from the single backend and
64-bit from the double one, with the header (and WCS) of the selected
science HDU. Details: [The profile](../outputs/profile.md),
[Model, residual and prepared images](../outputs/images.md).

## Runtime options

| Option | Meaning |
|---|---|
| `--precision auto\|single\|double` | the backend: `single`, the original ELLIPROF in 32-bit floating point; `double`, its IEEE-754 double-precision port; `auto` (default) uses double only for data single cannot hold. See [Precision](../concepts/precision.md) |
| `--timeout SECONDS` | maximum run time (default 1800). On timeout the backend is stopped, temporary files removed, and elliprof exits with status 124 |
| `--verbose` | show ELLIPROF's full output: iteration tables, model progress, every message |
| `--diagnostics` | versions, Python, OS, architecture and backend details, for bug reports |
| `-v`, `--version` | version, original developer and maintainer |
| `-h`, `--help` | full help |
| `--check-update` | ask PyPI whether a newer elliprof exists (installs nothing) |
| `-u`, `--update` | install the newest elliprof with this Python's pip ([Updating](../install.md#updating)) |

Not supported: the interactive options `OLD`, `EDIT` and `TV` of the
original program.

Changed in 0.1.4: `-m FILE` alone computes and writes the model (before,
`MODEL` was also required and `-m` alone was ignored).

## Examples

```sh
# profile (text) and model (FITS), traditional names
elliprof n1234j.fits RMSTAR X0=514 Y0=514 R0=10 R1=450 NR=25 NITER=5 \
    -o n1234.dat -m n1234.prf

# profile + CSV + DS9 regions
elliprof galaxy.fits X0=500 Y0=500 R0=5 R1=200 NR=30 \
    -o galaxy.dat --csv galaxy.csv --reg galaxy.reg

# mask and sky image
elliprof galaxy.fits --mask galaxy_mask.fits --sky-image background.fits \
    X0=500 Y0=500 R0=5 R1=200 NR=30

# a mask with 0 = good and nonzero = bad (e.g. a segmentation map)
elliprof galaxy.fits --mask segmap.fits --mask-convention zero-good \
    X0=500 Y0=500 R0=5 R1=200 NR=30

# model with the 4th-order (boxy/disky) term only; 10 iterations
elliprof galaxy.fits X0=500 Y0=500 R0=5 R1=200 NR=30 --niter 10 \
    -m galaxy.prf --model-harmonics 4

# image in an extension; model, prepared image and residual
elliprof 'galaxy.fits[SCI]' --mask galaxy_mask.fits --sky 1234.5 \
    X0=500 Y0=500 R0=5 R1=200 NR=30 -o galaxy.dat -m galaxy.prf \
    --prepared galaxy_prepared.fits --residual galaxy_residual.fits
```

## Limits

- `NR` ≤ 100.
- Isophotes smaller than about 3 pixels have too few samples.
- `GC` mode assumes images at most 2048 pixels on a side.
- The model image is relative to the subtracted sky.
