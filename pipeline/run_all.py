#!/usr/bin/env python3
"""Run the full research pipeline and write data/derived/summary.json.

    python3 -m pipeline.run_all        # from the repository root

Outputs
-------
data/derived/features.csv      pre-game features, one row per completed REG game
data/derived/live_candidates.csv  scheduled games without a result
data/derived/bets.csv          every pre-registered selection with its settlement
data/derived/summary.json      everything the static site renders
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import correlations as corr
from . import evaluation as ev
from . import markets as mk
from . import extras as ex
from . import props
from .core import load_games, build_features, load_manifest
from .strategies import STRATEGIES, build_all_bets

ROOT = Path(__file__).resolve().parents[1]
DERIVED = ROOT / "data" / "derived"


def _json_safe(obj):
    if isinstance(obj, dict):
        return {str(k): _json_safe(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_json_safe(v) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return None if np.isnan(obj) else float(obj)
    if isinstance(obj, float):
        return None if np.isnan(obj) or np.isinf(obj) else obj
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    if isinstance(obj, pd.Timestamp):
        return obj.strftime("%Y-%m-%dT%H:%M:%SZ")
    return obj


def predict_live(feats: pd.DataFrame, live: pd.DataFrame, season: int) -> pd.DataFrame:
    """Fit on every season before `season` and emit model lines for unplayed games."""
    if live.empty:
        return live
    train = feats[feats["season"] < season]
    if len(train) < 400:
        return live.assign(model_spread=np.nan)
    design_m = np.column_stack([
        np.ones(len(train)), train["elo_diff"].to_numpy(float),
        train["rest_diff"].fillna(0.0).to_numpy(float),
        train["qb_change_home"].to_numpy(float), train["qb_change_away"].to_numpy(float),
    ])
    beta_m, *_ = np.linalg.lstsq(design_m, train["result"].to_numpy(float), rcond=None)
    resid = train["result"].to_numpy(float) - design_m @ beta_m
    sigma_m = float(resid.std(ddof=design_m.shape[1]))

    design_t = np.column_stack([
        np.ones(len(train)), train["off_home"].to_numpy(float), train["def_home"].to_numpy(float),
        train["off_away"].to_numpy(float), train["def_away"].to_numpy(float),
        train["indoor"].to_numpy(float),
    ])
    beta_t, *_ = np.linalg.lstsq(design_t, train["total"].to_numpy(float), rcond=None)
    resid_t = train["total"].to_numpy(float) - design_t @ beta_t
    sigma_t = float(resid_t.std(ddof=design_t.shape[1]))

    out = live.copy()
    xm = np.column_stack([
        np.ones(len(out)), out["elo_diff"].to_numpy(float),
        out["rest_diff"].fillna(0.0).to_numpy(float),
        out["qb_change_home"].to_numpy(float), out["qb_change_away"].to_numpy(float),
    ])
    xt = np.column_stack([
        np.ones(len(out)), out["off_home"].to_numpy(float), out["def_home"].to_numpy(float),
        out["off_away"].to_numpy(float), out["def_away"].to_numpy(float),
        out["indoor"].to_numpy(float),
    ])
    out["model_spread"] = xm @ beta_m
    out["model_total"] = xt @ beta_t
    out["sd_spread"] = sigma_m
    out["sd_total"] = sigma_t
    from math import erf, sqrt
    z = (out["model_spread"] / sigma_m).to_numpy(float)
    cdf = np.array([0.5 * (1.0 + erf(x / sqrt(2.0))) for x in z])
    out["model_home_win_prob"] = cdf
    out["model_away_win_prob"] = 1.0 - cdf
    return out


def main() -> int:
    DERIVED.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest()
    games = load_games()
    feats, live = build_features(games)

    feats = feats.sort_values(["kickoff", "game_id"]).reset_index(drop=True)
    from .strategies import add_walk_forward_predictions
    feats = add_walk_forward_predictions(feats, first_eval=mk.EVAL_START)
    feats.drop(columns=["kickoff"]).to_csv(DERIVED / "features.csv", index=False)
    live.to_csv(DERIVED / "live_candidates.csv", index=False)

    coverage_out = {}
    for season, chunk in feats.groupby("season"):
        coverage_out[int(season)] = {
            "games": int(len(chunk)),
            "with_spread_price": int(chunk["home_spread_odds"].notna().sum()),
            "with_total_price": int(chunk["over_odds"].notna().sum()),
            "with_moneyline": int(chunk["home_moneyline"].notna().sum()),
        }
    (DERIVED / "coverage.json").write_text(json.dumps(coverage_out, indent=2) + "\n", encoding="utf-8")

    bets = build_all_bets(feats, eval_start=mk.EVAL_START)
    bets.to_csv(DERIVED / "bets.csv", index=False)
    print(f"bets: {len(bets)}")

    primary = bets[bets["season"].between(mk.EVAL_START, mk.EVAL_END)]
    holdout = bets[bets["season"].between(mk.HOLDOUT[0], mk.HOLDOUT[-1])]
    forward = bets[bets["season"] == 2026]

    window = feats[feats["season"].between(mk.EVAL_START, mk.EVAL_END)]
    priced_share = {
        m: float(_priced_share(window, m)) for m in ("ATS", "TOTAL", "ML")
    }
    universe_tests = {m: ev.universe_brier(window, m) for m in ("ATS", "TOTAL", "ML")}

    rows = []
    pvals = {}
    for sid, name, market in STRATEGIES:
        sub = primary[primary["strategy_id"] == sid]
        sub_hold = holdout[holdout["strategy_id"] == sid]
        sub_fwd = forward[forward["strategy_id"] == sid]
        if sub.empty:
            continue
        metrics = ev.strategy_metrics(sub)
        hold_metrics = ev.strategy_metrics(sub_hold)
        fwd_metrics = ev.strategy_metrics(sub_fwd)
        market_test = universe_tests.get(market)
        if market in ("PARLAY", "FUTURES"):
            market_test = None
        perm = ev.permutation_percentile(sub, feats, market)
        share = priced_share.get(market, priced_share["ATS"] if market == "PARLAY" else None)
        rows.append({
            "id": sid, "name": name, "market": market,
            "metrics_full": metrics, "holdout": hold_metrics, "forward_2026": fwd_metrics,
            "market_test": market_test, "permutation": perm, "priced_share": share,
            "brier_skill": (market_test or {}).get("brier_skill", metrics.get("brier_skill")),
        })
        if metrics.get("p_value") is not None:
            pvals[sid] = metrics["p_value"]

    qvals = ev.bh_fdr(pvals, q=0.10)

    causality_ok = (ROOT / "data" / "derived" / "causality_ok.flag").exists()
    for row in rows:
        row["q_value"] = qvals.get(row["id"])
        row["gates"] = ev.evaluate_gates(
            row["metrics_full"], row["holdout"], row["market_test"], row["q_value"],
            row["permutation"], causality_ok, row["priced_share"] or 1.0,
        )
        row["gate_passes"] = ev.gate_score(row["gates"])
        row["eligible"] = all(v == "pass" for v in row["gates"].values())
        if row["market_test"] is None and row["metrics_full"].get("brier_skill") is not None:
            row["gates"]["G6"] = "pass" if row["metrics_full"]["brier_skill"] >= 0 else "fail"
            row["gate_passes"] = ev.gate_score(row["gates"])
            row["eligible"] = all(v == "pass" for v in row["gates"].values())

    eligible_rows = [r for r in rows if r["eligible"]]
    rewards = ev.reward_points(eligible_rows)
    for row in rows:
        row["reward_points"] = rewards.get(row["id"])

    corr_out = corr.build_correlations(feats, primary)
    extras_out = ex.build_extras(window, primary)
    accuracy = {}
    for label, model_col, line_col, actual_col in [
        ("spread", "mu_spread", "spread_line", "result"),
        ("total", "mu_total", "total_line", "total"),
    ]:
        d = window.dropna(subset=[model_col, line_col, actual_col])
        accuracy[label] = {
            "games": int(len(d)),
            "model_rmse": float(np.sqrt(((d[actual_col] - d[model_col]) ** 2).mean())),
            "market_rmse": float(np.sqrt(((d[actual_col] - d[line_col]) ** 2).mean())),
            "model_corr": float(np.corrcoef(d[model_col], d[actual_col])[0, 1]),
            "market_corr": float(np.corrcoef(d[line_col], d[actual_col])[0, 1]),
        }
    props_out = props.run()
    live_pred = predict_live(feats, live, 2026)

    next_week = None
    upcoming = live_pred[live_pred["spread_line"].notna()]
    if not upcoming.empty:
        upcoming = upcoming.sort_values("kickoff")
        first_kick = upcoming["kickoff"].min()
        slate = upcoming[upcoming["kickoff"] <= first_kick + pd.Timedelta(days=7)]
        next_week = int(slate["week"].iloc[0])

    live_rows = []
    for rec in live_pred.itertuples(index=False):
        if pd.isna(rec.model_spread):
            continue
        market_edge = None
        if pd.notna(rec.spread_line):
            market_edge = float(rec.model_spread - rec.spread_line)
        live_rows.append({
            "game_id": rec.game_id, "week": int(rec.week),
            "kickoff": rec.kickoff.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "home_team": rec.home_team, "away_team": rec.away_team,
            "market_spread": None if pd.isna(rec.spread_line) else float(rec.spread_line),
            "market_total": None if pd.isna(rec.total_line) else float(rec.total_line),
            "model_spread": float(rec.model_spread), "model_total": float(rec.model_total),
            "model_home_win_prob": float(rec.model_home_win_prob),
            "model_away_win_prob": float(rec.model_away_win_prob),
            "spread_gap": market_edge,
        })

    summary = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "pinned_commit": manifest["pinned_commit"],
        "commit_url": manifest["commit_url"],
        "files": manifest["files"],
        "universe": {
            "reg_completed_games": int(len(feats)),
            "first_season": int(feats["season"].min()),
            "last_season": int(feats["season"].max()),
            "window_games": int(len(window)),
            "priced_games": {k: int(round(v * len(window))) for k, v in priced_share.items()},
            "priced_share": priced_share,
            "holdout_games": int(len(feats[feats["season"].between(mk.HOLDOUT[0], mk.HOLDOUT[-1])])),
            "forward_games": int((feats["season"] == 2026).sum()),
            "unplayed_games": int(len(live)),
        },
        "protocol": {
            "edge_min": mk.EDGE_MIN, "price_min": mk.PRICE_MIN, "price_max": mk.PRICE_MAX,
            "eval_window": [mk.EVAL_START, mk.EVAL_END], "holdout": list(mk.HOLDOUT),
            "bootstrap_resamples": ev.N_BOOT, "permutation_resamples": ev.N_PERM,
            "seed": ev.SEED, "fdr_level": 0.10,
        },
        "strategies": rows,
        "family": {"tests": len(pvals), "p_values": pvals, "q_values": {k: v for k, v in qvals.items() if k != "_q_level"}},
        "leaderboard": sorted(
            [{
                "id": r["id"], "name": r["name"], "market": r["market"],
                "gates_passed": r["gate_passes"], "eligible": r["eligible"],
                "reward_points": r["reward_points"],
                "full_roi": r["metrics_full"].get("roi"),
                "full_ci_low": r["metrics_full"].get("roi_ci_low"),
                "holdout_roi": r["holdout"].get("roi"),
                "holdout_ci_low": r["holdout"].get("roi_ci_low"),
                "holdout_bets": r["holdout"].get("bets"),
                "brier_skill": r["brier_skill"],
                "permutation_percentile": r["permutation"].get("percentile"),
                "bets": r["metrics_full"].get("bets"),
                "seasons": r["metrics_full"].get("seasons"),
            } for r in rows],
            key=lambda x: (-x["gates_passed"], -(x["holdout_ci_low"] if x["holdout_ci_low"] is not None else -9)),
        ),
        "correlations": corr_out,
        "extras": extras_out,
        "accuracy": accuracy,
        "props": props_out,
        "live": {"season": 2026, "next_week": next_week, "rows": live_rows},
        "coverage": coverage_out,
        "causality": causality_ok,
    }
    (DERIVED / "summary.json").write_text(
        json.dumps(_json_safe(summary), indent=2) + "\n", encoding="utf-8")
    print("wrote data/derived/summary.json")

    for row in summary["leaderboard"]:
        print(f"{row['id']:<4} {row['name'][:38]:<38} gates={row['gates_passed']}/9 "
              f"roi={row['full_roi'] if row['full_roi'] is None else round(row['full_roi']*100,2)}% "
              f"hold={row['holdout_roi'] if row['holdout_roi'] is None else round(row['holdout_roi']*100,2)}% "
              f"bets={row['bets']}")
    return 0


def _priced_share(window: pd.DataFrame, market: str) -> float:
    if window.empty:
        return 0.0
    if market == "ATS":
        ok = window["home_spread_odds"].notna() & window["away_spread_odds"].notna()
    elif market == "TOTAL":
        ok = window["over_odds"].notna() & window["under_odds"].notna()
    else:
        ok = window["home_moneyline"].notna() & window["away_moneyline"].notna()
    return float(ok.mean())


if __name__ == "__main__":
    raise SystemExit(main())
