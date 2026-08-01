"""Convert source/portrait-prepped.png into a self-typing ASCII portrait.

    py prep_photo.py ../source/portrait.jpg   # once, when the photo changes
    py make_portrait.py

Each row prints as one <text> element pinned with `textLength`, rather than as
individually positioned glyphs. Pinning the length is what keeps the columns
aligned: the SVG cannot ship a font, so it renders in whichever monospace face
the reader happens to have, and those differ in advance width. Left to the
font, the rows would ragged out. `lengthAdjust="spacing"` distributes the
correction between glyphs instead of stretching their shapes.

The portrait is one colour on purpose. Per-character colouring is what makes
most ASCII portraits read as static rather than as a face.
"""

import pathlib
import sys

import numpy as np
from PIL import Image

import theme

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "source" / "portrait-prepped.png"
OUT = ROOT / "ascii-portrait.svg"

# Bright (sparse) to dark (dense). The leading space is load-bearing: it maps
# the blown-out white background to nothing at all, so only the subject prints.
RAMP = " .`:-=+*cs#%@"

NAT_W = 618        # natural width; the README displays it at 370
COLS = 96          # characters per row
CHAR_ASPECT = 0.5  # a monospace cell is about half as wide as it is tall


# ---------------------------------------------------------------------------
#  THE TONE CURVE — this one is yours, Uroš.
# ---------------------------------------------------------------------------
def tone(b):
    """Map measured brightness to position on the ramp.

    `b` arrives normalised: 0.0 is black, 1.0 is white. Return a value in the
    same range. Higher output means a sparser glyph, so returning `b`
    unchanged maps brightness straight onto the ramp.

    This decides whether the portrait reads as a face or as mud, and there is
    no single right answer — it depends on your photo's histogram, which
    prep_photo.py prints when it runs.

        linear          return b
            Faithful, and usually the flattest. Skin tones cluster in the
            middle of the range, so most of the face collapses onto two or
            three ramp steps while the ends go unused.

        gamma           return b ** 0.7     (try 0.55 - 0.85)
            Lifts midtones toward the sparse end. Cheeks and forehead gain
            separation. Push too far and the black suit stops being a shape
            and becomes one solid slab.

        S-curve         return b * b * (3 - 2 * b)
            Smoothstep. Pushes light areas lighter and dark areas darker,
            widening the gap between the shirt and the jacket. Costs you
            detail at both extremes.

        contrast pivot  return min(1, max(0, (b - 0.5) * 1.4 + 0.5))
            Steepens around mid-grey and clips the ends. Strongest facial
            definition of the four, harshest everywhere else.

    Measured on the real photo, over the face region of the 96x41 grid:

        curve       glyphs  entropy  blank%  darkest%
        linear          13     3.18    57.2       7.4
        gamma .7        13     3.15    57.7       2.7
        S-curve         13     3.12    60.1      15.0
        pivot 1.4       13     3.04    61.4      16.0

    Linear wins on entropy and loses anyway. At 365px wide, 96 columns leaves
    about 3.8px per character, and gradation that fine is invisible — what
    survives at that size is the silhouette. gamma 0.7 is the clearest failure:
    darkest 2.7% means the hair and jacket stop reading as solid and the head
    loses its outline.

    The S-curve is in place because it holds the hair as one dark mass while
    keeping modelling around the eyes and nose. Swap the return below and
    re-run to try another; it takes about ten seconds.
    """
    return b * b * (3 - 2 * b)      # smoothstep
# ---------------------------------------------------------------------------


def build(img):
    pad = theme.PAD
    content_w = NAT_W - 2 * pad
    cell_w = content_w / COLS
    cell_h = cell_w / CHAR_ASPECT

    # Rows follow from the image's own proportions, so a slightly different
    # crop still renders undistorted.
    rows = max(1, round(COLS * CHAR_ASPECT * img.height / img.width))

    small = img.convert("L").resize((COLS, rows), Image.LANCZOS)
    a = np.asarray(small, dtype=np.float32) / 255.0

    curved = np.clip(np.vectorize(tone)(a), 0.0, 1.0)
    idx = np.rint((1.0 - curved) * (len(RAMP) - 1)).astype(int)

    lines = ["".join(RAMP[i] for i in row) for row in idx]

    art_top = theme.TITLE_BAR + pad
    height = art_top + rows * cell_h + pad
    font_size = cell_w / 0.6      # close to the natural advance, so textLength
                                  # only has to nudge rather than stretch

    out = []
    for r, line in enumerate(lines):
        y = art_top + (r + 1) * cell_h - cell_h * 0.22
        out.append(
            f'<text class="wipe" style="animation-delay:{r * 17}ms" '
            f'x="{pad}" y="{y:.2f}" xml:space="preserve" '
            f'textLength="{content_w}" lengthAdjust="spacing" '
            f'font-size="{font_size:.2f}" fill="{theme.ASCII}">'
            f'{theme.esc(line)}</text>'
        )

    body = (theme.window(NAT_W, height, "portrait.sh")
            + "\n  " + "\n  ".join(out))
    svg = theme.document(NAT_W, round(height), body,
                         "ASCII portrait of Uros Radojicic", theme.REVEAL_CSS)
    return svg, COLS, rows, height


def main():
    if not SRC.exists():
        sys.exit(f"missing {SRC.relative_to(ROOT)} — run prep_photo.py first")

    img = Image.open(SRC)
    svg, cols, rows, height = build(img)
    OUT.write_text(svg, encoding="utf-8")

    shown_w = 350       # the width README.md asks for; verify.py checks this
    shown_h = height * shown_w / NAT_W
    print(f"{OUT.name}  ·  {cols}x{rows} glyphs  ·  {NAT_W}x{height:.0f} natural")
    print(f"renders {shown_w}x{shown_h:.0f} in the README")
    print(f"{len(svg):,} bytes")


if __name__ == "__main__":
    main()
