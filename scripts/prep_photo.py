"""Turn a photo into a grayscale image ready for ASCII conversion.

    py prep_photo.py ../source/portrait.jpg

Three things have to happen before a photo converts into a readable portrait.

Background removal. The ASCII ramp maps bright to blank, so a *white* backdrop
disappears into spaces and only the subject prints. A mid-tone backdrop — the
warm orange wall in the source photo — maps to mid-density glyphs instead, and
the face ends up embedded in a solid rectangle of noise. Cutting the subject out
and compositing onto pure white is what makes the silhouette read.

Cropping. A three-quarter body shot spends most of its columns on a suit. Faces
are what people recognise, so the crop is driven by the subject's own alpha mask
and biased upward to hold the head and shoulders.

Contrast. Camera exposure keeps skin in a narrow mid band. The ramp has only a
dozen steps, so a narrow band collapses into one or two glyphs and the face goes
flat. Stretching the histogram spends the whole ramp on the subject.
"""

import pathlib
import sys

import numpy as np
from PIL import Image

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "source" / "portrait-prepped.png"

# Width-to-height of the finished crop, chosen so the portrait lands level with
# info-card.svg beside it in the README table. Derivation:
#
#   the card renders 490x337, so the portrait must be 337 tall at 370 wide
#   at a natural width of 618 that is a natural height of 618 * 337/370 = 563
#   minus the 34px title bar and 2x18 padding leaves 493 of art
#   in a content box 618 - 36 = 582 wide
#   art aspect = 582 / 493
TARGET_ASPECT = 582 / 493

# How much of the subject's height to keep, measured down from the top of the
# mask. 0.62 lands around mid-chest on a standing three-quarter shot.
KEEP = 0.62


def cutout(img):
    """Isolate the subject and composite it onto pure white."""
    try:
        from rembg import remove
    except ImportError:
        sys.exit(
            "rembg is required to separate the subject from the background.\n"
            "  py -m pip install -r requirements-portrait.txt\n"
            "First run downloads a ~176 MB model, once, locally. Both are free."
        )

    rgba = remove(img.convert("RGBA"))
    alpha = np.array(rgba.getchannel("A"))

    white = Image.new("RGB", rgba.size, (255, 255, 255))
    white.paste(rgba, mask=rgba.getchannel("A"))
    return white, alpha


def crop_to_subject(img, alpha):
    """Frame the head and shoulders, using the mask to find the subject."""
    ys, xs = np.nonzero(alpha > 24)
    if len(xs) == 0:
        return img

    top, bottom = ys.min(), ys.max()
    left, right = xs.min(), xs.max()

    height = int((bottom - top) * KEEP)
    width = int(height * TARGET_ASPECT)

    # A tall source frame cannot always supply the width the aspect asks for —
    # a 688px-wide photo needs 741px to pair with a 628px-tall crop. Shrink to
    # the largest correctly proportioned box that fits rather than clamping the
    # width alone, which would silently change the aspect and leave the
    # portrait taller than the card it sits beside.
    if width > img.width:
        width = img.width
        height = int(width / TARGET_ASPECT)

    # Centre horizontally on the head rather than the whole silhouette: the
    # shoulders are wider and would pull the face off-centre.
    head_band = alpha[top:top + max(1, (bottom - top) // 5)]
    head_xs = np.nonzero(head_band > 24)[1]
    cx = int(head_xs.mean()) if len(head_xs) else (left + right) // 2

    x0 = max(0, min(cx - width // 2, img.width - width))
    y0 = max(0, top - int(height * 0.06))          # a little air above the head
    return img.crop((x0, y0, min(x0 + width, img.width),
                     min(y0 + height, img.height)))


def stretch(img, lo=1.5, hi=99.0, gamma=0.95):
    """Rescale the histogram so the subject uses the full 0-255 range."""
    a = np.asarray(img.convert("L"), dtype=np.float32)

    # Percentiles over the non-white pixels only. Including the blown-out
    # background would put the top of the range at pure white and undo the
    # stretch entirely.
    subject = a[a < 250]
    if subject.size < 100:
        subject = a
    p_lo, p_hi = np.percentile(subject, lo), np.percentile(subject, hi)
    if p_hi - p_lo < 1:
        p_lo, p_hi = a.min(), max(a.max(), a.min() + 1)

    a = np.clip((a - p_lo) / (p_hi - p_lo), 0, 1) ** gamma
    return Image.fromarray((a * 255).astype(np.uint8), mode="L")


def main():
    if len(sys.argv) < 2:
        sys.exit("usage: py prep_photo.py <photo>")
    src = pathlib.Path(sys.argv[1])
    if not src.exists():
        sys.exit(f"no such file: {src}")

    img = Image.open(src)
    print(f"in    {src.name}  {img.width}x{img.height}")

    flat, alpha = cutout(img)
    coverage = (alpha > 24).mean()
    print(f"mask  subject covers {coverage:.0%} of the frame")
    if coverage < 0.05:
        sys.exit("subject mask is nearly empty — background removal failed")

    cropped = crop_to_subject(flat, alpha)
    print(f"crop  {cropped.width}x{cropped.height}  "
          f"(aspect {cropped.width / cropped.height:.3f}, "
          f"target {TARGET_ASPECT:.3f})")

    final = stretch(cropped)
    a = np.asarray(final)
    print(f"tone  min {a.min()}  mean {a.mean():.0f}  max {a.max()}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    final.save(OUT)
    print(f"out   {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
