"""Shared loaders/utilities for the NFL signal project.

Pure standard-library Python (no third-party dependencies) so the pipeline can be
re-run anywhere. Every function documented as "point-in-time" uses ONLY
information that was available before the game kicked off.
"""
from __future__ import annotations

import csv
import math
import os
import statistics
from collections import defaultdict
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
REPORTS = os.path.join(ROOT, "reports")


def fnum(v):
    """Parse a float, returning None for empty/unparseable cells (never guesses)."""
    if v is None:
        return None
    v = str(v).strip()
    if v == "" or v.upper() in ("NA", "NAN", "NULL"):
        return None
    try:
        return float(v)
    except ValueError:
        return None


def load_games(path=None):
    """Load the canonical game dataset (nflverse/nfldata games.csv)."""
    path = path or os.path.join(DATA, "games_1999_2026_nflverse.csv")
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            g = dict(r)
            g["season"] = int(r["season"])
            g["week"] = int(r["week"])
            g["home_score"] = fnum(r["home_score"])
            g["away_score"] = fnum(r["away_score"])
            g["spread_line"] = fnum(r["spread_line"])      # home spread, negative = home favoured
            g["total_line"] = fnum(r["total_line"])
            g["away_moneyline"] = fnum(r["away_moneyline"])
            g["home_moneyline"] = fnum(r["home_moneyline"])
            g["away_rest"] = fnum(r["away_rest"])
            g["home_rest"] = fnum(r["home_rest"])
            g["result"] = fnum(r["result"])                # home_score - away_score
            g["total"] = fnum(r["total"])                  # home_score + away_score
            g["over_odds"] = fnum(r["over_odds"])
            g["under_odds"] = fnum(r["under_odds"])
            g["away_spread_odds"] = fnum(r["away_spread_odds"])
            g["home_spread_odds"] = fnum(r["home_spread_odds"])
            g["temp"] = fnum(r["temp"])
            g["wind"] = fnum(r["wind"])
            g["div_game"] = int(fnum(r["div_game"]) or 0)
            g["played"] = g["home_score"] is not None and g["away_score"] is not None
            if g["played"]:
                g["margin"] = g["home_score"] - g["away_score"]
                g["tot"] = g["home_score"] + g["away_score"]
            rows.append(g)
    rows.sort(key=lambda g: (g["gameday"] or "", g["game_id"]))
    return rows


def american_to_decimal(ml):
    """American moneyline -> decimal odds."""
    if ml is None:
        return None
    if ml > 0:
        return 1.0 + ml / 100.0
    return 1.0 + 100.0 / abs(ml)


def american_to_prob(ml):
    """American moneyline -> implied probability (with vig)."""
    if ml is None:
        return None
    if ml > 0:
        return 100.0 / (ml + 100.0)
    return abs(ml) / (abs(ml) + 100.0)


def spread_payout(odds):
    """Payout per 1 unit staked for a spread/total leg at American odds (default -110)."""
    odds = -110.0 if odds is None else odds
    if odds > 0:
        return odds / 100.0
    return 100.0 / abs(odds)


def profit(units_risked, odds):
    return units_risked * spread_payout(odds)


def mean(xs):
    xs = [x for x in xs if x is not None]
    return sum(xs) / len(xs) if xs else None


def stdev(xs):
    xs = [x for x in xs if x is not None]
    return statistics.stdev(xs) if len(xs) > 1 else None


def pearson(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    xs2 = [p[0] for p in pairs]
    ys2 = [p[1] for p in pairs]
    mx, my = mean(xs2), mean(ys2)
    num = sum((x - mx) * (y - my) for x, y in pairs)
    dx = math.sqrt(sum((x - mx) ** 2 for x in xs2))
    dy = math.sqrt(sum((y - my) ** 2 for y in ys2))
    if dx == 0 or dy == 0:
        return None
    return num / (dx * dy)


def phi(a, b):
    """Phi coefficient (Pearson on two binary vectors) = empirical leg correlation."""
    return pearson([1.0 if x else 0.0 for x in a], [1.0 if y else 0.0 for y in b])


def logistic(x):
    if x > 35:
        return 1.0 - 1e-15
    if x < -35:
        return 1e-15
    return 1.0 / (1.0 + math.exp(-x))


def norm_cdf(x):
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def norm_ppf(p, lo=-8.0, hi=8.0):
    for _ in range(200):
        mid = (lo + hi) / 2
        if norm_cdf(mid) < p:
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def erf_inv_approx(p):
    return norm_ppf(p)


def bootstrap_pvalue(values, n_boot=20000, seed=20261101):
    """One-sided bootstrap p-value for H0: mean <= 0 (i.e. no edge). Returns (p, ci_low, ci_high)."""
    if not values:
        return None, None, None
    import random
    rng = random.Random(seed)
    n = len(values)
    obs = sum(values) / n
    stats = []
    for _ in range(n_boot):
        s = 0.0
        for _ in range(n):
            s += values[rng.randrange(n)]
        stats.append(s / n)
    stats.sort()
    p = sum(1 for s in stats if s <= 0) / n_boot
    lo = stats[int(0.025 * n_boot)]
    hi = stats[int(0.975 * n_boot)]
    return max(p, 1.0 / n_boot), lo, hi, obs


def benjamini_hochberg(pvals):
    """BH-FDR adjusted p-values, preserving input order."""
    idx = sorted(range(len(pvals)), key=lambda i: pvals[i])
    m = len(pvals)
    adj = [None] * m
    prev = 1.0
    for rank, i in enumerate(reversed(idx), start=1):
        k = m - rank + 1
        val = min(prev, pvals[i] * m / k)
        adj[i] = val
        prev = val
    return adj


def max_drawdown(profits):
    """Largest peak-to-trough decline of cumulative units."""
    cum = peak = dd = 0.0
    for p in profits:
        cum += p
        peak = max(peak, cum)
        dd = min(dd, cum - peak)
    return dd


def write_csv(path, rows, fields=None):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rows = list(rows)
    if not rows:
        return
    fields = fields or list(rows[0].keys())
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def game_date(g):
    try:
        return date.fromisoformat(g["gameday"])
    except Exception:
        return None
