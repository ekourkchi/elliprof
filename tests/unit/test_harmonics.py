"""Harmonic options -> ELLIPROF's COS3X/COS4X (no backend needed)."""

import pytest

from elliprof import harmonic_settings
from elliprof.core import elliprof_keywords, validate_keywords

# (options, expected (COS3X, COS4X)); None = keyword not passed, so
# ELLIPROF's own default (2, 2) applies, exactly as in 0.1.0
MAPPING = [
    ({}, (None, None)),
    ({"model_harmonics": "none"}, (0, 0)),
    ({"model_harmonics": ()}, (0, 0)),
    ({"model_harmonics": "3"}, (2, 0)),
    ({"model_harmonics": (3,)}, (2, 0)),
    ({"model_harmonics": "4"}, (0, 2)),
    ({"model_harmonics": 4}, (0, 2)),
    ({"model_harmonics": "3,4"}, (2, 2)),
    ({"model_harmonics": (4, 3)}, (2, 2)),
    ({"harmonic_mode": "median"}, (1, 1)),
    ({"model_harmonics": "4", "harmonic_mode": "median"}, (0, 1)),
    ({"model_harmonics": "3", "harmonic_mode": "MEDIAN"}, (1, 0)),
    ({"sixth_order": True}, (-2, 2)),
    ({"sixth_order": True, "harmonic_mode": "median"}, (-1, 1)),
    ({"sixth_order": True, "model_harmonics": "3"}, (-2, 0)),
    ({"cos3x": -2, "cos4x": 1}, (-2, 1)),
    ({"cos3x": 0}, (0, None)),
    ({"cos4x": "2"}, (None, 2)),
]


@pytest.mark.parametrize("opts,expected", MAPPING)
def test_mapping(opts, expected):
    assert harmonic_settings(**opts) == expected


@pytest.mark.parametrize("opts", [
    {"model_harmonics": "5"}, {"model_harmonics": (3, 5)},
    {"model_harmonics": "2"}, {"model_harmonics": "3;4"},
    {"harmonic_mode": "mean"},
    {"sixth_order": True, "model_harmonics": "4"},
    {"sixth_order": True, "model_harmonics": "none"},
    {"cos3x": 3}, {"cos3x": -3}, {"cos3x": 1.5}, {"cos3x": "x"},
    {"cos3x": True}, {"cos4x": -1}, {"cos4x": 3},
    {"cos3x": 1, "model_harmonics": "3"}, {"cos4x": 1, "sixth_order": True},
])
def test_invalid(opts):
    with pytest.raises(ValueError):
        harmonic_settings(**opts)


def test_keywords_validated():
    base = elliprof_keywords(r0=3, r1=80, nr=25)
    for good in ("COS3X=-2", "COS3X=2", "COS4X=0", "cos4x=2", "COS3X=1.0"):
        validate_keywords(base + [good])
    for bad in ("COS3X=3", "COS3X=-3", "COS4X=-1", "COS4X=0.5", "COS3X=a"):
        with pytest.raises(ValueError, match="must be an integer"):
            validate_keywords(base + [bad])
