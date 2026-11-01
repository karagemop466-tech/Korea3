#!/usr/bin/env python3
"""Secondary analyses: threshold sensitivity, luck band, multiple-testing null, power.

These are labelled *exploratory* on the site. They are not part of reward eligibility,
because they were designed after the pre-registered round was read.
"""
from __future__ import annotations

from math import sqrt

import numpy as np
import pandas as pd

from . import markets as mk
from . import strategies as st

SEED = 20261101


def priced_universe(feats: pd.DataFrame, market: str) -> pd.DataFrame:
    df = feats[feats["season"].between(mk.EVAL_START, mk.EVAL_END)].copy()
    if market == "ATS":
        df = df.dropna(subset=["spread_line", "home_spread_odds", "away_spread_odds"])
    elif market == "TOTAL":
        df = df.dropna(subset=["total_line", "over_odds", "under_odds"])
    else:
        df = df.dropna(subset=["home_moneyline", "away_moneyline"])
    return df


def threshold_sensitivity(feats: pd.DataFrame, market: str, strategy_meta: tuple[str, str],
                          thresholds=(0.02, 0.03, 0.05, 0.07, 0.10)) -> list[dict]:
    """How ROI and selectivity move with the edge threshold (exploratory)."""
    sid, name = strategy_meta
    df = feats[feats["season"].between(mk.EVAL_START, mk.EVAL_END)]
    rows = []
    prev_edge = mk.EDGE_MIN
    for t in thresholds:
        mk.EDGE_MIN = t
        bets = st.model_bets(df, sid, name, market)
        if not bets:
            rows.append({"threshold": t, "bets": 0})
            continue
        frame = pd.DataFrame([b.as_row() for b in bets])
        roi = float(frame["pnl"].mean())
        settled = frame[frame["outcome"] != 0]
        rows.append({
            "threshold": t,
            "bets": int(len(frame)),
            "share_of_games": float(len(frame) / max(len(df), 1)),
            "win_rate": float((settled["outcome"] > 0).mean()) if len(settled) else None,
            "roi": roi,
            "pnl_units": float(frame["pnl"].sum()),
            "avg_price": float(frame["price"].mean()),
        })
    mk.EDGE_MIN = prev_edge
    return rows


def luck_band(feats: pd.DataFrame, effort: dict[str, int], n_sims: int = 2000) -> dict:
    """Distribution of the BEST of N random strategies over the same weeks.

    Each simulated strategy bets `effort[k]` games chosen uniformly from priced games
    with a 50/50 side split. The maximum ROI across the family is the number a
    leaderboard would report as 'the winner' if nobody had any skill.
    """
    rng = np.random.default_rng(SEED)
    df = priced_universe(feats, "ATS")
    pnl_home = np.array([mk.pnl_for(r["home_spread_odds"], mk.settle(r, "ATS", "home")) for _, r in df.iterrows()])
    pnl_away = np.array([mk.pnl_for(r["away_spread_odds"], mk.settle(r, "ATS", "away")) for _, r in df.iterrows()])
    pool = np.concatenate([pnl_home, pnl_away])
    counts = list(effort.values())
    max_rois = np.empty(n_sims)
    chunk = 250
    done = 0
    while done < n_sims:
        size = min(chunk, n_sims - done)
        rois = np.empty((size, len(counts)))
        for j, k in enumerate(counts):
            draws = rng.choice(pool, size=(size, int(k)), replace=True)
            rois[:, j] = draws.mean(axis=1)
        max_rois[done:done + size] = rois.max(axis=1)
        done += size
    return {
        "n_sims": int(n_sims),
        "strategies_per_family": int(len(counts)),
        "mean_best_roi": float(max_rois.mean()),
        "p05_best_roi": float(np.percentile(max_rois, 5)),
        "p95_best_roi": float(np.percentile(max_rois, 95)),
        "prob_best_is_profitable": float((max_rois > 0).mean()),
        "mean_single_roi": float(-0.0476),
        "note": "Pool is every priced ATS side 2006-2025; a random bettor pays the full vig.",
    }


def power_table(sd: float = 0.95, alpha: float = 0.05, power: float = 0.80) -> list[dict]:
    """Bets required to detect a per-bet ROI edge at 80% power, one-sided alpha=0.05."""
    z_alpha = 1.6449
    z_power = 0.8416
    out = []
    for edge in (0.01, 0.02, 0.03, 0.05, 0.10):
        n = ((z_alpha + z_power) * sd / edge) ** 2
        out.append({"edge": edge, "bets_required": int(np.ceil(n)),
                    "seasons_at_750_bets": float(np.ceil(n) / 750.0)})
    return out


def hold(feats: pd.DataFrame) -> dict:
    """Average bookmaker hold embedded in the recorded two-way prices."""
    out = {}
    for market in ("ATS", "TOTAL", "ML"):
        df = priced_universe(feats, market)
        if df.empty:
            continue
        holds = []
        for _, r in df.iterrows():
            if market == "ML":
                a, b = r["home_moneyline"], r["away_moneyline"]
            elif market == "ATS":
                a, b = r["home_spread_odds"], r["away_spread_odds"]
            else:
                a, b = r["over_odds"], r["under_odds"]
            holds.append(1 / mk.american_to_decimal(a) + 1 / mk.american_to_decimal(b) - 1)
        out[market] = {"mean_hold": float(np.mean(holds)), "games": int(len(df))}
    return out


def build_extras(feats: pd.DataFrame, bets: pd.DataFrame) -> dict:
    effort = {sid: int((bets["strategy_id"] == sid).sum())
              for sid, _, _ in st.STRATEGIES
              if (bets["strategy_id"] == sid).sum() > 0}
    return {
        "sensitivity": {
            "S1": threshold_sensitivity(feats, "ATS", ("S1", "Elo margin vs closing spread")),
            "S2": threshold_sensitivity(feats, "ML", ("S2", "Elo margin vs closing moneyline")),
            "S3": threshold_sensitivity(feats, "TOTAL", ("S3", "Scoring-profile totals")),
        },
        "luck_band": luck_band(feats, effort),
        "power": power_table(),
        "hold": hold(feats),
    }
