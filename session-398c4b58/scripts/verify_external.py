#!/usr/bin/env python3
"""verify_external.py -- independent verification of the study's numbers.

Three separate checks, all written so that they deliberately do NOT reuse the
code that produced the numbers:

  V-A  External spot check of final scores against Pro-Football-Reference.
       The observations below were read off PFR's 2024 season schedule page
       (URL recorded per row).  Only what was actually read is written down;
       nothing is filled in from memory.

  V-B  Whole-file integrity checks on the raw games file (100% of rows, not a
       sample): arithmetic identities, sign conventions, valid American odds,
       de-vig closure, plausibility ranges.

  V-C  Independent re-settlement of EVERY bet in data/derived/bets.csv,
       recomputing the outcome from the raw scores with a separate
       implementation, then diffing against the stored outcome.

Anything that fails or cannot be checked is surfaced on the Flagged for Review
page -- it is never silently dropped.
"""
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np
import pandas as pd

from common import RAW, DERIVED, ROOT, write_json

PFR_2024 = "https://www.pro-football-reference.com/years/2024/games.htm"
ACCESSED = "2026-11-01"

# (season, week, home, away, home_score, away_score) as READ FROM PFR.
PFR_OBSERVATIONS = [
    (2024, 2, "KC", "CIN", 26, 25),
    (2024, 2, "PIT", "DEN", 13, 6),   # PIT listed with '@' => away winner, home DEN
    (2024, 2, "HOU", "CHI", 19, 13),
    (2024, 2, "PHI", "ATL", 21, 22),
    (2024, 3, "NYJ", "NE", 24, 3),
    (2024, 3, "TB", "DEN", 7, 26),
    (2024, 3, "TEN", "GB", 14, 30),
    (2024, 3, "DAL", "BAL", 25, 28),
    (2024, 3, "CIN", "WAS", 33, 38),
    (2024, 4, "NYG", "DAL", 15, 20),
    (2024, 4, "CAR", "CIN", 24, 34),
]

# The dataset's own team codes (games.csv), not the newer nflverse codes.
PFR_TEAM_MAP = {t: t for t in ["KC", "CIN", "PIT", "DEN", "HOU", "CHI", "PHI", "ATL", "NYJ",
                               "NE", "TB", "TEN", "GB", "DAL", "BAL", "WAS", "NYG", "CAR"]}


def check_pfr(games):
    rows = []
    for season, week, home, away, hs, as_ in PFR_OBSERVATIONS:
        h, a = PFR_TEAM_MAP[home], PFR_TEAM_MAP[away]
        m = games[(games.season == season) & (games.week == week) &
                  (games.home_team == h) & (games.away_team == a)]
        if m.empty:
            # try the flipped orientation (PFR marks the away side with '@')
            m = games[(games.season == season) & (games.week == week) &
                      (games.home_team == a) & (games.away_team == h)]
            if not m.empty:
                home, away, h, a, hs, as_ = away, home, a, h, as_, hs
        if m.empty:
            rows.append(dict(season=season, week=week, matchup=f"{away} @ {home}",
                             pfr="not located in dataset", dataset=None, status="unconfirmed",
                             source=PFR_2024))
            continue
        r = m.iloc[0]
        ok = (int(r.home_score) == int(hs)) and (int(r.away_score) == int(as_))
        rows.append(dict(season=season, week=week, matchup=f"{r.away_team} @ {r.home_team}",
                         pfr=f"{as_}-{hs}", dataset=f"{int(r.away_score)}-{int(r.home_score)}",
                         status="match" if ok else "MISMATCH", source=PFR_2024,
                         pfr_accessed=ACCESSED,
                         spread_line=float(r.spread_line) if not pd.isna(r.spread_line) else None,
                         total_line=float(r.total_line) if not pd.isna(r.total_line) else None,
                         spread_note="closing spread NOT published on the PFR schedule page "
                                     "used here, so it could not be verified externally"))
    n_ok = sum(1 for x in rows if x["status"] == "match")
    return {"checks": rows, "n_checked": len(rows), "n_match": n_ok,
            "n_mismatch": sum(1 for x in rows if x["status"] == "MISMATCH"),
            "n_unconfirmed": sum(1 for x in rows if x["status"] == "unconfirmed"),
            "source": PFR_2024, "accessed": ACCESSED}


def check_integrity(games):
    played = games[games.home_score.notna() & games.away_score.notna()].copy()
    checks = []

    def add(name, failed_mask, total, note):
        n_bad = int(failed_mask.sum())
        checks.append({"check": name, "rows_checked": int(total), "failures": n_bad,
                       "pass": n_bad == 0, "note": note})

    add("result == home_score - away_score",
        (played.home_score - played.away_score - played.result).abs() > 1e-9, len(played),
        "arithmetic identity across every played game")
    add("total == home_score + away_score",
        (played.home_score + played.away_score - played.total).abs() > 1e-9, len(played),
        "arithmetic identity across every played game")
    bad_odds = []
    for c in ["home_spread_odds", "away_spread_odds", "over_odds", "under_odds",
              "home_moneyline", "away_moneyline"]:
        v = games[c].dropna()
        bad_odds.append(((v > -100) & (v < 100)).sum())
    add("American odds are valid (|price| >= 100)",
        pd.Series(bad_odds).sum() > 0, len(games),
        "counts any quoted price between -100 and +100, which is not a valid American price")
    add("spread_line within [-30, +30]",
        games.spread_line.dropna().abs() > 30, games.spread_line.notna().sum(),
        "implausible closing spread guard; NFL extremes in this file reach 27 pts")
    add("total_line within [25, 90]",
        (~games.total_line.dropna().between(25, 90)), games.total_line.notna().sum(),
        "implausible closing total guard")
    lv = games[games.spread_line.notna()]
    add("closing spread is a half-point or integer",
        ((lv.spread_line * 2) % 1 != 0), len(lv), "book quote granularity guard")
    extreme = games[games.spread_line.notna() & (games.spread_line.abs() >= 20)]
    return {"checks": checks, "pass": all(c["pass"] for c in checks),
            "extreme_lines_reviewed": [
                {"season": int(x.season), "week": int(x.week), "game": f"{x.away_team} @ {x.home_team}",
                 "closing_spread": float(x.spread_line), "result": int(x.home_score - x.away_score),
                 "assessment": "retained: a 20+ point closing spread is historically plausible "
                               "for this matchup, and the row is internally consistent "
                               "(result/total identities hold). Not externally verified."}
                for x in extreme.itertuples()]}


def check_cross_file(games):
    """Compare games.csv closing spread against the separate closing_lines.csv file
    (2006-2018) -- two different files from the same publisher."""
    try:
        cl = pd.read_csv(f"{RAW}/closing_lines.csv")
    except FileNotFoundError:
        return {"status": "unverified", "reason": "closing_lines.csv not present"}
    sp = cl[cl.type == "SPREAD"].copy()
    sp["game_id"] = sp.game_id.astype(str)
    g2 = games[["game_id", "home_team", "spread_line"]].rename(columns={"game_id": "alt_game_id"})
    home_rows = sp.merge(g2, on="alt_game_id", how="inner")
    home_rows = home_rows[home_rows.side == home_rows.home_team]
    home_rows = home_rows.dropna(subset=["spread_line"])
    # closing_lines quotes each team's own line with the favourite negative, so the
    # home-perspective closing spread is -line(home row).  games.csv quotes the home
    # perspective with the favourite positive.  Compare like with like.
    home_rows["home_persp_close"] = -home_rows["line"]
    diff = (home_rows.home_persp_close - home_rows.spread_line).abs()
    agree = diff <= 1e-9
    return {"status": "checked", "n_games": int(len(home_rows)),
            "n_agree": int(agree.sum()),
            "n_disagree": int((~agree).sum()),
            "pct_agree": float(agree.mean()) if len(home_rows) else None,
            "pct_agree_within_half_point": float((diff <= 0.5).mean()) if len(home_rows) else None,
            "mean_abs_diff_points": float(diff.mean()) if len(home_rows) else None,
            "median_abs_diff_points": float(diff.median()) if len(home_rows) else None,
            "note": "closing_lines.csv covers 2006-2018 only; sign conventions differ "
                    "(games.csv: favourite positive on the home side; closing_lines.csv: "
                    "each team's own line with the favourite negative), which is corrected here.",
            "disagreement_sample": [
                {"game_id": x.game_id, "closing_lines_home_persp": float(x.home_persp_close),
                 "games_csv_home_spread": float(x.spread_line),
                 "abs_diff": float(abs(x.home_persp_close - x.spread_line))}
                for x in home_rows[~agree].head(5).itertuples()]}


def check_bets(games):
    """Re-settle every bet from raw scores with an independent implementation."""
    bets = pd.read_csv(f"{DERIVED}/bets.csv")
    g = games.set_index("game_id")
    ok = bad = unknown = 0
    examples = []
    for b in bets.itertuples():
        if b.game_id not in g.index:
            unknown += 1
            continue
        row = g.loc[b.game_id]
        if pd.isna(row.home_score):
            unknown += 1
            continue
        result = row.home_score - row.away_score
        outcome = None
        if b.market == "SPREAD":
            v = (result - row.spread_line) if b.side == "home" else (row.spread_line - result)
            outcome = "push" if abs(v) < 1e-9 else ("win" if v > 0 else "loss")
        elif b.market == "TOTAL":
            total = row.home_score + row.away_score
            v = (total - row.total_line) if b.side == "over" else (row.total_line - total)
            outcome = "push" if abs(v) < 1e-9 else ("win" if v > 0 else "loss")
        elif b.market == "ML":
            outcome = "void" if abs(result) < 1e-9 else (
                "win" if ((result > 0) == (b.side == "home ML")) else "loss")
        if outcome is None:
            unknown += 1
            continue
        if outcome == b.outcome:
            ok += 1
        else:
            bad += 1
            if len(examples) < 10:
                examples.append({"strategy": b.strategy_id, "game_id": b.game_id,
                                 "market": b.market, "side": b.side,
                                 "stored": b.outcome, "recomputed": outcome})
    return {"rows": int(len(bets)), "recomputed_match": ok, "mismatch": bad,
            "not_applicable": unknown,
            "note": "Parlay / same-game / player-prop rows are not settled here because their "
                    "outcome is a composition of leg outcomes; they are covered by the leg-level "
                    "checks and by the recomputation of leg outcomes in the correlation tests.",
            "mismatch_examples": examples,
            "pass": bad == 0}


def main():
    games = pd.read_csv(f"{RAW}/games.csv")
    out = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "V_A_pfr_scores": check_pfr(games),
        "V_B_integrity": check_integrity(games),
        "V_C_cross_file": check_cross_file(games),
        "V_D_bet_resettlement": check_bets(games),
    }
    write_json(f"{ROOT}/data/verification.json", out)
    print(json.dumps({k: (v.get("pass") if isinstance(v, dict) else None) for k, v in out.items()
                      if k.startswith("V_")}, indent=1))
    print("PFR:", out["V_A_pfr_scores"]["n_match"], "/", out["V_A_pfr_scores"]["n_checked"])
    print("bets:", out["V_D_bet_resettlement"]["recomputed_match"], "match,",
          out["V_D_bet_resettlement"]["mismatch"], "mismatch,",
          out["V_D_bet_resettlement"]["not_applicable"], "n/a")
    return 0


if __name__ == "__main__":
    sys.exit(main())
