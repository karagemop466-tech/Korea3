"""Fail-closed strategy validation, clustered uncertainty and leaderboard.

Luck cannot be removed.  These gates estimate how much of an observed result is
compatible with sampling noise, then refuse promotion unless the evidence is
strong on untouched, executable, officially evidenced observations.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Iterable
import hashlib
import json
import math

import numpy as np

from .contracts import ContractError, Forecast, SettledBet, probability, utc
from .evidence import EvidenceRegistry

GATE_NAMES = (
    "preregistration", "evidence_and_rights", "chronology", "sample",
    "probability_quality", "economics", "multiplicity", "stability",
    "execution_and_risk", "forward_freeze",
)


@dataclass(frozen=True)
class Protocol:
    protocol_id: str
    family: tuple[str, ...]
    train_seasons: tuple[int, ...]
    tune_seasons: tuple[int, ...]
    holdout_seasons: tuple[int, ...]
    forward_seasons: tuple[int, ...]
    min_holdout_bets: int = 200
    min_holdout_clusters: int = 20
    min_holdout_seasons: int = 3
    min_forward_bets: int = 100
    alpha: float = 0.05
    min_roi: float = 0.01
    decimal_slippage: float = 0.05
    max_drawdown_units: float = 20.0
    max_weekly_stake: float = 5.0
    bootstrap_replicates: int = 5000
    seed: int = 20261101

    def __post_init__(self):
        if not self.protocol_id or not self.family or len(set(self.family)) != len(self.family):
            raise ContractError("Protocol requires unique pre-registered family")
        groups = [set(self.train_seasons), set(self.tune_seasons), set(self.holdout_seasons), set(self.forward_seasons)]
        if any(not g for g in groups):
            raise ContractError("All four chronological windows are required")
        for i in range(len(groups)):
            for j in range(i + 1, len(groups)):
                if groups[i] & groups[j]:
                    raise ContractError("Chronological windows overlap")
        if not all(max(groups[i]) < min(groups[i + 1]) for i in range(3)):
            raise ContractError("Windows must be ordered train < tune < holdout < forward")
        if self.min_holdout_bets < 2 or self.min_holdout_clusters < 2 or self.min_holdout_seasons < 1:
            raise ContractError("Invalid sample thresholds")
        if not 0 < self.alpha < 1 or self.bootstrap_replicates < 100:
            raise ContractError("Invalid inference settings")

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


@dataclass
class GateResult:
    name: str
    status: str  # pass | fail | blocked
    detail: str
    value: float | None = None

    def to_dict(self):
        return asdict(self)


@dataclass
class StrategyReport:
    strategy_id: str
    gates: list[GateResult]
    metrics: dict
    eligible: bool
    score: float | None

    def to_dict(self):
        return {"strategy_id": self.strategy_id, "gates": [g.to_dict() for g in self.gates],
                "metrics": self.metrics, "eligible": self.eligible, "score": self.score}


def brier(probabilities: Iterable[float], outcomes: Iterable[float]) -> float:
    p = np.asarray(list(probabilities), float)
    y = np.asarray(list(outcomes), float)
    if p.shape != y.shape or p.size == 0 or not np.all((p >= 0) & (p <= 1)) or not np.all(np.isin(y, [0, 1])):
        raise ContractError("Brier requires aligned probabilities and binary outcomes")
    return float(np.mean((p - y) ** 2))


def log_loss(probabilities: Iterable[float], outcomes: Iterable[float], eps: float = 1e-12) -> float:
    p = np.asarray(list(probabilities), float)
    y = np.asarray(list(outcomes), float)
    if p.shape != y.shape or p.size == 0 or not np.all((p >= 0) & (p <= 1)) or not np.all(np.isin(y, [0, 1])):
        raise ContractError("Log loss requires aligned probabilities and binary outcomes")
    p = np.clip(p, eps, 1 - eps)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def calibration_bins(probabilities: Iterable[float], outcomes: Iterable[float], bins: int = 10) -> list[dict]:
    p, y = np.asarray(list(probabilities), float), np.asarray(list(outcomes), float)
    if p.shape != y.shape or p.size == 0 or bins < 1:
        raise ContractError("Invalid calibration input")
    out = []
    edges = np.linspace(0, 1, bins + 1)
    for i in range(bins):
        mask = (p >= edges[i]) & (p <= edges[i + 1] if i == bins - 1 else p < edges[i + 1])
        n = int(mask.sum())
        out.append({"bin": i, "lo": float(edges[i]), "hi": float(edges[i + 1]), "n": n,
                    "mean_forecast": float(p[mask].mean()) if n else None,
                    "observed_rate": float(y[mask].mean()) if n else None})
    return out


def cluster_bootstrap_mean(values: Iterable[float], clusters: Iterable[str],
                           replicates: int = 5000, alpha: float = 0.05,
                           seed: int = 20261101) -> dict:
    """Resample whole season-week clusters with replacement.

    This preserves within-week dependence.  It assumes clusters are exchangeable;
    it is not a guarantee for arbitrary temporal dependence.
    """
    v = np.asarray(list(values), float)
    c = np.asarray(list(clusters), str)
    if v.shape != c.shape or v.size == 0 or not np.all(np.isfinite(v)):
        raise ContractError("Invalid bootstrap input")
    unique = np.unique(c)
    if unique.size < 2 or replicates < 100 or not 0 < alpha < 1:
        raise ContractError("Bootstrap needs >=2 clusters, >=100 replicates and 0<alpha<1")
    sums = np.array([v[c == k].sum() for k in unique])
    counts = np.array([np.sum(c == k) for k in unique])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, unique.size, size=(replicates, unique.size))
    means = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    return {"mean": float(v.sum() / v.size), "lower": float(np.quantile(means, alpha / 2)),
            "upper": float(np.quantile(means, 1 - alpha / 2)), "clusters": int(unique.size),
            "replicates": replicates, "alpha": alpha}


def cluster_sign_permutation(values: Iterable[float], clusters: Iterable[str],
                             replicates: int = 5000, seed: int = 20261101) -> float:
    """One-sided cluster sign-flip p-value for mean > 0.

    Null assumption: cluster contributions are symmetric around zero.  This is
    a project modeling assumption, not an official betting standard.
    """
    v, c = np.asarray(list(values), float), np.asarray(list(clusters), str)
    if v.shape != c.shape or v.size == 0:
        raise ContractError("Invalid permutation input")
    unique = np.unique(c)
    if unique.size < 2:
        raise ContractError("Permutation needs >=2 clusters")
    sums = np.array([v[c == k].sum() for k in unique])
    counts = np.array([np.sum(c == k) for k in unique])
    observed = v.sum() / v.size
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(replicates, unique.size))
    null = (signs * sums).sum(axis=1) / counts.sum()
    return float((1 + np.sum(null >= observed)) / (replicates + 1))


def bonferroni(pvalues: Iterable[float]) -> list[float]:
    ps = [probability(p, "p") for p in pvalues]
    return [min(1.0, p * len(ps)) for p in ps]


def benjamini_hochberg(pvalues: Iterable[float]) -> list[float]:
    ps = np.asarray([probability(p, "p") for p in pvalues], float)
    if ps.size == 0:
        return []
    order = np.argsort(ps)
    q = np.empty_like(ps)
    running = 1.0
    for rank in range(ps.size - 1, -1, -1):
        i = order[rank]
        running = min(running, ps[i] * ps.size / (rank + 1))
        q[i] = running
    return q.tolist()


def max_drawdown(profits: Iterable[float]) -> float:
    p = np.asarray(list(profits), float)
    if p.size == 0 or not np.all(np.isfinite(p)):
        raise ContractError("Invalid profit series")
    equity = np.cumsum(p)
    peak = np.maximum.accumulate(np.concatenate(([0.0], equity)))[1:]
    return float(np.max(peak - equity))


def _gate(name, ok: bool | None, detail: str, value=None) -> GateResult:
    return GateResult(name, "blocked" if ok is None else "pass" if ok else "fail", detail, value)


def evaluate_strategy(strategy_id: str, bets: list[SettledBet], forecasts: list[Forecast],
                      protocol: Protocol, registry: EvidenceRegistry,
                      family_pvalues: dict[str, float] | None = None,
                      forward_bets: list[SettledBet] | None = None,
                      protocol_frozen_digest: str | None = None,
                      executable_quotes_verified: bool | None = None) -> StrategyReport:
    if strategy_id not in protocol.family:
        raise ContractError("Strategy is outside the pre-registered family")
    holdout = [b for b in bets if int(b.cluster.split("-")[0]) in protocol.holdout_seasons]
    fwd = forward_bets or []
    metrics: dict = {"holdout_bets": len(holdout), "forward_bets": len(fwd)}
    gates: list[GateResult] = []

    frozen = protocol_frozen_digest == protocol.digest() and set(family_pvalues or {}) == set(protocol.family)
    gates.append(_gate("preregistration", frozen, "Protocol digest and complete trial family must be frozen before evaluation"))

    evidence_ok = True
    try:
        for b in holdout + fwd:
            registry.audit_bet(b)
        evidence_ok = True
    except ContractError as exc:
        evidence_ok = False
        metrics["evidence_error"] = str(exc)
    gates.append(_gate("evidence_and_rights", evidence_ok if holdout else None,
                       "Every settled bet needs official event evidence, operator rules and redistribution rights"))

    chrono = True
    for f in forecasts:
        if utc(f.features_available_at) > utc(f.issued_at) or utc(f.issued_at) >= utc(f.kickoff):
            chrono = False
    for b in holdout + fwd:
        if b.market == "parlay" and len(set(b.legs)) != len(b.legs):
            chrono = False
    gates.append(_gate("chronology", chrono if forecasts else None,
                       "Features <= forecast < kickoff; no duplicate parlay legs; disjoint seasonal windows"))

    clusters = len({b.cluster for b in holdout})
    seasons = len({b.cluster.split("-")[0] for b in holdout})
    metrics.update(holdout_clusters=clusters, holdout_seasons=seasons)
    sample_ok = (len(holdout) >= protocol.min_holdout_bets and clusters >= protocol.min_holdout_clusters
                 and seasons >= protocol.min_holdout_seasons) if holdout else None
    gates.append(_gate("sample", sample_ok, "Minimum untouched holdout bets, season-week clusters and seasons"))

    usable = [b for b in holdout if b.result in {"win", "loss"} and b.p_win is not None]
    baseline = [b for b in usable if b.baseline_p_win is not None]
    if usable:
        p = [b.p_win for b in usable]
        y = [1.0 if b.result == "win" else 0.0 for b in usable]
        metrics["brier"] = brier(p, y)
        metrics["log_loss"] = log_loss(p, y)
        metrics["calibration"] = calibration_bins(p, y)
        if baseline:
            pb = [b.baseline_p_win for b in baseline]
            yb = [1.0 if b.result == "win" else 0.0 for b in baseline]
            metrics["baseline_brier"] = brier(pb, yb)
            metrics["baseline_log_loss"] = log_loss(pb, yb)
            model_by_id = {b.bet_id: b.p_win for b in usable}
            diff = [(b.baseline_p_win - (1.0 if b.result == "win" else 0.0)) ** 2 -
                    (model_by_id[b.bet_id] - (1.0 if b.result == "win" else 0.0)) ** 2
                    for b in baseline]
            skill = cluster_bootstrap_mean(diff, [b.cluster for b in baseline], protocol.bootstrap_replicates,
                                           protocol.alpha, protocol.seed)
            metrics["paired_brier_skill"] = skill
            model_brier_on_baseline = brier([model_by_id[b.bet_id] for b in baseline], yb)
            prob_ok = skill["lower"] > 0 and log_loss([model_by_id[b.bet_id] for b in baseline], yb) <= metrics["baseline_log_loss"]
            metrics["model_brier_on_baseline"] = model_brier_on_baseline
        else:
            prob_ok = None
    else:
        prob_ok = None
    gates.append(_gate("probability_quality", prob_ok,
                       "Paired holdout Brier improvement lower bound > 0 and no worse log loss versus a timestamped baseline"))

    if holdout:
        roi = [b.roi for b in holdout]
        ci = cluster_bootstrap_mean(roi, [b.cluster for b in holdout], protocol.bootstrap_replicates,
                                    protocol.alpha, protocol.seed)
        metrics["roi"] = ci
        pval = cluster_sign_permutation(roi, [b.cluster for b in holdout], protocol.bootstrap_replicates, protocol.seed + 1)
        metrics["cluster_p"] = pval
        econ_ok = ci["lower"] > 0 and ci["mean"] >= protocol.min_roi
    else:
        pval = None
        econ_ok = None
    gates.append(_gate("economics", econ_ok, "Holdout net ROI lower confidence bound > 0 and mean ROI >= protocol floor"))

    if pval is not None and family_pvalues and set(family_pvalues) == set(protocol.family):
        adj = bonferroni(list(family_pvalues.values()))
        keys = list(family_pvalues)
        q = adj[keys.index(strategy_id)]
        metrics["bonferroni_p"] = q
        metrics["bh_q"] = benjamini_hochberg(list(family_pvalues.values()))[keys.index(strategy_id)]
        multi_ok = q <= protocol.alpha
    else:
        multi_ok = None
    gates.append(_gate("multiplicity", multi_ok,
                       "Bonferroni-adjusted cluster p <= alpha across every registered trial; BH q reported as secondary"))

    if holdout:
        by_season: dict[str, list[float]] = {}
        for b in holdout:
            by_season.setdefault(b.cluster.split("-")[0], []).append(b.profit)
        season_profit = {s: float(sum(v)) for s, v in by_season.items()}
        total_profit = float(sum(season_profit.values()))
        positive_share = sum(v > 0 for v in season_profit.values()) / len(season_profit)
        best_share = max(season_profit.values()) / total_profit if total_profit > 0 else None
        stressed = [(b.profit - b.stake * protocol.decimal_slippage) if b.result == "win" else b.profit for b in holdout]
        stress_roi = float(np.mean([p / b.stake for p, b in zip(stressed, holdout)]))
        metrics.update(season_profit=season_profit, positive_season_share=positive_share,
                       best_season_profit_share=best_share, stressed_roi=stress_roi)
        stability_ok = positive_share >= 2 / 3 and stress_roi > 0 and (best_share is None or best_share <= 0.5)
    else:
        stability_ok = None
    gates.append(_gate("stability", stability_ok,
                       "Positive in >=2/3 holdout seasons, no season >50% of profit, and positive after decimal slippage"))

    if holdout:
        ordered = sorted(holdout, key=lambda b: (utc(b.kickoff), b.bet_id))
        dd = max_drawdown([b.profit for b in ordered])
        weekly: dict[str, float] = {}
        for b in holdout:
            weekly[b.cluster] = weekly.get(b.cluster, 0.0) + b.stake
        max_week = max(weekly.values())
        metrics.update(max_drawdown_units=dd, max_weekly_stake=max_week)
        risk_ok = (dd <= protocol.max_drawdown_units and max_week <= protocol.max_weekly_stake
                   and executable_quotes_verified is True)
    else:
        risk_ok = None
    gates.append(_gate("execution_and_risk", risk_ok,
                       "Drawdown and weekly exposure within pre-registered unit limits; executable quotes must be verified"))

    forward_ok = len(fwd) >= protocol.min_forward_bets and all(b.result in {"win", "loss", "push", "void"} for b in fwd) if fwd else None
    if fwd:
        metrics["forward_roi"] = float(np.mean([b.roi for b in fwd]))
        forward_ok = forward_ok and metrics["forward_roi"] > 0
    gates.append(_gate("forward_freeze", forward_ok,
                       "Post-freeze paper/forward sample meets minimum size and has positive net ROI; no real-money execution"))

    eligible = all(g.status == "pass" for g in gates)
    score = metrics.get("roi", {}).get("lower") if eligible else None
    return StrategyReport(strategy_id, gates, metrics, eligible, score)


def leaderboard(reports: list[StrategyReport], reward_pool: float | None = None) -> list[dict]:
    eligible = sorted([r for r in reports if r.eligible], key=lambda r: (-(r.score or -math.inf), r.strategy_id))
    rows = []
    for rank, r in enumerate(eligible, 1):
        reward = None
        if reward_pool is not None:
            if reward_pool < 0:
                raise ContractError("Reward pool cannot be negative")
            weights = {1: 0.5, 2: 0.3, 3: 0.2}
            reward = reward_pool * weights.get(rank, 0.0) if len(eligible) >= 3 else (reward_pool / len(eligible) if rank <= len(eligible) else 0.0)
        rows.append({"rank": rank, "strategy_id": r.strategy_id, "score": r.score,
                     "reward": reward, "status": "eligible"})
    for r in reports:
        if not r.eligible:
            rows.append({"rank": None, "strategy_id": r.strategy_id, "score": None,
                         "reward": None, "status": "not_eligible"})
    return rows
