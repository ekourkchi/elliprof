"""The Python `elliprof` command: argument parsing and input checks
(no fit needed for most of these)."""

import pytest

from elliprof import cli
from elliprof.core import elliprof_keywords, validate_keywords


def run(capsys, *argv):
    code = cli.main(list(map(str, argv)))
    out = capsys.readouterr()
    return code, out.out, out.err


def test_help(capsys):
    code, out, _ = run(capsys, "--help")
    assert code == 0 and "usage: elliprof image.fits" in out


def test_version(capsys):
    from elliprof import __version__
    code, out, _ = run(capsys, "--version")
    assert code == 0 and out.startswith(f"elliprof {__version__}\n")


def test_diagnostics(capsys):
    code, out, _ = run(capsys, "--diagnostics")
    assert code == 0
    for key in ("elliprof version", "Python", "OS", "architecture",
                "native backend"):
        assert key in out


def test_no_image(capsys):
    code, _, err = run(capsys)
    assert code == 2 and "usage" in err


@pytest.mark.parametrize("argv,message", [
    (["img.fits", "--bogus"], "unknown option --bogus"),
    (["img.fits", "--mask"], "--mask needs a value"),
    (["img.fits", "--center-radec", "1"], "needs two values"),
    (["img.fits", "--sky", "1", "--sky", "2"], "more than once"),
    (["img.fits", "X0=5", "R0=1"], "must be given together"),
    (["img.fits", "X0=a", "Y0=1"], "must be numbers"),
])
def test_usage_errors(argv, message, capsys):
    code, _, err = run(capsys, *argv)
    assert code == 2 and message in err


def test_missing_image_file(capsys, tmp_path):
    code, _, err = run(capsys, tmp_path / "nope.fits", "R0=1", "R1=2",
                       "NR=2")
    assert code == 1 and "image not found" in err


def test_invalid_image_file(capsys, tmp_path):
    bad = tmp_path / "bad.fits"
    bad.write_text("nope")
    code, _, err = run(capsys, bad, "R0=1", "R1=2", "NR=2")
    assert code == 1 and "not a readable FITS" in err


@pytest.fixture
def img(tmp_path):
    from helpers import write_fits
    import numpy as np
    return write_fits(tmp_path / "img.fits", np.ones((20, 30)))


@pytest.mark.parametrize("argv,message", [
    (["--sky", "1", "--sky-image", "{sky}"], "not both"),
    (["--sky", "x"], "--sky needs a number"),
    (["--mask", "{missing}"], "mask not found"),
    (["--sky-image", "{missing}"], "sky image not found"),
    (["X0=1", "Y0=1", "--center-physical", "1", "1"], "only one of"),
    (["--center-physical", "1", "1", "--center-radec", "1", "1"],
     "only one of"),
    (["--center-radec", "10", "10"], "no celestial WCS"),
    (["OLD"], "OLD is not supported"),
    (["EDIT"], "EDIT is not supported"),
])
def test_input_errors(argv, message, img, tmp_path, capsys):
    from helpers import write_fits
    import numpy as np
    sky = write_fits(tmp_path / "sky.fits", np.zeros((20, 30)))
    argv = [a.format(sky=sky, missing=tmp_path / "missing.fits")
            for a in argv]
    code, _, err = run(capsys, img, "R0=1", "R1=5", "NR=3", *argv)
    assert code != 0 and message in err, err


def test_missing_fit_parameters(img, capsys):
    code, _, err = run(capsys, img, "R0=1", "NR=3")
    assert code == 1 and "missing required fit parameters: r1" in err


def test_mask_size_mismatch(img, tmp_path, capsys):
    import numpy as np
    from elliprof.masks import write_bitmap_mask
    write_bitmap_mask(tmp_path / "m.dmask", np.ones((21, 30)))
    code, _, err = run(capsys, img, "R0=1", "R1=5", "NR=3", "--mask",
                       tmp_path / "m.dmask")
    assert code == 1 and "is 30 x 21 pixels but the image is 30 x 20" in err


def test_mask_origin_mismatch(img, tmp_path, capsys):
    import numpy as np
    from elliprof.masks import write_bitmap_mask
    write_bitmap_mask(tmp_path / "m.dmask", np.ones((20, 30)), cnpix=(1, 0))
    code, _, err = run(capsys, img, "R0=1", "R1=5", "NR=3", "--mask",
                       tmp_path / "m.dmask")
    assert code == 1 and "CNPIX1" in err


def test_keyword_builder():
    words = elliprof_keywords(r0=9, r1=347.0, nr=23, niter=10, rmstar=True,
                              cos3x=0, elliprof_sky=12.5, model=True)
    assert words == ["R0=9", "R1=347.0", "NR=23", "NITER=10", "SKY=12.5",
                     "COS3X=0", "MODEL", "RMSTAR"]


@pytest.mark.parametrize("words,message", [
    (["R0=1", "R1=2", "NR=3", "X0=4"], "center=(x, y)"),
    (["R0=1", "R1=2"], "missing required fit parameters: nr"),
    (["GC"], "GC needs nr"),
    (["R0=1", "R1=2", "NR=3"] + ["TEST"] * 12, "at most 16 keywords"),
])
def test_keyword_validation(words, message):
    with pytest.raises(ValueError, match=message.replace("(", r"\(")
                       .replace(")", r"\)")):
        validate_keywords(words)


def test_python_api_rejects_nonfinite():
    with pytest.raises(ValueError):
        elliprof_keywords(r0=float("nan"))
