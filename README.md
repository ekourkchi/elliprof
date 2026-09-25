# Standalone ELLIPROF

ELLIPROF is MONSTA/VISTA's elliptical-isophote surface photometry command. This directory builds it as a single program with gfortran and CFITSIO. It doesn't need the rest of MONSTA, X11, Mongo or readline.

**Status:** this version builds and runs, but it hasn't yet been checked against output from the original MONSTA. See "Not yet done" below.

## Build

Requirements are gfortran and CFITSIO. On macOS: `brew install gcc cfitsio`.

```sh
make                  # builds ./elliprof
make test             # also writes test_image.fits and runs ELLIPROF on it
```

If CFITSIO isn't installed through Homebrew, point the build at it with `make CFITSIO=/path/to/prefix`. Use `make WARN=-Wall` to see compiler warnings. The original sources produce many warnings; that's expected.

## Run

```sh
./elliprof image.fits X0=127.3 Y0=121.6 R0=3 R1=90 NR=30 [SKY=100] [options] \
           [-o out.prf] [-m model.fits] [--csv out.csv] [--reg out.reg]
```

- **Keywords:** these are the MONSTA ELLIPROF keywords, in the same syntax as `ELLIPROF buf ...` inside MONSTA. The program joins them into a command line and splits it with the original `UPPER`/`DISSECT` routines, exactly as `vista.f` does. That means:
  - Case doesn't matter.
  - `KEY=value` values can be expressions.
  - At most 16 keywords are accepted.
  - A bare integer (MONSTA's buffer number) is accepted and ignored.
- **Keyword list:** `X0= Y0= R0= R1= NR= RLAW= LINEAR FIXCTR= ELLIP= NITER= SCALE= SKY= MODEL RMSTAR COS3X= COS4X= TIE= AVG= GAIN= GC VERBOSE TEST DUMP= EDIT`. The full descriptions are in the `Chelp` lines at the top of `src/original/elliprof.f`.
- **`-o out.prf`:** writes the profile in the same format as MONSTA's `SAVE ELLIPROF=out ASCII`, using list-directed `N_PRF, PRF_SC, PARAM_PRF(12,250), PRF_HEAD`. This file keeps full precision, so use it for numerical comparisons.
- **`-m model.fits`:** with `MODEL` (or `GC MODEL`), writes the model image that ELLIPROF leaves in the image buffer.
- **`--csv out.csv`:** writes the profile as comma-separated values in fixed-width columns, after a few `#` comment lines. There is one row per contour: `Rmaj, x0, y0, I0, alpha, ellip, I3, A3, I4, A4, slope`.
  - The values are the same as in the `.prf`, in MONSTA's coordinate convention.
  - I0, I3 and I4 are written as `ES15.7`, which keeps full REAL\*4 precision.
  - The other columns use 4 or 6 decimals (at most 5e-5 pixels or degrees of rounding). For exact values, use the `.prf`.
- **`--reg out.reg`:** writes one DS9 `ellipse(x,y,a,b,angle)` per contour, in `image` coordinates with no labels.
  - Centre: `x0 − CNPIX1 + 0.5`, `y0 − CNPIX2 + 0.5`, converting MONSTA's pixel convention (see Coordinates) to DS9's.
  - Axes: `a = Rmaj`, `b = Rmaj·(1 − ellip)`.
  - Angle: `alpha − 90`. The major axis lies at `alpha + 90`; the two differ by 180°, which is the same ellipse.
  - Contours with NaN are written as `#` comment lines instead of ellipses, and a warning goes to stderr.
- **Where the files come from:** `--csv` and `--reg` are both generated from the final `/PRF/` after ELLIPROF returns. Leaving them out changes nothing else: stdout and the `.prf` are byte-identical either way.
- **Image input:** `image.fits` is read as REAL\*4 through CFITSIO, with BSCALE/BZERO applied and no NULL substitution. For an extension, use CFITSIO's `file.fits[1]` syntax.

### Coordinates

These follow VISTA's conventions:
- The centre of pixel `DATA(ix,iy)` is at `(x,y) = (ix-0.5, iy-0.5)`.
- The image origin is `CNPIX1`/`CNPIX2` from the header, or 0 if those keywords are missing. MONSTA's default CNPIX mode does the same. Output `x0`/`y0` include that origin.
- In the printed table, `alpha` is MONSTA's stored position angle, which is ELLIPROF's internal angle (CCW from +x) minus 90°. So an ellipse whose major axis is at 30° from +x prints as 120.

### Output

stdout contains:
1. ELLIPROF's own output: the final-iteration table and the `Re / Ie / Sky` line from the de Vaucouleurs fits along the major and minor axes.
2. The same table that MONSTA's `PRINT EPROF` produces, using that command's FORMAT statements.

Progress from `MODEL` goes to stderr. `DUMP=k` writes `fort.2`, as it does in the original.

## Layout

| Path | Contents |
|---|---|
| `src/original/` | `elliprof.f jtutil.f gcfit.f assign.f dissect.f value.f operate.f variable.f upper.f`, byte-identical copies of `monsta/libvista/fcode/` |
| `include/` | `vistalink.inc imagelink.inc profile.inc mongo.par`, byte-identical (`mongo.par` is the target of the libvista symlink) |
| `src/shim/main.f` | Driver. Sets the COMMON state VISTA normally sets up (`GO`, `XERR`, `NOGO`, `WORD()`, `ISR`/`ISC`/`IM`, `HEADBUF`), calls `ELLIPROF(DATA,NROW,NCOL)`, prints and saves `/PRF/` |
| `src/shim/stubs.f` | Replaces `INVISTA` (reads a line from stdin), `MARK` (stops with a message; there's no cursor), `TVCROSS`/`TVCIRC` (no-ops) and `TELLME` (progress to stderr) |
| `src/shim/fitsio.f` | CFITSIO read and write |
| `src/shim/profout.f` | `--csv` and `--reg` writers. The column mapping comes from where ELLIPROF fills `PARAM_PRF` (`elliprof.f`, loop 30) and from `PRINT EPROF`; the comments in `profile.inc` describe an older layout and are wrong for ELLIPROF |
| `tests/mktestimage.f` | Generates `test_image.fits`, a noiseless r^¼ galaxy: centre (127.3,121.6), Re=20, Ie=200, ellipticity 0.3, PA 30° from +x, sky 100 |

## Compiler flags

`-O -g -fno-automatic -ffp-contract=off`

- `-O -g -fno-automatic` are MONSTA's own flags. `-fno-automatic` gives local variables static storage and zero initialization, which the code relies on.
- `-ffp-contract=off` stops GCC from fusing multiply-adds into FMA instructions (it does this by default on arm64), so REAL\*4 results stay reproducible.
- Never build with bounds checking. The F77 code declares dummy arrays as `X(1)`/`X(2)` and indexes past them on purpose.

## Known limitations

- **TV:** `TV` works only when `X0 Y0 R0 R1 NR` are all given. Otherwise ELLIPROF asks for the cursor, and `MARK` stops the program.
- **`OLD` and `EDIT`:** these start from an earlier profile held in `/PRF/`. The program doesn't load a `.prf` file yet (MONSTA's `GET ELLIPROF=`), so they start from an empty profile.
- **Model header:** the model image is written with a minimal header (BITPIX -32, CNPIX if nonzero). It doesn't copy the input header the way MONSTA's `WD` does.

These bugs in the original code are kept as-is:
- `FITPROFILE` has room for only 100 radii, so `NR > 100` overwrites memory.
- `ARRAYCENTER` assumes an image at most 2048 pixels on a side (GC mode).
- `TRIMIT` doesn't remove the neighbours of a rejected star.
- Radii with fewer than 9 samples (R < ~2.9 px) make `FITCONTOUR` give up, which produces `NaN` on that isophote.

## Not yet done

- **Baseline comparison:** there isn't yet a baseline from the full MONSTA build to compare against.
- **What the synthetic image shows:** it only proves the program runs. It isn't evidence that the results are scientifically equivalent to MONSTA's.
- **Reading differences for integer images:** MONSTA normally reads FITS with its own reader (`disk.f`) and only falls back to CFITSIO. For BITPIX = -32 images the pixel values should be identical. For scaled integer images, the last bits may differ.
