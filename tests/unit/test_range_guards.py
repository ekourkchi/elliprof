"""Range protections of the double backend, on its own routines.

build/rangeprobe calls GETCONTOURD, ALTERD and EXPSC2D linked from the
objects of elliprof_native.  Each protection keeps the historical
arithmetic wherever it cannot leave the double range, and replaces it
only where it would give 0, a subnormal or Inf although the exact result
is representable:

* R4  bilinear sample (NAVG = 0): -f0 + sum of weights*pixels, which
      can overflow for pixels and f0 within HUGE/4 of DBL_MAX;
* R5  log-fit I0 update f0*exp(d), with exp(d) itself beyond the
      normal range;
* R6  model value exp(arg)*2**k in physical units (EXPSC2D).

References are exact (fractions) or 90-digit (decimal).  The historical
expressions are replayed in Python, whose float arithmetic is the same
IEEE binary64 arithmetic in the same order (no fused operations; the
backend is built with -ffp-contract=off).
"""

import math
import random
import struct
import subprocess
import sys
from decimal import Decimal, localcontext
from fractions import Fraction

import pytest

pytestmark = pytest.mark.native

MAX = sys.float_info.max
TINY = sys.float_info.min            # smallest normal
SUB = 5e-324                         # smallest subnormal
Q = 0.25 * MAX


def h(v):
    return "%016x" % struct.unpack("<Q", struct.pack("<d", v))[0]


def unh(s):
    return struct.unpack("<d", struct.pack("<Q", int(s, 16)))[0]


def run(probe, lines):
    text = "".join(t + " " + "".join(" " + h(v) for v in
                                     (list(vals) + [0.0] * 7)[:7]) + "\n"
                   for t, vals in lines)
    out = subprocess.run([str(probe)], input=text, stdout=subprocess.PIPE,
                         universal_newlines=True, check=True).stdout.split()
    assert len(out) == len(lines)
    return [unh(s) for s in out]


def to_double(q):
    """Exact rational or Decimal -> nearest binary64 (or +-Inf)."""
    try:
        return float(q)
    except OverflowError:
        return math.inf if q > 0 else -math.inf


def same(a, b):
    return a == b or (a != a and b != b)


def nint(x):                                   # Fortran NINT
    return int(math.floor(abs(x) + 0.5)) * (1 if x >= 0 else -1)


# ---- R4 -----------------------------------------------------------------

def weights(x, y):
    ix, iy = nint(x), nint(y)
    return ((x - ix + 0.5) * (y - iy + 0.5), (ix + 0.5 - x) * (y - iy + 0.5),
            (x - ix + 0.5) * (iy + 0.5 - y), (ix + 0.5 - x) * (iy + 0.5 - y))


def bilinear_historical(x, y, p00, p10, p01, p11, f0):
    w11, w01, w10, w00 = weights(x, y)
    return -f0 + w11 * p11 + w01 * p01 + w10 * p10 + w00 * p00


def bilinear_exact(x, y, p00, p10, p01, p11, f0):
    ix, iy = nint(x), nint(y)
    fx, gx = Fraction(x) - ix + Fraction(1, 2), ix + Fraction(1, 2) - Fraction(x)
    fy, gy = Fraction(y) - iy + Fraction(1, 2), iy + Fraction(1, 2) - Fraction(y)
    return (fx * fy * Fraction(p11) + gx * fy * Fraction(p01)
            + fx * gy * Fraction(p10) + gx * gy * Fraction(p00) - Fraction(f0))


M, M1 = MAX, math.nextafter(MAX, 0)
M2 = math.nextafter(M1, 0)
E = 1e-12
POSITIONS = [(4.5 + E, 4.5 + E), (5.5 - 2 * E, 5.5 - 2 * E), (5.0, 5.0),
             (4.5 + E, 5.5 - 2 * E), (4.8, 5.2), (4.75, 4.75)]
PIXELS = [
    [M] * 4, [M1] * 4, [M2] * 4, [0.9 * M] * 4, [1e308] * 4,
    [-M] * 4, [-0.9 * M] * 4, [M, -M, -M, M], [0.9 * M, -0.9 * M, -0.9 * M, 0.9 * M],
    [M, M, -M, -M], [M, 1.0, 1.0, 1.0], [1e-300, 1e-300, 1e-300, M],
    [1e300, 1e300, -M, 1e300], [1e-300, 1e300, 1e-300, 1e300],
    [-1e300, 1e-300, 1e300, -1e-300], [M, SUB, TINY, 1e-300],
    [Q] * 4, [math.nextafter(Q, M)] * 4]
F0S = [0.0, SUB, -SUB, 1e-300, 1.0, 1e300, 0.5 * M, M, -1e300, -0.5 * M, -M]


def test_r4_adversarial(rangeprobe):
    """+-DBL_MAX-like pixels, mixed signs, f0 large positive / negative /
    near zero, fractions near 0, 0.5 and 1: never an avoidable Inf, never
    a fabricated finite value, error at the rounding level."""
    cases = [(x, y, *p, f0) for p in PIXELS for x, y in POSITIONS
             for f0 in F0S]
    got = run(rangeprobe, [("B", c) for c in cases])
    avoidable = fabricated = 0
    worst = 0.0
    for c, g in zip(cases, got):
        exact = bilinear_exact(*c)
        r = to_double(exact)
        big = max(abs(Fraction(v)) for v in c[2:])
        if not math.isfinite(r):
            fabricated += math.isfinite(g)
            continue
        if not math.isfinite(g):
            avoidable += 1
            continue
        worst = max(worst, float(abs(Fraction(g) - exact) / big))
        if max(abs(v) for v in c[2:]) <= Q:   # historical path
            assert same(g, bilinear_historical(*c)), c
    assert avoidable == 0 and fabricated == 0
    # four products and four sums: a few half-ulps of the largest input
    assert worst <= 2 ** -51


def test_r4_original_expression_overflows_here():
    """The cases are adversarial: the historical sum overflows for some
    of them although the exact contour is finite (17 of the 576 cases of
    the R4 report; the clamp is needed for the first kind)."""
    n = 0
    for p in ([M] * 4, [M1] * 4):
        for x, y in POSITIONS:
            c = (x, y, *p, 0.0)
            if not math.isfinite(bilinear_historical(*c)) and \
                    math.isfinite(to_double(bilinear_exact(*c))):
                n += 1
    assert n > 0


@pytest.mark.parametrize("pixels", [[M] * 4, [M1] * 4, [-M] * 4,
                                    [M, -M, -M, M], [M, M, -M, -M]])
def test_r4_random_positions_near_dblmax(rangeprobe, pixels):
    rng = random.Random(11)
    pts = [(rng.uniform(4.5, 5.49), rng.uniform(4.5, 5.49))
           for _ in range(20000)]
    got = run(rangeprobe, [("B", (x, y, *pixels, 0.0)) for x, y in pts])
    assert all(min(pixels) <= g <= max(pixels) for g in got)


def test_r4_ordinary_inputs_unchanged(rangeprobe):
    rng = random.Random(12)
    cases = []
    for _ in range(20000):
        p = [rng.choice((1, 1, 1, -1)) * 10 ** rng.uniform(-300, 300)
             for _ in range(4)]
        cases.append((rng.uniform(1.5, 10.4), rng.uniform(1.5, 10.4), *p,
                      rng.choice((1, -1)) * 10 ** rng.uniform(-300, 300)))
    got = run(rangeprobe, [("B", c) for c in cases])
    assert all(same(g, bilinear_historical(*c)) for c, g in zip(cases, got))


# ---- R5 -----------------------------------------------------------------

def alter_historical(f0, d):
    try:
        t = math.exp(d)
    except OverflowError:
        t = math.inf
    return f0 * t


def times_exp(f0, d):
    with localcontext() as ctx:
        ctx.prec = 90
        return to_double(Decimal(f0) * Decimal(d).exp())


LN_TINY, LN_MAX = math.log(TINY), math.log(MAX)
R5_F0 = [M, 1e300, 1e100, 1.0, 1e-100, 1e-300, TINY, 1e-310, SUB]
R5_D = [-1500, -1454, -1400, -1000, -800, -745.2, -745.1, -740, -720, -709,
        -708.4, -708, -700, -100, 0.0, 100, 700, 709, 709.78, 709.8, 720,
        800, 1000, 1400, 1454, 1500,
        math.nextafter(LN_TINY, -math.inf), LN_TINY,
        math.nextafter(LN_TINY, math.inf), -745.13321910194122, -745.14,
        math.nextafter(LN_MAX, -math.inf), LN_MAX,
        math.nextafter(LN_MAX, math.inf), 1454.3, 1454.4, -1454.3, -1454.4,
        2839, -2979]


def test_r5_against_reference(rangeprobe):
    """Every representable f0*exp(d) within 4 ulp (the historical update
    gives Inf, 0 or a factor-2 error for 60 of these cases); genuine
    overflow / underflow stay Inf / 0."""
    cases = [(f0, float(d)) for f0 in R5_F0 for d in R5_D]
    got = run(rangeprobe, [("A", (f0, 1.0, d, 0.0)) for f0, d in cases])
    wrong_before = 0
    for (f0, d), g in zip(cases, got):
        r = times_exp(f0, d)
        if r == 0 or not math.isfinite(r):
            assert g == r, (f0, d, g, r)
            continue
        assert abs(g - r) <= 4 * math.ulp(r), (f0, d, g, r)
        h_ = alter_historical(f0, d)
        wrong_before += not (math.isfinite(h_) and h_ != 0
                             and abs(h_ - r) <= 4 * math.ulp(r))
        if LN_TINY <= d <= LN_MAX:
            assert same(g, h_), (f0, d)            # historical path
    assert wrong_before >= 44


def test_r5_ordinary_updates_unchanged(rangeprobe):
    rng = random.Random(5)
    cases = [(10 ** rng.uniform(-300, 300), rng.uniform(-708, 708))
             for _ in range(20000)]
    got = run(rangeprobe, [("A", (f0, 1.0, d, 0.0)) for f0, d in cases])
    assert all(same(g, alter_historical(f0, d))
               for (f0, d), g in zip(cases, got))


@pytest.mark.parametrize("f0,d", [
    (0.0, -800), (0.0, 800), (0.0, math.nan), (math.nan, 10),
    (math.nan, -800), (math.inf, -800), (-math.inf, 800), (1.0, math.nan),
    (1e-300, math.inf), (1e300, -math.inf), (math.inf, 1.0)])
def test_r5_invalid_inputs_keep_the_historical_result(rangeprobe, f0, d):
    """f0 = 0, non-finite f0 or d: never turned into a number."""
    assert same(run(rangeprobe, [("A", (f0, 1.0, d, 0.0))])[0],
                alter_historical(f0, d))


def test_r5_sign_is_kept(rangeprobe):
    # f0 > 0 in log fits; the fallback would still keep a sign
    g = run(rangeprobe, [("A", (-1e300, 1.0, -800.0, 0.0)),
                         ("A", (-1e-300, 1.0, 800.0, 0.0))])
    assert g[0] < 0 and abs(g[0] - times_exp(-1e300, -800.0)) <= \
        4 * math.ulp(g[0])
    assert g[1] < 0 and abs(g[1] - times_exp(-1e-300, 800.0)) <= \
        4 * math.ulp(g[1])


# ---- R6 -----------------------------------------------------------------

def exp_times_pow2(arg, k):
    with localcontext() as ctx:
        ctx.prec = 90
        return to_double(Decimal(arg).exp() * Decimal(2) ** k)


def test_expsc2d_against_reference(rangeprobe):
    """exp(arg)*2**k for k = 0, +-1, odd, large of both signs, near the
    normalization limits (|k| <= 1073), and results near DBL_MAX, near
    the smallest normal, subnormal and below the smallest subnormal."""
    ks = [0, 1, -1, 2, -2, 3, -3, 5, -7, 101, -101, 500, -500, 802, -802,
          997, -997, 1023, -1023, 1024, -1073, 1073]
    cases = []
    for k in ks:
        base = -k * math.log(2)
        for target in (709.7, 709.78, 709.79, 300, 1, 0, -300, -708.3,
                       -708.4, -720, -744.4, -745.1, -745.2, -800):
            cases.append((base + target, k))
    rng = random.Random(6)
    cases += [(rng.uniform(-1500, 1500), rng.randint(-1073, 1073))
              for _ in range(5000)]
    got = run(rangeprobe, [("E", (a, float(k))) for a, k in cases])
    for (a, k), g in zip(cases, got):
        r = exp_times_pow2(a, k)
        if r == 0 or not math.isfinite(r):
            # beyond the range (or rounding to its edge)
            assert g == r or abs(g) <= 2 * SUB or abs(g) >= M1, (a, k, g, r)
        elif abs(r) < TINY:
            assert abs(g - r) <= 2 * SUB, (a, k, g, r)     # subnormal
        else:
            assert abs(g - r) <= 5 * math.ulp(r), (a, k, g, r)
