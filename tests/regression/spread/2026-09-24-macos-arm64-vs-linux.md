# Cross-platform spread, measured 2026-09-24

Reference: macOS 26 arm64, elliprof_native built with Homebrew GCC 16.2.0, CFITSIO 4.7.
Compared: Ubuntu 24.04 aarch64 (native container) and x86_64 (emulated container), GCC 13.2, glibc, CFITSIO 4.3 (apt).
Linux aarch64 and Linux x86_64 were bit-identical to each other on every case.

Not yet measured: macOS x86_64, Windows x86_64 (need real CI runners).

Produced with: tests/regression/collect_outputs.py on each platform, then tests/regression/compare_platforms.py (raw maxima, no masking of ill-conditioned columns; see TEST_PLAN.md for the comparison rules).
## Linux x86_64 vs Darwin arm64

| case | Rmaj | x0 | y0 | I0 | alpha | ellip | I3 | A3 | I4 | A4 | slope |
|---|---|---|---|---|---|---|---|---|---|---|---|
| auto_center | 0.00e+00 | 0.00e+00 | 0.00e+00 | 2.44e-03 | 7.63e-05 | 1.13e-06 | 3.58e-07 | 1.42e+01 | 3.58e-07 | 8.83e-03 | 2.86e-06 |
| circular | 0.00e+00 | 4.20e-03 | 5.12e-03 | 4.10e+00 | 1.59e+02 | 2.08e-04 | 3.40e-04 | 5.81e+01 | 1.47e-04 | 4.37e+01 | 1.02e-02 |
| const_sky | 0.00e+00 | 0.00e+00 | 0.00e+00 | 2.44e-04 | 1.53e-05 | 5.96e-08 | 2.38e-07 | 2.80e-02 | 2.38e-07 | 1.27e-01 | 1.19e-06 |
| elliptical | 0.00e+00 | 0.00e+00 | 0.00e+00 | 3.81e-06 | 1.53e-05 | 0.00e+00 | 1.19e-07 | 1.34e-02 | 1.19e-07 | 3.48e-03 | 7.15e-07 |
| model | 0.00e+00 | 0.00e+00 | 0.00e+00 | 2.44e-04 | 1.53e-05 | 5.96e-08 | 2.38e-07 | 1.90e-02 | 2.38e-07 | 4.16e-02 | 1.19e-06 |
| noisy | 0.00e+00 | 2.29e-05 | 3.28e-04 | 2.38e-05 | 1.98e-04 | 4.29e-06 | 5.84e-06 | 9.74e-03 | 5.60e-06 | 5.08e-03 | 6.01e-05 |
| offcenter | 0.00e+00 | 0.00e+00 | 0.00e+00 | 2.44e-04 | 3.05e-05 | 1.79e-07 | 1.19e-07 | 6.13e-02 | 4.77e-07 | 1.85e-02 | 5.96e-07 |
| radec_center | 0.00e+00 | 0.00e+00 | 0.00e+00 | 2.44e-03 | 7.63e-05 | 1.13e-06 | 3.58e-07 | 1.42e+01 | 3.58e-07 | 8.83e-03 | 2.86e-06 |
| rotated | 0.00e+00 | 0.00e+00 | 7.63e-06 | 1.91e-06 | 0.00e+00 | 0.00e+00 | 0.00e+00 | 2.08e-02 | 1.19e-07 | 4.57e-03 | 9.54e-07 |
| sky_image | 0.00e+00 | 0.00e+00 | 0.00e+00 | 2.44e-04 | 1.53e-05 | 5.96e-08 | 2.38e-07 | 2.24e-02 | 2.38e-07 | 5.87e-02 | 1.19e-06 |
| star_mask | 0.00e+00 | 0.00e+00 | 0.00e+00 | 2.44e-04 | 1.53e-05 | 5.96e-08 | 2.38e-07 | 2.31e-02 | 2.38e-07 | 1.47e-01 | 1.19e-06 |
| star_nomask | 0.00e+00 | 0.00e+00 | 0.00e+00 | 2.44e-04 | 1.53e-05 | 5.96e-08 | 2.38e-07 | 1.90e-02 | 2.38e-07 | 1.14e-02 | 1.19e-06 |
| u12517 | 0.00e+00 | 2.99e-03 | 6.71e-04 | 4.69e-01 | 1.46e-02 | 1.86e-04 | 7.55e-05 | 7.19e-02 | 1.74e-05 | 4.03e-02 | 3.74e-05 |

## Overall maximum difference

| column | max abs | max rel |
|---|---|---|
| Rmaj | 0.000e+00 | 0.000e+00 |
| x0 | 4.204e-03 | 4.191e-05 |
| y0 | 5.119e-03 | 5.140e-05 |
| I0 | 4.104e+00 | 1.844e-03 |
| alpha | 1.595e+02 | 7.288e+00 |
| ellip | 2.083e-04 | 4.227e+00 |
| I3 | 3.396e-04 | 3.576e+23 |
| A3 | 5.811e+01 | 4.836e+00 |
| I4 | 1.472e-04 | 3.769e+00 |
| A4 | 4.375e+01 | 1.665e+01 |
| slope | 1.019e-02 | 6.736e-03 |
