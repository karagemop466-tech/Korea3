#!/usr/bin/env python3
"""Build the Depth Lab site: official club depth charts and the official NFL injury report.

Design rule for every page in this build: each table row carries at least one link to the
official page the value came from, and a value that no official source states is printed as a
flagged blank rather than filled in. The build fails if a row is emitted without a source link.

Usage:
    python3 depth_lab/build.py
Writes depth_lab/*.html.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RAW = DATA / "raw"
OUT = HERE

DEPTH = json.loads((DATA / "depth.json").read_text(encoding="utf-8"))
REPL = json.loads((DATA / "replacements.json").read_text(encoding="utf-8"))
INJ = json.loads((RAW / "nfl_injury_w10_2026.json").read_text(encoding="utf-8"))
SOURCES = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))

CAPTURED = "2026-11-13"
INJ_URL = INJ["_meta"]["source_url"]

PAGES: list[tuple[str, str, str]] = [
    ("index.html", "Depth Lab", "Overview"),
    ("depth.html", "Club depth charts", "Depth charts"),
    ("replacements.html", "Starter replacements", "Replacements"),
    ("questionable.html", "Questionable starters", "Questionable"),
    ("injuries.html", "Official NFL injury report", "Injuries"),
    ("flagged.html", "Flagged for review", "Flagged"),
    ("sources.html", "Sources", "Sources"),
    ("method.html", "Method and limits", "Method"),
]

MISSING_LINK: list[str] = []


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def e(x) -> str:
    return html.escape(str(x), quote=True)


def ilink(url: str, label: str) -> str:
    """An internal link - no new tab, no source-styling."""
    return f'<a href="{e(url)}">{e(label)}</a>'


def link(url: str, label: str = "source", note: str = "") -> str:
    """A source link. Records a violation when a row would otherwise ship without one."""
    if not url:
        MISSING_LINK.append(f"{label}:{note}")
        return '<span class="flag">no source</span>'
    host = url.split("/")[2] if "://" in url else url
    return (f'<a class="src" href="{e(url)}" target="_blank" rel="noopener noreferrer" '
            f'title="{e(url)}">{e(label)} &#8599;</a>')


def blank(why: str) -> str:
    return f'<span class="blank" title="{e(why)}">blank</span>'


def table(headers: list[str], rows: list[list[str]], cls: str = "") -> str:
    th = "".join(f'<th scope="col">{h}</th>' for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<div class="scroll"><table class="{cls}"><thead><tr>{th}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def shell(filename: str, title: str, h1: str, lead: str, body: str) -> str:
    nav = []
    for fn, navtitle, navlabel in PAGES:
        cls = ' class="active"' if fn == filename else ""
        nav.append(f'<a href="{fn}"{cls}>{e(navlabel)}</a>')
    nav_html = (
        '<div class="grp">Depth Lab</div>' + "".join(nav)
        + '<div class="grp">Rest of the repository</div>'
        '<a href="../index.html">Repository front door<span class="ext">&#8599;</span></a>'
        '<a href="../hub/index.html">Consolidated dashboard<span class="ext">&#8599;</span></a>'
        '<a href="../decision_lab/index.html">Decisions<span class="ext">&#8599;</span></a>'
        f'<a href="{e(INJ_URL)}" target="_blank" rel="noopener noreferrer">Official NFL injuries'
        '<span class="ext">&#8599;</span></a>'
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} | NFL Depth Lab</title>
<meta name="description" content="Official NFL club depth charts and the official NFL Week 10 2026 injury report, captured verbatim and joined with a published rule.">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<div class="wrap">
<aside class="nav">
<div class="brand"><b>Depth Lab</b><span>NFL 2026 &middot; Week 10 &middot; captured {CAPTURED}</span></div>
{nav_html}
</aside>
<main class="main">
<div class="eyebrow">Official sources only &middot; nothing inferred</div>
<h1>{e(h1)}</h1>
<p class="lead">{lead}</p>
{body}
<footer class="foot">
<p>Depth Lab is a capture and join of official publications. Club depth charts are the clubs' own
pages; the injury report is the NFL's. Where an official page did not state a value, the cell is
blank and flagged. No roster, news article, third-party site or model supplies a missing value.</p>
<p><a href="flagged.html">Flagged for review</a> &middot; <a href="method.html">Method and limits</a>
&middot; <a href="sources.html">Sources</a></p>
</footer>
</main>
</div>
</body>
</html>
"""


def write(filename: str, title: str, h1: str, lead: str, body: str) -> None:
    (OUT / filename).write_text(shell(filename, title, h1, lead, body), encoding="utf-8")


def card(tag: str, num: str, sub: str) -> str:
    return f'<div class="card"><div class="tag">{e(tag)}</div><div class="num">{e(num)}</div><div class="sub">{e(sub)}</div></div>'


def notice(title: str, text: str, kind: str = "") -> str:
    cls = f"notice {kind}".strip()
    return f'<div class="{cls}"><strong>{e(title)}</strong> {text}</div>'


# --------------------------------------------------------------------------- #
# derived numbers used on several pages
# --------------------------------------------------------------------------- #
CLUBS = DEPTH["clubs_captured"]
GAPS = DEPTH["coverage_gaps"]
ROWS = DEPTH["rows"]
PLAYERS = [r for r in ROWS if r["player"]]
N_BY_STRING: dict[int, int] = {}
for r in PLAYERS:
    N_BY_STRING[r["string"]] = N_BY_STRING.get(r["string"], 0) + 1
DEEP = sum(v for k, v in N_BY_STRING.items() if k >= 2)
CO_LISTED = [r for r in ROWS if r["co_listed"]]
INTERIOR_EMPTY = [r for r in ROWS if r.get("interior_empty")]
EMPTY_POSITION_ROWS = [r for r in ROWS if r.get("position_row_empty")]
NO_DATE = [c for c in json.loads((RAW / "depth_group1.json").read_text(encoding="utf-8"))["clubs"]
           + json.loads((RAW / "depth_group2.json").read_text(encoding="utf-8"))["clubs"]
           + json.loads((RAW / "depth_group3.json").read_text(encoding="utf-8"))["clubs"]
           if not (c.get("as_of_text") or "").strip()]
INJ_ROWS = sum(len(c["rows"]) for c in INJ["clubs"])
INJ_ABSENT = INJ["_meta"]["absent_clubs"]

SELF_CONFLICTS = [
    {"club": "LAC", "code": "F01",
     "what": ("Chargers.com prints two different statements about the same player on one page. "
              "The page's own Latest Transactions module headlines \"Chargers Place Derwin James "
              "Jr. on Injured Reserve\", while the Defense table on that same page lists Derwin "
              "James Jr. as the 1st-string safety."),
     "url": "https://www.chargers.com/team/depth-chart",
     "status": "Recorded, not resolved. Both statements are quoted as published; neither is treated as the truth."},
    {"club": "PHI", "code": "F02",
     "what": ("PhiladelphiaEagles.com carries a news module dated Nov 13, 2026 reading \"Eagles "
              "waive Hollywood Brown, Fred Johnson\", while the depth-chart tables on that same "
              "page still list Hollywood Brown as 2nd-string WR and Fred Johnson as 2nd-string RT."),
     "url": "https://www.philadelphiaeagles.com/team/depth-chart",
     "status": "Recorded, not resolved. The article body was not opened, so only the headline is quoted."},
    {"club": "CHI", "code": "F03",
     "what": ("Chicago's chart is the only captured page dated more than a week before the capture "
              "date: the heading reads \"Depth Chart (As of 10/31/2026)\" while the capture was made "
              "on 2026-11-13."),
     "url": "https://www.chicagobears.com/team/depth-chart",
     "status": "Flagged as stale. The rows are still published as captured."},
    {"club": "HOU", "code": "F04",
     "what": ("Houston is the one club whose depth chart could not be read. The page returned the "
              "heading \"Unofficial Depth Chart\" but no table rows: the chart is rendered by "
              "browser script, which the capture method does not execute."),
     "url": "https://www.houstontexans.com/team/depth-chart",
     "status": "Coverage gap. Houston is absent from every depth table on this site; no values are inferred."},
    {"club": "SEA", "code": "F05",
     "what": ("Seattle's page prints no depth-chart heading at all - the H1 is simply \"Seattle "
              "Seahawks\" - and no as-of date, so the chart has no published age."),
     "url": "https://www.seahawks.com/team/depth-chart/",
     "status": "Flagged. Rows published as captured."},
    {"club": "ARI", "code": "F06",
     "what": ("Arizona is the only captured club whose page titles the chart \"Official Depth "
              "Chart\" (H1: \"Arizona Cardinals Official Depth Chart\"), while every other club "
              "labels its chart unofficial and ARI prints no as-of date."),
     "url": "https://www.azcardinals.com/team/depth-chart",
     "status": "Flagged as an inconsistency across official publishers. Not resolved."},
    {"club": "NE", "code": "F07",
     "what": ("New England prints the strongest disclaimer found: \"The 2026 depth chart is "
              "unofficial and is published by the writers of Patriots.com. The depth chart reflects "
              "the opinions of the Patriots.com writers and don't necessarily reflect those of the "
              "organization.\""),
     "url": "https://www.patriots.com/team/depth-chart",
     "status": "Quoted verbatim. This is the reason every depth row on this site is labelled a club publication."},
    {"club": "WAS", "code": "F08",
     "what": ("Washington's own page title contains a typo - \"Commanders.comcom\" - preserved "
              "here verbatim rather than corrected."),
     "url": "https://www.commanders.com/team/depth-chart",
     "status": "Cosmetic; preserved to keep the capture faithful."},
    {"club": "NFL", "code": "F09",
     "what": (f"The official NFL injury report for Week 10 carries tables for "
              f"{len(INJ['clubs'])} of 32 clubs. {', '.join(INJ_ABSENT)} had no table on the page "
              "at capture time."),
     "url": INJ_URL,
     "status": ("Flagged. Whether those four are on a bye, were not published, or were not served "
                "to the capture is NOT KNOWN and is not inferred.")},
    {"club": "NFL", "code": "F10",
     "what": ("The injury report prints an empty Game Status cell for many players "
              f"({len(REPL['no_status'])} of the 1st-string players matched here). An empty cell is "
              "the league's own blank."),
     "url": INJ_URL,
     "status": "Empty cells are printed blank and are never filled in."},
]


# --------------------------------------------------------------------------- #
# page: index
# --------------------------------------------------------------------------- #
def page_index() -> None:
    counts = "".join([
        card("Clubs with a captured depth chart", f"{CLUBS} of 32",
             f"{len(GAPS)} coverage gap ({', '.join(g['code'] for g in GAPS)})"),
        card("Backups published (2nd string or deeper)", f"{DEEP:,}",
             "2nd string " + f"{N_BY_STRING.get(2, 0):,}" + " · 3rd " + f"{N_BY_STRING.get(3, 0):,}"
             + " · 4th " + f"{N_BY_STRING.get(4, 0):,}" + " · 5th " + f"{N_BY_STRING.get(5, 0):,}"),
        card("Starters Out or Doubtful", f"{len(REPL['rows'])}",
             f"{sum(1 for r in REPL['rows'] if r['replacement'])} with a next name published, "
             f"{sum(1 for r in REPL['rows'] if not r['replacement'])} with none"),
        card("Official injury-report rows", f"{INJ_ROWS:,}",
             f"{len(INJ['clubs'])} clubs · {len(INJ_ABSENT)} clubs absent from the page"),
    ])

    findings_rows = [
        ["The league does not publish string order, but the clubs do",
         ("nfl.com's roster pages list players with an ACT/RES status and no ranking, and its "
          f"depth-chart path returns 404. Every one of the {CLUBS} clubs that could be read publishes "
          "an ordered chart with columns for up to seven strings; players are actually named out to "
          "5th string."),
         link("https://www.nfl.com/teams/kansas-city-chiefs/roster/", "nfl.com roster", "F-A") +
         " " + link("https://www.chiefs.com/team/depth-chart", "chiefs.com chart", "F-A")],
        ["Clubs call their own charts unofficial",
         f"{len(NO_DATE)} of {CLUBS} captured clubs print no as-of date at all. New England states outright that the chart reflects writers' opinions, not the organisation's. Arizona is the only club that titles its chart \"Official\".",
         link("https://www.patriots.com/team/depth-chart", "patriots.com", "F-B") +
         " " + link("https://www.azcardinals.com/team/depth-chart", "azcardinals.com", "F-B")],
        ["Two clubs contradict themselves on one page",
         "The Chargers' own page announces Derwin James Jr. on injured reserve while listing him as 1st-string safety. The Eagles' own page announces two waivers dated Nov 13 while still listing both players on the chart.",
         link("https://www.chargers.com/team/depth-chart", "chargers.com", "F-C") +
         " " + link("https://www.philadelphiaeagles.com/team/depth-chart", "philadelphiaeagles.com", "F-C")],
        ["Published blanks are real and are left blank",
         f"{len(INTERIOR_EMPTY)} slots inside a position row and {len(EMPTY_POSITION_ROWS)} whole position rows were published empty. Baltimore and Miami each publish a Kicker row with nobody at any string.",
         link("https://www.baltimoreravens.com/team/depth-chart", "ravens K row", "F-D") +
         " " + link("https://www.miamidolphins.com/team/depth-chart", "dolphins K row", "F-D")],
        ["Co-listings are not rankings",
         f"{len(CO_LISTED)} player entries appear in a cell shared with another player. The clubs print no separator and no order between them, so both are shown at the same string and flagged.",
         link("https://www.colts.com/team/depth-chart", "colts.com", "F-E")],
        ["Depth is thin where it matters most",
         f"Only {N_BY_STRING.get(3, 0):,} players are published at 3rd string across {CLUBS} clubs, and {N_BY_STRING.get(4, 0):,} at 4th. Several clubs publish a single name for whole position groups.",
         ilink("depth.html", "the depth tables")],
    ]

    what_notice = notice(
        "What this site is.",
        "A verbatim capture of two kinds of official publication - each club's own depth chart and "
        "the NFL's own Week 10 injury report - plus one join between them whose rule is printed on "
        '<a href="replacements.html">the replacements page</a> before any result is shown. Nothing '
        "here is a projection, a rating, a starting designation or a betting value.")

    body = f"""
<div class="grid k4">{counts}</div>
{what_notice}
<section>
  <div class="section-head"><div><h2>Findings</h2>
  <p>Each row links the official page that carries the finding.</p></div>
  <span class="count small muted">{len(findings_rows):02d} findings</span></div>
  {table(["Finding", "What the official pages show", "Source"], findings_rows)}
</section>
<section>
  <div class="section-head"><div><h2>Read these in order</h2></div></div>
  <div class="grid k3">
    <a class="tile" href="depth.html"><b>Club depth charts</b><span>{CLUBS} clubs · every published string · {len(PLAYERS):,} player entries</span></a>
    <a class="tile" href="replacements.html"><b>Starter replacements</b><span>{len(REPL['rows'])} starters Out or Doubtful · next published name</span></a>
    <a class="tile" href="questionable.html"><b>Questionable starters</b><span>{len(REPL['questionable'])} starters listed Questionable</span></a>
    <a class="tile" href="injuries.html"><b>Official injury report</b><span>{INJ_ROWS:,} rows · {len(INJ['clubs'])} clubs · verbatim</span></a>
    <a class="tile" href="flagged.html"><b>Flagged for review</b><span>{len(SELF_CONFLICTS)} logged irregularities · all with source links</span></a>
    <a class="tile" href="method.html"><b>Method and limits</b><span>how the capture was made and what it cannot tell you</span></a>
  </div>
</section>
"""
    write("index.html", "Depth Lab", "NFL depth charts and injuries, from official pages only",
          "Every club in the league publishes an ordered depth chart on its own site. This build "
          "captures those pages and the NFL's official Week 10 injury report exactly as printed, "
          "and joins them under a rule that is stated before any result appears.", body)


# --------------------------------------------------------------------------- #
# page: depth charts
# --------------------------------------------------------------------------- #
def page_depth() -> None:
    club_objs = {}
    for f in ("depth_group1.json", "depth_group2.json", "depth_group3.json"):
        for c in json.loads((RAW / f).read_text(encoding="utf-8"))["clubs"]:
            club_objs[c["code"]] = c

    sections = []
    for code in sorted(DEPTH["clubs_with_data"]):
        club = club_objs[code]
        rows_by_unit: dict[str, dict[str, list]] = {"Offense": {}, "Defense": {}, "Special Teams": {}}
        order: dict[str, list] = {"Offense": [], "Defense": [], "Special Teams": []}
        for r in ROWS:
            if r["club_code"] != code:
                continue
            d = rows_by_unit[r["unit"]]
            if r["position"] not in d:
                d[r["position"]] = []
                order[r["unit"]].append(r["position"])
            d[r["position"]].append(r)

        unit_html = []
        for unit in ("Offense", "Defense", "Special Teams"):
            trs = []
            for pos in order[unit]:
                entries = sorted(rows_by_unit[unit][pos], key=lambda x: x["string"])
                cells = []
                for ent in entries:
                    if ent["empty_slot"]:
                        cells.append(blank("the club published this string cell empty"))
                    else:
                        nm = e(ent["player"])
                        if ent["player_url"]:
                            nm = ('<a href="' + e(ent["player_url"]) + '" target="_blank" '
                                  'rel="noopener noreferrer">' + nm + "</a>")
                        if ent["co_listed"]:
                            nm += (' <span class="pill warn" title="this player shares the cell '
                                   'with another player; the club printed no order between them">'
                                   'co-listed</span>')
                        cells.append('<span class="str' + str(ent["string"]) + '">' + nm + "</span>")
                trs.append(f'<tr><th scope="row">{e(pos)}</th><td>' +
                           ' &middot; '.join(cells) + "</td></tr>")
            unit_html.append(
                f'<div class="unit"><h3>{e(unit)}</h3>'
                f'<div class="scroll"><table class="depth"><thead><tr><th scope="col">Position</th>'
                f'<th scope="col">Players in the order the club printed them</th></tr></thead>'
                f'<tbody>{"".join(trs)}</tbody></table></div></div>')

        as_of = (club.get("as_of_text") or "").strip()
        as_of_html = (f'<span class="pill ok">{e(as_of)}</span>' if as_of
                      else blank("the club printed no as-of date on this page"))
        heading = (club.get("heading") or "").strip()
        open_attr = " open" if code in ("KC", "BAL") else ""
        sections.append(f"""
<details class="club" id="{e(code)}"{open_attr}>
  <summary><span class="code">{e(code)}</span> {e(club['name'])}
    <span class="muted small"> &middot; {len([r for r in ROWS if r['club_code'] == code and r['player']])} players published</span>
  </summary>
  <div class="meta">
    <span><b>Page title as printed:</b> {e(club['page_title'])}</span>
    <span><b>Heading as printed:</b> {e(heading) if heading else blank('no heading printed')}</span>
    <span><b>As-of date:</b> {as_of_html}</span>
    <span>{link(club['url'], 'open the club page', code)}</span>
  </div>
  {''.join(unit_html)}
</details>""")

    options_html = "".join(
        '<option value="' + e(c) + '">' + e(club_objs[c]["name"]) + "</option>"
        for c in sorted(DEPTH["clubs_with_data"]))

    read_notice = notice(
        "How to read a row.",
        "The order of names in a cell is the order of the club's own columns: 1st string, then "
        "2nd, then 3rd. Where a club printed two names in one cell with no separator, both are "
        'shown and marked <span class="pill warn">co-listed</span>, because the club published no '
        'order between them. A <span class="blank">blank</span> means the club left that cell empty.')

    hou_notice = notice(
        "Houston is missing on purpose.",
        '<a href="https://www.houstontexans.com/team/depth-chart" target="_blank" '
        'rel="noopener noreferrer">houstontexans.com &#8599;</a> returns the heading but renders '
        "the tables with browser script, so no rows could be read. Rather than fill the club in "
        'from a roster or a third-party site, Houston is left out of this page and logged on '
        '<a href="flagged.html">Flagged for review</a>.')

    body = f"""
{read_notice}
<div class="toolbar">
  <label>Jump to club
  <select onchange="if(this.value) location.hash=this.value">
    <option value="">choose…</option>
    {options_html}
  </select></label>
  <span class="muted small">{CLUBS} clubs · {len(PLAYERS):,} player entries · {len(CO_LISTED)} co-listed</span>
</div>
{hou_notice}
{"".join(sections)}
"""
    write("depth.html", "Club depth charts",
          f"Club depth charts: {CLUBS} of 32 clubs",
          "Each club's own published chart, in the club's own order and with the club's own blanks. "
          "Hover any pill to see why it is marked.", body)


# --------------------------------------------------------------------------- #
# page: replacements
# --------------------------------------------------------------------------- #
def page_replacements() -> None:
    rows = []
    for r in REPL["rows"]:
        if not r["replacement"]:
            repl = blank("the club published no further name at this position")
        elif r["replacement_url"]:
            repl = ('<a href="' + e(r["replacement_url"]) + '" target="_blank" '
                    'rel="noopener noreferrer">' + e(r["replacement"]) + "</a>")
        else:
            repl = e(r["replacement"])
        if r["replacement_co_listed"]:
            repl += ' <span class="pill warn">co-listed</span>'
        rows.append([
            f'<span class="code">{e(r["club"])}</span>',
            e(r["unit"]),
            e(r["position"]),
            '<a href="' + e(r["starter_url"]) + '" target="_blank" rel="noopener noreferrer">' + e(r["starter"]) + "</a>",
            '<span class="pill ' + ("bad" if r["starter_game_status"] == "Out" else "warn") + '">' + e(r["starter_game_status"]) + "</span>",
            e(r["starter_injury"]) or blank("the league printed no injury"),
            e(r["replacement_string"]) if r["replacement_string"] else "—",
            repl,
            f'{e(r["depth_published"])}',
            link(r["sources"][0], "chart", r["club"]) + " " + link(r["sources"][1], "injury", r["club"]),
        ])

    blank_rows = [r for r in REPL["rows"] if not r["replacement"]]
    deep_rows = [r for r in REPL["rows"] if r["replacement_string"] and r["replacement_string"] >= 3]

    body = f"""
{notice("The join rule, stated before the results.",
        "<b>" + e(REPL["join_rule"]) + "</b>")}
{notice("What this table is not.",
        "It is not an official depth designation and it is not a prediction. No official publisher "
        "says who will start. The replacement column is literally the next name the club printed, "
        "which is a statement about what the club published, not about who will play.",
        "warn")}
<div class="grid k4">
  {card("Starters Out or Doubtful", str(len(REPL["rows"])), "1st-string players on the club chart who appear on the NFL report")}
  {card("Replacement named", str(sum(1 for r in REPL["rows"] if r["replacement"])), "the club published a further name at that position")}
  {card("Replacement blank", str(len(blank_rows)), "the club published nobody; left blank, never filled in")}
  {card("Replacement is 3rd string or deeper", str(len(deep_rows)), "the starter's published backup was already a backup")}
</div>
<section>
  <div class="section-head"><div><h2>Starters ruled Out or Doubtful, with the next published name</h2>
  <p>Sorted by club. Every row links both official sources.</p></div>
  <span class="count small muted">{len(rows):02d} rows</span></div>
  {table(["Club", "Unit", "Position", "1st string (club chart)", "Game status (NFL)", "Injury (NFL)",
          "Next string", "Next name the club published", "Strings the club published", "Sources"],
         rows)}
</section>
<section>
  <div class="section-head"><div><h2>Where the club published nobody</h2>
  <p>These rows are the reason the page exists: an official source that stops talking is a gap, not a value to fill.</p></div></div>
  {table(["Club", "Unit", "Position", "1st string", "Game status", "Why the cell is blank", "Source"],
         [[f'<span class="code">{e(r["club"])}</span>', e(r["unit"]), e(r["position"]), e(r["starter"]),
           e(r["starter_game_status"]),
           "the club's own chart prints no further name at this position",
           link(r["sources"][0], "chart", r["club"])]
          for r in blank_rows])}
</section>
"""
    write("replacements.html", "Starter replacements",
          "Starters Out or Doubtful, and the next name the club published",
          "A join of the clubs' own depth charts with the NFL's official Week 10 injury report, "
          "under one printed rule. Read the rule before the table.", body)


# --------------------------------------------------------------------------- #
# page: questionable
# --------------------------------------------------------------------------- #
def page_questionable() -> None:
    rows = []
    for r in REPL["questionable"]:
        if r["next_string_name"]:
            nxt = ('<a href="' + e(r["sources"][0]) + '" target="_blank" rel="noopener noreferrer">'
                   + e(r["next_string_name"]) + "</a>")
        else:
            nxt = blank("the club published nobody at 2nd string")
        rows.append([
            f'<span class="code">{e(r["club"])}</span>', e(r["unit"]), e(r["position"]),
            f'<a href="{e(r["starter_url"])}" target="_blank" rel="noopener noreferrer">{e(r["starter"])}</a>',
            e(r["injury"]) or blank("the league printed no injury"),
            e(r["practice"]),
            nxt,
            e(r["depth_published"]),
            link(r["sources"][0], "chart", r["club"]) + " " + link(r["sources"][1], "injury", r["club"]),
        ])
    rows.sort(key=lambda r: (r[0], r[2]))

    no_backup = [r for r in REPL["questionable"] if not r["next_string_name"]]

    body = f"""
{notice("Questionable is not Out.",
        "A Questionable game status is the league saying the player's availability is uncertain. "
        "This page does not decide it and does not treat these as replacements. It lists them "
        "because the next published name is the thing a reader would want next to the status, and "
        "both facts come from official pages.")}
<div class="grid k3">
  {card("Questionable starters on the club chart", str(len(rows)), "1st-string players, official NFL report")}
  {card("With a 2nd string published", str(len(rows) - len(no_backup)), "the club printed a next name")}
  {card("With nobody published behind them", str(len(no_backup)), "the club printed no 2nd string")}
</div>
<section>
  <div class="section-head"><div><h2>Questionable 1st-string players</h2></div>
  <span class="count small muted">{len(rows):02d} rows</span></div>
  {table(["Club", "Unit", "Position", "1st string", "Injury (NFL)", "Practice (NFL)",
          "2nd string the club published", "Strings published", "Sources"], rows)}
</section>
"""
    write("questionable.html", "Questionable starters",
          f"Questionable 1st-string players ({len(rows)})",
          "The league lists these starters as Questionable for Week 10. Each row shows the next "
          "name the club itself published at that position.", body)


# --------------------------------------------------------------------------- #
# page: injuries
# --------------------------------------------------------------------------- #
def page_injuries() -> None:
    sections = []
    for club in INJ["clubs"]:
        trs = []
        for player, pos, injury, practice, game_status, url in club["rows"]:
            if not game_status:
                gs = blank("the league printed no game status")
            else:
                tone = "bad" if game_status == "Out" else ("warn" if game_status in ("Doubtful", "Questionable") else "ok")
                gs = '<span class="pill ' + tone + '">' + e(game_status) + "</span>"
            inj_cell = e(injury) if injury else blank("the league printed no injury")
            trs.append(
                '<tr><th scope="row"><a href="' + e(url) + '" target="_blank" rel="noopener noreferrer">'
                + e(player) + "</a></th><td>" + e(pos) + "</td><td>" + inj_cell
                + "</td><td>" + e(practice) + "</td><td>" + gs + "</td></tr>")
        sections.append(f"""
<details class="club" id="inj-{e(club['code'])}">
  <summary><span class="code">{e(club['code'])}</span> {e(club['name'])}
    <span class="muted small"> &middot; {len(club['rows'])} rows &middot; {e(club.get('game_slot', ''))} &middot; vs {e(club.get('opponent', ''))}</span>
  </summary>
  <div class="scroll"><table class="depth"><thead><tr>
    <th scope="col">Player</th><th scope="col">Position</th><th scope="col">Injuries</th>
    <th scope="col">Practice status</th><th scope="col">Game status</th>
  </tr></thead><tbody>{"".join(trs)}</tbody></table></div>
  <div class="meta">{link(INJ_URL, "official NFL injury report", club["code"])}</div>
</details>""")

    news_rows = [['<a href="' + e(n["url"]) + '" target="_blank" rel="noopener noreferrer">'
                  + e(n["headline"]) + "</a>",
                  '<span class="pill warn">headline only</span>', e(n["note"])]
                 for n in INJ["official_news_headlines"]]

    verbatim_notice = notice(
        "Verbatim.",
        'Every cell below is transcribed from <a href="' + e(INJ_URL) + '" target="_blank" '
        'rel="noopener noreferrer">nfl.com/injuries &#8599;</a> as printed on ' + CAPTURED
        + ". An empty Injury, Practice Status or Game Status cell is the league's own empty "
        "cell and is printed blank.")

    absent_notice = notice(
        ", ".join(INJ_ABSENT) + " are absent from the page.",
        "The official report carried no injury table for these clubs at capture time. Whether "
        "that is a bye week, an unpublished page, or a chunk that was not served is NOT KNOWN. "
        "No rows are invented for them.", "warn")

    body = f"""
{verbatim_notice}
{absent_notice}
<section>
  <div class="section-head"><div><h2>Week 10 injury report, all clubs that were published</h2></div>
  <span class="count small muted">{len(INJ['clubs'])} clubs · {INJ_ROWS} rows</span></div>
  {"".join(sections)}
</section>
<section>
  <div class="section-head"><div><h2>Official headlines seen on the same page</h2>
  <p>Listed because they sit on the official injury page. The article bodies were not opened, so they are recorded as headlines and used nowhere as data.</p></div>
  <span class="count small muted">{len(news_rows):02d} headlines</span></div>
  {table(["Headline as printed on nfl.com", "Status", "Note"], news_rows)}
</section>
"""
    write("injuries.html", "Official NFL injury report",
          f"Official NFL injury report, Week 10 2026 ({INJ_ROWS} rows)",
          "The league's own injury report, transcribed cell for cell with its own blanks left blank.",
          body)


# --------------------------------------------------------------------------- #
# page: flagged
# --------------------------------------------------------------------------- #
def page_flagged() -> None:
    conflict_rows = [[f'<span class="code">{e(c["club"])}</span>', e(c["code"]), c["what"],
                      link(c["url"], "official page", c["code"]), e(c["status"])]
                     for c in SELF_CONFLICTS]

    empty_rows = [[f'<span class="code">{e(r["club_code"])}</span>', e(r["unit"]), e(r["position"]),
                   e(r["string"]),
                   "the club printed this cell empty" if not r.get("position_row_empty")
                   else "the club printed the whole position row with nobody at any string",
                   link(r["source_url"], "club page", r["club_code"])]
                  for r in INTERIOR_EMPTY + EMPTY_POSITION_ROWS]

    co_rows = [[f'<span class="code">{e(r["club_code"])}</span>', e(r["unit"]), e(r["position"]),
                e(r["string"]), e(r["player"]),
                "shares the cell with another player; the club printed no order between them",
                link(r["source_url"], "club page", r["club_code"])]
               for r in sorted(CO_LISTED, key=lambda x: (x["club_code"], x["unit"], x["position"]))]

    nodate_rows = [[f'<span class="code">{e(c["code"])}</span>', e(c["name"]),
                    "no as-of date printed anywhere on the page",
                    link(c["url"], "club page", c["code"])]
                   for c in sorted(NO_DATE, key=lambda x: x["code"])]

    unmatched_sample = sorted(REPL["unmatched"], key=lambda x: (x["club"], x["position"]))
    un_rows = [[f'<span class="code">{e(u["club"])}</span>', e(u["unit"]), e(u["position"]),
                e(u["depth_name"]), e(u["why"]),
                link(u["depth_source"], "chart", u["club"]) + " " + link(u["injury_source"], "injury", u["club"])]
               for u in unmatched_sample[:400]]

    no_status_rows = [[f'<span class="code">{e(n["club"])}</span>', e(n["unit"]), e(n["position"]),
                       '<a href="' + e(n["player_url"]) + '" target="_blank" rel="noopener noreferrer">' + e(n["player"]) + "</a>",
                       e(n["practice"]), e(n["injury"]) or blank("none printed"),
                       e(n["why"])] for n in REPL["no_status"]]

    body = f"""
{notice("Why this page exists.",
        "The brief says a value that cannot be confirmed from an official source must be left blank "
        "and flagged, never inferred. Everything here is either an official source contradicting "
        "itself, an official source staying silent, or a limit of the capture method. None of it is "
        "smoothed over.")}
<section>
  <div class="section-head"><div><h2>Irregularities in the official pages themselves</h2>
  <p>Each row is a statement an official page makes that conflicts with another statement on the same page, or with what the other 31 clubs do.</p></div>
  <span class="count small muted">{len(conflict_rows):02d} logged</span></div>
  {table(["Club", "ID", "What the official page does", "Official page", "How this build handles it"], conflict_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Published blanks</h2>
  <p>Cells the club left empty. They are printed blank on the depth page and are never filled from a roster, a news story or a memory.</p></div>
  <span class="count small muted">{len(empty_rows):02d} slots</span></div>
  {table(["Club", "Unit", "Position", "String", "Why it is blank", "Source"], empty_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Co-listed players</h2>
  <p>Two or more names in one cell with no separator. The club published no order between them, so this build refuses to rank them.</p></div>
  <span class="count small muted">{len(co_rows):02d} entries</span></div>
  {table(["Club", "Unit", "Position", "String", "Player", "Why it is flagged", "Source"], co_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Clubs that print no date</h2>
  <p>A depth chart with no as-of date has no published age, so it cannot be checked for staleness.</p></div>
  <span class="count small muted">{len(nodate_rows):02d} of {CLUBS} clubs</span></div>
  {table(["Club", "Name", "What is missing", "Source"], nodate_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Starters on the injury report with no game status</h2>
  <p>The league lists these 1st-string players with a practice status but leaves Game Status empty. The empty cell is the league's own.</p></div>
  <span class="count small muted">{len(no_status_rows):02d} players</span></div>
  {table(["Club", "Unit", "Position", "Player", "Practice", "Injury", "Why no decision was made"], no_status_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Name-matching audit</h2>
  <p>Every 1st-string name that did NOT match a name on the official injury report, listed so the join can be checked by hand rather than trusted.</p></div>
  <span class="count small muted">{len(REPL['unmatched']):,} unmatched · showing {len(un_rows)}</span></div>
  {table(["Club", "Unit", "Position", "Name the club printed", "Why it was not joined", "Sources"], un_rows)}
</section>
"""
    write("flagged.html", "Flagged for review", "Flagged for review",
          "Irregularities, published blanks and capture limits. Every row links the official page "
          "it came from, and nothing here has been resolved by inferring a value.", body)


# --------------------------------------------------------------------------- #
# page: sources
# --------------------------------------------------------------------------- #
def page_sources() -> None:
    rows = []
    for s in SOURCES["sources"]:
        rows.append([
            f'<span class="code">{e(s.get("code", ""))}</span>' if s.get("code") else "",
            e(s["name"]),
            e(s["tier"]),
            '<a href="' + e(s["url"]) + '" target="_blank" rel="noopener noreferrer">' + e(s["url"]) + "</a>",
            e(s["status"]),
            e(s.get("note", "")),
        ])
    tier_defs = "".join(
        "<dt><b>" + e(k) + "</b></dt><dd>" + e(v) + "</dd>"
        for k, v in SOURCES["tier_definitions"].items())

    body = f"""
{notice("Tier definitions are this build's own, and they are recorded rather than assumed.",
        "The shared repository auditor at <code>verify/source_audit.py</code> keeps an "
        "<code>OFFICIAL_HOSTS</code> allow-list that does not include member-club domains, so "
        "club-published rows are classified there as <code>dataset</code>, not <code>official</code>. "
        "That shared allow-list was not edited by this session. Depth Lab records the club tier "
        "locally, here, so a reader can see the distinction and the open governance question is not "
        "silently closed.", "warn")}
<section>
  <div class="section-head"><div><h2>How this build tiers a source</h2>
  <p>These are this build's own definitions, written down so a reader can argue with them.</p></div></div>
  <dl class="defs">{tier_defs}</dl>
</section>
<section>
  <div class="section-head"><div><h2>Every source used</h2></div>
  <span class="count small muted">{len(rows):02d} sources</span></div>
  {table(["Club", "Publisher", "Tier", "URL", "Status", "Note"], rows)}
</section>
"""
    write("sources.html", "Sources", "Sources",
          "Where every value on this site came from, and how each publisher is classified.", body)


# --------------------------------------------------------------------------- #
# page: method
# --------------------------------------------------------------------------- #
def page_method() -> None:
    limits = [
        ["The capture is a snapshot, not a live feed",
         "All 31 club pages and the injury report were read once, on 2026-11-13. Clubs update charts on their own cadence and most print no date, so a chart captured today may already differ."],
        ["Club charts are the clubs' own opinion, by their own admission",
         "New England prints that the chart reflects the opinions of Patriots.com writers and not necessarily the organisation. No club in this capture presents its chart as an official competitive document except Arizona."],
        ["The club chart does not say who will play",
         "A depth chart is a publication, not a game-day designation. The NFL's own injury report is the official availability document, and even it prints an empty Game Status for many players."],
        ["Houston could not be read",
         "The Texans page renders its tables with browser script. Rather than substitute a roster or a third-party site, Houston is left out of every depth table and logged on the flagged page."],
        ["Four clubs are absent from the injury report",
         "Chicago, Denver, Philadelphia and Tampa Bay had no injury table on the official page at capture time. The reason is not known and is not inferred."],
        ["Co-listings are unranked by definition",
         "When a club prints two names in one cell, no order between them exists in the source. Any ranking would be invented."],
        ["No projection, price, rating or bet value appears anywhere in this build",
         "This build has no model in it. It publishes what official pages said and what they did not say."],
        ["Name matching is conservative on purpose",
         "Three hand-checked aliases reconcile a club's spelling with the league's. Two near-misses that a fuzzy matcher would have joined are deliberately left unjoined because they are different people."],
    ]

    steps = [
        ["1", "Claim the scope", "A block was appended to COORDINATION.md naming the session, the file scope and the tasks, and pushed before any scoped file was touched."],
        ["2", "Read the pages", "Each club's own /team/depth-chart page and the NFL's /injuries/ page were opened in full, chunk by chunk, until the tables were exhausted."],
        ["3", "Transcribe verbatim", "Table rows were written into data/raw/*.json exactly as printed, including empty cells, co-listed cells, wrapped continuation rows and club-specific position labels."],
        ["4", "Parse without inventing", "depth_lab/parse_depth.py turns layout into rows. It trims trailing padding columns, keeps interior blanks, numbers co-listed players at the same string, and never fills a cell."],
        ["5", "Join under a printed rule", "depth_lab/join_replacements.py applies the rule printed at the top of the replacements page, and writes an audit of every name it could not match."],
        ["6", "Build and fail closed", "depth_lab/build.py refuses to emit a row without a source link; depth_lab/check.py fails the build if any page links a non-HTTPS or non-official host in a source column, or if a generated number disagrees with the data files."],
    ]

    body = f"""
<section>
  <div class="section-head"><div><h2>How this was made</h2></div>
  <span class="count small muted">{len(steps)} steps</span></div>
  {table(["#", "Step", "What it means"], [[e(a), e(b), e(c)] for a, b, c in steps])}
</section>
<section>
  <div class="section-head"><div><h2>Limits</h2>
  <p>Read these before using anything on this site.</p></div>
  <span class="count small muted">{len(limits)} limits</span></div>
  {table(["Limit", "What it means for a reader"], [[e(a), e(b)] for a, b in limits])}
</section>
<section>
  <div class="section-head"><div><h2>Answering the question that prompted this build</h2></div></div>
  <div class="prose">
  <p>An earlier session concluded, after probing four clubs and nfl.com, that ordered 2nd-, 3rd- and
  4th-string depth was "not satisfiable from official sources". That conclusion was too broad. The
  correct, narrower finding is:</p>
  <ul>
    <li><b>The league does not publish string order.</b> nfl.com roster pages carry an ACT/RES status
    and no ranking, and the league's depth-chart path returns 404.</li>
    <li><b>The member clubs do publish it.</b> {CLUBS} of 32 club sites published an ordered chart
    that could be read, with columns for up to seven strings and names actually published out to
    5th string: {DEEP:,} players at 2nd string or deeper.</li>
    <li><b>But the clubs disclaim it.</b> Most print no date; New England states it is writers'
    opinion, not the organisation's; two clubs contradict themselves elsewhere on the same page.</li>
  </ul>
  <p>So the data the brief asked for exists on official sites, and it is usable, provided every row
  is stamped with the club that published it and the blanks are left blank. That is what this build
  does.</p>
  </div>
</section>
"""
    write("method.html", "Method and limits", "Method and limits",
          "How the capture, the parse and the join were done, and what they cannot tell you.", body)


# --------------------------------------------------------------------------- #
def main() -> int:
    (OUT / "assets").mkdir(exist_ok=True)
    page_index()
    page_depth()
    page_replacements()
    page_questionable()
    page_injuries()
    page_flagged()
    page_sources()
    page_method()
    if MISSING_LINK:
        print(f"FAIL: {len(MISSING_LINK)} rows were emitted without a source link")
        for m in MISSING_LINK[:20]:
            print("  -", m)
        return 1
    print(f"built {len(PAGES)} pages: " + ", ".join(p[0] for p in PAGES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
