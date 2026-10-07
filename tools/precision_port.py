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
PI_NOTE = ("C     PRECISION PORT: pi (and 1/3) in double precision; the "
           "original\nC     has 3.14159265 (and 0.33333333)\n")
LOGRATIO = """\
C     PRECISION PORT: contour/f0 would exceed DBL_MAX/4 (only possible
C     for f0 < 1, where HUGE/4*f0 is finite): log(contour/f0 + 1) is
C     evaluated as log(contour) - log(f0) + log1p(f0/contour), with
C     log1p(x) = x for x < 4/HUGE; a negative contour keeps the
C     sentinel, as the direct expression would give it
                  if(f0.gt.0 .and. f0.lt.1) then
                     if(abs(contour(i)).gt.0.25D0*huge(1D0)*f0) then
                        if(contour(i).gt.0) then
                           contour(i) = log(contour(i)) - log(f0)
     $                          + f0/contour(i)
                           nfit = nfit + 1
                        else
                           contour(i) = -1D10
                        end if
                        goto 120
                     end if
                  end if
"""
AVGSAFE = """\
C     PRECISION PORT: the historical sum below, unless M (the largest
C     |nonzero pixel| of the box) times the largest possible weight
C     sum exceeds HUGE/2; then the same sum of data/M, multiplied back
C     by M after the division by the weights
         pixmax = 0
         do 13 j = -navg,navg
            do 14 k= -navg,navg
               if (abs(data(ix+j,iy+k)).gt.pixmax)
     $              pixmax = abs(data(ix+j,iy+k))
 14         continue
 13      continue
         wmax = dble(2*navg+1)**2 * (4*navg+1)
         safe = pixmax.le.0.5D0*huge(1D0)/wmax
         ntot = 0
         nbadtot = 0
         pixtot = 0
         if (safe) then
         do 11 j = -navg,navg
            do 12 k= -navg,navg
               nwght = 2*(2*navg - iabs(j) - iabs(k)) + 1
               ntot = ntot + nwght
               if (data(ix+j,iy+k).eq.0) then
                  nbadtot = nbadtot + nwght
               else
                  pixtot = pixtot + nwght * data(ix+j,iy+k)
               endif
 12         continue
 11      continue
         else
         do 15 j = -navg,navg
            do 16 k= -navg,navg
               nwght = 2*(2*navg - iabs(j) - iabs(k)) + 1
               ntot = ntot + nwght
               if (data(ix+j,iy+k).eq.0) then
                  nbadtot = nbadtot + nwght
               else
                  pixtot = pixtot + nwght * (data(ix+j,iy+k)/pixmax)
               endif
 16         continue
 15      continue
         end if
C Omit a contour if more than 20% of the weights are bad.
         if (dble(nbadtot)/ntot.le.0.2D0) then
            if (safe) then
            contour(i) = pixtot/(ntot-nbadtot) - f0
            else
            contour(i) = pixmax*(pixtot/(ntot-nbadtot)) - f0
            end if
"""
BILINEAR = """\
C     PRECISION PORT (R4): the historical sum below, unless the four
C     pixels and f0 are finite and one of them exceeds HUGE/4.  Below
C     that every partial sum is at most HUGE/4 + HUGE/4*(1+4 eps), so
C     the historical arithmetic cannot overflow; above it, it can
C     (weights rounded to a sum just over 1 with pixels at +-DBL_MAX,
C     or -f0 added first).  Then: the same weighted sum P of the
C     pixels/4 (an exact scaling), clamped to [min, max] of the four
C     pixels/4 -- P is a convex combination, so only the rounding of
C     the weights can move it outside -- minus f0/4, times 4 (exact).
C     A contour beyond the double range stays +-Inf, as before.
            p00 = data(ix,iy)
            p10 = data(ix+1,iy)
            p01 = data(ix,iy+1)
            p11 = data(ix+1,iy+1)
            if(finited(p00).and.finited(p10).and.finited(p01).and.
     $           finited(p11).and.finited(f0)) then
               pbig = max(abs(p00),abs(p10),abs(p01),abs(p11),abs(f0))
            else
               pbig = 0
            end if
            if(pbig.le.0.25D0*huge(1D0)) then
            contour(i) = -f0 +
     $           (x-ix+0.5D0)*(y-iy+0.5D0)*data(ix+1,iy+1) +
     $           (ix+0.5D0-x)*(y-iy+0.5D0)*data(ix,iy+1) +
     $           (x-ix+0.5D0)*(iy+0.5D0-y)*data(ix+1,iy) +
     $           (ix+0.5D0-x)*(iy+0.5D0-y)*data(ix,iy)
            else
               pint = (x-ix+0.5D0)*(y-iy+0.5D0)*(0.25D0*p11) +
     $              (ix+0.5D0-x)*(y-iy+0.5D0)*(0.25D0*p01) +
     $              (x-ix+0.5D0)*(iy+0.5D0-y)*(0.25D0*p10) +
     $              (ix+0.5D0-x)*(iy+0.5D0-y)*(0.25D0*p00)
               pint = max(pint, 0.25D0*min(p00,p10,p01,p11))
               pint = min(pint, 0.25D0*max(p00,p10,p01,p11))
               contour(i) = 4*(pint - 0.25D0*f0)
            end if
"""
ALTEREXP = """\
C     PRECISION PORT (R5): f0*exp(d) as before when exp(d) is a finite
C     normal number.  Otherwise (exp(d) = Inf, 0 or subnormal: only for
C     |d| > 708) the product can still be representable, and a
C     subnormal exp(d) holds too few bits: then f0*e*e*e*e with
C     e = exp(d/4) (d/4 exact).  A nonzero representable result has
C     |d| <= ln(DBL_MAX/2**-1074) < 1455, so |d/4| < 364 and e is a
C     normal number; the partial products move monotonically from f0
C     to the result, so none over- or underflows unless the result
C     does (a genuine range error, reported as before).  f0 = 0,
C     non-finite f0 or d keep the historical expression.  f0 > 0 in
C     log fits (seeded from a positive pixel, only multiplied by
C     exp); the fallback would keep any sign.
         d = gain*(fcoeff(1)+fcoeff(4))
         t = exp(d)
         if(t.ge.tiny(1D0) .and. t.le.huge(1D0)) then
            f0 = f0 * t
         else if(d.eq.d .and. f0.ne.0 .and. abs(f0).le.huge(1D0)) then
            e = exp(d/4)
            f0 = f0*e
            f0 = f0*e
            f0 = f0*e
            f0 = f0*e
         else
            f0 = f0 * t
         end if
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
         " 2001 format(1x,'Re =',2f8.1,4x,'Ie =',2(1x,1pe16.8e3),4x,\n"
         "     $     'Sky =',2(1x,1pe16.8e3))\n", "print-devauc"),
        (r"WRITE\(6,\*\) K, PARAM\(1,K\), PARAM\(4,K\), FIT\+SKY\n",
         "WRITE(6,*) K, PARAM(1,K), POW2D(PARAM(4,K),KNORM),\n"
         "     $           POW2D(FIT+SKY,KNORM)\n", "print-test"),
        (r"(     \$ +)par\(4,k\),par\(5,k\)-90,",
         r"\1pow2d(par(4,k),knorm),par(5,k)-90,", "print-table", 2),
        (r" 1000       format\(f6\.1,2f8\.2,f8\.0,",
         " 1000       format(f6.1,2f8.2,1x,1pe14.6e3,0p,", "print-table-fmt"),
        (r"      write\(6,6725\) rmajor, exp\(flog\), sky, epsilon\n"
         r" 6725 format\('Extrapolated outer isophote: r,f,sky,eps =',"
         r"3f9\.1,f9\.3\)\n",
         "C     PRECISION PORT: f and sky printed in physical units\n"
         "      write(6,6725) rmajor, pow2d(exp(flog),knorm),\n"
         "     $     pow2d(sky,knorm), epsilon\n"
         " 6725 format('Extrapolated outer isophote: r,f,sky,eps =',\n"
         "     $     f9.1,2(1x,1pe16.8e3),0p,f9.3)\n", "print-extrap"),
        # constants to double precision (the original's 3.14159265 and
        # 0.33333333 are accurate to REAL*4 only); EPS of ZBRENT and the
        # other literals keep their historical values
        (r"(      parameter \(pi=)3\.14159265D0", PI_NOTE + r"\g<1>4D0*atan(1D0)",
         "pi", 5),
        (r"      q = 180/3\.14159265D0\n",
         PI_NOTE + "      q = 180/(4D0*atan(1D0))\n", "pi-q"),
        (r"third=0\.33333333D0", "third=1D0/3D0", "third"),
        # the model's range: the original keeps |ln I| < 85 (where the
        # REAL*4 EXP is finite and normal) and sets other pixels to 0;
        # in double EXP is finite up to LOG(HUGE(1D0)) and underflows
        # gradually below, so only overflow remains, and it is an error
        (r"(      external elliterpd\n)",
         r"\1C     PRECISION PORT: XERR (vistalink.inc) for the range error\n"
         r"      REAL CONST\n      include 'vistalink.inc'\n",
         "synth-xerr"),
        (r"            if\(abs\(arg\)\.lt\.85\) then\n"
         r"               data\(ix,iy\) = exp\(arg\) \+ sky\n"
         r"            else\n"
         r"               write\(6,4738\) ix, iy, arg\n"
         r" 4738          format\('Pixel at',2i5,' at exp ',1pg12\.2,"
         r"' set to 0'\)\n"
         r"               data\(ix,iy\) = 0\n"
         r"            end if\n",
         "C     PRECISION PORT: exp(arg) for every arg up to LOG(HUGE(1D0))"
         "\nC     (the original: |arg| < 85, else the pixel is set to 0);"
         "\nC     beyond, the model is not representable: an error.  An"
         "\nC     undefined arg (NaN: the log of a non-positive isophote"
         "\nC     intensity) is handled as in the original.\n"
         "            if(arg.le.log(huge(1D0))) then\n"
         "               data(ix,iy) = exp(arg) + sky\n"
         "C     PRECISION PORT: count exp(arg) underflowing to zero\n"
         "               if(data(ix,iy).eq.0) then\n"
         "                  if(exp(arg).eq.0) nunder = nunder + 1\n"
         "               end if\n"
         "            else if(arg.ne.arg) then\n"
         "               write(6,4738) ix, iy, arg\n"
         " 4738          format('Pixel at',2i5,' at exp ',1pg12.2,"
         "' set to 0')\n"
         "               data(ix,iy) = 0\n"
         "            else\n"
         "               write(0,4739) ix, iy, arg\n"
         " 4739          format('elliprof: error (double precision, ',\n"
         "     $              'model): the model at pixel',2(1x,i0),\n"
         "     $              ' is exp(',1pe12.4e3,'), beyond the ',\n"
         "     $              'double range')\n"
         "               xerr = .true.\n"
         "               return\n"
         "            end if\n", "synth-range"),
        (r"( 666  continue\n)",
         r"\1C     PRECISION PORT: a new synthesis pass counts afresh\n"
         r"      nunder = 0\n", "underflow-reset"),
        # contour/f0 can overflow for finite positive values whose ratio
        # exceeds DBL_MAX.  Only then (detected without dividing:
        # f0 < 1, so HUGE/4*f0 is finite) the logarithm is taken in the
        # log domain; every other case keeps the historical expression
        (r"(                  clog = contour\(i\)/f0 \+ 1\n)",
         LOGRATIO + r"\1", "log-ratio"),
        # the AVG box sum can overflow while the weighted average is
        # finite: only then (M * max weight sum > HUGE/2) accumulate
        # data/M and multiply back after the division
        (r"         ntot = 0\n         nbadtot = 0\n         pixtot = 0\n"
         r".*?            contour\(i\) = pixtot/\(ntot-nbadtot\) - f0\n",
         AVGSAFE, "avg-sum"),
        (r"(      subroutine getcontourd\(par,iterp,nstep,contour,nx,ny,"
         r"data,navg\)\n      IMPLICIT DOUBLE PRECISION \(A-H,O-Z\)\n)",
         r"\1C     PRECISION PORT: the AVG range test, the R4 finite test\n"
         r"      LOGICAL SAFE, FINITED\n", "avg-logical"),
        # R4: the bilinear sum (NAVG = 0) can overflow for finite pixels
        # within HUGE/4 of DBL_MAX while the interpolation is finite:
        # only there (predicted, before any Inf) the same sum on the
        # pixels/4, clamped to their hull, minus f0/4, times 4
        (r"            contour\(i\) = -f0 \+ \n"
         r"     \$           \(x-ix\+0\.5D0\)\*\(y-iy\+0\.5D0\)\*"
         r"data\(ix\+1,iy\+1\) \+ \n"
         r"     \$           \(ix\+0\.5D0-x\)\*\(y-iy\+0\.5D0\)\*"
         r"data\(ix,iy\+1\) \+ \n"
         r"     \$           \(x-ix\+0\.5D0\)\*\(iy\+0\.5D0-y\)\*"
         r"data\(ix\+1,iy\) \+ \n"
         r"     \$           \(ix\+0\.5D0-x\)\*\(iy\+0\.5D0-y\)\*"
         r"data\(ix,iy\)\n",
         lambda m: BILINEAR, "bilinear-range"),
        # R5: f0*exp(d) of a log fit, when exp(d) is not a finite
        # normal number although the product can be
        (r"         f0 = f0 \* exp\(gain\*\(fcoeff\(1\)\+fcoeff\(4\)\)\)\n",
         lambda m: ALTEREXP, "alter-exp"),
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
