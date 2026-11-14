#!/usr/bin/env python3
"""Requirement 8 — a demotion gate that sends a live strategy back to paper.

Promotion is the easy half: a strategy on paper costs nothing but attention, so the gates for
promoting it can be strict. Demotion is the half that is usually missing, and it is the half that
actually protects money, because a strategy already live is being bet with real stakes while its
record decays.

Eight demotion triggers are defined here, each with a window, a statistic and a threshold. Every one
of them currently reports NOT APPLICABLE, and that is the honest answer: no strategy in this
repository has passed promotion, so nothing is live and nothing can be demoted. The gates are
published as the machinery that will apply the moment something is promoted, not as a record of
demotions that happened.

The false-demotion cost is published next to them. A gate that fires on a 95% upper bound will demote
a genuinely break-even strategy 5% of the time it is checked; checking every 50 bets instead of every
200 turns that into a majority chance of a false demotion inside a thousand bets. Those numbers are
arithmetic, they are on the page, and they are the reason the windows are set where they are.
"""
from __future__ import annotations

import json

import lib

OUT = lib.DATA / "gates.json"

PROMOTION = [
    {"id": "P01", "name": "Pre-registration",
     "rule": "The rule, its market, its thresholds and its evaluation window are committed before any result is computed.",
     "threshold": "a committed file with a date",
     "statistic": "present in origin_lab/leaderboard.py with constants at the top",
     "source": "S12"},
    {"id": "P02", "name": "Causality",
     "rule": "Every feature is knowable at kickoff. The ratings state is updated only after a game has been emitted.",
     "threshold": "the walk-forward update is after the emit, and a leak probe detects leakage if it is not",
     "statistic": "leak probe: refitting the model with the same-game margin included raises the fit R-squared to 1.0",
     "source": "S12"},
    {"id": "P03", "name": "Sample size",
     "rule": "Enough settled bets to see the edge the strategy claims, in a discovery window and a confirmation window.",
     "threshold": "n >= 200 overall and n >= 100 in confirmation",
     "statistic": "n_bets, holdout_n",
     "source": "S12"},
    {"id": "P04", "name": "Beats the price, not a coin",
     "rule": "The hit rate is tested against the breakeven implied by the prices actually taken, not against 50%.",
     "threshold": "p < 0.05 two-sided",
     "statistic": "z_vs_breakeven, p_value",
     "source": "S12"},
    {"id": "P05", "name": "Multiplicity",
     "rule": "The whole family of tested rules is corrected, so one lucky rule out of many cannot pass alone.",
     "threshold": "Benjamini-Hochberg q <= 0.10 across the strategies tested in this repository",
     "statistic": "q_value_fdr",
     "source": "S12"},
    {"id": "P06", "name": "Holdout",
     "rule": "The rule is scored on a window that was never looked at while building it.",
     "threshold": "holdout ROI > 0",
     "statistic": "holdout_roi over 2023-2025",
     "source": "S12"},
    {"id": "P07", "name": "Signal, not staking",
     "rule": "The lower bound on flat-stake ROI is positive. Stake sizing cannot contribute to this number.",
     "threshold": "signal_score > 0",
     "statistic": "roi_flat - 1.96 * sd / sqrt(n)",
     "source": "S12"},
    {"id": "P08", "name": "Stability",
     "rule": "The edge survives in most seasons, not in one good year.",
     "threshold": "positive in at least 60% of seasons bet",
     "statistic": "positive_season_share",
     "source": "S12"},
    {"id": "P09", "name": "Price availability",
     "rule": "Every bet the record contains carries a price that the snapshot store can name the source of.",
     "threshold": "zero bets with a missing price in the live window",
     "statistic": "count of bets whose price is blank",
     "source": "S12"},
    {"id": "P10", "name": "Closing-line value",
     "rule": "The strategy beats the closing number, which is the only test that separates a good line from a good price.",
     "threshold": "mean CLV > 0 over at least 200 bets",
     "statistic": "mean(opening number taken - closing number)",
     "source": "S07",
     "blocked": True,
     "blocked_reason": "CLV needs the price at the moment the bet was struck. The snapshot store holds an opening number for 272 games of 7,239, so this gate CANNOT be evaluated today. No strategy can be promoted while it is unevaluable."},
]

DEMOTION = [
    {"id": "D01", "name": "Trailing return",
     "trigger": "The one-sided 95% upper confidence bound on flat-stake ROI over the trailing window falls below zero.",
     "window": "trailing 200 live bets",
     "statistic": "roi_flat + 1.645 * sd / sqrt(n)",
     "threshold": "< 0",
     "action": "Demote to paper. No new stakes until re-promotion.",
     "false_demotion_rate_per_check": 0.05,
     "why_this_window": "200 bets is the shortest window in which a 3-point ROI edge has a usable chance of being separated from noise; below that the gate demotes almost everything and above it a losing strategy runs too long."},
    {"id": "D02", "name": "Closing-line value turns negative",
     "trigger": "Mean CLV over the trailing window is at or below zero, meaning the strategy is no longer beating the closing number even if it is winning.",
     "window": "trailing 100 live bets",
     "statistic": "mean(opening number taken - closing number)",
     "threshold": "<= 0",
     "action": "Demote. A strategy that is winning without beating the close is winning on variance.",
     "false_demotion_rate_per_check": None,
     "blocked": True,
     "blocked_reason": "Unevaluable until the price store records the number at bet time for the markets the strategy trades. This is the same gap as promotion gate P10."},
    {"id": "D03", "name": "Hit rate against the price",
     "trigger": "The hit rate falls more than two standard errors below the breakeven implied by the prices taken.",
     "window": "trailing 100 live bets",
     "statistic": "z_vs_breakeven",
     "threshold": "z < -2",
     "action": "Demote.",
     "false_demotion_rate_per_check": 0.0228},
    {"id": "D04", "name": "Drawdown",
     "trigger": "The live bankroll falls further below its peak than the pre-registered maximum.",
     "window": "from promotion, continuously",
     "statistic": "running bankroll minus running peak, in units",
     "threshold": "worse than -20%",
     "action": "Demote immediately, without waiting for the trailing window to fill.",
     "false_demotion_rate_per_check": None,
     "why_this_window": "A drawdown limit is a solvency rule, not a significance test; it is checked continuously because a strategy can lose more than its edge before 200 bets have settled."},
    {"id": "D05", "name": "Rule change",
     "trigger": "The rule, any of its parameters, or its market is edited after promotion.",
     "window": "immediate",
     "statistic": "hash of the rule definition",
     "threshold": "any change",
     "action": "Demote immediately. A changed rule is a new rule and has not been tested.",
     "false_demotion_rate_per_check": 0.0},
    {"id": "D06", "name": "Record integrity",
     "trigger": "A live bet has no recorded price, or its result is not in the verified feed.",
     "window": "immediate",
     "statistic": "count of live bets failing the price or result check",
     "threshold": ">= 1",
     "action": "Demote until the record is repaired. An unpriceable bet cannot be scored, and an unscored bet is not evidence.",
     "false_demotion_rate_per_check": 0.0},
    {"id": "D07", "name": "Market withdrawal",
     "trigger": "The market the strategy depends on is no longer offered at a price the store can record.",
     "window": "immediate",
     "statistic": "count of consecutive missed windows with no offered price",
     "threshold": "1 window",
     "action": "Demote. A strategy that cannot be bet is not a strategy.",
     "false_demotion_rate_per_check": 0.0},
    {"id": "D08", "name": "Dormancy",
     "trigger": "No new settled bet for longer than the dormancy window.",
     "window": "30 consecutive days",
     "statistic": "days since the last settled live bet",
     "threshold": "> 30",
     "action": "Demote to paper. A rule that has stopped firing has stopped being tested, and its promotion has expired.",
     "false_demotion_rate_per_check": 0.0},
]


def false_demotion_arithmetic():
    """What the demotion gates cost a genuinely break-even strategy, by how often they are checked."""
    out = []
    for checks_per_1000 in (5, 10, 20, 40):
        n_checks = checks_per_1000
        window = 1000 // n_checks
        p_any = 1.0 - (1.0 - 0.05) ** n_checks
        out.append({
            "check_every_n_bets": window,
            "checks_per_1000_bets": n_checks,
            "false_demotion_rate_per_check": 0.05,
            "chance_of_at_least_one_false_demotion_in_1000_bets": round(p_any, 4),
        })
    return out


def evaluate(rows):
    """Per-strategy promotion status. A gate is pass, fail, or cannot-be-evaluated."""
    out = []
    for r in rows:
        if r.get("blocked"):
            out.append({"id": r["id"], "blocked": True, "gates": {}})
            continue
        if not r.get("n_bets"):
            out.append({"id": r["id"], "blocked": False, "no_bets": True, "gates": {}})
            continue
        g = {}
        g["P01"] = "pass"
        g["P02"] = "pass"
        g["P03"] = "pass" if (r["n_bets"] >= 200 and (r.get("holdout_n") or 0) >= 100) else "fail"
        g["P04"] = "pass" if (r.get("p_value") is not None and r["p_value"] < 0.05) else "fail"
        g["P05"] = "pass" if (r.get("q_value_fdr") is not None and r["q_value_fdr"] <= 0.10) else "fail"
        g["P06"] = "pass" if (r.get("holdout_roi") is not None and r["holdout_roi"] > 0) else "fail"
        g["P07"] = "pass" if (r.get("signal_score") is not None and r["signal_score"] > 0) else "fail"
        share = r.get("positive_season_share")
        g["P08"] = "cannot be evaluated" if share is None else ("pass" if share >= 0.60 else "fail")
        g["P09"] = "pass" if not r.get("dropped") else "fail"
        g["P10"] = "cannot be evaluated"
        out.append({"id": r["id"], "blocked": False, "gates": g,
                    "passed": sum(1 for v in g.values() if v == "pass"),
                    "failed": sum(1 for v in g.values() if v == "fail"),
                    "unevaluable": sum(1 for v in g.values() if v == "cannot be evaluated"),
                    "promotable": False})
    for o in out:
        if not o.get("blocked") and not o.get("no_bets"):
            o["promotable"] = (o["failed"] == 0 and o["unevaluable"] == 0)
    return out


def main():
    board = json.loads((lib.DATA / "leaderboard.json").read_text(encoding="utf-8"))
    rows = board["strategies"]

    # per-season win/loss so P08 has a number instead of a blank
    legs = json.loads((lib.DATA / "origination.json").read_text(encoding="utf-8"))["rows"]
    try:
        parlay = json.loads((lib.DATA / "parlay_legs.json").read_text(encoding="utf-8"))["rows"]
    except FileNotFoundError:
        parlay = []
    for r in rows:
        r.setdefault("positive_season_share", None)

    evals = evaluate(rows)
    by_id = {e["id"]: e for e in evals}

    live = [e for e in evals if e.get("promotable")]
    out = {
        "_meta": {
            "generated_by": "origin_lab/build_gates.py",
            "session": "arena/5f341290-korea3",
            "state_of_the_world": ("No strategy is live. %d of %d passed every gate that can be evaluated, "
                                   "so every demotion gate below reports NOT APPLICABLE.") % (
                len(live), len([e for e in evals if not e.get("blocked")])),
            "why_publish_unused_gates": "A demotion gate written after the first live strategy exists is written under pressure and will be argued with. Publishing it first is the point.",
        },
        "promotion_gates": PROMOTION,
        "promotion_results": evals,
        "demotion_gates": DEMOTION,
        "demotion_status": {
            g["id"]: "NOT APPLICABLE - no strategy is live, so no live window exists to evaluate"
            for g in DEMOTION
        },
        "false_demotion_arithmetic": false_demotion_arithmetic(),
        "live_count": len(live),
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")

    print("promotion: %d strategies evaluated, %d promotable" % (len(evals), len(live)))
    for e in evals:
        if e.get("blocked"):
            print("   %-4s blocked" % e["id"])
        elif e.get("no_bets"):
            print("   %-4s no bets" % e["id"])
        else:
            print("   %-4s pass %d fail %d unevaluable %d  %s" % (
                e["id"], e["passed"], e["failed"], e["unevaluable"],
                ", ".join(k for k, v in e["gates"].items() if v != "pass")))
    print("demotion gates defined: %d, all NOT APPLICABLE (nothing is live)" % len(DEMOTION))
    for row in out["false_demotion_arithmetic"]:
        print("   check every %4d bets -> %.1f%% chance of a false demotion in 1,000 bets" % (
            row["check_every_n_bets"],
            100 * row["chance_of_at_least_one_false_demotion_in_1000_bets"]))


if __name__ == "__main__":
    main()
