# Precision: single and double

elliprof has two backends, chosen with `--precision` (Python:
`precision=`):

| | single | double |
|---|---|---|
| what it is | the original ELLIPROF, compiled unchanged | a precision port of the same routines |
| arithmetic | 32-bit floating point (`REAL*4`) | IEEE-754 double precision (binary64) |
| values it can hold | about 1.2 × 10⁻³⁸ to 3.4 × 10³⁸, 7 digits | about 4.9 × 10⁻³²⁴ to 1.8 × 10³⁰⁸, 16 digits |
| model, residual, prepared | 32-bit FITS (`BITPIX` −32) | 64-bit FITS (`BITPIX` −64) |
| profile (`-o`, `--csv`) | 9 significant digits | 18 significant digits, 3-digit exponents |
| GC mode | yes | not yet |

The double backend reads and processes 64-bit FITS data without
reducing them to float32. Finite values are retained and calculations
are performed using IEEE-754 double precision throughout the double
path, subject to the representable range of the required intermediate
and final mathematical operations.

## Choosing: `auto`

`--precision auto` is the default. It runs **double** only when single
could not hold the data, and **single** otherwise, so ordinary images
give exactly the results of earlier versions. Double is chosen when

- the science image, or the sky image, is stored with `BITPIX` 64 or
  −64;
- a finite value of the science or sky image, after `BSCALE`/`BZERO`,
  would be infinite in 32-bit floating point (beyond about 3.4 × 10³⁸)
  or is nonzero but would be 0 (below about 7 × 10⁻⁴⁶); elliprof checks
  the actual values, never `DATAMIN`/`DATAMAX`;
- the `--sky` value or the `SKY=` keyword is such a value, or is a valid
  number that the original single-precision parser cannot read. That
  parser refuses decimal exponents beyond about ±38 even for numbers a
  32-bit float holds (`1e-40`, `3.4e38`), so 0.1.4 failed on them;
  elliprof runs the old parser on the text itself to decide.

Values that remain nonzero as tiny 32-bit numbers, values that are
merely not exact in 32 bits, and 32-bit integers above 2²⁴ do not
select double. Masks never do.

The summary says what ran and why, for example

```text
Precision: double (auto: science image BITPIX -64; fit on image x 2**-k, k = 10)
```

and the CSV records it (`# Precision:`). In Python,
`result.precision`, `result.precision_requested` and
`result.precision_reason` hold the same.

`--precision single` and `--precision double` force one backend.

## How the double backend works

1. The science and sky images are read with CFITSIO in double
   precision (`BSCALE`/`BZERO` applied in double). `--sky` is parsed
   exactly (correctly rounded).
2. Sky subtraction and the mask, as in single, in double precision.
3. **Normalization.** The fit runs on the prepared image multiplied by
   2⁻ᵏ, an exact power of two, so that typical values are near 1. k is
   the binary exponent of the median |value| of the finite nonzero
   pixels (of the largest |value| for `LINEAR`), moved if necessary so
   that no value overflows or becomes zero. Multiplying by a power of
   two changes no digit, and the fit is scale-invariant, so the
   result is the same as without it; intensities (`I0`, `SKY=`, the
   model) are converted back exactly. The summary, the CSV and the FITS
   `HISTORY` record k.
4. The fit and the model: the original routines in double precision,
   with π and 1/3 to double precision. The original model synthesis
   computes a pixel only where the natural log of its intensity lies
   within ±85 (the range of the 32-bit exponential) and sets other
   pixels to 0; the double port computes every pixel that double
   precision can represent.

A double profile is marked by a `HISTORY` card in the header text it
carries; `read_prf` and `read_profile` then read its values as exact
64-bit floats (`df.attrs["precision"] == "double"`).

## Single and double on ordinary data

On ordinary, well-conditioned data the two backends agree to the
rounding of 32-bit floating point: isophote centres to about 10⁻⁵
pixel, intensities to about 10⁻⁶ relative. Where a fit is
ill-conditioned (very faint outer isophotes, nearly circular isophotes
whose position angle is undefined), the iteration amplifies any
difference, and the two can differ by as much as the fit's own
sensitivity: for UGC 12517 a change of the sky by 10⁻⁴ counts moves the
outermost isophotes by about as much as single and double differ.

## Limits

- **GC mode** runs in single only.
- **Extreme ratios inside one image.** When the brightest and the
  typical values of one image are more than about 10³⁰⁸ apart (for
  example a galaxy at 10⁻³⁰⁰ with a 10³⁰⁰ source), the normalization
  cannot centre the data. Two quantities of the fit whose intermediate
  could then overflow are computed safely, only in that case: the log
  of an intensity ratio along an isophote (taken in the log domain when
  the ratio itself would exceed the double range) and the `AVG` box sum
  (accumulated in units of the box's largest value). Every ordinary
  image keeps the original arithmetic, bit for bit.
- If the fit itself still leaves the double range -- an isophote
  intensity overflowing or underflowing to 0 during the iteration, or a
  slope between neighbouring isophotes whose intensities differ by more
  than 10³⁰⁸ -- elliprof stops with a clear error naming the isophote,
  never a silent NaN.
- A `LINEAR` fit, which squares intensities, refuses an image spanning
  more than about 2¹⁵⁷³ with a clear error.
- The **single** backend's parser limit (above) still applies with
  `--precision single`.
- Pixels exactly at the largest double (1.8 × 10³⁰⁸) can make the
  four-pixel interpolation round past the double range; such values do
  not occur in ordinary data.
- **Model underflow.** Far in the wings, the model's exponential can be
  below the smallest double and becomes 0. This is counted, not an
  error: `Model: N pixels underflowed to zero at double precision.`
  in the summary, `# Model underflow to zero:` in the CSV, a `HISTORY`
  card in the model and residual, `result.model_underflow_zero_count`
  in Python.

## Memory

The double backend keeps these arrays per pixel: the image (8 bytes),
its prepared copy for `--residual` (8), the logical mask (4, also with
the default `--nonfinite mask`), and a transient buffer while a mask (12)
or a sky image (8) is read. With a mask and `--residual` that is
**32 bytes per pixel**:

| Image | Pixels | Per-pixel arrays (32 B/pixel) |
|---|---|---|
| 4096 × 4096 | 16.8 million | 512 MiB |
| 8192 × 8192 | 67.1 million | 2 GiB |
| 10000 × 10000 | 100 million | 3.0 GiB (3052 MiB) |

This is a baseline for the per-pixel arrays, not the peak memory of the
process: the fit's own arrays, CFITSIO buffers, the header, the Fortran
run time and, with the Python API, Python itself come on top.
`--verbose` prints the estimate for the run. If the memory is not
there, elliprof says so and stops. There is no size limit.

## Modern multi-extension images (JWST, HST, Euclid, ...)

elliprof stays a generic FITS tool. It needs no mission software.

- **Select the image HDU** with CFITSIO syntax: by name
  `'cal.fits[SCI]'`, number `'cal.fits[1]'`, or name and version
  `'cal.fits[SCI,2]'`. A table HDU, or an HDU without a 2-D image, is
  refused.
- **2-D only.** A cube is refused; fit one plane with a CFITSIO
  section, `'cube.fits[SCI][*,*,2:2]'`.
- **NaN no-data regions:** `--nonfinite` decides what happens to
  science pixels that are NaN or ±Inf after the sky and the mask.
  `mask` excludes them like masked pixels: the effective mask is your
  mask AND the finite pixels (and, later, a data-quality selection).
  `keep` passes them to ELLIPROF, as 0.1.4 did, with a warning; the
  log-intensity fit skips such samples, but `LINEAR` fits, the model
  and the products do not. `error` refuses the image. The default,
  `auto`, is `mask`, except with an explicit `--precision single`,
  where it is `keep`, so `--precision single` alone reproduces 0.1.4
  exactly. The summary records the policy and the NaN, +Inf and −Inf
  counts (`result.nonfinite_counts` in Python).
- **Data-quality flags:** a `DQ` extension can be used as an ordinary
  mask in which any nonzero flag is bad:
  `--mask 'cal.fits[DQ]' --mask-convention zero-good`. Selecting
  individual bits is not supported yet.
- **Units:** elliprof never converts units. `I0` and the model are in
  the units of the science image, and `BUNIT` and the WCS are copied to
  every product.
- **Uncertainties:** `ERR` and `VAR_*` extensions are not used; the fit
  is not weighted by them.
- The products are plain FITS images with the science header; they do
  not reproduce the input file's other extensions or its ASDF metadata.
