# What is an isophote?

An **isophote** is a curve of constant surface brightness on the sky: every
point on it is equally bright. For a smooth galaxy, the isophotes are
nested closed curves, bright near the centre and fainter outwards.

In elliptical galaxies, lenticulars and bulges, the isophotes are very
close to **ellipses**. The ellipses need not share one centre, one shape
or one orientation. Measuring how they change with radius is one of the
basic tools of galaxy structure. That is what ELLIPROF does: it describes
the galaxy as a set of nested ellipses, one per radius, and measures each
one.

!!! beginner "In one sentence"
    ELLIPROF slices the galaxy into rings of equal brightness and records,
    for each ring, how bright it is, where its centre is, how flattened
    it is, which way it points, and how much it differs from a perfect
    ellipse.

## The geometry of one isophote

<figure markdown="span">
  ![Diagram of one ellipse. The centre is marked with a cross, and the
  image's +x (columns) and +y (rows) axes are drawn as arrows. The
  semi-major axis a runs from the centre to the upper left, and the shorter
  semi-minor axis b runs to the lower left. An arc marks the angle alpha
  between the +y axis and the major axis, counter-clockwise. Dots around
  the ellipse mark sample points.](../assets/isophote_geometry.png){ width="520" }
  <figcaption>Schematic. The quantities ELLIPROF reports for each isophote.
  The dots are sample points at equal steps of the eccentric
  angle.</figcaption>
</figure>

| Quantity | Profile column | Meaning |
|---|---|---|
| semi-major axis $a$ | `Rmaj` | half the longest diameter, in pixels. This is the "radius" of the isophote |
| semi-minor axis $b$ | (from `ellip`) | half the shortest diameter |
| ellipticity | `ellip` | $\epsilon = 1 - b/a$. 0 for a circle, larger for flatter ellipses |
| position angle | `alpha` | direction of the major axis, in degrees (0–180), **counter-clockwise from the image +y axis** |
| centre | `x0`, `y0` | the fitted centre of this isophote, in pixels |
| intensity | `I0` | brightness of the isophote, in image units per pixel, after the sky is subtracted |

!!! warning "Position angle convention"
    ELLIPROF measures `alpha` counter-clockwise from the **+y axis of the
    image** (the pixel rows), not from north. Measured from +x, the major
    axis is at `alpha + 90`°. To get a sky position angle (east of north),
    you must also use the image orientation from its WCS. An angle of 0°
    and one of 180° are the same axis. For example, 3° and 177° differ by
    only 6°.

## The eccentric angle

ELLIPROF measures positions around each ellipse with the **eccentric
angle** $\theta$, not the ordinary polar angle. A point on the ellipse is

$$ (x, y) = (a\cos\theta,\ b\sin\theta) $$

in the ellipse's own frame (major axis along $x$). Geometrically, $\theta$
is the angle on the circle of radius $a$ drawn around the ellipse.

<figure markdown="span">
  ![Diagram of an ellipse inside its auxiliary circle of radius a. A point
  on the circle at angle theta is projected vertically onto the ellipse,
  giving the point (a cos theta, b sin theta).](../assets/eccentric_angle.png){ width="520" }
  <figcaption>Schematic. The eccentric angle θ. The harmonic phases A3 and A4
  are measured in this angle, from the major axis.</figcaption>
</figure>

The harmonic phases `A3` and `A4` (see
[Boxy and disky isophotes](harmonics.md)) are angles of this kind. **They
are not position angles.**

## Surface brightness and the profile

The intensities `I0` of the isophotes, as a function of semi-major axis,
form the galaxy's **surface-brightness profile**. Together with how
`ellip`, `alpha` and the centre change with radius, this is the
**profile** that ELLIPROF writes. See [The profile](../outputs/profile.md).

In magnitudes per square arcsecond, after a photometric calibration
([Galaxy surface photometry](../science/surface-photometry.md)):

$$ \mu = -2.5\log_{10}\!\left(\frac{I_0}{s^2}\right) + m_1 $$

where $s$ is the pixel scale in arcseconds and $m_1$ the magnitude of one
unit of image flux.

## Why isophotes change with radius

Real galaxies are not perfect nested ellipses, and the ways they depart
from that are informative:

- **Ellipticity changes** reflect the 3-D shape, or an embedded disk.
- **Position-angle twists** (`alpha` changing with radius) can mean a
  triaxial galaxy seen in projection, or an interaction.
- **Centre shifts** can mean asymmetry, dust or a disturbed galaxy. Fits
  near masked regions, or at very low surface brightness, also shift.
- **Boxy or disky isophotes** (the 4th-order term) are linked to how the
  galaxy formed. See [Boxy and disky isophotes](harmonics.md).

!!! researcher "Isophote fitting in the literature"
    ELLIPROF's approach is to sample the image along each ellipse, expand
    the intensity in a Fourier series of the angle, and use the low-order
    terms to correct the ellipse. The same approach underlies other
    isophote-fitting programs, notably the method described by
    Jedrzejewski (1987, MNRAS 226, 747). ELLIPROF is an independent
    implementation with its own conventions. Check the conventions on
    [How ELLIPROF fits a galaxy](how-it-works.md) before comparing numbers
    between programs.

Next: [How ELLIPROF fits a galaxy](how-it-works.md).
