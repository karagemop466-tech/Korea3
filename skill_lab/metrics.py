#!/usr/bin/env python3
"""Core skill statistics for the Skill Lab.

Everything is deterministic and defined over rows already in the repository.
The headline metric is the **benchmark-relative Brier skill score (BSS)**:

    BSS = Brier(market_prob, outcome) - Brier(model_prob, outcome)

computed over *settled* bets (outcome in {0, 1}; pushes excluded from Brier but
counted separately and reported as n). ``model_prob`` is a strategy's predicted
probability for the side it selected; ``market_prob`` is the closing line's
implied probability for that same side. BSS > 0 means the strategy predicts the
outcome it bet on **better** than the market; BSS < 0 means worse. This is the
standard Brier Skill Score direction (reference minus model).

Uncertainty is a **game-cluster bootstrap** (cluster by season-week) of the
BSS difference, giving a 95% percentile interval and a one-sided p-value
(skill > 0). Multiplicity across strategies is controlled with
Benjamini-Hochberg FDR, with Bonferroni published alongside.

No value is inferred. A strategy with no ``model_prob`` in the pinned data
(season futures) gets a blank BSS and is flagged, never imputed.
"""
from __future__ import annotations

import math
from typing import Iterable

import numpy as np
import pandas as pd

SEED = 20261119
N_BOOT = 2000


# --------------------------------------------------------------------------- #
# Probability / odds
# --------------------------------------------------------------------------- #
def american_to_implied(odds: pd.Series) -> pd.Series:
    """Implied probability from American odds (raw, with vig).

    +110 -> 100/210; -110 -> 110/210. NaN odds stay NaN.
    """
    o = pd.to_numeric(odds, errors="coerce")
    out = pd.Series(np.nan, index=o.index, dtype=float)
    pos = o > 0
    neg = o < 0
    out[pos] = 100.0 / (100.0 + o[pos])
    out[neg] = (-o[neg]) / (100.0 - o[neg])
    return out


def brier(p: Iterable[float], y: Iterable[float]) -> float:
    """Mean squared error of probabilities against 0/1 outcomes.

    Rows with a missing probability or outcome are dropped (never imputed).
    """
    p = np.asarray(list(p), dtype=float)
    y = np.asarray(list(y), dtype=float)
    mask = np.isfinite(p) & np.isfinite(y)
    if mask.sum() == 0:
        return float("nan")
    return float(np.mean((p[mask] - y[mask]) ** 2))


def settled(outcome: pd.Series) -> pd.Series:
    """Boolean mask of settled (non-push, non-missing) outcomes."""
    o = pd.to_numeric(outcome, errors="coerce")
    return o.isin([0.0, 1.0])


# --------------------------------------------------------------------------- #
# Game-cluster bootstrap
# --------------------------------------------------------------------------- #
def game_clusters(df: pd.DataFrame, season_col: str, week_col: str) -> list[np.ndarray]:
    """Indices grouped by (season, week) — the game-level cluster."""
    keys = list(zip(df[season_col].to_numpy(), df[week_col].to_numpy()))
    groups: dict[tuple, list[int]] = {}
    for i, k in enumerate(keys):
        groups.setdefault(k, []).append(i)
    return [np.array(v) for v in groups.values()]


def bss_from_frame(df: pd.DataFrame) -> float:
    """Benchmark-relative Brier skill for a frame with model_prob/market_prob/outcome.

    BSS = Brier(market) - Brier(model); positive = better than the market.
    """
    s = settled(df["outcome"])
    sub = df.loc[s, ["model_prob", "market_prob", "outcome"]]
    if sub.empty:
        return float("nan")
    return brier(sub["market_prob"], sub["outcome"]) - brier(sub["model_prob"], sub["outcome"])


def bootstrap_bss(
    df: pd.DataFrame,
    season_col: str = "season",
    week_col: str = "week",
    n_boot: int = N_BOOT,
    seed: int = SEED,
) -> dict:
    """Game-cluster bootstrap of the BSS difference.

    Returns the point estimate, 95% percentile interval, the lower bound, and a
    one-sided p-value (fraction of bootstrap replicates with BSS <= 0).
    """
    s = settled(df["outcome"])
    base = df.loc[s, ["model_prob", "market_prob", "outcome", season_col, week_col]].copy()
    # mask rows with a non-finite probability so the bootstrap matches brier(),
    # which already drops them (NaN <= 0 is False, which would fake a p-value of 0).
    finite = base["model_prob"].notna() & base["market_prob"].notna()
    base = base[finite]
    if base.empty:
        return {"bss": float("nan"), "ci_low": None, "ci_high": None,
                "lower_bound": None, "p_value": None, "n_boot": 0}
    clusters = game_clusters(base, season_col, week_col)
    p = base["model_prob"].to_numpy(float)
    mp = base["market_prob"].to_numpy(float)
    y = base["outcome"].to_numpy(float)
    rng = np.random.default_rng(seed)
    sims = np.empty(n_boot)
    for b in range(n_boot):
        pick = rng.integers(0, len(clusters), len(clusters))
        idx = np.concatenate([clusters[i] for i in pick])
        # BSS = Brier(market) - Brier(model); positive = better than the market
        sims[b] = np.mean((mp[idx] - y[idx]) ** 2) - np.mean((p[idx] - y[idx]) ** 2)
    point = float(np.mean((mp - y) ** 2) - np.mean((p - y) ** 2))
    return {
        "bss": point,
        "ci_low": float(np.percentile(sims, 2.5)),
        "ci_high": float(np.percentile(sims, 97.5)),
        "lower_bound": float(np.percentile(sims, 2.5)),
        "p_value": float((sims <= 0).mean()),
        "n_boot": n_boot,
    }


# --------------------------------------------------------------------------- #
# Multiplicity
# --------------------------------------------------------------------------- #
def bonferroni(pvals: dict[str, float]) -> dict[str, float]:
    items = {k: float(v) for k, v in pvals.items() if v is not None and math.isfinite(v)}
    m = len(items)
    if m == 0:
        return {}
    return {k: min(1.0, v * m) for k, v in items.items()}


def benjamini_hochberg(pvals: dict[str, float]) -> dict[str, float]:
    """BH FDR-adjusted q-values (step-up). Missing p-values stay missing."""
    items = {k: float(v) for k, v in pvals.items() if v is not None and math.isfinite(v)}
    m = len(items)
    if m == 0:
        return {}
    order = sorted(items, key=lambda k: items[k])
    q: dict[str, float] = {}
    prev = 1.0
    # walk from largest p to smallest, carrying the running minimum of the cap
    for rank in range(m, 0, -1):
        k = order[rank - 1]
        cap = items[k] * m / rank
        prev = min(prev, cap)
        q[k] = min(1.0, prev)
    return q
