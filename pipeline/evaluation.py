#!/usr/bin/env python3
"""Evaluation: metrics, week-block bootstrap, permutation luck test, gates, FDR.

The protocol is frozen in docs/preregistration.md. Every number a page shows is
produced here from data/derived/bets.csv and data/derived/features.csv.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

from . import markets as mk

SEED = 20261101
N_BOOT = 2000
N_PERM = 2000


# --------------------------------------------------------------------------- #
# Core statistics
# --------------------------------------------------------------------------- #
def week_clusters(bets: pd.DataFrame) -> list[np.ndarray]:
    if bets.empty:
        return []
    keys = list(zip(bets["season"].to_numpy(), bets["week"].to_numpy()))
    groups: dict[tuple[int, int], list[int]] = {}
    for i, k in enumerate(keys):
        groups.setdefault(k, []).append(i)
    return [np.array(v) for v in groups.values()]


def bootstrap_roi(bets: pd.DataFrame, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Week-block bootstrap of ROI per unit; also a one-sided p-value for ROI > 0."""
    if bets.empty:
        return {"roi_ci_low": None, "roi_ci_high": None, "p_value": None}
    pnl = bets["pnl"].to_numpy(float)
    clusters = week_clusters(bets)
    rng = np.random.default_rng(seed)
    sims = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, len(clusters), len(clusters))
        idx = np.concatenate([clusters[i] for i in pick])
        sims[b] = pnl[idx].mean()
    return {
        "roi_ci_low": float(np.percentile(sims, 2.5)),
        "roi_ci_high": float(np.percentile(sims, 97.5)),
        "p_value": float((sims <= 0).mean()),
    }


def brier(p: np.ndarray, y: np.ndarray) -> float:
    return float(np.mean((p - y) ** 2))


def log_loss(p: np.ndarray, y: np.ndarray) -> float:
    p = np.clip(p, 1e-6, 1 - 1e-6)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def strategy_metrics(bets: pd.DataFrame) -> dict:
    if bets.empty:
        return {"bets": 0}
    settled = bets[bets["outcome"] != 0]
    wins = int((settled["outcome"] > 0).sum())
    losses = int((settled["outcome"] < 0).sum())
    pushes = int((bets["outcome"] == 0).sum())
    boot = bootstrap_roi(bets)
    pnl = bets["pnl"].to_numpy(float)
    cum = np.cumsum(pnl)
    drawdown = float(np.max(np.maximum.accumulate(cum) - cum)) if len(cum) else 0.0

    by_season = bets.groupby("season")["pnl"].agg(["sum", "count"])
    seasons = by_season.index.to_numpy()
    season_roi = (by_season["sum"] / by_season["count"]).to_dict()
    pos_seasons = int((by_season["sum"] > 0).sum())
    total_profit = float(pnl.sum())
    best_share = float(by_season["sum"].max() / total_profit) if total_profit > 0 else None

    scored = bets.dropna(subset=["model_prob", "market_prob"])
    scored = scored[scored["outcome"] != 0]
    brier_model = brier(scored["model_prob"].to_numpy(float), (scored["outcome"] > 0).to_numpy(float)) if len(scored) else None
    brier_market = brier(scored["market_prob"].to_numpy(float), (scored["outcome"] > 0).to_numpy(float)) if len(scored) else None

    return {
        "bets": int(len(bets)),
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_rate": wins / (wins + losses) if (wins + losses) else None,
        "push_rate": pushes / len(bets),
        "roi": float(pnl.mean()),
        "pnl_units": total_profit,
        "roi_ci_low": boot["roi_ci_low"],
        "roi_ci_high": boot["roi_ci_high"],
        "p_value": boot["p_value"],
        "avg_price": float(bets["price"].mean()) if bets["price"].notna().any() else None,
        "avg_edge": float(bets["edge"].dropna().mean()) if bets["edge"].notna().any() else None,
        "max_drawdown": drawdown,
        "seasons": int(len(seasons)),
        "season_roi": {int(k): float(v) for k, v in season_roi.items()},
        "positive_season_share": pos_seasons / len(seasons) if len(seasons) else None,
        "best_season_profit_share": best_share,
        "brier_model": brier_model,
        "brier_market": brier_market,
        "brier_skill": (1 - brier_model / brier_market) if (brier_model is not None and brier_market) else None,
        "logloss_model": log_loss(scored["model_prob"].to_numpy(float), (scored["outcome"] > 0).to_numpy(float)) if len(scored) else None,
        "logloss_market": log_loss(scored["market_prob"].to_numpy(float), (scored["outcome"] > 0).to_numpy(float)) if len(scored) else None,
    }


def segment_metrics(bets: pd.DataFrame, mask: pd.Series) -> dict:
    return strategy_metrics(bets[mask])


def bh_fdr(pvals: dict[str, float], q: float = 0.10) -> dict[str, float]:
    """Benjamini-Hochberg q-values for a family of one-sided tests."""
    items = [(k, v) for k, v in pvals.items() if v is not None and not math.isnan(v)]
    m = len(items)
    out: dict[str, float] = {}
    if m == 0:
        return out
    ordered = sorted(items, key=lambda kv: kv[1])
    prev = 1.0
    for rank in range(m, 0, -1):
        key, p = ordered[rank - 1]
        val = min(prev, p * m / rank)
        out[key] = val
        prev = val
    out["_q_level"] = q
    return out


# --------------------------------------------------------------------------- #
# Universe benchmarks (Brier vs the market on every priced game)
# --------------------------------------------------------------------------- #
def universe_brier(feats: pd.DataFrame, market: str) -> dict:
    rows = []
    for _, row in feats.iterrows():
        if pd.isna(row["mu_spread"]) or not _priced(row, market):
            continue
        fair = mk.market_prob(row, market)
        if market == "ATS":
            p_model, p_loss, _ = mk.spread_probs(row["mu_spread"], row["sd_spread"], row["spread_line"], "home")
            y = 1.0 if row["result"] - row["spread_line"] > 0 else 0.0
            if row["result"] - row["spread_line"] == 0:
                continue
        elif market == "TOTAL":
            p_model, p_loss, _ = mk.total_probs(row["mu_total"], row["sd_total"], row["total_line"], "over")
            y = 1.0 if row["total"] - row["total_line"] > 0 else 0.0
            if row["total"] - row["total_line"] == 0:
                continue
        else:
            p_model, p_loss, _ = mk.moneyline_probs(row["mu_spread"], row["sd_spread"], "home")
            if row["result"] == 0:
                continue
            y = 1.0 if row["result"] > 0 else 0.0
        p_model_cond = p_model / (p_model + p_loss) if (p_model + p_loss) > 0 else np.nan
        rows.append((p_model_cond, fair[0], y))
    if not rows:
        return {"games": 0}
    arr = np.array(rows, dtype=float)
    bm = brier(arr[:, 0], arr[:, 2])
    bk = brier(arr[:, 1], arr[:, 2])
    return {
        "games": int(len(arr)),
        "brier_model": bm,
        "brier_market": bk,
        "brier_skill": 1 - bm / bk,
        "logloss_model": log_loss(arr[:, 0], arr[:, 2]),
        "logloss_market": log_loss(arr[:, 1], arr[:, 2]),
    }


def _priced(row: pd.Series, market: str) -> bool:
    if market == "ATS":
        return pd.notna(row["home_spread_odds"]) and pd.notna(row["away_spread_odds"])
    if market == "TOTAL":
        return pd.notna(row["over_odds"]) and pd.notna(row["under_odds"])
    return pd.notna(row["home_moneyline"]) and pd.notna(row["away_moneyline"])


# --------------------------------------------------------------------------- #
# Permutation (luck) test: same weekly count, same side mix, random games
# --------------------------------------------------------------------------- #
def permutation_percentile(bets: pd.DataFrame, feats: pd.DataFrame, market: str,
                           n_perm: int = N_PERM, seed: int = SEED) -> dict:
    if bets.empty or market not in ("ATS", "TOTAL", "ML"):
        return {"percentile": None, "n_perm": 0}
    sides = bets["side"].to_numpy()
    side_home_share = float((sides == "home").mean()) if market != "TOTAL" else float((sides == "over").mean())
    universe = feats[(feats["season"] >= mk.EVAL_START) & (feats["season"] <= mk.EVAL_END)]
    rng = np.random.default_rng(seed)

    pnl_home, pnl_away, week_index = {}, {}, {}
    for week, chunk in universe.groupby(["season", "week"]):
        priced = chunk[chunk.apply(lambda r: _priced(r, market), axis=1)]
        if priced.empty:
            continue
        home = np.array([mk.pnl_for(r["home_spread_odds"] if market == "ATS" else (r["over_odds"] if market == "TOTAL" else r["home_moneyline"]),
                                    mk.settle(r, market, "home" if market != "TOTAL" else "over")) for _, r in priced.iterrows()])
        away = np.array([mk.pnl_for(r["away_spread_odds"] if market == "ATS" else (r["under_odds"] if market == "TOTAL" else r["away_moneyline"]),
                                    mk.settle(r, market, "away" if market != "TOTAL" else "under")) for _, r in priced.iterrows()])
        pnl_home[week] = home
        pnl_away[week] = away
        week_index[week] = len(home)
    counts = bets.groupby(["season", "week"]).size().to_dict()
    actual = float(bets["pnl"].mean())
    sims = np.empty(n_perm)
    for i in range(n_perm):
        total, n = 0.0, 0
        for week, k in counts.items():
            home, away = pnl_home.get(week), pnl_away.get(week)
            if home is None or len(home) == 0:
                continue
            pick = rng.integers(0, len(home), k)
            drawn_home = rng.random(k) < side_home_share
            vals = np.where(drawn_home, home[pick], away[pick])
            total += float(vals.sum())
            n += k
        sims[i] = total / n if n else 0.0
    return {
        "percentile": float((sims < actual).mean() * 100),
        "sim_mean_roi": float(sims.mean()),
        "n_perm": int(n_perm),
    }


# --------------------------------------------------------------------------- #
# Gates
# --------------------------------------------------------------------------- #
GATE_SPECS = [
    ("G1", "Provenance", "Every bet traces to a hashed input row; no imputed price or line."),
    ("G2", "Causality", "tests/test_causality.py passes for the strategy features."),
    ("G3", "Sample", ">= 300 bets, >= 8 seasons, >= 40 holdout bets."),
    ("G4", "Holdout", "Holdout ROI > 0."),
    ("G5", "Significance", "Bootstrap CI low > 0 and BH-FDR q <= 0.10."),
    ("G6", "Market test", "Brier skill >= 0 against the de-vigged market."),
    ("G7", "Stability", "ROI > 0 in >= 60% of seasons and best season <= 50% of profit."),
    ("G8", "Execution", ">= 95% of candidates priced and settled; flat stakes."),
    ("G9", "Luck control", "Random-selection percentile >= 95."),
]


def evaluate_gates(summary: dict, holdout: dict, market_test: dict | None,
                   q_value: float | None, perm: dict, causality_ok: bool,
                   priced_share: float) -> dict:
    gates = {}

    gates["G1"] = "pass" if summary.get("bets", 0) > 0 and priced_share is not None else "fail"
    gates["G2"] = "pass" if causality_ok else "fail"
    ok3 = (summary.get("bets", 0) >= 300 and summary.get("seasons", 0) >= 8
           and holdout.get("bets", 0) >= 40)
    gates["G3"] = "pass" if ok3 else "fail"
    gates["G4"] = "pass" if (holdout.get("roi") is not None and holdout["roi"] > 0) else "fail"
    ci_ok = summary.get("roi_ci_low") is not None and summary["roi_ci_low"] > 0
    fdr_ok = q_value is not None and q_value <= 0.10
    gates["G5"] = "pass" if (ci_ok and fdr_ok) else "fail"
    if market_test and market_test.get("brier_skill") is not None:
        gates["G6"] = "pass" if market_test["brier_skill"] >= 0 else "fail"
    elif summary.get("brier_skill") is not None:
        gates["G6"] = "pass" if summary["brier_skill"] >= 0 else "fail"
    else:
        gates["G6"] = "unverified"
    stab_ok = (summary.get("positive_season_share") is not None
               and summary["positive_season_share"] >= 0.6
               and summary.get("best_season_profit_share") is not None
               and summary["best_season_profit_share"] <= 0.5)
    gates["G7"] = "pass" if stab_ok else "fail"
    gates["G8"] = "pass" if priced_share >= 0.95 else "fail"
    perm_ok = perm.get("percentile") is not None and perm["percentile"] >= 95
    gates["G9"] = "pass" if perm_ok else ("unverified" if perm.get("percentile") is None else "fail")
    return gates


def gate_score(gates: dict) -> int:
    return sum(1 for v in gates.values() if v == "pass")


def reward_points(eligible: list[dict]) -> dict[str, float]:
    """Pre-registered reward score, normalised across eligible strategies only."""
    if not eligible:
        return {}
    lbs = np.array([s["holdout"]["roi_ci_low"] for s in eligible], dtype=float)
    bs = np.array([s.get("brier_skill") if s.get("brier_skill") is not None else 0.0 for s in eligible], dtype=float)

    def norm(a: np.ndarray) -> np.ndarray:
        if np.ptp(a) == 0:
            return np.full_like(a, 1.0)
        return (a - a.min()) / np.ptp(a)

    score = 100 * (0.6 * norm(lbs) + 0.4 * norm(bs))
    return {s["id"]: float(v) for s, v in zip(eligible, score)}
