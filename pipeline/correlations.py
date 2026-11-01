#!/usr/bin/env python3
"""Correlation and dependence measurements used to price parlays and SGPs.

All coefficients are computed from the pinned snapshot. Nothing is assumed: where a
combination cannot be measured, the value is returned as None and is published blank.
"""
from __future__ import annotations

import itertools

import numpy as np
import pandas as pd

from . import markets as mk

SEED = 20261101
N_BOOT = 1000


def _week_groups(df: pd.DataFrame) -> list[np.ndarray]:
    groups: dict[tuple[int, int], list[int]] = {}
    for i, (s, w) in enumerate(zip(df["season"].to_numpy(), df["week"].to_numpy())):
        groups.setdefault((int(s), int(w)), []).append(i)
    return [np.array(v) for v in groups.values()]


def _phi(x: np.ndarray, y: np.ndarray) -> float:
    if len(x) < 3 or np.std(x) == 0 or np.std(y) == 0:
        return float("nan")
    return float(np.corrcoef(x, y)[0, 1])


def _boot_phi(x: np.ndarray, y: np.ndarray, groups: list[np.ndarray],
              n_boot: int = N_BOOT, seed: int = SEED) -> tuple[float | None, float | None]:
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_boot):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([groups[i] for i in pick])
        v = _phi(x[idx], y[idx])
        if not np.isnan(v):
            vals.append(v)
    if not vals:
        return None, None
    return float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))


def same_game_dependence(feats: pd.DataFrame) -> dict:
    """phi between binary market outcomes inside the same game (2006-2025, priced)."""
    df = feats[(feats["season"] >= mk.EVAL_START) & (feats["season"] <= mk.EVAL_END)].copy()
    df = df.dropna(subset=["spread_line", "total_line", "home_spread_odds", "over_odds"])
    df["ats_home"] = np.where(df["result"] - df["spread_line"] > 0, 1.0,
                              np.where(df["result"] - df["spread_line"] < 0, 0.0, np.nan))
    df["over"] = np.where(df["total"] - df["total_line"] > 0, 1.0,
                          np.where(df["total"] - df["total_line"] < 0, 0.0, np.nan))
    df["ml_home"] = np.where(df["result"] > 0, 1.0, np.where(df["result"] < 0, 0.0, np.nan))
    df = df.dropna(subset=["ats_home", "over", "ml_home"]).reset_index(drop=True)
    groups = _week_groups(df)

    pairs = {
        "ats_home__over": ("ats_home", "over"),
        "ats_home__ml_home": ("ats_home", "ml_home"),
        "over__ml_home": ("over", "ml_home"),
    }
    out = {"games": int(len(df)), "pairs": {}}
    for key, (a, b) in pairs.items():
        x, y = df[a].to_numpy(), df[b].to_numpy()
        lo, hi = _boot_phi(x, y, groups)
        joint = float((x * y).mean())
        out["pairs"][key] = {
            "phi": _phi(x, y), "ci_low": lo, "ci_high": hi, "n": int(len(x)),
            "joint_rate": joint,
            "independent_product": float(x.mean() * y.mean()),
            "dependence_bias": joint - x.mean() * y.mean(),
            "p_b_given_a": joint / float(x.mean()) if x.mean() else None,
            "p_b_marginal": float(y.mean()),
        }
    return out


def team_scoring_correlation(feats: pd.DataFrame) -> dict:
    df = feats[(feats["season"] >= mk.EVAL_START) & (feats["season"] <= mk.EVAL_END)].copy()
    df = df.dropna(subset=["home_score", "away_score"])
    x, y = df["home_score"].to_numpy(float), df["away_score"].to_numpy(float)
    r = float(np.corrcoef(x, y)[0, 1])
    groups = _week_groups(df.reset_index(drop=True))
    rng = np.random.default_rng(SEED)
    boots = []
    for _ in range(N_BOOT):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([groups[i] for i in pick])
        boots.append(float(np.corrcoef(x[idx], y[idx])[0, 1]))
    per_season = {}
    for season, chunk in df.groupby("season"):
        per_season[int(season)] = {
            "r": float(np.corrcoef(chunk["home_score"], chunk["away_score"])[0, 1]),
            "n": int(len(chunk)),
        }
    margin = df["result"].abs().to_numpy(float)
    total = df["total"].to_numpy(float)
    tboots = []
    for _ in range(N_BOOT):
        pick = rng.integers(0, len(groups), len(groups))
        idx = np.concatenate([groups[i] for i in pick])
        tboots.append(float(np.corrcoef(total[idx], margin[idx])[0, 1]))
    return {
        "home_vs_away_points": {
            "r": r, "ci_low": float(np.percentile(boots, 2.5)),
            "ci_high": float(np.percentile(boots, 97.5)), "n": int(len(df)),
        },
        "total_vs_abs_margin": {
            "r": float(np.corrcoef(total, margin)[0, 1]),
            "ci_low": float(np.percentile(tboots, 2.5)),
            "ci_high": float(np.percentile(tboots, 97.5)),
            "n": int(len(df)),
        },
        "per_season": per_season,
    }


def cross_game_independence(feats: pd.DataFrame, n_pairs: int = 20000, seed: int = SEED) -> dict:
    """phi of moneyline outcomes for two different games in the same week."""
    df = feats[(feats["season"] >= mk.EVAL_START) & (feats["season"] <= mk.EVAL_END)]
    df = df.dropna(subset=["home_moneyline", "result"])
    df = df[df["result"] != 0]
    rng = np.random.default_rng(seed)
    xs, ys = [], []
    for _, week in df.groupby(["season", "week"]):
        if len(week) < 2:
            continue
        vals = (week["result"] > 0).to_numpy(float)
        for _ in range(min(len(vals) * 8, 400)):
            i, j = rng.choice(len(vals), size=2, replace=False)
            xs.append(vals[i])
            ys.append(vals[j])
            if len(xs) >= n_pairs:
                break
        if len(xs) >= n_pairs:
            break
    x, y = np.array(xs), np.array(ys)
    rng2 = np.random.default_rng(seed + 1)
    boots = []
    for _ in range(N_BOOT):
        idx = rng2.integers(0, len(x), len(x))
        v = _phi(x[idx], y[idx])
        if not np.isnan(v):
            boots.append(v)
    return {
        "phi": _phi(x, y), "n_pairs": int(len(x)),
        "ci_low": float(np.percentile(boots, 2.5)), "ci_high": float(np.percentile(boots, 97.5)),
        "note": "same-week, different games",
    }


def parlay_dependence(bets: pd.DataFrame) -> dict:
    """Empirical joint hit rate vs the product of de-vigged leg probabilities."""
    out = {}
    for sid, label in [("S9", "cross-game moneyline parlay"), ("S10", "cross-game ATS parlay")]:
        sub = bets[(bets["strategy_id"] == sid) & (bets["outcome"] != 0)]
        if sub.empty:
            out[sid] = {"label": label, "cards": 0}
            continue
        joint = float((sub["outcome"] > 0).mean())
        expected = float(sub["market_prob"].mean())
        out[sid] = {
            "label": label,
            "cards": int(len(sub)),
            "joint_hit_rate": joint,
            "independence_expected": expected,
            "bias": joint - expected,
        }
    return out


def strategy_return_correlation(bets: pd.DataFrame) -> dict:
    frame = bets[bets["strategy_id"].isin([f"S{i}" for i in range(1, 9)])]
    weekly = (frame.groupby(["season", "week", "strategy_id"])["pnl"].sum()
              .unstack("strategy_id"))
    corr = weekly.corr(min_periods=50)
    ids = [c for c in corr.columns]
    return {
        "weeks": int(len(weekly)),
        "matrix": {a: {b: (None if pd.isna(corr.loc[a, b]) else float(corr.loc[a, b])) for b in ids} for a in ids},
    }


def leg_mix_same_game(bets: pd.DataFrame) -> dict:
    """Same-game spread+total combos: joint hit rate vs product for every pair."""
    s1 = bets[bets["strategy_id"] == "S1"].set_index("game_id")
    s3 = bets[bets["strategy_id"] == "S3"].set_index("game_id")
    shared = sorted(set(s1.index) & set(s3.index))
    if not shared:
        return {"games": 0}
    combos = []
    for gid in shared:
        a, b = s1.loc[gid], s3.loc[gid]
        if isinstance(a, pd.DataFrame) or isinstance(b, pd.DataFrame):
            continue
        combos.append((gid, a["outcome"], b["outcome"], a["market_prob"], b["market_prob"]))
    df = pd.DataFrame(combos, columns=["game_id", "ats", "total", "p_ats", "p_total"])
    df = df[(df["ats"] != 0) & (df["total"] != 0)]
    if df.empty:
        return {"games": 0}
    joint = float(((df["ats"] > 0) & (df["total"] > 0)).mean())
    expected = float((df["p_ats"] * df["p_total"]).mean())
    phi = _phi((df["ats"] > 0).to_numpy(float), (df["total"] > 0).to_numpy(float))
    return {
        "games": int(len(df)), "joint_hit_rate": joint, "independence_expected": expected,
        "bias": joint - expected, "phi": phi,
    }


def three_leg_same_game(feats: pd.DataFrame) -> dict:
    """ATS + total + moneyline inside the same game: joint vs product."""
    df = feats[(feats["season"] >= mk.EVAL_START) & (feats["season"] <= mk.EVAL_END)].copy()
    df = df.dropna(subset=["spread_line", "total_line", "home_moneyline", "home_spread_odds", "over_odds"])
    df["ats_home"] = np.where(df["result"] - df["spread_line"] > 0, 1.0,
                              np.where(df["result"] - df["spread_line"] < 0, 0.0, np.nan))
    df["over"] = np.where(df["total"] - df["total_line"] > 0, 1.0,
                          np.where(df["total"] - df["total_line"] < 0, 0.0, np.nan))
    df["ml_home"] = np.where(df["result"] > 0, 1.0, np.where(df["result"] < 0, 0.0, np.nan))
    df = df.dropna(subset=["ats_home", "over", "ml_home"])
    joint = float(((df["ats_home"] == 1) & (df["over"] == 1) & (df["ml_home"] == 1)).mean())
    return {
        "games": int(len(df)),
        "joint_favourite_over_ml": joint,
        "marginals": {
            "home_covers": float((df["ats_home"] == 1).mean()),
            "over": float((df["over"] == 1).mean()),
            "home_wins": float((df["ml_home"] == 1).mean()),
        },
        "product": float((df["ats_home"] == 1).mean() * (df["over"] == 1).mean() * (df["ml_home"] == 1).mean()),
    }


def build_correlations(feats: pd.DataFrame, bets: pd.DataFrame) -> dict:
    return {
        "same_game": same_game_dependence(feats),
        "team_scoring": team_scoring_correlation(feats),
        "cross_game": cross_game_independence(feats),
        "parlays": parlay_dependence(bets),
        "leg_mix_same_game": leg_mix_same_game(bets),
        "three_leg_same_game": three_leg_same_game(feats),
        "strategy_returns": strategy_return_correlation(bets),
        "prop_pairs": None,
    }
