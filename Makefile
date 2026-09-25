# Standalone ELLIPROF, extracted from MONSTA libvista.
#
#   make              build ./elliprof
#   make test_image.fits   write the synthetic smoke-test image
#   make test         build both and run ELLIPROF on the test image
#   make masktest     check the BITPIX=1 mask decoder on u12517j.dmask
#   make clean

FC      = gfortran
# Flags as in MONSTA's Make.Common, plus -ffp-contract=off so that
# multiply-adds are not fused (keeps REAL*4 results reproducible).
# Never add bounds checking: the F77 code declares dummy arrays as
# X(1) / X(2) and indexes past them on purpose.
FFLAGS  = -O -g -fno-automatic -ffp-contract=off
WARN    =
CFITSIO ?= $(shell brew --prefix cfitsio 2>/dev/null || echo /usr/local)
LDLIBS  = -L$(CFITSIO)/lib -lcfitsio

ORIG = elliprof jtutil gcfit assign dissect value operate variable upper
SHIM = main stubs fitsio profout maskio
OBJS = $(ORIG:%=build/%.o) $(SHIM:%=build/%.o)
INCS = $(wildcard include/*.inc include/*.par)

TESTARGS = X0=127.3 Y0=121.6 R0=2 R1=90 NR=30

all: elliprof

elliprof: $(OBJS)
	$(FC) $(FFLAGS) -o $@ $(OBJS) $(LDLIBS)

build/%.o: src/original/%.f $(INCS) | build
	$(FC) $(FFLAGS) $(WARN) -Iinclude -c $< -o $@

build/%.o: src/shim/%.f $(INCS) | build
	$(FC) $(FFLAGS) $(WARN) -Iinclude -c $< -o $@

build:
	mkdir -p build

build/mktestimage: tests/mktestimage.f | build
	$(FC) $(FFLAGS) $(WARN) -o $@ $< $(LDLIBS)

test_image.fits: build/mktestimage
	./build/mktestimage $@

test: elliprof test_image.fits
	./elliprof test_image.fits $(TESTARGS) -o test_image.prf

build/maskinfo: tests/maskinfo.f build/maskio.o build/fitsio.o
	$(FC) $(FFLAGS) $(WARN) -o $@ $^ $(LDLIBS)

masktest: build/maskinfo
	sh tests/test_mask_u12517.sh

clean:
	rm -rf build elliprof test_image.prf fort.2

.PHONY: all test masktest clean
