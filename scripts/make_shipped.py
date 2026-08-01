"""Render data/profile.json's `shipped` array as a terminal build manifest.

Green squares prove consistency; they say nothing about what was built. This is
the panel that answers that, in the same three columns a build tool would use.

Only projects listed in data/profile.json appear here. Several of the things on
this machine are under client confidentiality or cannot be distributed — that
filtering is deliberate and lives in the data file, not in this script.
"""

import json
import pathlib

import theme

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "profile.json"
OUT = ROOT / "shipped.svg"

W = 860
FS = 11.5
NAME_X = theme.PAD + 14
WHAT_X = theme.PAD + 184
STATUS_R = W - theme.PAD      # status column is right-aligned to here
PITCH = 26


def render(p):
    items = p["shipped"]
    y = theme.TITLE_BAR + theme.PAD + 10
    out = []

    out.append(f'<text class="fade" style="animation-delay:0ms" x="{theme.PAD}" '
               f'y="{y}" font-size="{FS}" fill="{theme.PROMPT}">$ '
               f'<tspan fill="{theme.TEXT}">ls ~/shipped</tspan></text>')
    y += 8
    out.append(f'<line class="fade" style="animation-delay:60ms" x1="{theme.PAD}" '
               f'y1="{y}" x2="{W - theme.PAD}" y2="{y}" stroke="{theme.BORDER}"/>')
    y += 24

    for i, it in enumerate(items):
        delay = 140 + i * 70
        out.append(
            f'<text class="fade" style="animation-delay:{delay}ms" '
            f'x="{theme.PAD}" y="{y}" font-size="{FS}" fill="{theme.PROMPT}">▸</text>'
            f'<text class="fade" style="animation-delay:{delay}ms" x="{NAME_X}" '
            f'y="{y}" font-size="{FS}" font-weight="600" fill="{theme.TEXT}">'
            f'{theme.esc(it["name"])}</text>'
            f'<text class="fade" style="animation-delay:{delay}ms" x="{WHAT_X}" '
            f'y="{y}" font-size="{FS}" fill="{theme.MUTED}">'
            f'{theme.esc(it["what"])}</text>'
            f'<text class="fade" style="animation-delay:{delay}ms" x="{STATUS_R}" '
            f'y="{y}" font-size="{FS}" text-anchor="end" fill="{theme.KEY}">'
            f'{theme.esc(it["status"])}</text>'
        )
        y += PITCH

    y += 2
    out.append(f'<line class="fade" style="animation-delay:{140 + len(items) * 70}ms" '
               f'x1="{theme.PAD}" y1="{y}" x2="{W - theme.PAD}" y2="{y}" '
               f'stroke="{theme.BORDER}"/>')
    y += 20
    out.append(
        f'<text class="fade" style="animation-delay:{180 + len(items) * 70}ms" '
        f'x="{theme.PAD}" y="{y}" font-size="{FS}" fill="{theme.MUTED}">'
        f'{len(items)} shipped  ·  client, hackathon and solo work  ·  '
        f'some projects omitted under client confidentiality</text>'
    )

    height = y + 8 + theme.PAD
    label = "Shipped projects: " + ", ".join(i["name"] for i in items)
    body = theme.window(W, height, f'{p["handle"]} — shipped') + "\n  " + "\n  ".join(out)
    return theme.document(W, height, body, label, theme.REVEAL_CSS), height


def main():
    p = json.loads(DATA.read_text(encoding="utf-8"))
    svg, h = render(p)
    OUT.write_text(svg, encoding="utf-8")
    print(f"{OUT.name}  ·  {W} x {h}  ·  {len(p['shipped'])} projects  "
          f"·  {len(svg):,} bytes")


if __name__ == "__main__":
    main()
