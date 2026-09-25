"""Check a release upload directory before it goes to PyPI.

    python tools/ci/check_release.py DIST_DIR VERSION

The release is wheel-only.  Fails unless DIST_DIR holds exactly one wheel
for each Supported platform (no Experimental ones, no sdist, nothing
else), all for VERSION, each carrying the licence notices and the native
backend and nothing from a build or test tree.  `twine check --strict` is
run separately.
"""

import re
import sys
import zipfile
from pathlib import Path
from typing import List, Tuple

NAME = "elliprof"

# Supported platforms (README "Platforms"): one py3-none wheel each.
# Experimental targets (linux riscv64, Windows ARM64) must not appear.
EXPECTED_TAGS = {
    "py3-none-manylinux_2_27_x86_64.manylinux_2_28_x86_64",
    "py3-none-manylinux_2_27_aarch64.manylinux_2_28_aarch64",
    "py3-none-manylinux_2_27_ppc64le.manylinux_2_28_ppc64le",
    "py3-none-manylinux_2_27_s390x.manylinux_2_28_s390x",
    "py3-none-musllinux_1_2_x86_64",
    "py3-none-musllinux_1_2_aarch64",
    "py3-none-macosx_11_0_arm64",
    "py3-none-macosx_10_16_x86_64.macosx_11_0_x86_64",
    "py3-none-win_amd64",
}

# licence files every wheel must carry (THIRD_PARTY_NOTICES.md)
RUNTIME_LICENSES = ["GPL-3.0.txt", "GCC-RUNTIME-LIBRARY-EXCEPTION-3.1.txt",
                    "LGPL-2.1.txt", "winpthreads-COPYING.txt",
                    "zlib-LICENSE.txt"]
WHEEL_REQUIRED = [
    "{di}/licenses/LICENSE",
    "{di}/licenses/THIRD_PARTY_NOTICES.md",
    *(f"{{di}}/licenses/licenses/{n}" for n in RUNTIME_LICENSES),
    "elliprof/_notices/LICENSE",
    "elliprof/_notices/THIRD_PARTY_NOTICES.md",
    "elliprof/_notices/CFITSIO_License.txt",
    *(f"elliprof/_notices/{n}" for n in RUNTIME_LICENSES),
    "elliprof/__init__.py",
]

# nothing from a build tree, a test run or a virtualenv
FORBIDDEN = re.compile(
    r"(^|/)(build|_skbuild|CMakeFiles|wheelhouse|dist|\.venv|__pycache__|"
    r"\.pytest_cache|elliprof_output)(/|$)|\.(o|obj|pyc|mod)$|(^|/)\.DS_Store$")


def fail(errors, msg):
    errors.append(msg)
    print("FAIL:", msg)


def metadata_version(text: str) -> str:
    m = re.search(r"^Version: (\S+)$", text, re.M)
    return m.group(1) if m else "?"


def check_wheel(path: Path, version: str, errors) -> Tuple[str, str]:
    m = re.fullmatch(rf"{NAME}-([^-]+)-(py3-none-.+)\.whl", path.name)
    if not m:
        fail(errors, f"{path.name}: unexpected wheel name")
        return "", ""
    ver, tag = m.groups()
    if ver != version:
        fail(errors, f"{path.name}: version {ver}, expected {version}")
    di = f"{NAME}-{ver}.dist-info"
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
        meta = (z.read(f"{di}/METADATA").decode()
                if f"{di}/METADATA" in names else "")
    if metadata_version(meta) != version:
        fail(errors, f"{path.name}: METADATA version {metadata_version(meta)}, "
                     f"expected {version}")
    for req in WHEEL_REQUIRED:
        if req.format(di=di) not in names:
            fail(errors, f"{path.name}: missing {req.format(di=di)}")
    exe = "elliprof/_bin/elliprof_native" + (".exe" if "win_" in tag else "")
    if exe not in names:
        fail(errors, f"{path.name}: missing backend {exe}")
    for n in sorted(names):
        if FORBIDDEN.search(n) or n.startswith(("tests/", "src/")):
            fail(errors, f"{path.name}: unexpected file {n}")
    return tag, ver


def main(dist: str, version: str) -> int:
    errors: List[str] = []
    files = sorted(Path(dist).iterdir())
    wheels = [f for f in files if f.suffix == ".whl"]
    for f in files:
        if f not in wheels:
            fail(errors, f"not a wheel (the release is wheel-only): {f.name}")
    results = [check_wheel(w, version, errors) for w in wheels]
    tags = [t for t, _ in results if t]
    versions = {v for _, v in results if v}
    if len(versions) > 1:
        fail(errors, f"wheels have different versions: {sorted(versions)}")
    if len(tags) != len(set(tags)):
        fail(errors, "more than one wheel for a platform tag")
    for t in sorted(EXPECTED_TAGS - set(tags)):
        fail(errors, f"missing wheel for {t}")
    for t in sorted(set(tags) - EXPECTED_TAGS):
        fail(errors, f"wheel for a platform not in the release: {t}")
    if len(wheels) != len(EXPECTED_TAGS):
        fail(errors, f"{len(wheels)} wheels, expected {len(EXPECTED_TAGS)}")

    print(f"\n{len(wheels)} wheels, version {version}:")
    for f in files:
        print(f"  {f.name}  ({f.stat().st_size / 1e6:.1f} MB)")
    if errors:
        print(f"\n{len(errors)} problem(s): not releasable")
        return 1
    print("\nOK: releasable")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    sys.exit(main(sys.argv[1], sys.argv[2]))
