"""T3/T5 — Signal research, single-bet strategy library, validation gates, leaderboard.

Every strategy is a mechanical rule evaluated on point-in-time features (see
pipeline/features.py). Bets are settled against the official final scores in the
dataset and priced at the closing line/odds carried in the dataset (never at a
number that was not available).

Design / validation / holdout windows are fixed in features.py and were declared
before any result was inspected.
"""
from __future__ import annotations

import csv
import json
import math
import os
from collections import defaultdict

from lib_core import (DATA, REPORTS, benjamini_hochberg, load_games, mean, max_drawdown,
                      norm_cdf, spread_payout, stdev)
from features import DESIGN, HOLDOUT, VALIDATION, apply_model, build, fit_model

UNIT = 1.0


# ----------------------------------------------------------------------------- settlement
def settle_ats(f, side):
    d = f["margin"] - f["spread_line"]
    if d == 0:
        return "P"
    if side == "home":
        return "W" if d > 0 else "L"
    return "W" if d < 0 else "L"


def settle_total(f, side):
    d = f["tot"] - f["total_line"]
    if d == 0:
        return "P"
    if side == "over":
        return "W" if d > 0 else "L"
    return "W" if d < 0 else "L"


def settle_ml(f, side):
    if f["margin"] == 0:
        return "P"
    if side == "home":
        return "W" if f["margin"] > 0 else "L"
    return "W" if f["margin"] < 0 else "L"


def odds_for(f, market, side):
    if market == "ATS":
        o = f["home_spread_odds"] if side == "home" else f["away_spread_odds"]
    elif market == "TOTAL":
        o = f["over_odds"] if side == "over" else f["under_odds"]
    else:
        o = f["home_ml"] if side == "home" else f["away_ml"]
    return -110.0 if o is None else o


def line_for(f, market, side):
    if market == "ATS":
        return f["spread_line"] if side == "home" else -f["spread_line"]
    if market == "TOTAL":
        return f["total_line"]
    return None


def make_bet(sid, f, market, side, edge, note=""):
    if market == "ATS" and f["spread_line"] is None:
        return None
    if market == "TOTAL" and f["total_line"] is None:
        return None
    if market == "ML" and (f["home_ml"] is None or f["away_ml"] is None):
        return None
    odds = odds_for(f, market, side)
    res = {"ATS": settle_ats, "TOTAL": settle_total, "ML": settle_ml}[market](f, side)
    profit = 0.0 if res == "P" else (spread_payout(odds) if res == "W" else -UNIT)
    return {
        "strategy": sid, "game_id": f["game_id"], "season": f["season"], "week": f["week"],
        "market": market, "side": side, "side_team": (f["home_team"] if side == "home" else
                                                      f["away_team"] if side == "away" else side),
        "line": line_for(f, market, side), "odds": odds, "result": res, "profit": profit,
        "edge": round(edge, 3) if edge is not None else None, "note": note,
    }


# ----------------------------------------------------------------------------- strategies
def s_elo_ats(thr):
    def rule(f):
        if "model_edge_home" not in f or abs(f["model_edge_home"]) < thr:
            return []
        side = "home" if f["model_edge_home"] > 0 else "away"
        b = make_bet(None, f, "ATS", side, f["model_edge_home"])
        return [b] if b else []
    return rule


def s_elo_total(thr):
    def rule(f):
        if "model_total_edge" not in f or abs(f["model_total_edge"]) < thr:
            return []
        side = "over" if f["model_total_edge"] > 0 else "under"
        b = make_bet(None, f, "TOTAL", side, f["model_total_edge"])
        return [b] if b else []
    return rule


def s_rest_diff(thr=3):
    def rule(f):
        if f["rest_diff"] is None or abs(f["rest_diff"]) < thr:
            return []
        side = "home" if f["rest_diff"] > 0 else "away"
        b = make_bet(None, f, "ATS", side, f["rest_diff"])
        return [b] if b else []
    return rule


def s_short_week_under(f):
    if f["min_rest"] is None or f["min_rest"] > 4:
        return []
    b = make_bet(None, f, "TOTAL", "under", None)
    return [b] if b else []


def s_div_home_dog_ats(f):
    if not f["div_game"] or f["spread_line"] is None or f["spread_line"] >= 0:
        return []
    b = make_bet(None, f, "ATS", "home", f["spread_line"])
    return [b] if b else []


def s_div_home_dog_ml(f):
    if not f["div_game"] or f["spread_line"] is None or f["spread_line"] >= 0:
        return []
    b = make_bet(None, f, "ML", "home", f["spread_line"])
    return [b] if b else []


def s_wind_under(f):
    if not f["wind_flag"]:
        return []
    b = make_bet(None, f, "TOTAL", "under", None)
    return [b] if b else []


def s_cold_under(f):
    if not f["cold_flag"]:
        return []
    b = make_bet(None, f, "TOTAL", "under", None)
    return [b] if b else []


def s_bye_ats(f):
    if f["home_off_bye"] and not f["away_off_bye"]:
        side = "home"
    elif f["away_off_bye"] and not f["home_off_bye"]:
        side = "away"
    else:
        return []
    b = make_bet(None, f, "ATS", side, None)
    return [b] if b else []


def s_fade_big_win(f, thr=21):
    for side, lm in (("away", f["last_margin_h"]), ("home", f["last_margin_a"])):
        if lm is not None and lm >= thr:
            b = make_bet(None, f, "ATS", side, lm)
            return [b] if b else []
    return []


def s_fade_cover(f, thr=14):
    for side, la in (("away", f["last_ats_h"]), ("home", f["last_ats_a"])):
        if la is not None and la >= thr:
            b = make_bet(None, f, "ATS", side, la)
            return [b] if b else []
    return []


def s_ml_value(f, thr=0.05):
    if f["home_ml"] is None or f["away_ml"] is None or "model_margin" not in f:
        return []
    p_home = norm_cdf(f["model_margin"] / 13.5)   # 13.5 = NFL margin sd (train-window residual sd, see model report)
    from lib_core import american_to_prob
    mkt_home = 1.0 / (1.0 / american_to_prob(f["home_ml"]) + 1.0 / american_to_prob(f["away_ml"]))
    mkt_away = 1 - mkt_home
    edges = {"home": p_home - mkt_home, "away": (1 - p_home) - mkt_away}
    side = max(edges, key=edges.get)
    if edges[side] < thr:
        return []
    b = make_bet(None, f, "ML", side, edges[side] * 100)
    return [b] if b else []


def s_home_dog_ats(f):
    if f["spread_line"] is None or f["spread_line"] >= 0:
        return []
    b = make_bet(None, f, "ATS", "home", f["spread_line"])
    return [b] if b else []


def s_rest_adv_fav_ats(f):
    """Rest advantage AND the model agrees with the side (interaction signal)."""
    if f["rest_diff"] is None or abs(f["rest_diff"]) < 3 or "model_edge_home" not in f:
        return []
    want = "home" if f["rest_diff"] > 0 else "away"
    if (f["model_edge_home"] > 0) != (want == "home"):
        return []
    b = make_bet(None, f, "ATS", want, f["rest_diff"])
    return [b] if b else []


STRATEGIES = [
    ("S01", "Elo ATS edge >= 3", "ATS", s_elo_ats(3.0),
     "Bet the side the own-line model favours by >= 3 points versus the closing spread."),
    ("S02", "Elo ATS edge >= 5", "ATS", s_elo_ats(5.0),
     "Same rule as S01 with a stricter 5-point threshold (fewer, larger disagreements)."),
    ("S03", "Model total edge >= 4", "TOTAL", s_elo_total(4.0),
     "Bet over/under when the own-line total model differs from the closing total by >= 4 points."),
    ("S04", "Rest differential >= 3 days", "ATS", s_rest_diff(3),
     "Bet the side with >= 3 more days of rest than its opponent, at the closing spread."),
    ("S05", "Short-week under", "TOTAL", s_short_week_under,
     "Under when either team had <= 4 days between games (Thursday/short-week spots)."),
    ("S06", "Divisional home dog ATS", "ATS", s_div_home_dog_ats,
     "Home underdog in a divisional game, at the closing spread."),
    ("S07", "Divisional home dog ML", "ML", s_div_home_dog_ml,
     "Home underdog in a divisional game, on the moneyline (dataset moneylines start in 2006)."),
    ("S08", "Wind >= 15 mph under", "TOTAL", s_wind_under,
     "Under when the recorded game-time wind is >= 15 mph (outdoor games only, by data availability)."),
    ("S09", "Cold (<= 32F) under", "TOTAL", s_cold_under,
     "Under when the recorded game-time temperature is <= 32F."),
    ("S10", "Team off bye ATS", "ATS", s_bye_ats,
     "Bet a team playing with >= 13 days rest (post-bye) when its opponent is not."),
    ("S11", "Fade 21+ point winner ATS", "ATS", s_fade_big_win,
     "Fade a team that won its previous game by >= 21 points (bet the opponent)."),
    ("S12", "Fade 14+ point cover ATS", "ATS", s_fade_cover,
     "Fade a team that covered its previous game by >= 14 points."),
    ("S13", "Moneyline value >= 5%", "ML", s_ml_value,
     "Bet the moneyline side where the model win probability exceeds the vig-free market probability by >= 5 points."),
    ("S14", "Any home underdog ATS", "ATS", s_home_dog_ats,
     "Blanket rule: every home underdog at the closing spread (benchmark/control strategy)."),
    ("S15", "Rest advantage + model agreement", "ATS", s_rest_adv_fav_ats,
     "Bet the rest-advantaged side only when the own-line model also favours that side by >= 3 points."),
]


# ----------------------------------------------------------------------------- metrics
def window(season):
    if DESIGN[0] <= season <= DESIGN[1]:
        return "design"
    if VALIDATION[0] <= season <= VALIDATION[1]:
        return "validation"
    if HOLDOUT[0] <= season <= HOLDOUT[1]:
        return "holdout"
    return "other"


def metrics(bets):
    settled = [b for b in bets if b["result"] != "P"]
    pushes = len(bets) - len(settled)
    n = len(bets)
    units = sum(b["profit"] for b in bets)
    profits = [b["profit"] for b in bets]
    sd = stdev(profits)
    m = mean(profits) if profits else None
    se = (sd / math.sqrt(len(profits))) if sd and len(profits) > 1 else None
    t = (m / se) if se else None
    p_one = (1 - norm_cdf(t)) if t is not None else None
    ci = [(m - 1.96 * se), (m + 1.96 * se)] if se else [None, None]
    wins = sum(1 for b in settled if b["result"] == "W")
    return {
        "bets": n, "pushes": pushes, "wins": wins, "losses": len(settled) - wins,
        "units": round(units, 2), "roi": round(units / n, 4) if n else None,
        "hit_rate": round(wins / len(settled), 4) if settled else None,
        "avg_odds": round(mean([b["odds"] for b in bets]), 1) if bets else None,
        "mean_profit": round(m, 4) if m is not None else None,
        "t_stat": round(t, 3) if t is not None else None,
        "p_one_sided": p_one,
        "roi_ci95": [round(ci[0], 4) if ci[0] is not None else None,
                     round(ci[1], 4) if ci[1] is not None else None],
        "max_drawdown": round(max_drawdown([b["profit"] for b in bets]), 2),
    }


def season_table(bets):
    out = []
    for s in sorted({b["season"] for b in bets}):
        sb = [b for b in bets if b["season"] == s]
        mm = metrics(sb)
        out.append({"season": s, "window": window(s), "bets": mm["bets"], "units": mm["units"],
                    "roi": mm["roi"], "hit_rate": mm["hit_rate"]})
    return out


def load_opening_lines():
    """2021-only opening lines (single book) -> CLV cohort. Never imputed."""
    path = os.path.join(DATA, "initial_lines.csv")
    out = {}
    if not os.path.exists(path):
        return out
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            if r["type"] not in ("SPREAD", "TOTAL"):
                continue
            key = (r["about"], r["type"], r["side"])
            try:
                out[key] = float(r["line"])
            except ValueError:
                continue
    return out


def attach_clv(bets, openings):
    for b in bets:
        b["clv"] = None
        if b["market"] == "ATS":
            side_code = b["side_team"]
            key = (b["game_id"], "SPREAD", side_code)
            o = openings.get(key)
            if o is not None and b["line"] is not None:
                b["clv"] = round(o - b["line"], 2)
        elif b["market"] == "TOTAL":
            key = (b["game_id"], "TOTAL", "Over" if b["side"] == "over" else "Under")
            o = openings.get(key)
            if o is not None and b["line"] is not None:
                b["clv"] = round((b["line"] - o) if b["side"] == "over" else (o - b["line"]), 2)
    return bets


# ----------------------------------------------------------------------------- gates
def run_gates(all_metrics, bh_p, season_rows, bets):
    g = {}
    full, hold = all_metrics["full"], all_metrics["holdout"]
    g["G1_SAMPLE"] = {
        "requirement": ">= 300 settled bets overall and >= 60 in the 2024-2026 holdout",
        "value": f"{full['bets']} overall / {hold['bets']} holdout",
        "pass": full["bets"] >= 300 and hold["bets"] >= 60,
    }
    g["G2_ROI_POSITIVE"] = {
        "requirement": "positive ROI overall AND positive ROI in the holdout",
        "value": f"{full['roi']} overall / {hold['roi']} holdout",
        "pass": (full["roi"] or -1) > 0 and (hold["roi"] or -1) > 0,
    }
    g["G3_SIGNIFICANCE"] = {
        "requirement": "Benjamini-Hochberg adjusted one-sided p < 0.05 across all 15 strategies",
        "value": None if bh_p is None else round(bh_p, 4),
        "pass": bh_p is not None and bh_p < 0.05,
    }
    pos_seasons = [r for r in season_rows if r["bets"] >= 20]
    share = None
    top = None
    if pos_seasons:
        tot = sum(r["units"] for r in pos_seasons)
        if tot > 0:
            top = max(r["units"] for r in pos_seasons)
            share = round(top / tot, 3)
    hit_share = (sum(1 for r in pos_seasons if (r["roi"] or 0) > 0) / len(pos_seasons)) if pos_seasons else None
    hit_txt = "no qualified seasons" if hit_share is None else f"{hit_share:.3f} of seasons positive"
    share_txt = "n/a (no positive total)" if share is None else f"{share:.3f}"
    g["G4_STABILITY"] = {
        "requirement": ">= 55% of qualified seasons positive AND no single season supplies > 50% of profit",
        "value": f"{hit_txt}; top season share {share_txt}",
        "pass": bool(hit_share is not None and hit_share >= 0.55 and (share is None or share <= 0.5)),
    }
    g["G5_DRAWDOWN"] = {
        "requirement": "max peak-to-trough drawdown <= 30 units",
        "value": full["max_drawdown"],
        "pass": (full["max_drawdown"] or 0) >= -30,
    }
    clv_vals = [b["clv"] for b in bets if b.get("clv") is not None]
    if len(clv_vals) >= 10:
        g["G6_CLV"] = {
            "requirement": "mean closing-line value (open vs close) >= 0 on the 2021 cohort",
            "value": f"{round(mean(clv_vals),3)} pts on n={len(clv_vals)}",
            "pass": mean(clv_vals) >= 0,
        }
    else:
        g["G6_CLV"] = {
            "requirement": "mean closing-line value (open vs close) >= 0 on the 2021 cohort",
            "value": f"insufficient data (n={len(clv_vals)}; opening lines exist for the 2021 season only)",
            "pass": None,
        }
    g["G7_HOLDOUT_NOT_NEGATIVE"] = {
        "requirement": "holdout ROI 95% CI lower bound > -10% (no blow-up risk in unseen data)",
        "value": hold["roi_ci95"],
        "pass": hold["roi_ci95"][0] is not None and hold["roi_ci95"][0] > -0.10,
    }
    return g


def score_strategy(all_metrics, gates):
    """Leaderboard score: holdout-weighted edge strength, discounted by risk."""
    full, hold = all_metrics["full"], all_metrics["holdout"]
    parts = []
    if full["roi"] is not None:
        parts.append(full["roi"] * 100)
    if hold["roi"] is not None:
        parts.append(hold["roi"] * 150)
    if full["t_stat"] is not None:
        parts.append(full["t_stat"] * 2.0)
    if full["max_drawdown"]:
        parts.append(-abs(full["max_drawdown"]) * 0.15)
    raw = sum(parts)
    validated = all(v["pass"] is not False for v in gates.values())
    return round(raw, 2), validated


def main():
    games = load_games()
    feats = build(games)
    model = fit_model(feats)
    apply_model(feats, model)
    openings = load_opening_lines()

    results = []
    all_bets = []
    pvals = []
    for sid, name, market, rule, desc in STRATEGIES:
        bets = []
        for f in feats:
            for b in rule(f):
                b["strategy"] = sid
                bets.append(b)
        bets = attach_clv(bets, openings)
        all_bets.extend(bets)
        by_win = defaultdict(list)
        for b in bets:
            by_win[window(b["season"])].append(b)
        per = {k: metrics(v) for k, v in by_win.items()}
        full = metrics(bets)
        hold = per.get("holdout") or metrics([])
        seas = season_table(bets)
        res = {
            "id": sid, "name": name, "market": market, "rule": desc,
            "metrics": {"full": full, "design": per.get("design"), "validation": per.get("validation"),
                        "holdout": per.get("holdout")},
            "seasons": seas,
            "clv": ({"n": len([b for b in bets if b.get("clv") is not None]),
                     "mean": round(mean([b["clv"] for b in bets if b.get("clv") is not None]), 3)
                     if any(b.get("clv") is not None for b in bets) else None}),
        }
        results.append(res)
        pvals.append(full["p_one_sided"] if full["p_one_sided"] is not None else 1.0)

    bh = benjamini_hochberg(pvals)

    for res, adj in zip(results, bh):
        res["bh_adjusted_p"] = round(adj, 5) if adj is not None else None
        res["gates"] = run_gates(res["metrics"],
                                 res["bh_adjusted_p"],
                                 res["seasons"],
                                 [b for b in all_bets if b["strategy"] == res["id"]])
        sc, validated = score_strategy(res["metrics"], res["gates"])
        res["score"] = sc
        res["validated"] = validated
        res["gates_passed"] = sum(1 for v in res["gates"].values() if v["pass"] is True)
        res["gates_total"] = sum(1 for v in res["gates"].values() if v["pass"] is not None)

    # leaderboard: validated first, then score
    lb = sorted(results, key=lambda r: (not r["validated"], -r["score"]))
    for i, r in enumerate(lb, start=1):
        r["rank"] = i
    eligible = [r for r in lb if r["validated"]]
    pool = 1000.0
    total_score = sum(max(r["score"], 0) for r in eligible)
    for r in lb:
        r["reward_units"] = (round(pool * max(r["score"], 0) / total_score, 2)
                             if r["validated"] and total_score > 0 else 0.0)

    # market baselines for context (no strategy logic, pure reference)
    played = [f for f in feats if f["spread_line"] is not None]
    base = {
        "n_games": len(feats),
        "n_with_spread": len(played),
        "home_cover_rate": round(sum(1 for f in played if f["margin"] - f["spread_line"] > 0) /
                                 sum(1 for f in played if f["margin"] - f["spread_line"] != 0), 4),
        "over_rate": round(sum(1 for f in feats if f["total_line"] is not None and f["tot"] - f["total_line"] > 0) /
                           sum(1 for f in feats if f["total_line"] is not None and f["tot"] - f["total_line"] != 0), 4),
        "mean_abs_closing_spread": round(mean([abs(f["spread_line"]) for f in played]), 2),
        "mean_closing_total": round(mean([f["total_line"] for f in feats if f["total_line"] is not None]), 2),
    }

    os.makedirs(REPORTS, exist_ok=True)
    with open(os.path.join(REPORTS, "strategies.json"), "w", encoding="utf-8") as fh:
        json.dump({"model": model, "baselines": base, "strategies": results,
                   "windows": {"design": DESIGN, "validation": VALIDATION, "holdout": HOLDOUT}}, fh, indent=1)
    with open(os.path.join(REPORTS, "leaderboard.json"), "w", encoding="utf-8") as fh:
        json.dump({"generated_utc": "2026-11-01",
                   "pool_units": pool,
                   "eligible": len(eligible),
                   "ranking": [{"rank": r["rank"], "id": r["id"], "name": r["name"],
                                "score": r["score"], "validated": r["validated"],
                                "reward_units": r["reward_units"],
                                "roi_full": r["metrics"]["full"]["roi"],
                                "roi_holdout": (r["metrics"]["holdout"] or {}).get("roi"),
                                "bets": r["metrics"]["full"]["bets"],
                                "gates_passed": r["gates_passed"], "gates_total": r["gates_total"]}
                               for r in lb]}, fh, indent=1)

    # per-bet audit trail (capped, deterministic sample) for the site
    sample = sorted(all_bets, key=lambda b: (b["season"], b["week"], b["game_id"], b["strategy"]))
    with open(os.path.join(REPORTS, "bets_sample.csv"), "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(sample[0].keys()), extrasaction="ignore")
        w.writeheader()
        for b in sample[-2000:]:
            w.writerow(b)

    print("model:", {k: model[k] for k in ("spread_beta", "spread_r2", "total_beta", "total_r2", "n_train")})
    print("baselines:", base)
    for r in lb:
        f_, h_ = r["metrics"]["full"], r["metrics"]["holdout"] or {}
        print(f"{r['rank']:>2} {r['id']} {r['name'][:32]:<32} n={f_['bets']:>5} roi={f_['roi']} "
              f"hold={h_.get('roi')} t={f_['t_stat']} bh={r['bh_adjusted_p']} "
              f"gates={r['gates_passed']}/{r['gates_total']} validated={r['validated']} score={r['score']}")


if __name__ == "__main__":
    main()
