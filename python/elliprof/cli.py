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
INTRO = """\
ELLIPROF - Galaxy Isophote Fitting

Fits elliptical isophotes to astronomical galaxy images and measures
radial surface brightness, ellipticity, position angle, and higher-order
isophotal structure.

ELLIPROF is particularly useful for elliptical galaxies and smooth
spheroidal galaxy components.

Maintained by {maintainer}
Email: {email}

Run:

    elliprof -h

for usage, parameters, options, and examples.
"""

VERSION = """\
elliprof {version}
Maintained by {maintainer}
Email: {email}
"""

HELP = """\
ELLIPROF - Galaxy Isophote Fitting (elliprof {version})

Fits a sequence of elliptical isophotes to a galaxy in a FITS image and
measures, for each one, its intensity, centre, ellipticity, position angle,
logarithmic slope and 3rd/4th-order deviations from a pure ellipse.

USAGE
  elliprof IMAGE.fits X0=x Y0=y R0=r R1=r NR=n [KEYWORD=value ...] [options]

  Keywords (KEY=value, case-insensitive) and options may be given in any
  order after the image.

INPUT IMAGE AND CENTRE
  IMAGE.fits    2-D FITS image of the galaxy (first argument).
  X0=x Y0=y     REQUIRED initial galaxy centre, in pixels.  ELLIPROF does
                not find the centre for you; it refines the centre of each
                isophote starting from this one (see FIXCTR).
                Coordinates: the centre of the pixel in FITS column i is at
                x = i - 0.5, i.e. half a pixel less than FITS/DS9 numbering.

RADIAL FITTING PARAMETERS
  R0=r          REQUIRED semi-major axis of the innermost isophote [pixels].
  R1=r          REQUIRED semi-major axis of the outermost isophote [pixels];
                0 < R0 < R1.
  NR=n          REQUIRED number of isophotes from R0 to R1 (2 to 100).
  RLAW=k        spacing of the isophotes: 0 linear, 1 logarithmic,
                2 linear in r^(1/4) (default).
  NITER=n       number of iterations (default 5, at most 1000).  Each
                iteration samples every isophote once (at up to 360 points),
                fits the intensity along it, and moves its centre, ellipticity
                and position angle towards the isophote.
  RMSTAR        reject star-like points: along each ellipse, samples brighter
                than median + 4 x (upper quartile - median) are ignored.  Only
                bright outliers are rejected, one point at a time; mask larger
                contaminants (--mask) instead.
  FIXCTR=k      0 free centre for every isophote (default), 1 all centres
                fixed at X0/Y0, 2 all centres set to the median centre.
  ELLIP=e       hold the ellipticity fixed at e (default: fitted).
  LINEAR        fit intensities instead of log intensities (default: log).
  TIE=k         k >= 0: smooth the parameters with radius by a polynomial of
                order k in r^(1/4); k < -1: running binomial average over |k|
                isophotes; -1 (default): no smoothing.
  AVG=n         sample the image as a weighted (2n+1) x (2n+1) box average
                instead of bilinear interpolation (default 0).
  GAIN=g        step size of each iteration (default 1).
  SCALE=s       image scale [arcsec/pixel], recorded in the profile.
  GC            globular-cluster mode: circular annuli around a centre found
                in the image (NR is then required, R0/R1 are not).
  VERBOSE       print the parameters after every iteration.

SKY / BACKGROUND AND MASK   (the image is prepared as (science - sky) x mask)
  --sky VALUE        subtract one constant sky value from every pixel.
  --sky-image FILE   subtract a sky/background image pixel by pixel
                     (science - sky_image); same dimensions as the image.
                     --sky and --sky-image cannot be used together.
  --mask FILE        multiply by a mask: 0 = bad / ignored, 1 = good; same
                     dimensions as the image.  FITS masks and legacy BITPIX=1
                     .dmask bitmaps are accepted.
  --sc VALUE         deprecated alias of --sky.
  SKY=s              ELLIPROF's own sky, used ONLY in its de Vaucouleurs fit
                     printed at the end; it does not change the image.
  Images are never resized, cropped or resampled.  ELLIPROF ignores pixels
  that are exactly 0, so masked pixels drop out of the fit.

HARMONIC / MODEL CONTROLS
  Every isophote is fitted with a constant plus the cos/sin of 1, 2, 3 and 4
  times the angle around the ellipse.  Orders 1-2 move the ellipse; orders 3
  and 4 are always measured (I3 A3 I4 A4) but never change the ellipse.
  The options below choose which measured terms are put into the MODEL image
  (MODEL + -m); they do not change the fitted profile, except --sixth-order.

  --model-harmonics none|3|4|3,4
                     harmonic terms included in the model image
                     (default 3,4).
  --harmonic-mode each|median
                     each: every isophote's own terms (default);
                     median: the median of each term over all isophotes.
  --sixth-order      fit and model the 6th-order term in place of the 3rd.
                     This DOES change the fit; I3/A3 then hold the 6th-order
                     amplitude and twice its phase.  Known original
                     behaviour: with 'each', the model image can have a few
                     NaN pixels at the very centre.

  Default: 3rd and 4th order fitted, each isophote's terms in the model
  (the same as COS3X=2 COS4X=2).

  Profile columns I3, I4: amplitude of the 3rd/4th-order intensity variation
  along the isophote, as a fraction of I0.  A3, A4: their phases [deg] in
  the angle around the ellipse from the major axis (intensity ~
  cos(n (theta - An)); A3 0-120, A4 0-90).  They are NOT the position angle.
  Boxy/disky: A4 near 0 or 90 deg = disky, A4 near 45 deg = boxy.

LEGACY ELLIPROF KEYWORDS
  COS3X=k       original 3rd-order switch: 0 none, 1 median, 2 each isophote
                (default) in the model; -1/-2: 6th order instead of 3rd
                (changes the fit).
  COS4X=k       original 4th-order switch: 0 none, 1 median, 2 each
                (default) in the model; never changes the fit.
  Use either COS3X/COS4X or the options above, not both.  OLD, EDIT and TV
  (interactive options) are not supported.

OUTPUT FILES
  -o FILE        the profile in ELLIPROF's .prf format, full precision.
  --csv FILE     the profile as a commented, comma-separated table: Rmaj x0 y0
                 I0 alpha ellip I3 A3 I4 A4 slope, one row per isophote.
  --reg FILE     the fitted ellipses as a DS9 region file (image coordinates):
                 ds9 IMAGE.fits -regions FILE
  -m FILE        with MODEL: a smooth model image of the galaxy built from the
                 fitted isophotes (relative to the subtracted sky); the
                 harmonic controls above decide what it contains.
  --prepared FILE  write the prepared image (after sky and mask) exactly as
                 ELLIPROF fits it.
  Without -o/--csv/--reg the profile is only printed to the terminal.

GENERAL OPTIONS
  --timeout SECONDS  stop ELLIPROF if it runs longer (default 1800).  The
                     backend and its child processes are terminated, temporary
                     files are removed, and elliprof exits with status 124.
  -v, --version      version and maintainer.
  --diagnostics      version, platform and backend report for bug reports.
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
        MODEL -m model.fits --model-harmonics 4

  3rd and 4th order in the model, median over radii:
    elliprof galaxy.fits X0=500 Y0=500 R0=5 R1=200 NR=30 \\
        MODEL -m model.fits --model-harmonics 3,4 --harmonic-mode median

  6th-order fit:
    elliprof galaxy.fits X0=500 Y0=500 R0=5 R1=200 NR=30 --sixth-order

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
                       email=__email__)


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
