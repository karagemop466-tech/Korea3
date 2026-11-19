#!/usr/bin/env python3
"""Shared, standard-library-only arithmetic for the luck lab.

Why this file exists
--------------------
The leaderboard pages already in this repository rank strategies on return per unit
staked (`line_lab`, `origin_lab`). The brief asks for two further things that no page
does yet:

  * a control baseline -- what a bettor with no information at all earns on the same
    universe and the same prices ("Add a control baseline (random picks; favorites only)
    to every leaderboard run"), and
  * benchmark-relative skill with a game-cluster lower bound and a multiplicity
    adjustment ("Rank with proper scores and uncertainty, not win rate").

Every number here is a deterministic computation over files committed in this
repository. No network, no clock, no randomness: the random-side control is computed in
closed form (both sides averaged), so it is exactly the expectation of a coin flip and
does not need a seed that a later run could disagree with.

Sign and settlement conventions are copied from `line_lab/markets.py` so the two surfaces
cannot quietly disagree. Where this file re-implements it, `luck_lab/check.py` asserts the
two implementations agree on every row of the ledger.
"""
from __future__ import annotations

import csv
import math
import os
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

DATASET = ROOT / "data" / "derived" / "model_dataset.csv"
BETS = ROOT / "data" / "derived" / "bets.csv"
DATASET_SOURCE = (
    "https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv"
)

# The same price sanity band line_lab/markets.py uses; a price outside it is dropped, not used.
PRICE_MIN, PRICE_MAX = -10000.0, 10000.0


def num(value) -> float | None:
    """Blank, 'nan' and junk all become None. Never guessed."""
    if value is None:
        return None
    s = str(value).strip()
    if s == "" or s.lower() in {"nan", "none", "null"}:
        return None
    try:
        f = float(s)
    except ValueError:
        return None
    if math.isnan(f) or math.isinf(f):
        return None
    return f


def american_profit(price: float, stake: float = 1.0) -> float:
    """Profit on a winning bet at an American price (1 unit stake = 1.0)."""
    price = float(price)
    return stake * (price / 100.0 if price > 0 else 100.0 / abs(price))


def american_to_prob(price: float) -> float:
    """Implied probability *including* the vig, from an American price."""
    price = float(price)
    return (abs(price) / (abs(price) + 100.0)) if price < 0 else (100.0 / (abs(price) + 100.0))


def decimal_odds(price: float) -> float:
    return 1.0 + american_profit(price, 1.0)


def devig_two_way(p1: float, p2: float) -> tuple[float, float]:
    """Proportional de-vig of two American prices -> (p1, p2) summing to 1.

    Mirrors line_lab/markets.py:devig_two_way.
    """
    i1, i2 = 1.0 / decimal_odds(p1), 1.0 / decimal_odds(p2)
    total = i1 + i2
    return i1 / total, i2 / total


def price_ok(price: float | None) -> bool:
    return price is not None and PRICE_MIN <= price <= PRICE_MAX


# --------------------------------------------------------------------------- #
# Statistics, standard library only
# --------------------------------------------------------------------------- #
def mean(xs) -> float | None:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else None


def sd(xs) -> float | None:
    """Sample standard deviation (n-1). None when n < 2."""
    xs = list(xs)
    if len(xs) < 2:
        return None
    m = sum(xs) / len(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (len(xs) - 1))


def wilson_ci(wins: int, n: int, z: float = 1.959963984540054) -> tuple[float, float] | None:
    """Wilson score interval for a binomial proportion. Pushes are excluded from n upstream."""
    if n == 0:
        return None
    ph = wins / n
    den = 1 + z * z / n
    centre = (ph + z * z / (2 * n)) / den
    half = (z / den) * math.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n))
    return max(0.0, centre - half), min(1.0, centre + half)


def cluster_bootstrap(clusters: list[tuple[float, int]], reps: int, z: float = 1.959963984540054
                      ) -> dict | None:
    """Percentile interval for a ratio-of-sums statistic resampled by cluster.

    Each cluster carries (sum_of_values, count). The point estimate is sum(v)/sum(n) over
    all clusters, and every replicate draws clusters with replacement and recomputes the
    same ratio. Resampling games -- not bets -- is the point: legs inside a game are
    dependent, and an iid bootstrap over bets understates the spread.

    Deterministic: a fixed, documented linear congruential generator, so two runs give the
    same interval and a reviewer can reproduce it with any language.
    """
    k = len(clusters)
    if k < 2:
        return None
    tot_v = sum(v for v, _ in clusters)
    tot_n = sum(n for _, n in clusters)
    if tot_n == 0:
        return None
    point = tot_v / tot_n
    vs = [v for v, _ in clusters]
    ns = [n for _, n in clusters]
    # Numerical Recipes LCG (glibc constants): reproducible across CPython versions.
    state = 20261119 & 0xFFFFFFFF
    a, c, m = 1664525, 1013904223, 1 << 32
    stats = []
    for _ in range(reps):
        sv = sn = 0.0
        for _i in range(k):
            state = (a * state + c) % m
            idx = (state * k) >> 32
            sv += vs[idx]
            sn += ns[idx]
        if sn:
            stats.append(sv / sn)
    if len(stats) < 2:
        return None
    stats.sort()

    def pct(q: float) -> float:
        pos = q * (len(stats) - 1)
        lo = int(math.floor(pos))
        hi = min(lo + 1, len(stats) - 1)
        frac = pos - lo
        return stats[lo] * (1 - frac) + stats[hi] * frac

    # A p-value for "statistic > 0" without shifting the bootstrap: the share of replicates
    # at or below zero, plus the standard +1/(reps+1) continuity correction.
    le_zero = sum(1 for s in stats if s <= 0)
    return {
        "point": point,
        "ci_low": pct(0.025),
        "ci_high": pct(0.975),
        "lb95": pct(0.05),
        "sd": sd(stats),
        "p_le_zero": (le_zero + 1) / (len(stats) + 1),
        "reps": len(stats),
        "clusters": k,
        "rng": "LCG(1664525, 1013904223, mod 2^32) seeded 20261119, index = state*k >> 32",
    }


def bh_qvalues(pairs: list[tuple[str, float]], alpha_hint: float = 0.10) -> dict[str, float]:
    """Benjamini-Hochberg q-values for a family of one-sided tests.

    `pairs` is [(key, p_value), ...]. Returns {key: q}. Same recursion line_lab/evaluation.py
    uses, re-implemented here so this lab does not import a module that needs pandas.
    """
    items = [(k, p) for k, p in pairs if p is not None and not math.isnan(p)]
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


def norm_sf(x: float) -> float:
    """One-sided standard normal tail P(Z > x)."""
    return 0.5 * math.erfc(x / math.sqrt(2.0))


def bets_to_significance(mean_effect: float | None, sd_effect: float | None,
                         z_one_sided: float = 1.6448536269514722) -> int | None:
    """Bets at which a per-bet effect of this size separates from zero.

    Solve mean - z * sd / sqrt(n) > 0  ->  n > (z * sd / mean)^2. Rounded up. Returns None
    when the mean is not positive, which is the honest answer: at a negative per-bet edge no
    number of bets clears the bar, so the page must say "not reachable at this effect size"
    rather than print a count.
    """
    if not mean_effect or mean_effect <= 0 or not sd_effect or sd_effect <= 0:
        return None
    return int(math.ceil((z_one_sided * sd_effect / mean_effect) ** 2))


# --------------------------------------------------------------------------- #
# Dataset loading
# --------------------------------------------------------------------------- #
def load_games() -> tuple[list[dict], dict]:
    """Read the pinned game dataset into plain dicts, one per game with a final score.

    A game enters the control universe only when it has both scores and the price pair the
    control needs; `universe` records exactly how many rows were dropped and why, so the
    denominators on the page are computed, not asserted.
    """
    rows = list(csv.DictReader(open(DATASET, encoding="utf-8", newline="")))
    games: list[dict] = []
    drop = {"no_score": 0, "no_ats": 0, "no_total": 0, "no_ml": 0, "bad_price": 0}
    for r in rows:
        hs, awy = num(r.get("home_score")), num(r.get("away_score"))
        if hs is None or awy is None:
            drop["no_score"] += 1
            continue
        margin = hs - awy
        total = hs + awy
        line = num(r.get("spread_line"))
        tline = num(r.get("total_line"))
        ho, ao = num(r.get("home_spread_odds")), num(r.get("away_spread_odds"))
        oo, uo = num(r.get("over_odds")), num(r.get("under_odds"))
        hm, am = num(r.get("home_moneyline")), num(r.get("away_moneyline"))
        g = {
            "game_id": r["game_id"],
            "season": int(num(r["season"]) or 0),
            "week": int(num(r["week"]) or 0),
            "home_team": r.get("home_team", ""),
            "away_team": r.get("away_team", ""),
            "margin": margin,
            "total": total,
            "spread_line": line,
            "total_line": tline,
            "ats_ready": line is not None and price_ok(ho) and price_ok(ao) and ho and ao,
            "total_ready": tline is not None and price_ok(oo) and price_ok(uo) and oo and uo,
            "ml_ready": price_ok(hm) and price_ok(am) and hm and am,
        }
        if g["ats_ready"]:
            g["home_spread_odds"], g["away_spread_odds"] = ho, ao
            ph, pa = devig_two_way(ho, ao)
            g["ats_devig_home"], g["ats_devig_away"] = ph, pa
        else:
            drop["no_ats"] += 1
        if g["total_ready"]:
            g["over_odds"], g["under_odds"] = oo, uo
            po, pu = devig_two_way(oo, uo)
            g["devig_over"], g["devig_under"] = po, pu
        else:
            drop["no_total"] += 1
        if g["ml_ready"]:
            g["home_moneyline"], g["away_moneyline"] = hm, am
            phm, pam = devig_two_way(hm, am)
            g["ml_devig_home"], g["ml_devig_away"] = phm, pam
            g["ml_fav_side"] = "home" if phm >= pam else "away"
        else:
            drop["no_ml"] += 1
        games.append(g)
    uni = {
        "dataset_rows": len(rows),
        "with_final_score": len(games),
        "dropped_no_final_score": drop["no_score"],
        "ats_priced": sum(1 for g in games if g["ats_ready"]),
        "total_priced": sum(1 for g in games if g["total_ready"]),
        "ml_priced": sum(1 for g in games if g["ml_ready"]),
        "season_min": min((g["season"] for g in games), default=None),
        "season_max": max((g["season"] for g in games), default=None),
    }
    return games, uni


def settle_ats(g: dict, side: str) -> int:
    """1 / -1 / 0 for win / loss / push. Home covers when (margin - line) > 0."""
    adj = g["margin"] - g["spread_line"]
    if adj == 0:
        return 0
    home_covered = adj > 0
    return 1 if (home_covered and side == "home") or ((not home_covered) and side == "away") else -1


def settle_total(g: dict, side: str) -> int:
    adj = g["total"] - g["total_line"]
    if adj == 0:
        return 0
    over = adj > 0
    return 1 if (over and side == "over") or ((not over) and side == "under") else -1


def settle_ml(g: dict, side: str) -> int:
    if g["margin"] == 0:
        return 0
    home_won = g["margin"] > 0
    return 1 if (home_won and side == "home") or ((not home_won) and side == "away") else -1


def cluster_bootstrap_ratio(pairs: list[tuple[float, float]], reps: int) -> dict | None:
    """Percentile interval for a ratio-of-sums statistic resampled by cluster.

    Each cluster carries (numerator_sum, denominator_sum) -- both floats, so a skill score whose
    denominator is another model's mean squared error resamples correctly instead of being
    divided by a count. Same generator as `cluster_bootstrap`, same draw rule.
    """
    k = len(pairs)
    if k < 2:
        return None
    tot_n = sum(a for a, _ in pairs)
    tot_d = sum(b for _, b in pairs)
    if not tot_d:
        return None
    point = tot_n / tot_d
    ns = [a for a, _ in pairs]
    ds = [b for _, b in pairs]
    state = 20261119 & 0xFFFFFFFF
    a, c, m = 1664525, 1013904223, 1 << 32
    stats = []
    for _ in range(reps):
        sn = sd_ = 0.0
        for _i in range(k):
            state = (a * state + c) % m
            idx = (state * k) >> 32
            sn += ns[idx]
            sd_ += ds[idx]
        if sd_:
            stats.append(sn / sd_)
    if len(stats) < 2:
        return None
    stats.sort()

    def pct(q: float) -> float:
        pos = q * (len(stats) - 1)
        lo = int(math.floor(pos))
        hi = min(lo + 1, len(stats) - 1)
        frac = pos - lo
        return stats[lo] * (1 - frac) + stats[hi] * frac

    le_zero = sum(1 for s_ in stats if s_ <= 0)
    return {
        "point": point,
        "ci_low": pct(0.025),
        "ci_high": pct(0.975),
        "lb95": pct(0.05),
        "sd": sd(stats),
        "p_le_zero": (le_zero + 1) / (len(stats) + 1),
        "reps": len(stats),
        "clusters": k,
        "rng": "LCG(1664525, 1013904223, mod 2^32) seeded 20261119, index = state*k >> 32",
    }


def rel(a, b, tol_abs: float = 1e-9, tol_rel: float = 1e-9) -> bool:
    """Tolerance comparison used by the verify gate."""
    if a is None or b is None:
        return a is None and b is None
    return abs(a - b) <= max(tol_abs, tol_rel * max(abs(a), abs(b)))


def sha256_file(path: Path) -> str:
    import hashlib

    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def repo_rel(path: Path) -> str:
    return os.path.relpath(path, ROOT).replace(os.sep, "/")
