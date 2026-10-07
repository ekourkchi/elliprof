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
- the `--sky` value or the `SKY=` keyword is such a value.

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
  typical values of one image are more than about 10³⁰⁸ apart, the
  normalization cannot centre the data, and some intermediate
  quantities of the fit (an intensity ratio along an isophote, an `AVG`
  box sum) can overflow; such isophotes come out as NaN. This needs
  data spanning most of the double range in a single image. A `LINEAR`
  fit, which squares intensities, refuses such an image with a clear
  error; the default log fit handles it unless the ratios themselves
  overflow.
- The **single** backend's command-line parser refuses numbers with a
  decimal exponent beyond ±38 even when a 32-bit float holds them (for
  example `--sky 1e-40`), as before; `--precision double` reads them.
- Memory: the double backend needs 8 bytes per pixel for the image, 8
  more for `--residual`, 4 for the mask, and a transient buffer while a
  sky image or mask is read. `--verbose` prints the estimate; if the
  memory is not there, elliprof says so and stops.

## Modern multi-extension images (JWST, HST, Euclid, ...)

elliprof stays a generic FITS tool. It needs no mission software.

- **Select the image HDU** with CFITSIO syntax: by name
  `'cal.fits[SCI]'`, number `'cal.fits[1]'`, or name and version
  `'cal.fits[SCI,2]'`. A table HDU, or an HDU without a 2-D image, is
  refused.
- **2-D only.** A cube is refused; fit one plane with a CFITSIO
  section, `'cube.fits[SCI][*,*,2:2]'`.
- **NaN no-data regions:** `--nonfinite mask` excludes NaN and ±Inf
  science pixels like masked ones (the effective mask is your mask and
  the finite pixels). The default, `keep`, passes them to ELLIPROF as
  before and warns; ELLIPROF's log-intensity fit skips such samples,
  but `LINEAR` fits and the products do not. `--nonfinite error`
  refuses the image.
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
