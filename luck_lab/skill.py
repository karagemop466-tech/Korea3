#!/usr/bin/env python3
"""Proper-score skill table: benchmark-relative, game-clustered, multiplicity-adjusted.

The brief asks for this and no page did it before:

  "Rank by benchmark-relative Brier skill with a game-cluster lower bound and a multiplicity
   adjustment for the number of trials. Raw win rate and short-run ROI cannot distinguish skill
   from variance."

`data/derived/bets.csv` is the only ledger in this repository that carries a model probability
*and* a de-vigged market probability on every bet, which is what a proper score needs. Each
strategy in it is scored on three windows:

  backtest   seasons 2006-2025 -- the frozen evaluation window in line_lab's protocol; the
             numbers on this table must reconcile with `data/derived/summary.json`, and
             `luck_lab/check.py` asserts that they do, row by row.
  holdout    2023-2025, the out-of-sample slice of that window.
  forward    2026, the season the ledger has been accumulating into since the protocol froze.

Per strategy: Brier skill score against the closing line (1 - BS_model / BS_market), log-loss
gain, calibration and five reliability bins, per-bet ROI with a game-cluster bootstrap lower
bound printed next to the iid one, the share of profit made by the single best game, the
residual against the closing consensus, bets-needed-to-significance, and a Benjamini-Hochberg
q over the whole tested family.

Two honest labelling rules:
  * `strategy_id` S1..S11 here is line_lab's ledger; `data/derived/gates_results.csv` re-uses
    S01..S18 for different rules (review-board flag X01). Every row on the page is namespaced
    `line_lab:S<n>` with its ledger named, so no score can be read from the wrong book.
  * Backtest columns are labelled *backtest* everywhere. The brief forbids a backtest number
    entering a live ranking, and the promotion decision is made on the escrow ledger
    (`luck_lab/escrow.py`), which starts empty.

Prices and outcomes are tier `dataset`: usable to score, never citable as a league fact.
"""
from __future__ import annotations

import csv
import json
import math
import sys
from pathlib import Path

import os

sys.path.insert(0, str(Path(__file__).resolve().parent))
DATA_DIR = Path(os.environ.get("LUCK_LAB_DATA", str(Path(__file__).resolve().parent / "data")))
from lib import (HERE, american_profit, bets_to_significance, bh_qvalues,  # noqa: E402
                 cluster_bootstrap, cluster_bootstrap_ratio, mean, num, rel, sd, wilson_ci)

BETS = HERE.parent / "data" / "derived" / "bets.csv"
SUMMARY = HERE.parent / "data" / "derived" / "summary.json"
OUT = DATA_DIR / "skill.json"
N_BOOT = 2000
FDR = 0.10
MIN_GAMES = 500
# The protocol line_lab froze in data/derived/summary.json:protocol. Read, not restated.
WINDOW_PRIMARY = "backtest_2006_2025"
WINDOW_HOLDOUT = "holdout_2023_2025"
WINDOW_FORWARD = "forward_2026"

DIVISION = {"ATS": "singles - side", "TOTAL": "singles - total", "ML": "singles - moneyline",
            "PARLAY": "parlay", "FUTURES": "futures (season, not a game market)"}


def clip(p: float) -> float:
    return min(max(p, 1e-6), 1 - 1e-6)


def reliability_bins(rows: list[tuple[float, float]], k: int = 5) -> list[dict]:
    """k equal-count bins of predicted probability against realised frequency."""
    if not rows:
        return []
    rows = sorted(rows, key=lambda t: t[0])
    n = len(rows)
    out = []
    for b in range(k):
        chunk = rows[(b * n) // k:((b + 1) * n) // k]
        if not chunk:
            continue
        preds = [p for p, _ in chunk]
        ys = [y for _, y in chunk]
        out.append({"bin": b + 1, "n": len(chunk), "mean_pred": mean(preds), "realised": mean(ys),
                    "gap": mean(ys) - mean(preds), "pred_min": min(preds), "pred_max": max(preds)})
    return out


def evaluate(sid: str, meta: dict, bets: list[dict], do_boot: bool = True) -> dict:
    """One strategy on one window. Push/void rows keep their 0 stake in the ROI denominator,
    which is the convention line_lab's `strategy_metrics` uses (pnl.mean() over all rows)."""
    n_all = len(bets)
    if n_all == 0:
        # An empty window is a fact to publish, not a zero to average over: nothing in the
        # ledger for this strategy falls inside the frozen window.
        return {"strategy": sid, "n_bets": 0, "n_decisive": 0, "n_games": 0, "wins": 0,
                "losses": 0, "pushes": 0, "hit_rate": None, "hit_ci": None, "profit_units": None,
                "roi": None, "roi_sd": None, "roi_se_iid": None, "roi_cluster_lb95": None,
                "brier_model": None, "brier_market_benchmark": None, "brier_skill": None,
                "brier_skill_lb95": None, "brier_skill_p_le_zero": None, "seasons": 0,
                "season_roi": {}, "empty_window": True,
                "note": "No rows for this strategy fall inside the evaluation window above.",
                "expected_roi_under_closing_consensus": None,
                "residual_vs_closing_consensus": None}
    settled = [b for b in bets if b["outcome"] != 0]
    wins = sum(1 for b in settled if b["outcome"] > 0)
    losses = len(settled) - wins
    pushes = n_all - len(settled)

    pnls_all = [b["pnl"] for b in bets]
    roi = mean(pnls_all)
    roi_sd = sd(pnls_all)
    profit = sum(pnls_all)

    bygame: dict[str, list[float]] = {}
    for b in bets:
        bygame.setdefault(b["game_id"], []).append(b["pnl"])
    roi_clusters = [(sum(v), len(v)) for v in bygame.values()]
    roi_boot = cluster_bootstrap(roi_clusters, N_BOOT) if do_boot else None

    scored = [b for b in settled if b["model_prob"] is not None and b["market_prob"] is not None]
    bs_model = bs_mkt = ll_model = ll_mkt = bss = llr = None
    bss_boot = ll_boot = None
    if scored:
        y = [1.0 if b["outcome"] > 0 else 0.0 for b in scored]
        bs_model = mean([(b["model_prob"] - yy) ** 2 for b, yy in zip(scored, y)])
        bs_mkt = mean([(b["market_prob"] - yy) ** 2 for b, yy in zip(scored, y)])
        ll_model = mean([-(yy * math.log(clip(b["model_prob"])) + (1 - yy) * math.log(1 - clip(b["model_prob"])))
                         for b, yy in zip(scored, y)])
        ll_mkt = mean([-(yy * math.log(clip(b["market_prob"])) + (1 - yy) * math.log(1 - clip(b["market_prob"])))
                       for b, yy in zip(scored, y)])
        bss = (1 - bs_model / bs_mkt) if bs_mkt else None
        llr = ll_mkt - ll_model
        gsum: dict[str, list[float]] = {}
        gsum_ll: dict[str, list[float]] = {}
        for b, yy in zip(scored, y):
            d = gsum.setdefault(b["game_id"], [0.0, 0.0])
            d[0] += (b["market_prob"] - yy) ** 2 - (b["model_prob"] - yy) ** 2
            d[1] += (b["market_prob"] - yy) ** 2
            llm = -(yy * math.log(clip(b["model_prob"])) + (1 - yy) * math.log(1 - clip(b["model_prob"])))
            llk = -(yy * math.log(clip(b["market_prob"])) + (1 - yy) * math.log(1 - clip(b["market_prob"])))
            g2 = gsum_ll.setdefault(b["game_id"], [0.0, 0.0])
            g2[0] += llk - llm
            g2[1] += 1
        if do_boot:
            bss_boot = cluster_bootstrap_ratio([(v[0], v[1]) for v in gsum.values()], N_BOOT)
            ll_boot = cluster_bootstrap([(v[0], v[1]) for v in gsum_ll.values()], N_BOOT)

    exp_rows, usable = [], []
    price_missing = 0
    for b in settled:
        if b["market_prob"] is None or b["price"] is None:
            if b["price"] is None:
                price_missing += 1
            continue
        usable.append(b)
        exp_rows.append(b["market_prob"] * american_profit(b["price"], 1.0) - (1.0 - b["market_prob"]))
    exp_roi = mean(exp_rows) if exp_rows else None
    resid_clusters = [(b["pnl"] - e, 1) for b, e in zip(usable, exp_rows)]
    resid_boot = cluster_bootstrap(resid_clusters, N_BOOT) if (resid_clusters and do_boot) else None

    cal_pairs = [(b["model_prob"], 1.0 if b["outcome"] > 0 else 0.0) for b in scored]
    mean_pred = mean([p for p, _ in cal_pairs]) if cal_pairs else None
    realised = mean([y for _, y in cal_pairs]) if cal_pairs else None

    per_game = sorted(((g, sum(v)) for g, v in bygame.items()), key=lambda t: -t[1])
    best5 = sum(v for _, v in per_game[:5])
    best5_bets = sum(len(bygame[g]) for g, _ in per_game[:5])

    by_season: dict[int, list[float]] = {}
    for b in bets:
        by_season.setdefault(b["season"], []).append(b["pnl"])
    season_roi = {str(s): mean(v) for s, v in sorted(by_season.items())}

    hit = (wins / len(settled)) if settled else None
    z_iid = (roi / (roi_sd / math.sqrt(n_all))) if (roi_sd and n_all >= 2) else None
    inflation = None
    if roi_boot and roi_sd and n_all >= 2 and roi_sd / math.sqrt(n_all) > 0:
        inflation = roi_boot["sd"] / (roi_sd / math.sqrt(n_all))
    se_eff = (roi_sd / math.sqrt(n_all)) * inflation if (roi_sd and inflation) else (roi_sd / math.sqrt(n_all) if roi_sd else None)
    n_needed = bets_to_significance(roi, (roi_sd * inflation) if inflation else roi_sd)

    return {
        "strategy": sid,
        "name": meta.get("name", ""),
        "market": meta.get("market", ""),
        "division": meta.get("division", ""),
        "n_bets": n_all,
        "n_decisive": len(settled),
        "n_games": len(bygame),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "hit_rate": hit,
        "hit_ci": list(wilson_ci(wins, len(settled))) if settled else None,
        "profit_units": profit,
        "roi": roi,
        "roi_sd": roi_sd,
        "roi_se_iid": (roi_sd / math.sqrt(n_all)) if roi_sd else None,
        "iid_inflation_cluster_over_iid": inflation,
        "roi_cluster_ci": [roi_boot["ci_low"], roi_boot["ci_high"]] if roi_boot else None,
        "roi_cluster_lb95": roi_boot["lb95"] if roi_boot else None,
        "roi_cluster_p_le_zero": roi_boot["p_le_zero"] if roi_boot else None,
        "roi_z_iid": z_iid,
        "brier_model": bs_model,
        "brier_market_benchmark": bs_mkt,
        "brier_skill": bss,
        "brier_skill_point_bootstrapped": bss_boot["point"] if bss_boot else None,
        "brier_skill_ci": [bss_boot["ci_low"], bss_boot["ci_high"]] if bss_boot else None,
        "brier_skill_lb95": bss_boot["lb95"] if bss_boot else None,
        "brier_skill_p_le_zero": bss_boot["p_le_zero"] if bss_boot else None,
        "brier_scored_bets": len(scored),
        "logloss_model": ll_model,
        "logloss_market_benchmark": ll_mkt,
        "logloss_gain_vs_market": llr,
        "logloss_gain_lb95": ll_boot["lb95"] if ll_boot else None,
        "mean_model_prob": mean_pred,
        "realised_win_rate": realised,
        "calibration_gap": (realised - mean_pred) if (realised is not None and mean_pred is not None) else None,
        "reliability_bins": reliability_bins(cal_pairs),
        "share_of_profit_from_best_game": (per_game[0][1] / profit) if (per_game and profit > 0) else None,
        "profit_ex_best5": profit - best5,
        "roi_ex_best5": ((profit - best5) / (n_all - best5_bets)) if n_all > best5_bets else None,
        "expected_roi_under_closing_consensus": exp_roi,
        "residual_vs_closing_consensus": (roi - exp_roi) if (roi is not None and exp_roi is not None) else None,
        "residual_cluster_lb95": resid_boot["lb95"] if resid_boot else None,
        "seasons": len(season_roi),
        "season_roi": season_roi,
        "positive_season_share": (sum(1 for v in season_roi.values() if v > 0) / len(season_roi)) if season_roi else None,
        "bets_to_significance_95": n_needed,
        "price_mean": mean([b["price"] for b in settled if b["price"] is not None]) if settled else None,
        "bets_without_a_price": price_missing,
        "probs_present": len(scored),
    }


def main() -> int:
    rows = list(csv.DictReader(open(BETS, encoding="utf-8", newline="")))
    per: dict[str, list[dict]] = {}
    meta: dict[str, dict] = {}
    for r in rows:
        sid = r["strategy_id"]
        mkt = (r["market"] or "").upper()
        season = int(num(r["season"]) or 0)
        try:
            outcome = int(float(r["outcome"]))
        except ValueError:
            outcome = 0
        bet = {
            "game_id": r["game_id"], "season": season, "week": int(num(r["week"]) or 0),
            "outcome": outcome, "pnl": num(r["pnl"]) if num(r["pnl"]) is not None else 0.0,
            "price": num(r["price"]), "model_prob": num(r["model_prob"]),
            "market_prob": num(r["market_prob"]),
        }
        per.setdefault(sid, []).append(bet)
        m = meta.setdefault(sid, {"name": r["strategy_name"], "market": mkt,
                                 "division": DIVISION.get(mkt, mkt.lower())})

    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    proto = summary.get("protocol", {})
    ew = proto.get("eval_window") or [2006, 2025]
    lo, hi = min(ew), max(ew)
    hw = proto.get("holdout") or [2023, 2024, 2025]
    hlo, hhi = min(hw), max(hw)

    results = []
    for sid in sorted(per, key=lambda s: int(s[1:])):
        allbets = per[sid]
        primary = [b for b in allbets if lo <= b["season"] <= hi]
        hold = [b for b in allbets if hlo <= b["season"] <= hhi]
        fwd = [b for b in allbets if b["season"] > hi]
        row = evaluate(sid, meta[sid], primary, do_boot=True)
        row["window"] = WINDOW_PRIMARY
        row["window_bounds"] = [lo, hi]
        row["holdout"] = evaluate(f"{sid}h", meta[sid], hold, do_boot=False)
        row["forward"] = evaluate(f"{sid}f", meta[sid], fwd, do_boot=False)
        row["rows_outside_window"] = len(allbets) - len(primary)
        # Independent recomputation of the number line_lab already published.
        pub = next((s for s in summary.get("strategies", []) if s["id"] == sid), None)
        rec = {"published_found": bool(pub)}
        if pub:
            mf = pub.get("metrics_full", {})
            checks = [
                ("bets", mf.get("bets"), row["n_bets"], 0),
                ("wins", mf.get("wins"), row["wins"], 0),
                ("losses", mf.get("losses"), row["losses"], 0),
                ("pushes", mf.get("pushes"), row["pushes"], 0),
                ("roi", mf.get("roi"), row["roi"], 1e-9),
                ("pnl_units", mf.get("pnl_units"), row["profit_units"], 1e-9),
                ("win_rate", mf.get("win_rate"), row["hit_rate"], 1e-9),
                ("brier_model", mf.get("brier_model"), row["brier_model"], 1e-9),
                ("brier_market", mf.get("brier_market"), row["brier_market_benchmark"], 1e-9),
                ("brier_skill", mf.get("brier_skill"), row["brier_skill"], 1e-9),
                ("logloss_model", mf.get("logloss_model"), row["logloss_model"], 1e-9),
                ("logloss_market", mf.get("logloss_market"), row["logloss_market_benchmark"], 1e-9),
            ]
            rec["checks"] = []
            for name, a, b, tol in checks:
                ok = rel(a, b, tol_abs=tol or 1e-9) if isinstance(a, float) or isinstance(b, float) else (a == b)
                rec["checks"].append({"field": name, "published": a, "recomputed": b,
                                      "match": bool(ok),
                                      "delta": (abs(a - b) if (a is not None and b is not None
                                                                and isinstance(a, float) and isinstance(b, float)) else None)})
            rec["matched"] = sum(1 for c in rec["checks"] if c["match"])
            rec["total"] = len(rec["checks"])
        row["reconciliation_with_line_lab"] = rec
        results.append(row)

    pairs = [(r["strategy"], r["brier_skill_p_le_zero"]) for r in results if r.get("brier_skill_p_le_zero") is not None]
    q = bh_qvalues(pairs)
    m_family = len(pairs)
    for r in results:
        r["bh_q_brier_skill"] = q.get(r["strategy"])
        r.setdefault("empty_window", False)
        r["bh_family_size"] = m_family
        r["qualified_proper_score"] = bool(
            r.get("brier_skill_lb95") is not None and r["brier_skill_lb95"] > 0
            and r.get("bh_q_brier_skill") is not None and r["bh_q_brier_skill"] < FDR
            and r.get("n_games", 0) >= MIN_GAMES
        )
        r["rank_by_skill_lb95"] = None
        r["demotion_watch"] = bool(r.get("roi_cluster_lb95") is not None and r["roi_cluster_lb95"] < 0)
        # A lucky forward run must not rescue a bad signal: report the forward number only.
        r["forward_roi_only_for_escrow"] = r["forward"].get("roi")

    doc = {
        "_meta": {
            "generated_by": "luck_lab/skill.py",
            "session": "arena/fcac3e4f-korea3",
            "ledger": "data/derived/bets.csv",
            "ledger_rows": len(rows),
            "ledger_namespace": "S1..S11 here are line_lab's; data/derived/gates_results.csv uses S01..S18 for other rules (flag X01).",
            "strategies": len(results),
            "protocol_source": "data/derived/summary.json:protocol (eval_window, holdout, bootstrap resamples, FDR level)",
            "protocol": proto,
            "benchmark": ("the de-vigged closing market probability on the same bet (market_prob). "
                          "Brier skill = 1 - mean((p_model-y)^2)/mean((p_market-y)^2); the benchmark is the "
                          "closing line, so a positive lower bound means the model beat the consensus on "
                          "probability, not that one settlement went well."),
            "cluster": ("game_id. A parlay's legs live inside one game and are not two observations; the iid "
                        "interval is printed beside the cluster interval and `iid_inflation_cluster_over_iid` "
                        "is how much the naive interval was too narrow."),
            "multiplicity": (f"Benjamini-Hochberg over the {m_family} strategies with both probabilities present, "
                             f"at q < {FDR}. m is published with every q so the reader can see the size of the family "
                             "the p-value was adjusted for."),
            "roi_convention": ("pnl.mean() over every staked row including pushes, matching "
                               "line_lab/evaluation.py:strategy_metrics. `n_decisive` excludes pushes for the win-rate "
                               "columns, which is what a break-even rate must be compared with."),
            "promotion_rule": ("qualified_proper_score = Brier-skill lower bound > 0 AND BH q < "
                               f"{FDR} AND distinct games >= {MIN_GAMES} on the backtest window. Promotion is still "
                               "blocked until the escrow ledger carries a prospective sample (luck_lab/escrow.py)."),
            "price_tier": "dataset - closing prices from the pinned nflverse file. Not an official source.",
            "backtest_bar": ("Every ROI column on this table is backtest. The brief forbids them appearing on the "
                             "live leaderboard; they appear here on the audit surface, labelled, and nowhere else."),
        },
        "rows": results,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    # Rank on the lower bound of the skill score, not on the point estimate: a rank is a claim
    # that one strategy is better, which is only supported if the bounds separate.
    ranked = sorted([r for r in results if r.get("brier_skill_lb95") is not None],
                    key=lambda r: -r["brier_skill_lb95"])
    for i, r in enumerate(ranked, 1):
        r["rank_by_skill_lb95"] = i
    fmt = lambda v, spec="+.5f": (format(v, spec) if isinstance(v, (int, float)) else "  -- n/a --")  # noqa: E731
    print(f"skill: {len(results)} strategies over {len(rows)} ledger rows -> luck_lab/data/skill.json")
    for r in results:
        rec = r["reconciliation_with_line_lab"]
        print(f"  {r['strategy']:4s} n={r['n_bets']:5d} games={r['n_games']:5d} roi={fmt(r['roi'],'+.4f')} "
              f"lb={fmt(r.get('roi_cluster_lb95'),'+.4f')} bss={fmt(r.get('brier_skill'))} "
              f"lb95={fmt(r.get('brier_skill_lb95'))} q={fmt(r.get('bh_q_brier_skill'),'.3f')} "
              f"recon={rec.get('matched', 0)}/{rec.get('total', 0)}")
    print(f"  ranked by skill lower bound: {[r['strategy'] for r in ranked]}")
    print(f"  any qualified: {any(r['qualified_proper_score'] for r in results)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
