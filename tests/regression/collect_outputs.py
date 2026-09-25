"""Run every regression case into a directory, for cross-platform
comparison (CI uploads the directory as an artifact).

    python tests/regression/collect_outputs.py OUTDIR
    python tests/regression/compare_platforms.py DIR1 DIR2 [...]
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from cases import all_runs  # noqa: E402
from runner import run_case  # noqa: E402


def main(outdir: str):
    out = Path(outdir)
    for name, image, kwargs in all_runs():
        run_case(name, image, kwargs, out / name)
        print("ran", name)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
