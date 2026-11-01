#!/usr/bin/env python3
"""run_all.py -- one command, full study.

    python3 scripts/run_all.py

Produces every number that appears on the site, into docs/data/*.json, plus the
derived tables in data/derived/.  Deterministic: fixed seeds everywhere.
"""
import json
import os
import platform
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

import market as MK
import correlations as CO
import props as PR
import validate as VA
from common import DERIVED, DOCS_DATA, REPO_URL, ROOT, write_json, r
from engine import (build_singles, build_parlays, build_sgp, settle_bets,
                    settle_parlays, settle_spread, settle_total, UNITS)
from features import build_features, assert_point_in_time
from model import build_predictions, quality_report

STRATEGY_META = {
    "S01": dict(name="Core spread edge", category="single", market="Spread",
                rule="Bet the side whose model margin differs from the closing spread by >= 2.0 pts "
                     "and whose expected value at the quoted price is >= +2%.",
                family="model"),
    "S02": dict(name="Core total edge", category="single", market="Total",
                rule="Bet over/under when the model total differs from the closing total by >= 2.5 pts "
                     "and EV >= +2%.", family="model"),
    "S03": dict(name="Wide spread edge", category="single", market="Spread",
                rule="As S01 with a 1.0-pt threshold (deliberately looser; tests whether selectivity helps).",
                family="model"),
    "S04": dict(name="Selective spread edge", category="single", market="Spread",
                rule="As S01 with a 4.0-pt threshold (only large disagreements with the market).",
                family="model"),
    "S05": dict(name="Selective total edge", category="single", market="Total",
                rule="As S02 with a 4.0-pt threshold.", family="model"),
    "S06": dict(name="Rest advantage", category="single", market="Spread",
                rule="Rest differential >= 4 days between the two teams AND model edge >= 1.0 pt.",
                family="model"),
    "S07": dict(name="Divisional home dog", category="single", market="Spread",
                rule="Divisional game, home team is the underdog, model edge >= 2.0 pts.",
                family="model"),
    "S08": dict(name="Fade the big favourite", category="single", market="Spread",
                rule="Closing spread >= 9 pts and the model disagrees by >= 1.5 pts on the underdog.",
                family="model"),
    "S09": dict(name="Dome totals", category="single", market="Total",
                rule="Indoor game only, total edge >= 2.0 pts.", family="model"),
    "S10": dict(name="Outdoor totals", category="single", market="Total",
                rule="Outdoor game only, total edge >= 2.0 pts.", family="model"),
    "S11": dict(name="Moneyline value", category="single", market="Moneyline",
                rule="Model win probability beats the de-vigged implied probability by >= 3 pts.",
                family="model"),
    "S12": dict(name="Moneyline value (selective)", category="single", market="Moneyline",
                rule="As S11 with a 8-pt gap and EV >= +5%.", family="model"),
    "P01": dict(name="Two-leg parlay", category="parlay", market="Mixed",
                rule="Each week, parlay the two highest-EV qualifying singles (S01/S02) from different games.",
                family="model"),
    "P02": dict(name="Three-leg parlay", category="parlay", market="Mixed",
                rule="Each week, parlay the three highest-EV qualifying singles from different games.",
                family="model"),
    "P03": dict(name="Same-game spread + total", category="sgp", market="Mixed",
                rule="Same game, spread leg and total leg both qualify (edge >= 1.5 pts each), priced at "
                     "the product of the two leg prices (book is assumed to ignore correlation).",
                family="model"),
    "T01": dict(name="Rec yards OVER", category="prop", market="Player prop",
                rule="Receiving yards over our number vs the naive trailing-median line, prior targets >= 4, "
                     "edge >= 5 pts. Priced at an ASSUMED -110 (see IR-03).", family="model"),
    "T02": dict(name="Rec yards UNDER", category="prop", market="Player prop",
                rule="Mirror of T01 on the under side.", family="model"),
    "T03": dict(name="Rec yards OVER (high usage)", category="prop", market="Player prop",
                rule="Prior targets >= 6 and edge >= 8 pts (selective variant).", family="model"),
    "T04": dict(name="Receptions OVER", category="prop", market="Player prop",
                rule="Receptions over, prior targets >= 4, edge >= 5 pts, assumed -110.", family="model"),
    "T05": dict(name="Receptions UNDER", category="prop", market="Player prop",
                rule="Mirror of T04 on the under side.", family="model"),
    "T06": dict(name="Rush attempts OVER", category="prop", market="Player prop",
                rule="Carries over for backs with prior carries >= 8, edge >= 5 pts, assumed -110.",
                family="model"),
    "T07": dict(name="Rush attempts UNDER", category="prop", market="Player prop",
                rule="Mirror of T06 on the under side.", family="model"),
    "T08": dict(name="Prop parlay: two team-mates", category="prop-parlay", market="Player prop combo",
                rule="Both of the top-two receivers on a team clear the edge filter; parlay priced at the "
                     "product of two -110 legs (27.4% break-even).", family="model"),
    "T09": dict(name="Prop parlay: same player, two markets", category="prop-parlay",
                market="Player prop combo",
                rule="Same player, targets over AND receptions over; priced at the product of two -110 legs.",
                family="model"),
    "C01": dict(name="Always home ATS", category="control", market="Spread",
                rule="Benchmark: bet the home team against the spread every game.", family="control"),
    "C02": dict(name="Always favourite ATS", category="control", market="Spread",
                rule="Benchmark: bet the favourite against the spread every game.", family="control"),
    "C03": dict(name="Always over", category="control", market="Total",
                rule="Benchmark: bet the over every game.", family="control"),
    "C04": dict(name="Coin-flip ATS", category="control", market="Spread",
                rule="Benchmark: randomly pick a side each game (seeded PRNG).", family="control"),
}


# --------------------------------------------------------------------------
def _sgp_bets(pred):
    sgp = build_sgp(pred, "P03", min_edge=1.5)
    if sgp.empty:
        return pd.DataFrame()
    rows = []
    for _, g in sgp.iterrows():
        dec = g.dec_s * g.dec_t
        p = g.p_s * g.p_t          # independence (rho measured at ~0.02)
        pm = g.pm_s * g.pm_t
        res_s = settle_spread(g.result, g.line_s, g.spread_side)
        res_t = settle_total(g.total, g.line_t, g.total_side)
        if "loss" in (res_s, res_t):
            outcome, profit = "loss", -UNITS
        elif res_s == "push" and res_t == "push":
            outcome, profit = "void", 0.0
        else:
            live = 1.0
            for res, d_ in ((res_s, g.dec_s), (res_t, g.dec_t)):
                if res == "win":
                    live *= d_
            outcome, profit = "win", (live - 1) * UNITS
        rows.append(dict(strategy_id="P03", bet_type="sgp", market="MIXED",
                         side=f"{g.spread_side} + {g.total_side}", season=int(g.season),
                         week=int(g.week), game_id=g.game_id, game_ids=g.game_id, n_legs=2,
                         line=np.nan, odds_dec=dec, p_model=p, p_market=pm, p_push=0.0,
                         ev=p * (dec - 1) - (1 - p), stake=UNITS, kelly=0.0, note="",
                         price_source="assumed",
                         home_team=g.home_team, away_team=g.away_team, gameday="",
                         outcome=outcome, profit=profit))
    return pd.DataFrame(rows)


def _prop_bets(markets, d):
    """Strategy T01-T07 plus the two prop-parlay strategies T08/T09."""
    rows = []
    for stat, m in markets.items():
        for spec in PR.PROP_SPECS.get(stat, []):
            b = PR.apply_prop_spec(m, spec)
            if b.empty:
                continue
            b = b.copy()
            b["bet_type"] = "prop"
            b["market"] = "PLAYER PROP"
            b["game_id"] = b["game_id"]
            b["stake"] = UNITS
            b["season"] = b.season
            b["p_push"] = b["push"].astype(float)
            b["kelly"] = 0.0
            b["price_source"] = "assumed"
            b["outcome"] = np.where(b["push"] == 1, "push",
                                    np.where(b["won"] == 1, "win", "loss"))
            b["note"] = ""
            b["home_team"] = ""
            b["away_team"] = ""
            b["gameday"] = ""
            rows.append(b)
    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame()
    return out


def _prop_parlays(mk_y, mk_t, mk_rec):
    """T08: two team-mates, both rec-yards overs.  T09: same player, targets + receptions."""
    rows = []

    def prep(m, stat, leg):
        x = m[(m.push == 0)].copy()
        for c in ["p_over", "line", "player_name", "game_id", "team", "position",
                  "season", "week", "over_won", f"targets_mu"]:
            if c in x.columns:
                x[f"{leg}_{c}"] = x[c]
        return x

    a = mk_y[["game_id", "team", "player_name", "position", "season", "week", "p_over",
              "line", "over_won", "targets_mu"]].copy()
    a = a[a.targets_mu >= 4]
    pairs = []
    for (gid, team), g in a.groupby(["game_id", "team"]):
        if len(g) < 2:
            continue
        g = g.sort_values("targets_mu", ascending=False).head(2)
        if len(g) < 2:
            continue
        p1, p2 = g.iloc[0], g.iloc[1]
        if (p1.p_over - 0.5) < 0.03 or (p2.p_over - 0.5) < 0.03:
            continue
        dec = PR.ASSUMED_DEC ** 2
        p = p1.p_over * p2.p_over
        won = int(p1.over_won == 1 and p2.over_won == 1)
        rows.append(dict(strategy_id="T08", bet_type="prop-parlay", market="PROP COMBO",
                         side=f"{p1.player_name} + {p2.player_name} rec yds over",
                         season=int(p1.season), week=int(p1.week), game_id=gid, game_ids=gid,
                         n_legs=2, line=np.nan, odds_dec=dec, p_model=p, p_market=p, p_push=0.0,
                         ev=p * (dec - 1) - (1 - p), stake=UNITS, kelly=0.0, note="",
                         price_source="assumed",
                         home_team="", away_team="", gameday="",
                         outcome="win" if won else "loss",
                         profit=(dec - 1) * UNITS if won else -UNITS))

    # T09: same player, targets over + receptions over
    j = mk_t.merge(mk_rec[["game_id", "player_name", "p_over", "over_won"]],
                   on=["game_id", "player_name"], suffixes=("_tgt", "_rec"))
    j = j[(j.p_over_tgt - 0.5 >= 0.03) & (j.p_over_rec - 0.5 >= 0.03)]
    if len(j):
        dec = PR.ASSUMED_DEC ** 2
        p = j.p_over_tgt * j.p_over_rec
        won = ((j.over_won_tgt == 1) & (j.over_won_rec == 1)).astype(int)
        for (_, row), w in zip(j.iterrows(), won):
            rows.append(dict(strategy_id="T09", bet_type="prop-parlay", market="PROP COMBO",
                             side=f"{row.player_name} targets + receptions over",
                             season=int(row.season), week=int(row.week), game_id=row.game_id,
                             game_ids=row.game_id, n_legs=2, line=np.nan, odds_dec=dec,
                             p_model=p[len(rows) - 0] if False else row.p_over_tgt * row.p_over_rec,
                             p_market=row.p_over_tgt * row.p_over_rec, p_push=0.0,
                             ev=0.0, stake=UNITS, kelly=0.0, note="", price_source="assumed",
                             home_team="", away_team="", gameday="",
                             outcome="win" if w else "loss",
                             profit=(dec - 1) * UNITS if w else -UNITS))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
def leaderboard(results):
    """Composite score + reward rubric.

    40% validation gates (the hard filters)
    30% lower bound of the ROI confidence interval (edge that survives sampling error)
    15% luck-null evidence (p-value against the zero-skill simulation)
    15% season consistency
    """
    rows = []
    for x in results:
        gates = x["gates_passed"] / x["gates_total"]
        lo = (x.get("roi_ci_bet") or [None, None])[0]
        edge = 0.0 if lo is None else float(np.clip((lo + 0.05) / 0.15, 0, 1))
        p = x.get("p_value_vs_market")
        luck = 0.0 if p is None else float(np.clip(1 - p / 0.10, 0, 1))
        cons = x.get("pct_seasons_profitable") or 0.0
        score = 100 * (0.40 * gates + 0.30 * edge + 0.15 * luck + 0.15 * cons)
        if not x.get("prices_observed", True):
            tier, reward = "price-unverified", 0.0
        elif x.get("is_control"):
            tier, reward = "benchmark", 0.0
        elif x.get("passes_all"):
            tier, reward = "A", 100.0
        elif score >= 55:
            tier, reward = "B", 60.0
        elif score >= 40:
            tier, reward = "C", 25.0
        else:
            tier, reward = "D", 5.0
        rows.append(dict(strategy_id=x["strategy_id"], score=score, tier=tier,
                         prices_observed=bool(x.get("prices_observed", True)),
                         reward_points=reward, roi=x["roi"],
                         roi_ci_lo=lo, p_value=p, gates_passed=x["gates_passed"],
                         gates_total=x["gates_total"], passes_all=x["passes_all"],
                         is_control=bool(x.get("is_control")),
                         pct_seasons_profitable=cons,
                         n_bets=x["n_bets"]))
    # ranking pool = strategies whose prices are all observed and that are not
    # benchmarks.  Assumed-price strategies are shown but not ranked or rewarded.
    def group(z):
        if z["is_control"]:
            return 2
        if not z["prices_observed"]:
            return 1
        return 0

    rows.sort(key=lambda z: (group(z), -z["score"]))
    rank = 0
    for z in rows:
        if group(z) == 0:
            rank += 1
            z["rank"] = rank
        else:
            z["rank"] = None
    pool = [z for z in rows if group(z) == 0]
    total = sum(z["score"] ** 2 for z in pool) or 1.0
    for z in pool:
        z["allocation_weight"] = z["score"] ** 2 / total
    return rows


def main():
    os.makedirs(DOCS_DATA, exist_ok=True)
    gen = datetime.now(timezone.utc).isoformat(timespec="seconds")
    prov = json.load(open(f"{ROOT}/data/PROVENANCE.json"))

    # ---- data + model ----------------------------------------------------
    feats = build_features()
    guard = assert_point_in_time(feats)
    pred, params = build_predictions(feats)
    pred.to_csv(f"{DERIVED}/predictions.csv", index=False)
    quality = quality_report(pred)

    played = pred[pred.result.notna()].copy()

    # ---- market structure ------------------------------------------------
    market_obj = {
        "hold": MK.hold_stats(played),
        "base_rates": MK.base_rates(played),
        "favourite_longshot": MK.favourite_longshot(played),
        "line_movement": MK.line_movement(pred),
        "margin_distribution": MK.quarter_lines(played),
    }

    # ---- bets ------------------------------------------------------------
    singles = settle_bets(build_singles(played), played)
    parlays = build_parlays(singles)
    parlay_df = settle_parlays(parlays, played) if parlays else pd.DataFrame()
    sgp_df = _sgp_bets(played)

    pw_raw, markets = PR.build_prop_market_table()
    prob_maps = {}
    for stat in list(markets):
        markets[stat], prob_maps[stat] = PR.empirical_probability(markets[stat], stat)
    prop_df = _prop_bets(markets, pw_raw)
    # targets market (needed for the same-player parlay)
    mk_tgt = PR.build_prop_markets(pw_raw, "targets")
    mk_tgt, _ = PR.empirical_probability(mk_tgt, "targets")
    prop_parlay_df = _prop_parlays(markets["receiving_yards"], mk_tgt, markets["receptions"])

    all_bets = pd.concat([x for x in [singles, parlay_df, sgp_df, prop_df, prop_parlay_df]
                          if len(x)], ignore_index=True)
    all_bets.to_csv(f"{DERIVED}/bets.csv", index=False)

    # ---- evaluation ------------------------------------------------------
    results = []
    for sid in STRATEGY_META:
        if sid not in set(all_bets.strategy_id):      # registered but produced no qualifying bet
            empty = all_bets.iloc[0:0]
            res = dict(strategy_id=sid, n_bets=0, n_decided=0, prices_observed=True,
                       seasons=[], n_seasons=0, stake=0.0, profit=0.0, roi=float("nan"),
                       hit_rate=None, avg_dec=None, avg_model_prob=None, avg_market_prob=None,
                       roi_ci_bet=None, roi_ci_season=None, by_season=[],
                       pct_seasons_profitable=None, holdout_roi=None, holdout_n=0,
                       p_value_vs_market=None, edge_monotonicity=None,
                       sharpe_per_bet=float("nan"), skew=0.0, kurtosis=3.0,
                       note="no bet qualified under this rule in the backtest window")
            res.update(STRATEGY_META.get(sid, {}))
            results.append(res)
    for sid, g in all_bets.groupby("strategy_id"):
        res = VA.evaluate_strategy(sid, g)
        res.update(STRATEGY_META.get(sid, {}))
        results.append(res)
    results, fdr = VA.apply_gates(results, leakage_ok=guard["passed"])

    # calibration + prop diagnostics
    prop_diag = {}
    for stat, m in markets.items():
        dec = m[m.push == 0]
        bins = pd.qcut(dec.p_over, 10, duplicates="drop")
        cal = dec.groupby(bins, observed=True).agg(pred=("p_over", "mean"),
                                                   actual=("over_won", "mean"),
                                                   n=("over_won", "size")).reset_index(drop=True)
        prop_diag[stat] = {
            "n_markets": int(len(m)), "push_rate": float(m.push.mean()),
            "over_rate_decided": float(dec.over_won.mean()),
            "calibration": [{"predicted": float(a.pred), "actual": float(a.actual),
                             "n": int(a.n)} for a in cal.itertuples()],
            "brier": float(np.mean((dec.p_over - dec.over_won) ** 2)),
            "brier_baseline_50": float(np.mean((0.5 - dec.over_won) ** 2)),
            "brier_note": "pushes excluded from the Brier score",
            "assumed_price": "-110",
            "breakeven_hit_rate": PR.BREAKEVEN_HIT,
        }

    # ---- correlations ----------------------------------------------------
    corr_obj = {
        "within_game": CO.within_game(played),
        "sgp_joint": CO.sgp_joint(played),
        "cross_game": CO.cross_game(played),
        "props": CO.prop_correlations(pw_raw),
        "prop_dispersion": CO.prop_dispersion(pw_raw),
    }

    # ---- line board ------------------------------------------------------
    board = pred[pred.season == 2026].copy()
    board = board.sort_values(["week", "gameday"])
    line_board = []
    for _, g in board.iterrows():
        line_board.append({
            "week": int(g.week), "date": g.gameday, "home": g.home_team, "away": g.away_team,
            "my_spread": r(g.my_spread, 1), "market_spread": r(g.spread_line, 1),
            "edge_spread": r(g.edge_spread, 2),
            "my_total": r(g.my_total, 1), "market_total": r(g.total_line, 1),
            "edge_total": r(g.edge_total, 2),
            "model_margin_raw": r(g.mu_margin, 2), "model_total_raw": r(g.mu_total, 2),
            "market_total_hold": None,
            "played": bool(not pd.isna(g.result)),
            "result": r(g.result, 0) if not pd.isna(g.result) else None,
            "ats_grade": ("push" if (not pd.isna(g.result) and g.result == g.spread_line)
                          else "won" if (not pd.isna(g.result) and g.result > g.spread_line)
                          else "lost" if not pd.isna(g.result) else None),
            "source": "nflverse/nfldata games.csv (pinned commit)",
        })

    # ---- leaderboard -----------------------------------------------------
    lb = leaderboard(results)

    # ---- write site data -------------------------------------------------
    write_json(f"{DOCS_DATA}/meta.json", {
        "generated_utc": gen, "repo": REPO_URL,
        "python": platform.python_version(), "numpy": np.__version__,
        "pandas": pd.__version__,
        "n_games": int(len(feats)), "n_games_with_lines": int(played.spread_line.notna().sum()),
        "n_bets": int(len(all_bets)), "n_strategies": int(len(results)),
        "n_passing_all_gates": int(sum(1 for x in results if x["passes_all"])),
        "seasons_backtested": [int(played.season.min()), int(played.season.max())],
        "dataset_commit": prov["files"]["games.csv"]["commit"],
        "dataset_url": prov["files"]["games.csv"]["pinned_url"],
        "leakage_guard": guard,
        "model_quality": quality,
    })
    write_json(f"{DOCS_DATA}/market.json", market_obj)
    write_json(f"{DOCS_DATA}/model.json", {"quality": quality, "season_params": params})
    write_json(f"{DOCS_DATA}/strategies.json", {
        "registry": [dict(id=k, **v) for k, v in STRATEGY_META.items()],
        "results": results, "fdr_passed": fdr})
    write_json(f"{DOCS_DATA}/leaderboard.json", lb)
    write_json(f"{DOCS_DATA}/parlays.json", {
        "results": [x for x in results if x["strategy_id"] in ("P01", "P02", "P03", "T08", "T09")],
        "cross_game_independence": corr_obj["cross_game"],
        "sgp_joint": corr_obj["sgp_joint"]})
    write_json(f"{DOCS_DATA}/props.json", {
        "diagnostics": prop_diag, "probability_maps": prob_maps,
        "results": [x for x in results if x["strategy_id"].startswith("T")],
        "dispersion": corr_obj["prop_dispersion"],
        "assumed_price_note": "Prop prices are ASSUMED -110; no verifiable prop price source was "
                              "available. Hit rates are measured, ROI is conditional on the assumption."})
    write_json(f"{DOCS_DATA}/correlations.json", corr_obj)
    write_json(f"{DOCS_DATA}/validation.json", {
        "gate_definitions": [{"id": a, "name": b, "test": c} for a, b, c in VA.GATE_DEFS],
        "holdout_seasons": VA.HOLDOUT_SEASONS, "min_bets": VA.MIN_BETS,
        "min_seasons": VA.MIN_SEASONS, "n_sims": VA.N_SIMS,
        "results": [{k: x[k] for k in ("strategy_id", "name", "category", "n_bets",
                                       "gates", "gates_passed", "gates_total", "passes_all",
                                       "holdout_roi", "p_value_vs_market",
                                       "pct_seasons_profitable", "roi_drop_best_season")
                     if k in x} for x in results]})
    write_json(f"{DOCS_DATA}/luck.json", {
        "results": [{k: x[k] for k in ("strategy_id", "name", "roi", "roi_ci_bet",
                                       "roi_ci_season", "null_roi_mean", "null_roi_sd",
                                       "null_roi_p05", "null_roi_p95", "p_value_vs_market",
                                       "sharpe_per_bet", "skew", "kurtosis",
                                       "edge_monotonicity", "by_season", "n_bets")
                     if k in x} for x in results]})
    write_json(f"{DOCS_DATA}/lineboard.json", line_board)
    write_json(f"{DOCS_DATA}/sources.json", prov)

    print(f"games={len(feats)} bets={len(all_bets)} strategies={len(results)} "
          f"passing_all_gates={sum(1 for x in results if x['passes_all'])}")
    print("top of leaderboard:", [f"{z['strategy_id']}:{z['score']:.1f}" for z in lb[:5]])
    return 0


if __name__ == "__main__":
    sys.exit(main())
