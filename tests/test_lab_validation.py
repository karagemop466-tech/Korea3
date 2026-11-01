import pytest
from nfl_lab.validation import (Protocol, brier, log_loss, calibration_bins, cluster_bootstrap_mean,
                                cluster_sign_permutation, bonferroni, benjamini_hochberg,
                                max_drawdown, evaluate_strategy, leaderboard)
from nfl_lab.contracts import ContractError, SettledBet, Forecast
from nfl_lab.evidence import EvidenceRegistry


def make_protocol():
    return Protocol("test", ("A", "B"), (2010, 2011), (2012,), (2013, 2014, 2015), (2016,),
                    min_holdout_bets=4, min_holdout_clusters=2, min_holdout_seasons=2,
                    min_forward_bets=2, bootstrap_replicates=200)


def test_scores():
    assert brier([0.5, 0.5], [1, 0]) == 0.25
    assert brier([1, 0], [1, 0]) == 0
    assert log_loss([0.5], [1]) == pytest.approx(0.693147, abs=1e-5)
    with pytest.raises(ContractError):
        brier([0.5], [0.5])
    bins = calibration_bins([0.1, 0.9], [0, 1], bins=2)
    assert bins[0]["n"] == 1 and bins[1]["observed_rate"] == 1


def test_cluster_bootstrap_and_permutation():
    values = [1, 1, -1, -1, 1, 1]
    clusters = ["a", "a", "b", "b", "c", "c"]
    ci = cluster_bootstrap_mean(values, clusters, replicates=200)
    assert ci["clusters"] == 3 and ci["mean"] == pytest.approx(1 / 3)
    p = cluster_sign_permutation(values, clusters, replicates=200)
    assert 0 < p <= 1
    with pytest.raises(ContractError):
        cluster_bootstrap_mean([1], ["a"], replicates=200)


def test_multiplicity():
    assert bonferroni([0.01, 0.02]) == [0.02, 0.04]
    q = benjamini_hochberg([0.01, 0.04, 0.03])
    assert q[0] <= q[2] <= q[1]
    assert max_drawdown([1, -2, 3, -1]) == 2


def test_empty_strategy_is_blocked_not_passed():
    protocol = make_protocol()
    report = evaluate_strategy("A", [], [], protocol, EvidenceRegistry(), protocol_frozen_digest=protocol.digest())
    assert not report.eligible
    assert report.score is None
    assert any(g.status == "blocked" for g in report.gates)
    assert not any(g.status == "pass" and g.name == "economics" for g in report.gates)


def test_unregistered_strategy_rejected():
    protocol = make_protocol()
    with pytest.raises(ContractError):
        evaluate_strategy("C", [], [], protocol, EvidenceRegistry())


def test_leaderboard_no_eligible_no_rewards():
    protocol = make_protocol()
    reports = [evaluate_strategy(s, [], [], protocol, EvidenceRegistry()) for s in ("A", "B")]
    board = leaderboard(reports, reward_pool=1000)
    assert all(r["rank"] is None and r["reward"] is None and r["status"] == "not_eligible" for r in board)


def test_protocol_overlap_rejected():
    with pytest.raises(ContractError):
        Protocol("bad", ("A",), (2010,), (2010,), (2011,), (2012,))
