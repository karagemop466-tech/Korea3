"""Typed contracts for the fail-closed NFL research workbench.

No network access and no sportsbook execution. A URL is provenance, not a
redistribution licence. Real observations must carry both official evidence and
an explicit rights record before entering the verified pipeline.

Hardening note (2026-11-02): identity, acceptance-time and artifact fields are
optional at construction for backwards-compatible loading, but admission
requires them. A record that merely parses is not an admitted record.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Literal
import math
import re


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


def sha256_hex(value: str | None, name: str = "sha256") -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
        raise ContractError(f"{name} must be a 64-character lowercase hex digest")
    return value


def integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ContractError(f"{name} must be an integer")
    return value


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
    # Admission metadata. Link-only reference sources may leave these empty.
    kind: str = "reference"
    review_status: str = "unverified"
    operator: str | None = None
    jurisdictions: tuple[str, ...] = ()
    markets: tuple[str, ...] = ()
    effective_from: str | None = None
    effective_until: str | None = None
    version: str | None = None
    license_ref: str | None = None
    license_sha256: str | None = None
    rights_scope: tuple[str, ...] = ()
    support_scope: str = "context"
    source_version: str | None = None
    parlay_kind: str | None = None
    push_action: str | None = None
    void_action: str | None = None
    min_remaining_legs: int | None = None
    below_min_action: str | None = None
    player_nonparticipation_action: str | None = None

    def __post_init__(self):
        if not self.evidence_id or not self.method:
            raise ContractError("Evidence requires id and verification method")
        utc(self.verified_at)
        if self.rights not in {"link_only", "licensed", "public_domain"}:
            raise ContractError("Unknown rights status")
        if self.review_status not in {"verified", "unverified"}:
            raise ContractError("Unknown review status")
        if self.review_status == "unverified" and self.claim:
            raise ContractError("Unverified evidence must leave its claim blank")
        if self.rights in {"licensed", "public_domain"}:
            sha256_hex(self.content_sha256, "content_sha256")
            if not self.rights_scope:
                raise ContractError("Stored-data rights require an explicit scope")
        if self.rights == "licensed":
            if not self.license_ref or not self.license_ref.startswith("https://"):
                raise ContractError("Licensed content requires an HTTPS licence reference")
            sha256_hex(self.license_sha256, "license_sha256")
        if self.content_sha256 is not None:
            sha256_hex(self.content_sha256, "content_sha256")
        if self.license_sha256 is not None:
            sha256_hex(self.license_sha256, "license_sha256")
        if self.effective_from:
            utc(self.effective_from)
        if self.effective_until:
            utc(self.effective_until)
        if self.effective_from and self.effective_until and utc(self.effective_from) >= utc(self.effective_until):
            raise ContractError("Evidence effective interval is empty")
        if self.kind == "settlement_rules":
            if not self.operator or not self.jurisdictions or not self.markets or not self.version:
                raise ContractError("Settlement rules require operator, jurisdictions, markets and version")
            if not self.effective_from or not self.effective_until:
                raise ContractError("Settlement rules require an explicit effective interval")
        if self.parlay_kind is not None:
            if self.parlay_kind not in {"traditional", "sgp"}:
                raise ContractError("Unknown parlay kind")
            if self.push_action not in {"drop", "loss", "void_ticket"} or self.void_action not in {"drop", "loss", "void_ticket"}:
                raise ContractError("Parlay rules require explicit push/void actions")
            if self.parlay_kind == "traditional" and (self.push_action != "drop" or self.void_action != "drop"):
                raise ContractError("Traditional rule here means drop/reprice")
            if self.min_remaining_legs is None or self.min_remaining_legs < 1:
                raise ContractError("Parlay rules require a minimum remaining-leg count")
            if self.below_min_action not in {"void_ticket", "loss"}:
                raise ContractError("Parlay rules require an explicit below-minimum action")
        if self.player_nonparticipation_action is not None and self.player_nonparticipation_action != "void":
            raise ContractError("Only an explicit nonparticipation-void rule is supported for player props")

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
    status: str = "unverified"
    result_available_at: str | None = None

    def __post_init__(self):
        if not self.game_id or not self.home or not self.away or self.home == self.away:
            raise ContractError("Invalid game identity")
        integer(self.season, "season")
        integer(self.week, "week")
        if self.season < 1920 or not 1 <= self.week <= 22:
            raise ContractError("Invalid season/week")
        integer(self.home_score, "home_score")
        integer(self.away_score, "away_score")
        if self.home_score < 0 or self.away_score < 0:
            raise ContractError("Scores cannot be negative")
        utc(self.kickoff)
        if self.result_available_at:
            utc(self.result_available_at)
            if utc(self.result_available_at) < utc(self.kickoff):
                raise ContractError("Final result cannot be available before kickoff")
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
    market: Literal["spread", "total", "moneyline", "player_prop", "parlay"]
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
    jurisdiction: str | None = None
    market_stat: str | None = None
    legs: tuple[str, ...] = ()

    def __post_init__(self):
        if self.market not in {"spread", "total", "moneyline", "player_prop", "parlay"}:
            raise ContractError("Unknown market")
        if not self.quote_id or not self.game_id:
            raise ContractError("Quote requires quote_id and event id")
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
        if not isinstance(self.executable, bool):
            raise ContractError("executable must be boolean")
        if self.market == "player_prop":
            if not self.player_id or not self.market_stat:
                raise ContractError("Player prop requires player_id and market_stat")
            if self.selection not in {"over", "under"} or self.line is None:
                raise ContractError("Player prop requires over/under and a quoted threshold")
        elif self.player_id is not None or self.market_stat is not None:
            raise ContractError("player_id/market_stat are only valid for player props")
        if self.market == "spread" and (self.selection not in {"home", "away"} or self.line is None):
            raise ContractError("Spread requires home/away and a quoted handicap")
        if self.market == "total" and (self.selection not in {"over", "under"} or self.line is None):
            raise ContractError("Total requires over/under and a quoted threshold")
        if self.market == "moneyline" and (self.selection not in {"home", "away"} or self.line is not None):
            raise ContractError("Two-way moneyline requires home/away and no threshold")
        if self.market == "parlay":
            if self.selection != "ticket" or self.line is not None or len(self.legs) < 2 or len(set(self.legs)) != len(self.legs):
                raise ContractError("Parlay quote requires a ticket selection and at least two unique legs")
        elif self.legs:
            raise ContractError("Only parlay quotes may carry legs")


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
    forecast_id: str | None = None
    line: float | None = None
    player_id: str | None = None
    market_stat: str | None = None
    artifact_sha256: str | None = None
    code_commit: str | None = None
    feature_snapshot_sha256: str | None = None
    baseline_quote_id: str | None = None
    opposite_quote_id: str | None = None
    baseline_method: str | None = None

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
        if self.line is not None:
            finite(self.line, "line")
        if self.artifact_sha256 is not None:
            sha256_hex(self.artifact_sha256, "artifact_sha256")
        if self.feature_snapshot_sha256 is not None:
            sha256_hex(self.feature_snapshot_sha256, "feature_snapshot_sha256")

    @property
    def p_action_win(self) -> float:
        denom = 1.0 - self.p_push - self.p_void
        if denom <= 0:
            raise ContractError("Forecast has no action mass")
        return self.p_win / denom


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
    # Acceptance/settlement chain. Required by EvidenceRegistry.audit_bet.
    forecast_id: str | None = None
    selection: str | None = None
    line: float | None = None
    player_id: str | None = None
    market_stat: str | None = None
    operator: str | None = None
    jurisdiction: str | None = None
    accepted_at: str | None = None
    accepted_american: float | None = None
    settled_at: str | None = None
    leg_outcomes: tuple[str, ...] = ()
    adjusted_american: float | None = None

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
        if not self.bet_id or not self.quote_id or not self.rules_id or not self.evidence_id:
            raise ContractError("Settlement requires bet, quote, rules and evidence ids")
        if not self.source_url.startswith("https://"):
            raise ContractError("Settlement source must be HTTPS")
        utc(self.kickoff)
        if not re.fullmatch(r"\d{4}-\d{2}", self.cluster):
            raise ContractError("cluster must be YYYY-WW")
        if self.market not in {"single", "parlay"}:
            raise ContractError("Ticket market must be single or parlay")
        if self.market == "parlay" and len(self.legs) < 2:
            raise ContractError("Parlay settlement requires legs")
        if self.market == "single" and self.legs:
            raise ContractError("Single settlement cannot carry parlay legs")
        if self.p_win is not None:
            probability(self.p_win, "p_win")
        if self.baseline_p_win is not None:
            probability(self.baseline_p_win, "baseline_p_win")
        if self.accepted_at:
            utc(self.accepted_at)
        if self.settled_at:
            utc(self.settled_at)
        if self.accepted_american is not None:
            finite(self.accepted_american, "accepted_american")
            if abs(self.accepted_american) < 100:
                raise ContractError("Accepted American odds must be <= -100 or >= +100")
        if self.adjusted_american is not None:
            finite(self.adjusted_american, "adjusted_american")
            if abs(self.adjusted_american) < 100:
                raise ContractError("Adjusted American odds must be <= -100 or >= +100")
        if self.line is not None:
            finite(self.line, "line")
        for outcome in self.leg_outcomes:
            if outcome not in {"win", "loss", "push", "void"}:
                raise ContractError("Unknown leg outcome")

    @property
    def roi(self) -> float:
        return self.profit / self.stake
