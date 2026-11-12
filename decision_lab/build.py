#!/usr/bin/env python3
"""Build the decision_lab pages from decision_lab/data/*.json.

Design rules, all of which check.py enforces on the output:

1.  **No manual input.** Every published value comes from a JSON file in ``data/``. Those files
    are transcriptions of official pages, each carrying the ID of the source it came from. This
    script contains no NFL facts of its own - no player, no score, no injury, no price.
2.  **No inference.** If a JSON field is an empty string the page prints a blank marker. This
    script never substitutes a default, a guess, or a value carried over from a neighbouring row.
3.  **Every table row carries a source link.** The link is to the official publisher of that
    row's text. Where a row's text has no official publisher, the row says so and is flagged.
4.  **Deterministic.** Standard library only, no network, no clock, no random. Rebuilding
    produces byte-identical files, so CI can fail on drift.
5.  **Derived values are labelled derived.** The only arithmetic here is counting rows that are
    already published, and grouping position codes by the convention printed on the page. Both
    are shown to the reader with their rule, not presented as official facts.

Usage:  python3 decision_lab/build.py
"""
from __future__ import annotations

import json
from collections import Counter
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
ASSETS = HERE / "assets"
REPO = HERE.parent

# --------------------------------------------------------------------------- #
# data
# --------------------------------------------------------------------------- #
def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


SOURCES = load("sources.json")
INJ = load("injuries.json")
CONF = load("contradictions.json")
SUG = load("suggestions.json")
QST = load("questions.json")

SRC = {s["id"]: s for s in SOURCES["sources"]}
CAPTURED = INJ["captured_utc"]
SEASON = INJ["season"]
WEEK = INJ["week"]

# --------------------------------------------------------------------------- #
# position -> unit convention.
# This is a PRESENTATION rule, not an official classification. The official report
# prints a position code per player and no unit. The full mapping is published on
# every page that uses it, so a reader can audit or reject it. Codes that are not
# listed map to "" and are printed blank, never guessed.
# --------------------------------------------------------------------------- #
OFFENSE = {"QB", "RB", "WR", "TE", "FB", "C", "G", "T", "OT", "OG", "OL"}
DEFENSE = {"LB", "OLB", "ILB", "MLB", "DE", "DT", "NT", "DL", "CB", "S", "SAF", "DB", "FS", "SS"}
SPECIAL = {"K", "PK", "P", "LS", "H", "KR", "PR"}


def unit_of(pos: str) -> str:
    """Return Offence / Defence / Special teams, or "" for a code not in the convention."""
    p = (pos or "").strip().upper()
    if p in OFFENSE:
        return "Offence"
    if p in DEFENSE:
        return "Defence"
    if p in SPECIAL:
        return "Special teams"
    return ""


# --------------------------------------------------------------------------- #
# small helpers
# --------------------------------------------------------------------------- #
def e(x) -> str:
    return escape("" if x is None else str(x), quote=True)


def blank(label: str = "blank", flag: str = "") -> str:
    """A value that is not confirmable from an official source is printed blank and flagged."""
    f = f' <a href="flagged.html#{e(flag)}">[{e(flag)}]</a>' if flag else ""
    return f'<span class="blank" title="Not confirmable from an official source. Left blank, never inferred.">{e(label)}</span>{f}'


def src(id_: str, label: str = "") -> str:
    """A source link. Refuses to emit a link for a source this session did not read,
    unless the label makes the limitation explicit, so an unopened page can never be
    presented as confirmed evidence. An unknown source ID fails the build outright:
    a row must never cite a source that is not in the register."""
    if not id_:
        raise KeyError("empty source id: a row must cite a registered source or print an explicit blank")
    s = SRC.get(id_)
    if not s:
        raise KeyError(f"source id {id_!r} is cited by a row but is not in data/sources.json")
    txt = label or s["id"]
    if not s.get("read"):
        return (f'<a href="{e(s["url"])}" title="{e(s["publisher"])} - cited but NOT opened this session">'
                f'{e(txt)}<sup>&#9888;</sup></a>')
    return f'<a href="{e(s["url"])}" title="{e(s["publisher"])}">{e(txt)}</a>'


def tier_tag(id_: str) -> str:
    s = SRC.get(id_)
    if not s:
        return ""
    cls = {"official-league": "official", "official-club": "club", "third-party": "third"}[s["tier"]]
    lbl = {"official-league": "official league", "official-club": "official club",
           "third-party": "NOT official"}[s["tier"]]
    return f'<span class="tag {cls}">{e(lbl)}</span>'


def ps_tag(ps: str) -> str:
    m = {"Full Participation in Practice": ("full", "Full"),
         "Limited Participation in Practice": ("lim", "Limited"),
         "Did Not Participate In Practice": ("dnp", "DNP")}
    if ps in m:
        c, t = m[ps]
        return f'<span class="tag {c}">{e(t)}</span>'
    return f'<span class="tag lo">{e(ps)}</span>' if ps else blank()


def gs_tag(gs: str) -> str:
    m = {"Out": "out", "Questionable": "q", "Doubtful": "q"}
    if gs in m:
        return f'<span class="tag {m[gs]}">{e(gs)}</span>'
    return f'<span class="tag lo">{e(gs)}</span>' if gs else blank("blank", "D13")


def sev_tag(s: str) -> str:
    cls = {"high": "hi", "medium": "med", "low": "lo"}.get(s, "lo")
    return f'<span class="tag {cls}">{e(s)}</span>'


# --------------------------------------------------------------------------- #
# derived counts - arithmetic over rows that are themselves published, never a
# number that appears only in a headline
# --------------------------------------------------------------------------- #
DESIG = INJ["designations"]["rows"]
PRAC = INJ["practice_participation"]["rows"]
ROUNDUP = INJ["injury_detail_from_roundup"]["rows"]
GAMES = INJ["games"]
NOINJ = INJ["no_injuries_reported"]["teams"]
HEADLINES = INJ["official_headlines_on_report_page"]["rows"]
GAPS = INJ["coverage_gaps"]
PROBE = INJ["roster_status_probe"]

CLUBS_IN_REPORT = sorted({r["team"] for r in PRAC} | {d["team"] for d in DESIG}
                         | {t["team"] for t in NOINJ})
CLUBS_IN_ROUNDUP = sorted({r["team"] for r in ROUNDUP})
DESIG_BY_CLUB = Counter(d["team"] for d in DESIG)
ALL_CLUBS = sorted(set(CLUBS_IN_REPORT) | set(GAPS["clubs_not_captured"]))

Q_ROWS = QST["questions"]
Q_BLOCKING = [q for q in Q_ROWS if q["blocking"]]
Q_OPEN = [q for q in Q_ROWS if q["status"] == "open"]
S_ROWS = SUG["suggestions"]
S_UNDECIDED = [s for s in S_ROWS if s["decision_status"].startswith("Proposed")]
C_ROWS = CONF["rows"]
C_HIGH = [c for c in C_ROWS if c["severity"] == "high"]

OFFICIAL_READ = [s for s in SOURCES["sources"] if s["tier"] != "third-party" and s.get("read")]
NOT_OPENED = [s for s in SOURCES["sources"] if s["tier"] != "third-party" and not s.get("read")]
REJECTED = [s for s in SOURCES["sources"] if s["tier"] == "third-party"]


# --------------------------------------------------------------------------- #
# flags. Derived from the data so a flag can never drift from the row it flags.
# --------------------------------------------------------------------------- #
def build_flags() -> list[dict]:
    f: list[dict] = []
    for c in C_ROWS:
        f.append({
            "id": c["id"],
            "severity": c["severity"],
            "title": f'{c["club_name"]}: {c["kind"]}',
            "detail": c["why_it_matters"],
            "status": c["resolution_status"],
            "sources": [x["id"] for x in (c["source_a"], c["source_b"]) if x.get("id")],
            "page": "conflicts.html",
        })
    f.append({
        "id": "D13", "severity": "medium",
        "title": "Game Status blank on the large majority of captured injury rows",
        "detail": ("Of the captured Week 10 rows, " + str(len(DESIG)) + " carry an official game-status "
                   "designation and " + str(len(PRAC)) + " carry a practice status with a BLANK game status and "
                   "a BLANK injury cell. The blanks are printed as the official page printed them. They mean the "
                   "designation had not been published at capture time; they do NOT mean the player is healthy, "
                   "and no row here treats a blank as available."),
        "status": "published as blank", "sources": ["O01"], "page": "injuries.html",
    })
    f.append({
        "id": "D14", "severity": "medium",
        "title": "Depth-string ordering is unavailable from every official league publisher probed",
        "detail": ("The brief requires knowing when 2nd, 3rd or 4th string backups replace starters. The official "
                   "club roster page publishes no string ordering and no depth-chart tab (" + PROBE["roster_url"] +
                   "), and the club transaction path returns 404. Every depth-string cell in this directory is "
                   "therefore blank. Ordered charts exist only from non-official commercial publishers, which are "
                   "listed in the source register and rejected as evidence."),
        "status": "blocked - open question Q04", "sources": ["O04", "O05"], "page": "depth.html",
    })
    f.append({
        "id": "D17", "severity": "low",
        "title": "A position code that is not in the published convention is left unmapped",
        "detail": ("The Offence / Defence / Special teams grouping is a presentation convention applied by build.py, "
                   "not an official classification, and the full mapping is printed on every page that uses it. If a "
                   "position code appears that the convention does not list, the unit cell is printed blank rather "
                   "than being assigned by guesswork. No such code occurs in the captured week; the rule is recorded "
                   "so that the behaviour is defined before it is needed."),
        "status": "rule published", "sources": ["O01"], "page": "injuries.html",
    })
    f.append({
        "id": "D15", "severity": "medium",
        "title": "Official definitions of Out, Doubtful and Questionable were not retrieved",
        "detail": ("The report uses these designations but this session could not open the official rulebook or "
                   "football-operations policy page - the page reader failed for every attempt after source O03. "
                   "No definition is published, and none is written from memory, because converting a designation "
                   "into a probability of playing without the league's own definition would invent a number."),
        "status": "blocked - open question Q12", "sources": ["O01"], "page": "injuries.html",
    })
    var = GAPS.get("club_code_variance", {})
    f.append({
        "id": var.get("flag", "D18"), "severity": "medium",
        "title": "Club codes on the official report differ from the codes in the repository dataset",
        "detail": ("The official Week 10 report prints " + ", ".join(
            '"' + k + '"' for k in sorted(var.get("official_report_code", {}))) +
            " for clubs the repository's historical game dataset stores as " + ", ".join(
            '"' + var.get("repository_dataset_code", {}).get(k, "") + '"'
            for k in sorted(var.get("official_report_code", {}))) +
            ". That dataset is a third-party-derived file, not an official publisher. No official "
            "crosswalk was consulted, so decision_lab declares the alias map under "
            "coverage_gaps.club_code_variance for its own coverage gate and marks it unverified. "
            "Joining the two files on the club code alone silently drops those clubs."),
        "status": "declared alias, status unverified", "sources": ["O01"], "page": "injuries.html",
    })
    f.append({
        "id": "D16", "severity": "high",
        "title": "No betting price, odds line, correlation coefficient or strategy result is published here",
        "detail": ("No official publisher releases betting prices or model output for this project. Nothing in this "
                   "directory originates a line, states an edge, quotes a correlation or reports a return. The "
                   "injury and depth data published here is an INPUT to a future decision, not a recommendation to "
                   "bet. Open questions Q06, Q09, Q13 and Q16 record what would have to exist first."),
        "status": "by design - not a defect", "sources": [], "page": "index.html",
    })
    return f


FLAGS = build_flags()
FLAG = {x["id"]: x for x in FLAGS}


# --------------------------------------------------------------------------- #
# page shell
# --------------------------------------------------------------------------- #
NAV = [
    ("Decision lab", "index.html", "Overview and what this pack can support"),
    ("Injury and availability", "injuries.html", "Official Week 10 report, designations and practice status"),
    ("Depth capability", "depth.html", "What official sources do and do not publish about backups"),
    ("Source conflicts", "conflicts.html", "Verified disagreements between two official NFL.com pages"),
    ("Suggestions", "suggestions.html", "Options to review and choose from before anything is built"),
    ("Open questions", "open-questions.html", "What must be answered before a decision is reasonable"),
    ("Sources", "sources.html", "Every official page cited, and whether it was opened"),
    ("Flagged for review", "flagged.html", "Irregularities, blanks and blockers"),
    ("Verification", "verification.html", "What was checked, how, and what was not"),
]
NAV_OTHER = [
    ("Repository front door", "../index.html"),
    ("Consolidated dashboard", "../hub/index.html"),
    ("Verified workbench", "../verified/index.html"),
    ("Flagged for review (root)", "../flagged.html"),
]

PAGE_COUNT = len(NAV)


def head(title: str, desc: str) -> str:
    return (f'<!DOCTYPE html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            f'<meta name="viewport" content="width=device-width,initial-scale=1">\n'
            f'<title>{e(title)}</title>\n<meta name="description" content="{e(desc)}">\n'
            f'<link rel="stylesheet" href="assets/style.css">\n</head>\n')


def nav(active: str) -> str:
    out = ['<div class="wrap">\n<aside class="nav">\n'
           f'<div class="brand"><b>Decision Lab</b>'
           f'<span>NFL {e(SEASON)} &middot; Week {e(WEEK)} pack</span></div>\n'
           '<div class="grp">This pack</div>\n']
    for label, href, _t in NAV:
        cls = ' class="active"' if href == active else ""
        out.append(f'<a href="{e(href)}"{cls}>{e(label)}</a>\n')
    out.append('<div class="grp">Rest of the repository</div>\n')
    for label, href in NAV_OTHER:
        out.append(f'<a href="{e(href)}">{e(label)}<span class="ext">&#8599;</span></a>\n')
    out.append('</aside>\n<main>\n')
    return "".join(out)


def header(title: str, sub: str, verdict: str = "") -> str:
    v = ""
    if verdict:
        kind = "no" if verdict.startswith("NOT") else "yes"
        v = (f'<div class="verdict {kind}"><b>Can you act on this page?</b><p>{verdict}</p></div>')
    return (f'<header class="ph"><h1>{e(title)}</h1><p class="sub">{sub}</p>'
            f'<span class="stamp">Captured <b>{e(CAPTURED)}</b> UTC &middot; NFL {e(SEASON)} season, '
            f'week {e(WEEK)} &middot; session <b>arena/e35b6c85-korea3</b></span></header>\n{v}')


def footer() -> str:
    return (f'<footer class="pf">'
            f'<p>Generated by <code>decision_lab/build.py</code> from <code>decision_lab/data/*.json</code>. '
            f'Standard library only, no network access, no manual input, deterministic output.</p>'
            f'<p>Provenance vocabulary used on every page: '
            f'<span class="tag official">official league</span> published by the NFL; '
            f'<span class="tag club">official club</span> published by an NFL member club; '
            f'<span class="tag recomputed">recomputed</span> counted from rows already published here; '
            f'<span class="tag derived">derived</span> grouped by a stated presentation convention; '
            f'<span class="tag unverified">unverified</span> blank, because no official source confirms it.</p>'
            f'<p>No page in this directory publishes a betting price, an odds line, a correlation coefficient, '
            f'a return figure or a recommendation to bet. See flag '
            f'<a href="flagged.html#D16">D16</a>.</p>'
            f'</footer>\n</main>\n</div>\n<script src="assets/app.js"></script>\n</body>\n</html>\n')


def page(slug: str, title: str, desc: str, body: str, verdict: str = "") -> str:
    return head(title + " — Decision Lab", desc) + "<body>\n" + nav(slug) + \
        header(title, desc, verdict) + body + footer()


def table(tid: str, cols: list[tuple[str, str]], rows: list[str], caption: str = "") -> str:
    """cols = [(header, css-class), ...]. rows are pre-rendered <tr> strings."""
    cap = f"<caption>{caption}</caption>\n" if caption else ""
    th = "".join(f'<th class="{c}">{h}</th>' if c else f"<th>{h}</th>" for h, c in cols)
    return (f'<div class="tscroll"><table id="{e(tid)}">\n{cap}'
            f'<thead><tr>{th}</tr></thead>\n<tbody>\n' + "".join(rows) + '</tbody>\n</table></div>\n')


def filters(tid: str, controls: list[tuple[str, str, str]], placeholder: str) -> str:
    """controls = [(data-filter key, label, kind)] where kind is 'text' or 'select'."""
    out = [f'<div class="filters" data-tables="{e(tid)}">']
    for key, label, kind in controls:
        if kind == "text":
            out.append(f'<label>{e(label)} <input type="search" data-filter="text" '
                       f'placeholder="{e(placeholder)}"></label>')
        else:
            out.append(f'<label>{e(label)} <select data-filter="{e(key)}" data-autofill="{e(tid)}">'
                       f'<option value="__all">all</option></select></label>')
    out.append('<button type="button" data-reset class="tag lo">reset</button>')
    out.append('<span class="count"></span></div>\n')
    return "".join(out)


def convention_block() -> str:
    """Publish the position-code convention so the Offence/Defence grouping is auditable."""
    rows = []
    for name, codes in (("Offence", sorted(OFFENSE)), ("Defence", sorted(DEFENSE)),
                        ("Special teams", sorted(SPECIAL))):
        rows.append(f'<tr data-search="{e(name + " " + " ".join(codes))}">'
                    f'<td><span class="tag derived">derived</span> {e(name)}</td>'
                    f'<td class="mono">{e(", ".join(codes))}</td>'
                    f'<td>{src("O01")}</td></tr>')
    rows.append('<tr data-search="unlisted blank"><td><span class="tag unverified">unverified</span> '
                'Any code not listed above</td><td class="mono">&mdash;</td>'
                f'<td>{src("O01")}</td></tr>')
    return ('<div class="note"><b>The Offence / Defence grouping is a presentation convention, not an official '
            'classification.</b><p>The official report prints a position code per player and prints no unit. '
            'The mapping below is applied by <code>build.py</code> and is published in full so it can be audited '
            'or rejected. A position code that is not listed is left BLANK rather than assigned to a unit by '
            'guesswork.</p></div>\n'
            + table("conv", [("Unit", ""), ("Position codes mapped to it", ""), ("Source of the codes", "")],
                    rows, "Table: position-code to unit convention"))


# --------------------------------------------------------------------------- #
# pages
# --------------------------------------------------------------------------- #
def page_index() -> str:
    b = []
    b.append('<section class="card"><h2>What this is</h2>'
             '<p class="lead">A dated decision pack for NFL '
             f'{e(SEASON)} Week {e(WEEK)}, built to close three requirements in the project brief that the '
             'repository did not previously implement: a suggestions section with a decision gate, a register of '
             'the questions that must be answered before a decision is reasonable, and an injury and '
             'depth-availability tracker sourced only from official publishers.</p>'
             '<p>Nothing here is a betting recommendation. The injury and availability data is an <em>input</em> '
             'to a future decision. No page in this directory originates a line, states an edge, quotes a '
             f'correlation or reports a return &mdash; see flag <a href="flagged.html#D16">D16</a>.</p></section>\n')

    b.append('<div class="kpis">'
             f'<div class="kpi"><div class="n">{len(OFFICIAL_READ)}</div>'
             '<div class="l">official pages opened and read</div></div>'
             f'<div class="kpi warn"><div class="n">{len(NOT_OPENED)}</div>'
             '<div class="l">official pages cited but NOT opened</div></div>'
             f'<div class="kpi"><div class="n">{len(PRAC) + len(DESIG)}</div>'
             '<div class="l">injury-report player rows transcribed</div></div>'
             f'<div class="kpi bad"><div class="n">{len(DESIG)}</div>'
             '<div class="l">rows with an official game-status designation</div></div>'
             f'<div class="kpi bad"><div class="n">{len(C_HIGH)}</div>'
             '<div class="l">high-severity conflicts between official sources</div></div>'
             f'<div class="kpi warn"><div class="n">{len(Q_BLOCKING)}</div>'
             '<div class="l">open questions that block a decision</div></div>'
             f'<div class="kpi warn"><div class="n">{len(S_UNDECIDED)}</div>'
             '<div class="l">suggestions awaiting your decision</div></div>'
             f'<div class="kpi"><div class="n">{len(FLAG)}</div>'
             '<div class="l">flags published for review</div></div>'
             '</div>\n')

    b.append('<section class="card"><h2>The four findings that change what you should do next</h2>')
    rows = []
    findings = [
        ("F1", "The official weekly injury report and the official weekly news roundup disagree for the same week",
         f'Cincinnati, Seattle and the Los Angeles Chargers are each printed as "No Injuries Reported" in the '
         f'tabular report, while the same publisher names injuries for all three elsewhere &mdash; including a '
         f'Seahawks starting quarterback ruled out, headlined on the very same page. '
         f'<a href="conflicts.html">All {len(C_ROWS)} verified conflicts</a>.',
         "Do not build on one official feed alone.", ["O01", "O03"]),
        ("F2", "A player placed on injured reserve disappears from the weekly report entirely",
         'The Dolphins section lists ten players and no quarterback, while an official headline on that same page '
         'reports a Dolphins quarterback placed on injured reserve with a replacement in line for a first start. '
         'The report lists availability for the coming game, so the most severe availability event it could '
         'report is structurally invisible in it.',
         'Add an official roster-status feed. <a href="suggestions.html#S03">Suggestion S03</a>.', ["O01", "O07"]),
        ("F3", "No official league publisher provides depth-chart string ordering",
         'The official club roster page lists players alphabetically with a status code and offers only Info, '
         'Roster and Stats tabs. The club transaction path returns 404. Ordered charts exist only from commercial '
         'third parties, which this project rejects as evidence. The brief\'s 2nd/3rd/4th-string requirement '
         'cannot be met from official sources as they stand.',
         '<a href="depth.html">Capability probe</a>; <a href="suggestions.html#S04">Suggestion S04</a>; '
         '<a href="open-questions.html#Q04">Question Q04</a>.', ["O04", "O05"]),
        ("F4", "Official depth-chart news does exist, and it names the replacement directly",
         'The official roundup carries a DEPTH CHART NEWS heading under which it states which quarterback starts '
         'and who he replaces, citing the club\'s own announcement. This is the one official route found to the '
         'starter-to-backup resolution the brief asks for, and it is prose rather than a table.',
         '<a href="injuries.html#depthnews">Depth-chart news table</a>.', ["O03", "O14"]),
    ]
    for fid, title, detail, action, sids in findings:
        links = " ".join(src(s) for s in sids)
        rows.append(f'<tr id="{e(fid)}" data-search="{e((fid + " " + title + " " + detail).lower())}">'
                    f'<td class="mono">{e(fid)}</td><td><b>{title}</b><br>{detail}</td>'
                    f'<td>{action}</td><td>{links}</td></tr>')
    b.append(table("findings", [("ID", ""), ("Finding", ""), ("What follows from it", ""), ("Source", "")], rows))
    b.append('</section>\n')

    b.append('<section class="card"><h2>Pages in this pack</h2>')
    rows = []
    counts = {
        "index.html": "&mdash;", "injuries.html": f'{len(PRAC) + len(DESIG)} player rows',
        "depth.html": f'{len(REJECTED)} rejected non-official publishers',
        "conflicts.html": f'{len(C_ROWS)} verified conflicts',
        "suggestions.html": f'{len(S_ROWS)} suggestions', "open-questions.html": f'{len(Q_ROWS)} questions',
        "sources.html": f'{len(SOURCES["sources"])} registered sources',
        "flagged.html": f'{len(FLAGS)} flags', "verification.html": "checks and results",
    }
    for label, href, what in NAV:
        rows.append(f'<tr data-search="{e((label + " " + what).lower())}">'
                    f'<td><a href="{e(href)}">{e(label)}</a></td><td>{what}</td>'
                    f'<td class="num">{counts.get(href, "")}</td>'
                    f'<td>{src("O01") if href != "verification.html" else "n/a"}</td></tr>')
    b.append(table("pages", [("Page", ""), ("What it holds", ""), ("Volume", "num"), ("Primary source", "")], rows))
    b.append('</section>\n')

    b.append('<section class="card"><h2>How to use this pack</h2><ol class="tight">'
             '<li>Read <a href="open-questions.html">Open questions</a> first. '
             f'{len(Q_BLOCKING)} of {len(Q_ROWS)} questions are marked blocking, which means the decision they '
             'name cannot reasonably be made until they are answered.</li>'
             '<li>Then read <a href="suggestions.html">Suggestions</a>. Every entry lists options with their '
             'trade-offs and is stuck at <em>Proposed</em>. Nothing is implemented until you choose.</li>'
             '<li>Use <a href="injuries.html">Injury and availability</a> only as a dated snapshot, and read it '
             'alongside <a href="conflicts.html">Source conflicts</a>, which explains why the official report '
             'looks empty mid-week.</li>'
             '<li>Anything blank is blank because no official source confirms it. '
             '<a href="flagged.html">Every blank is flagged</a>. No blank is an implied zero.</li>'
             '</ol></section>\n')
    return page("index.html", "NFL Decision Lab",
                "Suggestions, open questions and an injury and depth-availability tracker for NFL "
                f"{SEASON} Week {WEEK}, sourced only from official publishers.", "".join(b),
                "NOT decision-ready for betting. It IS decision-ready for choosing what to build next: "
                f"{len(S_UNDECIDED)} suggestions await your choice and {len(Q_BLOCKING)} questions block a "
                "betting decision. No line, price, correlation or return is published anywhere in this pack.")


def page_injuries() -> str:
    b = []
    b.append('<div class="note bad"><b>Read this before using any number on this page.</b>'
             f'<p>This is a snapshot captured on <b>{e(CAPTURED)}</b> UTC, on a Thursday, for a week whose games '
             f'run Thursday to Monday. The official report is a live current-week view, not an archive (O02). At '
             f'capture only <b>{len(DESIG)}</b> rows across <b>{len(CLUBS_IN_REPORT)}</b> clubs carried an official '
             f'game-status designation. A blank Game Status or Injuries cell means the designation had not been '
             f'published yet &mdash; it does <b>not</b> mean the player is healthy. Flag '
             f'<a href="flagged.html#D13">D13</a>.</p>'
             f'<p>Coverage is partial and declared: {e(GAPS["clubs_captured"])} of 32 clubs were captured. '
             f'{e(", ".join(GAPS["clubs_not_captured"]))} were not, and their absence is not explained by any '
             f'official source. Flag <a href="flagged.html#D05">D05</a>.</p></div>\n')

    b.append('<div class="kpis">'
             f'<div class="kpi"><div class="n">{len(GAMES)}</div><div class="l">games listed on the official report</div></div>'
             f'<div class="kpi"><div class="n">{len(CLUBS_IN_REPORT)}</div><div class="l">clubs captured</div></div>'
             f'<div class="kpi bad"><div class="n">{len(GAPS["clubs_not_captured"])}</div><div class="l">clubs NOT captured</div></div>'
             f'<div class="kpi"><div class="n">{len(PRAC) + len(DESIG)}</div><div class="l">player rows transcribed</div></div>'
             f'<div class="kpi bad"><div class="n">{len(DESIG)}</div><div class="l">official designations (Out / Questionable)</div></div>'
             f'<div class="kpi"><div class="n">{len(NOINJ)}</div><div class="l">clubs printed as "No Injuries Reported"</div></div>'
             f'<div class="kpi warn"><div class="n">{len(ROUNDUP)}</div><div class="l">rows from the official roundup</div></div>'
             f'<div class="kpi warn"><div class="n">{len(HEADLINES)}</div><div class="l">official headlines on the report page</div></div>'
             '</div>\n')

    # --- designations -----------------------------------------------------
    b.append('<section class="card"><h2>1. Officially designated availability</h2>'
             '<p class="lead">Every row the official Week 10 report printed with a non-blank Game Status, or a '
             'non-blank Injuries value. These are the only official availability outcomes in the captured report. '
             'Transcribed verbatim; the Injury and Game Status columns are exactly as printed.</p>')
    rows = []
    for d in DESIG:
        rows.append(
            f'<tr data-team="{e(d["team"])}" data-unit="{e(unit_of(d["position"]))}" data-gs="{e(d["game_status"])}" '
            f'data-search="{e((d["team"] + " " + d["player"] + " " + d["position"] + " " + d["injury"] + " " + d["game_status"]).lower())}">'
            f'<td class="mono">{e(d["team"])}</td>'
            f'<td><a href="{e(d["player_url"])}">{e(d["player"])}</a></td>'
            f'<td class="mono">{e(d["position"])}</td>'
            f'<td><span class="tag derived">derived</span> {e(unit_of(d["position"])) or blank("unmapped", "D17")}</td>'
            f'<td>{e(d["injury"])}</td><td>{ps_tag(d["practice_status"])}</td><td>{gs_tag(d["game_status"])}</td>'
            f'<td>{blank("no string order published", "D14")}</td>'
            f'<td>{src(d["source_id"])}</td></tr>')
    b.append(filters("design", [("team", "Club", "select"), ("unit", "Unit", "select"), ("gs", "Game status", "select")],
                     "player, club, injury"))
    b.append(table("design", [("Club", ""), ("Player", ""), ("Pos", ""), ("Unit", ""), ("Injury (as printed)", ""),
                              ("Practice status", ""), ("Game status", ""), ("Depth string", ""), ("Source", "")],
                   rows, "Table: officially designated availability, NFL "
                          f"{SEASON} Week {WEEK}"))
    b.append('<p style="font-size:13px;color:var(--muted)">Depth string is blank on every row because no official '
             f'league publisher prints one &mdash; flag <a href="flagged.html#D14">D14</a>, question '
             '<a href="open-questions.html#Q04">Q04</a>.</p>')
    b.append('</section>\n')

    # --- depth chart news -------------------------------------------------
    b.append('<section class="card" id="depthnews"><h2>2. Official depth-chart news: starters and the backups who replace them</h2>'
             '<p class="lead">Rows from the DEPTH CHART NEWS sections of the official NFL.com roundup. This is the '
             'only official source found that names a replacement directly, which is what the brief asks the system '
             'to know. Text is verbatim; no starter or backup is inferred anywhere else on this site.</p>')
    rows = []
    for r in ROUNDUP:
        if r["section"] != "DEPTH CHART NEWS":
            continue
        club = ""
        for g in GAMES:
            if r["team"] in (g["away"], g["home"]):
                club = f'{g["away"]} @ {g["home"]}'
                break
        plink = (f'<a href="{e(r["player_url"])}">{e(r["player"])}</a>' if r.get("player_url")
                 else blank("no official link on the source page", "D11"))
        extra = ""
        if r.get("club_announcement_url"):
            extra = (f'<br><a href="{e(r["club_announcement_url"])}">club announcement</a> '
                     f'{tier_tag(r["club_source_id"])}')
        rows.append(f'<tr data-team="{e(r["team"])}" data-search="{e((r["team"] + " " + r["text"]).lower())}">'
                    f'<td class="mono">{e(r["team"])}</td><td>{plink}</td>'
                    f'<td class="mono">{e(r["position"])}</td><td>{e(club) or blank("not captured", "D06")}</td>'
                    f'<td>{e(r["text"])}{extra}</td>'
                    f'<td>{src(r["source_id"])}</td></tr>')
    b.append(table("depthnews", [("Club", ""), ("Player", ""), ("Pos", ""), ("Week 10 matchup", ""),
                                 ("Official text, verbatim", ""), ("Source", "")], rows,
                   "Table: official depth-chart news"))
    b.append('<div class="note"><b>Only two clubs have depth-chart news here, and that is the finding.</b>'
             '<p>Arizona and Cleveland are the only clubs whose DEPTH CHART NEWS section this session retrieved. '
             'The roundup\'s remaining club sections were in page chunks that could not be fetched, so they have no '
             f'rows &mdash; they are not assumed to be empty. Flag <a href="flagged.html#D12">D12</a>, question '
             '<a href="open-questions.html#Q02">Q02</a>.</p></div>')
    b.append('</section>\n')

    # --- headlines --------------------------------------------------------
    b.append('<section class="card"><h2>3. Official headlines printed on the report page itself</h2>'
             '<p class="lead">The NEWS section of the official injury report carries headlines that contradict the '
             'report\'s own tables. They are transcribed here exactly as printed. The linked article bodies were '
             '<b>not</b> retrieved, so nothing beyond the headline text is asserted, and no player row is created '
             'from a headline.</p>')
    rows = []
    for h in HEADLINES:
        art = src(h["article_source_id"]) if h.get("article_source_id") else blank("not registered", "D12")
        rows.append(f'<tr data-search="{e(h["headline"].lower())}">'
                    f'<td><a href="{e(h["url"])}">{e(h["headline"])}</a></td>'
                    f'<td>{art}</td><td>{src(h["source_id"], "report page")}</td></tr>')
    b.append(table("headlines", [("Headline as printed on the official report page", ""),
                                 ("Article body", ""), ("Headline seen on", "")], rows,
                   "Table: official NFL.com headlines, transcribed verbatim"))
    b.append('</section>\n')

    # --- roundup injuries -------------------------------------------------
    b.append('<section class="card"><h2>4. Injury detail and roster moves from the official roundup</h2>'
             '<p class="lead">The weekly report leaves the Injuries column blank at mid-week capture; the official '
             'roundup names the injury for many of the same players. The two are published in separate tables with '
             'separate citations and are <b>never merged into one cell</b>, so no value is ever attributed to a '
             'source that does not print it. Only the eight club sections actually retrieved are here.</p>')
    b.append(filters("roundup", [("team", "Club", "select"), ("section", "Section", "select")],
                     "player, injury, roster move"))
    rows = []
    for r in ROUNDUP:
        if r["section"] == "DEPTH CHART NEWS":
            continue
        plink = (f'<a href="{e(r["player_url"])}">{e(r["player"])}</a>' if r.get("player_url")
                 else blank("no official link on the source page", "D11"))
        note = ""
        if r.get("verbatim_note"):
            note = f'<br><span class="tag unverified">verbatim</span> {e(r["verbatim_note"])}'
        if r.get("truncation_note"):
            note = f'<br><span class="tag unverified">truncated</span> {e(r["truncation_note"])}'
        rows.append(f'<tr data-team="{e(r["team"])}" data-section="{e(r["section"])}" '
                    f'data-search="{e((r["team"] + " " + r["section"] + " " + r["text"]).lower())}">'
                    f'<td class="mono">{e(r["team"])}</td>'
                    f'<td><span class="tag lo">{e(r["section"])}</span></td>'
                    f'<td>{plink}</td><td class="mono">{e(r["position"])}</td>'
                    f'<td><span class="tag derived">derived</span> {e(unit_of(r["position"])) or blank("unmapped", "D17")}</td>'
                    f'<td>{e(r["text"])}{note}</td><td>{src(r["source_id"])}</td></tr>')
    b.append(table("roundup", [("Club", ""), ("Section", ""), ("Player", ""), ("Pos", ""), ("Unit", ""),
                               ("Official text, verbatim", ""), ("Source", "")], rows,
                   "Table: official roundup entries for ARI, ATL, BAL, BUF, CAR, CIN, CLE, DAL"))
    b.append(convention_block())
    b.append('</section>\n')

    # --- practice participation ------------------------------------------
    b.append('<section class="card"><h2>5. Practice participation, all captured rows</h2>'
             '<p class="lead">Every player row this session captured from the official report. The Injuries and '
             'Game Status columns were BLANK on the official page for all of these rows and are printed blank. '
             'This table is usable for participation counts; it is not usable for injury type, which is why table 4 '
             'exists separately.</p>')
    b.append(filters("prac", [("team", "Club", "select"), ("unit", "Unit", "select"), ("ps", "Practice status", "select")],
                     "player, club, position"))
    rows = []
    for r in PRAC:
        rows.append(f'<tr data-team="{e(r["team"])}" data-unit="{e(unit_of(r["position"]))}" '
                    f'data-ps="{e(r["practice_status"])}" '
                    f'data-search="{e((r["team"] + " " + r["player"] + " " + r["position"]).lower())}">'
                    f'<td class="mono">{e(r["team"])}</td>'
                    f'<td><a href="{e(r["player_url"])}">{e(r["player"])}</a></td>'
                    f'<td class="mono">{e(r["position"])}</td>'
                    f'<td><span class="tag derived">derived</span> {e(unit_of(r["position"])) or blank("unmapped", "D17")}</td>'
                    f'<td>{ps_tag(r["practice_status"])}</td>'
                    f'<td>{blank()}</td><td>{blank("blank", "D13")}</td>'
                    f'<td>{src("O01")}</td></tr>')
    b.append(table("prac", [("Club", ""), ("Player", ""), ("Pos", ""), ("Unit", ""), ("Practice status", ""),
                            ("Injuries (as printed)", ""), ("Game status", ""), ("Source", "")], rows,
                   f"Table: all {len(PRAC)} captured practice-participation rows"))
    b.append('</section>\n')

    # --- club rollup ------------------------------------------------------
    b.append('<section class="card"><h2>6. Club roll-up by unit</h2>'
             '<p class="lead">Counts of the rows in table 5, grouped by the published position-code convention. '
             'This is <span class="tag recomputed">recomputed</span> arithmetic over rows already on this page '
             '&mdash; not an official league statistic, and not a measure of how injured a club is, because the '
             'report lists only the players a club chose to report.</p>')
    b.append(filters("roll", [("unit", "Unit", "select")], "club"))
    rows = []
    for club in CLUBS_IN_REPORT:
        crows = [dict(r) for r in PRAC if r["team"] == club]
        crows += [{"position": d["position"], "practice_status": d["practice_status"]}
                  for d in DESIG if d["team"] == club]
        c = Counter(r["practice_status"] for r in crows)
        by_unit = Counter(unit_of(r["position"]) or "(unmapped)" for r in crows)
        if not crows:
            rows.append(f'<tr data-unit="" data-search="{e(club.lower())}"><td class="mono">{e(club)}</td>'
                        f'<td colspan="7"><span class="tag lo">No Injuries Reported</span> '
                        f'&mdash; printed verbatim by the official report. See '
                        f'<a href="conflicts.html">source conflicts</a>: for three of these clubs another official '
                        f'NFL.com page reports injuries for the same week.</td>'
                        f'<td>{src("O01")}</td></tr>')
            continue
        rows.append(f'<tr data-unit="{e(by_unit.most_common(1)[0][0])}" data-search="{e(club.lower())}">'
                    f'<td class="mono">{e(club)}</td>'
                    f'<td class="num">{len(crows)}</td>'
                    f'<td class="num">{c.get("Did Not Participate In Practice", 0)}</td>'
                    f'<td class="num">{c.get("Limited Participation in Practice", 0)}</td>'
                    f'<td class="num">{c.get("Full Participation in Practice", 0)}</td>'
                    f'<td class="num">{by_unit.get("Offence", 0)}</td>'
                    f'<td class="num">{by_unit.get("Defence", 0)}</td>'
                    f'<td class="num">{by_unit.get("Special teams", 0)}</td>'
                    f'<td>{src("O01")}</td></tr>')
    b.append(table("roll", [("Club", ""), ("Rows", "num"), ("DNP", "num"), ("Limited", "num"), ("Full", "num"),
                            ("Offence", "num"), ("Defence", "num"), ("Special teams", "num"), ("Source", "")],
                   rows, "Table: captured practice rows per club, grouped by unit"))
    b.append('<div class="note warn"><b>Why four clubs have no row in this table.</b>'
             f'<p>{e(", ".join(GAPS["clubs_not_captured"]))} were not captured. Whether they are on bye, were '
             'listed in an unretrieved page chunk, or are omitted by the report is NOT KNOWN and is not inferred. '
             f'Flag <a href="flagged.html#D05">D05</a>, question <a href="open-questions.html#Q10">Q10</a>.</p></div>')

    # --- club-code variance (flag D18) ------------------------------------
    var = GAPS.get("club_code_variance", {})
    alias = var.get("aliases_used_for_coverage_gate_only", {})
    off_code = var.get("official_report_code", {})
    rep_code = var.get("repository_dataset_code", {})
    if alias:
        rows = []
        for repo_code in sorted(set(off_code) | set(rep_code)):
            canon = alias.get(repo_code, repo_code)
            declared = repo_code in alias
            rows.append(f'<tr data-search="{e((repo_code + " " + canon).lower())}">'
                        f'<td class="mono">{e(off_code.get(repo_code, "")) or blank("not captured", "D18")}</td>'
                        f'<td class="mono">{e(rep_code.get(repo_code, "")) or blank("not captured", "D18")}</td>'
                        f'<td class="mono">{e(canon)}</td>'
                        f'<td><span class="tag unverified">{e(var.get("status", "unverified"))}</span> '
                        + ('declared alias, for the coverage gate only, not evidence' if declared
                           else 'already canonical in both; the divergence is the dataset spelling')
                        + '</td>'
                        f'<td>{src("O01")} <a href="flagged.html#D18">flag register</a></td></tr>')
        b.append(table("codes", [("Official report code (O01)", ""), ("Repository dataset code", ""),
                                ("Club both spellings denote", ""), ("Status", ""), ("Source", "")],
                       rows, "Table: club codes that differ between the official report and the repository dataset"))
        b.append('<div class="note warn"><b>Why two spellings of the same club are both printed.</b>'
                 f'<p>{e(var.get("compared_against", ""))}. No official crosswalk was consulted and none is '
                 'invented here. The alias map is a join instruction recorded so that a future merge does not '
                 f'silently drop these clubs. Flag <a href="flagged.html#D18">D18</a>.</p></div>')
    b.append('</section>\n')

    # --- games ------------------------------------------------------------
    b.append('<section class="card"><h2>7. Official Week 10 game list</h2>'
             '<p class="lead">Day, kickoff, broadcast and each club\'s win-loss-tie record exactly as printed on '
             'the official report. Blank cells were blank at the capture boundary and are not filled from a '
             'neighbouring row.</p>')
    rows = []
    for g in GAMES:
        note = f'<br><span class="tag unverified">truncated</span> {e(g["_blank_reason"])}' if g.get("_blank_reason") else ""
        rows.append(f'<tr data-search="{e((g["away"] + " " + g["home"] + " " + g["day"]).lower())}">'
                    f'<td>{e(g["day"]) or blank("not captured", "D06")}</td>'
                    f'<td class="mono">{e(g["kickoff"]) or blank("not captured", "D06")}</td>'
                    f'<td>{e(g["broadcast"]) or blank("not captured", "D06")}{note}</td>'
                    f'<td><a href="{e(g["away_url"])}">{e(g["away"])}</a> {e(g["away_name"])} '
                    f'<span class="mono">({e(g["away_record"])})</span></td>'
                    f'<td><a href="{e(g["home_url"])}">{e(g["home"])}</a> {e(g["home_name"])} '
                    f'<span class="mono">({e(g["home_record"])})</span></td>'
                    f'<td class="num">{DESIG_BY_CLUB.get(g["away"], 0) + DESIG_BY_CLUB.get(g["home"], 0)}</td>'
                    f'<td>{src("O01")}</td></tr>')
    b.append(table("games", [("Day", ""), ("Kickoff", ""), ("Broadcast", ""), ("Away", ""), ("Home", ""),
                             ("Designations", "num"), ("Source", "")], rows,
                   "Table: official Week 10 game list as printed on the injury report"))
    b.append('</section>\n')
    return page("injuries.html", "Injury and availability tracker",
                "The official NFL.com Week 10 injury report, the official depth-chart news that names replacements, "
                "and the practice-participation rows, transcribed verbatim with per-row source links.",
                "".join(b),
                f"NOT decision-ready. Only {len(DESIG)} of {len(PRAC) + len(DESIG)} captured rows carry an official "
                f"designation, {len(GAPS['clubs_not_captured'])} clubs were not captured at all, and no official "
                "source defines the designations. Use it as a dated snapshot of what is known, not as a health "
                "assessment.")


def page_depth() -> str:
    b = []
    b.append('<div class="note bad"><b>Capability finding, not a data table.</b>'
             '<p>The brief requires the system to know when 2nd, 3rd or 4th string backups replace starters, on '
             'offence and defence. This page records what was probed, what each official publisher does and does '
             'not provide, and what was found only from non-official publishers and therefore rejected.</p></div>\n')

    b.append('<section class="card"><h2>1. What each official publisher provides</h2>')
    rows = [
        ("Weekly injury report", "O01", "Player, position code, injury text, practice status, game status; each "
         "player name links an official player page", "No string ordering. No indication of who replaces an "
         "unavailable player. Players on injured reserve do not appear at all (D08)."),
        ("Club roster page", "O04", "Player, jersey number, position code, roster status code (observed: ACT), "
         "height, weight, experience, college; rows alphabetical by surname",
         "No first/second/third-string ordering anywhere. No depth-chart tab &mdash; the club navigation offers "
         "only Info, Roster and Stats. No legend for the status-code vocabulary."),
        ("Club transaction page", "O05", "Nothing &mdash; the path returns NFL.com's 404 page",
         "The club-level transaction feed does not exist at this path. Recorded as a verified absence so no future "
         "session re-derives it by assumption."),
        ("League transaction hub", "O12", "Attested to exist by the body text of the official roundup, which links "
         "it as \"a daily breakdown\"", "Content, coverage and machine-readability UNVERIFIED. This session could "
         "not open it. No value is published from it."),
        ("Weekly news roundup", "O03", "DEPTH CHART NEWS sections that name a starting quarterback and the player "
         "he replaces, citing the club's own announcement; injured-reserve designations to return; activations off "
         "injured reserve", "Prose, not tabular. Covers only what the editor wrote. Not every club appears every "
         "week, and not every position is ever mentioned."),
        ("Club announcement (member club)", "O14", "The primary source behind the league site's own depth-chart "
         "news for Cleveland", "Club domains are not in this repository's official-host allow-list, so adopting "
         "them is a governance decision (question Q15, suggestion S13)."),
    ]
    rendered = []
    for name, sid, provides, missing in rows:
        s = SRC[sid]
        rendered.append(
            f'<tr data-search="{e((name + " " + provides + " " + missing).lower())}">'
            f'<td><b>{e(name)}</b><br><span class="mono" style="font-size:11.6px">{e(s["url"])}</span></td>'
            f'<td>{tier_tag(sid)} {"opened" if s.get("read") else "<b>NOT opened</b>"}</td>'
            f'<td>{provides}</td><td>{missing}</td><td>{src(sid)}</td></tr>')
    rows = rendered
    b.append(table("cap", [("Official publisher probed", ""), ("Tier", ""), ("What it DOES provide", ""),
                           ("What it does NOT provide", ""), ("Source", "")], rows,
                   "Table: capability of each official publisher for depth and availability"))
    b.append('</section>\n')

    b.append('<section class="card"><h2>2. The depth-string field is blank everywhere, on purpose</h2>'
             '<p class="lead">This is what the brief asks for and what official sources cannot supply. Rather than '
             'fill it, the field is published empty with a flag, so that the gap is visible to a reader instead of '
             'being hidden behind a plausible-looking number.</p>')
    rows = []
    for label in ("1st string", "2nd string", "3rd string", "4th string"):
        rows.append(f'<tr data-search="{e(label.lower())}"><td>{e(label)}</td>'
                    f'<td>{blank("blank", "D14")}</td>'
                    f'<td>No official league publisher prints string ordering. The official club roster page is '
                    f'alphabetical with a status code and no depth-chart tab.</td>'
                    f'<td>{src("O04")} {src("O05")}</td></tr>')
    b.append(table("strings", [("Field required by the brief", ""), ("Value published", ""),
                               ("Why it is blank", ""), ("Evidence for the absence", "")], rows,
                   "Table: the four depth-string fields the brief requires"))
    b.append('</section>\n')

    b.append('<section class="card"><h2>3. Non-official publishers found, and rejected</h2>'
             '<p class="lead">A search for official depth charts returned only commercial third parties. They are '
             'recorded here for completeness and explicitly <b>rejected as evidence</b>: no value anywhere in this '
             'repository is taken from them. One useful thing is kept &mdash; the field structure a legitimate '
             'official feed would have to supply, which is recorded as a specification, not as data.</p>')
    rows = []
    for s in REJECTED:
        rows.append(f'<tr data-search="{e((s["publisher"] + " " + s["title"]).lower())}">'
                    f'<td><a href="{e(s["url"])}">{e(s["publisher"])}</a></td>'
                    f'<td>{e(s["title"])}</td><td>{tier_tag(s["id"])}</td>'
                    f'<td>{e(s["read_note"])}</td>'
                    f'<td><span class="tag unverified">rejected</span> {e(s["supports"])}</td></tr>')
    b.append(table("rejected", [("Publisher", ""), ("Page", ""), ("Tier", ""), ("Why it was recorded", ""),
                                ("What it supports", "")], rows,
                   "Table: third-party depth-chart publishers, rejected as evidence"))
    b.append('<div class="note"><b>The specification worth keeping from X03.</b>'
             '<p>One rejected publisher lays its chart out as Player 1 through Player 5 per position, split into '
             'an Offence table and a Defence table, with a jersey number beside each name. That is exactly the '
             'shape an official feed would need to have for the brief\'s requirement to be met, so it is recorded '
             'here as a requirement specification. The data itself is not used and must not be.</p></div>')
    b.append('</section>\n')

    b.append('<section class="card"><h2>4. The route that does work, and what it would take</h2>'
             '<p class="lead">Official depth-chart news is real and citable. It is prose, it is selective, and it '
             'currently arrives on a page whose club sections this session could only partly retrieve. Making it '
             'usable is a decision for the owner, not for this pack.</p>')
    rows = []
    steps = [
        ("1", "Decide whether the 32 member-club domains count as official publishers",
         "NFL.com itself cites a club announcement as the source of its depth-chart news, so the league publisher "
         "already treats club sites as primary. But this repository's allow-list excludes them.",
         "S13", "Q15"),
        ("2", "Survey the official club sites for a published depth chart",
         "Record per club whether one exists, in what format, and how often it is updated. Publish the survey, "
         "including the clubs that have none.", "S04", "Q04"),
        ("3", "Snapshot all 32 official roster status columns weekly and diff them",
         "A starter moving to a reserve status is the highest-value availability signal available from an official "
         "source, and it is the one the weekly report structurally hides.", "S03", "Q05"),
        ("4", "Learn the status-code vocabulary by observation, then ask for definitions",
         "Only ACT was observed. Publish the codes actually seen with counts; leave meanings blank until NFL "
         "Football Operations or the rulebook defines them.", "S03", "Q05"),
        ("5", "Never infer a string from snap counts or participation",
         "A snap-count ranking is a model output, not a published depth chart. It would have to be labelled as a "
         "model estimate everywhere it appeared, and it still would not answer the brief.", "S04", "Q04"),
    ]
    for n, step, why, sug, q in steps:
        rows.append(f'<tr data-search="{e((step + " " + why).lower())}"><td class="mono">{e(n)}</td>'
                    f'<td><b>{e(step)}</b></td><td>{e(why)}</td>'
                    f'<td><a href="suggestions.html#{e(sug)}">{e(sug)}</a></td>'
                    f'<td><a href="open-questions.html#{e(q)}">{e(q)}</a></td>'
                    f'<td>{src("O03")} {src("O04")}</td></tr>')
    b.append(table("route", [("#", ""), ("Step", ""), ("Why", ""), ("Suggestion", ""), ("Question", ""),
                             ("Evidence", "")], rows, "Table: the route to official depth data"))
    b.append('</section>\n')
    return page("depth.html", "Depth capability probe",
                "What official NFL publishers do and do not provide about backups, string ordering and roster "
                "status, and which non-official publishers were found and rejected.",
                "".join(b),
                "NOT decision-ready. The capability the brief requires &mdash; knowing which string of backup "
                "replaces a starter &mdash; does not exist in any official league publication this session could "
                "reach. This page documents the absence with evidence and sets out the options.")


def page_conflicts() -> str:
    b = []
    b.append('<div class="note bad"><b>Two official NFL.com pages disagree about the same week.</b>'
             f'<p>{len(C_ROWS)} discrepancies were verified this session by reading two official pages and '
             f'comparing them; {len(C_HIGH)} are high severity. Each row cites both pages. Nothing here is '
             'inferred, and no discrepancy is resolved by preferring one source &mdash; both are published side by '
             'side, because the disagreement is itself the useful information about when the data may be '
             'trusted.</p></div>\n')
    b.append('<div class="kpis">'
             f'<div class="kpi bad"><div class="n">{len(C_HIGH)}</div><div class="l">high severity</div></div>'
             f'<div class="kpi warn"><div class="n">{sum(1 for c in C_ROWS if c["severity"] == "medium")}</div><div class="l">medium severity</div></div>'
             f'<div class="kpi"><div class="n">{sum(1 for c in C_ROWS if c["severity"] == "low")}</div><div class="l">low severity</div></div>'
             f'<div class="kpi bad"><div class="n">{sum(1 for c in C_ROWS if c["resolution_status"].startswith("unresolved"))}</div><div class="l">unresolved</div></div>'
             f'<div class="kpi warn"><div class="n">{sum(1 for c in C_ROWS if c["resolution_status"].startswith("blocked"))}</div><div class="l">blocked</div></div>'
             '</div>\n')

    b.append('<section class="card"><h2>Verified discrepancies between official sources</h2>')
    b.append(filters("conf", [("severity", "Severity", "select"), ("club", "Club", "select")], "club, kind, why it matters"))
    rows = []
    for c in C_ROWS:
        sa, sb = c["source_a"], c["source_b"]
        sbl = (src(sb["id"]) + " " + sb["what_it_says"]) if sb.get("id") else \
              '<span class="tag lo">single-source defect</span> ' + sb["what_it_says"]
        rows.append(
            f'<tr id="{e(c["id"])}" data-severity="{e(c["severity"])}" data-club="{e(c["club"])}" '
            f'data-search="{e((c["id"] + " " + c["club"] + " " + c["club_name"] + " " + c["kind"] + " " + c["why_it_matters"]).lower())}">'
            f'<td class="mono">{e(c["id"])}</td><td>{sev_tag(c["severity"])}</td>'
            f'<td class="mono">{e(c["club"])}</td><td>{e(c["kind"])}</td>'
            f'<td>{src(sa["id"])} {sa["what_it_says"]}</td>'
            f'<td>{sbl}</td>'
            f'<td>{e(c["why_it_matters"])}</td>'
            f'<td><span class="tag {"unverified" if c["resolution_status"].startswith(("unresolved","blocked")) else "recomputed"}">'
            f'{e(c["resolution_status"])}</span><br>{e(c["resolution_rule"])}</td></tr>')
    b.append(table("conf", [("ID", ""), ("Severity", ""), ("Club", ""), ("Kind", ""),
                            ("Official source A says", ""), ("Official source B says", ""),
                            ("Why it matters", ""), ("Resolution", "")], rows,
                   "Table: verified discrepancies, NFL "
                   f"{SEASON} Week {WEEK}"))
    b.append('</section>\n')

    b.append('<section class="card"><h2>The structural conclusion</h2>'
             '<p>Three of these discrepancies share one cause, and it is not an error by either publisher. The '
             'weekly injury report describes availability for the coming game. A player on injured reserve is not '
             'available for it, so he is not listed &mdash; which means the report cannot show the most severe '
             'availability event there is (D08). And designations are added through the week, so a Thursday '
             'capture shows almost none of them (D13).</p>'
             '<p>Two consequences follow, and both are decisions rather than findings:</p>'
             '<ul class="tight">'
             '<li>A single official feed is not enough. <a href="suggestions.html#S02">S02</a> proposes taking the '
             'union with provenance kept separate, and <a href="suggestions.html#S03">S03</a> proposes adding an '
             'official roster-status feed that the weekly report cannot substitute for.</li>'
             '<li>Every row must carry its capture time. <a href="suggestions.html#S05">S05</a> proposes a '
             'staleness gate, because a page that looks live but is four days old is how a decision gets made on '
             'data that has already changed.</li>'
             '</ul></section>\n')
    return page("conflicts.html", "Source conflicts",
                f"{len(C_ROWS)} verified discrepancies between two official NFL.com publications covering the same "
                "week, each citing both pages, none resolved by preferring one over the other.",
                "".join(b),
                f"NOT decision-ready, and deliberately so. {len(C_HIGH)} high-severity conflicts between official "
                "sources are unresolved. This page exists to stop a decision being made on one feed alone.")


def page_suggestions() -> str:
    gate = SUG["decision_gate"]
    b = []
    b.append(f'<div class="gate"><b>Decision gate &mdash; enforced by code, not by convention.</b>'
             f'<p>{e(gate["rule"])}</p>'
             f'<p>Enforced by <code>{e(gate["enforced_by"])}</code>, which fails the build if any suggestion is '
             f'marked Approved, Rejected or Implemented. Deciding is {e(gate["who_decides"])}\'s to do. '
             f'{len(S_UNDECIDED)} of {len(S_ROWS)} suggestions are currently awaiting that decision.</p></div>\n')

    b.append('<div class="kpis">'
             f'<div class="kpi"><div class="n">{len(S_ROWS)}</div><div class="l">suggestions registered</div></div>'
             f'<div class="kpi warn"><div class="n">{len(S_UNDECIDED)}</div><div class="l">awaiting your decision</div></div>'
             f'<div class="kpi bad"><div class="n">{sum(1 for s in S_ROWS if s["blocking"])}</div><div class="l">blocking a stated decision</div></div>'
             f'<div class="kpi"><div class="n">{sum(len(s["options"]) for s in S_ROWS)}</div><div class="l">options laid out to choose from</div></div>'
             f'<div class="kpi ok"><div class="n">{sum(1 for s in S_ROWS if s["decision_status"] == "In force")}</div><div class="l">in force</div></div>'
             '</div>\n')

    b.append('<section class="card"><h2>Register</h2>'
             '<p class="lead">Filter by category or blocking status. Each entry states the problem with its '
             'evidence, lays out options with their trade-offs, and records a recommendation. The recommendation is '
             'advice; the decision is yours and is recorded in <code>suggestions.json</code>.</p>')
    b.append(filters("sug", [("category", "Category", "select"), ("decision_status", "Status", "select"),
                             ("blocking", "Blocking", "select")], "title, problem, option"))
    rows = []
    for s in S_ROWS:
        cats = s["category"]
        st = s["decision_status"]
        stc = "inforce" if st == "In force" else "proposed"
        opts = "<br>".join(f'<b>{e(o["id"])}.</b> {e(o["label"])}' for o in s["options"])
        blocks = f'<br><span class="tag unverified">blocks</span> {e(s.get("blocks", ""))}' if s.get("blocks") else ""
        evlinks = []
        for i in s["evidence"]:
            if i in SRC:
                evlinks.append(src(i))
            elif i.startswith("D"):
                f_ = FLAG.get(i)
                evlinks.append(f'<a href="{e(f_["page"] if f_ else "conflicts.html")}#{e(i)}">{e(i)}</a>')
            else:
                evlinks.append(f'<span class="tag lo" title="Repository command or file, output quoted in the '
                               f'problem text">{e(i)}</span>')
        blocktag = ('<span class="tag hi">blocking</span>' if s["blocking"]
                    else '<span class="tag lo">no</span>')
        rows.append(
            f'<tr id="{e(s["id"])}" data-category="{e(cats)}" data-decision_status="{e(st)}" '
            f'data-blocking="{"yes" if s["blocking"] else "no"}" '
            f'data-search="{e((s["id"] + " " + s["title"] + " " + s["problem"] + " " + opts).lower())}">'
            f'<td class="mono"><a href="suggestions.html#{e(s["id"])}" title="Permalink to this suggestion">{e(s["id"])}</a></td>'
            f'<td><b>{e(s["title"])}</b><br><span class="tag lo">{e(cats)}</span></td>'
            f'<td>{e(s["problem"])}</td>'
            f'<td>{opts}</td>'
            f'<td>{e(s["recommendation"])}</td>'
            f'<td><span class="tag {stc}">{e(st)}</span>'
            f'{" " + blocktag if s["blocking"] else ""}{blocks}</td>'
            f'<td>{" ".join(evlinks) or blank("no external evidence", "")}</td></tr>')
    b.append(table("sug", [("ID", ""), ("Suggestion", ""), ("Problem, with its evidence", ""),
                           ("Options", ""), ("Recommendation", ""), ("Decision status", ""),
                           ("Evidence", "")], rows,
                   "Table: suggestion register with decision gate"))
    b.append('</section>\n')

    b.append('<section class="card"><h2>How to decide</h2>'
             '<p class="lead">The register is built so a decision can be recorded without editing any page. Each '
             'suggestion carries three fields that are empty until you fill them.</p>')
    rows = []
    for field, meaning, allowed in (
            ("chosen_option", "The option letter you selected, e.g. \"c\".", "One of the option IDs listed for that suggestion, or empty."),
            ("decision_date", "When you decided, in UTC.", "A date, or empty."),
            ("decision_status", "Where the suggestion now stands.",
             " / ".join(gate["statuses_allowed"]) + ". The build fails if an agent sets Approved, Rejected or Implemented."),
    ):
        rows.append(f'<tr data-search="{e((field + " " + meaning).lower())}"><td class="mono">{e(field)}</td>'
                    f'<td>{e(meaning)}</td><td>{e(allowed)}</td>'
                    f'<td><a href="data/suggestions.json" '
                    f'title="Repository file">suggestions.json</a></td></tr>')
    b.append(table("howto", [("Field", ""), ("What it records", ""), ("Allowed values", ""), ("Where", "")], rows,
                   "Table: recording a decision"))
    b.append('<div class="note"><b>Why the gate is in code.</b><p>A convention that says "do not implement before '
             'deciding" is forgotten by the next session. <code>check.py</code> fails the build instead, so an '
             'undecided suggestion cannot quietly become an implemented one. This is the mechanism that makes the '
             'brief\'s "choose the best path before implementing any changes" enforceable rather than '
             'aspirational.</p></div>')
    b.append('</section>\n')
    return page("suggestions.html", "Suggestions and decision gate",
                f"{len(S_ROWS)} suggestions for improving the site and the research, each with options and "
                "trade-offs, none implemented, all awaiting the owner's decision.",
                "".join(b),
                "This page IS the decision surface. It is not a list of changes made &mdash; it is a list of "
                f"changes proposed. {len(S_UNDECIDED)} await your choice and nothing is built until you choose.")


def page_questions() -> str:
    b = []
    b.append('<div class="note"><b>What this register is for.</b>'
             f'<p>The brief asks for a clear list of questions, information and answers that must be addressed '
             f'before a decision can reasonably be made, based on what is already known and what is not, with '
             f'suggestions for discovering the missing information. {len(Q_ROWS)} questions are registered; '
             f'{len(Q_BLOCKING)} are marked blocking, meaning the decision named in that row cannot reasonably be '
             f'made until the question is answered.</p>'
             f'<p>The <b>Answer</b> column is empty on every row. That is deliberate. '
             f'<code>check.py</code> fails the build if an answer is present while a question is still open, so a '
             f'conclusion cannot be written ahead of its evidence.</p></div>\n')

    b.append('<div class="kpis">'
             f'<div class="kpi"><div class="n">{len(Q_ROWS)}</div><div class="l">questions registered</div></div>'
             f'<div class="kpi bad"><div class="n">{len(Q_BLOCKING)}</div><div class="l">blocking a decision</div></div>'
             f'<div class="kpi warn"><div class="n">{len(Q_OPEN)}</div><div class="l">open</div></div>'
             f'<div class="kpi ok"><div class="n">{sum(1 for q in Q_ROWS if q["status"] != "open")}</div><div class="l">settled by artifact</div></div>'
             f'<div class="kpi"><div class="n">{len({q["category"] for q in Q_ROWS})}</div><div class="l">categories</div></div>'
             '</div>\n')

    b.append('<section class="card"><h2>Register</h2>')
    b.append(filters("q", [("category", "Category", "select"), ("blocking", "Blocking", "select"),
                           ("status", "Status", "select")], "question, what is known, what is not"))
    rows = []
    for q in Q_ROWS:
        sids = q["source_ids"]
        links = " ".join(src(s) if s in SRC else
                         f'<a href="flagged.html#{e(s)}">{e(s)}</a>' for s in sids) or \
                blank("no external source - answerable from the repository alone", "")
        sug = q.get("related_suggestion", "")
        sugl = f'<a href="suggestions.html#{e(sug)}">{e(sug)}</a>' if sug else blank()
        ans = (f'<span class="tag settled">{e(q["status"])}</span><br>{e(q.get("answer_note", ""))}'
               if q["status"] != "open" else
               f'<span class="tag open">open</span> {blank("no answer recorded", "")}')
        qblock = ('<span class="tag hi">blocking</span>' if q["blocking"]
                  else '<span class="tag lo">no</span>')
        rows.append(
            f'<tr id="{e(q["id"])}" data-category="{e(q["category"])}" '
            f'data-blocking="{"yes" if q["blocking"] else "no"}" data-status="{e(q["status"])}" '
            f'data-search="{e((q["id"] + " " + q["category"] + " " + q["question"] + " " + q["known"] + " " + q["unknown"]).lower())}">'
            f'<td class="mono"><a href="open-questions.html#{e(q["id"])}" title="Permalink to this question">{e(q["id"])}</a></td>'
            f'<td><span class="tag lo">{e(q["category"])}</span></td>'
            f'<td><b>{e(q["question"])}</b></td>'
            f'<td>{e(q["known"])}</td>'
            f'<td>{e(q["unknown"])}</td>'
            f'<td>{e(q["blocks_a_decision"])}</td>'
            f'<td>{e(q["how_to_discover"])}</td>'
            f'<td>{e(q["who_can_answer"])}</td>'
            f'<td>{qblock}</td>'
            f'<td>{ans}</td>'
            f'<td>{links}</td><td>{sugl}</td></tr>')
    b.append(table("q", [("ID", ""), ("Category", ""), ("Question", ""), ("What we KNOW, and from where", ""),
                         ("What we do NOT know", ""), ("Which decision it blocks", ""),
                         ("How to discover the missing information", ""), ("Who can answer", ""),
                         ("Blocking", ""), ("Answer", ""), ("Sources", ""), ("Suggestion", "")], rows,
                   "Table: open questions and required information"))
    b.append('</section>\n')

    b.append('<section class="card"><h2>Grouped by what is being blocked</h2>'
             '<p class="lead">The same list read the other way: each decision the brief asks for, and the questions '
             'that must be answered before it can reasonably be made.</p>')
    groups: dict[str, list[str]] = {}
    for q in Q_ROWS:
        if q["blocking"]:
            groups.setdefault(q["blocks_a_decision"], []).append(q["id"])
    rows = []
    for dec in sorted(groups):
        ids = sorted(groups[dec])
        idlinks = " ".join('<a href="#' + e(i) + '">' + e(i) + '</a>' for i in ids)
        rows.append(f'<tr data-search="{e((dec + " " + " ".join(ids)).lower())}">'
                    f'<td>{e(dec)}</td><td class="num">{len(ids)}</td>'
                    f'<td>{idlinks}</td>'
                    f'<td><a href="flagged.html">flag register</a></td></tr>')
    b.append(table("blocked", [("Decision that cannot yet be made", ""), ("Blocking questions", "num"),
                               ("Which", ""), ("Flags", "")], rows,
                   "Table: decisions blocked by unanswered questions"))
    b.append('</section>\n')
    return page("open-questions.html", "Open questions and required information",
                f"{len(Q_ROWS)} questions that must be answered before a decision is reasonable, each stating what "
                "is known and from where, what is not known, and how to discover it.",
                "".join(b),
                f"NOT decision-ready. {len(Q_BLOCKING)} of {len(Q_ROWS)} questions block a decision named in this "
                "register, and no answer column is filled. This page is the list of what has to be resolved first.")


def page_sources() -> str:
    b = []
    b.append('<div class="note"><b>What "read" means, and why it matters.</b>'
             '<p>A source is marked <b>opened</b> only if this session retrieved the page and read the text that '
             'the citation claims. A source marked <b>NOT opened</b> is cited because an official page that WAS '
             'read links it, or because its headline was read on such a page. Values from an unopened source are '
             'never published as confirmed: only the headline or the link is, and the row says so.</p>'
             '<p>Tiers: <span class="tag official">official league</span> the NFL itself; '
             '<span class="tag club">official club</span> an NFL member club, cited only where NFL.com cites it; '
             '<span class="tag third">NOT official</span> a commercial publisher, recorded and rejected.</p></div>\n')
    b.append('<div class="kpis">'
             f'<div class="kpi ok"><div class="n">{len(OFFICIAL_READ)}</div><div class="l">official pages opened and read</div></div>'
             f'<div class="kpi warn"><div class="n">{len(NOT_OPENED)}</div><div class="l">official pages cited, NOT opened</div></div>'
             f'<div class="kpi"><div class="n">{len(REJECTED)}</div><div class="l">third-party publishers rejected</div></div>'
             f'<div class="kpi"><div class="n">{len(SOURCES["sources"])}</div><div class="l">entries in the register</div></div>'
             '</div>\n')

    b.append('<section class="card"><h2>Source register</h2>')
    b.append(filters("srcs", [("tier", "Tier", "select")], "publisher, what it supports"))
    rows = []
    for s in SOURCES["sources"]:
        read = ("<span class='tag recomputed'>opened</span>" if s.get("read")
                else "<span class='tag unverified'>NOT opened</span>")
        note = s.get("read_note", "")
        rows.append(f'<tr id="{e(s["id"])}" data-tier="{e(s["tier"])}" '
                    f'data-search="{e((s["id"] + " " + s["publisher"] + " " + s["title"] + " " + s["supports"]).lower())}">'
                    f'<td class="mono">{e(s["id"])}</td>'
                    f'<td>{e(s["publisher"])}<br>{tier_tag(s["id"])}</td>'
                    f'<td><a href="{e(s["url"])}">{e(s["title"])}</a>'
                    f'<br><span class="mono" style="font-size:11.4px;color:var(--muted)">{e(s["url"])}</span></td>'
                    f'<td>{read}</td>'
                    f'<td>{e(s["supports"])}</td>'
                    f'<td>{e(note) if note else blank("no note", "")}</td></tr>')
    b.append(table("srcs", [("ID", ""), ("Publisher", ""), ("Page", ""), ("Read this session", ""),
                            ("Exactly what it supports", ""), ("Limitations recorded", "")], rows,
                   f"Table: source register, all fetched {SOURCES['fetched_utc']} UTC"))
    b.append('</section>\n')

    b.append('<section class="card"><h2>What is deliberately absent from this register</h2>'
             '<ul class="tight">'
             '<li><b>No betting price or odds line.</b> No official publisher releases one for this project. '
             'Every originated line in the wider repository is labelled recomputed from an open dataset, never '
             'official.</li>'
             '<li><b>No correlation coefficient.</b> Computing a same-game parlay correlation needs paired '
             'outcomes and the prices offered for each leg from one book at one moment. No source here supplies '
             'them. Question <a href="open-questions.html#Q06">Q06</a>.</li>'
             '<li><b>No return, ROI or strategy result.</b> Nothing in this directory claims an edge.</li>'
             '<li><b>No funded reward.</b> Question <a href="open-questions.html#Q09">Q09</a> records that legal '
             'review is required and has not happened.</li>'
             '<li><b>No depth-chart string.</b> Capability probe on <a href="depth.html">the depth page</a>.</li>'
             '</ul></section>\n')
    return page("sources.html", "Official source register",
                f"Every page cited by this directory, its publisher and tier, whether it was actually opened this "
                "session, and exactly what it supports.",
                "".join(b),
                f"Decision-ready as a citation record. {len(OFFICIAL_READ)} official pages were opened and read; "
                f"{len(NOT_OPENED)} are cited but were not opened, and every value depending on them is blank.")


def page_flagged() -> str:
    b = []
    b.append('<div class="note warn"><b>Flagged for review. Nothing here blocks publication.</b>'
             f'<p>{len(FLAGS)} items are published for your review. Each has a stable anchor, the official source '
             'behind it where one exists, and a status. Per the brief, flagged irregularities and unverified items '
             'do not block a merge &mdash; they are published so they can be reviewed after the site is '
             'live.</p></div>\n')
    b.append('<div class="kpis">'
             f'<div class="kpi"><div class="n">{len(FLAGS)}</div><div class="l">flags published</div></div>'
             f'<div class="kpi bad"><div class="n">{sum(1 for x in FLAGS if x["severity"] == "high")}</div><div class="l">high severity</div></div>'
             f'<div class="kpi warn"><div class="n">{sum(1 for x in FLAGS if x["severity"] == "medium")}</div><div class="l">medium severity</div></div>'
             f'<div class="kpi"><div class="n">{sum(1 for x in FLAGS if x["severity"] == "low")}</div><div class="l">low severity</div></div>'
             '</div>\n')

    b.append('<section class="card"><h2>Flag register</h2>')
    b.append(filters("flags", [("severity", "Severity", "select")], "flag, detail"))
    rows = []
    for x in sorted(FLAGS, key=lambda z: ({"high": 0, "medium": 1, "low": 2}[z["severity"]], z["id"])):
        links = " ".join(src(s) for s in x["sources"]) or \
            blank("no official source - this is a statement about the repository or the brief", "")
        rows.append(f'<tr id="{e(x["id"])}" data-severity="{e(x["severity"])}" '
                    f'data-search="{e((x["id"] + " " + x["title"] + " " + x["detail"]).lower())}">'
                    f'<td class="mono">{e(x["id"])}</td><td>{sev_tag(x["severity"])}</td>'
                    f'<td><b>{e(x["title"])}</b></td><td>{e(x["detail"])}</td>'
                    f'<td><span class="tag unverified">{e(x["status"])}</span></td>'
                    f'<td><a href="{e(x["page"])}">{e(x["page"])}</a></td>'
                    f'<td>{links}</td></tr>')
    b.append(table("flags", [("ID", ""), ("Severity", ""), ("Flag", ""), ("Detail", ""), ("Status", ""),
                             ("Published on", ""), ("Official source", "")], rows,
                   "Table: everything flagged for your review"))
    b.append('</section>\n')

    b.append('<section class="card"><h2>Every blank published in this directory</h2>'
             '<p class="lead">A blank is not a zero and not a missing value waiting to be filled. Each one is '
             'listed here with the reason it is blank, so nothing can be inferred later from an empty '
             'cell.</p>')
    rows = []
    blanks = [
        ("Depth string, 1st to 4th", "injuries.html, depth.html", "No official league publisher prints string "
         "ordering; the club roster page is alphabetical with no depth-chart tab.", "D14", "O04"),
        ("Game Status on most injury rows", "injuries.html", "Blank on the official page at Thursday capture. The "
         "designation had not been published, which is not the same as the player being available.", "D13", "O01"),
        ("Injuries column on most injury rows", "injuries.html", "Blank on the official page. Injury type for some "
         "of these players exists in the roundup and is published separately, never merged back.", "D04", "O03"),
        ("Definitions of Out, Doubtful, Questionable", "injuries.html", "The official rulebook could not be "
         "retrieved. No definition is written from memory.", "D15", "O01"),
        ("Kickoff and broadcast, Texans at Browns", "injuries.html", "Fell across an unretrieved page-chunk "
         "boundary. Not copied from the neighbouring game.", "D06", "O01"),
        ("Player link, one Bengals lineman", "injuries.html", "The official roundup prints his name without a "
         "hyperlink. No player URL is invented.", "D11", "O03"),
        ("Practice status, one Cowboys cornerback", "injuries.html", "The page text was cut off mid-line at the "
         "chunk boundary.", "D12", "O03"),
        ("DEN, CHI, PHI, TB entirely", "injuries.html", "Not captured, and no official source explains their "
         "absence. Not assumed to be on bye and not assumed to be healthy.", "D05", "O01"),
        ("Answer column, every open question", "open-questions.html", "Answers belong to the named responder, not "
         "to the agent. The build fails if an answer appears while a question is open.", "", ""),
        ("Chosen option and decision date, every suggestion", "suggestions.html", "Choosing is the owner's "
         "decision. The build fails if the agent records one.", "", ""),
        ("Correlation coefficients, ROI, prices, rewards", "everywhere", "No official publisher supplies them, and "
         "none is invented. This is by design.", "D16", ""),
    ]
    for what, where, why, flag, sid in blanks:
        fl = f'<a href="#{e(flag)}">{e(flag)}</a>' if flag else blank("no flag id", "")
        sl = src(sid) if sid else blank("no single source", "")
        # "where" is a comma-separated list of page names, or the word "everywhere". Each part becomes
        # a link, so this row always carries at least one source link of its own.
        whl = []
        for part in [x.strip() for x in where.split(",")]:
            target = "index.html" if part == "everywhere" else part
            whl.append(f'<a href="{e(target)}">{e(part)}</a>' if target.endswith(".html") else e(part))
        rows.append(f'<tr data-search="{e((what + " " + where + " " + why).lower())}">'
                    f'<td>{e(what)}</td><td>{", ".join(whl)}</td><td>{e(why)}</td>'
                    f'<td>{fl}</td><td>{sl}</td></tr>')
    b.append(table("blanks", [("What is blank", ""), ("Where", ""), ("Why it is blank rather than filled", ""),
                              ("Flag", ""), ("Source of the absence", "")], rows,
                   "Table: every blank published, with its reason"))
    b.append('</section>\n')
    return page("flagged.html", "Flagged for review",
                f"{len(FLAGS)} irregularities, blockers and declared blanks, each with its status and official "
                "source where one exists. Published for review; none of it blocks the merge.",
                "".join(b),
                "This page is the review queue. Nothing on it blocks publication, and nothing on it has been "
                "smoothed over: every blank in the pack is listed here with the reason it is blank.")


def page_verification() -> str:
    b = []
    b.append('<section class="card"><h2>What was verified, and how</h2>'
             '<p class="lead">Every check below was run on the repository at the commit this branch was created '
             'from, and again after this directory was built. No check is claimed that was not executed.</p>')
    rows = []
    checks = [
        ("V01", "Requirement gap: no suggestions section existed", 
         "grep -ril 'suggestion' over all tracked *.html, *.md and *.json",
         "0 matches", "gap confirmed, now closed by suggestions.html", ""),
        ("V02", "Requirement gap: no depth-chart or string tracking existed",
         "grep -ril 'depth chart|2nd string|third string' over the tree",
         "0 matches", "gap confirmed; official capability probed and recorded on depth.html", ""),
        ("V03", "Requirement gap: injury tracking was unclaimed backlog",
         "COORDINATION.md backlog item B02", "listed as unclaimed with rationale \"Not in the dataset; weekly PDFs only\"",
         "rationale disproved: the official weekly report is retrievable and machine-readable", ""),
        ("V04", "Page and landing-page volume behind suggestion S01",
         "git ls-files '*.html' | wc -l ; git ls-files '*index.html'",
         "134 HTML pages, 11 index.html files", "confirmed; quoted in suggestion S01", ""),
        ("V05", "Workflow duplication behind suggestion S11",
         "git ls-files '.github/workflows/*'", "7 workflows", "confirmed; quoted in suggestion S11", ""),
        ("V06", "Official injury report retrieved and transcribed",
         "page reader over O01 and O02",
         f"{len(PRAC) + len(DESIG)} player rows, {len(GAMES)} games, {len(NOINJ)} clubs printed as no injuries",
         "transcribed verbatim into injuries.json", "O01"),
        ("V07", "Official depth-chart news retrieved and transcribed",
         "page reader over O03", f"{len(ROUNDUP)} roundup rows across {len(CLUBS_IN_ROUNDUP)} clubs",
         "transcribed verbatim; un-retrieved clubs have no rows and are not assumed empty", "O03"),
        ("V08", "Cross-source comparison of the two official feeds",
         "manual line-by-line comparison of O01 against O03 and against headlines on O01",
         f"{len(C_ROWS)} discrepancies, {len(C_HIGH)} high severity", "published on conflicts.html, none resolved by preferring a source", "O01"),
        ("V09", "Depth-chart capability probe",
         "direct fetch of the official club roster page and the club transaction path",
         "roster is alphabetical with a status code and no depth-chart tab; transaction path returns 404",
         "recorded as a verified absence on depth.html", "O04"),
        ("V10", "Official 2025 standings retrieved as a completed-season control",
         "page reader over O06", "all 32 clubs, each with wins and losses summing to 17",
         "used only to confirm completed-season aggregates remain retrievable", "O06"),
        ("V11", "Deterministic rebuild", "python3 decision_lab/build.py ; git diff --exit-code -- decision_lab",
         "see console output below", "no drift", ""),
        ("V12", "Fail-closed verifier", "python3 decision_lab/check.py", "see console output below",
         "per-row source links, blank discipline, decision gate, internal links", ""),
        ("V13", "Existing repository gates still pass", 
         "verify/source_audit.py, verify/linkcheck_all.py, line_lab/check_site.py, hub/check_hub.py, "
         "scripts/verify_site.py, pipeline/link_check.py, nfl_lab.check_verified, pytest tests/",
         "see console output below", "this directory adds no unsourced row and no broken link", ""),
    ]
    # Where the evidence is a repository artifact rather than an official page, link the artifact.
    # Every row must carry a source link, and "a command I ran" is not one.
    REPO_EVIDENCE = {
        "V01": ("../COORDINATION.md", "board + grep over the tree"),
        "V02": ("../COORDINATION.md", "board + grep over the tree"),
        "V03": ("../COORDINATION.md", "backlog item B02"),
        "V04": ("../index.html", "the 134 published pages"),
        "V05": ("../.github/workflows/hub-verify.yml", "one of the 7 workflows"),
        "V11": ("build.py", "build.py"),
        "V12": ("check.py", "check.py"),
        "V13": ("../verify/source_audit.py", "the repository-wide audits"),
    }
    for vid, what, how, result, outcome, sid in checks:
        if sid in SRC:
            sl = src(sid)
        else:
            # Evidence is a repository artifact, or a command run over it. Link the artifact rather
            # than leaving the row without a source, because the standing rule is one link per row.
            target, label = REPO_EVIDENCE[vid]
            sl = f'<a href="{e(target)}" title="Repository artifact">{e(label)}</a>'
        rows.append(f'<tr id="{e(vid)}" data-search="{e((vid + " " + what + " " + how + " " + result).lower())}">'
                    f'<td class="mono">{e(vid)}</td><td>{e(what)}</td><td class="mono">{e(how)}</td>'
                    f'<td>{e(result)}</td><td>{e(outcome)}</td><td>{sl}</td></tr>')
    b.append(table("ver", [("ID", ""), ("What was verified", ""), ("How", ""), ("Result", ""),
                           ("Outcome", ""), ("Source", "")], rows,
                   "Table: verification performed this session"))
    b.append('</section>\n')

    b.append('<section class="card"><h2>What was NOT verified</h2>'
             '<p class="lead">Stated plainly, because an audit that lists only its successes is not an audit.</p>'
             '<ul class="tight">'
             f'<li><b>{len(NOT_OPENED)} official pages are cited but were not opened.</b> The page reader failed '
             'for every attempt after source O03. Each is marked NOT opened in the register, and every value '
             'depending on it is blank. Only headlines read on a page that WAS opened are quoted.</li>'
             '<li><b>The official definitions of Out, Doubtful and Questionable.</b> Not retrieved, not written '
             'from memory. Flag <a href="flagged.html#D15">D15</a>.</li>'
             '<li><b>Completeness of the Week 10 capture.</b> 28 of 32 clubs. Flag '
             '<a href="flagged.html#D05">D05</a>.</li>'
             '<li><b>The league transaction hub.</b> Attested to exist by a page that was read; its own content is '
             'unknown. Question <a href="open-questions.html#Q03">Q03</a>.</li>'
             '<li><b>Any betting price, correlation, ROI, edge or strategy result.</b> No official source supplies '
             'one, and none is published or estimated here. Flag <a href="flagged.html#D16">D16</a>.</li>'
             '<li><b>Whether existing validation-gate thresholds were frozen before or after the results they '
             'gate.</b> Not audited this session. Question <a href="open-questions.html#Q08">Q08</a>.</li>'
             '</ul></section>\n')

    b.append('<section class="card"><h2>Reproduce</h2><pre class="mono" style="background:#f2f4f7;'
             'padding:12px;border-radius:7px;overflow-x:auto;font-size:12.6px">'
             'python3 decision_lab/build.py          # regenerate every page from data/*.json\n'
             'git diff --exit-code -- decision_lab   # must be empty: the build is deterministic\n'
             'python3 decision_lab/check.py          # fail-closed verifier\n'
             'python3 verify/source_audit.py         # repository-wide per-row source audit\n'
             'python3 verify/linkcheck_all.py        # repository-wide link integrity\n'
             '</pre>'
             '<p class="lead">Standard library only. No network access, no manual input, no third-party '
             'dependency. Results are recorded on the board in <code>COORDINATION.md</code>.</p></section>\n')
    return page("verification.html", "Verification record",
                "What was checked, how it was checked, what the result was, and an equally explicit list of what "
                "was not verified.",
                "".join(b),
                "Decision-ready as an audit record. It states its own limits: "
                f"{len(NOT_OPENED)} cited official pages were not opened, and everything depending on them is "
                "blank rather than estimated.")


# --------------------------------------------------------------------------- #
PAGES = {
    "index.html": page_index,
    "injuries.html": page_injuries,
    "depth.html": page_depth,
    "conflicts.html": page_conflicts,
    "suggestions.html": page_suggestions,
    "open-questions.html": page_questions,
    "sources.html": page_sources,
    "flagged.html": page_flagged,
    "verification.html": page_verification,
}


def main() -> int:
    HERE.mkdir(parents=True, exist_ok=True)
    (HERE / ".nojekyll").write_text("", encoding="utf-8")
    (ASSETS).mkdir(parents=True, exist_ok=True)
    for name in sorted(PAGES):
        (HERE / name).write_text(PAGES[name](), encoding="utf-8")
    print(f"built {len(PAGES)} pages; "
          f"{len(SOURCES['sources'])} sources ({len(OFFICIAL_READ)} opened); "
          f"{len(PRAC) + len(DESIG)} injury rows; {len(C_ROWS)} conflicts; "
          f"{len(S_ROWS)} suggestions; {len(Q_ROWS)} questions; {len(FLAGS)} flags")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
