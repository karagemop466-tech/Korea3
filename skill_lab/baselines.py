#!/usr/bin/env python3
"""Control baselines for the Skill Lab (requirement C04).

Three no-skill references are computed on the **verified results-feed universe**
(``market_lab/data/results_feed.csv``): every settled market-side whose outcome
was re-settled against the official final score and matched the recorded one.

1. **Market benchmark** — the closing line's implied probability for each side.
   This is the definitive no-skill reference: a strategy that merely repeated the
   market's own implied probability would score BSS = 0 by construction.
2. **Random 50/50 picks** — a predictor that picks a side at random. Its Brier
   is exactly 0.25 analytically (E[(0.5 - y)^2] = 0.25 for y in {0,1}); a seeded
   realised ROI is also reported for context and is labelled seed-dependent.
3. **Favourites-only** — always take the side with the higher implied
   probability. A concrete, computable strategy; its Brier, ROI and game-cluster
   bootstrap are all real numbers from the pinned rows.

Pushes (recomputed_outcome = 0.5) are excluded from Brier and counted separately.
Nothing is inferred; a missing price leaves the row out of the relevant metric.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .metrics import american_to_implied, brier, game_clusters, settled

SEED = 20261119


def unit_pnl(price: pd.Series, outcome: pd.Series) -> pd.Series:
    """Profit per $1 staked at American ``price`` given a 0/1/0.5 outcome.

    win  -> odds/100 if odds>0 else 100/|odds|;  loss -> -1;  push -> 0.
    """
    o = pd.to_numeric(price, errors="coerce")
    oc = pd.to_numeric(outcome, errors="coerce")
    out = pd.Series(np.nan, index=o.index, dtype=float)
    win = oc == 1.0
    lose = oc == 0.0
    push = oc == 0.5
    pos = o > 0
    neg = o < 0
    out[win & pos] = o[win & pos] / 100.0
    out[win & neg] = 100.0 / (-o[win & neg])
    out[lose] = -1.0
    out[push] = 0.0
    return out


def control_universe(results: pd.DataFrame) -> pd.DataFrame:
    """Verified, settled market-side rows with a usable price and outcome."""
    df = results[results["verification"] == "verified"].copy()
    df = df[df["recomputed_outcome"].notna()].copy()
    df["implied"] = american_to_implied(df["price"])
    df = df[df["implied"].notna()].copy()
    df["outcome01"] = df["recomputed_outcome"].where(
        df["recomputed_outcome"].isin([0.0, 1.0])
    )
    return df


def market_benchmark(df: pd.DataFrame) -> dict:
    """Brier of the market's own implied probability, plus mean vig."""
    s = df["outcome01"].notna()
    sub = df.loc[s]
    b = brier(sub["implied"], sub["outcome01"])
    # mean vig per game-market (sum of the two sides' implied probs minus 1)
    vig = df.groupby(["game_id", "market"])["implied"].sum() - 1.0
    return {
        "brier": b,
        "n": int(s.sum()),
        "mean_vig": float(vig.mean()) if len(vig) else float("nan"),
        "n_markets": int(len(vig)),
    }


def favourites_only(df: pd.DataFrame) -> dict:
    """Always bet the higher-implied-probability side; settle on the official score."""
    rows = []
    for (game, market), grp in df.groupby(["game_id", "market"]):
        if len(grp) < 2:
            continue
        grp = grp.sort_values("implied", ascending=False)
        fav = grp.iloc[0]
        rows.append({
            "game_id": game, "market": market, "season": fav["season"],
            "week": fav["week"], "side": fav["side"], "implied": fav["implied"],
            "outcome": fav["outcome01"], "price": fav["price"],
        })
    fav = pd.DataFrame(rows)
    fav = fav[fav["outcome"].notna()].copy()
    fav["pnl"] = unit_pnl(fav["price"], fav["outcome"])
    b = brier(fav["implied"], fav["outcome"])
    roi_boot = bootstrap_roi(fav)
    # game-cluster bootstrap of the favourites-only Brier
    boot = _bootstrap_brier(fav)
    return {
        "brier": b,
        "n": int(len(fav)),
        "roi": roi_boot["roi"],
        "roi_ci_low": roi_boot["ci_low"],
        "roi_ci_high": roi_boot["ci_high"],
        "roi_p_value": roi_boot["p_value"],
        "push_n": int((fav["outcome"] == 0.5).sum()) if "outcome" in fav else 0,
        "ci_low": boot["ci_low"], "ci_high": boot["ci_high"],
        "p_value": boot["p_value"],
    }


def bootstrap_roi(df: pd.DataFrame, n_boot: int = 2000, seed: int = SEED) -> dict:
    """Game-cluster bootstrap of mean unit ROI; 95% CI and one-sided p (ROI > 0)."""
    s = df["outcome"].notna()
    base = df.loc[s, ["pnl", "season", "week"]].copy()
    if base.empty:
        return {"roi": float("nan"), "ci_low": None, "ci_high": None, "p_value": None}
    clusters = game_clusters(base, "season", "week")
    pnl = base["pnl"].to_numpy(float)
    rng = np.random.default_rng(seed)
    sims = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, len(clusters), len(clusters))
        idx = np.concatenate([clusters[i] for i in pick])
        sims[b] = pnl[idx].mean()
    return {
        "roi": float(pnl.mean()),
        "ci_low": float(np.percentile(sims, 2.5)),
        "ci_high": float(np.percentile(sims, 97.5)),
        "p_value": float((sims <= 0).mean()),
        "n_boot": n_boot,
    }


def _bootstrap_brier(df: pd.DataFrame) -> dict:
    s = df["outcome"].notna()
    base = df.loc[s, ["implied", "outcome", "season", "week"]].copy()
    if base.empty:
        return {"ci_low": None, "ci_high": None, "p_value": None}
    clusters = game_clusters(base, "season", "week")
    p = base["implied"].to_numpy(float)
    y = base["outcome"].to_numpy(float)
    rng = np.random.default_rng(SEED)
    n_boot = 2000
    sims = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, len(clusters), len(clusters))
        idx = np.concatenate([clusters[i] for i in pick])
        sims[b] = np.mean((p[idx] - y[idx]) ** 2)
    point = float(np.mean((p - y) ** 2))
    return {
        "ci_low": float(np.percentile(sims, 2.5)),
        "ci_high": float(np.percentile(sims, 97.5)),
        "p_value": float((sims <= 0).mean()),
        "point": point,
    }


def random_5050(df: pd.DataFrame, seed: int = SEED) -> dict:
    """Random-pick control. Brier is analytic (0.25); ROI is a seeded realisation."""
    rng = np.random.default_rng(seed)
    rows = []
    for (game, market), grp in df.groupby(["game_id", "market"]):
        if len(grp) < 2:
            continue
        pick = grp.iloc[rng.integers(0, len(grp))]
        rows.append({"game_id": game, "market": market, "season": pick["season"],
                     "week": pick["week"], "implied": pick["implied"],
                     "outcome": pick["outcome01"], "price": pick["price"]})
    rnd = pd.DataFrame(rows)
    rnd = rnd[rnd["outcome"].notna()].copy()
    rnd["pnl"] = unit_pnl(rnd["price"], rnd["outcome"])
    roi = float(rnd["pnl"].mean()) if not rnd.empty else float("nan")
    # BSS on the random universe: Brier(market implied of the picked side) - 0.25
    mk_brier = brier(rnd["implied"], rnd["outcome"]) if not rnd.empty else float("nan")
    return {
        "brier": 0.25,  # analytic: E[(0.5 - y)^2] = 0.25 for y in {0,1}
        "brier_analytic": True,
        "market_brier": mk_brier,
        "bss": (mk_brier - 0.25) if np.isfinite(mk_brier) else float("nan"),
        "n": int(len(rnd)),
        "roi": roi,
        "roi_seed_dependent": True,
        "seed": seed,
    }
