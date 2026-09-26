# The profile

The **profile** is ELLIPROF's main result: one set of numbers for each
fitted isophote. elliprof writes it in two formats with the same
content:

| Option | File |
|---|---|
| `-o FILE.prf` | ELLIPROF's native profile format, at full precision, with the run settings and the image header |
| `--csv FILE.csv` | a commented, comma-separated table, one row per isophote |

In Python, `result.profile` (from `run_elliprof`) or
`elliprof.read_profile("FILE.prf")` gives the same table as a pandas
DataFrame.

!!! warning "A .prf file is not an image"
    The `.prf` is a **table of numbers**, not a picture. You cannot open it
    in DS9. To *see* the fit, use the DS9 region file (`--reg`) on the
    image, the model image (`MODEL -m`) or the residual (`--residual`).
    See [Model, residual and prepared images](images.md).

If you give neither `-o` nor `--csv`, the profile table is printed on the
terminal instead.

## Columns

| Column | Unit | Meaning |
|---|---|---|
| `Rmaj` | pixels | semi-major axis *a* of the isophote |
| `x0`, `y0` | pixels | fitted centre of this isophote, in [ELLIPROF coordinates](../concepts/how-it-works.md#1-the-initial-centre-and-the-fitted-centres) |
| `I0` | image units / pixel | intensity of the isophote, after the sky is subtracted |
| `alpha` | degrees, 0–180 | position angle of the major axis, **counter-clockwise from the image +y axis**. From +x it is `alpha + 90` |
| `ellip` | | ellipticity 1 − b/a |
| `I3`, `I4` | fraction of `I0` | amplitude of the 3rd/4th-order intensity variation around the isophote |
| `A3`, `A4` | degrees | their phases, in eccentric angle from the major axis (`A3` 0–120, `A4` 0–90). **Not** position angles |
| `slope` | | logarithmic slope d ln I / d ln r, from the neighbouring isophotes (set to −2 where it would be positive) |

The details are on [What is an isophote?](../concepts/isophotes.md),
[How ELLIPROF fits a galaxy](../concepts/how-it-works.md) and
[Boxy and disky isophotes](../concepts/harmonics.md).

!!! researcher "What the profile does not contain"
    - **No uncertainties.** Estimate them yourself, for example from
      repeated fits with different masks, skies or starting values, or
      from simulations.
    - **No calibration.** `I0` is in image units per pixel. Converting to
      mag/arcsec² needs a zeropoint and a pixel scale; see
      [Galaxy surface photometry](../science/surface-photometry.md).
    - **No sky position angle.** `alpha` is relative to the image axes.

## The profile of UGC 12517

<figure markdown="span">
  ![Six panels against semi-major axis for UGC 12517: the isophote
  intensity falling by a factor of 300 from 12 to 347 pixels; the
  ellipticity about 0.21 inside 70 pixels and falling to 0.175 at the edge;
  the position angle constant within about 1.5 degrees; the logarithmic
  slope steepening from −1.2 to −2.7; a4/a small and mostly slightly
  negative, around −0.2 percent; and the fitted centres staying within
  about 1.5 pixels of the starting centre.](../assets/profile_panels.png)
  <figcaption>The UGC 12517 profile (real fit, 22 isophotes; the
  unfitted r = 9 isophote inside the masked nucleus is left out). Position
  angles are unwrapped across 0°/180° for plotting.</figcaption>
</figure>

What you can read from it:

- The **intensity** falls smoothly, with no breaks.
- The **ellipticity** is about 0.21 out to ~70 pixels (9″), then falls
  slowly to 0.175: the galaxy is rounder in its outskirts.
- The **position angle** is constant to within about 1.5°: no isophote
  twist.
- The **slope** steepens outwards, as expected for an elliptical galaxy.
- **a4/a** is within a few tenths of a percent of zero: nearly pure
  ellipses.
- The **centres** agree to better than half a pixel inside ~100 pixels,
  and scatter by up to 1.5 pixels further out, where the galaxy is faint
  and heavily masked.

The second isophote (11.7 pixels) is also affected by the masked nucleus:
its ellipticity and I4 differ from their neighbours.

### Plotting conventions

!!! beginner "Position angles near 0° and 180°"
    `alpha` is an axis direction, so 0° and 180° are the same. A galaxy
    with its major axis near the image's y axis can jump between ~2° and
    ~178° from one isophote to the next, although the orientation has
    barely changed. To plot it, unwrap the angles:

    ```python
    import numpy as np
    alpha = np.degrees(np.unwrap(np.radians(2 * p.alpha))) / 2
    ```

- Plot the radius on a log axis, or as $r^{1/4}$ (a de Vaucouleurs law is
  then a straight line in magnitudes).
- Plot intensities on a log axis, or as surface brightness in
  magnitudes.

## Reading the files

```python
from elliprof import read_profile, read_prf

p = read_profile("u12517j.prf")      # pandas DataFrame
print(p.attrs["scale"])              # SCALE= (arcsec/pixel), if given

raw = read_prf("u12517j.prf")        # dict: n, scale, params (250 x 12), header
```

The CSV starts with `#` comment lines (input, mask, sky, parameters,
version, units, and the column names). elliprof reads it back with
`parse_elliprof_csv`:

```python
from elliprof import parse_elliprof_csv
p, meta = parse_elliprof_csv("u12517j.csv")    # DataFrame, dict of header lines
print(meta["Sky"], meta["Parameters"])
```

With another CSV reader, skip the `#` lines and supply the column names
(they are in `elliprof.COLUMNS`):
`pandas.read_csv("u12517j.csv", comment="#", header=None, names=elliprof.COLUMNS, skipinitialspace=True)`.
