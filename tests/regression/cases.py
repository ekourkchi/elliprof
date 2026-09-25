"""Deterministic regression cases, shared by the generator, the tests,
the baseline updater and the cross-platform collector.

Each synthetic image is an r^(1/4) (de Vaucouleurs) galaxy

    I(r) = Ie * exp(-7.669 * ((r / Re)**0.25 - 1)) + sky,
    r = sqrt(u**2 + (v / q)**2),  (u, v) = rotated by PA from +x,

sampled at pixel centres in ELLIPROF's convention (the centre of the
0-based array element [j, i] is at x = i + 0.5, y = j + 0.5).  The
images are generated once by make_synthetic.py and stored in
tests/data/regression/, so every platform fits exactly the same bytes.
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = ROOT / "tests" / "data" / "regression"
BASELINE = ROOT / "tests" / "regression" / "baseline"
EXAMPLE = ROOT / "examples" / "u12517"

SIZE = (200, 200)          # ncol, nrow
FIT = dict(r0=3, r1=80, nr=25, niter=5)

# truth: galaxy centre (ELLIPROF coordinates), q = b/a, pa = major axis
# angle in degrees CCW from +x, Re, Ie, sky
BASE = dict(x0=100.3, y0=99.6, re=15.0, ie=300.0, q=0.7, pa=30.0, sky=0.0)

CASES = {
    "circular": dict(truth=dict(BASE, q=1.0, pa=0.0),
                     run=dict(center=(100.3, 99.6))),
    "elliptical": dict(truth=dict(BASE, q=0.6, pa=0.0),
                       run=dict(center=(100.3, 99.6))),
    "rotated": dict(truth=dict(BASE, q=0.6, pa=55.0),
                    run=dict(center=(100.3, 99.6))),
    "offcenter": dict(truth=dict(BASE, x0=70.4, y0=120.9),
                      run=dict(center=(70.4, 120.9), r1=60)),
    "const_sky": dict(truth=dict(BASE, sky=250.0),
                      run=dict(center=(100.3, 99.6), sky=250.0)),
    "sky_image": dict(truth=dict(BASE, sky="gradient"),
                      run=dict(center=(100.3, 99.6), sky_image="SKY")),
    "star_nomask": dict(truth=dict(BASE, star=(150.0, 60.0)),
                        run=dict(center=(100.3, 99.6)), image="star"),
    "star_mask": dict(truth=dict(BASE, star=(150.0, 60.0)),
                      run=dict(center=(100.3, 99.6), mask="MASK"),
                      image="star"),
    "noisy": dict(truth=dict(BASE, sky=50.0, noise=2.0),
                  run=dict(center=(100.3, 99.6), sky=50.0)),
    "model": dict(truth=BASE, run=dict(center=(100.3, 99.6), model=True)),
}

# The real example (not a truth test; structure + baseline only)
U12517 = dict(image=EXAMPLE / "u12517j.fits",
              run=dict(x0=567, y0=562, sky=3246.0,
                       mask=EXAMPLE / "u12517j.dmask", r0=9, r1=347, nr=23,
                       niter=10, rmstar=True))


def image_path(name: str) -> Path:
    return DATA / f"{CASES[name].get('image', name)}.fits"


def run_kwargs(name: str) -> dict:
    """Keyword arguments for run_elliprof for a case."""
    case = CASES[name]
    kw = dict(FIT)
    kw.update(case["run"])
    kw["x0"], kw["y0"] = kw.pop("center")
    if kw.get("sky_image") == "SKY":
        kw["sky_image"] = DATA / f"{name}_sky.fits"
    if kw.get("mask") == "MASK":
        kw["mask"] = DATA / "star.dmask"
    return kw


def all_runs():
    """(name, image, kwargs) for every case including u12517."""
    for name in CASES:
        yield name, image_path(name), run_kwargs(name)
    if U12517["image"].is_file():
        yield "u12517", U12517["image"], dict(U12517["run"])
