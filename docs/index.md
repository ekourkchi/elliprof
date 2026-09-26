---
title: ELLIPROF - galaxy isophote fitting
---

# ELLIPROF

<p class="hero-tagline">
<strong>Fit elliptical isophotes to a galaxy image, and measure how its brightness,
shape and orientation change with radius.</strong> ELLIPROF also builds a smooth
model of the galaxy and the residual image left when that model is
subtracted.
</p>

<figure markdown="span">
  ![Four panels of the elliptical galaxy UGC 12517. First, the observed
  HST image: a smooth elliptical galaxy surrounded by small stars and
  background galaxies. Second, the same image with orange fitted ellipses,
  slightly elongated vertically, nested around the centre. Third, the smooth
  model image built by ELLIPROF. Fourth, the residual image (observed minus
  model) in red and blue, with masked stars and galaxies shown in
  grey.](assets/hero_u12517.png)
  <figcaption>UGC 12517 observed with HST WFC3/IR (F110W), from the example in
  the elliprof repository. From left to right: the image, the fitted
  isophotes, the ELLIPROF model, and the residual. Every panel is a real
  elliprof 0.1.3 product.</figcaption>
</figure>

<figure markdown="span">
  ![Four small line plots against semi-major axis: the isophote intensity
  falls smoothly with radius; the ellipticity is about 0.21 in the inner
  part and falls to 0.18 outside; the position angle stays within a few
  degrees; the fourth-order amplitude I4 stays below about one
  percent.](assets/hero_profiles.png)
  <figcaption>The profile of the same fit: intensity, ellipticity, position
  angle and the 4th-order (boxy/disky) amplitude, one point per
  isophote.</figcaption>
</figure>

## What ELLIPROF does

You give ELLIPROF a FITS image, an initial galaxy centre and the range of
radii to fit. It fits a sequence of nested ellipses, one per radius. For
each ellipse it measures:

- the **intensity** of the isophote;
- the **centre**, **ellipticity** and **position angle**;
- the **logarithmic slope** of the intensity profile;
- the **3rd- and 4th-order deviations** from a pure ellipse, including the
  classic **boxy/disky** term.

From the fit it can build a **model image** of the galaxy and a **residual
image** (data − sky − model). The residual shows what the smooth model
does not describe: dust, disks, shells, tidal features and, at the
smallest scales, the pixel-to-pixel brightness fluctuations that
[surface brightness fluctuation (SBF)](sbf/index.md) distances rely on.

ELLIPROF works best for smooth light distributions: elliptical galaxies,
lenticulars, bulges and other early-type systems.

<div class="scope-box" markdown>
**ELLIPROF is not an SBF pipeline.** It fits isophotes and produces a
smooth galaxy model and a residual image, which are *inputs* to an SBF
measurement. The power-spectrum analysis, the corrections for globular
clusters and background galaxies, the calibration and the distance itself
are done by other software and by the researcher. See
[ELLIPROF's role in SBF](sbf/elliprof-role.md).
</div>

## Install and run

```sh
python -m pip install elliprof
elliprof -h
```

Prebuilt packages exist for Linux, macOS and Windows, and Python 3.6–3.14.
No compiler is needed. See [Install](install.md), then the
[5-minute quick start](quickstart.md).

## Where to start

!!! beginner "New to galaxy isophotes"
    Start with [What is an isophote?](concepts/isophotes.md), then run the
    [quick start](quickstart.md) and the
    [UGC 12517 tutorial](tutorials/u12517.md).

!!! researcher "You know surface photometry"
    Go to [How ELLIPROF fits a galaxy](concepts/how-it-works.md) for the
    exact conventions, then [The profile](outputs/profile.md),
    [Boxy and disky isophotes](concepts/harmonics.md) and the
    [command-line reference](reference/cli.md).

!!! advanced "You are preparing SBF data"
    Read [Surface brightness fluctuations](sbf/index.md),
    [ELLIPROF's role in SBF](sbf/elliprof-role.md) and
    [A residual for SBF work](tutorials/sbf-residual.md).

---

ELLIPROF was originally developed by John Tonry as part of MONSTA.<br>
Maintained by Ehsan Kourkchi (Edwin Kay) · Email: ekourkchi@gmail.com ·
[Source code](https://github.com/ekourkchi/elliprof) ·
[About and credits](about.md)
