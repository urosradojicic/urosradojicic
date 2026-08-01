"""Scrape the public contribution calendar into data/contributions.json.

No token and no GraphQL. github.com/users/<login>/contributions is the same
fragment the profile page lazy-loads for itself, served unauthenticated.

Note on what this can and cannot see: the endpoint returns whatever GitHub has
decided is publicly visible for the account. Commits to private repositories
are excluded at the source unless "Include private contributions on my profile"
is enabled in settings. No amount of scraping recovers them.

Markup as of 2026-08:

    <td data-date="2025-07-27" data-level="0"
        id="contribution-day-component-0-0" class="ContributionCalendar-day"></td>
    <tool-tip for="contribution-day-component-0-0">No contributions on July 27th.</tool-tip>

The cell is empty. There is no data-count attribute — the number exists only in
the sibling tool-tip's prose, joined by id. A parser that reads only the cells
produces a correctly shaped calendar in which every day is zero, and renders
without raising anything.
"""

import json
import pathlib
import re
import sys
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup

USER = "urosradojicic"
URL = f"https://github.com/users/{USER}/contributions"
OUT = pathlib.Path(__file__).resolve().parent.parent / "data" / "contributions.json"

# "17 contributions on April 13th." / "1 contribution on ..." / "No contributions on ..."
COUNT_RE = re.compile(r"^(No|[\d,]+)\s+contribution", re.I)
TOTAL_RE = re.compile(r"([\d,]+)\s+contributions?\s+in\s+the\s+last\s+year", re.I)


def parse_count(text):
    """Pull the integer out of a tool-tip sentence. 'No contributions' is zero."""
    m = COUNT_RE.match(text.strip())
    if not m:
        raise ValueError(f"unrecognised tool-tip wording: {text!r}")
    head = m.group(1)
    return 0 if head.lower() == "no" else int(head.replace(",", ""))


def scrape(html):
    soup = BeautifulSoup(html, "html.parser")

    # id -> count, from the tool-tips.
    counts = {}
    for tip in soup.find_all("tool-tip"):
        target = tip.get("for")
        if target and target.startswith("contribution-day-component"):
            counts[target] = parse_count(tip.get_text())

    days = []
    for cell in soup.select("td.ContributionCalendar-day"):
        iso = cell.get("data-date")
        if not iso:
            continue  # weekday label cell, not a day
        cid = cell.get("id")
        if cid not in counts:
            raise ValueError(f"no tool-tip found for cell {cid} ({iso})")
        days.append({
            "date": iso,
            "count": counts[cid],
            "level": int(cell.get("data-level", 0)),
        })

    if not days:
        raise ValueError("no day cells parsed — GitHub's markup has changed")

    days.sort(key=lambda d: d["date"])

    # The headline figure GitHub states, kept as a cross-check against our sum.
    stated = None
    h = soup.find(id="js-contribution-activity-description")
    if h:
        m = TOTAL_RE.search(h.get_text())
        if m:
            stated = int(m.group(1).replace(",", ""))

    return days, stated


def streaks(days):
    """Current and longest runs of consecutive active days.

    A zero on the final day does not break the current streak: the day is still
    in progress in some timezone, and GitHub's own UI treats it the same way.
    """
    longest = run = 0
    for d in days:
        run = run + 1 if d["count"] > 0 else 0
        longest = max(longest, run)

    current = 0
    tail = days[:-1] if days and days[-1]["count"] == 0 else days
    for d in reversed(tail):
        if d["count"] == 0:
            break
        current += 1

    return current, longest


def main():
    r = requests.get(URL, headers={
        "User-Agent": f"{USER}-profile-readme (+https://github.com/{USER})",
        "Accept": "text/html",
    }, timeout=30)
    r.raise_for_status()

    days, stated = scrape(r.text)
    total = sum(d["count"] for d in days)
    active = sum(1 for d in days if d["count"] > 0)
    best = max(days, key=lambda d: d["count"])
    current, longest = streaks(days)

    if stated is not None and stated != total:
        # Not fatal: the window GitHub counts and the window it renders can
        # differ by a day at the boundary. Worth surfacing rather than hiding.
        print(f"note: GitHub states {stated}, cells sum to {total}", file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "user": USER,
        "range": {"from": days[0]["date"], "to": days[-1]["date"]},
        "total": total,
        "stated_total": stated,
        "active_days": active,
        "best_day": {"date": best["date"], "count": best["count"]},
        "current_streak": current,
        "longest_streak": longest,
        "days": days,
    }, indent=2), encoding="utf-8")

    print(f"{len(days)} days  ·  {total} contributions  ·  {active} active  "
          f"·  best {best['count']} on {best['date']}  "
          f"·  streak {current} (longest {longest})")


if __name__ == "__main__":
    main()
