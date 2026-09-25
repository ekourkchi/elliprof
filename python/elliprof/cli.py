"""The ``elliprof`` command.

Same syntax as the native backend, plus automatic, physical and RA/DEC
centres::

    elliprof image.fits [KEY=value ...] [X0=x Y0=y |
                        --center-physical X Y | --center-radec RA DEC]
                        [--sky V | --sky-image F] [--mask F]
                        [-o out.prf] [--csv out.csv] [--reg out.reg]
                        [-m model.fits]

The chosen centre is converted to ELLIPROF's X0/Y0 and passed to the
compiled backend together with everything else.
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from ._version import __version__

USAGE = """\
usage: elliprof image.fits [KEY=value ...] [options]

Fit elliptical isophotes (MONSTA's ELLIPROF) to a FITS image.

Fit parameters (ELLIPROF keywords, case-insensitive):
  R0=r R1=r NR=n       inner/outer semi-major axis and number of isophotes
                       (required)
  NITER=n RLAW=k LINEAR FIXCTR=k ELLIP=e SCALE=s RMSTAR COS3X=k COS4X=k
  TIE=k AVG=n GAIN=g GC VERBOSE MODEL SKY=s (SKY= only affects ELLIPROF's
  de Vaucouleurs fit; use --sky to subtract the background)

Centre (default: the geometric image centre):
  X0=x Y0=y                    ELLIPROF image coordinates
  --center-physical X Y        IRAF/DS9 physical coordinates (LTV/LTM)
  --center-radec RA DEC        celestial, via the FITS WCS; decimal degrees
                               or sexagesimal (12:34:56.7 -12:34:56)

Preprocessing (in this order):
  --sky V | --sky-image F      subtract a constant or an image
  --mask F                     then multiply by a mask (0 = masked,
                               1 = good; MONSTA BITPIX=1 .dmask files OK)
  --sc V                       deprecated alias for --sky

Output:
  -o out.prf                   MONSTA-compatible profile
  --csv out.csv                commented, fixed-width CSV profile
  --reg out.reg                fitted ellipses as a DS9 region file
  -m model.fits                model image (with MODEL)
  --prepared F                 the image after sky and mask (diagnostic)

Other:
  --version                    versions of elliprof and its backend
  --diagnostics                environment report for bug reports
  -h, --help                   this help
"""

VALUE_OPTS = {"--mask", "--sky", "--sc", "--sky-image", "-o", "--prf",
              "--csv", "--reg", "-m", "--prepared"}
PAIR_OPTS = {"--center-physical", "--center-radec"}


class UsageError(Exception):
    pass


def _parse(argv: List[str]) -> dict:
    opts = {"words": [], "image": None}
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg in ("-h", "--help", "--version", "--diagnostics"):
            opts[arg.lstrip("-")] = True
            i += 1
        elif arg in VALUE_OPTS:
            if i + 1 >= len(argv):
                raise UsageError(f"{arg} needs a value")
            key = {"--sc": "--sky", "--prf": "-o"}.get(arg, arg)
            if arg == "--sc":
                print("elliprof: --sc is deprecated, use --sky",
                      file=sys.stderr)
            if key in opts:
                raise UsageError(f"{arg} given more than once")
            opts[key] = argv[i + 1]
            i += 2
        elif arg in PAIR_OPTS:
            if i + 2 >= len(argv):
                raise UsageError(f"{arg} needs two values")
            if arg in opts:
                raise UsageError(f"{arg} given more than once")
            opts[arg] = (argv[i + 1], argv[i + 2])
            i += 3
        elif arg.startswith("-"):
            raise UsageError(f"unknown option {arg}")
        elif opts["image"] is None:
            opts["image"] = arg
            i += 1
        else:
            opts["words"].append(arg)
            i += 1
    return opts


def _split_center(words: List[str]):
    """Take X0=/Y0= out of the ELLIPROF words."""
    found, rest = {}, []
    for w in words:
        key = w.split("=", 1)[0].upper()
        if key in ("X0", "Y0") and "=" in w:
            try:
                found[key] = float(w.split("=", 1)[1])
            except ValueError:
                raise UsageError(f"{w}: X0/Y0 must be numbers") from None
        else:
            rest.append(w)
    if len(found) == 1:
        raise UsageError("X0= and Y0= must be given together")
    return ((found["X0"], found["Y0"]) if found else None), rest


def main(argv: Optional[List[str]] = None) -> int:
    argv = sys.argv[1:] if argv is None else list(argv)
    try:
        opts = _parse(argv)
    except UsageError as exc:
        print(f"elliprof: error: {exc}", file=sys.stderr)
        return 2
    if opts.get("help"):
        print(USAGE, end="")
        return 0
    if opts.get("version"):
        from .diagnostics import diagnostics
        info = diagnostics()
        print(f"elliprof {__version__}")
        print(info.get("backend version", info.get("native backend")))
        return 0
    if opts.get("diagnostics"):
        from .diagnostics import diagnostics, format_diagnostics
        print(format_diagnostics(diagnostics()))
        return 0
    if opts["image"] is None:
        print(USAGE, end="", file=sys.stderr)
        return 2

    from .core import ElliprofError, run_elliprof
    try:
        center, words = _split_center(opts["words"])
        sky = opts.get("--sky")
        if sky is not None:
            try:
                float(sky)
            except ValueError:
                raise UsageError(f"--sky needs a number, got {sky}") \
                    from None
        with tempfile.TemporaryDirectory(prefix="elliprof-") as tmp:
            tmp = Path(tmp)
            result = run_elliprof(
                opts["image"], mask=opts.get("--mask"), sky=sky,
                sky_image=opts.get("--sky-image"), center=center,
                center_physical=opts.get("--center-physical"),
                center_radec=opts.get("--center-radec"), extra=words,
                output_dir=tmp, prf_path=opts.get("-o") or tmp / "p.prf",
                csv_path=opts.get("--csv") or tmp / "p.csv",
                reg_path=opts.get("--reg") or tmp / "p.reg",
                model_path=opts.get("-m"), prepared=opts.get("--prepared"),
                check=False)
            print(result.center_info.describe())
            sys.stdout.write(result.stdout)
            sys.stderr.write(result.stderr)
            return result.returncode
    except UsageError as exc:
        print(f"elliprof: error: {exc}", file=sys.stderr)
        return 2
    except (ValueError, FileNotFoundError, ElliprofError) as exc:
        print(f"elliprof: error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
