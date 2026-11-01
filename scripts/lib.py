"""lib.py — shared, dependency-light statistics + provenance helpers.

Every function here is deliberately explicit so that any number published on the
site can be traced to a formula a reader can re-implement by hand.

Statistical choices (documented, not tuned):
  * Break-even win rate at -110 prices is 110/210 = 52.3810%  (price cited in
    research/sources.md, source: NFL official support article on point spreads).
  * Confidence intervals: percentile bootstrap, 10,000 resamples, fixed seed
    (20261101) so results are reproducible.
  * Multiple-testing: Benjamini-Hochberg false-discovery-rate control across the
    whole tested signal family, because we test many rules at once.
  * Empirical Bayes shrinkage: moment-matched prior variance tau^2 computed from
    the observed dispersion of edges across the family; the shrunk edge is the
    part of an observed edge that is not attributable to sampling luck.
"""

from __future__ import annotations

import hashlib
import json
import math
import os

import numpy as np
from scipy import stats

SEED = 20261101
BREAKEVEN_110 = 110.0 / 210.0  # 0.5238095238095238


# ---------------------------------------------------------------- provenance
def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def provenance() -> dict:
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(root, "data", "provenance.json"), encoding="utf-8") as fh:
        return json.load(fh)


def row_source_url(filename: str) -> str:
    """Blob URL, pinned to the exact commit, for a raw data file."""
    p = provenance()
    return p["primary_dataset"]["files"][filename]["row_source_template"]


# ------------------------------------------------------------------ payoffs
def payout_per_unit(odds: float) -> float:
    """Profit on a 1-unit stake. American odds. -110 -> 0.9090909..., +150 -> 1.5"""
    odds = float(odds)
    if odds < 0:
        return 100.0 / abs(odds)
    return odds / 100.0


def breakeven(odds: float) -> float:
    b = payout_per_unit(odds)
    return 1.0 / (1.0 + b)


# ---------------------------------------------------------------- inference
def binom_p(wins: int, n: int, p0: float = BREAKEVEN_110, alternative: str = "greater") -> float:
    """One-sided exact binomial test that the true win rate exceeds break-even."""
    if n <= 0:
        return float("nan")
    res = stats.binomtest(int(wins), int(n), p0, alternative=alternative)
    return float(res.pvalue)


def binom_pvalue_wrap(wins: int, n: int, p0: float = BREAKEVEN_110) -> float:
    """Alias used by signals.py: one-sided exact binomial p-value vs break-even."""
    return binom_p(wins, n, p0, alternative="greater")


def wilson_ci(wins: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    if n <= 0:
        return (float("nan"), float("nan"))
    z = stats.norm.ppf(1 - alpha / 2)
    p = wins / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (c - h, c + h)


def boot_roi_ci(profits: np.ndarray, n_boot: int = 10000, alpha: float = 0.05) -> tuple[float, float]:
    """Percentile bootstrap CI for mean profit per bet (ROI). Seeded -> reproducible."""
    profits = np.asarray(profits, dtype=float)
    if profits.size == 0:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, profits.size, size=(n_boot, profits.size))
    means = profits[idx].mean(axis=1)
    return (float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2)))


def coinflip_pvalue(profits: np.ndarray, p0: float = BREAKEVEN_110, n_sims: int = 20000) -> float:
    """Monte-Carlo answer to: 'how often would a pure coin-flip bettor at break-even
    skill produce at least this much profit over this many bets?'
    This is the plain-language "luck test" version of the binomial p-value."""
    profits = np.asarray(profits, dtype=float)
    if profits.size == 0:
        return float("nan")
    win_pay = float(profits[profits > 0].mean()) if np.any(profits > 0) else 0.9
    lose_pay = float(profits[profits < 0].mean()) if np.any(profits < 0) else -1.0
    rng = np.random.default_rng(SEED + 1)
    n = profits.size
    draws = rng.random((n_sims, n)) < p0
    sums = np.where(draws, win_pay, lose_pay).sum(axis=1)
    return float((sums >= profits.sum()).mean())


def bh_fdr(pvals: list[float], alpha: float = 0.10) -> tuple[list[float], list[bool]]:
    """Benjamini-Hochberg q-values and reject flags."""
    p = np.asarray(pvals, dtype=float)
    m = p.size
    order = np.argsort(p)
    ranked = p[order]
    q = np.empty(m, dtype=float)
    prev = 1.0
    for i in range(m - 1, -1, -1):
        val = ranked[i] * m / (i + 1)
        prev = min(prev, val)
        q[order[i]] = prev
    return ([float(x) for x in q], [bool(x <= alpha) for x in q])


def empirical_bayes_tau2(edges: np.ndarray, ses: np.ndarray) -> float:
    """Moment-matched prior variance of true edges across a tested family.

    Var(observed) = Var(true) + E[se^2]  ->  tau^2 = max(0, Var(obs) - mean(se^2)).
    A tau^2 of 0 means: the spread of measured edges is fully explained by
    sampling noise, i.e. 'it is all luck' and every shrunk edge collapses to 0.
    """
    edges = np.asarray(edges, float)
    ses = np.asarray(ses, float)
    ok = np.isfinite(edges) & np.isfinite(ses)
    edges, ses = edges[ok], ses[ok]
    if edges.size < 3:
        return 0.0
    return float(max(0.0, np.var(edges, ddof=1) - np.mean(ses ** 2)))


def shrink_edge(edge: float, se: float, tau2: float, n_eff: float | None = None) -> float:
    """Posterior mean of the true edge under a N(0, tau^2) prior."""
    if not np.isfinite(edge) or not np.isfinite(se) or se <= 0:
        return 0.0
    return float(edge * tau2 / (tau2 + se ** 2))


def skill_z(wins: int, n: int, p0: float = BREAKEVEN_110) -> float:
    if n <= 0:
        return float("nan")
    return float((wins / n - p0) / math.sqrt(p0 * (1 - p0) / n))


def required_n(edge_pp: float, p0: float = BREAKEVEN_110, power: float = 0.80, alpha: float = 0.05) -> int | None:
    """Bets needed to detect an edge of `edge_pp` percentage points at 80% power."""
    if edge_pp <= 0:
        return None
    d = edge_pp
    za = stats.norm.ppf(1 - alpha)
    zb = stats.norm.ppf(power)
    return int(math.ceil(((za + zb) ** 2) * p0 * (1 - p0) / (d ** 2)))


def fmt_pct(x: float, dp: int = 1) -> str:
    return "—" if x is None or not np.isfinite(x) else f"{x*100:.{dp}f}%"


def fmt_num(x: float, dp: int = 2) -> str:
    return "—" if x is None or not np.isfinite(x) else f"{x:.{dp}f}"
