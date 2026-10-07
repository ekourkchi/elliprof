# Changes

## 0.1.4 (release candidate, not yet released)

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

Earlier versions (0.1.0–0.1.3): see the
[tags](https://github.com/ekourkchi/elliprof/tags) and the
[PyPI release history](https://pypi.org/project/elliprof/#history).
