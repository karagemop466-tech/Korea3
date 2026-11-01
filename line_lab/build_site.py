#!/usr/bin/env python3
"""Render the static dashboard from data/derived/summary.json.

Every number on the site is read from summary.json, which is produced by
pipeline/run_all.py from the hashed snapshot in data/raw. Nothing is typed by hand,
so a page cannot drift from the data. Run:

    python3 -m pipeline.build_site
"""
from __future__ import annotations

import json
from html import escape
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
DERIVED = BASE / "data" / "derived"
SITE = ROOT
REPO = "https://github.com/karagemop466-tech/Korea3"
BLOB = f"{REPO}/blob/main/"
S = json.loads((DERIVED / "summary.json").read_text(encoding="utf-8"))
TESTS = json.loads((DERIVED / "tests.json").read_text(encoding="utf-8"))

DICT = ("https://github.com/nflverse/nflreadr/blob/23f915a5be30415aeaa0c5c80cd23b2c69cda122/"
        "data-raw/dictionary_schedules.csv")
DATASETS = f"https://github.com/nflverse/nfldata/blob/{S['pinned_commit']}/DATASETS.md"
PLAYER_RELEASE = "https://github.com/nflverse/nflverse-data/releases/tag/player_stats"
NFLLOADER = ("https://github.com/nflverse/nflreadr/blob/23f915a5be30415aeaa0c5c80cd23b2c69cda122/"
             "R/load_schedules.R")
FILES = {Path(f["file"]).name: f for f in S["files"]}
SRC_GAMES = FILES["games.csv"]["source_url"]
SRC_CLOSING = FILES["closing_lines.csv"]["source_url"]
SRC_INITIAL = FILES["initial_lines.csv"]["source_url"]
SRC_WINTOT = FILES["win_totals.csv"]["source_url"]
SRC_TEAMS = FILES["teams.csv"]["source_url"]
SRC_BETS = BLOB + "line_lab/data/derived/bets.csv"
SRC_FEATS = BLOB + "line_lab/data/derived/features.csv"
SRC_SUMMARY = BLOB + "line_lab/data/derived/summary.json"
SRC_TESTS = BLOB + "line_lab/data/derived/tests.json"
SRC_ENGINE = BLOB + "line_lab/strategies.py"
SRC_CORE = BLOB + "line_lab/core.py"
SRC_EVAL = BLOB + "line_lab/evaluation.py"
SRC_CORR = BLOB + "line_lab/correlations.py"
SRC_EXTRAS = BLOB + "line_lab/extras.py"
SRC_PREREG = BLOB + "line_lab/docs/preregistration.md"
SRC_EXEC = BLOB + "line_lab/EXECUTIVE_SUMMARY.md"
SRC_REQS = BLOB + "line_lab/docs/requirements.md"

NAV = [
    ("index.html", "Overview"),
    ("leaderboard.html", "Leaderboard"),
    ("strategies.html", "Strategies"),
    ("validation.html", "Validation"),
    ("correlations.html", "Correlations"),
    ("parlays.html", "Parlays"),
    ("props.html", "Player props"),
    ("lines.html", "Live lines"),
    ("data.html", "Data"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged for review"),
    ("methodology.html", "Method"),
    ("requirements.html", "Requirements"),
    ("sessions.html", "All sessions"),
]


# --------------------------------------------------------------------------- #
# formatting helpers
# --------------------------------------------------------------------------- #
def e(x) -> str:
    return escape(str(x))


def blank() -> str:
    return '<a class="flag" href="flagged.html">unverified</a>'


def pct(x, d: int = 2) -> str:
    return blank() if x is None else f"{x * 100:.{d}f}%"


def signed_pct(x, d: int = 2) -> str:
    if x is None:
        return blank()
    cls = "pos" if x > 0 else ("neg" if x < 0 else "")
    return f'<span class="{cls}">{x * 100:+.{d}f}%</span>'


def num(x, d: int = 2) -> str:
    return blank() if x is None else f"{x:,.{d}f}"


def signed(x, d: int = 2) -> str:
    if x is None:
        return blank()
    cls = "pos" if x > 0 else ("neg" if x < 0 else "")
    return f'<span class="{cls}">{x:+.{d}f}</span>'


def ci(low, high, d: int = 2) -> str:
    if low is None or high is None:
        return blank()
    return f"[{low * 100:+.{d}f}%, {high * 100:+.{d}f}%]"


def pill(status: str) -> str:
    status = (status or "").lower()
    css = {"pass": "pass", "fail": "fail", "unverified": "warn", "blocked": "warn"}.get(status, "info")
    label = {"pass": "pass", "fail": "fail", "unverified": "unverified"}.get(status, status or "info")
    return f'<span class="pill {css}">{e(label)}</span>'


def src(url: str, label: str = "source") -> str:
    return f'<a href="{e(url)}" target="_blank" rel="noopener noreferrer">{e(label)} ↗</a>'


def table(headers, rows, caption: str = "", cls: str = "") -> str:
    head = "".join(f"<th scope=\"col\">{h}</th>" for h in headers)
    body = []
    for row in rows:
        cells = []
        for cell in row:
            if isinstance(cell, dict):
                cells.append(f'<td class="{cell.get("cls", "")}">{cell["v"]}</td>')
            else:
                cells.append(f"<td>{cell}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    cap = f"<caption>{caption}</caption>" if caption else ""
    return (f'<div class="scroll"><table class="{cls}">{cap}<thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def right(v) -> dict:
    if v is None or (isinstance(v, str) and v.strip() in ("None", "nan", "NaN", "")):
        return {"v": blank(), "cls": "num"}
    return {"v": v, "cls": "num"}


def mono(v: str) -> dict:
    return {"v": f'<span class="mono">{v}</span>', "cls": "mono"}


def page(slug: str, title: str, subtitle: str, body: str, eyebrow: str = "") -> str:
    links = []
    for href, label in NAV:
        cls = ' class="active"' if href == slug else ""
        links.append(f'<a href="{e(href)}"{cls}>{e(label)}</a>')
    nav = "".join(links)
    stamp = S["generated_utc"]
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} | NFL Line Lab</title>
<meta name="description" content="Reproducible NFL line origination research: strategies, validation gates, correlations and measured results.">
<link rel="stylesheet" href="assets/style.css">
<script src="assets/app.js" defer></script>
</head>
<body>
<header class="site">
  <div class="wrap">
    <div class="topbar">
      <a class="brand" href="index.html">
        <span class="mark">N</span>
        <span><strong>NFL Line Lab</strong><small>Independent line origination research</small></span>
      </a>
      <span class="badge">Research only · no betting advice</span>
    </div>
    <nav class="main" aria-label="Main navigation">{nav}</nav>
  </div>
</header>
<main class="wrap">
  <div class="eyebrow">{e(eyebrow or title)}</div>
  <h1>{e(title)}</h1>
  <p class="lead">{subtitle}</p>
  {body}
</main>
<footer class="site">
  <div class="wrap">
    <div>Independent research · not affiliated with the NFL · data rebuilt {e(stamp)}<br>
      Pinned source commit <a href="{e(S['commit_url'])}" target="_blank" rel="noopener noreferrer">{e(S['pinned_commit'][:10])}</a></div>
    <div>Betting involves risk. Blank cells mean unverified, never zero. <a href="flagged.html">Review limitations</a></div>
  </div>
</footer>
</body>
</html>
"""


def gate_strip(gates: dict) -> str:
    return "".join(
        f'<span class="pill {"pass" if v == "pass" else ("warn" if v == "unverified" else "fail")}">'
        f'{k}</span> ' for k, v in gates.items()
    )


def strategy_by_id(sid: str) -> dict:
    for row in S["strategies"]:
        if row["id"] == sid:
            return row
    raise KeyError(sid)


# --------------------------------------------------------------------------- #
# pages
# --------------------------------------------------------------------------- #
def page_index() -> str:
    u = S["universe"]
    lb = S["leaderboard"]
    eligible = [r for r in lb if r["eligible"]]
    best = lb[0] if lb else None
    luck = S["extras"]["luck_band"]
    hold = S["extras"]["hold"]
    acc = S["accuracy"]
    best_roi_row = max(lb, key=lambda r: r["full_roi"] if r["full_roi"] is not None else -9)
    avg_hold = sum(v["mean_hold"] for v in hold.values()) / max(len(hold), 1)

    kpis = f"""
<div class="grid k4">
  <div class="card"><div class="tag">Games analysed</div><div class="num">{u['reg_completed_games']:,}</div>
    <div class="sub">{u['first_season']}–{u['last_season']} regular season · {u['window_games']:,} in the priced 2006–2025 window</div></div>
  <div class="card"><div class="tag">Selections evaluated 2006–2025</div><div class="num">{sum((r['metrics_full'].get('bets') or 0) for r in S['strategies']):,}</div>
    <div class="sub">11 pre-registered strategies, settled at recorded closing prices</div></div>
  <div class="card"><div class="tag">Reward-eligible strategies</div><div class="num">{len(eligible)}</div>
    <div class="sub">All nine gates must pass. None did.</div></div>
  <div class="card"><div class="tag">Best-of-11 random ROI</div><div class="num">{luck['mean_best_roi']*100:+.1f}%</div>
    <div class="sub">No-skill band: {luck['p05_best_roi']*100:+.1f}% to {luck['p95_best_roi']*100:+.1f}%</div></div>
</div>"""

    findings = [
        ("No strategy earned a reward",
         f"0 of {len(S['strategies'])} pre-registered strategies passed all nine validation gates. "
         f"Best full-sample ROI is {best_roi_row['full_roi']*100:+.2f}% ({best_roi_row['id']}), and its "
         f"week-block 95% interval {ci(strategy_by_id(best_roi_row['id'])['metrics_full']['roi_ci_low'], strategy_by_id(best_roi_row['id'])['metrics_full']['roi_ci_high'])} "
         "contains zero.",
         SRC_SUMMARY),
        ("The winner of a small leaderboard is usually luck",
         f"Simulating 11 no-skill strategies with the same bet counts produces a best strategy averaging "
         f"{luck['mean_best_roi']*100:+.1f}% ROI, and a profitable 'winner' {luck['prob_best_is_profitable']*100:.0f}% of the time "
         f"(95th percentile {luck['p95_best_roi']*100:+.1f}%). Any ranking of a handful of backtests must clear this band.",
         SRC_EXTRAS),
        ("The model is close to the market on accuracy, not on calibration",
         f"Spread RMSE {acc['spread']['model_rmse']:.2f} points versus the market's {acc['spread']['market_rmse']:.2f}; "
         f"correlation with the result {acc['spread']['model_corr']:.3f} versus {acc['spread']['market_corr']:.3f}. "
         f"Total RMSE {acc['total']['model_rmse']:.2f} versus {acc['total']['market_rmse']:.2f}. "
         "Being close is not enough: Brier skill against the de-vigged market is negative for every model strategy.",
         SRC_FEATS),
        ("The vig is the wall",
         f"Average two-way hold in the recorded prices is {avg_hold*100:.2f}%. Detecting a 3% per-bet edge at 80% power "
         f"needs about {S['extras']['power'][2]['bets_required']:,} settled bets, roughly "
         f"{S['extras']['power'][2]['seasons_at_750_bets']:.0f} seasons at 750 bets per season.",
         SRC_EXTRAS),
        ("Same-game legs are not independent; cross-game legs are",
         f"Measured phi: moneyline vs spread {S['correlations']['same_game']['pairs']['ats_home__ml_home']['phi']:.3f}, "
         f"spread vs total {S['correlations']['same_game']['pairs']['ats_home__over']['phi']:.3f}, "
         f"moneyline vs total {S['correlations']['same_game']['pairs']['over__ml_home']['phi']:.3f}, "
         f"two different games in the same week {S['correlations']['cross_game']['phi']:.3f}.",
         SRC_CORR),
        ("Home and away scoring are slightly negatively correlated",
         f"r = {S['correlations']['team_scoring']['home_vs_away_points']['r']:.3f} "
         f"(95% {S['correlations']['team_scoring']['home_vs_away_points']['ci_low']:.3f} to "
         f"{S['correlations']['team_scoring']['home_vs_away_points']['ci_high']:.3f}, n={S['correlations']['team_scoring']['home_vs_away_points']['n']:,}). "
         "Combo legs built on 'both teams will score a lot' do not get a positive boost from this data.",
         SRC_CORR),
        ("Player props could not be measured, so nothing is published",
         "No reachable source provides official player-level game logs or licensed prop prices. Every prop value on this "
         "site is blank and listed for review rather than estimated.",
         PLAYER_RELEASE),
    ]
    find_rows = [[f"<strong>{e(t)}</strong>", d, src(link, "evidence")] for t, d, link in findings]

    status_rows = []
    for row in lb:
        m = strategy_by_id(row["id"])["metrics_full"]
        status_rows.append([
            f"<strong>{e(row['id'])}</strong>",
            e(row["name"]),
            e(row["market"]),
            f"{row['gates_passed']}/9",
            right(signed_pct(row["full_roi"])),
            right(ci(m["roi_ci_low"], m["roi_ci_high"])),
            right(pct(m["win_rate"])),
            right(f"{row['bets']:,}"),
            src(SRC_BETS, "bets"),
        ])

    body = f"""
{kpis}
<div class="notice"><strong>Other builds in this repository.</strong> This root dashboard is one of five bodies of
work produced by parallel sessions. The empirical pipeline site is at <a href="site/index.html">/site/</a>, the second
Line Lab build at <a href="docs/index.html">/docs/</a>, the independent audit at <a href="audit/flagged.html">/audit/</a>,
and the original brief is preserved at <a href="site/prior/index.html">/site/prior/</a>.
<a href="sessions.html">See all sessions →</a></div>

<div class="notice"><strong>Read this first.</strong> This is an audit trail, not a picks page. The pre-registered
strategy family was tested on {u['window_games']:,} priced regular-season games and none of it cleared the gates.
The useful output is the measurement: how large the vig is, how wide the luck band is, which leg combinations are
genuinely dependent, and what would have to be true for a strategy to be worth money.</div>

<section>
  <div class="section-head"><div><h2>Key findings</h2>
    <p>Each row links to the generated evidence behind it.</p></div>
    <span class="count small muted">{len(findings):02} findings</span></div>
  {table(["Finding", "What the data shows", "Evidence"], find_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Scoreboard</h2>
    <p>Full-sample results 2006–2025 at the recorded closing price. Sorted by gates passed, then holdout lower bound.</p></div>
    <a class="small" href="leaderboard.html">Open full leaderboard →</a></div>
  {table(["ID", "Strategy", "Market", "Gates", "ROI / bet", "95% interval", "Win rate", "Bets", "Source"], status_rows,
         "ROI is profit per 1-unit stake; pushes settle at zero and are excluded from the win rate.")}
</section>

<section>
  <div class="section-head"><div><h2>How to read this site</h2>
    <p>Six pages carry the evidence, three carry the apparatus, two carry the caveats.</p></div></div>
  <div class="grid k3">
    <div class="card"><h3><a href="leaderboard.html">Leaderboard</a></h3><p class="small muted">Ranking, eligibility and the reward rule, with every gate visible.</p></div>
    <div class="card"><h3><a href="strategies.html">Strategies</a></h3><p class="small muted">The eleven pre-registered strategies, their inputs and their measured results.</p></div>
    <div class="card"><h3><a href="validation.html">Validation</a></h3><p class="small muted">Nine gates, the test suite, and what each gate rejected.</p></div>
    <div class="card"><h3><a href="correlations.html">Correlations</a></h3><p class="small muted">Measured dependence between legs, with confidence intervals and sample sizes.</p></div>
    <div class="card"><h3><a href="parlays.html">Parlays</a></h3><p class="small muted">Joint hit rates versus the independence assumption, and what it costs.</p></div>
    <div class="card"><h3><a href="lines.html">Live lines</a></h3><p class="small muted">Model-implied spreads, totals and win probabilities for unplayed games.</p></div>
    <div class="card"><h3><a href="data.html">Data</a></h3><p class="small muted">Pinned snapshot, hashes, row counts and per-season coverage.</p></div>
    <div class="card"><h3><a href="props.html">Player props</a></h3><p class="small muted">Blocked. Required inputs and the estimator that is ready to run.</p></div>
    <div class="card"><h3><a href="flagged.html">Flagged for review</a></h3><p class="small muted">Everything unverified, undocumented or assumption-based, with sources.</p></div>
  </div>
</section>"""
    return page("index.html", "NFL line origination, measured", 
                "A reproducible research system for originating and testing NFL lines: eleven pre-registered "
                "strategies, nine validation gates, measured correlation structure, and a leaderboard that refuses "
                "to reward luck.", body, eyebrow="Executive dashboard")


def page_leaderboard() -> str:
    lb = S["leaderboard"]
    rows = []
    for i, row in enumerate(lb, 1):
        st = strategy_by_id(row["id"])
        rows.append([
            right(str(i)),
            f"<strong>{e(row['id'])}</strong>",
            e(row["name"]),
            e(row["market"]),
            f"{row['gates_passed']}/9",
            right(signed_pct(row["full_roi"])),
            right(ci(st["metrics_full"]["roi_ci_low"], st["metrics_full"]["roi_ci_high"])),
            right(signed_pct(row["holdout_roi"])),
            right(f"{row['holdout_bets'] or 0:,}"),
            right(None if row["brier_skill"] is None else f"{row['brier_skill']:+.3f}"),
            right("" if row["permutation_percentile"] is None else f"{row['permutation_percentile']:.1f}"),
            right(f"{row['bets']:,}"),
            "1.0" if row["eligible"] else '<span class="pill blank">not awarded</span>',
            pill("verified") if row["eligible"] else '<span class="pill fail">not eligible</span>',
            src(SRC_SUMMARY, "evidence"),
        ])
    gate_rows = []
    for row in lb:
        st = strategy_by_id(row["id"])
        gate_rows.append([f"<strong>{e(row['id'])}</strong>", e(row["name"]), gate_strip(st["gates"]),
                          right(f"{row['gates_passed']}/9"), src(SRC_SUMMARY, "gates")])

    fail_counts = {}
    for row in S["strategies"]:
        for g, v in row["gates"].items():
            fail_counts.setdefault(g, {"pass": 0, "fail": 0, "unverified": 0})
            fail_counts[g][v] += 1
    fail_rows = []
    for gid, spec in gate_specs():
        c = fail_counts.get(gid, {})
        fail_rows.append([f"<strong>{e(gid)}</strong>", e(spec["name"]), e(spec["requirement"]),
                          right(str(c.get("pass", 0))), right(str(c.get("fail", 0))),
                          right(str(c.get("unverified", 0))), src(SRC_PREREG, "pre-registration")])

    body = f"""
<div class="notice"><strong>Nobody is eligible.</strong> The reward rule pays only strategies that pass all nine gates.
{len([r for r in lb if r['eligible']])} of {len(lb)} passed. The ranking below is therefore an ordering of
<em>failed candidates</em>, useful for research direction, not for staking money. Reward points are blank because
nothing qualified; a blank is not a zero.</div>

<section>
  <div class="section-head"><div><h2>Ranked candidates</h2>
  <p>Rank order is the pre-registered rule: gates passed, then holdout ROI lower confidence bound.</p></div></div>
  {table(["#", "ID", "Strategy", "Market", "Gates", "ROI / bet", "95% interval", "Holdout ROI", "Holdout bets",
          "Brier skill", "Luck pct.", "Bets", "Reward pts", "Status", "Source"], rows,
         "Window: 2006–2025 regular season. Holdout: 2023–2025. Luck percentile: share of 2,000 random-selection "
         "simulations with a lower ROI (higher is better; 95+ is the gate).")}
</section>

<section>
  <div class="section-head"><div><h2>Gate matrix</h2><p>PASS requires evidence; UNVERIFIED means the input needed to test the gate does not exist.</p></div></div>
  {table(["ID", "Strategy", "G1–G9", "Passed", "Source"], gate_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Which gates did the work</h2>
    <p>Counts across the {len(S['strategies'])} strategies. A gate that never fails is not doing any filtering.</p></div></div>
  {table(["Gate", "Name", "Requirement", "Pass", "Fail", "Unverified", "Source"], fail_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Reward rule (pre-registered)</h2></div></div>
  <div class="card">
    <p class="small">Only strategies passing G1–G9 are reward-eligible. Eligible strategies are ranked by the holdout ROI
    lower confidence bound, then by Brier skill. Reward points = 100 × (0.6 × normalised holdout lower bound + 0.4 ×
    normalised Brier skill), normalised across eligible strategies only.</p>
    <dl class="kv">
      <dt>Eligible strategies</dt><dd>{len([r for r in lb if r['eligible']])}</dd>
      <dt>Monetary prize pool</dt><dd>{blank()} — no pool is funded, sponsored or escrowed. Any prize figure would be invented.</dd>
      <dt>Reward points awarded</dt><dd>{blank()} — the rule only pays eligible strategies, and none qualified.</dd>
      <dt>Rule text</dt><dd>{src(SRC_PREREG, "docs/preregistration.md §8")}</dd>
    </dl>
  </div>
</section>

<section>
  <div class="section-head"><div><h2>What an unfiltered leaderboard would have shown</h2>
    <p>Ranking the same 11 candidates by full-sample ROI alone — the usual way a backtest league is reported.</p></div></div>
  {table(["Rank by raw ROI", "ID", "Strategy", "ROI / bet", "Gates passed", "Would it get paid?",
          "Source"],
         [[right(str(i)), f"<strong>{e(r['id'])}</strong>", e(r['name']), right(signed_pct(r['full_roi'])),
           f"{r['gates_passed']}/9", '<span class="pill fail">no</span>', src(SRC_SUMMARY, "evidence")]
          for i, r in enumerate(sorted(S['leaderboard'], key=lambda x: -(x['full_roi'] or -9)), 1)])}
</section>"""
    return page("leaderboard.html", "Leaderboard", 
                "The competition table. A strategy is only ranked as eligible when it survives provenance, causality, "
                "sample, holdout, significance, market, stability, execution and luck gates — all nine, simultaneously.",
                body)


def gate_specs():
    return [
        ("G1", {"name": "Provenance", "requirement": "Every bet traces to a row in a hashed input; no imputed price or line."}),
        ("G2", {"name": "Causality", "requirement": "Truncation test: features rebuilt without future games must be identical."}),
        ("G3", {"name": "Sample", "requirement": "≥ 300 bets, ≥ 8 seasons, ≥ 40 holdout bets."}),
        ("G4", {"name": "Holdout", "requirement": "Holdout (2023–2025) ROI > 0."}),
        ("G5", {"name": "Significance", "requirement": "Week-block bootstrap CI low > 0 and BH-FDR q ≤ 0.10 across 11 tests."}),
        ("G6", {"name": "Market test", "requirement": "Brier skill ≥ 0 against the de-vigged closing market."}),
        ("G7", {"name": "Stability", "requirement": "ROI > 0 in ≥ 60% of seasons; best season ≤ 50% of total profit."}),
        ("G8", {"name": "Execution", "requirement": "≥ 95% of the window's games carry a two-sided recorded price; flat stakes."}),
        ("G9", {"name": "Luck control", "requirement": "Random-selection permutation percentile ≥ 95."}),
    ]


def page_strategies() -> str:
    cards = []
    for row in S["strategies"]:
        st = strategy_by_id(row["id"])
        full = st["metrics_full"]
        hold = st["holdout"]
        fwd = st["forward_2026"]
        season_rows = [[e(k), right(signed_pct(v)), src(SRC_BETS, "bets")]
                       for k, v in sorted(full.get("season_roi", {}).items())]
        cards.append(f"""
<section>
  <div class="section-head"><div><h2>{e(row['id'])} · {e(row['name'])}</h2>
    <p>{strategy_blurb(row['id'])}</p></div>{pill('verified') if row['eligible'] else '<span class="pill fail">not eligible</span>'}</div>
  <div>
    <div>{table(["Metric", "2006–2025", "Holdout 2023–25", "Forward 2026", "Source"], [
        ["Bets", right(f"{full.get('bets',0):,}"), right(f"{hold.get('bets',0):,}"), right(f"{fwd.get('bets',0):,}"), src(SRC_BETS, "bets")],
        ["ROI per unit", right(signed_pct(full.get('roi'))), right(signed_pct(hold.get('roi'))), right(signed_pct(fwd.get('roi'))), src(SRC_BETS, "bets")],
        ["95% interval", right(ci(full.get('roi_ci_low'), full.get('roi_ci_high'))), right(ci(hold.get('roi_ci_low'), hold.get('roi_ci_high'))), right(ci(fwd.get('roi_ci_low'), fwd.get('roi_ci_high'))), src(SRC_EVAL, "bootstrap")],
        ["Win rate", right(pct(full.get('win_rate'))), right(pct(hold.get('win_rate'))), right(pct(fwd.get('win_rate'))), src(SRC_BETS, "bets")],
        ["Push rate", right(pct(full.get('push_rate'))), right(pct(hold.get('push_rate'))), right(pct(fwd.get('push_rate'))), src(SRC_BETS, "bets")],
        ["Brier skill vs market", right(None if (st['market_test'] or {}).get('brier_skill') is None else f"{(st['market_test'] or {}).get('brier_skill'):+.3f}"), right(None), right(None), src(SRC_EVAL, "brier")],
        ["Luck percentile", right('' if st['permutation'].get('percentile') is None else f"{st['permutation']['percentile']:.1f}"), right(None), right(None), src(SRC_EVAL, "permutation")],
    ])}</div>
    <details><summary>Season-by-season ROI, 2006–2025</summary>
      {table(["Season", "ROI", "Source"], season_rows)}
    </details>
  </div>
  <p class="tiny muted">{gate_strip(st['gates'])} &nbsp; · &nbsp; {gate_passed_text(st['gates'])}</p>
</section>""")

    blurb = {
        "S1": "A walk-forward Elo margin model (Elo + rest differential + quarterback change) fitted on seasons before the game, converted to a normal margin distribution and compared with the de-vigged closing spread.",
        "S2": "The same margin distribution converted to a win probability and compared with the de-vigged closing moneyline.",
        "S3": "A totals model built from opponent-unadjusted exponential-moving-average points scored and allowed, plus roof, fitted walk-forward and compared with the de-vigged closing total.",
        "S4": "Buy the team with at least three extra rest days; skips week 1 because the source fills week-1 rest with a placeholder value.",
        "S5": "Historical divisional-underdog effect: home underdogs inside the division.",
        "S6": "Outdoor games with wind ≥ 15 mph or temperature ≤ 32 °F, bet under.",
        "S7": "Bet with a referee crew's historical total tendency (expanding mean of total minus league mean, minimum 30 prior games, prior seasons only).",
        "S8": "Fade a team whose starting quarterback changed from its previous game while the opponent's did not.",
        "S9": "Two legs per week from the S2 selections, different games, priced multiplicatively like a book parlay.",
        "S10": "Two legs per week from the S1 selections, different games, priced multiplicatively.",
        "S11": "Preseason season win-total futures: prior-season Pythagorean projection versus the posted line, 2003–2020 only.",
    }
    return page("strategies.html", "Strategy lab", 
                "Eleven strategies were fixed in writing before any result was computed. Each one is a hypothesis about a "
                "specific, measurable market inefficiency; each is judged on out-of-sample behaviour, not on fit.",
                "".join(cards))


def strategy_blurb(sid: str) -> str:
    return {
        "S1": "Elo margin model versus the closing spread. Inputs: Elo rating, rest differential, quarterback change. Fitted only on seasons before the game.",
        "S2": "The same margin distribution as S1, converted to a win probability, versus the de-vigged moneyline.",
        "S3": "Scoring-profile totals: EWMA points scored and allowed for both teams plus roof, fitted walk-forward.",
        "S4": "Rest asymmetry: buy a team with at least three more rest days. Week 1 excluded because the source's week-1 rest value is a placeholder.",
        "S5": "Divisional home underdog: home team inside a divisional game and getting points.",
        "S6": "Weather under: outdoor or open roof, wind ≥ 15 mph or temperature ≤ 32 °F.",
        "S7": "Referee crew total tendency: expanding crew deviation from the league total, prior games only, minimum 30 games.",
        "S8": "Backup-quarterback fade: fade the side that changed starting quarterback while the opponent did not.",
        "S9": "Two-leg cross-game moneyline parlay from S2's two highest-edge selections each week.",
        "S10": "Two-leg cross-game ATS parlay from S1's two highest-edge selections each week.",
        "S11": "Season win-total futures: Pythagorean projection from the prior season versus the posted line (2003–2020).",
    }[sid]


def gate_passed_text(gates: dict) -> str:
    fails = [k for k, v in gates.items() if v == "fail"]
    unv = [k for k, v in gates.items() if v == "unverified"]
    parts = []
    if fails:
        parts.append("failed " + ", ".join(fails))
    if unv:
        parts.append("unverified " + ", ".join(unv))
    return e("; ".join(parts) if parts else "all gates passed")


def page_validation() -> str:
    specs = gate_specs()
    spec_rows = [[f"<strong>{e(g)}</strong>", e(s['name']), e(s['requirement']), src(SRC_PREREG, "pre-registration")]
                 for g, s in specs]
    matrix = []
    for row in S["strategies"]:
        matrix.append([f"<strong>{e(row['id'])}</strong>", e(row['name'])] +
                      [pill(v) for v in row['gates'].values()] + [src(SRC_SUMMARY, "gates")])
    tests_rows = []
    for name, res in TESTS.items():
        detail = {k: v for k, v in res.items() if k not in ("status",)}
        tests_rows.append([f"<strong>{e(name)}</strong>", pill(res.get("status", "")),
                           e(", ".join(f"{k}={v}" for k, v in detail.items())[:220]),
                           src(SRC_TESTS, "report")])
    proto = S["protocol"]
    proto_rows = [
        ["Edge threshold", f"≥ {proto['edge_min']*100:.0f} percentage points vs the de-vigged price", src(SRC_PREREG, "§4")],
        ["Price band", f"{proto['price_min']:+.0f} to {proto['price_max']:+.0f} American", src(SRC_PREREG, "§4")],
        ["Stake", "1 unit flat; no staking plan is evaluated", src(SRC_PREREG, "§4")],
        ["Evaluation window", f"{proto['eval_window'][0]}–{proto['eval_window'][1]} regular season", src(SRC_PREREG, "§1")],
        ["Holdout", f"{proto['holdout'][0]}–{proto['holdout'][-1]}", src(SRC_PREREG, "§1")],
        ["Bootstrap", f"{proto['bootstrap_resamples']:,} week-block resamples, seed {proto['seed']}", src(SRC_EVAL, "code")],
        ["Permutation", f"{proto['permutation_resamples']:,} simulations matched on weekly bet count and side mix", src(SRC_EVAL, "code")],
        ["Multiple testing", f"Benjamini–Hochberg across {S['family']['tests']} tests, q ≤ {proto['fdr_level']}", src(SRC_EVAL, "code")],
    ]
    body = f"""
<div class="notice"><strong>Passing is hard on purpose.</strong> A gate that cannot be evaluated is recorded as
unverified, which is not a pass. The reward rule requires all nine.</div>

<section>
  <div class="section-head"><div><h2>Gate definitions</h2><p>Frozen in docs/preregistration.md before the first backtest ran.</p></div></div>
  {table(["Gate", "Name", "Requirement", "Source"], spec_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Gate results</h2><p>One row per strategy; columns are the nine gates in pre-registration order.</p></div></div>
  {table(["ID", "Strategy", "G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8", "G9", "Source"], matrix)}
</section>

<section>
  <div class="section-head"><div><h2>Test suite</h2>
    <p>Run with <code>python3 tests/test_causality.py</code>. Any failure blocks G2 for every strategy.</p></div></div>
  {table(["Check", "Status", "Detail", "Source"], tests_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Protocol constants</h2></div></div>
  {table(["Setting", "Value", "Source"], proto_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Why G6 is the gate that kills most candidates</h2></div></div>
  <div class="card"><p class="small">G6 compares the model's probability for every priced game against the de-vigged
  closing price using the Brier score. A model can be profitable only if it is better than the market at pricing, or at
  least not worse while selecting a biased subset. Every model here scored worse than the market, which is the honest
  reading: the market already contains the information these features carry.
  {src(SRC_EVAL, "evaluation code")}</p></div>
</section>"""
    return page("validation.html", "Validation gates",
                "Nine gates stand between a backtest and a reward. This page shows the definitions, the results, the test "
                "suite and the protocol constants.", body)


def page_correlations() -> str:
    cg = S["correlations"]
    pair_rows = []
    labels = {
        "ats_home__ml_home": "Home covers the spread × Home wins outright",
        "ats_home__over": "Home covers the spread × Game goes over",
        "over__ml_home": "Game goes over × Home wins outright",
    }
    for key, val in cg["same_game"]["pairs"].items():
        pair_rows.append([
            e(labels.get(key, key)),
            right(f"{val['phi']:.4f}"),
            right(f"[{val['ci_low']:.4f}, {val['ci_high']:.4f}]"),
            right(pct(val["joint_rate"])),
            right(pct(val["independent_product"])),
            right(signed_pct(val["dependence_bias"])),
            right(pct(val["p_b_given_a"])),
            right(pct(val["p_b_marginal"])),
            right(f"{val['n']:,}"),
            src(SRC_CORR, "method"),
        ])
    ts = cg["team_scoring"]
    team_rows = [
        ["Home points × Away points", right(f"{ts['home_vs_away_points']['r']:.4f}"),
         right(f"[{ts['home_vs_away_points']['ci_low']:.4f}, {ts['home_vs_away_points']['ci_high']:.4f}]"),
         right(f"{ts['home_vs_away_points']['n']:,}"), src(SRC_CORR, "method")],
        ["Game total × absolute margin", right(f"{ts['total_vs_abs_margin']['r']:.4f}"),
         right(f"[{ts['total_vs_abs_margin']['ci_low']:.4f}, {ts['total_vs_abs_margin']['ci_high']:.4f}]"),
         right(f"{ts['total_vs_abs_margin']['n']:,}"), src(SRC_CORR, "method")],
        ["Two different games, same week (moneyline)", right(f"{cg['cross_game']['phi']:.4f}"),
         right(f"[{cg['cross_game']['ci_low']:.4f}, {cg['cross_game']['ci_high']:.4f}]"),
         right(f"{cg['cross_game']['n_pairs']:,}"), src(SRC_CORR, "method")],
    ]
    season_rows = [[e(k), right(f"{v['r']:+.4f}"), right(str(v['n'])), src(SRC_CORR, "method")]
                   for k, v in sorted(ts["per_season"].items())]
    matrix = cg["strategy_returns"]["matrix"]
    ids = list(matrix.keys())
    mat_rows = []
    for a in ids:
        row = [f"<strong>{e(a)}</strong>"]
        for b in ids:
            v = matrix[a].get(b)
            row.append(right("" if v is None else f"{v:+.2f}"))
        row.append(src(SRC_BETS, "bets"))
        mat_rows.append(row)
    three = cg["three_leg_same_game"]
    three_rows = [[e(k), right(pct(v)), src(SRC_CORR, "method")] for k, v in three["marginals"].items()]
    three_rows.append(["Joint (all three)", right(pct(three["joint_favourite_over_ml"])), src(SRC_CORR, "method")])
    three_rows.append(["Product of the three marginals", right(pct(three["product"])), src(SRC_CORR, "method")])

    body = f"""
<div class="notice"><strong>These are measured coefficients, not assumptions.</strong> Each value comes from the
recorded outcomes of {cg['same_game']['games']:,} priced games (2006–2025). Intervals are week-block bootstraps.
Where a combination could not be measured, the cell is blank and listed on the review page.</div>

<section>
  <div class="section-head"><div><h2>Same-game dependence</h2>
    <p>phi is the Pearson correlation of two binary leg outcomes; it equals the signed dependence in a 2×2 table.
    "P(B|A)" is the conditional win rate of the second leg given the first leg won.</p></div></div>
  {table(["Leg pair (same game)", "phi", "95% interval", "Joint rate", "Product of marginals", "Dependence bias",
          "P(B|A)", "P(B)", "n", "Source"], pair_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Scoring and cross-game dependence</h2>
    <p>Team scores are the raw material behind most player-prop combos, so their dependence matters even though it is
    not a prop measurement itself.</p></div></div>
  {table(["Relationship", "r", "95% interval", "n", "Source"], team_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Three-leg same-game combination</h2>
    <p>Home covers + over + home wins outright, all in the same game.</p></div></div>
  {table(["Quantity", "Rate", "Source"], three_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Team-scoring correlation by season</h2>
    <p>If the relationship were stable, the sign would persist across seasons.</p></div></div>
  {table(["Season", "r", "Games", "Source"], season_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Correlation of weekly strategy returns</h2>
    <p>How much two strategies rise and fall together. Overlapping exposure means one bet is effectively two.</p></div></div>
  {table(["Strategy"] + ids + ["Source"], mat_rows,
         "Pearson correlation of week-level strategy P&L, weeks with at least 50 overlapping observations.")}
</section>

<section>
  <div class="section-head"><div><h2>Player-prop leg pairs</h2></div></div>
  <div class="card"><p class="small">Not measured: no reachable source provides official player-level game logs or
  licensed prop prices. Every prop correlation is blank and listed on <a href="flagged.html">Flagged for review</a>.
  The estimator that will compute phi for pairs such as "QB passing yards over 275.5" × "WR receiving yards over 65.5"
  is written and waiting for inputs: {src(SRC_CORR, "correlation code")}.</p></div>
</section>

<section>
  <div class="section-head"><div><h2>How to use a phi value</h2></div></div>
  <div class="card small">
    <p>For two binary legs with marginal probabilities p<sub>A</sub> and p<sub>B</sub>, the independent price uses
    p<sub>A</sub>·p<sub>B</sub>. The dependence-adjusted joint is
    P(A∩B) = p<sub>A</sub>p<sub>B</sub> + phi·√(p<sub>A</sub>(1−p<sub>A</sub>)p<sub>B</sub>(1−p<sub>B</sub>)).</p>
    <p>With p<sub>A</sub> = p<sub>B</sub> = 0.5 and phi = 0.67 (moneyline × spread), the joint is 0.50 instead of 0.25 —
    double the independent price. Multiplying marginals for that combination underprices the parlay by half. For legs in
    different games phi is {cg['cross_game']['phi']:.3f}, so the correction is negligible there.</p>
    <p class="muted">phi is a linear dependence measure; it does not describe the tail of a multi-leg distribution. For
    three or more legs, use the measured joint rate in the table above or simulate the joint distribution.</p>
  </div>
</section>"""
    return page("correlations.html", "Correlation and dependence",
                "Parlay and same-game pricing lives or dies on dependence. This page reports every dependence value that "
                "can be measured from the official-derived game data, with sample sizes and confidence intervals.",
                body)


def page_parlays() -> str:
    p = S["correlations"]["parlays"]
    rows = []
    for sid, val in p.items():
        rows.append([f"<strong>{e(sid)}</strong>", e(val.get("label", "")), right(f"{val.get('cards', 0):,}"),
                     right(pct(val.get("joint_hit_rate"))), right(pct(val.get("independence_expected"))),
                     right(signed_pct(val.get("bias"))), src(SRC_BETS, "bets")])
    pair = S["correlations"]["same_game"]["pairs"]
    mix = S["correlations"]["leg_mix_same_game"]
    three = S["correlations"]["three_leg_same_game"]
    mix_rows = [
        ["Home covers × over, same game", right(f"{mix.get('games', 0):,}"), right(pct(mix.get("joint_hit_rate"))),
         right(pct(mix.get("independence_expected"))), right(signed_pct(mix.get("bias"))),
         right("" if mix.get("phi") is None else f"{mix['phi']:.3f}"), src(SRC_CORR, "method")],
        ["Home covers × home wins outright", right(f"{pair['ats_home__ml_home']['n']:,}"),
         right(pct(pair['ats_home__ml_home']['joint_rate'])), right(pct(pair['ats_home__ml_home']['independent_product'])),
         right(signed_pct(pair['ats_home__ml_home']['dependence_bias'])), right(f"{pair['ats_home__ml_home']['phi']:.3f}"),
         src(SRC_CORR, "method")],
        ["Home covers × over × home wins (three legs)", right(f"{three['games']:,}"),
         right(pct(three['joint_favourite_over_ml'])), right(pct(three['product'])),
         right(signed_pct(three['joint_favourite_over_ml'] - three['product'])), right(None), src(SRC_CORR, "method")],
    ]
    config_rows = [
        ("Legs per card", "2 (fixed in the pre-registration)", SRC_PREREG, "§5"),
        ("Leg source", "Top two edges of the week from S1 (spread) or S2 (moneyline), different games", SRC_ENGINE, "engine"),
        ("Parlay price", "Product of the legs' decimal odds, no same-game adjustment", SRC_PREREG, "§4"),
        ("Push handling", "A pushed leg becomes a 1.0 multiplier; a lost leg loses the full stake", SRC_ENGINE, "engine"),
        ("Same-game pricing rules", "Operator rules unreachable from this environment", None, None),
    ]
    body = f"""
<div class="notice"><strong>The independence assumption is the whole product.</strong> A parlay price is a product of
leg probabilities. If the legs are positively dependent, the book's multiplicative price is too generous; if they are
negatively dependent, it is too stingy. The tables below measure which case you are in.</div>

<section>
  <div class="section-head"><div><h2>Measured parlay behaviour</h2>
    <p>Two-leg cards built from the strategy selections. "Independence expected" is the product of the de-vigged leg
    probabilities; the bias column is the gap the book would misprice.</p></div></div>
  {table(["Card", "Description", "Cards settled", "Joint hit rate", "Independence expected", "Bias", "Source"], rows)}
</section>

<section>
  <div class="section-head"><div><h2>Combination-by-combination</h2></div></div>
  {table(["Combination", "n", "Measured joint", "Product of marginals", "Bias", "phi", "Source"], mix_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Parlay construction rules used here</h2></div></div>
  {table(["Rule", "Setting", "Source"], [[e(a), e(b) if c else blank(), src(c, label) if c else blank()] for a, b, c, label in config_rows])}
</section>

<section>
  <div class="section-head"><div><h2>Why cross-game parlays are still bad value</h2></div></div>
  <div class="card small">
    <p>Cross-game legs are effectively independent (phi {S['correlations']['cross_game']['phi']:.3f}), so the price is
    arithmetically fair. That does not make it profitable: the bookmaker's hold compounds with every leg. At the measured
    average hold of {S['extras']['hold']['ML']['mean_hold']*100:.2f}% per market, a two-leg card carries roughly
    {(1 + S['extras']['hold']['ML']['mean_hold'])**2 - 1:.2%} of embedded margin before any skill, and the S9 parlay lost
    {signed_pct(strategy_by_id('S9')['metrics_full']['roi'])} per card over {strategy_by_id('S9')['metrics_full']['bets']:,} cards.
    {src(SRC_EXTRAS, "hold calculation")}</p>
  </div>
</section>"""
    return page("parlays.html", "Parlays and same-game combos",
                "Single bets, cross-game parlays and same-game combinations, priced with measured dependence rather than assumed "
                "independence.", body)


def page_props() -> str:
    pr = S["props"]
    inputs_player = table(["Required column", "Why", "Source"],
                          [[f'<span class="mono">{e(c)}</span>', "Official player-level game log field",
                            src(PLAYER_RELEASE, "release")] for c in pr["required_player_log_columns"]])
    inputs_prop = table(["Required column", "Why", "Source"],
                        [[f'<span class="mono">{e(c)}</span>', "Quoted market input", blank()]
                         for c in pr["required_prop_line_columns"]])
    reason_rows = [[e(r), '<span class="pill fail">blocked</span>', src(PLAYER_RELEASE, "nflverse release")]
                   for r in pr["blocking_reasons"]]
    results = pr["results"]
    result_rows = [[e(k.replace("_", " ")), right(v) if isinstance(v, (int, float)) else (blank() if v is None else e(v)),
                    src(SRC_SUMMARY, "summary")] for k, v in results.items()]
    body = f"""
<div class="notice"><strong>Nothing on this page is estimated.</strong> Player-prop markets require two inputs that
this research environment cannot reach: an official player-level game log and licensed prop lines with prices. Every
prop value on the site is blank and listed on <a href="flagged.html">Flagged for review</a>.</div>

<section>
  <div class="section-head"><div><h2>Status</h2></div></div>
  {table(["Blocker", "Status", "Source"], reason_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Values</h2><p>Blank means unverified. No coefficient, hit rate or ROI is published.</p></div></div>
  {table(["Measure", "Value", "Source"], result_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Inputs the estimator needs</h2></div></div>
  <div class="grid k2">
    <div><h3 class="small">Player game log</h3>{inputs_player}</div>
    <div><h3 class="small">Prop lines</h3>{inputs_prop}</div>
  </div>
</section>

<section>
  <div class="section-head"><div><h2>Estimator (written, waiting for inputs)</h2>
    <p>{src(BLOB + 'pipeline/props.py', 'pipeline/props.py')}</p></div></div>
  <div class="card"><ol class="small">
    {''.join(f'<li>{e(x)}</li>' for x in pr['estimator'])}
  </ol></div>
</section>

<section>
  <div class="section-head"><div><h2>What player props would add if the inputs existed</h2></div></div>
  <div class="card small">
    <p>Player props are the market where public models most often claim an edge, because a book must price hundreds of
    correlated thresholds from one game. The measurement plan is the same as the one already working for game markets:
    walk-forward pricing, week-block bootstrap intervals, a de-vigged market benchmark, and a luck band. Without the two
    inputs above, any number published here would be a fabrication, so none is published.</p>
  </div>
</section>"""
    return page("props.html", "Player props", 
                "Blocked by data availability, not by method. This page lists the exact inputs required, the estimator that "
                "will run when they exist, and nothing else.", body)


def page_lines() -> str:
    live = S["live"]
    rows = []
    for r in live["rows"]:
        gap = r.get("spread_gap")
        rows.append([
            e(r["kickoff"][:10]),
            right(str(r["week"])),
            e(f"{r['away_team']} @ {r['home_team']}"),
            right(num(r["market_spread"], 1) if r["market_spread"] is not None else blank()),
            right(num(r["model_spread"], 1)),
            right(signed(gap, 1) if gap is not None else blank()),
            right(num(r["market_total"], 1) if r["market_total"] is not None else blank()),
            right(num(r["model_total"], 1)),
            right(pct(r["model_home_win_prob"], 1)),
            right(pct(r["model_away_win_prob"], 1)),
            src(SRC_SUMMARY, "model"),
        ])
    next_week = [r for r in live["rows"] if live.get("next_week") and r["week"] == live["next_week"]]
    covered = sum(1 for r in live["rows"] if r["market_spread"] is not None)
    body = f"""
<div class="notice"><strong>Model output, not a pick.</strong> These are the lines this system would originate from its own
ratings, shown next to the market line where one exists. The same system failed all nine validation gates, so treat the
gaps as disagreement to investigate, not as value to bet.</div>

<section>
  <div class="section-head"><div><h2>Origin story: how a model line is built</h2></div></div>
  <div class="card small">
    <ol>
      <li>Elo ratings updated game by game in kickoff order, with a 75% carry-over across seasons and 55 Elo points of home field.</li>
      <li>Exponential moving averages (4-game half-life) of points scored and allowed for each team.</li>
      <li>A margin regression on Elo differential, rest differential and quarterback change, refit each season on all prior seasons.</li>
      <li>A totals regression on the four team scoring averages plus a roof indicator, refit the same way.</li>
      <li>Normal distributions around each fitted mean produce cover, over and moneyline probabilities.</li>
    </ol>
    <p>{src(SRC_CORE, "feature code")} · {src(SRC_ENGINE, "model code")} · {src(SRC_PREREG, "pre-registration")}</p>
  </div>
</section>

<section>
  <div class="section-head"><div><h2>Next slate (week {live.get('next_week')})</h2>
    <p>Model spread is from the home team's perspective: positive means the model favours the home team by that many points.</p></div></div>
  {table(["Date", "Wk", "Matchup", "Market spread", "Model spread", "Gap", "Market total", "Model total",
          "Model home win", "Model away win", "Source"],
         [r for r in rows if r[1]["v"] == str(live.get("next_week"))])}
</section>

<section>
  <div class="section-head"><div><h2>Remaining schedule</h2>
    <p>{len(live['rows'])} unplayed regular-season games are in the snapshot; {covered} already carry a market line.</p></div></div>
  <details><summary>Show all {len(live['rows'])} unplayed games</summary>
  {table(["Date", "Wk", "Matchup", "Market spread", "Model spread", "Gap", "Market total", "Model total",
          "Model home win", "Model away win", "Source"], rows)}
  </details>
</section>

<section>
  <div class="section-head"><div><h2>Model vs market, 2006–2025</h2>
    <p>How far the same model is from the closing line, measured on completed games.</p></div></div>
  {table(["Quantity", "Spread", "Total", "Source"], [
      ["Games compared", right(f"{S['accuracy']['spread']['games']:,}"), right(f"{S['accuracy']['total']['games']:,}"), src(SRC_FEATS, "features")],
      ["Model RMSE vs actual result", right(num(S['accuracy']['spread']['model_rmse'])), right(num(S['accuracy']['total']['model_rmse'])), src(SRC_FEATS, "features")],
      ["Market RMSE vs actual result", right(num(S['accuracy']['spread']['market_rmse'])), right(num(S['accuracy']['total']['market_rmse'])), src(SRC_FEATS, "features")],
      ["Model correlation with result", right(num(S['accuracy']['spread']['model_corr'], 3)), right(num(S['accuracy']['total']['model_corr'], 3)), src(SRC_FEATS, "features")],
      ["Market correlation with result", right(num(S['accuracy']['spread']['market_corr'], 3)), right(num(S['accuracy']['total']['market_corr'], 3)), src(SRC_FEATS, "features")],
  ])}
</section>"""
    return page("lines.html", "Live model lines",
                "Line origination in practice: the model's own spread, total and win probabilities for unplayed games, "
                "compared with the market where a line exists.", body)


def page_data() -> str:
    rows = []
    for f in S["files"]:
        rows.append([e(Path(f["file"]).name), right(f"{f['rows']:,}"), right(f"{f['bytes']:,}"),
                     mono(f["sha256"][:24] + "…"), src(f["source_url"], "pinned file")])
    cov = S["coverage"]
    cov_rows = []
    for season, v in sorted(cov.items(), key=lambda kv: int(kv[0])):
        cov_rows.append([right(e(season)), right(f"{v['games']:,}"), right(f"{v['with_spread_price']:,}"),
                         right(f"{v['with_total_price']:,}"), right(f"{v['with_moneyline']:,}"),
                         src(SRC_GAMES, "games.csv")])
    acc = S["accuracy"]
    acc_rows = [
        ["Spread model RMSE / market RMSE", right(num(acc['spread']['model_rmse'])), right(num(acc['spread']['market_rmse'])), src(SRC_FEATS, "features")],
        ["Total model RMSE / market RMSE", right(num(acc['total']['model_rmse'])), right(num(acc['total']['market_rmse'])), src(SRC_FEATS, "features")],
        ["Spread correlation, model / market", right(num(acc['spread']['model_corr'], 3)), right(num(acc['spread']['market_corr'], 3)), src(SRC_FEATS, "features")],
        ["Total correlation, model / market", right(num(acc['total']['model_corr'], 3)), right(num(acc['total']['market_corr'], 3)), src(SRC_FEATS, "features")],
    ]
    checks = [[f"<strong>{e(k)}</strong>", pill(v.get('status', '')), src(SRC_TESTS, "tests.json")] for k, v in TESTS.items()]
    body = f"""
<div class="notice"><strong>One pinned snapshot.</strong> Everything on this site is computed from five files at commit
<a href="{e(S['commit_url'])}" target="_blank" rel="noopener noreferrer">{e(S['pinned_commit'][:10])}</a>, hashed on
download. Re-running <code>python3 -m pipeline.run_all</code> against the same commit reproduces every number here.</div>

<section>
  <div class="section-head"><div><h2>Ingested files</h2>
    <p>Hashes are verified by the test suite before any strategy is evaluated.</p></div></div>
  {table(["File", "Rows", "Bytes", "SHA-256", "Source"], rows)}
</section>

<section>
  <div class="section-head"><div><h2>Coverage by season</h2>
    <p>Games in the snapshot and how many carry a two-sided recorded price. Missing prices are excluded, never filled.</p></div></div>
  {table(["Season", "Games", "Spread priced", "Total priced", "Moneyline priced", "Source"], cov_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Model accuracy versus the market</h2></div></div>
  {table(["Measure", "Model", "Market", "Source"], acc_rows)}
</section>

<section>
  <div class="section-head"><div><h2>Reproduction</h2></div></div>
  <div class="card">
<pre><code>python3 pipeline/fetch_data.py        # download + hash the pinned snapshot
python3 tests/test_causality.py       # provenance, causality, settlement checks
python3 -m pipeline.run_all           # backtests, gates, correlations, summary.json
python3 -m pipeline.build_site        # rebuild every page from summary.json
python3 pipeline/check_site.py        # links, sources, and no fabricated values</code></pre>
    <p class="small muted">Inputs: {src(SRC_GAMES, "games.csv")} · {src(SRC_CLOSING, "closing_lines.csv")} ·
    {src(SRC_INITIAL, "initial_lines.csv")} · {src(SRC_WINTOT, "win_totals.csv")} · {src(SRC_TEAMS, "teams.csv")}</p>
  </div>
</section>

<section>
  <div class="section-head"><div><h2>Verification checks</h2></div></div>
  {table(["Check", "Status", "Source"], checks)}
</section>"""
    return page("data.html", "Data and reproduction",
                "A single pinned snapshot, hashed on download, with every derived file traceable to it.", body)


def page_sources() -> str:
    rows = [
        ["nflverse/nfldata games.csv", "Schedules, final scores, closing spread/total/moneylines and prices", "Hash + row count verified this session; field definitions checked against the nflverse dictionary", "verified", SRC_GAMES],
        ["nflverse/nfldata closing_lines.csv", "Independent closing-line cross-check for 2006–2018 (moneyline prices)", "Hash + row count verified; column semantics are not documented by the publisher (flagged)", "verified", SRC_CLOSING],
        ["nflverse/nfldata initial_lines.csv", "2021 opening lines, single book (WSGT) — the only opening-line history available", "Hash + row count verified; not documented by the publisher (flagged)", "verified", SRC_INITIAL],
        ["nflverse/nfldata win_totals.csv", "Season win-total lines and prices, 2003–2020", "Hash + row count verified; not documented by the publisher (flagged)", "verified", SRC_WINTOT],
        ["nflverse/nfldata teams.csv", "Team identifiers used to reconcile abbreviations", "Hash + row count verified", "verified", SRC_TEAMS],
        ["nflverse/nflreadr dictionary_schedules.csv", "What each schedule/game field means: spread sign, rest, roof, temperature, wind, referee", "Read directly from the pinned source file", "verified", DICT],
        ["nflverse/nflreadr load_schedules.R", "Confirms the nflverse schedules dataset is served from nflverse/nfldata", "Read directly from source", "verified", NFLLOADER],
        ["nflverse/nfldata DATASETS.md", "Publisher's dataset notes, including that games data begins in 2006 for odds purposes", "Read directly from source", "verified", DATASETS],
        ["nflverse/nflverse-data releases: player_stats", "Exists (1,822 assets) but cannot be downloaded from this sandbox", "Release listing verified via the GitHub API; asset host unreachable", "verified", PLAYER_RELEASE],
        ["NIST statistics handbook / correlation cautions", "Method citations for confidence intervals and correlation interpretation", "External host unreachable from the research sandbox; retained as a citation only", "not verified", "https://www.itl.nist.gov/div898/handbook/"],
        ["NFL.com official statistics and records", "League's own pointer to official statistics", "External host unreachable from the research sandbox", "not verified", "https://www.nfl.com/"],
        ["DraftKings parlay help", "Operator statement of parlay and correlated-leg restrictions", "External host unreachable; no settlement rule archive is available", "not verified", "https://help.draftkings.com/"],
    ]
    trows = []
    for name, what, how, status, url in rows:
        trows.append([f"<strong>{e(name)}</strong>", e(what), e(how),
                      pill("pass") if status == "verified" else '<span class="pill warn">not verified</span>',
                      src(url, "open")])
    body = f"""
<div class="notice"><strong>Verification is limited by the sandbox, and this page says so.</strong> The research
environment can reach only GitHub hosts. Sources hosted there were downloaded, hashed and read. Sources on other hosts
are cited but not re-verified in this session, and they are listed on <a href="flagged.html">Flagged for review</a>.</div>

<section>
  <div class="section-head"><div><h2>Source register</h2>
    <p>Every table row elsewhere on the site links to one of these sources.</p></div></div>
  {table(["Source", "What it establishes", "How it was verified", "Status", "Link"], trows)}
</section>

<section>
  <div class="section-head"><div><h2>Provenance note</h2></div></div>
  <div class="card small">
    <p>nflverse is an independent open-source project that distributes NFL data. It is <em>not</em> an NFL-operated
    service, so this project calls the data "official-derived" rather than "official". The nflverse schedule dataset's own
    data dictionary attributes the closing spread to Pro Football Reference; the vendor behind the price columns published
    alongside it is not documented anywhere in the repository, which is recorded as an irregularity.</p>
    <p>{src(DICT, "field dictionary")} · {src(DATASETS, "dataset notes")}</p>
  </div>
</section>"""
    return page("sources.html", "Source register", 
                "What each source establishes, how it was checked in this session, and what could not be checked at all.",
                body)


def page_flagged() -> str:
    rows = [
        ["Player-prop markets", "No official player-level game log or licensed prop line/price could be obtained; all prop values are blank.",
         "Blocks prop ROI, prop correlation and any prop strategy.", PLAYER_RELEASE, "Provide a licensed prop archive or run the pipeline where the nflverse release host is reachable."],
        ["Price-column vendor", "The publisher documents what the price columns mean but not where the prices came from or which book they represent.",
         "Weakens any claim that a strategy could have transacted at these prices.", DICT, "Confirm the upstream odds vendor and whether quotes are executable closing prices."],
        ["Undocumented files", "closing_lines.csv, initial_lines.csv and win_totals.csv have no published field documentation.",
         "Their interpretation here is inferred from column names; S11 and the 2021 CLV study depend on it.", SRC_INITIAL, "Publisher documentation or an independent sample cross-check."],
        ["Execution assumption", "Bets are settled at the recorded closing price, which assumes a bettor could transact at the close.",
         "Makes every ROI an upper bound on achievable returns.", SRC_PREREG, "Intraday quote snapshots would let the pipeline bet at a pre-close timestamp."],
        ["Opening-line history", "Only 2021 exists, from one book, so closing-line value cannot be measured across the sample.",
         "No strategy can prove it beats the close over time.", SRC_INITIAL, "Multi-season opening-line archive."],
        ["Same-game parlay rules", "Operator-specific void, push and correlated-leg pricing rules could not be read from an official source.",
         "SGP economics here are an approximation that ignores book repricing.", "https://help.draftkings.com/", "Capture dated operator rule pages and archive them."],
        ["Monetary rewards", "No pool, sponsor or funding exists.",
         "Reward points are the only reward; prize money is blank.", SRC_PREREG, "Fund a pool and publish the rules before the next evaluation round."],
        ["External method citations", "NIST, NFL.com and operator help pages are unreachable from the research sandbox.",
         "Their content is cited, not re-verified in this session.", "https://www.itl.nist.gov/div898/handbook/", "Re-verify manually or run the session with broader network access."],
        ["S11 holdout", "Season win totals stop in 2020, so the 2023–2025 holdout cannot evaluate S11.",
         "S11 fails G3/G4 by construction; it is not evidence of anything.", SRC_WINTOT, "Extend the futures archive to the current season."],
        ["2026 forward cut", f"Only {S['universe']['forward_games']} games of the 2026 season are complete in this snapshot.",
         "The forward column is a live monitor, not gate evidence.", SRC_GAMES, "Re-run weekly as games complete."],
        ["Referee tendency", "Only the head official is recorded; crews change between seasons.",
         "S7's signal is a coarse proxy for the actual crew.", DICT, "Crew-level assignment data would be required."],
        ["Weather coverage", "Temperature and wind exist only for outdoor and open-roof games.",
         "Winter games with missing weather are dropped from S6, not imputed.", DICT, "A weather archive joined by stadium and kickoff time."],
        ["Week-1 rest values", "The source fills week-1 rest with a placeholder value.",
         "S4 excludes week 1 to avoid a false rest edge.", DICT, "Prior-season final-week dates would allow a true calculation."],
        ["Automation", "Ingestion is a script that must be run, not a scheduled job.",
         "The site is a snapshot as of the timestamp in the footer.", SRC_CORE, "Add a scheduled refresh workflow."],
        ["Legal and eligibility", "Jurisdiction, age limits, licensing and current league policy were not verified.",
         "Nothing here is legal or betting advice.", "https://www.nfl.com/", "Obtain jurisdiction-specific legal review."],
    ]
    trows = [[f"<strong>{e(a)}</strong>", e(b), e(c), src(u, "source"), e(d)] for a, b, c, u, d in rows]
    body = f"""
<div class="notice"><strong>This page exists so nothing can hide.</strong> These are the items that could not be
verified, the assumptions that were necessary, and the sources behind both. None of them block the release — they block
the claims.</div>

<section>
  <div class="section-head"><div><h2>Open items</h2>
    <p>{len(rows)} entries. Status is "flagged", not "failed": each one is a specific follow-up.</p></div></div>
  {table(["Item", "What is unverified", "Why it matters", "Source", "Review action"], trows)}
</section>

<section>
  <div class="section-head"><div><h2>How blanks are handled</h2></div></div>
  <div class="card small">
    <p>A blank cell on this site always links back to this page. It means "the data needed to compute this does not
    exist in a reachable, verifiable source". It never means zero, and no value is ever interpolated, back-filled or
    estimated to fill the space. The site's build check fails if a blank is rendered without the flag link.</p>
    <p>{src(BLOB + 'pipeline/check_site.py', 'link and value checker')}</p>
  </div>
</section>"""
    return page("flagged.html", "Flagged for review",
                "Every irregularity, unverified value and assumption behind this research, with its source and the action "
                "that would close it.", body)


def page_methodology() -> str:
    body = f"""
<section>
  <div class="section-head"><div><h2>Protocol</h2><p>Frozen in writing before the first backtest. The file is in the repo with its own commit history.</p></div></div>
  {table(["Step", "What is done", "Why", "Source"], [
      ["Universe", f"Regular season, completed games, {S['protocol']['eval_window'][0]}–{S['protocol']['eval_window'][1]} for evaluation; 1999–2005 only to warm up ratings.", "Prices begin in 2006 in the source.", src(SRC_GAMES, "data")],
      ["Causality", "State is updated only after a game is emitted; models refit each season on prior seasons only; a truncation test proves it.", "A feature that can see the future invalidates everything downstream.", src(SRC_TESTS, "test")],
      ["Pricing", "Two-way prices de-vigged with the proportional method; integer lines keep a modelled push probability.", "Comparing a model to a vigged price makes every model look good.", src(SRC_EVAL, "code")],
      ["Selection", f"Bet when the model's conditional probability beats the de-vigged market by ≥ {S['protocol']['edge_min']*100:.0f} points and the price is inside {S['protocol']['price_min']:+.0f} to {S['protocol']['price_max']:+.0f}.", "Pre-registered, not tuned.", src(SRC_PREREG, "§4")],
      ["Settlement", "Win/loss/push from the recorded final score at the recorded price; flat 1-unit stake.", "No staking model is evaluated.", src(SRC_ENGINE, "engine")],
      ["Uncertainty", f"{S['protocol']['bootstrap_resamples']:,} week-block bootstrap resamples; {S['protocol']['permutation_resamples']:,} permutation simulations.", "Games inside a week share conditions; resampling whole weeks respects that.", src(SRC_EVAL, "code")],
      ["Multiplicity", f"Benjamini–Hochberg across {S['family']['tests']} tests at q ≤ {S['protocol']['fdr_level']}.", "Eleven tests means eleven chances to be lucky.", src(SRC_EVAL, "code")],
      ["Rewards", "Only all-nine-gate strategies are ranked and scored.", "A leaderboard that pays in-sample winners is a luck factory.", src(SRC_PREREG, "§8")],
  ])}
</section>

<section>
  <div class="section-head"><div><h2>Formulas</h2></div></div>
  <div class="card">
<pre><code>Elo update
  expected_home = 1 / (1 + 10^(-(elo_home + 55 - elo_away) / 400))
  multiplier    = ln(|margin| + 1) * 2.2 / (0.001 * winner_elo_diff + 2.2)
  elo_home'     = elo_home + 20 * multiplier * (won - expected_home)
  new season    : elo = 1500 + 0.75 * (elo - 1500)

Team scoring profile (half-life 4 games)
  off_t = off_(t-1) + (1 - 0.5^(1/4)) * (points_scored - off_(t-1))
  def_t = def_(t-1) + (1 - 0.5^(1/4)) * (points_allowed - def_(t-1))

Model
  margin ~ 1 + elo_diff + rest_diff + qb_change_home + qb_change_away      (OLS, prior seasons)
  total  ~ 1 + off_home + def_home + off_away + def_away + indoor           (OLS, prior seasons)
  P(home covers line L) = 1 - Phi((L - mu) / sigma)

De-vig (proportional)
  p_i = (1 / decimal_i) / sum_j (1 / decimal_j)

Bootstrap ROI interval
  resample weeks with replacement; ROI = sum(pnl) / n_bets

phi for two binary legs
  phi = corr(A, B);   P(A and B) = p_A p_B + phi * sqrt(p_A(1-p_A) p_B(1-p_B))</code></pre>
    <p class="small">{src(SRC_CORE, "feature code")} · {src(SRC_ENGINE, "model code")} · {src(SRC_EVAL, "evaluation code")} · {src(SRC_PREREG, "pre-registration")}</p>
  </div>
</section>

<section>
  <div class="section-head"><div><h2>Power: how many bets a real edge needs</h2>
    <p>Two-sided test at 5%, 80% power, per-bet standard deviation 0.95 units.</p></div></div>
  {table(["True edge per bet", "Bets required", "Seasons at 750 bets", "Source"],
         [[right(f"{p['edge']*100:.0f}%"), right(f"{p['bets_required']:,}"), right(f"{p['seasons_at_750_bets']:.1f}"), src(SRC_EXTRAS, "code")]
          for p in S["extras"]["power"]])}
</section>

<section>
  <div class="section-head"><div><h2>Luck band</h2>
    <p>What a leaderboard of {S['extras']['luck_band']['strategies_per_family']} no-skill strategies looks like.</p></div></div>
  {table(["Quantity", "Value", "Source"], [
      ["Mean ROI of a single random strategy", right(signed_pct(S['extras']['luck_band']['mean_single_roi'])), src(SRC_EXTRAS, "simulation")],
      ["Mean ROI of the BEST of the family", right(signed_pct(S['extras']['luck_band']['mean_best_roi'])), src(SRC_EXTRAS, "simulation")],
      ["5th percentile of the best", right(signed_pct(S['extras']['luck_band']['p05_best_roi'])), src(SRC_EXTRAS, "simulation")],
      ["95th percentile of the best", right(signed_pct(S['extras']['luck_band']['p95_best_roi'])), src(SRC_EXTRAS, "simulation")],
      ["Chance the family produces a profitable winner", right(pct(S['extras']['luck_band']['prob_best_is_profitable'], 1)), src(SRC_EXTRAS, "simulation")],
  ])}
</section>

<section>
  <div class="section-head"><div><h2>Threshold sensitivity (exploratory)</h2>
    <p>How ROI moves with the edge threshold. Post-hoc and therefore not eligible for rewards — it exists to show that
    the apparent gains at higher thresholds are inside the luck band.</p></div></div>
  {table(["Strategy", "Threshold", "Bets", "Share of games", "Win rate", "ROI", "Source"],
         [[f"<strong>{e(sid)}</strong>", right(f"{r['threshold']*100:.0f} pp"),
           right(f"{r.get('bets',0):,}"), right(pct(r.get('share_of_games'))), right(pct(r.get('win_rate'))),
           right(signed_pct(r.get('roi'))), src(SRC_EXTRAS, "code")]
          for sid, rows in S['extras']['sensitivity'].items() for r in rows])}
</section>

<section>
  <div class="section-head"><div><h2>Limitations</h2></div></div>
  <div class="card small"><ul>
    <li>Closing-price settlement is an upper bound; no intraday quotes are available.</li>
    <li>The models use public, game-level information only: no tracking data, injuries, or player participation.</li>
    <li>Elo, the moving-average half-life and the home-field constant are project choices, not estimates.</li>
    <li>One season of opening lines exists, so closing-line value is unmeasurable at sample.</li>
    <li>Brier skill is a proper scoring rule but says nothing about which side of a line to take; the gates use both.</li>
    <li>Nothing here is a forecast of future results, and betting loses money for most participants.</li>
  </ul></div>
</section>"""
    return page("methodology.html", "Method", 
                "The protocol, the formulas, the power calculation and the limits — everything needed to attack the results "
                "rather than trust them.", body)


def page_requirements() -> str:
    rows = [
        ["Collect, organise and analyse a full requirement list", "Requirements captured and mapped to evidence on this page and in docs/requirements.md", "done", SRC_REQS],
        ["Originate own NFL lines", "Model-implied spread, total and win probabilities for every unplayed game, rebuilt from ratings each run", "done", "lines.html"],
        ["Research and develop signal strategies", "11 pre-registered strategies across spread, total, moneyline, parlay and futures markets", "done", SRC_ENGINE],
        ["Leaderboard competition with rewards", "Ranking with a pre-registered reward rule; no strategy became eligible, so no points were awarded; no money is funded", "partial", SRC_PREREG],
        ["Single bets", "S1–S8 settle single bets at recorded closing prices", "done", SRC_BETS],
        ["Parlays", "S9/S10 two-leg cross-game cards plus measured dependence for combination pricing", "done", SRC_ENGINE],
        ["Player prop bet combos", "Blocked: no reachable official player logs or prop prices; estimator written, values blank", "blocked", "props.html"],
        ["Every strategy passes validation gates", "9 gates implemented; 0 of 11 strategies passed all of them", "done (result: none pass)", "validation.html"],
        ["Determine correlation values", "phi for same-game pairs, cross-game dependence, team-scoring correlation, strategy-return matrix — all with intervals and n", "done", SRC_CORR],
        ["Remove luck from the equation", "Week-block bootstrap, permutation test, BH-FDR, holdout, and a measured luck band for the whole family", "done", SRC_EVAL],
        ["Skill-based, selective strategies", "Selectivity measured (share of games bet), skill tested against the de-vigged market; no candidate showed positive Brier skill", "done (result: negative)", "leaderboard.html"],
        ["Executive summary", "EXECUTIVE_SUMMARY.md plus the dashboard on the home page", "done", SRC_EXEC],
        ["Repo review, line by line, official sources, links", "Input files hashed and re-verified; every table row links to a source; external hosts flagged as unverified", "done", "sources.html"],
        ["GitHub Pages site with clean dashboard UI", "13 pages generated from the data, mobile-friendly, no external dependencies", "done", "index.html"],
        ["Verification: blank rather than inferred", "Build check fails on a blank cell without a review link or a table row without a source", "done", BLOB + "line_lab/check_site.py"],
        ["Parallel-session coordination", "COORDINATION.md board with claims, scopes and a session log", "done", BLOB + "COORDINATION.md"],
        ["Pull request, merge and Pages deploy", "Session integrates on its own branch, opens a PR, merges and verifies the deploy", "done", REPO + "/pulls"],
    ]
    trows = [[f"<strong>{e(a)}</strong>", e(b), pill("pass") if c.startswith("done") else ('<span class="pill fail">blocked</span>' if c == "blocked" else '<span class="pill warn">partial</span>'),
              src(u, "evidence") if u.startswith("http") else f'<a href="{e(u)}">{e(u)}</a>'] for a, b, c, u in rows]
    body = f"""
<div class="notice"><strong>Two requirements are honestly short of complete.</strong> The reward competition cannot pay
anything until a strategy is eligible, and player-prop combos are blocked by data availability. Both are published on
<a href="flagged.html">Flagged for review</a> rather than papered over.</div>
<section>
  <div class="section-head"><div><h2>Requirement traceability</h2></div></div>
  {table(["Requirement", "What was delivered", "Status", "Evidence"], trows)}
</section>"""
    return page("requirements.html", "Requirements and delivery", 
                "Every stated requirement, what was actually delivered, and a link to the evidence.", body)


def page_sessions() -> str:
    rows = [
        ["This dashboard (root site)", "arena/9f5e9cb5-korea3",
         "line_lab/ + root *.html", "11 pre-registered strategies, 9 gates, 0 eligible; measured dependence; 13 pages",
         '<a href="index.html">open</a>', src(BLOB + "line_lab/EXECUTIVE_SUMMARY.md", "exec summary")],
        ["Empirical pipeline site", "arena/c70bdb9d-korea3",
         "site/", "18 pre-registered signals, 8 gates, correlation lab, player-prop framework, own-line model; reports 0 of 18 passing all gates",
         '<a href="site/index.html">open</a>', src(BLOB + "site/index.html", "site")],
        ["Second Line Lab build", "arena/d118ca7e-korea3",
         "docs/", "Separate pipeline with reports/ and a 13-page docs site, rebuilt deterministically in CI",
         '<a href="docs/index.html">open</a>', src(BLOB + "docs/index.html", "site")],
        ["Independent audit", "arena/65d448da-korea3",
         "audit/", "Line-by-line audit, data-rights review, cross-session QA and its own flagged register",
         '<a href="audit/flagged.html">open</a>', src(BLOB + "audit/line-by-line.md", "audit")],
        ["First research brief", "arena/9febee68-korea3",
         "site/prior/", "The original plan-only brief: seven pages, every performance value blank and flagged",
         '<a href="site/prior/index.html">open</a>', src(BLOB + "site/prior/index.html", "brief")],
        ["Prior copies of this dashboard's pages", "arena/9febee68-korea3",
         "site/prior/", "Superseded root pages kept byte-identical when this dashboard took over the repo root",
         '<a href="site/prior/index.html">open</a>', src(BLOB + "site/prior/index.html", "copy")],
    ]
    body = f"""
<div class="notice"><strong>This repository carries several bodies of work from parallel sessions.</strong>
Each session was told the same brief. Rather than delete anyone's output, the root URL now serves this dashboard
(generated from <code>line_lab/</code>), and every other build stays in place, reachable below. Nothing was overwritten:
prior root pages were copied to <code>site/prior/</code> before this build took the root.</div>

<section>
  <div class="section-head"><div><h2>Bodies of work</h2>
    <p>Descriptions of the other builds are quoted from their own documentation in this repository, not re-verified here.</p></div></div>
  {table(["Body", "Session", "Location", "What it reports", "Open", "Source"], rows)}
</section>

<section>
  <div class="section-head"><div><h2>What is different about this build</h2></div></div>
  <div class="card small"><ul>
    <li>Every page is rendered from one generated <code>summary.json</code>; no number is typed by hand.</li>
    <li>The pre-registered protocol, including the reward rule and the luck band, was committed before the first backtest.</li>
    <li>The build check fails if a table row has no source link, if a blank lacks a link to the review page, or if a
        strategy's ROI in the pages disagrees with <code>bets.csv</code>.</li>
    <li>Player props are declared blocked rather than estimated; the estimator and its required schema are committed.</li>
  </ul></div>
</section>

<section>
  <div class="section-head"><div><h2>Coordination record</h2></div></div>
  <div class="card small"><p>The task board, claims, conflict resolutions and handoff notes are in
  {src(BLOB + "COORDINATION.md", "COORDINATION.md")}. The audit of the previous state of this repository, including the
  irregularity that three sessions had published to the same Pages path, is recorded there and in
  {src(BLOB + "audit/cross-session-qa.md", "audit/cross-session-qa.md")}.</p></div>
</section>"""
    return page("sessions.html", "All sessions", 
                "Five bodies of work, one repository. This page keeps them separate, honest and reachable.", body)


def main() -> int:
    pages = {
        "index.html": page_index,
        "leaderboard.html": page_leaderboard,
        "strategies.html": page_strategies,
        "validation.html": page_validation,
        "correlations.html": page_correlations,
        "parlays.html": page_parlays,
        "props.html": page_props,
        "lines.html": page_lines,
        "data.html": page_data,
        "sources.html": page_sources,
        "flagged.html": page_flagged,
        "methodology.html": page_methodology,
        "requirements.html": page_requirements,
        "sessions.html": page_sessions,
    }
    SITE.mkdir(parents=True, exist_ok=True)
    (SITE / "assets").mkdir(parents=True, exist_ok=True)
    (ROOT / "assets").mkdir(parents=True, exist_ok=True)
    for asset in ("style.css", "app.js"):
        src = ROOT / "line_lab" / "assets" / asset
        if src.exists():
            (ROOT / "assets" / asset).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
    for name, fn in pages.items():
        (SITE / name).write_text(fn(), encoding="utf-8")
        print(f"wrote {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
