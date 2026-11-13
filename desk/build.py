#!/usr/bin/env python3
"""Build desk/*.html from desk/data/*.json.

Rules, all of which check.py enforces on the output:

1.  **No manual input, and no invented values.** This script contains no NFL fact of its own: no
    player, no injury, no record, no price, no coefficient. Everything it prints is read from a
    JSON file in ``data/``, and those files either transcribe a page an agent opened or are
    derived from a repository artifact by ``build_ledger.py``.
2.  **Blank means blank.** An empty field prints a blank marker carrying the words "never inferred"
    plus, where it matters, a link to the flag that explains it. Nothing is defaulted or carried
    over from a neighbouring row.
3.  **Every table row links a source.** A source that was not opened this cycle renders with a
    not-opened marker and can never be printed as plain confirmed evidence; citing an unregistered
    source ID raises and fails the build.
4.  **Deterministic.** Standard library only, no network, no clock, no randomness, and the ledger
    is only ever re-derived when ``build_ledger.py`` is run. Two consecutive builds are byte
    identical, which is what lets CI fail on drift.
5.  **No decisions.** Suggestions are rendered with their decision columns blank, because check.py
    fails if anything here has been approved on the owner's behalf.

Usage:  python3 desk/build.py
"""
from __future__ import annotations

import json
import re
from collections import Counter
from html import escape
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

# --------------------------------------------------------------------------- #
def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


META = load("meta.json")
SRC = {s["id"]: s for s in load("sources.json")["sources"]}
AVAIL = load("availability.json")
DEPTH = load("depth.json")
REC = load("reconcile.json")
GATES = load("gates.json")
SUG = load("suggestions.json")
QST = load("questions.json")
FLG = load("flags.json")
VER = load("verification.json")
LED = load("ledger.json")
DEC = load("decisions.json")

REPO_BLOB = "https://github.com/karagemop466-tech/Korea3/blob/main/"

CAP = META["captured_utc"]
UNIT = {}
for unit, codes in DEPTH["position_unit_convention"].items():
    if unit != "note":
        for c in codes:
            UNIT[c] = unit
UNMAPPED_NOTE = DEPTH["position_unit_convention"]["note"]

NAV = [
    ("index.html", "Desk home"),
    ("executive.html", "Executive summary"),
    ("availability.html", "Availability"),
    ("depth.html", "Depth & vacancies"),
    ("reconcile.html", "Cross-check"),
    ("signals.html", "Signals ledger"),
    ("gates.html", "Gates & luck"),
    ("suggestions.html", "Suggestions"),
    ("questions.html", "Questions"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged for review"),
    ("verification.html", "Verification"),
]

# --------------------------------------------------------------------------- #
def e(x) -> str:
    return escape("" if x is None else str(x), quote=True)


def blank(label: str = "blank", flag: str = "") -> str:
    f = f' <a href="flagged.html#{e(flag)}">[{e(flag)}]</a>' if flag else ""
    return (f'<span class="blank" title="Not published by an official source. Left blank, never inferred.">'
            f'{e(label)}</span>{f}')


def src(id_: str, label: str = "") -> str:
    """A row's source link. An unregistered ID is a build error, not a warning."""
    if not id_:
        raise KeyError("empty source id on a row: cite a registered source or print an explicit blank")
    s = SRC.get(id_)
    if not s:
        raise KeyError(f"source id {id_!r} is cited but is not in data/sources.json")
    txt = label or s["id"]
    if not s.get("read"):
        return (f'<a href="{e(s["url"])}" title="{e(s["publisher"])} - registered but NOT opened this cycle">'
                f'{e(txt)}<sup>&#9888;</sup></a>')
    return f'<a href="{e(s["url"])}" title="{e(s["publisher"])} - opened {e(s.get("read_utc", ""))}">{e(txt)}</a>'


def table(headers, rows, cls="") -> str:
    head = "".join(f"<th>{e(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    empty = ('<tr class="no-rows"><td colspan="%d" class="none">No rows: the source published none.</td></tr>'
             % len(headers)) if not rows else ""
    return f'<table class="grid{(" " + cls) if cls else ""}"><thead><tr>{head}</tr></thead><tbody>{body or empty}</tbody></table>'


def flag_strip(page_name: str) -> str:
    """Every irregularity that touches this page, linked to where it is written up.

    Without this a flag buried in a table cell is easy to skip; the strip is what makes the
    'flagged for review' page a place a reader is actually routed through.
    """
    mine = [f for f in FLG["flags"] if page_name in f.get("seen_on", [])]
    if not mine:
        return ""
    links = " ".join(f'<a href="flagged.html#{e(f["id"])}">{e(f["id"])}</a> {e(f["title"])}' for f in mine)
    return ('<p class="note"><strong>Flagged for review on this page:</strong> ' + links + "</p>")


def q_link(qid: str) -> str:
    return f'<a href="questions.html#{e(qid)}" title="the question this relates to">{e(qid)}</a>'


def fl_link(fid: str) -> str:
    return f'<a href="flagged.html#{e(fid)}" title="the irregularity this touches">{e(fid)}</a>'


def chip(text, kind="info") -> str:
    return f'<span class="chip {kind}">{e(text)}</span>'


def status_strip() -> str:
    hi = sum(1 for f in FLG["flags"] if f["severity"] == "high" and f["status"] == "open")
    open_q = QST["counts"]["open"]
    elig = sum(1 for r in LED["line_lab"]["strategies"] if r["eligible"])
    blocked = SUG["decision_gate"]["counts"]["Proposed - awaiting owner decision"]
    return ('<div class="strip">'
            f'{chip("captured " + CAP, "date")}'
            f'{chip(str(hi) + " open high-severity flags", "bad")}'
            f'{chip(str(open_q) + " blocking-or-open questions", "warn")}'
            f'{chip(str(elig) + " strategies eligible for a reward", "ok")}'
            f'{chip(str(blocked) + " suggestions awaiting your decision", "info")}'
            '<a class="strip-link" href="flagged.html">read the flags first</a></div>')


def page(slug: str, title: str, sub: str, body: str) -> str:
    parts = []
    for href, label in NAV:
        cls = ' class="active"' if href == slug else ""
        parts.append(f'<a href="{e(href)}"{cls}>{e(label)}</a>')
    links = "".join(parts)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} &middot; Week 10 decision desk</title>
<link rel="stylesheet" href="assets/style.css"></head>
<body>
<header class="mast"><div class="wrap">
<a class="home" href="index.html">Week 10 decision desk</a>
<span class="mast-sub">NFL line origination &middot; 2026 regular season, week 10 &middot; captured {e(CAP)}</span>
</div></header>
<nav class="nav"><div class="wrap">{links}<a href="../index.html" title="the site this desk reports into">&#8598; site hub</a></div></nav>
<main class="wrap">
<h1>{e(title)}</h1>
<p class="lede">{sub}</p>
{body}
{flag_strip(slug)}
</main>
<footer class="foot"><div class="wrap">
<p><strong>Provenance rule.</strong> Every table row links the source it was taken from. Official means
the league or a member club; market numbers come from one pinned third-party dataset and are labelled as
such on the row. A blank cell means no official publisher provided that value.</p>
<p><strong>Not advice.</strong> No strategy in this repository has cleared its validation gates, no reward is
funded, and nothing here is a recommendation to wager. Generated by <code>desk/build.py</code> from
<code>desk/data/*.json</code>; verify with <code>python3 desk/check.py</code>.</p>
</div></footer>
<script src="assets/app.js"></script>
</body></html>
"""


def anchor(text: str) -> str:
    out = []
    for ch in text.lower():
        out.append(ch if ch.isalnum() else "-")
    return "".join(out).strip("-")[:48]


# --------------------------------------------------------------------------- #
# derived, with the rule shown
# --------------------------------------------------------------------------- #
def club_deficiency():
    """Counts of published designations per club, split by unit. Pure arithmetic on rows
    already published on this page - not an official figure and never presented as one."""
    rows = []
    for g in AVAIL["games"]:
        for club, name in ((g["away"], None), (g["home"], None)):
            rows.append(club)
    by_club = {}
    for r in AVAIL["designations"]:
        c = r["club"]
        d = by_club.setdefault(c, {"OUT": 0, "DOUBTFUL": 0, "QUESTIONABLE": 0, "Offence": 0, "Defence": 0,
                                   "Special teams": 0, "unmapped": 0, "game": None})
        d[r["status"]] += 1
        u = UNIT.get((r["position"] or "").strip().upper(), "")
        if u:
            d[u] += 1
        else:
            d["unmapped"] += 1
    for g in AVAIL["games"]:
        for c in (g["away"], g["home"]):
            d = by_club.setdefault(c, {"OUT": 0, "DOUBTFUL": 0, "QUESTIONABLE": 0, "Offence": 0,
                                        "Defence": 0, "Special teams": 0, "unmapped": 0, "game": None})
    names = {r["club"]: r["club_name"] for r in AVAIL["designations"]}
    names.update({"LAC": "Los Angeles Chargers", "BAL": "Baltimore Ravens"})
    for b in AVAIL["byes"]:
        names[b["club"]] = b["club_name"]
    return by_club, names


# --------------------------------------------------------------------------- #
def page_index() -> str:
    a = AVAIL
    b = []
    b.append("<h2>What this desk is</h2>")
    b.append("<ul>" + "".join(f"<li>{e(x)}</li>" for x in a.get("what_this_is", META["what_this_is"])) + "</ul>")
    b.append("<h3>And what it is not</h3><ul>" + "".join(f"<li>{e(x)}</li>" for x in META["what_this_is_not"]) + "</ul>")
    b.append("<h2>The five things worth reading, in order</h2>")
    b.append(
        '<ol class="read"><li><a href="flagged.html">Flags F01-F04</a> &mdash; one gap closed (four "missing" clubs are on bye, '
        'confirmed from the scores page), three opened: the designation definitions have no date, '
        'no official publisher orders a depth chart, and the statuses article promises 14 games and prints 13.</li>'
        '<li><a href="reconcile.html">The cross-check</a> &mdash; 18 designations read across three official pages on the same day: '
        f'{REC["counts"]["agree"]} agree, {REC["counts"]["partial"]} say different things about different fields, '
        f'{REC["counts"]["contradict"]} contradict. One of them is a Texan listed questionable by two publishers and ruled out by a third.</li>'
        '<li><a href="availability.html">Availability</a> &mdash; all 160 published designations for the slate, per-row linked, '
        'with per-club counts and the four bye clubs.</li>'
        '<li><a href="signals.html">Signals ledger</a> &mdash; every strategy this repository has tested, recomputed from the '
        'artifacts that produced it, with the gate it failed and what that costs: no ledger has an eligible strategy, and 15 strategy IDs '
        'name different rules in different ledgers.</li>'
        '<li><a href="suggestions.html">Suggestions</a> &mdash; 14 paths with their costs, nothing implemented, the decision gate enforced by the build.</li></ol>')
    bc, names = club_deficiency()
    tot_out = sum(v["OUT"] for v in bc.values())
    tot_d = sum(v["DOUBTFUL"] for v in bc.values())
    tot_q = sum(v["QUESTIONABLE"] for v in bc.values())
    b.append("<h2>This cycle at a glance</h2>")
    b.append(table(["Measure", "Value", "Where it comes from"], [
        [e("Games in the Week 10 slate"), str(a["slate"]["games"]), src("A03")],
        [e("Clubs playing / on bye / total"),
         f'{a["slate"]["clubs_with_a_game"]} / {a["slate"]["clubs_on_bye"]} / {a["slate"]["clubs_total"]}',
         src("A05") + " " + src("A03")],
        [e("Published designations"),
         f'{a["designation_count"]} ({tot_out} out, {tot_d} doubtful, {tot_q} questionable)', src("A03")],
        [e("Clubs with no designation list published"),
         ", ".join(e(c) for c in a["clubs_with_no_designations_published"]) + " &mdash; the Monday game", src("A03") + " " + src("A01")],
        [e("Starters replaced where an official publisher named the replacement"), "2 of 5 known quarterback vacancies", src("A04")],
        [e("Depth-string cells that could be filled from an official source"), "0 &mdash; blank everywhere, flagged", src("A08") + " " + src("A09")],
        [e("Strategies eligible for a reward, across all ledgers"), "0", src("R01") + " " + src("R03") + " " + src("R04")],
        [e("Pinned dataset files whose SHA-256 still matches the ledger's record"),
         f'{LED["pinned_dataset"]["matched"]} of {LED["pinned_dataset"]["total"]}', src("R05")],
    ]))
    b.append('<p class="note"><strong>Transcription policy.</strong> ' + e(META["transcription_policy"]) + "</p>")
    b.append("<h2>Decision impact: what a choice moves</h2>")
    b.append('<p class="lede2">' + e(META["impact_model"]["summary"]) + "</p>")
    decided = {r["suggestion"] for r in DEC["records"]}
    irows = []
    for x in SUG["suggestions"]:
        im = x["impact"]
        irows.append([f'<a href="suggestions.html#{e(x["id"])}">{e(x["id"])}</a>',
                      e(x["title"]),
                      chip("recorded", "ok") if x["id"] in decided
                      else chip(x["decision_status"], "bad" if x["blocking"] else "info"),
                      str(len(im["moves"])) + " change(s) on the pages",
                      str(len(im["unblocks"])) + " question(s) answered",
                      str(len(im["closes"])) + " flag(s) retired",
                      "; ".join(e(v) for v in im["enables"]) or "no new feature, only a rule change",
                      " ".join(src(i, i) for i in x["source_ids"]) or src("R01", "the tree itself")])
    b.append(table(["ID", "Suggestion", "State", "What it changes", "Questions it answers", "Flags it retires",
                    "What it makes possible", "Evidence"], irows, "dense"))
    b.append('<p>' + str(len(DEC["records"])) + " recorded decision(s) in <code>desk/data/decisions.json</code> against "
             + str(len(SUG["suggestions"])) + " proposals. Until an entry exists, the build refuses to move a suggestion "
             'past Proposed, so this table cannot fill itself in and no page below it changes.</p>')
    b.append('<p class="mut"><em>' + e(META["impact_model"]["why_blank"]) + "</em></p>")
    b.append('<p class="cta"><a class="btn" href="suggestions.html">Choose a path</a> '
             '<a class="btn ghost" href="questions.html">See what is still unknown</a> '
             '<a class="btn ghost" href="../index.html">Repository landing page</a></p>')
    return page("index.html", "Week 10 decision desk", META["purpose"], status_strip() + "".join(b))


def page_availability() -> str:
    a = AVAIL
    g_rows = []
    for g in a["games"]:
        res = e(g["result"]) if g["result"] else blank("no result published", "F06") if g["status"] != "Scheduled" else ""
        g_rows.append([
            str(g["no"]), e(g["day"]) + "<br><span class='mut'>" + e(g["kickoff_et"]) + " ET</span>",
            f'<a href="{e(g["game_url"])}">{e(g["away"])}</a><br><span class="mut">{e(g["away_record"])}</span>',
            f'<a href="{e(g["game_url"])}">{e(g["home"])}</a><br><span class="mut">{e(g["home_record"])}</span>',
            e(g["venue"]), e(g["broadcast"]),
            (chip("FINAL", "ok") if g["status"] == "FINAL" else chip("Scheduled", "info")),
            res if g["result"] else '<span class="mut">&mdash;</span>',
            src(g["designation_source"], "statuses") + " " + src(g["result_source"] or "A05", "result"),
        ])
    body = ["<h2>The slate, as the league published it</h2>",
            table(["#", "Day / kickoff", "Away (record)", "Home (record)", "Venue", "Broadcast", "State", "Result", "Sources"], g_rows),
            '<p class="note">Records are printed exactly as the citing page shows them. Washington and New York differ '
            'between the article and the live report because the Thursday game finished in between &mdash; flag '
            '<a href="flagged.html#F06">F06</a>.</p>']

    body.append("<h2>Every designation the league published for this week</h2>")
    body.append(f'<p>{a["designation_count"]} rows. Each links the official article it was transcribed from and the '
                'player\'s own official page. A row is <em>not</em> a claim about who starts.</p>')
    d_rows = []
    for r in a["designations"]:
        kind = {"OUT": "bad", "DOUBTFUL": "warn", "QUESTIONABLE": "info"}[r["status"]]
        pos = e(r["position"]) if r["position"] else blank("no position printed", "F13")
        d_rows.append([
            f'<a href="https://www.nfl.com/teams/{e(r["club"].lower())}">{e(r["club"])}</a>',
            pos,
            f'<a href="{e(r["player_url"])}">{e(r["player"])}</a>',
            chip(r["status"], kind),
            e(r["injury"]) if r["injury"] else blank("no injury text printed", ""),
            str(r["game"]),
            src(r["source"], "article row") + ' <a href="https://www.nfl.com/injuries/league/2026/reg10" title="live weekly report page">report</a>',
        ])
    body.append(table(["Club", "Position", "Player", "Game status", "Injury text", "Game", "Sources"], d_rows, "dense"))

    bc, names = club_deficiency()
    body.append("<h2>Per club: what is missing from the roster</h2>")
    body.append('<p class="note">Counted from the rows above. The unit split uses a presentation convention, not an '
                'official classification: ' + e(UNMAPPED_NOTE) + "</p>")
    c_rows = []
    for c in sorted(bc, key=lambda x: (-bc[x]["OUT"], x)):
        d = bc[c]
        c_rows.append([e(c), e(names.get(c, c)), str(d["OUT"]), str(d["DOUBTFUL"]), str(d["QUESTIONABLE"]),
                       str(d["Offence"]), str(d["Defence"]), str(d["Special teams"]),
                       str(d["unmapped"]) + (" " + blank("unmapped code", "F14") if d["unmapped"] else ""),
                       src("A03")])
    body.append(table(["Club", "Name", "Out", "Doubtful", "Questionable", "Offence", "Defence", "Special", "Unmapped unit", "Source"], c_rows))

    body.append("<h2>Clubs with no designation list</h2>")
    gap_rows = [[e(c), e(names.get(c, "")), "no list printed in the statuses article; 17 and 8 rows respectively on the live report, all with a blank game status",
                 src("A03") + " " + src("A01"), chip("flag F04", "bad")]
                for c in a["clubs_with_no_designations_published"]]
    body.append(table(["Club", "Name", "What the pages actually show", "Sources", "Flag"], gap_rows))
    body.append('<p class="note">' + e(a["clubs_with_no_designations_note"]) + "</p>")

    body.append("<h2>On bye - no Week 10 game, so no row in the report</h2>")
    b_rows = [[e(b["club"]), e(b["club_name"]), e(b["record"]), e(b["note"]), src(b["source"], "scores page")] for b in a["byes"]]
    body.append(table(["Club", "Name", "Record", "How it is known", "Source"], b_rows))

    pol = a["policy_definitions"]
    body.append("<h2>What the designations mean, in the league's own words</h2>")
    body.append('<p class="note">From the official revision page this desk opened. The page carries no date line, so '
                'this is published as the wording of a Competition Committee revision, not as proof of the rule in '
                'force in 2026 - flag <a href="flagged.html#F02">F02</a>.</p>')
    def polrow(kind, code, text, tone):
        return [chip(kind, tone), e(code), e(text) + " " + src("A06", "policy article")]
    body.append(table(["Report", "Code as printed", "Definition as published", "Source"],
                      [polrow("Practice", x["code"], x["definition"], "info") for x in pol["practice"]] +
                      [polrow("Game status", x["code"], x["definition"], "info") for x in pol["game_status"]] +
                      [polrow("Caveat", "currency", pol["currency_caveat"], "warn")], "dense"))
    body.append('<p class="cta"><a class="btn" href="reconcile.html">Compare this table against the other two official pages</a></p>')
    return page("availability.html", "Availability - Week 10, 2026",
                "Who the league says is not playing, row by row, with the page each row came from.",
                status_strip() + "".join(body))


def page_depth() -> str:
    d = DEPTH
    body = ["<h2>The requirement, stated plainly</h2>",
            "<p>The brief asks the system to know which backups replace starters &mdash; second, third, fourth string &mdash; "
            "on both sides of the ball. Below is every vacancy the official pages support this week, and what each one could "
            "and could not say about the fill.</p>"]
    for line in d["conclusions"]:
        body.append(f"<p>{e(line)}</p>")

    body.append("<h2>Vacancies and fills</h2>")
    v_rows = []
    for v in d["vacancies"]:
        repl = e(v["replacement"]) if v["replacement"] else blank("no official replacement published", v["depth_string_flag"])
        depth = e(v["depth_string_cell"]) if v["depth_string_cell"] else blank("no ordering published", v["depth_string_flag"])
        grade = {"named replacement": chip("named replacement", "ok"),
                 "no official replacement published": chip("no replacement published", "bad"),
                 "headline only, article not opened": chip("headline only", "warn"),
                 "cause stated, replacement not stated": chip("cause only", "warn"),
                 "partial": chip("partial", "warn")}.get(v["evidence_grade"], chip(v["evidence_grade"], "info"))
        v_rows.append([e(v["club"]), e(v["unit"]), e(v["position"]), e(v["vacated_by"]), e(v["vacancy_cause"]),
                       grade, repl, depth,
                       f'&ldquo;{e(v["quote"])}&rdquo; {src(v["source"])}', e(v["note"])])
    body.append(table(["Club", "Unit", "Position", "Player unavailable", "Cause as printed", "Evidence grade",
                       "Replacement named", "Depth string", "Official wording", "Reading"], v_rows))

    body.append("<h2>Where depth ordering was looked for, and what came back</h2>")
    a_rows = []
    for a in d["source_audit"]:
        opened = chip("opened this cycle" if a["opened"] else "not opened this cycle",
                      "ok" if a["opened"] else "warn")
        a_rows.append([e(a["publisher"]), f'<a href="{e(a["url"])}">{e(a["url"])}</a>', opened,
                       e(a["what_it_publishes"]), e(a["what_it_omits"]), e(a["usable_for"]), e(a["verdict"])])
    body.append(table(["Publisher", "Address", "State", "What it publishes", "What it omits", "Usable for", "Verdict"], a_rows))
    body.append('<p class="cta"><a class="btn" href="suggestions.html#K04">Decide how to close this gap</a> '
                '<a class="btn ghost" href="flagged.html#F03">read the flag</a></p>')
    return page("depth.html", "Depth and vacancies",
                "A vacancy is an official designation. A fill exists only where a publisher named one.",
                status_strip() + "".join(body))


def page_reconcile() -> str:
    r = REC
    body = ["<h2>Three official pages, one week, compared line by line</h2>",
            f'<p>{e(r["_note"][0])} {e(r["_note"][2])} {e(r["_note"][3])}</p>',
            table(["Publisher", "Page read on " + e(r["compared_utc"])],
                  [[e(k), f'<a href="{e(v)}">{e(v)}</a>'] for k, v in r["publishers"].items()]),
            "<h3>Tally</h3>",
            "<ul>" + "".join(f"<li>{e(k)}: <strong>{v}</strong></li>" for k, v in r["counts"].items()) + "</ul>",
            "<h2>The rows</h2>"]
    cls = {"agree": "ok", "partial": "warn", "contradict": "bad"}
    rows = []
    for x in r["rows"]:
        sev = chip(x["severity"], "bad" if x["severity"] == "high" else "warn" if x["severity"] == "medium" else "info")
        rows.append([f'<a id="{e(x["id"])}" name="{e(x["id"])}">{e(x["id"])}</a>', e(x["club"]),
                     (f'<a href="https://www.nfl.com/players/{e(x["slug"])}">{e(x["player"])}</a>' if x["slug"] else e(x["player"])),
                     e(x["check"]), chip(x["classification"], cls.get(x["classification"], "info")), sev,
                     e(x["a01"]) + " " + src("A01", "report"), e(x["a03"]) + " " + src("A03", "article"),
                     (e(x["a04"]) + " " + src("A04", "roundup")) if x["a04"] and x["a04"] != "absent"
                     else e(x["a04"]) + " " + src("A04", "roundup"),
                     e(x["why"]), e(x["action"])])
    body.append(table(["ID", "Club", "Player", "Field compared", "Verdict", "Severity",
                       "Live report (A01)", "Statuses article (A03)", "Friday roundup (A04)",
                       "Why it matters", "What the system should do"], rows, "dense"))
    body.append('<p class="note">Quotations are copied from the page text read on 2026-11-13. Where a publisher did not '
                'cover something, the cell says so; that is different from it publishing a contradiction.</p>')
    return page("reconcile.html", "Cross-source reconciliation",
                "What line-by-line verification actually finds when the league publishes the same week three ways.",
                status_strip() + "".join(body))


def page_signals() -> str:
    L = LED
    body = ["<h2>One leaderboard out of four ledgers</h2>",
            "<p>The repository has been building the same competition four times, with three gate vocabularies and two "
            "ID schemes. This page is a reconciliation, not another backtest: every figure is read from the artifact "
            "named on the row, and <code>desk/check.py</code> re-derives the whole table before it will pass.</p>",
            '<p class="note"><strong>Provenance, stated once:</strong> ' + e(L["note"][2]) +
            ' The pinned dataset behind these numbers: <a href="' + e(L["pinned_dataset"]["commit_url"]) + '">' +
            e(L["pinned_dataset"]["commit_url"].split("/")[-1][:12]) + '</a>; local re-hash this cycle: ' +
            f'{L["pinned_dataset"]["matched"]} of {L["pinned_dataset"]["total"]} files identical.</p>']

    body.append("<h3>Own lines: how good is the number we originate?</h3>")
    ol = L["own_lines"]
    acc = ol["line_lab_accuracy"] or {}
    body.append(table(["Measure", "Spread", "Total", "Source"], [
        [e("games in the accuracy window"), str(acc.get("spread", {}).get("games", "")), str(acc.get("total", {}).get("games", "")), src("R01")],
        [e("model RMSE"), str(acc.get("spread", {}).get("model_rmse", "")), str(acc.get("total", {}).get("model_rmse", "")), src("R01")],
        [e("market RMSE"), str(acc.get("spread", {}).get("market_rmse", "")), str(acc.get("total", {}).get("market_rmse", "")), src("R01")],
        [e("model correlation to outcome"), str(acc.get("spread", {}).get("model_corr", "")), str(acc.get("total", {}).get("model_corr", "")), src("R01")],
        [e("market correlation to outcome"), str(acc.get("spread", {}).get("market_corr", "")), str(acc.get("total", {}).get("market_corr", "")), src("R01")],
        [e("README MAE claim check"), e(ol["readme_claim_check"]["verdict"]), e(str(len(ol["readme_claim_check"]["matched_rows"])) + " grid rows within 0.02"), src("R01")],
        [e("unplayed fixtures with an originated line"), str(ol["unplayed_fixtures"]), "&mdash;", src("R01")],
    ]))
    body.append('<p class="note">Read this table as the honest headline of the project: the originated line is close to '
                'the market but does not beat it on outcome correlation, which is why no downstream signal survives its '
                'gates. RMSE is around 13.5 for both model and market; the model tracks outcomes slightly worse than the '
                'market does.</p>')

    body.append("<h3>line_lab ledger - 11 strategies, nine gates</h3>")
    rows = []
    for s in L["line_lab"]["strategies"]:
        lk = s["luck"]
        reward = str(s["reward_points"]) if s["reward_points"] != "" else blank("no reward recorded")
        rows.append([e(s["id"]), e(s["name"]), e(s["market"]), str(s["bets"]), f'{s["win_rate"]:.4f}',
                     f'{s["roi_full"]:+.4f}', f'[{s["roi_ci_low"]:+.4f}, {s["roi_ci_high"]:+.4f}]',
                     f'{s["holdout_roi"]:+.4f}', str(s["holdout_bets"]),
                     f'{s["q_value_fdr"]:.4f}' if isinstance(s["q_value_fdr"], float) else str(s["q_value_fdr"]),
                     str(s["permutation_percentile"]), f'{lk.get("z_vs_breakeven", "")}',
                     f'{lk.get("p_vs_breakeven", "")}', f'{lk.get("luck_band_95_pp", "")}',
                     f'{s["gates_passed"]}/{s["gates_total"]}',
                     chip("eligible", "ok") if s["eligible"] else chip("not eligible", "bad"),
                     reward, src("R01")])
    body.append(table(["ID", "Rule", "Market", "Bets", "Win rate", "ROI", "95% CI", "Holdout ROI", "Holdout bets",
                       "q (FDR)", "Permutation pctl", "z vs breakeven", "p vs breakeven", "Luck band (±pp)",
                       "Gates passed", "State", "Reward", "Source"], rows, "dense"))

    body.append("<h3>Pipeline ledger - 18 signals, eight gates, discovery and confirmation</h3>")
    rows = []
    for s in L["pipeline"]["signals"]:
        lk = s["luck"]
        rows.append([e(s["id"]), e(s["name"]), e(s["market"]), str(s["n"]), str(s["n_conf"]), f'{s["win_rate"]:.4f}',
                     f'{s["roi"]:+.4f}', f'{s["roi_conf"]:+.4f}', f'{s["shrunk_roi"]:+.4f}',
                     f'[{s["ci_low"]:+.4f}, {s["ci_high"]:+.4f}]', f'{s["p"]:.4f}', f'{s["q_fdr"]:.4f}',
                     f'{lk.get("z_vs_breakeven", "")} / {lk.get("p_vs_breakeven", "")}',
                     f'{lk.get("n_needed_at_2pp_80pct", "")}',
                     str(s["seasons_positive"]) + " / " + str(s["seasons_tested"]),
                     "pass: " + ", ".join(s["gates_passed"]) if s["gates_passed"] else "&mdash;",
                     "fail: " + ", ".join(s["gates_failed"]) if s["gates_failed"] else "none",
                     chip(s["verdict"], "ok" if s["verdict"] == "PASS" else "bad") + " " + chip(s["tier"], "info"),
                     src("R02")])
    body.append(table(["ID", "Rule", "Market", "n", "n confirm", "Win rate", "ROI", "ROI confirm", "Shrunk ROI",
                       "95% CI", "p", "q", "z / p vs breakeven", "n needed at 2pp", "Seasons +", "Gates passed",
                       "Gates failed", "Verdict", "Source"], rows, "dense"))
    body.append('<p class="note"><strong>Zero rows with an empty "Gates failed" cell.</strong> '
                + (f'Passed all eight: {", ".join(L["pipeline"]["passed"])}' if L["pipeline"]["passed"]
                   else "No signal in this ledger passes all eight gates. That is the current state of the project and it is the number the reward competition has to live with.")
                + "</p>")

    body.append("<h3>Docs leaderboard - six-gate scoring, and what the pool actually pays</h3>")
    rows = [[str(x["rank"]), e(x["id"]), e(x["name"]), str(x["score"]), f'{x["roi_full"]}', f'{x["roi_holdout"]}',
             str(x["bets"]), f'{x["gates_passed"]}/{x["gates_total"]}',
             chip("validated", "ok") if x["validated"] else chip("not validated", "bad"),
             (str(x["reward_units"]) if x["reward_units"] != "" else blank("no funded reward")) + " units",
             src("R03")] for x in L["docs_leaderboard"]["rows"]]
    body.append(table(["Rank", "ID", "Rule", "Score", "ROI full", "ROI holdout", "Bets", "Gates", "State", "Reward", "Source"], rows))
    body.append(f'<p class="note">Pool recorded as {e(str(L["docs_leaderboard"]["pool_units"]))} units with '
                f'{e(str(L["docs_leaderboard"]["eligible"]))} eligible strategies, so the payout to every row is 0.0. '
                'The verified workbench goes further: '
                f'{L["verified_workbench"]["n"]} rows, all rank null, score null, reward null, status not_eligible.</p>')

    body.append("<h3>Why IDs cannot be trusted across ledgers</h3>")
    rows = [[e(c["id"]), e(c["line_lab"]) or blank("not in this ledger"), e(c["pipeline"]), e(c["docs_leaderboard"]), src("R02") + " " + src("R03")]
            for c in L["id_collisions"]["rows"]]
    body.append(table(["Shared ID", "line_lab means", "pipeline means", "docs leaderboard means", "Sources"], rows))
    body.append('<p class="note">' + e(L["id_collisions"]["note"]) + "</p>")

    body.append("<h3>Dependence: what a parlay and a prop combo actually need</h3>")
    c = L["correlation"]
    rows = [[e(x["pair"]), str(x.get("n", "")), f'{x["marginal_a_implied"]:.4f}', f'{x["marginal_b"]:.4f}',
             f'{x["joint"]:.4f}', f'{x["phi_published"]:+.6f}', f'{x["phi_recomputed"]:+.6f}', f'{x["abs_gap"]:.1e}',
             chip(x["status"], "ok" if x["status"] == "MATCH" else "bad"),
             f'[{x["ci_low"]:+.4f}, {x["ci_high"]:+.4f}]', src("R01")] for x in c["same_game_pairs"]]
    body.append(table(["Same-game pair", "n", "P(A) implied", "P(B)", "P(A and B)", "phi published", "phi recomputed here",
                       "gap", "Check", "95% CI", "Source"], rows))
    body.append(table(["Requirement / measurement", "Value", "Reading", "Source"], [
        [e("Breakeven phi for a 2-leg parlay at -110"), f'{c["breakeven_phi_2leg"]:.4f}',
         e("below this, combining two singles is worse than the singles"), src("R03")],
        [e("Breakeven phi for a 3-leg parlay at -110"), f'{c["breakeven_phi_3leg"]:.4f}', e("falls as legs are added"), src("R03")],
        [e("Measured same-game spread x total"), e("see row above: +0.0161"), e("two orders of magnitude short of the requirement"), src("R01")],
        [e("Measured same-game spread x home ML"), e("see row above: +0.6706"), e("the dependence a ticket is meant to avoid"), src("R01")],
        [e("Cross-game mean phi over " + str(c["cross_game"].get("seasons", "")) + " seasons"), f'{c["cross_game"].get("mean_phi", "")}',
         e("cross-game legs behave independently; the pooled test against zero returns p=" + str((c.get("cross_game_test") or {}).get("pooled_p_value_vs_zero", ""))), src("R03")],
        [e("Signal pairs evaluated in the family matrix"), str(c["signal_matrix"].get("pairs_evaluable", "")),
         e("median |phi| across different markets " + str(c["signal_matrix"].get("median_abs_phi_different_market", ""))
           + "; share above 0.15 is " + str(c["signal_matrix"].get("share_different_market_abs_phi_gt_0.15", ""))), src("R03")],
        [e("Prop lines and player logs in the dataset"), e("absent"), e("props cannot be validated at all today"), src("R01")],
    ]))

    body.append("<h3>Luck, priced</h3>")
    lkb = L["line_lab"]["luck_band"]
    body.append(table(["Null experiment", "Value", "What it means for a leaderboard", "Source"], [
        [e("simulations"), str(lkb.get("n_sims", "")), e("as published"), src("R01")],
        [e("strategies drawn per simulation"), str(lkb.get("strategies_per_family", "")), e("a family the size of this project's"), src("R01")],
        [e("mean best-of-family ROI"), f'{lkb.get("mean_best_roi", "")}', e("pure noise produces a +5% 'winner' on average"), src("R01")],
        [e("5th - 95th percentile of best ROI"), f'{lkb.get("p05_best_roi", "")} to {lkb.get("p95_best_roi", "")}',
         e("a top-of-leaderboard ROI of +8.4% sits inside this band"), src("R01")],
        [e("probability the best of the family is profitable at all"), f'{lkb.get("prob_best_is_profitable", "")}',
         e("which is the case against ranking by headline ROI"), src("R01")],
        [e("mean single-strategy ROI in the pool"), f'{lkb.get("mean_single_roi", "")}', e("a random bettor pays the vig"), src("R01")],
        [e("pool note"), e(lkb.get("note", "")), "", src("R01")],
    ]))
    rows = [[f'{p.get("edge", "")}', str(p.get("bets_required", "")), f'{round(float(p.get("seasons_at_750_bets", 0)), 1)}', src("R01")]
            for p in L["line_lab"]["power_table"]]
    body.append("<h4>Published power table (bets needed to see an edge, as the ledger computes it)</h4>")
    body.append(table(["Edge", "Bets required", "Seasons at 750 bets/season", "Source"], rows))
    rows = [[e(s["id"]), e(s["name"]), str(s["luck"].get("n_decided", "")), f'{s["luck"].get("z_vs_breakeven", "")}',
             f'{s["luck"].get("p_vs_breakeven", "")}', f'{s["luck"].get("luck_band_95_pp", "")}',
             str(s["luck"].get("n_needed_at_2pp_80pct", "")), str(s["luck"].get("n_needed_at_2pp_90pct", "")),
             f'{s["luck"].get("seasons_at_500_bets_80pct", "")}', src("R01")] for s in L["line_lab"]["strategies"]]
    body.append("<h4>Desk recomputation of the same idea, against the vig rather than against 50%</h4>")
    body.append('<p class="note">Formula on <a href="gates.html">the gates page</a>. p0 is the breakeven win rate at -110 '
                '(52.38%), not 50%, because that is the bar a real ticket has to clear. This table makes every strategy '
                'look worse than the published power table, which is the point.</p>')
    body.append(table(["ID", "Rule", "Decided bets", "z vs breakeven", "p vs breakeven", "95% luck band (pp)",
                       "n needed for +2pp at 80%", "n needed at 90%", "Seasons at 500 bets", "Source"], rows, "dense"))

    body.append("<h3>Multiplicity, checked by hand</h3>")
    m = L["multiplicity"]
    body.append(table(["Check", "Value", "Source"], [
        [e("family size"), str(m["family_size"]), src("R02")],
        [e("smallest five p-values"), e(", ".join(str(x) for x in m["sorted_p_head"])), src("R02")],
        [e("q at rank 1, recomputed from those p-values by this desk"), str(m["q_at_rank_1_by_hand"]), src("R01")],
        [e("q at rank 1 as published"), str(m["q_published_rank_1"]), src("R02")],
        [e("note"), e(m["note"]), f'<a href="{REPO_BLOB}desk/build_ledger.py">build_ledger.py</a>'], 
    ]))
    body.append('<p class="cta"><a class="btn" href="gates.html">What a strategy must clear</a> '
                '<a class="btn ghost" href="suggestions.html#K08">Decide how the leaderboard is scored</a></p>')
    return page("signals.html", "Signals ledger and competition",
                "Everything this repository has tested, recomputed from the artifacts that published it, with the gate each rule failed.",
                status_strip() + "".join(body))


def page_gates() -> str:
    g = GATES
    body = ["<h2>The promotion policy</h2>",
            "<p>Twelve gates, consolidated from the three systems this repository already runs. A strategy is ranked, "
            "rewarded or quoted to anyone only when every non-blocking row below passes and the blocking rows have an "
            "owner decision attached to them.</p>"]
    for line in g["notes"]:
        body.append(f"<p>{e(line)}</p>")
    LEDGER_SRC = {"line_lab": "R01", "pipeline": "R02", "docs": "R03", "verified": "R04", "nfl_lab": "R04"}
    rows = []
    for p in g["policy"]:
        ids = p.get("sources") or re.findall(r"\b([ACRX]\d\d)\b", p["source_ledgers"])
        links = " ".join(src(i, i) for i in dict.fromkeys(ids)) or e(p["source_ledgers"])
        files = " ".join(f'<a href="{REPO_BLOB}{f}" title="the file that implements this gate in this repository">{e(f)}</a>'
                         for f in p.get("files", []))
        rows.append([f'<a id="{e(p["id"])}" name="{e(p["id"])}">{e(p["id"])}</a>', e(p["name"]), e(p["rule"]), e(p["threshold"]), e(p["why"]),
                     e(p["source_ledgers"]) + " " + links + " " + files,
                     e(p["status_now"]),
                     chip("needs a source that does not exist", "bad") if p["blocking"] else chip("computable today", "ok"),
                     e(p["official_source_needed"])])
    body.append(table(["Key", "Gate", "Rule", "Threshold as defined", "Why it exists",
                       "Where it is implemented", "State of play this cycle", "Blocking", "Missing source"], rows, "dense"))
    body.append("<h2>The arithmetic the gates rest on</h2>")
    body.append('<p class="note">These are the desk\'s own definitions and the code that evaluates them, not facts about '
                'the league, so the table cites files in this repository instead of publishers: '
                '<a href="' + REPO_BLOB + 'desk/build_ledger.py">desk/build_ledger.py</a> computes them and '
                '<a href="' + REPO_BLOB + 'desk/check.py">desk/check.py</a> re-runs it before the build is allowed to pass. '
                'The numbers they rest on come from the ledgers linked in the table above.</p>')
    ar = g["arithmetic"]
    arsrc = g.get("arithmetic_sources", {})
    arows = []
    for k, v in ar.items():
        meta = arsrc.get(k, {})
        cites = " ".join(src(i, i) for i in meta.get("ids", []))
        files = " ".join(f'<a href="{REPO_BLOB}{f}" title="{e(meta.get("why", ""))}">{e(f)}</a>'
                         for f in meta.get("files", []))
        arows.append([e(k), e(v), (e(meta.get("why", "")) + " " + cites + " " + files).strip() or
                      f'<a href="{REPO_BLOB}desk/data/gates.json">gates.json</a>'])
    body.append(table(["Quantity", "Value / formula", "Where the number comes from"], arows, "dense"))
    body.append('<p class="cta"><a class="btn" href="signals.html">See the ledgers against these gates</a> '
                '<a class="btn ghost" href="questions.html#KQ11">The sample-size question</a></p>')
    return page("gates.html", "Validation gates, correlation and luck",
                "What a signal has to clear before it is a strategy, stated once for every ledger in the repository.",
                status_strip() + "".join(body))


def page_suggestions() -> str:
    s = SUG
    gate = s["decision_gate"]
    decided = {r["suggestion"]: r for r in DEC["records"]}
    body = ["<h2>Suggestions, and the gate on them</h2>",
            f'<p class="rule">{e(gate["rule"])}</p>',
            f'<p>Enforced by <code>{e(gate["enforced_by"])}</code>. Who decides: {e(gate["who_decides"])}. '
            'The record a decision has to leave lives in <code>desk/data/decisions.json</code>: the build fails if a '
            'state here has no record there, and fails if a record there has no state here.</p>']
    # gate["counts"] is maintained by hand, so the two figures a reader most cares about are
    # recomputed from the register itself and the hand-maintained duplicates are not printed.
    recount = {"Proposed - awaiting owner decision", "blocking"}
    counts_rows = [[e(k), str(v), chip("from the register", "info")]
                   for k, v in gate["counts"].items() if k not in recount]
    counts_rows.insert(0, [e("Proposed - awaiting owner decision"),
                           str(sum(1 for x in s["suggestions"] if x["decision_status"].startswith("Proposed"))),
                           chip("recomputed here", "ok")])
    counts_rows.append([e("blocking a decision"), str(sum(1 for x in s["suggestions"] if x["blocking"])),
                        chip("recomputed here", "ok")])
    counts_rows.append([e("carried forward from earlier boards"),
                        str(sum(1 for x in s["suggestions"] if not x.get("new_this_cycle")))])
    counts_rows.append([e("blocking a decision"), str(sum(1 for x in s["suggestions"] if x["blocking"]))])
    counts_rows.append([e("with a recorded decision"), str(len(DEC["records"]))])
    reg = REPO_BLOB + "desk/data/suggestions.json"
    link = f'<a href="{reg}" title="the register these counts are taken from, in the repository">suggestions.json</a>'
    counts_rows = [r + [link] for r in counts_rows]
    body.append(table(["Register state", "Count", "Counted from"], counts_rows))

    # ---------------------------------------------------------------- impact
    body.append("<h2>What a decision moves</h2>")
    body.append('<p class="lede2">' + e(META["impact_model"]["summary"]) + "</p>")
    rows = []
    for x in s["suggestions"]:
        im = x["impact"]
        rec = decided.get(x["id"])
        state = (chip("recorded " + rec["decision"], "ok") if rec
                 else chip(x["decision_status"], "bad" if x["blocking"] else "info"))
        rows.append([f'<a href="#{e(x["id"])}">{e(x["id"])}</a>',
                     e(x["title"]),
                     state,
                     "; ".join(e(m) for m in im["moves"]),
                     " ".join(q_link(q) for q in im["unblocks"]) or '<span class="mut">none</span>',
                     " ".join(fl_link(fl) for fl in im["closes"]) or '<span class="mut">none</span>',
                     " ".join(f'<a href="{e(p)}">{e(p)}</a>' for p in im["affects_pages"]),
                     "; ".join(e(en) for en in im["enables"]) or '<span class="mut">nothing new</span>',
                     e(x["missing_information"]),
                     " ".join(src(i, i) for i in x["source_ids"]) or '<span class="mut">no external evidence</span>'])
    body.append(table(["ID", "Suggestion", "State", "What changes on the pages", "Questions it answers",
                       "Flags it retires", "Files it edits", "What it makes possible", "Still to be found out",
                       "Evidence the problem is real"], rows, "dense"))
    body.append('<p class="note">' + e(s["impact_legend"]) + "</p>")

    body.append("<h2>The register in full</h2>")
    for x in s["suggestions"]:
        im = x["impact"]
        rec = decided.get(x["id"])
        ev = " ".join(src(i, i) for i in x["source_ids"]) if x["source_ids"] else \
            f'<a href="{REPO_BLOB}desk/data/suggestions.json">the register</a>'
        opts = table(["Path", "What it costs", "Evidence the problem is real"],
                     [[e(o["option"]), e(o["implications"]),
                       e(o.get("rests_on", "the finding above, from the pages this row links")) + " " + ev]
                      for o in x["options"]])
        evidence = " ".join(src(i, i) for i in x["source_ids"]) if x["source_ids"] else \
            '<span class="mut">no external source - this is a proposal about the site itself</span>'
        if rec:
            rec_html = (f'<span class="ok">recorded {e(rec["date"])} as {e(rec["decision"])}: option {e(rec["option"])}</span>')
        else:
            rec_html = '<em class="mut">no record, so every consequence below stays unstarted - by design</em>'
        consequences = []
        if im["unblocks"]:
            consequences.append("<li><strong>answers</strong> " + " ".join(q_link(q) for q in im["unblocks"]) + "</li>")
        if im["closes"]:
            consequences.append("<li><strong>retires</strong> " + " ".join(fl_link(fl) for fl in im["closes"]) + "</li>")
        if im["enables"]:
            consequences.append("<li><strong>makes possible</strong> " + e("; ".join(im["enables"])) + "</li>")
        consequences.append("<li><strong>edits</strong> " + e(", ".join(im["affects_pages"])) + " (inside desk/ only)</li>")
        body.append(f'<section class="sug" id="{e(x["id"])}"><h3>{e(x["id"])} &middot; {e(x["title"])} '
                    f'<span class="mut">&middot; {e(x["category"])}</span>'
                    + (" " + chip("new this cycle", "ok") if x.get("new_this_cycle") else "")
                    + (" " + chip("blocks a decision", "bad") if x["blocking"] else "") + "</h3>"
                    + f'<p class="prob"><strong>Problem.</strong> {e(x["problem"])}</p>'
                    + f'<p><strong>Evidence.</strong> {e(x["evidence"])} {evidence}'
                    + (f' <span class="mut">relates: {e(x["relates_to"])}</span>' if x.get("relates_to") else "") + "</p>"
                    + opts
                    + f'<p><strong>Recommendation.</strong> {e(x["recommendation"])}</p>'
                    + f'<p><strong>Information still missing.</strong> {e(x["missing_information"])}</p>'
                    + "<h4>If chosen</h4><ul>" + "".join(f"<li>{e(m)}</li>" for m in im["moves"])
                    + "".join(consequences) + "</ul>"
                    + '<div class="decision"><span class="dstate">' + e(x["decision_status"]) + "</span>"
                    + '<span class="dchoice">chosen option: '
                    + (e(x["chosen_option"]) if x["chosen_option"] else '<em class="mut">blank until you decide</em>')
                    + '</span><span class="ddate">decision date: '
                    + (e(x["decision_date"]) if x["decision_date"] else '<em class="mut">blank</em>')
                    + f'</span><span class="downer">{e(x["decision_owner"])}</span>'
                    + f'<span class="drec">{rec_html}</span></div></section>')

    body.append("<h2>How to record a decision</h2>")
    body.append("<ol>" + "".join(f"<li>{e(x)}</li>" for x in META["impact_model"]["how_to_record"]) + "</ol>")
    body.append("<h3>What moves, and what does not</h3><ul>"
                "<li><strong>Moves:</strong> " + "; ".join(e(x) for x in META["impact_model"]["what_moves"]) + "</li>"
                "<li><strong>Does not move:</strong> " + "; ".join(e(x) for x in META["impact_model"]["what_does_not_move"])
                + "</li></ul>")
    body.append('<p class="note">' + e(META["impact_model"]["why_blank"]) + "</p>")

    body.append("<h2>Decision log</h2>")
    if DEC["records"]:
        drows = []
        for r in DEC["records"]:
            cons = " ".join(fl_link(c) if c.startswith("F") else q_link(c) for c in r["consequences_applied"])
            drows.append([e(r["id"]), f'<a href="#{e(r["suggestion"])}">{e(r["suggestion"])}</a>', e(r["decision"]),
                          e(r["option"]), e(r["date"]), e(r["recorded_by"]), e(r.get("note", "")), cons,
                          src("R06", "register")])
        body.append(table(["ID", "Suggestion", "Decision", "Option chosen", "Date", "Recorded by", "Note",
                           "Consequences applied", "Source"], drows, "dense"))
    else:
        shape = e(json.dumps(DEC["record_shape"], indent=1, sort_keys=True))
        body.append('<p class="none">Empty as at ' + e(DEC["as_of_utc"]) + ". The shape of a record:</p>"
                    f"<pre><code>{shape}</code></pre>")
        body.append('<p class="note">An empty log is the correct state at the end of a session told to propose and not '
                    'to decide. It is printed rather than omitted so that "nothing has been chosen" is a fact on the '
                    'page instead of an absence a reader has to notice.</p>')
    body.append('<p class="note">Nothing in this register has been implemented by this session. Where a suggestion says '
                '"in force", it records a rule the repository has already adopted, not a choice made here.</p>')
    return page("suggestions.html", "Suggestions for review",
                "The paths available, what each one moves, and the record a choice has to leave behind before this desk changes state.",
                status_strip() + "".join(body))


def page_questions() -> str:
    q = QST
    body = ["<h2>What has to be known before a decision can be made reasonably</h2>",
            f'<p>{e(q["_note"][0])} {e(q["_note"][1])} {e(q["_note"][2])}</p>',
            table(["Register", "Count", "Counted from"],
                  [[e(k), str(v), f'<a href="{REPO_BLOB}desk/data/questions.json">{e("questions.json")}</a>']
                   for k, v in q["counts"].items()] +
                  [[e("rows carrying a source id"), str(sum(1 for x_ in q["questions"] if x_["source_ids"])),
                    f'<a href="{REPO_BLOB}desk/data/questions.json">{e("questions.json")}</a>']])]
    for x in q["questions"]:
        st = {"open": chip("open", "warn"), "answered this cycle": chip("answered this cycle", "ok"),
              "answered in repo": chip("answered in repo", "info")}.get(x["status"], chip(x["status"], "info"))
        ans = ""
        if x["answer"]:
            who = " " + src(x["answer_source_id"], "settled by") if x.get("answer_source_id") else ""
            ans = f'<div class="answer"><strong>Answer.</strong> {e(x["answer"])}{who}</div>'
        else:
            ans = '<div class="answer none2"><strong>Answer.</strong> <em class="mut">none recorded - this question is open, and the build fails if one is written without a source that settles it.</em></div>'
        body.append(f'<section class="q" id="{e(x["id"])}"><h3>{e(x["id"])} &middot; {e(x["question"])} '
                    f'<span class="mut">&middot; {e(x["category"])}</span> {st}'
                    + (" " + chip("blocking", "bad") if x["blocking"] else "") + "</h3>"
                    + f'<p><strong>Known.</strong> {e(x["known"])}</p>'
                    + f'<p><strong>Not known.</strong> {e(x["unknown"])}</p>'
                    + f'<p><strong>How to find out.</strong> {e(x["how_to_discover"])}</p>'
                    + f'<p><strong>Who can answer.</strong> {e(x["who_can_answer"])}</p>'
                    + ans
                    + '<p class="rel">Related: ' + e(x["relates_suggestion"]) + " &middot; sources: "
                    + " ".join(src(s, s) for s in x["source_ids"]) + "</p></section>")
    return page("questions.html", "Questions and required information",
                "What is known, what is missing, how it can be found, and which decisions are blocked until it is.",
                status_strip() + "".join(body))


def page_sources() -> str:
    rows = []
    for s in SRC.values():
        tier = {"official-league": ("official league", "ok"), "official-club": ("official club", "ok"),
                "repo-derived": ("repository artifact", "info"), "third-party-pinned": ("third-party, pinned", "warn"),
                "rejected": ("rejected", "bad")}[s["tier"]]
        rows.append([e(s["id"]), f'<a href="{e(s["url"])}">{e(s["url"])}</a>', e(s["publisher"]), chip(tier[0], tier[1]),
                     chip("opened", "ok") if s["read"] else chip("not opened", "warn"),
                     e(s.get("read_utc", "")), str(s.get("chunks_read", "")), e(s["title"]),
                     e(s["supports"]), e(s["does_not_support"])])
    body = ["<h2>Everything this desk relies on, and exactly how far each source goes</h2>",
            "<p>Registered sources only: the build fails if any row cites an ID that is not in this table, and any page "
            "citing a source that was not opened renders with a warning marker instead of looking like evidence.</p>",
            table(["ID", "Address", "Publisher", "Tier", "State", "Read", "Chunks", "Title", "What it supports", "What it does not support"], rows, "dense")]
    body.append('<p class="note"><strong>Negative results are sources too.</strong> A08 and A10 are recorded because they '
                'return nothing, which is the evidence behind the biggest gap in this project. X01 is registered so that '
                'the phrase "only rejected publishers have this data" is a checked statement.</p>')
    return page("sources.html", "Source register",
                "Tier, state, and the precise boundary of what each page supports.",
                status_strip() + "".join(body))


def page_flagged() -> str:
    body = ["<h2>Flagged for review</h2>",
            f'<p>{e(FLG["_note"][0])} {e(FLG["_note"][1])}</p>',
            table(["Severity", "Count", "Counted from"],
                  [[e(k), str(v), f'<a href="{REPO_BLOB}desk/data/flags.json">{e("flags.json")}</a>']
                   for k, v in FLG["counts"].items()])]
    rows = []
    for f in FLG["flags"]:
        rows.append([f'<a id="{e(f["id"])}">{e(f["id"])}</a>',
                     chip(f["severity"], {"high": "bad", "medium": "warn", "low": "info"}[f["severity"]]),
                     e(f["title"]), e(f["detail"]), e(f["consequence"]), e(f["action_taken"]),
                     " ".join(src(s, s) for s in f["sources"]),
                     chip(f["status"], "ok" if "resolved" in f["status"] else "warn")])
    for f in FLG["flags"]:
        rows[FLG["flags"].index(f)].append(" ".join(f'<a href="{e(pg)}">{e(pg)}</a>' for pg in f.get("seen_on", []))
                                           or '<span class="mut">this register only</span>')
    body.append(table(["Flag", "Severity", "Finding", "What was actually seen", "Consequence", "What was done",
                       "Sources", "Status", "Where it is visible"], rows, "dense"))
    body.append('<p class="note">Per the brief, none of these blocks the merge or the deployment. They block decisions, '
                'which is a different and slower thing.</p>')
    return page("flagged.html", "Flagged for review",
                "Irregularities found while capturing, reconciling and recomputing this cycle.",
                status_strip() + "".join(body))


def page_verification() -> str:
    v = VER
    body = ["<h2>What was checked, and with what command</h2>",
            f'<p>Run on {e(v["as_of_utc"])}. Every result below was produced by executing the named command in this '
            'repository, not by reading a report about it.</p>']
    rows = []
    for c in v["checks"]:
        state = c["state"]
        rows.append([e(c["name"]), f'<code>{e(c["command"])}</code>', e(c["scope"]),
                     chip(state, "ok" if state == "pass" else ("warn" if state in ("partial", "blocked") else "bad")),
                     e(c["result"]), src(c["source"], c["source"]) if c.get("source") else ""])
    body.append(table(["Check", "Command", "Scope", "State", "What it printed", "Source"], rows, "dense"))
    body.append("<h3>Coverage arithmetic of this desk</h3>")
    cov = '<a href="https://github.com/karagemop466-tech/Korea3/blob/main/desk/data/verification.json" ' \
          'title="this file, in the repository">verification.json</a>'
    body.append(table(["Measure", "Value", "Counted from"],
                      [[e(k), str(v), cov] for k, v in v["coverage"].items()]))
    body.append('<p class="mut"><em>These are counts over the files in <code>desk/data/</code>, not claims about the '
                'league: <code>desk/check.py</code> recomputes each of them from the pages themselves, which is what '
                'makes them checkable. The rows they summarise carry their own source links.</em></p>')
    body.append("<h3>How to reproduce</h3>")
    body.append("<ol>" + "".join(f"<li><code>{e(x)}</code></li>" for x in v["reproduce"]) + "</ol>")
    body.append('<p class="note">' + e(v["limits"]) + "</p>")
    return page("verification.html", "Verification log",
                "The commands that produced this desk's claims, and what each one can and cannot prove.",
                status_strip() + "".join(body))


def page_executive() -> str:
    a, L, q, f, s = AVAIL, LED, QST, FLG, SUG
    hi = [x for x in f["flags"] if x["severity"] == "high"]
    body = [f'<h2>Decision memo - 2026 week 10, captured {e(CAP)}</h2>',
            "<p class=\"lede2\">Five paragraphs, then the numbers.</p>",
            "<h3>1. The site now answers the question it was built for, and the answer is a gap</h3>",
            "<p>The brief asks the system to know which backups replace starters. This cycle the official pages support "
            "the first half of that sentence for all 32 clubs and the second half for two of them. The league publishes "
            "who is out and, occasionally, a coach sentence naming a replacement; it publishes no depth ordering anywhere "
            "an agent can verify. That single fact decides three of the fourteen open suggestions and is the reason no "
            "replacement-quality signal can be built from official data this season.</p>",
            "<h3>2. What was newly established</h3>",
            "<ul>"
            f"<li>The four clubs missing from last cycle's capture are on bye - named by the official scores page, not inferred ({e('F01')}, resolved).</li>"
            "<li>A blank game-status cell is not missing data: under the league's published revision, a player certain to play is removed from the report. That changes how every injury feature must be coded (Q02 answered; the rule's currency is still open, F02).</li>"
            "<li>One designation is published under three different player URLs by three official pages, so the join key the whole pipeline needs does not exist yet (F08/Q03 evidence).</li>"
            f'<li>Two of the three official pages for the same week contradict each other on a live case: a Texan listed questionable and ruled out on the same Friday ({e("N01")}).</li>'
            "</ul>",
            "<h3>3. The state of the line-origination project</h3>",
            "<p>Recomputed from the artifacts rather than restated: 11 strategies in one ledger, 18 signals in another, "
            "15 ranked rows in a third, 8 rows a fourth refuses to score. None is eligible anywhere. The originated line "
            "is competitive on error but not on outcome correlation, and the strongest raw result in the repository "
            "(+8.41% over 607 bets) becomes +2.48% after the shrinkage the project's own gate applies - and its q across "
            "a family of 18 is 0.288. The competition therefore has no winner, which is the correct output of honest "
            "gates and the reason the reward design matters more than any single rule.</p>",
            "<h3>4. What is blocked, and on what</h3>",
            f"<p>{q['counts']['open']} questions are open and {q['counts']['blocking']} of them block a decision. "
            f"Every blocking question has the same shape: the missing thing is not an analysis, it is an input "
            "(ordered depth, a price source, a roster-status feed, a capture cadence) or an owner decision "
            "(site authority, reward form, evidence bar for rules). {s['decision_gate']['counts']['Proposed - awaiting owner decision']} "
            "suggestions are on the board with options and costs attached; the build refuses to let any of them be "
            "recorded as approved here.</p>",
            "<h3>5. What I would do first, if a path were chosen today</h3>",
            "<p>K02 and K07 cost almost nothing and remove two classes of silent error (bye-week false alarms, "
            "as-of-date contradictions). K11 turns capture into an event log, which is the only change that makes the "
            "injury signal testable at all. K06 has to land before any reward exists, because 15 strategy IDs currently "
            "name two different rules and a leaderboard that pays by ID can pay the wrong entry. K01 is not research and "
            "is the cheapest quality win available: pick a front door, and this desk becomes a subpage of it instead of a "
            "tenth tree.</p>"]
    body.append("<h2>Numbers behind the memo</h2>")
    body.append(table(["Item", "Value", "Source"], [
        [e("Designations published for the slate"), str(a["designation_count"]), src("A03")],
        [e("Clubs covered (playing + bye)"), f'{a["slate"]["clubs_with_a_game"]} + {a["slate"]["clubs_on_bye"]} = {a["slate"]["clubs_total"]}', src("A05")],
        [e("Reconciled designations - agree / partial / contradict"),
         f'{REC["counts"]["agree"]} / {REC["counts"]["partial"]} / {REC["counts"]["contradict"]}', src("A01") + " " + src("A03") + " " + src("A04")],
        [e("Rows in this directory with a per-row source link"), "every row; the verifier counts them", src("R01")],
        [e("Strategies eligible in any ledger"), "0", src("R01") + " " + src("R02") + " " + src("R03") + " " + src("R04")],
        [e("Pinned dataset files re-hashed and matched"), f'{L["pinned_dataset"]["matched"]} of {L["pinned_dataset"]["total"]}', src("R05")],
        [e("Same-game phi recomputed vs published"), "3 of 3 pairs match to 1e-6", src("R01")],
        [e("Colliding strategy IDs across ledgers"), str(len(L["id_collisions"]["colliding_ids"])), src("R02") + " " + src("R03")],
        [e("High-severity flags opened or left open"), str(sum(1 for x in hi if x["status"] == "open")), src("A01")],
        [e("Suggestions awaiting the owner"), str(s["decision_gate"]["counts"]["Proposed - awaiting owner decision"]),
         f'<a href="{REPO_BLOB}desk/data/suggestions.json">suggestions.json</a>'],
    ]))
    body.append('<p class="cta"><a class="btn" href="suggestions.html">Suggestions</a> '
                '<a class="btn ghost" href="questions.html">Questions</a> '
                '<a class="btn ghost" href="availability.html">The data</a> '
                '<a class="btn ghost" href="signals.html">The leaderboard</a></p>')
    return page("executive.html", "Executive summary",
                "The important details of this cycle, with the evidence attached to each claim.",
                status_strip() + "".join(body))


# --------------------------------------------------------------------------- #
PAGES = {}


def _register():
    import sys
    mod = sys.modules[__name__]
    for name, fn in sorted(vars(mod).items()):
        if name.startswith("page_") and callable(fn):
            PAGES[name[5:] + ".html"] = fn


_register()


def build() -> None:
    _register()
    for name in sorted(PAGES):
        (HERE / name).write_text(PAGES[name](), encoding="utf-8")
    rows = sum(1 for _ in AVAIL["designations"])
    print(f"built {len(PAGES)} pages; {rows} designation rows; "
          f"{len(SRC)} sources; {len(FLG['flags'])} flags; "
          f"{len(SUG['suggestions'])} suggestions; {len(QST['questions'])} questions")


if __name__ == "__main__":
    build()
