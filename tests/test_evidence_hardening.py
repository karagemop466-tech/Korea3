"""Synthetic adversarial tests for the hardened evidence chain.

These fixtures are not NFL observations and are never written to verified/data.
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, replace
from datetime import datetime, timedelta, timezone

import pytest

from nfl_lab.contracts import ContractError, Evidence, Forecast, Game, Quote, SettledBet
from nfl_lab.evidence import (BASELINE_METHOD, BET_FIELDS, GAME_FIELDS, QUOTE_FIELDS,
                              EvidenceRegistry, InputBundle, audit_bundle, canonical_bytes,
                              official_publisher)
from nfl_lab.validation import (Protocol, ProtocolFreeze, cluster_bootstrap_ratio,
                                evaluate_family, evaluate_strategy, leaderboard)

KICKOFF = datetime(2013, 9, 8, 18, tzinfo=timezone.utc)


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def digest(b):
    return hashlib.sha256(b).hexdigest()


def rec(eid, url, kind, fields, payload, operator=None, **kwargs):
    licence = b"synthetic-licence"
    publisher = official_publisher(url)
    licence_ref = "https://www.nfl.com/legal/terms/" if publisher == "nfl.com" else "https://sportsbook.draftkings.com/help/general-betting-rules/market-rules"
    r = Evidence(eid, url, publisher, "synthetic claim", "2026-11-02T00:00:00Z", "synthetic",
                 rights="licensed", content_sha256=digest(payload), fields=tuple(fields), kind=kind,
                 review_status="verified", operator=operator, rights_scope=(kind,),
                 license_ref=licence_ref, license_sha256=digest(licence), **kwargs)
    return r, payload, licence


def attach(reg, record, payload, licence):
    reg.add(record)
    reg.register_artifact(record.content_sha256, payload)
    reg.register_artifact(record.license_sha256, licence)


def forecast_with_artifact(**kwargs):
    f0 = Forecast(**kwargs)
    payload = canonical_bytes({k: v for k, v in asdict(f0).items() if k != "artifact_sha256"})
    f = replace(f0, artifact_sha256=digest(payload))
    return f, payload


def make_chain():
    reg = EvidenceRegistry()
    game = Game("g1", 2013, 1, iso(KICKOFF), "T0", "T1", 24, 20, "ge", "https://www.nfl.com/synthetic/g1",
                status="final", result_available_at=iso(KICKOFF + timedelta(hours=4)))
    attach(reg, *rec("ge", game.source_url, "game_result", GAME_FIELDS, b"synthetic-game"))
    rules, rp, rl = rec("rules", "https://sportsbook.draftkings.com/help/sport-rules/football", "settlement_rules",
                        {"settlement_rules"}, b"synthetic-rules", operator="draftkings.com",
                        jurisdictions=("US-NJ",), markets=("spread", "total", "moneyline", "player_prop", "parlay"),
                        effective_from="2013-01-01T00:00:00Z", effective_until="2014-01-01T00:00:00Z", version="synthetic-v1",
                        parlay_kind="traditional", push_action="drop", void_action="drop", min_remaining_legs=1,
                        below_min_action="void_ticket", player_nonparticipation_action="void")
    attach(reg, rules, rp, rl)
    observed = iso(KICKOFF - timedelta(hours=1))
    qh = Quote("qh", "g1", "spread", "home", -3.5, -110, observed, iso(KICKOFF), "draftkings.com", "qhe",
               "https://sportsbook.draftkings.com/synthetic/qh", "rules", executable=True, jurisdiction="US-NJ")
    qa = Quote("qa", "g1", "spread", "away", 3.5, -110, observed, iso(KICKOFF), "draftkings.com", "qae",
               "https://sportsbook.draftkings.com/synthetic/qa", "rules", executable=True, jurisdiction="US-NJ")
    attach(reg, *rec("qhe", qh.source_url, "quote", QUOTE_FIELDS, b"synthetic-quote-home", operator="draftkings.com", jurisdictions=("US-NJ",), markets=("spread",)))
    attach(reg, *rec("qae", qa.source_url, "quote", QUOTE_FIELDS, b"synthetic-quote-away", operator="draftkings.com", jurisdictions=("US-NJ",), markets=("spread",)))
    f, fp = forecast_with_artifact(
        strategy_id="A", event_id="g1", market="spread", selection="home", p_win=0.55, p_push=0.0, p_void=0.0,
        issued_at=iso(KICKOFF - timedelta(minutes=55)), kickoff=iso(KICKOFF), model_version="v1",
        features_available_at=iso(KICKOFF - timedelta(hours=2)), baseline_id="market", baseline_p_win=0.5,
        forecast_id="f1", line=-3.5, code_commit="synthetic-commit", feature_snapshot_sha256=digest(b"features"),
        baseline_quote_id="qh", opposite_quote_id="qa", baseline_method=BASELINE_METHOD)
    reg.register_forecast_artifact(f.artifact_sha256, fp)
    profit = 100 / 110
    bet = SettledBet("b1", "A", "g1", "2013-01", iso(KICKOFF), 1.0, profit, "win", "qh", "be",
                     "https://sportsbook.draftkings.com/synthetic/b1", "rules", forecast_id="f1", selection="home",
                     line=-3.5, operator="draftkings.com", jurisdiction="US-NJ",
                     accepted_at=iso(KICKOFF - timedelta(minutes=50)), accepted_american=-110,
                     settled_at=iso(KICKOFF + timedelta(hours=5)))
    attach(reg, *rec("be", bet.source_url, "settlement", BET_FIELDS, b"synthetic-settlement", operator="draftkings.com", jurisdictions=("US-NJ",), markets=("spread",)))
    bundle = InputBundle(games=[game], quotes=[qh, qa], bets=[bet], forecasts=[f])
    return reg, bundle


def test_full_synthetic_chain_admits():
    reg, bundle = make_chain()
    out = audit_bundle(reg, bundle)
    assert out["errors"] == []
    assert {k: len(v) for k, v in out["admitted"].items()} == {"games": 1, "quotes": 2, "bets": 1, "forecasts": 1, "player_games": 0}


def test_wrong_publisher_rules_rejected():
    reg, bundle = make_chain()
    wrong, payload, licence = rec("rules", "https://www.nfl.com/synthetic/rules", "settlement_rules", {"settlement_rules"},
                                  b"wrong", operator="draftkings.com", jurisdictions=("US-NJ",), markets=("spread",),
                                  effective_from="2013-01-01T00:00:00Z", effective_until="2014-01-01T00:00:00Z", version="v1")
    reg.records["rules"] = wrong
    reg.register_artifact(wrong.content_sha256, payload)
    reg.register_artifact(wrong.license_sha256, licence)
    with pytest.raises(ContractError, match="publisher"):
        audit_bundle(reg, bundle)
        reg.audit_quote(bundle.quotes[0])


def test_link_only_rules_rejected():
    reg, bundle = make_chain()
    old = reg.records["rules"]
    link_only = Evidence("rules", old.url, "draftkings.com", "synthetic", "2026-11-02T00:00:00Z", "synthetic",
                         kind="settlement_rules", review_status="verified", operator="draftkings.com",
                         jurisdictions=("US-NJ",), markets=("spread",), effective_from="2013-01-01T00:00:00Z",
                         effective_until="2014-01-01T00:00:00Z", version="v1")
    reg.records["rules"] = link_only
    with pytest.raises(ContractError):
        reg.audit_quote(bundle.quotes[0])


def test_missing_source_artifact_rejected():
    reg, bundle = make_chain()
    reg.artifacts.pop(reg.records["ge"].content_sha256)
    with pytest.raises(ContractError, match="artifact"):
        reg.audit_game(bundle.games[0])


def test_settlement_requires_resolved_quote_and_matching_price():
    reg, bundle = make_chain()
    games, quotes, players, forecasts = bundle.indexes()
    with pytest.raises(ContractError, match="quote_id"):
        reg.audit_bet(replace(bundle.bets[0], quote_id="missing"), quotes, games, players, forecasts)
    with pytest.raises(ContractError, match="price"):
        reg.audit_bet(replace(bundle.bets[0], accepted_american=100), quotes, games, players, forecasts)
    with pytest.raises(ContractError, match="profit"):
        reg.audit_bet(replace(bundle.bets[0], profit=99.0), quotes, games, players, forecasts)


def test_forecast_identity_and_artifact_are_bound():
    reg, bundle = make_chain()
    games, quotes, players, forecasts = bundle.indexes()
    with pytest.raises(ContractError, match="forecast_id"):
        reg.audit_bet(replace(bundle.bets[0], forecast_id="other"), quotes, games, players, forecasts)
    reg.forecast_artifacts.pop(bundle.forecasts[0].artifact_sha256)
    with pytest.raises(ContractError, match="artifact"):
        reg.audit_bet(bundle.bets[0], quotes, games, players, forecasts)


def test_external_execution_boolean_and_pvalues_are_not_accepted():
    protocol = Protocol("p", ("A",), (2010,), (2011,), (2013,), (2014,), min_holdout_bets=2, min_holdout_clusters=2, min_holdout_seasons=1, bootstrap_replicates=100)
    with pytest.raises(TypeError):
        evaluate_strategy("A", [], [], protocol, EvidenceRegistry(), executable_quotes_verified=True)
    with pytest.raises(TypeError):
        evaluate_strategy("A", [], [], protocol, EvidenceRegistry(), family_pvalues={"A": 0.0})


def test_family_multiplicity_is_computed_internally():
    reg, bundle = make_chain()
    protocol = Protocol("p", ("A", "B"), (2010,), (2011,), (2013,), (2014,), min_holdout_bets=2, min_holdout_clusters=2, min_holdout_seasons=1, bootstrap_replicates=100)
    freeze = ProtocolFreeze(protocol.digest(), "2013-01-01T00:00:00Z", ("A", "B"), ("v1",), BASELINE_METHOD, "synthetic")
    reports = evaluate_family(protocol, reg, bundle, freeze)
    assert len(reports) == 2
    assert all("bonferroni_p" in r.metrics for r in reports)
    assert not any(r.eligible for r in reports)


def test_stake_weighted_ratio_not_mean_of_bets():
    ci = cluster_bootstrap_ratio([1.0, -2.0], [1.0, 100.0], ["a", "b"], replicates=100)
    assert ci["mean"] == pytest.approx(-1.0 / 101.0, abs=1e-9)


def test_rewards_remain_disabled():
    with pytest.raises(ContractError):
        leaderboard([], reward_pool=1.0)
