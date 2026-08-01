"""Assert the generated SVGs are correct without looking at them.

The reveal animations cannot be confirmed visually: any renderer honouring
`prefers-reduced-motion: reduce` — the Browser pane among them — never plays
them. So correctness is checked in the source instead: geometry stays inside
the canvas, every animated element carries its declaration, widths line up
across components, and the documents parse.

Run after any generator change.  py verify.py
"""

import pathlib
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter

# On stdlib ElementTree rather than defusedxml: the only documents parsed here
# are the four SVGs our own generators wrote moments earlier. Nothing external
# reaches this parser as XML — the scraped contribution data arrives as JSON,
# and every value crossing into the SVG is an int, an ISO date, or passed
# through theme.esc(), so no DOCTYPE or entity declaration can ever appear in
# the output. Adding a dependency to a repo whose point is minimal dependencies
# would buy nothing here. Revisit if this script is ever pointed at SVGs from
# somewhere else.

ROOT = pathlib.Path(__file__).resolve().parent.parent
SVG_NS = "{http://www.w3.org/2000/svg}"

failures = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg)
    if not cond:
        failures.append(msg)


def geometry(path):
    """Every positioned element must sit inside the canvas."""
    root = ET.parse(path).getroot()
    w, h = float(root.get("width")), float(root.get("height"))
    worst = []
    for el in root.iter():
        tag = el.tag.replace(SVG_NS, "")
        try:
            if tag == "rect":
                x, y = float(el.get("x", 0)), float(el.get("y", 0))
                x2 = x + float(el.get("width", 0))
                y2 = y + float(el.get("height", 0))
            elif tag == "text":
                x, y = float(el.get("x", 0)), float(el.get("y", 0))
                x2, y2 = x, y
            else:
                continue
        except (TypeError, ValueError):
            continue
        if x < -1 or y < -1 or x2 > w + 1 or y2 > h + 1:
            worst.append((tag, x, y, x2, y2))
    return w, h, worst, root


def report(name):
    path = ROOT / name
    print(f"\n{name}")
    if not path.exists():
        check(False, "file exists")
        return None
    w, h, out, root = geometry(path)
    check(True, f"parses as XML  ·  {w:.0f} x {h:.0f}")
    check(not out, f"all elements within canvas"
                   + (f" — {len(out)} outside: {out[:3]}" if out else ""))
    check(root.find(f"{SVG_NS}title") is not None, "has <title> for screen readers")
    check(root.get("role") == "img", 'has role="img"')
    return w, h, root, path.read_text(encoding="utf-8")


print("=" * 62)
print("Generated SVG verification")
print("=" * 62)

natural = {}   # stem -> (width, height) as authored

# --- heatmap -----------------------------------------------------------------
r = report("contrib-heatmap.svg")
if r:
    w, h, root, src = r
    natural["contrib-heatmap"] = (w, h)
    pops = [e for e in root.iter(f"{SVG_NS}rect") if e.get("class") == "pop"]
    check(len(pops) in range(364, 372),
          f"day cells present: {len(pops)} (expect 365-371)")
    check(all("animation-delay" in (e.get("style") or "") for e in pops),
          "every day cell carries an animation-delay")
    check("@keyframes pop" in src, "@keyframes pop is defined")
    check("transform-box: fill-box" in src,
          "pop uses transform-box: fill-box (else cells fly off-canvas)")
    check("prefers-reduced-motion" in src, "reduced-motion fallback present")
    delays = [int(re.search(r"animation-delay:(\d+)ms", e.get("style")).group(1))
              for e in pops]
    check(max(delays) < 1500, f"reveal completes quickly: {max(delays)}ms last delay")
    lv = Counter(e.get("fill") for e in pops)
    print(f"    level spread: " +
          "  ".join(f"{c}={n}" for c, n in lv.most_common()))
    lit = sum(n for c, n in lv.items() if c != "#161b22")
    check(lit > 0, f"{lit} lit cells")
    check(len(lv) >= 4, f"{len(lv)} distinct colours in use (ramp not collapsed)")

# --- info card ---------------------------------------------------------------
r = report("info-card.svg")
if r:
    w, h, root, src = r
    natural["info-card"] = (w, h)
    rows = [e for e in root.iter() if (e.get("class") or "") == "fade"]
    check(len(rows) >= 8, f"{len(rows)} animated rows")
    check("@keyframes fade" in src, "@keyframes fade is defined")

# --- shipped -----------------------------------------------------------------
r = report("shipped.svg")
if r:
    w, h, root, src = r
    natural["shipped"] = (w, h)
    rows = [e for e in root.iter() if (e.get("class") or "") == "fade"]
    check(len(rows) >= 7, f"{len(rows)} animated rows")

# --- portrait ----------------------------------------------------------------
r = report("ascii-portrait.svg")
if r:
    w, h, root, src = r
    natural["ascii-portrait"] = (w, h)
    rows = [e for e in root.iter(f"{SVG_NS}text") if e.get("class") == "wipe"]
    check(len(rows) > 20, f"{len(rows)} glyph rows")
    check(all(e.get("textLength") for e in rows),
          "every row pins its textLength (columns align on any font)")
    check(all(e.get("lengthAdjust") == "spacing" for e in rows),
          'lengthAdjust="spacing" (glyph shapes preserved)')
    lens = {len(e.text or "") for e in rows}
    check(len(lens) == 1, f"all rows same character count: {lens}")

# --- rendered layout ---------------------------------------------------------
# What matters is not the SVGs' natural sizes but the sizes the README asks for.
# Each is scaled by its width= attribute, so the displayed height follows from
# the natural aspect. These are the numbers a reader actually sees.
print("\nrendered layout (from README.md)")

readme = (ROOT / "README.md").read_text(encoding="utf-8")
asked = {m.group(1): float(m.group(2)) for m in
         re.finditer(r'<img src="\./([\w-]+)\.svg" width="(\d+)"', readme)}

check(set(asked) == {"contrib-heatmap", "ascii-portrait", "info-card", "shipped"},
      f"README references all four SVGs: {sorted(asked)}")

shown = {}
for name, w_shown in asked.items():
    nat = natural.get(name)
    if not nat:
        continue
    scale = w_shown / nat[0]
    shown[name] = (w_shown, nat[1] * scale)
    print(f"    {name:<18} {w_shown:>5.0f} x {nat[1] * scale:>5.1f}"
          f"   (natural {nat[0]:.0f} x {nat[1]:.0f}, scale {scale:.3f})")

if {"ascii-portrait", "info-card", "contrib-heatmap"} <= shown.keys():
    # The newline between the two <img> tags collapses to one space, ~4.4px at
    # GitHub's 16px base font. That space is the gutter.
    GUTTER = 4.4
    row = shown["ascii-portrait"][0] + GUTTER + shown["info-card"][0]
    check(abs(row - shown["contrib-heatmap"][0]) <= 6,
          f"portrait + gutter + card = {row:.1f} lines up with the "
          f'{shown["contrib-heatmap"][0]:.0f} wide panels')

    dh = abs(shown["ascii-portrait"][1] - shown["info-card"][1])
    check(dh <= 12,
          f"portrait and card render within {dh:.1f}px of the same height "
          f"(they sit side by side)")

if {"contrib-heatmap", "shipped"} <= shown.keys():
    check(shown["contrib-heatmap"][0] == shown["shipped"][0],
          f'heatmap and shipped share a displayed width: '
          f'{shown["shipped"][0]:.0f}')

check(all(w <= 880 for w, _ in shown.values()),
      "nothing exceeds GitHub's ~880px README content width")

print("\n" + "=" * 62)
if failures:
    print(f"{len(failures)} FAILED")
    for f in failures:
        print("  - " + f)
    sys.exit(1)
print("all checks passed")
