"""The ``elliprof`` command.

    elliprof image.fits X0=x Y0=y R0=r R1=r NR=n [KEY=value ...] [options]

``elliprof``, ``-h``/``--help`` and ``-v``/``--version`` are answered
before anything heavy is imported (no numpy, pandas or backend), so they
work even in a Python environment with broken optional packages.  A fit
never imports pandas either.
"""

import sys
from typing import List, Optional

from ._version import __email__, __maintainer__, __version__

# Plain ASCII only: old terminals (LANG=C) cannot print anything else.
CREDIT = "ELLIPROF was originally developed by John Tonry as part of MONSTA."

INTRO = """\
ELLIPROF - Galaxy Isophote Fitting

Fits elliptical isophotes to astronomical galaxy images and measures
radial intensity/surface-brightness structure, ellipticity, position
angle, centre variation and higher-order isophotal structure.

{credit}

Maintained by {maintainer}
Email: {email}

Run:

    elliprof -h

for usage, parameters, options, and examples.
"""

VERSION = """\
elliprof {version}
{credit}
Maintained by {maintainer}
Email: {email}
"""

HELP = """\
ELLIPROF - Galaxy Isophote Fitting (elliprof {version})

Fits a sequence of elliptical isophotes to a galaxy in a FITS image and
measures, for each one, its intensity, centre, ellipticity, position angle,
logarithmic slope and 3rd/4th-order deviations from a pure ellipse.  Suited
above all to elliptical galaxies, bulges and other smooth light
distributions.

USAGE
  elliprof IMAGE.fits X0=x Y0=y R0=r R1=r NR=n [KEYWORD=value ...] [options]

  Keywords (KEY=value, case-insensitive) and options may follow the image in
  any order.  With no -o/--csv/--reg the profile is only printed.

INPUT IMAGE AND INITIAL CENTRE
  IMAGE.fits    2-D FITS image of the galaxy (the first argument).
  X0=x Y0=y     REQUIRED initial galaxy centre [pixels].  ELLIPROF does not
                look for the galaxy: you give the starting centre, and the
                fit then finds a centre for EACH isophote (the x0, y0
                columns), unless FIXCTR=1.  Coordinates: the centre of the
                pixel in FITS column i is at x = i - 0.5 (half a pixel less
                than FITS/DS9 numbering); likewise for y and rows.

RADIAL FITTING PARAMETERS
  R0=r          REQUIRED semi-major axis of the innermost isophote [pixels].
  R1=r          REQUIRED semi-major axis of the outermost isophote [pixels];
                0 < R0 < R1.
  NR=n          REQUIRED number of isophotes, 2 to 100, including R0 and R1.
  RLAW=k        how the NR semi-major axes are spaced from R0 to R1:
                  2  equal steps in r^(1/4) (default),
                  1  equal steps in log r (geometric),
                  0  equal steps in r (linear).
  NITER=n       number of iterations (default 5, at most 1000).  One
                iteration visits every isophote once: it samples the image
                along the current ellipse (up to 360 points), fits the
                intensity around it with harmonics of orders 0-4, and moves
                the centre, ellipticity and position angle so that the
                ellipse follows the isophote; the slopes are then updated.
                Increase NITER if the parameters are still changing between
                the last iterations (e.g. with a poor starting centre).
  RMSTAR        reject star-like points: along each ellipse, samples brighter
                than median + 4 x (upper quartile - median) are ignored in
                that iteration.  Meant for faint stars and knots on the
                galaxy.  Only bright outliers are rejected, one sample at a
                time (the original code does not also drop the neighbouring
                samples it intends to); mask larger or extended
                contaminants with --mask instead.
  FIXCTR=k      0 each isophote finds its own centre (default); 1 all
                centres fixed at X0,Y0; 2 all centres set to the median of
                the fitted centres after each iteration.
  ELLIP=e       hold the ellipticity (1 - b/a) fixed at e (default: fitted).
  LINEAR        fit the intensities along each ellipse instead of their
                logarithms (default: logarithmic).
  TIE=k         smooth the parameters with radius after each iteration:
                k >= 0 a weighted polynomial of order k in r^(1/4); k < -1 a
                running binomial average over |k| isophotes; -1 (default) no
                smoothing.
  AVG=n         sample the image with a weighted (2n+1) x (2n+1) box average
                instead of bilinear interpolation (default 0); points with
                more than 20% masked weight are skipped.
  GAIN=g        fraction of each computed correction applied per iteration
                (default 1).
  SCALE=s       image scale [arcsec/pixel]; recorded in the profile only.
  GC            globular-cluster mode: circular annuli around a centre that
                ELLIPROF finds itself (then only NR is required).
  VERBOSE       print the parameters after every iteration.

SKY / BACKGROUND AND MASK
  The image is prepared as  (science - sky) x mask  before fitting; ELLIPROF
  ignores pixels that are exactly 0.  The sky is never estimated for you.
  --sky VALUE        subtract one constant sky/background level from every
                     pixel [same units as the image].
  --sky-image FILE   subtract a sky/background image pixel by pixel
                     (science - sky_image).  It must have exactly the same
                     dimensions as the science image.
                     --sky and --sky-image cannot be used together.
  --mask FILE        multiply by a mask: 0 = bad / excluded, 1 = good /
                     kept.  It must have exactly the same dimensions.  FITS
                     masks and legacy BITPIX=1 .dmask bitmaps (historical
                     ELLIPROF data) are accepted.
  --sc VALUE         deprecated alias of --sky; use --sky.
  SKY=s              ELLIPROF's own sky level, used ONLY in the de Vaucouleurs
                     fit it prints at the end; it does not change the image or
                     the profile (use --sky for that).
  Images are never resized, interpolated, cropped, shifted or reprojected.

MODEL AND HARMONIC CONTROLS
  MODEL -m FILE      build a 2-D model image of the galaxy from the fitted
                     isophotes and write it as FITS (both MODEL and -m are
                     needed).  The model follows the fitted intensity, centre,
                     ellipticity and position angle with radius, plus the
                     harmonic terms chosen below; it is relative to the
                     subtracted sky.  image - model shows what the smooth
                     model does not describe (dust, disks, shells, tidal
                     features, ...).
  Every isophote is fitted with a constant plus cos/sin of 1, 2, 3 and 4
  times the angle around the ellipse.  Orders 1-2 move the ellipse; orders 3
  and 4 are always measured (I3 A3 I4 A4) but never change the ellipse.
  These options choose what goes into the MODEL image and do NOT change the
  fitted profile -- except --sixth-order:
  --model-harmonics none|3|4|3,4
                     harmonic terms included in the model (default 3,4).
  --harmonic-mode each|median
                     each: every isophote's own terms (default); median: the
                     median of each term over all isophotes.
  --sixth-order      fit and model the 6th-order term in place of the 3rd.
                     This DOES change the fit; I3/A3 then hold the 6th-order
                     amplitude and twice its phase.  Known original
                     behaviour: in 'each' mode the model can have a few NaN
                     pixels at the very centre.
  Default: the same as COS3X=2 COS4X=2 (see LEGACY ELLIPROF CONTROLS).

OUTPUT FILES
  -o FILE        the profile in ELLIPROF's native .prf format, full precision.
                 A .prf is a table of numbers (one set of values per
                 isophote, plus the run settings), NOT an image.
  --csv FILE     the same profile as a commented, comma-separated table, one
                 row per isophote (columns below).
  --reg FILE     the fitted ellipses as a DS9 region file, to overlay on the
                 image:  ds9 IMAGE.fits -regions FILE
  -m FILE        the 2-D model image (FITS), with MODEL; see above.
  --prepared FILE  the prepared image (after sky and mask) exactly as
                 ELLIPROF fits it.

PROFILE COLUMNS (.prf, --csv)
  Rmaj    semi-major axis a of the isophote [pixels]
  x0 y0   fitted centre of this isophote [pixels, same coordinates as X0,Y0]
  I0      intensity level of the isophote [image units, after the sky]
  alpha   position angle of the major axis [deg, 0-180], counter-clockwise
          from the +y axis (i.e. from +x it is alpha + 90)
  ellip   ellipticity 1 - b/a
  I3 I4   amplitude of the 3rd/4th-order intensity variation around the
          isophote, as a fraction of I0 (dimensionless)
  A3 A4   their phases [deg] in the angle around the ellipse measured from
          the major axis: intensity ~ cos(n (theta - An)); A3 0-120, A4 0-90.
          They are NOT position angles.
  slope   logarithmic slope d ln I / d ln r from the neighbouring isophotes
          (set to -2 where it would be positive)
  Boxy/disky: A4 near 0 or 90 deg = disky, A4 near 45 deg = boxy.  I4 is an
  intensity amplitude, not a4/a or B4 (see the README for the conversion).

LEGACY ELLIPROF CONTROLS
  COS3X=k       original 3rd-order switch: 0 none, 1 median, 2 each isophote
                (default) in the MODEL image; -1/-2: the 6th-order term in
                place of the 3rd (changes the fit).
  COS4X=k       original 4th-order switch: 0 none, 1 median, 2 each
                (default) in the MODEL image; never changes the fit.
  Use either COS3X/COS4X or the options above, not both.  The interactive
  options OLD, EDIT and TV are not supported.

DIAGNOSTICS AND RUNTIME OPTIONS
  --timeout SECONDS  maximum run time of the fit (default 1800).  A safety
                     limit, not a fitting parameter: the backend and its child
                     processes are stopped, temporary files removed, and
                     elliprof exits with status 124.
  --diagnostics      report for support: versions, Python, OS/macOS,
                     architecture, backend location, architecture, minimum
                     macOS and version, and the numpy/pandas versions.
  -v, --version      version, original developer and maintainer.
  -h, --help         this help.

EXAMPLES
  Basic galaxy fit:
    elliprof galaxy.fits X0=500 Y0=500 R0=5 R1=200 NR=30 \\
        -o galaxy.prf --csv galaxy.csv --reg galaxy.reg

  Constant sky:
    elliprof galaxy.fits --sky 1234.5 X0=500 Y0=500 R0=5 R1=200 NR=30

  Mask and sky image:
    elliprof galaxy.fits --mask galaxy_mask.fits --sky-image background.fits \\
        X0=500 Y0=500 R0=5 R1=200 NR=30

  Model image with the 4th-order (boxy/disky) term only:
    elliprof galaxy.fits X0=500 Y0=500 R0=5 R1=200 NR=30 \\
        MODEL -m galaxy_model.fits --model-harmonics 4

  3rd and 4th order in the model, median over radii:
    elliprof galaxy.fits X0=500 Y0=500 R0=5 R1=200 NR=30 \\
        MODEL -m galaxy_model.fits --model-harmonics 3,4 --harmonic-mode median

  6th-order fit:
    elliprof galaxy.fits X0=500 Y0=500 R0=5 R1=200 NR=30 --sixth-order

{credit}
Maintained by {maintainer}   Email: {email}
Documentation: https://github.com/ekourkchi/elliprof
"""

# kept for callers of the old module attribute
USAGE = HELP

VALUE_OPTS = {"--mask", "--sky", "--sc", "--sky-image", "-o", "--csv",
              "--reg", "-m", "--prepared", "--timeout", "--model-harmonics",
              "--harmonic-mode"}
FLAG_OPTS = {"-h": "help", "--help": "help", "-v": "version",
             "--version": "version", "--diagnostics": "diagnostics",
             "--sixth-order": "sixth-order"}


class UsageError(Exception):
    pass


def _fmt(text: str) -> str:
    return text.format(version=__version__, maintainer=__maintainer__,
                       email=__email__, credit=CREDIT)


def _parse(argv: List[str]) -> dict:
    opts = {"words": [], "image": None}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in FLAG_OPTS:
            opts[FLAG_OPTS[arg]] = True
            i += 1
        elif arg in VALUE_OPTS:
            if i + 1 >= len(argv):
                raise UsageError(f"{arg} needs a value")
            key = "--sky" if arg == "--sc" else arg
            if arg == "--sc":
                print("elliprof: --sc is deprecated, use --sky",
                      file=sys.stderr)
            if key in opts:
                raise UsageError(f"{arg} given more than once")
            opts[key] = argv[i + 1]
            i += 2
        elif arg.startswith("-"):
            raise UsageError(f"unknown option {arg} (see elliprof -h)")
        elif opts["image"] is None:
            opts["image"] = arg
            i += 1
        else:
            opts["words"].append(arg)
            i += 1
    return opts


def _split_center(words: List[str]):
    """Take X0=/Y0= out of the ELLIPROF words; both are required."""
    found, rest = {}, []
    for w in words:
        key, eq, value = w.partition("=")
        if key.upper() in ("X0", "Y0") and eq:
            found[key.upper()] = value
        else:
            rest.append(w)
    if len(found) != 2:
        raise UsageError("X0 and Y0 are required")
    return found["X0"], found["Y0"], rest


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    if not argv:
        print(_fmt(INTRO), end="")
        return 0
    try:
        opts = _parse(argv)
    except UsageError as exc:
        print(f"elliprof: error: {exc}", file=sys.stderr)
        return 2
    if opts.get("help"):
        print(_fmt(HELP), end="")
        return 0
    if opts.get("version"):
        print(_fmt(VERSION), end="")
        return 0
    if opts.get("diagnostics"):
        from .diagnostics import diagnostics, format_diagnostics
        print(format_diagnostics(diagnostics()))
        return 0
    if opts["image"] is None:
        print("elliprof: error: no image given (see elliprof -h)",
              file=sys.stderr)
        return 2

    # Only a real fit gets this far.  It needs the backend and numpy (to
    # check the inputs), never pandas: the command line writes files and
    # does not build the profile DataFrame.
    import tempfile
    from pathlib import Path

    from .core import (DEFAULT_TIMEOUT, ElliprofError, ElliprofTimeoutError,
                       run_elliprof)
    try:
        if "--sky" in opts and "--sky-image" in opts:
            raise UsageError("--sky and --sky-image cannot be used together")
        x0, y0, words = _split_center(opts["words"])
        try:
            timeout = float(opts.get("--timeout", DEFAULT_TIMEOUT))
        except ValueError:
            raise UsageError("--timeout needs a number of seconds") \
                from None
        with tempfile.TemporaryDirectory(prefix="elliprof-") as tmp:
            tmp = Path(tmp)
            result = run_elliprof(
                opts["image"], x0, y0, mask=opts.get("--mask"),
                sky=opts.get("--sky"), sky_image=opts.get("--sky-image"),
                extra=words, output_dir=tmp,
                prf_path=opts.get("-o") or tmp / "p.prf",
                csv_path=opts.get("--csv") or tmp / "p.csv",
                reg_path=opts.get("--reg") or tmp / "p.reg",
                model_path=opts.get("-m"), prepared=opts.get("--prepared"),
                model_harmonics=opts.get("--model-harmonics"),
                harmonic_mode=opts.get("--harmonic-mode"),
                sixth_order=opts.get("sixth-order", False),
                timeout=timeout, check=False, load_profile=False)
            sys.stdout.write(result.stdout)
            sys.stderr.write(result.stderr)
            return result.returncode
    except UsageError as exc:
        print(f"elliprof: error: {exc}", file=sys.stderr)
        return 2
    except ElliprofTimeoutError as exc:
        print(f"elliprof: error: {exc}", file=sys.stderr)
        print("command: " + " ".join(exc.command), file=sys.stderr)
        return 124
    except (ValueError, FileNotFoundError, ElliprofError) as exc:
        print(f"elliprof: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
