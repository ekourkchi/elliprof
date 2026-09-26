# Boxy and disky isophotes

Real isophotes are not perfect ellipses. ELLIPROF measures how they
differ with the **3rd- and 4th-order harmonics** of the intensity around
each fitted ellipse. The 4th-order term is the classic measure of
**boxy** and **disky** isophotes.

## What I3, A3, I4, A4 are

Around each fitted ellipse, ELLIPROF fits the intensity with a constant
plus harmonics of orders 1–4 in the
[eccentric angle](isophotes.md#the-eccentric-angle) θ. Orders 1 and 2
are used to move the ellipse. Once the fit has converged they are close
to zero. What remains are orders 3 and 4:

$$ I(\theta) \approx I_0\left[1 + I_3\cos 3(\theta - A_3) + I_4\cos 4(\theta - A_4)\right] $$

| Column | Meaning |
|---|---|
| `I3`, `I4` | amplitude of the 3rd/4th-order variation, **as a fraction of `I0`** (dimensionless) |
| `A3`, `A4` | the phase, in degrees of eccentric angle **measured from the major axis**. `A3` is 0–120 and `A4` is 0–90 |

`A3` and `A4` are **not position angles**. They say *where around the
ellipse* the extra light is.

## Boxy or disky?

<figure markdown="span">
  ![Left: three shapes drawn over each other: a pure ellipse, a disky
  isophote that is pointed along its major and minor axes, and a boxy
  isophote with squared-off corners on the diagonals. Right: the
  intensity along a pure ellipse for each case against eccentric angle.
  The disky curve peaks at 0, 90, 180 and 270 degrees, the boxy curve at
  45, 135, 225 and 315 degrees, and the pure ellipse is flat.](../assets/boxy_disky_shapes.png)
  <figcaption>Schematic, with the deviations exaggerated. A disky isophote
  sticks out along its axes, so a pure ellipse finds extra light at 0°
  and 90°. A boxy isophote sticks out along the diagonals, at 45°.</figcaption>
</figure>

| `A4` near | Extra light | Shape |
|---|---|---|
| 0° or 90° | along the major and minor axes | **disky** (pointed, "lemon-shaped") |
| 45° | along the diagonals | **boxy** (squared-off) |

`A4` = 0° and `A4` = 90° are the same pattern, because
cos 4(θ − 90°) = cos 4θ. `I4` gives the size of the deviation.

## The conventional a4/a

In the literature, boxiness is usually quoted as **a4/a**: the cos 4θ
coefficient of the isophote's *radial* deviation from the ellipse,
divided by the semi-major axis. It is positive for disky isophotes and
negative for boxy ones. `I4` is an *intensity* amplitude, not a4/a.

To first order, a radial deviation δr of the isophote changes the
intensity at the ellipse by δI/I ≈ (−slope) · δr/r, where slope is
d ln I / d ln r. Therefore

$$ \frac{a_4}{a} \approx \frac{I_4\cos(4A_4)}{-\text{slope}} $$

and every term is in the profile.

<figure markdown="span">
  ![Left: a synthetic disky galaxy image with the ellipses fitted by
  elliprof. Right: the recovered a4/a against radius for three synthetic
  galaxies: injected a4/a of +0.03, 0 and −0.03. The recovered curves are
  flat at +0.030, 0 and −0.030 except at the first and last
  isophotes.](../assets/boxy_disky_recovery.png)
  <figcaption>A test with real elliprof fits: synthetic galaxies with known
  a4/a = +0.03, 0 and −0.03 are recovered as +0.030, 0.000 and −0.030 by
  the formula above.</figcaption>
</figure>

!!! warning "Other programs, other conventions"
    Other isophote-fitting programs report the 4th-order term with
    different normalisations and sign conventions (for example, a "B4"
    intensity coefficient, or a radial coefficient divided by a gradient).
    Convert every catalogue to a4/a before comparing.

## UGC 12517

In the example fit, `I4` is about 0.004 (0.4% of the isophote intensity)
and `A4` is mostly between 40° and 55°. That gives a4/a between about
−0.004 and +0.001, with a median of −0.002: very nearly pure ellipses,
if anything slightly boxy (see the a4/a panel on
[The profile](../outputs/profile.md#the-profile-of-ugc-12517)).

!!! researcher "Significance"
    ELLIPROF's profile does not include uncertainties. A deviation of a
    few tenths of a percent is small. Before interpreting it, estimate the
    noise, for example by refitting with different masks, sky levels or
    starting parameters, or by fitting simulated images with the same
    noise.

## Why it matters

The 4th-order shape of elliptical galaxies correlates with other
properties. Disky ellipticals tend to be rotation-supported and of lower
luminosity. Boxy ellipticals tend to be more luminous, slowly rotating,
and more often radio-loud and X-ray bright. This was the basis of
Kormendy & Bender's (1996) proposal to divide ellipticals into disky and
boxy types. See Kormendy, Fisher, Cornell & Bender (2009) for a detailed
study. Harmonic analysis of isophotes goes back to work including
Jedrzejewski (1987).

- Jedrzejewski, R. I. 1987, MNRAS, 226, 747, [doi:10.1093/mnras/226.4.747](https://doi.org/10.1093/mnras/226.4.747)
- Kormendy, J. & Bender, R. 1996, ApJ, 464, L119, [doi:10.1086/310095](https://doi.org/10.1086/310095)
- Kormendy, J., Fisher, D. B., Cornell, M. E. & Bender, R. 2009, ApJS, 182, 216, [doi:10.1088/0067-0049/182/1/216](https://doi.org/10.1088/0067-0049/182/1/216)

## The harmonics in the model image

The 3rd- and 4th-order terms are **always fitted and reported**. Separately,
you choose which of them go into the **model image**. This changes the
model (and therefore the residual), but **not the fitted profile**.

| Option | Model image contains | Original setting |
|---|---|---|
| (default) | 3rd- and 4th-order terms, each isophote's own values | `COS3X=2 COS4X=2` |
| `--model-harmonics none` | pure ellipses | `COS3X=0 COS4X=0` |
| `--model-harmonics 3` | 3rd-order term only | `COS3X=2 COS4X=0` |
| `--model-harmonics 4` | 4th-order term only (boxy/disky) | `COS3X=0 COS4X=2` |
| `--model-harmonics 3,4` | both (the default) | `COS3X=2 COS4X=2` |
| add `--harmonic-mode median` | the median of each term over all isophotes | 1 instead of 2 |

<figure markdown="span">
  ![Left: the UGC 12517 model built from pure ellipses. Middle: the
  difference made by adding the 4th-order term, a faint four-fold
  red-and-blue pattern around the centre. Right: the difference made by
  adding the 3rd- and 4th-order terms, a similar but less symmetric
  pattern.](../assets/model_harmonics.png)
  <figcaption>Real UGC 12517 models. Adding the harmonic terms changes the
  model by a small, structured amount. The fitted profile is the same in
  all three runs.</figcaption>
</figure>

!!! beginner "Which should I use?"
    Keep the default (3,4) to get a model that follows the galaxy as
    closely as ELLIPROF can. Use `--model-harmonics none` to see the
    boxy/disky structure itself: the residual from a pure-ellipse model
    shows it directly.

### Sixth order instead of third

`--sixth-order` (the original `COS3X` < 0) fits and models the 6th-order
term **in place of** the 3rd. It is the only harmonic setting that
changes the fit. The `I3` and `A3` columns then hold the 6th-order
amplitude, and a phase equal to twice the 6th-order phase (0–120°).

!!! warning "Known original behaviour"
    With `--sixth-order` in the default `each` mode, the model can have a
    few NaN pixels at the very centre, inside the innermost isophote.
