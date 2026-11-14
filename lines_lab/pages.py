"""Render the Line Origination Lab pages from the computed evidence bundle.

Run:   python3 lines_lab/build.py
Check: python3 lines_lab/check.py

Design rules (enforced by ``check.py``):
  * every ``<tbody>`` row carries at least one source link — to an official publisher,
    to the pinned dataset, or to the code in this repository that computes the value;
  * a value that could not be sourced is rendered as a blank with a link to the review
    page, never as zero, never inferred;
  * every internal link resolves to a file that exists;
  * the build is deterministic — no clock, no network, no randomness.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

from . import evidence as EV
from .sources import BY_ID, DATASET, REPO_BLOB, REPO_TREE, SOURCES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "lines_lab"

SESSION = EV.SESSION
TODAY = EV.TODAY
LIVE = "https://karagemop466-tech.github.io/Korea3/lines_lab/"

NAV_GROUPS = [
    ("Start here", [
        ("index.html", "Overview"),
        ("executive.html", "Executive summary"),
        ("findings.html", "Findings & analysis"),
    ]),
    ("The three markets", [
        ("snapshots.html", "Price snapshots"),
        ("results.html", "Verified results"),
        ("fair-vs-market.html", "Fair line vs market"),
    ]),
    ("Origination & signals", [
        ("signals.html", "Signal tests"),
        ("leaderboard.html", "Leaderboard"),
        ("demotion.html", "Promotion & demotion"),
        ("correlations.html", "Correlations"),
        ("parlays.html", "Parlays & combos"),
    ]),
    ("Availability", [
        ("depth.html", "Depth of replacement"),
    ]),
    ("Evidence", [
        ("sources.html", "Source register"),
        ("verification.html", "Verification log"),
    ]),
    ("Decisions", [
        ("suggestions.html", "Suggestions"),
        ("questions.html", "Questions to answer"),
        ("flagged.html", "Flagged for review"),
    ]),
]
PAGES = [p for _, items in NAV_GROUPS for p, _ in items]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def E(v) -> str:
    return html.escape(str(v), quote=False)


def blank(why: str = "unverified") -> str:
    return f'<span class="blank" title="not confirmable from a source">{why}</span>'


def link_repo(path: str, label: str = "repo") -> str:
    return f'<a href="{REPO_BLOB}{path}">{E(label)} ↗</a>'


def link_tree(path: str, label: str = "repo") -> str:
    return f'<a href="{REPO_TREE}{path}">{E(label)} ↗</a>'


def link_source(sid: str) -> str:
    s = BY_ID[sid]
    return f'<a href="{s["url"]}">{E(sid)} ↗</a>'


def src(cell: str) -> str:
    return f'<td class="src">{cell}</td>'


def num(v, digits: int = 3, signed: bool = False, pct: bool = False, suffix: str = "") -> str:
    if v is None:
        return blank()
    try:
        f = float(v)
    except (TypeError, ValueError):
        return E(v)
    if f != f:  # NaN
        return blank()
    if pct:
        return f"{f * 100:+.{digits}f}%" if signed else f"{f * 100:.{digits}f}%"
    return f"{f:+.{digits}f}{suffix}" if signed else f"{f:.{digits}f}{suffix}"


def pill(text: str, kind: str) -> str:
    return f'<span class="pill {kind}">{E(text)}</span>'


def page(title: str, slug: str, crumb: str, lead: str, body: str,
         description: str, badge: str = "Official sources only · blank = unverified") -> str:
    nav = []
    for group, items in NAV_GROUPS:
        parts = []
        for href, label in items:
            cls = ' class="active"' if href == slug else ""
            parts.append(f'<a href="{href}"{cls}>{E(label)}</a>')
        anchors = "".join(parts)
        nav.append(f'<div class="group"><h3>{E(group)}</h3>'
                   f'<nav aria-label="{E(group)}">{anchors}</nav></div>')
    nav_html = "\n".join(nav)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} · Line Origination Lab</title>
<meta name="description" content="{E(description)}">
<link rel="stylesheet" href="assets/style.css">
<script src="assets/app.js" defer></script>
</head>
<body>
<div class="shell">
  <aside class="side">
    <div class="brand"><span class="mark">L</span><span><strong>Line Origination Lab</strong>
      <small>Originate the line · test the signal</small></span></div>
    <p class="tagline">Session {E(SESSION)}<br>Built {E(TODAY)} (UTC)</p>
    {nav_html}
    <div class="foot">Independent research. Not betting advice.<br>
      Blank means <strong>unverified</strong>, never zero.<br>
      <a href="../index.html">← Repository dashboard</a><br>
      <a href="flagged.html">Flagged for review</a>
    </div>
  </aside>
  <div class="content">
    <div class="topbar"><div class="crumb">{crumb}</div>
      <span class="badge">{E(badge)}</span></div>
    <main class="wrap">
      <h1>{E(title)}</h1>
      <p class="lead">{lead}</p>
      {body}
    </main>
    <footer class="site">
      Every table row links its source. A blank cell is an unverified value and links to
      <a href="flagged.html">Flagged for review</a>. Market numbers come from the pinned
      nflverse dataset at commit <code>{DATASET['commit'][:12]}</code>; the NFL does not publish
      betting prices, so <strong>no market value here is labelled official</strong>.
      Settled from final scores by this build. &middot;
      <a href="sources.html">Source register</a> &middot;
      <a href="verification.html">Verification log</a> &middot;
      <a href="{REPO_TREE}">{DATASET['repo']} ↗</a>
    </footer>
  </div>
</div>
</body>
</html>
"""


PAGE_TITLES = {
    "index.html": "Overview",
    "executive.html": "Executive summary",
    "findings.html": "Findings & analysis",
    "snapshots.html": "Price snapshots",
    "results.html": "Verified results",
    "fair-vs-market.html": "Fair line vs market",
    "signals.html": "Signal tests",
    "leaderboard.html": "Leaderboard",
    "demotion.html": "Promotion & demotion",
    "correlations.html": "Correlations",
    "parlays.html": "Parlays & combos",
    "depth.html": "Depth of replacement",
    "sources.html": "Source register",
    "verification.html": "Verification log",
    "suggestions.html": "Suggestions",
    "questions.html": "Questions to answer",
    "flagged.html": "Flagged for review",
}


def page_title(slug: str) -> str:
    return PAGE_TITLES.get(slug, slug[:-5].replace("-", " ").title())


def table(headers: list[str], rows: list[list[str]], caption: str,
          numeric_cols: set[int] | None = None, table_id: str | None = None,
          filterable: bool = False) -> str:
    numeric_cols = numeric_cols or set()
    ths_parts = []
    for i, h in enumerate(headers):
        cls = ' class="num"' if i in numeric_cols else ""
        ths_parts.append(f'<th scope="col"{cls}>{E(h)}</th>')
    ths = "".join(ths_parts)
    body = "\n".join(
        "<tr>" + "".join(c if c.startswith("<td") else f"<td>{c}</td>" for c in row) + "</tr>"
        for row in rows)
    tid = f' id="{table_id}"' if table_id else ""
    filt = ""
    if filterable and table_id:
        filt = (f'<div class="filters"><input id="{table_id}-q" data-filter="#{table_id}" '
                f'type="search" placeholder="Filter rows…" aria-label="Filter table rows">'
                f'<span class="count" data-count-for="{table_id}-q"></span></div>')
    return (f'<div class="panel">{filt}<div class="scroll"><table{tid}>\n'
            f'<caption>{caption}</caption>\n<thead><tr>{ths}</tr></thead>\n'
            f'<tbody>\n{body}\n</tbody></table></div></div>')


def kpi(k: str, v: str, s: str, kind: str = "") -> str:
    return (f'<div class="kpi {kind}"><div class="k">{E(k)}</div>'
            f'<div class="v">{v}</div><div class="s">{E(s)}</div></div>')


def kpis(items: list[tuple[str, str, str, str]]) -> str:
    return '<div class="kpis">' + "".join(kpi(*i) for i in items) + "</div>"
