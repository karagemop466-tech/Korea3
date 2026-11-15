"""Fail-closed consistency check for injury_recheck. Exit 1 on any failure."""
import json, os, sys
ROOT = os.path.dirname(os.path.abspath(__file__))
d = json.load(open(os.path.join(ROOT, "data/week10_official.json")))
fails = []
clubs = d["clubs"]
codes = [c["club"] for c in clubs]
if len(codes) != 32 or len(set(codes)) != 32: fails.append(f"need 32 unique clubs, got {len(codes)}")
for c in clubs:
    if c["bye"] == (c["live_rows"] is not None): fails.append(f"{c['club']}: bye flag and table presence disagree")
    if not c["source"].startswith("https://www.nfl.com/"): fails.append(f"{c['club']}: source is not nfl.com")
    if c["bye"] and c["source"] != d["_meta"]["schedule_source"]: fails.append(f"{c['club']}: bye row must cite schedule")
byes = sorted(c["club"] for c in clubs if c["bye"])
if byes != ["CHI", "DEN", "PHI", "TB"]: fails.append(f"bye set is {byes}")
total = sum(c["live_rows"] for c in clubs if c["live_rows"] is not None)
if total != d["_meta"]["total_live_rows"]: fails.append(f"row total {total} != meta {d['_meta']['total_live_rows']}")
if len(d["games"]) != 14 or d["_meta"]["teams_playing"] != 28: fails.append("expected 14 games / 28 teams")
teams_in_games = sorted([g["away"] for g in d["games"]] + [g["home"] for g in d["games"]])
if sorted(teams_in_games + byes) != sorted(codes): fails.append("games + byes do not cover all 32 clubs exactly once")
diffs = {c["club"]: (c["repo_raw_rows"], c["live_rows"]) for c in clubs if not c["repo_matches_live"]}
expected = {"BAL": (8, 10)}  # known and recorded in README/flags; any other diff is a new failure
if diffs != expected: fails.append(f"repo-vs-live differences {diffs} != known {expected}")
if fails:
    print("FAIL"); [print(" -", f) for f in fails]; sys.exit(1)
print(f"PASS: 32 clubs; 28 with tables; {total} live rows; 14 games; byes {byes}; known repo diffs {diffs}")
