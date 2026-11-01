#!/usr/bin/env python3
"""Reproduce two QA findings in a pinned, unmerged parallel-session snapshot.

Uses intentionally synthetic games only; they are not NFL data or betting results.
The other session's module is loaded from Git into memory and is never modified.
Run from the repository root after the snapshot commit has been fetched:
    python3 audit/reproduce_standings_qa.py
A successful run means the issues were reproduced in this snapshot, not fixed.
"""
from __future__ import annotations

import subprocess
import sys
import types

SNAPSHOT = "99832574a9e603081c08d175a2bd4f35b114ddb7"
OFFICIAL_CONTEXT = "https://www.nfl.com/standings/division/2025/REG"


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
    previous = sys.modules.get("lib_core")
    sys.modules["lib_core"] = stub
    namespace = {"__name__": "independent_qa"}
    try:
        exec(compile(source, f"{SNAPSHOT}:pipeline/verify.py", "exec"), namespace)
    finally:
        if previous is None:
            del sys.modules["lib_core"]
        else:
            sys.modules["lib_core"] = previous
    return namespace, captured


def official_row(w, loss, tie, pf, pa):
    return {"w": str(w), "l": str(loss), "t": str(tie), "pf": str(pf),
            "pa": str(pa), "source_url": OFFICIAL_CONTEXT}


def main():
    mod, captured = load_snapshot()
    # Synthetic names and values, solely to exercise code paths.
    game = {"season": 2099, "game_type": "REG", "played": True,
            "home_team": "ARI", "away_team": "BUF", "home_score": 7, "away_score": 0}
    official = {"AZ": official_row(1, 0, 0, 7, 0),
                "BUF": official_row(0, 1, 0, 0, 7)}
    mod["load_official"] = lambda _: official
    result = mod["compare"]([game], 2099, "unused", "/synthetic/out.csv")
    assert result["teams_match"] == 2
    assert result["teams_missing_from_dataset"] == ["AZ"]
    assert result["teams_extra_in_dataset"] == ["ARI"]
    print("REPRODUCED: mapped team matches but raw-set summary reports false missing/extra codes")

    captured.clear()
    mod["load_official"] = lambda _: {"AZ": official_row(0, 0, 0, 0, 0)}
    missing = mod["compare"]([], 2099, "unused", "/synthetic/out.csv")
    assert missing["teams_match"] == 1 and captured[0]["status"] == "MATCH"
    assert missing["teams_missing_from_dataset"] == ["AZ"]
    print("REPRODUCED: absent zero-valued team can be labeled MATCH instead of UNVERIFIED")


if __name__ == "__main__":
    main()
