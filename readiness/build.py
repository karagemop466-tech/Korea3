"""Build the decision-readiness section (readiness/*.html and readiness/data/*.json).

Run:  python3 readiness/build.py
Every number on the pages is computed by readiness/data_sources.py from files in the
repository, or from readiness/data/official_recheck.json (official pages read 2026-11-15).
readiness/check.py re-runs this build and fails if anything is missing or inconsistent.
"""
import collections
import html
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import data_sources  # noqa: E402
import register  # noqa: E402
import content  # noqa: E402

REPO_BLOB = "https://github.com/karagemop466-tech/Korea3/blob/main/"
BUILD_DATE = "2026-11-15"

NAV = [
    ("index.html", "Decision readiness"),
    ("questions.html", "Questions &amp; information"),
    ("suggestions.html", "Suggestions &amp; paths"),
    ("flagged.html", "Flagged for review"),
    ("verification.html", "Official re-checks"),
    ("../index.html", "Main dashboard"),
]

CSS = """
:root{--ink:#1d2430;--mute:#5b6675;--line:#e3e7ee;--bg:#f7f8fb;--card:#fff;--acc:#2250a3}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 system-ui,-apple-system,Segoe UI,Roboto,sans-serif;color:var(--ink);background:var(--bg)}
header{background:#fff;border-bottom:1px solid var(--line);padding:14px 22px;position:sticky;top:0;z-index:2}
header h1{font-size:18px;margin:0 0 6px}
nav a{display:inline-block;margin:2px 10px 2px 0;padding:4px 10px;border-radius:14px;background:#eef2f9;color:var(--acc);text-decoration:none;font-size:13px}
nav a.on{background:var(--acc);color:#fff}
main{max-width:1400px;margin:0 auto;padding:18px 22px 60px}
h2{font-size:17px;margin:26px 0 8px}
p.lede{color:var(--mute);max-width:980px}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin:14px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:12px}
.card b{display:block;font-size:22px}.card span{color:var(--mute);font-size:12px}
.tablewrap{overflow-x:auto;background:var(--card);border:1px solid var(--line);border-radius:10px}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:7px 9px;border-bottom:1px solid var(--line);vertical-align:top;text-align:left}
th{background:#f2f5fa;position:sticky;top:0;font-weight:600}
td.id{white-space:nowrap;color:var(--mute)}
.st{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;white-space:nowrap}
.st-BUILT{background:#dcf3e3;color:#17633a}.st-PARTIAL{background:#fff1cc;color:#7a5600}
.st-NOT-BUILT{background:#fde0de;color:#8a1f16}.st-BLOCKED{background:#e9e3f5;color:#4b2e83}
.st-NOT-MET{background:#f9c8c3;color:#7a1109}.st-DECISION{background:#dbe9ff;color:#1d4f9e}
.st-UNVERIFIED{background:#ececec;color:#444}.st-REJECTED{background:#f1e4ff;color:#5b1f8a}
.sev-High{color:#8a1f16;font-weight:600}.sev-Medium{color:#7a5600;font-weight:600}.sev-Low{color:#17633a;font-weight:600}
.badge{font-size:11px;color:var(--mute)}.warn{color:#8a1f16}
.note{background:#fff;border-left:4px solid var(--acc);padding:10px 14px;margin:14px 0;color:var(--mute)}
.legend span{margin-right:12px}
footer{color:var(--mute);font-size:12px;margin-top:30px}
a{color:var(--acc)}
"""


def esc(s):
    return html.escape("" if s is None else str(s))


def status_html(s):
    cls = "st st-" + s.replace(" ", "-")
    return f'<span class="{cls}">{esc(s)}</span>'


def page(title, active, body):
    nav = "".join(
        f'<a href="{href}"{" class=on" if href == active else ""}>{label}</a>'
        for href, label in NAV)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} | NFL decision readiness</title>
<style>{CSS}</style></head>
<body>
<header><h1>NFL decision readiness &middot; {esc(title)}</h1>
<nav>{nav}</nav></header>
<main>{body}
<footer>Research only. Not betting advice. Blank means unverified, never zero. Built {BUILD_DATE} from repository state;
official pages were re-read on 2026-11-15 as listed on the <a href="verification.html">official re-checks</a> page.</footer>
</main></body></html>"""


def path_link(path):
    if path is None:
        return "<i>no file</i>"
    if path.endswith(".html"):
        href = path if not path.startswith("readiness/") else path.replace("readiness/", "")
        if path.startswith("readiness/"):
            return f'<a href="{esc(href)}">{esc(path)}</a>'
        return f'<a href="../{esc(path)}">{esc(path)}</a>'
    return f'<a href="{REPO_BLOB}{esc(path)}">{esc(path)}</a>'


def off_html(key):
    """Official-source cell. Every cell carries a link: official, or the flag / register that explains its absence."""
    label, url, kind = register.OFF[key] if key in register.OFF else (None, None, "none")
    if kind == "process":
        return (f'<a href="{REPO_BLOB}readiness/register.py">Internal rule: register definition</a> '
                '<span class="badge">(no external value)</span>')
    if kind == "none":
        return ('<a class="warn" href="flagged.html">No official source exists for this value: see flags</a>')
    tag = {"reread": "re-read 2026-11-15",
           "headline": "seen as link on an official page; not re-opened",
           "404": "404 at this path; not a source"}[kind]
    cls = "warn" if kind == "404" else ""
    return f'<a class="{cls}" href="{esc(url)}">{esc(label)}</a> <span class="badge">({tag})</span>'


def main_table(R):
    rows = []
    for r in R:
        if r["exists"]:
            exists = "<br>".join(path_link(p) for _, p in r["exists"])
        else:
            exists = (f'<a href="{REPO_BLOB}readiness/register.py">No artifact in the repository: '
                      'the register definition</a>')
        gate = esc(r["gate"])
        if r["note"]:
            gate += f'<br><span class="badge">{esc(r["note"])}</span>'
        rows.append(
            f'<tr id="{esc(r["id"])}"><td class="id">{esc(r["id"])}</td>'
            f'<td><b>{esc(r["req"])}</b><br><span class="badge">{esc(r["group"])}</span></td>'
            f'<td>{status_html(r["status"])}</td>'
            f'<td>{exists}</td>'
            f'<td>{gate}</td>'
            f'<td>{esc(r["clears"])}</td>'
            f'<td>{off_html(r["off"])}</td></tr>')
    return ('<div class="tablewrap"><table><thead><tr>'
            '<th>#</th><th>Requirement (from the brief)</th><th>Status</th>'
            '<th>What exists in the repository</th><th>Gate that blocks it</th>'
            '<th>Number that would clear it</th><th>Official source</th>'
            '</tr></thead><tbody>' + "\n".join(rows) + '</tbody></table></div>')


def build_index(R, n, counts):
    cards = [
        (len(R), "requirements in the brief, one row each"),
        (counts.get("BUILT", 0), "built and gated as described"),
        (counts.get("PARTIAL", 0), "partly built"),
        (counts.get("NOT BUILT", 0), "not built"),
        (counts.get("BLOCKED", 0), "blocked on a source or decision"),
        (counts.get("DECISION", 0), "need an owner decision"),
        (counts.get("NOT MET", 0), "contradicted by the repository today"),
        (counts.get("UNVERIFIED", 0), "not checked this session"),
        (n["live_strategies_today"] if "live_strategies_today" in n else n["live_lifecycle"], "strategies live today"),
        (f"{n['live_rows_manual']} vs {n['hub_players_listed']}", "live Week 10 rows (manual count) vs published"),
    ]
    card_html = "".join(f'<div class="card"><b>{esc(v)}</b><span>{esc(t)}</span></div>' for v, t in cards)
    legend = " ".join(status_html(s) for s in register.STATUSES)
    body = f"""
<h2>Decision readiness: one row per requirement</h2>
<p class="lede">Every requirement in the current brief, with its status in this repository on {BUILD_DATE}, the gate that blocks it,
and the number that would clear it. Numbers are computed from files in the repository or from official pages re-read on 2026-11-15.
Nothing is recommended for betting. No strategy is live.</p>
<div class="cards">{card_html}</div>
<div class="note"><b>Headline.</b> No strategy is live (lifecycle file: 0 of {n['strategies_lifecycle']}). Two of the brief's rules are
contradicted by the repository today: backtest numbers appear on the leaderboard (F05), and two parlay strategies are ranked without a
joint-evidence gate (F06). Three published Week 10 game-status cells are blank where the official page says Out (F01), and four clubs are shown
as having no injuries when the official page lists players (F02). See <a href="flagged.html">Flagged for review</a>.</div>
<p class="legend"><b>Status:</b> {legend}</p>
{main_table(R)}
<h2>How to read this table</h2>
<p class="lede">A status describes this repository only. &ldquo;Official source&rdquo; links are the NFL or club page for the value; the label says
whether the page was re-read on 2026-11-15, or only seen as a link. A row with no official source says so and is flagged, not filled in.
&ldquo;Process&rdquo; rows are internal rules with no external value.</p>
"""
    return body


def ref_links(text):
    """Turn register, flag, question and suggestion IDs in a string into links to their rows."""
    out = []
    for tok in re.findall(r"\b([A-DFQS]\d\d)\b", text or ""):
        if tok[0] in "ABCD":
            href = f"index.html#{tok}"
        elif tok[0] == "F":
            href = f"flagged.html#{tok}"
        elif tok[0] == "Q":
            href = f"questions.html#{tok}"
        else:
            href = f"suggestions.html#{tok}"
        out.append(f'<a href="{href}">{tok}</a>')
    return ", ".join(out) if out else '<span class="warn">no row referenced</span>'


def build_questions():
    rows = []
    for q in content.QUESTIONS:
        rows.append(
            f'<tr id="{esc(q["id"])}"><td class="id">{esc(q["id"])}</td><td><b>{esc(q["q"])}</b>'
            f'<br><span class="badge">{"Blocking" if q["blocking"] else "Not blocking"}</span></td>'
            f'<td>{esc(q["held"])}</td><td>{esc(q["missing"])}</td>'
            f'<td>{esc(q["discover"])}</td><td>{ref_links(q["blocks"])}</td></tr>')
    table = ('<div class="tablewrap"><table><thead><tr><th>#</th><th>Question</th><th>What we hold</th>'
             '<th>What is missing</th><th>How to discover it</th><th>Blocks (register rows)</th></tr></thead><tbody>'
             + "\n".join(rows) + "</tbody></table></div>")
    return f"""
<h2>Questions, information held, information missing</h2>
<p class="lede">These must be answered before a decision can rest on the information we have. None has been answered on the owner's behalf.
Blocking questions stop at least one requirement; the register row IDs are linked in the last column.</p>
{table}"""


def build_suggestions():
    rows = []
    for s_ in content.SUGGESTIONS:
        rows.append(
            f'<tr id="{esc(s_["id"])}"><td class="id">{esc(s_["id"])}</td><td><b>{esc(s_["title"])}</b></td>'
            f'<td>{ref_links(s_["why"])}</td>'
            f'<td>{esc(s_["path"])}</td><td>{esc(s_["effort"])}</td><td>{esc(s_["changes"])}</td>'
            f'<td>{esc(s_["recommendation"])}</td><td><span class="badge">Awaiting owner choice</span></td></tr>')
    table = ('<div class="tablewrap"><table><thead><tr><th>#</th><th>Suggestion</th><th>Why (linked)</th><th>Path</th><th>Effort</th>'
             '<th>What would change</th><th>Recommendation</th><th>Status</th></tr></thead><tbody>'
             + "\n".join(rows) + "</tbody></table></div>")
    return f"""
<h2>Suggestions and paths</h2>
<div class="note"><b>Nothing here is implemented.</b> Each suggestion is a proposed path. The owner chooses which paths to take, and in
what order, before any change is made. Paths: <b>A</b> repair now (no new policy); <b>B</b> build (new capture or analysis); <b>C</b> owner
decision required first.</div>
<p class="lede">Suggestions to improve decision-making and to discover missing information. The main-dashboard suggestions board
(<a href="../hub/suggestions.html">hub/suggestions.html</a>) holds earlier proposals and is not replaced by this list.</p>
{table}""" 


def build_flags():
    rows = []
    for f in content.FLAGS:
        ev = "<br>".join(
            (f'<a href="{REPO_BLOB}{esc(e.split(" ")[0])}">{esc(e)}</a>' if os.path.exists(os.path.join(data_sources.ROOT, e.split(" ")[0]))
             else f'<a href="{REPO_BLOB}readiness/data/official_recheck.json">{esc(e)}</a>')
            for e in f["evidence"])
        off = off_html(f["official"]) if f["official"] else (
            '<a href="index.html">No official value involved: see register</a>')
        rows.append(
            f'<tr id="{esc(f["id"])}"><td class="id">{esc(f["id"])}</td><td class="sev-{esc(f["sev"])}">{esc(f["sev"])}</td>'
            f'<td>{esc(f["area"])}</td><td>{esc(f["finding"])}</td><td>{ev}</td>'
            f'<td>{off}</td>'
            f'<td>{esc(f["status"])}</td></tr>')
    table = ('<div class="tablewrap"><table><thead><tr><th>ID</th><th>Severity</th><th>Area</th><th>Finding</th>'
             '<th>Evidence in repository</th><th>Official source</th><th>Status</th></tr></thead><tbody>'
             + "\n".join(rows) + "</tbody></table></div>")
    return f"""
<h2>Flagged for review</h2>
<p class="lede">Irregularities found while re-checking the repository against official pages. They do not block publication.
Each one names the evidence and the official page. Nothing has been changed in other builds to fix them.</p>
{table}"""


def build_verification(n):
    rc = json.load(open(os.path.join(HERE, "data", "official_recheck.json"), encoding="utf-8"))
    pages = []
    for p in rc["pages"]:
        pages.append(f'<tr><td><a href="{esc(p["url"])}">{esc(p["url"])}</a></td>'
                     f'<td>{esc(p["title"])}</td><td>{esc(p["result"])}</td></tr>')
    pages_t = ('<div class="tablewrap"><table><thead><tr><th>Official URL</th><th>Page title</th><th>What was read</th>'
               '</tr></thead><tbody>' + "\n".join(pages) + "</tbody></table></div>")

    live = rc["live_week10_club_counts"]
    hub_no = set(n["hub_no_injuries"])
    raw = {}
    d = json.load(open(os.path.join(data_sources.ROOT, "depth_lab/data/raw/nfl_injury_w10_2026.json"), encoding="utf-8"))
    for c in d["clubs"]:
        # rows are lists: [name, position, injury, practice, game status, url]
        raw[c["code"]] = len(c["rows"])
    confirmed = {"SEA", "CIN", "BAL"}
    clubs = []
    for code in sorted(live):
        st = []
        if code in hub_no:
            st.append("hub says 'no injuries reported'")
        if raw.get(code) != live[code]:
            st.append(f"raw capture has {raw.get(code)} rows, live has {live[code]}")
        status = "; ".join(st) if st else "row counts agree"
        vstat = ("confirmed against the fetched page" if code in confirmed
                 else "UNVERIFIED: count from a manual read; not re-fetched or parsed")
        cls = "warn" if st else ""
        clubs.append(f'<tr><td><a href="https://www.nfl.com/injuries/league/2026/reg10">{esc(code)}</a></td><td>{live[code]}</td><td>{raw.get(code)}</td>'
                     f'<td class="{cls}">{esc(status)}</td><td>{esc(vstat)}</td></tr>')
    clubs_t = ('<div class="tablewrap"><table><thead><tr><th>Club</th><th>Live rows (manual count)</th>'
               '<th>Repository raw capture rows</th><th>Comparison</th><th>Verification</th></tr></thead><tbody>'
               + "\n".join(clubs) + "</tbody></table></div>")

    cells = []
    for c in rc["live_week10_cell_findings"]:
        L = c["live"]
        cells.append(f'<tr><td><a href="https://www.nfl.com/injuries/league/2026/reg10">{esc(c["club"])}</a></td><td><a href="https://www.nfl.com/injuries/league/2026/reg10">{esc(c["player"])}</a></td>'
                     f'<td>{esc(L["injury"]) or "blank"}</td><td>{esc(L["practice"])}</td>'
                     f'<td>{esc(L["game"]) or "blank"}</td><td>{esc(c.get("note", ""))}</td></tr>')
    cells_t = ('<div class="tablewrap"><table><thead><tr><th>Club</th><th>Player</th><th>Injury (live)</th>'
               '<th>Practice (live)</th><th>Game status (live)</th><th>Repository capture note</th></tr></thead><tbody>'
               + "\n".join(cells) + "</tbody></table></div>")

    tr = []
    for t in rc["trades_nov2026"]:
        tr.append(f'<tr><td><a href="https://www.nfl.com/transactions/">{esc(t["date"])}</a></td><td>{esc(t["name"])}</td><td>{esc(t["from"])}</td><td>{esc(t["to"])}</td></tr>')
    trades_t = ('<div class="tablewrap"><table><thead><tr><th>Date (Nov 2026)</th><th>Player</th><th>From</th><th>To</th></tr></thead><tbody>'
                + "\n".join(tr) + "</tbody></table></div>")

    rs = []
    for t in rc["reserve_nov2026_seen"]:
        rs.append(f'<tr><td><a href="https://www.nfl.com/transactions/league/reserve-list/2026/11">{esc(t["date"])}</a></td><td>{esc(t["name"])}</td><td>{esc(t["club"])}</td><td>Reserve/Injured</td></tr>')
    res_t = ('<div class="tablewrap"><table><thead><tr><th>Date</th><th>Player</th><th>Club</th><th>Transaction</th></tr></thead><tbody>'
             + "\n".join(rs) + "</tbody></table></div>")

    heads = []
    for h in rc["headlines_seen_on_injury_page"]:
        heads.append(f'<li><a href="{esc(h["url"])}">{esc(h["headline"])}</a></li>')

    return f"""
<h2>Official re-checks, 2026-11-15</h2>
<p class="lede">What was read from official pages on {rc["_meta"]["fetch_date_utc"]} (UTC), and what it shows. Counts are manual counts of the
fetched tables and should be confirmed by a parser (see Suggestion S02). The sandbox could reach NFL pages only through the page-fetch tool.</p>
<div class="note"><b>Method limits.</b> {esc(rc["_meta"]["limits"])}</div>
<h2>Pages read</h2>{pages_t}
<h2>Week 10 injury tables: live page against the repository capture</h2>
<p class="lede">Live total (manual count): <b>{n["live_rows_manual"]} rows</b> across <b>{n["live_clubs_with_tables"]} clubs</b>.
Absent from the page: {", ".join(rc["live_week10_absent"])}. Repository raw capture: {n["raw_rows"]} rows across {n["raw_clubs"]} clubs.
Published hub copy: {n["hub_players_listed"]} players and {n["hub_clubs_listed"]} clubs with rows.</p>
{clubs_t}
<h2>Cell-level checks: Detroit and Baltimore</h2>
<p class="lede">Each named player's cells on the live page, against the repository note. Seattle and Cincinnati were compared by row count only.</p>
{cells_t}
<h2>Official trades, November 2026 (nfl.com/transactions)</h2>{trades_t}
<h2>Official reserve list, November 2026 (page 1 of 2)</h2><p class="lede">Malik Willis (MIA, 11/10) appears here and is not in MIA's injury table.</p>{res_t}
<h2>Official headlines on the injury page (links, not re-opened)</h2><ul>{"".join(heads)}</ul>
<h2>Club depth charts re-read</h2>
<ul>
<li><a href="https://www.baltimoreravens.com/team/depth-chart">Ravens</a>: QB order Jacoby Brissett, Joe Fagnano, Kedon Slovis.</li>
<li><a href="https://www.houstontexans.com/team/depth-chart">Texans</a>: headed &ldquo;Unofficial Depth Chart&rdquo;; the depth table is an image; no table text.</li>
</ul>
"""


def main():
    n = data_sources.compute()
    R = register.rows(n)
    counts = collections.Counter(r["status"] for r in R)
    n["live_strategies_today"] = n["live_lifecycle"]
    pages = {
        "index.html": ("Decision readiness", "index.html", build_index(R, n, counts)),
        "questions.html": ("Questions &amp; information", "questions.html", build_questions()),
        "suggestions.html": ("Suggestions &amp; paths", "suggestions.html", build_suggestions()),
        "flagged.html": ("Flagged for review", "flagged.html", build_flags()),
        "verification.html": ("Official re-checks", "verification.html", build_verification(n)),
    }
    for fname, (title, active, body) in pages.items():
        with open(os.path.join(HERE, fname), "w", encoding="utf-8") as f:
            f.write(page(title, active, body))

    os.makedirs(os.path.join(HERE, "data"), exist_ok=True)
    with open(os.path.join(HERE, "data", "register.json"), "w", encoding="utf-8") as f:
        json.dump({"rows": R, "counts": dict(counts), "computed": n,
                   "flags": content.FLAGS, "questions": content.QUESTIONS,
                   "suggestions": content.SUGGESTIONS, "statuses": register.STATUSES},
                  f, indent=1, default=str, ensure_ascii=False)
    print(f"built {len(pages)} pages; {len(R)} requirement rows; statuses {dict(counts)}; "
          f"{len(content.FLAGS)} flags; {len(content.QUESTIONS)} questions; {len(content.SUGGESTIONS)} suggestions")


if __name__ == "__main__":
    main()
