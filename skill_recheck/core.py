#!/usr/bin/env python3
"""skill_lab.core — proper-score skill ranking with uncertainty and control baselines.

Pre-registered display and scoring rules (fixed before any number was computed,
recorded here and on skill_lab/method.html):

R1  Ranked family: singles strategies S1-S8 of the per-bet ledger
    data/derived/bets.csv (markets ATS, TOTAL, ML). S9/S10 are two-leg parlays:
    their published probabilities are products of leg marginals, which the
    joint-evidence gate (C01) forbids ranking on; they are shown unranked.
    S11 futures carry no model probability; skill columns blank, flagged.
R2  Scored subset per strategy: rows with a non-null model_prob and
    outcome != 0. Pushes are excluded from scoring; the excluded count is
    published, never silently dropped.
R3  Proper score: Brier score BS = mean((p - y)^2), y = 1 if outcome > 0 else 0.
    Benchmark-relative skill BSS(x) = 1 - BS_model / BS_x for benchmark x, all
    evaluated on the same events and the same outcomes:
      market  : market_prob as published (proportionally de-vigged closing line);
      coin    : p = 0.5 for every event;
      favourite: p_fav = market_prob of the majority side on that event
                 (p_market if >= 0.5 else 1 - p_market); the outcome y is still
                 the strategy's own side. It answers "did this side choice beat
                 always taking the majority side on these events?"
R4  Uncertainty: cluster bootstrap, 2000 resamples, seed 20261119, two
    clusterings - game (game_id) and week (season, week). BSS is recomputed
    per resample (numerator and denominator both resampled). Reported: 2.5/97.5
    percentiles per clustering, one-sided p = P(BSS* <= 0), and
    ranking_bound = min(lower_game, lower_week) - the more conservative of the
    two lower bounds.
R5  Multiplicity: Benjamini-Hochberg FDR at q = 0.10 across the ranked family
    on the bootstrap p-values (q_skill), plus the Bonferroni threshold
    alpha/m for reference. Eligibility: ranking_bound > 0 AND q_skill <= 0.10.
    No minimum-n rule: the confidence bound carries the sample-size penalty.
R6  Control baselines (C04), always shown with the leaderboard, never ranked:
    coin-flip and majority-side ("favourites only") columns on each strategy's
    own events, plus two global control rows over the full priced closing-line
    universe (2006-2025, data/raw/closing_lines.csv):
      CONTROL majority side: ATS favourite, ML favourite, TOTAL majority side
      (de-vigged over/under probability >= 0.5), at closing prices;
      CONTROL random picks: one seeded realisation (numpy default_rng, seed
      20261119), side drawn 50/50 per event at the chosen side's price.
R7  Two-sided "what would change our mind" field per ranked strategy:
    would-confirm: approximate additional bets at the observed BSS needed for
    the lower bound to reach 0 (delta-method n = (z*se/bss)^2, ceil, minus n
    scored; null when bss <= 0 or already eligible);
    would-overturn: the BSS level at or below which the ranking bound drops to
    0 - z0.95 * se (one-sided z = 1.6448536269514722).
R8  Determinism: no wall clock anywhere. Build identity = SHA-256 of the
    inputs, printed on every page. Two builds on the same inputs are
    byte-identical.

Inputs are the repository's pinned artifacts; nothing is fetched. Every number
a page shows is recomputed by skill_lab/check.py with independent arithmetic.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

SEED = 20261119
N_BOOT = 2000
FDR_Q = 0.10
Z95 = 1.6448536269514722  # one-sided 95% normal quantile
SINGLES = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
COMBOS = ["S9", "S10"]
FUTURES = "S11"


# --------------------------------------------------------------------------- #
# Proper scores
# --------------------------------------------------------------------------- #
def brier(p: np.ndarray, y: np.ndarray) -> float:
    """Mean squared probability error. Both arrays same length, y in {0,1}."""
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def bss(bs_model: float, bs_bench: float) -> float | None:
    """Benchmark-relative Brier skill; undefined when the benchmark score is 0."""
    if bs_bench is None or bs_bench <= 0:
        return None
    return 1.0 - bs_model / bs_bench


def favourite_prob(p_market: np.ndarray) -> np.ndarray:
    """Majority-side probability per event (R3): p if >= .5 else 1 - p."""
    p = np.asarray(p_market, float)
    return np.where(p >= 0.5, p, 1.0 - p)


def clusters_of(keys) -> list[np.ndarray]:
    """Index arrays grouped by identical key (game id or (season, week))."""
    groups: dict = {}
    for i, k in enumerate(keys):
        groups.setdefault(k, []).append(i)
    return [np.asarray(v) for v in groups.values()]


def bootstrap_bss_multi(p_model: np.ndarray, benches: dict[str, np.ndarray],
                        y: np.ndarray, keys, n_boot: int = N_BOOT,
                        seed: int = SEED) -> dict[str, dict]:
    """Cluster-bootstrap distributions of BSS against several benchmarks.

    The same resample index sets are used for every benchmark on a given
    clustering, so the comparisons are paired. keys: the clustering variable
    (game_id for the game clustering; the (season, week) tuple for the week
    clustering). Returns per benchmark: point, ci_low, ci_high, p, se, n.
    """
    p_m = np.asarray(p_model, float)
    yy = np.asarray(y, float)
    bench = {k: np.asarray(v, float) for k, v in benches.items()}
    n = len(yy)
    clusters = clusters_of(keys)
    n_c = len(clusters)
    base_bs_m = brier(p_m, yy)
    base_bs_b = {k: brier(v, yy) for k, v in bench.items()}
    out = {
        k: {"point": bss(base_bs_m, bb), "n": int(n)}
        for k, bb in base_bs_b.items()
    }
    rng = np.random.default_rng(seed)
    sims = {k: np.full(n_boot, np.nan) for k in bench}
    for b in range(n_boot):
        pick = rng.integers(0, n_c, n_c)
        idx = np.concatenate([clusters[i] for i in pick])
        bs_m = brier(p_m[idx], yy[idx])
        for k, v in bench.items():
            bs_b = brier(v[idx], yy[idx])
            if bs_b > 0:
                sims[k][b] = 1.0 - bs_m / bs_b
    for k in bench:
        s = sims[k][~np.isnan(sims[k])]
        if len(s) == 0:
            out[k].update({"ci_low": None, "ci_high": None, "p": None, "se": None})
        else:
            out[k].update({
                "ci_low": float(np.percentile(s, 2.5)),
                "ci_high": float(np.percentile(s, 97.5)),
                "p": float((s <= 0).mean()),
                "se": float(np.std(s, ddof=1)) if len(s) > 1 else None,
            })
    return out


def bootstrap_bss(p_model: np.ndarray, p_bench: np.ndarray, y: np.ndarray,
                  keys, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Single-benchmark wrapper around bootstrap_bss_multi."""
    r = bootstrap_bss_multi(p_model, {"bench": p_bench}, y, keys, n_boot, seed)
    return r["bench"]


# --------------------------------------------------------------------------- #
# Multiplicity
# --------------------------------------------------------------------------- #
def bh_fdr(pvals: dict[str, float | None], q: float = FDR_Q) -> dict[str, float]:
    """Benjamini-Hochberg q-values; None inputs are skipped (family shrinks)."""
    items = [(k, v) for k, v in pvals.items() if v is not None and not math.isnan(v)]
    m = len(items)
    out: dict[str, float] = {}
    if m == 0:
        return out
    ordered = sorted(items, key=lambda kv: kv[1])
    prev = 1.0
    for rank in range(m, 0, -1):
        key, p = ordered[rank - 1]
        val = min(prev, p * m / rank)
        out[key] = val
        prev = val
    return out


# --------------------------------------------------------------------------- #
# A16 two-sided field
# --------------------------------------------------------------------------- #
def change_mind(bss_point: float | None, se: float | None, n: int,
                bound: float | None) -> dict:
    """Two-sided what-would-change-our-mind numbers (R7). Deterministic."""
    if bss_point is None or se is None or se <= 0:
        return {"confirm_more_bets": None, "overturn_level": None}
    overturn = Z95 * se
    confirm = None
    if bss_point > 0:
        need = (Z95 * se / bss_point) ** 2
        more = math.ceil(need) - int(n)
        confirm = max(more, 0)
    return {"confirm_more_bets": confirm, "overturn_level": overturn,
            "eligible_now": bool(bound is not None and bound > 0)}


# --------------------------------------------------------------------------- #
# Settlement arithmetic (mirrors line_lab.markets conventions)
# --------------------------------------------------------------------------- #
def american_to_decimal(price: float) -> float:
    price = float(price)
    if price == 0:
        return 2.0  # even money, coded as 0 in the pinned dataset
    return 1.0 + (price / 100.0 if price > 0 else 100.0 / abs(price))


def devig_two_way(p1: float, p2: float) -> tuple[float, float]:
    """Proportional de-vig of two American prices -> (p_side1, p_side2)."""
    i1, i2 = 1.0 / american_to_decimal(p1), 1.0 / american_to_decimal(p2)
    total = i1 + i2
    return i1 / total, i2 / total


def pnl(price: float, outcome: int, stake: float = 1.0) -> float:
    """Profit of one settled bet at American odds: +profit, -stake, 0 push."""
    if outcome == 0:
        return 0.0
    dec = american_to_decimal(price)
    return stake * (dec - 1.0) if outcome > 0 else -stake


def roi_ci(pnls, keys, n_boot: int = N_BOOT, seed: int = SEED) -> dict:
    """Week-cluster bootstrap CI and one-sided p for mean profit per bet."""
    a = np.asarray(pnls, float)
    if len(a) == 0:
        return {"point": None, "ci_low": None, "ci_high": None, "p": None}
    cs = clusters_of(keys)
    rng = np.random.default_rng(seed)
    sims = np.empty(n_boot)
    n_c = len(cs)
    for b in range(n_boot):
        pick = rng.integers(0, n_c, n_c)
        idx = np.concatenate([cs[i] for i in pick])
        sims[b] = a[idx].mean()
    return {
        "point": float(a.mean()),
        "ci_low": float(np.percentile(sims, 2.5)),
        "ci_high": float(np.percentile(sims, 97.5)),
        "p": float((sims <= 0).mean()),
    }
