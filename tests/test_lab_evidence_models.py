import hashlib
from datetime import datetime, timedelta, timezone

import numpy as np
import pytest

from nfl_lab.contracts import ContractError, Evidence, Forecast, Game, Quote
from nfl_lab.evidence import EvidenceRegistry, official_publisher
from nfl_lab.models import PlayerGame, PlayerPropModel, TeamLineModel, joint_from_scenarios


def iso(dt):
    return dt.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def licensed_record(eid, url, kind, fields, content, operator=None, **kwargs):
    digest = hashlib.sha256(content).hexdigest()
    licence = b"synthetic-licence-artifact"
    licence_digest = hashlib.sha256(licence).hexdigest()
    publisher = official_publisher(url)
    licence_ref = "https://www.nfl.com/legal/terms/" if publisher == "nfl.com" else "https://sportsbook.draftkings.com/help/general-betting-rules/market-rules"
    rec = Evidence(eid, url, publisher, "synthetic claim", "2026-11-02T00:00:00Z", "synthetic fixture",
                   rights="licensed", content_sha256=digest, fields=tuple(fields), kind=kind,
                   review_status="verified", operator=operator, rights_scope=(kind,),
                   license_ref=licence_ref, license_sha256=licence_digest, **kwargs)
    return rec, content, licence


def test_official_publisher_allowlist():
    assert official_publisher("https://www.nfl.com/legal/terms/") == "nfl.com"
    assert official_publisher("https://support.draftkings.com/dk/en-us/x") == "draftkings.com"
    assert official_publisher("https://www.itl.nist.gov/x") == "nist.gov"
    assert official_publisher("https://eutils.ncbi.nlm.nih.gov/x") == "nih.gov"
    assert official_publisher("https://nfl.com.example.com/x") is None
    assert official_publisher("http://www.nfl.com/x") is None
    assert official_publisher("https://github.com/nflverse/nfldata") is None


def test_link_only_evidence_cannot_admit_stored_data():
    rec = Evidence("e1", "https://www.nfl.com/legal/terms/", "NFL", "claim", "2026-11-01T00:00:00Z", "read", review_status="verified")
    reg = EvidenceRegistry([rec])
    with pytest.raises(ContractError):
        reg.require("e1", rec.url, require_rights=True)
    assert reg.require("e1", rec.url, require_rights=False).evidence_id == "e1"


def test_licensed_evidence_hash_required():
    content = b"synthetic"
    rec, payload, licence = licensed_record("e2", "https://www.nfl.com/stats/player-stats/", "game_result", {"game_result"}, content)
    reg = EvidenceRegistry([rec])
    reg.register_artifact(rec.content_sha256, payload)
    reg.register_artifact(rec.license_sha256, licence)
    reg.require("e2", rec.url, "game_result", content=content, kind="game_result")
    with pytest.raises(ContractError):
        reg.require("e2", rec.url, "game_result", content=b"changed", kind="game_result")
    with pytest.raises(ContractError):
        Evidence("e3", "https://www.nfl.com/x", "nfl.com", "claim", "2026-11-01T00:00:00Z", "read", rights="licensed")


def test_quote_rejects_missing_line_and_post_kickoff():
    with pytest.raises(ContractError):
        Quote("q", "g", "spread", "home", None, -110, "2026-01-01T18:00:00Z", "2026-01-01T18:00:00Z", "op", "e", "https://sportsbook.draftkings.com/x", "r")
    with pytest.raises(ContractError):
        Quote("q", "g", "total", "over", 45.5, -110, "2026-01-01T19:00:00Z", "2026-01-01T18:00:00Z", "op", "e", "https://sportsbook.draftkings.com/x", "r")


def test_forecast_rejects_future_features():
    with pytest.raises(ContractError):
        Forecast("s", "g", "spread", "home", 0.5, 0, 0, "2026-01-01T17:00:00Z", "2026-01-01T18:00:00Z", "v1", "2026-01-01T17:30:00Z")


def synthetic_games(n=200):
    games = []
    for i in range(n):
        home = f"T{i % 4}"
        away = f"T{(i + 1) % 4}"
        kickoff = datetime(2020 + i // 100, 1 + i % 12, 1, 18, tzinfo=timezone.utc)
        games.append(Game(f"g{i}", 2020 + i // 100, 1 + i % 17, iso(kickoff), home, away,
                          20 + i % 7, 17 + i % 5, "e", "https://www.nfl.com/x",
                          status="final", result_available_at=iso(kickoff + timedelta(hours=4))))
    return games


def test_team_model_is_causal_and_deterministic():
    games = synthetic_games()
    model = TeamLineModel(min_games=50)
    cutoff = "2020-07-01T00:00:00Z"
    a = model.originate(games, "T0", "T1", cutoff, "future")
    b = model.originate(games, "T0", "T1", cutoff, "future")
    assert a.to_dict() == b.to_dict()
    assert a.n_train < len(games)
    truncated = [g for g in games if g.result_available_at <= cutoff]
    c = model.originate(truncated, "T0", "T1", cutoff, "future")
    assert a.to_dict() == c.to_dict()
    with pytest.raises(ContractError):
        model.originate(games[:10], "T0", "T1", cutoff, "future")


def test_player_mixture_and_void():
    logs = []
    for i in range(6):
        kickoff = datetime(2020, i + 1, 1, 18, tzinfo=timezone.utc)
        logs.append(PlayerGame("p", f"g{i}", iso(kickoff), "T0", "T1", "WR", "receiving_yards", 50 + 10 * i, True, "e", "https://www.nfl.com/x", stats_available_at=iso(kickoff + timedelta(hours=4))))
    kickoff = datetime(2020, 8, 1, 18, tzinfo=timezone.utc)
    logs.append(PlayerGame("p", "g7", iso(kickoff), "T0", "T1", "WR", "receiving_yards", 0, False, "e", "https://www.nfl.com/x", stats_available_at=iso(kickoff + timedelta(hours=4))))
    model = PlayerPropModel(min_player_games=3)
    f = model.forecast(logs, "p", "receiving_yards", 75.5, "2021-01-01T00:00:00Z", position="WR")
    assert 0 < f["p_participate"] < 1
    assert f["p_over"] + f["p_under"] + f["p_push"] + f["p_void"] == pytest.approx(1)
    assert f["p_void"] > 0


def test_joint_scenarios_preserve_dependence():
    x = np.array([[10, 10], [20, 20], [30, 30], [40, 40]])
    out = joint_from_scenarios(x, [15, 15])
    assert out["joint_over"] == 0.75
    assert out["independent_over"] == pytest.approx(0.5625)
    assert out["dependence_lift"] > 0
