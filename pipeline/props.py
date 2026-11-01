"""T6b — Player-prop module: what can be verified now, and what cannot.

Two parts:
  1. scoring_distributions / key_numbers  — computed from official final scores. Real numbers.
  2. prop_framework                       — the model, the gates and the data requirements for
                                            player props, plus the explicit data gap (F-04).

No player-level statistic is fabricated. Where player data is required, the report says so.
"""
from __future__ import annotations

import json
import math
import os
from collections import Counter

from lib_core import REPORTS, load_games, mean, stdev


def scoring_distributions(games):
    team_pts = []
    for g in games:
        if g["played"]:
            team_pts.append(g["home_score"])
            team_pts.append(g["away_score"])
    m = mean(team_pts)
    sd = stdev(team_pts)
    dist = []
    for k in range(0, 46, 3):
        dist.append({"points_at_least": k,
                     "share_of_team_games": round(mean([1.0 if p >= k else 0.0 for p in team_pts]), 4),
                     "n": len(team_pts)})
    # Poisson vs observed dispersion test (variance/mean ratio) - supports using a negative-binomial
    var = sd ** 2
    out = {
        "n_team_games": len(team_pts),
        "mean_points": round(m, 3),
        "sd_points": round(sd, 3),
        "variance_over_mean": round(var / m, 3),
        "poisson_expected_ratio": 1.0,
        "interpretation": "variance/mean >> 1 => team scoring is over-dispersed versus Poisson; prop models should use a negative-binomial / normal mixture, not Poisson.",
        "cumulative": dist,
    }
    return out


def key_numbers(games):
    played = [g for g in games if g["played"]]
    margins = Counter(abs(int(g["margin"])) for g in played)
    totals = Counter(int(g["tot"]) for g in played)
    rows = []
    for k in range(0, 15):
        rows.append({"number": k, "margin_share_pct": round(100 * margins.get(k, 0) / len(played), 3),
                     "margin_games": margins.get(k, 0)})
    # the practical consequence for line-making: never sell through the key numbers
    cum = {}
    for k in (3, 7, 10, 14):
        cum[str(k)] = round(sum(margins.get(i, 0) for i in range(0, k + 1)) / len(played), 4)
    return {"n_games": len(played), "margin_distribution": rows,
            "cumulative_share_margin_le": cum,
            "most_common_totals": [{"total": t, "games": c} for t, c in totals.most_common(10)],
            "push_rate_at_spread": round(sum(1 for g in played
                                            if g["spread_line"] is not None
                                            and g["margin"] == g["spread_line"]) /
                                        max(1, sum(1 for g in played if g["spread_line"] is not None)), 4)}


PROP_FRAMEWORK = {
    "markets": [
        {"market": "Passing yards", "model": "Normal(projected mean, game-level sd) with a floor at 0",
         "primary_driver": "team pass volume projection x opponent pass defence x game script (spread)"},
        {"market": "Rushing yards", "model": "Normal with right skew; mixture over game script",
         "primary_driver": "team run volume, expected win probability (leading teams run more), opponent run defence"},
        {"market": "Receptions", "model": "Negative binomial (count data, over-dispersed)",
         "primary_driver": "target share x team pass attempts; route participation"},
        {"market": "Receiving yards", "model": "Normal with heavy right tail",
         "primary_driver": "targets x depth of target x opponent coverage; strongly co-moves with the QB leg"},
        {"market": "Anytime touchdown", "model": "Bernoulli with p from expected team points x player TD share",
         "primary_driver": "team implied total, red-zone usage"},
    ],
    "correlation_structure": [
        {"pair": "QB passing yards + own WR/TE receiving yards", "sign": "strongly positive",
         "reason": "shared pass volume and the same completions",
         "empirical_status": "NOT MEASURED in this build - requires player-week game logs (F-04)"},
        {"pair": "QB passing yards + own RB rushing yards", "sign": "negative (moderate)",
         "reason": "game script: trailing teams pass, leading teams run",
         "empirical_status": "NOT MEASURED (F-04)"},
        {"pair": "Two pass-catchers on the same team", "sign": "slightly negative to small positive",
         "reason": "target competition vs shared volume; the net sign is an empirical question",
         "empirical_status": "NOT MEASURED (F-04)"},
        {"pair": "Pass-catcher + opposing pass-catcher", "sign": "positive but small",
         "reason": "shared pace / shootout environment",
         "empirical_status": "anchor: measured corr(home points, away points) = see correlations.json"},
        {"pair": "Player yardage + game total OVER", "sign": "positive",
         "reason": "team scoring environment",
         "empirical_status": "anchor available at team level: see correlations.json"},
    ],
    "required_sample_sizes": {
        "note": "Games needed to estimate a prop-pair correlation to +/-0.10 with 95% confidence (Fisher z).",
        "by_true_r": None,   # filled from correlations.json in build_site
    },
    "validation_gates_for_props": [
        {"gate": "P1 Player identity mapping", "requirement": "player id resolved to the official roster for the game (no name-only joins)"},
        {"gate": "P2 Injury/participation status known at bet time", "requirement": "models may only use information published before kickoff"},
        {"gate": "P3 Closing prop line captured", "requirement": "a verified market line must exist; without it no edge can be claimed"},
        {"gate": "P4 >= 200 settled props per market", "requirement": "sample size floor before any claim"},
        {"gate": "P5 Holdout positive and BH-adjusted p < 0.05", "requirement": "same multiplicity control as game markets"},
        {"gate": "P6 Correlation matrix estimated, not assumed", "requirement": "SGP legs priced from a measured joint distribution with a stated CI"},
    ],
    "data_gap": {
        "id": "F-04",
        "statement": "Player-week statistics could not be obtained from a verifiable source inside this build environment.",
        "evidence": [
            "nflverse release assets (player_stats_*, stats_player_week_*) live on release-assets.githubusercontent.com, which is blocked from the build sandbox (TLS failure recorded in COORDINATION.md).",
            "Every reachable GitHub mirror of stats_player_week_*.csv was inspected and is a truncated or synthetic test fixture: Eric-Weng/CommishDesk contains team codes XXX/YYY and a fabricated player; Fibonacci-0112/NFL-360 is cut at 76 rows; balprab24/fantasy-kai ships a single-season fixture only.",
        ],
        "consequence": "Player-prop baselines, prop lines and prop correlations are therefore NOT published as numbers. The site publishes the framework, the gates, the required sample sizes and the team-level anchors that a prop model must be consistent with.",
        "what_would_unblock_it": "Any one of: (a) a player-week CSV export supplied directly, (b) an official league stats feed, (c) a licensed odds feed for closing prop lines.",
    },
}


def main():
    games = load_games()
    out = {
        "generated_utc": "2026-11-01",
        "scoring_distributions": scoring_distributions(games),
        "key_numbers": key_numbers(games),
        "prop_framework": PROP_FRAMEWORK,
    }
    os.makedirs(REPORTS, exist_ok=True)
    with open(os.path.join(REPORTS, "props.json"), "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=1)
    print(json.dumps(out["scoring_distributions"], indent=1)[:900])
    print(json.dumps(out["key_numbers"], indent=1)[:1200])


if __name__ == "__main__":
    main()
