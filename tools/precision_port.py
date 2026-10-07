"""Generate the double-precision backend from the original sources.

    python tools/precision_port.py           write src/double/*.f
    python tools/precision_port.py --check   exit 1 if they differ

src/double/elliprof_d.f and src/double/jtutil_d.f are maintained
precision ports of routines in src/original/elliprof.f and
src/original/jtutil.f.  They are generated, never edited by hand: every
change from the original is a rule in this file, so the port can be
audited against (and regenerated from) the frozen original.  A unit test
checks that the committed files are exactly what this script writes.

Permitted changes (the provenance header of each file repeats them):

* precision declarations: REAL, REAL*4 and REAL*8 become DOUBLE
  PRECISION, and each unit gets IMPLICIT DOUBLE PRECISION (A-H,O-Z)
  (units that already had IMPLICIT REAL*8 keep theirs, promoted);
  functions of the port get an explicit DOUBLE PRECISION type, in their
  FUNCTION statement and in every unit that calls them;
* real literals are written with a D exponent and the same decimal
  digits (0.33333333 becomes 0.33333333D0, 1e-4 becomes 1D-4);
* precision-specific intrinsics become generic: ALOG, ALOG10, AMIN1,
  AMAX1, FLOAT and SNGL become LOG, LOG10, MIN, MAX and DBLE;
* routines and COMMON blocks are renamed (a trailing D) so that the two
  backends never share code or storage; profile.inc becomes
  profile_d.inc (/PRFD/, /PRFNMD/); CONST of /VISCON/ stays REAL;
* explicitly reviewed edits (REVIEWED below), each marked
  "PRECISION PORT" in the generated source.

Character strings and FORMAT statements are never changed, so messages
and printed formats are those of the original.
"""

import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = ROOT / "src" / "original"
DOUBLE = ROOT / "src" / "double"

# file -> (output, routines of the original that are ported)
PORTS = {
    "elliprof.f": ("elliprof_d.f", {
        "elliprof", "fitprofile", "getcontour", "trimit", "fitcontour",
        "alter", "amodder", "dvfit", "linfit", "dlinsqrt", "synthesize",
        "elliterp"}),
    "jtutil.f": ("jtutil_d.f", {
        "amedian", "fitwlpoly", "dofitlpoly", "lpoly", "bc", "zbrent"}),
}

# Routine names (whole words).  ASSIGN becomes the original ASSIGNd,
# which already returns REAL*8 (assign.f); LPI and INVERT (jtutil.f) are
# REAL*8 in the original and are called unchanged.
RENAME = {
    "elliprof": "elliprofd", "fitprofile": "fitprofiled",
    "getcontour": "getcontourd", "trimit": "trimitd",
    "fitcontour": "fitcontourd", "alter": "alterd",
    "amodder": "amodderd", "dvfit": "dvfitd", "linfit": "linfitd",
    "dlinsqrt": "dlinsqrtd", "synthesize": "synthesized",
    "elliterp": "elliterpd", "amedian": "amediand",
    "fitwlpoly": "fitwlpolyd", "dofitlpoly": "dofitlpolyd",
    "lpoly": "lpolyd", "bc": "bcd", "zbrent": "zbrentd",
    "assign": "assignd"}
# functions of the port, typed explicitly where they are called
FUNCTIONS = ["amediand", "lpolyd", "zbrentd", "bcd", "amodderd",
             "elliterpd"]
COMMONS = {"elltest": "elltstd", "ellizero": "ellzd"}
INTRINSICS = {"alog10": "log10", "alog": "log", "amin1": "min",
              "amax1": "max", "float": "dble", "sngl": "dble"}

# a real literal: 1.5, 1., .5, 1.5e3, 3.e-8, 1e10 (not part of a name,
# not 1.5D0, not the 1 of 1.5 or the .5 of 1.5)
LITERAL = re.compile(r"(?<![\w])(?<!\d\.)((?:\d+\.\d*|\.\d+)"
                     r"(?:[eE][+-]?\d+)?|\d+[eE][+-]?\d+)(?![\w])(?!\.\d)")

# ---- explicitly reviewed edits ----------------------------------------
# (regular expression on the generated text, replacement (re.sub
# syntax), label[, expected number of matches, default 1]).

GC_REFUSE = """\
C     PRECISION PORT: the globular-cluster (GC) branch of the original
C     (ARRAYCENTER and MAKEGCMODEL in gcfit.f) is single precision only
C     and is not part of the double backend.  The driver refuses GC
C     before calling ELLIPROFD; this is a second guard.
      if(igc.eq.1) then
         write(6,*) 'double-precision GC mode is not yet supported'
         xerr = .true.
         return
      end if
"""
GC_OMIT = """\
C     PRECISION PORT: the GC branch (label 100 to MAKEGCMODEL) of the
C     original is omitted here; see the GC guard above.
"""
NORM_DECL = """\
C     PRECISION PORT: the normalization exponent (norm_d.inc); POW2D(X,K)
C     is X * 2**K (src/shim/double/prep_d.f)
      include 'norm_d.inc'
      DOUBLE PRECISION POW2D
"""
REVIEWED = {
    "elliprof.f": [
        (r"      if\(igc\.eq\.1\) goto 100\n", GC_REFUSE, "gc-refuse"),
        (r"C Fit concentric circles to a globular cluster\n.*?"
         r"     \$     ,width\)\n", GC_OMIT, "gc-omit"),
        # normalization: declarations in ELLIPROFD, FITPROFILED and
        # SYNTHESIZED
        (r"(      include 'profile_d\.inc'\n)", r"\1" + NORM_DECL,
         "norm-elliprofd"),
        (r"(maxstep=360, maxrad=100\)\n      include 'vistalink\.inc'\n)",
         r"\1" + NORM_DECL, "norm-fitprofiled"),
        (r"(      external elliterpd\n)", r"\1" + NORM_DECL,
         "norm-synthesized"),
        # keywords: plain numbers converted exactly (KWVALD), not by
        # the original parser (which scales by a REAL*4 power of ten)
        (r"call assignd\(", "call kwvald(", "keywords", 17),
        # SKY= is an intensity: physical -> internal units
        (r"(            call kwvald\(word\(i\),sky,parm\)\n"
         r"            if \(xerr\) return\n            isky = 1\n)",
         r"\1C     PRECISION PORT: SKY= in internal units\n"
         r"            sky = pow2d(sky, -knorm)\n", "sky-keyword"),
        # the fallback I0 of an isophote without positive samples: 1000
        # physical, i.e. 1000 * 2**(-k) internal (never beyond HUGE)
        (r"         par\(4,k\) = 1000\n",
         "C     PRECISION PORT: the fallback I0 = 1000 in physical units\n"
         "         par(4,k) = min(pow2d(1000D0, -knorm), huge(1D0))\n",
         "fallback-i0"),
        # printed intensities in physical units, in formats that hold
        # the whole double range
        (r"      write\(6,2001\) reff, remin, feff, femin, sky, skymin\n"
         r" 2001 format\(1x,'Re =',2f8\.1,4x,'Ie =',2f9\.1,4x,'Sky =',"
         r"2f9\.1\)\n",
         "C     PRECISION PORT: Ie and Sky printed in physical units\n"
         "      write(6,2001) reff, remin, pow2d(feff,knorm),\n"
         "     $     pow2d(femin,knorm), pow2d(sky,knorm),\n"
         "     $     pow2d(skymin,knorm)\n"
         " 2001 format(1x,'Re =',2f8.1,4x,'Ie =',2(1x,1pg15.8),4x,\n"
         "     $     'Sky =',2(1x,1pg15.8))\n", "print-devauc"),
        (r"WRITE\(6,\*\) K, PARAM\(1,K\), PARAM\(4,K\), FIT\+SKY\n",
         "WRITE(6,*) K, PARAM(1,K), POW2D(PARAM(4,K),KNORM),\n"
         "     $           POW2D(FIT+SKY,KNORM)\n", "print-test"),
        (r"(     \$ +)par\(4,k\),par\(5,k\)-90,",
         r"\1pow2d(par(4,k),knorm),par(5,k)-90,", "print-table", 2),
        (r" 1000       format\(f6\.1,2f8\.2,f8\.0,",
         " 1000       format(f6.1,2f8.2,1pg13.6,0p,", "print-table-fmt"),
        (r"      write\(6,6725\) rmajor, exp\(flog\), sky, epsilon\n"
         r" 6725 format\('Extrapolated outer isophote: r,f,sky,eps =',"
         r"3f9\.1,f9\.3\)\n",
         "C     PRECISION PORT: f and sky printed in physical units\n"
         "      write(6,6725) rmajor, pow2d(exp(flog),knorm),\n"
         "     $     pow2d(sky,knorm), epsilon\n"
         " 6725 format('Extrapolated outer isophote: r,f,sky,eps =',\n"
         "     $     f9.1,2(1x,1pg15.8),0p,f9.3)\n", "print-extrap"),
    ],
}

HEADER = """\
C     ----------------------------------------------------------------
C     Double-precision port of src/original/{src}
C     original SHA-256: {sha}
C     This is a maintained precision port, not the historical original
C     (which is kept unchanged in src/original/ and stays the reference).
C     Generated by tools/precision_port.py; do not edit by hand.
C     Permitted changes: precision declarations (REAL -> DOUBLE
C     PRECISION, IMPLICIT DOUBLE PRECISION), real literals written with
C     a D exponent (same decimal value), precision-specific intrinsics
C     (ALOG, ALOG10, AMIN1, AMAX1, FLOAT, SNGL -> generic forms),
C     renamed routines and COMMON blocks, and explicitly reviewed
C     numerical-range protections marked "PRECISION PORT".
C     ----------------------------------------------------------------
"""


def is_comment(line):
    return line[:1] in ("c", "C", "*", "!") or line.strip() == ""


def is_continuation(line):
    return (not is_comment(line) and len(line) > 5
            and line[5] not in " 0")


def outside_strings(line, fn):
    """Apply fn to the statement part of a code line, outside '...'."""
    head, body = line[:6], line[6:]
    parts = re.split(r"('[^']*')", body)
    return head + "".join(p if p.startswith("'") else fn(p) for p in parts)


def literal_d(m):
    s = m.group(1)
    return re.sub("[eE]", "D", s) if re.search("[eE]", s) else s + "D0"


def statement(text):
    for a, b in RENAME.items():
        text = re.sub(rf"\b{a}\b", b, text, flags=re.I)
    for a, b in COMMONS.items():
        text = re.sub(rf"/\s*{a}\s*/", f"/{b}/", text, flags=re.I)
    for a, b in INTRINSICS.items():
        text = re.sub(rf"\b{a}\s*\(", b + "(", text, flags=re.I)
    text = re.sub(r"\breal\s*\*\s*[48]\b", "double precision", text,
                  flags=re.I)
    text = re.sub(r"(?<![\w*])real\b(?!\s*\*)", "double precision", text,
                  flags=re.I)
    return LITERAL.sub(literal_d, text)


def transform(line):
    if is_comment(line):
        return line
    if re.match(r"\s+include\s+'profile\.inc'", line, re.I):
        return line.replace("profile.inc", "profile_d.inc")
    if re.match(r"\s*\d*\s+format\s*\(", line, re.I):
        return line
    if re.match(r"      function\s", line, re.I):
        line = ("      DOUBLE PRECISION FUNCTION "
                + line[6:].split(None, 1)[1])
    return outside_strings(line, statement)


def wrap(line):
    """Fixed form: continue a code line longer than 72 columns."""
    if is_comment(line) or len(line) <= 72:
        return line
    cut = line.rfind(",", 7, 72)
    assert cut > 6, line
    return line[:cut + 1] + "\n     $     " + line[cut + 1:].lstrip()


def units(lines):
    """Split a source file into program units (comments before a unit
    belong to the previous one, as in the original layout)."""
    out, cur = [], []
    for line in lines:
        if (cur and not is_comment(line) and re.match(
                r"\s+(real\s+|double precision\s+)?(subroutine|function)\b",
                line, re.I)):
            out.append(cur)
            cur = []
        cur.append(line)
    out.append(cur)
    return out


def port_unit(unit, name):
    code = [x for x in unit if not is_comment(x)]
    has_implicit = any(re.match(r"\s+implicit\b", x, re.I) for x in code)
    uses_viscon = any(re.search(r"include\s+'vistalink.inc'", x, re.I)
                      for x in code)
    body = " ".join(x.lower() for x in code)
    declared = " ".join(
        transform(x).lower() for x in code
        if re.match(r"\s+(double precision|real)\b", transform(x), re.I))
    calls = [f for f in FUNCTIONS
             if f != RENAME[name]
             and re.search(rf"\b{next(k for k, v in RENAME.items() if v == f)}"
                           r"\b", body)
             and not re.search(rf"\b{f}\b", declared)]

    added = []
    if not has_implicit:
        added.append("      IMPLICIT DOUBLE PRECISION (A-H,O-Z)")
    if uses_viscon:
        added += ["C     CONST is REAL in /VISCON/ (vistalink.inc) for every"
                  " unit", "      REAL CONST"]
    if calls:
        added.append("      DOUBLE PRECISION "
                     + ", ".join(c.upper() for c in calls))

    out, state = [], "header"
    for line in unit:
        if state == "pending" and not is_continuation(line):
            out += added
            state = "done"
        out.append(transform(line))
        if state == "header" and not is_comment(line):
            state = "pending"
    return "\n".join(wrap(x) for x in out)


def port(src):
    target, routines = PORTS[src]
    path = ORIGINAL / src
    sha = hashlib.sha256(path.read_bytes()).hexdigest()
    ported = []
    for unit in units(path.read_text().split("\n")):
        first = next((x for x in unit if not is_comment(x)), "")
        m = re.search(r"(subroutine|function)\s+(\w+)", first, re.I)
        if m and m.group(2).lower() in routines:
            ported.append(port_unit(unit, m.group(2).lower()))
    text = "\n".join(ported) + "\n"
    for edit in REVIEWED.get(src, []):
        pattern, new, label = edit[:3]
        count = edit[3] if len(edit) > 3 else 1
        n = len(re.findall(pattern, text, re.S))
        if n != count:
            raise SystemExit(f"reviewed edit {label!r} matched {n} "
                             f"times, expected {count}")
        text = re.sub(pattern, new, text, flags=re.S)
    text = "\n".join(wrap(x) for x in text.split("\n"))
    return target, HEADER.format(src=src, sha=sha) + text


def main(argv):
    check = "--check" in argv
    status = 0
    for src in PORTS:
        target, text = port(src)
        path = DOUBLE / target
        if check:
            if not path.exists() or path.read_text() != text:
                print(f"{path.relative_to(ROOT)} is not what "
                      "tools/precision_port.py generates", file=sys.stderr)
                status = 1
        else:
            path.write_text(text)
            print(f"wrote {path.relative_to(ROOT)}")
    return status


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
