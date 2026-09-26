# 5-minute quick start

This page fits a real galaxy: **UGC 12517**, an elliptical galaxy observed
with the Hubble Space Telescope (WFC3/IR camera, F110W filter). The image
and its mask are in the elliprof repository.

## 1. Get the data

```sh
mkdir elliprof-quickstart && cd elliprof-quickstart
curl -LO https://raw.githubusercontent.com/ekourkchi/elliprof/main/examples/u12517/u12517j.fits
curl -LO https://raw.githubusercontent.com/ekourkchi/elliprof/main/examples/u12517/u12517j.dmask
```

- `u12517j.fits`: the image, 1025 × 1022 pixels, 0.128″ per pixel (4 MB).
- `u12517j.dmask`: a pixel mask in the historical ELLIPROF bitmap format.
  **0 = masked, 1 = good.** About 10% of the pixels are masked: stars,
  background galaxies, the nucleus and the image edges.

## 2. Run elliprof

```sh
elliprof u12517j.fits \
    --mask u12517j.dmask --sky 3246 \
    X0=567 Y0=562 \
    R0=9 R1=347 NR=23 NITER=10 RMSTAR \
    -o u12517j.prf --csv u12517j.csv --reg u12517j.reg \
    MODEL -m u12517j_model.fits --residual u12517j_residual.fits
```

| Part | Meaning |
|---|---|
| `--sky 3246` | subtract a constant sky level (in image units) from every pixel |
| `--mask u12517j.dmask` | ignore the masked pixels |
| `X0=567 Y0=562` | the **initial** galaxy centre, in pixels. You must give it; ELLIPROF then fits a centre for every isophote |
| `R0=9 R1=347 NR=23` | 23 isophotes with semi-major axes from 9 to 347 pixels |
| `NITER=10` | 10 iterations of the fit (the default is 5) |
| `RMSTAR` | reject star-like bright points along each ellipse |
| `-o`, `--csv`, `--reg` | the profile (native format and CSV) and the ellipses as DS9 regions |
| `MODEL -m ...` | build the model image and write it |
| `--residual ...` | write data − sky − model (masked pixels are 0) |

elliprof prints a short summary:

```text
elliprof 0.1.3
Fitting 23 isophotes...
Image:    u12517j.fits (1025 x 1022)
Sky:      scalar 3246
Mask:     u12517j.dmask - 103402 pixels masked (9.871%)
Fit complete: 23 isophotes.
elliprof: note: 10 isophote fit(s) had too few usable samples along the ellipse (e.g. inside a masked region) and kept their previous parameters
Profile:  u12517j.prf
CSV:      u12517j.csv
Regions:  u12517j.reg
Model:    u12517j_model.fits
Residual: u12517j_residual.fits
Done.
```

The note is expected here. The innermost isophote (9 pixels) lies inside
the masked nucleus, so it has no usable pixels in any of the 10
iterations and keeps its starting values. Start at `R0=12` and the note
goes away.

## 3. Look at the result

**The ellipses on the image** (in [SAOImage DS9](https://sites.google.com/cfa.harvard.edu/saoimageds9)):

```sh
ds9 u12517j.fits -regions u12517j.reg
```

**The model and residual:** open `u12517j_model.fits` and
`u12517j_residual.fits` in DS9 next to the image. They carry the image's
WCS, so you can lock them by WCS (Frame → Lock → Frame → WCS).

**The profile:** `u12517j.csv` is a table with one row per isophote:

```text
#     Rmaj,         x0,         y0,              I0,      alpha,      ellip,              I3,         A3,              I4,         A4,      slope
    9.0000,   567.0000,   562.0000,   4.8629281E+05,     3.6000,   0.219101,   0.0000000E+00,     0.0000,   0.0000000E+00,     0.0000,  -0.232092
   11.7009,   567.6519,   562.7004,   4.5242172E+05,     1.6186,   0.262981,   2.2035360E-02,   105.0390,   1.1071682E-02,    54.0785,  -0.640556
   14.9685,   567.0881,   562.5162,   3.3846838E+05,   176.6152,   0.210783,   8.2063675E-04,    21.3147,   5.5096149E-03,    43.7455,  -1.228434
   ...
```

The first row is the isophote inside the masked nucleus. It still holds
its starting values (I3 = I4 = 0, centre = X0, Y0).

Plot it in Python:

```python
import matplotlib.pyplot as plt
from elliprof import read_profile

p = read_profile("u12517j.prf").iloc[1:]      # skip the unfitted r = 9
fig, ax = plt.subplots(1, 2, figsize=(9, 3.5))
ax[0].loglog(p.Rmaj, p.I0, "o-")
ax[0].set(xlabel="semi-major axis [pixels]", ylabel="I0")
ax[1].semilogx(p.Rmaj, p.ellip, "o-")
ax[1].set(xlabel="semi-major axis [pixels]", ylabel="ellipticity 1 - b/a")
plt.show()
```

## 4. The same in Python

```python
from elliprof import run_elliprof

r = run_elliprof("u12517j.fits", x0=567, y0=562, r0=9, r1=347, nr=23,
                 niter=10, rmstar=True, mask="u12517j.dmask", sky=3246,
                 model=True, residual_path="u12517j_residual.fits",
                 output_dir=".")
print(r.profile[["Rmaj", "I0", "ellip", "alpha", "I4", "A4"]])
print(r.model_path, r.residual_path)
```

## Next

- [What is an isophote?](concepts/isophotes.md): what the numbers mean.
- [UGC 12517, step by step](tutorials/u12517.md): the same fit, explained
  in detail.
- [The profile](outputs/profile.md): every column and its convention.
