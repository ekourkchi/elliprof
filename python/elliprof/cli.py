"""The ``elliprof`` command.

    elliprof image.fits X0=x Y0=y R0=r R1=r NR=n [KEY=value ...] [options]

``elliprof``, ``-h``/``--help`` and ``-v``/``--version`` are answered
before anything heavy is imported (no numpy, pandas or backend), so they
work even in a Python environment with broken optional packages.  A fit
never imports pandas either.
"""

import re
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

COMMON WORKFLOW
  elliprof n1234j.fits RMSTAR X0=514 Y0=514 R0=10 R1=450 NR=25 NITER=5 \\
      -o n1234.dat -m n1234.prf --residual n1234_resid.fits

  -o FILE           write the profile: a text table, one row per isophote
                    (traditionally named .dat)
  -m FILE           compute the 2-D galaxy model and write it as a FITS
                    image (traditionally named .prf).  Nothing else is
                    needed: no MODEL keyword.
  --residual FILE   write mask x (science - sky - model) as a FITS image
  --mask FILE       mask: 0 or NaN = bad, any other value = good (default)
  --mask-convention zero-good
                    read the mask the other way: 0 = good, nonzero = bad
  NITER=n, --niter n
                    number of fitting iterations (default 5)
  File names are your choice; extensions are never checked or added.

  Keywords (KEY=value, case-insensitive) and options may follow the image in
  any order.  Output is a short summary (inputs, notes, files written); the
  profile table is printed only if neither -o nor --csv is given.

INPUT IMAGE AND INITIAL CENTRE
  IMAGE.fits    2-D FITS image of the galaxy (the first argument), stored
                with any BITPIX: 8, 16, 32, 64 (integers) or -32, -64
                (floating point).  It is read in the precision of the
                backend (see --precision): 32-bit floats for single, 64-bit
                for double.  An image in
                an extension is chosen with CFITSIO syntax, quoted for the
                shell:  'galaxy.fits[SCI]'  'galaxy.fits[1]'.  The selected
                HDU is fitted; there is no fallback to another.
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
  NITER=n       number of iterations (default 5, at most 1000); --niter n
                is the same.  One iteration visits every isophote once: it
                samples the image along the current ellipse (up to 360
                points), fits the intensity around it with harmonics of
                orders 0-4, and moves the centre, ellipticity and position
                angle so that the ellipse follows the isophote; the slopes
                are then updated.  Increase NITER if the parameters are
                still changing between the last iterations (e.g. with a
                poor starting centre).
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
  --mask FILE        a logical mask, read by default as:
                       0                          = bad / excluded
                       any other finite value     = good / kept
                         (1, 2, -1, 0.5, ...)
                       NaN, Inf, undefined (BLANK) = bad
                     Values are never weights: bad pixels become exactly 0,
                     good pixels keep their value.  Accepted: FITS images of
                     any BITPIX (8, 16, 32, 64, -32, -64) and legacy
                     BITPIX=1 .dmask bitmaps (historical ELLIPROF data),
                     recognised from the file itself.  Exactly the same
                     dimensions as the image.
  --mask-convention nonzero-good|zero-good
                     how the mask's values are read.  nonzero-good (the
                     default) is the rule above.  zero-good is the opposite
                     convention:
                       0                          = good / kept
                       any nonzero value          = bad / excluded
                       NaN, Inf, undefined (BLANK) = bad
                     A legacy .dmask bitmap always means 1 = good and is
                     refused with zero-good.
  --nonfinite auto|mask|keep|error
                     science pixels that are NaN or +-Inf after the sky and
                     the mask (e.g. no-data regions): mask excludes them like
                     masked pixels; keep passes them on, as before 0.2.0, with
                     a warning; error refuses the image.  auto (default):
                     keep with --precision single (historical reproduction),
                     mask otherwise.
  --mask and --sky-image may also select an HDU: 'products.fits[MASK]'.
  --sc VALUE         deprecated alias of --sky; use --sky.
  SKY=s              ELLIPROF's own sky level, used ONLY in the de Vaucouleurs
                     fit it prints at the end; it does not change the image or
                     the profile (use --sky for that).
  Images are never resized, interpolated, cropped, shifted or reprojected.

MODEL AND HARMONIC CONTROLS
  -m FILE            compute a 2-D model image of the galaxy from the fitted
                     isophotes and write it as FITS.  The model follows the
                     fitted intensity, centre, ellipticity and position
                     angle with radius, plus the harmonic terms chosen
                     below; it is relative to the subtracted sky and covers
                     masked pixels too.  The model is computed after the
                     fit, so it never changes the profile.
  --residual FILE    mask x (science - sky - model): what the smooth model
                     does not describe (dust, disks, shells, tidal
                     features, ...); exactly 0 on masked pixels.  Uses the
                     same model as -m (-m is optional).
  MODEL              no longer needed and ignored (kept so that old
                     commands still run); -m FILE writes the model.
                     MODEL=value is an error.
  Every isophote is fitted with a constant plus cos/sin of 1, 2, 4 and 3
  (or, with --sixth-order, 6) times the eccentric angle around the
  ellipse, all at once.  Orders 1-2 move the ellipse; the 3rd/6th and 4th
  orders are measured (I3 A3 I4 A4) and do not move it.
  --model-harmonics none|3|4|3,4
                     which measured terms go into the model image (and so
                     the residual); default 3,4.  This never changes the
                     fitted profile.  With --sixth-order: none|6|4|4,6.
  --harmonic-mode each|median
                     each: every isophote's own terms (default); median: the
                     median of each term over all isophotes.
  --sixth-order      measure the 6th-order term INSTEAD of the 3rd.  I3/A3
                     then hold the 6th-order amplitude and TWICE its phase
                     (there are no I6/A6 columns).  The fit can change a
                     little where ellipses are poorly sampled.  Known
                     original limitations of a 6th-order MODEL: its sign is
                     wrong beyond a fitted PA wrap across 0/180 deg (a
                     warning says so), and a few central pixels can be NaN.
                     --sixth-order --model-harmonics none (COS3X=-3)
                     measures the 6th order without modelling it.
  Default: the same as COS3X=2 COS4X=2.  Full explanation:
  https://ekourkchi.github.io/elliprof/concepts/harmonics/

OUTPUT FILES
  -o FILE        the profile in ELLIPROF's native text format, full
                 precision (traditionally n1234.dat).  A table of numbers
                 (one set of values per isophote, plus the run settings),
                 NOT an image.
  --csv FILE     the same profile as a commented, comma-separated table, one
                 row per isophote (columns below).
  --reg FILE     the fitted ellipses as a DS9 region file, to overlay on the
                 image:  ds9 IMAGE.fits -regions FILE
  -m FILE        the 2-D model image, FITS (traditionally n1234.prf).
  --residual FILE  mask x (science - sky - model), FITS.
  --prepared FILE  mask x (science - sky), FITS: the image exactly as
                 ELLIPROF fits it.
  The model, residual and prepared images are floating-point FITS (32-bit
  from the single backend, 64-bit from the double one) with the header of
  the selected science HDU (WCS, BUNIT, ...), so they overlay the science
  image exactly in DS9 and other WCS-aware software.

PRECISION
  --precision auto|single|double
                 the backend.  single: the original ELLIPROF, in 32-bit
                 floating point.  double: its port to IEEE-754 double
                 precision throughout (reading, sky, fit, model, products;
                 64-bit products, profile values with 18 digits).
                 auto (default): double only when single cannot hold the
                 data -- a science or sky image stored with BITPIX 64 or
                 -64, or values (after BSCALE/BZERO, or the sky) beyond the
                 float32 range or nonzero but 0 in float32; otherwise
                 single.  The summary says which ran and why.  GC needs
                 single.

PROFILE COLUMNS (-o, --csv)
  Rmaj    semi-major axis a of the isophote [pixels]
  x0 y0   fitted centre of this isophote [pixels, same coordinates as X0,Y0]
  I0      intensity level of the isophote [image units, after the sky]
  alpha   position angle of the major axis [deg, 0-180], counter-clockwise
          from the +y axis (i.e. from +x it is alpha + 90)
  ellip   ellipticity 1 - b/a
  I3 I4   amplitude of the 3rd/4th-order intensity variation around the
          isophote, as a fraction of I0 (dimensionless)
  A3 A4   their phases [deg] in the eccentric angle around the ellipse,
          from the end of the major axis at angle alpha: intensity ~
          1 + In cos(n (theta - An)); A3 0-120, A4 0-90.  They are NOT
          position angles.  With --sixth-order (COS3X < 0) I3 is the
          6th-order amplitude and A3 twice the 6th-order phase.
  slope   logarithmic slope d ln I / d ln r from the neighbouring isophotes
          (set to -2 where it would be positive)
  Boxy/disky: A4 near 0 or 90 deg = disky, A4 near 45 deg = boxy.  I4 is an
  intensity amplitude, not a4/a or B4 (see the README for the conversion).

LEGACY ELLIPROF CONTROLS (the original concise interface, fully supported)
  COS3X=k       sign = the order measured, |k| = its use in the model:
                   2  measure 3rd, model each isophote's term (default)
                   1  measure 3rd, model the median term
                   0  measure 3rd, not in the model
                  -2  measure 6th, model each isophote's term
                  -1  measure 6th, model the median term
                  -3  measure 6th, not in the model (the original code
                      does this for COS3X <= -3; -3 is the supported value)
  COS4X=k       the 4th order is always measured:
                   2  model each isophote's term (default)
                   1  model the median term
                   0  not in the model
  Use either COS3X/COS4X or the options above, not both.  The options
  set both values at once, e.g. --model-harmonics none = COS3X=0
  COS4X=0, --model-harmonics 4 = COS3X=0 COS4X=2, --harmonic-mode median
  = COS3X=1 COS4X=1, --sixth-order --model-harmonics none = COS3X=-3
  COS4X=0.  The interactive
  options OLD, EDIT and TV are not supported.

DIAGNOSTICS AND RUNTIME OPTIONS
  --timeout SECONDS  maximum run time of the fit (default 1800).  A safety
                     limit, not a fitting parameter: the backend and its child
                     processes are stopped, temporary files removed, and
                     elliprof exits with status 124.
  --verbose          show ELLIPROF's full output: iteration tables, model
                     progress, every message.  (The legacy keyword VERBOSE
                     keeps its meaning -- print the parameters after every
                     iteration -- and also shows the full output.)
  --diagnostics      report for support: versions, Python, OS/macOS,
                     architecture, backend location, architecture, minimum
                     macOS and version, and the numpy/pandas versions.
  -v, --version      version, original developer and maintainer.
  -h, --help         this help.

UPDATES
  --check-update     ask PyPI whether a newer elliprof exists; installs
                     nothing.
  -u, --update       install the newest elliprof from PyPI with this
                     Python's pip (python -m pip install --upgrade).  Not
                     for a source checkout or editable install.
  After a fit in an interactive terminal, elliprof checks PyPI at most once
  a day, in the background, and prints one line if a newer version exists.
  It never installs anything by itself, never delays the fit, and is
  silent offline and in scripts.  Set ELLIPROF_NO_UPDATE_CHECK=1 to turn
  the check off.

EXAMPLES
  Profile, model and residual (traditional names):
    elliprof n1234j.fits RMSTAR X0=514 Y0=514 R0=10 R1=450 NR=25 NITER=5 \\
        -o n1234.dat -m n1234.prf --residual n1234_resid.fits

  Profile as text, CSV and DS9 regions:
    elliprof galaxy.fits X0=500 Y0=500 R0=5 R1=200 NR=30 \\
        -o galaxy.dat --csv galaxy.csv --reg galaxy.reg

  Constant sky and a mask:
    elliprof galaxy.fits --sky 1234.5 --mask galaxy_mask.fits \\
        X0=500 Y0=500 R0=5 R1=200 NR=30 -o galaxy.dat

  A mask where 0 = good and nonzero = bad (e.g. a segmentation map):
    elliprof galaxy.fits --mask segmap.fits --mask-convention zero-good \\
        X0=500 Y0=500 R0=5 R1=200 NR=30 -o galaxy.dat

  Sky image; model with the 4th-order (boxy/disky) term only:
    elliprof galaxy.fits --sky-image background.fits \\
        X0=500 Y0=500 R0=5 R1=200 NR=30 -m galaxy.prf --model-harmonics 4

  3rd and 4th order in the model, median over radii; 10 iterations:
    elliprof galaxy.fits X0=500 Y0=500 R0=5 R1=200 NR=30 --niter 10 \\
        -m galaxy.prf --model-harmonics 3,4 --harmonic-mode median

  6th-order fit:
    elliprof galaxy.fits X0=500 Y0=500 R0=5 R1=200 NR=30 --sixth-order

  Image in an extension; model, prepared image and residual:
    elliprof 'galaxy.fits[SCI]' --mask galaxy_mask.fits --sky 1234.5 \\
        X0=500 Y0=500 R0=5 R1=200 NR=30 -o galaxy.dat -m galaxy.prf \\
        --prepared galaxy_prepared.fits --residual galaxy_residual.fits

{credit}
Maintained by {maintainer}   Email: {email}
Documentation: https://ekourkchi.github.io/elliprof/
"""

# kept for callers of the old module attribute
USAGE = HELP

VALUE_OPTS = {"--mask", "--sky", "--sc", "--sky-image", "-o", "--csv",
              "--reg", "-m", "--prepared", "--residual", "--timeout",
              "--model-harmonics", "--harmonic-mode", "--mask-convention",
              "--niter", "--precision", "--nonfinite"}
FLAG_OPTS = {"-h": "help", "--help": "help", "-v": "version",
             "--version": "version", "--diagnostics": "diagnostics",
             "-u": "update", "--update": "update",
             "--check-update": "check-update",
             "--sixth-order": "sixth-order", "--verbose": "verbose"}


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


# Lines of the backend's standard output (its own summary lines, and
# messages of the unchanged ELLIPROF routines) used by the short summary
_IMAGE = re.compile(r":\s+(\d+) cols x\s+(\d+) rows")
_SKY = re.compile(r"^\s*Sky: subtracted (scalar|image)\s+(.*?)\s*$")
_MASK = re.compile(r"^\s*Mask: (.*) \(BITPIX (-?\d+)\): (\d+) pixels masked"
                   r" \(\s*([\d.]+)%\)")
_NONF = re.compile(r"^\s*Mask: (\d+) of them NaN")
_NONFIN = re.compile(r"^\s*Non-finite: policy (.*?); NaN (\d+), \+Inf "
                     r"(\d+), -Inf (\d+); masked (\d+)")
_UNDER = re.compile(r"^\s*Model: (\d+) pixels underflowed to zero")
_BITPIX64 = re.compile(r"^\s*Image: BITPIX (-?64) converted")
_PREC = re.compile(r"^\s*Precision: (single|double) .*?; requested (\w+)"
                   r"(?: \(auto: (.*)\))?\s*$")
_NORM = re.compile(r"Normalization: fit on image x 2\*\*\(-k\), "
                   r"k = (-?\d+)")
_NOTES = (
    ("FITCONTOUR: quitting",
     "{n} isophote fit(s) had too few usable samples along the ellipse "
     "(e.g. inside a masked region) and kept their previous parameters"),
    ("dlogI/dlogr forced to -2",
     "the intensity slope was not decreasing at {n} isophote(s) and was "
     "set to -2"),
    ("GETCONTOUR: omitted",
     "{n} sample(s) were skipped because their AVG box was mostly masked"),
    ("set to 0",
     "{n} model pixel(s) were out of range and set to 0"),
)


def _summary(result, opts: dict, nr: str = "") -> None:
    """The short report of a successful fit: inputs, notes (stderr),
    files written.  The profile table is shown only if no profile file
    was asked for."""
    out = result.stdout.splitlines()
    image = str(opts["image"])
    size = next((m for m in map(_IMAGE.search, out) if m), None)
    b64 = next((m for m in map(_BITPIX64.match, out) if m), None)
    print("Image:    " + image + (f" ({size.group(1)} x {size.group(2)})"
                                   if size else "")
          + (f", BITPIX {b64.group(1)} read as 32-bit float" if b64
             else ""))
    prec = next((m for m in map(_PREC.match, out) if m), None)
    if prec:
        how = f"auto: {prec.group(3)}" if prec.group(3) else "requested"
        norm = next((m for m in map(_NORM.search, out) if m), None)
        if norm:
            how += f"; fit on image x 2**-k, k = {norm.group(1)}"
        print(f"Precision: {prec.group(1)} ({how})")
    if opts.get("--sky") is not None:
        print("Sky:      scalar " + str(opts["--sky"]).strip())
    elif opts.get("--sky-image"):
        print("Sky:      image " + str(opts["--sky-image"]))
    else:
        print("Sky:      none")
    mask = next((m for m in map(_MASK.match, out) if m), None)
    if mask:
        nonf = next((m for m in map(_NONF.match, out) if m), None)
        extra = f", {nonf.group(1)} of them NaN/Inf/undefined" if nonf \
            else ""
        conv = opts.get("--mask-convention", "nonzero-good")
        print(f"Mask:     {opts['--mask']} - {mask.group(3)} pixels masked "
              f"({float(mask.group(4)):.3f}%){extra}; {conv}")
    else:
        print("Mask:     none")
    nf = next((m for m in map(_NONFIN.match, out) if m), None)
    if nf and any(int(g) for g in nf.groups()[1:4]):
        print(f"Non-finite: NaN {nf.group(2)}, +Inf {nf.group(3)}, -Inf "
              f"{nf.group(4)}; {nf.group(5)} masked (policy "
              f"{nf.group(1)})")
    if "SURFACE PHOTOMETRY PROFILE COMPUTATION:" in result.stdout:
        table = result.stdout.split(
            "SURFACE PHOTOMETRY PROFILE COMPUTATION:", 1)[1]
        rows = [l for l in table.splitlines() if l.strip()]
        print("Fit complete: %d isophotes." % max(0, len(rows) - 1))
        print("\n".join(rows))
    elif nr:
        print(f"Fit complete: {nr} isophotes.")
    else:
        print("Fit complete.")
    under = next((m for m in map(_UNDER.match, out) if m), None)
    if under:
        print(f"Model: {under.group(1)} pixels underflowed to zero at "
              "double precision.")
    sys.stdout.flush()
    for text, note in _NOTES:
        n = sum(text in l for l in out)
        if n:
            print("elliprof: note: " + note.format(n=n), file=sys.stderr)
    sys.stderr.write(result.stderr)
    sys.stderr.flush()
    for label, key in (("Profile", "-o"), ("CSV", "--csv"),
                       ("Regions", "--reg"), ("Model", "-m"),
                       ("Prepared", "--prepared"),
                       ("Residual", "--residual")):
        if opts.get(key):
            print(f"{label + ':':<9} {opts[key]}")
    print("Done.")


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
    if opts.get("check-update") or opts.get("update"):
        from . import update
        return update.update() if opts.get("update") \
            else update.check_update()
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
        if "--niter" in opts:
            if any(w.partition("=")[0].strip().upper() == "NITER"
                   and w.partition("=")[1] for w in words):
                raise UsageError("give the iteration count once: NITER= "
                                 "or --niter")
            words.append("NITER=" + opts["--niter"].strip())
        conv = opts.get("--mask-convention", "nonzero-good")
        if conv not in ("nonzero-good", "zero-good"):
            raise UsageError("--mask-convention must be nonzero-good or "
                             f"zero-good, not {conv!r}")
        if "--mask-convention" in opts and "--mask" not in opts:
            raise UsageError("--mask-convention needs --mask")
        nonfinite = opts.get("--nonfinite", "auto")
        if nonfinite not in ("auto", "mask", "keep", "error"):
            raise UsageError("--nonfinite must be auto, mask, keep or "
                             f"error, not {nonfinite!r}")
        precision = opts.get("--precision", "auto")
        if precision not in ("auto", "single", "double"):
            raise UsageError("--precision must be auto, single or double, "
                             f"not {precision!r}")
        try:
            timeout = float(opts.get("--timeout", DEFAULT_TIMEOUT))
        except ValueError:
            raise UsageError("--timeout needs a number of seconds") \
                from None
        # --verbose, or ELLIPROF's own VERBOSE keyword: everything the
        # backend prints; otherwise a short summary
        raw = opts.get("verbose", False) or any(
            w.strip().upper() == "VERBOSE" for w in words)
        nr = [w.partition("=")[2].strip() for w in words
              if w.partition("=")[0].strip().upper() == "NR"]
        with tempfile.TemporaryDirectory(prefix="elliprof-") as tmp:
            kwargs = dict(
                mask=opts.get("--mask"), sky=opts.get("--sky"),
                sky_image=opts.get("--sky-image"), extra=words,
                output_dir=Path(tmp), prf_path=opts.get("-o"),
                csv_path=opts.get("--csv"), reg_path=opts.get("--reg"),
                model_path=opts.get("-m"), prepared=opts.get("--prepared"),
                residual_path=opts.get("--residual"),
                model_harmonics=opts.get("--model-harmonics"),
                harmonic_mode=opts.get("--harmonic-mode"),
                sixth_order=opts.get("sixth-order", False),
                mask_convention=conv, precision=precision,
                nonfinite=nonfinite,
                timeout=timeout, check=False, load_profile=False,
                default_outputs=False,
                backend_verbose=opts.get("verbose", False))
            from .update import finish_notice, start_notice
            notice = start_notice()
            if not raw:
                print(f"elliprof {__version__}")
                print(f"Fitting {nr[-1]} isophotes..." if nr
                      else "Fitting...")
                sys.stdout.flush()
            result = run_elliprof(opts["image"], x0, y0, **kwargs)
            if raw or result.returncode != 0:
                # everything the backend said: on request, and always
                # when it failed, so that no error is ever hidden
                sys.stdout.write(result.stdout)
                sys.stdout.flush()
                sys.stderr.write(result.stderr)
            else:
                _summary(result, opts, nr[-1] if nr else "")
            if result.returncode == 0:
                finish_notice(notice)
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
