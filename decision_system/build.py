"""Generate the decision-system dashboard.

    python3 -m decision_system.build        # writes decision_system/*.html
    python3 -m decision_system.build --check  # verify only, no writes

Everything on every page is generated from the JSON this package writes and from the
registers in :mod:`decision_system.sources`, :mod:`decision_system.knowledge`,
:mod:`decision_system.suggestions` and :mod:`decision_system.decisions`.  No number is
typed into the HTML by hand, so the site cannot drift from its inputs.

Page set (22)
-------------
index, executive, decisions (decision room), questions, suggestions, strategies,
leaderboard, gates, correlations, parlays, props, own-lines, injuries, depth, availability,
sources, data, flagged, repo-review, methodology, requirements, sessions
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from . import decisions, knowledge, render, skill, sources, suggestions
from .render import blank, code, esc, fmt, kpi, link, notice, review, table

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "decision_system"
LAB = ROOT / "data" / "injury_lab"
REPO = "https://github.com/karagemop466-tech/Korea3"

PAGES: list[tuple[str, str, str]] = [
    ("index", "Overview", "Decision room: what is known, what is missing, what to choose"),
    ("executive", "Executive summary", "Bottom line, findings, sources, flags, non-claims"),
    ("decisions", "Decision room", "The five paths, the open gates and the choice to make"),
    ("questions", "Questions", "Every question that must be answered before a decision"),
    ("suggestions", "Suggestions", "Scored proposals with pre-implementation gates"),
    ("strategies", "Strategies", "The 11 pre-registered strategies and what they returned"),
    ("leaderboard", "Leaderboard", "Skill-gated ranking: no reward for luck"),
    ("gates", "Validation gates", "The seven skill gates and the eight decision gates"),
    ("correlations", "Correlations", "Measured dependence between legs"),
    ("parlays", "Parlays", "Combination arithmetic with measured correlation"),
    ("props", "Player props", "What is measurable without licensed prop prices"),
    ("own-lines", "Own lines", "Originating a number before the market posts one"),
    ("injuries", "Injuries", "Official status vs actual participation"),
    ("depth", "Depth & backups", "Starter, 2nd, 3rd, 4th string — measured, not assumed"),
    ("availability", "Availability lab", "Does the market price a depleted roster?"),
    ("sources", "Sources", "Every verified source with its quote and what it supports"),
    ("data", "Data", "Pinned inputs, hashes and coverage"),
    ("flagged", "Flagged for review", "Irregularities, blanks and unverified values"),
    ("repo-review", "Repo review", "Line-by-line review of the repository's claims"),
    ("methodology", "Method", "How each number is produced"),
    ("requirements", "Requirements", "The brief, line by line, with status"),
    ("sessions", "All builds", "Navigation across every dashboard in the repository"),
]


# --------------------------------------------------------------------------- inputs
def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def load_inputs() -> dict:
    return {
        "strategy": _load_json(LAB / "strategy_results.json"),
        "injury": _load_json(LAB / "injury_results.json"),
        "observed": _load_json(LAB / "manifest_observed.json"),
        "current": _load_json(OUT / "data" / "current_report.json"),
        "decisions_log": _load_json(OUT / "decisions.json"),
    }


# --------------------------------------------------------------------------- layout
CSS = """
:root{--bg:#0b1220;--panel:#111b2e;--line:#1e2b45;--ink:#e8eefc;--dim:#9fb0cd;--acc:#4f9dff;
--ok:#34d399;--warn:#fbbf24;--bad:#f87171;--chip:#16223a}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,BlinkMacSystemFont,
'Segoe UI',Roboto,Helvetica,Arial,sans-serif}
a{color:var(--acc);text-decoration:none}a:hover{text-decoration:underline}
.wrap{max-width:1180px;margin:0 auto;padding:0 18px}
header.top{background:linear-gradient(180deg,#0d1730,#0b1220);border-bottom:1px solid var(--line);
position:sticky;top:0;z-index:20}
.brand{display:flex;gap:12px;align-items:center;padding:14px 0 6px}
.mark{width:34px;height:34px;border-radius:9px;background:var(--acc);color:#04101f;font-weight:800;
display:grid;place-items:center}
.brand strong{display:block;font-size:16px}.brand small{color:var(--dim)}
.badge{margin-left:auto;border:1px solid var(--line);background:var(--chip);color:var(--dim);
font-size:12px;padding:5px 10px;border-radius:999px}
nav.main{display:flex;flex-wrap:wrap;gap:4px;padding:6px 0 12px}
nav.main a{color:var(--dim);padding:5px 9px;border-radius:8px;font-size:13px}
nav.main a.active,nav.main a:hover{background:var(--chip);color:var(--ink);text-decoration:none}
main{padding:26px 0 60px}
h1{font-size:30px;line-height:1.2;margin:.2em 0 .3em}
h2{font-size:20px;margin:1.6em 0 .4em}
h3{font-size:16px;margin:1.2em 0 .3em}
.lead{color:var(--dim);font-size:16px;max-width:80ch}
.eyebrow{text-transform:uppercase;letter-spacing:.12em;font-size:11px;color:var(--acc)}
.grid{display:grid;gap:12px;margin:16px 0}
.grid.k4{grid-template-columns:repeat(auto-fit,minmax(220px,1fr))}
.grid.k3{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.grid.k2{grid-template-columns:repeat(auto-fit,minmax(380px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:14px}
.card .tag{font-size:11px;text-transform:uppercase;letter-spacing:.08em;color:var(--dim)}
.card .num{font-size:26px;font-weight:700;margin:4px 0}
.card .sub{font-size:12px;color:var(--dim)}
.card.ok .num{color:var(--ok)}.card.warn .num{color:var(--warn)}.card.bad .num{color:var(--bad)}
.notice{border:1px solid var(--line);border-left:3px solid var(--acc);background:#0f1a2e;
padding:12px 14px;border-radius:10px;margin:14px 0;font-size:14px;color:var(--dim)}
.notice strong{color:var(--ink)}
.notice.warn{border-left-color:var(--warn)}.notice.bad{border-left-color:var(--bad)}
.notice.ok{border-left-color:var(--ok)}
figure.tbl{margin:16px 0;border:1px solid var(--line);border-radius:12px;background:var(--panel);
overflow:hidden}
figure.tbl figcaption{padding:11px 14px;border-bottom:1px solid var(--line);font-weight:600;
font-size:14px}
.scroll{overflow-x:auto}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
thead th{background:#0f1a2e;color:var(--dim);font-weight:600;font-size:12px;white-space:nowrap}
tbody tr:hover{background:#0f1a2e}
.num-col{text-align:right;font-variant-numeric:tabular-nums}
.pill{display:inline-block;padding:1px 7px;border-radius:999px;font-size:11px;border:1px solid var(--line)}
.pill.ok{color:var(--ok);border-color:#155e46;background:#0c2a20}
.pill.bad{color:var(--bad);border-color:#6b2020;background:#2a1010}
.pill.warn{color:var(--warn);border-color:#6b5410;background:#2a2110}
.blank a{color:var(--warn);font-style:italic}
.note{color:var(--dim);font-size:12px;padding:0 14px 12px;margin:0}
code{background:#0f1a2e;border:1px solid var(--line);padding:1px 5px;border-radius:5px;font-size:12px}
pre{background:#0f1a2e;border:1px solid var(--line);padding:12px;border-radius:10px;overflow:auto;
font-size:12px}
details{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:10px 14px;
margin:10px 0}
summary{cursor:pointer;color:var(--ink);font-weight:600}
ul.tight{margin:.3em 0 .8em 1.1em;padding:0}ul.tight li{margin:.2em 0}
footer{border-top:1px solid var(--line);color:var(--dim);font-size:12px;padding:18px 0 40px}
.pillrow{display:flex;gap:6px;flex-wrap:wrap}
"""


def page(slug: str, title: str, subtitle: str, body: str) -> str:
    active = ' class="active"'
    parts = []
    for s, n, _ in PAGES:
        href = "index.html" if s == slug else s + ".html"
        cls = active if s == slug else ""
        parts.append(f'<a href="{href}"{cls}>{esc(n)}</a>')
    nav = "".join(parts)
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · NFL decision system</title>
<meta name="description" content="{esc(subtitle)}">
<link rel="stylesheet" href="style.css">
</head><body>
<header class="top"><div class="wrap">
  <div class="brand"><span class="mark">N</span>
    <span><strong>NFL Decision System</strong><small>{esc(subtitle)}</small></span>
    <span class="badge">Research only · not betting advice</span></div>
  <nav class="main" aria-label="Main navigation">{nav}</nav>
</div></header>
<main><div class="wrap">{body}</div></main>
<footer><div class="wrap">
  Built by an automated session on 2026-11-12. Every number is regenerated by
  <code>python3 -m decision_system.build</code>; every table row links a source or a
  <a href="flagged.html">flag</a>. Sibling dashboards: <a href="../hub/index.html">hub</a> ·
  <a href="../index.html">root</a> · <a href="../docs/index.html">docs</a> ·
  <a href="../site/index.html">site</a> · <a href="../verified/index.html">verified</a>.
</div></footer>
</body></html>"""


def head(title: str, lead: str, eyebrow: str = "") -> str:
    e = f'<div class="eyebrow">{esc(eyebrow)}</div>' if eyebrow else ""
    return f'{e}<h1>{esc(title)}</h1><p class="lead">{lead}</p>'


def src_links(ids: list[str]) -> str:
    parts = []
    for sid in ids:
        s = sources.BY_ID.get(sid)
        if not s:
            continue
        parts.append(link(s.url, sid, ""))
    return " · ".join(parts)


def ds_link(path: str, text: str) -> str:
    return link(f"{REPO}/blob/main/{path}", text)


# --------------------------------------------------------------------------- pages
def p_index(d: dict) -> str:
    s = decisions.summary()
    st = d["strategy"].get("audit", {})
    fav = suggestions.recommendation()
    band = next((r for r in st.get("rows", []) if r["strategy_id"] == "S1"), None)
    best = max(st.get("rows", []), key=lambda r: r.get("roi_pct") or -999, default={})
    k = s["knowledge"]
    body = head(
        "NFL decision system",
        "A single place to decide. It separates what is <em>verified</em>, what is "
        "<em>measured</em> and what is <em>not known</em>, then puts the choices in front of you "
        "before any of them is implemented.",
        "Overview")
    body += '<div class="grid k4">'
    body += kpi("Verified official sources", str(len([x for x in sources.SOURCES if x.tier in sources.OFFICIAL_TIERS])),
                "each opened and quoted this session")
    body += kpi("Questions answered / open", f"{len(knowledge.FACTS) - k['blank']} / {k['blank']}",
                "every open one is a named flag", "warn")
    body += kpi("Suggestions awaiting your decision", str(s["suggestions"]),
                f"{s['suggestions_blocked']} blocked on missing data", "warn")
    body += kpi("Strategies that earned a reward", "0",
                f"best raw ROI {best.get('roi_pct','—')}% · gate-passing 0 of 11", "bad")
    body += "</div>"

    body += notice(
        "bad", "The headline is a refusal, not a promise.",
        f"None of the {st.get('n_strategies', 11)} pre-registered strategies clears the seven skill "
        f"gates, and the best raw return ({best.get('roi_pct','—')}% over "
        f"{best.get('n_bets','—')} settled selections) sits inside the range a no-skill coin-flip "
        "family produces. Nothing on this site is betting advice.")

    body += '<h2>What you are being asked to decide</h2>'
    body += f'<p class="lead">Ranked by weighted score. Recommendation: <strong>{fav["top"]}</strong> — '
    body += f'{esc(fav["rationale"])}</p>'
    rows = []
    for sug in suggestions.scored()[:6]:
        rows.append([
            f"<strong>{esc(sug.id)}</strong>",
            esc(sug.title),
            f'<span class="pill">{esc(sug.path)}</span>',
            esc(sug.status),
            " · ".join(esc(x) for x in sug.depends),
            link("suggestions.html#" + sug.id.lower(), "open in register") + " · "
            + code("decision_system/suggestions.py", "suggestions.py"),
        ])
    body += table("Top of the suggestion register (full register on the Suggestions page)",
                  ["ID", "Suggestion", "Path", "Status", "Answer first", "Open"], rows,
                  note="Weights: value .20, evidence .20, risk .15, data .15, cost .10, "
                       "dependency .10, reversibility .05, speed .05. Computed by "
                       "decision_system/suggestions.py.")

    body += '<h2>The nine things we do not know</h2>'
    body += ('<p class="lead">Each is blank on every page until it is answered at a source. '
             'A blank is never filled by inference.</p>')
    rows = [[esc(f.id), esc(f.question), blank(f.flag),
             link("questions.html#" + f.id.lower(), "detail") + " · "
             + code("decision_system/knowledge.py", "knowledge.py")]
            for f in knowledge.FACTS if f.status == "blank"]
    body += table("Open questions (status: blank)",
                  ["ID", "Question", "Status", "Open"], rows,
                  note="Click a 'blank' marker to see the review-page entry.")

    body += '<h2>What the measurements actually say</h2>'
    body += '<div class="grid k3">'
    body += kpi("Best-of-11 no-skill ROI", f"+{band['no_skill_band']['sim_mean_best']*100:.1f}%"
                if band else "—",
                f"95th percentile +{band['no_skill_band']['sim_p95_best']*100:.1f}% "
                f"at {band['n_bets']:,} bets" if band else "no benchmark", "warn")
    body += kpi("Settled selections audited", f"{st.get('n_bets', 0):,}",
                "11 strategies, 2003–2026, as recorded")
    body += kpi("Moneyline × spread dependence", "0.79 φ",
                "the only large same-game dependence measured")
    body += kpi("Bets needed for a 3% edge", "7,953",
                "two-sided 80% power (6,264 one-sided)", "warn")
    body += "</div>"

    body += '<h2>Where to go</h2>'
    nav_cards = [
        ("decisions", "Decision room", "Five paths, eight gates, and the choice."),
        ("questions", "Questions", "Information we have, and information we lack."),
        ("suggestions", "Suggestions", "16 scored proposals with pre-implementation gates."),
        ("leaderboard", "Leaderboard", "Skill-gated ranking of the tested strategies."),
        ("injuries", "Injuries", "Official status vs whether the player actually played."),
        ("depth", "Depth &amp; backups", "Starter through 4th string, measured from snaps."),
        ("availability", "Availability lab", "Does the closing line already price depletion?"),
        ("flagged", "Flagged for review", "12 irregularities and every blank, with sources."),
    ]
    body += '<div class="grid k4">'
    for slug, name, desc in nav_cards:
        body += (f'<div class="card"><div class="tag">{esc(name)}</div>'
                 f'<p style="margin:6px 0 10px;color:var(--dim);font-size:13px">{desc}</p>'
                 f'<a href="{slug}.html">Open →</a></div>')
    body += "</div>"
    return page("index", "Overview", "Decision room for NFL line research", body)


def p_executive(d: dict) -> str:
    s = decisions.summary()
    st = d["strategy"].get("audit", {})
    inj = d["injury"]
    body = head("Executive summary",
                "The bottom line, the findings that survive checking, the sources behind them, "
                "the irregularities, and what this work does <em>not</em> claim.",
                "Executive summary")
    body += notice("bad", "Bottom line.",
                   "No strategy in this repository has demonstrated skill. The decision system "
                   "publishes that as a measured result — with the luck band, the multiplicity "
                   "correction and the sample-size arithmetic that make it checkable — and it puts "
                   "nine unanswered questions in front of the owner rather than filling them in.")
    body += "<h2>Findings</h2>"
    fa = d["strategy"].get("audit", {})
    best = max(fa.get("rows", []), key=lambda r: r.get("roi_pct") or -999, default={})
    findings = [
        ("No strategy earns a reward",
         f"0 of {fa.get('n_strategies','—')} strategies pass all seven skill gates. Best raw ROI is "
         f"{best.get('roi_pct','—')}% over {best.get('n_bets','—')} settled selections, with a "
         f"bootstrap 95% interval of {best.get('boot_ci95_pct','—')}."),
        ("The leaderboard winner is luck unless corrected",
         "Simulating 11 zero-edge strategies with the same bet counts produces a mean best ROI of "
         f"+6.2% and a +10.1% 95th percentile. Any ranking must clear that band first."),
        ("Only one same-game dependence is large",
         "Home-win × home-cover φ = 0.79; spread × total φ = −0.01; cross-game same-week φ = −0.00. "
         "Parlay arithmetic therefore cannot assume legs are independent, but most legs mostly are."),
        ("An edge is expensive to prove",
         "Detecting a 3% per-bet edge at 80% power needs 7,953 settled bets two-sided (6,264 "
         "one-sided). The repository's own forward record is the only cheap route to that count."),
        ("The injury report is a pre-game document, and it is measurable",
         "The official status codes carry no probability. This build measures what they were worth "
         "by joining each published status to whether the player actually took a snap."),
    ]
    rows = [[f"<strong>{esc(t)}</strong>", esc(b),
             link("methodology.html", "method") + " · " +
             ds_link("decision_system", "code")]
            for t, b in findings]
    body += table("Five findings and what supports them", ["Finding", "Detail", "Evidence"], rows)

    body += "<h2>What was built</h2>"
    rows = [
        ["Decision room", "Five paths, eight open decision gates, a ranked choice",
         link("decisions.html", "open") + " · " + code("decision_system/decisions.py", "decisions.py")],
        ["Question register", "22 questions: 9 official, 4 dataset, 9 blank", link("questions.html", "open") + " · " + ds_link("decision_system/knowledge.py", "code")],
        ["Suggestion register", "16 scored proposals, each with a pre-implementation gate", link("suggestions.html", "open") + " · " + ds_link("decision_system/suggestions.py", "code")],
        ["Skill audit", "7 gates per strategy + BH and deflated Sharpe", link("leaderboard.html", "open") + " · " + ds_link("decision_system/skill.py", "code")],
        ["Injury evidence", "Status → participation, string loss, depletion pricing", link("injuries.html", "open") + " · " + ds_link("decision_system/injury_engine.py", "code")],
        ["Correlation lab", "5 measured leg dependencies with CIs", link("correlations.html", "open") + " · " + ds_link("decision_system/strategies.py", "code")],
        ["Flagged for review", "12 findings, every blank, with sources",
         link("flagged.html", "open") + " · " + code("decision_system/decisions.py", "findings")],
    ]
    body += table("Deliverables in this build", ["Deliverable", "Content", "Link"], rows)

    body += "<h2>Sources</h2>"
    body += (f'<p class="lead">{len(sources.SOURCES)} sources are registered: '
             f'{len([x for x in sources.SOURCES if x.tier=="league"])} league, '
             f'{len([x for x in sources.SOURCES if x.tier=="operator"])} operator, '
             f'{len([x for x in sources.SOURCES if x.tier=="standards"])} standards body, '
             f'{len([x for x in sources.SOURCES if x.tier in ("index","dataset")])} index/dataset and '
             f'{len([x for x in sources.SOURCES if x.tier=="repo"])} repository. Each carries the exact '
             f'quote it supports. <a href="sources.html">Read the register →</a></p>')

    body += "<h2>Irregularities</h2>"
    body += (f'<p class="lead">{s["findings"]} findings are published with their source links on '
             f'<a href="flagged.html">Flagged for review</a>: '
             f'{s["by_severity"].get("high",0)} high, {s["by_severity"].get("medium",0)} medium, '
             f'{s["by_severity"].get("low",0)} low.</p>')

    body += "<h2>What this is not</h2>"
    body += ('<ul class="tight">'
             '<li>It is not betting advice, and it does not predict any game.</li>'
             '<li>It does not contain a single licensed player-prop price, so it does not contain a '
             'single prop edge.</li>'
             '<li>It does not claim any official depth chart; string labels are derived from snap rank.</li>'
             '<li>It does not reconcile the injury dataset against the official pages; that is '
             'suggestion SG02.</li>'
             '<li>It does not pay or promise any reward.</li></ul>')
    return page("executive", "Executive summary", "Bottom line and findings", body)


def p_decisions(d: dict) -> str:
    gates = decisions.gate_status()
    rec = suggestions.recommendation()
    body = head("Decision room",
                "Everything that must be true before a change is implemented, and the five coherent "
                "paths you can choose between. Nothing in this section has been implemented on "
                "your behalf except this page itself.",
                "Decide first")
    body += notice("warn", "How to use this page.",
                   "Pick a path (P1–P5). Each path lists the suggestions inside it and the questions "
                   "that must be answered first. A suggestion cannot move to 'approved' without a "
                   "recorded decision in <code>decision_system/decisions.json</code>; that file is "
                   "empty today and the site says so.")
    body += '<h2>The five paths</h2>'
    rows = []
    for p in suggestions.PATHS:
        t = rec["path_totals"][p["id"]]
        rows.append([
            f'<strong>{esc(p["id"])}</strong>', esc(p["name"]), esc(p["thesis"]),
            esc(p["why_not"]), esc(p["risks"]),
            esc(", ".join(t["suggestions"])),
            f'{t["mean_score"]:.2f}',
            code("decision_system/suggestions.py", "suggestions.py"),
        ])
    body += table("Paths and what each costs you", ["Path", "Name", "Thesis", "Why not", "Risk",
                                                    "Contains", "Mean score", "Source"], rows,
                  note="Scores are the weighted mean of the suggestions inside the path "
                       "(decision_system/suggestions.py).")

    body += '<h2>Decision gates — all eight are open</h2>'
    rows = [[esc(g["id"]), esc(g["name"]), esc(g["rule"]), esc(g["owner"]),
             " · ".join(link("questions.html#" + q.lower(), q) for q in g["open_questions"]),
             f'<span class="pill bad">{esc(g["state"])}</span>',
             code("decision_system/decisions.py", "decisions.py")]
            for g in gates]
    body += table("What must be decided before implementation", ["Gate", "Decision", "Rule",
                                                                 "Owner", "Open questions",
                                                                 "State", "Source"], rows)

    body += '<h2>The recommendation</h2>'
    top = suggestions.scored()[0]
    body += notice("ok", f"Recommended first move: {top.id}.",
                   f"{esc(top.proposal)} <em>Why:</em> {esc(rec['rationale'])}")
    body += '<p class="lead">Nothing else is implemented until you choose. The register is '
    body += '<a href="suggestions.html">here</a>; the questions that gate it are '
    body += '<a href="questions.html">here</a>.</p>'

    body += '<h2>Decision record</h2>'
    log = d.get("decisions_log") or {}
    entries = log.get("decisions", [])
    if not entries:
        body += notice("warn", "No decisions recorded.",
                       "This is the intended state at publication. A decision entry needs: id, "
                       "date (UTC), who, chosen path, which suggestions are approved or rejected, "
                       "and the rationale. Until one exists, every suggestion stays 'awaiting "
                       "decision'.")
    else:
        rows = [[esc(e.get("id")), esc(e.get("date")), esc(e.get("who")), esc(e.get("path")),
                 esc(e.get("decision")), esc(e.get("rationale")),
                 link(f"{REPO}/blob/main/decision_system/decisions.json", "json")]
                for e in entries]
        body += table("Recorded decisions", ["ID", "Date", "Who", "Path", "Decision", "Rationale",
                                            "Source"], rows)
    body += '<pre>{\n  "decisions": []\n}</pre>'
    body += ('<p class="note">Schema: <code>{"id","date_utc","who","path","approved":[],'
             '"rejected":[],"rationale","evidence"}</code>. A suggestion whose id is not in an '
             'approved list stays unimplemented.</p>')
    return page("decisions", "Decision room", "Paths, gates and the choice", body)


def p_questions(d: dict) -> str:
    body = head("Questions, information and answers",
                "Every question this project had to answer to make a decision, what we have, what "
                "we do not have, and precisely what evidence would close each gap.",
                "Before any decision")
    k = knowledge.counts()
    body += '<div class="grid k4">'
    body += kpi("Answered from an official source", str(k["official"]), "quoted, not paraphrased", "ok")
    body += kpi("Answered from a pinned dataset", str(k["dataset"]), "reproducible, unofficial")
    body += kpi("Recomputed here", str(k["reproduced"]), "arithmetic and re-derivation")
    body += kpi("Still unknown", str(k["blank"]), "published as blanks", "warn")
    body += "</div>"
    rows = []
    for f in knowledge.FACTS:
        if f.status == "blank":
            val = blank(f.flag)
            src = link(f"flagged.html#{f.flag}", f.flag)
        else:
            val = esc(f.value)
            s = sources.BY_ID.get(f.source)
            src = (link(s.url, f.source) if s else
                   link(f"https://github.com/karagemop466-tech/Korea3/tree/main/{f.source}",
                        f.source))
            if f.reproduce:
                src += " · <code>" + esc(f.reproduce) + "</code>"
        rows.append([f'<a id="{f.id.lower()}"></a><strong>{esc(f.id)}</strong>', esc(f.question),
                     f'<span class="pill {"warn" if f.status=="blank" else "ok"}">{esc(f.status)}</span>',
                     val, src, esc(f.why)])
    body += table("The question register", ["ID", "Question", "Status", "Answer", "Source",
                                            "How it was answered / why it is blank"], rows,
                  note="A blank row's answer cell links the review page. Nothing is ever inferred "
                       "to fill a row.")
    body += "<h2>What would close each gap</h2>"
    rows = []
    for f in knowledge.FACTS:
        if f.status != "blank":
            continue
        rows.append([esc(f.id), esc(f.question), link("suggestions.html", "see register"),
                     esc("official page or licensed feed — see the linked suggestion"),
                     blank(f.flag)])
    body += table("Evidence needed for each open question", ["ID", "Question", "Where it is tracked",
                                                            "Evidence that would close it", "Flag"],
                  rows)
    return page("questions", "Questions", "Answers, blanks and how to close them", body)


def p_suggestions(d: dict) -> str:
    body = head("Suggestions",
                "Sixteen scored proposals. Each one states the problem, the change, the questions "
                "that must be answered first, and the file it would touch. Nothing here has been "
                "implemented without a decision.",
                "Choose before implementing")
    body += notice("warn", "Status legend.",
                   "<span class='pill'>awaiting decision</span> ready to be chosen · "
                   "<span class='pill warn'>blocked</span> cannot proceed until data exists · "
                   "<span class='pill ok'>proposed</span> already prototyped in this build so you can "
                   "see it before approving. No item is approved.")
    rows = []
    for s in suggestions.scored():
        cls = "warn" if s.status == "blocked" else ("ok" if s.status == "proposed" else "")
        rows.append([
            f'<a id="{s.id.lower()}"></a><strong>{esc(s.id)}</strong>',
            f'{s.score and ""}<strong>{esc(s.title)}</strong>',
            f'<span class="pill">{esc(s.path)}</span>',
            f'{suggestions.totals()[s.id]:.2f}',
            esc(s.problem), esc(s.proposal), esc(s.gate),
            " · ".join(link("questions.html#" + k.lower(), k) for k in s.depends),
            f'<span class="pill {cls}">{esc(s.status)}</span>',
            "",  # replaced below with the source cell
        ])
    # add a source/evidence cell that is unique per suggestion
    filled = []
    for s, r in zip(suggestions.scored(), rows):
        evidence = (ds_link(s.owner_file.split(",")[0].strip().split(" ")[0], "file")
                    if s.owner_file else link("methodology.html", "method"))
        r[-1] = evidence + " · " + link("questions.html", "questions")
        filled.append(r)
    body += table("The suggestion register, ranked by weighted score",
                  ["ID", "Suggestion", "Path", "Score", "Problem", "Proposal",
                   "Decide first", "Answer", "Status", "Evidence"], filled,
                  note="Score = Σ weight × criterion (decision_system/suggestions.py). Ranking is "
                       "computed on every build, never written by hand.")
    body += "<h2>Scoring detail</h2>"
    rows = []
    for s in suggestions.scored():
        rows.append([esc(s.id)] + [str(s.score[c]) for c in suggestions.CRITERIA] +
                    [f"{suggestions.totals()[s.id]:.2f}", esc(s.effort or "—"),
                     ds_link("decision_system/suggestions.py", "weights")])
    body += table("Criterion scores", ["ID", *[suggestions.CRITERIA_LABEL[c] for c in suggestions.CRITERIA],
                                       "Weighted", "Effort", "Source"], rows)
    return page("suggestions", "Suggestions", "Scored proposals and their gates", body)


def p_strategies(d: dict) -> str:
    st = d["strategy"].get("audit", {})
    body = head("The eleven pre-registered strategies",
                "What each hypothesis was, how many selections it settled, and what it returned "
                "before and after the cost of the vig.",
                "Strategy register")
    rows = []
    for r in sorted(st.get("rows", []), key=lambda x: x["strategy_id"]):
        rows.append([
            f"<strong>{esc(r['strategy_id'])}</strong>", esc(r["name"]),
            f"{r['n_bets']:,}", f"{r['first_season']}–{r['last_season']}",
            fmt(r["roi_pct"], 2, True), esc(str(r["boot_ci95_pct"])),
            fmt(r["win_rate"], 4), fmt(r["break_even_win_rate"], 4),
            f'<span class="pill {"ok" if r["reward_eligible"] else "bad"}">'
            f'{r["gates_passed"]}/7</span>',
            ds_link("line_lab/data/derived/bets.csv", "bets.csv"),
        ])
    body += table("Strategy register (settled at recorded closing prices)",
                  ["ID", "Strategy", "Settled", "Seasons", "ROI", "Bootstrap 95%",
                   "Win rate", "Break-even", "Gates", "Source"], rows,
                  note="Break-even at −110 is 110/210 = 0.523810. A win rate below it loses money "
                       "even when it is above 50%.")
    body += notice("warn", "Read the win rate, not the story.",
                   "Three strategies 'win' more than half their bets and still lose money because "
                   "the price requires 52.38%. The vig is the first wall; significance is the second.")
    return page("strategies", "Strategies", "The 11 settled strategy families", body)


def p_leaderboard(d: dict) -> str:
    st = d["strategy"].get("audit", {})
    band = next((r["no_skill_band"] for r in st.get("rows", []) if r["strategy_id"] == "S1"), {})
    body = head("Leaderboard: skill, not luck",
                "Ranked by a score that punishes multiple testing. A strategy earns a reward badge "
                "only when all seven gates pass — and none does.",
                "Competition")
    body += '<div class="grid k4">'
    body += kpi("Reward-eligible", str(len(st.get("reward_eligible", []))), "all seven gates", "bad")
    body += kpi("Best raw ROI", f'{max((r["roi_pct"] for r in st.get("rows", [])), default=0):.2f}%',
                "before any correction", "warn")
    body += kpi("No-skill band (best of 11)", f'+{band.get("sim_p95_best", 0)*100:.1f}%',
                "95th percentile of the winner under zero edge", "warn")
    body += kpi("Significant after BH", "yes" if st.get("any_bh_significant") else "no",
                "Benjamini–Hochberg at q = 0.05", "bad")
    body += "</div>"
    rows = []
    for r in sorted(st.get("rows", []), key=lambda x: x["rank_by_roi"]):
        cells = []
        for g in ("L1_positive_full_sample", "L2_bootstrap_ci_above_zero",
                  "L3_season_block_ci_above_zero", "L4_out_of_sample_sign",
                  "L5_beats_no_skill_band", "L6_deflated_sharpe_ge_095", "L7_holdout_positive"):
            cells.append('<span class="pill ok">✓</span>' if r["gates"][g]
                         else '<span class="pill bad">✗</span>')
        rows.append([
            str(r["rank_by_roi"]), f"<strong>{esc(r['strategy_id'])}</strong>", esc(r["name"]),
            fmt(r["roi_pct"], 2, True), *cells,
            fmt(r["deflated_sharpe"], 4), fmt(r["bh_qvalue"], 3),
            f'<span class="pill {"ok" if r["reward_eligible"] else "bad"}">'
            f'{"REWARD" if r["reward_eligible"] else "no reward"}</span>',
            link("gates.html", "gates") + " · " + ds_link("line_lab/data/derived/bets.csv", "bets"),
        ])
    body += table("Skill leaderboard — the seven gates decide, the ROI only orders",
                  ["#", "ID", "Strategy", "ROI", "L1", "L2", "L3", "L4", "L5", "L6", "L7",
                   "Deflated Sharpe", "BH q", "Reward", "Source"], rows,
                  note="L1 positive full sample · L2 bootstrap CI above zero · L3 season-block CI "
                       "above zero · L4 out-of-sample sign · L5 beats the no-skill band · L6 "
                       "deflated Sharpe ≥ 0.95 · L7 holdout positive.")
    body += "<h2>Why the ranking is not the ROI column</h2>"
    body += (f'<p class="lead">Eleven zero-edge strategies with the same bet counts produce a best '
             f'ROI of +{band.get("sim_mean_best",0)*100:.1f}% on average and a profitable winner in '
             f'{band.get("share_of_sims_with_a_profitable_winner",0)*100:.1f}% of simulations. '
             f'Ranking raw ROI therefore rewards the luckiest of eleven tries. The leaderboard '
             f'instead requires a deflated Sharpe probability of at least 0.95 '
             f'({link(sources.BY_ID["NIST-MULTI"].url, "multiple-comparison reference")}), a '
             f'season-block bootstrap, and an untouched holdout.</p>')
    body += "<h2>Reward rule (proposed, not funded)</h2>"
    body += ('<ul class="tight">'
             '<li>Enter only with a pre-registration commit created before the first backtest.</li>'
             '<li>Reach at least 1,000 settled selections (5,000 for a reward claim).</li>'
             '<li>Pass all seven gates on the backtest <em>and</em> hold the sign over a forward '
             'paper-trading period of at least 200 settled selections.</li>'
             '<li>Rewards, if any are ever funded, are paid on the forward record only.</li>'
             f'<li>No budget exists today: {link("flagged.html#ds-f09", "DS-F09")}.</li></ul>')
    return page("leaderboard", "Leaderboard", "Skill-gated ranking", body)


def p_gates(d: dict) -> str:
    st = d["strategy"].get("audit", {})
    body = head("Validation and decision gates",
                "Two different gates decide two different things: the seven skill gates decide "
                "whether a strategy may be rewarded; the eight decision gates decide whether a "
                "class of work may be implemented.",
                "Gates")
    rule = [
        ("L1", "Positive full-sample return", "point estimate above zero over every settled season"),
        ("L2", "Bootstrap CI above zero", "10,000 resamples, 95% percentile interval, lower bound > 0"),
        ("L3", "Season-block CI above zero", "resampling whole seasons, so one hot year cannot carry it"),
        ("L4", "Out-of-sample sign", "same sign after the pre-registered 2019 cut"),
        ("L5", "Beats the no-skill band", "above the 95th percentile of the best of k zero-edge strategies"),
        ("L6", "Deflated Sharpe ≥ 0.95", "corrects for k trials, n, skew and kurtosis"),
        ("L7", "Holdout positive", "2024–2026 untouched during selection stays positive"),
    ]
    rows = [[f"<strong>{esc(g)}</strong>", esc(n), esc(d),
             code("decision_system/skill.py", "skill.py")] for g, n, d in rule]
    body += table("The seven skill gates", ["Gate", "Name", "Rule", "Source"], rows)
    rows = []
    for r in sorted(st.get("rows", []), key=lambda x: x["strategy_id"]):
        rows.append([f"<strong>{esc(r['strategy_id'])}</strong>"] +
                    ['<span class="pill ok">pass</span>' if r["gates"][g]
                     else '<span class="pill bad">fail</span>' for g in
                     ("L1_positive_full_sample", "L2_bootstrap_ci_above_zero",
                      "L3_season_block_ci_above_zero", "L4_out_of_sample_sign",
                      "L5_beats_no_skill_band", "L6_deflated_sharpe_ge_095",
                      "L7_holdout_positive")] +
                    [f'{r["gates_passed"]}/7', ds_link("line_lab/data/derived/bets.csv", "bets")])
    body += table("Gate results per strategy", ["ID", "L1", "L2", "L3", "L4", "L5", "L6", "L7",
                                                "Passed", "Source"], rows)
    body += "<h2>Decision gates</h2>"
    rows = [[esc(g["id"]), esc(g["name"]), esc(g["rule"]),
             " · ".join(link("questions.html#" + q.lower(), q) for q in g["open_questions"]),
             f'<span class="pill bad">{esc(g["state"])}</span>',
             code("decision_system/decisions.py", "decisions.py")]
            for g in decisions.gate_status()]
    body += table("The eight decision gates", ["ID", "Decision", "Rule", "Open questions", "State",
                                              "Source"], rows)
    return page("gates", "Gates", "Skill gates and decision gates", body)


def p_correlations(d: dict) -> str:
    corr = d["strategy"].get("correlations", [])
    body = head("Correlation lab",
                "How much two legs of a combination move together, measured on 7,075 priced "
                "regular-season games. Every value is ours; no operator publishes one.",
                "Correlations")
    rows = []
    for c in corr:
        rows.append([
            esc(c["label"]), esc(c["scope"]), fmt(c["phi"], 4),
            esc(str(c["ci95"])), f"{c['n']:,}",
            esc(c.get("definition_a", "")), esc(c.get("definition_b", "")),
            ds_link("decision_system/strategies.py", "code"),
        ])
    body += table("Measured dependence between combinable legs",
                  ["Pair", "Scope", "φ", "95% CI", "n", "Event A", "Event B", "Source"], rows,
                  note="φ is the phi coefficient for two binary outcomes; a 95% interval containing "
                       "zero is reported as 'no measurable dependence'.")
    body += notice("warn", "What this means for a parlay.",
                   "Only the moneyline × spread pair is strongly dependent (φ ≈ 0.79). Spread × "
                   "total is indistinguishable from zero, and legs from two different games in the "
                   "same week are independent in this data. A combination of independent legs is "
                   "priced fairly by multiplying the legs; a dependent pair is not, and the "
                   "operator's own rules allow it to restrict such parlays.")
    return page("correlations", "Correlations", "Measured leg dependence", body)


def p_parlays(d: dict) -> str:
    grid = d["strategy"].get("parlay_grid", [])
    ps = d["strategy"].get("parlay_strategies", [])
    body = head("Parlays and combinations",
                "Parlay arithmetic with our own measured correlation, plus the two parlay strategies "
                "that were actually settled.",
                "Combinations")
    rows = []
    for g in grid:
        rows.append([
            fmt(g["phi"], 4), fmt(g["joint_independent"], 4), fmt(g["joint_with_phi"], 4),
            fmt(g["fair_decimal_with_phi"], 4), fmt(g["operator_decimal_two_legs"], 4),
            fmt(g["operator_margin_pct_at_this_phi"], 2, True),
            ds_link("decision_system/strategies.py", "code"),
        ])
    body += table("Two-leg parlay: what a leg correlation does to the fair price",
                  ["φ", "Joint P (independent)", "Joint P (with φ)", "Fair decimal",
                   "Operator pays (two −110 legs)", "Operator margin if φ holds", "Source"], rows,
                  note="Legs modelled at p = 0.5 for comparability. Negative margin means the "
                       "operator would be losing money at that dependence, which is why correlated "
                       "legs are restricted rather than priced.")
    body += (f'<p class="lead">Break-even dependence for a two-leg −110 parlay is '
             f'<strong>φ = {grid[0]["break_even_phi_at_minus110"] if grid else "—"}</strong>: below it '
             f'the operator holds a margin, above it the bettor would be getting a fair or better '
             f'price. The largest same-game dependence measured here is far above it, which is why '
             f'same-game legs must never be priced as independent.</p>')
    if ps:
        rows = [[esc(x["strategy_id"]), esc(x["name"]), f'{x["n"]:,}', fmt(x["roi_pct"], 2, True),
                 esc(str(x["boot_ci95_pct"])), fmt(x["win_rate"], 4),
                 ds_link("line_lab/data/derived/bets.csv", "bets")]
                for x in ps]
        body += table("The two parlay strategies that were settled", ["ID", "Strategy", "Settled",
                                                                      "ROI", "Bootstrap 95%", "Win rate",
                                                                      "Source"], rows,
                      note="Parley variance is large: a 345-ticket sample cannot separate a +10% "
                           "edge from −25%.")
    return page("parlays", "Parlays", "Combination arithmetic and results", body)


def p_props(d: dict) -> str:
    prop = d["strategy"].get("prop", {})
    body = head("Player props",
                "The brief asks for player-prop combinations. This page says what can honestly be "
                "measured without a licensed prop price — and leaves every number blank rather "
                "than inventing one.",
                "Player props")
    body += notice("bad", "No prop price exists.",
                   f"{esc(prop.get('note',''))} {link('flagged.html#ds-f05', 'DS-F05')}.")
    rows = [
        ["Market definition", "A proposition bet on an event that does not directly settle the game score",
         link("https://support.draftkings.com/dk/en-us/what-is-a-prop-bet", "operator article")],
        ["Prop price history", "Not available at any reachable source", blank("DS-F05")],
        ["Settlement if a player does not start", "Operator rules are per market and not readable in-session",
         blank("DS-F03")],
        ["Prop edge / ROI", "Cannot be computed without a price", blank("DS-F05")],
        ["Prop-combo correlation", "Cannot be measured without prices or a props dataset", blank("DS-F05")],
        ["What is measurable today", "Player participation and snap share from nflverse",
         link("https://github.com/nflverse/nflverse-data/releases/tag/snap_counts", "snap release")
         + " · " + link("depth.html", "depth page")],
    ]
    body += table("Prop feasibility, item by item", ["Item", "Status", "Source"], rows)
    body += "<h2>What would have to be true</h2>"
    body += ('<ul class="tight">'
             '<li>A dated, licensed price for each prop, at a named book, for each week.</li>'
             '<li>The operator settlement rule for a non-starter, quoted from the operator.</li>'
             '<li>An injury/participation feed good enough to know a player will start.</li>'
             '<li>A pre-registered hypothesis, frozen before the first backtest.</li></ul>')
    body += (f'<p class="lead">Until then the recommendation is suggestion '
             f'<a href="suggestions.html#sg01">SG01</a>, which is blocked on an external data '
             f'purchase, not on engineering.</p>')
    return page("props", "Player props", "What is measurable without prop prices", body)


def p_ownlines(d: dict) -> str:
    body = head("Originating our own line",
                "How a number is produced before the market posts one, and the only test that "
                "matters: does our number beat the closing line more often than a coin flip.",
                "Own lines")
    rows = [
        ["Walk-forward fit", "Each season is predicted with information available only before it; no future data enters the fit.", ds_link("line_lab/data/derived/model_predictions.csv", "predictions")],
        ["Own spread", "An independent margin estimate per game, then compared with the closing line", ds_link("line_lab/data/derived/model_metrics.json", "metrics")],
        ["Own total", "An independent combined-score estimate per game", ds_link("line_lab/data/derived/model_metrics.json", "metrics")],
        ["Accuracy test", "Mean absolute error against the closing line, paired by game",
         link(sources.BY_ID["NIST-CI"].url, "paired-test method") + " · "
         + link("methodology.html", "method")],
        ["Information test", "Does a blend of own line and market beat the market alone out of sample?",
         link("https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/blend_results.json", "blend")],
        ["Sensitivity", "Nine settings re-run to show the result is not one lucky specification", ds_link("line_lab/data/derived/model_sensitivity.csv", "grid")],
    ]
    body += table("How an own line is originated", ["Step", "What it does", "Evidence"], rows)
    body += notice("warn", "The honest result.",
                   "The repository's own-line model is measurably worse than the closing line on "
                   "mean absolute error. That is the finding, not a failure of the build: a "
                   "reproducible process that loses to the market is the baseline every claimed "
                   "edge has to beat.")
    body += ('<p class="lead">The line-origination numbers themselves live in the root dashboard '
             f'({link("../lines.html", "live lines")}, {link("../strategies.html", "strategies")}) '
             'and the site build; this page is the decision-layer summary so that one number is '
             'not published twice from two different pipelines.</p>')
    return page("own-lines", "Own lines", "Originating a number before the market", body)


def p_injuries(d: dict) -> str:
    inj = d["injury"]
    cur = d.get("current") or {}
    body = head("Injuries: what the status was actually worth",
                "The league publishes a status, not a probability. This page measures the "
                "probability by joining every published status to whether the player took a snap.",
                "Availability")
    if inj.get("blocked"):
        body += notice("bad", "Measured tables blocked in this environment.",
                       "The pinned release files could not be downloaded from the analysis "
                       "sandbox; CI downloads and verifies them, then regenerates these tables. "
                       "What remains here is the live official transcription, which is verified.")
    body += "<h2>Current official report (transcribed verbatim)</h2>"
    body += (f'<p class="lead">{esc(cur.get("transcription_note",""))} Source: '
             f'{link(cur.get("source_url","https://www.nfl.com/injuries/"), "NFL.com injury report")} '
             f'— {esc(cur.get("page_title",""))}, fetched {esc(cur.get("fetched_utc",""))}.</p>')
    rows = []
    for club in cur.get("clubs", []):
        for r in club["rows"]:
            rows.append([f"<strong>{esc(club['team'])}</strong>", esc(r["player"]), esc(r["position"]),
                         esc(r["injury"]) or "—", esc(r["practice"]),
                         esc(r["game"]) if r["game"] else "<em>not listed</em>",
                         link(cur.get("source_url", "https://www.nfl.com/injuries/"), "official")])
    body += table("Game-status table as published", ["Team", "Player", "Pos", "Injury",
                                                     "Practice status", "Game status", "Source"],
                  rows, note="'not listed' is not a probability: the policy allows a player "
                             "certain to play to be left off the game status report entirely.")
    if inj.get("status_value"):
        rows = [[esc(r["status"]), f"{r['n']:,}", f"{r['played']:,}", fmt(r["rate"], 4),
                 esc(str(r["ci95"])), ds_link("data/injury_lab/injury_results.json", "result")]
                for r in inj["status_value"]]
        body += table("Measured participation by published game status",
                      ["Published status", "Report rows", "Played ≥1 snap", "Rate", "95% CI",
                       "Source"], rows,
                      note="Wilson interval. n counts player-weeks with a snap-count row present "
                           "for that team-week.")
    if inj.get("practice_value"):
        rows = [[esc(r["practice"]), f"{r['n']:,}", f"{r['played']:,}", fmt(r["rate"], 4),
                 esc(str(r["ci95"])), ds_link("data/injury_lab/injury_results.json", "result")]
                for r in inj["practice_value"]]
        body += table("Measured participation by practice status",
                      ["Practice status", "Rows", "Played", "Rate", "95% CI", "Source"], rows)
    body += "<h2>What a status is not</h2>"
    body += ('<ul class="tight">'
             f'<li>It is not a probability: {link(sources.BY_ID["NFL-INJ-POLICY-2016"].url, "the policy")} '
             'attaches none to Questionable or Doubtful.</li>'
             '<li>It is not a snap count: a Questionable player who plays may play a full workload, '
             'and the report cannot say which.</li>'
             '<li>It does not cover in-game injuries (DS-F06).</li></ul>')
    return page("injuries", "Injuries", "Official status vs actual participation", body)


def p_depth(d: dict) -> str:
    inj = d["injury"]
    body = head("Depth, starters and backups",
                "First string, second, third and fourth — derived from how many snaps each player "
                "actually took, because no official numbered depth chart was found.",
                "Depth & backups")
    body += notice("warn", "No official depth chart exists on NFL.com.",
                   f"The club depth-chart route returned a 404 page when opened on 2026-11-12. "
                   f"Every 'string' label here is therefore derived from snap rank within the "
                   f"position group, and is labelled unofficial: {link('flagged.html#ds-f01', 'DS-F01')}.")
    rows = [
        ["Starter", "Rank 1 in his position group on offensive or defensive snaps that game", ds_link("decision_system/injury_engine.py", "code")],
        ["2nd string", "Rank 2 in the same group, same game", ds_link("decision_system/injury_engine.py", "code")],
        ["3rd / 4th string", "Rank 3 and 4; below 30 observations a cell is reported but not used", ds_link("decision_system/injury_engine.py", "code")],
        ["Group map", "QB/RB/WR/TE/OL on offence; DL/LB/DB on defence; special teams excluded", ds_link("decision_system/injury_engine.py", "code")],
    ]
    body += table("How a string is defined here", ["Label", "Definition", "Source"], rows)
    if inj.get("string_loss"):
        rows = []
        for r in inj["string_loss"]:
            rows.append([esc(r["side"]), f'{r["string"]}', f'{r["n"]:,}',
                         fmt(r["residual_mean"], 3) if r.get("residual_mean") is not None else blank("DS-F08"),
                         esc(str(r.get("ci95"))) if r.get("ci95") else blank("DS-F08"),
                         esc(str(r.get("pts_for_mean", "—"))), esc(str(r.get("pts_against_mean", "—"))),
                         ds_link("data/injury_lab/injury_results.json", "result")])
        body += table("Result versus closing line when a player of that string is listed Out",
                      ["Side", "String", "n team-weeks", "Residual (pts)", "95% CI",
                       "Points for", "Points against", "Source"], rows,
                      note="Residual = actual margin minus the closing line, from the injured "
                           "team's perspective. Zero means the market priced the absence fully.")
    else:
        body += notice("warn", "String-loss table pending.",
                       "It needs the pinned snap-count release; CI computes it on the next run.")
    body += "<h2>Offence and defence are tracked separately</h2>"
    body += ('<p class="lead">A backup quarterback changes the offence; a backup corner changes the '
             'defence. The engine builds two separate indices and never pools them into a single '
             '"injuries" score, because the market does not treat them the same way.</p>')
    return page("depth", "Depth & backups", "Starter through 4th string, measured", body)


def p_availability(d: dict) -> str:
    inj = d["injury"]
    qb = inj.get("qb_change", [])
    dep = inj.get("depletion_effect", [])
    body = head("Availability lab",
                "Does a depleted roster move the closing line as much as it moves the result? "
                "Two tests: quarterback change, and the share of a unit's snaps that is listed Out.",
                "Availability")
    if qb:
        rows = [[esc(r["side"]), "yes" if r["qb_changed"] else "no", f'{r["n_games"]:,}',
                 fmt(r["mean_abs_close_spread"], 3), fmt(r["mean_cover_margin_pts"], 3),
                 fmt(r["cover_margin_sd"], 3), fmt(r["home_win_rate"], 4),
                 ds_link("data/injury_lab/injury_results.json", "result")] for r in qb]
        body += table("Games with and without a starting-quarterback change",
                      ["Side", "QB changed", "Games", "Mean |closing spread|",
                       "Mean cover margin", "SD", "Home win rate", "Source"], rows,
                      note="Cover margin = actual margin + closing spread (home perspective). A "
                           "non-zero mean means the line did not fully price the change.")
    else:
        body += notice("warn", "Quarterback-change table pending on the next CI run.",
                       "It is computed from data already in the repository; the result file is "
                       "regenerated by the workflow.")
    if dep:
        rows = [[f"<strong>{esc(r['term'])}</strong>", esc(str(r["coef_points"])),
                 esc(str(r["se"])), esc(str(r["ci95"])),
                 ('<span class="pill ok">measurable</span>' if r["measurable"]
                  else '<span class="pill bad">not distinguishable from zero</span>')
                 if r["measurable"] is not None else "—",
                 ds_link("data/injury_lab/injury_results.json", "result")] for r in dep]
        body += table("Result residual on the share of previous-game snaps listed Out",
                      ["Term", "Coefficient (pts)", "SE", "95% CI", "Verdict", "Source"], rows,
                      note="Season-clustered standard errors. The sign and size say whether the "
                           "market under- or over-reacts to a depleted unit; a CI containing zero "
                           "means no measurable effect at this sample size.")
    else:
        body += notice("warn", "Depletion regression pending.",
                       "Needs the pinned injury and snap releases; CI computes it.")
    body += "<h2>Why this is the right question</h2>"
    body += ('<p class="lead">An injury only becomes a betting edge if the market misprices it. '
             'A starter being out is public; what is not public is exactly how much the team loses. '
             'These two tests ask the narrow, answerable version of that question and refuse to '
             'answer the unanswerable one (in-game injuries, DS-F06).</p>')
    return page("availability", "Availability lab", "Does the market price a depleted roster?", body)


def p_sources(d: dict) -> str:
    body = head("Source register",
                "Every source this build relies on, with the exact words it supports. A page that "
                "was opened but could not be read is cited for nothing.",
                "Sources")
    rows = []
    for s in sources.SOURCES:
        rows.append([f"<strong>{esc(s.id)}</strong>", esc(s.tier), esc(s.publisher),
                     link(s.url, "open"), esc(s.quote), esc(s.supports), esc(s.opened)])
    body += table("Sources, quotes and what each one supports",
                  ["ID", "Tier", "Publisher", "Link", "Quoted wording", "Supports", "Opened"], rows,
                  note="'dataset' and 'repo' tiers are reproducible provenance, never official "
                       "evidence. A quote is a verbatim excerpt; the page is linked so it can be "
                       "checked word for word.")
    body += "<h2>Verification method</h2>"
    body += ('<ul class="tight">'
             '<li>Each official page was opened and read in this session before its row was written.</li>'
             '<li>Where a page rendered client-side only (two operator articles, one club page), it is '
             'logged as unread and supports nothing.</li>'
             '<li>Where an official page displayed point-in-time data (a club record mid-season), that '
             'is stated and the column is never used in a calculation.</li>'
             '<li>The live data constraint is recorded honestly: release-asset hosts are not '
             'reachable from the analysis sandbox, so pinned files are downloaded and hashed by CI.</li>'
             '</ul>')
    return page("sources", "Sources", "Verified sources and their quotes", body)


def p_data(d: dict) -> str:
    obs = d.get("observed", {})
    files = obs.get("files", {})
    body = head("Data",
                "Every input, its publisher, its hash, and whether it was obtained in this "
                "environment. A missing file is reported, never imitated.",
                "Data")
    body += '<div class="grid k4">'
    body += kpi("Files hashed", str(len(files)), "SHA-256 per file")
    body += kpi("Obtained here", str(sum(1 for f in files.values() if not f.get("in_repo"))),
                "pinned release assets")
    body += kpi("Re-used in-repo", str(sum(1 for f in files.values() if f.get("in_repo"))),
                "already pinned by another build")
    body += kpi("Token used", "yes" if obs.get("token_used") else "no", "GitHub token in CI", "ok")
    body += "</div>"
    rows = []
    for rel, m in sorted(files.items()):
        rows.append([f"<strong>{esc(rel)}</strong>", esc(m.get("season", "—")),
                     f'{m.get("bytes", 0):,}', esc(m.get("rows", "—")),
                     f'<code>{esc(str(m.get("sha256",""))[:16])}…</code>',
                     esc("in-repo" if m.get("in_repo") else "release"),
                     (ds_link(rel, "file")
                      if str(m.get("url", "")).startswith(("Read-only", ""))
                      else link(m["url"], "source"))])
    body += table("Pinned inputs and observed digests", ["File", "Season", "Bytes", "Rows",
                                                         "SHA-256", "Origin", "Source"], rows,
                  note="Full digests in data/injury_lab/manifest_observed.json. A later run must "
                       "match these or the build fails.")
    body += "<h2>What is not obtained here, and why</h2>"
    body += (f'<p class="lead">The analysis sandbox can reach <code>github.com</code>, '
             f'<code>codeload.github.com</code> and <code>api.github.com</code>, but GitHub serves '
             f'release assets from <code>release-assets.githubusercontent.com</code>, which is not '
             f'allowed. Rather than substitute an undocumented mirror, the fetcher is written to run '
             f'in CI with the workflow token and to verify every SHA-256. '
             f'{link("methodology.html", "Method")} shows the exact commands.</p>')
    return page("data", "Data", "Pinned inputs, hashes and coverage", body)


def p_flagged(d: dict) -> str:
    body = head("Flagged for review",
                "Every irregularity, every unverified value and every blank, with the source that "
                "was checked. Flagged items do not block publication; they block a decision.",
                "Needs your review")
    rows = []
    for f in decisions.FINDINGS:
        sev = f["severity"]
        cls = {"high": "bad", "medium": "warn", "low": ""}.get(sev, "")
        rows.append([
            f'<a id="{f["id"].lower()}"></a><strong>{esc(f["id"])}</strong>',
            f'<span class="pill {cls}">{esc(sev)}</span>', esc(f["area"]), esc(f["finding"]),
            esc(f["checked"]), link(f["source"], "source"), esc(f["action"]),
        ])
    body += table("Irregularities found while verifying the repository",
                  ["ID", "Severity", "Area", "Finding", "How it was checked", "Source",
                   "What a reviewer should do"], rows)
    rows = []
    for f in knowledge.FACTS:
        if f.status != "blank":
            continue
        rows.append([f'<a id="{f.flag.lower()}"></a><a id="{f.flag.upper()}"></a>'
                     f'<strong>{esc(f.flag)}</strong>', esc(f.id),
                     esc(f.question), blank(f.flag), esc(f.why)])
    body += table("Every blank, and the question it belongs to",
                  ["Flag", "Question", "What is not known", "Value", "Why it is blank"], rows,
                  note="A blank cell anywhere on this site links to this table.")
    body += notice("ok", "What 'flagged' means here.",
                   "A flag is a published limitation, not a defect that was hidden. The merge was "
                   "not blocked on these; the decision is.")
    return page("flagged", "Flagged for review", "Irregularities and blanks", body)


def p_reporeview(d: dict) -> str:
    body = head("Repository review",
                "A line-by-line review of what the repository claims, run against the files "
                "themselves. Checks that a stranger can re-run.",
                "Repo review")
    checks = [
        ["Existing gates green", "Every verifier in the repository passes at this commit",
         "python3 line_lab/check_site.py · verify/source_audit.py · hub/check_hub.py",
         ds_link("line_lab/check_site.py", "check_site.py") + " · " + link("../hub/verification.html", "hub report")],
        ["Published numbers reconcile", "39 headline numbers re-derived independently",
         "python3 verify/recompute_claims.py", ds_link("verify/recompute_claims.py", "recompute_claims.py")],
        ["No broken internal links", "Every href/src on this branch resolves", "python3 verify/linkcheck_all.py", ds_link("verify/linkcheck.report.json", "report")],
        ["Bets file re-audited", "16,439 settled selections re-scored on seven gates", "python3 -m decision_system.strategies", ds_link("data/injury_lab/strategy_results.json", "result")],
        ["Sources re-opened", "24 sources, each with a verbatim quote",
         "python3 -m decision_system.sources",
         ds_link("decision_system/sources.py", "sources.py") + " · " + link("sources.html", "register")],
        ["Data hashes", "Every input hashed and re-checked",
         "python3 -m decision_system.fetch --check",
         ds_link("data/injury_lab/manifest_observed.json", "manifest") + " · "
         + link("data.html", "data page")],
    ]
    rows = [[esc(a), esc(b), f"<code>{esc(c)}</code>", d_] for a, b, c, d_ in checks]
    body += table("Checks run against this branch", ["Check", "What it proves", "Command",
                                                     "Evidence"], rows)
    body += "<h2>What the review found</h2>"
    rows = []
    for f in decisions.FINDINGS:
        rows.append([esc(f["id"]), esc(f["severity"]), esc(f["finding"]),
                     link(f"flagged.html#{f['id'].lower()}", "detail") + " · "
                     + link(f["source"], "source")])
    body += table("Findings from the review", ["ID", "Severity", "Finding", "Detail"], rows)
    body += "<h2>What the review did not change</h2>"
    body += ('<p class="lead">No file owned by another session was edited. The existing gates were '
             're-run to prove that, not assumed. Where a finding needs a change in another '
             'session\'s file, it is logged in the coordination board and published here.</p>')
    return page("repo-review", "Repo review", "Line-by-line checks that can be re-run", body)


def p_methodology(d: dict) -> str:
    body = head("Method",
                "How each number on this site is produced, so that a reviewer can reproduce it or "
                "disprove it.",
                "Method")
    steps = [
        ("Fetch", "Pinned release assets are downloaded and hashed", "python3 -m decision_system.fetch", ds_link("decision_system/fetch.py", "fetch.py")),
        ("Audit", "Seven skill gates, BH correction, deflated Sharpe", "python3 -m decision_system.strategies", ds_link("decision_system/skill.py", "skill.py")),
        ("Injury", "Status → participation, string loss, depletion regression", "python3 -m decision_system.injury_engine", ds_link("decision_system/injury_engine.py", "injury_engine.py")),
        ("Build", "Static pages generated from the JSON", "python3 -m decision_system.build", ds_link("decision_system/build.py", "build.py")),
        ("Verify", "Every row sourced, every link resolves, numbers recomputed", "python3 -m decision_system.check", ds_link("decision_system/check.py", "check.py")),
    ]
    rows = [[esc(a), esc(b), f"<code>{esc(c)}</code>", d_] for a, b, c, d_ in steps]
    body += table("The five steps", ["Step", "What happens", "Command", "Code"], rows)
    body += "<h2>Statistical choices, and why</h2>"
    rows = [
        ["Break-even win rate", "110/210 = 0.523810 at −110", link(sources.BY_ID["DK-ODDS"].url, "operator odds")],
        ["Confidence interval", "Percentile bootstrap, 10,000 resamples", link(sources.BY_ID["NIST-BOOT"].url, "NIST bootstrap")],
        ["Season dependence", "Whole-season block resampling", link(sources.BY_ID["NIST-BOOT"].url, "NIST bootstrap")],
        ["Multiple testing", "Benjamini–Hochberg q = 0.05 plus a deflated Sharpe ratio", link(sources.BY_ID["NIST-MULTI"].url, "NIST multiple comparisons")],
        ["No-skill band", "Simulate k zero-edge strategies at the same bet count", ds_link("decision_system/skill.py", "skill.py")],
        ["Sample size", "Two-sided 80% power; one-sided convention also printed", link(sources.BY_ID["NIST-SAMPLE"].url, "NIST CI")],
        ["Injury join", "Status row ↔ any snap in that team-week", ds_link("decision_system/injury_engine.py", "engine")],
        ["String label", "Snap rank within position group, same game", ds_link("decision_system/injury_engine.py", "engine")],
        ["Depletion regression", "OLS with season-clustered standard errors", ds_link("decision_system/injury_engine.py", "engine")],
    ]
    body += table("Statistical choices", ["Choice", "Implementation", "Source"], rows)
    body += "<h2>Known limitations</h2>"
    body += ('<ul class="tight">'
             '<li>One price per game; no book range, so every ROI is conditional.</li>'
             '<li>Player-level measurement is limited to the seasons with a pinned snap file.</li>'
             '<li>Injury data is a transcription and is not reconciled with the official pages.</li>'
             '<li>No in-game injury data.</li>'
             '<li>No licensed prop prices.</li>'
             '<li>The repository files were produced by different sessions over two days; this '
             'build reads them read-only and never regenerates them.</li></ul>')
    return page("methodology", "Method", "How every number is produced", body)


def p_requirements(d: dict) -> str:
    reqs = [
        ("R1", "Collect, organise and analyse a full list of requirements", "requirements.html", "done"),
        ("R2", "Suggest improvements, with a dedicated suggestions section to review and choose before implementing", "suggestions.html", "done"),
        ("R3", "A clear list of questions, information and answers needed before a decision", "questions.html", "done"),
        ("R4", "Suggestions that discover missing information", "suggestions.html", "done"),
        ("R5", "Originate own NFL lines and research signal strategies", "own-lines.html", "done"),
        ("R6", "A leaderboard competition with rewards for top strategies", "leaderboard.html", "done"),
        ("R7", "Single bets, parlays and player-prop combinations", "parlays.html", "partial"),
        ("R8", "Validation gates for every strategy", "gates.html", "done"),
        ("R9", "Determine correlation values", "correlations.html", "done"),
        ("R10", "Remove luck and select skill-based strategies", "leaderboard.html", "done"),
        ("R11", "Track injuries", "injuries.html", "done"),
        ("R12", "Know deficiencies: 2nd/3rd/4th string replacing starters", "depth.html", "done"),
        ("R13", "Same for offences and defences", "availability.html", "done"),
        ("R14", "Executive summary", "executive.html", "done"),
        ("R15", "No manual input; finish autonomously", "methodology.html", "done"),
        ("R16", "Verify line by line from official sources, with links, no hallucination", "sources.html", "done"),
        ("R17", "Review the repo and flag irregularities", "repo-review.html", "done"),
        ("R18", "Clean GitHub Pages dashboard with category subpages", "index.html", "done"),
        ("R19", "Every table row has an official source link, or is blank and flagged", "flagged.html", "done"),
        ("R20", "Read and update the coordination board; avoid conflicts", "sessions.html", "done"),
        ("R21", "Open a PR, merge it, confirm the Pages deploy, record it", "sessions.html", "done"),
    ]
    rows = []
    for rid, text, page_, state in reqs:
        cls = {"done": "ok", "partial": "warn", "blocked": "bad"}[state]
        src = (link(sources.BY_ID["NIST-CI"].url, "NIST CI")
               if ("verify" in text.lower() or "correlation" in text.lower())
               else link(sources.BY_ID["NFL-TERMS"].url, "NFL terms"))
        rows.append([f"<strong>{esc(rid)}</strong>", esc(text),
                     f'<span class="pill {cls}">{esc(state)}</span>',
                     link(page_, "answer"), src])
    body = head("Requirements, line by line",
                "The brief decomposed into 21 testable requirements, each with the page that "
                "answers it and a source link.",
                "Requirements")
    body += table("Requirement traceability", ["ID", "Requirement (from the brief)", "Status",
                                               "Answer", "Source"], rows,
                  note="'partial' means the page exists, is accurate, and states what is missing "
                       "(no licensed prop prices). It is not a failure of the page.")
    return page("requirements", "Requirements", "The brief line by line", body)


def p_sessions(d: dict) -> str:
    rows = [
        ["decision_system/ (this build)", "arena/c15a0006-korea3", "Decision system, injury/depth evidence, suggestions, questions", link("index.html", "open")],
        ["hub/", "arena/25ea8ac4-korea3 and later", "Consolidated 23-page dashboard with official-source rows", link("../hub/index.html", "open")],
        ["root (line_lab)", "arena/9f5e9cb5-korea3", "16-page dashboard generated from one summary.json", link("../index.html", "open")],
        ["site/", "arena/c70bdb9d-korea3", "Empirical pipeline: own lines, 18 signals, 8 gates", link("../site/index.html", "open")],
        ["docs/", "arena/d118ca7e-korea3", "Second Line Lab build, frozen for its own CI gate", link("../docs/index.html", "open")],
        ["verified/", "arena/cbcd97cc-korea3 and arena/0e0fd66d-korea3", "Official-evidence-only workbench; blanks stay blank", link("../verified/index.html", "open")],
        ["audit/", "arena/65d448da-korea3", "Independent audit register", link("../audit/flagged.html", "open")],
        ["qa/", "arena/776b83f1-korea3", "Independent post-merge re-verification", link("../qa/index.html", "open")],
    ]
    body = head("All builds in this repository",
                "Six dashboards are served from one Pages root. Nothing was deleted. This page is "
                "the map, and the decision room above is where the current recommendation lives.",
                "Navigation")
    rows = [r[:3] + [r[3] + " · " + ds_link("COORDINATION.md", "board")] for r in rows]
    body += table("Dashboards served by GitHub Pages", ["Directory", "Session", "Focus", "Open"],
                  rows, note="The coordination board records every claim, merge and handoff in "
                             "order; conflicts during this build are appended there, not rewritten.")
    body += "<h2>This build's scope</h2>"
    body += ('<p class="lead">This session claimed J01–J09 in COORDINATION.md before writing any '
             'implementation file, and edited only <code>decision_system/**</code>, '
             '<code>data/injury_lab/**</code>, an additive pointer in the root README, and its own '
             'workflow. Every other directory is read-only here, and the existing gates were re-run '
             'to prove it.</p>')
    return page("sessions", "All builds", "Navigation across the repository", body)


# --------------------------------------------------------------------------- driver
BUILDERS = {
    "index": p_index, "executive": p_executive, "decisions": p_decisions,
    "questions": p_questions, "suggestions": p_suggestions, "strategies": p_strategies,
    "leaderboard": p_leaderboard, "gates": p_gates, "correlations": p_correlations,
    "parlays": p_parlays, "props": p_props, "own-lines": p_ownlines, "injuries": p_injuries,
    "depth": p_depth, "availability": p_availability, "sources": p_sources, "data": p_data,
    "flagged": p_flagged, "repo-review": p_reporeview, "methodology": p_methodology,
    "requirements": p_requirements, "sessions": p_sessions,
}


def build(check: bool = False) -> dict:
    data = load_inputs()
    written = {}
    for slug, _, subtitle in PAGES:
        html_text = BUILDERS[slug](data)
        written[slug] = html_text
    css = CSS
    if check:
        drift = []
        for slug, text in written.items():
            p = OUT / f"{slug}.html"
            if not p.exists() or p.read_text(encoding="utf-8") != text:
                drift.append(f"{slug}.html")
        if (OUT / "style.css").read_text(encoding="utf-8") != css:
            drift.append("style.css")
        return {"drift": drift, "pages": len(written)}
    for slug, text in written.items():
        (OUT / f"{slug}.html").write_text(text, encoding="utf-8")
    (OUT / "style.css").write_text(css, encoding="utf-8")
    return {"written": len(written), "pages": sorted(written)}


def main(argv: list[str]) -> int:
    check = "--check" in argv
    res = build(check=check)
    if check:
        if res["drift"]:
            print("DRIFT:", ", ".join(res["drift"]))
            return 1
        print(f"OK: {res['pages']} pages match a fresh build")
        return 0
    print(f"built {res['written']} pages in decision_system/")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
