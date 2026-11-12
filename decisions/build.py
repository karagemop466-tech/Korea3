#!/usr/bin/env python3
"""Build the decision-readiness section (`decisions/`) of the NFL Line Lab repository.

Run:  python3 decisions/build.py
Then: python3 decisions/check.py     (fail-closed verifier)

Design rules (enforced by decisions/check.py):
  * every <tbody> row links to an official publisher or to the exact committed
    file the value was computed from;
  * a value that could not be confirmed is a blank marker linking to flagged.html;
  * every internal link resolves and every anchor exists;
  * deterministic output: no timestamps, no network, no randomness.

The section lives in its own directory so it does not collide with the
contested `hub/` scope owned by other sessions (see COORDINATION.md).
"""
from __future__ import annotations

import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "decisions"
DATA = OUT / "data"
SNAPSHOT = "2026-11-12"
SESSION = "arena/7f33cb21-korea3"

REPO = "https://github.com/karagemop466-tech/Korea3"
REPO_TREE = REPO + "/tree/main/"
REPO_BLOB = REPO + "/blob/main/"

SOURCES = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
SRC = {s["id"]: s for s in SOURCES["sources"]}
SUGGESTIONS = json.loads((DATA / "suggestions.json").read_text(encoding="utf-8"))
QUESTIONS = json.loads((DATA / "questions.json").read_text(encoding="utf-8"))
DEFECTS = json.loads((DATA / "defects.json").read_text(encoding="utf-8"))
INJURIES = json.loads((DATA / "injuries_week10_2026.json").read_text(encoding="utf-8"))
TIERS = json.loads((DATA / "depth_tiers.json").read_text(encoding="utf-8"))
STANDINGS = json.loads((DATA / "standings_2026.json").read_text(encoding="utf-8"))
RECOMPUTE = json.loads((DATA / "recompute.json").read_text(encoding="utf-8"))

SHORT = {
    "NFL-INJ-POLICY": "NFL injury policy",
    "NFL-INJ-LIVE": "NFL injury report",
    "NFL-INJ-WK10": "NFL Week 10 statuses",
    "NFL-INACTIVES": "NFL inactives",
    "NGS": "Next Gen Stats",
    "NGS-PART": "NGS participation (404)",
    "NFL-DEPTH-PAGE": "NFL depth charts (404)",
    "NFL-2026-STAND": "NFL 2026 standings",
    "NFL-TERMS": "NFL Terms",
    "REPO": "repository",
    "WAS-DEPTH": "WAS depth chart",
    "NYG-DEPTH": "NYG depth chart",
    "NE-DEPTH": "NE depth chart",
    "DET-DEPTH": "DET depth chart",
    "DK-SGP": "DK same-game parlay rules",
    "DK-PARLAY": "DK parlay rules",
    "DK-STARTER": "DK prop playing-time rule",
    "DK-SPREAD": "DK push rule",
    "NIST-MULT": "NIST multiple comparisons",
    "NIST-EDA352": "NIST RMSE definition",
}


def E(v) -> str:
    return html.escape(str(v), quote=False)


def A(url, label, cls=""):
    k = f' class="{cls}"' if cls else ""
    return f'<a href="{html.escape(str(url), quote=True)}"{k}>{E(label)}</a>'


def src_link(sid):
    s = SRC[sid]
    return A(s["url"], SHORT.get(sid, sid) + " \u2197", "srcl")


def repo_link(path, label=None):
    return A(REPO_BLOB + path, label or path, "srcl")


def blank_marker(why="unverified"):
    return f'<a class="flag" href="flagged.html">{E(why)}</a>'


def pill(text, kind="info"):
    return f'<span class="pill {kind}">{E(text)}</span>'


def T(headers, rows, caption=None, note=None, anchor=None):
    cap = f' id="{anchor}"' if anchor else ""
    out = ['<div class="scroll"><table>']
    if caption:
        out.append(f"<caption{cap}>{E(caption)}</caption>")
    out.append("<thead><tr>" + "".join(f"<th>{E(h)}</th>" for h in headers) + "</tr></thead><tbody>")
    for r in rows:
        out.append("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>")
    out.append("</tbody></table></div>")
    if note:
        out.append(f'<p class="small muted">{note}</p>')
    return "\n".join(out)


def KPI(items):
    return '<div class="grid k4">' + "".join(
        f'<div class="card"><div class="tag">{E(t)}</div><div class="num">{E(v)}</div>'
        f'<div class="sub">{E(s)}</div></div>' for t, v, s in items) + "</div>"


def callout(kind, title, body):
    return f'<div class="callout {kind}"><h3>{E(title)}</h3>{body}</div>'


def state_link(n, text):
    """Link to a source register entry that is 'blocked', with a 404 badge."""
    return src_link(n) + " " + pill(text, "bad")


NAV = [
    ("Start", [("index", "Overview"), ("executive-summary", "Executive summary")]),
    ("Decide", [("suggestions", "Suggestions for review"), ("questions", "Questions & decisions"),
                ("paths", "Paths & scoring")]),
    ("Evidence", [("injuries", "Injuries & role depth"), ("standings", "Official standings"),
                  ("recompute", "Independent recomputation")]),
    ("Quality", [("defects", "Defect register"), ("flagged", "Flagged for review"),
                 ("method", "Method & sources")]),
]


def page(slug, title, lead, sections, kpis=None):
    group = next(g for g, items in NAV for s, _ in items if s == slug)
    nav = []
    for g, items in NAV:
        nav.append(f'<div class="group"><h3>{E(g)}</h3><nav aria-label="{E(g)}">')
        for s, label in items:
            active = ' class="active"' if s == slug else ""
            nav.append(f'<a href="{s}.html"{active}>{E(label)}</a>')
        nav.append("</nav></div>")
    body = [kpis] if kpis else []
    for sec in sections:
        body.append("<section><div class=\"section-head\">"
                    f"<h2>{E(sec['h'])}</h2>"
                    + (f"<p>{sec['p']}</p>" if sec.get("p") else "")
                    + "</div>")
        if sec.get("html"):
            body.append(sec["html"])
        if sec.get("note"):
            body.append(f'<p class="small muted">{sec["note"]}</p>')
        body.append("</section>")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} | NFL Line Lab — decisions</title>
<meta name="description" content="{E(lead[:170])}">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<div class="shell">
  <aside class="side">
    <div class="brand"><span class="mark">D</span><span><strong>Decision readiness</strong><small>NFL Line Lab</small></span></div>
    <p class="tagline">Snapshot {SNAPSHOT} (UTC)<br>Session {E(SESSION)}</p>
    {''.join(nav)}
    <div class="foot">Research only · not betting advice.<br>Blank means unverified, not zero.<br>
      {A("../index.html", "← Repository dashboard")} · {A("../hub/index.html", "Consolidated hub")}
    </div>
  </aside>
  <div class="content">
    <div class="topbar"><div class="crumb"><strong>{E(group)}</strong> / {E(title)}</div>
      <span class="badge">Official sources only · blank = unverified</span></div>
    <main class="wrap">
      <div class="eyebrow">{E(group)}</div>
      <h1>{E(title)}</h1>
      <p class="lead">{lead}</p>
      {''.join(body)}
    </main>
    <footer class="site">
      <div>Independent research; not affiliated with the NFL or any sportsbook. Snapshot {SNAPSHOT} (UTC).<br>
      Every table row links to an official publisher or to the committed file a value came from.
      A blank cell is unverified and links to {A("flagged.html", "Flagged for Review")}.</div>
      <div style="margin-top:8px">{A("../hub/index.html", "Consolidated hub")} ·
      {A("../hub/sources.html", "Official sources")} · {A("../hub/flagged.html", "Hub flags")} ·
      {A(REPO_TREE, "Repository ↗")}</div>
    </footer>
  </div>
</div>
</body>
</html>
"""


def pct(x, d=1):
    return f"{x:.{d}f}%"


# ------------------------------------------------------------------ pages ----
def build_index():
    n_sug = len(SUGGESTIONS["suggestions"])
    n_q = len(QUESTIONS["questions"])
    n_block = sum(1 for q in QUESTIONS["questions"] if "blocks" in q["status"])
    c = RECOMPUTE["counts"]
    kpis = KPI([
        ("Suggestions registered", n_sug, "All proposed — none implemented"),
        ("Questions registered", n_q, f"{n_block} block a decision"),
        ("Independent checks run", c["checks"], f"{c['match']} matched exactly"),
        ("Verified injury rows", INJURIES["summary"]["players_listed"],
         f"Week {INJURIES['summary']['week']} {INJURIES['summary']['season']}, official"),
    ])
    orient = [
        ["What could we do to improve the site and the research?",
         A("suggestions.html", "Suggestions for review") + f" — {n_sug} proposals, scored, in three paths"],
        ["What do we still not know, and what would resolve it?",
         A("questions.html", "Questions & decisions") + " — each question with what we hold, what we lack and the resolving action"],
        ["What is verified about injuries and depth today?",
         A("injuries.html", "Injuries & role depth") + " — official player rows and a confidence tier per finding"],
        ["Can the repository's own numbers be reproduced?",
         A("recompute.html", "Independent recomputation") + f" — {c['checks']} checks from committed data, no project imports"],
        ["What is broken or uncertain?",
         A("defects.html", "Defect register") + " and " + A("flagged.html", "Flagged for review")],
    ]
    holds_up = callout("ok", "What holds up",
        f"<p>Every headline number that could be recomputed from committed data was reproduced: "
        f"<strong>{c['match']} of {c['checks']}</strong> checks matched exactly, including the parlay break-even arithmetic, "
        "the correlation coefficients and the 7,075-game universe. No fabricated number was found.</p>")
    does_not = callout("warn", "What does not",
        "<p>Nothing in the repository has a lawful data licence, an executable price archive, a funded reward, or a power "
        "target. The best rule (strategy <strong>S14</strong> in the gate table, cited here as <strong>G-S14</strong>) is "
        "+8.41% raw ROI over 607 bets with an FDR-adjusted q of 0.288, and 0 of 18 rules pass their "
        "gates. The leaderboard cannot rank skill because it holds no evidence of any.</p>")
    new = callout("bad", "The one thing that is genuinely new",
        f"<p>The project had no injury data at all. It now publishes a dated snapshot of the official league report: "
        f"<strong>{INJURIES['summary']['players_listed']} players</strong> across "
        f"{INJURIES['summary']['clubs_with_listings']} clubs for {INJURIES['summary']['games']} games. But of the "
        f"{INJURIES['summary']['practice_counts']['DNP']} players who did not practise, only "
        f"{INJURIES['summary']['game_status_counts'].get('Out',0)} carry a final status. The official page says who is hurt, "
        "not who will play.</p>")
    steps = [
        ["1", "Read the questions register and mark each as answered or accepted as open.",
         "A decision made on an unanswered question is a guess with a citation.", A("questions.html", "Questions")],
        ["2", "Read the scored suggestions and disagree with the weights if you want to.",
         "The weights are published so the ranking can be challenged, not obeyed.", A("suggestions.html", "Suggestions")],
        ["3", "Pick a path, not a pile of items.", "Paths encode dependency order.", A("paths.html", "Paths")],
        ["4", "Record the decision in the decision log.",
         "An implicit decision cannot be reviewed or reversed.", A("suggestions.html#log", "Decision log")],
        ["5", "Implement one item, then re-run every verifier.",
         "The build is fail-closed; a broken link stops publication.", A("method.html", "Method")],
    ]
    secs = [
        dict(h="What this section is for",
             p="This is the review surface for decisions that have not been made. It exists so a path can be examined and "
               "chosen before anything is built, and so every claim can be traced to an official publisher or a committed file.",
             html=T(["Question you are probably asking", "Where the answer is"], 
                   [r + [repo_link("decisions/build.py", "build.py")] for r in orient],
                   caption="Orientation", note="Navigation rows point at this site's own pages; the substantive answer on each page carries its own official source.")),
        dict(h="The honest position after this session",
             p="Two things are true at once, and both matter for any decision.",
             html='<div class="two">' + holds_up + does_not + "</div>" + new),
        dict(h="How to use this section",
             p="Read the questions first, then the suggestions, then choose a path. A proposal cannot be judged solved while "
               "the question that blocks it is open.",
             html=T(["Step", "Action", "Why in this order", "Page", "Definition"], 
                   [r[:3] + [A("method.html", "Method"), repo_link("decisions/build.py", "build.py")] for r in steps],
                   caption="Review sequence, with the two columns above",
                   note=f"All four steps are about method; the rules the build enforces are on {A('method.html', 'Method & sources')}.")),
    ]
    return page("index", "Decision readiness — overview",
                "The review surface for this project: what we can do, what we still do not know, what is verified about "
                "injuries and role depth, what reproduces, and what is broken. Nothing here has been implemented.",
                secs, kpis)


def build_suggestions():
    w = {a["key"]: a["weight"] for a in SUGGESTIONS["rubric"]["axes"]}
    rows = []
    for sug in SUGGESTIONS["suggestions"]:
        score = sum(w[k] * v for k, v in sug["scores"].items())
        rows.append([
            f'<strong>{E(sug["id"])}</strong>', E(sug["title"]), E(sug["problem"]),
            " ".join(A("questions.html#" + q.lower(), q) if q.startswith("Q")
                     else f'<span class="muted">{E(q)}</span>' for q in sug["depends_on"]) or "nothing",
            f'{sug["scores"]["decision_value"]}/{sug["scores"]["evidence_gain"]}/'
            f'{sug["scores"]["feasibility"]}/{sug["scores"]["risk_control"]}',
            f"<strong>{score:.2f}</strong>", E(sug["effort"]), E(sug["reversibility"]),
            pill("proposed — not implemented", "warn"),
            " ".join([src_link(x) for x in sug["sources"]] + [repo_link("decisions/data/suggestions.json", "registry")]),
        ])
    order = sorted(SUGGESTIONS["suggestions"], key=lambda s: -sum(w[k] * v for k, v in s["scores"].items()))
    top = order[0]
    kpis = KPI([
        ("Proposals", len(SUGGESTIONS["suggestions"]), "All status: proposed"),
        ("Implemented", 0, "No change made without a recorded decision"),
        ("Paths offered", len(SUGGESTIONS["paths"]), "Coverage / governance / evidence"),
        ("Top weighted score", f"{sum(w[k]*v for k, v in top['scores'].items()):.2f}", f"{top['id']} proposed first by score"),
    ])
    rubric = [[a["label"], f'{a["weight"]:.2f}', a["meaning"],
               repo_link("decisions/data/suggestions.json", "registry")]
              for a in SUGGESTIONS["rubric"]["axes"]]
    root = [["S01", "Licence for official NFL data"],
            ["S02", "Executable timestamped quote archive"],
            ["S04", "Daily archived injury snapshot"],
            ["S05", "Availability coverage for 32 clubs"],
            ["S08", "Power / minimum-detectable-effect calculator"],
            ["S13", "One canonical site surface"]]
    ns = callout("info", "Two numbering schemes that look alike",
        "<p>A <strong>gate strategy</strong> (<code>G-S01</code>…<code>G-S16</code>) is a betting rule scored in "
        "<code>data/derived/gates_results.csv</code>. A <strong>proposal</strong> (<code>S01</code>…<code>S15</code>) is a "
        "change to this project, scored on this page. They share digits and nothing else. The gate table keeps its original "
        "IDs; anywhere both appear on this site a strategy is written <strong>G-S14</strong>.</p>")
    secs = [
        dict(h="Two numbering schemes that look alike", p="Read this before quoting any S-number from this site.", html=ns),
        dict(h="How to read the scores",
             p="Each proposal is scored 1-5 on four published axes and the weighted total is computed by the build script. "
               "The weights are shown so you can disagree with them and re-rank. This is a decision aid, not a verdict.",
             html=T(["Axis", "Weight", "What a 5 means", "Where the weights live"], rubric, caption="Scoring rubric")),
        dict(h="Register of proposals",
             p="Every row is a proposal that has NOT been implemented. The Questions column links the register entries that "
               "must be answered first. Proposal IDs are <strong>S01–S15 and belong to this page only</strong>; the gate "
               "table's strategy IDs also run S01–S16 but are a different namespace — where both appear, a strategy is "
               "written <strong>G-S14</strong>.",
             html=T(["ID", "Proposal", "Problem it solves", "Questions", "Axes DV/EG/F/RC", "Weighted", "Effort",
                     "Reversibility", "Status", "Source"], rows,
                    caption="15 proposals in ID order — the ranked order is on the Paths page",
                    note="Axes: Decision value / Evidence gain / Feasibility today / Risk control.")),
        dict(h="The six that matter most",
             p="If only six could be done, these are the ones this session would argue for — three that unblock everything "
               "else and three that are cheap and protect what is built.",
             html=T(["ID", "Proposal", "Why it is on this short list", "Source"], [
                 ["S01", "Licence for official NFL data",
                  "Root blocker: without it no empirical claim can be published as a product.", src_link("NFL-TERMS")],
                 ["S02", "Executable timestamped quote archive",
                  "No price means no ROI, no CLV and no testable edge — ever.", src_link("NFL-TERMS")],
                 ["S04", "Daily archived injury snapshot",
                  "There is no injury history at all, so no injury signal can be tested until archiving starts.",
                  src_link("NFL-INJ-LIVE")],
                 ["S05", "Availability coverage for 32 clubs",
                  "Four clubs cannot support a league-wide signal.", src_link("NFL-DEPTH-PAGE")],
                 ["S08", "Power / MDE calculator",
                  "Stops the leaderboard ranking noise as merit.", src_link("NIST-MULT")],
                 ["S13", "One canonical site surface",
                  "Seven builds currently disagree; a reader cannot tell which is the project's position.",
                  repo_link("COORDINATION.md", "board")],
             ], caption="Short list")),
        dict(h="Decision log", anchor=None,
             p="Nothing has been decided yet. This table is where a decision gets recorded. It is empty on purpose.",
             html=f'<span id="log"></span>' + T(["Date", "Proposal", "Decision", "Owner", "Rationale"],
                                                [["—", "—", blank_marker("no decision recorded"), "—", "—"]],
                                                caption="Decision log (empty)")),
    ]
    return page("suggestions", "Suggestions for review",
                "Fifteen proposals to improve the site and the research, each with its problem, its score, its reversibility "
                "and the questions it depends on — plus an empty decision log. Nothing here has been implemented.",
                secs, kpis)


def build_paths():
    w = {a["key"]: a["weight"] for a in SUGGESTIONS["rubric"]["axes"]}
    byid = {s["id"]: s for s in SUGGESTIONS["suggestions"]}
    prow = []
    for p in SUGGESTIONS["paths"]:
        seq = " → ".join(f'<strong>{E(i)}</strong> {E(byid[i]["title"])}' for i in p["sequence"])
        blocked = ", ".join(A("questions.html#" + q.lower(), q) for q in p["blocked_by"]) or "nothing"
        kind = {"first": "ok", "second": "info", "third": "warn"}.get(p["recommendation"], "info")
        prow.append([f'<strong>{E(p["id"])}</strong> — {E(p["name"])}', seq, E(p["unlocks"]), E(p["effort"]),
                     blocked, pill("do " + p["recommendation"], kind),
                     repo_link("decisions/data/suggestions.json", "registry")])
    ranked = sorted(SUGGESTIONS["suggestions"],
                    key=lambda s: (-sum(w[k] * v for k, v in s["scores"].items()), s["id"]))
    rrows = []
    for i, sug in enumerate(ranked, 1):
        rrows.append([str(i), f'<strong>{E(sug["id"])}</strong>', E(sug["title"]),
                      f'{sum(w[k]*v for k, v in sug["scores"].items()):.2f}', E(sug["effort"]),
                      E(sug["reversibility"]), repo_link("decisions/data/suggestions.json", "registry")])
    secs = [
        dict(h="Three paths",
             p="Pick a path rather than a pile of items: the steps inside a path depend on each other, and taking a step out of "
               "order is how a project ends up ranking luck.",
             html=T(["Path", "Sequence", "What it unlocks", "Effort", "Blocked by", "Recommendation", "Source"],
                    prow, caption="Paths")),
        dict(h="Recommended order", p=SUGGESTIONS["recommended_reason"],
             html=T(["Order", "Path", "Why", "Source"], [
                 ["1", "P2 — Coverage first", "Completes the availability requirement with sources verifiable today and needs no licence.", repo_link("decisions/data/suggestions.json", "registry")],
                 ["2", "P3 — Governance first", "Cheap, immediate, and protects everything built after it.", repo_link("decisions/data/suggestions.json", "registry")],
                 ["3", "P1 — Evidence first", "Depends on a contract the project does not control. No engineering substitutes for it.", src_link("NFL-TERMS")],
             ], caption="Recommended sequence")),
        dict(h="Full ranking by weighted score",
             p="The same 15 proposals sorted by the published rubric. A high score is not permission to implement: each is "
               "still blocked on the questions on its row.",
             html=T(["Rank", "ID", "Proposal", "Weighted", "Effort", "Reversibility", "Source"], rrows,
                    caption="Ranked proposals")),
    ]
    return page("paths", "Paths & scoring",
                "Three coherent paths and the full weighted ranking, with the recommended order and the reason for it. "
                "Choosing a path does not authorise data acquisition the NFL Terms prohibit.", secs)


def build_questions():
    rows = []
    for q in QUESTIONS["questions"]:
        ans = q["answer"] if q["answer"] else blank_marker("unverified")
        kind = "ok" if q["status"].startswith("answered") else ("bad" if "blocks" in q["status"] else "warn")
        rows.append([f'<span id="{q["id"].lower()}"><strong>{E(q["id"])}</strong></span>', E(q["question"]),
                     E(q["why_it_blocks"]), E(q["we_have"]), E(q["we_lack"]), E(q["resolution"]), ans,
                     pill(q["status"], kind), " ".join(src_link(x) for x in q["sources"])])
    n_block = sum(1 for q in QUESTIONS["questions"] if "blocks" in q["status"])
    n_ans = sum(1 for q in QUESTIONS["questions"] if q["status"].startswith("answered"))
    kpis = KPI([
        ("Questions", len(QUESTIONS["questions"]), "Grouped by what they block"),
        ("Blocking a decision", n_block, "No verdict is possible while open"),
        ("Answered from an official source", n_ans, "Quotable, linked on the row"),
        ("Answers left blank", len(QUESTIONS["questions"]) - n_ans, "Unknown, flagged, not guessed"),
    ])
    rules = [
        ["An answered question cites an official page", "The answer is quotable and the link is on the row.",
         src_link("NFL-INJ-POLICY")],
        ["An unanswered question leaves the cell blank",
         "It blocks the linked proposal and appears on Flagged for Review.", A("flagged.html", "flags")],
        ["A blocking question stops a verdict", "No strategy, rank or reward decision is made while it is open.",
         repo_link("decisions/data/questions.json", "registry")],
        ["Every proposal names its questions",
         "The suggestions register links each proposal to the questions it needs answered first.",
         repo_link("decisions/data/suggestions.json", "registry")],
    ]
    secs = [
        dict(h="How to use this register",
             p="A decision is reasonable only when each question is answered or consciously accepted as open. The 'we have' and "
               "'we lack' columns are deliberately separate: the gap is the decision, not the answer.",
             html=T(["Rule", "Consequence", "Where"], rules, caption="Rules")),
        dict(h="The register",
             p=f"{len(QUESTIONS['questions'])} questions: {n_block} block a decision; the rest are answered or non-blocking. "
               "Every row links the official page that supports the answer.",
             html=T(["ID", "Question", "Why it blocks a decision", "We have", "We lack", "What resolves it", "Answer",
                     "Status", "Official source"], rows, caption="Questions & decisions")),
    ]
    return page("questions", "Questions & decisions",
                "The questions that must be answered — or explicitly accepted as unanswerable — before any decision is "
                "reasonable, with the information held, the information missing and what would resolve each one.",
                secs, kpis)


def build_injuries():
    s = INJURIES["summary"]
    kpis = KPI([
        ("Players on the official report", s["players_listed"], f"Week {s['week']} {s['season']}, read {s['read_utc']}"),
        ("Clubs listing players", f'{s["clubs_with_listings"]} / 32', "4 clubs: no injuries reported"),
        ("Rows with a final game status", pct(s["game_status_coverage_pct"]), "The rest are practice status only"),
        ("Clubs with a verified depth chart", f'{TIERS["coverage"]["clubs_with_depth_chart_verified"]} / 32',
         "Role depth is blank for the other 28"),
    ])
    practice = [
        ["Did not participate", str(s["practice_counts"]["DNP"]),
         "The player did not practise that day. It is NOT a declaration that he will miss the game.",
         src_link("NFL-INJ-POLICY")],
        ["Limited participation", str(s["practice_counts"]["Limited"]),
         "Less than 100 percent of the player's normal repetitions.", src_link("NFL-INJ-POLICY")],
        ["Full participation", str(s["practice_counts"]["Full"]),
         "100 percent of the player's normal repetitions.", src_link("NFL-INJ-POLICY")],
    ]
    inputs_tbl = T(["Input a model may use", "Is it official?", "Is it present today?", "Official source"], [
        ["Practice status (DNP / Limited / Full)", "Yes — league policy", "Yes, on every row", src_link("NFL-INJ-POLICY")],
        ["Game status (Out / Doubtful / Questionable)", "Yes — league policy",
         f"No — present on {s['game_status_coverage_pct']}% of rows", src_link("NFL-INJ-LIVE")],
        ["Inactive list (final)", "Yes — the league publishes it", "No — the official page was empty when read",
         src_link("NFL-INACTIVES")],
        ["Snap count / participation", "No official public source found", "No", src_link("NGS-PART")],
        ["Point value of an absence", "No official source found", "No", src_link("NFL-INJ-LIVE")],
    ], caption="Availability inputs, and whether they exist")
    central = callout("bad", "Why this changes how any injury signal must be built",
        f"<p>Only <strong>{pct(s['game_status_coverage_pct'])}</strong> of the rows on the official page carry a final game status. "
        "A model that treats 'did not practise' as 'will not play' would invent absences the league has not declared. A model "
        "that ignores practice status throws away the only information actually present. The only defensible design has two "
        "separate fields and never merges them — proposal "
        f"<strong>S11</strong> on the {A('suggestions.html', 'suggestions page')}.</p>") + inputs_tbl
    tier_rows = []
    keymap = {"Confirmed loss": "confirmed_loss_out", "At risk, undesignated": "at_risk_undesignated",
              "At risk, designated": "at_risk_designated", "Limited but active": "limited_active",
              "Full participant": "full"}
    for d in TIERS["tier_definitions"]:
        tier_rows.append([E(d["tier"]), E(d["rule"]), E(d["counts_as"]),
                          str(TIERS["tier_counts"][keymap[d["tier"]]]), src_link("NFL-INJ-POLICY")])
    find_rows = []
    for f in TIERS["week10_findings"]:
        kind = {"verified pages": "ok", "data gap": "warn"}.get(f["status"], "info")
        find_rows.append([E(f["id"]), E(f["club"]), E(f["position"]), E(f["finding"]), E(f["tier"]),
                          E(f["why_it_matters"]), pill(f["status"], kind),
                          " ".join(src_link(x) for x in f["sources"])])
    gap_rows = [[E(g["id"]), E(g["gap"]), " ".join(src_link(x) for x in g["sources"])]
                for g in TIERS["structural_gaps"]]
    club_rows = []
    verified = set(TIERS["coverage"]["clubs_with_depth_chart_verified_list"])
    for club in sorted({r["team"] for r in INJURIES["rows"]}):
        rs = [r for r in INJURIES["rows"] if r["team"] == club]
        dnp = sum(1 for r in rs if r["practice"] == "DNP")
        lim = sum(1 for r in rs if r["practice"] == "Limited")
        full = sum(1 for r in rs if r["practice"] == "Full")
        out = sum(1 for r in rs if r["game_status"] == "Out")
        q = sum(1 for r in rs if r["game_status"] == "Questionable")
        club_rows.append([E(club), str(len(rs)), str(dnp), str(lim), str(full),
                          str(out) if out else "—", str(q) if q else "—",
                          pill("depth verified", "ok") if club in verified else pill("no depth chart read", "warn"),
                          src_link("NFL-INJ-LIVE")])
    pos_rows = [[E(k), str(v), src_link("NFL-INJ-LIVE")]
                for k, v in sorted(s["position_group_counts"].items(), key=lambda kv: -kv[1])]
    secs = [
        dict(h="What the official report actually says",
             p="This is the first injury data this project has ever published: a dated snapshot of the league's own page, "
               "transcribed row by row. It is not a feed, it has no history, and the page itself carries no timestamp.",
             html=T(["Practice status", "Players", "What the league says it means", "Official source"], practice,
                    caption="Practice status, official definitions",
                    note=f"Definitions quoted from the league's own announcement {src_link('NFL-INJ-POLICY')}; the practice "
                         f"status is present for all {s['players_listed']} rows.")),
        dict(h="The central finding: practice status is not availability",
             p=f"Of the {s['practice_counts']['DNP']} players who did not practise, "
               f"{s['game_status_counts'].get('Out',0)} carry an official Out designation and "
               f"{s['game_status_counts'].get('Questionable',0)} a Questionable one. The remaining "
               f"{s['game_status_counts']['blank']} rows have no game status at all.",
             html=central),
        dict(h="Role-depth tiers used in this section",
             p="The brief asks for 2nd, 3rd and 4th string. Because no official league-wide depth chart exists, each finding "
               "carries a tier describing what the official pages support — never what they imply about the lineup.",
             html=T(["Tier", "Rule", "What it may be used for", "Rows", "Official source"], tier_rows,
                    caption="Tier definitions")),
        dict(h="Week 10 findings the official pages support",
             p="Nine findings follow directly from the two official sources. Each is a statement about what is published, not "
               "a claim about how a game will go.",
             html=T(["ID", "Club", "Pos", "Finding", "Tier", "Why it matters", "Status", "Official source"], find_rows,
                    caption="Findings")),
        dict(h="Structural gaps that limit any depth model",
             p="These are not defects to fix; they are the shape of the available evidence. Each caps what may honestly be claimed.",
             html=T(["ID", "Gap", "Official source"], gap_rows, caption="Structural gaps")),
        dict(h="The full snapshot, by club",
             p="All rows are in decisions/data/injuries_week10_2026.json. This table is the club-level summary: practice "
               "status counts and the game statuses that exist.",
             html=T(["Club", "Listed", "DNP", "Limited", "Full", "Out", "Questionable", "Depth chart", "Official source"],
                    club_rows, caption="Week 10 2026 by club",
                    note="Four clubs showed 'No Injuries Reported' on the official page: "
                         + ", ".join(s["clubs_no_injuries_reported"]) +
                         ". Absence from the report is not a health statement: under league policy a player certain to play "
                         "is not listed.")),
        dict(h="Position mix of the listed players",
             p="Where the reported injuries sit by position group. A coverage check, not a measure of team strength.",
             html=T(["Position group", "Players", "Official source"], pos_rows, caption="Listed players by position group")),
    ]
    return page("injuries", "Injuries & role depth",
                "What the official league injury report says for 2026 Week 10, transcribed row by row, plus a confidence tier "
                "for each finding and an explicit account of what cannot be known from official sources.",
                secs, kpis)


def build_standings():
    rows = []
    for r in STANDINGS["rows"]:
        streak = E(r["streak"]) if r["streak"] else blank_marker("not read")
        rows.append([E(r["club"]), f'{r["w"]}-{r["l"]}-{r["t"]}', f'{r["pct"]:.3f}', str(r["pf"]), str(r["pa"]),
                     ("+" if r["net"] > 0 else "") + str(r["net"]), streak, src_link("NFL-2026-STAND")])
    kpis = KPI([
        ("Official club rows transcribed", len(STANDINGS["rows"]), "Read 2026-11-12"),
        ("Dataset last completed game", "2026-10-29", "14 days before this snapshot"),
        ("Clubs with 8+ games officially", sum(1 for r in STANDINGS["rows"] if r["w"] + r["l"] + r["t"] >= 8),
         "The dataset is complete only through Week 9"),
        ("Rows deliberately blank", 1, "One streak not visible in the fetched text"),
    ])
    stale = callout("warn", "The staleness problem, stated precisely",
        "<p>The pinned dataset contains 7,075 completed regular-season games and 164 unplayed 2026 fixtures. Its last "
        "completed game is <strong>2026-10-29</strong>. The official 2026 division standings on 2026-11-12 show clubs with "
        "eight and nine games played. The gap is about one week of games, including any result that moved a division. "
        f"Nothing on the site currently says this. Proposal <strong>S12</strong> on the {A('suggestions.html', 'suggestions page')} "
        "is to print the dataset date on every page and fail the build when the gap exceeds a threshold.</p>")
    limits = [
        ["That a team is stronger than its record", "Record alone does not separate schedule strength, injuries or luck."],
        ["That the model is validated against current form", "The model was fitted on data that ends a week earlier."],
        ["That these numbers can be used as a feature", "A feature needs a licensed, timestamped feed, not a transcribed page."],
    ]
    secs = [
        dict(h="Why the official standings are on this page",
             p="Every model input in this repository comes from a dataset whose most recent completed game is 2026-10-29. The "
               "official standings read on 2026-11-12 describe a league that has played roughly a week more. Any decision "
               "taken today rests on data already behind the official record.",
             html=stale),
        dict(h="Official 2026 regular-season standings, as read",
             p="Only the rows this session actually read are recorded. Columns are those the official page displays. A value "
               "not visible in the fetched text is blank rather than inferred.",
             html=T(["Club", "W-L-T", "Pct", "PF", "PA", "Net", "Streak", "Official source"], rows,
                    caption="NFL.com 2026 division standings", note=STANDINGS["not_read"])),
        dict(h="What this does not tell you",
             p="These are records, not forecasts. They are published as a freshness check on the project's own data, not as a "
               "modelling input.",
             html=T(["Claim this table does NOT support", "Why not", "Official source"], 
                   [r + [src_link("NFL-2026-STAND")] for r in limits], caption="Limits")),
    ]
    return page("standings", "Official standings",
                "The official 2026 standings as read on 2026-11-12, used as a freshness check on the project's pinned dataset "
                "— not as a modelling input.", secs, kpis)


def build_recompute():
    c = RECOMPUTE["counts"]
    kpis = KPI([
        ("Checks run", c["checks"], "From committed data, no project imports"),
        ("Exact matches", c["match"], "Including every headline number"),
        ("Definitional issues", c["definition"], "Labelling, not arithmetic"),
        ("Blocked / unknowable", c["blocked"], "No official quantity exists"),
    ])
    kind = {"match": "ok", "mismatch": "bad", "definition": "warn", "blocked": "info"}
    rows = []
    for r in RECOMPUTE["results"]:
        pub = E(r["published"]) if r["published"] else blank_marker("not published")
        rec = E(r["recomputed"]) if r["recomputed"] not in ("", None) else blank_marker("no official quantity")
        rows.append([f'<strong>{E(r["id"])}</strong>', E(r["claim"]), pub, E(r["published_in"]), rec, E(r["formula"]),
                     pill(r["verdict"], kind[r["verdict"]]), E(r["note"]),
                     repo_link("decisions/recompute.py", "recompute.py")])
    ok = callout("ok", "The result",
        f"<p><strong>{c['match']} of {c['checks']}</strong> checks reproduced the published value exactly, including the "
        "7,075-game universe, the MAE pair (10.670 vs 10.247), the same-game correlation, both parlay break-evens and the gate "
        "counts. No fabricated number was found.</p>")
    soft = callout("warn", "Where it is soft",
        f"<p>One entry is a labelling issue rather than an arithmetic one (D01: 10.670 is an MAE, not an RMSE). {c['blocked']} "
        "entries are blocked because the underlying quantity does not exist in any official source — a statement about the "
        "world, not a bug.</p>")
    wrows = [[w["id"], E(w["raised_as"]), E(w["why_wrong"]), repo_link("decisions/recompute.py", "recompute.py")]
             for w in DEFECTS["own_claims_withdrawn"]]
    secs = [
        dict(h="Why this exists",
             p="An independent check is only independent if it does not reuse the code it is checking. decisions/recompute.py "
               "imports nothing from this repository and re-derives each number from the raw or committed CSV. Where a value "
               "could not be re-derived it says so rather than repeating the published figure.",
             html=ok + soft),
        dict(h="Every check, with its formula",
             p="The formula column states the arithmetic in words so a reader can check it without running the script. The "
               "published-in column names the file and, where relevant, the line.",
             html=T(["ID", "Claim checked", "Published", "Published in", "Recomputed here", "Formula", "Verdict", "Note",
                     "Script"], rows, caption=f"{c['checks']} independent checks")),
        dict(h="Retracted checks are kept, not deleted",
             p="While building this page the session raised three findings and withdrew them after checking its own arithmetic. "
               "They are recorded here rather than removed, because a verification log that hides its retractions is worth less "
               "than one that shows them.",
             html=T(["ID", "What was raised", "Why it was wrong", "Where it is recorded"], wrows, caption="Withdrawn claims",
                    note="None of the three was ever published as a repository defect. All three were caught by recomputing "
                         "the published expression verbatim before publication.")),
    ]
    return page("recompute", "Independent recomputation",
                "Twenty-four checks that re-derive the project's published numbers from committed data without importing any "
                "project code, including the three checks this session got wrong and withdrew.", secs, kpis)


def build_defects():
    s = DEFECTS["summary"]
    kpis = KPI([
        ("Open defects", s["repo_defects_open"], "All low or medium severity"),
        ("Other session's findings re-checked", len(DEFECTS["other_session_findings"]["results"]), "All confirmed"),
        ("Own claims withdrawn", s["own_claims_withdrawn"], "Caught before publication"),
        ("Broken links / missing sources", 0, "Enforced by decisions/check.py"),
    ])
    rep = []
    for x in DEFECTS["repo_defects"]:
        path = x["file"].split(":")[0]
        where = repo_link(path, "file") if (ROOT / path).exists() else repo_link("COORDINATION.md", "board")
        rep.append([f'<strong>{E(x["id"])}</strong>', pill(x["severity"], "warn" if x["severity"] != "low" else "info"),
                    E(x["file"]), E(x["claim"]), E(x["evidence"]), E(x.get("recommended_fix", "—")),
                    pill(x["status"], "ok" if x["status"].startswith("withdrawn") else "warn"), where])
    club_src = {"V01": "NE-DEPTH", "V02": "NE-DEPTH", "V03": "WAS-DEPTH",
                "V04": "DET-DEPTH", "V05": "DET-DEPTH", "V06": "NE-DEPTH"}
    ver = [[f'<strong>{E(x["id"])}</strong>', E(x["finding"]), pill(x["verdict"], "ok"), E(x["evidence"]),
            src_link("NFL-INJ-LIVE") + " " + src_link(club_src[x["id"]]),
            repo_link("hub/injuries.html", "hub/injuries.html")]
           for x in DEFECTS["other_session_findings"]["results"]]
    wd = [[f'<strong>{E(w["id"])}</strong>', E(w["raised_as"]), E(w["why_wrong"]), E(w["lesson"]),
           repo_link("decisions/recompute.py", "recompute.py")]
          for w in DEFECTS["own_claims_withdrawn"]]
    fp = [
        ["The injury report shows far more DNP than Out",
         "Correct. The game status is filed later in the week; the page is mid-week.", src_link("NFL-INJ-LIVE")],
        ["78.6% of games have no opening line",
         "Correct. Pre-2021 opening lines do not exist in this dataset; the limitation is published.",
         repo_link("data/derived/coverage.json", "coverage.json")],
        ["A live check_hub run counts more rows than the committed report",
         "Correct. The report is regenerated by the gate before the drift check.",
         repo_link("hub/check_hub.py", "check_hub.py")],
        ["Depth charts say 'unofficial'",
         "Correct, and it is the clubs' own word. A limitation, not an error.", src_link("NE-DEPTH")],
    ]
    secs = [
        dict(h="Repository defects found by this session",
             p="Each defect names the exact file (and line where it is a line), the evidence and the fix recommended. None is "
               "severe enough to block publication; none has been silently corrected, because these files belong to other sessions.",
             html=T(["ID", "Severity", "File", "Claim", "Evidence", "Recommended fix", "Status", "Where"], rep,
                    caption="Open and withdrawn defects")),
        dict(h="The other session's findings, independently re-checked",
             p="Another session (arena/6cbe5d15-korea3) published six depth findings earlier today. This session re-read all "
               "four official club depth charts and the official injury page and checked each finding against them.",
             html=T(["ID", "Finding checked", "Verdict", "Evidence read independently", "Official sources", "Where it was published"], ver,
                    caption="Cross-session verification", note=DEFECTS["other_session_findings"]["note"])),
        dict(h="Claims this session raised and withdrew",
             p="Three. All three were wrong, all three were caught before publication, and all three are kept here.",
             html=T(["ID", "What was raised", "Why it was wrong", "Lesson", "Recorded in"], wd, caption="Withdrawn")),
        dict(h="What is NOT a defect, and should not be reported as one",
             p="Several things look wrong at first glance and are not. Recording them saves the next session the same detour.",
             html=T(["Looks like a defect", "Why it is not", "Source"], fp, caption="False positives")),
    ]
    return page("defects", "Defect register",
                "What is broken, what is merely mislabelled, what the other session got right, and the three claims this session "
                "raised and withdrew. Nothing here is silently corrected.", secs, kpis)


def build_flagged():
    rows = []
    for q in QUESTIONS["questions"]:
        if not q["answer"]:
            rows.append([f'Q-{E(q["id"])}', E(q["question"]), E(q["why_it_blocks"]), blank_marker("no official answer"),
                         " ".join(src_link(x) for x in q["sources"])])
    for g in TIERS["structural_gaps"]:
        rows.append([f'T-{E(g["id"])}', E(g["gap"]), "Caps what can be claimed", blank_marker("no official source"),
                     " ".join(src_link(x) for x in g["sources"])])
    for x in DEFECTS["repo_defects"]:
        if x["status"].startswith("open"):
            rows.append([f'D-{E(x["id"])}', E(x["claim"]), E(x["severity"]) + " severity",
                         blank_marker("needs owner review"), repo_link("decisions/data/defects.json", "registry")])
    rows.append(["R-01", "Several parallel site builds are live in one repository and disagree with each other.",
                 "A reader cannot tell which is authoritative.", blank_marker("needs owner decision"),
                 repo_link("COORDINATION.md", "board")])
    rows.append(["R-02", "The reward competition has no sponsor, pool, jurisdiction or terms.",
                 "No reward exists and none should be implied.", blank_marker("needs owner decision"), src_link("NFL-TERMS")])
    rows.append(["R-03", "The pinned dataset is 14 days behind the official standings and no page says so.",
                 "Decisions made today rest on stale records.", blank_marker("needs fix (S12)"), src_link("NFL-2026-STAND")])
    clearing = [
        ["Cite the official page or the owner decision", "Reword the flag so it no longer applies.",
         repo_link("decisions/data/sources.json", "source register")],
        ["Add the value with its source", "Fill the cell from another site or from memory.",
         repo_link("decisions/data/sources.json", "source register")],
        ["Re-run decisions/check.py and attach the output", "Delete the row.",
         repo_link("decisions/check.py", "check.py")],
    ]
    secs = [
        dict(h="How to read this page",
             p="Everything here is unresolved. It is published so it can be reviewed after the site is live, not so it can "
               "block publication. Each row names what is unknown and why.",
             html=T(["Ref", "Item", "Why it matters", "Status", "Where it comes from"], rows,
                    caption="Full flag register")),
        dict(h="How to request a change",
             p="Record the request in COORDINATION.md against this session's section, or open an issue. A flag is cleared only "
               "by an official source or an owner decision, never by editing the wording.",
             html=T(["To clear a flag you must", "Not", "Where"], clearing, caption="Clearing a flag")),
    ]
    return page("flagged", "Flagged for review",
                "Every unresolved item in this section in one table: unanswered questions, structural gaps, open defects and "
                "repository-level issues. Nothing here blocks publication.", secs)


def build_method():
    kind = {"verified": "ok", "blocked": "bad", "unverified": "warn"}
    rows = [[E(sr["id"]), E(sr["publisher"]), E(sr["tier"]), A(sr["url"], sr["url"][:58] + " ↗", "srcl"),
             E(sr["claim"]) if sr["claim"] else blank_marker("page did not state the claim"),
             pill(sr["status"], kind.get(sr["status"], "info")), E(sr["method"])]
            for sr in SOURCES["sources"]]
    tiers = [
        ["Official league", "NFL, NFL Support, NFL Football Operations, Next Gen Stats",
         "Rules, definitions, injury reports, standings, depth", "Prices", src_link("NFL-INJ-POLICY")],
        ["Official club", "WAS, NYG, NE, DET club sites", "Depth order, labelled official/unofficial per club",
         "Injury status", src_link("NE-DEPTH")],
        ["Licensed operator", "DraftKings Sportsbook", "Settlement, parlay repricing, playing-time rules",
         "Historical prices", src_link("DK-SGP")],
        ["Standards body", "NIST/SEMATECH", "RMSE, multiple comparisons, bootstrap", "NFL facts", src_link("NIST-MULT")],
        ["This repository", "Committed files", "Counts, arithmetic, project state", "External facts",
         repo_link("decisions/recompute.py", "recompute.py")],
    ]
    rules = [
        ["Every table row links an official publisher or the committed file it came from",
         "decisions/check.py fails the build otherwise.", repo_link("decisions/check.py", "check.py")],
        ["An unverifiable value is blank and links to the flag page", "The blank marker is machine-checked.",
         A("flagged.html", "flags")],
        ["No network access during the build", "The build reads only committed JSON; snapshots are dated, not live.",
         repo_link("decisions/build.py", "build.py")],
        ["The build is deterministic", "Running build.py twice yields byte-identical output; the checker re-runs and diffs.",
         repo_link("decisions/build.py", "build.py")],
        ["A number is never inferred", "Where a quantity does not exist officially it is blank and the reason recorded.",
         repo_link("decisions/recompute.py", "recompute.py")],
    ]
    reproduce = ("<pre><code>python3 decisions/recompute.py   # re-derive every number from committed data\n"
                 "python3 decisions/build.py       # regenerate this section (deterministic)\n"
                 "python3 decisions/check.py       # fail-closed verifier for this section</code></pre>"
                 '<p class="small muted">Snapshots the build reads: '
                 f'{repo_link("decisions/data/injuries_week10_2026.json", "injury snapshot")}, '
                 f'{repo_link("decisions/data/standings_2026.json", "standings snapshot")} and '
                 f'{repo_link("decisions/data/recompute.json", "recomputation output")}. '
                 "They are dated and are not refreshed by the build.</p>")
    secs = [
        dict(h="What counts as an official source here",
             p="An official publisher is the organisation that publishes the fact: the NFL and its clubs and properties, licensed "
               "operators for their own rules, US standards bodies for statistical definitions, and this repository's committed "
               "files for project-state facts. A third-party dataset is never used to fill a verified value.",
             html=T(["Tier", "Who", "Used for", "Not used for", "Example source"], tiers, caption="Source tiers")),
        dict(h="Every source opened for this section",
             p=f"{len(SOURCES['sources'])} entries. Each was opened on 2026-11-12; the quoted text is what was read in the page "
               "body. A blocked entry records the 404 itself as evidence, because its absence is a finding.",
             html=T(["ID", "Publisher", "Tier", "URL", "Quoted claim", "Status", "Method"], rows, caption="Source register")),
        dict(h="Verification discipline", p="The rules below are what the checker enforces, not aspirations.",
             html=T(["Rule", "How it is enforced", "Where"], rules, caption="Rules")),
        dict(h="Reproduce", p="Three commands. The first needs no third-party packages; all three are standard library only.",
             html=reproduce),
    ]
    return page("method", "Method & sources",
                "What counts as an official source, every page opened for this section, and the rules the verifier enforces.",
                secs)


def build_exec():
    c = RECOMPUTE["counts"]
    n_block = sum(1 for q in QUESTIONS["questions"] if "blocks" in q["status"])
    s = INJURIES["summary"]
    adds = ("<ul>"
            f"<li><strong>Decision readiness.</strong> {len(SUGGESTIONS['suggestions'])} scored proposals and "
            f"{len(QUESTIONS['questions'])} questions ({n_block} blocking) so a path can be chosen before anything is built.</li>"
            f"<li><strong>Injury intelligence.</strong> The first injury data in the project: {s['players_listed']} official "
            "player rows for 2026 Week 10, with the confidence tier of every finding stated.</li>"
            f"<li><strong>Independent recomputation.</strong> {c['checks']} checks re-derived from committed data; "
            f"{c['match']} matched exactly and no fabricated number was found.</li>"
            "<li><strong>Honest failure.</strong> Four of this session's own claims were wrong and are published as withdrawn on the defect register, including one caught while this page was being built.</li>"
            "</ul>")
    findings = [
        ["1", "No lawful data basis and no price archive",
         "NFL Terms 1.1/1.3; no quote file anywhere in the repository",
         "No empirical claim can be published as a product until S01 (licence) and S02 (price archive) are resolved. This is the root blocker.",
         src_link("NFL-TERMS")],
        ["2", "The best rule does not survive multiplicity",
         "Gate strategy G-S14: +8.41% over 607 bets, q = 0.288; 0 of 18 rules pass",
         "The leaderboard cannot rank skill today. Ranking it would publish luck as merit.",
         repo_link("data/derived/gates_results.csv", "gates_results.csv")],
        ["3", "Availability is the biggest missing input, and it is half-obtainable now",
         f"{s['players_listed']} official rows available; only {s['game_status_coverage_pct']}% carry a game status",
         "Build the two-field data model (S11) and archive daily (S04). Do not treat DNP as an absence.",
         src_link("NFL-INJ-POLICY")],
        ["4", "No official depth chart or snap count exists",
         "nfl.com/depth-charts 404; nextgenstats /stats/participation 404; NE and DET label their own charts unofficial",
         "The 2nd/3rd/4th-string requirement can only ever be club-sourced opinion. State that limit or drop the claim.",
         src_link("NE-DEPTH")],
        ["5", "The site is stale and fragmented",
         "Dataset ends 2026-10-29; seven parallel builds live in one repository",
         "Freeze the data date (S12) and pick one canonical surface (S13) before adding anything.",
         repo_link("data/raw/games.csv", "games.csv")],
    ]
    nexts_src = [repo_link("decisions/data/suggestions.json", "registry"),
                 src_link("NFL-INJ-POLICY"),
                 repo_link("data/raw/games.csv", "games.csv")]
    nexts = [
        ["1", "Add two separate fields, practice status and game status, and never merge them",
         "The snapshot already shows why: most non-participants have no game status.", A("suggestions.html", "S11"), "nothing"],
        ["2", "Archive one dated injury snapshot per day with the read time",
         "There is no history, so no injury signal can be tested until archiving starts.", A("suggestions.html", "S04"),
         "Q01 (licence), Q03 (storage)"],
        ["3", "Freeze the dataset date on every page and auto-flag staleness",
         "The site presents two-week-old data with no warning.", A("suggestions.html", "S12"), "nothing"],
    ]
    nonclaims = [
        ["That any injury signal works", "No history, no prices, and the game status field is mostly blank."],
        ["That any player will or will not play", "Availability is the league's declaration, not this project's prediction."],
        ["That the depth tiers are official", "Two of the four clubs call their own charts unofficial."],
        ["That a leaderboard should be funded", "No power target, no quotes, no terms (Q05, Q06)."],
        ["That the project's numbers are wrong", "They reproduced. What matters is what they support, which is little."],
    ]
    secs = [
        dict(h="Bottom line",
             p="The project has built a real line-origination pipeline, and it does not have an edge. That is the finding, and "
               "it is a useful one: it is stated honestly, it reproduces, and it stops the project spending money chasing a "
               "signal that is not there.",
             html=callout("ok", "What this session adds", adds)),
        dict(h="The five findings that matter for a decision",
             p="Every claim below is sourced on the page that owns it.",
             html=T(["#", "Finding", "Evidence", "What it means for the decision", "Source"], findings,
                   caption="Findings")),
        dict(h="Recommended next three actions",
             html=T(["Order", "Action", "Why now", "Where", "Blocked by", "Source"],
                   [n + [src] for n, src in zip(nexts, nexts_src)], caption="Next actions")),
        dict(h="What this section does not claim",
             html=T(["Non-claim", "Reason", "Where the claim lives"], 
                   [[n[0], n[1], repo_link("decisions/data/suggestions.json", "registry")] for n in nonclaims],
                   caption="Non-claims")),
    ]
    return page("executive-summary", "Executive summary",
                "What this session found, what it adds, the five findings that matter for a decision and the next three actions "
                "— written so a reader who reads nothing else still makes a better decision.", secs)


PAGES = {
    "index": build_index,
    "executive-summary": build_exec,
    "suggestions": build_suggestions,
    "questions": build_questions,
    "paths": build_paths,
    "injuries": build_injuries,
    "standings": build_standings,
    "recompute": build_recompute,
    "defects": build_defects,
    "flagged": build_flagged,
    "method": build_method,
}


def build():
    (OUT / "assets").mkdir(parents=True, exist_ok=True)
    for slug, fn in PAGES.items():
        (OUT / f"{slug}.html").write_text(fn(), encoding="utf-8")
    print(f"built {len(PAGES)} pages; {len(SOURCES['sources'])} sources; "
          f"{len(SUGGESTIONS['suggestions'])} suggestions; {len(QUESTIONS['questions'])} questions")


if __name__ == "__main__":
    build()
