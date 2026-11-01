"""Typed contracts for the fail-closed NFL research workbench.

No network access and no sportsbook execution.  A URL is provenance, not a
redistribution licence.  Real observations must carry both an official evidence
reference and an explicit rights record before entering the verified pipeline.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Literal
import math


class ContractError(ValueError):
    """An input cannot be admitted to the verified pipeline."""


def utc(value: str) -> datetime:
    try:
        d = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ContractError(f"Invalid ISO-8601 timestamp: {value!r}") from exc
    if d.tzinfo is None:
        raise ContractError("Timestamp must include a timezone")
    return d.astimezone(timezone.utc)


def finite(value: Any, name: str) -> float:
    if isinstance(value, bool):
        raise ContractError(f"{name} must be numeric, not boolean")
    try:
        x = float(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{name} must be numeric") from exc
    if not math.isfinite(x):
        raise ContractError(f"{name} must be finite")
    return x


def probability(value: Any, name: str = "probability") -> float:
    x = finite(value, name)
    if not 0.0 <= x <= 1.0:
        raise ContractError(f"{name} must be in [0, 1]")
    return x


@dataclass(frozen=True)
class Evidence:
    evidence_id: str
    url: str
    publisher: str
    claim: str
    verified_at: str
    method: str
    rights: str = "link_only"
    content_sha256: str | None = None
    fields: tuple[str, ...] = ()

    def __post_init__(self):
        if not self.evidence_id or not self.claim or not self.method:
            raise ContractError("Evidence requires id, claim and verification method")
        utc(self.verified_at)
        if self.rights not in {"link_only", "licensed", "public_domain"}:
            raise ContractError("Unknown rights status")
        if self.rights == "licensed" and not self.content_sha256:
            raise ContractError("Licensed content requires a pinned content hash")

    def to_dict(self):
        return asdict(self)


@dataclass(frozen=True)
class Game:
    game_id: str
    season: int
    week: int
    kickoff: str
    home: str
    away: str
    home_score: int
    away_score: int
    evidence_id: str
    source_url: str

    def __post_init__(self):
        if not self.game_id or not self.home or not self.away or self.home == self.away:
            raise ContractError("Invalid game identity")
        if self.season < 1920 or not 1 <= self.week <= 22:
            raise ContractError("Invalid season/week")
        if self.home_score < 0 or self.away_score < 0:
            raise ContractError("Scores cannot be negative")
        utc(self.kickoff)
        if not self.evidence_id or not self.source_url.startswith("https://"):
            raise ContractError("Game requires official evidence and HTTPS source")

    @property
    def margin(self) -> int:
        return self.home_score - self.away_score

    @property
    def total(self) -> int:
        return self.home_score + self.away_score

    @property
    def cluster(self) -> str:
        return f"{self.season}-{self.week:02d}"


@dataclass(frozen=True)
class Quote:
    quote_id: str
    game_id: str
    market: Literal["spread", "total", "moneyline", "player_prop"]
    selection: str
    line: float | None
    american: float
    observed_at: str
    kickoff: str
    operator: str
    evidence_id: str
    source_url: str
    rules_id: str
    executable: bool = False
    player_id: str | None = None

    def __post_init__(self):
        if self.market not in {"spread", "total", "moneyline", "player_prop"}:
            raise ContractError("Unknown market")
        finite(self.american, "american")
        if abs(self.american) < 100:
            raise ContractError("American odds must be <= -100 or >= +100")
        if self.line is not None:
            finite(self.line, "line")
        if utc(self.observed_at) >= utc(self.kickoff):
            raise ContractError("Pregame quote must precede kickoff")
        if not self.operator or not self.rules_id or not self.evidence_id:
            raise ContractError("Quote requires operator, rules and evidence")
        if not self.source_url.startswith("https://"):
            raise ContractError("Quote source must be HTTPS")
        if self.market == "player_prop" and not self.player_id:
            raise ContractError("Player prop requires player_id")
        if self.market in {"spread", "total", "player_prop"} and self.line is None:
            raise ContractError("Threshold market requires a line; never impute one")


@dataclass(frozen=True)
class Forecast:
    strategy_id: str
    event_id: str
    market: str
    selection: str
    p_win: float
    p_push: float
    p_void: float
    issued_at: str
    kickoff: str
    model_version: str
    features_available_at: str
    baseline_id: str | None = None
    baseline_p_win: float | None = None

    def __post_init__(self):
        probability(self.p_win, "p_win")
        probability(self.p_push, "p_push")
        probability(self.p_void, "p_void")
        if self.p_win + self.p_push + self.p_void > 1 + 1e-10:
            raise ContractError("Outcome probabilities exceed one")
        if utc(self.issued_at) >= utc(self.kickoff):
            raise ContractError("Forecast must precede kickoff")
        if utc(self.features_available_at) > utc(self.issued_at):
            raise ContractError("Feature timestamp is later than forecast")
        if self.baseline_p_win is not None:
            probability(self.baseline_p_win, "baseline_p_win")
        if not self.model_version or not self.strategy_id:
            raise ContractError("Forecast requires strategy and model version")


@dataclass(frozen=True)
class SettledBet:
    bet_id: str
    strategy_id: str
    event_id: str
    cluster: str
    kickoff: str
    stake: float
    profit: float
    result: Literal["win", "loss", "push", "void"]
    quote_id: str
    evidence_id: str
    source_url: str
    rules_id: str
    p_win: float | None = None
    baseline_p_win: float | None = None
    market: str = "single"
    legs: tuple[str, ...] = ()

    def __post_init__(self):
        stake = finite(self.stake, "stake")
        profit = finite(self.profit, "profit")
        if stake <= 0:
            raise ContractError("Stake must be positive")
        if self.result not in {"win", "loss", "push", "void"}:
            raise ContractError("Unknown settlement result")
        if self.result in {"push", "void"} and abs(profit) > 1e-10:
            raise ContractError("Push/void must return stake (zero net profit)")
        if self.result == "loss" and abs(profit + stake) > 1e-10:
            raise ContractError("Full loss must equal negative stake")
        if self.result == "win" and profit <= 0:
            raise ContractError("Win must have positive net profit")
        if not self.quote_id or not self.rules_id or not self.evidence_id:
            raise ContractError("Settlement requires quote, rules and evidence")
        if not self.source_url.startswith("https://"):
            raise ContractError("Settlement source must be HTTPS")
        utc(self.kickoff)
        if self.p_win is not None:
            probability(self.p_win, "p_win")
        if self.baseline_p_win is not None:
            probability(self.baseline_p_win, "baseline_p_win")

    @property
    def roi(self) -> float:
        return self.profit / self.stake
