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

if [ -f "$PREFIX/lib/libcfitsio.a" ]; then
    echo "CFITSIO already in $PREFIX"
    exit 0
fi
work=$(mktemp -d)
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
rm -rf "$work"
echo "static CFITSIO $VERSION installed in $PREFIX"
