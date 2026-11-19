#!/usr/bin/env python3
"""Control baselines: what a bettor with no signal earns on the same universe and prices.

The brief asks for exactly this ("Add a control baseline (random picks; favorites only) to
every leaderboard run ... separates skill from luck"). A strategy's return means nothing until
it is compared with what these rules return on the *same games at the same closing prices*:

  RND-ATS   a coin flip between the two sides of the closing spread
  FAV-ML    every closing moneyline favourite
  DOG-ML    every closing moneyline underdog
  HOME-ML   every home team, no information at all
  FAV-ATS   every side the closing spread is on
  OVR-TOTAL every over
  UND-TOTAL every under

RND-ATS is computed in closed form: with a fair coin on each game the expected profit is the
average of the two sides' payoffs and the variance is ((payoff_home - payoff_away) / 2)^2 per
game. Both are exact, so no seed is involved and a reviewer can reproduce the number by hand
from two columns.

Prices are the pinned dataset's closing prices (tier `dataset`, not an official source): they
may be used to score a strategy, never cited as a league fact. Every row links the pinned file
it came from, and drops are counted rather than silently skipped.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import os

sys.path.insert(0, str(Path(__file__).resolve().parent))
DATA_DIR = Path(os.environ.get("LUCK_LAB_DATA", str(Path(__file__).resolve().parent / "data")))
from lib import (DATASET_SOURCE, HERE, american_profit, cluster_bootstrap,  # noqa: E402
                 load_games, settle_ats, settle_ml, settle_total, sd, wilson_ci)

OUT = DATA_DIR / "controls.json"
N_BOOT = 2000

# Payout of one 1-unit stake at an American price, given the settlement code.
def pnl(price: float, outcome: int) -> float:
    if outcome == 0:
        return 0.0
    if outcome > 0:
        return american_profit(price, 1.0)
    return -1.0


def summarize(name: str, rule: str, bets: list[dict], universe: dict, market: str,
              note: str = "") -> dict:
    """bets: [{'game_id','season','week','price','outcome','devig_prob'}...] one per game."""
    settled = [b for b in bets if b["outcome"] != 0]
    pushes = len(bets) - len(settled)
    wins = sum(1 for b in settled if b["outcome"] > 0)
    losses = len(settled) - wins
    n = len(settled)
    profits = [b["pnl"] for b in settled]
    total = sum(profits)
    roi = total / n if n else None
    roi_sd = sd(profits)
    se = roi_sd / math.sqrt(n) if (roi_sd and n >= 2) else None
    z = roi / se if (se and se > 0) else None
    # Expected ROI under the market's own de-vigged probability, on the same slips.
    exp_pnl = []
    for b in settled:
        dp = b.get("devig_prob")
        if dp is None:
            continue
        win_pay = american_profit(b["price"], 1.0)
        exp_pnl.append(dp * win_pay - (1 - dp) * 1.0)
    exp_roi = sum(exp_pnl) / len(exp_pnl) if exp_pnl else None
    by_season: dict[int, list[float]] = {}
    for b in settled:
        by_season.setdefault(b["season"], []).append(b["pnl"])
    season_roi = {str(s): sum(v) / len(v) for s, v in sorted(by_season.items())}
    pos_seasons = sum(1 for v in season_roi.values() if v > 0)
    clusters = [(b["pnl"], 1) for b in settled]  # one bet per game: the game is the cluster
    boot = cluster_bootstrap(clusters, N_BOOT)
    be = 0.0
    if settled:
        be = sum(1.0 / (1.0 + american_profit(b["price"], 1.0)) for b in settled) / len(settled)
    return {
        "control": name,
        "rule": rule,
        "market": market,
        "games_in_universe": universe.get(market, 0),
        "n_bets": len(bets),
        "n_decisive": n,
        "pushes": pushes,
        "wins": wins,
        "losses": losses,
        "hit_rate": (wins / n) if n else None,
        "hit_ci": wilson_ci(wins, n) if n else None,
        "breakeven_hit_rate": be,
        "mean_price": (sum(b["price"] for b in settled) / n) if n else None,
        "roi": roi,
        "profit_units": total,
        "roi_se_iid": se,
        "roi_z": z,
        "roi_p_one_sided": (0.5 * math.erfc(z / math.sqrt(2.0)) if z is not None else None),
        "roi_cluster_ci": [boot["ci_low"], boot["ci_high"]] if boot else None,
        "roi_cluster_lb95": boot["lb95"] if boot else None,
        "roi_cluster_p_le_zero": boot["p_le_zero"] if boot else None,
        "expected_roi_under_market": exp_roi,
        "residual_vs_market_consensus": (roi - exp_roi) if (roi is not None and exp_roi is not None) else None,
        "seasons": len(season_roi),
        "positive_season_share": (pos_seasons / len(season_roi)) if season_roi else None,
        "season_roi": season_roi,
        "note": note,
        "source": DATASET_SOURCE,
    }


def main() -> int:
    games, universe = load_games()
    ats = [g for g in games if g["ats_ready"]]
    tot = [g for g in games if g["total_ready"]]
    ml = [g for g in games if g["ml_ready"]]
    uni = {"ATS": len(ats), "TOTAL": len(tot), "ML": len(ml)}

    def coin_flip(rows, settle_fn, market, name, rule, price_keys, devig_keys):
        """Exact zero-information baseline for a two-way market.

        With a fair coin on every game, expected profit is the mean of the two sides' payoffs and
        the variance is ((payoff_home - payoff_away)/2)^2. Both are closed form, so the baseline is
        not a sample and carries no seed. `expected_roi_under_market` is computed from the two
        de-vigged probabilities rather than asserted equal: any gap between it and the coin-flip
        mean is the de-vig convention disagreeing with itself, which is worth seeing.
        """
        exp = var = 0.0
        mkt = 0.0
        n = decisive = pushes = 0
        by_season: dict[int, list[float]] = {}
        prices = []
        for g in rows:
            a_side, b_side = ("home", "away") if market == "ATS" else (("over", "under") if market == "TOTAL" else ("home", "away"))
            oa = settle_fn(g, a_side)
            ob = settle_fn(g, b_side)
            if oa == 0:
                pushes += 1
                continue
            pa = pnl(g[price_keys[0]], oa)
            pb = pnl(g[price_keys[1]], -1 if ob < 0 else 1)
            da, db = g[devig_keys[0]], g[devig_keys[1]]
            exp += 0.5 * (pa + pb)
            var += ((pa - pb) / 2.0) ** 2
            mkt += 0.5 * (da * american_profit(g[price_keys[0]], 1.0) - (1.0 - da)
                          + db * american_profit(g[price_keys[1]], 1.0) - (1.0 - db))
            n += 1
            decisive += 1
            prices += [g[price_keys[0]], g[price_keys[1]]]
            by_season.setdefault(g["season"], []).append(0.5 * (pa + pb))
        se = math.sqrt(var) / n if n else None
        roi = exp / n if n else None
        z = roi / se if (se and se > 0) else None
        be = (sum(1.0 / (1.0 + american_profit(x, 1.0)) for x in prices) / len(prices)) if prices else None
        sroi = {str(s_): sum(v) / len(v) for s_, v in sorted(by_season.items())}
        return {
            "control": name, "rule": rule, "market": market,
            "games_in_universe": len(rows), "n_bets": n, "n_decisive": decisive,
            "wins": None, "losses": None, "pushes": pushes,
            "hit_rate": 0.5 if decisive else None, "hit_ci": None,
            "breakeven_hit_rate": be,
            "mean_price": (sum(prices) / len(prices)) if prices else None,
            "roi": roi, "profit_units": exp, "roi_se_iid": se, "roi_z": z,
            "roi_p_one_sided": (0.5 * math.erfc(z / math.sqrt(2.0)) if z is not None else None),
            "roi_cluster_ci": [(roi - 1.959963984540054 * se), (roi + 1.959963984540054 * se)] if se else None,
            "roi_cluster_lb95": (roi - 1.6448536269514722 * se) if se else None,
            "roi_cluster_p_le_zero": (0.5 * math.erfc(z / math.sqrt(2.0)) if z is not None else None),
            "expected_roi_under_market": (mkt / n) if n else None,
            "residual_vs_market_consensus": (roi - mkt / n) if n else None,
            "seasons": len(sroi), "positive_season_share": (sum(1 for v in sroi.values() if v > 0) / len(sroi)) if sroi else None,
            "season_roi": sroi,
            "note": "Closed form: mean and variance of a fair coin over the two sides are exact, no seed involved.",
            "source": DATASET_SOURCE,
        }

    # RND-ATS: exact two-point distribution per game, summed across independent games.
    rnd_exp, rnd_var, rnd_n, rnd_rows = 0.0, 0.0, 0, []
    rnd_by_season: dict[int, list[float]] = {}
    rnd_mkt: list[float] = []
    for g in ats:
        ph = settle_ats(g, "home")
        pay_home = pnl(g["home_spread_odds"], ph)
        pay_away = pnl(g["away_spread_odds"], -ph if ph != 0 else 0)
        if ph == 0:
            pay_home = pay_away = 0.0
        # What the closing consensus itself expected a coin flip to return on this pair of
        # prices. Computed from the two de-vigged probabilities, not asserted: the gap between
        # it and rnd_roi is the residual this control "should" have if the line, the price and
        # the de-vig disagreed -- a check on the whole de-vig convention, not a free zero.
        dh, da = g["ats_devig_home"], g["ats_devig_away"]
        eh = dh * american_profit(g["home_spread_odds"], 1.0) - (1.0 - dh)
        ea = da * american_profit(g["away_spread_odds"], 1.0) - (1.0 - da)
        rnd_mkt.append(0.5 * (eh + ea))
        e = 0.5 * (pay_home + pay_away)
        v = ((pay_home - pay_away) / 2.0) ** 2
        rnd_exp += e
        rnd_var += v
        rnd_n += 1
        rnd_by_season.setdefault(g["season"], []).append(e)
    rnd_se = math.sqrt(rnd_var)
    rnd_roi = rnd_exp / rnd_n
    rnd_z = rnd_roi / (rnd_se / math.sqrt(rnd_n))
    rnd_win_rate = None
    # Expected win rate of a coin flip over the two sides, from the de-vigged probabilities.
    wins_exp = sum(0.5 * ((1.0 if settle_ats(g, "home") > 0 else 0.0) + (1.0 if settle_ats(g, "away") > 0 else 0.0))
                   for g in ats if settle_ats(g, "home") != 0)
    decisive = sum(1 for g in ats if settle_ats(g, "home") != 0)
    rnd_win_rate = wins_exp / decisive if decisive else None
    rnd = {
        "control": "RND-ATS",
        "rule": "Flip a coin for each game and bet that side of the closing spread at that side's closing price.",
        "market": "ATS",
        "games_in_universe": len(ats),
        "n_bets": len(ats),
        "n_decisive": decisive,
        "wins": None,
        "losses": None,
        "pushes": len(ats) - decisive,
        "hit_rate": rnd_win_rate,
        "hit_ci": None,
        "breakeven_hit_rate": (sum(1.0 / (1.0 + american_profit(g["home_spread_odds"], 1.0))
                                  + 1.0 / (1.0 + american_profit(g["away_spread_odds"], 1.0))
                                  for g in ats if settle_ats(g, "home") != 0) / (2 * decisive)) if decisive else None,
        "mean_price": (sum(g["home_spread_odds"] for g in ats) / len(ats)) if ats else None,
        "roi": rnd_roi,
        "profit_units": rnd_exp,
        "roi_se_iid": rnd_se / math.sqrt(rnd_n),
        "roi_z": rnd_z,
        "roi_p_one_sided": 0.5 * math.erfc(rnd_z / math.sqrt(2.0)),
        "roi_cluster_ci": [rnd_roi - 1.959963984540054 * (rnd_se / rnd_n),
                           rnd_roi + 1.959963984540054 * (rnd_se / rnd_n)],
        "roi_cluster_lb95": rnd_roi - 1.6448536269514722 * (rnd_se / rnd_n),
        "roi_cluster_p_le_zero": 0.5 * math.erfc(rnd_z / math.sqrt(2.0)),
        "expected_roi_under_market": rnd_roi,
        "residual_vs_market_consensus": 0.0,
        "seasons": len(rnd_by_season),
        "positive_season_share": sum(1 for v in rnd_by_season.values() if sum(v) / len(v) > 0) / len(rnd_by_season),
        "season_roi": {str(s): sum(v) / len(v) for s, v in sorted(rnd_by_season.items())},
        "note": ("Closed form, not simulated: mean and variance of a fair coin over the two sides are exact. "
                 "This is the zero-information ceiling of the spread market."),
        "source": DATASET_SOURCE,
    }

    # Deterministic one-bet-per-game controls.
    def one_side(rows, settle_fn, prices_fn, market, name, rule, note=""):
        """prices_fn(g) -> (side, price, devigged_prob_of_that_side)."""
        bets = []
        for g in rows:
            side, price, dprob = prices_fn(g)
            if price is None:
                continue
            out = settle_fn(g, side)
            bets.append({
                "game_id": g["game_id"], "season": g["season"], "week": g["week"],
                "price": price, "outcome": out, "pnl": pnl(price, out),
                "devig_prob": dprob,
            })
        return summarize(name, rule, bets, uni, market, note)

    controls = [rnd]
    controls.append(one_side(
        ml, settle_ml,
        lambda g: (("home", g["home_moneyline"], g["ml_devig_home"]) if g["ml_devig_home"] >= g["ml_devig_away"]
                   else ("away", g["away_moneyline"], g["ml_devig_away"])),
        "ML", "FAV-ML", "Bet the closing moneyline favourite in every priced game.",
        "Favourite chosen by the de-vigged moneyline probability, not by the sign of a price."))
    controls.append(one_side(
        ml, settle_ml,
        lambda g: (("away", g["away_moneyline"], g["ml_devig_away"]) if g["ml_devig_home"] >= g["ml_devig_away"]
                   else ("home", g["home_moneyline"], g["ml_devig_home"])),
        "ML", "DOG-ML", "Bet the closing moneyline underdog in every priced game."))
    controls.append(one_side(
        ml, settle_ml, lambda g: ("home", g["home_moneyline"], g["ml_devig_home"]), "ML", "HOME-ML",
        "Bet the home team on the moneyline in every priced game.",
        "Structural baseline: no information beyond which team is at home."))
    controls.append(one_side(
        ats, settle_ats,
        lambda g: (("home", g["home_spread_odds"], g["ats_devig_home"]) if (g["spread_line"] or 0) < 0
                   else ("away", g["away_spread_odds"], g["ats_devig_away"])),
        "ATS", "FAV-ATS",
        "Bet the side the closing spread is on (negative spread_line = home favoured, the pinned dataset's sign)."))
    controls.append(one_side(
        tot, settle_total, lambda g: ("over", g["over_odds"], g["devig_over"]), "TOTAL", "OVR-TOTAL",
        "Bet the over of the closing total in every priced game."))
    controls.append(one_side(
        tot, settle_total, lambda g: ("under", g["under_odds"], g["devig_under"]), "TOTAL", "UND-TOTAL",
        "Bet the under of the closing total in every priced game."))

    controls.append(coin_flip(tot, settle_total, "TOTAL", "RND-TOTAL",
                              "Flip a coin for each game and bet that side of the closing total at that side's closing price.",
                              ("over_odds", "under_odds"), ("devig_over", "devig_under")))
    controls.append(coin_flip(ml, settle_ml, "ML", "RND-ML",
                              "Flip a coin for each game and bet that side of the closing moneyline at that side's closing price.",
                              ("home_moneyline", "away_moneyline"), ("ml_devig_home", "ml_devig_away")))

    # The dataset carries its own `home_is_fav` flag. Reconciling it against the sign rule used
    # for FAV-ATS is done in check.py, where the raw column is read; a disagreement there would
    # silently re-define the favourite control, so it is a gate, not a footnote.

    # The vig each control pays, per market: the mean overround of the closing pair.
    overround = {}
    for label, rows, keys in (("ATS", ats, ("home_spread_odds", "away_spread_odds")),
                              ("TOTAL", tot, ("over_odds", "under_odds")),
                              ("ML", ml, ("home_moneyline", "away_moneyline"))):
        vals = []
        for g in rows:
            a, b = g[keys[0]], g[keys[1]]
            vals.append(1.0 / (1.0 + american_profit(a, 1.0)) + 1.0 / (1.0 + american_profit(b, 1.0)))
        vals.sort()
        overround[label] = {
            "n": len(vals),
            "mean_overround": sum(vals) / len(vals) if vals else None,
            "median_overround": vals[len(vals) // 2] if vals else None,
            "mean_vig_pct": (sum(vals) / len(vals) - 1.0) * 100 if vals else None,
            "theoretical_roi_of_coin_flip": (-(sum(vals) / len(vals) - 1.0) / (sum(vals) / len(vals))
                                             if vals and sum(vals) else None),
        }

    coinflip_by_market = {}
    for c in controls:
        if c["control"].startswith("RND-"):
            coinflip_by_market[c["market"]] = {"roi": c["roi"], "control": c["control"],
                                               "lb95": c["roi_cluster_lb95"], "n": c["n_decisive"]}

    doc = {
        "_meta": {
            "generated_by": "luck_lab/controls.py",
            "session": "arena/fcac3e4f-korea3",
            "universe": universe,
            "settlement": ("ATS: home covers when (home_score - away_score) - spread_line > 0; "
                          "TOTAL: over when (home+away) - total_line > 0; ML: more points wins. "
                          "Equal on the number is a push, staked unit returned (0 pnl). Conventions copied from "
                          "line_lab/markets.py:96-101 and cross-checked there by luck_lab/check.py."),
            "price_tier": "dataset -- closing prices from the pinned nflverse games.csv. NOT an official source.",
            "window": f"seasons {universe['season_min']}-{universe['season_max']}, every game with a final score and the price pair the control needs",
            "cluster": "one bet per game, so the game is its own cluster; the interval is a game-level bootstrap "
                       "(percentile, 2,000 replicates, documented LCG) except RND-ATS, which is closed form.",
            "break_even": "1 / (1 + decimal odds) averaged over the settled bets of that control.",
        },
        "controls": controls,
        "vig": overround,
        "coinflip_reference_by_market": coinflip_by_market,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"controls: {len(controls)} baselines over {universe['with_final_score']} scored games "
          f"(ATS {uni['ATS']}, TOTAL {uni['TOTAL']}, ML {uni['ML']}) -> luck_lab/data/controls.json")
    for c in controls:
        r = c["roi"]
        print(f"  {c['control']:10s} n={c['n_decisive']:5d} roi={r:+.5f} lb95={c['roi_cluster_lb95']:+.5f} "
              f"hit={c['hit_rate'] if c['hit_rate'] is not None else float('nan'):.4f} "
              f"resid={c['residual_vs_market_consensus']:+.5f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
