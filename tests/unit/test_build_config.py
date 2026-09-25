"""The Makefile (development) and CMakeLists.txt (wheels) must build the
same program: same sources, same numerical flags, no preprocessing."""

import re

from helpers import ROOT

MAKEFILE = (ROOT / "Makefile").read_text()
CMAKE = (ROOT / "CMakeLists.txt").read_text()


def make_var(name):
    m = re.search(rf"^{name}\s*=\s*(.*)$", MAKEFILE, re.M)
    return m.group(1).split()


def cmake_set(name):
    m = re.search(rf"set\({name}\s+(.*?)\)", CMAKE, re.S)
    return m.group(1).split()


def test_same_numerical_flags():
    assert make_var("FFLAGS") == cmake_set("ELLIPROF_FFLAGS") == \
        ["-O", "-g", "-fno-automatic", "-ffp-contract=off"]


def test_no_forbidden_flags():
    for text in (MAKEFILE, CMAKE):
        code = "\n".join(l for l in text.splitlines()
                         if not l.lstrip().startswith("#"))
        for flag in ("-fcheck", "-ffast-math", "-O2", "-O3", "-march",
                     "-Ofast", "-funsafe-math"):
            assert flag not in code


def test_same_sources():
    assert make_var("ORIG") == cmake_set("ORIGINAL")
    assert make_var("SHIM") == cmake_set("SHIM")


def test_cmake_disables_preprocessing_and_build_type_flags():
    assert "Fortran_PREPROCESS OFF" in CMAKE
    assert 'set(CMAKE_Fortran_FLAGS${cfg} "" CACHE STRING "" FORCE)' in CMAKE
