# Install

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

## Supported systems

| | |
|---|---|
| Python | 3.6 through 3.14 |
| Linux | x86_64, aarch64, ppc64le, s390x (glibc, "manylinux"); x86_64, aarch64 (musl, e.g. Alpine) |
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
