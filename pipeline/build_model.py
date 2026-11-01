"""T4 — Own-line origination: build our own spread/total, then measure it against the market.

Outputs reports/model.json (numbers used by the site's "Own Lines" page).

The comparison uses only closing lines that exist in the dataset; nothing is imputed.
"""
from __future__ import annotations

import csv
import json
import os
from collections import defaultdict

from lib_core import (DATA, REPORTS, american_to_prob, load_games, mean, norm_cdf, pearson,
                      stdev)
from features import DESIGN, HOLDOUT, VALIDATION, apply_model, build, fit_model


def mae(pairs):
    return mean([abs(a - b) for a, b in pairs])


def rmse(pairs):
    return (mean([(a - b) ** 2 for a, b in pairs]) or 0) ** 0.5


def window_of(s):
    if DESIGN[0] <= s <= DESIGN[1]:
        return "design"
    if VALIDATION[0] <= s <= VALIDATION[1]:
        return "validation"
    if HOLDOUT[0] <= s <= HOLDOUT[1]:
        return "holdout"
    return "other"


def main():
    games = load_games()
    feats = build(games)
    model = fit_model(feats)
    apply_model(feats, model)

    # residual sd of the model on the design window feeds the win-probability conversion
    tr = [f for f in feats if DESIGN[0] <= f["season"] <= DESIGN[1]]
    resid = [f["margin"] - f["model_margin"] for f in tr]
    sd_margin = stdev(resid)

    out = {"generated_utc": "2026-11-01", "coefficients": model,
           "design_residual_sd_margin": round(sd_margin, 3)}

    # ---- accuracy by window: our line vs the market line, both against the actual result
    rows = []
    for w in ("design", "validation", "holdout"):
        sub = [f for f in feats if window_of(f["season"]) == w and f["spread_line"] is not None]
        if not sub:
            continue
        rows.append({
            "window": w, "n": len(sub),
            "model_mae": round(mae([(f["model_margin"], f["margin"]) for f in sub]), 3),
            "market_mae": round(mae([(f["spread_line"], f["margin"]) for f in sub]), 3),
            "model_rmse": round(rmse([(f["model_margin"], f["margin"]) for f in sub]), 3),
            "market_rmse": round(rmse([(f["spread_line"], f["margin"]) for f in sub]), 3),
            "model_corr": round(pearson([f["model_margin"] for f in sub], [f["margin"] for f in sub]), 4),
            "market_corr": round(pearson([f["spread_line"] for f in sub], [f["margin"] for f in sub]), 4),
            "model_bias": round(mean([f["model_margin"] - f["margin"] for f in sub]), 3),
            "market_bias": round(mean([f["spread_line"] - f["margin"] for f in sub]), 3),
        })
    out["spread_accuracy"] = rows

    tot_rows = []
    for w in ("design", "validation", "holdout"):
        sub = [f for f in feats if window_of(f["season"]) == w and f["total_line"] is not None]
        if not sub:
            continue
        tot_rows.append({
            "window": w, "n": len(sub),
            "model_mae": round(mae([(f["model_total"], f["tot"]) for f in sub]), 3),
            "market_mae": round(mae([(f["total_line"], f["tot"]) for f in sub]), 3),
            "model_corr": round(pearson([f["model_total"] for f in sub], [f["tot"] for f in sub]), 4),
            "market_corr": round(pearson([f["total_line"] for f in sub], [f["tot"] for f in sub]), 4),
            "model_bias": round(mean([f["model_total"] - f["tot"] for f in sub]), 3),
        })
    out["total_accuracy"] = tot_rows

    # ---- calibration of the model's moneyline probabilities (holdout-safe: report all windows)
    cal = []
    band = [(0.0, 0.2), (0.2, 0.35), (0.35, 0.5), (0.5, 0.65), (0.65, 0.8), (0.8, 1.01)]
    for lo, hi in band:
        sub = [f for f in feats if lo <= norm_cdf(f["model_margin"] / sd_margin) < hi]
        if not sub:
            continue
        pred = mean([norm_cdf(f["model_margin"] / sd_margin) for f in sub])
        actual = mean([1.0 if f["margin"] > 0 else (0.5 if f["margin"] == 0 else 0.0) for f in sub])
        cal.append({"bin": f"{lo:.2f}-{hi:.2f}", "n": len(sub),
                    "predicted_home_win_rate": round(pred, 4),
                    "actual_home_win_rate": round(actual, 4),
                    "calibration_gap": round(actual - pred, 4)})
    out["win_probability_calibration"] = cal
    brier = mean([(norm_cdf(f["model_margin"] / sd_margin) - (1.0 if f["margin"] > 0 else 0.0)) ** 2
                  for f in feats])
    out["brier_score_model_all_games"] = round(brier, 4)

    # ---- threshold search for own-line betting, chosen on DESIGN only, then applied forward
    search = []
    for thr in (1.0, 2.0, 2.5, 3.0, 3.5, 4.0, 5.0, 6.0):
        out_rows = []
        for w in ("design", "validation", "holdout"):
            sub = [f for f in feats if window_of(f["season"]) == w and f["spread_line"] is not None
                   and abs(f["model_margin"] - f["spread_line"]) >= thr]
            if not sub:
                continue
            profits = []
            for f in sub:
                d = (f["margin"] - f["spread_line"]) * (1 if f["model_margin"] > f["spread_line"] else -1)
                profits.append(0.0 if d == 0 else (0.909 if d > 0 else -1.0))
            out_rows.append({"window": w, "bets": len(sub), "roi": round(mean(profits), 4),
                             "t_stat": round(mean(profits) / (stdev(profits) / len(profits) ** 0.5), 3)
                             if len(profits) > 2 and stdev(profits) else None})
        by = {r["window"]: r for r in out_rows}
        search.append({"threshold_points": thr, **{f"{k}_roi": v["roi"] for k, v in by.items()},
                       **{f"{k}_bets": v["bets"] for k, v in by.items()}})
    out["threshold_search_spread"] = search

    # ---- opening vs closing line study (2021 only: the single season with opening lines in the dataset)
    path = os.path.join(DATA, "initial_lines.csv")
    opens = {}
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["type"] == "SPREAD":
                try:
                    opens[(r["about"], r["side"])] = float(r["line"])
                except ValueError:
                    pass
    movers = []
    for f in feats:
        if f["game_id"] in ("",):
            continue
        oh = opens.get((f["game_id"], f["home_team"]))
        if oh is None or f["spread_line"] is None:
            continue
        movers.append({"game_id": f["game_id"], "season": f["season"],
                       "open_home": oh, "close_home": f["spread_line"],
                       "move": round(f["spread_line"] - oh, 2),
                       "model_home": round(f["model_margin"], 2),
                       "model_minus_open": round(f["model_margin"] - oh, 2),
                       "result_home_margin": f["margin"]})
    out["opening_vs_closing"] = {
        "season": 2021,
        "n_games_with_both": len(movers),
        "mean_abs_move_points": round(mean([abs(m["move"]) for m in movers]), 3) if movers else None,
        "share_moved_toward_model": round(mean([1.0 if (m["move"] > 0) == (m["model_minus_open"] > 0) else 0.0
                                               for m in movers]), 4) if movers else None,
        "model_mae_vs_open": round(mae([(m["model_home"], m["result_home_margin"]) for m in movers]), 3) if movers else None,
        "model_mae_vs_close": round(mae([(m["close_home"], m["result_home_margin"]) for m in movers]), 3) if movers else None,
        "source": "data/initial_lines.csv (book: WSGT) vs closing spread in data/games_1999_2026_nflverse.csv",
    }

    # ---- per-season model vs market (used by the site chart table)
    per_season = []
    for s in sorted({f["season"] for f in feats}):
        sub = [f for f in feats if f["season"] == s and f["spread_line"] is not None]
        if not sub:
            continue
        per_season.append({"season": s, "n": len(sub),
                           "model_mae": round(mae([(f["model_margin"], f["margin"]) for f in sub]), 2),
                           "market_mae": round(mae([(f["spread_line"], f["margin"]) for f in sub]), 2),
                           "total_model_mae": round(mae([(f["model_total"], f["tot"]) for f in sub
                                                         if f["total_line"] is not None]), 2)
                           if any(f["total_line"] is not None for f in sub) else None})
    out["per_season"] = per_season

    os.makedirs(REPORTS, exist_ok=True)
    with open(os.path.join(REPORTS, "model.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)

    print(json.dumps({k: out[k] for k in ("spread_accuracy", "total_accuracy",
                                          "brier_score_model_all_games", "opening_vs_closing")}, indent=1)[:2200])
    print("threshold search:")
    for r in search:
        print(r)


if __name__ == "__main__":
    main()
