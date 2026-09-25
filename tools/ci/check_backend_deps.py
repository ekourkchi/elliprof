"""Check that the installed elliprof backend only needs libraries that
are bundled in the wheel or provided by the operating system.

    python tools/ci/check_backend_deps.py

Run in the environment where the wheel is installed.  Exits non-zero
and lists offending libraries otherwise.  Uses otool (macOS), readelf
(Linux) or objdump (Windows, e.g. from MSYS2/MinGW).
"""

import re
import subprocess
import sys
from pathlib import Path


def backend() -> Path:
    import elliprof
    return elliprof.find_backend().resolve()


def macos(exe: Path):
    out = subprocess.run(["otool", "-L", str(exe)], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         universal_newlines=True,
                         check=True).stdout.splitlines()[1:]
    deps = [l.split(" (")[0].strip() for l in out if l.strip()]
    ok = ("@loader_path/", "@rpath/", "/usr/lib/", "/System/Library/")
    return deps, [d for d in deps if not d.startswith(ok)]


def _run(*cmd):
    return subprocess.run(list(cmd), stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE, universal_newlines=True,
                          check=True).stdout


def _minos(path: Path):
    """Minimum macOS of a Mach-O file (LC_BUILD_VERSION minos, or
    LC_VERSION_MIN_MACOSX version for older targets)."""
    lines = _run("otool", "-l", str(path)).splitlines()
    for i, line in enumerate(lines):
        cmd = line.split()[-1:] == ["LC_BUILD_VERSION"] and "minos" or \
            line.split()[-1:] == ["LC_VERSION_MIN_MACOSX"] and "version"
        if cmd:
            for follow in lines[i + 1:i + 6]:
                parts = follow.split()
                if parts[:1] == [cmd]:
                    return tuple(int(x) for x in parts[1].split("."))
    return None


def macos_minimums(exe: Path) -> int:
    """Every Mach-O shipped in the wheel must run on the oldest macOS its
    platform tag promises (the tag alone proves nothing)."""
    site = exe.parents[2]
    wheel = sorted(site.glob("elliprof-*.dist-info/WHEEL"))
    tags = [l.split(":", 1)[1].strip() for l in wheel[-1].read_text()
            .splitlines() if l.startswith("Tag:")] if wheel else []
    promised = [tuple(int(x) for x in m.groups()) for t in tags
                for m in [re.search(r"macosx_(\d+)_(\d+)_", t)] if m]
    if not promised:
        print("macOS minimum: no macosx tag found, not checked")
        return 0
    floor = min(promised)
    if floor == (10, 16):      # macOS 11 in the old-SDK numbering
        floor = (11, 0)
    files = [exe] + sorted((exe.parents[1] / ".dylibs").glob("*.dylib"))
    bad = 0
    print("macOS minimum promised by the wheel tag: %d.%d" % floor)
    for f in files:
        m = _minos(f)
        flag = ""
        if m is None or m > floor:
            flag, bad = "   <-- NEWER THAN THE TAG (or unknown)", bad + 1
        print("  %-28s minos %s%s" % (f.name, ".".join(map(str, m or ())),
                                      flag))
    return bad


def linux(exe: Path):
    out = subprocess.run(["readelf", "-d", str(exe)], stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         universal_newlines=True, check=True).stdout
    deps = re.findall(r"\(NEEDED\).*\[(.+?)\]", out)
    libs = exe.parents[1].parent / "elliprof.libs"
    bundled = {p.name for p in libs.glob("*")} if libs.is_dir() else set()
    # manylinux policy libraries every glibc system has; musl's libc
    system = re.compile(r"^(libc|libm|libdl|librt|libpthread|libgcc_s|"
                        r"libz|ld-linux[-\w]*|libutil|libresolv|"
                        r"libc\.musl-\w+|ld-musl-\w+)\.so")
    bad = [d for d in deps if d not in bundled and not system.match(d)]
    return deps, bad


def windows(exe: Path):
    # The backend is its own process: only DLLs next to it (or in the
    # system) are found -- not the elliprof.libs directory that delvewheel
    # registers for the Python process.  Follow bundled DLLs transitively.
    def imports(pe: Path):
        out = subprocess.run(["objdump", "-p", str(pe)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                             universal_newlines=True, check=True).stdout
        return re.findall(r"DLL Name: (\S+)", out)

    here = {p.name.lower(): p for p in exe.parent.glob("*.dll")}
    system = re.compile(r"^(kernel32|msvcrt|ucrtbase|api-ms-win-.*|user32|"
                        r"advapi32|ws2_32|shell32|ntdll)\.dll$", re.I)
    deps, bad, todo, seen = [], [], [exe], set()
    while todo:
        pe = todo.pop()
        for d in imports(pe):
            if d.lower() in seen:
                continue
            seen.add(d.lower())
            deps.append(d)
            if d.lower() in here:
                todo.append(here[d.lower()])
            elif not system.match(d):
                bad.append(d)
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
    if sys.platform == "darwin" and macos_minimums(exe):
        print("FAIL: a binary needs a newer macOS than the wheel claims")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
