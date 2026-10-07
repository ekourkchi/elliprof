# Example: UGC 12517

A real HST image of the galaxy UGC 12517, fitted with elliprof using a pixel mask and a constant sky.

```sh
sh examples/u12517/run_example.sh            # outputs next to the data
sh examples/u12517/run_example.sh /tmp/out   # or into another directory
```

The script works from any directory. It uses the installed `elliprof` command if there is one, and otherwise the source checkout (after `make`).

## Files

| File | What it is |
|---|---|
| `u12517j.fits` | The science image: HST WFC3/IR F110W, 1025 × 1022 pixels, 0.128″/pixel. |
| `u12517j.dmask` | The pixel mask, 1025 × 1022, as a legacy `BITPIX = 1` bitmap. **0 = masked, 1 = good.** 103,402 pixels (9.87%) are masked: the nucleus (about 10 px in radius), foreground stars and background galaxies, and the image edges. |
| `centers.dat`, `calibrate.dat` | Supporting data from the original analysis: a centre estimate and photometric calibration. elliprof does not read them; the centre below is given explicitly. |

## The command

```sh
elliprof u12517j.fits \
    --mask u12517j.dmask \
    --sky 3246.0 \
    X0=567 Y0=562 \
    R0=9 R1=347 NR=23 NITER=10 RMSTAR \
    -o u12517.dat \
    -m u12517.prf \
    --residual u12517_residual.fits \
    --csv u12517.csv \
    --reg u12517.reg
```

| Option | Meaning |
|---|---|
| `--sky 3246.0` | Subtract a constant sky level from every pixel. |
| `--mask u12517j.dmask` | Then multiply by the mask, so masked pixels become exactly 0. ELLIPROF ignores pixels that are exactly 0, which is why the sky must be subtracted first. |
| `X0=567 Y0=562` | Initial centre, in ELLIPROF image coordinates. ELLIPROF refines the centre of every isophote. |
| `R0=9 R1=347 NR=23` | 23 isophotes with semi-major axes from 9 to 347 pixels, spaced evenly in r^¼ by default. |
| `NITER=10 RMSTAR` | 10 iterations (the default is 5); reject star-like outliers along each isophote. |
| `-o u12517.dat` | The profile, a text table (traditional name `.dat`). |
| `-m u12517.prf` | Compute the galaxy model and write it as a FITS image (traditional name `.prf`). No `MODEL` keyword is needed. |
| `--residual u12517_residual.fits` | mask × (science − sky − model), FITS. |

## Output

| File | Contents |
|---|---|
| `u12517.dat` | The profile, full precision (a table of numbers, not an image). |
| `u12517.prf` | The model image (FITS, 32-bit float, with the science header and WCS). |
| `u12517_residual.fits` | The residual image: science − sky − model on good pixels, 0 on masked ones. |
| `u12517.csv` | The same profile as commented, fixed-width CSV: `Rmaj, x0, y0, I0, alpha, ellip, I3, A3, I4, A4, slope`. |
| `u12517.reg` | One DS9 ellipse per isophote. |

The innermost isophote (r = 9) lies almost entirely inside the masked nucleus. ELLIPROF prints `FITCONTOUR: quitting, nused = 0` and keeps its starting values for that isophote. This is expected.

## Viewing the ellipses in DS9

```sh
ds9 u12517j.fits -regions u12517.reg
```

Or open the image in DS9 and use **Region → Open…**. The regions are in DS9 `image` coordinates, so they line up with the pixels.
