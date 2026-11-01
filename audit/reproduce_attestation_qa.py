#!/usr/bin/env python3
"""Synthetic regression checks against a pinned post-merge verifier snapshot.

No official standings or game data are loaded. The verifier is read from Git and
its output writer is stubbed, so this script does not modify the owner's files.
The first two checks confirm fixes to the earlier synthetic findings; the latter
checks reproduce stale attestation and summary behavior in this snapshot.
"""
from __future__ import annotations

import subprocess
import sys
import types

SNAPSHOT = "f968dcdddf6f7b94ab7b2d91b37c06f1dcd7b69e"
SOURCE_CONTEXT = "https://www.nfl.com/standings/division/2025/REG"


def load_snapshot():
    source = subprocess.check_output(
        ["git", "show", f"{SNAPSHOT}:pipeline/verify.py"], text=True
    )
    captured = []
    stub = types.ModuleType("lib_core")
    stub.DATA = "/synthetic/data"
    stub.REPORTS = "/synthetic/reports"
    stub.load_games = lambda: []
    stub.write_csv = lambda path, rows: captured.extend(rows)
    old = sys.modules.get("lib_core")
    sys.modules["lib_core"] = stub
    namespace = {"__name__": "independent_post_merge_qa"}
    try:
        exec(compile(source, f"{SNAPSHOT}:pipeline/verify.py", "exec"), namespace)
    finally:
        if old is None:
            del sys.modules["lib_core"]
        else:
            sys.modules["lib_core"] = old
    return namespace, captured


def official_row(w, loss, tie, pf, pa):
    return {"w": str(w), "l": str(loss), "t": str(tie), "pf": str(pf),
            "pa": str(pa), "source_url": SOURCE_CONTEXT}


def synthetic_game(home_score):
    return {"season": 2099, "game_type": "REG", "played": True,
            "home_team": "ARI", "away_team": "BUF",
            "home_score": home_score, "away_score": 0}


def main():
    mod, captured = load_snapshot()
    mod["load_official"] = lambda _: {
        "AZ": official_row(1, 0, 0, 7, 0),
        "BUF": official_row(0, 1, 0, 0, 7),
    }
    live = mod["compare_live"]([synthetic_game(7)], 2099, "unused", "/synthetic/out.csv")
    assert live["teams_match"] == 2
    assert not live["missing_from_dataset"] and not live["extra_in_dataset"]
    captured.clear()
    mod["load_official"] = lambda _: {"AZ": official_row(0, 0, 0, 0, 0)}
    missing = mod["compare_live"]([], 2099, "unused", "/synthetic/out.csv")
    assert missing["teams_match"] == 0
    assert captured[0]["status"] == "MISSING_FROM_DATASET"
    print("FIXED IN SNAPSHOT: normalized team sets and absent-zero-team handling")

    # The synthetic attestation represents a prior check of the 7–0 game.
    att = {"attested_on": "2099-01-01", "results": [{
        "season": 2099, "source_urls": [SOURCE_CONTEXT],
        "teams_compared": 2, "teams_match": 2, "mismatch_teams": [],
        "missing_from_dataset": [], "teams_compared_teams": ["ARI", "BUF"],
    }]}
    captured.clear()
    mod["compare_attested"]([synthetic_game(7)], 2099, att, "/synthetic/out.csv")
    original = {row["team"]: row for row in captured}
    assert original["ARI"]["pf_derived"] == 7
    assert original["ARI"]["status"] == "MATCH"

    # Change the current input without changing the earlier attestation.
    captured.clear()
    changed = mod["compare_attested"]([synthetic_game(70)], 2099, att, "/synthetic/out.csv")
    rows = {row["team"]: row for row in captured}
    assert rows["ARI"]["pf_derived"] == 70
    assert rows["ARI"]["status"] == "MATCH" and changed["teams_match"] == 2
    print("REPRODUCED: changed derived values inherit the old MATCH attestation")

    # The rows and the summary disagree if all attested teams disappear.
    captured.clear()
    absent = mod["compare_attested"]([], 2099, att, "/synthetic/out.csv")
    assert all(row["status"] == "MISSING_FROM_DATASET" for row in captured)
    assert absent["teams_match"] == absent["teams_compared"] == 2
    print("REPRODUCED: all teams missing but the summary still reports 2/2 matched")


if __name__ == "__main__":
    main()
