"""The ``elliprof`` command.

    elliprof image.fits X0=x Y0=y R0=r R1=r NR=n [KEY=value ...]
             [--sky V | --sky-image F] [--mask F]
             [-o out.prf] [--csv out.csv] [--reg out.reg] [-m model.fits]
             [--timeout SECONDS]
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path
from typing import List, Optional

from ._version import __maintainer__, __version__

USAGE = """\
usage: elliprof image.fits X0=x Y0=y R0=r R1=r NR=n [KEY=value ...] [options]

Fit elliptical isophotes (ELLIPROF) to a FITS image.

Required:
  X0=x Y0=y            initial centre (ELLIPROF image coordinates: the
                       centre of the pixel in FITS column i is at i - 0.5)
  R0=r R1=r NR=n       inner/outer semi-major axis (0 < R0 < R1) and
                       number of isophotes (2..100)

Optional ELLIPROF keywords (case-insensitive):
  NITER=n RLAW=k LINEAR FIXCTR=k ELLIP=e SCALE=s RMSTAR COS3X=k COS4X=k
  TIE=k AVG=n GAIN=g GC VERBOSE MODEL SKY=s (SKY= only affects ELLIPROF's
  de Vaucouleurs fit; use --sky to subtract the background)

Preparation (in this order):
  --sky V | --sky-image F      subtract a constant or an image of the
                               same size
  --mask F                     then multiply by a mask of the same size
                               (0 = masked, 1 = good; BITPIX=1 .dmask OK)

Output:
  -o out.prf                   profile, full precision
  --csv out.csv                commented, fixed-width CSV profile
  --reg out.reg                fitted ellipses as a DS9 region file
  -m model.fits                model image (with MODEL)

Other:
  --timeout SECONDS            stop ELLIPROF after this long (default 1800)
  --version                    versions of elliprof and its backend
  --diagnostics                environment report for bug reports
  -h, --help                   this help
"""

VALUE_OPTS = {"--mask", "--sky", "--sc", "--sky-image", "-o", "--csv",
              "--reg", "-m", "--prepared", "--timeout"}


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
            key = "--sky" if arg == "--sc" else arg
            if arg == "--sc":
                print("elliprof: --sc is deprecated, use --sky",
                      file=sys.stderr)
            if key in opts:
                raise UsageError(f"{arg} given more than once")
            opts[key] = argv[i + 1]
            i += 2
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
        print(f"elliprof {__version__} (maintained by {__maintainer__})")
        print(info.get("backend version", info.get("native backend")))
        return 0
    if opts.get("diagnostics"):
        from .diagnostics import diagnostics, format_diagnostics
        print(format_diagnostics(diagnostics()))
        return 0
    if opts["image"] is None:
        print(USAGE, end="", file=sys.stderr)
        return 2

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
                timeout=timeout, check=False)
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
