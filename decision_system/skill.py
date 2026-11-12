"""Skill versus luck: the statistics that decide what may be rewarded.

The brief asks for a leaderboard competition where luck is removed and only
selectively skill-based strategies can earn a reward.  That turns a betting
backtest into a multiple-testing problem, and this module makes the problem
explicit instead of hiding it behind one ROI number.

Definitions used everywhere on the site
--------------------------------------
edge            mean profit per $1 staked (ROI as a fraction)
break-even      the win rate a price requires: 110/210 = 0.523810 at -110
luck band       the distribution of *the best of k* strategies when none of the k
                has an edge.  Simulated, not assumed.
deflated Sharpe DSR: P(true Sharpe > 0) after accounting for how many strategies
                were tried, how long each series is, and how non-normal its
                returns are (Bailey & Lopez de Prado 2014).  Computed here from
                the closed form with skew and kurtosis moments.
skill test      every pre-registered strategy must pass ALL of:
                  L1  positive point estimate over the full priced window
                  L2  bootstrap 95% CI lower bound > 0 (NIST bootstrap reference)
                  L3  survives a block bootstrap by season (not one lucky year)
                  L4  out-of-sample: the same sign after the pre-registered cut
                  L5  clears the no-skill band for the number of strategies tried
                  L6  deflated Sharpe probability >= 0.95
                  L7  holdout season untouched during selection stays positive
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd

EULER_GAMMA = 0.5772156649015329


# --------------------------------------------------------------------------- basics
def implied_prob(american: float) -> float:
    """Implied probability of American odds (no vig removal)."""
    a = float(american)
    if a == 0:
        return float("nan")
    return (-a) / (-a + 100.0) if a < 0 else 100.0 / (a + 100.0)


def decimal_odds(american: float) -> float:
    """Total return per 1 unit staked, stake included (-110 -> 1.909...)."""
    a = float(american)
    return 1.0 + (100.0 / -a if a < 0 else a / 100.0)


def pnl_per_unit(price: float, won: bool, push: bool = False) -> float:
    """Profit per 1 unit staked, following the operator's push rule."""
    if push:
        return 0.0
    return decimal_odds(price) - 1.0 if won else -1.0


def break_even_win_rate(price: float = -110.0) -> float:
    """Win probability at which the expected value of the bet is exactly zero."""
    return implied_prob(price)


def n_bets_for_edge(edge: float, sd: float = 0.9549, alpha: float = 0.05,
                    power: float = 0.80, sides: int = 2) -> int:
    """Settled bets needed to detect ``edge`` on the mean return.

    ``sd`` defaults to the standard deviation of a -110 bet's per-unit return,
    sqrt(0.5238*(0.9091)^2 + 0.4762*1) = 0.9549.  ``sides=1`` reproduces the
    one-sided convention used by earlier sessions (which reported ~6,200 bets for a
    3% edge); ``sides=2`` is the stricter, default convention here.  The page
    publishes both so the difference cannot be mistaken for a contradiction.
    """
    z_a = _norm_ppf(1 - alpha / 2) if sides == 2 else _norm_ppf(1 - alpha)
    z_b = 0.8416212335729143 if power == 0.80 else _norm_ppf(power)
    return int(math.ceil(((z_a + z_b) * sd / edge) ** 2))


def _norm_ppf(p: float) -> float:
    # Acklam's rational approximation; plenty for reporting sample sizes.
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


# ---------------------------------------------------------------------- inference
def bootstrap_ci(x: np.ndarray, n_boot: int = 10000, alpha: float = 0.05,
                 seed: int = 20261112) -> tuple[float, float, float]:
    """Percentile bootstrap of the mean. Returns (mean, lo, hi)."""
    x = np.asarray(x, dtype=float)
    if x.size < 2:
        return (float(x.mean()) if x.size else float("nan"), float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, x.size, size=(n_boot, x.size))
    means = x[idx].mean(axis=1)
    lo, hi = np.quantile(means, [alpha / 2, 1 - alpha / 2])
    return float(x.mean()), float(lo), float(hi)


def block_bootstrap_seasons(df: pd.DataFrame, value_col: str, season_col: str = "season",
                            n_boot: int = 2000, seed: int = 20261112) -> tuple[float, float]:
    """Resample whole seasons with replacement (keeps within-season dependence)."""
    seasons = df[season_col].unique()
    if len(seasons) < 3:
        return (float("nan"), float("nan"))
    rng = np.random.default_rng(seed)
    means = []
    grouped = {s: g[value_col].to_numpy() for s, g in df.groupby(season_col)}
    for _ in range(n_boot):
        pick = rng.choice(seasons, size=len(seasons), replace=True)
        pooled = np.concatenate([grouped[s] for s in pick])
        means.append(pooled.mean())
    lo, hi = np.quantile(means, [0.025, 0.975])
    return float(lo), float(hi)


def no_skill_band(n_strategies: int, n_bets: int, price: float = -110.0,
                  n_sim: int = 20000, seed: int = 20261112) -> dict:
    """Distribution of the BEST of k zero-edge strategies with the same bet count.

    Every strategy is simulated with the break-even win probability of the price, so
    the expected ROI is exactly zero before vig; with vig applied (-110 both ways)
    the mean is the negative hold.  This is the band any leaderboard winner must beat.
    """
    p = break_even_win_rate(price)
    rng = np.random.default_rng(seed)
    wins = rng.binomial(n_bets, p, size=(n_sim, n_strategies))
    roi = wins * pnl_per_unit(price, True) + (n_bets - wins) * (-1.0)
    roi = roi / n_bets
    best = roi.max(axis=1)
    return {
        "n_strategies": int(n_strategies),
        "n_bets": int(n_bets),
        "price": float(price),
        "break_even": round(p, 6),
        "expected_roi_zero_vig": 0.0,
        "sim_mean_best": round(float(best.mean()), 4),
        "sim_p05_best": round(float(np.quantile(best, 0.05)), 4),
        "sim_p95_best": round(float(np.quantile(best, 0.95)), 4),
        "sim_p99_best": round(float(np.quantile(best, 0.99)), 4),
        "share_of_sims_with_a_profitable_winner": round(float((best > 0).mean()), 4),
        "simulations": int(n_sim),
    }


def deflated_sharpe(returns: np.ndarray, n_trials: int) -> dict:
    """Bailey & Lopez de Prado (2014) deflated Sharpe ratio.

    ``returns`` is a per-bet return series (not annualised); the Sharpe is taken in
    per-bet units, which is the natural unit for a betting leaderboard.  The expected
    maximum Sharpe of ``n_trials`` independent zero-skill trials is subtracted before
    the normal CDF is applied.
    """
    r = np.asarray(returns, dtype=float)
    n = r.size
    if n < 3 or np.std(r, ddof=1) == 0:
        return {"sharpe": float("nan"), "deflated": float("nan"), "sr0": float("nan")}
    mu, sd = r.mean(), r.std(ddof=1)
    sr = mu / sd
    skew = float(pd.Series(r).skew())
    kurt = float(pd.Series(r).kurt()) + 3.0  # pandas returns excess kurtosis
    trials = max(int(n_trials), 2)
    e = EULER_GAMMA
    sr0 = math.sqrt(1.0 / (n - 1)) * (
        (1 - e) * _norm_ppf(1 - 1.0 / trials) + e * _norm_ppf(1 - 1.0 / (trials * math.e)))
    denom = math.sqrt(max(1e-12, 1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2))
    z = (sr - sr0) * math.sqrt(n - 1) / denom
    return {
        "sharpe": round(float(sr), 5),
        "sr0": round(float(sr0), 5),
        "skew": round(skew, 4),
        "kurtosis": round(kurt, 4),
        "deflated": round(float(0.5 * (1 + math.erf(z / math.sqrt(2)))), 5),
    }


# ------------------------------------------------------------------ strategy audit
def audit_strategy(bets: pd.DataFrame, name: str, strategy_id: str,
                   n_trials: int, cut_season: int = 2019,
                   holdout_from: int = 2024, n_boot: int = 10000) -> dict:
    """Run the seven skill gates on one settled selection set.

    ``bets`` needs columns: season, pnl, price, outcome (1 win / 0 loss), plus an
    optional ``week`` for block bootstraps.
    """
    b = bets.sort_values(["season", "week"] if "week" in bets else ["season"]).copy()
    b["pnl"] = b["pnl"].astype(float)
    r = b["pnl"].to_numpy()
    n = r.size
    mean = float(r.mean()) if n else float("nan")
    ci_mean, ci_lo, ci_hi = bootstrap_ci(r, n_boot=n_boot)
    sb_lo, sb_hi = block_bootstrap_seasons(b, "pnl", n_boot=min(n_boot, 2000))
    oos = b[b.season > cut_season]["pnl"]
    holdout = b[b.season >= holdout_from]["pnl"]
    band = no_skill_band(n_trials, max(n, 1), price=-110.0, n_sim=4000)
    ds = deflated_sharpe(r, n_trials)

    gates = {
        "L1_positive_full_sample": bool(n > 0 and mean > 0),
        "L2_bootstrap_ci_above_zero": bool(np.isfinite(ci_lo) and ci_lo > 0),
        "L3_season_block_ci_above_zero": bool(np.isfinite(sb_lo) and sb_lo > 0),
        "L4_out_of_sample_sign": bool(len(oos) > 0 and oos.mean() > 0),
        "L5_beats_no_skill_band": bool(n > 0 and mean > band["sim_p95_best"]),
        "L6_deflated_sharpe_ge_095": bool(ds["deflated"] == ds["deflated"] and ds["deflated"] >= 0.95),
        "L7_holdout_positive": bool(len(holdout) > 0 and holdout.mean() > 0),
    }
    return {
        "strategy_id": strategy_id,
        "name": name,
        "n_bets": int(n),
        "first_season": int(b.season.min()) if n else None,
        "last_season": int(b.season.max()) if n else None,
        "mean_pnl_per_unit": round(mean, 5) if n else None,
        "roi_pct": round(100 * mean, 3) if n else None,
        "boot_ci95_pct": [round(100 * ci_lo, 3), round(100 * ci_hi, 3)] if n else None,
        "season_block_ci95_pct": [round(100 * sb_lo, 3), round(100 * sb_hi, 3)]
                                  if np.isfinite(sb_lo) else None,
        "oos_mean_pct": round(100 * float(oos.mean()), 3) if len(oos) else None,
        "oos_n": int(len(oos)),
        "holdout_mean_pct": round(100 * float(holdout.mean()), 3) if len(holdout) else None,
        "holdout_n": int(len(holdout)),
        "win_rate": round(float((b.outcome == 1).mean()), 5) if n else None,
        "break_even_win_rate": round(break_even_win_rate(-110.0), 6),
        "sharpe": ds["sharpe"],
        "deflated_sharpe": ds["deflated"],
        "expected_max_sharpe_zero_skill": ds["sr0"],
        "gates": gates,
        "gates_passed": int(sum(gates.values())),
        "reward_eligible": bool(all(gates.values())),
        "no_skill_band": band,
    }


def bonferroni_alpha(n_trials: int, alpha: float = 0.05) -> float:
    return alpha / max(n_trials, 1)


def fdr_bh(pvals: list[float], q: float = 0.05) -> dict:
    """Benjamini-Hochberg step-up; returns rejected mask and the q values."""
    p = np.asarray(pvals, dtype=float)
    m = p.size
    order = np.argsort(p)
    ranked = p[order]
    qvals = ranked * m / np.arange(1, m + 1)
    qvals = np.minimum.accumulate(qvals[::-1])[::-1]
    reject_sorted = qvals <= q
    reject = np.zeros(m, dtype=bool)
    reject[order] = reject_sorted
    out = np.zeros(m)
    out[order] = qvals
    return {"reject": reject.tolist(), "qvalues": np.round(out, 6).tolist()}
