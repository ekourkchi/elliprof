"""Check that the installed elliprof backend only needs libraries that
are bundled in the wheel or provided by the operating system.

    python tools/ci/check_backend_deps.py

Run in the environment where the wheel is installed.  Exits non-zero
and lists offending libraries otherwise.  Uses otool (macOS), readelf
(Linux) or objdump (Windows, e.g. from MSYS2/MinGW).
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


def backend() -> Path:
    import elliprof
    return elliprof.find_backend().resolve()


def macos(exe: Path):
    out = subprocess.run(["otool", "-L", str(exe)], capture_output=True,
                         text=True, check=True).stdout.splitlines()[1:]
    deps = [l.split(" (")[0].strip() for l in out if l.strip()]
    ok = ("@loader_path/", "@rpath/", "/usr/lib/", "/System/Library/")
    return deps, [d for d in deps if not d.startswith(ok)]


def linux(exe: Path):
    out = subprocess.run(["readelf", "-d", str(exe)], capture_output=True,
                         text=True, check=True).stdout
    deps = re.findall(r"\(NEEDED\).*\[(.+?)\]", out)
    libs = exe.parents[1].parent / "elliprof.libs"
    bundled = {p.name for p in libs.glob("*")} if libs.is_dir() else set()
    # manylinux policy libraries every glibc system has
    system = re.compile(r"^(libc|libm|libdl|librt|libpthread|libgcc_s|"
                        r"libz|ld-linux[-\w]*|libutil|libresolv)\.so")
    bad = [d for d in deps if d not in bundled and not system.match(d)]
    return deps, bad


def windows(exe: Path):
    out = subprocess.run(["objdump", "-p", str(exe)], capture_output=True,
                         text=True, check=True).stdout
    deps = re.findall(r"DLL Name: (\S+)", out)
    here = {p.name.lower() for p in exe.parent.glob("*.dll")}
    libs = exe.parents[1].parent / "elliprof.libs"
    if libs.is_dir():
        here |= {p.name.lower() for p in libs.glob("*.dll")}
    system = re.compile(r"^(kernel32|msvcrt|ucrtbase|api-ms-win-.*|user32|"
                        r"advapi32|ws2_32|shell32|ntdll)\.dll$", re.I)
    bad = [d for d in deps if d.lower() not in here and not system.match(d)]
    return deps, bad


def main() -> int:
    exe = backend()
    check = {"darwin": macos, "win32": windows}.get(sys.platform, linux)
    deps, bad = check(exe)
    print(f"backend: {exe}")
    for d in deps:
        print(f"  needs {d}{'   <-- NOT bundled / not system' if d in bad else ''}")
    if bad:
        print("FAIL: the backend depends on libraries outside the wheel")
        return 1
    print("OK: every dependency is bundled or part of the OS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
