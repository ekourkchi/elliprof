# Python

The `elliprof` package runs exactly the same backend as the command
line, with the same settings.

```python
from elliprof import run_elliprof

r = run_elliprof("galaxy.fits", x0=500, y0=500, r0=5, r1=200, nr=30)
print(r.profile)            # pandas DataFrame, one row per isophote
```

## `run_elliprof`

```python
run_elliprof(image, x0, y0, *, r0, r1, nr, **options) -> ElliprofResult
```

The keyword names follow the command line, in lower case.

| Argument | Command line | Meaning |
|---|---|---|
| `image` | `IMAGE.fits` | path; may select an HDU: `"galaxy.fits[SCI]"` |
| `x0`, `y0` | `X0=`, `Y0=` | initial centre (ELLIPROF coordinates) |
| `r0`, `r1`, `nr` | `R0=`, `R1=`, `NR=` | radii (required) |
| `niter`, `rlaw`, `fixctr`, `ellip`, `tie`, `avg`, `gain`, `scale` | same keywords | see the [CLI reference](cli.md) |
| `rmstar=True`, `linear=True`, `gc=True` | `RMSTAR`, `LINEAR`, `GC` | switches |
| `sky` / `sky_image` | `--sky` / `--sky-image` | sky to subtract |
| `mask` | `--mask` | logical mask |
| `elliprof_sky` | `SKY=` | ELLIPROF's own sky (de Vaucouleurs fit only) |
| `model=True` | `MODEL` | build the model image |
| `model_harmonics` | `--model-harmonics` | `()`, `(3,)`, `(4,)` or `(3, 4)` (default) |
| `harmonic_mode` | `--harmonic-mode` | `"each"` (default) or `"median"` |
| `sixth_order=True` | `--sixth-order` | 6th order instead of 3rd |
| `cos3x`, `cos4x` | `COS3X=`, `COS4X=` | original switches (instead of the three above) |
| `output_dir`, `prefix` | | where and under which name to write the outputs (default: a new temporary directory, named after the image) |
| `prf_path`, `csv_path`, `reg_path`, `model_path` | `-o`, `--csv`, `--reg`, `-m` | explicit output paths, used as given (relative to the current directory, not `output_dir`) |
| `prepared` | `--prepared` | path of the prepared image |
| `residual_path` | `--residual` | path of the residual (implies the model) |
| `load_profile` | | `False` skips reading the profile (and never imports pandas) |
| `backend_verbose=True` | `--verbose` | the backend's full output in `result.stdout` |
| `timeout` | `--timeout` | seconds (default 1800; `None` = no limit) |
| `check` | | raise on failure (default `True`) |

It returns an `ElliprofResult` with:

| Attribute | Content |
|---|---|
| `profile` | the profile as a pandas DataFrame |
| `prf_path`, `csv_path`, `reg_path` | the profile and region files |
| `model_path`, `residual_path`, `prepared_path` | the images (or `None`) |
| `output_dir` | the directory the outputs went to |
| `center` | the initial centre |
| `stdout`, `stderr`, `returncode`, `command` | the backend run |
| `version`, `backend_path` | versions and paths, for records |

Errors raise `ElliprofError` (the fit failed; `.result` holds the
backend output), `ElliprofTimeoutError` (on timeout) or `GeometryError`
(a mask or sky image does not line up with the science image).

## Helpers

| Function | Purpose |
|---|---|
| `read_profile(path)` | a `.prf` file as a DataFrame (exact float32 values); `df.attrs` holds `scale` and the run `flags` |
| `read_prf(path)` | the raw `.prf` content: `n`, `scale`, `params` (250 × 12), `header` |
| `parse_elliprof_csv(path)` | a `--csv` file: `(DataFrame, header dict)` |
| `COLUMNS` | the profile column names |
| `write_ds9_regions(profile, path)` | DS9 ellipses from a profile |
| `read_ds9_regions(path)` | read them back |
| `load_mask(path)` | a mask as float32, as the backend sees it (FITS masks need astropy) |
| `write_bitmap_mask(path, mask)` | write a legacy BITPIX=1 mask |
| `subtract_sky(data, sky=None, sky_image=None)` | `data − sky` in float32, as the backend does |
| `apply_mask(data, mask)` | bad pixels → exactly 0, as the backend does |
| `harmonic_settings(...)` | the `COS3X`/`COS4X` values for given model-harmonic options |
| `find_backend()` | the path of the compiled backend |

## Example: fit and plot

```python
import matplotlib.pyplot as plt
from elliprof import run_elliprof

r = run_elliprof("u12517j.fits", x0=567, y0=562, r0=12, r1=347, nr=22,
                 niter=10, rmstar=True, mask="u12517j.dmask", sky=3246,
                 model=True, residual_path="u12517j_residual.fits",
                 output_dir="out")
p = r.profile
fig, ax = plt.subplots(1, 3, figsize=(12, 3.5))
ax[0].loglog(p.Rmaj, p.I0, "o-");     ax[0].set_ylabel("I0")
ax[1].semilogx(p.Rmaj, p.ellip, "o-"); ax[1].set_ylabel("ellip")
ax[2].semilogx(p.Rmaj, p.I4, "o-");    ax[2].set_ylabel("I4")
for a in ax:
    a.set_xlabel("Rmaj [pixels]")
plt.tight_layout()
plt.show()
```

A notebook with a worked example is in the repository:
[`notebooks/elliprof_example.ipynb`](https://github.com/ekourkchi/elliprof/blob/main/notebooks/elliprof_example.ipynb).
