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


def platform_id() -> dict:
    exe = find_backend()
    version = subprocess.run([str(exe), "--version"], capture_output=True,
                             text=True).stdout.strip()
    return {"system": platform.system(), "machine": platform.machine(),
            "backend": version}


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
                center_source=res.center_source,
                dvfit=parse_dvfit(res.stdout))
    if model:
        meta["model_sha256"] = hashlib.sha256(
            (outdir / "model.fits").read_bytes()).hexdigest()
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
    return all(a.get(k) == b.get(k) for k in ("system", "machine",
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
