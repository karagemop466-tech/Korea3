"""build_dataset.py — turn the pinned raw nflverse files into a leak-free modelling table.

Rules enforced here (and re-checked in verify_site.py):
  * Only completed regular-season games with a closing spread AND total are modelled.
  * `result`, `total` and scores are NEVER used as model inputs, only as outcomes.
  * Push handling: a bet on the spread that lands exactly on the number is a push
    (stake returned, excluded from win-rate denominators, counted in a push column).
  * 2026 is a live season: unplayed games are dropped, not filled.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd

from lib import row_source_url

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
OUT = os.path.join(ROOT, "data", "derived")

SURFACE_MAP = {
    "grass": "grass",
    "grass ": "grass",          # trailing-space duplicate present in source
    "astroturf": "turf",
    "astroplay": "turf",
    "fieldturf": "turf",
    "sportturf": "turf",
    "matrixturf": "turf",
    "a_turf": "turf",
    "dessograss": "grass",
}


def load_games() -> pd.DataFrame:
    g = pd.read_csv(os.path.join(RAW, "games.csv"), low_memory=False)
    g["gameday"] = pd.to_datetime(g["gameday"], errors="coerce")
    return g


def build() -> pd.DataFrame:
    g = load_games()
    df = g[g.game_type == "REG"].copy()

    # completed games only
    df = df[df["home_score"].notna() & df["away_score"].notna()]
    # priced games only (line + total present)
    df = df[df["spread_line"].notna() & df["total_line"].notna()]

    df["margin"] = df["home_score"] - df["away_score"]          # home perspective
    df["total_score"] = df["home_score"] + df["away_score"]

    # SIGN CONVENTION (verified twice; see research/00-repo-review.md §3):
    #   games.spread_line is signed OPPOSITE to the conventional home spread.
    #   Conventional home spread = -spread_line  (positive spread_line => home favoured).
    #   Home ATS margin = margin + conventional home spread = margin - spread_line.
    df["home_spread"] = -df["spread_line"]
    df["home_ats_margin"] = df["margin"] - df["spread_line"]     # >0 => home covered

    df["home_cover"] = np.where(df["home_ats_margin"] > 0, 1,
                        np.where(df["home_ats_margin"] < 0, 0, np.nan))
    df["push"] = (df["home_ats_margin"] == 0).astype(int)
    df["over"] = np.where(df["total_score"] > df["total_line"], 1,
                   np.where(df["total_score"] < df["total_line"], 0, np.nan))
    df["total_push"] = (df["total_score"] == df["total_line"]).astype(int)
    df["home_win"] = (df["margin"] > 0).astype(int)
    df["tie"] = (df["margin"] == 0).astype(int)

    # normalised environment fields (explicitly UNVERIFIED - no source field in dataset)
    df["surface_clean"] = df["surface"].str.strip().map(SURFACE_MAP)
    df["is_dome"] = df["roof"].isin(["dome", "closed"]).astype(int)
    df["roof_known"] = df["roof"].notna().astype(int)
    df["outdoor"] = (df["roof"] == "outdoors").astype(int)

    df["rest_diff"] = df["home_rest"] - df["away_rest"]
    df["home_off_bye"] = (df["home_rest"] >= 13).astype(int)
    df["away_off_bye"] = (df["away_rest"] >= 13).astype(int)
    df["home_short_week"] = (df["home_rest"] <= 6).astype(int)
    df["away_short_week"] = (df["away_rest"] <= 6).astype(int)
    df["is_thursday"] = (df["weekday"] == "Thursday").astype(int)
    df["is_monday"] = (df["weekday"] == "Monday").astype(int)
    df["is_sunday"] = (df["weekday"] == "Sunday").astype(int)

    df["abs_spread"] = df["spread_line"].abs()
    df["home_is_dog"] = (df["spread_line"] > 0).astype(int)
    df["home_is_fav"] = (df["spread_line"] < 0).astype(int)
    df["pickem"] = (df["spread_line"] == 0).astype(int)

    keep = [
        "game_id", "season", "week", "gameday", "weekday", "gametime",
        "away_team", "home_team", "away_score", "home_score", "margin", "total_score",
        "spread_line", "home_spread", "total_line", "home_moneyline", "away_moneyline",
        "away_spread_odds", "home_spread_odds", "over_odds", "under_odds",
        "home_ats_margin", "home_cover", "push", "over", "total_push", "home_win", "tie",
        "away_rest", "home_rest", "rest_diff", "div_game", "location", "roof", "is_dome",
        "roof_known", "outdoor", "surface", "surface_clean", "temp", "wind",
        "home_off_bye", "away_off_bye", "home_short_week", "away_short_week",
        "is_thursday", "is_monday", "is_sunday", "abs_spread", "home_is_dog",
        "home_is_fav", "pickem", "overtime", "stadium", "referee",
        "home_coach", "away_coach", "home_qb_name", "away_qb_name",
    ]
    df = df[keep].sort_values(["season", "week", "gameday", "game_id"]).reset_index(drop=True)
    df["row_source"] = row_source_url("games.csv")
    return df


def qa(df: pd.DataFrame) -> dict:
    """Hard checks. If any of these fail the pipeline must not publish."""
    checks = {}
    checks["rows"] = int(len(df))
    checks["seasons"] = [int(df.season.min()), int(df.season.max())]
    checks["no_future_games"] = bool(df["home_score"].notna().all())
    checks["unique_game_ids"] = bool(df["game_id"].is_unique)
    checks["margin_reconciles"] = bool((df["margin"] == df["home_score"] - df["away_score"]).all())
    checks["total_reconciles"] = bool((df["total_score"] == df["home_score"] + df["away_score"]).all())
    checks["cover_consistent"] = bool(
        ((df["home_ats_margin"] > 0) == (df["home_cover"] == 1)).all()
    )
    checks["push_rate_spread"] = round(float(df["push"].mean()), 4)
    checks["push_rate_total"] = round(float(df["total_push"].mean()), 4)
    checks["home_cover_rate_excl_push"] = round(float(df["home_cover"].dropna().mean()), 4)
    checks["over_rate_excl_push"] = round(float(df["over"].dropna().mean()), 4)
    checks["mean_margin"] = round(float(df["margin"].mean()), 3)
    checks["mean_total"] = round(float(df["total_score"].mean()), 3)
    return checks


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    d = build()
    d.to_csv(os.path.join(OUT, "model_dataset.csv"), index=False)
    import json
    c = qa(d)
    with open(os.path.join(OUT, "qa_build_dataset.json"), "w", encoding="utf-8") as fh:
        json.dump(c, fh, indent=2)
    print(json.dumps(c, indent=2))
