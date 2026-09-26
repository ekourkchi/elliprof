"""The informational commands -- ``elliprof`` with no arguments, -h/--help,
-v/--version -- must work without numpy, pandas or the backend, so that a
broken scientific stack (e.g. numexpr/bottleneck built for NumPy 1.x under
NumPy 2) cannot get in their way.  A command-line fit must not need
pandas."""

import os
import re
import subprocess
import sys

import pytest

from elliprof import __email__, __maintainer__, __version__, cli
from helpers import ROOT

PYTHON_DIR = str(ROOT / "python")

# Make importing these fail loudly, and point the backend at nothing: a
# hidden import or backend call makes the command fail.
POISON = """
import sys
class _Poison:
    def find_module(self, name, path=None):
        return self if name.split(".")[0] in BLOCKED else None
    def load_module(self, name):
        raise ImportError("blocked for this test: " + name)
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in BLOCKED:
            raise ImportError("blocked for this test: " + name)
        return None
sys.meta_path.insert(0, _Poison())
for mod in list(sys.modules):
    if mod.split(".")[0] in BLOCKED:
        del sys.modules[mod]
from elliprof.cli import main
code = main(sys.argv[1:])
loaded = sorted(m for m in sys.modules if m.split(".")[0] in WATCH)
print("LOADED:" + ",".join(loaded), file=sys.stderr)
sys.exit(code)
"""


def _run(args, blocked=("numpy", "pandas"),
         watch=("numpy", "pandas", "numexpr", "bottleneck")):
    code = ("BLOCKED = %r\nWATCH = %r\n" % (set(blocked), set(watch))) + POISON
    env = dict(os.environ, PYTHONPATH=PYTHON_DIR,
               ELLIPROF_NATIVE=os.path.join(os.sep, "nonexistent", "backend"))
    return subprocess.run([sys.executable, "-c", code, *args],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, env=env, timeout=60)


CREDIT = ("ELLIPROF was originally developed by John Tonry as part of "
          "MONSTA.")
VERSION_TEXT = (f"elliprof {__version__}\n{CREDIT}\n"
                f"Maintained by {__maintainer__}\nEmail: {__email__}\n")


@pytest.mark.parametrize("args", [[], ["-h"], ["--help"], ["-v"],
                                  ["--version"]])
def test_informational_commands_need_no_scientific_stack(args):
    proc = _run(args)
    assert proc.returncode == 0, proc.stderr
    loaded = re.search(r"LOADED:(.*)", proc.stderr).group(1)
    assert loaded == "", f"imported {loaded}"
    assert "Traceback" not in proc.stderr


def test_no_arguments_prints_a_short_introduction():
    proc = _run([])
    assert proc.returncode == 0
    out = proc.stdout
    assert out.startswith("ELLIPROF - Galaxy Isophote Fitting\n")
    assert CREDIT in out
    assert f"Maintained by {__maintainer__}" in out
    assert f"Email: {__email__}" in out
    assert "elliprof -h" in out
    assert len(out.splitlines()) < 25          # an introduction, not help


def test_version_short_and_long_are_identical():
    assert _run(["-v"]).stdout == _run(["--version"]).stdout == VERSION_TEXT


def test_help_short_and_long_are_identical():
    assert _run(["-h"]).stdout == _run(["--help"]).stdout


def test_help_is_plain_ascii_and_fits_a_terminal():
    text = _run(["-h"]).stdout
    text.encode("ascii")
    assert max(len(l) for l in text.splitlines()) <= 79


HELP_SECTIONS = ["USAGE", "INPUT IMAGE AND INITIAL CENTRE",
                 "RADIAL FITTING PARAMETERS", "SKY / BACKGROUND AND MASK",
                 "MODEL AND HARMONIC CONTROLS", "OUTPUT FILES",
                 "PROFILE COLUMNS", "LEGACY ELLIPROF CONTROLS",
                 "DIAGNOSTICS AND RUNTIME OPTIONS", "EXAMPLES"]


def test_help_documents_every_public_option_and_keyword():
    text = _run(["-h"]).stdout
    for section in HELP_SECTIONS:
        assert "\n" + section in text, section
    # every option the parser accepts
    for opt in sorted(cli.VALUE_OPTS | set(cli.FLAG_OPTS)):
        assert re.search(r"(^|[\s,])" + re.escape(opt) + r"\b", text), opt
    # every ELLIPROF keyword the backend accepts
    for kw in ("X0=", "Y0=", "R0=", "R1=", "NR=", "NITER=", "RLAW=",
               "RMSTAR", "FIXCTR=", "ELLIP=", "LINEAR", "TIE=", "AVG=",
               "GAIN=", "SCALE=", "GC", "VERBOSE", "SKY=", "MODEL",
               "COS3X=", "COS4X="):
        assert kw in text, kw
    assert "--sc VALUE         deprecated alias of --sky" in text
    assert "0 = bad / excluded; any other finite" in text
    assert "NaN, Inf and" in text and "never" in text and "weights" in text
    assert "'galaxy.fits[SCI]'" in text
    assert "mask x (science - sky - model)" in text
    assert "(default 1800)" in text and "status 124" in text
    # profile columns, and the profile is not an image
    for col in ("Rmaj", "x0 y0", "I0", "alpha", "ellip", "I3 I4", "A3 A4",
                "slope"):
        assert "\n  " + col in text, col
    assert "NOT an image" in text and "2-D model image" in text
    assert CREDIT in text


def test_diagnostics_do_not_import_the_scientific_stack():
    proc = _run(["--diagnostics"])
    assert proc.returncode == 0, proc.stderr
    assert re.search(r"LOADED:(.*)", proc.stderr).group(1) == ""
    for key in ("elliprof version", "Python", "architecture", "numpy",
                "pandas", "native backend"):
        assert key in proc.stdout


def test_invalid_invocations_still_fail():
    assert _run(["galaxy.fits", "R0=1", "R1=5", "NR=3"],
                blocked=()).returncode != 0
    proc = _run(["--frobnicate"])
    assert proc.returncode == 2 and "unknown option" in proc.stderr


def test_command_line_fit_does_not_import_pandas(native, tmp_path):
    """A real fit through the command line, with pandas blocked."""
    image = ROOT / "tests" / "data" / "regression" / "elliptical.fits"
    code = ("BLOCKED = {'pandas'}\nWATCH = {'pandas'}\n" + POISON)
    env = dict(os.environ, PYTHONPATH=PYTHON_DIR, ELLIPROF_NATIVE=str(native))
    proc = subprocess.run(
        [sys.executable, "-c", code, str(image), "X0=100.3", "Y0=99.6",
         "R0=3", "R1=80", "NR=25", "-o", str(tmp_path / "p.prf"),
         "--csv", str(tmp_path / "p.csv"), "--reg", str(tmp_path / "p.reg")],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        universal_newlines=True, env=env, timeout=300)
    assert proc.returncode == 0, proc.stderr
    assert re.search(r"LOADED:(.*)", proc.stderr).group(1) == ""
    for ext in ("prf", "csv", "reg"):
        assert (tmp_path / f"p.{ext}").stat().st_size > 0


def test_api_explains_a_broken_pandas(native, tmp_path):
    """The Python API needs pandas for result.profile; if it cannot be
    imported, the fit still runs and the error says what to do."""
    image = ROOT / "tests" / "data" / "regression" / "elliptical.fits"
    code = (
        "import sys\nsys.modules['pandas'] = None\n"
        "from elliprof import run_elliprof\n"
        "try:\n"
        "    run_elliprof(%r, 100.3, 99.6, r0=3, r1=80, nr=25,\n"
        "                 output_dir=%r)\n"
        "except ImportError as exc:\n"
        "    print(exc)\n" % (str(image), str(tmp_path)))
    env = dict(os.environ, PYTHONPATH=PYTHON_DIR, ELLIPROF_NATIVE=str(native))
    proc = subprocess.run([sys.executable, "-c", code],
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True, env=env, timeout=300)
    assert "elliprof could not import pandas" in proc.stdout, proc.stderr
    assert "python -m pip install --upgrade numexpr bottleneck" in proc.stdout
    assert 'python -m pip install "numpy<2"' in proc.stdout
    assert (tmp_path / "elliptical.prf").stat().st_size > 0   # fit finished
