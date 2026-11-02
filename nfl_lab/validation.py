"""Fail-closed strategy validation, clustered uncertainty and leaderboard.

Luck cannot be removed. These gates estimate how much of an observed result is
compatible with sampling noise, then refuse promotion unless the evidence is
strong on untouched, executable, officially evidenced observations.

Hardening note (2026-11-02): p-values are computed inside the registered family,
not accepted from callers; execution is proved by quote/settlement admission,
not a boolean; probability scores use the matched forecast artifact and are
conditional on action so pushes/voids do not enter binary Brier/log-loss.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Iterable
import hashlib
import json
import math

import numpy as np

from .contracts import ContractError, Forecast, SettledBet, finite, probability, utc
from .evidence import BASELINE_METHOD, EvidenceRegistry, InputBundle

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
    min_forward_clusters: int = 10
    alpha: float = 0.05
    min_roi: float = 0.01
    decimal_slippage: float = 0.05
    max_drawdown_units: float = 20.0
    max_weekly_stake: float = 5.0
    unit_stake: float = 1.0
    bootstrap_replicates: int = 5000
    seed: int = 20261101
    baseline_method: str = BASELINE_METHOD

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
        if self.min_forward_bets < 2 or self.min_forward_clusters < 2:
            raise ContractError("Invalid forward sample thresholds")
        if not 0 < self.alpha < 1 or self.bootstrap_replicates < 100:
            raise ContractError("Invalid inference settings")
        for name in ("min_roi", "decimal_slippage", "max_drawdown_units", "max_weekly_stake", "unit_stake"):
            finite(getattr(self, name), name)
        if self.decimal_slippage < 0 or self.max_drawdown_units <= 0 or self.max_weekly_stake <= 0 or self.unit_stake <= 0:
            raise ContractError("Invalid risk/stress settings")
        if self.baseline_method != BASELINE_METHOD:
            raise ContractError("Unknown frozen baseline method")

    def digest(self) -> str:
        return hashlib.sha256(json.dumps(asdict(self), sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class ProtocolFreeze:
    """Project-authored freeze manifest; not an official NFL source."""
    protocol_digest: str
    frozen_at: str
    family: tuple[str, ...]
    model_versions: tuple[str, ...]
    baseline_method: str
    code_fingerprint: str

    def __post_init__(self):
        utc(self.frozen_at)
        if not self.protocol_digest or not self.family or not self.model_versions or not self.code_fingerprint:
            raise ContractError("Freeze requires digest, time, family, model versions and code fingerprint")


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


def _cluster_arrays(values, clusters):
    v = np.asarray(list(values), float)
    c = np.asarray(list(clusters), str)
    if v.shape != c.shape or v.size == 0 or not np.all(np.isfinite(v)):
        raise ContractError("Invalid cluster input")
    unique = np.unique(c)
    if unique.size < 2:
        raise ContractError("Cluster inference needs >=2 clusters")
    return v, c, unique


def cluster_bootstrap_mean(values: Iterable[float], clusters: Iterable[str],
                           replicates: int = 5000, alpha: float = 0.05,
                           seed: int = 20261101) -> dict:
    v, c, unique = _cluster_arrays(values, clusters)
    if replicates < 100 or not 0 < alpha < 1:
        raise ContractError("Bootstrap needs >=100 replicates and 0<alpha<1")
    sums = np.array([v[c == k].sum() for k in unique])
    counts = np.array([np.sum(c == k) for k in unique])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, unique.size, size=(replicates, unique.size))
    means = sums[idx].sum(axis=1) / counts[idx].sum(axis=1)
    return {"mean": float(v.sum() / v.size), "lower": float(np.quantile(means, alpha / 2)),
            "upper": float(np.quantile(means, 1 - alpha / 2)), "clusters": int(unique.size),
            "replicates": replicates, "alpha": alpha}


def cluster_bootstrap_ratio(numerators: Iterable[float], denominators: Iterable[float],
                            clusters: Iterable[str], replicates: int = 5000,
                            alpha: float = 0.05, seed: int = 20261101) -> dict:
    """Stake-weighted ROI with whole season-week clusters resampled."""
    n, c, unique = _cluster_arrays(numerators, clusters)
    d = np.asarray(list(denominators), float)
    if d.shape != n.shape or not np.all(np.isfinite(d)) or np.any(d <= 0):
        raise ContractError("Ratio denominators must be positive and aligned")
    if replicates < 100 or not 0 < alpha < 1:
        raise ContractError("Bootstrap needs >=100 replicates and 0<alpha<1")
    num = np.array([n[c == k].sum() for k in unique])
    den = np.array([d[c == k].sum() for k in unique])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, unique.size, size=(replicates, unique.size))
    ratios = num[idx].sum(axis=1) / den[idx].sum(axis=1)
    return {"mean": float(n.sum() / d.sum()), "lower": float(np.quantile(ratios, alpha / 2)),
            "upper": float(np.quantile(ratios, 1 - alpha / 2)), "clusters": int(unique.size),
            "replicates": replicates, "alpha": alpha}


def cluster_sign_permutation(values: Iterable[float], clusters: Iterable[str],
                             replicates: int = 5000, seed: int = 20261101) -> float:
    v, c, unique = _cluster_arrays(values, clusters)
    sums = np.array([v[c == k].sum() for k in unique])
    counts = np.array([np.sum(c == k) for k in unique])
    observed = v.sum() / v.size
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(replicates, unique.size))
    null = (signs * sums).sum(axis=1) / counts.sum()
    return float((1 + np.sum(null >= observed)) / (replicates + 1))


def cluster_sign_permutation_ratio(numerators: Iterable[float], denominators: Iterable[float],
                                   clusters: Iterable[str], replicates: int = 5000,
                                   seed: int = 20261101) -> float:
    n, c, unique = _cluster_arrays(numerators, clusters)
    d = np.asarray(list(denominators), float)
    if d.shape != n.shape or not np.all(np.isfinite(d)) or np.any(d <= 0):
        raise ContractError("Ratio denominators must be positive and aligned")
    num = np.array([n[c == k].sum() for k in unique])
    den = np.array([d[c == k].sum() for k in unique])
    observed = n.sum() / d.sum()
    rng = np.random.default_rng(seed)
    signs = rng.choice([-1.0, 1.0], size=(replicates, unique.size))
    null = (signs * num).sum(axis=1) / den.sum()
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


def _freeze_ok(protocol: Protocol, freeze: ProtocolFreeze | None) -> bool:
    return (freeze is not None and freeze.protocol_digest == protocol.digest()
            and tuple(freeze.family) == tuple(protocol.family)
            and freeze.baseline_method == protocol.baseline_method)


def _indexes(bundle: InputBundle, forward: InputBundle | None):
    games, quotes, players, forecasts = bundle.indexes()
    if forward:
        fg, fq, fp, ff = forward.indexes()
        games.update(fg)
        quotes.update(fq)
        players.update(fp)
        forecasts.update(ff)
    return games, quotes, players, forecasts


def _audit_bets(bets, registry, games, quotes, players, forecasts):
    for bet in bets:
        registry.audit_bet(bet, quotes, games, players, forecasts)


def _raw_strategy(strategy_id: str, holdout: list[SettledBet], fwd: list[SettledBet],
                  protocol: Protocol, registry: EvidenceRegistry, freeze: ProtocolFreeze | None,
                  games, quotes, players, forecasts) -> tuple[StrategyReport, float]:
    metrics: dict = {"holdout_bets": len(holdout), "forward_bets": len(fwd)}
    gates: list[GateResult] = []
    frozen = _freeze_ok(protocol, freeze)
    gates.append(_gate("preregistration", frozen if freeze is not None else None,
                       "Project freeze digest, complete family, model versions and baseline method must be fixed before evaluation"))

    evidence_ok = True
    try:
        ids = [b.bet_id for b in holdout + fwd]
        if len(ids) != len(set(ids)):
            raise ContractError("Duplicate bet id")
        _audit_bets(holdout + fwd, registry, games, quotes, players, forecasts)
        if frozen:
            for b in holdout + fwd:
                f = forecasts[b.forecast_id]
                if f.model_version not in freeze.model_versions:
                    raise ContractError("Forecast model version is outside the freeze")
    except ContractError as exc:
        evidence_ok = False
        metrics["evidence_error"] = str(exc)
    gates.append(_gate("evidence_and_rights", evidence_ok if (holdout or fwd) else None,
                       "Every bet resolves to licensed official evidence, dated operator rules, an executable accepted quote and a hashed forecast"))

    chrono = None
    if holdout or fwd:
        chrono = evidence_ok
        for b in holdout + fwd:
            f = forecasts.get(b.forecast_id or "")
            if f is None or utc(f.features_available_at) > utc(f.issued_at) or utc(f.issued_at) > utc(b.accepted_at) or utc(b.accepted_at) >= utc(b.kickoff):
                chrono = False
            if b.market == "parlay" and len(set(b.legs)) != len(b.legs):
                chrono = False
    gates.append(_gate("chronology", chrono,
                       "Features <= forecast <= acceptance < kickoff; no duplicate parlay legs; disjoint seasonal windows"))

    clusters = len({b.cluster for b in holdout})
    seasons = len({b.cluster.split("-")[0] for b in holdout})
    metrics.update(holdout_clusters=clusters, holdout_seasons=seasons)
    sample_ok = (len(holdout) >= protocol.min_holdout_bets and clusters >= protocol.min_holdout_clusters
                 and seasons >= protocol.min_holdout_seasons) if holdout else None
    gates.append(_gate("sample", sample_ok, "Minimum untouched holdout bets, season-week clusters and seasons"))

    usable = [b for b in holdout if b.result in {"win", "loss"}]
    prob_ok = None
    if usable and evidence_ok:
        try:
            fs = [forecasts[b.forecast_id] for b in usable]
            if any(f.baseline_p_win is None for f in fs):
                raise ContractError("Missing baseline probability")
            p = [f.p_action_win for f in fs]
            pb = [f.baseline_p_win for f in fs]
            y = [1.0 if b.result == "win" else 0.0 for b in usable]
            metrics["brier"] = brier(p, y)
            metrics["log_loss"] = log_loss(p, y)
            metrics["baseline_brier"] = brier(pb, y)
            metrics["baseline_log_loss"] = log_loss(pb, y)
            metrics["calibration"] = calibration_bins(p, y)
            diff = [(bi - yi) ** 2 - (pi - yi) ** 2 for bi, pi, yi in zip(pb, p, y)]
            skill = cluster_bootstrap_mean(diff, [b.cluster for b in usable], protocol.bootstrap_replicates,
                                           protocol.alpha, protocol.seed)
            metrics["paired_brier_skill"] = skill
            prob_ok = skill["lower"] > 0 and metrics["log_loss"] <= metrics["baseline_log_loss"]
        except (ContractError, KeyError):
            prob_ok = None
    gates.append(_gate("probability_quality", prob_ok,
                       "Matched forecast artifacts; action-conditional paired Brier improvement lower bound > 0 and no worse log loss"))

    pval = 1.0
    econ_ok = None
    if holdout and evidence_ok:
        try:
            ci = cluster_bootstrap_ratio([b.profit for b in holdout], [b.stake for b in holdout],
                                         [b.cluster for b in holdout], protocol.bootstrap_replicates,
                                         protocol.alpha, protocol.seed)
            metrics["roi"] = ci
            pval = cluster_sign_permutation_ratio([b.profit for b in holdout], [b.stake for b in holdout],
                                                  [b.cluster for b in holdout], protocol.bootstrap_replicates, protocol.seed + 1)
            metrics["cluster_p"] = pval
            econ_ok = ci["lower"] > 0 and ci["mean"] >= protocol.min_roi
        except ContractError:
            econ_ok = None
    gates.append(_gate("economics", econ_ok, "Stake-weighted holdout net ROI lower confidence bound > 0 and mean ROI >= protocol floor"))
    gates.append(_gate("multiplicity", None, "Computed after the complete registered family is evaluated"))

    stability_ok = None
    if holdout and evidence_ok:
        by_season: dict[str, list[float]] = {}
        for b in holdout:
            by_season.setdefault(b.cluster.split("-")[0], []).append(b.profit)
        season_profit = {s: float(sum(v)) for s, v in by_season.items()}
        total_profit = float(sum(season_profit.values()))
        positive_share = sum(v > 0 for v in season_profit.values()) / len(season_profit)
        best_share = max(season_profit.values()) / total_profit if total_profit > 0 else None
        stressed = [(b.profit - b.stake * protocol.decimal_slippage) if b.result == "win" else b.profit for b in holdout]
        stress_roi = float(sum(stressed) / sum(b.stake for b in holdout))
        metrics.update(season_profit=season_profit, positive_season_share=positive_share,
                       best_season_profit_share=best_share, stressed_roi=stress_roi)
        stability_ok = positive_share >= 2 / 3 and stress_roi > 0 and (best_share is None or best_share <= 0.5)
    gates.append(_gate("stability", stability_ok,
                       "Positive in >=2/3 holdout seasons, no season >50% of profit, and positive after decimal slippage"))

    risk_ok = None
    if holdout and evidence_ok:
        ordered = sorted(holdout, key=lambda b: (utc(b.kickoff), b.bet_id))
        dd = max_drawdown([b.profit / protocol.unit_stake for b in ordered])
        weekly: dict[str, float] = {}
        for b in holdout:
            weekly[b.cluster] = weekly.get(b.cluster, 0.0) + b.stake / protocol.unit_stake
        max_week = max(weekly.values())
        metrics.update(max_drawdown_units=dd, max_weekly_stake_units=max_week)
        risk_ok = dd <= protocol.max_drawdown_units and max_week <= protocol.max_weekly_stake
    gates.append(_gate("execution_and_risk", risk_ok,
                       "Accepted executable quotes are evidence-verified; drawdown and weekly exposure are within pre-registered unit limits"))

    forward_ok = None
    if fwd:
        forward_ok = evidence_ok and frozen
        forward_ok = forward_ok and len(fwd) >= protocol.min_forward_bets
        forward_ok = forward_ok and len({b.cluster for b in fwd}) >= protocol.min_forward_clusters
        forward_ok = forward_ok and all(int(b.cluster.split("-")[0]) in protocol.forward_seasons for b in fwd)
        forward_ok = forward_ok and all(utc(forecasts[b.forecast_id].issued_at) > utc(freeze.frozen_at) for b in fwd)
        forward_ok = forward_ok and not ({b.bet_id for b in fwd} & {b.bet_id for b in holdout})
        if forward_ok:
            metrics["forward_roi"] = float(sum(b.profit for b in fwd) / sum(b.stake for b in fwd))
            forward_ok = metrics["forward_roi"] > 0
    gates.append(_gate("forward_freeze", forward_ok,
                       "Post-freeze paper/forward sample meets size/cluster minima, stays in forward seasons and has positive net ROI"))

    report = StrategyReport(strategy_id, gates, metrics, False, None)
    return report, pval


def evaluate_family(protocol: Protocol, registry: EvidenceRegistry, bundle: InputBundle,
                    freeze: ProtocolFreeze | None, forward_bundle: InputBundle | None = None) -> list[StrategyReport]:
    games, quotes, players, forecasts = _indexes(bundle, forward_bundle)
    reports: list[StrategyReport] = []
    pvals: list[float] = []
    for sid in protocol.family:
        holdout = [b for b in bundle.bets if b.strategy_id == sid and int(b.cluster.split("-")[0]) in protocol.holdout_seasons]
        fwd = [b for b in (forward_bundle.bets if forward_bundle else []) if b.strategy_id == sid]
        report, pval = _raw_strategy(sid, holdout, fwd, protocol, registry, freeze, games, quotes, players, forecasts)
        reports.append(report)
        pvals.append(pval)
    adj = bonferroni(pvals)
    bh = benjamini_hochberg(pvals)
    for i, report in enumerate(reports):
        has_holdout = report.metrics.get("holdout_bets", 0) > 0 and report.metrics.get("holdout_clusters", 0) >= 2
        evidence = next(g for g in report.gates if g.name == "evidence_and_rights")
        ok = adj[i] <= protocol.alpha if has_holdout and evidence.status == "pass" else None
        report.metrics["bonferroni_p"] = adj[i]
        report.metrics["bh_q"] = bh[i]
        report.gates = [(_gate("multiplicity", ok, "Bonferroni across every registered trial; BH q secondary") if g.name == "multiplicity" else g) for g in report.gates]
        report.eligible = all(g.status == "pass" for g in report.gates)
        report.score = report.metrics.get("roi", {}).get("lower") if report.eligible else None
    return reports


def evaluate_strategy(strategy_id: str, bets: list[SettledBet], forecasts: list[Forecast],
                      protocol: Protocol, registry: EvidenceRegistry,
                      bundle: InputBundle | None = None,
                      freeze: ProtocolFreeze | None = None,
                      forward_bets: list[SettledBet] | None = None) -> StrategyReport:
    """Single-strategy convenience wrapper.

    Multi-strategy families must use evaluate_family so multiplicity is computed
    over the complete family. External p-values and execution booleans are not
    accepted.
    """
    if strategy_id not in protocol.family:
        raise ContractError("Strategy is outside the pre-registered family")
    if bundle is None:
        bundle = InputBundle(bets=bets, forecasts=forecasts)
    forward_bundle = InputBundle(bets=forward_bets or [])
    reports = evaluate_family(protocol, registry, bundle, freeze, forward_bundle)
    report = next(r for r in reports if r.strategy_id == strategy_id)
    if len(protocol.family) > 1:
        report.gates = [(_gate("multiplicity", None, "Use evaluate_family for a multi-strategy registered family") if g.name == "multiplicity" else g) for g in report.gates]
        report.eligible = False
        report.score = None
    return report


def leaderboard(reports: list[StrategyReport], reward_pool: float | None = None) -> list[dict]:
    if reward_pool is not None:
        raise ContractError("Rewards are disabled: no funded pool, sponsor, jurisdiction or payout terms are verified")
    eligible = sorted([r for r in reports if r.eligible],
                      key=lambda r: (-(r.score or -math.inf),
                                     -(r.metrics.get("paired_brier_skill", {}).get("lower") or -math.inf),
                                     r.strategy_id))
    rows = []
    for rank, r in enumerate(eligible, 1):
        rows.append({"rank": rank, "strategy_id": r.strategy_id, "score": r.score,
                     "reward": None, "status": "eligible"})
    for r in reports:
        if not r.eligible:
            rows.append({"rank": None, "strategy_id": r.strategy_id, "score": None,
                         "reward": None, "status": "not_eligible"})
    return rows
