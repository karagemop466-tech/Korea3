"""Shared helpers: paths, odds math, IO, statistics primitives.

Only numpy is required for the maths (kept dependency-light on purpose so a
reviewer can re-run everything from a clean machine).
"""
import json
import math
import os

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")
DERIVED = os.path.join(ROOT, "data", "derived")
SITE_DIR = os.path.join(ROOT, "site")
DOCS_DATA = os.path.join(ROOT, "site", "data")
REPO_URL = "https://github.com/karagemop466-tech/Korea3"


# --------------------------------------------------------------------------
# odds
# --------------------------------------------------------------------------
def american_to_decimal(odds):
    """-110 -> 1.909..., +150 -> 2.5. Returns nan for missing/zero."""
    o = np.asarray(odds, dtype=float)
    out = np.full(o.shape, np.nan)
    neg = o < 0
    pos = o > 0
    out[neg] = 1.0 + (100.0 / np.abs(o[neg]))
    out[pos] = 1.0 + (o[pos] / 100.0)
    return out


def american_to_prob(odds):
    d = american_to_decimal(odds)
    return np.where(np.isnan(d), np.nan, 1.0 / d)


def american_to_payout(odds):
    """Profit per 1 unit staked (decimal - 1)."""
    return american_to_decimal(odds) - 1.0


def devig_two_way(p_a, p_b):
    """Multiplicative (proportional) de-vig of a two-way market."""
    s = p_a + p_b
    return p_a / s, p_b / s, s - 1.0  # last value = market hold


def prob_from_spread(mu, sigma, line):
    """P(outcome > line) under a normal model; handles integer pushes.

    Returns (p_win, p_push).  For half-point lines p_push is 0.
    """
    from math import erf, sqrt

    def Phi(x):
        return 0.5 * (1.0 + erf(x / sqrt(2.0)))

    p_win = 1.0 - Phi((line - mu) / sigma)
    if abs(line - round(line)) < 1e-9:  # integer line -> push possible
        p_push = Phi((line + 0.5 - mu) / sigma) - Phi((line - 0.5 - mu) / sigma)
        p_win = p_win - p_push * 0.5  # half of the push mass is "over the line"
        p_win = max(p_win, 0.0)
        return p_win, p_push
    return p_win, 0.0


# --------------------------------------------------------------------------
# statistics
# --------------------------------------------------------------------------
def bootstrap_mean_ci(x, n_boot=10000, alpha=0.05, seed=7):
    """Percentile bootstrap CI for the mean of x."""
    x = np.asarray([v for v in x if not (v is None or (isinstance(v, float) and math.isnan(v)))], dtype=float)
    if len(x) < 5:
        return None, None
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    means = x[idx].mean(axis=1)
    return float(np.quantile(means, alpha / 2)), float(np.quantile(means, 1 - alpha / 2))


def cluster_bootstrap_ci(values, clusters, n_boot=5000, alpha=0.05, seed=11):
    """Bootstrap resampling whole clusters (e.g. seasons) -- honest for bets that
    share a season-level environment."""
    values = np.asarray(values, dtype=float)
    clusters = np.asarray(clusters)
    keys = np.unique(clusters)
    if len(keys) < 3:
        return None, None
    groups = [values[clusters == k] for k in keys]
    rng = np.random.default_rng(seed)
    out = np.empty(n_boot)
    for i in range(n_boot):
        pick = rng.integers(0, len(groups), len(groups))
        out[i] = np.concatenate([groups[j] for j in pick]).mean()
    return float(np.quantile(out, alpha / 2)), float(np.quantile(out, 1 - alpha / 2))


def sharpe(profits):
    p = np.asarray(profits, dtype=float)
    if len(p) < 2 or p.std(ddof=1) == 0:
        return float("nan")
    return float(p.mean() / p.std(ddof=1))


def skew_kurt(x):
    x = np.asarray(x, dtype=float)
    n = len(x)
    if n == 0:
        return 0.0, 3.0
    m = x.mean()
    s = x.std(ddof=0)
    if s == 0:
        return 0.0, 3.0
    sx = float(((x - m) ** 3).mean() / s ** 3)
    kx = float(((x - m) ** 4).mean() / s ** 4)
    return sx, kx


def norm_cdf(z):
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def norm_ppf(p):
    """Acklam-style rational approximation, good to ~1e-9."""
    if p <= 0:
        return -np.inf
    if p >= 1:
        return np.inf
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


def bh_fdr(pvals, q=0.10):
    """Benjamini-Hochberg. Returns list of booleans (reject null)."""
    p = np.asarray(pvals, dtype=float)
    n = len(p)
    order = np.argsort(p)
    ranked = p[order]
    thresh = q * (np.arange(1, n + 1) / n)
    below = ranked <= thresh
    reject = np.zeros(n, dtype=bool)
    if below.any():
        kmax = np.max(np.where(below)[0])
        reject[order[:kmax + 1]] = True
    return reject.tolist()


def deflated_sharpe(sr, n_obs, skew, kurt, n_trials, var_sr_trials=None):
    """Bailey & Lopez de Prado deflated Sharpe ratio -> probability that the
    observed Sharpe exceeds what the best of `n_trials` zero-skill trials would show.

    sr      : per-observation Sharpe ratio
    n_obs   : number of observations
    n_trials: number of strategies tried (multiple-testing haircut)
    """
    if n_trials < 1 or n_obs < 3 or not np.isfinite(sr):
        return float("nan")
    if var_sr_trials is None:
        var_sr_trials = 1.0 / n_obs  # conservative: variance of a zero-skill SR estimate
    e = 0.5772156649
    z = (1 - e) * norm_ppf(1 - 1.0 / n_trials) + e * norm_ppf(1 - 1.0 / (n_trials * math.e))
    sr0 = math.sqrt(var_sr_trials) * z
    denom = math.sqrt(max(1e-9, 1 - skew * sr + (kurt - 1) / 4.0 * sr ** 2))
    return norm_cdf((sr - sr0) * math.sqrt(n_obs - 1) / denom)


# --------------------------------------------------------------------------
# io
# --------------------------------------------------------------------------
def write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=1, default=_default)
    return path


def _default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        v = float(o)
        return None if math.isnan(v) or math.isinf(v) else v
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(str(type(o)))


def r(x, n=4):
    """Safe round -> None for nan/inf."""
    try:
        if x is None:
            return None
        x = float(x)
        if math.isnan(x) or math.isinf(x):
            return None
        return round(x, n)
    except (TypeError, ValueError):
        return None
