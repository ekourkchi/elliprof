"""The double backend (src/double) is generated from the frozen original
by tools/precision_port.py: the committed files must be exactly what the
script writes, and each names the original it was made from."""

import hashlib
import re
import subprocess
import sys

from helpers import ROOT

TOOL = ROOT / "tools" / "precision_port.py"


def test_port_is_what_the_tool_generates():
    r = subprocess.run([sys.executable, str(TOOL), "--check"],
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
    assert r.returncode == 0, r.stderr


def test_provenance_names_the_current_original():
    for port, original in (("elliprof_d.f", "elliprof.f"),
                           ("jtutil_d.f", "jtutil.f")):
        text = (ROOT / "src" / "double" / port).read_text()
        sha = hashlib.sha256(
            (ROOT / "src" / "original" / original).read_bytes()).hexdigest()
        assert f"port of src/original/{original}" in text
        assert f"original SHA-256: {sha}" in text
        assert "Permitted changes" in text


def test_fixed_form_line_length():
    for path in list((ROOT / "src" / "double").rglob("*.f")) + \
            list((ROOT / "src" / "double").rglob("*.inc")):
        for n, line in enumerate(path.read_text().splitlines(), 1):
            if not re.match(r"[cC*!]", line):
                assert len(line) <= 72, f"{path.name}:{n}"


def test_no_single_precision_left_in_the_port():
    for path in (ROOT / "src" / "double").glob("*.f"):
        code = "\n".join(l for l in path.read_text().splitlines()
                         if not re.match(r"[cC*!]", l) and l.strip())
        code = re.sub(r"'[^']*'", "''", code)
        for bad in (r"\breal\s*\*\s*4\b", r"\balog\s*\(",
                    r"\balog10\s*\(", r"\bamin1\s*\(", r"\bamax1\s*\(",
                    r"\bfloat\s*\(", r"\bsngl\s*\(",
                    r"/\s*(prf|prf_name|elltest|ellizero)\s*/"):
            assert not re.search(bad, code, re.I), (path.name, bad)
        # the only REAL left is CONST of the shared /VISCON/ block
        for line in code.splitlines():
            if re.match(r"\s+real\b", line, re.I):
                assert line.strip().upper() == "REAL CONST", line
