#!/bin/sh
# Fit UGC 12517 with elliprof, using its mask and a constant sky.
#
#   sh examples/u12517/run_example.sh [OUTPUT_DIR]
#
# Works from any directory.  Uses the installed `elliprof` command if
# there is one, otherwise the source checkout (after `make`).
set -eu

HERE=$(cd "$(dirname "$0")" && pwd)
ROOT=$(cd "$HERE/../.." && pwd)
OUT=${1:-$HERE}
mkdir -p "$OUT"
OUT=$(cd "$OUT" && pwd)

if command -v elliprof >/dev/null 2>&1 && elliprof --version >/dev/null 2>&1
then
    set -- elliprof
else
    PY=python3
    [ -x "$ROOT/.venv/bin/python" ] && PY="$ROOT/.venv/bin/python"
    PYTHONPATH="$ROOT/python${PYTHONPATH:+:$PYTHONPATH}"
    export PYTHONPATH
    set -- "$PY" -m elliprof
fi

cd "$HERE"
"$@" u12517j.fits \
    --mask u12517j.dmask \
    --sky 3246.0 \
    X0=567 Y0=562 \
    R0=9 R1=347 NR=23 NITER=10 RMSTAR \
    -o "$OUT/u12517j.prf" \
    --csv "$OUT/u12517j.csv" \
    --reg "$OUT/u12517j.reg"

echo
echo "Wrote $OUT/u12517j.prf, u12517j.csv and u12517j.reg"
