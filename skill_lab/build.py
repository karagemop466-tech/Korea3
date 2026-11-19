#!/usr/bin/env python3
"""Build the Skill Lab: data files + dashboard pages.

Run:  python3 -m skill_lab.build

Inputs (already pinned and committed in the tree, no network):
  line_lab/data/derived/bets.csv        per-bet model_prob / market_prob / outcome
  market_lab/data/results_feed.csv      verified, settled market-side universe

Outputs (written to skill_lab/data and skill_lab/*.html):
  data/skill_leaderboard.csv   per-strategy benchmark-relative Brier skill + uncertainty
  data/control_baselines.csv   market / random / favourites-only controls (C04)
  data/per_market.csv          skill by strategy x market
  data/skill_summary.json      counts, method, sources, seeds
  index.html  method.html  flagged.html

Every table row links to the pinned source. A value that cannot be computed from
the pinned data is left blank and flagged on flagged.html — never inferred.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import baselines as bl
from .metrics import benjamini_hochberg, bonferroni, brier, bootstrap_bss, settled

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
DATA = BASE / "data"

BETS = ROOT / "line_lab" / "data" / "derived" / "bets.csv"
RESULTS = ROOT / "market_lab" / "data" / "results_feed.csv"

BETS_URL = "https://github.com/karagemop466-tech/Korea3/blob/main/line_lab/data/derived/bets.csv"
RESULTS_URL = "https://github.com/karagemop466-tech/Korea3/blob/main/market_lab/data/results_feed.csv"
NFLVERSE_URL = "https://github.com/nflverse/nfldata/tree/a270278f3ac4e937295fe6a27814b3c4a2b62645"
PROV_URL = "https://github.com/karagemop466-tech/Korea3/blob/main/data/provenance.json"
PINNED_COMMIT = "a270278f3ac4e937295fe6a27814b3c4a2b62645"

# Strategies that require a validated joint probability + operator void/push rules
# before they may be ranked (readiness C01, NOT MET). Computed, but not ranked.
GATED_IDS = {"S9", "S10"}
# Strategies with no model_prob in the pinned data -> Brier left blank, flagged.
NO_PROB_IDS = {"S11"}


# --------------------------------------------------------------------------- #
# Formatting helpers
# --------------------------------------------------------------------------- #
def fmt(x, nd=4):
    if x is None:
        return ""
    try:
        xf = float(x)
    except (TypeError, ValueError):
        return ""
    if not np.isfinite(xf):
        return ""
    return f"{xf:.{nd}f}"


def fmt_int(x):
    if x is None:
        return ""
    try:
        return str(int(x))
    except (TypeError, ValueError):
        return ""


def esc(s) -> str:
    return html.escape(str(s))


def link(href: str, text: str) -> str:
    return f'<a href="{esc(href)}" target="_blank" rel="noopener noreferrer">{esc(text)}</a>'


def two_links() -> str:
    return (f'{link(BETS_URL, "bets.csv")} · {link(NFLVERSE_URL, "nflverse pin")}')


def res_links() -> str:
    return (f'{link(RESULTS_URL, "results_feed.csv")} · {link(NFLVERSE_URL, "nflverse pin")}')


# --------------------------------------------------------------------------- #
# Strategy metrics
# --------------------------------------------------------------------------- #
def _common_settled(grp: pd.DataFrame) -> pd.DataFrame:
    """Settled rows with BOTH model_prob and market_prob finite.

    Brier(model) and Brier(market) must be computed over the same rows, otherwise
    their difference is not the benchmark-relative skill the bootstrap measures.
    """
    s = settled(grp["outcome"])
    mask = s & grp["model_prob"].notna() & grp["market_prob"].notna()
    return grp.loc[mask, ["model_prob", "market_prob", "outcome", "season", "week"]]


def strategy_rows(bets: pd.DataFrame) -> list[dict]:
    rows = []
    for (sid, name), grp in bets.groupby(["strategy_id", "strategy_name"], sort=False):
        sub = _common_settled(grp)
        n_bets = int(len(grp))
        n_settled = int(len(sub))
        n_push = int((grp["outcome"] == 0).sum())
        brier_m = brier(sub["model_prob"], sub["outcome"]) if n_settled else float("nan")
        brier_mk = brier(sub["market_prob"], sub["outcome"]) if n_settled else float("nan")
        boot = bootstrap_bss(grp) if n_settled else {}
        gated = sid in GATED_IDS
        noprob = sid in NO_PROB_IDS or not np.isfinite(brier_m)
        rows.append({
            "id": sid, "name": name, "market": grp["market"].iloc[0],
            "n_bets": n_bets, "n_settled": n_settled, "n_push": n_push,
            "brier_model": brier_m, "brier_market": brier_mk,
            "bss": boot.get("bss", float("nan")),
            "ci_low": boot.get("ci_low"), "ci_high": boot.get("ci_high"),
            "lower_bound": boot.get("lower_bound"),
            "p_value": boot.get("p_value"),
            "gated": gated, "no_prob": noprob,
            "source": two_links(),
        })
    return rows


def apply_ranks(rows: list[dict]) -> tuple[list[dict], dict[str, float], dict[str, float]]:
    """Rank eligible strategies by BSS; compute BH + Bonferroni across eligible."""
    eligible = [r for r in rows if not r["gated"] and not r["no_prob"] and np.isfinite(r["bss"])]
    pvals = {r["id"]: r["p_value"] for r in eligible if r["p_value"] is not None}
    bh = benjamini_hochberg(pvals)
    bf = bonferroni(pvals)
    ordered = sorted(eligible, key=lambda r: r["bss"], reverse=True)
    for rank, r in enumerate(ordered, 1):
        r["skill_rank"] = rank
        r["bh_q"] = bh.get(r["id"])
        r["bonf_q"] = bf.get(r["id"])
    for r in rows:
        r.setdefault("skill_rank", None)
        r.setdefault("bh_q", None)
        r.setdefault("bonf_q", None)
    return rows, bh, bf


def per_market_rows(bets: pd.DataFrame) -> list[dict]:
    rows = []
    for (sid, name, market), grp in bets.groupby(
            ["strategy_id", "strategy_name", "market"], sort=False):
        sub = _common_settled(grp)
        if sub.empty:
            continue
        boot = bootstrap_bss(grp)
        rows.append({
            "strategy_id": sid, "strategy_name": name, "market": market,
            "n_settled": int(len(sub)),
            "bss": boot.get("bss", float("nan")),
            "ci_low": boot.get("ci_low"), "ci_high": boot.get("ci_high"),
            "p_value": boot.get("p_value"),
            "source": two_links(),
        })
    return rows


# --------------------------------------------------------------------------- #
# Control baselines
# --------------------------------------------------------------------------- #
def control_rows(results: pd.DataFrame) -> list[dict]:
    uni = bl.control_universe(results)
    mk = bl.market_benchmark(uni)
    fav = bl.favourites_only(uni)
    rnd = bl.random_5050(uni)
    # BSS vs market on the favourites universe: favourites predict at the
    # market's own implied probability, so BSS = 0 by construction.
    rows = [
        {
            "control": "Market benchmark (closing implied prob)",
            "brier": mk["brier"], "bss": 0.0,
            "roi": float("nan"), "roi_ci_low": None, "roi_ci_high": None,
            "roi_p": None, "n": mk["n"],
            "note": "No-skill reference; BSS = 0 by construction. Mean vig per "
                    f"game-market = {fmt(mk['mean_vig'], 4)} over {mk['n_markets']} markets.",
            "source": res_links(),
        },
        {
            "control": "Favourites-only",
            "brier": fav["brier"], "bss": 0.0,
            "roi": fav["roi"], "roi_ci_low": fav["roi_ci_low"],
            "roi_ci_high": fav["roi_ci_high"], "roi_p": fav["roi_p_value"],
            "n": fav["n"],
            "note": "Always the higher-implied-probability side; predicts at the "
                    "market's implied prob so BSS = 0. ROI is a real, bootstrapped number.",
            "source": res_links(),
        },
        {
            "control": "Random 50/50 picks",
            "brier": rnd["brier"], "bss": rnd["bss"],
            "roi": rnd["roi"], "roi_ci_low": None, "roi_ci_high": None,
            "roi_p": None, "n": rnd["n"],
            "note": f"Brier = 0.25 (analytic). BSS is the market implied prob of the "
                    f"picked side minus 0.25 on the same universe. ROI is a single seeded "
                    f"realisation (seed {rnd['seed']}), labelled seed-dependent.",
            "source": res_links(),
        },
    ]
    return rows


# --------------------------------------------------------------------------- #
# HTML
# --------------------------------------------------------------------------- #
CSS = """
:root{--bg:#0f1420;--panel:#1a2130;--ink:#e8ecf4;--mut:#9aa6b8;--line:#2a3548;--acc:#5b9dff;--good:#46c08a;--bad:#ff6b6b;--warn:#f0b429}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;background:var(--bg);color:var(--ink)}
a{color:var(--acc)}header{padding:22px 28px;border-bottom:1px solid var(--line);background:var(--panel)}
h1{margin:0 0 4px;font-size:22px}h2{margin:26px 0 10px;font-size:17px;color:var(--ink)}
.sub{color:var(--mut);font-size:13px}nav{margin-top:12px;font-size:14px}nav a{margin-right:16px}
main{padding:24px 28px;max-width:1180px}.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin:18px 0}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px}.card .k{color:var(--mut);font-size:12px}.card .v{font-size:22px;font-weight:600;margin-top:4px}
table{width:100%;border-collapse:collapse;margin:10px 0;font-size:13.5px;background:var(--panel)}th,td{padding:8px 10px;border-bottom:1px solid var(--line);text-align:right;vertical-align:top}
th:first-child,td:first-child,th.l,td.l{text-align:left}th{color:var(--mut);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.03em}
tbody tr:hover{background:#202a3d}.pos{color:var(--good)}.neg{color:var(--bad)}.mut{color:var(--mut);font-size:12px}
.tag{display:inline-block;padding:1px 7px;border-radius:6px;font-size:11px;border:1px solid var(--line)}.tag.g{color:var(--warn);border-color:var(--warn)}.tag.u{color:var(--bad);border-color:var(--bad)}
footer{padding:18px 28px;border-top:1px solid var(--line);color:var(--mut);font-size:12px}
.note{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;margin:14px 0;font-size:13.5px}
"""


def nav(active: str) -> str:
    items = [("index", "Dashboard"), ("method", "Method & sources"), ("flagged", "Flagged for review")]
    out = ['<nav>']
    for key, label in items:
        cur = ' style="color:var(--acc);font-weight:600"' if key == active else ""
        out.append(f'<a href="{key}.html"{cur}>{label}</a>')
    out.append('<a href="../index.html">↑ Repo root</a>')
    out.append('</nav>')
    return "".join(out)


def page(title: str, active: str, body: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="description" content="{esc(title)} — NFL line-origination skill vs luck, control baselines and benchmark-relative Brier skill. Official-evidence-only; every row sourced.">
<title>{esc(title)} — Skill Lab</title><style>{CSS}</style></head>
<body><header><h1>{esc(title)}</h1>
<div class="sub">NFL Line Lab · Skill vs Luck · control baselines + benchmark-relative proper-score ranking</div>
{nav(active)}</header>
<main>{body}</main>
<footer>Pinned source commit {PINNED_COMMIT} · inputs: <a href="{BETS_URL}">bets.csv</a>, <a href="{RESULTS_URL}">results_feed.csv</a> · <a href="{PROV_URL}">provenance</a> · nothing inferred; unverifiable values are blank and flagged.</footer>
</body></html>"""


def leaderboard_table(rows: list[dict]) -> str:
    hdr = ["ID", "Strategy", "Market", "n bets", "n settled", "n push",
           "Brier (model)", "Brier (market)", "BSS", "95% CI low", "95% CI high",
           "p (1-sided)", "BH q", "Bonf q", "Skill rank", "Status", "Source"]
    body = []
    for r in rows:
        bss = r["bss"]
        bss_cls = "pos" if (bss is not None and np.isfinite(bss) and bss > 0) else (
            "neg" if (bss is not None and np.isfinite(bss) and bss < 0) else "mut")
        if r["gated"]:
            status = '<span class="tag g">gated (C01)</span>'
            rank = "—"
        elif r["no_prob"]:
            status = '<span class="tag u">unverified</span>'
            rank = "—"
        elif r["skill_rank"]:
            status = '<span class="tag">ranked</span>'
            rank = str(r["skill_rank"])
        else:
            status = '<span class="tag">not ranked</span>'
            rank = "—"
        body.append(
            f'<tr><td class="l">{esc(r["id"])}</td><td class="l">{esc(r["name"])}</td>'
            f'<td>{esc(r["market"])}</td><td>{fmt_int(r["n_bets"])}</td>'
            f'<td>{fmt_int(r["n_settled"])}</td><td>{fmt_int(r["n_push"])}</td>'
            f'<td>{fmt(r["brier_model"])}</td><td>{fmt(r["brier_market"])}</td>'
            f'<td class="{bss_cls}">{fmt(bss)}</td><td>{fmt(r["ci_low"])}</td>'
            f'<td>{fmt(r["ci_high"])}</td><td>{fmt(r["p_value"])}</td>'
            f'<td>{fmt(r["bh_q"])}</td><td>{fmt(r["bonf_q"])}</td>'
            f'<td>{rank}</td><td class="l">{status}</td>'
            f'<td class="l">{r["source"]}</td></tr>')
    return f'<table><thead><tr>{"".join(f"<th>{h}</th>" for h in hdr)}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def controls_table(rows: list[dict]) -> str:
    hdr = ["Control", "Brier", "BSS vs market", "ROI", "ROI 95% CI", "p (ROI>0)", "n", "Note", "Source"]
    body = []
    for r in rows:
        roi = r["roi"]
        roi_cls = "pos" if (roi is not None and np.isfinite(roi) and roi > 0) else (
            "neg" if (roi is not None and np.isfinite(roi) and roi < 0) else "mut")
        ci = ""
        if r["roi_ci_low"] is not None and r["roi_ci_high"] is not None:
            ci = f'{fmt(r["roi_ci_low"])} … {fmt(r["roi_ci_high"])}'
        body.append(
            f'<tr><td class="l">{esc(r["control"])}</td><td>{fmt(r["brier"])}</td>'
            f'<td>{fmt(r["bss"])}</td><td class="{roi_cls}">{fmt(roi)}</td>'
            f'<td>{ci}</td><td>{fmt(r["roi_p"])}</td><td>{fmt_int(r["n"])}</td>'
            f'<td class="l mut">{esc(r["note"])}</td><td class="l">{r["source"]}</td></tr>')
    return f'<table><thead><tr>{"".join(f"<th>{h}</th>" for h in hdr)}</tr></thead><tbody>{"".join(body)}</tbody></table>'


def permarket_table(rows: list[dict]) -> str:
    hdr = ["Strategy", "Market", "n settled", "BSS", "95% CI low", "95% CI high", "p (1-sided)", "Source"]
    body = []
    for r in rows:
        bss = r["bss"]
        cls = "pos" if (bss is not None and np.isfinite(bss) and bss > 0) else (
            "neg" if (bss is not None and np.isfinite(bss) and bss < 0) else "mut")
        body.append(
            f'<tr><td class="l">{esc(r["strategy_id"])} · {esc(r["strategy_name"])}</td>'
            f'<td>{esc(r["market"])}</td><td>{fmt_int(r["n_settled"])}</td>'
            f'<td class="{cls}">{fmt(bss)}</td><td>{fmt(r["ci_low"])}</td>'
            f'<td>{fmt(r["ci_high"])}</td><td>{fmt(r["p_value"])}</td>'
            f'<td class="l">{r["source"]}</td></tr>')
    return f'<table><thead><tr>{"".join(f"<th>{h}</th>" for h in hdr)}</tr></thead><tbody>{"".join(body)}</tbody></table>'


# --------------------------------------------------------------------------- #
# Build
# --------------------------------------------------------------------------- #
def build() -> dict:
    DATA.mkdir(parents=True, exist_ok=True)
    bets = pd.read_csv(BETS, low_memory=False)
    results = pd.read_csv(RESULTS, low_memory=False)

    strat = strategy_rows(bets)
    strat, bh, bf = apply_ranks(strat)
    ctrl = control_rows(results)
    pm = per_market_rows(bets)

    # ---- write CSVs ----
    pd.DataFrame(strat).to_csv(DATA / "skill_leaderboard.csv", index=False)
    pd.DataFrame(ctrl).to_csv(DATA / "control_baselines.csv", index=False)
    pd.DataFrame(pm).to_csv(DATA / "per_market.csv", index=False)

    ranked = [r for r in strat if r["skill_rank"]]
    positive = [r for r in ranked if r["bss"] is not None and np.isfinite(r["bss"]) and r["bss"] > 0]
    sig_bh = [r for r in ranked if r["bh_q"] is not None and np.isfinite(r["bh_q"]) and r["bh_q"] < 0.05]
    best = max(ranked, key=lambda r: r["bss"]) if ranked else None

    summary = {
        "generated_by": "arena/3d29863c-korea3",
        "pinned_commit": PINNED_COMMIT,
        "seed": 20261119,
        "n_boot": 2000,
        "bets_rows": int(len(bets)),
        "results_rows": int(len(results)),
        "strategies": int(len(strat)),
        "strategies_ranked": int(len(ranked)),
        "strategies_bss_positive": int(len(positive)),
        "strategies_significant_bh": int(len(sig_bh)),
        "best_skill": {"id": best["id"], "name": best["name"], "bss": best["bss"]} if best else None,
        "controls": {r["control"]: {"brier": r["brier"], "roi": r["roi"], "n": r["n"]} for r in ctrl},
        "method": {
            "skill": "BSS = Brier(model_prob, outcome) - Brier(market_prob, outcome) over settled bets",
            "uncertainty": "game-cluster bootstrap (season-week), 2000 replicates, 95% percentile CI",
            "multiplicity": "Benjamini-Hochberg FDR across ranked strategies; Bonferroni alongside",
            "controls": "market benchmark; random 50/50 (analytic Brier 0.25); favourites-only",
        },
        "sources": [BETS_URL, RESULTS_URL, NFLVERSE_URL, PROV_URL],
    }
    (DATA / "skill_summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    # ---- flagged items ----
    flags = []
    for r in strat:
        if r["gated"]:
            flags.append({"id": r["id"], "item": r["name"], "flag": "GATED",
                          "detail": "Parlay strategy. Joint-evidence gate (readiness C01) is NOT MET; "
                                    "the BSS is computed but the strategy is not ranked as skill until a "
                                    "validated joint probability and operator void/push rules are available.",
                          "source": r["source"]})
        if r["no_prob"]:
            flags.append({"id": r["id"], "item": r["name"], "flag": "UNVERIFIED",
                          "detail": "No model_prob in the pinned bets.csv for this strategy; Brier and BSS "
                                    "are left blank and not inferred.",
                          "source": r["source"]})
    for r in ctrl:
        if r["control"] == "Random 50/50 picks":
            flags.append({"id": "CTRL-RND", "item": "Random 50/50 picks", "flag": "SEED-DEPENDENT",
                          "detail": "Brier is analytic (0.25); the published ROI is a single seeded "
                                    f"realisation (seed {20261119}) and is not a stable estimate.",
                          "source": r["source"]})

    # ---- HTML ----
    cards = [
        ("Strategies ranked", str(len(ranked))),
        ("BSS > 0 (better than market)", str(len(positive))),
        ("Significant after BH (q<0.05)", str(len(sig_bh))),
        ("Best skill", (f'{fmt(best["bss"])} · {best["id"]}' if best else "—")),
        ("Control: favourites ROI", fmt(ctrl[1]["roi"])),
        ("Control: random Brier", fmt(ctrl[2]["brier"])),
    ]
    cards_html = "".join(
        f'<div class="card"><div class="k">{esc(k)}</div><div class="v">{esc(v)}</div></div>'
        for k, v in cards)

    idx_body = f"""
    <div class="note">This page ranks NFL line-origination strategies by <strong>prediction skill, not
    win rate or ROI</strong>. The headline metric is the <strong>benchmark-relative Brier skill score
    (BSS)</strong>: how much better (or worse) a strategy predicts the side it bet on than the closing
    line's own implied probability, with a game-cluster bootstrap confidence interval and a
    multiplicity-adjusted significance test. Two no-skill <strong>control baselines</strong> — random
    50/50 picks and favourites-only — are published beside every strategy so skill can be separated
    from luck. Every value carries its sample size <em>n</em>; nothing is inferred.<br>
    <span class="mut">Scope note: these are <strong>backtest skill metrics</strong> computed over the
    historical bet universe. Requirement A09 (forbid backtest numbers from the <em>live</em> promotion
    leaderboard) remains open and is tracked on the readiness register; this surface is the separate
    skill-evaluation layer, not the live leaderboard.</span></div>
    <div class="cards">{cards_html}</div>
    <h2>Strategy leaderboard — benchmark-relative Brier skill</h2>
    <p class="mut">BSS &gt; 0 = better than the market. CI is a 95% game-cluster bootstrap interval.
    p is one-sided (skill &gt; 0). q is Benjamini-Hochberg FDR across ranked strategies.</p>
    {leaderboard_table(strat)}
    <h2>Control baselines (C04) — the no-skill floor</h2>
    <p class="mut">Computed on the verified, settled results-feed universe. The market benchmark and
    favourites-only predict at the market's own implied probability, so their BSS is 0 by construction;
    their value is the ROI floor a no-skill bettor would realise.</p>
    {controls_table(ctrl)}
    <h2>Skill by market</h2>
    {permarket_table(pm)}
    <p class="mut">Sources: {link(BETS_URL, "bets.csv")} (per-bet model &amp; market probability and outcome),
    {link(RESULTS_URL, "results_feed.csv")} (verified settled universe for the controls), pinned to
    {link(NFLVERSE_URL, "nflverse @ " + PINNED_COMMIT)}.</p>
    """

    method_body = f"""
    <div class="note"><strong>What this computes.</strong> For every pre-registered strategy, the
    benchmark-relative Brier skill score (BSS) measures prediction skill against the closing line:
    BSS = Brier(model_prob, outcome) − Brier(market_prob, outcome), over settled bets (pushes excluded
    from Brier and counted separately as <em>n push</em>). <strong>Uncertainty</strong> is a
    game-cluster bootstrap — outcomes are resampled by (season, week) cluster, 2000 replicates, giving
    a 95% percentile interval and a one-sided p-value (skill &gt; 0). <strong>Multiplicity</strong> is
    controlled with Benjamini-Hochberg FDR across the ranked strategies, with Bonferroni published
    alongside. <strong>Controls</strong> are computed on the verified results-feed universe: the market
    benchmark (closing implied probability), random 50/50 picks (analytic Brier 0.25), and
    favourites-only (always the higher-implied-probability side).</div>
    <h2>Why skill, not win rate</h2>
    <p>Raw win rate and short-run ROI cannot separate skill from variance. A strategy can post a positive
    ROI over a season purely by luck; the game-cluster bootstrap and the multiplicity adjustment are
    what make a skill claim testable. A strategy is only ranked here if it has a computable
    <em>model_prob</em>; parlays are computed but held behind the joint-evidence gate (C01), and
    strategies with no probability in the pinned data are left blank and flagged.</p>
    <p><strong>Relationship to the live leaderboard.</strong> Every number on this surface is a
    <em>backtest</em> skill metric computed over the historical bet universe. Readiness requirement A09
    ("forbid backtest numbers from ever appearing on the leaderboard") is still open: the live
    promotion leaderboard must not carry these figures until A09 is satisfied. This page is the
    skill-evaluation layer, published separately so skill and luck can be judged without polluting the
    live board.</p>
    <h2>Sources (official / pinned)</h2>
    <table><thead><tr><th class="l">Source</th><th class="l">What it provides</th><th class="l">Link</th></tr></thead><tbody>
    <tr><td class="l">nflverse/nfldata (pinned)</td><td class="l">Market lines, prices and official final scores; the only source of market numbers (the NFL does not publish spreads/totals).</td><td class="l">{link(NFLVERSE_URL, "nflverse @ " + PINNED_COMMIT)}</td></tr>
    <tr><td class="l">bets.csv</td><td class="l">Per-bet model_prob, market_prob, outcome for the 11 pre-registered strategies.</td><td class="l">{link(BETS_URL, "bets.csv")}</td></tr>
    <tr><td class="l">results_feed.csv</td><td class="l">Verified, settled market-side universe (re-settled against the official score).</td><td class="l">{link(RESULTS_URL, "results_feed.csv")}</td></tr>
    <tr><td class="l">provenance.json</td><td class="l">Pinned commit, checksums and data-irregularity notes.</td><td class="l">{link(PROV_URL, "provenance.json")}</td></tr>
    </tbody></table>
    <p class="mut">Note on tiers: nflverse is an open community dataset (tier 3 in
    <a href="{PROV_URL}">provenance.json</a>), not an NFL official publication. The NFL does not publish
    point spreads, totals or prices in machine-readable form, so market numbers carry no official
    publisher; every table row links to the pinned source that provides them.</p>
    """

    flagged_body = "".join(
        f'<tr><td class="l">{esc(f["id"])}</td><td class="l">{esc(f["item"])}</td>'
        f'<td><span class="tag {"g" if f["flag"]=="GATED" else "u"}">{esc(f["flag"])}</span></td>'
        f'<td class="l">{esc(f["detail"])}</td><td class="l">{f["source"]}</td></tr>'
        for f in flags) or '<tr><td colspan="5" class="l mut">No flagged items.</td></tr>'
    flagged_body = f"""
    <div class="note">Values that cannot be computed from the pinned data are left <strong>blank</strong>
    on the dashboard and recorded here. Nothing is inferred or filled in. These items do not block the
    site; they are published so the owner can review them.</div>
    <table><thead><tr><th class="l">ID</th><th class="l">Item</th><th>Flag</th><th class="l">Detail</th><th class="l">Source</th></tr></thead>
    <tbody>{flagged_body}</tbody></table>
    """

    (BASE / "index.html").write_text(page("Skill vs Luck — Dashboard", "index", idx_body), encoding="utf-8")
    (BASE / "method.html").write_text(page("Skill vs Luck — Method & sources", "method", method_body), encoding="utf-8")
    (BASE / "flagged.html").write_text(page("Skill vs Luck — Flagged for review", "flagged", flagged_body), encoding="utf-8")
    return summary


if __name__ == "__main__":
    s = build()
    print(f"built skill_lab: {s['strategies']} strategies ({s['strategies_ranked']} ranked), "
          f"{s['strategies_bss_positive']} with BSS>0, {s['strategies_significant_bh']} significant after BH")
