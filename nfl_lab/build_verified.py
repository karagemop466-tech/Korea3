"""Generate the official-evidence-only dashboard under verified/."""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "verified"
DATA = OUT / "data"

NAV = [
    ("index.html", "Overview"),
    ("strategies.html", "Strategies"),
    ("lines.html", "Own lines"),
    ("props.html", "Player props"),
    ("parlays.html", "Parlays"),
    ("correlations.html", "Correlations"),
    ("validation.html", "Validation"),
    ("leaderboard.html", "Leaderboard"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged for review"),
    ("requirements.html", "Requirements"),
    ("audit.html", "Repo audit"),
]

CSS = """
:root{color-scheme:light;--ink:#152238;--muted:#5c6b80;--line:#dfe6ee;--bg:#f5f7fa;--card:#fff;--green:#0d6b57;--amber:#9a6700;--red:#b42318;--blue:#1d4ed8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.6 system-ui,-apple-system,'Segoe UI',sans-serif}
a{color:var(--blue)}header{background:#fff;border-bottom:1px solid var(--line)}.wrap{max-width:1240px;margin:0 auto;padding:0 24px}
.top{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:20px 0}.brand{display:flex;gap:12px;align-items:center;text-decoration:none;color:var(--ink);font-weight:800;font-size:18px}.mark{display:grid;place-items:center;width:42px;height:42px;border-radius:12px;background:#123f35;color:#fff}.brand small{display:block;font-size:11px;letter-spacing:.12em;color:var(--muted);font-weight:700}
.badge{font-size:11px;font-weight:800;letter-spacing:.08em;color:var(--green);background:#e7f4ef;border:1px solid #bfe3d6;padding:6px 10px;border-radius:999px;white-space:nowrap}
nav{display:flex;gap:4px;overflow-x:auto;padding:0 0 12px}nav a{white-space:nowrap;text-decoration:none;color:#475569;font-size:13px;font-weight:650;padding:8px 11px;border-radius:8px}nav a:hover{background:#eef2f7}nav a.active{background:#123f35;color:#fff}
main{padding:40px 24px 64px}.eyebrow{font-size:11px;font-weight:800;letter-spacing:.14em;color:var(--green);text-transform:uppercase}h1{font-size:clamp(30px,4vw,44px);line-height:1.15;letter-spacing:-.03em;margin:10px 0}h2{font-size:21px;margin:0;letter-spacing:-.01em}.lead{color:var(--muted);font-size:17px;max-width:900px;margin:0 0 24px}
.notice{background:#fff8e6;border:1px solid #f0d58a;border-left:4px solid #d99a00;border-radius:10px;padding:14px 16px;margin:0 0 24px;color:#6b4e00}.notice.info{background:#eef4ff;border-color:#c7d7fe;border-left-color:#3b82f6;color:#1e3a8a}
.grid{display:grid;gap:16px;margin:24px 0}.k4{grid-template-columns:repeat(4,1fr)}.k3{grid-template-columns:repeat(3,1fr)}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:18px;box-shadow:0 4px 16px #10233f08}.card .tag{font-size:11px;font-weight:800;letter-spacing:.08em;color:var(--muted);text-transform:uppercase}.card .num{font-size:30px;font-weight:850;letter-spacing:-.03em;margin:6px 0}.card .sub{font-size:13px;color:var(--muted)}
section{background:#fff;border:1px solid var(--line);border-radius:14px;overflow:hidden;margin:22px 0;box-shadow:0 4px 16px #10233f06}.section-head{display:flex;justify-content:space-between;align-items:center;gap:16px;padding:18px 20px;border-bottom:1px solid var(--line)}.section-head p{margin:4px 0 0;color:var(--muted);font-size:13px}.count{font-size:11px;font-weight:800;color:var(--muted);background:#f1f5f9;padding:5px 9px;border-radius:999px;white-space:nowrap}
.scroll{overflow-x:auto}table{width:100%;border-collapse:collapse;min-width:820px}th{background:#f8fafc;color:#64748b;font-size:11px;letter-spacing:.08em;text-transform:uppercase;text-align:left}th,td{padding:13px 18px;border-top:1px solid var(--line);vertical-align:top}td:first-child{font-weight:700}td{font-size:14px}.muted{color:var(--muted)}.small{font-size:12px}.blank{display:inline-block;min-width:64px;border-bottom:1px dashed #cbd5e1;color:#94a3b8}.pill{display:inline-block;font-size:11px;font-weight:800;border-radius:999px;padding:3px 9px}.pill.blocked,.pill.unvalidated{background:#fff7ed;color:#9a3412}.pill.pass{background:#ecfdf5;color:#065f46}.pill.fail{background:#fef2f2;color:#991b1b}.pill.info{background:#eff6ff;color:#1e40af}
code{background:#f1f5f9;border-radius:5px;padding:2px 5px;font-size:13px}.footnote{color:var(--muted);font-size:12px;margin-top:18px}footer{border-top:1px solid var(--line);background:#fff;color:var(--muted);font-size:12px;padding:22px 0}.tools{display:flex;gap:10px;flex-wrap:wrap;margin:14px 0}.tools input,.tools select{border:1px solid var(--line);border-radius:8px;padding:9px 12px;font:inherit;background:#fff}.btn{display:inline-block;text-decoration:none;font-weight:700;font-size:13px;border-radius:8px;padding:9px 13px;background:#123f35;color:#fff}.btn.secondary{background:#fff;color:#123f35;border:1px solid var(--line)}
@media(max-width:900px){.k4,.k3{grid-template-columns:repeat(2,1fr)}}@media(max-width:560px){.k4,.k3{grid-template-columns:1fr}.top{flex-direction:column;align-items:flex-start}main{padding:28px 16px 48px}.wrap{padding:0 16px}}
"""

JS = """
document.addEventListener('input',e=>{if(!e.target.matches('[data-filter]'))return;const q=e.target.value.toLowerCase();const table=document.querySelector(e.target.dataset.filter);if(!table)return;table.querySelectorAll('tbody tr').forEach(tr=>{tr.hidden=!tr.textContent.toLowerCase().includes(q)})});
"""


def e(x) -> str:
    return escape(str(x), quote=True)


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


_SOURCE_CACHE = None


def src(source_id: str, label: str = "Official reference") -> str:
    global _SOURCE_CACHE
    if _SOURCE_CACHE is None:
        _SOURCE_CACHE = {r["evidence_id"]: r for r in load("sources.json")}
    r = _SOURCE_CACHE[source_id]
    return (f'<a href="{e(r["url"])}" data-source-id="{e(source_id)}" data-source-url="{e(r["url"])}" '
            f'target="_blank" rel="noopener noreferrer">{e(label)} ↗</a>')


def blank(flag: str = "flagged.html") -> str:
    return f'<span class="blank" aria-label="unverified"></span> <a class="small" href="{flag}">unverified</a>'


def pill(status: str) -> str:
    cls = status if status in {"pass", "fail", "blocked", "unvalidated", "info"} else "info"
    return f'<span class="pill {cls}">{e(status.replace("_", " "))}</span>'


def table(headers: list[str], rows: list[list[str]], caption: str = "") -> str:
    head = "".join(f"<th scope=\"col\">{e(h)}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in row) + "</tr>" for row in rows)
    cap = f"<caption class=\"small muted\">{e(caption)}</caption>" if caption else ""
    return f'<div class="scroll"><table>{cap}<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>'


def section(title: str, subtitle: str, content: str, count: str = "") -> str:
    c = f'<span class="count">{e(count)}</span>' if count else ""
    return f'<section><div class="section-head"><div><h2>{e(title)}</h2><p>{e(subtitle)}</p></div>{c}</div>{content}</section>'


def page(slug: str, title: str, subtitle: str, body: str) -> str:
    nav = "".join(f'<a href="{href}" class="{"active" if href == slug else ""}">{e(label)}</a>' for href, label in NAV)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} | NFL Verified Workbench</title><meta name="description" content="Official-evidence-only NFL line origination research and validation workbench.">
<link rel="stylesheet" href="assets/style.css"><script src="assets/app.js" defer></script></head><body>
<header><div class="wrap"><div class="top"><a class="brand" href="index.html"><span class="mark">N</span><span>NFL Verified Workbench<small>OFFICIAL EVIDENCE · FAIL-CLOSED VALIDATION</small></span></a><span class="badge">RESEARCH ONLY · NO PICKS</span></div>
<nav aria-label="Main navigation">{nav}</nav></div></header>
<main class="wrap"><div class="eyebrow">NFL / {e(title)}</div><h1>{e(title)}</h1><p class="lead">{e(subtitle)}</p>{body}
<p class="footnote">Generated 2026-11-02. Blank means unverified, not zero. Exploratory third-party results are preserved in the <a href="../index.html">main repository dashboard</a> and are not promoted here. Independent research; not affiliated with the NFL or any sportsbook.</p></main>
<footer><div class="wrap">NFL Verified Workbench · <a href="flagged.html">Flagged for review</a> · <a href="sources.html">Official sources</a> · <a href="../audit/flagged.html">Independent audit</a></div></footer></body></html>"""


def page_index() -> str:
    status = load("status.json")
    strategies = load("strategies.json")
    cards = f"""<div class="grid k4">
<div class="card"><div class="tag">Verified empirical values</div><div class="num">{status['verified_empirical_values']}</div><div class="sub">No licensed event-level official dataset was admitted.</div></div>
<div class="card"><div class="tag">Reward-eligible strategies</div><div class="num">{status['eligible_strategies']}</div><div class="sub">Every gate must pass; none can pass on empty inputs.</div></div>
<div class="card"><div class="tag">Pre-registered hypotheses</div><div class="num">{len(strategies)}</div><div class="sub">Singles, player props, parlays and joint-player combinations.</div></div>
<div class="card"><div class="tag">Real-money execution</div><div class="num">0</div><div class="sub">No bets placed; no sportsbook account access.</div></div></div>"""
    rows = [
        ["What this layer does", "Provides typed contracts, exact pricing/settlement arithmetic, causal model specifications, clustered validation gates, and a row-level official-source register.", pill("info"), src("nist_ci")],
        ["Evidence-chain hardening", "Settlement admission now resolves the quoted operator, dated/jurisdiction-specific rules, accepted price, official outcome and hashed forecast artifact. Caller-supplied execution booleans and p-values are rejected.", pill("info"), src("dk_player_settlement")],
        ["What it refuses to do", "It does not scrape NFL.com, impute missing prices, treat a community mirror as official verification, or publish unverified correlations, ROI or rewards.", pill("blocked"), src("nfl_terms")],
        ["Current decision", "Keep all empirical fields blank and all strategies unvalidated until licensed, event-level official evidence and archived operator rules are admitted.", pill("blocked"), src("nfl_stats")],
        ["Luck policy", "Luck cannot be eliminated. Promotion requires untouched holdout evidence, clustered uncertainty, multiplicity control, price stress, and a post-freeze forward sample.", pill("info"), src("nist_multiple")],
        ["Exploratory archive", "Earlier sessions' third-party backtests remain available from the main dashboard and session index, clearly separated from this verified view.", pill("info"), src("nfl_terms")],
    ]
    body = cards + '<div class="notice"><strong>Read this first.</strong> This is the official-evidence-only view. It intentionally contains no measured NFL edge, correlation coefficient, ROI, live line, or funded reward. Those values require inputs that were not available under the project’s verification and data-rights rules.</div>'
    body += section("Executive summary", "Decision-ready status and boundaries", table(["Item", "Finding", "Status", "Official reference"], rows), f"{len(rows)} entries")
    body += '<div class="tools"><a class="btn" href="strategies.html">Open strategy lab</a><a class="btn secondary" href="validation.html">Open validation gates</a><a class="btn secondary" href="flagged.html">Open review flags</a></div>'
    return page("index.html", "Executive summary", "A fail-closed research workbench for originating NFL lines without publishing unverified numbers.", body)


def page_strategies() -> str:
    rows = []
    for s in load("strategies.json"):
        rows.append([e(s["id"]) + "<br>" + e(s["name"]), e(s["category"]), e(s["hypothesis"]), e(s["signal"]), e(s["model"]), pill(s["status"]), src(s["source_id"])])
    body = '<div class="notice info"><strong>Hypotheses, not edges.</strong> Each row is a research design. No strategy has passed validation. Required inputs and failure modes are part of the pre-registered specification.</div>'
    body += '<div class="tools"><input data-filter="#strategy-table" placeholder="Filter strategies…" aria-label="Filter strategies"></div>'
    body += section("Strategy register", "Single bets, player props, parlays and risk filters", table(["ID / name", "Category", "Hypothesis", "Signal", "Model", "Status", "Source"], rows), f"{len(rows)} hypotheses").replace('<table>', '<table id="strategy-table">', 1)
    detail = []
    for s in load("strategies.json"):
        detail.append([e(s["id"]), "<br>".join(e(x) for x in s["required"]), "<br>".join(e(x) for x in s["failure_modes"]), src(s["source_id"])])
    body += section("Required inputs and failure modes", "Admission requirements before any backtest or promotion", table(["ID", "Required licensed inputs", "Failure modes", "Source"], detail))
    return page("strategies.html", "Strategy lab", "Pre-registered, mechanically specified hypotheses with explicit data requirements and failure modes.", body)


def page_lines() -> str:
    rows = [
        ["Fair home spread", "Negative median of the predictive home-margin distribution", blank(), pill("blocked"), src("nfl_stats")],
        ["Fair total", "Median of the predictive total-points distribution", blank(), pill("blocked"), src("dk_market_rules")],
        ["Home win / tie / loss", "Empirical predictive margin distribution; tie mass retained", blank(), pill("blocked"), src("dk_market_rules")],
        ["Market edge", "Model probability minus timestamped de-vigged executable market probability", blank(), pill("blocked"), src("dk_odds")],
    ]
    body = '<div class="notice"><strong>No live or historical verified lines are published.</strong> The model code exists, but it emits nothing without admitted licensed official game history. Missing values are blank, not inferred.</div>'
    body += section("Line origination outputs", "What the model would produce after admission", table(["Output", "Definition", "Verified value", "Status", "Source"], rows))
    body += section("Causality rules", "No future information may enter a forecast", table(["Rule", "Requirement", "Status", "Source"], [
        ["Training cutoff", "Only official-final games whose result availability timestamp is at or before the forecast cutoff may enter the fit.", pill("info"), src("nist_ci")],
        ["Feature timestamp", "Every feature must be available at or before the forecast issue time.", pill("info"), src("nfl_ops")],
        ["Quote timestamp", "Executable quote must be observed before kickoff and matched to the same line and market.", pill("info"), src("dk_odds")],
        ["Residual distribution", "Empirical training residuals preserve discrete score structure; no normal approximation is forced.", pill("info"), src("nist_bootstrap")],
    ]))
    return page("lines.html", "Own lines", "Causal line-origination specification with blank verified outputs until licensed official inputs exist.", body)


def page_props() -> str:
    rows = [
        ["Participation probability", "Beta prior updated by admitted player game logs", blank(), pill("blocked"), src("dk_player_settlement")],
        ["Conditional production", "Recency-weighted empirical outcomes shrunk toward a position pool", blank(), pill("blocked"), src("nfl_stats")],
        ["Over / under / push", "Participation-weighted threshold probabilities at the operator's quoted line", blank(), pill("blocked"), src("dk_prop")],
        ["Void handling", "Nonparticipation routed to archived operator rule, not silently treated as an under", blank(), pill("blocked"), src("dk_player_settlement")],
        ["Joint player combo", "Aligned scenario simulation preserving within-game dependence", blank(), pill("blocked"), src("dk_sgp")],
    ]
    body = '<div class="notice"><strong>Player-prop numbers are withheld.</strong> No licensed official player game logs or timestamped executable operator prop quotes were admitted. No prop correlation, line, probability or ROI is published.</div>'
    body += section("Player-prop outputs", "Mixture model and settlement-aware pricing", table(["Output", "Definition", "Verified value", "Status", "Source"], rows))
    body += section("Settlement checks", "Operator-specific rules must be archived before evaluation", table(["Check", "Requirement", "Status", "Source"], [
        ["Participation definition", "DraftKings football rules define participation as playing in at least one play in the applicable event; the archived rule for the exact market/date still controls settlement.", pill("info"), src("dk_football_rules")],
        ["Nonparticipation", "Use the archived sport-specific rule for the exact market, operator, jurisdiction and date.", pill("blocked"), src("dk_player_settlement")],
        ["Early exit", "Do not assume an injury-related exit has the same settlement as inactive/nonparticipation.", pill("blocked"), src("dk_player_settlement")],
        ["SGP void leg", "Use the operator's SGP-specific repricing rule; traditional parlay arithmetic is not a substitute.", pill("blocked"), src("dk_sgp")],
    ]))
    return page("props.html", "Player props", "Participation-aware player-prop and combo specification; all empirical values remain unverified.", body)


def page_parlays() -> str:
    rows = [
        ["Traditional parlay", "All legs must win; a pushed leg is removed and odds recalculated under the operator's rule.", blank(), pill("blocked"), src("dk_parlay")],
        ["Same-game parlay", "SGP odds are calculated differently; dependence must be priced jointly and void rules are sport/state specific.", blank(), pill("blocked"), src("dk_sgp")],
        ["Cross-game joint probability", "Estimate from aligned outcomes; do not assume independence merely because games differ.", blank(), pill("blocked"), src("nist_correlation")],
        ["Player-prop combo", "Use aligned scenario simulation or a validated joint distribution, not the product of marginals without evidence.", blank(), pill("blocked"), src("dk_sgp")],
    ]
    body = '<div class="notice info"><strong>Exact arithmetic is implemented; empirical ticket prices are not.</strong> The engine supports push/void policies as explicit inputs. It never invents an operator’s last-available repricing snapshot.</div>'
    body += section("Parlay structures", "Traditional, same-game and player-prop combinations", table(["Structure", "Rule / method", "Verified price", "Status", "Source"], rows))
    body += section("Pricing identities", "Definitions used by the engine", table(["Identity", "Formula", "Source"], [
        ["American to decimal", "<code>d = 1 + a/100</code> for <code>a &gt; 0</code>; <code>d = 1 + 100/|a|</code> for <code>a &lt; 0</code>.", src("dk_odds")],
        ["Fair decimal with push/void", "<code>d = 1 + (1 − p_win − p_push − p_void) / p_win</code>.", src("dk_odds")],
        ["Two-leg joint from phi", "<code>P(A∩B) = pA·pB + φ·√(pA(1−pA)pB(1−pB))</code>, subject to feasible bounds.", src("nist_correlation")],
        ["Fréchet bounds", "Project-derived probability bound: <code>max(0, Σp − n + 1) ≤ P(all) ≤ min(p)</code>. The official reference supports correlation context, not an NFL betting rule.", src("nist_correlation")],
    ]))
    return page("parlays.html", "Parlays", "Settlement-aware parlay arithmetic and joint-probability requirements; no verified ticket prices.", body)


def page_correlations() -> str:
    rows = [
        ["Player leg pairs", "Binary outcomes at matched quoted thresholds; phi with cluster uncertainty and missingness", blank(), blank(), blank(), pill("blocked"), src("nist_correlation")],
        ["Same-game market pairs", "Spread/total/moneyline outcomes at the same timestamp and line", blank(), blank(), blank(), pill("blocked"), src("nist_correlation")],
        ["Cross-game returns", "Aligned season-week strategy returns, including zero-exposure weeks", blank(), blank(), blank(), pill("blocked"), src("nist_bootstrap")],
        ["Threshold sensitivity", "Re-estimate at neighboring lines and pregame snapshots", blank(), blank(), blank(), pill("blocked"), src("nist_correlation")],
    ]
    body = '<div class="notice"><strong>No empirical correlation coefficient is published in this verified view.</strong> Earlier third-party estimates remain in the exploratory archive. They are not event-level official verification and are not promoted here.</div>'
    body += section("Correlation register", "What will be measured after admission", table(["Pair family", "Definition", "Verified φ / r", "Sample n", "Interval", "Status", "Source"], rows))
    body += section("Interpretation rules", "Correlation is a pricing input, not a causal claim", table(["Rule", "Requirement", "Source"], [
        ["Linear association", "Pearson/phi measures linear association; zero does not prove independence.", src("nist_correlation")],
        ["Threshold specificity", "A coefficient is tied to the exact leg thresholds, market, snapshot and settlement rule.", src("dk_market_rules")],
        ["Multi-leg caution", "Pairwise coefficients do not uniquely determine a three-or-more-leg joint distribution.", src("nist_correlation")],
        ["Uncertainty", "Resample whole season-week clusters; report sample size and missingness.", src("nist_bootstrap")],
    ]))
    return page("correlations.html", "Correlations", "Threshold-specific dependence measurement plan with blank verified coefficients.", body)


def page_validation() -> str:
    gates = load("gates.json")
    first = gates[0]["gates"] if gates else []
    rows = []
    source_map = {"preregistration": "nist_multiple", "evidence_and_rights": "nfl_terms", "chronology": "nfl_ops", "sample": "nist_ci", "probability_quality": "nist_ci", "economics": "nist_ci", "multiplicity": "nist_bonferroni", "stability": "nist_bootstrap", "execution_and_risk": "dk_odds", "forward_freeze": "nist_multiple"}
    for g in first:
        rows.append([e(g["name"].replace("_", " ").title()), e(g["detail"]), pill(g["status"]), src(source_map.get(g["name"], "nist_ci"))])
    body = '<div class="notice"><strong>All gates are fail-closed.</strong> A missing input is blocked, not passed. No strategy is reward-eligible on empty or unverified inputs.</div>'
    body += section("Mandatory gates", "Every gate must pass before leaderboard eligibility", table(["Gate", "Requirement", "Current status", "Source"], rows), f"{len(rows)} gates")
    body += section("Luck controls", "What the workbench estimates instead of claiming luck removal", table(["Control", "Implementation", "Source"], [
        ["Clustered uncertainty", "Season-week cluster bootstrap for ROI and paired Brier skill.", src("nist_bootstrap")],
        ["Multiplicity", "Bonferroni across the complete registered family; BH q reported as secondary.", src("nist_bonferroni")],
        ["Price stress", "Recompute wins after a pre-registered decimal slippage haircut.", src("dk_odds")],
        ["Forward freeze", "Require a post-freeze forward/paper sample; no real-money execution.", src("nist_multiple")],
        ["Probability quality", "Action-conditional Brier score, log loss, calibration bins and paired improvement versus a timestamped baseline. The scoring formula is project-defined; the NWS reference remains unverified.", src("nist_ci")],
    ]))
    return page("validation.html", "Validation gates", "Fail-closed promotion rules, clustered uncertainty and multiplicity control.", body)


def page_leaderboard() -> str:
    board = load("leaderboard.json")
    rows = []
    for r in board:
        rows.append([e(r["strategy_id"]), "—" if r["rank"] is None else str(r["rank"]), blank(), blank(), blank(), pill(r["status"]), src("nist_multiple")])
    body = '<div class="notice"><strong>No rewards are funded or paid.</strong> The leaderboard is a competition specification. Only strategies passing every gate can receive a rank or score; reward amounts remain blank until a sponsor, pool, eligibility rules and payout terms are verified.</div>'
    body += section("Eligibility board", "No fabricated rankings", table(["Strategy", "Rank", "Holdout lower-bound score", "Verified ROI", "Reward", "Status", "Source"], rows))
    body += section("Competition rules", "Proposed design, not an official contest", table(["Rule", "Specification", "Source"], [
        ["Eligibility", "All mandatory gates pass on admitted official evidence and executable quotes.", src("nist_multiple")],
        ["Score", "Lower confidence bound of untouched holdout net ROI; tie-break by paired probability-score improvement.", src("nist_ci")],
        ["Rewards", "Disabled in code until a funded pool, sponsor, jurisdiction and payout terms are verified; no prize is currently offered or computed.", src("nfl_rg")],
        ["Anti-gaming", "Register every candidate and tuning trial; no retroactive family changes; no in-sample winner promotion.", src("nist_multiple")],
    ]))
    return page("leaderboard.html", "Leaderboard", "A reward-eligible-only competition specification with no fabricated scores or prizes.", body)


def page_sources() -> str:
    rows = []
    for r in load("sources.json"):
        claim = e(r["claim"]) if r["claim"] else blank()
        status = pill("pass") if r["review_status"] == "verified" else pill("blocked")
        link = (f'<a href="{e(r["url"])}" data-source-id="{e(r["evidence_id"])}" data-source-url="{e(r["url"])}" '
                f'target="_blank" rel="noopener noreferrer">Official source ↗</a>')
        rows.append([e(r["evidence_id"]), e(r["publisher"]), claim, status, e(r.get("support_scope", "context")), e(r.get("source_version") or ""), e(r["verified_at"]), e(r["method"]), link])
    body = '<div class="notice info"><strong>Link-only evidence.</strong> These sources support the specific statements shown. They do not grant redistribution rights, endorse the project, or verify any empirical betting value. An unverified source has a blank claim and is flagged.</div>'
    body += section("Official source register", "Primary league, operator and government references; support scope is explicit", table(["ID", "Publisher", "Claim reviewed", "Review", "Support scope", "Version", "Checked (UTC)", "Verification method", "Link"], rows), f"{len(rows)} sources")
    return page("sources.html", "Source register", "Official publisher links reviewed for the exact claims shown; no inferred values.", body)


def page_flagged() -> str:
    rows = [
        ["F-V01", "Licensed event-level official outcomes", "No NFL license or admitted event-level official dataset exists in this workbench.", blank(), "Blocked", src("nfl_terms")],
        ["F-V02", "Executable historical odds", "No timestamped executable operator archive was admitted; community closing lines are not official quote evidence.", blank(), "Blocked", src("dk_odds")],
        ["F-V03", "Player-prop inputs", "No licensed official player game logs or operator prop quotes were admitted.", blank(), "Blocked", src("dk_player_settlement")],
        ["F-V04", "Correlation coefficients", "No matched official leg outcomes at quoted thresholds were admitted.", blank(), "Blocked", src("nist_correlation")],
        ["F-V05", "Strategy performance", "No verified holdout ROI, Brier skill, forward sample or reward-eligible strategy exists.", blank(), "Blocked", src("nist_ci")],
        ["F-V06", "Archived settlement rules", "Current help pages do not prove the rule in force for a historical bet; exact operator/date/jurisdiction snapshots are required.", blank(), "Needs review", src("dk_sgp")],
        ["F-V07", "Rewards and legal eligibility", "No funded pool, sponsor, jurisdiction, age or licensing verification exists.", blank(), "Needs review", src("nfl_rg")],
        ["F-V08", "Exploratory third-party results", "Earlier sessions' backtests use community data and are preserved as exploratory, not official verification.", blank(), "Needs review", src("nfl_terms")],
        ["F-V09", "Data-rights boundary", "NFL.com terms restrict systematic compilation without written consent; this workbench performs no NFL fetching.", blank(), "Flagged", src("nfl_terms")],
        ["F-V10", "Luck removal claim", "Luck cannot be eliminated; the workbench only estimates uncertainty and refuses promotion without strong out-of-sample evidence.", blank(), "Flagged", src("nist_ci")],
        ["R1", "Settlement-rule admission", "Fixed in code: rules must be official, same operator, market/jurisdiction-specific, versioned, effective at acceptance, licensed and hash-pinned. Historical archives are still absent.", blank(), "Mitigated; data blocked", src("dk_player_settlement")],
        ["R2", "Quote-to-settlement identity", "Fixed in code: settlement resolves the admitted quote and checks event, market, selection, threshold, operator, jurisdiction, acceptance time, accepted price and recomputed profit.", blank(), "Mitigated; data blocked", src("dk_odds")],
        ["R3", "Forecast-to-bet binding", "Fixed in code: each bet resolves a forecast artifact hash, model version, feature snapshot, baseline quote pair and pre-acceptance issue time. Probability scoring uses the matched forecast.", blank(), "Mitigated; data blocked", src("nist_ci")],
        ["R4", "Row-level source semantics", "Mitigated: generated rows carry source IDs checked against the registry; support scope is published. CI does not re-fetch live pages, so content drift still requires scheduled/manual re-review.", blank(), "Partially mitigated", src("nfl_terms")],
        ["R5", "Responsible-gambling attribution", "Fixed: the cited responsible-betting story is attributed to Associated Press content hosted by NFL.com, not presented as an NFL-authored release.", blank(), "Resolved", src("nfl_rg")],
        ["R6", "NWS Brier-score reference", "The official NWS PDF could not be directly retrieved in this session. Its claim is blank and unverified; project scoring definitions do not rely on it as verified evidence.", blank(), "Unverified", src("nws_metrics")],
    ]
    body = '<div class="notice"><strong>Unverified values stay blank.</strong> These flags do not block publication of the research workbench, but they do block any verified empirical claim, betting signal or reward.</div>'
    body += section("Flagged for review", "Open blockers and irregularities", table(["ID", "Item", "Finding", "Unverified value", "Status", "Official source"], rows), f"{len(rows)} flags")
    body += '<p class="footnote">See also the <a href="../audit/flagged.html">independent cross-session audit</a> and the <a href="../index.html">exploratory main dashboard</a>.</p>'
    return page("flagged.html", "Flagged for review", "Open blockers, unverified values and data-rights boundaries.", body)


def page_requirements() -> str:
    rows = [
        ["Collect/organize/analyze NFL requirements", "Typed contracts, source register, strategy registry, validation engine and static dashboard implemented.", pill("info"), src("nfl_stats")],
        ["Originate own lines", "Causal team-line model specified and implemented; verified outputs blank pending licensed official history.", pill("blocked"), src("nfl_stats")],
        ["Useful signals", "Eight pre-registered hypotheses with signals, required inputs and failure modes; none validated.", pill("unvalidated"), src("nist_multiple")],
        ["Singles / parlays / player-prop combos", "Settlement-aware pricing and joint-probability code; empirical prices and correlations blank.", pill("blocked"), src("dk_parlay")],
        ["Validation gates", "Ten fail-closed gates including evidence, chronology, sample, probability quality, economics, multiplicity, stability, risk and forward freeze.", pill("info"), src("nist_bonferroni")],
        ["Correlation values", "Measurement code and uncertainty plan implemented; verified coefficients blank.", pill("blocked"), src("nist_correlation")],
        ["Remove luck", "Reframed as uncertainty estimation, multiplicity control, price stress and untouched holdout/forward evidence; luck cannot be eliminated.", pill("info"), src("nist_ci")],
        ["Leaderboard rewards", "Eligibility-only ranking and hypothetical reward specification; no funded prizes.", pill("blocked"), src("nfl_rg")],
        ["Executive summary", "Published on the overview page and in VERIFIED_EXECUTIVE_SUMMARY.md.", pill("info"), src("nfl_stats")],
        ["No manual input", "Build and checks run automatically; no user credentials or manual data entry required for the empty verified view.", pill("info"), src("nfl_ops")],
        ["Official source per row", "Every table row carries a registry source ID linking to an official league, operator or government source; the checker validates the ID/URL pair and support scope is shown.", pill("info"), src("nfl_terms")],
        ["Unverified values blank", "No inferred prices, correlations, ROI, lines or rewards are published in this view.", pill("info"), src("nfl_terms")],
        ["Parallel coordination", "Claims, conflicts, handoffs and integration results recorded in COORDINATION.md.", pill("info"), src("nfl_ops")],
        ["GitHub Pages delivery", "Static site generated under verified/ and linked from the repository dashboard after final integration.", pill("info"), src("nfl_stats")],
    ]
    body = section("Requirement traceability", "User requirement → implementation → verification boundary", table(["Requirement", "Implementation / status", "Status", "Source"], rows), f"{len(rows)} requirements")
    return page("requirements.html", "Requirements", "Line-by-line traceability from the request to the delivered workbench and its limits.", body)


def page_audit() -> str:
    rows = [
        ["A-V01", "NFL data-rights restriction", "Collector was proposed, stopped before execution, and removed after reviewing NFL.com Terms §§1.1/1.3.", "No NFL content was fetched or stored by this workbench.", src("nfl_terms")],
        ["A-V02", "Community data is not official verification", "Existing third-party backtests are preserved but not promoted into the verified view.", "Every verified empirical field remains blank.", src("nfl_terms")],
        ["A-V03", "Missing prices must not be imputed", "Quote contract rejects missing threshold lines and non-executable quotes cannot enter verified evaluation.", "No -110 substitution is used in this workbench.", src("dk_odds")],
        ["A-V04", "Current rules are not historical rules", "Settlement evaluation requires an archived operator rule snapshot matched to the bet.", "Historical settlement remains blocked.", src("dk_sgp")],
        ["A-V05", "Correlation is not causation", "Correlation register reports threshold-specific association with uncertainty, not causal proof.", "No empirical coefficient is published here.", src("nist_correlation")],
        ["A-V06", "Multiple comparisons inflate winners", "Validation requires a frozen family and Bonferroni control; BH q is secondary.", "No in-sample winner is promoted.", src("nist_multiple")],
        ["A-V07", "Synthetic tests are not NFL findings", "Unit tests use synthetic fixtures only and are excluded from published empirical outputs.", "Test results validate code, not betting skill.", src("nist_bootstrap")],
        ["A-V08", "Independent audit preserved", "The earlier audit remains at ../audit/flagged.html and is linked, not overwritten.", "Cross-session irregularities remain visible.", src("nfl_terms")],
        ["A-V09", "Evidence-chain bypasses", "R1–R3 were reproduced from the prior implementation and closed with resolved quote/rules/forecast admission plus adversarial synthetic tests.", "No real NFL record is admitted by the default build.", src("dk_player_settlement")],
        ["A-V10", "Caller-supplied validation shortcuts", "External family p-values and executable-quote booleans are no longer accepted; multiplicity is computed across the registered family and execution is evidence-checked.", "Empty or incomplete inputs remain blocked.", src("nist_bonferroni")],
        ["A-V11", "Availability-time leakage", "Team and player models now filter on result/stats availability timestamps, not merely kickoff.", "Synthetic truncation tests pass.", src("nfl_ops")],
        ["A-V12", "ROI and probability scoring", "ROI is stake-weighted with cluster resampling; binary probability scores are conditional on action and use matched forecast artifacts.", "No empirical ROI or Brier value is published.", src("nist_bootstrap")],
        ["A-V13", "Reward allocation", "Reward allocation is disabled until funding, sponsor, jurisdiction and payout terms are verified.", "No prize amount is computed or offered.", src("nfl_rg")],
        ["A-V14", "Source semantic mapping", "Every generated table row carries a registry source ID; the checker validates the ID/URL pair and publishes support scope.", "Live source-content drift is still a review flag.", src("nfl_terms")],
    ]
    body = '<div class="notice info"><strong>Scope.</strong> This page records the verified workbench’s own audit decisions. The independent cross-session audit is maintained separately and linked below.</div>'
    body += section("Workbench audit", "Irregularities and corrective decisions", table(["ID", "Issue", "Decision", "Effect", "Official source"], rows), f"{len(rows)} entries")
    body += '<p class="footnote">Independent audit: <a href="../audit/flagged.html">Flagged for review</a> · <a href="../audit/line-by-line.md">Line-by-line review</a> · <a href="../audit/data-rights-review.md">Data-rights review</a></p>'
    return page("audit.html", "Repo audit", "Audit decisions for the fail-closed workbench and links to the independent review.", body)


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "assets").mkdir(exist_ok=True)
    (OUT / "assets" / "style.css").write_text(CSS, encoding="utf-8")
    (OUT / "assets" / "app.js").write_text(JS, encoding="utf-8")
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    pages = {
        "index.html": page_index, "strategies.html": page_strategies, "lines.html": page_lines,
        "props.html": page_props, "parlays.html": page_parlays, "correlations.html": page_correlations,
        "validation.html": page_validation, "leaderboard.html": page_leaderboard, "sources.html": page_sources,
        "flagged.html": page_flagged, "requirements.html": page_requirements, "audit.html": page_audit,
    }
    for name, fn in pages.items():
        (OUT / name).write_text(fn(), encoding="utf-8")


if __name__ == "__main__":
    build()
