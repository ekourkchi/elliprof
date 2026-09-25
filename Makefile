# elliprof: MONSTA's ELLIPROF as a standalone program and Python package.
#
# Native development build (release wheels are built by CMake through
# scikit-build-core, see pyproject.toml and CMakeLists.txt):
#
#   make                  build ./elliprof_native (and ./elliprof -> it)
#   make test             quick native smoke test on a synthetic image
#   make test-unit        Python unit tests          (pytest tests/unit)
#   make test-integration native CLI / Python API / Python CLI agreement
#   make test-regression  synthetic baselines and the u12517 example
#   make python-test      all of the above through pytest
#   make check            build + source hashes + every test suite
#   make update-baselines regenerate tests/regression/baseline (never
#                         run by make test / make check)
#   make docker-test      build and test inside a Linux container
#   make docker-shell     interactive shell in that container
#   make notebook-check   execute notebooks/elliprof_example.ipynb
#   make clean

FC      = gfortran
# Numerical flags, as MONSTA's Make.Common plus -ffp-contract=off so
# that multiply-adds are never fused (keeps REAL*4 results
# reproducible).  CMakeLists.txt must use the same list; a test checks.
# Never add bounds checking, -O2/-O3, -ffast-math or -march: the F77
# code indexes dummy arrays declared X(1)/X(2) past their bounds on
# purpose, and optimisation changes REAL*4 results.
FFLAGS  = -O -g -fno-automatic -ffp-contract=off
WARN    =
PYTHON ?= $(shell [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)
VERSION := $(shell cat VERSION)

# CFITSIO: Homebrew, else pkg-config, else the system default paths.
CFITSIO ?= $(shell brew --prefix cfitsio 2>/dev/null)
ifneq ($(CFITSIO),)
LDLIBS  = -L$(CFITSIO)/lib -lcfitsio
else
LDLIBS  = $(shell pkg-config --libs cfitsio 2>/dev/null || echo -lcfitsio)
endif

ORIG = elliprof jtutil gcfit assign dissect value operate variable upper
SHIM = main stubs fitsio profout maskio prep
OBJS = $(ORIG:%=build/%.o) $(SHIM:%=build/%.o)
INCS = $(wildcard include/*.inc include/*.par) build/version.inc

all: elliprof_native elliprof

elliprof_native: $(OBJS)
	$(FC) $(FFLAGS) -o $@ $(OBJS) $(LDLIBS)

# Old name, kept so existing ./elliprof commands keep working
elliprof: elliprof_native
	ln -sf elliprof_native $@

build/%.o: src/original/%.f $(INCS) | build
	$(FC) $(FFLAGS) $(WARN) -Iinclude -Ibuild -c $< -o $@

build/%.o: src/shim/%.f $(INCS) | build
	$(FC) $(FFLAGS) $(WARN) -Iinclude -Ibuild -c $< -o $@

build/version.inc: VERSION | build
	printf "      CHARACTER*(*) VERSTR\n      PARAMETER (VERSTR='%s')\n" \
	    "$(VERSION)" > $@

build:
	mkdir -p build

# Test tools (tests/tools/*.f), used by the pytest suites
build/maskinfo: tests/tools/maskinfo.f build/maskio.o build/fitsio.o
	$(FC) $(FFLAGS) $(WARN) -o $@ $^ $(LDLIBS)

build/mktestimage: tests/tools/mktestimage.f | build
	$(FC) $(FFLAGS) $(WARN) -o $@ $< $(LDLIBS)

build/test_image.fits: build/mktestimage
	./build/mktestimage $@

tools: build/maskinfo build/mktestimage

test: all build/test_image.fits
	./elliprof_native build/test_image.fits X0=127.3 Y0=121.6 R0=3 \
	    R1=90 NR=30 SKY=100 -o build/test_image.prf

test-unit: all tools
	$(PYTHON) -m pytest tests/unit

test-integration: all tools
	$(PYTHON) -m pytest tests/integration

test-regression: all tools
	$(PYTHON) -m pytest tests/regression

python-test: all tools
	$(PYTHON) -m pytest tests/unit tests/integration tests/regression

check: all tools
	$(PYTHON) -m pytest tests/unit/test_source_hashes.py
	$(PYTHON) -m pytest tests/unit tests/integration tests/regression

update-baselines: all tools
	$(PYTHON) tests/regression/update_baselines.py

DOCKER ?= docker
docker-test:
	$(DOCKER) build -f docker/Dockerfile -t elliprof-test .
	$(DOCKER) run --rm elliprof-test

docker-shell:
	$(DOCKER) build -f docker/Dockerfile -t elliprof-test .
	$(DOCKER) run --rm -it elliprof-test bash

# Executes a copy of the notebook in memory; the file is not modified.
notebook-check: all
	$(PYTHON) -c "import nbclient, nbformat, matplotlib" 2>/dev/null || \
	    { echo "notebook-check needs: pip install -e .[notebook]"; exit 1; }
	$(PYTHON) -c "import nbformat, nbclient; \
	    nb = nbformat.read('notebooks/elliprof_example.ipynb', 4); \
	    nbclient.NotebookClient(nb, timeout=600, \
	        resources={'metadata': {'path': 'notebooks'}}).execute(); \
	    print('notebook OK')"

clean:
	rm -rf build elliprof elliprof_native fort.2

.PHONY: all tools test test-unit test-integration test-regression \
	python-test check update-baselines docker-test docker-shell \
	notebook-check clean
