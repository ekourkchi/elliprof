"""The Python API: :func:`run_elliprof`.

The fit runs in the compiled backend (``elliprof_native``) in a
separate process; this module only validates the inputs, turns the
chosen centre into ELLIPROF's ``X0``/``Y0``, builds the command line
and reads the results back.
"""

from __future__ import annotations

import math
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple, Union

import pandas as pd

from ._native import find_backend
from ._version import __version__
from .coordinates import Center, resolve_center
from .io import check_same_geometry, read_header
from .profile import read_profile

PathLike = Union[str, os.PathLike]

NCON = 16  # ELLIPROF reads at most 16 keywords (vistalink.inc)
UNSUPPORTED = {"OLD": "needs a previous profile in memory",
               "EDIT": "edits a previous profile interactively"}


class ElliprofError(RuntimeError):
    """The fit failed; ``.result`` holds the backend's output."""

    def __init__(self, message: str, result: "ElliprofResult" = None):
        super().__init__(message)
        self.result = result


@dataclass
class ElliprofResult:
    profile: Optional[pd.DataFrame]
    prf_path: Optional[Path]
    csv_path: Optional[Path]
    reg_path: Optional[Path]
    model_path: Optional[Path]
    stdout: str
    stderr: str
    returncode: int
    center: Tuple[float, float]
    center_source: str
    command: List[str]
    version: str = __version__
    backend_path: Optional[Path] = None
    output_dir: Optional[Path] = None
    prepared_path: Optional[Path] = None
    center_info: Optional[Center] = None

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _num(value) -> str:
    """Format a number for ELLIPROF: integers stay integers, floats keep
    full precision (the backend parses them like MONSTA)."""
    if isinstance(value, bool):
        raise TypeError("expected a number, got a bool")
    if isinstance(value, int):
        return str(value)
    value = float(value)
    if not math.isfinite(value):
        raise ValueError(f"not a finite number: {value}")
    return repr(value)


def elliprof_keywords(*, r0=None, r1=None, nr=None, niter=None, rlaw=None,
                      linear=False, fixctr=None, ellip=None, scale=None,
                      elliprof_sky=None, model=False, rmstar=False,
                      cos3x=None, cos4x=None, tie=None, avg=None, gain=None,
                      gc=False, verbose=False, extra: Iterable[str] = ()
                      ) -> List[str]:
    """ELLIPROF keyword words (without X0/Y0) for the given options."""
    words = []
    for key, value in (("R0", r0), ("R1", r1), ("NR", nr), ("NITER", niter),
                       ("RLAW", rlaw), ("FIXCTR", fixctr), ("ELLIP", ellip),
                       ("SCALE", scale), ("SKY", elliprof_sky),
                       ("COS3X", cos3x), ("COS4X", cos4x), ("TIE", tie),
                       ("AVG", avg), ("GAIN", gain)):
        if value is not None:
            words.append(f"{key}={_num(value)}")
    for key, flag in (("LINEAR", linear), ("MODEL", model),
                      ("RMSTAR", rmstar), ("GC", gc), ("VERBOSE", verbose)):
        if flag:
            words.append(key)
    words.extend(str(w) for w in extra)
    return words


def _word_key(word: str) -> str:
    return word.split("=", 1)[0].strip().upper()


def validate_keywords(words: Sequence[str]) -> None:
    keys = [_word_key(w) for w in words]
    for key, why in UNSUPPORTED.items():
        if key in keys:
            raise ValueError(f"{key} is not supported: it {why}, which "
                             "elliprof cannot load yet")
    if "X0" in keys or "Y0" in keys:
        raise ValueError("give the centre with center=(x, y), not X0=/Y0=")
    if "GC" in keys:
        if "NR" not in keys:
            raise ValueError("GC needs nr")
    else:
        missing = [k for k in ("R0", "R1", "NR") if k not in keys]
        if missing:
            raise ValueError("missing required fit parameters: " +
                             ", ".join(k.lower() for k in missing))
    if len(words) + 2 > NCON:
        raise ValueError(f"ELLIPROF accepts at most {NCON} keywords "
                         f"including X0 and Y0; got {len(words) + 2}")


def _require_file(path, what):
    if not Path(path).is_file():
        raise FileNotFoundError(f"{what} not found: {path}")


def run_elliprof(image: PathLike, *, mask: Optional[PathLike] = None,
                 sky: Optional[float] = None,
                 sky_image: Optional[PathLike] = None,
                 center=None, center_physical=None, center_radec=None,
                 r0=None, r1=None, nr=None, niter=None, rlaw=None,
                 linear=False, fixctr=None, ellip=None, scale=None,
                 elliprof_sky=None, model=False, rmstar=False, cos3x=None,
                 cos4x=None, tie=None, avg=None, gain=None, gc=False,
                 verbose=False, extra: Iterable[str] = (),
                 output_dir: Optional[PathLike] = None,
                 prefix: Optional[str] = None,
                 prf_path: Optional[PathLike] = None,
                 csv_path: Optional[PathLike] = None,
                 reg_path: Optional[PathLike] = None,
                 model_path: Optional[PathLike] = None,
                 prepared: Optional[PathLike] = None,
                 check: bool = True, backend: Optional[PathLike] = None,
                 ) -> ElliprofResult:
    """Fit elliptical isophotes to ``image`` with ELLIPROF.

    Preprocessing, in this order: subtract ``sky`` (a number) or
    ``sky_image`` (a FITS image), then multiply by ``mask`` (0 = masked,
    1 = good; MONSTA BITPIX=1 masks supported).

    Centre: ``center=(x, y)`` in ELLIPROF image coordinates,
    ``center_physical=(x, y)`` in IRAF/DS9 physical coordinates, or
    ``center_radec=(ra, dec)`` (degrees, sexagesimal strings, or a
    SkyCoord; needs a FITS WCS).  With none of them the geometric image
    centre is used.

    ``elliprof_sky`` is ELLIPROF's own ``SKY=`` keyword (used only in its
    de Vaucouleurs fit); it is unrelated to ``sky``.

    Output files (.prf, .csv, .reg, and the model FITS with
    ``model=True``) go to ``output_dir`` (a new temporary directory by
    default), named after ``prefix`` (default: the image name), unless
    explicit paths are given.
    """
    image = Path(image)
    _require_file(image, "image")
    header = read_header(str(image))
    if sky is not None and sky_image is not None:
        raise ValueError("give either sky or sky_image, not both")
    if sky is not None:
        if isinstance(sky, str):
            # passed through verbatim, parsed by the backend like MONSTA
            try:
                float(sky)
            except ValueError:
                raise ValueError(f"sky must be a number, got {sky!r}") \
                    from None
            sky_arg = sky.strip()
        else:
            sky_arg = _num(sky)
    if sky_image is not None:
        _require_file(sky_image, "sky image")
        check_same_geometry(str(image), str(sky_image), "sky image")
    if mask is not None:
        _require_file(mask, "mask")
        check_same_geometry(str(image), str(mask), "mask")

    words = elliprof_keywords(
        r0=r0, r1=r1, nr=nr, niter=niter, rlaw=rlaw, linear=linear,
        fixctr=fixctr, ellip=ellip, scale=scale, elliprof_sky=elliprof_sky,
        model=model, rmstar=rmstar, cos3x=cos3x, cos4x=cos4x, tie=tie,
        avg=avg, gain=gain, gc=gc, verbose=verbose, extra=extra)
    validate_keywords(words)
    ctr = resolve_center(header, center=center,
                         center_physical=center_physical,
                         center_radec=center_radec)

    out = Path(output_dir) if output_dir is not None else \
        Path(tempfile.mkdtemp(prefix="elliprof-"))
    out.mkdir(parents=True, exist_ok=True)
    stem = prefix or image.name.split(".")[0]
    prf = Path(prf_path) if prf_path else out / f"{stem}.prf"
    csv = Path(csv_path) if csv_path else out / f"{stem}.csv"
    reg = Path(reg_path) if reg_path else out / f"{stem}.reg"
    if model_path is not None:
        mdl = Path(model_path)
    elif model:
        mdl = out / f"{stem}_model.fits"
    else:
        mdl = None

    exe = Path(backend) if backend else find_backend()
    cmd = [str(exe), str(image.resolve()),
           f"X0={_num(ctr.x0)}", f"Y0={_num(ctr.y0)}", *words]
    if sky is not None:
        cmd += ["--sky", sky_arg]
    if sky_image is not None:
        cmd += ["--sky-image", str(Path(sky_image).resolve())]
    if mask is not None:
        cmd += ["--mask", str(Path(mask).resolve())]
    cmd += ["--center-source", ctr.source,
            "-o", str(prf.resolve()), "--csv", str(csv.resolve()),
            "--reg", str(reg.resolve())]
    if mdl is not None:
        cmd += ["-m", str(mdl.resolve())]
    if prepared is not None:
        cmd += ["--prepared", str(Path(prepared).resolve())]

    # The backend runs in the output directory, so anything it writes
    # on its own (DUMP= -> fort.2) lands there.
    proc = subprocess.run(cmd, cwd=str(out), capture_output=True, text=True)
    ok = proc.returncode == 0
    result = ElliprofResult(
        profile=read_profile(str(prf)) if ok and not gc else None,
        prf_path=prf if ok and prf.exists() else None,
        csv_path=csv if ok and csv.exists() else None,
        reg_path=reg if ok and reg.exists() else None,
        model_path=mdl if ok and mdl is not None and mdl.exists() else None,
        stdout=proc.stdout, stderr=proc.stderr, returncode=proc.returncode,
        center=(ctr.x0, ctr.y0), center_source=ctr.source, command=cmd,
        backend_path=exe, output_dir=out,
        prepared_path=Path(prepared) if prepared else None,
        center_info=ctr)
    if check and not ok:
        detail = proc.stderr.strip() or proc.stdout.strip()[-2000:]
        raise ElliprofError(f"elliprof failed (exit {proc.returncode}): "
                            f"{detail}", result)
    return result
