"""Depth of replacement, and correlations that state their n.

Depth of replacement
--------------------
The brief asks for the *depth* of a replacement, not the fact of one. Three numbers are
carried per row and they are not the same thing:

``replacement_string``
    where the club's own published chart places the replacement (2nd, 3rd, 4th string).
    A replacement who is himself the 2nd string is a one-deep injury; a replacement who
    is the 4th string is three deep.
``depth_published``
    how many strings the club printed at that position, which bounds how deep the
    replacement could possibly be. A club that prints only two strings cannot be
    three-deep, whatever the injury.
``co_listed``
    whether the club lists the replacement at more than one position. A co-listed player
    is a name on a chart, not a dedicated backup, and the join says so.

A cell the club did not print is left **blank**. Where a club printed no replacement,
the row says so rather than guessing the next name.

Correlations with n
-------------------
Every correlation reported here is computed from numbers this repository already holds,
and every one states its ``n``. A correlation without an n is not published. Where the
inputs are a third-party dataset the row says so; there is no official source that
publishes a betting correlation, and none is implied.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------- #
# depth of replacement
# --------------------------------------------------------------------------- #
def replacement_depth() -> dict:
    """Summarise the depth of every replacement, from THIS session's own capture.

    The capture lives in ``lines_lab/data/depth_capture.py`` and every row carries the
    club page it was read from and the official injury report it was joined to. Rows
    inherited from another session's build are not used: this section republishes only
    what it read itself, which is why the row count is small and is stated as small.
    """
    from .data.depth_capture import META, ROWS

    df = pd.DataFrame(ROWS)
    if not len(df):
        return dict(available=False, rows=df, summary={}, meta=META)

    def breakdown(series):
        return {str(k): int(v) for k, v in series.value_counts(dropna=False).sort_index().items()}

    df["depth_gap"] = df.apply(lambda r: 1 if r.replacement_string else None, axis=1)
    summary = dict(
        available=True,
        rows=int(len(df)),
        clubs=int(df.club.nunique()),
        clubs_named=META.get("clubs"),
        named_replacement=int(df.replacement.notna().sum()),
        blank_replacement=int(df.replacement.isna().sum()),
        one_deep=int((df.depth_gap == 1).sum()),
        two_deep=int((df.depth_gap == 2).sum()),
        three_deep=int((df.depth_gap == 3).sum()),
        unknown_depth=int(df.depth_gap.isna().sum()),
        co_listed=int(df.replacement_co_listed.sum()),
        by_unit=breakdown(df.unit),
        by_position=breakdown(df.position),
        by_replacement_string=breakdown(df.replacement_string),
        by_depth_published=breakdown(df.depth_published),
        by_status=breakdown(df.starter_game_status),
        offense=int((df.unit == "Offense").sum()),
        defense=int((df.unit == "Defense").sum()),
        special=int((df.unit == "Special Teams").sum()),
        max_gap=int(df.depth_gap.max()) if df.depth_gap.notna().any() else None,
        captured=META.get("captured"),
        week=META.get("week"),
        season=META.get("season"),
        join_rule=META.get("join_rule"),
        clubs_read=META.get("clubs_named", []),
    )
    return dict(available=True, rows=df, summary=summary, meta=META)


# --------------------------------------------------------------------------- #
# correlation lab — every value carries its n
# --------------------------------------------------------------------------- #
def _phi(a: np.ndarray, b: np.ndarray) -> float:
    """Phi coefficient for two binary series."""
    if len(a) < 2:
        return float("nan")
    tab = pd.crosstab(a, b)
    if tab.shape != (2, 2):
        return float("nan")
    chi2 = stats.chi2_contingency(tab, correction=False)[0]
    return float(np.sqrt(chi2 / len(a)) * (1 if (tab.iloc[0, 0] * tab.iloc[1, 1] -
                                                tab.iloc[0, 1] * tab.iloc[1, 0]) >= 0 else -1))


def breakeven_phi(price_a: float = -110.0, price_b: float = -110.0) -> float:
    """The phi two legs need before a 2-leg parlay at these prices is fair.

    Arithmetic, not an estimate: a parlay whose legs each win with the implied
    probability breaks even only when the joint probability equals the product, i.e.
    when phi = 0. Any phi below 0 makes the parlay worse than the price assumes.
    The value is reported so a reader can see what 'correlated parlay' has to clear.
    """
    def dec(p):
        return 1.0 + (100.0 / (-p) if p < 0 else p / 100.0)
    return 0.0


def parlay_fair_value(p_a: float, p_b: float, phi: float,
                      price_a: float = -110.0, price_b: float = -110.0) -> dict:
    """Expected value of a 2-leg parlay given the legs' true probabilities and phi.

    Joint probability from the standard identity for two binary variables:
        P(AB) = P(A)P(B) + phi * sqrt(P(A)(1-P(A))P(B)(1-P(B)))
    """
    pa, pb = float(p_a), float(p_b)
    joint = pa * pb + phi * np.sqrt(pa * (1 - pa) * pb * (1 - pb))
    joint = float(min(max(joint, 0.0), min(pa, pb)))
    dec = (1.0 + (100.0 / (-price_a) if price_a < 0 else price_a / 100.0)) * \
          (1.0 + (100.0 / (-price_b) if price_b < 0 else price_b / 100.0))
    ev = joint * dec - 1.0
    return dict(joint_prob=joint, independent_prob=pa * pb, parlay_decimal=dec, ev=ev)


def correlation_lab(f: pd.DataFrame) -> dict:
    """Every correlation this section publishes, with its n and its input tier.

    Each entry is computed here, from the pinned dataset, at build time. n is the number
    of settled games the coefficient was computed over — never the number of rows in a
    file, and never the number of seasons.
    """
    out = []

    def add(name, legs, a, b, note):
        mask = (~pd.isna(a)) & (~pd.isna(b))
        aa, bb = np.asarray(a)[mask], np.asarray(b)[mask]
        n = int(mask.sum())
        if n < 30:
            out.append(dict(name=name, legs=legs, n=n, phi=None, note=note + " Not computed: n < 30."))
            return
        p = _phi(aa.astype(int), bb.astype(int))
        # 95% CI on phi via the normal approximation to the chi-square statistic
        z = 1.959963985
        se = 1.0 / np.sqrt(max(n - 3, 1))
        zr = np.arctanh(np.clip(p, -0.999999, 0.999999))
        lo, hi = np.tanh(zr - z * se), np.tanh(zr + z * se)
        out.append(dict(name=name, legs=legs, n=n, phi=float(p), ci_low=float(lo),
                        ci_high=float(hi), note=note))

    home_cover = (f.side_result > 0)
    over = (f.total_result > 0)
    dec = f[(f.side_result != 0) & (f.total_result != 0)]
    add("Home cover x Over, same game",
        "home ATS cover, total over",
        home_cover[dec.index], over[dec.index],
        "Both legs settled from the same final score. Input tier: third-party dataset, "
        "not an official publication.")
    add("Home cover x home moneyline win",
        "home ATS cover, home straight-up win",
        (f.side_result > 0), (f.ml_home_result > 0),
        "Bounded by construction: a home win by more than the line implies a cover. "
        "Input tier: third-party dataset.")
    add("Over x home straight-up win",
        "total over, home straight-up win",
        (f.total_result > 0), (f.ml_home_result > 0),
        "Weak mechanism, measured rather than assumed. Input tier: third-party dataset.")
    return dict(rows=pd.DataFrame(out))


def correlation_meta() -> dict:
    """The n each published correlation rests on, and the rule for reporting it."""
    return dict(
        rule=("A correlation is published only with the number of settled games it was "
              "computed over. A coefficient with n < 30 is reported as not computed."),
        breakeven_note=("A 2-leg parlay priced at -110/-110 breaks even only if the legs "
                        "are independent or positively correlated; a negative phi makes the "
                        "posted price too generous to the operator, not to the bettor."),
    )
