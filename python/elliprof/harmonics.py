"""Harmonic settings: the original ELLIPROF ``COS3X=`` / ``COS4X=`` modes.

What ELLIPROF does (src/original/elliprof.f, the original code):

* Every isophote is fitted with a constant plus the cos/sin of 1, 2, 3
  and 4 times the eccentric angle along the ellipse -- always all nine
  terms.  Orders 1-2 update the centre, ellipticity and angle; orders 3
  and 4 are measured and reported (I3, A3, I4, A4) but never change the
  ellipse.  No setting leaves the 3rd- or 4th-order terms out of the fit.
* ``COS3X`` and ``COS4X`` (integers, default 2) choose how those measured
  terms go into the MODEL image: 0 = not at all, 1 = the median over all
  isophotes, 2 = each isophote's own value.
* A negative ``COS3X`` (-1, -2) fits and models the 6th-order term in
  place of the 3rd: this is the only setting that changes the fit.  The
  I3/A3 columns then hold the 6th-order amplitude and phase.

The friendlier options below translate into exactly these values.
"""

from typing import Iterable, Optional, Tuple, Union

MODES = {"each": 2, "median": 1}
COS3X_RANGE = (-2, 2)
COS4X_RANGE = (0, 2)


def _int_in(value, name, lo, hi) -> int:
    try:
        f = float(value)
    except (TypeError, ValueError):
        f = float("nan")
    if isinstance(value, bool) or f != f or f != int(f) or not lo <= f <= hi:
        raise ValueError(f"{name} must be an integer from {lo} to {hi}, "
                         f"got {value!r}")
    return int(f)


def parse_model_harmonics(value: Union[None, str, Iterable]) -> Optional[
        Tuple[int, ...]]:
    """``"none"``, ``"3"``, ``"4"``, ``"3,4"`` or a sequence of 3/4 ->
    a sorted tuple of harmonic orders (``()`` for none)."""
    if value is None:
        return None
    if isinstance(value, str):
        text = value.strip().lower()
        items = [] if text in ("none", "") else text.split(",")
    elif isinstance(value, int):
        items = [value]
    else:
        items = list(value)
    orders = set()
    for item in items:
        try:
            order = int(str(item).strip())
        except ValueError:
            order = None
        if order not in (3, 4):
            raise ValueError("model harmonics must be 'none', 3, 4 or 3,4 "
                             f"(ELLIPROF has only these), got {value!r}")
        orders.add(order)
    return tuple(sorted(orders))


def harmonic_settings(model_harmonics=None, harmonic_mode=None,
                      sixth_order=False, cos3x=None, cos4x=None
                      ) -> Tuple[Optional[int], Optional[int]]:
    """Return ``(COS3X, COS4X)`` for ELLIPROF, or ``None`` for a keyword
    that is not needed (ELLIPROF's own default then applies: 2 and 2).

    Either give the original ``cos3x``/``cos4x`` values, or use
    ``model_harmonics`` (which measured terms go into the model image:
    ``()``, ``(3,)``, ``(4,)``, ``(3, 4)``; default ``(3, 4)``),
    ``harmonic_mode`` (``"each"``, default, or ``"median"``) and
    ``sixth_order`` (fit the 6th-order term instead of the 3rd).
    """
    friendly = (model_harmonics is not None or harmonic_mode is not None
                or bool(sixth_order))
    if friendly and (cos3x is not None or cos4x is not None):
        raise ValueError("give either COS3X/COS4X or the model-harmonics / "
                         "harmonic-mode / sixth-order options, not both")
    if not friendly:
        c3 = None if cos3x is None else _int_in(cos3x, "COS3X", *COS3X_RANGE)
        c4 = None if cos4x is None else _int_in(cos4x, "COS4X", *COS4X_RANGE)
        return c3, c4
    orders = parse_model_harmonics(model_harmonics)
    if orders is None:
        orders = (3, 4)
    mode = "each" if harmonic_mode is None else str(harmonic_mode).lower()
    if mode not in MODES:
        raise ValueError("harmonic mode must be 'each' or 'median', got "
                         f"{harmonic_mode!r}")
    m = MODES[mode]
    c3 = m if 3 in orders else 0
    c4 = m if 4 in orders else 0
    if sixth_order:
        if c3 == 0:
            raise ValueError(
                "the 6th-order term takes the place of the 3rd-order one, "
                "and ELLIPROF has no setting that fits it but leaves it out "
                "of the model: include 3 in the model harmonics")
        c3 = -c3
    return c3, c4
