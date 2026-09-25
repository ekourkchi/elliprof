#!/bin/sh
# Make sure a cibuildwheel Linux build image has gfortran and the zlib
# headers (the manylinux_2_28 images already do; musllinux is Alpine, and
# other images may not).  Does nothing when both are present.
#
#   sh tools/ci/linux_toolchain.sh
set -eu

have_zlib() { [ -f /usr/include/zlib.h ]; }
if command -v gfortran >/dev/null 2>&1 && have_zlib; then
    echo "toolchain: $(gfortran --version | head -1)"
    exit 0
fi
if command -v apk >/dev/null 2>&1; then
    apk add --no-cache gfortran zlib-dev
elif command -v dnf >/dev/null 2>&1; then
    dnf install -y gcc-gfortran zlib-devel
elif command -v yum >/dev/null 2>&1; then
    yum install -y gcc-gfortran zlib-devel
else
    echo "linux_toolchain.sh: no gfortran and no known package manager" >&2
    exit 1
fi
echo "toolchain: $(gfortran --version | head -1)"
