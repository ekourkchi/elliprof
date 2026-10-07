#!/usr/bin/env bash
# Build a static CFITSIO (no curl, no bzip2) from pinned, checksummed
# source into PREFIX.  Used by the wheel builds so that release wheels
# never depend on a system CFITSIO.
#
#   bash tools/ci/build_cfitsio.sh PREFIX
set -euo pipefail

PREFIX=${1:?usage: build_cfitsio.sh PREFIX}
VERSION=4.7.0
SHA256=ce573bbea8e75b429f8c3d3e86498741ba3dc9628a1530d2f65268397ad059e8
URL=https://heasarc.gsfc.nasa.gov/FTP/software/fitsio/c/cfitsio-$VERSION.tar.gz

here=$(cd "$(dirname "$0")" && pwd)
work=$(mktemp -d)

# The Fortran-interface ABI probe (cfitsio_f77_probe.f) runs after every
# build, and also on a CFITSIO already present in PREFIX: a wrong
# long/INTEGER mapping in the Fortran wrappers must stop the wheel build.
probe() {
    lib=$(ls "$PREFIX"/lib*/libcfitsio.a | head -1)
    (cd "$work" && "${FC:-gfortran}" -o f77probe "$here/cfitsio_f77_probe.f" \
        "$lib" -lz -lm && ./f77probe)
}

if [ -n "$(ls "$PREFIX"/lib*/libcfitsio.a 2>/dev/null)" ]; then
    echo "CFITSIO already in $PREFIX"
    probe
    rm -rf "$work"
    exit 0
fi
if [ -n "${CFITSIO_TARBALL:-}" ]; then
    # offline / cached builds: a local copy (still checksum-verified)
    cp "$CFITSIO_TARBALL" "$work/cfitsio.tar.gz"
else
    # the HEASARC server occasionally answers 404; retry a few times
    for attempt in 1 2 3 4 5; do
        curl -fsSL --retry 3 -o "$work/cfitsio.tar.gz" "$URL" && break
        [ "$attempt" = 5 ] && { echo "cannot download $URL" >&2; exit 1; }
        sleep $((attempt * 10))
    done
fi
if command -v sha256sum >/dev/null 2>&1; then
    echo "$SHA256  $work/cfitsio.tar.gz" | sha256sum -c -
else
    echo "$SHA256  $work/cfitsio.tar.gz" | shasum -a 256 -c -
fi
tar xzf "$work/cfitsio.tar.gz" -C "$work"

# f77_wrap.h selects the Fortran-wrapper mapping of C long (8 bytes) to
# Fortran INTEGER (4 bytes) from a fixed list of 64-bit architectures.
# CFITSIO 4.7.0 omits riscv64, so there every long argument has the wrong
# size (FTGISZ read 256 x 256 as 256 x 0; FTGPVE failed with status 307).
# Add riscv64 (LP64: 8-byte long) to that list and nothing else: the
# preprocessor result is unchanged on every other architecture.  Fail if
# the expected line is gone, so that a CFITSIO upgrade is looked at again.
f77="$work/cfitsio-$VERSION/f77_wrap.h"
if grep -q '__riscv' "$f77"; then
    echo "f77_wrap.h already handles riscv: not patched"
else
    anchor='    ||  defined(__aarch64__) '
    if [ "$(grep -cxF "$anchor" "$f77")" != 1 ]; then
        echo "build_cfitsio.sh: f77_wrap.h changed (no unique" \
             "'$anchor' line); review the riscv64 patch" >&2
        exit 1
    fi
    awk -v a="$anchor" '$0 == a {
            print a "\\"
            print "    || (defined(__riscv) && __riscv_xlen == 64) "
            next }
        { print }' "$f77" > "$f77.new"
    mv "$f77.new" "$f77"
    grep -n -B1 '__riscv' "$f77"
fi

cmake -S "$work/cfitsio-$VERSION" -B "$work/build" \
    ${CFITSIO_CMAKE_GENERATOR:+-G "$CFITSIO_CMAKE_GENERATOR"} \
    -DCMAKE_INSTALL_PREFIX="$PREFIX" \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_POSITION_INDEPENDENT_CODE=ON \
    -DBUILD_SHARED_LIBS=OFF -DUSE_CURL=OFF -DUSE_BZIP2=OFF \
    -DTESTS=OFF -DUTILS=OFF
cmake --build "$work/build" --parallel
cmake --install "$work/build"
mkdir -p "$PREFIX/share/licenses/cfitsio"
cp "$work/cfitsio-$VERSION/licenses/License.txt" \
   "$PREFIX/share/licenses/cfitsio/"
probe
rm -rf "$work"
echo "static CFITSIO $VERSION installed in $PREFIX"
