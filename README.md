# elliprof

**Elliptical-isophote surface photometry of galaxies.** elliprof fits a set of concentric ellipses to a galaxy image. For each isophote it measures:
- the centre, position angle and ellipticity;
- the mean surface brightness;
- the 3θ and 4θ harmonic (boxy/disky) terms;
- the logarithmic slope.

It can also build a smooth model image of the galaxy.

The fitting code is ELLIPROF from John Tonry's MONSTA package (a descendant of Lick VISTA), compiled unchanged from the original Fortran. elliprof adds FITS input and output, masks, sky subtraction, flexible centre selection, CSV and DS9 output, and a Python API.

> **Status:** technically complete, but **not yet published**. Redistribution rights for the legacy source code are still being resolved; see [LICENSING_STATUS.md](LICENSING_STATUS.md). Until then, install from source or from locally built wheels.

## Installation

Once released:

```sh
pip install elliprof
```

Binary wheels will contain everything needed, including the compiled backend, CFITSIO and the Fortran runtime. **No compiler, gfortran or CFITSIO is needed.**

**From source**, you need gfortran and CFITSIO:

```sh
brew install gcc cfitsio                          # macOS
sudo apt install gfortran libcfitsio-dev          # Debian / Ubuntu
pip install .                                     # or: pip install -e .
```

## Quick start

```sh
elliprof galaxy.fits \
    --mask galaxy.dmask \
    --sky 1234.5 \
    X0=500 Y0=500 \
    R0=5 R1=200 NR=40 \
    --csv galaxy.csv --reg galaxy.reg -o galaxy.prf
```

```python
from elliprof import run_elliprof

result = run_elliprof("galaxy.fits", mask="galaxy.dmask", sky=1234.5,
                      center=(500, 500), r0=5, r1=200, nr=40)
result.profile          # pandas DataFrame, one row per isophote
result.csv_path, result.reg_path, result.prf_path
```

`python -m elliprof` is the same as the `elliprof` command. A worked example on a real HST image is in [examples/u12517](examples/u12517/README.md) and [notebooks/elliprof_example.ipynb](notebooks/elliprof_example.ipynb).

## What happens to the image

1. **Read** the FITS image. It is converted to 32-bit floats, with BSCALE/BZERO applied.
2. **Subtract the sky**: either a constant with `--sky V` (Python: `sky=`), or an image of the same size with `--sky-image F` (`sky_image=`). You can't give both.
3. **Apply the mask** with `--mask F` (`mask=`). The image is multiplied by the mask: **0 = masked, 1 = good**. Masked pixels become exactly 0, and ELLIPROF ignores pixels that are exactly 0. That's why the sky has to be subtracted *first*.
4. **Fit** with ELLIPROF.

Masks can be ordinary FITS images or MONSTA/SBF `.dmask` bitmaps (`BITPIX = 1`, which other FITS readers can't open); elliprof decodes these exactly as MONSTA does. A mask or sky image must have the same size and origin as the science image, otherwise elliprof stops with an error.

`--sky` is **not** ELLIPROF's own `SKY=` keyword. `SKY=` (Python: `elliprof_sky=`) only sets the sky used in ELLIPROF's final de Vaucouleurs fit and doesn't change the image. `--sc` is a deprecated alias for `--sky`.

## Choosing the centre

Give at most one of these:

| Command line | Python | Coordinates |
|---|---|---|
| `X0=x Y0=y` | `center=(x, y)` | ELLIPROF image coordinates (below) |
| `--center-physical X Y` | `center_physical=(x, y)` | IRAF/DS9 physical coordinates (`LTV`/`LTM` keywords) |
| `--center-radec RA DEC` | `center_radec=(ra, dec)` | celestial, via the image's FITS WCS (astropy). Decimal degrees (`188.73658 -12.58242`) or sexagesimal (`12:34:56.78 -12:34:56.7`), read in the WCS's own frame. A `SkyCoord` is also accepted. |
| (none) | (none) | the geometric image centre |

The chosen centre is always reported, for example `Center source: RA/DEC` / `Converted center: X0=567.1321 Y0=562.1094`. The centre is only the starting point: ELLIPROF fits the centre of every isophote (unless `FIXCTR=1`). A RA/DEC centre on an image without a WCS is an error, never a silent fallback.

**ELLIPROF image coordinates** put the centre of the pixel in FITS column *i* at x = *i* − 0.5, so the image spans 0 ≤ x ≤ NCOL. That's half a pixel less than FITS/DS9 image coordinates. The geometric centre is (NCOL/2, NROW/2).

## Fit parameters

The ELLIPROF keywords, as `KEY=value` on the command line or as keyword arguments in Python:

| Keyword | Python | Meaning |
|---|---|---|
| `R0=` `R1=` `NR=` | `r0` `r1` `nr` | inner and outer semi-major axis (pixels) and number of isophotes (required) |
| `NITER=` | `niter` | iterations (default 5) |
| `RLAW=` | `rlaw` | radius spacing: 0 linear, 1 logarithmic, 2 r^¼ (default) |
| `LINEAR` | `linear` | fit intensities instead of log intensities |
| `FIXCTR=` | `fixctr` | 0 free centres, 1 fixed, 2 median centre |
| `ELLIP=` | `ellip` | force this ellipticity |
| `RMSTAR` | `rmstar` | reject star-like outliers along each isophote |
| `COS3X=` `COS4X=` | `cos3x` `cos4x` | 3θ/4θ terms in the model (0 none, 1 median, 2 each isophote; `COS3X<0` uses 6θ) |
| `TIE=` | `tie` | smooth the parameters with radius (polynomial order, or −n: n-point smoothing) |
| `AVG=` | `avg` | average a (2n+1)² box when sampling |
| `GAIN=` | `gain` | iteration gain (default 1) |
| `SCALE=` | `scale` | arcsec/pixel, recorded in the profile |
| `SKY=` | `elliprof_sky` | sky for the de Vaucouleurs fit only (see above) |
| `MODEL` | `model` | make a model image (`-m model.fits`) |
| `GC` | `gc` | globular-cluster mode: circular annuli |
| `VERBOSE` | `verbose` | print every iteration |

## Output

| Option | File |
|---|---|
| `-o out.prf` | the profile in MONSTA's `SAVE ELLIPROF` format, with exact values (`elliprof.read_profile`) |
| `--csv out.csv` | the same as comma-separated, fixed-width columns with `#` header lines (`elliprof.parse_elliprof_csv`) |
| `--reg out.reg` | one DS9 ellipse per isophote, in DS9 `image` coordinates, no labels |
| `-m model.fits` | the model image, with `MODEL` |

Profile columns:

| Column | Meaning |
|---|---|
| `Rmaj` | semi-major axis (pixels) |
| `x0`, `y0` | isophote centre (ELLIPROF coordinates, plus the image origin CNPIX if any) |
| `I0` | mean intensity on the isophote (image units, above the subtracted sky) |
| `alpha` | position angle; the major axis lies at `alpha + 90`° counter-clockwise from +x |
| `ellip` | ellipticity 1 − b/a |
| `I3`, `A3` / `I4`, `A4` | 3θ / 4θ amplitude (relative to I0) and phase (degrees) |
| `slope` | d log I / d log r |

**DS9:** `ds9 galaxy.fits -regions galaxy.reg`, or *Region → Open…*. Each ellipse is `ellipse(x0 + 0.5, y0 + 0.5, Rmaj, Rmaj·(1−ellip), alpha − 90)`. The angle `alpha − 90` and the major-axis angle `alpha + 90` differ by 180°, which draws the same ellipse.

`elliprof --version` and `elliprof --diagnostics` report versions, platform and the backend in use, which is useful for bug reports.

## Platforms

| Platform | Status |
|---|---|
| Linux x86_64 (manylinux_2_28) | wheel built and tested in clean containers, Python 3.12; tests on real CI runners pending |
| Linux aarch64 (manylinux_2_28) | wheel built and tested in clean containers, Python 3.10 and 3.13 |
| macOS arm64 | wheel built and tested locally (tagged macOS 26 by the local toolchain; CI wheels will target macOS 15) |
| macOS x86_64 | **not yet built** (CI workflow ready) |
| Windows x86_64 | **not yet built** (CI workflow ready, MSYS2 gfortran; unverified) |
| Windows ARM64 | not supported (no gfortran for Windows on ARM) |

## Testing

```sh
make check            # build, source checksums, unit + integration + regression tests
make docker-test      # the same inside an Ubuntu container
make notebook-check   # run the example notebook
```

The test plan is in [tests/TEST_PLAN.md](tests/TEST_PLAN.md).

---

## Reference: how it is built

* **The reference code is never changed.** `src/original/` (9 Fortran files) and `include/` (4 files) are byte-identical copies from MONSTA, checked against SHA-256 hashes in `tests/original_source_hashes.txt` on every test run.
* **`src/shim/` stands in for the MONSTA environment** that normally surrounds ELLIPROF:
  - reading the image (`RD`);
  - sky and mask arithmetic, exactly as MONSTA's `SC`, `SI` and `MI`;
  - splitting the command line into keywords with MONSTA's own parser;
  - output as `PRINT EPROF` / `SAVE ELLIPROF` would produce it.
  - The display and terminal routines ELLIPROF calls are stubbed out.
* **`python/elliprof/`** handles centre selection, validation, running the backend in a subprocess, and reading the results. The compiled backend (`elliprof_native`) is an implementation detail. It can be run directly, but it needs explicit `X0=`/`Y0=`.
* **Build:** `make` for development, CMake via scikit-build-core for wheels, cibuildwheel for release builds. Both builds use exactly the same compiler flags, checked by a test: `-O -g -fno-automatic -ffp-contract=off`, with no preprocessing and no bounds checking. Different builds on one machine produce byte-identical results.
* **Across platforms**, Linux x86_64 and aarch64 give bit-identical results. macOS differs from Linux only at the level of rounding in the maths library (see `tests/regression/spread/`).

## Known limitations

* **`OLD` and `EDIT`** continue a previous profile held in memory, which elliprof can't load yet. They are refused.
* **`TV`** (interactive display and cursor) isn't available.
* **Legacy behaviour is kept as it is**, for equivalence with MONSTA:
  - `NR` must be ≤ 100 (the internal fit arrays hold 100 radii);
  - isophotes smaller than about 3 pixels have too few samples and give `NaN`;
  - `GC` mode assumes images at most 2048 pixels on a side;
  - `RMSTAR` does not remove the neighbours of a rejected star.
* **Model image:** it has a minimal FITS header and is sky-subtracted.
* **Windows paths:** non-ASCII paths may not work on Windows.
