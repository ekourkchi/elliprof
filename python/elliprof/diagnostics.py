"""Environment report for bug reports (``elliprof --diagnostics``).

Nothing heavy is imported: package versions come from the installed
package metadata, so a broken numpy/pandas stack (e.g. old numexpr or
bottleneck built for NumPy 1.x under NumPy 2) cannot crash the report.
"""

import platform
import struct
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional

from ._native import BackendNotFoundError, backend_source, find_backend
from ._version import __version__


def _dist_version(name: str) -> str:
    try:
        try:
            from importlib.metadata import PackageNotFoundError, version
        except ImportError:  # Python < 3.8
            from importlib_metadata import PackageNotFoundError, version
        try:
            return version(name)
        except PackageNotFoundError:
            return "not installed"
    except Exception as exc:  # pragma: no cover
        return f"unknown ({exc})"


def _binary_info(path: Path) -> Dict[str, str]:
    """Architecture (Mach-O / ELF / PE header) and, for Mach-O, the
    minimum macOS version the binary was built for."""
    info = {}
    try:
        with open(str(path), "rb") as f:
            head = f.read(65536)
    except OSError as exc:
        return {"backend architecture": f"unreadable ({exc})"}
    magic = head[:4]
    if magic == b"\xcf\xfa\xed\xfe":                       # 64-bit Mach-O
        cpu, _, _, ncmds = struct.unpack("<iiII", head[4:20])
        info["backend architecture"] = {0x01000007: "x86_64",
                                        0x0100000C: "arm64"}.get(cpu,
                                                                 hex(cpu))
        minos = _macho_minos(head, ncmds)
        if minos:
            info["backend minimum macOS"] = minos
    elif magic == b"\x7fELF":
        order = ">" if head[5] == 2 else "<"
        machine = struct.unpack(order + "H", head[18:20])[0]
        info["backend architecture"] = {
            0x3E: "x86_64", 0xB7: "aarch64", 0x15: "ppc64le",
            0x16: "s390x", 0xF3: "riscv64"}.get(machine, hex(machine))
    elif magic[:2] == b"MZ":
        pe = struct.unpack("<I", head[0x3C:0x40])[0]
        machine = struct.unpack("<H", head[pe + 4:pe + 6])[0]
        info["backend architecture"] = {0x8664: "AMD64",
                                        0xAA64: "ARM64"}.get(machine,
                                                             hex(machine))
    return info


def _macho_minos(head: bytes, ncmds: int) -> Optional[str]:
    """LC_BUILD_VERSION minos or LC_VERSION_MIN_MACOSX version."""
    off = 32                                   # mach_header_64
    for _ in range(ncmds):
        if off + 16 > len(head):
            break
        cmd, size = struct.unpack("<II", head[off:off + 8])
        if cmd == 0x32:                        # LC_BUILD_VERSION
            v = struct.unpack("<I", head[off + 12:off + 16])[0]
        elif cmd == 0x24:                      # LC_VERSION_MIN_MACOSX
            v = struct.unpack("<I", head[off + 8:off + 12])[0]
        else:
            off += size
            continue
        return f"{v >> 16}.{(v >> 8) & 0xFF}"
    return None


def diagnostics() -> Dict[str, str]:
    info = {
        "elliprof version": __version__,
        "Python": f"{platform.python_version()} ({sys.executable})",
        "OS": f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
    }
    if sys.platform == "darwin":
        info["macOS"] = platform.mac_ver()[0] or "unknown"
    try:
        exe = find_backend()
        info["native backend"] = f"{exe} [{backend_source()}]"
        info.update(_binary_info(exe))
        proc = subprocess.run([str(exe), "--version"], stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              universal_newlines=True, timeout=30)
        info["backend version"] = (proc.stdout.strip() or
                                   f"failed: {proc.stderr.strip()}")
    except BackendNotFoundError as exc:
        info["native backend"] = f"not found ({exc})"
    except (OSError, subprocess.SubprocessError) as exc:
        info["backend version"] = f"cannot run backend: {exc}"
    for dist in ("numpy", "pandas", "astropy", "numexpr", "bottleneck"):
        info[dist] = _dist_version(dist)
    return info


def format_diagnostics(info: Dict[str, str]) -> str:
    width = max(len(k) for k in info)
    return "\n".join(f"{k:<{width}} : {v}" for k, v in info.items())
