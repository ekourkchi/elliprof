"""Run regression cases and compare outputs (shared by the tests,
update_baselines.py and the cross-platform tools)."""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / "python"))

from elliprof import find_backend, run_elliprof  # noqa: E402
from elliprof.profile import COLUMNS, read_profile  # noqa: E402

FILES = ("profile.prf", "profile.csv", "profile.reg", "stdout.txt")


def binary_arch(path) -> str:
    """CPU architecture of an executable, from its Mach-O / ELF / PE
    header (the backend may differ from the running Python, e.g. an
    x86_64 backend under Rosetta)."""
    import struct
    with open(path, "rb") as f:
        head = f.read(4096)
    magic = head[:4]
    if magic in (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe"):   # Mach-O
        cpu = struct.unpack("<i", head[4:8])[0]
        return {0x01000007: "x86_64", 0x0100000C: "arm64"}.get(cpu, hex(cpu))
    if magic == b"\x7fELF":
        machine = struct.unpack("<H", head[18:20])[0]
        return {0x3E: "x86_64", 0xB7: "aarch64"}.get(machine, hex(machine))
    if magic[:2] == b"MZ":                                       # PE
        pe = struct.unpack("<I", head[0x3C:0x40])[0]
        machine = struct.unpack("<H", head[pe + 4:pe + 6])[0]
        return {0x8664: "AMD64", 0xAA64: "ARM64"}.get(machine, hex(machine))
    return platform.machine()


def os_version() -> str:
    """OS release that provides the maths library: results can differ in
    the last bits between macOS versions or glibc versions."""
    system = platform.system()
    if system == "Darwin":
        return "macOS " + platform.mac_ver()[0]
    if system == "Linux":
        lib, ver = platform.libc_ver()
        return f"{lib} {ver}".strip()
    return platform.version()


def platform_id() -> dict:
    exe = find_backend()
    version = subprocess.run([str(exe), "--version"], capture_output=True,
                             text=True).stdout.strip()
    return {"system": platform.system(), "os": os_version(),
            "machine": binary_arch(exe), "backend": version}


def run_case(name, image, kwargs, outdir: Path):
    """Run one case into outdir (profile.prf/.csv/.reg, stdout.txt,
    meta.json)."""
    outdir.mkdir(parents=True, exist_ok=True)
    kw = dict(kwargs)
    model = kw.get("model", False)
    res = run_elliprof(image, output_dir=outdir, prefix="profile",
                       model_path=outdir / "model.fits" if model else None,
                       **kw)
    # keep machine-specific absolute paths out of stored outputs
    root = str(HERE.parents[1])

    def scrub(text):
        return text.replace(str(outdir.resolve()), "<OUT>") \
            .replace(str(outdir), "<OUT>").replace(root, "<ROOT>")
    (outdir / "stdout.txt").write_text(scrub(res.stdout))
    csv = outdir / "profile.csv"
    csv.write_text("".join(scrub(l) if l.startswith("#") else l
                           for l in open(csv)))
    meta = dict(platform_id(), case=name, center=list(res.center),
                dvfit=parse_dvfit(res.stdout))
    if model:
        # the pixel values only; header text may change between versions
        from astropy.io import fits
        data = fits.getdata(outdir / "model.fits").astype(">f4")
        meta["model_sha256"] = hashlib.sha256(data.tobytes()).hexdigest()
    (outdir / "meta.json").write_text(json.dumps(meta, indent=1) + "\n")
    return res


_DV = re.compile(r"Re =\s*(\S+)\s+(\S+)\s+Ie =\s*(\S+)\s+(\S+)\s+"
                 r"Sky =\s*(\S+)\s+(\S+)")


def parse_dvfit(stdout: str) -> dict:
    """ELLIPROF's de Vaucouleurs fit line: Re, Ie, Sky for the major and
    minor axis."""
    m = _DV.search(stdout)
    if not m:
        return {}
    v = [float(x) for x in m.groups()]
    return {"re": v[0:2], "ie": v[2:4], "sky": v[4:6]}


def csv_rows(path):
    return [l for l in open(path) if not l.startswith("#")]


def same_platform(a: dict, b: dict) -> bool:
    return all(a.get(k) == b.get(k) for k in ("system", "os", "machine",
                                               "backend"))


def column_differences(ref: Path, new: Path) -> dict:
    """Per column: max |new - ref| over contours (NaN-aware) from the
    .prf files, plus contour counts."""
    a = read_profile(str(ref / "profile.prf"))
    b = read_profile(str(new / "profile.prf"))
    out = {"n_ref": len(a), "n_new": len(b)}
    if len(a) != len(b):
        return out
    for col in COLUMNS:
        x, y = a[col].to_numpy(), b[col].to_numpy()
        nan_mismatch = np.isnan(x) != np.isnan(y)
        d = np.abs(x - y)
        if col in ("A3", "A4"):  # phase angles: 120 / 90 degree period
            period = 120.0 if col == "A3" else 90.0
            d = np.minimum(d, period - d)
        d = d[~np.isnan(d)]
        rel = d / np.maximum(np.abs(x[~np.isnan(x - y)]), 1e-30)
        out[col] = {"abs": float(d.max()) if d.size else 0.0,
                    "rel": float(rel.max()) if rel.size else 0.0,
                    "nan_mismatch": int(nan_mismatch.sum())}
    return out
