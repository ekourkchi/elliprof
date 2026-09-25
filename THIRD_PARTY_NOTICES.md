# Third-party components

The binary wheels of elliprof contain, besides the elliprof code itself (whose licensing is pending, see [LICENSING_STATUS.md](LICENSING_STATUS.md)), the following third-party components.

## CFITSIO 4.7.0

Statically linked into the `elliprof_native` backend in every binary wheel. It is built by `tools/ci/build_cfitsio.sh` from the official source tarball, pinned by SHA-256, without curl and without bzip2 support. Source builds link whatever CFITSIO is installed.

HEASARC, NASA Goddard Space Flight Center: <https://heasarc.gsfc.nasa.gov/fitsio/>

Licence (from `licenses/License.txt` in the CFITSIO distribution):

> Copyright (Unpublished--all rights reserved under the copyright laws of the United States), U.S. Government as represented by the Administrator of the National Aeronautics and Space Administration. No copyright is claimed in the United States under Title 17, U.S. Code.
>
> Permission to freely use, copy, modify, and distribute this software and its documentation without fee is hereby granted, provided that this copyright notice and disclaimer of warranty appears in all copies.
>
> DISCLAIMER:
>
> THE SOFTWARE IS PROVIDED 'AS IS' WITHOUT ANY WARRANTY OF ANY KIND, EITHER EXPRESSED, IMPLIED, OR STATUTORY, INCLUDING, BUT NOT LIMITED TO, ANY WARRANTY THAT THE SOFTWARE WILL CONFORM TO SPECIFICATIONS, ANY IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND FREEDOM FROM INFRINGEMENT, AND ANY WARRANTY THAT THE DOCUMENTATION WILL CONFORM TO THE SOFTWARE, OR ANY WARRANTY THAT THE SOFTWARE WILL BE ERROR FREE. IN NO EVENT SHALL NASA BE LIABLE FOR ANY DAMAGES, INCLUDING, BUT NOT LIMITED TO, DIRECT, INDIRECT, SPECIAL OR CONSEQUENTIAL DAMAGES, ARISING OUT OF, RESULTING FROM, OR IN ANY WAY CONNECTED WITH THIS SOFTWARE, WHETHER OR NOT BASED UPON WARRANTY, CONTRACT, TORT , OR OTHERWISE, WHETHER OR NOT INJURY WAS SUSTAINED BY PERSONS OR PROPERTY OR OTHERWISE, AND WHETHER OR NOT LOSS WAS SUSTAINED FROM, OR AROSE OUT OF THE RESULTS OF, OR USE OF, THE SOFTWARE OR SERVICES PROVIDED HEREUNDER.

## GCC Fortran runtime libraries

These are shipped as shared libraries next to the backend by the wheel-repair tools (delocate, auditwheel, delvewheel), so they are dynamically linked and replaceable.

| Library | Wheels (verified) | Licence |
|---|---|---|
| libgfortran | macOS arm64, Linux aarch64, Linux x86_64 | GNU GPL v3 with the **GCC Runtime Library Exception 3.1** |
| libgcc_s | macOS arm64 (Linux uses the system copy) | GNU GPL v3 with the GCC Runtime Library Exception 3.1 |
| libquadmath | macOS arm64, Linux x86_64 | GNU LGPL v2.1 or later |

The Runtime Library Exception allows these libraries to be distributed with programs compiled by GCC, under terms of the distributor's choice. libquadmath is under the LGPL. Shipping it as an unmodified, replaceable shared library, with its licence text, meets the LGPL's terms.

The Windows wheels are expected to add `libgcc_s_seh-1.dll`, `libwinpthread-1.dll` (MinGW-w64, permissive licence) and `zlib1.dll` (zlib licence) from MSYS2. They haven't been built yet, so this list must be checked against the first real Windows wheel.

GCC: <https://gcc.gnu.org/>. Licence texts: <https://www.gnu.org/licenses/gcc-exception-3.1.html>, <https://www.gnu.org/licenses/gpl-3.0.html>, <https://www.gnu.org/licenses/lgpl-2.1.html>.

**Before release:** put the full texts of these licences in the wheel (see LICENSING_STATUS.md). They are not included yet.

## System libraries (not bundled)

* zlib (`libz`), used by CFITSIO, comes from the operating system on macOS and Linux (it's in the manylinux policy).
* The C library, maths library and system frameworks.

## Python dependencies (installed by pip, not bundled)

| Package | Licence |
|---|---|
| numpy | BSD 3-Clause |
| pandas | BSD 3-Clause |
| astropy | BSD 3-Clause |

Optional: matplotlib (PSF-based matplotlib licence), nbclient / nbformat / ipykernel (BSD 3-Clause), pytest (MIT).
