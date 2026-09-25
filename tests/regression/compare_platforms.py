"""Measure the numerical spread between platforms.

    python tests/regression/compare_platforms.py REF_DIR DIR [DIR ...]

Each directory comes from collect_outputs.py on one platform (or is the
baseline directory).  Prints, per case and column, the largest
absolute and relative difference from REF_DIR, and the overall maximum
per column, as a Markdown table.  Used to choose the cross-platform
tolerances in tolerances.json: measure first, then set.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from runner import column_differences  # noqa: E402
from elliprof.profile import COLUMNS  # noqa: E402


def platform_name(d: Path) -> str:
    for meta in sorted(d.glob("*/meta.json")):
        m = json.loads(meta.read_text())
        return f"{m['system']} {m['machine']}, {m.get('os', '?')} [{d.name}]"
    return d.name


def main(ref: str, others):
    ref = Path(ref)
    overall = {}
    for other in map(Path, others):
        print(f"\n## {platform_name(other)} vs {platform_name(ref)}\n")
        print("| case | " + " | ".join(COLUMNS) + " |")
        print("|---" * (len(COLUMNS) + 1) + "|")
        for case in sorted(p.name for p in ref.iterdir() if p.is_dir()):
            if not (other / case / "profile.prf").exists():
                print(f"| {case} | missing |")
                continue
            diff = column_differences(ref / case, other / case)
            if diff["n_ref"] != diff["n_new"]:
                print(f"| {case} | contour count {diff['n_ref']} vs "
                      f"{diff['n_new']} |")
                continue
            cells = []
            for col in COLUMNS:
                d = diff[col]
                cells.append(f"{d['abs']:.2e}" +
                             (f" ({d['nan_mismatch']} NaN)"
                              if d["nan_mismatch"] else ""))
                o = overall.setdefault(col, {"abs": 0.0, "rel": 0.0})
                o["abs"] = max(o["abs"], d["abs"])
                o["rel"] = max(o["rel"], d["rel"])
            print(f"| {case} | " + " | ".join(cells) + " |")
    print("\n## Overall maximum difference\n")
    print("| column | max abs | max rel |")
    print("|---|---|---|")
    for col in COLUMNS:
        o = overall.get(col, {"abs": 0.0, "rel": 0.0})
        print(f"| {col} | {o['abs']:.3e} | {o['rel']:.3e} |")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2:])
