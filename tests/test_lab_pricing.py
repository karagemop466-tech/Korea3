import math
import pytest
from nfl_lab.pricing import (american_to_decimal, decimal_to_american, implied_probability,
                             remove_vig_two_way, fair_decimal, expected_roi, settle_single,
                             settle_moneyline, ParlayRule, settle_parlay, phi, phi_from_counts,
                             joint_from_phi, required_phi, frechet_bounds, parlay_ev_independent)
from nfl_lab.contracts import ContractError


def test_american_decimal_roundtrip():
    for a in [-110, -250, 100, 150, 300]:
        d = american_to_decimal(a)
        assert d > 1
        assert decimal_to_american(d) == pytest.approx(a)
    assert american_to_decimal(-110) == pytest.approx(1 + 100 / 110)
    assert implied_probability(-110) == pytest.approx(110 / 210)


def test_invalid_odds():
    for a in [0, 50, -50, float("nan")]:
        with pytest.raises(ContractError):
            american_to_decimal(a)
    with pytest.raises(ContractError):
        decimal_to_american(1)


def test_remove_vig():
    x, y = remove_vig_two_way(-110, -110)
    assert x == pytest.approx(0.5) and y == pytest.approx(0.5)
    with pytest.raises(ContractError):
        remove_vig_two_way(200, 200)


def test_fair_decimal_and_ev():
    assert fair_decimal(0.5) == pytest.approx(2)
    assert fair_decimal(0.5, p_push=0.1) == pytest.approx(1.8)
    assert expected_roi(0.5, -110) == pytest.approx(-1 / 22)
    assert expected_roi(0.5, 100) == pytest.approx(0)
    assert expected_roi(0.5, -110, p_push=0.2) == pytest.approx(0.5 * (100 / 110) - 0.3)


def test_settle_single():
    assert settle_single(24, 20, "over", -110)[0] == "win"
    assert settle_single(20, 20, "over", -110) == ("push", 0)
    assert settle_single(19, 20, "over", -110)[0] == "loss"
    assert settle_single(19, 20, "under", -110)[0] == "win"
    assert settle_single(24, 20, "home", -110, stake=2)[1] == pytest.approx(2 * 100 / 110)
    # home spread -3.5: margin 3 loses, margin 4 wins
    assert settle_single(3, -3.5, "home", -110)[0] == "loss"
    assert settle_single(4, -3.5, "home", -110)[0] == "win"


def test_moneyline():
    assert settle_moneyline(24, 20, 150)[0] == "win"
    assert settle_moneyline(20, 20, 150) == ("push", 0)
    assert settle_moneyline(20, 24, 150)[0] == "loss"
    with pytest.raises(ContractError):
        settle_moneyline(20, 20, 150, two_way=False)


def test_parlay_traditional():
    rule = ParlayRule("traditional", "drop", "drop", "test")
    legs = [("win", 1.9), ("win", 1.9)]
    result, profit, dec = settle_parlay(legs, rule)
    assert result == "win" and dec == pytest.approx(3.61) and profit == pytest.approx(2.61)
    result, profit, dec = settle_parlay([("win", 1.9), ("push", 1.9)], rule)
    assert result == "win" and dec == pytest.approx(1.9)
    result, profit, dec = settle_parlay([("push", 1.9), ("void", 1.9)], rule)
    assert result == "void" and profit == 0
    assert settle_parlay([("loss", 1.9), ("void", 1.9)], rule)[0] == "loss"


def test_parlay_sgp_explicit():
    rule = ParlayRule("sgp", "void_ticket", "drop", "test", min_remaining_legs=2)
    assert settle_parlay([("win", 1.9), ("push", 1.9)], rule)[0] == "void"
    rule2 = ParlayRule("sgp", "loss", "drop", "test", min_remaining_legs=2)
    assert settle_parlay([("win", 1.9), ("push", 1.9)], rule2)[0] == "loss"
    with pytest.raises(ContractError):
        settle_parlay([("win", 1.9)], rule)


def test_phi_and_joint():
    assert phi([1, 1, 0, 0], [1, 1, 0, 0]) == pytest.approx(1)
    assert phi([1, 1, 0, 0], [0, 0, 1, 1]) == pytest.approx(-1)
    assert phi([1, 0, 1, 0], [1, 1, 0, 0]) == pytest.approx(0)
    assert phi([1, 1], [1, 1]) is None
    assert phi_from_counts(10, 0, 0, 10) == pytest.approx(1)
    assert joint_from_phi(0.5, 0.5, 0) == pytest.approx(0.25)
    assert joint_from_phi(0.5, 0.5, 1) == pytest.approx(0.5)
    with pytest.raises(ContractError):
        joint_from_phi(0.9, 0.9, -1)
    assert required_phi(0.5, 0.5, 4) == pytest.approx(0)
    assert required_phi(0.5, 0.5, (21 / 11) ** 2) == pytest.approx(0.09752, abs=1e-4)
    assert frechet_bounds([0.5, 0.5]) == (0, 0.5)
    assert frechet_bounds([0.8, 0.8, 0.8]) == pytest.approx((0.4, 0.8))
    assert parlay_ev_independent([0.5, 0.5], [100, 100]) == pytest.approx(0)
