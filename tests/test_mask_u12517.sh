#!/bin/sh
# Check the BITPIX=1 mask decoder on examples/u12517/u12517j.dmask.
# Expected values come from an independent decode of the same file
# following MONSTA's bitfp_/FITSorder, cross-checked against a mask
# that MONSTA itself wrote (see examples/u12517/README.md).
cd "$(dirname "$0")/.." || exit 1
out=$(./build/maskinfo examples/u12517/u12517j.dmask 567 562 20) || exit 1
echo "$out" | sed -n '1,11p'
fail=0
check() {
    if echo "$out" | grep -qx "$1"; then echo "ok    $1"
    else echo "FAIL  expected: $1"; fail=1; fi
}
check 'BITPIX:        1'
check 'size:          1025 x 1022'
check 'CNPIX1,CNPIX2: 0,0'
check 'value 0 (masked): 103402'
check 'value 1 (good):   944148'
check 'other values:     0'
check 'masked fraction:   0.09871'
check 'value at (567,562): 0.00000000'
check 'zeros in box of half-width 20: 301'
exit $fail
