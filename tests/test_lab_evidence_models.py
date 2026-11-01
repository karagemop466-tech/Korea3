import hashlib
import pytest
from nfl_lab.contracts import ContractError, Evidence, Game, Quote, Forecast
from nfl_lab.evidence import EvidenceRegistry, official_publisher
from nfl_lab.models import TeamLineModel, PlayerGame, PlayerPropModel, joint_from_scenarios
import numpy as np


def test_official_publisher_allowlist():
    assert official_publisher("https://www.nfl.com/legal/terms/") == "nfl.com"
    assert official_publisher("https://support.draftkings.com/dk/en-us/x") == "draftkings.com"
    assert official_publisher("https://www.itl.nist.gov/x") == "nist.gov"
    assert official_publisher("https://nfl.com.example.com/x") is None
    assert official_publisher("http://www.nfl.com/x") is None
    assert official_publisher("https://github.com/nflverse/nfldata") is None


def test_link_only_evidence_cannot_admit_stored_data():
    rec = Evidence("e1", "https://www.nfl.com/legal/terms/", "NFL", "claim", "2026-11-01T00:00:00Z", "read")
    reg = EvidenceRegistry([rec])
    with pytest.raises(ContractError):
        reg.require("e1", rec.url, require_rights=True)
    assert reg.require("e1", rec.url, require_rights=False).evidence_id == "e1"


def test_licensed_evidence_hash_required():
    content = b"synthetic"
    digest = hashlib.sha256(content).hexdigest()
    rec = Evidence("e2", "https://www.nfl.com/stats/player-stats/", "NFL", "claim", "2026-11-01T00:00:00Z", "read", rights="licensed", content_sha256=digest)
    reg = EvidenceRegistry([rec])
    reg.require("e2", rec.url, content=content)
    with pytest.raises(ContractError):
        reg.require("e2", rec.url, content=b"changed")
    with pytest.raises(ContractError):
        Evidence("e3", "https://www.nfl.com/x", "NFL", "claim", "2026-11-01T00:00:00Z", "read", rights="licensed")


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
        games.append(Game(f"g{i}", 2020 + i // 100, 1 + i % 17, f"2020-{1 + i % 12:02d}-01T18:00:00Z",
                          home, away, 20 + i % 7, 17 + i % 5, "e", "https://www.nfl.com/x"))
    return games


def test_team_model_is_causal_and_deterministic():
    games = synthetic_games()
    model = TeamLineModel(min_games=50)
    cutoff = "2020-06-01T00:00:00Z"
    a = model.originate(games, "T0", "T1", cutoff, "future")
    b = model.originate(games, "T0", "T1", cutoff, "future")
    assert a.to_dict() == b.to_dict()
    assert a.n_train < len(games)
    truncated = [g for g in games if g.kickoff < cutoff]
    c = model.originate(truncated, "T0", "T1", cutoff, "future")
    assert a.to_dict() == c.to_dict()
    with pytest.raises(ContractError):
        model.originate(games[:10], "T0", "T1", cutoff, "future")


def test_player_mixture_and_void():
    logs = []
    for i in range(6):
        logs.append(PlayerGame("p", f"g{i}", f"2020-0{i+1}-01T18:00:00Z", "T0", "T1", "WR", "receiving_yards", 50 + 10 * i, True, "e", "https://www.nfl.com/x"))
    logs.append(PlayerGame("p", "g7", "2020-08-01T18:00:00Z", "T0", "T1", "WR", "receiving_yards", 0, False, "e", "https://www.nfl.com/x"))
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
