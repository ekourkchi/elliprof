# How elliprof is built

!!! advanced "For developers and the curious"
    You do not need this page to use elliprof. It explains how the package
    is put together, which matters when you want to know exactly which
    code produced a number.

## Layers

```text
 elliprof command / Python API      python/elliprof/   (cli.py, core.py, ...)
            |  builds the argument list, runs a subprocess, reads the outputs
            v
 elliprof_native  (compiled backend)
   src/shim/     main.f     driver: arguments, flags, image origin, outputs
                 fitsio.f   FITS input/output through CFITSIO
                 maskio.f   masks (FITS of any BITPIX, legacy BITPIX=1)
                 prep.f     (science - sky) x mask
                 profout.f  profile, CSV and DS9 region output
                 stubs.f    stand-ins for the original interactive environment
   src/original/ elliprof.f and its helpers  <- the numerical code, UNCHANGED
   include/      original include files       <- UNCHANGED
            |
            v
 CFITSIO (linked statically into the wheels)
```

- **The numerical code is the original.** `src/original/` and `include/`
  are copied byte for byte from the original distribution. They are
  never modified, and their SHA-256 hashes are checked on every test run.
  The isophote fit, the model synthesis, RMSTAR and the harmonics are
  exactly the original ELLIPROF.
- **The shim** replaces what the original interactive environment
  (MONSTA) provided around ELLIPROF: reading the image, preparing it,
  parsing the command, and writing the results. The interactive parts
  (terminal input, image display) are stubbed out, which is why `OLD`,
  `EDIT` and `TV` are not supported.
- **The Python layer** turns the command line or the `run_elliprof`
  arguments into a backend command. It runs the backend in a subprocess,
  with a timeout, and reads the profile. The command line and Python
  run the same backend with the same settings.

## Regression tests

The repository's test suite runs the backend on real and synthetic
images and compares the profiles with stored baselines. The built wheels
are tested too, on the platforms where their test dependencies install. See
[`tests/TEST_PLAN.md`](https://github.com/ekourkchi/elliprof/blob/main/tests/TEST_PLAN.md).

## Building from source

```sh
brew install gcc cfitsio              # or: apt install gfortran libcfitsio-dev
git clone https://github.com/ekourkchi/elliprof.git
cd elliprof
python -m pip install -e ".[test]"
make check                            # build and run all tests
```

## Scripts behind the figures

Every figure on this site is made by a script in
[`docs/scripts/`](https://github.com/ekourkchi/elliprof/tree/main/docs/scripts),
from the real UGC 12517 data or, for schematics and simulations, from
code that is clearly labelled as such.

```sh
python -m pip install elliprof matplotlib astropy
python docs/scripts/make_all.py          # writes docs/assets/*.png
```

| Script | Figures |
|---|---|
| `make_u12517_overview.py` | home-page hero, preparation chain, model, residual, model harmonics, WCS alignment, SBF residual illustration (real data) |
| `make_profile_plots.py` | profile panels and sky sensitivity, in measured image units (real data, real re-fits) |
| `make_isophote_diagram.py` | isophote geometry and eccentric angle (schematic); RLAW spacing (exact); RMSTAR and fitted centres (real data) |
| `make_boxy_disky_diagram.py` | boxy/disky shapes (schematic); a4/a recovery (real fits of synthetic images) |
| `make_sbf_workflow.py` | the SBF workflow diagram |
| `make_sbf_power_spectrum_schematic.py` | SBF simulation and power-spectrum fit (simulation) |
| `make_readme_banner.py` | the README header image (real data) |
| `residual_checks.py` | the residual table in the [SBF tutorial](../tutorials/sbf-residual.md) |
| `common.py` | shared settings and the elliprof runs |

## Building this site

```sh
python -m pip install -r requirements-docs.txt
mkdocs serve              # preview at http://127.0.0.1:8000
mkdocs build --strict     # the check the site workflow runs
```
