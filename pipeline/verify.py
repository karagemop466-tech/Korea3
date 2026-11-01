"""T2 — Verification of the working dataset against the official NFL standings.

DATA-RIGHTS DESIGN (see flagged item F-10)
------------------------------------------
NFL.com's terms restrict systematic retrieval and reproduction of its content, and this project holds no NFL licence.
The 64 rows of NFL-sourced standings values that were originally transcribed to run this comparison have therefore
been removed from the repository. What remains is an *attestation*: which teams were compared, how many matched, the
URLs read, and the date. No NFL-sourced numeric value is redistributed here.

Consequences
  * `pipeline/verify.py` ALWAYS recomputes the derived aggregates from the open dataset (that is our own arithmetic).
  * It re-runs the official comparison only if a rights holder drops `official_csv` files into data/official/
    (paths and schema documented in the attestation). Otherwise it reports the attested result and sets
    `reproducible_offline: false`, so nobody can mistake an attested check for a live re-check.
  * `reports/standings_check_<season>.csv` publishes derived values + match status + the official URL.
    It does not reproduce the official numbers.

Scope note (QA request from arena/65d448da-korea3): this is a TEAM-AGGREGATE reconciliation. It validates the
outcome of every game through wins/losses/ties/points-for/points-against, but it is not a per-game official
verification and is never described as one (flagged item F-11).
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
# The mapping is applied BEFORE any comparison, including the set-difference checks
# (QA request from arena/65d448da-korea3 / audit/cross-session-qa.md).
NFLCOM_TO_DATASET = {"AZ": "ARI"}

ATTESTATION = os.path.join(DATA, "official", "verification_attestation.json")


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


def compare_live(games, season, official_path, out_csv):
    """Re-run the comparison locally. Only possible when a rights holder supplies the CSV."""
    derived = derive_standings(games, season)
    official = load_official(official_path)
    rows, matches, mismatches, missing = [], 0, [], []
    mapped_official = {NFLCOM_TO_DATASET.get(t, t): o for t, o in official.items()}
    for team in sorted(mapped_official):
        o = mapped_official[team]
        d = derived.get(team)
        if d is None:                      # never silently treat an absent team as a match
            status = "MISSING_FROM_DATASET"
            missing.append(team)
            d = {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "games": 0}
        else:
            ok = all(int(o[k]) == d[k] for k in ("w", "l", "t", "pf", "pa"))
            status = "MATCH" if ok else "MISMATCH"
            if ok:
                matches += 1
            else:
                mismatches.append(team)
        rows.append(_row(season, team, d, status, o["source_url"], "re-run locally against supplied official CSV"))
    write_csv(out_csv, rows)
    return {
        "season": season,
        "mode": "re-run locally",
        "teams_compared": len(mapped_official),
        "teams_match": matches,
        "mismatch_teams": mismatches,
        "missing_from_dataset": missing,
        "extra_in_dataset": sorted(set(derived) - set(mapped_official)),
        "source_url": list(official.values())[0]["source_url"] if official else None,
        "games_covered": sum(1 for g in games if g["season"] == season and g["game_type"] == "REG" and g["played"]),
        "comparison_csv": os.path.relpath(out_csv, os.path.dirname(REPORTS)),
    }


def _row(season, team, d, status, source_url, method):
    return {
        "season": season, "team": team, "games_played": d["games"],
        "w_derived": d["w"], "l_derived": d["l"], "t_derived": d["t"],
        "pf_derived": d["pf"], "pa_derived": d["pa"],
        "status": status, "verification_method": method, "source_url": source_url,
    }


def compare_attested(games, season, att, out_csv):
    """Publish our own derived aggregates plus the attested match status. No official values reproduced."""
    derived = derive_standings(games, season)
    entry = next((r for r in att["results"] if r["season"] == season), None)
    if entry is None:
        return None
    bad = set(entry.get("mismatch_teams", [])) | set(entry.get("missing_from_dataset", []))
    rows = []
    for team in sorted(entry["teams_compared_teams"]):
        d = derived.get(team)
        if d is None:
            status = "MISSING_FROM_DATASET"
            d = {"w": 0, "l": 0, "t": 0, "pf": 0, "pa": 0, "games": 0}
        else:
            status = "MISMATCH" if team in bad else "MATCH"
        rows.append(_row(season, team, d, status, entry["source_urls"][0],
                         f"attested {att['attested_on']} (official values not redistributed)"))
    write_csv(out_csv, rows)
    return {
        "season": season,
        "mode": "attested (official values not redistributed)",
        "teams_compared": entry["teams_compared"],
        "teams_match": entry["teams_match"],
        "mismatch_teams": entry.get("mismatch_teams", []),
        "missing_from_dataset": entry.get("missing_from_dataset", []),
        "extra_in_dataset": sorted(set(derived) - set(entry["teams_compared_teams"])),
        "source_url": entry["source_urls"][0],
        "source_urls": entry["source_urls"],
        "attested_on": att["attested_on"],
        "games_covered": sum(1 for g in games if g["season"] == season and g["game_type"] == "REG" and g["played"]),
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
    both = [g for g in played if g["spread_line"] is not None]
    out["spread_convention_check"] = {
        "n_with_spread": len(both),
        "mean_margin_minus_spread": round(sum(g["margin"] - g["spread_line"] for g in both) / len(both), 3),
        "home_cover_rate_excl_push": round(
            sum(1 for g in both if g["margin"] - g["spread_line"] > 0) /
            max(1, sum(1 for g in both if g["margin"] - g["spread_line"] != 0)), 4),
        "push_rate": round(sum(1 for g in both if g["margin"] - g["spread_line"] == 0) / len(both), 4),
        "share_home_favoured": round(sum(1 for g in both if g["spread_line"] > 0) / len(both), 4),
        "interpretation": ("nflverse DATASETS.md: positive spread_line = home team favoured (lines up with "
                           "result = home - away). Confirmed empirically: mean(home margin - spread_line) is ~0 and "
                           "the cover rate excluding pushes is ~50%."),
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
    s25 = derive_standings(games, 2025)
    out["season_2025_arithmetic"] = {
        "team_slots": sum(v["w"] + v["l"] + v["t"] for v in s25.values()),
        "games_played_times_two": 2 * sum(1 for g in games
                                         if g["season"] == 2025 and g["game_type"] == "REG" and g["played"]),
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
    with open(ATTESTATION, encoding="utf-8") as fh:
        att = json.load(fh)
    checks, modes = [], set()
    for season in (2025, 2026):
        local = os.path.join(DATA, "official", f"nfl_standings_{season}_REG.csv")
        out_csv = os.path.join(REPORTS, f"standings_check_{season}.csv")
        if os.path.exists(local):
            c = compare_live(games, season, local, out_csv)
        else:
            c = compare_attested(games, season, att, out_csv)
        if c:
            checks.append(c)
            modes.add(c["mode"])
    res["standings_checks"] = checks
    res["reproducible_offline"] = all(c["mode"] == "re-run locally" for c in checks)
    res["redistribution_policy"] = (
        "Official NFL values are NOT stored in this repository (F-10). Only derived values, match status, team codes "
        "of any mismatch, source URLs and the attestation date are published.")
    total_rows = sum(c["teams_compared"] for c in checks)
    total_match = sum(c["teams_match"] for c in checks)
    res["summary"] = {
        "official_rows_compared": total_rows,
        "official_rows_matching": total_match,
        "match_rate": round(total_match / total_rows, 4) if total_rows else None,
        "games_covered_by_verified_standings": sum(c["games_covered"] for c in checks),
        "verification_scope": ("team-aggregate reconciliation (W/L/T/PF/PA), NOT a per-game official verification (F-11)"),
        "modes": sorted(modes),
    }
    os.makedirs(REPORTS, exist_ok=True)
    with open(os.path.join(REPORTS, "verification.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)
    print(json.dumps(res["summary"], indent=1))
    for c in checks:
        print(c["season"], c["mode"], c["teams_match"], "/", c["teams_compared"],
              "mismatch:", c["mismatch_teams"], "missing:", c["missing_from_dataset"])
    ing = res["integrity"]
    print("rows", ing["n_rows"], "played", ing["n_played"], "dupes", len(ing["duplicate_game_ids"]))
    print("spread conv:", ing["spread_convention_check"])
    print("2025 arith:", ing["season_2025_arithmetic"])


if __name__ == "__main__":
    main()
