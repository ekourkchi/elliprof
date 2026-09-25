"""Give a macOS 11 x86_64 wheel the equivalent ``macosx_10_16`` tag.

    python tools/ci/macos_compat_tag.py WHEEL_DIR

Pythons built against an older macOS SDK (e.g. python.org's 3.6) see
macOS 11 and later as "10.16", and pip releases that still support them
(pip 21.3.1 on Python 3.6) then accept only macosx_10_* wheels.  macOS
10.16 *is* macOS 11 in that numbering, and a real macOS 10.15 reports
10.15, so ``macosx_10_16_x86_64.macosx_11_0_x86_64`` promises exactly
what ``macosx_11_0_x86_64`` does.  Only the file name and the WHEEL tags
change; the contents are untouched.
"""

import subprocess
import sys
from pathlib import Path

OLD = "macosx_11_0_x86_64"
NEW = "macosx_10_16_x86_64." + OLD


def main(wheel_dir: str) -> int:
    for whl in sorted(Path(wheel_dir).glob(f"*-{OLD}.whl")):
        subprocess.run([sys.executable, "-m", "pip", "install", "-q",
                        "wheel>=0.40"], check=True)
        subprocess.run([sys.executable, "-m", "wheel", "tags",
                        "--platform-tag", NEW, "--remove", str(whl)],
                       check=True)
    for whl in sorted(Path(wheel_dir).glob("*.whl")):
        print("wheel:", whl.name)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
