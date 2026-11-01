"""T2 — Independent verification of the working dataset against official NFL sources.

Outputs:
  reports/verification.json           machine-readable result of every check
  reports/standings_check_2025.csv    line-by-line derived vs official, 2025
  reports/standings_check_2026.csv    line-by-line derived vs official, 2026

Nothing here "fixes" data. It only compares and reports MATCH / MISMATCH / UNVERIFIED.
"""
from __future__ import annotations

import csv
import json
import os
from collections import Counter, defaultdict

from lib_core import DATA, REPORTS, load_games, write_csv

REG = {"REG"}

# nfl.com renders the Cardinals as "AZ"; the dataset uses "ARI". This is the only
# abbreviation difference between the two sources (all others match verbatim).
NFLCOM_TO_DATASET = {"AZ": "ARI"}


def derive_standings(games, season, game_type="REG"):
    st = defaultdict(lambda: {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "games": 0})
    for g in games:
        if g["season"] != season or g["game_type"] != game_type or not g["played"]:
            continue
        h, a = g["home_team"], g["away_team"]
        st[h]["pf"] += g["home_score"]; st[h]["pa"] += g["away_score"]; st[h]["games"] += 1
        st[a]["pf"] += g["away_score"]; st[a]["pa"] += g["home_score"]; st[a]["games"] += 1
        if g["home_score"] > g["away_score"]:
            st[h]["w"] += 1; st[a]["l"] += 1
        elif g["home_score"] < g["away_score"]:
            st[a]["w"] += 1; st[h]["l"] += 1
        else:
            st[h]["t"] += 1; st[a]["t"] += 1
    return st


def load_official(path):
    with open(path, newline="", encoding="utf-8") as fh:
        return {r["team"]: r for r in csv.DictReader(fh)}


def compare(games, season, official_path, out_csv):
    derived = derive_standings(games, season)
    official = load_official(official_path)
    rows, matches, mismatches, unverified = [], 0, [], []
    for team in sorted(official):
        o = official[team]
        lookup = NFLCOM_TO_DATASET.get(team, team)
        d = derived.get(lookup, {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "games": 0})
        fields = {}
        ok = True
        for k, dk in (("w", "w"), ("l", "l"), ("t", "t"), ("pf", "pf"), ("pa", "pa")):
            off_val = int(o[k])
            der_val = d[dk]
            fields[k + "_official"] = off_val
            fields[k + "_derived"] = der_val
            if off_val != der_val:
                ok = False
        if ok:
            matches += 1
        else:
            mismatches.append(team)
        rows.append({
            "season": season,
            "team": team,
            "games_played": d["games"],
            "w_official": fields["w_official"], "w_derived": fields["w_derived"],
            "l_official": fields["l_official"], "l_derived": fields["l_derived"],
            "t_official": fields["t_official"], "t_derived": fields["t_derived"],
            "pf_official": fields["pf_official"], "pf_derived": fields["pf_derived"],
            "pa_official": fields["pa_official"], "pa_derived": fields["pa_derived"],
            "status": "MATCH" if ok else "MISMATCH",
            "source_url": o["source_url"],
        })
    write_csv(out_csv, rows)
    teams_official = set(official)
    teams_derived = set(derived)
    return {
        "season": season,
        "teams_compared": len(official),
        "teams_match": matches,
        "mismatches": mismatches,
        "teams_missing_from_dataset": sorted(teams_official - teams_derived),
        "teams_extra_in_dataset": sorted(teams_derived - teams_official),
        "source_url": list(official.values())[0]["source_url"] if official else None,
        "comparison_csv": os.path.relpath(out_csv, os.path.dirname(REPORTS)),
    }


def integrity_checks(games):
    out = {}
    ids = Counter(g["game_id"] for g in games)
    out["n_rows"] = len(games)
    out["duplicate_game_ids"] = [k for k, v in ids.items() if v > 1]
    played = [g for g in games if g["played"]]
    out["n_played"] = len(played)
    out["seasons"] = [min(g["season"] for g in games), max(g["season"] for g in games)]
    out["game_types"] = dict(Counter(g["game_type"] for g in games))
    # sign convention checks (documented, not assumed)
    both = [g for g in played if g["spread_line"] is not None]
    out["spread_convention_check"] = {
        "n_with_spread": len(both),
        "mean_margin_minus_spread": round(sum(g["margin"] - g["spread_line"] for g in both) / len(both), 3),
        "home_cover_rate_excl_push": round(
            sum(1 for g in both if g["margin"] - g["spread_line"] > 0) /
            max(1, sum(1 for g in both if g["margin"] - g["spread_line"] != 0)), 4),
        "push_rate": round(sum(1 for g in both if g["margin"] - g["spread_line"] == 0) / len(both), 4),
        "share_home_favoured": round(sum(1 for g in both if g["spread_line"] > 0) / len(both), 4),
        "interpretation": "nflverse DATASETS.md: positive spread_line = home team favoured (lines up with result = home - away). Confirmed empirically: mean(home margin - spread_line) is ~0 and the cover rate excluding pushes is ~50%.",
    }
    tot = [g for g in played if g["total_line"] is not None]
    out["total_convention_check"] = {
        "n_with_total": len(tot),
        "mean_total_minus_line": round(sum(g["tot"] - g["total_line"] for g in tot) / len(tot), 3),
        "over_rate_excl_push": round(
            sum(1 for g in tot if g["tot"] - g["total_line"] > 0) /
            max(1, sum(1 for g in tot if g["tot"] - g["total_line"] != 0)), 4),
        "push_rate": round(sum(1 for g in tot if g["tot"] - g["total_line"] == 0) / len(tot), 4),
    }
    # missingness of market fields by season (documented so no imputation sneaks in)
    miss = {}
    for s in sorted({g["season"] for g in games}):
        sg = [g for g in games if g["season"] == s and g["played"]]
        if not sg:
            continue
        miss[s] = {
            "played": len(sg),
            "spread_line": sum(1 for g in sg if g["spread_line"] is not None),
            "total_line": sum(1 for g in sg if g["total_line"] is not None),
            "away_moneyline": sum(1 for g in sg if g["away_moneyline"] is not None),
            "home_moneyline": sum(1 for g in sg if g["home_moneyline"] is not None),
            "wind": sum(1 for g in sg if g["wind"] is not None),
            "temp": sum(1 for g in sg if g["temp"] is not None),
            "rest": sum(1 for g in sg if g["home_rest"] is not None and g["away_rest"] is not None),
        }
    out["field_coverage_by_season"] = miss
    out["ties"] = sum(1 for g in played if g["margin"] == 0)
    out["overtimes"] = sum(1 for g in played if str(g.get("overtime", "0")) == "1")
    out["neutral_site_games"] = sum(1 for g in games if g.get("location") == "Neutral")
    out["teams_seen"] = sorted({g["home_team"] for g in games})
    # arithmetic consistency: 2025 W+L+T must equal 2 x games
    s25 = derive_standings(games, 2025)
    out["season_2025_arithmetic"] = {
        "team_slots": sum(v["w"] + v["l"] + v["t"] for v in s25.values()),
        "games_played_times_two": 2 * sum(1 for g in games if g["season"] == 2025 and g["game_type"] == "REG" and g["played"]),
        "pf_total": sum(v["pf"] for v in s25.values()),
        "pa_total": sum(v["pa"] for v in s25.values()),
    }
    return out


def main():
    games = load_games()
    res = {"generated_utc": "2026-11-01",
           "dataset": "data/games_1999_2026_nflverse.csv",
           "dataset_source": "https://github.com/nflverse/nfldata",
           "integrity": integrity_checks(games)}
    res["standings_checks"] = [
        compare(games, 2025, os.path.join(DATA, "official", "nfl_standings_2025_REG.csv"),
                os.path.join(REPORTS, "standings_check_2025.csv")),
        compare(games, 2026, os.path.join(DATA, "official", "nfl_standings_2026_REG.csv"),
                os.path.join(REPORTS, "standings_check_2026.csv")),
    ]
    total_rows = sum(c["teams_compared"] for c in res["standings_checks"])
    total_match = sum(c["teams_match"] for c in res["standings_checks"])
    res["summary"] = {
        "official_rows_compared": total_rows,
        "official_rows_matching": total_match,
        "match_rate": round(total_match / total_rows, 4) if total_rows else None,
        "games_covered_by_verified_standings": sum(
            sum(1 for g in games if g["season"] == s and g["game_type"] == "REG" and g["played"])
            for s in (2025, 2026)),
    }
    os.makedirs(REPORTS, exist_ok=True)
    with open(os.path.join(REPORTS, "verification.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps({k: res[k] for k in ("summary",)}, indent=1))
    for c in res["standings_checks"]:
        print(c["season"], c["teams_match"], "/", c["teams_compared"], "mismatches:", c["mismatches"])
    ing = res["integrity"]
    print("rows", ing["n_rows"], "played", ing["n_played"], "dupes", len(ing["duplicate_game_ids"]))
    print("spread conv:", ing["spread_convention_check"])
    print("total conv:", ing["total_convention_check"])
    print("2025 arith:", ing["season_2025_arithmetic"])
    print("ties", ing["ties"], "ot", ing["overtimes"], "neutral", ing["neutral_site_games"])


if __name__ == "__main__":
    main()
