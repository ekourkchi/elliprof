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
| `u12517j.fits` | The science image: HST WFC3/IR (the `j` is F110W), 1025 × 1022 pixels, BITPIX −32, 0.128″/pixel. It has a celestial WCS (`RA---TAN`/`DEC--TAN`, FK5 J2000) and no CNPIX. |
| `u12517j.dmask` | The pixel mask, 1025 × 1022, in MONSTA's bitmap format (`BITPIX = 1`, which standard FITS readers reject). **0 = masked, 1 = good.** 103,402 pixels (9.87%) are masked: the nucleus (about 10 px in radius around (567, 562)), foreground stars and background galaxies, and the image edges. |
| `centers.dat` | `u12517  567  562  35.081`: galaxy name, centre x and y in MONSTA/ELLIPROF image coordinates, and the photometric zero point m1star. It is kept as part of the historical dataset. **elliprof does not read it**; its x, y are simply the `X0=567 Y0=562` passed below. |
| `calibrate.dat` | Photometric calibration for the later SBF analysis (gain, pixel scale, extinction, zero point, exposure time, sky brightness). ELLIPROF itself uses none of it. |

## The command

```sh
elliprof u12517j.fits \
    --mask u12517j.dmask \
    --sky 3246.0 \
    X0=567 Y0=562 \
    R0=9 R1=347 NR=23 NITER=10 RMSTAR \
    -o u12517j.prf --csv u12517j.csv --reg u12517j.reg
```

| Option | Meaning |
|---|---|
| `--sky 3246.0` | Subtract a constant sky level from every pixel first. 3246.0 is the value the SBF pipeline used for this galaxy (0.900 × the initial sky median). This is not ELLIPROF's own `SKY=` keyword, which only affects its de Vaucouleurs fit. |
| `--mask u12517j.dmask` | Then multiply by the mask, so masked pixels become exactly 0. |
| `X0=567 Y0=562` | Starting centre, in ELLIPROF image coordinates. ELLIPROF then fits the centre of every isophote. |
| `R0=9 R1=347 NR=23` | 23 isophotes with semi-major axes from 9 to 347 pixels, spaced by default evenly in r^¼. |
| `NITER=10 RMSTAR` | 10 iterations; reject star-like outliers along each isophote. |

**Why the sky comes before the mask.** ELLIPROF has no mask input of its own. It skips pixels whose value is exactly 0. Masking after sky subtraction leaves the masked pixels at 0. Masking first would leave them at −sky, and they would be fitted as real data. This is the order of the MONSTA scripts in the original SBF pipeline (`sc 1 sky`, then `rd 2 mask`, `mi 1 2`).

**Centre.** The centre is given explicitly here. Without `X0`/`Y0`, elliprof uses the geometric image centre, (512.5, 511.0) for this image. The Python command also accepts `--center-radec` or `--center-physical`.

## Output

| File | Contents |
|---|---|
| `u12517j.prf` | MONSTA-compatible profile (`SAVE ELLIPROF=file ASCII` format), with exact values. |
| `u12517j.csv` | The same profile as commented, fixed-width CSV: `Rmaj, x0, y0, I0, alpha, ellip, I3, A3, I4, A4, slope`. |
| `u12517j.reg` | One DS9 ellipse per isophote. |

The innermost isophote (r = 9) lies almost entirely inside the masked nucleus. ELLIPROF prints `FITCONTOUR: quitting, nused = 0` and keeps its starting values for that isophote. This is expected.

## Viewing the ellipses in DS9

```sh
ds9 u12517j.fits -regions u12517j.reg
```

Or open the image in DS9 and use **Region → Open…** to load `u12517j.reg`. The regions are in DS9 `image` coordinates, so they line up with the pixels. A square-root or log scale helps.

## Relation to the historical pipeline

This example isn't a pixel-for-pixel reproduction of the SBF pipeline run on this galaxy. That run:
- multiplied in extra masks (a common edge mask and source-extraction masks), not just this `.dmask`;
- **filled the masked pixels with a previous model** instead of leaving them at 0;
- started from a SExtractor centre (567.63, 562.61) with R1 = 347 and NR = 23.

Even so, from r ≈ 15 to ≈ 100 pixels this example matches the profile MONSTA itself printed in that run to within a few units in the last printed digit. For example, at r = 15.0 MONSTA gave x0 = 567.09, y0 = 562.52, I0 = 338458, alpha = 176.62, ellip = 0.211, and this example gives 567.09, 562.52, 338468, 176.62, 0.211. That is supporting evidence, not a proof of equivalence.
