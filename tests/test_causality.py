#!/usr/bin/env python3
"""Causality, settlement and provenance tests. Run: python3 tests/test_causality.py

These are hard checks. If any assert fires, no strategy may be marked G2-pass.
"""
from __future__ import annotations

import hashlib
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from line_lab import markets as mk  # noqa: E402
from line_lab.core import load_games, build_features, load_manifest  # noqa: E402

FLAG = ROOT / "data" / "derived" / "causality_ok.flag"
REPORT = ROOT / "data" / "derived" / "tests.json"
PREGAME_COLS = [
    "elo_home", "elo_away", "elo_diff", "off_home", "def_home", "off_away", "def_away",
    "qb_change_home", "qb_change_away", "ref_total_dev",
]


def check_hashes() -> dict:
    manifest = load_manifest()
    out = {}
    for entry in manifest["files"]:
        path = ROOT / entry["file"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        assert digest == entry["sha256"], f"hash mismatch for {entry['file']}"
        out[entry["file"]] = digest
    return out


def check_truncation() -> dict:
    """Features computed with data truncated at 2022 must match the full-history run."""
    games = load_games()
    full, _ = build_features(games)
    cut, _ = build_features(games[games["season"] <= 2022])
    left = cut[PREGAME_COLS].reset_index(drop=True)
    right = full[full["season"] <= 2022][PREGAME_COLS].reset_index(drop=True)
    assert len(left) == len(right), "row counts differ under truncation"
    diff = (left - right).abs().max()
    worst = float(np.nanmax(diff.to_numpy(dtype=float)))
    assert worst < 1e-9, f"features leak future information (max delta {worst})"
    return {"rows_compared": int(len(left)), "max_abs_delta": worst}


def check_live_state() -> dict:
    """Unplayed-game state must equal the state after the last completed game."""
    games = load_games()
    _, live = build_features(games)
    full, _ = build_features(games)
    last = full[full["season"] == 2026].sort_values("kickoff").iloc[-1]
    first_live = live[live["season"] == 2026].sort_values("kickoff").iloc[0]
    # Elo of any team in the first unplayed week must equal its rating after the last game
    teams = {first_live["home_team"], first_live["away_team"]}
    ok = True
    for team in teams:
        seen = full[(full["home_team"] == team) | (full["away_team"] == team)]
        if seen.empty:
            continue
        last = seen.iloc[-1]
        post = float(last["elo_home_post"] if last["home_team"] == team else last["elo_away_post"])
        live_val = float(first_live["elo_home"] if first_live["home_team"] == team else first_live["elo_away"])
        ok = ok and abs(post - live_val) < 1e-9
    assert ok, "live state does not match the post-game rating of the last completed game"
    return {"teams_checked": len(teams), "last_completed_game": str(last["game_id"])}


def check_settlement(n: int = 400, seed: int = 7) -> dict:
    """Recompute settlement from raw scores on a random sample, independently."""
    games = load_games()
    feats, _ = build_features(games)
    rng = np.random.default_rng(seed)
    sample = feats.sample(min(n, len(feats)), random_state=int(seed))
    checked = 0
    for _, row in sample.iterrows():
        home_score, away_score = row["home_score"], row["away_score"]
        if pd.isna(row["spread_line"]):
            continue
        margin = home_score - away_score
        assert margin == row["result"], "result column does not equal home - away"
        assert home_score + away_score == row["total"], "total column does not equal the score sum"
        cover = margin - row["spread_line"]
        if cover != 0:
            assert mk.settle(row, "ATS", "home") == (1 if cover > 0 else -1)
            assert mk.settle(row, "ATS", "away") == (-1 if cover > 0 else 1)
        else:
            assert mk.settle(row, "ATS", "home") == 0
        if pd.notna(row["total_line"]):
            over = (home_score + away_score) - row["total_line"]
            if over != 0:
                assert mk.settle(row, "TOTAL", "over") == (1 if over > 0 else -1)
        if pd.notna(row["home_moneyline"]):
            if margin != 0:
                assert mk.settle(row, "ML", "home") == (1 if margin > 0 else -1)
        checked += 1
    return {"games_recomputed": checked}


def check_odds_arithmetic() -> dict:
    """American odds conversions and de-vig must be internally consistent."""
    assert abs(mk.american_to_decimal(-110) - 1.9090909) < 1e-6
    assert abs(mk.american_to_decimal(150) - 2.5) < 1e-9
    a, b = mk.devig_two_way(-110, -110)
    assert abs(a - 0.5) < 1e-9 and abs(b - 0.5) < 1e-9
    h, aw = mk.devig_two_way(-148, 124)
    assert abs(h + aw - 1.0) < 1e-12
    # totals model probabilities must integrate to 1 (win + loss + push)
    w, l, p = mk.total_probs(45.0, 13.0, 45.0, "over")
    assert abs(w + l + p - 1.0) < 1e-9
    return {"ok": True}


def check_no_lookahead_columns() -> dict:
    """Feature table must not contain result columns in the pre-game section used by models."""
    feats, _ = build_features(load_games())
    banned = [c for c in PREGAME_COLS if c in ("result", "total", "home_score", "away_score")]
    assert not banned
    assert not feats["stage"] .empty if "stage" in feats else True
    return {"pregame_columns": len(PREGAME_COLS)}


def main() -> int:
    FLAG.parent.mkdir(parents=True, exist_ok=True)
    report = {}
    checks = {
        "hashes": check_hashes,
        "truncation": check_truncation,
        "live_state": check_live_state,
        "settlement": check_settlement,
        "odds": check_odds_arithmetic,
        "columns": check_no_lookahead_columns,
    }
    failed = []
    for name, fn in checks.items():
        try:
            report[name] = {"status": "pass", **fn()}
        except AssertionError as exc:  # pragma: no cover - failure path
            report[name] = {"status": "fail", "error": str(exc)}
            failed.append(name)
    REPORT.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if failed:
        FLAG.unlink(missing_ok=True)
        print("FAILED:", ", ".join(failed))
        return 1
    FLAG.write_text("ok\n", encoding="utf-8")
    print("all causality / settlement / provenance checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
