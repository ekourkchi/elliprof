"""The Python API: :func:`run_elliprof`.

The fit runs in the compiled backend (``elliprof_native``) in a
separate process.  This module validates the inputs, builds the command
line, runs the backend with a time limit, and reads the results.
"""

import math
import os
import shutil
import signal
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

import pandas as pd

from ._native import find_backend
from ._version import __version__
from .io import check_same_geometry, image_info
from .profile import read_profile

PathLike = Union[str, os.PathLike]

DEFAULT_TIMEOUT = 1800.0  # seconds
NCON = 16      # ELLIPROF reads at most 16 keywords
NR_MAX = 100   # ELLIPROF's fitting arrays hold at most 100 isophotes
NITER_MAX = 1000
UNSUPPORTED = ("OLD", "EDIT", "TV")  # interactive or stateful options


class ElliprofError(RuntimeError):
    """The fit failed; ``.result`` holds the backend's output."""

    def __init__(self, message: str, result: "ElliprofResult" = None):
        super().__init__(message)
        self.result = result


class ElliprofTimeoutError(ElliprofError):
    """The backend exceeded the time limit and was terminated."""

    def __init__(self, timeout: float, command: List[str]):
        super().__init__(f"ELLIPROF exceeded the {timeout:g}-second "
                         f"timeout and was terminated")
        self.timeout = timeout
        self.command = command


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
    command: List[str]
    center: Tuple[float, float]
    version: str = __version__
    backend_path: Optional[Path] = None
    output_dir: Optional[Path] = None
    prepared_path: Optional[Path] = None

    @property
    def ok(self) -> bool:
        return self.returncode == 0


def _finite(value, name) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a number, got {value!r}")
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ValueError(f"{name} must be a number, got {value!r}") from None
    if not math.isfinite(v):
        raise ValueError(f"{name} must be a finite number, got {value!r}")
    return v


def _num(value) -> str:
    """A number as the backend should read it: integers stay integers,
    floats keep full precision."""
    if isinstance(value, int) and not isinstance(value, bool):
        return str(value)
    return repr(_finite(value, "value"))


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


def _parse_words(words: Sequence[str]) -> Dict[str, Optional[str]]:
    out = {}
    for w in words:
        key, eq, value = w.partition("=")
        out[key.strip().upper()] = value.strip() if eq else None
    return out


def validate_keywords(words: Sequence[str]) -> None:
    """Refuse anything ELLIPROF would handle badly, before it runs."""
    kw = _parse_words(words)
    for key in UNSUPPORTED:
        if key in kw:
            raise ValueError(f"{key} is not supported (interactive or "
                             "stateful option)")
    if "X0" in kw or "Y0" in kw:
        raise ValueError("give the centre as x0=, y0=, not as keywords")
    if len(words) + 2 > NCON:
        raise ValueError(f"ELLIPROF accepts at most {NCON} keywords "
                         f"including X0 and Y0; got {len(words) + 2}")
    gc = "GC" in kw
    need = ("NR",) if gc else ("R0", "R1", "NR")
    missing = [k for k in need if k not in kw]
    if missing:
        raise ValueError("missing required fit parameters: " +
                         ", ".join(missing))
    values = {}
    for key in ("R0", "R1", "NR", "NITER"):
        if key in kw:
            values[key] = _finite(kw[key], key)
    nr = values["NR"]
    if nr != int(nr) or not 2 <= nr <= NR_MAX:
        raise ValueError(f"NR must be an integer between 2 and {NR_MAX}")
    if not gc and not 0 < values["R0"] < values["R1"]:
        raise ValueError("radii must satisfy 0 < R0 < R1")
    if "NITER" in values:
        n = values["NITER"]
        if n != int(n) or not 1 <= n <= NITER_MAX:
            raise ValueError("NITER must be an integer between 1 and "
                             f"{NITER_MAX}")


def _require_file(path, what):
    if not Path(path).is_file():
        raise FileNotFoundError(f"{what} not found: {path}")


def _kill_process_tree(proc: subprocess.Popen) -> None:
    """Terminate the backend and anything it started."""
    if os.name == "posix":
        for sig in (signal.SIGTERM, signal.SIGKILL):
            try:
                os.killpg(proc.pid, sig)
            except (ProcessLookupError, PermissionError):
                return
            try:
                proc.wait(timeout=5)
                return
            except subprocess.TimeoutExpired:
                continue
    else:  # Windows: kill the whole process tree
        subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        proc.kill()


def _run(cmd: List[str], cwd: Path, timeout: Optional[float]):
    """Run the backend with no terminal input and a time limit."""
    kwargs = dict(cwd=str(cwd), stdin=subprocess.DEVNULL,
                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                  universal_newlines=True)
    if os.name == "posix":
        kwargs["start_new_session"] = True     # own process group
    else:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    proc = subprocess.Popen(cmd, **kwargs)
    try:
        out, err = proc.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        _kill_process_tree(proc)
        proc.communicate()
        raise ElliprofTimeoutError(timeout, cmd) from None
    except BaseException:
        _kill_process_tree(proc)
        raise
    return proc.returncode, out, err


def run_elliprof(image: PathLike, x0: float, y0: float, *,
                 mask: Optional[PathLike] = None,
                 sky: Optional[float] = None,
                 sky_image: Optional[PathLike] = None,
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
                 timeout: Optional[float] = DEFAULT_TIMEOUT,
                 check: bool = True, backend: Optional[PathLike] = None,
                 ) -> ElliprofResult:
    """Fit elliptical isophotes to ``image`` with ELLIPROF.

    ``x0``, ``y0`` (required): initial centre in ELLIPROF image
    coordinates, where the centre of the pixel in FITS column i is at
    x = i - 0.5.  ELLIPROF refines the centre of every isophote.

    Preparation, in this order: subtract ``sky`` (a number) or
    ``sky_image`` (a FITS image of the same size), then multiply by
    ``mask`` (0 = masked, 1 = good; legacy BITPIX=1 masks supported).

    ``r0``, ``r1``, ``nr`` are required (0 < r0 < r1, 2 <= nr <= 100).
    ``elliprof_sky`` is ELLIPROF's own ``SKY=`` keyword, used only in its
    de Vaucouleurs fit; it is unrelated to ``sky``.

    Output files (.prf, .csv, .reg, and the model FITS with
    ``model=True``) go to ``output_dir`` (a new temporary directory by
    default), named after ``prefix`` (default: the image name), unless
    explicit paths are given.

    ``timeout`` (seconds, default 1800; ``None`` for no limit): if the
    backend runs longer, it is terminated and
    :class:`ElliprofTimeoutError` is raised.
    """
    # ---- validate everything before anything is run
    image = Path(image)
    _require_file(image, "image")
    image_info(str(image))
    x0 = _finite(x0, "X0")
    y0 = _finite(y0, "Y0")
    if sky is not None and sky_image is not None:
        raise ValueError("--sky and --sky-image cannot be used together")
    if sky is not None:
        if isinstance(sky, str):
            _finite(sky, "sky")
            sky_arg = sky.strip()   # the backend parses it itself
        else:
            sky_arg = _num(sky)
    if sky_image is not None:
        _require_file(sky_image, "sky image")
        check_same_geometry(str(image), str(sky_image), "sky image")
    if mask is not None:
        _require_file(mask, "mask")
        check_same_geometry(str(image), str(mask), "mask")
    if timeout is not None and not _finite(timeout, "timeout") > 0:
        raise ValueError("timeout must be positive (or None)")
    words = elliprof_keywords(
        r0=r0, r1=r1, nr=nr, niter=niter, rlaw=rlaw, linear=linear,
        fixctr=fixctr, ellip=ellip, scale=scale, elliprof_sky=elliprof_sky,
        model=model, rmstar=rmstar, cos3x=cos3x, cos4x=cos4x, tie=tie,
        avg=avg, gain=gain, gc=gc, verbose=verbose, extra=extra)
    validate_keywords(words)

    # ---- output files
    made_tmp = output_dir is None
    out = Path(tempfile.mkdtemp(prefix="elliprof-")) if made_tmp \
        else Path(output_dir)
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
    cmd = [str(exe), str(image.resolve()), f"X0={_num(x0)}",
           f"Y0={_num(y0)}", *words]
    if sky is not None:
        cmd += ["--sky", sky_arg]
    if sky_image is not None:
        cmd += ["--sky-image", str(Path(sky_image).resolve())]
    if mask is not None:
        cmd += ["--mask", str(Path(mask).resolve())]
    cmd += ["-o", str(prf.resolve()), "--csv", str(csv.resolve()),
            "--reg", str(reg.resolve())]
    if mdl is not None:
        cmd += ["-m", str(mdl.resolve())]
    if prepared is not None:
        cmd += ["--prepared", str(Path(prepared).resolve())]

    # The backend runs in the output directory, so anything it writes on
    # its own (DUMP= -> fort.2) lands there.
    try:
        code, stdout, stderr = _run(cmd, out, timeout)
    except ElliprofTimeoutError:
        if made_tmp:
            shutil.rmtree(out, ignore_errors=True)
        raise
    ok = code == 0
    result = ElliprofResult(
        profile=read_profile(str(prf)) if ok and not gc else None,
        prf_path=prf if ok and prf.exists() else None,
        csv_path=csv if ok and csv.exists() else None,
        reg_path=reg if ok and reg.exists() else None,
        model_path=mdl if ok and mdl is not None and mdl.exists() else None,
        stdout=stdout, stderr=stderr, returncode=code, command=cmd,
        center=(x0, y0), backend_path=exe, output_dir=out,
        prepared_path=Path(prepared) if prepared else None)
    if check and not ok:
        detail = stderr.strip() or stdout.strip()[-2000:]
        raise ElliprofError(f"elliprof failed (exit {code}): {detail}",
                            result)
    return result
