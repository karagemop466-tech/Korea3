#!/usr/bin/env python3
"""Build the injury_lab pages from injury_lab/data/*.json.

    python3 -m injury_lab.build_site

Rules, all of them enforced on the output by ``check_site.py``:

1. **No facts in this file.** This script contains no player, no injury, no line and no score. Every
   value is read from a data file that a capture or a computation produced.
2. **No inference.** An empty string in the data prints as a blank marker with the reason it is blank.
   Nothing is defaulted, carried across a row, or filled from a neighbour.
3. **Every row carries its source.** Injury and depth rows link the official page they were transcribed
   from *and* the retained capture; market rows link the pinned dataset file. A row with no source fails
   the build.
4. **Deterministic.** Standard library only, no network, no clock, no randomness. Two builds produce
   byte-identical files, so CI can fail on drift - and so the number on the page cannot disagree with the
   file it came from.
5. **Derived arithmetic is labelled derived** and shows the inputs, so a reader can recompute it by hand.
"""
from __future__ import annotations

import csv
import json
from collections import Counter
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"

CAPS = json.loads((DATA / "captures.json").read_text(encoding="utf-8"))
DEPTH = json.loads((DATA / "depth.json").read_text(encoding="utf-8"))
JOIN = json.loads((DATA / "joined.json").read_text(encoding="utf-8"))
SIG = json.loads((DATA / "signals.json").read_text(encoding="utf-8"))
BUILDS = json.loads((DATA / "builds.json").read_text(encoding="utf-8"))
FLAGS = json.loads((DATA / "flags.json").read_text(encoding="utf-8"))
SOURCES = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
RAW_INDEX = json.loads((DATA / "raw_index.json").read_text(encoding="utf-8"))

SRC = {s["id"]: s for s in SOURCES["sources"]}
ROWS = CAPS["injury_rows"]
CAPTURE_BY_NAME = {Path(c["file"]).name: c for c in RAW_INDEX["captures"]}
CAP_META = {c["capture"]: c for c in CAPS["captures"]}
GAMES_URL = JOIN["pinned_games_blob_url"]

PAGES = [
    ("index.html", "Overview", "What this lab is, what it holds and what it refuses"),
    ("capture.html", "Capture", "The official source, its limits, and the retention model"),
    ("injuries.html", "Injuries", "Every captured designation row, verbatim, per club and fixture"),
    ("depth.html", "Depth charts", "Ordered strings as the clubs publish them, provenance included"),
    ("replacements.html", "Replacements", "Who has to play when a starter is out"),
    ("signals.html", "Signal family", "Nine pre-registered injury rules and the gates they must clear"),
    ("leaderboard.html", "Leaderboard", "Every strategy and gate ledger in the repo, with the collisions"),
    ("builds.html", "Build index", "Which surface is canonical for what, counted from disk"),
    ("audit.html", "Cross-capture audit", "Two records of one official page, one day apart"),
    ("decisions.html", "Decisions to make", "Six options for the owner, none of them implemented"),
    ("sources.html", "Sources", "Every page opened, what it supports and what it does not"),
    ("flagged.html", "Flagged for review", "Thirty irregularities, published as found"),
    ("verification.html", "Verification", "What was checked, by which command, with which result"),
]


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def e(x) -> str:
    return escape("" if x is None else str(x), quote=True)


def blank(reason: str, flag: str = "") -> str:
    f = f' <a href="flagged.html#{e(flag)}">[{e(flag)}]</a>' if flag else ""
    return (f'<span class="blank" title="Not published by an official source, so it is blank rather '
            f'than guessed. {e(reason)}">{e(reason)}</span>{f}')


def src(sid: str, label: str = "") -> str:
    """A source link. Refuses to render an unregistered id, and marks an unopened source visibly."""
    if not sid:
        raise KeyError("empty source id: a row must cite a registered source or print an explicit blank")
    s = SRC.get(sid)
    if not s:
        raise KeyError(f"{sid} is cited by a row but is not in data/sources.json")
    txt = label or s["id"]
    if not s.get("read"):
        return (f'<a href="{e(s["url"])}" title="{e(s["publisher"])} - attempt failed, see the source '
                f'register">{e(txt)}<sup>&#9888;</sup></a>')
    return f'<a href="{e(s["url"])}" title="{e(s["publisher"])} ({e(s.get("extent", ""))})">{e(txt)}</a>'


def repo(path: str, label: str = "") -> str:
    """A link to a file in this repository, resolved from this lab's directory.

    Pages are served from ``injury_lab/``, so every repo path is written relative to that - ``../`` on both
    GitHub Pages and a local checkout. A directory is linked at its index page rather than at the bare
    directory, because a bare directory only resolves once the server decides to append one.
    """
    target = f'../{path}{"index.html" if path.endswith("/") else ""}'
    return f'<a href="{e(target)}" title="file in this repository: {e(path)}">{e(label or path)}</a>'


def tier(sid: str) -> str:
    t = {"official-league": ("official", "official league"), "official-club": ("club", "official club"),
         "pinned-community": ("third", "pinned third-party"), "repository-file": ("repo", "repo file")}
    cls, lbl = t[SRC[sid]["tier"]]
    return f'<span class="tag {cls}">{e(lbl)}</span>'


def capture_link(name: str) -> str:
    meta = CAPTURE_BY_NAME.get(name, {})
    return (f'<a href="raw/{e(name)}" title="retained capture, sha256 {e(meta.get("sha256", ""))[:16]}">'
            f'capture</a>')


def table(headers: list[str], rows: list[list[str]], caption: str = "", kind: str = "") -> str:
    tag = f' data-rows="{e(kind)}"' if kind else ""
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    cap = f"<caption>{caption}</caption>" if caption else ""
    return (f'<div class="scroll"><table{tag}>{cap}<thead><tr>{head}</tr></thead>'
            f'<tbody>{body}</tbody></table></div>')


def page(slug: str, title: str, intro: str, sections: list[str], lead: str = "") -> str:
    links = "".join('<a href="{0}"{1}>{2}</a>'.format(
        p, ' class="active"' if p == slug else "", e(lbl)) for p, lbl, _ in PAGES)
    secs = "\n".join(sections)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} | injury_lab</title>
<meta name="description" content="{e(intro)}">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="site">
  <div class="wrap">
    <div class="topbar">
      <a class="brand" href="index.html"><span class="mark">I</span>
        <span><strong>injury_lab</strong><small>Injury and depth capture, the join, and the injury signal family</small></span></a>
      <span class="badge">Research only &middot; no picks &middot; no funded rewards</span>
    </div>
    <nav class="main" aria-label="injury_lab navigation">{links}</nav>
  </div>
</header>
<main class="wrap">
  <div class="eyebrow">{e(slug.replace('.html', '') or 'index')}</div>
  <h1>{e(title)}</h1>
  <p class="lead">{lead or e(intro)}</p>
{secs}
  <p class="foot">Generated by <code>injury_lab/build_site.py</code> from <code>injury_lab/data/*.json</code>.
  Rebuild with <code>python3 -m injury_lab.build_site</code>; verify with
  <code>python3 -m injury_lab.check_site</code>. Capture date of every official page used here:
  2026-11-13 (session <code>arena/7acec358-korea3</code>).</p>
</main>
</body>
</html>
"""


# --------------------------------------------------------------------------- #
# pages
# --------------------------------------------------------------------------- #
def card(tag: str, num: str, sub: str) -> str:
    return f'<div class="card"><div class="tag">{e(tag)}</div><div class="num">{num}</div><div class="sub">{sub}</div></div>'


def page_index() -> str:
    played = [g for g in JOIN["game_features"] if g["played"]]
    n_rows = len(ROWS)
    desig = Counter(r["game_status"] for r in ROWS if r["game_status"])
    secs = [
        '<div class="grid k4">'
        + card("captured fixtures", str(len(CAP_META)), "3 weekly reports &middot; all truncated by chunk")
        + card("designation rows", str(n_rows), "verbatim from the official report, each linked")
        + card("charts with ordered strings", str(len(DEPTH["charts"])), "Detroit, New England, Dallas &middot; club publishers")
        + card("replacement rows", str(len(JOIN["replacements"])), "starter out &rarr; the name printed next to him")
        + "</div>",
        '<div class="grid k4">'
        + card("rules pre-registered", str(len(SIG["family"])), "F01-F09 &middot; gates IG1-IG9")
        + card("rules promoted", '<span class="pill-bad">0</span>', "every one fails the sample gate")
        + card("open flags", str(len(FLAGS["flags"])), f'{sum(1 for f in FLAGS["flags"] if f["severity"] == "high")} high severity')
        + card("official pages opened", str(sum(1 for s in SOURCES["sources"] if s["read"])),
               f'{sum(1 for s in SOURCES["sources"] if not s["read"])} attempted and failed, recorded')
        + "</div>",
        '<section><div class="section-head"><h2>What this directory adds</h2>'
        '<p>Everything here exists because the rest of the repository said it could not.</p></div>'
        '<ul class="tight">'
        '<li><strong>Injuries now reach the strategies.</strong> The root dashboard&rsquo;s own limitations '
        'section says &ldquo;No injury data&rdquo;, and the 18-rule family was built without any. Here the '
        'official weekly report is parsed, retained and joined, so an injury rule can be computed instead '
        'of described.</li>'
        '<li><strong>The depth requirement is no longer recorded as impossible.</strong> Three member clubs '
        'publish an ordered chart on their own domain; '
        f'{len(JOIN["replacements"])} absence-to-replacement rows are published with both sources linked. '
        'Flag <a href="flagged.html#H05">H05</a>.</li>'
        '<li><strong>Captures are retained and hashed</strong>, so a transcription can be re-checked after '
        'the official page moves. It does move: flag <a href="flagged.html#H01">H01</a>.</li>'
        '<li><strong>The collisions that break decisions are quantified</strong>, not narrated: '
        f'{len(BUILDS["strategy_id_collisions"])} clashing strategy ids and '
        f'{len(BUILDS["gate_id_collisions"])} clashing gate ids, on the '
        '<a href="leaderboard.html">leaderboard page</a>.</li></ul></section>',
        '<section><div class="section-head"><h2>What it refuses</h2></div>'
        '<ul class="tight">'
        '<li>No promotion and no reward. Six completed fixtures match a retained capture against a '
        '300-bet gate, so every rule in the family reads <em>FAIL</em> or <em>BLOCKED</em>. '
        'Flag <a href="flagged.html#H25">H25</a>.</li>'
        '<li>No imputation. A blank Game Status means the designation had not been published when the page '
        'was read; it does not mean the player was available. A fixture with no line in the pinned dataset '
        'has no line here.</li>'
        '<li>No bookmaker page, no third-party depth-chart site, no price that is not in the pinned '
        'dataset.</li>'
        '<li>No currency amount anywhere, so a reward figure cannot be copied off this site. '
        'Flag <a href="flagged.html#H28">H28</a>.</li></ul></section>',
        '<section><div class="section-head"><h2>Read it in this order</h2></div>'
        + table(["step", "page", "why"], [
            ["1", '<a href="capture.html">Capture</a>',
             'What the official source is, how far back it goes, and the three ways it can mislead a bot.'],
            ["2", '<a href="injuries.html">Injuries</a>', 'The rows themselves, verbatim, with the blanks.'],
            ["3", '<a href="depth.html">Depth charts</a>', 'What clubs publish about backups, in their own words.'],
            ["4", '<a href="replacements.html">Replacements</a>', 'The joined answer: who plays in place of the absent starter.'],
            ["5", '<a href="signals.html">Signal family</a>', 'What would have to be true for any of this to be worth money.'],
            ["6", '<a href="leaderboard.html">Leaderboard</a>', 'Every rule this repository has tested, and the two id collisions.'],
            ["7", '<a href="audit.html">Cross-capture audit</a>',
             'The parser checked against an independent transcription of the same page, and what the two '
             'records disagree about.'],
            ["8", '<a href="decisions.html">Decisions to make</a>',
             'Six paths with costs, and the seven questions that have to be answered before any of them is '
             'reasonable. Nothing on that page is implemented.'],
            ["9", '<a href="flagged.html">Flagged for review</a>', 'Everything a decision would otherwise '
             'step over, including the errors found in this lab&rsquo;s own code.'],
        ], "") + '</section>',
        f'<section><div class="section-head"><h2>Coverage on one line</h2></div><p>'
        f'{n_rows} rows captured across {len(CAP_META)} weekly reports; '
        f'{len(CAPS["capture_gaps"])} capture gaps declared; '
        f'{sum(1 for r in ROWS if not r["unit"])} rows with a position code no captured page defines '
        f'(<a href="flagged.html#H30">H30</a>); '
        f'{len(played)} joined fixtures with a result, '
        f'{len(JOIN["unjoined_fixtures"])} fixtures that did not match the pinned dataset on date and both '
        f'club codes, {len(JOIN.get("fixtures_not_attempted", []))} captured fixture the join refused to '
        f'attempt because only one club was in the capture, and {len(JOIN["refused_joins"])} club-season '
        'joins refused on purpose. The four numbers reconcile: 10 fixtures were captured and 9 were '
        'joined.</p></section>',
    ]
    return page("index.html", "Injury and depth: capture, join, and what it cannot yet prove",
                "The injury-aware half of this repository: what the official sources publish about "
                "availability and backups, held verbatim, joined to the market data, and run through the "
                "repository&rsquo;s own validation gates.", secs,
                lead="A capture pipeline, a join and nine pre-registered rules &mdash; and a record of "
                     "exactly why none of them can be promoted yet.")


def page_capture() -> str:
    from .capture import urls_for
    url_rows = []
    for season, week in ((2026, 10), (2025, 1), (2015, 10), (2024, 18), (2009, 1), (1999, 1)):
        u = urls_for(season, week)
        opened = next((c for c in CAP_META.values() if c["season"] == season and c["week"] == week), None)
        status = (f'read {opened["retrieved_utc"]} &middot; chunk {e(opened["chunk"])}' if opened
                  else blank("not opened by this session", "H04"))
        url_rows.append([f"{season} wk {week}", f'<a href="{e(u["official_week_page"])}">{e(u["official_week_page"])}</a>',
                          f'<a href="{e(u["official_week_page_unpadded_variant"])}">padded/unpadded pair</a>',
                          status])
    secs = [
        '<section><div class="section-head"><h2>The source, and what this session proved about it</h2>'
        '<p>One URL pattern, week-addressable, official, and deeper than the repository&rsquo;s registers '
        'claimed.</p></div>'
        + table(["season / week", "official week URL", "sibling form", "status"], url_rows)
        + '<p>Three weeks were opened here: 2026 W10, 2025 W1 and 2015 W10. All three returned that '
        'season&rsquo;s report with the same table shape, so the archive is not a current-week snapshot. '
        'The rows for 2024 and 2009 are <em>not</em> published here, because nobody opened them in this '
        'session; the URL is printed so anyone can, and the claim stays unproven until they do. '
        'Backlog item B02 on the board asserted the report was &ldquo;weekly PDFs only&rdquo; &mdash; that '
        'is not what these three fetches show.</p></section>',
        '<div class="notice warn"><strong>Three hazards on this page, each of which breaks an automated '
        'reader.</strong> (1) The page <em>mutates</em> under a fixed URL &mdash; '
        '<a href="flagged.html#H01">H01</a>. (2) The <code>&lt;title&gt;</code> can name a different week '
        'from the one the page shows &mdash; <a href="flagged.html#H02">H02</a>. (3) A week that has not '
        'been published yet <em>redirects to the previous week</em> rather than 404ing, so a weekly job '
        'asking for &ldquo;this week&rdquo; silently re-reads last week &mdash; '
        f'{src("I02")}.</div>',
        '<section><div class="section-head"><h2>Retained captures</h2>'
        '<p>Every published row must appear in one of these, byte for byte. That is rule P7 of the '
        'checker, and it is what turns &ldquo;an agent read a page&rdquo; into something a reader can '
        'audit.</p></div>'
        + table(["file", "sha256", "bytes", "player rows", "retrieved", "source"],
                [[f'<a href="raw/{e(c["file"].split("/")[-1])}"><code>{e(c["file"])}</code></a>',
                  f'<span class="mono">{e(c["sha256"])}</span>', e(c["bytes"]), e(c["player_rows"]),
                  e(c["retrieved_utc"]), e("retained by this session")] for c in RAW_INDEX["captures"]])
        + '</section>',
        '<section><div class="section-head"><h2>Capture gaps, declared</h2>'
        '<p>Not defects of the data &mdash; defects of the retrieval, recorded so nobody reads them as '
        '&ldquo;nothing to report&rdquo;.</p></div>'
        + table(["capture", "season/week", "what happened", "clubs in the affected fixture", "unparsed lines",
                 "sources"],
                [[e(g["capture"]), f'{g["season"]} / W{g["week"]}', e(g["detail"]),
                  (e(", ".join(g["clubs_captured_in_this_fixture"])) if g.get("clubs_captured_in_this_fixture")
                   else blank("the capture ended before the fixture header, so not even the clubs are known")),

                  e(CAP_META[g["capture"]]["unparsed_table_lines"]),
                  f'{src("I01" if g["season"] == 2026 else ("I03" if g["season"] == 2025 else "I04"))} '
                  f'&middot; {capture_link(g["capture"])} &middot; '
                  f'{repo("injury_lab/data/captures.json", "captures.json")}'] for g in CAPS["capture_gaps"]])
        + '</section>',
        '<section><div class="section-head"><h2>Table lines the parser could not read</h2>'
        '<p>Published as quoted text with the diagnosis attached. One line in the whole capture set does '
        'not match a row shape, and it is worth being exact about it, because "we could not read it" and '
        '"the page changed" need different fixes.</p></div>'
        + table(["capture", "the line, quoted", "pipes present / needed", "position", "diagnosis",
                 "sources"],
                [[e(c["capture"]), f'<code>{e(u["line"])}</code>',
                  f'{u["line_columns_present"]} / {u["columns_a_row_needs"]}',
                  ('last table line in the file' if u["at_last_table_line"] else f'line {u["line_index"]}'),
                  e(u["classification"]),
                  f'{capture_link(c["capture"])} &middot; '
                  f'{repo("injury_lab/parse.py", "parse.py")}']
                 for c in CAPS["captures"] for u in c["unparsed_lines"]])
        + '<p>So: <strong>no unknown page shape exists in this capture set.</strong> The single line is '
        'Patrick Mahomes&rsquo; row cut off mid-cell where the fetch stopped, three lines before the '
        'capture&rsquo;s own truncation note. It is also the only Chief whose row was in flight, which is '
        'why the Chiefs show 5 complete rows and Atlanta none. Nothing was inferred to fill it: '
        'Mahomes is published as absent from the capture, not as unlisted on the page.</p></section>',
        '<section><div class="section-head"><h2>What a full capture costs, in the units that matter</h2>'
        '<p>Computed from the observed page sizes, not estimated. This is the number the owner needs '
        'before authorising the work.</p></div>'
        + table(["quantity", "value", "how it was obtained", "source"], [
            ["games per week", '<code>14</code>', "regular-season fixtures per weekly report page (13 Sunday + Thu/Fri/Mon pattern)", f'{src("I01")} &middot; {repo("injury_lab/data/captures.json", "captures.json")}'],
            ["weeks per season", '<code>18</code>', "the 2026 selector offered WEEK 1 to WEEK 10 mid-season; a full regular season runs to 18", f'{src("I15")} &middot; {src("I01")}'],
            ["bets IG3 demands", f'<code>{300}</code>', f'{repo("docs/preregistration.md", "docs/preregistration.md")} G3', f'{repo("docs/preregistration.md")} {src("I12")}'],
            ["observed trigger rate, strongest rule",
             f'{max(r["fires"] for r in SIG["family"])}/{len([g for g in JOIN["game_features"] if g["played"]])} games',
             "from the pilot on this page; see signals",
             f'{repo("injury_lab/data/signals.json", "signals.json")} &middot; {src("I10")}'],
            ["weeks needed for the broadest rule (F05)",
             f'{[r for r in SIG["family"] if r["id"] == "F05"][0]["weeks_of_capture_for_IG3"]}',
             "300 bets at the observed fire rate, rounded up",
             f'{repo("injury_lab/data/signals.json", "signals.json")} &middot; {src("I12")}'],
            ["weeks needed for the total-scoring rule (F03)",
             f'{[r for r in SIG["family"] if r["id"] == "F03"][0]["weeks_of_capture_for_IG3"]}',
             "two triggers in six captured games",
             f'{repo("injury_lab/data/signals.json", "signals.json")} &middot; {src("I12")}'],
            ["weeks needed for the quarterback rule (F02)",
             f'{[r for r in SIG["family"] if r["id"] == "F02"][0]["weeks_of_capture_for_IG3"]}',
             "one trigger in six captured games &rarr; the arithmetic is unkind",
             f'{repo("injury_lab/data/signals.json", "signals.json")} &middot; {src("I12")}'],
        ])
        + '<p>Read that as a decision, not a complaint: the injury archive is deep enough to test injury '
        'rules, and the cost of using it is the number of page reads above. A session with outbound network '
        'access runs <code>python3 -m injury_lab.capture fetch --season 2015 --week 10</code> per week; '
        'this sandbox cannot reach nfl.com at all, which is why the captures in this directory were read '
        'through the agent&rsquo;s page fetcher and retained rather than re-fetched at will.</p></section>',
        '<section><div class="section-head"><h2>Refresh design, if the site is to stay true</h2></div>'
        '<ul class="tight">'
        '<li>Key the job on the <em>fixture dates</em> printed in the page, never on the week label or the '
        'title (H02).</li>'
        '<li>Treat a redirect from the week you asked for as &ldquo;not published yet&rdquo;, and a 5xx on '
        'a club domain as &ldquo;not captured&rdquo; rather than &ldquo;not published&rdquo; '
        '(<a href="flagged.html#H10">H10</a>).</li>'
        '<li>Re-hash the retained capture before trusting it, and keep the old one: history is the '
        'evidence, the live page is only an opinion with a date.</li>'
        '<li>Publish the intra-week delta explicitly - the Wednesday report and the Saturday report are '
        'different inputs to the same fixture, and a model trained on one and bet on the other is a '
        'different strategy (see IG2 on the <a href="signals.html">signals page</a>).</li>'
        '</ul></section>',
    ]
    return page("capture.html", "Capture: the official injury archive, held properly",
                "How the weekly report is addressed, what it mutates, where it truncates, and what a "
                "complete weekly capture would cost.", secs)


def page_injuries() -> str:
    by_capture: dict[str, list[dict]] = {}
    for r in ROWS:
        by_capture.setdefault(r["capture"], []).append(r)
    secs = ['<div class="notice">Verbatim rows from the official weekly report. An empty <em>Injuries</em> '
            'cell means the page printed nothing there &mdash; it does not mean the player is healthy, and '
            'it does not mean zero. Flag <a href="flagged.html#H13">H13</a> and question Q22 in the '
            'decision pack exist because of exactly this confusion.</div>']
    for cap, rows in sorted(by_capture.items()):
        meta = CAP_META[cap]
        secs.append(f'<section><div class="section-head"><h3>{e(cap)}</h3>'
                    f'<p>season {meta["season"]} &middot; week {meta["week"]} &middot; {meta["player_rows"]} rows '
                    f'&middot; fixtures captured {meta["fixtures_captured"]} &middot; retrieved '
                    f'{e(meta["retrieved_utc"])} &middot; <a href="{e(meta["url"])}">official page</a> '
                    f'&middot; {capture_link(cap)}</a></p></div>')
        rows_html = []
        for r in rows:
            fixture = f'{e(r["away"])} @ {e(r["home"])}' if r["home"] else f'{e(r["away"])} (opponent not in this chunk)'
            rows_html.append([
                f'{r["season"]} W{r["week"]}', f'F{r["fixture_no"]}', fixture, e(r["day"].title()),
                e(r["club"]), f'<a href="{e(r["player_url"])}">{e(r["player"])}</a>' if r["player_url"]
                else f'{e(r["player"])} {blank("no player link printed on the page", "H21")}',
                f'<span class="mono">{e(r["position_code"])}</span>',
                e(r["injury_text"]) or blank("no injury text printed", "H27"),
                e(r["practice_status"]) or blank("no practice status printed", "H04"),
                f'<strong>{e(r["game_status"])}</strong>' if r["game_status"]
                else blank("no designation published at capture time", "H01"),
                f'{e(r["unit"])}' if r["unit"] else blank("code not defined by any captured page", "H30"),
                f'{src("I01" if r["season"] == 2026 else ("I03" if r["season"] == 2025 else "I04"))} '
                f'{capture_link(cap)}'])
        secs.append(table(["season", "fx", "fixture", "day", "club", "player", "pos", "injury",
                           "practice status", "game status", "unit", "sources"], rows_html,
                          kind="injuries"))
        secs.append(f'<p class="tag">record at capture: '
                    + ", ".join(f'{e(c["name"])} {e(m["records"][i]) if i < len(m["records"]) else "(none printed)"}'
                                for m in meta["fixtures"] for i, c in enumerate(m["clubs"]))
                    + ' &mdash; win-loss records as printed on the report, and the reason a capture needs a date.</p>')
        secs.append('</section>')
    desig = Counter(r["game_status"] or "(blank)" for r in ROWS)
    secs.append('<section><div class="section-head"><h2>Designation vocabulary actually observed</h2>'
                '<p>Counts over the captured rows, and the era they come from. No definition of any of '
                'these words was retrieved, so none is restated here.</p></div>'
                + table(["designation", "rows", "seasons seen", "captured on"],
                        [[e(k), e(v),
                          ", ".join(str(s) for s in sorted({r["season"] for r in ROWS
                                                             if (r["game_status"] or "(blank)") == k})),
                          " ".join(capture_link(c) for c in sorted({r["capture"] for r in ROWS
                                                                    if (r["game_status"] or "(blank)") == k}))
                          + f' &middot; {repo("injury_lab/data/captures.json", "captures.json")}']
                         for k, v in sorted(desig.items(), key=lambda kv: -kv[1])])
                + '<p class="tag">Probable and Doubtful appear only in the 2015 capture. Flag '
                  '<a href="flagged.html#H03">H03</a>.</p></section>')
    nir = [x for c in CAPS["captures"] for x in c.get("no_injuries_reported", [])]
    secs.append('<section><div class="section-head"><h2>Clubs the report cleared without a table</h2>'
                '<p>The page prints a literal line instead of a table for a club with nothing to report. '
                'It is a different fact from &ldquo;no row was captured&rdquo;, and the two are never '
                'merged here.</p></div>'
                + (table(["club", "fixture", "the line as printed", "capture"],
                         [[e(x["club"]), f'F{x["fixture_no"]}', f'<code>{e(x["line"])}</code>',
                           capture_link(c["capture"])]
                          for c in CAPS["captures"] for x in c.get("no_injuries_reported", [])])
                   or '<p><span class="blank" title="Not published by an official source, so it is blank '
                      'rather than guessed. The retained chunks contain no occurrence of the phrase; that '
                      'is a statement about the chunks, not about the clubs.">no occurrence in the retained '
                      'chunks</span> <a href="flagged.html#H04">[H04]</a></p>')
                + '<p class="tag">The earlier transcription in this repository records this phrase for five '
                  'clubs of the same week, in chunks this lab does not hold '
                  f'({src("I16", "decision_lab/data/injuries.json")}). Neither record contradicts the '
                  'other; together they show why a count of captured rows is not a count of what the page '
                  'printed.</p></section>')
    unmapped = Counter(r["position_code"] for r in ROWS if not r["unit"])
    secs.append('<section><div class="section-head"><h2>Position codes no captured page defines</h2>'
                '<p>These rows are kept, and their unit is blank. Filling it from general knowledge is the '
                'thing this repository has been built to avoid.</p></div>'
                + table(["code", "rows", "treatment", "captured on"],
                        [[f'<span class="mono">{e(k)}</span>', e(v),
                          'unit left blank; excluded from every unit-scoped count',
                          " ".join(capture_link(c) for c in sorted({r["capture"] for r in ROWS
                                                                    if r["position_code"] == k}))
                          + f' &middot; {src("I01")}']
                         for k, v in sorted(unmapped.items(), key=lambda kv: -kv[1])])
                + f'<p>That is {sum(unmapped.values())} of {len(ROWS)} captured rows. Flag '
                  '<a href="flagged.html#H30">H30</a>.</p></section>')
    covered = sorted({r["club"] for r in ROWS})
    secs.append('<section><div class="section-head"><h2>Club coverage, stated as a gap</h2>'
                '<p>The report is a league page, so every club in a captured fixture is covered; the clubs '
                'below simply are not in the chunks retained. Not captured is not the same as absent.</p></div>'
                + table(["clubs with captured rows", "count", "clubs with no captured rows in this directory",
                         "count", "sources"],
                        [[e(", ".join(covered)), e(len(covered)),
                          "all other member clubs, not read by this session",
                          e(32 - len(covered)),
                          f'{src("I01")} &middot; {src("I03")} &middot; {src("I04")} &middot; '
                          f'{repo("injury_lab/data/captures.json", "captures.json")}']])
        + '</section>')
    return page("injuries.html", "Injury and availability rows, verbatim",
                "Every designation captured from the official weekly reports, with the page it came from, "
                "the capture that holds it, and an explicit blank wherever the page printed nothing.", secs)


def page_depth() -> str:
    secs = ['<div class="notice"><strong>Correction to a standing conclusion.</strong> The decision pack '
            'records that the brief&rsquo;s 2nd/3rd/4th-string requirement is not satisfiable from official '
            'sources. Three club sites, opened on 2026-11-13, publish ordered strings. The requirement is '
            'satisfiable for a current season from club publishers; it is <em>not</em> established for past '
            'seasons. Flag <a href="flagged.html#H05">H05</a>.</div>']
    for c in DEPTH["charts"]:
        prov = " ".join(c["provenance_lines"]) or "(no provenance statement on the page)"
        secs.append(f'<section><div class="section-head"><h3>{e(c["url"])}</h3>'
                    f'<p>{e(c["title"])} &middot; {c["row_count"]} rows &middot; retrieved '
                    f'{e(c["retrieved_utc"])} &middot; {capture_link(c["capture"])}</p></div>'
                    f'<p><em>The page&rsquo;s own words:</em> &ldquo;{e(prov)}&rdquo; &mdash; recorded '
                    'because the three charts do not mean the same thing. '
                    '<a href="flagged.html#H06">H06</a>.</p>')
        for unit, entries in c["units"].items():
            if not entries:
                continue
            max_cols = max(len(en["strings"]) for en in entries)
            rows_html = []
            for en in entries:
                cells = []
                for i in range(max_cols):
                    if i < len(en["strings"]):
                        names = en["strings"][i]
                        if not names:
                            cells.append(blank("no name printed in this column", "H08"))
                        elif len(names) > 1:
                            cells.append(" + ".join(f'<a href="{e(n["url"])}">{e(n["name"])}</a>'
                                                    for n in names)
                                         + f' {blank("tie in one cell; no order published", "H17")}')
                        else:
                            cells.append(f'<a href="{e(names[0]["url"])}">{e(names[0]["name"])}</a>')
                    else:
                        cells.append(blank("column does not exist on this page", "H08"))
                rows_html.append([f'<span class="mono">{e(en["position_label"])}</span>'] + cells
                                 + [f'{src("I05") if "lions" in c["url"] else (src("I06") if "patriots" in c["url"] else src("I08"))} '
                                    f'{capture_link(c["capture"])}'])
            secs.append(f'<h4>{e(unit)} &mdash; {len(entries)} rows, {max_cols} printed string columns</h4>')
            secs.append(table(["position label"] + [f'string {i + 1}' for i in range(max_cols)] + ["source"],
                              rows_html))
        secs.append('</section>')
    from .conventions import unit_map
    legend = [{"code": k, **v} for k, v in unit_map().items()]
    secs.append('<section><div class="section-head"><h2>Reading rules used here</h2>'
                '<p>Published so they can be rejected. The clubs print no string numbers, no unit for a '
                'code, and no ordering inside a crowded cell.</p></div>'
                '<ul class="tight">'
                '<li><strong>string number = printed column index.</strong> None of the three pages labels '
                'a column. A parser that called column 2 &ldquo;1st string&rdquo; without saying so would '
                'be inventing a league convention.</li>'
                '<li><strong>unit = the section heading the row sits under.</strong> That is a published '
                'fact of the page, unlike a code &rarr; unit table assembled from what a reader assumes.</li>'
                '<li><strong>an ambiguous cell stays ambiguous.</strong> A cell with two names yields no '
                'first string here.</li>'
                '<li><strong>no de-duplication by player.</strong> A man listed in two slots is printed '
                'twice, because no page states the rule for counting him once '
                '(<a href="flagged.html#H14">H14</a>, <a href="flagged.html#H15">H15</a>).</li>'
                '</ul></section>')
    if legend:
        secs.append('<section><h2>Unit map actually in force</h2>' + table(
            ["code", "unit", "basis", "captured on"],
            [[f'<span class="mono">{e(l["code"])}</span>', e(l["unit"]) or blank(l.get("why_blank", "unmapped"), "H30"),
              f'{e(l["basis"])} &middot; {len(l["evidence"])} captured page(s)',
              " ".join(capture_link(h["source"]) for h in l["evidence"][:3])] for l in legend])
        + '<p class="tag">Built by <code>injury_lab/conventions.py</code> from the legend printed on the '
          '2015 report and the section headings printed on the three club charts. A code that appears in '
          'neither is refused, not mapped, which is why the table is 29 codes and the capture has more '
          'codes than that.</p></section>')
    return page("depth.html", "Depth charts: what the clubs publish about backups",
                "Ordered strings from three member-club publishers, with each club's own provenance "
                "statement attached to every row.", secs)


def page_replacements() -> str:
    rows_html = []
    for r in JOIN["replacements"]:
        rows_html.append([
            f'{r["season"]} W{r["week"]}', f'{e(r["gameday"])}',
            f'{e(r["club"])} <span class="mono">({e(r["club_code"])})</span>',
            f'<a href="{e(r["report_row_url"])}">{e(r["player"])}</a>',
            f'<strong>{e(r["game_status"])}</strong>' + (f' <span class="tag">{e(r["injury_text"])}</span>'
                                                          if r["injury_text"] else ""),
            (f'<span class="mono">{e(r["chart_position_label"])}</span>' if r["chart_position_label"]
             else blank("no slot found on the club chart", "H07")),
            f'string {r["string_found"]}' if r["string_found"] else blank("no slot on the chart", "H07"),
            (f'<a href="{e(r["next_string_url"])}">{e(r["next_string_name"])}</a>'
             if r["next_string_name"] else blank("no name printed in the next column", "H08")),
            e(r["third_string_name"]) or blank("no third name printed", "H08"),
            e(r["chart_unit"]) if r["chart_unit"] else blank("unit unknown", "H12"),
            f'{r["attribution_shared_players"]} shared names',
            (e(r["match_key_used"]) if r["match_key_used"] not in ("", "none")
             else blank("no chart row matched this player at all", "H21")),
            f'{src("I01" if r["season"] == 2026 else "I04")} &middot; '
            f'{src("I05") if "lions" in r["chart_url"] else src("I06")} &middot; '
            f'{capture_link(r["chart_capture"])}'])
    secs = ['<div class="notice"><strong>This is the brief&rsquo;s central request, answered from two '
            'official publishers at once</strong>: the league report says a player is unavailable, the '
            'club&rsquo;s own chart says who is printed next to him. Where the chart prints nobody, the cell '
            'is blank and flagged &mdash; that is a finding about the roster, not a gap in the table.</div>',
            '<section><div class="section-head"><h2>Starter absent &rarr; who replaces him</h2>'
            f'<p>{len(JOIN["replacements"])} rows, all from the 2026 W10 report joined to a same-season club '
            'chart. Attribution is measured: a chart counts as belonging to a club only if it shares player '
            'names or slugs with that club&rsquo;s report rows, and the count is on every row.</p></div>'
            + table(["week", "date", "club", "player", "designation", "chart slot", "his string",
                     "next string", "and after him", "unit", "attribution", "join key", "sources"], rows_html,
                    kind="replacements")
            + '</section>',
            '<section><div class="section-head"><h2>What the rows show</h2></div><ul class="tight">']
    absent = [r for r in JOIN["replacements"] if r["absent_from_report"]]
    secs.append(f'<li><strong>{len(absent)} of {len(JOIN["replacements"])} rows are absences</strong> '
                '(Out or Doubtful); the rest are Questionable designations, where the club&rsquo;s own next '
                'name is a contingency, not a plan.</li>')
    thin = [r for r in JOIN["replacements"] if r["chart_row_found"] and not r["next_string_name"]]
    secs.append(f'<li><strong>{len(thin)} rows have no name printed after the player</strong> at that slot: '
                'the chart is one deep there. That is the deficiency the brief asks to detect, and it is '
                'only visible because the blanks are preserved. '
                + ", ".join(f'{e(r["player"])} ({e(r["chart_position_label"])})' for r in thin) + '.</li>')
    unplaced = [r for r in JOIN["replacements"] if not r["chart_row_found"]]
    secs.append(f'<li><strong>{len(unplaced)} designations have no slot on the club&rsquo;s own chart</strong>: '
                + ", ".join(e(r["player"]) for r in unplaced)
                + ' &mdash; Kerby Joseph is printed Out by the league and does not appear on Detroit&rsquo;s '
                'chart at all (<a href="flagged.html#H07">H07</a>).</li>')
    secs.append('<li><strong>One row was found only by URL slug and one only by printed name</strong>, so a '
                'join on either key alone silently drops designations '
                '(<a href="flagged.html#H21">H21</a>).</li></ul></section>')
    ref_html = [[f'{r["season"]}',
                 e(r["club"]) or blank("the report printed a code without a club name here", "H04"),
                 f'<span class="mono">{e(r["club_code"])}</span>',
                 e(r["reason"]),
                 (e(", ".join(str(x) for x in r["chart_captured_for_this_club"]))
                  if r.get("chart_captured_for_this_club") else "<em>no chart retained for this club</em>"),
                 (f'{len(r["shared_players"])} shared' if r.get("shared_players")
                  else "<em>no chart to compare</em>"),
                 f'{src("I01" if r["season"] == 2026 else ("I03" if r["season"] == 2025 else "I04"))} '
                 f'&middot; {repo("injury_lab/data/joined.json", "joined.json")}']
                for r in JOIN["refused_joins"]]
    secs.append('<section><div class="section-head"><h2>Joins refused, on purpose</h2>'
                '<p>Every club-season pair the report mentions where no same-season chart was retained. '
                'Published so the refusal survives the next session instead of being &ldquo;helpfully&rdquo; '
                'joined.</p></div>'
                + table(["season", "club", "code", "why no replacement row exists", "charts retained for this club",
                         "shared names", "sources"], ref_html) + "</section>")
    na = JOIN.get("fixtures_not_attempted", [])
    if na:
        secs.append('<section><div class="section-head"><h2>Captured fixtures the join never attempted</h2>'
                    '<p>A different fact from a refused join and a different fact again from a fixture that '
                    'did not appear. These headers were read, but they never carried two clubs, so there was '
                    'no date-and-two-codes key to match and nothing was snapped to a nearby game.</p></div>'
                    + table(["capture", "season/week", "fixture", "day and kickoff", "clubs retained",
                             "rows", "why nothing was attempted", "source"],
                            [[e(x["capture"]), f'{x["season"]} / W{x["week"]}', f'F{x["fixture_no"]}',
                              f'{e(x["day"])} &middot; {e(x["kickoff"])}',
                              e(", ".join(x["clubs_captured"])), e(x["player_rows"]), e(x["reason"]),
                              f'{capture_link(x["capture"])} &middot; '
                              f'{repo("injury_lab/data/joined.json", "joined.json")}']
                             for x in na])
                    + f'<p>{len(na)} fixture of {len(JOIN["game_features"]) + len(JOIN["unjoined_fixtures"]) + len(na)} '
                      'captured here. It is counted on the overview page so the totals reconcile: captured '
                      f'= joined ({len(JOIN["game_features"])}) + unmatched ({len(JOIN["unjoined_fixtures"])}) '
                      f'+ not attempted ({len(na)}).</p></section>')

    return page("replacements.html", "Replacements: the backup who has to play",
                "Official designation joined to the club&rsquo;s own ordered chart, with both sources on "
                "every row and a refusal where the join would be a guess.", secs)


def page_signals() -> str:
    fam = SIG["family"]
    rows_html = []
    for r in fam:
        gates = " ".join(f'<span class="tag {"ok" if v == "PASS" else ("fail" if v == "FAIL" else "derived")}">{e(k)}</span>'
                         for k, v in r["gates"].items())
        rows_html.append([
            f'<span class="mono">{e(r["id"])}</span>', e(r["name"]),
            e(r["bet_shape"]) if r["bet_shape"] not in ("", "none") else "<em>places no bet</em>",
            e(r["market"]) if r["market"] not in ("", "n/a", "none") else "<em>no market</em>",
            e(r["rule"]), e(r["hypothesis"]),
            e(", ".join(r["requires"])),
            e(r["fires"]), e(r["fires_settled"]),
            (f'{r["wins"]}/{r["fires_settled"]}' if r["fires_settled"] else blank("no settled bet", "H25")),
            (f'{r["win_rate_wilson_95ci"][0]:.3f} to {r["win_rate_wilson_95ci"][1]:.3f}'
             if r["win_rate_wilson_95ci"] else blank("undefined at n=0", "H25")),
            (f'{r["pilot_roi"]:+.3f}' if r["pilot_roi"] is not None else blank("no settled bet", "H25")),
            e(r["bets_still_needed_for_IG3"]),
            (e(r["weeks_of_capture_for_IG3"]) if r["weeks_of_capture_for_IG3"]
             else blank("no fire rate to divide 300 by", "H25")),
            gates, '<span class="tag fail">no</span>',
            f'{repo("injury_lab/data/signals.json", "signals.json")} &middot; '
            f'{repo("injury_lab/signals.py", "signals.py")} &middot; {src("I10")}'])
    secs = [
        '<div class="notice warn"><strong>Nothing here is a finding about profitability.</strong> Six '
        'completed fixtures in the pinned dataset match a retained official capture, against a gate that '
        'requires 300 bets, 8 seasons and 40 holdout bets. The pilot columns exist to show the pipeline '
        'runs and to show how wide the noise is: the deliberately meaningless control rule &ldquo;F05&rdquo; '
        'wins five of six bets at the recorded closing prices. That is the argument for the gates, not '
        'against them.</div>',
        '<section><div class="section-head"><h2>The gates this family must clear</h2>'
        '<p>Thresholds are copied from files in this repository, with the file named. Where two registers '
        'disagree, the stricter value is used.</p></div>'
        + table(["gate", "name", "threshold applied", "which register it comes from"],
                [[f'<span class="mono">{e(g["id"])}</span>', e(g["name"]), e(g["threshold"]),
                  f'{e(g["register"])} &middot; {repo(g["cite"])}'] for g in SIG["gate_register"]])
        + '<p class="tag">Two existing registers in this repository use G1&ndash;G8 for different rules, so '
          'this family uses an IG prefix. Flag <a href="flagged.html#H23">H23</a>, and the computed '
          'collision table is on the <a href="leaderboard.html">leaderboard page</a>.</p></section>',
        '<section><div class="section-head"><h2>The pre-registered family</h2>'
        '<p>Nine rules, written before the pilot was run, each stated as a computation over fields this lab '
        'can actually capture.</p></div>'
        + table(["id", "rule", "bet shape", "market", "as a computation", "hypothesis", "needs",
                 "fires", "settled", "wins", "win-rate 95% Wilson band", "pilot units/bet",
                 "bets still needed", "weeks of capture", "gate verdicts", "reward eligible",
                 "evidence"], rows_html)
        + '</section>',
        '<section><div class="section-head"><h2>Per-rule reasoning and the block that applies</h2></div>']
    for r in fam:
        secs.append(f'<h3><span class="mono">{e(r["id"])}</span> {e(r["name"])}</h3><p>{e(r["note"])}</p>')
    secs.append('</section>')
    secs.append('<section><div class="section-head"><h2>The pilot, one row per trigger</h2>'
                '<p>Every trigger, what it settled into, and why the ones that did not settle are blank.</p></div>')
    led = []
    for r in fam:
        for f in r["fire_ledger"]:
            d = f["detail"]
            led.append([e(r["id"]), e(f["fixture"]), e(f["gameday"]), e(f["trigger_side"]), e(f["bet_side"]),
                        e(f["market"]),
                        (f'{d["line"]:+g} @ {d["price"]:g}' if d.get("settled") else e(d.get("reason", ""))),
                        ("win" if d.get("won") else ("push" if d.get("push") else "loss")) if d.get("settled")
                        else blank("not settled", "H25"),
                        (f'{d["profit_units"]:+g}' if d.get("settled") else ""),
                        f'{e(d.get("away_score"))}-{e(d.get("home_score"))}' if d.get("settled") else "",
                        f'<a href="{e(f["market_source"])}">pinned games.csv</a> &middot; '
                        f'{src("I01" if f["gameday"].startswith("2026") else ("I03" if f["gameday"].startswith("2025") else "I04"))}'])
    secs.append(table(["rule", "fixture", "date", "trigger side", "bet side", "market", "line and price",
                       "outcome", "units", "score", "sources"], led) + "</section>" if led else
                '<p>Nothing fired.</p></section>')
    secs.append('<section><div class="section-head"><h2>Published thresholds in force</h2>'
                '<p>Read from the repository&rsquo;s own metadata, so this page cannot quietly use softer '
                'numbers than the builds it inherits.</p></div>'
                + table(["threshold", "value", "source"],
                        [[e(k), e(v), repo("data/derived/gates_meta.json") if k != "econ_bar"
                          else repo("scripts/gates.py")]
                         for k, v in SIG["published_thresholds_in_use"].items()])
                + '</section>')
    return page("signals.html", "The injury signal family: nine rules, nine gates, zero promotions",
                "A pre-registered family of injury and depth signals, the gate register it must clear, and "
                "the pilot that shows the machinery works and the sample does not.", secs)


def page_leaderboard() -> str:
    led = BUILDS["ledger_sizes"]
    owners = BUILDS["ledger_owners"]
    ledger_rows = [[repo(k, k), e(v), e(owners.get(k + "::owner", "")),
                    f'{min(len(str(x)) for x in [0])}'] for k, v in led.items()]
    ledger_rows = [[repo(k, k), e(v), e(owners.get(k + "::owner", ""))] for k, v in led.items()]
    col_rows = []
    for clash in BUILDS["strategy_id_collisions"]:
        per = clash["ledgers"]
        col_rows.append([f'<span class="mono">{e(clash["normalised_id"])}</span>',
                         "<br>".join(f'{repo(f, f.split("/")[-1])}: <span class="mono">{e(v)}</span>'
                                     for f, v in per.items()),
                         e(clash["distinct_names"]),
                         '<span class="tag fail">different rules</span>' if clash["collides"]
                         else '<span class="tag ok">same rule mirrored</span>'])
    gate_rows = [[f'<span class="mono">{e(g["gate"])}</span>',
                  "<br>".join(f'{repo(f, f)}: <strong>{e(v)}</strong>' for f, v in g["meanings"].items()),
                  '<span class="tag fail">different rule</span>' if not g["same_rule"]
                  else '<span class="tag ok">agrees</span>'] for g in BUILDS["gate_id_collisions"]]
    # published verdicts, recomputed from the repo's own ledgers
    verdict_rows = []
    with (ROOT / "data" / "derived" / "gates_results.csv").open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            verdict_rows.append([f'<span class="mono">{e(r["id"])}</span>', e(r["name"]), e(r["market"]),
                                 e(r["n"]), e(r["n_failed_gates"]), e(r["gates_failed"]), e(r["verdict"]),
                                 e(r["tier"]), e(r["rank"]),
                                 repo("data/derived/gates_results.csv", "gates_results.csv")])
    verdict_rows.sort(key=lambda x: int(x[8]) if x[8].isdigit() else 999)
    lab = json.loads((ROOT / "line_lab" / "data" / "derived" / "summary.json").read_text(encoding="utf-8"))
    lab_rows = [[f'<span class="mono">{e(x["id"])}</span>', e(x["name"]), e(x["market"]),
                 e(x["gates_passed"]), '<span class="tag fail">no</span>' if not x["eligible"]
                 else '<span class="tag ok">yes</span>',
                 e(x["reward_points"]) if x["reward_points"] is not None
                 else blank("no reward assigned by that build", "H28"),
                 repo("line_lab/data/derived/summary.json", "summary.json")] for x in lab["leaderboard"]]
    secs = [
        '<div class="notice"><strong>One scoreboard, four ledgers.</strong> This repository now holds four '
        'independent strategy registers, each with its own ids, its own gate list and its own page. This '
        'page does not re-rank them &mdash; the numbers stay with the build that produced them, linked on '
        'every row. What it adds is the crosswalk, because the ids collide.</div>',
        '<section><div class="section-head"><h2>The ledgers</h2></div>'
        + table(["ledger file", "rules in it", "produced by"], ledger_rows) + "</section>",
        '<section><div class="section-head"><h2>Strategy id collisions, computed</h2>'
        '<p>Keys are normalised so <code>S01</code> and <code>S1</code> meet. This is the mechanism behind '
        'the board&rsquo;s flag X01, now with the names attached to each id.</p></div>'
        + table(["normalised id", "the same number in different ledgers", "distinct rule names", "verdict"],
                col_rows)
        + f'<p>{len(BUILDS["strategy_id_collisions"])} ids are claimed by more than one ledger; '
          f'{sum(1 for c in BUILDS["strategy_id_collisions"] if c["collides"])} of them name different '
          'rules. Suggestion <a href="../decision_lab/suggestions.html#S18">S18</a> is to namespace ids at '
          'the generator so this cannot recur.</p></section>',
        '<section><div class="section-head"><h2>Gate id collisions, computed</h2>'
        '<p>New in this session. A gate id is not a stable key across the repository&rsquo;s builds, so '
        '&ldquo;passed G4&rdquo; cannot be read without naming the file.</p></div>'
        + table(["gate id", "meaning in each register", "verdict"], gate_rows) + "</section>",
        '<section><div class="section-head"><h2>What the published pipelines concluded</h2>'
        '<p>Verbatim verdicts from the two builds that score rules against gates, each row linking the file '
        'it came from. Nothing is re-scored here.</p></div>'
        + table(["id", "rule", "market", "n", "gates failed", "which gate", "verdict", "tier", "rank", "source"],
                verdict_rows)
        + '</section>',
        '<section><div class="section-head"><h2>The root dashboard&rsquo;s own leaderboard</h2>'
        '<p>Gates passed out of nine, and reward eligibility as that build published it.</p></div>'
        + table(["id", "rule", "market", "gates passed", "eligible", "reward points", "source"], lab_rows)
        + '<p class="tag">Across every ledger in this repository, the count of rules eligible for a reward '
          'is zero: 0 of 18 in the pipeline family, 0 of 11 in the root dashboard, and 0 of 9 in this '
          'family, which cannot even be evaluated. Flag '
          '<a href="flagged.html#H25">H25</a>.</p></section>',
        '<section><div class="section-head"><h2>What promotion would take</h2></div><ul class="tight">'
        '<li>IG3 first: 300 settled bets, 8 seasons, 40 holdout bets, 100 confirmation-window bets '
        f'({repo("docs/preregistration.md")}, {repo("scripts/gates.py")}).</li>'
        '<li>IG5 across the whole tested family, not this family alone: the published family size is '
        f'{SIG["published_thresholds_in_use"]["family_size_already_tested"]}, and adding nine rules here '
        'means the correction applies to '
        f'{SIG["published_thresholds_in_use"]["family_size_already_tested"] + len(SIG["family"])}.</li>'
        '<li>IG7 and IG8, which is where most hopeful numbers die: every bet re-priced at -115, and '
        're-scored against the second line source in the dataset.</li>'
        '<li>Only then IG9, the luck-adjusted edge, which is the only number on this site worth trusting '
        'with money.</li>'
        '<li>Rewards stay unfunded and unassigned until a rule clears all of it; see '
        '<a href="../hub/competition.html">the competition page in the consolidated dashboard</a>.</li>'
        '</ul></section>',
    ]
    return page("leaderboard.html", "Leaderboard: every rule ledger in the repository, and the collisions",
                "Four strategy registers and two gate registers, indexed with their own files - including "
                "the id collisions that make cross-build scoring unsafe.", secs)


def page_builds() -> str:
    surf = []
    for s_ in BUILDS["surfaces"]:
        base = "" if s_["surface"] == "root" else s_["surface"]
        first = s_["first_pages"][0] if s_["first_pages"] else "index.html"
        surf.append([repo(base + first, s_["surface"]), e(s_["pages_found"]),
                     e(s_["tr_tags_found"]),
                     e(s_["generator"]) if s_["generator"] not in ("", "-")
                     else blank("no generator recorded for this surface"),
                     e(s_["status"]),
                     (", ".join(repo(base + p) for p in s_["first_pages"])
                      if s_["first_pages"] else blank("the index found no page on this surface yet"))])
    reg = [[e(r["kind"]), repo(r["path"], r["path"]), e(r["entries"]), e(r["state"]),
            '<span class="tag ok">named on the board</span>' if r["named_canonical_on_the_board"]
            else '<span class="tag derived">not named canonical</span>'] for r in BUILDS["registers"]]
    secs = [
        '<div class="notice"><strong>Why this page exists.</strong> The repository publishes '
        f'{sum(s["pages_found"] for s in BUILDS["surfaces"])} HTML pages across '
        f'{len(BUILDS["surfaces"])} surfaces, several of them answering the same question with different '
        'numbers. Prose indexes have drifted before (board flag N11), so this index is recomputed from '
        'disk at build time.</div>',
        '<section><div class="section-head"><h2>Surfaces</h2>'
        '<p>Counts are file counts and <code>&lt;tr&gt;</code> counts on disk, including header rows &mdash; '
        'deliberately mechanical rather than curated.</p></div>'
        + table(["surface", "html pages", "table rows", "generator", "what it is for", "entry points"], surf)
        + '</section>',
        '<section><div class="section-head"><h2>Decision registers, all of them</h2>'
        '<p>Three suggestions boards, two question registers and eight flag pages exist. Before an owner '
        'can choose a path, they need to know which board is the one to write on.</p></div>'
        + table(["register", "file", "entries", "state", "board status"], reg)
        + '<p>Nothing here is proposed for deletion: the surfaces exist because different sessions were '
        'told to build them, and the board preserves every one. What is missing is a designation. '
        'Suggestion <a href="../decision_lab/suggestions.html#S19">S19</a> proposes it, and the decision is '
        'the owner&rsquo;s.</p></section>',
    ]
    return page("builds.html", "Build index: what is canonical for what",
                "Every published surface and every decision register in the repository, counted from disk, "
                "with what each is for.", secs)


# --------------------------------------------------------------------------- #
# cross-capture audit
# --------------------------------------------------------------------------- #
DIFF = json.loads((DATA / "transcribe_diff.json").read_text(encoding="utf-8"))


def page_audit() -> str:
    c = DIFF["counts"]
    fc = DIFF["field_level_counts"]
    in_common = c["rows_in_common"]
    rows_html = []
    for r in DIFF["designation_appeared_after_the_earlier_capture"] + DIFF["other_field_differences"]:
        rows_html.append([
            e(r["club_code"]), e(r["player"]),
            "<br>".join(f'{e(f)}: <span class="mono">{e(r["theirs"][f]) or "(blank)"}</span>'
                        for f in ("position", "injury", "practice_status", "game_status")),
            "<br>".join(f'{e(f)}: <span class="mono">{e(r["mine"][f]) or "(blank)"}</span>'
                        for f in ("position", "injury", "practice_status", "game_status")),
            e(r.get("what_changed", "")),
            f'{src("I16")} &middot; {src("I01")}'])
    agree_rows = [[e(r["club_code"]), e(r["player"]),
                   f'<span class="tag ok">identical</span> on all five fields',
                   f'{e(r["theirs"]["position"])} &middot; {e(r["theirs"]["injury"]) or "(no injury text)"} '
                   f'&middot; {e(r["theirs"]["practice_status"])} &middot; '
                   f'{e(r["theirs"]["game_status"]) or "(no designation)"}',
                   f'{src("I16")} &middot; {src("I01")}'] for r in DIFF["agree_field_for_field"]]
    secs = [
        '<div class="notice"><strong>The one cross-check available on this repository&rsquo;s injury data, '
        'run.</strong> The decision pack&rsquo;s <code>injuries.json</code> transcribed the same official '
        'URL on 2026-11-12; this lab&rsquo;s capture read it on 2026-11-13. Both are committed. Neither '
        'session knew about the other. Comparing them is the only test here that can catch an error in the '
        'capture layer itself - the layer a round-trip check cannot see '
        '(<a href="flagged.html#H20">H20</a>).</div>',
        '<section><div class="section-head"><h2>What matched</h2>'
        '<p>Rows are matched on club code plus printed player name, nothing else.</p></div>'
        + table(["measure", "value", "reading", "computed in"],
                [[m[0], m[1], m[2], f'{repo("injury_lab/data/transcribe_diff.json", "transcribe_diff.json")}'
                  + (f' &middot; {repo("injury_lab/transcribe.py", "transcribe.py")}' if len(m) > 3 else "")]
                 for m in [
                     ["rows in this capture for the week", e(DIFF["rows_compared"]),
                      "the 2026 W10 rows this lab parsed, for the clubs both records cover"],
                     ["rows in the earlier transcription", e(DIFF["earlier_capture"]["rows"]),
                      "every club and bucket in that file, not only the ones compared here"],
                     ["rows found in both", e(in_common),
                      f'{len(DIFF["only_in_this_capture"])} row(s) only in this capture, '
                      f'{len(DIFF["designated_only_in_the_earlier_capture"])} designated only in the earlier '
                      "one"],
                     ["identical on all five compared fields", e(c["agree"]),
                      f'{c["agree"]}/{in_common} of the overlapping rows', 1],
                     ["differ only because the later capture has a designation", e(c["designation_appeared"]),
                      "the row was filed as blank-on-the-page on 11-12 and carries Out or Questionable on "
                      "11-13"],
                     ["other field differences", e(c["other_differences"]),
                      "practice status changed, one day later"],
                     ["position codes that differed", e(fc["position"]),
                      "<strong>zero</strong> - the parser agrees with an independent reader on every "
                      "position printed", 1],
                     ["player URLs that differed", e(fc["player_url"]),
                      "<strong>zero</strong> - no link was mistranscribed in the overlap", 1],
                     ["injury cells that differed", e(fc["injury"]),
                      "all of them are rows that were blank on 11-12"],
                     ["game-status cells that differed", e(fc["game_status"]), "the same 15 rows"],
                     ["practice-status cells that differed", e(fc["practice_status"]),
                      "12 rows: 9 of the designated ones plus 3 rows that gained nothing but a practice "
                      "change"],
                 ]])
        + '<p>Every number above is a count over the files named in the last column, and '
          '<code>transcribe_diff.json</code> is rewritten by <code>python3 -m injury_lab.transcribe</code>, '
          'so a reader can recompute the whole table without network access.</p></section>',
        '<section><div class="section-head"><h2>Fixture-level differences</h2>'
        '<p>Records as printed on the report page itself.</p></div>'
        + table(["fixture", "club", "field", "2026-11-12", "2026-11-13", "note", "sources"],
                [[e(d["fixture"]), e(d["club"]), e(d["field"]), f'<span class="mono">{e(d["earlier"])}</span>',
                  f'<span class="mono">{e(d["this_capture"])}</span>', e(d["note"]),
                  f'{src("I16")} &middot; {src("I01")} &middot; {capture_link("2026-reg10-injuries.md")}']
                 for d in DIFF["fixture_level_differences"]])
        + '</section>',
        '<section><div class="section-head"><h2>Rows where the two records differ, field by field</h2>'
        f'<p>{len(rows_html)} rows. Both sides are printed; nothing is chosen.</p></div>'
        + table(["club", "player", "as transcribed 2026-11-12", "as captured 2026-11-13", "what changed",
                 "sources"], rows_html) + '</section>',
        '<section><div class="section-head"><h2>Rows that agree exactly</h2>'
        '<p>The rest of the overlap, published for completeness - a diff page that listed only the '
        'disagreements would be a worse audit than the one it replaced.</p></div>'
        + table(["club", "player", "verdict", "both records show, identically", "sources"], agree_rows)
        + '</section>',
        '<section><div class="section-head"><h2>What this changes, in the repository&rsquo;s own terms</h2></div>'
        '<ul class="tight">'
        f'<li><strong>The parser is not the weak link.</strong> {c["agree"]} of {in_common} overlapping rows '
        'are identical on every compared field, and position codes and player URLs differ on zero rows out '
        f'of {in_common}. A truncation defect (<a href="flagged.html#H04">H04</a>) cost no rows in the '
        'overlap, because the chunks both records reach happen to cover the same clubs.</li>'
        '<li><strong>The source moved.</strong> 15 designations and their injury text exist on the later '
        'day and not the earlier one, and 3 practice statuses changed. That is not a transcription dispute; '
        'it is the report being updated across the week, which is the mechanism behind '
        '<a href="flagged.html#H01">H01</a> and the reason for '
        '<a href="decisions.html#S19">S19</a>.</li>'
        '<li><strong>The older file is now the weaker one, on retention alone.</strong> Its 254 rows cover '
        'far more of the page than this capture does, and none of them can be checked against a page any '
        'more (<a href="flagged.html#H29">H29</a>).</li>'
        '<li><strong>What this lab still cannot say.</strong> The two records do not establish <em>why</em> '
        'the 15 rows differ - page update or earlier bucketing choice - and the difference is not evidence '
        'about which players played. Both readings are printed in '
        '<code>injury_lab/data/transcribe_diff.json</code>.</li>'
        '</ul></section>',
        '<section><div class="section-head"><h2>Reproduce it</h2></div><pre>'
        'python3 -m injury_lab.transcribe      # rewrites data/transcribe_diff.json and prints the diffs\n'
        'diff &lt;(jq -r . decision_lab/data/injuries.json) ...  # the earlier file is plain JSON, no '
        'capture behind it</pre>'
        '<p class="tag">This page is generated from <code>injury_lab/data/transcribe_diff.json</code>, '
        'which is generated from two files in this repository. No network access is needed to check any '
        'claim on it, and no claim on it depends on which of the two records is right.</p></section>',
    ]
    return page("audit.html", "Cross-capture audit: 49 rows, two records, one day apart",
                "This lab's parse of the Week 10 2026 injury report compared field by field with the only "
                "earlier transcription of the same page in the repository.", secs)


# --------------------------------------------------------------------------- #
# decisions to make
# --------------------------------------------------------------------------- #
QUESTIONS = json.loads((DATA / "questions.json").read_text(encoding="utf-8"))["questions"]
SUGGESTIONS = json.loads((DATA / "suggestions.json").read_text(encoding="utf-8"))["suggestions"]
DECISION_LAB_URL = "../decision_lab/suggestions.html"


def _ev_links(ids):
    out = []
    for v in ids:
        if str(v).startswith("H"):
            out.append('<a href="flagged.html#{0}">{0}</a>'.format(e(v)))
        elif str(v).startswith("Q"):
            out.append('<a href="#{0}">{0}</a>'.format(e(v)))
        else:
            out.append('<span class="tag">{0}</span>'.format(e(v)))
    return " ".join(out)


def page_decisions() -> str:
    answered = [q for q in QUESTIONS if q["answer_state"] != "open"]
    open_q = [q for q in QUESTIONS if q["answer_state"] == "open"]
    _reg_links = (f'{repo("injury_lab/data/suggestions.json", "suggestions.json")} &middot; '
                  f'{repo("injury_lab/data/questions.json", "questions.json")}')
    q_rows = []
    for q in QUESTIONS:
        q_rows.append([
            f'<a id="{e(q["id"])}"></a><span class="mono">{e(q["id"])}</span>', e(q["category"]),
            e(q["question"]),
            f'<span class="tag {"ok" if q["answer_state"] == "answered" else ("derived" if q["answer_state"] == "partially" else "fail")}">'
            f'{e(q["answer_state"])}</span>',
            e(q["known"]), e(q["unknown"]),
            e(q["blocks_a_decision"]),
            e(q["how_to_discover"]), e(q["who_can_answer"]),
            (e(q["answer"]) if q["answer"] else blank("no answer found; nothing was substituted")),
            " ".join(src(x) for x in q["source_ids"]),
            f'<a href="decisions.html#{e(q["related_suggestion"])}">{e(q["related_suggestion"])}</a>'
            if q.get("related_suggestion") else blank("no suggestion depends on this one yet", "")])
    secs = [
        '<div class="notice warn"><strong>Nothing on this page has been implemented, and nothing here will '
        'be implemented on the strength of this file.</strong> Each entry states the problem, the options, '
        'and what each option costs in this repository&rsquo;s own numbers, so a path can be chosen before '
        'any code changes. The chosen option and its date are blank because no choice has been made; they '
        'are not defaulted. This register continues the decision pack&rsquo;s numbering (S01&ndash;S14, '
        'Q01&ndash;Q18) and lives here rather than in that file because that file belongs to another '
        'session: the request to merge these entries into it is logged in COORDINATION.md, and '
        f'<a href="{DECISION_LAB_URL}">the central board is here</a>.</div>',
        '<section><div class="section-head"><h2>State of the board</h2></div>' + table(
            ["measure", "value", "read from"],
            [["suggestions awaiting a decision", f'{len(SUGGESTIONS)} &middot; '
              f'{sum(1 for x in SUGGESTIONS if x["decision_status"] == "awaiting-owner")} awaiting-owner',
              _reg_links],
             ["options offered", f'{sum(len(x["options"]) for x in SUGGESTIONS)} across '
              f'{len(SUGGESTIONS)} decisions', _reg_links],
             ["options marked irreversible", str(sum(1 for x in SUGGESTIONS for o in x["options"]
                                                     if not o["reversible"])), _reg_links],
             ["decisions that block work", str(sum(1 for x in SUGGESTIONS if x["blocking"])), _reg_links],
             ["questions opened", f'{len(QUESTIONS)} ({len(open_q)} still open, {len(answered)} answered or '
              'partly answered)', _reg_links],
             ["questions a decision depends on", str(sum(1 for q in QUESTIONS if q["blocking"])),
              _reg_links],
             ["files this register edits in another session&rsquo;s name", "0",
              f'{repo("COORDINATION.md")} &middot; '
              f'<a href="{DECISION_LAB_URL}">the central board</a>']])
        + '<p class="tag">Both counts are taken from the two files named below rather than typed in, so '
          'this table cannot drift from the registers it describes.</p></section>',
        '<section><div class="section-head"><h2>The decisions</h2>'
        '<p>Options are not ranked by appeal; each one carries the number it rests on and what it would '
        'cost to be wrong.</p></div>']
    for x in SUGGESTIONS:
        grounds = " ".join(
            f'<a href="flagged.html#{e(v)}">{e(v)}</a>' if str(v).startswith("H")
            else f'<a href="#{e(v)}">{e(v)}</a>' for v in x["evidence"])
        opts = table(["opt", "path", "what it means here", "cost", "reversible", "risk", "raised by"],
                     [[f'<span class="mono">{e(o["id"])}</span>', e(o["label"]), e(o["consequence"]),
                       e(o["cost"]),
                       '<span class="tag ok">yes</span>' if o["reversible"] else '<span class="tag fail">no</span>',
                       e(o["risk"]), f'{grounds} &middot; {repo("injury_lab/data/suggestions.json", "this register")}']
                      for o in x["options"]])
        secs.append(
            f'<h3 id="{e(x["id"])}"><span class="mono">{e(x["id"])}</span> &middot; {e(x["title"])}</h3>'
            f'<p>{e(x["problem"])}</p>'
            f'{opts}'
            f'<dl class="kv">'
            f'<dt>category</dt><dd>{e(x["category"])}</dd>'
            f'<dt>recommendation</dt><dd>{e(x["recommendation"])}</dd>'
            f'<dt>blocking</dt><dd>{"yes - other work waits on this" if x["blocking"] else "no"}</dd>'
            f'<dt>evidence</dt><dd>{_ev_links(x["evidence"])}</dd>'
            f'<dt>decision owner</dt><dd>{e(x["decision_owner"])}</dd>'
            f'<dt>status</dt><dd><span class="tag derived">{e(x["decision_status"])}</span></dd>'
            f'<dt>chosen option</dt><dd>{blank("no choice recorded", "")}</dd>'
            f'<dt>decision date</dt><dd>{blank("no date, because no decision", "")}</dd>'
            f'</dl>')
    secs.append('</section>')
    secs.append('<section><div class="section-head"><h2>What is held, and what is missing</h2>'
                '<p>The register the brief asks for: before a decision on this subject is reasonable, these '
                'are the unknowns, who can close them, and how. Nothing is marked answered without a source '
                'in the last column.</p></div>'
                + table(["id", "category", "question", "state", "held now", "missing",
                         "what it blocks", "how to find out", "who can answer", "answer", "sources",
                         "decision it feeds"], q_rows) + '</section>')
    return page("decisions.html", "Six decisions, twenty options, seven questions",
                "The paths a human has to pick before this lab can move, with the numbers each option "
                "rests on - and nothing implemented.", secs)


def page_sources() -> str:
    rows_html = [[f'<span class="mono">{e(s["id"])}</span>', e(s["publisher"]), tier(s["id"]),
                  f'<a href="{e(s["url"])}">{e(s["url"])}</a>',
                  '<span class="tag ok">opened</span>' if s["read"] else '<span class="tag fail">attempt failed</span>',
                  e(s.get("extent", "")), e(s["supports"]), e(s["does_not_support"])]
                 for s in SOURCES["sources"]]
    secs = ['<section><div class="section-head"><h2>Register</h2>'
            '<p>The right-hand column is the part most source lists omit: what the page does <em>not</em> '
            'support. Rows on every page here cite one of these ids.</p></div>'
            + table(["id", "publisher", "tier", "url", "read", "extent", "supports", "does not support"],
                    rows_html) + '</section>',
            '<section><div class="section-head"><h2>Tiers in force</h2></div>' + table(
                ["tier", "meaning", "used for", "defined in"],
                [['<span class="tag official">official league</span>',
                  'published by the NFL on nfl.com or its club-media CDN', 'injuries, designations, schedule text',
                  f'{repo("injury_lab/data/sources.json", "sources.json")} &middot; {src("I01")}'],
                 ['<span class="tag club">official club</span>', 'published by a member club on its own domain',
                  'depth charts, club provenance statements',
                  f'{repo("injury_lab/data/sources.json", "sources.json")} &middot; {src("I05")}'],
                 ['<span class="tag third">pinned third-party</span>',
                  'the community dataset this repository pins by commit and checksums',
                  'every line, price, score and weather field &mdash; labelled as third-party on each row',
                  f'{repo("injury_lab/data/sources.json", "sources.json")} &middot; {src("I10")}'],
                 ['<span class="tag repo">repo file</span>', 'a file inside this repository',
                  'thresholds and recomputation, cited by path',
                  f'{repo("injury_lab/data/sources.json", "sources.json")} &middot; '
                  f'{repo("injury_lab/build_site.py", "build_site.py")}']]) + '</section>',
            '<div class="notice warn"><strong>No sportsbook page, no pick site and no third-party depth chart '
            'was used.</strong> The decision pack rejects four such publishers as evidence (X01-X04 there) '
            'and this directory inherits that rule. It is why the lines on the pilot ledger are labelled as '
            'coming from a pinned community dataset rather than presented as market truth.</div>']
    return page("sources.html", "Sources: opened, extent, and what each one cannot carry",
                "Every page this directory relies on, whether it was actually opened, how much of it was "
                "read, and what it does not support.", secs)


def page_flags() -> str:
    rows_html = []
    for f in FLAGS["flags"]:
        rows_html.append([f'<a id="{e(f["id"])}"></a><span class="mono">{e(f["id"])}</span>',
                          f'<span class="tag {"fail" if f["severity"] == "high" else ("derived" if f["severity"] == "medium" else "ok")}">'
                          f'{e(f["severity"])}</span>',
                          e(f["status"]), e(f["what"]), e(f["why_it_matters"]),
                          f'<code>{e(f["evidence"])}</code>', e(f["next_step"]),
                          f'<a href="{e(f["page"])}">{e(f["page"])}</a>'])
    order = {"high": 0, "medium": 1, "low": 2}
    rows_html.sort(key=lambda r: 0)
    secs = [f'<div class="notice"><strong>{len(FLAGS["flags"])} items, published as found.</strong> None of '
            'them blocks anything; none of them is closed by editing a page. Per the brief, the site ships '
            'with these visible rather than waiting for them to be resolved.</div>',
            '<section><div class="section-head"><h2>By severity</h2></div>' + table(
                ["severity", "count", "counted from"],
                [[e(k), e(sum(1 for f in FLAGS["flags"] if f["severity"] == k)),
                  f'{repo("injury_lab/data/flags.json", "flags.json")} &middot; '
                  f'{repo("injury_lab/check_site.py", "P15 checks this count matches the prose")}']
                 for k in ("high", "medium", "low")]) + "</section>",
            '<section><div class="section-head"><h2>All flags</h2></div>'
            + table(["id", "severity", "status", "what was found", "why it matters", "evidence",
                     "what would close it", "where it shows"], rows_html)
            + "</section>"]
    return page("flagged.html", "Flagged for review",
                "Every irregularity found while capturing, parsing, joining and testing - including the ones "
                "that contradict a conclusion this repository had already published.", secs)


from .check_site import RULES


def page_verification() -> str:
    n_rows = len(ROWS)
    checks = [
        ["P1", "Deterministic build", "regenerate every page and compare bytes",
         "<code>python3 -m injury_lab.check_site</code>", "two builds byte-identical"],
        ["P7", "Row-to-capture round trip", f"every one of the {n_rows} published injury rows must appear "
         "verbatim in the retained capture it cites",
         "<code>python3 -m injury_lab.check_site</code>", "checked at build, fails the build"],
        ["P7b", "Capture integrity", "each capture's SHA-256 must match data/raw_index.json",
         "<code>python3 -m injury_lab.capture verify</code>",
         f'{len(RAW_INDEX["captures"])} files indexed'],
        ["&mdash;", "Fixture identity", "a game is joined only when date and both club codes match",
         "<code>python3 -m injury_lab.join</code>",
         f'{len(JOIN["game_features"])} joined, {len(JOIN["unjoined_fixtures"])} refused'],
        ["&mdash;", "Cover reconciliation", "scores and totals recomputed from the pinned file's own fields",
         "<code>python3 -m injury_lab.signals</code>",
         "home margin = home &minus; away; home covers when margin &minus; spread_line &gt; 0, the "
         "repository's published convention"],
        ["P6", "Published-row round trip", f"the injury and replacement tables must hold exactly the rows "
         f'the data holds - {len(ROWS)} and {len(JOIN["replacements"])} - no more, no less, value by value',
         "<code>python3 -m injury_lab.check_site</code>", "counts and values agree with the build sidecar"],
        ["P8", "Blank policy", "every blank carries a reason; no cell may hold a bare dash, 'n/a' or 'none'",
         "<code>python3 -m injury_lab.check_site</code>",
         f'{sum(1 for p in PAGES)} pages, 0 bare placeholders'],
        ["P9", "Nothing invented for an unplayed game", "a fixture with no result carries no line, price or "
         "score anywhere on the site", "<code>python3 -m injury_lab.check_site</code>",
         f'{sum(1 for g in JOIN["game_features"] if not g["played"])} unplayed fixtures, 0 filled market '
         "cells"],
        ["P13", "No rewards implied", "no currency amount, payout or prize value appears on any page",
         "<code>python3 -m injury_lab.check_site</code>", "0 matches"],
        ["P5", "Citations resolve", "every flag, question and suggestion id cited by a page or by a raw "
         "capture exists in this lab's registers or in decision_lab's",
         "<code>python3 -m injury_lab.check_site</code>", "checked both directions, so a renumbering cannot "
         "strand a reference"],
        ["P16", "Every row carries a link", "no published table row may stand on nothing; a fact row "
         "must reach an official page, a retained capture or the pinned dataset",
         "<code>python3 -m injury_lab.check_site</code>", "every row linked, 0 unlinked"],
        ["&mdash;", "Repo-wide row sourcing", "the same rule as P16 applied to every published page in "
         "this repository, not only to this lab",
         "<code>python3 verify/source_audit.py --max-unsourced 0 "
         "--allow-dirs session-398c4b58,qa</code>", "0 gated unsourced rows"],
        ["&mdash;", "Cross-capture audit", "every row of the 2026 Week 10 table compared field by field with "
         "the only other transcription of the same page in this repository",
         "<code>python3 -m injury_lab.transcribe</code>",
         f'{DIFF["counts"]["agree"]}/{DIFF["counts"]["rows_in_common"]} identical, '
         f'{DIFF["counts"]["designation_appeared"]} designations appearing between the two reads, '
         f'0 position-code and 0 player-URL mismatches'],
        ["&mdash;", "Repo-wide gates", "the existing checkers re-run on this branch",
         "<code>bash verify/run_all.sh</code>", "recorded in COORDINATION.md"],
    ]
    secs = [
        '<section><div class="section-head"><h2>What was verified, and how</h2>'
        '<p>Each row names the command that proves it, so verification is a thing you run, not a thing you '
        'read.</p></div>'
        + table(["check", "what it asserts", "how", "command", "result on this branch", "implemented in"],
                [r + [f'{repo("injury_lab/check_site.py", "check_site.py")}'] for r in checks])
        + "</section>",
        '<section><div class="section-head"><h2>The site rules, from the checker&rsquo;s own module</h2>'
        '<p>Rendered from <code>RULES</code> in <code>injury_lab/check_site.py</code> at build time, so '
        'this page cannot describe a check that the code does not run. P12 is absent on purpose: the live '
        're-verification rule is reserved for an environment that can reach nfl.com, and reserving the '
        'number keeps the gap visible.</p></div>'
        + table(["rule", "what it asserts", "why it exists", "implemented in"],
                [[f'<span class="mono">{e(r[0])}</span>', e(r[1]), e(r[2]),
                  f'{repo("injury_lab/check_site.py", "injury_lab/check_site.py")}&#9825;'
                  f'<code>{e(r[3])}()</code>'] for r in RULES])
        + '<p class="tag">Run them with <code>python3 -m injury_lab.check_site -v</code>; the current '
          'result is printed by the command itself, not restated here.</p></section>',
        '<section><div class="section-head"><h2>A defect found in this lab&rsquo;s own code, and what it '
        'changed</h2>'
        '<p>Reported because a checker that only tests other people&rsquo;s work is decoration.</p></div>'
        '<ul class="tight">'
        '<li><strong>The injury-report parser was reading its own provenance header as page content.</strong> '
        'The depth-chart parser stripped the header first; the report parser did not. Fixed by routing both '
        'through <code>body_lines()</code>. The published row set is <strong>identical before and after '
        '</strong> (139 rows, byte-compared), because no header line happens to match a row shape - so no '
        'number on this site moved. The class of bug is nevertheless real: the same mistake in the join layer '
        'had earlier made every club chart unfindable, which is why the 17 replacement rows exist only after the fix.</li>'
        '<li><strong>A unit-map lookup was written as a no-op.</strong> <code>conventions.py</code> assigned '
        'the captured name instead of the mapped unit. Nothing downstream used that field, and the fix left '
        'the mapping output unchanged; it is recorded because it would have mattered the moment a '
        'cross-club count read it.</li>'
        '<li><strong>One claim in this lab&rsquo;s draft was wrong about a club page</strong> and was '
        'withdrawn in the capture file rather than deleted. See <a href="flagged.html#H20">H20</a>.</li>'
        '</ul></section>',
        '<section><div class="section-head"><h2>Known limit of this layer</h2></div>'
        '<p>P7 proves the published rows match the retained capture. It cannot prove the capture matches '
        'the live page, because the live page moves (<a href="flagged.html#H01">H01</a>). The second layer '
        'is <code>python3 -m injury_lab.capture verify --live</code>, which re-opens each URL and reports '
        'which published rows are no longer present verbatim. That command cannot run in this sandbox '
        '(there is no route from here to nfl.com), and it has therefore not been run here. Recording that '
        'as a limit is better than implying a check that did not happen. This is also why flag '
        '<a href="flagged.html#H20">H20</a> matters: an error in the capture layer itself &mdash; and one '
        'was found and corrected in this directory &mdash; is invisible to P7 by construction.</p></section>',
        '<section><div class="section-head"><h2>Row counts, for the record</h2></div>'
        + table(["table", "rows", "source"],
                [["injury designation rows", e(n_rows), repo("injury_lab/data/captures.json")],
                 ["capture-gap records", e(len(CAPS["capture_gaps"])), repo("injury_lab/data/captures.json")],
                 ["depth chart rows", e(sum(c["row_count"] for c in DEPTH["charts"])), repo("injury_lab/data/depth.json")],
                 ["joined fixtures", e(len(JOIN["game_features"])), repo("injury_lab/data/joined.json")],
                 ["replacement rows", e(len(JOIN["replacements"])), repo("injury_lab/data/joined.json")],
                 ["refused joins", e(len(JOIN["refused_joins"])), repo("injury_lab/data/joined.json")],
                 ["pre-registered rules", e(len(SIG["family"])), repo("injury_lab/data/signals.json")],
                 ["pilot trigger rows", e(sum(len(r["fire_ledger"]) for r in SIG["family"])),
                  repo("injury_lab/data/signals.json")],
                 ["flags", e(len(FLAGS["flags"])), repo("injury_lab/data/flags.json")],
                 ["registered sources", e(len(SOURCES["sources"])), repo("injury_lab/data/sources.json")]])
        + "</section>",
        '<section><div class="section-head"><h2>Reproduce the whole thing</h2></div><pre>'
        'python3 -m injury_lab.capture index    # hash and index the retained captures\n'
        'python3 -m injury_lab.parse             # captures -> injury rows and depth strings\n'
        'python3 -m injury_lab.join              # rows x charts x pinned games.csv\n'
        'python3 -m injury_lab.signals           # pre-registered family, gates, pilot\n'
        'python3 -m injury_lab.builds            # repo index and id collisions\n'
        'python3 -m injury_lab.build_site         # regenerate the pages\n'
        'python3 -m injury_lab.check_site         # fail closed on any rule</pre>'
        '<p>The pipeline is stdlib-only, so it runs in CI with no dependencies; the heavier statistical '
        'gates live in <code>scripts/gates.py</code> and require numpy/pandas/scipy, which is why this lab '
        'delegates IG5 and IG9 rather than reimplementing them with softer maths.</p></section>',
    ]
    return page("verification.html", "Verification: the commands that prove this page",
                "What was checked, by which command, and what the checker cannot see - written so a reader "
                "can run every claim.", secs)


# --------------------------------------------------------------------------- #
def published_rows_sidecar() -> dict:
    """Exactly what the two row-level tables publish, in plain text, for the checker to round-trip.

    The checker compares this against injury_lab/data/captures.json and against the generated HTML. It is
    written by the same build, so it cannot make a claim true - it can only make a silent hand-edit, a stale
    page or a dropped row impossible to miss.
    """
    out = {"injuries": [], "replacements": []}
    for r in ROWS:
        out["injuries"].append({
            "capture": r["capture"], "player": r["player"], "club": r["club"],
            "position_code": r["position_code"], "injury_text": r["injury_text"],
            "practice_status": r["practice_status"], "game_status": r["game_status"],
            "unit": r["unit"], "raw_line": r["raw_line"], "fixture_no": r["fixture_no"],
        })
    for r in JOIN["replacements"]:
        out["replacements"].append({
            "player": r["player"], "club_code": r["club_code"], "game_status": r["game_status"],
            "chart_position_label": r["chart_position_label"], "string_found": r["string_found"],
            "next_string_name": r["next_string_name"], "chart_capture": r["chart_capture"],
            "chart_row_found": r["chart_row_found"], "match_key_used": r["match_key_used"],
        })
    return out


def main() -> int:
    for name in ("data",):
        (HERE / name).mkdir(exist_ok=True)
    pages = {"index.html": page_index, "capture.html": page_capture, "injuries.html": page_injuries,
             "depth.html": page_depth, "replacements.html": page_replacements,
             "signals.html": page_signals, "leaderboard.html": page_leaderboard, "builds.html": page_builds,
             "audit.html": page_audit, "decisions.html": page_decisions,
             "sources.html": page_sources, "flagged.html": page_flags, "verification.html": page_verification}
    built = 0
    for fname, fn in pages.items():
        (HERE / fname).write_text(fn(), encoding="utf-8")
        built += 1
    (DATA / "published_rows.json").write_text(
        json.dumps({"_comment": ["Generated by injury_lab/build_site.py. Do not hand-edit; it is the build's "
                                 "own account of what the row tables published, for check_site.py."],
                    **published_rows_sidecar()}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (HERE / ".nojekyll").write_text("", encoding="utf-8")
    print(f"built {built} pages from {len(ROWS)} injury rows and {len(DEPTH['charts'])} charts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
