"""The original ELLIPROF sources are the reference implementation and
must stay byte-identical.  tests/original_source_hashes.txt is edited
by hand only, never regenerated automatically."""

import hashlib

import pytest

from helpers import ROOT

HASHES = ROOT / "tests" / "original_source_hashes.txt"


def _expected():
    out = {}
    for line in HASHES.read_text().splitlines():
        if line.strip() and not line.startswith("#"):
            digest, name = line.split(None, 1)
            out[name.strip()] = digest
    return out


def test_hash_file_lists_all_protected_files():
    names = set(_expected())
    assert len(names) == 13
    assert {p.relative_to(ROOT).as_posix()
            for p in (ROOT / "src" / "original").glob("*.f")} \
        | {p.relative_to(ROOT).as_posix()
           for p in (ROOT / "include").iterdir()} == names


@pytest.mark.parametrize("name,digest", sorted(_expected().items()))
def test_original_file_unchanged(name, digest):
    # Hash the bytes as stored; a checkout that rewrote line endings
    # would also fail here (see .gitattributes).
    data = (ROOT / name).read_bytes()
    assert hashlib.sha256(data).hexdigest() == digest, (
        f"{name} differs from the original source")
