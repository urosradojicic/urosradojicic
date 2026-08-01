"""Regenerate every SVG, then verify them.

    py build.py            everything that does not need the photo
    py build.py --all      including the portrait

The portrait is skipped by default because it depends on source/ artefacts that
only change when the photo does, and on a toolchain the daily workflow never
installs.
"""

import pathlib
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent

STEPS = [
    ("fetch_contributions.py", False),
    ("render_heatmap.py", False),
    ("make_info_card.py", False),
    ("make_shipped.py", False),
    ("make_portrait.py", True),      # needs --all
]


def main():
    everything = "--all" in sys.argv
    for script, portrait_only in STEPS:
        if portrait_only and not everything:
            print(f"-- skip {script}  (pass --all to include the portrait)")
            continue
        print(f"-- {script}")
        r = subprocess.run([sys.executable, script], cwd=HERE)
        if r.returncode:
            sys.exit(f"{script} failed with code {r.returncode}")

    print("-- verify.py")
    sys.exit(subprocess.run([sys.executable, "verify.py"], cwd=HERE).returncode)


if __name__ == "__main__":
    main()
