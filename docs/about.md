# About and credits

**ELLIPROF was originally developed by John Tonry as part of MONSTA.**

**Maintained by Ehsan Kourkchi (Edwin Kay)**<br>
Email: ekourkchi@gmail.com

Source code and issues: <https://github.com/ekourkchi/elliprof><br>
Package: <https://pypi.org/project/elliprof/>

## History

ELLIPROF is part of MONSTA, an astronomical image-analysis and plotting
package written mostly in Fortran. MONSTA combines the Vista
image-processing system and the Mongo plotting package. Within MONSTA,
ELLIPROF is the command that fits elliptical isophotes to a galaxy and
builds a model image from them.

The `elliprof` package makes ELLIPROF available outside MONSTA, as a
command-line program and a Python library. The numerical code is the
original, compiled unchanged. New code reads and writes FITS files,
prepares the image and handles the command line. See
[How elliprof is built](reference/architecture.md).

The original source files keep their authorship: `elliprof.f`,
`jtutil.f`, `gcfit.f` and `profile.inc` by John Tonry; the Vista
support files by Tod R. Lauer and Richard J. Stover. See
[THIRD_PARTY_NOTICES.md](https://github.com/ekourkchi/elliprof/blob/main/THIRD_PARTY_NOTICES.md).

For the history of the surface brightness fluctuation *method*, see
[SBF history and references](sbf/history.md). The two histories are
separate.

## Licence

The `elliprof` package code is under the MIT License. The original
ELLIPROF sources and the bundled libraries keep their own terms (see
[LICENSE](https://github.com/ekourkchi/elliprof/blob/main/LICENSE) and
[THIRD_PARTY_NOTICES.md](https://github.com/ekourkchi/elliprof/blob/main/THIRD_PARTY_NOTICES.md)).

## Example data

The UGC 12517 image used throughout this site is an HST WFC3/IR F110W
image, distributed with the repository in `examples/u12517` together
with its mask and the calibration from the original analysis.

## Disclaimer

This software is provided as-is, without warranty of any kind. The
maintainer is not responsible for software errors, incorrect scientific
results, data loss, or decisions made using results produced by this
software. Users are responsible for independently validating results for
their scientific application.
