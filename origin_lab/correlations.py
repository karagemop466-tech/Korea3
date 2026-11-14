#!/usr/bin/env python3
"""Requirement 7 — correlations computed only from officially sourced numbers, with n on every row.

What counts as officially sourced here
--------------------------------------
A final score is a fact only the league creates. The NFL publishes every one of them. Everything in
Table A and Table B is a function of final scores and of nothing else: margins, totals, team points
for and against, and the win/loss of a bet whose strike price we set ourselves.

A market price is not. No official publisher prints NFL point spreads, totals or moneylines — not
the league, not Football Operations, not any club. So any correlation whose definition needs a
market number cannot be computed from officially sourced inputs, and under this brief it is left
blank with a reason on the row rather than computed from the third-party dataset and labelled
"correlation".

That is not a rounding problem, it is the central tension in the brief, and it is raised as an open
question rather than resolved here: parlay pricing *needs* a leg-correlation, and a leg-correlation
as usually defined needs a market price. The way out that this repository uses is to originate its
own numbers (requirement 3), so a leg is defined against our own fair line instead of a book's, and
its outcome is then a pure function of the official score. Table B shows that working.

Every row carries n, and every r carries a Fisher-z 95% interval.
"""
from __future__ import annotations

import json
import math
from collections import defaultdict

import lib

OUT = lib.DATA / "correlations.json"


def r_ci(xs, ys, label, note, source_id="S05"):
    n = min(len(xs), len(ys))
    r = lib.pearson(xs, ys)
    lo, hi = lib.fisher_ci(r, n) if r is not None else (None, None)
    return {
        "pair": label, "n": n,
        "r": lib.round_or_none(r, 5),
        "ci_low": lib.round_or_none(lo, 5), "ci_high": lib.round_or_none(hi, 5),
        "note": note, "source_id": source_id,
        "sourced": "official",
    }


def phi_from_table(a, b, c, d):
    """2x2 phi coefficient from the four joint counts."""
    n = a + b + c + d
    if n == 0:
        return None, 0
    r1, r2 = (a + b) / n, (a + c) / n
    p1 = a / n
    denom = math.sqrt(r1 * (1 - r1) * r2 * (1 - r2))
    if denom == 0:
        return None, n
    return (p1 - r1 * r2) / denom, n


def main():
    games = [g for g in lib.load_csv(lib.RAW / "games.csv") if g["game_type"] == "REG"]
    played = []
    for g in games:
        hs, as_ = lib.fint(g, "home_score"), lib.fint(g, "away_score")
        if hs is None or as_ is None:
            continue
        played.append({"season": lib.fint(g, "season"), "week": lib.fint(g, "week"),
                       "home": g["home_team"], "away": g["away_team"],
                       "hs": hs, "as_": as_, "margin": hs - as_, "total": hs + as_})

    # ---------------------------------------------------------------- Table A
    A = []
    A.append(r_ci([g["margin"] for g in played], [g["total"] for g in played],
                  "Home margin vs game total (same game)",
                  "Both are arithmetic on the official final score. A positive value means the home team tends to win by more in high-scoring games."))
    A.append(r_ci([g["hs"] for g in played], [g["as_"] for g in played],
                  "Home points vs away points (same game)",
                  "The two halves of one official scoreline. This is the number a same-game totals parlay actually rests on."))

    # consecutive games, same team
    by_team = defaultdict(list)
    order = sorted(played, key=lambda g: (g["season"], g["week"], g["home"]))
    for g in order:
        by_team[g["home"]].append({"pf": g["hs"], "pa": g["as_"], "margin": g["margin"]})
        by_team[g["away"]].append({"pf": g["as_"], "pa": g["hs"], "margin": -g["margin"]})
    for field, label in (("pf", "points scored"), ("pa", "points conceded"), ("margin", "margin")):
        xs, ys = [], []
        for t, hist in by_team.items():
            for i in range(len(hist) - 1):
                xs.append(hist[i][field]); ys.append(hist[i + 1][field])
        A.append(r_ci(xs, ys, f"Team {label}, consecutive games (same team, t vs t+1)",
                      "Autocorrelation of an official scoreboard quantity. If this were strongly positive it would be a scoreboard fact worth trading on; the interval is what decides that."))

    # week-level league scoring environment
    week_tot = defaultdict(list)
    for g in played:
        week_tot[(g["season"], g["week"])].append(g["total"])
    weeks = sorted(week_tot)
    wmeans = [lib.mean(week_tot[w]) for w in weeks]
    A.append(r_ci(wmeans[:-1], wmeans[1:],
                  "League mean game total, consecutive weeks (t vs t+1)",
                  "Whether a high-scoring week is followed by another. One point per week; n is the number of consecutive week pairs."))

    # team-season level
    seas_pf, seas_pa = defaultdict(lambda: [0, 0]), defaultdict(lambda: [0, 0])
    seas_games = defaultdict(int)
    team_games = defaultdict(int)
    for g in played:
        if g["season"] >= 2026:      # 2026 is in progress; including it would mix a partial season in
            continue
        seas_pf[(g["season"], g["home"])][0] += g["hs"]
        seas_pa[(g["season"], g["home"])][1] += g["as_"]
        seas_pf[(g["season"], g["away"])][0] += g["as_"]
        seas_pa[(g["season"], g["away"])][1] += g["hs"]
        seas_games[g["season"]] += 1
        team_games[(g["season"], g["home"])] += 1
        team_games[(g["season"], g["away"])] += 1
    keys = sorted(seas_pf)
    A.append(r_ci([seas_pf[k][0] for k in keys], [seas_pa[k][1] for k in keys],
                  "Team-season points for vs points against",
                  "One point per team-season, seasons 1999-2025 only. 2026 is excluded because the season is in progress and its totals are not final."))
    xs, ys = [], []
    by_t = defaultdict(dict)
    for k in keys:
        gp = team_games[k] or 1
        by_t[k[1]][k[0]] = seas_pf[k][0] / gp
    for t, d in by_t.items():
        for s in sorted(d):
            if s + 1 in d:
                xs.append(d[s]); ys.append(d[s + 1])
    A.append(r_ci(xs, ys, "Team-season scoring rate, season t vs t+1",
                  "How much of a club's scoring rate survives into the next season. One point per consecutive team-season pair."))

    # ---------------------------------------------------------------- Table B: parlay leg dependence
    B = []
    try:
        legs = json.loads((lib.DATA / "parlay_legs.json").read_text(encoding="utf-8"))["rows"]
    except FileNotFoundError:
        legs = []
    for sid, label, note in (
        ("S6", "Same-game card: our side leg vs our total leg",
         "Both legs are defined against the line this repository originates, so each leg's outcome is a function of the official final score alone. The dependence measured here is therefore officially sourced."),
        ("S7", "Cross-game card: the week's two largest side legs",
         "Two games, so there is no shared-score reason for dependence; the measurement is the test of whether one exists."),
    ):
        rs = [r for r in legs if r["strategy"] == sid]
        if not rs:
            B.append({"pair": label, "n": 0, "phi": None, "ci_low": None, "ci_high": None,
                      "joint_observed": None, "joint_if_independent": None,
                      "note": note, "sourced": "official"})
            continue
        a = sum(1 for r in rs if r["leg1_win"] == 1 and r["leg2_win"] == 1)
        b = sum(1 for r in rs if r["leg1_win"] == 1 and r["leg2_win"] == 0)
        c = sum(1 for r in rs if r["leg1_win"] == 0 and r["leg2_win"] == 1)
        d = sum(1 for r in rs if r["leg1_win"] == 0 and r["leg2_win"] == 0)
        phi, n = phi_from_table(a, b, c, d)
        # Fisher-z CI for phi uses the same transform as Pearson r on 0/1 data
        lo, hi = lib.fisher_ci(phi, n) if phi is not None else (None, None)
        r1 = (a + b) / n
        r2 = (a + c) / n
        B.append({
            "pair": label, "n": n,
            "phi": lib.round_or_none(phi, 5),
            "ci_low": lib.round_or_none(lo, 5), "ci_high": lib.round_or_none(hi, 5),
            "joint_observed": round(a / n, 5),
            "joint_if_independent": round(r1 * r2, 5),
            "joint_difference": round(a / n - r1 * r2, 5),
            "note": note + (" A negative phi means the legs win together less often than independence implies, so a card priced at the product of the two legs is worse for the bettor than its price suggests."
                            if phi is not None and phi < 0 else ""),
            "sourced": "official",
        })

    # ---------------------------------------------------------------- Table C: cannot be computed
    C = [
        {"pair": "Market spread cover vs market total over (same game)",
         "why": "Both legs are defined by a market number. No official publisher prints NFL spreads or totals, so there is no officially sourced input to correlate.",
         "n": None, "unblock": "Admit the pinned third-party market file as an input, or originate the legs against our own numbers (which is what Table B does)."},
        {"pair": "Our fair-vs-market difference vs the settled outcome",
         "why": "One side of the pair is a market price. Our own fair number is reproducible, the market's is not officially published.",
         "n": None, "unblock": "Same choice. Until it is made, the leaderboard reports ROI at the recorded close and flags the convention."},
        {"pair": "Correlation a two-leg card needs to break even",
         "why": "The threshold is arithmetic on the two leg prices. Prices are not officially published, so the threshold cannot be stated as an officially sourced number.",
         "n": None, "unblock": "Decide the price-input question. The formula is published on the page; only the input is missing."},
        {"pair": "Player-prop leg correlations",
         "why": "No official publisher prints player-prop prices, and no official player-level log is reachable from this repository. There is nothing to correlate.",
         "n": None, "unblock": "Acquire an official or licensed player feed. The schema is committed and every value is blank until then."},
    ]

    ties = sum(1 for g in played if g["margin"] == 0)
    out = {
        "_meta": {
            "generated_by": "origin_lab/correlations.py",
            "session": "arena/5f341290-korea3",
            "rule": "A correlation is published only when every variable it correlates is an official league fact or a function of one. Anything that needs a market price, a model output or a third-party figure is left blank with a reason. n is on every row.",
            "interval": "Two-sided 95% Fisher-z interval on the published r or phi.",
            "official_figures_used": "Final scores only: home_score and away_score, 1999-2026 regular season, transcribed into the pinned dataset and, for 2026, reconciled club by club against the league's own standings page.",
        },
        "table_a_official": A,
        "table_b_parlay_legs": B,
        "table_c_not_computable": C,
        "ties": {"games": len(played), "ties": ties,
                 "rate": round(ties / len(played), 6) if played else None,
                 "note": "A regular-season game can end tied. This is the base rate a moneyline settlement rule has to handle; it is published because the fair-price column depends on it."},
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")

    print("Table A (officially sourced, scoreboard only): %d rows" % len(A))
    for r in A:
        print("   n=%-6d r=%-9s [%s, %s]  %s" % (r["n"], r["r"], r["ci_low"], r["ci_high"], r["pair"][:62]))
    print("Table B (parlay leg dependence): %d rows" % len(B))
    for r in B:
        print("   n=%-6d phi=%-9s joint=%s indep=%s  %s" % (
            r["n"], r["phi"], r["joint_observed"], r["joint_if_independent"], r["pair"][:52]))
    print("Table C (not computable from official sources): %d rows" % len(C))
    print("ties: %d of %d games (%s)" % (ties, len(played), out["ties"]["rate"]))


if __name__ == "__main__":
    main()
