"""The Python `elliprof` command and API: argument parsing and input
validation (these fail before the backend is started)."""

import numpy as np
import pytest

from elliprof import cli
from elliprof.core import elliprof_keywords, validate_keywords
from helpers import write_fits

FIT = ["R0=1", "R1=5", "NR=3"]


def run(capsys, *argv):
    code = cli.main(list(map(str, argv)))
    out = capsys.readouterr()
    return code, out.out, out.err


@pytest.fixture
def img(tmp_path):
    return write_fits(tmp_path / "img.fits", np.ones((20, 30)))


def test_help(capsys):
    code, out, _ = run(capsys, "--help")
    assert code == 0 and "usage: elliprof image.fits X0=x Y0=y" in out
    assert "monsta" not in out.lower()


def test_version(capsys):
    from elliprof import __maintainer__, __version__
    code, out, _ = run(capsys, "--version")
    assert code == 0
    assert out.startswith(f"elliprof {__version__} (maintained by {__maintainer__})\n")


def test_diagnostics(capsys):
    code, out, _ = run(capsys, "--diagnostics")
    assert code == 0
    for key in ("elliprof version", "Python", "OS", "architecture",
                "native backend"):
        assert key in out
    # ignore where this checkout happens to live on disk
    from helpers import ROOT
    text = out.replace(str(ROOT.parent), "<dir>").lower()
    assert "monsta" not in text


def test_no_image(capsys):
    code, _, err = run(capsys)
    assert code == 2 and "usage" in err


@pytest.mark.parametrize("words", [FIT, ["X0=5"] + FIT, ["Y0=5"] + FIT])
def test_center_is_required(words, img, capsys):
    code, _, err = run(capsys, img, *words)
    assert code == 2 and "error: X0 and Y0 are required" in err


@pytest.mark.parametrize("argv,message", [
    (["--bogus"], "unknown option --bogus"),
    (["--mask"], "--mask needs a value"),
    (["--sky", "1", "--sky", "2"], "more than once"),
    (["--sky", "1", "--sky-image", "x.fits"],
     "--sky and --sky-image cannot be used together"),
    (["--timeout", "soon"], "--timeout needs a number"),
    (["--center-radec", "1", "2"], "unknown option --center-radec"),
    (["--center-physical", "1", "2"], "unknown option --center-physical"),
])
def test_usage_errors(argv, message, img, capsys):
    code, _, err = run(capsys, img, "X0=5", "Y0=5", *FIT, *argv)
    assert code == 2 and message in err


@pytest.mark.parametrize("words,message", [
    (["X0=nan", "Y0=5"], "X0 must be a finite number"),
    (["X0=5", "Y0=inf"], "Y0 must be a finite number"),
    (["X0=abc", "Y0=5"], "X0 must be a number"),
    (["X0=5", "Y0=5", "R0=5", "R1=5", "NR=3"], "0 < R0 < R1"),
    (["X0=5", "Y0=5", "R0=-1", "R1=5", "NR=3"], "0 < R0 < R1"),
    (["X0=5", "Y0=5", "R0=1", "R1=5", "NR=1"], "between 2 and 100"),
    (["X0=5", "Y0=5", "R0=1", "R1=5", "NR=101"], "between 2 and 100"),
    (["X0=5", "Y0=5", "R0=1", "R1=5", "NR=2.5"], "between 2 and 100"),
    (["X0=5", "Y0=5", "R0=1", "R1=5", "NR=nan"], "NR must be a finite"),
    (["X0=5", "Y0=5", *FIT, "NITER=0"], "NITER must be an integer"),
    (["X0=5", "Y0=5", *FIT, "NITER=2000"], "NITER must be an integer"),
    (["X0=5", "Y0=5", "R0=1", "NR=3"], "missing required fit parameters"),
    (["X0=5", "Y0=5", *FIT, "OLD"], "OLD is not supported"),
    (["X0=5", "Y0=5", *FIT, "edit"], "EDIT is not supported"),
    (["X0=5", "Y0=5", *FIT, "TV"], "TV is not supported"),
])
def test_validation_errors(words, message, img, capsys):
    code, _, err = run(capsys, img, *words)
    assert code == 1 and message in err, err


@pytest.mark.parametrize("argv,message", [
    (["--sky", "x"], "sky must be a number"),
    (["--sky", "nan"], "sky must be a finite number"),
    (["--mask", "{missing}"], "mask not found"),
    (["--sky-image", "{missing}"], "sky image not found"),
])
def test_input_file_errors(argv, message, img, tmp_path, capsys):
    argv = [a.format(missing=tmp_path / "missing.fits") for a in argv]
    code, _, err = run(capsys, img, "X0=5", "Y0=5", *FIT, *argv)
    assert code == 1 and message in err, err


def test_missing_image_file(capsys, tmp_path):
    code, _, err = run(capsys, tmp_path / "nope.fits", "X0=5", "Y0=5", *FIT)
    assert code == 1 and "image not found" in err


def test_invalid_image_file(capsys, tmp_path):
    bad = tmp_path / "bad.fits"
    bad.write_text("nope")
    code, _, err = run(capsys, bad, "X0=5", "Y0=5", *FIT)
    assert code == 1 and "not a readable FITS" in err


def test_keyword_builder():
    words = elliprof_keywords(r0=9, r1=347.0, nr=23, niter=10, rmstar=True,
                              cos3x=0, elliprof_sky=12.5, model=True)
    assert words == ["R0=9", "R1=347.0", "NR=23", "NITER=10", "SKY=12.5",
                     "COS3X=0", "MODEL", "RMSTAR"]


@pytest.mark.parametrize("words,message", [
    (["R0=1", "R1=2", "NR=3", "X0=4"], "x0=, y0="),
    (["GC"], "missing required fit parameters: NR"),
    (["R0=1", "R1=2", "NR=3"] + ["TEST"] * 12, "at most 16 keywords"),
])
def test_keyword_validation(words, message):
    with pytest.raises(ValueError, match=message.replace("(", r"\(")):
        validate_keywords(words)


def test_gc_needs_only_nr():
    validate_keywords(["GC", "NR=5"])


def test_api_requires_center(img):
    from elliprof import run_elliprof
    with pytest.raises(TypeError):
        run_elliprof(img, r0=1, r1=5, nr=3)
    with pytest.raises(ValueError, match="finite"):
        run_elliprof(img, float("nan"), 5, r0=1, r1=5, nr=3)


def test_api_has_no_center_conversion():
    import inspect

    import elliprof
    for name in ("resolve_center", "radec_to_image", "physical_to_image",
                 "image_center", "center_radec", "center_physical"):
        assert not hasattr(elliprof, name)
    params = inspect.signature(elliprof.run_elliprof).parameters
    assert "center_radec" not in params and "center_physical" not in params
