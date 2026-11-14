#!/usr/bin/env python3
"""Signal/staking separation and the demotion gate, computed from the committed ledger.

All arithmetic is stdlib-only and deterministic (fixed seed). Three rules govern it:

1. SIGNAL and STAKING are computed from disjoint columns of the same bets and are never
   combined into one ranking. The signal view uses only probability quality against the
   market (Brier, mirroring line_lab/evaluation.py's published definition, y = outcome > 0);
   the staking view uses only flat-stake cash flows.
2. Every confidence interval is a week-block bootstrap (resample (season, week) blocks with
   replacement, same block count as observed, fixed seed, 2,000 draws) — the convention the
   published leaderboard already uses.
3. The demotion gate is published as a rule and *demonstrated* on paper strategies as an
   explicitly-labelled dry run. No strategy in this repository is live (0 of 11 pass the
   nine promotion gates), so the gate's live set is empty and nothing here is a statement
   about a live position.

Usage:
    python3 ops_lab/metrics.py
"""
from __future__ import annotations

import csv
import json
import random
import statistics
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"

SEED = 20261114
ITERS = 2000
WINDOW = 100
STEP = 50


def load_bets() -> dict[str, list[dict]]:
    per: dict[str, list[dict]] = {}
    with open(ROOT / "data/derived/bets.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            r["season_i"] = int(r["season"])
            r["week_i"] = int(r["week"])
            r["pnl_f"] = float(r["pnl"]) if r["pnl"] else 0.0
            r["outcome_i"] = int(float(r["outcome"]))
            per.setdefault(r["strategy_id"], []).append(r)
    for s in per:
        per[s].sort(key=lambda r: (r["season_i"], r["week_i"], r["game_id"]))
    return per


EVAL_START, EVAL_END = 2006, 2025  # the published leaderboard window


def load_published() -> dict[str, dict]:
    s = json.loads((ROOT / "data/derived/summary.json").read_text(encoding="utf-8"))
    return {row["id"]: row for row in s["leaderboard"]}


def week_blocks(rows: list[dict]) -> dict[tuple, list[dict]]:
    blocks: dict[tuple, list[dict]] = {}
    for r in rows:
        blocks.setdefault((r["season_i"], r["week_i"]), []).append(r)
    return blocks


def bootstrap_ci(block_stat: list[float], iters: int = ITERS) -> tuple[float, float]:
    """Percentile bootstrap over per-block statistics (fixed seed)."""
    rng = random.Random(SEED)
    dist = []
    m = len(block_stat)
    for _ in range(iters):
        dist.append(statistics.fmean(block_stat[rng.randrange(m)] for _ in range(m)))
    dist.sort()
    return dist[int(0.025 * (iters - 1))], dist[int(0.975 * (iters - 1))]


def brier_block_stats(rows: list[dict]) -> list[float]:
    """Per-week-block Brier skill of the model against the de-vigged market."""
    out = []
    for _, block in week_blocks(rows).items():
        scored = [r for r in block if r["model_prob"] and r["market_prob"]]
        if not scored:
            continue
        bm = statistics.fmean((float(r["model_prob"]) - (1 if r["outcome_i"] > 0 else 0)) ** 2 for r in scored)
        bmk = statistics.fmean((float(r["market_prob"]) - (1 if r["outcome_i"] > 0 else 0)) ** 2 for r in scored)
        out.append(1 - bm / bmk if bmk else float("nan"))
    return out


def roi_block_stats(rows: list[dict]) -> list[float]:
    return [statistics.fmean(r["pnl_f"] for r in block) for block in week_blocks(rows).values()]


def brier_overall(rows: list[dict]) -> dict:
    scored = [r for r in rows if r["model_prob"] and r["market_prob"]]
    if not scored:
        return {"n": 0}
    bm = statistics.fmean((float(r["model_prob"]) - (1 if r["outcome_i"] > 0 else 0)) ** 2 for r in scored)
    bmk = statistics.fmean((float(r["market_prob"]) - (1 if r["outcome_i"] > 0 else 0)) ** 2 for r in scored)
    return {"n": len(scored), "brier_model": bm, "brier_market": bmk,
            "brier_skill": 1 - bm / bmk if bmk else float("nan")}


def staking_overall(rows: list[dict]) -> dict:
    if not rows:
        return {"n": 0}
    pnl = [r["pnl_f"] for r in rows]
    cum = 0.0
    peak = 0.0
    dd = 0.0
    for x in pnl:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    by_season: dict[int, list[float]] = {}
    for r in rows:
        by_season.setdefault(r["season_i"], []).append(r["pnl_f"])
    seasons = {s: statistics.fmean(v) for s, v in by_season.items()}
    worst_season = min(seasons, key=seasons.get)
    by_week: dict[tuple, float] = {}
    for r in rows:
        by_week[(r["season_i"], r["week_i"])] = by_week.get((r["season_i"], r["week_i"]), 0.0) + r["pnl_f"]
    worst_week = min(by_week, key=by_week.get)
    return {"n": len(rows), "roi": statistics.fmean(pnl), "max_drawdown": dd,
            "worst_season": worst_season, "worst_season_roi": seasons[worst_season],
            "worst_week": f"{worst_week[0]} week {worst_week[1]}",
            "worst_week_units": by_week[worst_week],
            "weeks_total": len(by_week),
            "weeks_negative_share": sum(1 for v in by_week.values() if v < 0) / len(by_week)}


# --------------------------------------------------------------------------- #
# demotion gate
# --------------------------------------------------------------------------- #
def drawdown_band(rows: list[dict], iters: int = ITERS) -> float:
    """95th percentile of the max-drawdown distribution under week-shuffling (luck band)."""
    week_sums = [sum(r["pnl_f"] for r in block) for block in week_blocks(rows).values()]
    rng = random.Random(SEED)
    dist = []
    for _ in range(iters):
        rng.shuffle(week_sums)
        cum = 0.0
        peak = 0.0
        dd = 0.0
        for x in week_sums:
            cum += x
            peak = max(peak, cum)
            dd = max(dd, peak - cum)
        dist.append(dd)
    dist.sort()
    return dist[int(0.95 * (iters - 1))]


def window_triggers(rows: list[dict]) -> dict:
    """Dry-run D2 (signal collapse) and D3 (staking collapse) over trailing-100 windows."""
    singles = [r for r in rows if r["market"] in ("ATS", "TOTAL", "ML")]
    d2 = d3 = 0
    d2_first = d3_first = ""
    windows = d2_windows = 0
    for i in range(0, max(0, len(singles) - WINDOW + 1), STEP):
        win = singles[i:i + WINDOW]
        windows += 1
        tag = f"{win[0]['season']} w{win[0]['week']}–{win[-1]['season']} w{win[-1]['week']}"
        bs = brier_block_stats(win)
        if bs and len(bs) >= 5:
            d2_windows += 1
            skill = statistics.fmean(bs)
            _, hi = bootstrap_ci(bs)
            if skill < 0 and hi < 0:
                d2 += 1
                if not d2_first:
                    d2_first = tag
        st = roi_block_stats(win)
        if st and len(st) >= 5:
            roi = statistics.fmean(r["pnl_f"] for r in win)
            _, hi = bootstrap_ci(st)
            if roi < 0 and hi < 0:
                d3 += 1
                if not d3_first:
                    d3_first = tag
    return {"windows": windows, "d2_windows": d2_windows, "d2_triggers": d2, "d2_first": d2_first,
            "d3_triggers": d3, "d3_first": d3_first}


def snapshot_coverage(rows: list[dict]) -> dict:
    """D1: every single-market bet must have a price-snapshot row for its market side."""
    cov: dict[str, set[str]] = {}
    with open(DATA / "price_snapshots.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            cov.setdefault(r["market_uid"], set()).add(r["snapshot_type"])
    singles = [r for r in rows if r["market"] in ("ATS", "TOTAL", "ML")]
    market = {"ATS": "SPREAD", "TOTAL": "TOTAL", "ML": "MONEYLINE"}
    with_snap = 0
    for r in singles:
        if f"{r['game_id']}:{market[r['market']]}:{r['side']}" in cov:
            with_snap += 1
    parlays = sum(1 for r in rows if r["market"] == "PARLAY")
    futures = sum(1 for r in rows if r["market"] == "FUTURES")
    return {"singles": len(singles), "with_snapshot": with_snap,
            "without_snapshot": len(singles) - with_snap,
            "parlays_legs_not_in_ledger": parlays, "futures_no_feed_row": futures}


def market_move_2021(rows: list[dict]) -> dict:
    """Opening (WSGT 2021) vs betting line for the same market side — descriptive only."""
    opening: dict[str, str] = {}
    with open(DATA / "price_snapshots.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["snapshot_type"] == "opening_wsgt":
                opening[f"{r['game_id']}:{r['market']}:{r['side']}"] = r["line"]
    market = {"ATS": "SPREAD", "TOTAL": "TOTAL"}
    moves = []
    for r in rows:
        if r["season_i"] != 2021 or r["market"] not in market or not r["line"]:
            continue
        o = opening.get(f"{r['game_id']}:{market[r['market']]}:{r['side']}")
        if o:
            moves.append(float(o) - float(r["line"]))
    if not moves:
        return {"n": 0}
    return {"n": len(moves), "mean_open_minus_bet": statistics.fmean(moves),
            "share_positive": sum(1 for m in moves if m > 0) / len(moves)}


# --------------------------------------------------------------------------- #
def main() -> None:
    bets = load_bets()
    published = load_published()

    split_rows = []
    demote_rows = []
    move_rows = []
    crosscheck_failures = []
    for sid in sorted(bets):
        rows = bets[sid]
        rows_window = [r for r in rows if EVAL_START <= r["season_i"] <= EVAL_END]
        b = brier_overall(rows_window)   # signal view: published window
        s = staking_overall(rows_window)  # staking view: published window
        bci = bootstrap_ci(brier_block_stats(rows)) if b.get("n") else ("", "")
        rci = bootstrap_ci(roi_block_stats(rows)) if s.get("n") else ("", "")
        pub = published.get(sid, {})
        roi_delta = (s["roi"] - pub["full_roi"]) if "full_roi" in pub and s.get("n") else None
        brier_delta = (b["brier_skill"] - pub["brier_skill"]) if "brier_skill" in pub and b.get("n") else None
        status = "match"
        if "full_roi" in pub and roi_delta is not None and abs(roi_delta) > 5e-4:
            status = "ROI MISMATCH"
        if pub and s.get("n") and pub["bets"] != s["n"]:
            status = "BETS COUNT MISMATCH"
        # NOTE: the leaderboard column labelled per-strategy "Brier skill" is the
        # market-universe G6 diagnostic (identical for every strategy in a market),
        # so a difference against the per-strategy value is expected and is NOT a
        # cross-check failure; it is published as a flagged presentation irregularity.
        if status != "match":
            crosscheck_failures.append(sid)
        split_rows.append({
            "strategy_id": sid, "name": pub.get("name", ""), "market": pub.get("market", ""),
            "bets": s.get("n", 0),
            "signal_bets": b.get("n", 0),
            "brier_model": f"{b['brier_model']:.6f}" if b.get("n") else "",
            "brier_market": f"{b['brier_market']:.6f}" if b.get("n") else "",
            "brier_skill": f"{b['brier_skill']:.6f}" if b.get("n") else "",
            "brier_skill_ci_low": f"{bci[0]:.6f}" if b.get("n") else "",
            "brier_skill_ci_high": f"{bci[1]:.6f}" if b.get("n") else "",
            "roi": f"{s['roi']:.6f}" if s.get("n") else "",
            "roi_ci_low": f"{rci[0]:.6f}" if s.get("n") else "",
            "roi_ci_high": f"{rci[1]:.6f}" if s.get("n") else "",
            "max_drawdown_units": f"{s['max_drawdown']:.2f}" if s.get("n") else "",
            "worst_season": s.get("worst_season", ""),
            "worst_season_roi": f"{s['worst_season_roi']:.4f}" if s.get("n") else "",
            "worst_week": s.get("worst_week", ""),
            "worst_week_units": f"{s['worst_week_units']:.2f}" if s.get("n") else "",
            "weeks_negative_share": f"{s['weeks_negative_share']:.3f}" if s.get("n") else "",
            "published_full_roi": (f"{pub['full_roi']:.6f}" if pub.get("full_roi") is not None else ""),
            "published_brier_semantics": "universe-level G6 market-test value, identical within a market",
            "brier_on_own_bets_differs_from_published": "yes" if (b.get("n") and pub.get("brier_skill") is not None and abs(b["brier_skill"] - pub["brier_skill"]) > 5e-3) else "no",
            "published_brier_skill": (f"{pub['brier_skill']:.6f}" if pub.get("brier_skill") is not None else ""),
            "roi_delta": f"{roi_delta:.2e}" if roi_delta is not None else "",
            "brier_delta": f"{brier_delta:.2e}" if brier_delta is not None else "",
            "crosscheck": status,
        })

        # demotion gate rows (live set is empty; everything below is paper + dry-run)
        cov = snapshot_coverage(rows)
        trig = window_triggers(rows)
        dd_band = drawdown_band(rows) if s.get("n") else None
        d5 = "yes" if (s.get("n") and s["max_drawdown"] > dd_band) else "no"
        demote_rows.append({
            "strategy_id": sid,
            "state": "paper (0/9 promotion gates passed)",
            "d1_singles": cov["singles"], "d1_with_snapshot": cov["with_snapshot"],
            "d1_without_snapshot": cov["without_snapshot"],
            "d1_parlays_legs_not_in_ledger": cov["parlays_legs_not_in_ledger"],
            "d1_futures_no_feed_row": cov["futures_no_feed_row"],
            "windows_evaluated": trig["windows"],
            "d2_windows_evaluated": trig["d2_windows"],
            "d2_triggers": trig["d2_triggers"], "d2_first_window": trig["d2_first"],
            "d3_triggers": trig["d3_triggers"], "d3_first_window": trig["d3_first"],
            "max_drawdown_units": f"{s['max_drawdown']:.2f}" if s.get("n") else "",
            "luck_band_p95_units": f"{dd_band:.2f}" if dd_band is not None else "",
            "d5_would_trigger": d5,
        })

        mm = market_move_2021(rows)
        move_rows.append({"strategy_id": sid, **{k: (f"{v:.3f}" if isinstance(v, float) else v)
                                                  for k, v in mm.items()}})

    columns = list(split_rows[0].keys())
    with open(DATA / "leaderboard_split.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        w.writerows(split_rows)

    with open(DATA / "demotion_status.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(demote_rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(demote_rows)

    with open(DATA / "market_move_2021.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(move_rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(move_rows)

    meta = {
        "seed": SEED, "bootstrap_iters": ITERS, "window": WINDOW, "step": STEP,
        "crosscheck_failures": crosscheck_failures,
        "live_strategies": 0,
        "demotion_note": "the live set is empty: no strategy passes all nine promotion gates, "
                         "so the demotion gate is armed and applies to zero strategies; the "
                         "trigger counts are an explicitly-labelled dry run on paper strategies",
    }
    (DATA / "metrics_meta.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")

    print(f"leaderboard_split.csv: {len(split_rows)} strategies; cross-check failures: {crosscheck_failures or 'none'}")
    for r in split_rows:
        print(f"  {r['strategy_id']}: roi {r['roi']} (pub {r['published_full_roi']}, Δ {r['roi_delta']}); "
              f"brier skill {r['brier_skill']} (pub {r['published_brier_skill']}, Δ {r['brier_delta']})")
    for r in demote_rows:
        print(f"  {r['strategy_id']}: D1 {r['d1_without_snapshot']} singles w/o snapshot; "
              f"D2 {r['d2_triggers']}/{r['windows_evaluated']} windows; D3 {r['d3_triggers']}; D5 {r['d5_would_trigger']}")


if __name__ == "__main__":
    main()
