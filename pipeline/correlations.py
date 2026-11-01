"""T6 — Correlation engine: how same-game legs actually co-move, and what that does to parlay pricing.

Everything is measured from official final scores in data/games_1999_2026_nflverse.csv.
No correlation value on the site is assumed; each has a sample size and a CI.

Definitions used throughout
---------------------------
* home_cover        : home margin - closing home spread > 0  (spread_line > 0 = home favoured)
* over              : (home + away points) - closing total > 0
* home_ml           : home team wins outright
* favorite          : the side with the shorter price (spread_line > 0 => home is the favourite)
* team_total_over   : a team beats half the closing game total (proxy used ONLY where the
                      official team-total line is not in verified data - flagged, see F-07)
"""
from __future__ import annotations

import json
import math
import os
from collections import defaultdict

from lib_core import (REPORTS, mean, norm_cdf, norm_ppf, pearson, phi, stdev, load_games)
from features import DESIGN, HOLDOUT, VALIDATION, build

VIG_PRICE = -110.0


def payout(odds=-110.0):
    return odds / 100.0 if odds > 0 else 100.0 / abs(odds)


def ci_corr(r, n):
    """95% CI for a correlation via Fisher z."""
    if r is None or n < 4:
        return [None, None]
    if abs(r) >= 0.999:
        r = 0.999 if r > 0 else -0.999
    z = 0.5 * math.log((1 + r) / (1 - r))
    se = 1.0 / math.sqrt(n - 3)
    return [round(math.tanh(z - 1.96 * se), 4), round(math.tanh(z + 1.96 * se), 4)]


def bin_rows(games):
    rows = []
    for g in games:
        if not g["played"] or g["spread_line"] is None or g["total_line"] is None:
            continue
        d = g["margin"] - g["spread_line"]
        t = g["tot"] - g["total_line"]
        rows.append({
            "game_id": g["game_id"], "season": g["season"], "week": g["week"],
            "home_cover": d > 0, "away_cover": d < 0, "push_spread": d == 0,
            "over": t > 0, "under": t < 0, "push_total": t == 0,
            "home_ml": g["margin"] > 0, "away_ml": g["margin"] < 0,
            "home_fav": g["spread_line"] > 0,
            "home_pts": g["home_score"], "away_pts": g["away_score"],
            "margin": g["margin"], "tot": g["tot"],
            "home_beat_half": g["home_score"] * 2 > g["tot"],
            "wind": g["wind"], "temp": g["temp"],
        })
    return rows


def pair_table(rows):
    """Measured joint probabilities and correlations for the leg pairs that matter in SGPs."""
    defs = [
        ("home_cover", "over", "Home team covers  +  game goes OVER"),
        ("home_cover", "under", "Home team covers  +  game goes UNDER"),
        ("away_cover", "over", "Away team covers  +  game goes OVER"),
        ("home_ml", "over", "Home team wins outright  +  game goes OVER"),
        ("home_ml", "home_cover", "Home wins outright  +  home covers"),
        ("home_fav_cover", "over", "Favourite covers  +  game goes OVER"),
        ("home_beat_half", "over", "Home team top-scorer (beats half the total)  +  OVER"),
    ]
    out = []
    for a, b, label in defs:
        def val(r, k):
            if k == "home_fav_cover":
                return r["home_cover"] if r["home_fav"] else r["away_cover"]
            return r[k]
        usable = [r for r in rows if not (r["push_spread"] or r["push_total"])]
        A = [val(r, a) for r in usable]
        B = [val(r, b) for r in usable]
        n = len(usable)
        pa = sum(A) / n
        pb = sum(B) / n
        pj = sum(1 for i in range(n) if A[i] and B[i]) / n
        r = phi(A, B)
        out.append({
            "leg_a": a, "leg_b": b, "label": label, "n": n,
            "p_a": round(pa, 4), "p_b": round(pb, 4),
            "p_independent": round(pa * pb, 6),
            "p_joint_measured": round(pj, 6),
            "difference_pct": round((pj - pa * pb) * 100, 3),
            "phi": round(r, 4) if r is not None else None,
            "phi_ci95": ci_corr(r, n),
            "legs_correlated": bool(r is not None and abs(r) > 2 / math.sqrt(n)),
        })
    return out


def cross_game_baseline(rows, trials=4000, seed=7):
    """Same-market pairs from DIFFERENT games in the same week: the 'independent' control."""
    import random
    rng = random.Random(seed)
    by_week = defaultdict(list)
    for r in rows:
        by_week[(r["season"], r["week"])].append(r)
    phis = []
    for _ in range(trials):
        ws = [w for w in by_week.values() if len(w) >= 4]
        w = rng.choice(ws)
        a, b = rng.sample(w, 2)
        if a["push_spread"] or b["push_spread"]:
            continue
        phis.append(1.0 if a["home_cover"] == b["home_cover"] else 0.0)
    if not phis:
        return None
    return {"n_pairs": len(phis), "mean_agreement": round(mean(phis), 4),
            "note": "Agreement of the home-cover outcome for two unrelated games in the same week. 0.50 => independent."}


def parlay_math(pairs, n_legs=2):
    """Given measured pair dependencies, price a 2-leg SGP under independent vs measured probabilities."""
    out = []
    for p in pairs:
        fair_ind = p["p_independent"]
        fair_meas = p["p_joint_measured"]
        odds_ind = (1 / fair_ind) if fair_ind else None
        odds_meas = (1 / fair_meas) if fair_meas else None
        # A book that multiplies -110 legs (payout 0.9091 each) pays this decimal price:
        book_pay = (1 + payout()) ** n_legs
        ev_per_unit = fair_meas * book_pay - 1  # stake 1 unit, win book_pay-1... (see note below)
        ev_per_unit = fair_meas * (book_pay - 1) - (1 - fair_meas)
        out.append({
            "label": p["label"],
            "p_independent": round(fair_ind, 6),
            "p_measured": round(fair_meas, 6),
            "fair_decimal_odds_independent": round(odds_ind, 3) if odds_ind else None,
            "fair_decimal_odds_measured": round(odds_meas, 3) if odds_meas else None,
            "book_decimal_odds_if_-110_both_legs": round(book_pay, 4),
            "ev_per_1u_vs_book_price": round(ev_per_unit, 4),
        })
    return out


def main():
    games = load_games()
    rows = bin_rows(games)
    pairs = pair_table(rows)

    # continuous structure that drives prop-vs-prop correlation
    home_pts = [r["home_pts"] for r in rows]
    away_pts = [r["away_pts"] for r in rows]
    cont = {
        "corr_home_pts_away_pts": round(pearson(home_pts, away_pts), 4),
        "corr_home_pts_away_pts_ci95": ci_corr(pearson(home_pts, away_pts), len(rows)),
        "corr_margin_total": round(pearson([r["margin"] for r in rows], [r["tot"] for r in rows]), 4),
        "corr_margin_total_ci95": ci_corr(pearson([r["margin"] for r in rows], [r["tot"] for r in rows]), len(rows)),
        "mean_home_pts": round(mean(home_pts), 3), "sd_home_pts": round(stdev(home_pts), 3),
        "mean_away_pts": round(mean(away_pts), 3), "sd_away_pts": round(stdev(away_pts), 3),
        "mean_total": round(mean([r["tot"] for r in rows]), 3),
        "sd_total": round(stdev([r["tot"] for r in rows]), 3),
        "mean_margin": round(mean([r["margin"] for r in rows]), 3),
        "sd_margin": round(stdev([r["margin"] for r in rows]), 3),
        "share_games_both_teams_20plus": round(mean([1.0 if r["home_pts"] >= 20 and r["away_pts"] >= 20 else 0.0
                                                     for r in rows]), 4),
        "home_win_rate": round(mean([1.0 if r["home_ml"] else (0.5 if r["margin"] == 0 else 0.0) for r in rows]), 4),
    }

    # stability of the headline correlations across eras (guards against a single-era artefact)
    era = []
    for lo, hi, name in [(1999, 2008, "1999-2008"), (2009, 2017, "2009-2017"), (2018, 2026, "2018-2026")]:
        sub = [r for r in rows if lo <= r["season"] <= hi]
        if not sub:
            continue
        p = pair_table(sub)
        d = {x["leg_a"] + "&" + x["leg_b"]: x["phi"] for x in p}
        era.append({"era": name, "n": len(sub),
                    "phi_home_cover_over": d.get("home_cover&over"),
                    "phi_home_ml_over": d.get("home_ml&over"),
                    "phi_fav_cover_over": d.get("home_fav_cover&over"),
                    "corr_home_away_pts": round(pearson([r["home_pts"] for r in sub],
                                                        [r["away_pts"] for r in sub]), 4)})

    # sample-size requirement for measuring a prop-pair correlation to +/-0.10 (Fisher z, 95%)
    n_req = {}
    for r_true in (0.2, 0.3, 0.4, 0.5, 0.6):
        z = 0.5 * math.log((1 + r_true) / (1 - r_true))
        # want se_z = 1/sqrt(n-3) <= 0.10/1.96 in r-space ~ use delta method approx se_r = 0.099
        se_r = 0.10 / 1.96
        n = 3 + (1 / (se_r * (1 - r_true ** 2))) ** 2
        n_req[f"true_r_{r_true}"] = int(round(n))

    out = {
        "generated_utc": "2026-11-01",
        "sample": {"games": len(rows), "seasons": [min(r["season"] for r in rows), max(r["season"] for r in rows)],
                   "source": "official final scores in data/games_1999_2026_nflverse.csv"},
        "pair_correlations": pairs,
        "cross_game_control": cross_game_baseline(rows),
        "parlay_pricing": parlay_math(pairs),
        "continuous_structure": cont,
        "era_stability": era,
        "prop_sample_size_requirements": n_req,
        "notes": [
            "Pushes are excluded from all pair correlations and from the market base rates.",
            "phi is reported on binary legs; the 95% CI is a Fisher transform approximation.",
            "EV figures assume a book that prices both legs at -110 and multiplies them independently - the standard same-game-parlay construction.",
        ],
    }
    os.makedirs(REPORTS, exist_ok=True)
    with open(os.path.join(REPORTS, "correlations.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    print("pair correlations (n=%d):" % len(rows))
    for p in pairs:
        print(f"  {p['label'][:52]:<52} p_a={p['p_a']} p_b={p['p_b']} joint={p['p_joint_measured']} "
              f"indep={p['p_independent']} phi={p['phi']} ci={p['phi_ci95']}")
    print("cross-game control:", out["cross_game_control"])
    for r in out["parlay_pricing"]:
        print("  EV (book -110 x2):", r["label"][:46], r["ev_per_1u_vs_book_price"])
    print("continuous:", cont)
    print("era:", era)


if __name__ == "__main__":
    main()
