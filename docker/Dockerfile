# Linux development and test image for elliprof.
#
#   make docker-test     build this image and run the full check
#   make docker-shell    interactive shell inside it
#
# Linux only: macOS and Windows are tested on real CI runners.
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
        gfortran make pkg-config libcfitsio-dev \
        python3 python3-venv python3-pip \
 && rm -rf /var/lib/apt/lists/*

RUN python3 -m venv /venv \
 && /venv/bin/pip install --no-cache-dir numpy pandas astropy pytest
ENV PATH=/venv/bin:$PATH

WORKDIR /src
COPY . /src
RUN make clean && make PYTHON=/venv/bin/python all tools

# Full validation: source hashes, unit, integration, regression.  The
# regression baselines were made on another platform, so they are
# compared with the (provisional) cross-platform tolerances.
CMD ["make", "PYTHON=/venv/bin/python", "check"]
