"""Unit tests for skill_lab (synthetic fixtures only — no repository data)."""
from __future__ import annotations

import math

import numpy as np
import pytest

from skill_recheck import core


# --------------------------------------------------------------------------- #
# Proper scores
# --------------------------------------------------------------------------- #
def test_brier_known_values():
    p = np.array([0.5, 0.9, 0.1])
    y = np.array([1.0, 1.0, 0.0])
    assert core.brier(p, y) == pytest.approx((0.25 + 0.01 + 0.01) / 3)
    assert core.brier(np.full(100, 0.5), np.array([1.0] * 50 + [0.0] * 50)) == pytest.approx(0.25)


def test_bss_identities():
    assert core.bss(0.2, 0.2) == pytest.approx(0.0)
    assert core.bss(0.1, 0.2) == pytest.approx(0.5)
    assert core.bss(0.2, 0.0) is None  # undefined benchmark
    assert core.bss(0.2, -0.1) is None


def test_favourite_prob_mapping():
    p = np.array([0.6, 0.4, 0.5])
    assert core.favourite_prob(p).tolist() == [0.6, 0.6, 0.5]


# --------------------------------------------------------------------------- #
# Bootstrap and multiplicity
# --------------------------------------------------------------------------- #
def test_bootstrap_deterministic_and_sane():
    rng = np.random.default_rng(7)
    n = 400
    y = (rng.random(n) < 0.5).astype(float)
    # a modest, honest forecaster with per-event confidence (non-degenerate loss)
    conf = 0.55 + 0.25 * rng.random(n)
    p_model = np.where(y == 1, conf, 1 - conf)
    p_bench = np.full(n, 0.5)
    keys = [int(i // 10) for i in range(n)]
    a = core.bootstrap_bss(p_model, p_bench, y, keys, n_boot=200, seed=11)
    b = core.bootstrap_bss(p_model, p_bench, y, keys, n_boot=200, seed=11)
    assert a["point"] == pytest.approx(b["point"])
    assert a["ci_low"] == pytest.approx(b["ci_low"])
    assert a["point"] > 0.1
    assert a["ci_low"] <= a["point"] <= a["ci_high"]
    lows = {round(core.bootstrap_bss(p_model, p_bench, y, keys, n_boot=200, seed=s)["ci_low"], 12)
            for s in (11, 12, 13)}
    assert len(lows) > 1  # different seeds draw different resamples


def test_bh_fdr_known_values():
    q = core.bh_fdr({"a": 0.01, "b": 0.02, "c": 0.04, "d": 1.0}, q=0.10)
    assert q["a"] == pytest.approx(0.04)
    assert q["b"] == pytest.approx(0.04)
    assert q["c"] == pytest.approx(4 / 3 * 0.04)  # step-up, not enforced down
    assert q["d"] == pytest.approx(1.0)
    assert core.bh_fdr({}) == {}


# --------------------------------------------------------------------------- #
# A16 field
# --------------------------------------------------------------------------- #
def test_change_mind_arithmetic():
    r = core.change_mind(0.02, 0.01, 100, -0.001)
    assert r["overturn_level"] == pytest.approx(0.01 * core.Z95)
    need = math.ceil((core.Z95 * 0.01 / 0.02) ** 2) - 100
    # the observed sample already clears the line: the field reports 0, never negative
    assert r["confirm_more_bets"] == max(need, 0)
    r2 = core.change_mind(-0.02, 0.01, 100, None)
    assert r2["confirm_more_bets"] is None  # no sample size clears a negative effect
    assert core.change_mind(None, None, 0, None)["overturn_level"] is None


# --------------------------------------------------------------------------- #
# Settlement and odds arithmetic
# --------------------------------------------------------------------------- #
def test_american_to_decimal_and_pnl():
    assert core.american_to_decimal(-110) == pytest.approx(1 + 100 / 110)
    assert core.american_to_decimal(0) == pytest.approx(2.0)  # even money
    assert core.american_to_decimal(150) == pytest.approx(2.5)
    assert core.pnl(-110, 1) == pytest.approx(100 / 110)
    assert core.pnl(-110, -1) == pytest.approx(-1.0)
    assert core.pnl(-110, 0) == 0.0
    assert core.pnl(150, 1) == pytest.approx(1.5)


def test_devig_sums_to_one():
    p1, p2 = core.devig_two_way(-110, -110)
    assert p1 + p2 == pytest.approx(1.0)
    assert p1 == pytest.approx(0.5)
    p1, p2 = core.devig_two_way(-150, 130)
    assert p1 + p2 == pytest.approx(1.0)
    assert 0 < p1 < 1


def test_clusters_of():
    keys = ["a", "b", "a", "c", "b", "a"]
    cs = core.clusters_of(keys)
    assert sorted(len(c) for c in cs) == [1, 2, 3]
    assert sorted(i for c in cs for i in c) == list(range(6))


def test_roi_ci_deterministic():
    rng = np.random.default_rng(3)
    pnls = rng.normal(-0.05, 0.5, 300)
    keys = [int(i // 3) for i in range(300)]
    a = core.roi_ci(pnls, keys, n_boot=100, seed=5)
    b = core.roi_ci(pnls, keys, n_boot=100, seed=5)
    assert a == b
    assert a["ci_low"] <= a["point"] <= a["ci_high"]
    assert a["point"] == pytest.approx(float(np.mean(pnls)))


# --------------------------------------------------------------------------- #
# Settlement rules (build.settle) on synthetic games
# --------------------------------------------------------------------------- #
def test_settle_moneyline_and_ties():
    from skill_recheck.build import settle
    g = {"home": "HOME", "away": "AWAY", "hs": 24, "as": 27}
    assert settle("MONEYLINE", "AWAY", None, g) == 1
    assert settle("MONEYLINE", "HOME", None, g) == 0
    g3 = {"home": "HOME", "away": "AWAY", "hs": 13, "as": 13}
    assert settle("MONEYLINE", "HOME", None, g3) == 2  # tie pushes
    assert settle("MONEYLINE", "AWAY", None, g3) == 2


def test_settle_spread():
    from skill_recheck.build import settle
    # home trails by 3: away won by 3
    g = {"home": "HOME", "away": "AWAY", "hs": 24, "as": 27}
    assert settle("SPREAD", "AWAY", 3.0, g) == 1   # +3, won by 3 -> covers by 6
    assert settle("SPREAD", "HOME", -3.0, g) == 0
    # home won by exactly 3 at -3 -> push
    g2 = {"home": "HOME", "away": "AWAY", "hs": 27, "as": 24}
    assert settle("SPREAD", "AWAY", 3.0, g2) == 2
    assert settle("SPREAD", "HOME", -3.0, g2) == 2
    assert settle("SPREAD", "HOME", -3.5, g2) == 0  # won by 3, laid 3.5 -> no cover
    assert settle("SPREAD", "AWAY", 3.5, g2) == 1   # lost by 3, got 3.5 -> covers


def test_settle_total():
    from skill_recheck.build import settle
    g = {"home": "HOME", "away": "AWAY", "hs": 27, "as": 24}
    assert settle("TOTAL", "Over", 51.0, g) == 2
    assert settle("TOTAL", "Under", 51.0, g) == 2
    assert settle("TOTAL", "Over", 50.0, g) == 1
    assert settle("TOTAL", "Under", 52.0, g) == 1
    assert settle("TOTAL", "Over", 52.0, g) == 0


# --------------------------------------------------------------------------- #
# Control metrics on synthetic events
# --------------------------------------------------------------------------- #
def _ev(home_wins: bool, p0: float = 0.6):
    return {
        "season": 2020, "week": 1,
        "side0": "HOME", "side1": "AWAY",
        "price0": -110.0, "price1": -110.0,
        "line0": -3.0, "line1": 3.0,
        "r0": 1 if home_wins else 0, "r1": 0 if home_wins else 1,
        "p0": p0, "p1": 1 - p0, "imputed": 1,
    }


def test_control_metrics_majority_synthetic():
    from skill_recheck import build
    evts = [_ev(True), _ev(False), _ev(True), _ev(True)]
    m = build.control_metrics(evts, "majority")  # p0 = 0.6 >= 0.4 -> always side0
    assert m["n_events"] == 4 and m["n_decided"] == 4 and m["wins"] == 3
    assert m["win_rate"] == pytest.approx(0.75)
    exp_roi = (3 * core.pnl(-110, 1) + core.pnl(-110, -1)) / 4
    assert m["roi"] == pytest.approx(round(exp_roi, 4))
    assert m["imputed_share"] == pytest.approx(1.0)
    # forecasts are the majority-side probability (0.6) on all four decided events
    assert m["bs"] == pytest.approx((0.16 + 0.36 + 0.16 + 0.16) / 4)
    assert m["bss_vs_coin"] == pytest.approx(1 - 0.21 / 0.25)


def test_control_metrics_random_deterministic():
    from skill_recheck import build
    evts = [_ev(True), _ev(False), _ev(True), _ev(True)]
    a = build.control_metrics(evts, "random")
    b = build.control_metrics(evts, "random")
    assert a["roi"] == b["roi"]  # same seed -> same picks
    assert a["bs"] == pytest.approx(0.25)  # forecast 0.5 on all decided events
    assert a["bss_vs_coin"] == pytest.approx(0.0)


def test_control_metrics_majority_by_line_for_universe_b():
    from skill_recheck import build
    evts = [_ev(True), _ev(False), _ev(True), _ev(True)]
    for e in evts:
        e["p0"] = None  # universe B: no odds, no de-vigged forecast
        e["p1"] = None
    m = build.control_metrics(evts, "majority")  # favourite by line0 < 0 -> side0
    assert m["wins"] == 3
    assert m["bs"] is None  # no forecast -> Brier column blank
    assert m["bss_vs_coin"] is None
