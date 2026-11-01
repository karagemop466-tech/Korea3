"""T3b — Systematic signal scan.

Instead of hand-picking a few rules, every candidate signal family is scanned over a
grid of thresholds. All tests are reported (no winner's-curse filtering), then
Benjamini-Hochberg controls the false-discovery rate across the WHOLE battery.
Split-sample (design / validation / holdout) results are printed side by side so a
signal that only worked in the search window is visible as such.
"""
from __future__ import annotations

import json
import math
import os

from lib_core import REPORTS, benjamini_hochberg, load_games, mean, norm_cdf, spread_payout, stdev
from features import DESIGN, HOLDOUT, VALIDATION, apply_model, build, fit_model
from run_strategies import make_bet


def window(s):
    if DESIGN[0] <= s <= DESIGN[1]:
        return "design"
    if VALIDATION[0] <= s <= VALIDATION[1]:
        return "validation"
    return "holdout"


def evaluate(name, family, direction, rule, feats):
    bets = []
    for f in feats:
        for spec in rule(f):
            market, side = spec
            b = make_bet(None, f, market, side, spec[2] if len(spec) > 2 else None)
            if b:
                bets.append(b)
    if not bets:
        return None
    prof = [b["profit"] for b in bets]
    sd = stdev(prof)
    t = (mean(prof) / (sd / math.sqrt(len(prof)))) if sd else None
    p_one = (1 - norm_cdf(t)) if t is not None else None
    wins = sum(1 for b in bets if b["result"] == "W")
    loses = sum(1 for b in bets if b["result"] == "L")
    row = {
        "signal": name, "family": family, "direction": direction, "n": len(bets),
        "roi": round(mean(prof), 4), "hit_rate": round(wins / (wins + loses), 4) if wins + loses else None,
        "t_stat": round(t, 3) if t is not None else None, "p_one_sided": p_one,
        "windows": {},
    }
    for w in ("design", "validation", "holdout"):
        sub = [b["profit"] for b in bets if window(b["season"]) == w]
        row["windows"][w] = {
            "n": len(sub),
            "roi": round(mean(sub), 4) if sub else None,
            "t_stat": round(mean(sub) / (stdev(sub) / math.sqrt(len(sub))), 3)
            if len(sub) > 2 and stdev(sub) else None,
        }
    return row


def build_rule(fn):
    """Wrap a predicate into a rule returning [(market, side)]."""
    return lambda f: fn(f)


def main():
    games = load_games()
    feats = build(games)
    model = fit_model(feats)
    apply_model(feats, model)

    tests = []

    for thr in (1, 2, 2.5, 3, 3.5, 4, 5, 6, 7):
        tests.append(evaluate(
            f"Elo/own-line spread edge >= {thr}", "own line vs market", "spread",
            lambda f, thr=thr: ([("ATS", "home")] if f.get("model_edge_home", 0) >= thr
                                else [("ATS", "away")] if f.get("model_edge_home", 0) <= -thr else []), feats))
    for thr in (1, 2, 3, 4, 5, 6, 8):
        tests.append(evaluate(
            f"Own-line total edge >= {thr}", "own line vs market", "total",
            lambda f, thr=thr: ([("TOTAL", "over")] if f.get("model_total_edge", 0) >= thr
                                else [("TOTAL", "under")] if f.get("model_total_edge", 0) <= -thr else []), feats))
    for thr in (1, 2, 3, 4, 5, 6, 7):
        tests.append(evaluate(
            f"Rest differential >= {thr} days", "schedule/rest", "spread",
            lambda f, thr=thr: ([("ATS", "home")] if (f["rest_diff"] or 0) >= thr
                                else [("ATS", "away")] if (f["rest_diff"] or 0) <= -thr else []), feats))
    for thr in (3, 4, 5):
        tests.append(evaluate(
            f"Short-week under (min rest <= {thr})", "schedule/rest", "total",
            lambda f, thr=thr: [("TOTAL", "under")] if (f["min_rest"] is not None and f["min_rest"] <= thr) else [], feats))
    for thr in (10, 12, 15, 18, 20):
        tests.append(evaluate(
            f"Wind >= {thr} mph -> under", "weather", "total",
            lambda f, thr=thr: [("TOTAL", "under")] if (f["wind"] or 0) >= thr else [], feats))
        tests.append(evaluate(
            f"Wind >= {thr} mph -> over", "weather", "total",
            lambda f, thr=thr: [("TOTAL", "over")] if (f["wind"] or 0) >= thr else [], feats))
    for thr in (20, 28, 32, 40):
        tests.append(evaluate(
            f"Temperature <= {thr}F -> under", "weather", "total",
            lambda f, thr=thr: [("TOTAL", "under")] if (f["temp"] is not None and f["temp"] <= thr) else [], feats))
    tests.append(evaluate(
        "Divisional game -> home underdog ATS", "situational", "spread",
        lambda f: [("ATS", "home")] if (f["div_game"] and (f["spread_line"] or 0) < 0) else [], feats))
    tests.append(evaluate(
        "Divisional game -> home underdog moneyline", "situational", "moneyline",
        lambda f: [("ML", "home")] if (f["div_game"] and (f["spread_line"] or 0) < 0 and f["home_ml"] is not None) else [], feats))
    tests.append(evaluate(
        "Any home underdog ATS (control)", "situational", "spread",
        lambda f: [("ATS", "home")] if (f["spread_line"] is not None and f["spread_line"] < 0) else [], feats))
    tests.append(evaluate(
        "Any away underdog ATS (control)", "situational", "spread",
        lambda f: [("ATS", "away")] if (f["spread_line"] is not None and f["spread_line"] > 0) else [], feats))
    tests.append(evaluate(
        "Team off bye -> ATS", "schedule/rest", "spread",
        lambda f: ([("ATS", "home")] if f["home_off_bye"] and not f["away_off_bye"]
                   else [("ATS", "away")] if f["away_off_bye"] and not f["home_off_bye"] else []), feats))
    for thr in (14, 17, 21, 24):
        def fade(f, thr=thr):
            for side, lm in (("away", f["last_margin_h"]), ("home", f["last_margin_a"])):
                if lm is not None and lm >= thr:
                    return [("ATS", side)]
            return []
        tests.append(evaluate(f"Fade team that won last game by >= {thr}", "mean reversion", "spread", fade, feats))
    for thr in (10, 14, 17):
        def fade_c(f, thr=thr):
            for side, la in (("away", f["last_ats_h"]), ("home", f["last_ats_a"])):
                if la is not None and la >= thr:
                    return [("ATS", side)]
            return []
        tests.append(evaluate(f"Fade team that covered by >= {thr} last week", "mean reversion", "spread", fade_c, feats))
    for thr in (2, 3, 5, 8):
        def mlval(f, thr=thr):
            if f["home_ml"] is None or f["away_ml"] is None:
                return []
            from lib_core import american_to_prob
            p_home = norm_cdf(f["model_margin"] / 13.5)
            mh = 1.0 / (1.0 / american_to_prob(f["home_ml"]) + 1.0 / american_to_prob(f["away_ml"]))
            edges = {"home": p_home - mh, "away": (1 - p_home) - (1 - mh)}
            side = max(edges, key=edges.get)
            return [("ML", side)] if edges[side] * 100 >= thr else []
        tests.append(evaluate(f"Moneyline value >= {thr}%", "own line vs market", "moneyline", mlval, feats))
    tests.append(evaluate(
        "Dome game -> over", "weather", "total",
        lambda f: [("TOTAL", "over")] if f["dome_flag"] else [], feats))

    tests = [t for t in tests if t]
    ps = [t["p_one_sided"] if t["p_one_sided"] is not None else 1.0 for t in tests]
    adj = benjamini_hochberg(ps)
    for t, a in zip(tests, adj):
        t["bh_adjusted_p"] = round(a, 4) if a is not None else None
        t["survives_fdr"] = bool(a is not None and a < 0.05)
        w = t["windows"]
        t["consistent_out_of_sample"] = bool(
            (w["validation"]["roi"] or -1) > 0 and (w["holdout"]["roi"] or -1) > 0)

    summary = {
        "tests_run": len(tests),
        "survive_fdr_05": sum(1 for t in tests if t["survives_fdr"]),
        "positive_full_sample": sum(1 for t in tests if t["roi"] > 0),
        "positive_in_both_out_of_sample_windows": sum(1 for t in tests if t["consistent_out_of_sample"]),
        "expected_false_positives_at_5pct_if_all_null": round(0.05 * len(tests), 2),
    }
    out = {"generated_utc": "2026-11-01", "summary": summary, "tests": tests,
           "windows": {"design": DESIGN, "validation": VALIDATION, "holdout": HOLDOUT},
           "method": "Each row is a mechanical rule priced at the closing line carried in the dataset. "
                     "p-values are one-sided (H0: ROI <= 0) and BH-adjusted across all tests in the battery."}
    os.makedirs(REPORTS, exist_ok=True)
    with open(os.path.join(REPORTS, "scan.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps(summary, indent=1))
    for t in sorted(tests, key=lambda x: -(x["t_stat"] or 0))[:12]:
        w = t["windows"]
        print(f"{t['signal'][:44]:<44} n={t['n']:>5} roi={t['roi']:>7} t={t['t_stat']:>6} "
              f"bh={t['bh_adjusted_p']:>7} des={w['design']['roi']} val={w['validation']['roi']} hold={w['holdout']['roi']}")


if __name__ == "__main__":
    main()
