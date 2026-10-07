"""COMMON blocks of the single and the double backends.

The double backend (src/double) is a precision port with its own COMMON
blocks; the blocks it shares with the rest of the program (VISTA command
state, image bookkeeping) must have exactly the same size in every object
file, and the precision-specific blocks must never be shared.  Read from
the object files of the development build with `nm -P`."""

import shutil
import subprocess

import pytest

from helpers import ROOT

BUILD = ROOT / "build"
DOUBLE_OBJECTS = ("elliprof_d", "jtutil_d", "main_d", "fitsio_d",
                  "prep_d", "profout_d")
# precision-specific blocks: single name -> double name
PAIRS = {"prf": "prfd", "prf_name": "prfnmd", "elltest": "elltstd",
         "ellizero": "ellzd"}
# Known in the original: VARIABLE (variable.f) declares /VISCON/ larger
# than vistalink.inc does.  Not used by elliprof; recorded, not changed.
KNOWN_ORIGINAL = {("viscon", "variable")}


def commons(obj):
    out = subprocess.run(["nm", "-P", str(obj)], stdout=subprocess.PIPE,
                         universal_newlines=True, check=True).stdout
    sizes = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and parts[1] == "C":
            name = parts[0].lstrip("_").rstrip("_").lower()
            value = int(parts[2], 16)
            size = int(parts[3], 16) if len(parts) > 3 else 0
            # ELF: value is the alignment, size the size; Mach-O: the
            # value is the size
            sizes[name] = size or value
    return sizes


@pytest.fixture(scope="module")
def objects():
    if shutil.which("nm") is None:
        pytest.skip("nm not available")
    objs = {p.stem: p for p in BUILD.glob("*.o")}
    if not all(d in objs for d in DOUBLE_OBJECTS):
        pytest.skip("no development build (make) in build/")
    return {name: commons(path) for name, path in objs.items()}


def test_shared_blocks_have_one_size(objects):
    sizes = {}
    for obj, blocks in objects.items():
        for block, size in blocks.items():
            if (block, obj) not in KNOWN_ORIGINAL:
                sizes.setdefault(block, {})[obj] = size
    for block, per_obj in sizes.items():
        assert len(set(per_obj.values())) == 1, (block, per_obj)


def test_double_blocks_are_private(objects):
    for obj, blocks in objects.items():
        double = obj in DOUBLE_OBJECTS
        for single_name, double_name in PAIRS.items():
            if double:
                assert single_name not in blocks, (obj, single_name)
            else:
                assert double_name not in blocks, (obj, double_name)


def test_double_profile_block_layout(objects):
    # /PRFD/: PARAM_PRF(12,250) and PRF_SC in DOUBLE PRECISION, N_PRF
    blocks = objects["elliprof_d"]
    assert blocks["prfd"] >= 12 * 250 * 8 + 8 + 4
    assert blocks["prfnmd"] == objects["elliprof"]["prf_name"]
    # the single block is unchanged: REAL*4 PARAM_PRF, padded PRF_SC
    assert objects["elliprof"]["prf"] == 12 * 250 * 4 + 8
