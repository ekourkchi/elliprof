#!/bin/sh
# Test a Linux wheel in a clean container that has no compiler and no
# CFITSIO: install it, inspect its native dependencies, run the
# installed-wheel tests and the numerical regression suite against the
# installed backend, and collect the regression outputs for comparison.
#
#   docker run --rm [--platform linux/ARCH] -v "$PWD:/project:ro" \
#       -v "$PWD/spread:/spread" IMAGE sh /project/tools/ci/test_wheel_linux.sh MODE [NAME]
#
# MODE apt: Debian; numpy, pandas, pytest and astropy from the
#           distribution (PyPI has no wheels for them on ppc64le, s390x
#           or riscv64), the wheel from /project/wheelhouse.
# MODE pip: python:*-alpine / -slim; dependencies as binary wheels from
#           PyPI, or from /project/deps (prebuilt elsewhere) where PyPI
#           has none.  Nothing is compiled here.
set -eu
mode=${1:?usage: test_wheel_linux.sh apt|pip [NAME]}
name=${2:-wheel}
export PYTHONDONTWRITEBYTECODE=1 ELLIPROF_TEST_REQUIRE_NO_COMPILER=1

case $mode in
apt)
    export DEBIAN_FRONTEND=noninteractive
    apt-get -qq update
    apt-get -qq install -y --no-install-recommends python3 python3-venv \
        python3-pip python3-numpy python3-pandas python3-astropy \
        python3-pytest binutils >/dev/null
    python3 -m venv --system-site-packages /venv
    ;;
pip)
    if command -v apk >/dev/null 2>&1; then
        apk add --no-cache binutils >/dev/null
    else
        apt-get -qq update && apt-get -qq install -y binutils >/dev/null
    fi
    python3 -m venv /venv
    links=""
    [ -d /project/deps ] && links="--find-links /project/deps"
    # shellcheck disable=SC2086
    /venv/bin/pip install -q --only-binary=:all: $links \
        numpy pandas pytest astropy
    ;;
*)
    echo "unknown mode $mode" >&2; exit 2 ;;
esac
. /venv/bin/activate

echo "== platform"
uname -m; python -c 'import platform, sys; print(sys.version); print(platform.libc_ver())'

echo "== no compiler, no CFITSIO"
for cc in gcc cc gfortran clang; do
    if command -v $cc >/dev/null 2>&1; then echo "unexpected compiler: $cc" >&2; exit 1; fi
done
# A distribution package (e.g. astropy) may bring its own libcfitsio; the
# backend must not use it (check_backend_deps.py and ldd below).
find / -xdev -name 'libcfitsio*' 2>/dev/null | sed 's/^/note: present, not ours: /'

echo "== install the wheel"
pip install -q /project/wheelhouse/*.whl
pip list 2>/dev/null | grep -iE '^(elliprof|numpy|pandas|astropy|pytest) '

echo "== native dependencies"
python /project/tools/ci/check_backend_deps.py
backend=$(python -c 'import elliprof; print(elliprof.find_backend())')
ldd "$backend" || true
if ldd "$backend" 2>/dev/null | grep -qi cfitsio; then
    echo "the backend loads an external CFITSIO" >&2; exit 1
fi

cd /tmp
echo "== installed-wheel tests"
python -m pytest -p no:cacheprovider -c /project/tests/packaging/pytest.ini \
    /project/tests/packaging -q

echo "== regression suite (installed backend)"
ELLIPROF_NATIVE=$(python -c 'import elliprof; print(elliprof.find_backend())')
export ELLIPROF_NATIVE
python -m pytest -p no:cacheprovider -c /project/pyproject.toml \
    --rootdir /project -o "pythonpath=tests tests/regression" \
    /project/tests/regression -q -rxXs

if [ -d /spread ]; then
    echo "== regression outputs -> /spread/$name"
    python /project/tests/regression/collect_outputs.py "/spread/$name"
fi
