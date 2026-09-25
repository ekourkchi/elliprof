# Third-party components

The code written for elliprof is under the MIT License (see [LICENSE](LICENSE)). The components below are not; they keep their own terms.

## Original ELLIPROF sources (`src/original/`, `include/`)

These files are the numerical reference implementation. They are copied byte-for-byte from the original distribution, never modified, and checked against SHA-256 hashes on every test run. Their authorship and notices are kept exactly as written:

* `elliprof.f`, `jtutil.f`, `gcfit.f`, `profile.inc`: John Tonry.
* `assign.f`, `value.f`, `operate.f`, `variable.f`, `vistalink.inc`, `imagelink.inc`: Tod R. Lauer.
* `dissect.f`, `upper.f`: Richard J. Stover.
* `mongo.par`: "Copyright (c) 1987, 1994 - John Tonry". The graphics package it belongs to was distributed under the GNU GPL, version 1 or later.

Most of these files carry no explicit licence statement. In addition, several routines in `gcfit.f` (`MRQMIN`, `MRQCOF`, `COVSRT`, `GAUSSJ`, `GAMMQ`, `GSER`, `GCF`, `GAMMLN`, used only by the `GC` option) and `ZBRENT` in `jtutil.f` (used by `MODEL`) follow *Numerical Recipes* (Press, Teukolsky, Vetterling & Flannery), whose own licence restricts redistribution. The MIT License of this package does not apply to any of these files.

## CFITSIO 4.7.0

Statically linked into the `elliprof_native` backend in the binary wheels. It is built from the official source, pinned by SHA-256, without curl or bzip2. Source: <https://heasarc.gsfc.nasa.gov/fitsio/>. Its licence text ships in every wheel as `elliprof/_notices/CFITSIO_License.txt`:

> Copyright (Unpublished--all rights reserved under the copyright laws of the United States), U.S. Government as represented by the Administrator of the National Aeronautics and Space Administration. No copyright is claimed in the United States under Title 17, U.S. Code.
>
> Permission to freely use, copy, modify, and distribute this software and its documentation without fee is hereby granted, provided that this copyright notice and disclaimer of warranty appears in all copies.
>
> DISCLAIMER:
>
> THE SOFTWARE IS PROVIDED 'AS IS' WITHOUT ANY WARRANTY OF ANY KIND, EITHER EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED TO, ANY WARRANTY THAT THE SOFTWARE WILL CONFORM TO SPECIFICATIONS, ANY IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND FREEDOM FROM INFRINGEMENT, AND ANY WARRANTY THAT THE DOCUMENTATION WILL CONFORM TO THE SOFTWARE, OR ANY WARRANTY THAT THE SOFTWARE WILL BE ERROR FREE. IN NO EVENT SHALL NASA BE LIABLE FOR ANY DAMAGES, INCLUDING, BUT NOT LIMITED TO, DIRECT, INDIRECT, SPECIAL OR CONSEQUENTIAL DAMAGES, ARISING OUT OF, RESULTING FROM, OR IN ANY WAY CONNECTED WITH THIS SOFTWARE, WHETHER OR NOT BASED UPON WARRANTY, CONTRACT, TORT , OR OTHERWISE, WHETHER OR NOT INJURY WAS SUSTAINED BY PERSONS OR PROPERTY OR OTHERWISE, AND WHETHER OR NOT LOSS WAS SUSTAINED FROM, OR AROSE OUT OF THE RESULTS OF, OR USE OF, THE SOFTWARE OR SERVICES PROVIDED HEREUNDER.

## Runtime libraries bundled in the binary wheels

The wheel-repair tools (auditwheel, delocate) and, on Windows, the build put these shared libraries into the wheel next to the backend. They are dynamically linked and can be replaced. These are the libraries found in the tested wheels:

| Wheel | Bundled libraries |
|---|---|
| macOS arm64, x86_64 | libgfortran, libquadmath, libgcc_s |
| manylinux x86_64, ppc64le | libgfortran, libquadmath |
| manylinux aarch64, s390x | libgfortran |
| musllinux x86_64 | libgcc_s, libgfortran, libquadmath |
| musllinux aarch64 | libgcc_s, libgfortran |
| Windows x86_64 | libgcc_s_seh-1, libgfortran-5, libquadmath-0, libwinpthread-1, zlib1 |

| Library | Licence | Licence text in the wheel (`elliprof/_notices/`) |
|---|---|---|
| libgfortran, libgcc_s, libgcc_s_seh-1 (GCC) | GNU GPL v3 with the GCC Runtime Library Exception 3.1 | `GPL-3.0.txt`, `GCC-RUNTIME-LIBRARY-EXCEPTION-3.1.txt` |
| libquadmath (GCC) | GNU LGPL v2.1 or later | `LGPL-2.1.txt` |
| libwinpthread (MinGW-w64 winpthreads) | MIT-style, with parts under a BSD-style licence (Lockless Inc.) | `winpthreads-COPYING.txt` |
| zlib1 (zlib) | zlib licence | `zlib-LICENSE.txt` |

The same texts are also in the wheel's `.dist-info/licenses/licenses/` directory and in the repository's `licenses/` directory.

The GCC libraries are unmodified builds from each platform's toolchain: conda-forge (macOS), the manylinux `gcc-toolset` (manylinux), Alpine Linux (musllinux) and MSYS2 UCRT64 (Windows). Their corresponding source code is the GNU Compiler Collection, available from <https://gcc.gnu.org/> and from those distributions' source packages. The winpthreads source is at <https://www.mingw-w64.org/> and zlib's at <https://zlib.net/>.

## System libraries (not bundled)

zlib (used by CFITSIO) on macOS and Linux, the C and maths libraries, and system frameworks.

## Python dependencies (installed by pip, not bundled)

| Package | Licence |
|---|---|
| numpy | BSD 3-Clause |
| pandas | BSD 3-Clause |

Optional, for tests and the notebook: astropy (BSD 3-Clause), matplotlib (matplotlib licence), nbclient, nbformat and ipykernel (BSD 3-Clause), pytest (MIT).
