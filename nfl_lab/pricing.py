"""Exact odds, settlement and dependence arithmetic.

Conventions: American odds; spread is the selected team's handicap; total and
player-prop lines are over/under thresholds.  Net profit excludes returned stake.
Parlay rules are explicit inputs, never inferred from a generic help article.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Iterable, Literal

import numpy as np

from .contracts import ContractError, finite, probability

Outcome = Literal["win", "loss", "push", "void"]


def american_to_decimal(american: float) -> float:
    a = finite(american, "american")
    if abs(a) < 100:
        raise ContractError("American odds must be <= -100 or >= +100")
    return 1 + (a / 100 if a > 0 else 100 / abs(a))


def decimal_to_american(decimal: float) -> float:
    d = finite(decimal, "decimal")
    if d <= 1:
        raise ContractError("Decimal odds must exceed one")
    return (d - 1) * 100 if d >= 2 else -100 / (d - 1)


def implied_probability(american: float) -> float:
    return 1 / american_to_decimal(american)


def remove_vig_two_way(a: float, b: float) -> tuple[float, float]:
    """Proportional normalization; an assumption, not the unique true no-vig price."""
    x, y = implied_probability(a), implied_probability(b)
    if x + y <= 1:
        raise ContractError("Two-way overround must exceed one for this helper")
    return x / (x + y), y / (x + y)


def fair_decimal(p_win: float, p_push: float = 0, p_void: float = 0) -> float:
    pw, pp, pv = map(probability, (p_win, p_push, p_void))
    if pw + pp + pv > 1 + 1e-12 or pw <= 0:
        raise ContractError("Invalid outcome distribution")
    # Conditional on action, push/void stakes are returned.
    return 1 + (1 - pw - pp - pv) / pw


def expected_roi(p_win: float, american: float, p_push: float = 0, p_void: float = 0) -> float:
    pw, pp, pv = map(probability, (p_win, p_push, p_void))
    if pw + pp + pv > 1 + 1e-12:
        raise ContractError("Outcome probabilities exceed one")
    pl = 1 - pw - pp - pv
    return pw * (american_to_decimal(american) - 1) - pl


def settle_single(actual: float, line: float, selection: str, american: float,
                  stake: float = 1.0) -> tuple[Outcome, float]:
    stake = finite(stake, "stake")
    if stake <= 0:
        raise ContractError("Stake must be positive")
    actual = finite(actual, "actual")
    line = finite(line, "line")
    if selection in {"over", "under"}:
        # line is the total/prop threshold.
        diff = actual - line
        if selection == "under":
            diff = -diff
    elif selection in {"home", "away"}:
        # actual is the selected team's score margin; line is its handicap
        # (favorite negative, underdog positive), added to the margin.
        diff = actual + line
    else:
        raise ContractError("Selection must be home/away or over/under")
    if abs(diff) < 1e-12:
        return "push", 0.0
    return ("win", stake * (american_to_decimal(american) - 1)) if diff > 0 else ("loss", -stake)


def settle_moneyline(selected_score: float, opponent_score: float, american: float,
                     stake: float = 1.0, two_way: bool = True) -> tuple[Outcome, float]:
    if not two_way:
        raise ContractError("Three-way moneylines require an explicit draw selection")
    stake = finite(stake, "stake")
    if stake <= 0:
        raise ContractError("Stake must be positive")
    diff = finite(selected_score, "score") - finite(opponent_score, "opponent")
    if diff == 0:
        return "push", 0.0
    return ("win", stake * (american_to_decimal(american) - 1)) if diff > 0 else ("loss", -stake)


@dataclass(frozen=True)
class ParlayRule:
    """Operator/market-specific rule snapshot.

    traditional: push/void legs drop and decimal payout is recalculated.
    sgp: caller must specify what happens to pushes and voids.  'void_ticket'
    returns the stake; 'drop_reprice' removes the leg; 'loss' loses the ticket.
    No default SGP rule is supplied.
    """
    kind: Literal["traditional", "sgp"]
    push: Literal["drop", "loss", "void_ticket"]
    void: Literal["drop", "loss", "void_ticket"]
    evidence_id: str
    min_remaining_legs: int = 1
    below_min: Literal["void_ticket", "loss"] = "void_ticket"

    def __post_init__(self):
        if not self.evidence_id:
            raise ContractError("Parlay rule requires an evidence id")
        if self.kind == "traditional" and (self.push != "drop" or self.void != "drop"):
            raise ContractError("Traditional rule here means drop/reprice; use sgp for other rules")
        if self.push not in {"drop", "loss", "void_ticket"} or self.void not in {"drop", "loss", "void_ticket"}:
            raise ContractError("Unknown push/void action")
        if isinstance(self.min_remaining_legs, bool) or not isinstance(self.min_remaining_legs, int) or self.min_remaining_legs < 1:
            raise ContractError("min_remaining_legs must be a positive integer")
        if self.below_min not in {"void_ticket", "loss"}:
            raise ContractError("Unknown below-minimum action")
        if self.kind == "sgp" and self.min_remaining_legs < 2:
            raise ContractError("SGP rules must state a minimum remaining-leg count of at least two")


def settle_parlay(legs: Iterable[tuple[Outcome, float]], rule: ParlayRule,
                  stake: float = 1.0) -> tuple[Outcome, float, float]:
    """Return (result, net profit, effective decimal after rule adjustments).

    Each leg's second item is its original decimal price.  A losing leg cannot
    be rescued by a later void.  All-void tickets return stake.  This function
    does not invent the operator's last-available repricing snapshot.
    """
    legs = list(legs)
    stake = finite(stake, "stake")
    if len(legs) < 2 or stake <= 0:
        raise ContractError("Parlay needs at least two legs and positive stake")
    for result, decimal in legs:
        if result not in {"win", "loss", "push", "void"}:
            raise ContractError("Unknown leg outcome")
        if finite(decimal, "decimal") <= 1:
            raise ContractError("Decimal odds must exceed one")
    if any(r == "loss" for r, _ in legs):
        return "loss", -stake, 1.0
    for result, action in [(r, rule.push if r == "push" else rule.void if r == "void" else "drop")
                           for r, _ in legs if r in {"push", "void"}]:
        if action == "loss":
            return "loss", -stake, 1.0
        if action == "void_ticket":
            return "void", 0.0, 1.0
    # Losses and ticket-void actions have already returned.  Push/void legs
    # with the explicit drop action are removed from the payout calculation.
    remaining = [d for r, d in legs if r == "win"]
    if not remaining:
        return "void", 0.0, 1.0
    decimal = float(np.prod(remaining))
    if len(remaining) < rule.min_remaining_legs:
        if rule.below_min == "loss":
            return "loss", -stake, 1.0
        return "void", 0.0, 1.0
    return "win", stake * (decimal - 1), decimal


def phi_from_counts(n11: int, n10: int, n01: int, n00: int) -> float | None:
    if any(isinstance(x, bool) for x in (n11, n10, n01, n00)):
        raise ContractError("Counts must be integers, not booleans")
    counts = np.array([n11, n10, n01, n00], dtype=float)
    if np.any(counts < 0) or np.any(counts != np.floor(counts)) or counts.sum() == 0:
        raise ContractError("Counts must be non-negative integers with positive total")
    a, b, c, d = counts
    denom = np.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    return None if denom == 0 else float((a * d - b * c) / denom)


def phi(x: Iterable[float], y: Iterable[float]) -> float | None:
    x, y = np.asarray(list(x), float), np.asarray(list(y), float)
    if x.shape != y.shape or x.size < 2 or not np.all(np.isin(x, [0, 1])) or not np.all(np.isin(y, [0, 1])):
        raise ContractError("Phi requires aligned binary vectors of length >= 2")
    return phi_from_counts(int(np.sum((x == 1) & (y == 1))), int(np.sum((x == 1) & (y == 0))),
                           int(np.sum((x == 0) & (y == 1))), int(np.sum((x == 0) & (y == 0))))


def joint_from_phi(pa: float, pb: float, rho: float) -> float:
    pa, pb = probability(pa, "pa"), probability(pb, "pb")
    rho = finite(rho, "rho")
    lo = max(-np.sqrt(pa * pb / ((1 - pa) * (1 - pb))), -np.sqrt((1 - pa) * (1 - pb) / (pa * pb))) if 0 < pa < 1 and 0 < pb < 1 else 0.0
    hi = min(np.sqrt(pa * (1 - pb) / ((1 - pa) * pb)), np.sqrt(pb * (1 - pa) / ((1 - pb) * pa))) if 0 < pa < 1 and 0 < pb < 1 else 0.0
    if not lo - 1e-12 <= rho <= hi + 1e-12:
        raise ContractError("Phi is outside the feasible range for these marginals")
    return float(np.clip(pa * pb + rho * np.sqrt(pa * (1 - pa) * pb * (1 - pb)), 0, 1))


def required_phi(pa: float, pb: float, decimal_payout: float) -> float | None:
    pa, pb = probability(pa, "pa"), probability(pb, "pb")
    d = finite(decimal_payout, "decimal_payout")
    if d <= 1:
        raise ContractError("Decimal payout must exceed one")
    denom = np.sqrt(pa * (1 - pa) * pb * (1 - pb))
    return None if denom == 0 else float((1 / d - pa * pb) / denom)


def frechet_bounds(probabilities: Iterable[float]) -> tuple[float, float]:
    ps = [probability(p) for p in probabilities]
    if not ps:
        raise ContractError("At least one probability required")
    return max(0.0, sum(ps) - len(ps) + 1), min(ps)


def parlay_ev_independent(p_win: Iterable[float], american_legs: Iterable[float]) -> float:
    """Binary, no-push/no-void independent-leg EV. Not an SGP pricing model."""
    ps, odds = list(p_win), list(american_legs)
    if len(ps) != len(odds) or len(ps) < 2:
        raise ContractError("Need aligned legs, at least two")
    joint = float(np.prod([probability(p) for p in ps]))
    return joint * float(np.prod([american_to_decimal(a) for a in odds])) - 1
