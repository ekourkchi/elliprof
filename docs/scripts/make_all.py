"""Regenerate every documentation figure in docs/assets/.

    python -m pip install elliprof matplotlib astropy
    python docs/scripts/make_all.py

The elliprof products used by the figures are written to
docs/scripts/_work/ (not tracked).
"""

import runpy
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPTS = (
    "make_u12517_overview.py",
    "make_profile_plots.py",
    "make_isophote_diagram.py",
    "make_boxy_disky_diagram.py",
    "make_sbf_workflow.py",
    "make_sbf_power_spectrum_schematic.py",
)

if __name__ == "__main__":
    import sys
    sys.path.insert(0, str(HERE))
    for name in SCRIPTS:
        print("==", name)
        runpy.run_path(str(HERE / name), run_name="__main__")
