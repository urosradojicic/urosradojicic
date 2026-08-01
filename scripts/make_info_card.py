"""Render data/profile.json's `card` array as a neofetch-style panel.

Keys and values are emitted as separate <text> elements at fixed x positions
rather than one string padded with spaces. Padding would only line up if the
reader happens to have the same monospace font we assumed; absolute positions
line up on every machine.
"""

import json
import pathlib

import theme

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "profile.json"
OUT = ROOT / "info-card.svg"

W = 490
FS = 11.5          # body size
KEY_X = theme.PAD
VAL_X = theme.PAD + 52
PITCH = 24         # vertical distance between rows


def render(p):
    rows = p["card"]
    y = theme.TITLE_BAR + theme.PAD + 10
    out = []

    # neofetch opens with user@host over a rule the same width as it.
    handle = p["handle"]
    out.append(f'<text class="fade" style="animation-delay:0ms" x="{KEY_X}" '
               f'y="{y}" font-size="{FS + 1}" font-weight="600" '
               f'fill="{theme.PROMPT}">{theme.esc(handle)}</text>')
    y += 7
    out.append(f'<line class="fade" style="animation-delay:60ms" x1="{KEY_X}" '
               f'y1="{y}" x2="{W - theme.PAD}" y2="{y}" stroke="{theme.BORDER}"/>')
    y += 22

    for i, row in enumerate(rows):
        delay = 120 + i * 55
        out.append(
            f'<text class="fade" style="animation-delay:{delay}ms" x="{KEY_X}" '
            f'y="{y}" font-size="{FS}" fill="{theme.KEY}">'
            f'{theme.esc(row["key"])}</text>'
            f'<text class="fade" style="animation-delay:{delay}ms" x="{VAL_X}" '
            f'y="{y}" font-size="{FS}" fill="{theme.TEXT}">'
            f'{theme.esc(row["value"])}</text>'
        )
        y += PITCH

    # Closing prompt, the way a terminal sits waiting after printing output.
    y += 4
    out.append(
        f'<text class="fade" style="animation-delay:{120 + len(rows) * 55}ms" '
        f'x="{KEY_X}" y="{y}" font-size="{FS}" fill="{theme.PROMPT}">$ '
        f'<tspan fill="{theme.MUTED}">open to internships and junior roles</tspan>'
        f'</text>'
    )

    height = y + 8 + theme.PAD
    label = f'{p["name"]} — {rows[0]["value"]}'
    body = theme.window(W, height, f'{handle} — whoami') + "\n  " + "\n  ".join(out)
    return theme.document(W, height, body, label, theme.REVEAL_CSS), height


def main():
    p = json.loads(DATA.read_text(encoding="utf-8"))
    svg, h = render(p)
    OUT.write_text(svg, encoding="utf-8")
    print(f"{OUT.name}  ·  {W} x {h}  ·  {len(p['card'])} rows  ·  {len(svg):,} bytes")


if __name__ == "__main__":
    main()
