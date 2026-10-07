"""Harmonic settings: the original ELLIPROF ``COS3X=`` / ``COS4X=`` modes.

What ELLIPROF does (src/original/elliprof.f; see docs/concepts/harmonics.md):

* Every isophote is fitted by least squares with nine terms at once: a
  constant, cos/sin of 1, 2 and 4 times the eccentric angle, and cos/sin
  of either 3 times it (``COS3X >= 0``) or 6 times it (``COS3X < 0``;
  FITCONTOUR).  Only orders 0-2 move the ellipse (ALTER); the 3rd/6th
  and 4th orders are measured and reported (I3, A3, I4, A4).  Because
  all nine terms are solved together, the 3rd/6th-order choice can still
  shift the fitted geometry slightly where an ellipse is poorly sampled.
* ``|COS3X|`` and ``COS4X`` choose how the measured term goes into the
  model image (SYNTHESIZE): 0 = not at all, 1 = the median over all
  isophotes, 2 = each isophote's own value.  They never change the fit.
* Supported values: COS3X 2, 1, 0 (3rd order) and -2, -1, -3 (6th
  order: each, median, none); COS4X 2, 1, 0.  In 6th-order mode the I3/A3
  columns hold the 6th-order amplitude and twice its phase.

The descriptive options below translate into exactly these values.
"""

from typing import Iterable, Optional, Tuple, Union

MODES = {"each": 2, "median": 1}
COS3X_RANGE = (-3, 2)
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


def parse_model_harmonics(value: Union[None, str, Iterable],
                          sixth_order: bool = False) -> Optional[
        Tuple[int, ...]]:
    """``"none"``, ``"3"``, ``"4"``, ``"3,4"`` or a sequence of 3/4 ->
    a sorted tuple of harmonic orders (``()`` for none).  With
    ``sixth_order`` the 6th order takes the place of the 3rd, and may be
    written 6 (``"6"``, ``"4,6"``); 3 then means the same slot."""
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
        if order == 6 and sixth_order:
            order = 3                   # the 6th order uses the 3rd's slot
        if order not in (3, 4):
            if order == 6:
                raise ValueError("model harmonic 6 needs --sixth-order "
                                 "(sixth_order=True)")
            raise ValueError("model harmonics must be 'none', 3, 4 or 3,4 "
                             "(with --sixth-order: 6, 4 or 4,6), got "
                             f"{value!r}")
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
    ``sixth_order`` (fit the 6th-order term instead of the 3rd; with no
    3rd/6th order in the model this is ``COS3X=-3``, measurement only).
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
    orders = parse_model_harmonics(model_harmonics, bool(sixth_order))
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
        c3 = -3 if c3 == 0 else -c3     # -3: measure the 6th order only
    return c3, c4
