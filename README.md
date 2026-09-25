# elliprof

ELLIPROF fits elliptical isophotes to astronomical FITS images.

For each isophote it measures the centre, position angle, ellipticity, mean intensity, the 3θ and 4θ (boxy/disky) harmonic terms, and the logarithmic slope. It can also write a smooth model image of the galaxy. The numerical code is the original ELLIPROF Fortran, compiled unchanged; `elliprof` makes it easy to install and run, from the command line or from Python.

## Installation

```sh
pip install elliprof
```

Binary wheels include the compiled program and everything it needs. No compiler, gfortran or CFITSIO is required. (See **Platforms** for which wheels have been tested.)

## Usage

```sh
elliprof galaxy.fits \
    X0=500 Y0=500 \
    R0=5 R1=200 NR=30 \
    --csv profile.csv \
    --reg profile.reg
```

Scalar sky:

```sh
elliprof galaxy.fits \
    --sky 1234.5 \
    X0=500 Y0=500 \
    R0=5 R1=200 NR=30
```

2-D sky:

```sh
elliprof galaxy.fits \
    --sky-image background.fits \
    X0=500 Y0=500 \
    R0=5 R1=200 NR=30
```

Mask + 2-D sky:

```sh
elliprof galaxy.fits \
    --mask mask.fits \
    --sky-image background.fits \
    X0=500 Y0=500 \
    R0=5 R1=200 NR=30
```

Python:

```python
from elliprof import run_elliprof

result = run_elliprof(
    image="galaxy.fits",
    x0=500,
    y0=500,
    r0=5,
    r1=200,
    nr=30,
)

print(result.profile)
```

`python -m elliprof` is the same as the `elliprof` command. A worked example on a real HST image is in [examples/u12517](examples/u12517/README.md) and [notebooks/elliprof_example.ipynb](notebooks/elliprof_example.ipynb).

## Inputs

| Input | Command line | Python | Notes |
|---|---|---|---|
| science image | first argument | `image=` | 2-D FITS image |
| initial centre | `X0=x Y0=y` | `x0=`, `y0=` | **required**; ELLIPROF refines it for every isophote |
| radii | `R0=r R1=r NR=n` | `r0=`, `r1=`, `nr=` | **required**; 0 < R0 < R1, 2 ≤ NR ≤ 100 |
| scalar sky | `--sky V` | `sky=` | subtracted from every pixel |
| 2-D sky | `--sky-image F` | `sky_image=` | subtracted pixel by pixel; same size as the image |
| mask | `--mask F` | `mask=` | 0 = ignored, 1 = good; same size as the image |

The image is prepared as `(science − sky) × mask`, and ELLIPROF ignores pixels that are exactly 0.
- `--sky` and `--sky-image` can't be used together.
- A mask or sky image with different dimensions from the science image is an error. Nothing is ever resized, cropped or resampled.
- Masks can be ordinary FITS images or legacy `.dmask` bitmaps (`BITPIX = 1`).

**Coordinates:** `X0`, `Y0` are in ELLIPROF image coordinates, where the centre of the pixel in FITS column *i* is at x = *i* − 0.5. That is half a pixel less than DS9 or FITS pixel numbering.

### Other ELLIPROF parameters

| Keyword | Python | Meaning |
|---|---|---|
| `NITER=` | `niter` | iterations (default 5, at most 1000) |
| `RLAW=` | `rlaw` | radius spacing: 0 linear, 1 logarithmic, 2 r^¼ (default) |
| `LINEAR` | `linear` | fit intensities instead of log intensities |
| `FIXCTR=` | `fixctr` | 0 free centres, 1 fixed, 2 median centre |
| `ELLIP=` | `ellip` | force this ellipticity |
| `RMSTAR` | `rmstar` | reject star-like outliers along each isophote |
| `COS3X=` `COS4X=` | `cos3x` `cos4x` | 3θ/4θ terms in the model (0 none, 1 median, 2 each isophote; `COS3X<0` uses 6θ) |
| `TIE=` | `tie` | smooth the parameters with radius |
| `AVG=` | `avg` | average a (2n+1)² box when sampling |
| `GAIN=` | `gain` | iteration gain (default 1) |
| `SCALE=` | `scale` | arcsec/pixel, recorded in the profile |
| `SKY=` | `elliprof_sky` | sky used only in ELLIPROF's de Vaucouleurs fit (it does not change the image; use `--sky` for that) |
| `MODEL` | `model` | make a model image (`-m model.fits`) |
| `GC` | `gc` | globular-cluster mode: circular annuli |
| `VERBOSE` | `verbose` | print every iteration |

`OLD`, `EDIT` and `TV` (interactive options) are not supported.

## Output

| Option | Python result | Contents |
|---|---|---|
| `-o out.prf` | `result.prf_path` | profile, full precision (`elliprof.read_profile`) |
| `--csv out.csv` | `result.csv_path` | fixed-width, comma-separated profile with `#` provenance lines |
| `--reg out.reg` | `result.reg_path` | one DS9 ellipse per isophote, no labels |
| `-m model.fits` | `result.model_path` | model image (with `MODEL`) |

`result.profile` is a pandas DataFrame with one row per isophote:

| Column | Meaning |
|---|---|
| `Rmaj` | semi-major axis (pixels) |
| `x0`, `y0` | isophote centre |
| `I0` | mean intensity above the subtracted sky |
| `alpha` | position angle; the major axis lies at `alpha + 90`° counter-clockwise from +x |
| `ellip` | ellipticity 1 − b/a |
| `I3`, `A3`, `I4`, `A4` | 3θ/4θ amplitude (relative to I0) and phase (degrees) |
| `slope` | d log I / d log r |

To view the fit in DS9: `ds9 galaxy.fits -regions profile.reg`.

**Safety:**
- Invalid input fails immediately with a clear message, before anything runs.
- The program never waits for keyboard input.
- A run that takes longer than 30 minutes is stopped. Change the limit with `--timeout SECONDS` or `run_elliprof(..., timeout=...)`.

`elliprof --version` and `elliprof --diagnostics` print version and platform information for bug reports.

## Platforms

| Platform | Status |
|---|---|
| Linux x86_64, aarch64 (manylinux_2_28) | Supported |
| Linux ppc64le, s390x (manylinux_2_28) | Supported (wheels tested under QEMU emulation) |
| Linux x86_64, aarch64 (musllinux_1_2, e.g. Alpine) | Supported |
| macOS 11+ arm64, x86_64 | Supported |
| Windows x86_64 | Supported |
| Linux riscv64 (manylinux_2_39) | Experimental: the wheel builds, but its tests have not completed |
| Windows ARM64 | Experimental: no wheel (no GNU Fortran toolchain yet) |

Supported means the wheel was installed and passed the installed-wheel and regression tests in a clean environment without a compiler or CFITSIO. On ppc64le and s390x, PyPI has no numpy or pandas wheels, so install those from your Linux distribution or conda. 32-bit systems and macOS older than 11 are not supported.

## Development

```sh
brew install gcc cfitsio                  # or: apt install gfortran libcfitsio-dev
pip install -e ".[test]"
make check                                # build and run all tests
```

The original numerical sources in `src/original/` and `include/` are never modified, and their SHA-256 hashes are checked on every test run. The test plan is in [tests/TEST_PLAN.md](tests/TEST_PLAN.md).

**Known limitations:**
- NR ≤ 100.
- Isophotes smaller than about 3 pixels have too few samples.
- `GC` mode assumes images at most 2048 pixels on a side.
- The model image is written relative to the subtracted sky.

---

Historical note: ELLIPROF was originally developed by John Tonry as part of MONSTA.

Maintained by Ehsan Kourkchi (Edwin Kay)
Email: [ekourkchi@gmail.com](mailto:ekourkchi@gmail.com)

License: MIT for the elliprof package code (see [LICENSE](LICENSE)). The original ELLIPROF sources and bundled libraries keep their own terms (see [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)).

**Disclaimer.** This software is provided as-is, without warranty of any kind. The maintainer is not responsible for software errors, incorrect scientific results, data loss, or decisions made using results produced by this software. Users are responsible for independently validating results for their scientific application.
