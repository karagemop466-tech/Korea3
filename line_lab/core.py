#!/usr/bin/env python3
"""Load the pinned snapshot and build strictly pre-game features.

Every feature in `build_features()` is computed from games that kicked off before
the game it describes. The code keeps all state in mutable dictionaries that are
updated only *after* a game is emitted, so a feature row can never see its own
result or any later result.

Conventions
-----------
* `spread_line` and `total_line` come from nflverse/nfldata `games.csv`.
  The nflverse data dictionary (nflreadr/data-raw/dictionary_schedules.csv)
  defines `spread_line` as "positive = home team favoured", which this project
  re-verified against results: mean(result) = +5.94 when spread_line > 0 and
  -4.43 when spread_line < 0.
* `result = home_score - away_score`; `total = home_score + away_score`.
* Home covers when `result - spread_line > 0`.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
RAW = BASE / "data" / "raw"

HFA_ELO = 55.0          # home-field advantage in Elo points (project constant)
ELO_K = 20.0            # update step (project constant)
SEASON_REGRESSION = 0.75  # weight kept on the old rating at a new season
EWMA_HALFLIFE = 4.0     # games
REF_MIN_GAMES = 30      # minimum prior games before a crew tendency is published

ODDS_COLS = ["spread_line", "total_line", "home_moneyline", "away_moneyline",
             "home_spread_odds", "away_spread_odds", "over_odds", "under_odds"]


def load_manifest() -> dict:
    return json.loads((RAW / "MANIFEST.json").read_text(encoding="utf-8"))


def load_games() -> pd.DataFrame:
    g = pd.read_csv(RAW / "games.csv", low_memory=False)
    g["gameday"] = pd.to_datetime(g["gameday"], errors="coerce")
    g["kickoff"] = pd.to_datetime(
        g["gameday"].dt.strftime("%Y-%m-%d") + " " + g["gametime"].fillna("13:00"),
        errors="coerce",
    )
    g["kickoff"] = g["kickoff"].fillna(g["gameday"] + pd.Timedelta(hours=13))
    g = g.sort_values(["kickoff", "game_id"]).reset_index(drop=True)
    g["completed"] = g["home_score"].notna() & g["away_score"].notna()
    return g


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def build_features(g: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return (completed-game features, scheduled-but-unplayed game rows).

    Both tables use state that existed before the game's kickoff. Unplayed games are
    emitted with the state as of the last completed game, so the live table can be
    turned into model lines without touching any future information.
    """
    alpha = 1.0 - 0.5 ** (1.0 / EWMA_HALFLIFE)
    elo: dict[str, float] = {}
    off: dict[str, float] = {}
    deff: dict[str, float] = {}
    last_game: dict[str, pd.Timestamp] = {}
    last_qb: dict[str, str] = {}
    season_started: dict[str, int] = {}
    ref_dev: dict[str, float] = {}
    ref_n: dict[str, int] = {}
    # league scoring level, updated only from completed prior seasons
    season_mean: dict[int, float] = {}
    running_sum = 0.0
    running_n = 0
    seen_seasons: set[int] = set()

    rows: list[dict] = []
    live_rows: list[dict] = []
    for rec in g.itertuples(index=False):
        season = int(rec.season)
        if season not in seen_seasons:
            # season bookkeeping: league mean from previous completed seasons only
            if running_n:
                season_mean[season] = running_sum / running_n
            seen_seasons.add(season)
        base = season_mean.get(season, 21.0)

        home, away = rec.home_team, rec.away_team
        if not rec.completed and rec.game_type == "REG":
            eh, ea = elo.get(home, 1500.0), elo.get(away, 1500.0)
            if season_started.get(home) != season:
                eh = 1500.0 + SEASON_REGRESSION * (eh - 1500.0)
            if season_started.get(away) != season:
                ea = 1500.0 + SEASON_REGRESSION * (ea - 1500.0)
            neutral = str(rec.location) == "Neutral"
            live_rows.append({
                "game_id": rec.game_id, "season": season,
                "week": int(rec.week) if pd.notna(rec.week) else 0,
                "kickoff": rec.kickoff, "gameday": rec.gameday,
                "home_team": home, "away_team": away, "location": rec.location,
                "roof": rec.roof, "surface": rec.surface, "temp": rec.temp, "wind": rec.wind,
                "div_game": rec.div_game, "home_rest": rec.home_rest, "away_rest": rec.away_rest,
                "rest_diff": (rec.home_rest - rec.away_rest)
                             if pd.notna(rec.home_rest) and pd.notna(rec.away_rest) else np.nan,
                "elo_home": eh, "elo_away": ea,
                "elo_diff": eh - ea + (0.0 if neutral else HFA_ELO),
                "off_home": off.get(home, base), "def_home": deff.get(home, base),
                "off_away": off.get(away, base), "def_away": deff.get(away, base),
                "qb_change_home": int(last_qb.get(home) is not None and isinstance(rec.home_qb_id, str)
                                      and rec.home_qb_id != last_qb.get(home)),
                "qb_change_away": int(last_qb.get(away) is not None and isinstance(rec.away_qb_id, str)
                                      and rec.away_qb_id != last_qb.get(away)),
                "indoor": int(str(rec.roof) in ("dome", "closed")),
                "spread_line": rec.spread_line, "total_line": rec.total_line,
                "home_moneyline": rec.home_moneyline, "away_moneyline": rec.away_moneyline,
                "home_spread_odds": rec.home_spread_odds, "away_spread_odds": rec.away_spread_odds,
                "over_odds": rec.over_odds, "under_odds": rec.under_odds,
                "home_coach": rec.home_coach, "away_coach": rec.away_coach,
                "stadium": rec.stadium,
            })
            continue

        if rec.completed and rec.game_type == "REG":
            eh, ea = elo.get(home, 1500.0), elo.get(away, 1500.0)
            # preseason regression happens at a team's first game of a season
            if season_started.get(home) != season:
                eh = 1500.0 + SEASON_REGRESSION * (eh - 1500.0)
                season_started[home] = season
            if season_started.get(away) != season:
                ea = 1500.0 + SEASON_REGRESSION * (ea - 1500.0)
                season_started[away] = season

            neutral = str(rec.location) == "Neutral"
            hfa = 0.0 if neutral else HFA_ELO
            elo_diff = eh - ea + hfa

            o_h, d_h = off.get(home, base), deff.get(home, base)
            o_a, d_a = off.get(away, base), deff.get(away, base)

            week = int(rec.week) if pd.notna(rec.week) else 0
            prev_qb_home = last_qb.get(home)
            prev_qb_away = last_qb.get(away)
            qb_ch_home = int(prev_qb_home is not None and week > 1
                             and isinstance(rec.home_qb_id, str)
                             and rec.home_qb_id != prev_qb_home)
            qb_ch_away = int(prev_qb_away is not None and week > 1
                             and isinstance(rec.away_qb_id, str)
                             and rec.away_qb_id != prev_qb_away)

            ref = rec.referee if isinstance(rec.referee, str) else None
            r_dev = ref_dev.get(ref, np.nan) if ref else np.nan
            r_n = ref_n.get(ref, 0) if ref else 0
            if ref_n.get(ref, 0) < REF_MIN_GAMES:
                r_dev = np.nan

            rows.append({
                "game_id": rec.game_id,
                "season": season,
                "week": week,
                "kickoff": rec.kickoff,
                "gameday": rec.gameday,
                "home_team": home,
                "away_team": away,
                "location": rec.location,
                "roof": rec.roof,
                "surface": rec.surface,
                "temp": rec.temp,
                "wind": rec.wind,
                "div_game": rec.div_game,
                "home_rest": rec.home_rest,
                "away_rest": rec.away_rest,
                "rest_diff": (rec.home_rest - rec.away_rest)
                             if pd.notna(rec.home_rest) and pd.notna(rec.away_rest) else np.nan,
                "elo_home": eh, "elo_away": ea, "elo_diff": elo_diff,
                "off_home": o_h, "def_home": d_h, "off_away": o_a, "def_away": d_a,
                "qb_change_home": qb_ch_home, "qb_change_away": qb_ch_away,
                "referee": ref, "ref_total_dev": r_dev, "ref_prior_games": r_n,
                "home_score": rec.home_score, "away_score": rec.away_score,
                "result": rec.result, "total": rec.total,
                "spread_line": rec.spread_line, "total_line": rec.total_line,
                "home_moneyline": rec.home_moneyline, "away_moneyline": rec.away_moneyline,
                "home_spread_odds": rec.home_spread_odds, "away_spread_odds": rec.away_spread_odds,
                "over_odds": rec.over_odds, "under_odds": rec.under_odds,
                "home_rest_raw": rec.home_rest, "away_rest_raw": rec.away_rest,
                "home_qb_id": rec.home_qb_id, "away_qb_id": rec.away_qb_id,
                "home_coach": rec.home_coach, "away_coach": rec.away_coach,
                "stadium": rec.stadium,
            })
            row_idx = len(rows) - 1

            # ---- state update (strictly after emission) ----
            margin = rec.result
            if margin is not None and not (isinstance(margin, float) and math.isnan(margin)):
                exp_home = 1.0 / (1.0 + 10 ** (-elo_diff / 400.0))
                moved = 1.0 if margin > 0 else 0.0
                winner_diff = elo_diff if margin > 0 else -elo_diff
                mult = (math.log(abs(margin) + 1.0) * 2.2) / (0.001 * winner_diff + 2.2)
                delta = ELO_K * mult * (moved - exp_home)
                elo[home] = eh + delta
                elo[away] = ea - delta
                rows[row_idx]["elo_home_post"] = elo[home]
                rows[row_idx]["elo_away_post"] = elo[away]

                off[home] = o_h + alpha * (rec.home_score - o_h)
                deff[home] = d_h + alpha * (rec.away_score - d_h)
                off[away] = o_a + alpha * (rec.away_score - o_a)
                deff[away] = d_a + alpha * (rec.home_score - d_a)

                last_game[home] = rec.kickoff
                last_game[away] = rec.kickoff
                if isinstance(rec.home_qb_id, str):
                    last_qb[home] = rec.home_qb_id
                if isinstance(rec.away_qb_id, str):
                    last_qb[away] = rec.away_qb_id

                if ref:
                    dev = rec.total - 2.0 * (running_sum / running_n if running_n else 21.0)
                    n = ref_n.get(ref, 0)
                    ref_dev[ref] = (ref_dev.get(ref, 0.0) * n + dev) / (n + 1)
                    ref_n[ref] = n + 1

                running_sum += rec.home_score + rec.away_score
                running_n += 2

    df = pd.DataFrame(rows)
    df["kickoff"] = pd.to_datetime(df["kickoff"])
    df["cover_margin"] = df["result"] - df["spread_line"]
    df["total_margin"] = df["total"] - df["total_line"]
    df["indoor"] = df["roof"].isin(["dome", "closed"]).astype(int)
    df["season"] = df["season"].astype(int)
    df["week"] = df["week"].astype(int)
    df = df.sort_values(["kickoff", "game_id"]).reset_index(drop=True)
    live = pd.DataFrame(live_rows)
    if not live.empty:
        live["kickoff"] = pd.to_datetime(live["kickoff"])
        live = live.sort_values(["kickoff", "game_id"]).reset_index(drop=True)
    return df, live


def write_features() -> tuple[pd.DataFrame, pd.DataFrame]:
    g = load_games()
    feats, live = build_features(g)
    out = ROOT / "data" / "derived"
    out.mkdir(parents=True, exist_ok=True)
    feats.drop(columns=["kickoff"]).to_csv(out / "features.csv", index=False)
    coverage = {}
    for season, chunk in feats.groupby("season"):
        coverage[int(season)] = {
            "games": int(len(chunk)),
            "with_spread_price": int(chunk["home_spread_odds"].notna().sum()),
            "with_total_price": int(chunk["over_odds"].notna().sum()),
            "with_moneyline": int(chunk["home_moneyline"].notna().sum()),
        }
    (out / "coverage.json").write_text(json.dumps(coverage, indent=2) + "\n", encoding="utf-8")
    live.to_csv(out / "live_candidates.csv", index=False)
    return feats, live


if __name__ == "__main__":
    f, live = write_features()
    print(f"features: {len(f)} regular-season games, {f.season.min()}-{f.season.max()}")
    print(f"unplayed scheduled games: {len(live)}")
    priced = int(f[(f.season >= 2006) & (f.season <= 2025)].home_spread_odds.notna().sum())
    print("2006-2025 rows with a recorded spread price:", priced)
