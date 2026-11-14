#!/usr/bin/env python3
"""Shared helpers for origin_lab.

Design rules that every module here follows:

1. **Stdlib only.** No numpy, pandas, scipy or network. Every page in `origin_lab/` must be
   reproducible from the committed data on a bare Python 3.11, so the CI job has nothing to
   install and nothing to fetch.
2. **Deterministic.** No clock, no randomness, no directory-order dependence. Two consecutive
   builds must produce byte-identical output.
3. **Read-only on inputs.** Nothing under `data/`, `depth_lab/`, `desk/`, `line_lab/` or anywhere
   else in the repository is written by this package.
4. **Blank, never invented.** A value that cannot be traced to a source is rendered as a blank cell
   with a link to `flagged.html`, never as a zero, a dash or a plausible-looking number.
"""
from __future__ import annotations

import csv
import html
import json
import math
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
RAW = ROOT / "data" / "raw"
DATA = BASE / "data"
OUT = BASE

# The pinned nflverse commit this repository already built everything else on. Quoted, not re-derived.
NFLVERSE_COMMIT = "a270278f3ac4e937295fe6a27814b3c4a2b62645"
NFLVERSE_TREE = f"https://github.com/nflverse/nfldata/tree/{NFLVERSE_COMMIT}"


def raw_file(name: str) -> str:
    return f"{NFLVERSE_TREE}/data/{name}"


# --------------------------------------------------------------------------------------------
# Source register. Every row on every page links one of these by id.
# --------------------------------------------------------------------------------------------
SOURCES = {
    "S01": {
        "id": "S01",
        "publisher": "NFL.com",
        "title": "2026 Week 10 schedule (official)",
        "url": "https://www.nfl.com/schedules/2026/REG10/",
        "tier": "official",
        "what_it_provides": "Week 10 fixtures, kickoff times, and the one Week 10 game with a final score at capture.",
    },
    "S02": {
        "id": "S02",
        "publisher": "NFL.com",
        "title": "2026 league standings (official)",
        "url": "https://www.nfl.com/standings/league/2026/REG",
        "tier": "official",
        "what_it_provides": "All 32 clubs: W-L-T, points for, points against. Used to verify the results feed in aggregate.",
    },
    "S03": {
        "id": "S03",
        "publisher": "NFL.com",
        "title": "2026 Week 9 scores (official)",
        "url": "https://www.nfl.com/scores/2026/REG9",
        "tier": "official",
        "what_it_provides": "Final scores for all 15 Week 9 games and the two clubs on bye.",
    },
    "S04": {
        "id": "S04",
        "publisher": "NFL Football Operations",
        "title": "2026 NFL Rulebook (official)",
        "url": "https://operations.nfl.com/rules-officiating/2026-nfl-rulebook",
        "tier": "official",
        "what_it_provides": "Playing rules, including the overtime provisions that decide whether a regular-season game can end tied.",
    },
    "S05": {
        "id": "S05",
        "publisher": "nflverse / nfldata (pinned commit)",
        "title": "games.csv — schedule, scores and closing market numbers",
        "url": raw_file("games.csv"),
        "tier": "dataset",
        "what_it_provides": "One row per game 1999-2026: final scores, closing spread, closing total, closing moneylines.",
    },
    "S06": {
        "id": "S06",
        "publisher": "nflverse / nfldata (pinned commit)",
        "title": "closing_lines.csv — per-side closing prices 2006-2018",
        "url": raw_file("closing_lines.csv"),
        "tier": "dataset",
        "what_it_provides": "Closing moneyline / spread / total with price and settled outcome, one row per side.",
    },
    "S07": {
        "id": "S07",
        "publisher": "nflverse / nfldata (pinned commit)",
        "title": "initial_lines.csv — opening numbers, 2021 only",
        "url": raw_file("initial_lines.csv"),
        "tier": "dataset",
        "what_it_provides": "The only opening numbers available anywhere in this repository: Westgate (WSGT) spreads and totals for the 2021 season.",
    },
    "S08": {
        "id": "S08",
        "publisher": "nflverse / nfldata (pinned commit)",
        "title": "sc_lines.csv — secondary-book spreads 2013-2020",
        "url": raw_file("sc_lines.csv"),
        "tier": "dataset",
        "what_it_provides": "A second book's spread, used only as a cross-book consistency check.",
    },
    "S09": {
        "id": "S09",
        "publisher": "nflverse / nfldata (pinned commit)",
        "title": "teams.csv — club code disambiguation",
        "url": raw_file("teams.csv"),
        "tier": "dataset",
        "what_it_provides": "Maps the three-letter codes used by the league, the dataset and the clubs onto each other.",
    },
    "S10": {
        "id": "S10",
        "publisher": "NFL.com",
        "title": "Official NFL injury report, Week 10 2026",
        "url": "https://www.nfl.com/injuries/",
        "tier": "official",
        "what_it_provides": "Per-club player availability as published by the league. Transcribed by session arena/3436db70-korea3 into depth_lab/data/raw/nfl_injury_w10_2026.json and reused here without modification.",
    },
    "S11": {
        "id": "S11",
        "publisher": "Member clubs (31 sites)",
        "title": "Club-published depth charts, Week 10 2026",
        "url": "https://www.nfl.com/teams/",
        "tier": "dataset",
        "what_it_provides": "The only published source of ordered depth (1st/2nd/3rd/4th string) per position. Transcribed by session arena/3436db70-korea3 into depth_lab/data/raw/depth_group*.json and reused here without modification. Twelve of the 31 clubs label their own chart 'unofficial'; the classification question is on flagged.html.",
    },
    "S13": {
        "id": "S13",
        "publisher": "NFL.com",
        "title": "2026 Week 8 scores (official)",
        "url": "https://www.nfl.com/scores/2026/week-8",
        "tier": "official",
        "what_it_provides": "Final scores for all 14 Week 8 games and the four clubs on bye. Fills the 13 Week 8 games the pinned dataset never saw.",
    },
    "S12": {
        "id": "S12",
        "publisher": "This repository",
        "title": "origin_lab generator source",
        "url": "https://github.com/karagemop466-tech/Korea3/tree/main/origin_lab",
        "tier": "internal",
        "what_it_provides": "The code that produced every derived number, so any figure can be re-derived by a reader.",
    },
}

TIER_NOTE = {
    "official": "Published by the league or its Football Operations division.",
    "dataset": "Third-party or club-published. No official publisher prints NFL prices; see flagged.html F-A01.",
    "internal": "Produced by this repository. Not external evidence.",
}


# --------------------------------------------------------------------------------------------
# Small numeric helpers
# --------------------------------------------------------------------------------------------
def mean(xs):
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def pstdev(xs):
    xs = list(xs)
    if len(xs) < 2:
        return None
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / len(xs))


def sstdev(xs):
    xs = list(xs)
    if len(xs) < 2:
        return None
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def pearson(xs, ys):
    xs, ys = list(xs), list(ys)
    n = len(xs)
    if n != len(ys) or n < 3:
        return None
    mx, my = mean(xs), mean(ys)
    sxy = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    sxx = sum((a - mx) ** 2 for a in xs)
    syy = sum((b - my) ** 2 for b in ys)
    if sxx <= 0 or syy <= 0:
        return None
    return sxy / math.sqrt(sxx * syy)


def _norm_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def fisher_ci(r: float, n: int, level: float = 1.959963984540054):
    """Two-sided CI for a Pearson r via the Fisher z transform. Returns (low, high) or (None, None)."""
    if r is None or n is None or n < 4:
        return None, None
    if abs(r) >= 1.0:
        return None, None
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    lo = math.tanh(z - level * se)
    hi = math.tanh(z + level * se)
    return lo, hi


def american_to_decimal(price):
    """American price -> decimal odds. Returns None if the price is not a usable number."""
    if price is None or price == "":
        return None
    try:
        p = float(price)
    except (TypeError, ValueError):
        return None
    if p == 0:
        return None
    if p > 0:
        return 1.0 + p / 100.0
    return 1.0 + 100.0 / abs(p)


def decimal_to_american(dec):
    if dec is None or dec <= 1.0:
        return None
    if dec >= 2.0:
        return round((dec - 1.0) * 100.0)
    return round(-100.0 / (dec - 1.0))


def prob_to_american(p):
    if p is None or p <= 0 or p >= 1:
        return None
    return decimal_to_american(1.0 / p)


def implied_prob(price):
    dec = american_to_decimal(price)
    return 1.0 / dec if dec else None


def devig(home_price, away_price):
    """Remove the overround from a two-way price pair. Returns (p_home, overround) or (None, None)."""
    ph, pa = implied_prob(home_price), implied_prob(away_price)
    if ph is None or pa is None or (ph + pa) <= 0:
        return None, None
    return ph / (ph + pa), (ph + pa) - 1.0


def round_or_none(x, nd=3):
    if x is None:
        return None
    return round(x, nd)


# --------------------------------------------------------------------------------------------
# CSV loading
# --------------------------------------------------------------------------------------------
def load_csv(path: Path):
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def fnum(row, key):
    v = row.get(key, "")
    if v is None or v == "":
        return None
    try:
        return float(v)
    except ValueError:
        return None


def fint(row, key):
    v = row.get(key, "")
    if v is None or v == "":
        return None
    try:
        return int(float(v))
    except ValueError:
        return None


# --------------------------------------------------------------------------------------------
# HTML rendering
# --------------------------------------------------------------------------------------------
def esc(x) -> str:
    return html.escape("" if x is None else str(x), quote=True)


NAV = [
    ("index.html", "Overview"),
    ("price-snapshots.html", "Price snapshots"),
    ("results-feed.html", "Results feed"),
    ("origination.html", "Origination order"),
    ("fair-lines.html", "Fair / market / diff"),
    ("leaderboard.html", "Leaderboard"),
    ("replacement-depth.html", "Replacement depth"),
    ("correlations.html", "Correlations"),
    ("gates.html", "Promotion &amp; demotion"),
    ("questions.html", "Open questions"),
    ("suggestions.html", "Suggestions board"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged for review"),
]


def page(title, subtitle, body, active=None):
    nav = "".join(
        f'<a class="nav-link{" is-active" if active == href else ""}" href="{href}">{label}</a>'
        for href, label in NAV
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} — NFL origination desk</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="site-header">
  <a class="brand" href="index.html">NFL origination desk</a>
  <nav class="nav">{nav}</nav>
</header>
<main class="wrap">
  <h1>{esc(title)}</h1>
  <p class="lede">{subtitle}</p>
{body}
  <footer class="site-footer">
    <p>Generated by <code>origin_lab/build.py</code> from committed data. Every table row links the
    publisher it came from. A blank cell is a value no official publisher printed; it is never filled
    in. See <a href="flagged.html">Flagged for review</a>.</p>
    <p>A dash in a table cell means no source in this repository printed that value. It is never
    filled in, inferred or estimated. Values that need an owner's decision are on
    <a href="flagged.html">Flagged for review</a>.</p>
    <p><a href="../index.html">Back to the site index</a> · <a href="sources.html">Sources</a></p>
  </footer>
</main>
</body>
</html>
"""


def table(headers, rows, note=None, cls=""):
    """rows: list of list[str] already escaped by the caller (call esc() on every cell)."""
    th = "".join(f"<th>{h}</th>" for h in headers)
    tb = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    nt = f'<p class="table-note">{note}</p>' if note else ""
    return (
        f'<div class="table-wrap"><table class="{cls}"><thead><tr>{th}</tr></thead>'
        f"<tbody>{tb}</tbody></table></div>{nt}"
    )


def blank_cell(flag_id=None):
    """The one canonical way to render an unknown value."""
    target = f"flagged.html#{flag_id}" if flag_id else "flagged.html"
    return f'<span class="blank" title="No official publisher printed this value">—</span> <a class="blank-link" href="{target}">unverified</a>'


def src_link(sid, label=None):
    s = SOURCES[sid]
    lab = label or s["id"]
    return f'<a href="{esc(s["url"])}" title="{esc(s["title"])}">{esc(lab)}</a>'


def num(x, nd=3, dash=True):
    if x is None:
        return "—" if dash else ""
    if isinstance(x, float):
        return f"{x:.{nd}f}"
    return esc(x)


def kpi(items):
    out = []
    for label, value, sub in items:
        out.append(
            f'<div class="kpi"><div class="kpi-label">{esc(label)}</div>'
            f'<div class="kpi-value">{value}</div>'
            f'<div class="kpi-sub">{esc(sub)}</div></div>'
        )
    return '<div class="kpi-row">' + "".join(out) + "</div>"


def write_page(name: str, content: str):
    (OUT / name).write_text(content, encoding="utf-8")
