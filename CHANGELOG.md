# Changes

## Unreleased (candidate 0.2.0, branch precision64)

### Added

- **A double-precision backend.** `--precision single|double|auto`
  (Python `precision=`). single is the original ELLIPROF (32-bit
  floating point, unchanged); double is its port to IEEE-754 double
  precision: images read as 64-bit floats, sky and mask in double, an
  exact power-of-two normalization, the fit and the model in double,
  64-bit model/residual/prepared images, profiles with 18 significant
  digits. `auto` (the default) runs double only for data single cannot
  hold (`BITPIX` ±64, values beyond or below the 32-bit range); every
  other image gives the same results as 0.1.4. The summary, the CSV and
  `result.precision` say which backend ran and why.
- `--nonfinite auto|mask|keep|error` (`nonfinite=`): what happens to NaN
  and ±Inf science pixels (e.g. no-data regions). The default `auto`
  masks them, except with an explicit `--precision single`, which keeps
  them as 0.1.4 did; `--precision single` therefore still reproduces
  0.1.4 exactly. The summary records the policy and the counts.
- In double precision, intensity ratios along an isophote and `AVG` box
  sums that would exceed the double range are computed safely (only
  then; ordinary images keep the original arithmetic bit for bit), and
  a fit that still leaves the double range stops with a clear error.
  Model pixels that underflow to 0 are counted and reported.
- `auto` also chooses double when the single backend's parser cannot
  read a `--sky` or `SKY=` value (0.1.4 failed on, e.g., `--sky 1e-40`).
- `read_prf`/`read_profile` read double profiles exactly;
  `subtract_sky`/`apply_mask` take `precision="double"`.

### Changed

- An image with a third axis longer than 1 (a cube) is refused instead
  of being fitted on its first plane; select a plane with a CFITSIO
  section, `'cube.fits[SCI][*,*,2:2]'`.
- An image with an empty axis (`NAXISn = 0`, e.g. 256 x 0) is refused
  with "selected FITS image has invalid dimensions" before anything is
  allocated or fitted, in every precision (it used to hang or fit
  nothing).
- The CSV header has a `# Precision:` line, and the backend summary a
  `Precision:` line.
- `parse_elliprof_csv` parses numbers round-trip exactly.

### Fixed

- Wheel builds: CFITSIO 4.7.0's Fortran wrappers passed every C `long`
  argument with the wrong size on riscv64 (its `f77_wrap.h` lists the
  64-bit architectures and omits riscv64), so the riscv64 backend read
  images as 256 x 0. `tools/ci/build_cfitsio.sh` adds riscv64 to that
  list (no change on any other architecture) and runs a Fortran ABI
  probe (`tools/ci/cfitsio_f77_probe.f`) after every CFITSIO build.

## 0.1.4 (2026-10-06)

The numerical results are unchanged: for the same input, mask
convention and parameters, 0.1.4 writes a byte-identical profile (`-o`)
and region file, and model, residual and prepared images with identical
pixels. Only provenance text differs: the version in the images'
`HISTORY` card and in the CSV header, and the CSV's record of the command
as typed. The original ELLIPROF Fortran is untouched (SHA-256 verified).

### Changed

- **`-m FILE` alone computes and writes the model image.** Before, the
  model also needed the keyword `MODEL`, and `-m FILE` by itself was
  ignored. The common command is now

  ```sh
  elliprof n1234j.fits RMSTAR X0=514 Y0=514 R0=10 R1=450 NR=25 NITER=5 \
      -o n1234.dat -m n1234.prf
  ```

- `MODEL` is no longer needed. A bare `MODEL` in an old command is
  accepted and has no effect (a note says so). `MODEL=value` is an error;
  the model file is named only with `-m`.
- Without `-m` or `--residual`, no model is computed, even with a bare
  `MODEL` (the profile never depends on the model).
- The documentation uses the traditional ELLIPROF file names: `.dat` for
  the text profile (`-o`) and `.prf` for the FITS model image (`-m`).
  elliprof never checks or adds file extensions.
- Masks are classified from the value as stored, at full precision. A
  64-bit mask holding values such as 1e-300 or ±1e300 is now read
  correctly (0.1.3 treated tiny values as 0 and stopped with a CFITSIO
  overflow error on huge ones). Ordinary masks are unaffected.

### Added

- `--mask-convention zero-good` (Python: `mask_convention="zero-good"`):
  read a mask with 0 = good and any nonzero value = bad, as in many
  bad-pixel, data-quality and segmentation maps. NaN, Inf and undefined
  pixels are bad in both conventions. The default, `nonzero-good`
  (0 = bad), is unchanged. Refused for legacy `.dmask` bitmaps, which
  always mean 1 = good.
- `--niter N`, the same as ELLIPROF's `NITER=N` (default 5, from the
  original code). NITER is the only iteration count of the isophote fit.
- `COS3X=-3`: measure the 6th-order harmonic without putting it into the
  model. The original ELLIPROF code does this for any `COS3X` <= -3 (its
  help documents only 0/1/2 and "< 0: 6th order"); the package now
  exposes `COS3X=-3` as the supported spelling. Together: 2/1/0 = 3rd
  order, each / median / none; -2/-1/-3 = 6th order, each / median /
  none. Modern spelling: `--sixth-order --model-harmonics none` (or
  `4`). With `--sixth-order`, `--model-harmonics` also accepts `6` and
  `4,6`. Exactly -3..2 (`COS3X`) and 0..2 (`COS4X`) are accepted; other
  values are refused.
- A warning when a 6th-order term is put into the model (`COS3X=-2` or
  `-1`) and the fitted position angle wraps across 0/180 deg. This is a
  pre-existing limitation of the original ELLIPROF model synthesis, not a
  0.1.4 change: beyond the wrap it gives the 6th-order term the wrong
  sign, so the model and residual are wrong there. The measured profile
  is correct. The original code and its output are left unchanged;
  `COS3X=-3` measures the 6th order without the problem.
- In 6th-order mode the CSV header says so (`# Harmonic order: 6 ...`):
  the `I3`/`A3` columns then hold the 6th-order amplitude and twice its
  phase. Column names and the `.dat` format are unchanged.
- `elliprof --update` (also `-u`) installs the newest elliprof from PyPI
  with the pip of the Python that runs elliprof. `elliprof --check-update`
  only reports whether a newer version exists.
- After a fit in an interactive terminal, elliprof checks PyPI at most
  once a day, in the background, and prints one line if a newer version
  exists. It never installs anything by itself, never delays a fit, and
  is silent offline and in scripts. `ELLIPROF_NO_UPDATE_CHECK=1` turns it
  off.
- 64-bit FITS science images (`BITPIX` 64 and −64) are documented and
  tested. They were already read correctly: the pixels are converted to
  the nearest 32-bit float, the precision ELLIPROF works in, and the
  summary now notes the conversion. Products stay 32-bit floating point.
- The README shows the UGC 12517 example: the image, fitted isophotes,
  model, residual and profile. The banner uses an absolute URL so that
  it also displays on PyPI.
- The example notebook shows the original image, the model and the
  residual side by side, on the same stretch.
- Documentation: a new "Harmonic analysis" page, verified against the
  original source (the fitted convention, the phase ranges and the A3
  reference end, measuring versus modelling, every `COS3X`/`COS4X` value
  and its exact modern equivalent, sixth order and its output semantics,
  the a4/a conversion, synthetic and real examples, the SBF context);
  workflow and harmonic-mode diagrams; corrected wording: the 3rd/6th and
  4th orders do not move the ellipse, but the 3rd-or-6th choice can
  shift the fitted geometry slightly where an ellipse is poorly sampled.

Earlier versions (0.1.0–0.1.3): see the
[tags](https://github.com/ekourkchi/elliprof/tags) and the
[PyPI release history](https://pypi.org/project/elliprof/#history).
