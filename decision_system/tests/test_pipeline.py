"""End-to-end test of the decision system on real-shaped CSVs.

The fixture files use the exact column names of the pinned nflverse releases, so this
test exercises the loaders, the joins, the regression and the build — the parts that
cannot be tested against the live releases from this sandbox.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from decision_system import injury_engine as ie


@pytest.fixture()
def lab(tmp_path, monkeypatch) -> Path:
    """A miniature data/injury_lab with nflverse column names."""
    lab = tmp_path / "injury_lab"
    (lab / "injuries").mkdir(parents=True)
    (lab / "snap_counts").mkdir(parents=True)

    inj_by_season: dict[int, list[dict]] = {}
    snaps_by_season: dict[int, list[dict]] = {}
    teams = ["AAA", "BBB", "CCC", "DDD"]
    for season in (2024, 2025):
        inj_by_season[season], snaps_by_season[season] = [], []
        for week in range(1, 6):
            for t in teams:
                # one starter and one backup per team and week
                for i, (name, off) in enumerate([(f"{t} Starter", 50), (f"{t} Backup", 20)]):
                    status = "Out" if (i == 0 and week % 3 == 0) else (
                        "Questionable" if (i == 1 and week % 4 == 0) else "")
                    if status != "Out":      # a player declared Out records no snaps
                        snaps_by_season[season].append({
                            "game_id": f"{season}_{week:02d}_XXX_{t}", "season": season,
                            "game_type": "REG", "week": week, "player": name,
                            "position": "WR", "team": t, "opponent": "XXX",
                            "offense_snaps": off, "offense_pct": off / 70,
                            "defense_snaps": 0, "defense_pct": 0, "st_snaps": 0, "st_pct": 0})
                    inj_by_season[season].append({
                        "season": season, "game_type": "REG", "season_type": "REG", "team": t,
                        "week": week, "gsis_id": f"00-{season}{week}{t}{i}", "position": "WR",
                        "full_name": name, "first_name": name.split()[0],
                        "last_name": name.split()[1],
                        "report_primary_injury": "Knee" if status else "",
                        "report_secondary_injury": "", "report_status": status,
                        "practice_primary_injury": "", "practice_secondary_injury": "",
                        "practice_status": ("Did Not Participate In Practice" if status == "Out"
                                            else "Full Participation in Practice")})
    for season in (2024, 2025):
        pd.DataFrame(inj_by_season[season]).to_csv(
            lab / "injuries" / f"injuries_{season}.csv", index=False)
        pd.DataFrame(snaps_by_season[season]).to_csv(
            lab / "snap_counts" / f"snap_counts_{season}.csv", index=False)
    monkeypatch.setattr(ie, "LAB", lab)
    return lab


def test_loaders_accept_the_real_schema(lab):
    inj = ie.load_injuries()
    snaps = ie.load_snaps()
    assert len(inj) == 2 * 5 * 4 * 2          # every report row is kept
    assert len(snaps) == 2 * (5 * 4 * 2 - 4)  # minus the four "Out" starters
    assert set(inj["report_status"]) == {"", "Out", "Questionable"}
    assert snaps["offense_snaps"].max() == 50


def test_status_join_produces_a_rate_for_every_status(lab):
    inj, snaps = ie.load_injuries(), ie.load_snaps()
    joined = ie.build_status_join(inj, snaps)
    table = ie.status_value_table(joined)
    out_row = next(r for r in table if r["status"] == "Out")
    assert out_row["n"] > 0
    assert out_row["rate"] == 0.0           # a player declared Out records no snaps
    blank_row = next(r for r in table if r["status"].startswith("(blank"))
    assert blank_row["rate"] > 0.9         # a blank status is almost always a participant


def test_string_loss_and_depletion_run_end_to_end(lab):
    inj, snaps = ie.load_injuries(), ie.load_snaps()
    depth = ie.add_depth_string(snaps)
    assert not depth.empty and depth["rank"].min() == 1
    games = pd.DataFrame([
        {"game_id": f"2024_0{w}_XXX_AAA", "season": 2024, "game_type": "REG", "week": w,
         "home_team": "AAA", "away_team": "XXX", "home_score": 20 + w, "away_score": 17,
         "total": 37 + w, "spread_line": -3.0, "total_line": 44.0,
         "home_moneyline": -150.0, "away_moneyline": 130.0} for w in range(1, 6)
    ] + [
        {"game_id": f"2025_0{w}_XXX_AAA", "season": 2025, "game_type": "REG", "week": w,
         "home_team": "AAA", "away_team": "XXX", "home_score": 20 + w, "away_score": 17,
         "total": 37 + w, "spread_line": -3.0, "total_line": 44.0,
         "home_moneyline": -150.0, "away_moneyline": 130.0} for w in range(1, 6)
    ])
    rows = ie.string_loss_table(inj, depth, games)
    assert rows and all("n" in r for r in rows)
    dep = ie.depletion_index(inj, snaps)
    assert not dep.empty and "out_share_off" in dep.columns
    # fewer than 200 team-weeks -> the regression refuses to publish coefficients
    assert ie.depletion_effect(dep, games) == []


def test_run_writes_a_result_file_and_reports_coverage(lab, monkeypatch):
    monkeypatch.setattr(ie, "load_depth_current", lambda: pd.DataFrame())
    res = ie.run()
    assert res["coverage"]["injury_rows"] > 0
    assert res["status_value"] and res["practice_value"]
    assert (lab / "injury_results.json").exists()
    blob = json.loads((lab / "injury_results.json").read_text())
    assert blob["coverage"]["injury_seasons"] == [2024, 2025]
