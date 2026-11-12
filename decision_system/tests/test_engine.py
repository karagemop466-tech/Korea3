"""Synthetic tests for the decision system.

They do not prove anything about the NFL.  They prove that the code does what its
docstring says on a fixture whose answer is known by construction, which is the only
way to catch a pipeline bug without network access to the real releases.

Run:  python3 -m pytest decision_system/tests -q
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from decision_system import injury_engine as ie
from decision_system import skill, strategies


# --------------------------------------------------------------------------- fixtures
def synthetic_injuries() -> pd.DataFrame:
    rows = []
    for week, status in ((1, ""), (2, "Out"), (3, "Questionable"), (4, "Doubtful")):
        rows.append({"season": 2024, "game_type": "REG", "week": week, "team": "AAA",
                     "full_name": "Alpha Player", "position": "WR", "report_status": status,
                     "practice_status": "Full Participation in Practice"})
    df = pd.DataFrame(rows)
    df["name_key"] = df["full_name"].map(ie.norm_name)
    return df


def synthetic_snaps() -> pd.DataFrame:
    rows = []
    # Alpha plays weeks 1-4; Beta is the backup who plays only when Alpha is out (week 2)
    for week in (1, 3, 4):
        rows.append({"season": 2024, "week": week, "game_type": "REG", "team": "AAA",
                     "player": "Alpha Player", "position": "WR", "offense_snaps": 40,
                     "defense_snaps": 0, "st_snaps": 0})
    rows.append({"season": 2024, "week": 2, "game_type": "REG", "team": "AAA",
                 "player": "Beta Player", "position": "WR", "offense_snaps": 35,
                 "defense_snaps": 0, "st_snaps": 0})
    df = pd.DataFrame(rows)
    df["name_key"] = df["player"].map(ie.norm_name)
    return df


def synthetic_games() -> pd.DataFrame:
    return pd.DataFrame([
        {"game_id": f"2024_0{w}_BBB_AAA", "season": 2024, "game_type": "REG", "week": w,
         "home_team": "AAA", "away_team": "BBB", "home_score": 20, "away_score": 17,
         "total": 37, "spread_line": -3.0, "total_line": 44.0,
         "home_moneyline": -150.0, "away_moneyline": 130.0}
        for w in (1, 2, 3, 4)
    ])


# ----------------------------------------------------------------------------- tests
def test_break_even_and_decimal_identities():
    assert skill.break_even_win_rate(-110) == pytest.approx(110 / 210)
    assert skill.decimal_odds(-110) == pytest.approx(21 / 11)
    assert skill.decimal_odds(100) == pytest.approx(2.0)
    assert skill.pnl_per_unit(-110, won=True) == pytest.approx(21 / 11 - 1)
    assert skill.pnl_per_unit(-110, won=False) == -1.0
    assert skill.pnl_per_unit(-110, won=False, push=True) == 0.0


def test_no_skill_band_is_centred_below_zero_at_minus_110():
    band = skill.no_skill_band(11, 600, n_sim=4000)
    # A zero-edge family at -110 loses the vig; the best of 11 should still not be
    # systematically profitable at a realistic bet count.
    assert band["break_even"] == pytest.approx(110 / 210)
    assert band["sim_p05_best"] < band["sim_p95_best"]
    assert -0.20 < band["sim_mean_best"] < 0.20


def test_no_skill_band_winner_gets_more_likely_as_k_grows():
    small = skill.no_skill_band(2, 500, n_sim=6000, seed=1)["sim_p95_best"]
    large = skill.no_skill_band(40, 500, n_sim=6000, seed=1)["sim_p95_best"]
    assert large > small


def test_deflated_sharpe_punishes_more_trials():
    rng = np.random.default_rng(3)
    r = rng.choice([0.909, -1.0], size=800, p=[0.53, 0.47])
    few = skill.deflated_sharpe(r, 2)["deflated"]
    many = skill.deflated_sharpe(r, 500)["deflated"]
    assert many < few


def test_bootstrap_ci_brackets_the_mean():
    rng = np.random.default_rng(11)
    x = rng.normal(0.02, 0.9, 1500)
    mean, lo, hi = skill.bootstrap_ci(x, n_boot=2000)
    assert lo < mean < hi
    assert abs(mean - x.mean()) < 1e-12


def test_block_bootstrap_returns_an_interval():
    df = pd.DataFrame({"season": [2020] * 50 + [2021] * 50 + [2022] * 50,
                       "pnl": list(np.linspace(-1, 1, 150))})
    lo, hi = skill.block_bootstrap_seasons(df, "pnl", n_boot=300)
    assert lo < hi


def test_audit_strategy_flags_a_coin_flip_as_no_reward():
    rng = np.random.default_rng(5)
    n = 400
    pnl = rng.choice([0.909, -1.0], size=n, p=[0.5, 0.5])
    bets = pd.DataFrame({"season": np.repeat(range(2018, 2026), n // 8),
                         "week": 1, "pnl": pnl, "price": -110.0, "outcome": (pnl > 0).astype(int)})
    rec = skill.audit_strategy(bets, "coin flip", "X1", n_trials=11, n_boot=1000)
    assert rec["reward_eligible"] is False
    assert rec["gates"]["L5_beats_no_skill_band"] is False


def test_parlay_math_break_even_phi():
    rec = strategies.parlay_math(phi=0.0, p=0.5, price=-110.0)
    assert rec["break_even_phi_at_minus110"] == pytest.approx(0.0975, abs=1e-3)
    pos = strategies.parlay_math(phi=0.5, p=0.5)
    assert pos["operator_margin_pct_at_this_phi"] < 0 < rec["operator_margin_pct_at_this_phi"]


def test_status_value_table_counts_participation():
    inj, snaps = synthetic_injuries(), synthetic_snaps()
    joined = ie.build_status_join(inj, snaps)
    table = {r["status"]: r for r in ie.status_value_table(joined)}
    out_row = next(v for k, v in table.items() if k.startswith("Out"))
    assert out_row["n"] == 1 and out_row["played"] == 0
    blank_row = next(v for k, v in table.items() if k.startswith("(blank"))
    assert blank_row["n"] == 1 and blank_row["played"] == 1
    q_row = next(v for k, v in table.items() if k.startswith("Questionable"))
    assert q_row["rate"] == pytest.approx(1.0)


def test_add_depth_string_ranks_the_real_snap_leader_first():
    depth = ie.add_depth_string(synthetic_snaps())
    assert "side" in depth.columns
    week1 = depth[(depth.week == 1) & (depth.side == "off")]
    assert len(week1) == 1 and int(week1.iloc[0]["rank"]) == 1
    week3 = depth[(depth.week == 3) & (depth.side == "off")]
    assert int(week3.iloc[0]["rank"]) == 1


def test_string_loss_table_does_not_invent_rows():
    inj, snaps, games = synthetic_injuries(), synthetic_snaps(), synthetic_games()
    depth = ie.add_depth_string(snaps)
    rows = ie.string_loss_table(inj, depth, games)
    # One Out row, and the player's most recent prior appearance is week 1 -> rank 1.
    string1 = [r for r in rows if r["side"] == "Offence" and r["string"] == 1]
    assert string1 and string1[0]["n"] == 1
    # The table must say it is not used rather than compute a CI on n=1.
    assert string1[0]["residual_mean"] is None


def test_team_game_side_residual_identity():
    g = synthetic_games()
    side = ie._team_game_side(g)
    home = side[(side.team == "AAA") & (side.week == 1)].iloc[0]
    assert home["residual"] == pytest.approx((20 - 17) + (-3.0))
    away = side[(side.team == "BBB") & (side.week == 1)].iloc[0]
    assert away["residual"] == pytest.approx((17 - 20) + (-3.0))


def test_depletion_effect_reports_a_row_per_term():
    rng = np.random.default_rng(7)
    games = synthetic_games()
    dep = pd.DataFrame({"season": 2024, "week": [1, 2, 3, 4], "team": "AAA",
                        "out_share_off": [0.0, 0.5, 0.1, 0.2],
                        "out_share_def": [0.0, 0.0, 0.3, 0.1],
                        "q_share_off": [0.1] * 4, "q_share_def": [0.0] * 4})
    assert ie.depletion_effect(dep, games) == []  # fewer than 200 rows: refused, not faked


def test_suggestion_register_refuses_approval():
    from decision_system.suggestions import Suggestion, CRITERIA
    score = {c: 3 for c in CRITERIA}
    with pytest.raises(ValueError):
        Suggestion("X", "t", "P1", "p", "x", "g", ("K01",), score, status="approved")


def test_knowledge_blank_must_be_flagged():
    from decision_system.knowledge import Fact
    with pytest.raises(ValueError):
        Fact("KX", "q", "blank", "", "why")
    with pytest.raises(ValueError):
        Fact("KY", "q", "blank", "a value", "why", flag="DS-F01")


def test_cell_never_renders_none_or_nan():
    from decision_system.render import cell
    assert cell(None) == "&mdash;"
    assert cell(float("nan")) == "&mdash;"
    assert cell(1.23456, 2) == "1.23"
    assert cell([0.1, 0.2], 3) == "0.1, 0.2"
    assert cell(1639) == "1,639"


def test_table_refuses_a_none_cell():
    from decision_system.render import table
    ok = "https://www.nfl.com/"
    with pytest.raises(ValueError):
        table("t", ["a", "src"], [[None, ok]])
    with pytest.raises(ValueError):
        table("t", ["a", "src"], [["None", ok]])
    table("t", ["a", "src"], [["—", ok]])   # the em dash is allowed
