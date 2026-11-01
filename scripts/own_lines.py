"""own_lines.py — publish our own spread and total for games that have no line yet.

This is the product of the whole exercise: a line we originate, for the next slate,
with no market input at all. It is produced by fitting the ratings model on every
completed game up to and including the most recent one, then applying it to the
unplayed fixtures.

We also publish the closing line next to it whenever the market has posted one, so
the reader can see the disagreement, but the own line is computed without it.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from model import _design, fit_ridge, predict, HALF_LIFE_DAYS, LAMBDA

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
DER = os.path.join(ROOT, "data", "derived")


def main() -> None:
    g = pd.read_csv(os.path.join(RAW, "games.csv"), low_memory=False)
    g["gameday"] = pd.to_datetime(g["gameday"], errors="coerce")
    reg = g[g.game_type == "REG"].copy()
    completed = reg[reg.home_score.notna() & reg.away_score.notna()].copy()
    upcoming = reg[reg.home_score.isna()].copy()

    if upcoming.empty:
        print("no unplayed games in dataset")
        return

    cutoff = completed["gameday"].max() + pd.Timedelta(days=1)
    teams = sorted(set(reg.home_team) | set(reg.away_team))
    train = completed[completed.season >= completed.season.max() - 3].copy()
    age = (cutoff - train["gameday"]).dt.days.to_numpy(float)
    w = 0.5 ** (age / HALF_LIFE_DAYS)
    train["rest_diff"] = train["home_rest"] - train["away_rest"]
    train["div_game"] = train["div_game"].fillna(0)
    train["is_dome"] = train["roof"].isin(["dome", "closed"]).astype(int)
    X, y = _design(train, teams, "B")
    beta = fit_ridge(X, y, np.concatenate([w, w]), len(teams), LAMBDA)

    up = upcoming.sort_values(["gameday", "gametime"]).copy()
    up["rest_diff"] = up["home_rest"] - up["away_rest"]
    up["div_game"] = up["div_game"].fillna(0)
    up["is_dome"] = up["roof"].isin(["dome", "closed"]).astype(int)
    ph, pa = predict(beta, teams, up, "B")

    up["own_home_pts"] = np.round(ph, 1)
    up["own_away_pts"] = np.round(pa, 1)
    up["own_spread"] = np.round(-(ph - pa) * 2) / 2      # conventional home spread, half-point grid
    up["own_total"] = np.round((ph + pa) * 2) / 2
    up["market_spread_if_posted"] = np.where(up["spread_line"].notna(), -up["spread_line"], np.nan)
    up["market_total_if_posted"] = up["total_line"]
    up["disagreement_spread"] = up["own_spread"] - up["market_spread_if_posted"]
    up["disagreement_total"] = up["own_total"] - up["market_total_if_posted"]

    out = up[["game_id", "season", "week", "gameday", "weekday", "gametime",
              "away_team", "home_team", "location", "roof",
              "home_rest", "away_rest", "div_game",
              "own_away_pts", "own_home_pts", "own_spread", "own_total",
              "market_spread_if_posted", "market_total_if_posted",
              "disagreement_spread", "disagreement_total"]].copy()
    out.to_csv(os.path.join(DER, "own_lines_upcoming.csv"), index=False)

    meta = {
        "cutoff_date": str(cutoff.date()),
        "model_fit_on_games": int(len(train)),
        "n_upcoming": int(len(out)),
        "weeks": sorted({int(x) for x in out["week"].unique()}),
        "lambda": LAMBDA, "half_life_days": HALF_LIFE_DAYS,
        "n_with_posted_market_line": int(out["market_spread_if_posted"].notna().sum()),
        "note": "Own lines are computed WITHOUT the market. Where a market line is shown it is "
                "for comparison only and plays no part in the own line.",
    }
    with open(os.path.join(DER, "own_lines_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print(out.head(20).to_string(index=False))
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
