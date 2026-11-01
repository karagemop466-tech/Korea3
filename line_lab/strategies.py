#!/usr/bin/env python3
"""Pre-registered strategy family: walk-forward fitting, selection, settlement.

Nothing in this module looks at a result before it is used. Model coefficients for
season S are fitted on seasons < S; signal rules use only pre-game columns.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, asdict

import numpy as np
import pandas as pd

from . import markets as mk
from .core import RAW, ROOT


@dataclass
class Bet:
    strategy_id: str
    strategy_name: str
    market: str
    season: int
    week: int
    game_id: str
    kickoff: str
    side: str
    line: float
    price: float
    model_prob: float
    market_prob: float
    edge: float
    outcome: int
    pnl: float

    def as_row(self) -> dict:
        return asdict(self)


# --------------------------------------------------------------------------- #
# Walk-forward fitting
# --------------------------------------------------------------------------- #
def _ols(x: np.ndarray, y: np.ndarray) -> tuple[np.ndarray, float]:
    design = np.column_stack([np.ones(len(x)), x])
    beta, *_ = np.linalg.lstsq(design, y, rcond=None)
    resid = y - design @ beta
    sigma = float(np.sqrt((resid ** 2).sum() / max(len(y) - design.shape[1], 1)))
    return beta, sigma


def add_walk_forward_predictions(feats: pd.DataFrame, first_eval: int = 2006) -> pd.DataFrame:
    """Attach mu/sigma for the spread and total models, refit each season."""
    out = feats.copy()
    for col in ["mu_spread", "sd_spread", "mu_total", "sd_total", "sigma_ml"]:
        out[col] = np.nan

    seasons = sorted(out["season"].unique())
    for season in seasons:
        if season < first_eval:
            continue
        train = out[out["season"] < season]
        if len(train) < 400:
            continue
        rest = train["rest_diff"].fillna(0.0)
        xm = np.column_stack([
            train["elo_diff"].to_numpy(float),
            rest.to_numpy(float),
            train["qb_change_home"].to_numpy(float),
            train["qb_change_away"].to_numpy(float),
        ])
        ym = train["result"].to_numpy(float)
        bm, sm = _ols(xm, ym)

        xt = np.column_stack([
            train["off_home"].to_numpy(float), train["def_home"].to_numpy(float),
            train["off_away"].to_numpy(float), train["def_away"].to_numpy(float),
            train["indoor"].to_numpy(float),
        ])
        yt = train["total"].to_numpy(float)
        bt, st = _ols(xt, yt)

        cur = out["season"] == season
        xm_cur = np.column_stack([
            out.loc[cur, "elo_diff"].to_numpy(float),
            out.loc[cur, "rest_diff"].fillna(0.0).to_numpy(float),
            out.loc[cur, "qb_change_home"].to_numpy(float),
            out.loc[cur, "qb_change_away"].to_numpy(float),
        ])
        xt_cur = np.column_stack([
            out.loc[cur, "off_home"].to_numpy(float), out.loc[cur, "def_home"].to_numpy(float),
            out.loc[cur, "off_away"].to_numpy(float), out.loc[cur, "def_away"].to_numpy(float),
            out.loc[cur, "indoor"].to_numpy(float),
        ])
        out.loc[cur, "mu_spread"] = bm[0] + xm_cur @ bm[1:]
        out.loc[cur, "sd_spread"] = sm
        out.loc[cur, "sigma_ml"] = sm
        out.loc[cur, "mu_total"] = bt[0] + xt_cur @ bt[1:]
        out.loc[cur, "sd_total"] = st
    return out


# --------------------------------------------------------------------------- #
# Selection helpers
# --------------------------------------------------------------------------- #
def _probs(row: pd.Series, market: str, side: str) -> tuple[float, float, float]:
    if market == "ATS":
        return mk.spread_probs(row["mu_spread"], row["sd_spread"], row["spread_line"], side)
    if market == "TOTAL":
        return mk.total_probs(row["mu_total"], row["sd_total"], row["total_line"], side)
    return mk.moneyline_probs(row["mu_spread"], row["sd_spread"], side)


def _priced(row: pd.Series, market: str) -> bool:
    if market == "ATS":
        return pd.notna(row["home_spread_odds"]) and pd.notna(row["away_spread_odds"]) and pd.notna(row["spread_line"])
    if market == "TOTAL":
        return pd.notna(row["over_odds"]) and pd.notna(row["under_odds"]) and pd.notna(row["total_line"])
    return pd.notna(row["home_moneyline"]) and pd.notna(row["away_moneyline"])


def _bet(strategy_id: str, name: str, market: str, row: pd.Series, side: str,
         model_prob: float, market_prob: float, edge: float) -> Bet:
    price = mk.side_price(row, market, side)
    outcome = mk.settle(row, market, side)
    return Bet(
        strategy_id=strategy_id, strategy_name=name, market=market,
        season=int(row["season"]), week=int(row["week"]), game_id=str(row["game_id"]),
        kickoff=str(row["kickoff"]), side=side,
        line=float(mk.line_for(row, market)),
        price=float(price), model_prob=float(model_prob), market_prob=float(market_prob),
        edge=float(edge), outcome=int(outcome),
        pnl=float(mk.pnl_for(price, outcome)),
    )


def model_bets(df: pd.DataFrame, strategy_id: str, name: str, market: str) -> list[Bet]:
    """Pre-registered edge rule: |model - market| >= 3 pp, price in band, best side only."""
    bets: list[Bet] = []
    for _, row in df.iterrows():
        if not _priced(row, market) or pd.isna(row["mu_spread"]):
            continue
        if market == "TOTAL" and pd.isna(row["mu_total"]):
            continue
        fair = mk.market_prob(row, market)
        options = [("home", fair[0]), ("away", fair[1])] if market != "TOTAL" else [("over", fair[0]), ("under", fair[1])]
        best = None
        for side, mkt_p in options:
            price = mk.side_price(row, market, side)
            if not mk.price_ok(price):
                continue
            p_win, p_loss, _ = _probs(row, market, side)
            cond = p_win / (p_win + p_loss) if (p_win + p_loss) > 0 else np.nan
            if pd.isna(cond):
                continue
            edge = cond - mkt_p
            if best is None or edge > best[3]:
                best = (side, cond, mkt_p, edge)
        if best and best[3] >= mk.EDGE_MIN:
            bets.append(_bet(strategy_id, name, market, row, best[0], best[1], best[2], best[3]))
    return bets


def _rule_bets(df: pd.DataFrame, strategy_id: str, name: str, market: str,
               mask: pd.Series, side: str, base_rates: dict[int, float] | None = None) -> list[Bet]:
    bets: list[Bet] = []
    for _, row in df[mask].iterrows():
        if not _priced(row, market) or not mk.price_ok(mk.side_price(row, market, side)):
            continue
        fair = mk.market_prob(row, market)
        mkt_p = fair[0] if side in ("home", "over") else fair[1]
        model_p = (base_rates or {}).get(int(row["season"]), np.nan)
        edge = (model_p - mkt_p) if pd.notna(model_p) else np.nan
        bets.append(_bet(strategy_id, name, market, row, side, model_p, mkt_p, edge))
    return bets


# --------------------------------------------------------------------------- #
# Strategy definitions
# --------------------------------------------------------------------------- #
STRATEGIES = [
    ("S1", "Elo margin vs closing spread", "ATS"),
    ("S2", "Elo margin vs closing moneyline", "ML"),
    ("S3", "Scoring-profile totals", "TOTAL"),
    ("S4", "Rest asymmetry", "ATS"),
    ("S5", "Divisional home underdog", "ATS"),
    ("S6", "Weather under", "TOTAL"),
    ("S7", "Referee crew total tendency", "TOTAL"),
    ("S8", "Backup-quarterback fade", "ATS"),
    ("S9", "Two-leg cross-game ML parlay", "PARLAY"),
    ("S10", "Two-leg cross-game ATS parlay", "PARLAY"),
    ("S11", "Season win-total futures", "FUTURES"),
]


def build_all_bets(feats: pd.DataFrame, eval_start: int = 2006) -> pd.DataFrame:
    window = feats[(feats["season"] >= eval_start)].copy()
    window = window.sort_values(["kickoff", "game_id"])
    bets: list[Bet] = []

    bets += model_bets(window, "S1", "Elo margin vs closing spread", "ATS")
    bets += model_bets(window, "S2", "Elo margin vs closing moneyline", "ML")
    bets += model_bets(window, "S3", "Scoring-profile totals", "TOTAL")

    # S4 rest asymmetry (week >= 2 only; week 1 rest is a placeholder in the source)
    m4 = (window["week"] >= 2) & (window["rest_diff"].abs() >= 3)
    bets += _rule_bets(window[m4 & (window["rest_diff"] > 0)], "S4", "Rest asymmetry", "ATS", slice(None), "home")
    bets += _rule_bets(window[m4 & (window["rest_diff"] < 0)], "S4", "Rest asymmetry", "ATS", slice(None), "away")

    # S5 divisional home underdog
    m5 = (window["div_game"] == 1) & (window["spread_line"] < 0)
    bets += _rule_bets(window, "S5", "Divisional home underdog", "ATS", m5, "home")

    # S6 weather under
    m6 = window["roof"].isin(["outdoors", "open"]) & ((window["wind"] >= 15) | (window["temp"] <= 32))
    bets += _rule_bets(window, "S6", "Weather under", "TOTAL", m6, "under")

    # S7 referee crew tendency (expanding, prior games only, min 30 games)
    m7_over = window["ref_total_dev"] >= 1.5
    m7_under = window["ref_total_dev"] <= -1.5
    bets += _rule_bets(window, "S7", "Referee crew total tendency", "TOTAL", m7_over, "over")
    bets += _rule_bets(window, "S7", "Referee crew total tendency", "TOTAL", m7_under, "under")

    # S8 backup-QB fade
    m8_away = (window["qb_change_home"] == 1) & (window["qb_change_away"] == 0)
    m8_home = (window["qb_change_away"] == 1) & (window["qb_change_home"] == 0)
    bets += _rule_bets(window, "S8", "Backup-quarterback fade", "ATS", m8_away, "away")
    bets += _rule_bets(window, "S8", "Backup-quarterback fade", "ATS", m8_home, "home")

    frame = pd.DataFrame([b.as_row() for b in bets])
    if frame.empty:
        return frame

    # base-rate model probabilities for the signal rules (prior seasons only)
    frame = _attach_base_rates(frame)

    # S9 / S10 parlays from the model selections, two legs per week, different games
    frame = _add_parlays(frame)
    frame = _add_win_total_futures(frame, feats)
    frame = frame.sort_values(["kickoff", "strategy_id", "game_id"]).reset_index(drop=True)
    return frame


def _attach_base_rates(frame: pd.DataFrame) -> pd.DataFrame:
    out = frame.copy()
    out["base_rate"] = np.nan
    signal = out["strategy_id"].isin(["S4", "S5", "S6", "S7", "S8"])
    for sid in ["S4", "S5", "S6", "S7", "S8"]:
        sub = out[(out["strategy_id"] == sid) & (out["outcome"] != 0)]
        for season in sorted(out.loc[out["strategy_id"] == sid, "season"].unique()):
            prior = sub[sub["season"] < season]
            if len(prior) < 30:
                continue
            rate = float((prior["outcome"] > 0).mean())
            # nudge away from 0/1 so log loss stays finite
            rate = min(max(rate, 0.01), 0.99)
            idx = out.index[(out["strategy_id"] == sid) & (out["season"] == season)]
            out.loc[idx, "base_rate"] = rate
            out.loc[idx, "model_prob"] = rate
            out.loc[idx, "edge"] = rate - out.loc[idx, "market_prob"]
    out.loc[~signal, ["base_rate"]] = np.nan
    return out


def _add_parlays(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for sid, source, label in [("S9", "S2", "Two-leg cross-game ML parlay"),
                               ("S10", "S1", "Two-leg cross-game ATS parlay")]:
        seeds = frame[frame["strategy_id"] == source].copy()
        if seeds.empty:
            continue
        seeds["abs_edge"] = seeds["edge"].abs()
        for (season, week), group in seeds.groupby(["season", "week"]):
            group = group.sort_values("abs_edge", ascending=False).drop_duplicates("game_id")
            legs = group.head(2)
            if len(legs) < 2:
                continue
            decimal = 1.0
            outcome = 1
            for _, leg in legs.iterrows():
                outcome = 0 if leg["outcome"] == 0 else (outcome if leg["outcome"] > 0 else -1)
                decimal *= mk.american_to_decimal(leg["price"]) if leg["outcome"] != 0 else 1.0
            pnl = 0.0 if outcome == 0 else ((decimal - 1.0) if outcome > 0 else -1.0)
            model_p = float(np.prod(legs["model_prob"].astype(float)))
            market_p = float(np.prod(legs["market_prob"].astype(float)))
            rows.append({
                "strategy_id": sid, "strategy_name": label, "market": "PARLAY",
                "season": int(season), "week": int(week),
                "game_id": "+".join(legs["game_id"].astype(str)),
                "kickoff": str(legs["kickoff"].max()), "side": "parlay",
                "line": np.nan, "price": np.nan,
                "model_prob": model_p, "market_prob": market_p,
                "edge": model_p - market_p, "outcome": int(outcome), "pnl": float(pnl),
                "base_rate": np.nan,
            })
    if not rows:
        return frame
    return pd.concat([frame, pd.DataFrame(rows)], ignore_index=True)


def _add_win_total_futures(frame: pd.DataFrame, feats: pd.DataFrame) -> pd.DataFrame:
    """S11: prior-season Pythagorean projection vs preseason win-total line."""
    path = RAW / "win_totals.csv"
    if not path.exists():
        return frame
    totals = pd.read_csv(path)
    results = feats[feats["season"] >= 1999]
    rows = []
    for rec in totals.itertuples(index=False):
        season = int(rec.season)
        prior = results[results["season"] == season - 1]
        if prior.empty:
            continue
        home_rows = pd.DataFrame({"team": prior["home_team"].to_numpy(),
                                  "pf": prior["home_score"].to_numpy(float),
                                  "pa": prior["away_score"].to_numpy(float)})
        away_rows = pd.DataFrame({"team": prior["away_team"].to_numpy(),
                                  "pf": prior["away_score"].to_numpy(float),
                                  "pa": prior["home_score"].to_numpy(float)})
        team_games = pd.concat([home_rows, away_rows], ignore_index=True)
        tg = team_games[team_games["team"] == rec.team]
        if len(tg) < 8:
            continue
        pf, pa = float(tg["pf"].sum()), float(tg["pa"].sum())
        if pf + pa == 0:
            continue
        pyth = pf ** 2.6 / (pf ** 2.6 + pa ** 2.6)
        games_played = len(tg)
        projected = pyth * 16.0
        edge_wins = projected - float(rec.line)
        if abs(edge_wins) < 2.0:
            continue
        side = "over" if edge_wins > 0 else "under"
        price = rec.over_odds if side == "over" else rec.under_odds
        if not mk.price_ok(price):
            continue
        actual_games = results[(results["season"] == season) & (
            (results["home_team"] == rec.team) | (results["away_team"] == rec.team))]
        wins = int(((actual_games["home_team"] == rec.team) & (actual_games["result"] > 0)).sum()
                   + ((actual_games["away_team"] == rec.team) & (actual_games["result"] < 0)).sum())
        if len(actual_games) < games_played - 2:
            continue  # season not complete in the snapshot
        if wins == float(rec.line):
            outcome, pnl = 0, 0.0
        else:
            won = (wins > float(rec.line)) if side == "over" else (wins < float(rec.line))
            outcome = 1 if won else -1
            pnl = mk.pnl_for(price, outcome)
        market_p = None
        if pd.notna(rec.over_odds) and pd.notna(rec.under_odds):
            fair = mk.devig_two_way(rec.over_odds, rec.under_odds)
            market_p = fair[0] if side == "over" else fair[1]
        rows.append({
            "strategy_id": "S11", "strategy_name": "Season win-total futures", "market": "FUTURES",
            "season": season, "week": 0, "game_id": f"{season}_{rec.team}_WIN_TOTAL",
            "kickoff": f"{season}-09-01", "side": side, "line": float(rec.line), "price": float(price),
            "model_prob": np.nan, "market_prob": market_p if market_p is not None else np.nan,
            "edge": np.nan, "outcome": int(outcome), "pnl": float(pnl), "base_rate": np.nan,
        })
    if not rows:
        return frame
    return pd.concat([frame, pd.DataFrame(rows)], ignore_index=True)
