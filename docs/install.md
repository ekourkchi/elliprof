# Install

!!! note "Release status"
    These pages describe **elliprof 0.2.0rc1, a pre-release** for testing.
    The current **stable release is 0.1.4**: `python -m pip install elliprof`
    installs 0.1.4. To try the release candidate, install it explicitly:

    ```sh
    python -m pip install elliprof==0.2.0rc1     # or: python -m pip install --pre elliprof
    ```

    Once 0.2.0 final is published, `python -m pip install -U elliprof` will
    select it. The double-precision backend (`--precision`, 64-bit products)
    is new in 0.2.0rc1 and not part of 0.1.4.

```sh
python -m pip install elliprof
```

This installs the `elliprof` command and the `elliprof` Python package.
The packages on PyPI are prebuilt, so you need no Fortran compiler and no
separate CFITSIO installation.

Check that it works:

```sh
elliprof            # a short introduction
elliprof -v         # version, original developer and maintainer
elliprof -h         # full help: every parameter, option and example
```

`python -m elliprof` does the same as `elliprof`. That helps when the
command is not on your `PATH`.

## Updating

```sh
elliprof --check-update   # is a newer version on PyPI? (installs nothing)
elliprof --update         # install it; elliprof -u is the same
```

`elliprof --update` runs `python -m pip install --upgrade elliprof` with
the same Python that runs elliprof, so the new version lands where the
old one was. In a conda environment, or a system Python that pip may not
change ("externally managed"), update elliprof the way you installed it.
A source checkout or editable install is updated with git, not with
`--update`.

After a fit in an interactive terminal, elliprof asks PyPI at most once a
day, in the background, whether a newer version exists, and prints one
line if so. It never installs anything by itself, never delays a fit,
and is silent offline and in scripts or batch jobs. Set
`ELLIPROF_NO_UPDATE_CHECK=1` to turn the check off. An installed
pre-release (0.2.0rc1) is not offered updates by `--check-update`,
`--update` or this notice; update it with pip directly.

## Supported systems

| | |
|---|---|
| Python | 3.6 through 3.14 |
| Linux | x86_64, aarch64, ppc64le, s390x, riscv64 (glibc, "manylinux"); x86_64, aarch64 (musl, e.g. Alpine). ppc64le, s390x and riscv64 are validated under QEMU emulation, not yet on native hardware |
| macOS | Intel (x86_64): 10.13 High Sierra or newer. Apple Silicon (arm64): 11 Big Sur or newer |
| Windows | x86_64 |

Python and the operating system are separate requirements. A supported
Python on an unsupported operating system still cannot install elliprof.

## If pip says "No matching distribution found"

pip found no elliprof build for your computer. The usual reasons:

- a Python older than 3.6;
- an old pip that does not recognise current package names;
- an operating system older than the minimum above;
- a processor with no elliprof build, for example a 32-bit system.

First check what you have:

```sh
python --version
python -m pip --version
uname -m        # x86_64 = Intel/AMD, arm64/aarch64 = ARM
```

If Python is between 3.6 and 3.14, upgrade pip and try again:

```sh
python -m pip install --upgrade pip
python -m pip install elliprof
```

On Python 3.6 the newest pip is 21.3.1: `python -m pip install "pip==21.3.1"`.

!!! beginner "Virtual environments"
    If your system Python is managed by the operating system, or you do
    not want to mix packages, make a virtual environment first:

    ```sh
    python -m venv elliprof-env
    source elliprof-env/bin/activate      # Windows: elliprof-env\Scripts\activate
    python -m pip install elliprof
    ```

## Optional packages

- `astropy` is needed only by the Python helper `elliprof.load_mask` when
  it reads FITS masks. elliprof itself reads and writes FITS without it.
- For the plots on this site you also need `matplotlib`. See
  [Scripts behind the figures](reference/architecture.md#scripts-behind-the-figures).

## Reporting a problem

`elliprof --diagnostics` prints the versions, Python, operating system,
architecture and backend location. Include its output when you report an
issue at <https://github.com/ekourkchi/elliprof/issues>.
