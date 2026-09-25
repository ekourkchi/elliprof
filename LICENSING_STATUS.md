# Licensing status

**Public redistribution of this package is on hold until the licensing of the legacy MONSTA/VISTA source code is resolved.** Nothing has been published to PyPI or anywhere else.

The package and its build are technically complete, but no open-source licence has been assigned. This file is not a licence and grants no rights. The status of each part, as found in the source, is below.

## 1. Legacy numerical code in `src/original/` and `include/`

These are byte-identical copies of files from MONSTA (`monsta/libvista/fcode/`, plus `mongo.par` from `monsta/libmongo/include/`).

| Files | Authorship / notice found in the source | Licence found |
|---|---|---|
| `assign.f`, `value.f`, `operate.f`, `variable.f`, `vistalink.inc`, `imagelink.inc` | "Author: Tod R. Lauer" (1982, Lick VISTA) | **none** |
| `dissect.f`, `upper.f` | "Author: Richard J. Stover" (1983, Lick VISTA) | **none** |
| `elliprof.f`, `jtutil.f` ("Various random utilities from JT"), `profile.inc` | no author line; MONSTA is John Tonry's; "JT" = Tonry | **none** |
| `gcfit.f` | no author line | **none** (see §2) |
| `mongo.par` | "Mongo Interactive Graphics Software, Copyright (c) 1987, 1994 - John Tonry" | the Mongo sources carry the **GNU GPL, version 1 or later** (full notice in MONSTA's `libmongo/fonts.dat`) |

Code with no licence is, by default, all rights reserved by its copyright holders. Redistribution in source or binary form (the wheels contain compiled copies) needs permission from the rights holders. They are probably John Tonry, and possibly Tod Lauer, Richard Stover and/or Lick Observatory / the University of California.

## 2. Numerical Recipes routines

These routines, compiled into the backend, are recognisably from *Numerical Recipes* (Press, Teukolsky, Vetterling & Flannery), including NR's own comment text:

* `gcfit.f`: `MRQMIN`, `MRQCOF`, `COVSRT`, `GAUSSJ`, `GAMMQ`, `GSER`, `GCF`, `GAMMLN` (used only by ELLIPROF's `GC` mode);
* `jtutil.f`: `ZBRENT` (modified by JT; used by ELLIPROF's `MODEL` option).

The Numerical Recipes licence does not permit redistribution of the routines in source or binary form without a separate licence from Numerical Recipes Software. If a Numerical Recipes licence applies, it is also incompatible with the GPL of the Mongo code.

The origin of `INVERT` and `DOFITLPOLY` in `jtutil.f` is not recorded and should be confirmed.

Nothing has been changed for licensing reasons. Replacing these routines would change the numerical code and needs an explicit decision.

## 3. New code in this package

The driver and shims (`src/shim/`), the Python package (`python/elliprof/`), the tests, build files and documentation were written for this package. Their licence is still to be chosen. It must be compatible with however §1 and §2 are resolved.

## 4. Bundled third-party components

See [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md). Those components (CFITSIO, the GCC Fortran runtime) are freely redistributable under their own licences.

## Before any public release

1. Get written permission, or a licence, for the legacy code in §1 from its rights holders, and settle the GPL status of `mongo.par` / Mongo.
2. Resolve the Numerical Recipes routines in §2: obtain a redistribution licence, or decide explicitly how to replace them and re-validate the numerics.
3. Choose a licence for the new code in §3 that is compatible with the outcome.
4. Put the full licence texts of every bundled component in the wheels (see THIRD_PARTY_NOTICES.md).
5. Only then add a `LICENSE` file and `license` metadata, and consider publishing.
