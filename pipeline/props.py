#!/usr/bin/env python3
"""Player-prop layer.

Status in this environment: BLOCKED, by design, not by choice.

To price a player prop you need (a) an official player-level game log and (b) the
quoted prop line and price from a licensed sportsbook. Neither is reachable here:

* nflverse publishes official-derived player game logs as GitHub *release assets*
  (`nflverse/nflverse-data`, tag `player_stats`). This sandbox cannot reach
  `release-assets.githubusercontent.com`, and no git-committed copy exists in
  nflverse/nfldata.
* Prop lines are operator data. There is no open, licensed, historical prop-line
  archive in any reachable repository, so any prop ROI or correlation printed here
  would be invented.

This module therefore: (1) verifies what is present in `data/raw/`, (2) publishes
the exact input schema it needs, (3) publishes the estimator that will run once the
inputs land, and (4) returns empty values that the site renders blank.
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .core import RAW, ROOT

REQUIRED_PLAYER_LOG = [
    "game_id", "player_id", "player_name", "position", "team",
    "passing_yards", "passing_tds", "interceptions", "rushing_yards", "rushing_tds",
    "receptions", "receiving_yards", "receiving_tds", "targets",
]
REQUIRED_PROP_LINES = [
    "game_id", "player_id", "market", "line", "over_price", "under_price",
    "book", "quote_timestamp_utc",
]


def phi_coefficient(a: np.ndarray, b: np.ndarray) -> float:
    """phi = Pearson correlation of two binary vectors; equals signed dependence for 2x2 tables."""
    if len(a) < 3 or np.std(a) == 0 or np.std(b) == 0:
        return float("nan")
    return float(np.corrcoef(a, b)[0, 1])


def conditional_over_rate(log: pd.DataFrame, market: str, threshold: float,
                          segment: pd.Series) -> float:
    """P(player over threshold | segment) with the market column chosen by name."""
    col = market
    subset = log[log[segment]]
    if subset.empty:
        return float("nan")
    return float((subset[col] > threshold).mean())


def availability() -> dict:
    player_log = RAW / "player_stats.csv"
    prop_lines = RAW / "prop_lines.csv"
    status = {
        "player_log_present": player_log.exists(),
        "prop_lines_present": prop_lines.exists(),
        "player_log_path": str(player_log.relative_to(ROOT)),
        "prop_lines_path": str(prop_lines.relative_to(ROOT)),
        "required_player_log_columns": REQUIRED_PLAYER_LOG,
        "required_prop_line_columns": REQUIRED_PROP_LINES,
        "blocking_reasons": [
            "GitHub release assets (release-assets.githubusercontent.com) are unreachable from this sandbox, "
            "so nflverse player_stats (the canonical player game log release) cannot be downloaded.",
            "No licensed historical player-prop line/price archive exists in any reachable repository, "
            "so prop ROI, hit rate and correlation values cannot be measured without fabrication.",
        ],
        "estimator_ready": True,
        "estimator": [
            "phi between binary leg outcomes at matched thresholds (e.g. QB passing yards 275.5 and WR receiving yards 65.5)",
            "joint hit rate vs product of marginals for every same-game pair, with week-block bootstrap CI",
            "threshold-swept conditional probability P(leg B over | leg A over) to expose non-linear dependence",
            "delta-method or bootstrap CI on the correlation, plus n and missingness per pair",
        ],
        "results": {
            "pairs_measured": 0,
            "phi": None,
            "joint_hit_rate": None,
            "independence_expected": None,
            "roi": None,
            "note": "No value is published. Blank means unverified, never zero.",
        },
    }
    return status


def run() -> dict:
    return availability()


if __name__ == "__main__":
    print(json.dumps(run(), indent=2))
