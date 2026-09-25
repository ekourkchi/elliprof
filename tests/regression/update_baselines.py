"""Regenerate tests/regression/baseline/ (maintenance only).

    make update-baselines          (or: python tests/regression/update_baselines.py)

Never run by `make test` or `make check`.  Review the printed
differences and commit the new baselines deliberately.
"""

import json
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cases import BASELINE, all_runs  # noqa: E402
from runner import FILES, column_differences, run_case  # noqa: E402


def main():
    BASELINE.mkdir(parents=True, exist_ok=True)
    for name, image, kwargs in all_runs():
        with tempfile.TemporaryDirectory() as tmp:
            new = Path(tmp) / name
            run_case(name, image, kwargs, new)
            old = BASELINE / name
            if (old / "profile.prf").exists():
                diff = column_differences(old, new)
                worst = {k: v["abs"] for k, v in diff.items()
                         if isinstance(v, dict) and v["abs"] > 0}
                print(f"{name:14s} changed: {worst or 'identical'}")
            else:
                print(f"{name:14s} new baseline")
            if old.exists():
                shutil.rmtree(old)
            old.mkdir(parents=True)
            for f in FILES + ("meta.json",):
                shutil.copy(new / f, old / f)
    meta = json.loads((BASELINE / "circular" / "meta.json").read_text())
    print(f"baselines written for {meta['system']} {meta['machine']}, "
          f"{meta['backend']}")


if __name__ == "__main__":
    main()
