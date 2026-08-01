"""Render data/contributions.json as an animated 53x7 calendar.

Cells reveal on a diagonal — delay rises with (week + weekday) — so the wave
sweeps from the top-left corner to the bottom-right rather than marching
column by column. It plays once and holds.
"""

import json
import pathlib
from datetime import date

import theme

ROOT = pathlib.Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "contributions.json"
OUT = ROOT / "contrib-heatmap.svg"

W = 860
CELL, GAP = 12, 3
PITCH = CELL + GAP
LABEL_COL = 30          # width reserved for Mon/Wed/Fri
GRID_X = theme.PAD + LABEL_COL
MONTH_Y = theme.TITLE_BAR + theme.PAD + 8
GRID_Y = MONTH_Y + 12
WEEKDAYS = {1: "Mon", 3: "Wed", 5: "Fri"}   # row index -> label, Sunday = 0
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun",
          "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def bucket(count, thresholds):
    """Map a day's count onto 0-5 of the colour ramp."""
    if count <= 0:
        return 0
    for i, t in enumerate(thresholds, start=1):
        if count <= t:
            return i
    return 5


def thresholds_for(counts):
    """Choose the four cut points between levels 1 and 5.

    GitHub buckets by quartiles of the active-day distribution. On a calendar
    where most active days are low and a handful are large, quartiles push the
    bulk of real work into the two dimmest greens, and the grid reads as
    emptier than it is.

    Percentiles of the *active* days are used instead, which spreads the same
    days across the full ramp: a typical day still lands mid-green, and only a
    genuine outlier reaches the top colour.
    """
    active = sorted(c for c in counts if c > 0)
    if not active:
        return [1, 2, 3, 4]

    def pct(p):
        return active[min(len(active) - 1, int(len(active) * p))]

    cuts = [pct(0.35), pct(0.60), pct(0.80), pct(0.94)]
    # Keep the cut points strictly increasing, so no level is unreachable.
    for i in range(1, len(cuts)):
        cuts[i] = max(cuts[i], cuts[i - 1] + 1)
    return cuts


def render(d):
    days = d["days"]
    start = date.fromisoformat(days[0]["date"])
    # Column 0 begins on the Sunday of the first week.
    origin = start.toordinal() - ((start.weekday() + 1) % 7)

    cuts = thresholds_for([x["count"] for x in days])

    cells, month_labels, seen_months = [], [], set()
    weeks = 0
    for x in days:
        dt = date.fromisoformat(x["date"])
        offset = dt.toordinal() - origin
        week, row = divmod(offset, 7)
        weeks = max(weeks, week + 1)

        x_pos = GRID_X + week * PITCH
        y_pos = GRID_Y + row * PITCH
        lvl = bucket(x["count"], cuts)
        delay = (week + row) * 11

        cells.append(
            f'<rect class="pop" style="animation-delay:{delay}ms" '
            f'x="{x_pos}" y="{y_pos}" width="{CELL}" height="{CELL}" rx="2.5" '
            f'fill="{theme.HEAT[lvl]}"><title>{theme.esc(x["count"])} on '
            f'{theme.esc(x["date"])}</title></rect>'
        )

        # Label a column the first time a new month appears in it.
        key = (dt.year, dt.month)
        if dt.day <= 7 and key not in seen_months:
            seen_months.add(key)
            month_labels.append(
                f'<text x="{x_pos}" y="{MONTH_Y}" font-size="10.5" '
                f'fill="{theme.MUTED}">{MONTHS[dt.month - 1]}</text>'
            )

    for row, name in WEEKDAYS.items():
        y = GRID_Y + row * PITCH + CELL - 2
        cells.append(
            f'<text x="{theme.PAD}" y="{y}" font-size="10" '
            f'fill="{theme.MUTED}">{name}</text>'
        )

    grid_bottom = GRID_Y + 7 * PITCH - GAP
    foot_y = grid_bottom + 24
    height = foot_y + 10 + theme.PAD

    footer = (
        f'<text x="{theme.PAD}" y="{foot_y}" font-size="11.5" '
        f'fill="{theme.TEXT}">{d["total"]:,} contributions in the last year'
        f'<tspan fill="{theme.MUTED}">   ·   {d["active_days"]} active days'
        f'   ·   longest streak {d["longest_streak"]}'
        f'   ·   best day {d["best_day"]["count"]}</tspan></text>'
    )

    # Legend, right-aligned: Less [][][][][][] More
    swatches, lx = [], W - theme.PAD - 34 - (6 * 13)
    for i, c in enumerate(theme.HEAT):
        swatches.append(
            f'<rect x="{lx + i * 13}" y="{foot_y - 9}" width="10" height="10" '
            f'rx="2" fill="{c}"/>'
        )
    legend = (
        f'<text x="{lx - 6}" y="{foot_y}" font-size="10.5" text-anchor="end" '
        f'fill="{theme.MUTED}">Less</text>'
        + "".join(swatches)
        + f'<text x="{lx + 6 * 13 + 4}" y="{foot_y}" font-size="10.5" '
          f'fill="{theme.MUTED}">More</text>'
    )

    label = (f'{d["total"]} GitHub contributions in the last year, '
             f'{d["active_days"]} active days')
    body = (theme.window(W, height, f'{d["user"]} — contributions')
            + "\n  " + "\n  ".join(month_labels + cells + [footer, legend]))

    return theme.document(W, height, body, label, theme.REVEAL_CSS), weeks, cuts


def main():
    d = json.loads(DATA.read_text(encoding="utf-8"))
    svg, weeks, cuts = render(d)
    OUT.write_text(svg, encoding="utf-8")
    print(f"{OUT.name}  ·  {len(d['days'])} cells over {weeks} weeks  "
          f"·  level cuts at {cuts}  ·  {len(svg):,} bytes")


if __name__ == "__main__":
    main()
