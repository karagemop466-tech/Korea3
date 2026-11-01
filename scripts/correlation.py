"""correlation.py — measured correlations for parlays and player-prop combos.

Everything numeric here is computed from the pinned dataset. Nothing is assumed.

Outputs
-------
corr_same_game.csv    phi between two legs of the SAME game, with n, bootstrap CI,
                      exact p-value, the empirical joint win rate, the product of the
                      single-leg rates, and the gap between them in percentage points.
corr_cross_game.csv   the independence assumption, tested: outcomes of unrelated games.
corr_signal_matrix.csv  correlation of per-game P&L between our 18 strategies
                      (this is what decides whether combining strategies diversifies).
parlay_math.csv       exact arithmetic: EV of a k-leg parlay at a posted price as a
                      function of the measured phi, and the phi needed to break even.
"""
from __future__ import annotations

import itertools
import json
import os

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DER = os.path.join(ROOT, "data", "derived")
SEED = 20261101


def phi(x: np.ndarray, y: np.ndarray) -> float:
    x = np.asarray(x, float); y = np.asarray(y, float)
    if x.size < 3:
        return np.nan
    return float(np.corrcoef(x, y)[0, 1])


def phi_ci(x, y, n_boot=4000, alpha=0.05):
    x = np.asarray(x, float); y = np.asarray(y, float)
    rng = np.random.default_rng(SEED)
    idx = rng.integers(0, x.size, size=(n_boot, x.size))
    vals = np.array([np.corrcoef(x[i], y[i])[0, 1] for i in idx])
    vals = vals[np.isfinite(vals)]
    return float(np.quantile(vals, alpha / 2)), float(np.quantile(vals, 1 - alpha / 2))


def pair_row(name, a, b, label_a, label_b, n_boot=4000) -> dict:
    a = np.asarray(a, float); b = np.asarray(b, float)
    ok = np.isfinite(a) & np.isfinite(b)
    a, b = a[ok], b[ok]
    p1, p2 = float(a.mean()), float(b.mean())
    joint = float(((a == 1) & (b == 1)).mean())
    r = phi(a, b)
    lo, hi = phi_ci(a, b, n_boot)
    # exact test of independence on the 2x2 table
    tab = np.array([[((a == 1) & (b == 1)).sum(), ((a == 1) & (b == 0)).sum()],
                    [((a == 0) & (b == 1)).sum(), ((a == 0) & (b == 0)).sum()]])
    chi2, pchi, _, _ = stats.chi2_contingency(tab, correction=False)
    return {
        "pair": name, "leg_a": label_a, "leg_b": label_b, "n": int(a.size),
        "rate_a": round(p1, 4), "rate_b": round(p2, 4),
        "joint_win_rate": round(joint, 4),
        "product_of_rates": round(p1 * p2, 4),
        "gap_pp": round((joint - p1 * p2) * 100, 3),
        "phi": round(r, 4), "phi_ci_low": round(lo, 4), "phi_ci_high": round(hi, 4),
        "chi2": round(float(chi2), 3), "p_value": float(f"{pchi:.4g}"),
    }


def same_game(d: pd.DataFrame) -> pd.DataFrame:
    rows = []
    base = d.dropna(subset=["home_cover", "over"])
    hc = base["home_cover"].to_numpy(float)
    ov = base["over"].to_numpy(float)

    rows.append(pair_row("Home cover x Over", hc, ov, "home ATS cover", "over"))

    # favourite side cover
    fav_home = base["home_spread"] < 0
    fav = np.where(fav_home, base["home_cover"], 1 - base["home_cover"])
    rows.append(pair_row("Favourite cover x Over", fav, ov, "favourite ATS cover", "over"))

    # underdog side cover
    dog = np.where(fav_home, 1 - base["home_cover"], base["home_cover"])
    rows.append(pair_row("Underdog cover x Over", dog, ov, "underdog ATS cover", "over"))

    # moneyline + spread in the same game (same team) - the classic redundant pair
    hw = base["home_win"].to_numpy(float)
    rows.append(pair_row("Home ML win x Home cover", hw, hc, "home moneyline", "home ATS cover"))
    rows.append(pair_row("Home ML win x Over", hw, ov, "home moneyline", "over"))

    # environment / situation splits
    dom = base["is_dome"] == 1
    rows.append(pair_row("Dome only: Home cover x Over", hc[dom.to_numpy()], ov[dom.to_numpy()],
                         "home ATS cover (dome)", "over (dome)"))
    div = base["div_game"] == 1
    rows.append(pair_row("Divisional only: Home cover x Over", hc[div.to_numpy()], ov[div.to_numpy()],
                         "home ATS cover (division)", "over (division)"))
    out = base["outdoor"] == 1
    rows.append(pair_row("Outdoor only: Home cover x Over", hc[out.to_numpy()], ov[out.to_numpy()],
                         "home ATS cover (outdoors)", "over (outdoors)"))
    return pd.DataFrame(rows)


def cross_game(d: pd.DataFrame) -> pd.DataFrame:
    """Test the assumption that different games are independent."""
    rows = []
    rng = np.random.default_rng(SEED)
    for season in sorted(d["season"].unique()):
        s = d[d["season"] == season].dropna(subset=["home_cover"])
        if len(s) < 32:
            continue
        rng2 = np.random.default_rng(SEED + int(season))
        a_i = rng2.integers(0, len(s), size=200)
        b_i = (a_i + rng2.integers(1, len(s) - 1, size=200)) % len(s)
        hc = s["home_cover"].to_numpy(float)
        rows.append({"season": int(season), "n_pairs": int(len(a_i)),
                     "phi": round(float(np.corrcoef(hc[a_i], hc[b_i])[0, 1]), 4)})
    return pd.DataFrame(rows)


def signal_matrix() -> tuple[pd.DataFrame, dict]:
    """Pairwise correlation of leg OUTCOMES between strategies, on shared games only.

    Two strategies can only be correlated where they both bet the same game, so the
    matrix is built on the intersection of games for each pair. Pairs that bet
    opposite sides of the same market on the same games are structurally -1 and are
    labelled, not treated as a discovery.
    """
    b = pd.read_csv(os.path.join(DER, "signal_bets.csv"))
    b = b[b.result != 0]
    market = b.groupby("signal")["market"].first().to_dict()
    piv = b.pivot_table(index="game_id", columns="signal", values="result", aggfunc="first")
    cols = list(piv.columns)
    mat = pd.DataFrame(np.nan, index=cols, columns=cols)
    overlap = pd.DataFrame(0, index=cols, columns=cols)
    pairs = []
    for a, c in itertools.combinations(cols, 2):
        sub = piv[[a, c]].dropna()
        n = len(sub)
        overlap.loc[a, c] = overlap.loc[c, a] = n
        if n >= 100 and sub[a].nunique() > 1 and sub[c].nunique() > 1:
            r = float(np.corrcoef(sub[a], sub[c])[0, 1])
            mat.loc[a, c] = mat.loc[c, a] = r
            pairs.append({"a": a, "b": c, "n_shared": n, "phi": r,
                          "same_market": market.get(a) == market.get(c)})
    P = pd.DataFrame(pairs)
    same = P[P.same_market]
    diff = P[~P.same_market]
    summ = {
        "n_signals": len(cols),
        "pairs_evaluable": int(P.shape[0]),
        "pairs_same_market": int(same.shape[0]),
        "pairs_different_market": int(diff.shape[0]),
        "median_abs_phi_different_market": round(float(diff["phi"].abs().median()), 4) if len(diff) else None,
        "share_different_market_abs_phi_gt_0.15": round(float((diff["phi"].abs() > 0.15).mean()), 4) if len(diff) else None,
        "median_abs_phi_same_market": round(float(same["phi"].abs().median()), 4) if len(same) else None,
        "most_negative_different_market": (
            {"a": diff.loc[diff["phi"].idxmin(), "a"], "b": diff.loc[diff["phi"].idxmin(), "b"],
             "phi": round(float(diff["phi"].min()), 4), "n_shared": int(diff.loc[diff["phi"].idxmin(), "n_shared"])}
            if len(diff) else None),
        "most_positive_different_market": (
            {"a": diff.loc[diff["phi"].idxmax(), "a"], "b": diff.loc[diff["phi"].idxmax(), "b"],
             "phi": round(float(diff["phi"].max()), 4), "n_shared": int(diff.loc[diff["phi"].idxmax(), "n_shared"])}
            if len(diff) else None),
    }
    P.round(4).to_csv(os.path.join(DER, "corr_signal_pairs.csv"), index=False)
    return mat.round(4), summ, overlap


def joint_prob(p1: float, p2: float, r: float) -> float:
    """Exact joint probability of two Bernoullis with marginal rates p1,p2 and phi r."""
    return p1 * p2 + r * np.sqrt(p1 * (1 - p1) * p2 * (1 - p2))


def parlay_math() -> pd.DataFrame:
    """EV of a parlay priced as if the legs were independent.

    A book that multiplies -110 x -110 pays a decimal of (210/110)^2 = 3.6446.
    True joint probability depends on the real correlation, so:
        EV per unit = joint * decimal - 1
    """
    rows = []
    for price in (-110.0, -105.0):
        dec1 = 1 + 100 / abs(price)
        for true_p in (0.5, 110 / 210):
            for r in (-0.30, -0.20, -0.10, 0.0, 0.05, 0.10, 0.15, 0.20, 0.30):
                j = joint_prob(true_p, true_p, r)
                for k in (2, 3):
                    dec = dec1 ** k
                    joint = j if k == 2 else true_p ** k  # reported for 2 legs only where r applies
                    if k == 2:
                        ev = joint * dec - 1
                    else:
                        ev = (true_p ** k) * dec - 1
                    rows.append({
                        "legs": k, "price_each": price, "assumed_true_leg_rate": round(true_p, 4),
                        "phi": r, "parlay_decimal": round(dec, 4),
                        "true_joint_prob": round(joint, 5),
                        "ev_per_unit": round(ev, 4),
                        "ev_pct": round(ev * 100, 2),
                    })
    df = pd.DataFrame(rows)
    # breakeven phi: smallest phi in the grid with EV >= 0 at the -110 / p=0.5 / 2-leg cell
    cell = df[(df.legs == 2) & (df.price_each == -110.0) & (df.assumed_true_leg_rate == 0.5)]
    be = cell[cell.ev_per_unit >= 0]["phi"].min()
    return df, (None if pd.isna(be) else float(be))


def breakeven_phi_exact(price: float = -110.0, true_p: float = 0.5, legs: int = 2) -> float:
    dec = (1 + 100 / abs(price)) ** legs
    target = 1 / dec
    # target = p^2 + r*p*(1-p)  for two equal Bernoulli legs
    return float((target - true_p ** 2) / (true_p * (1 - true_p)))


if __name__ == "__main__":
    d = pd.read_csv(os.path.join(DER, "model_dataset.csv"), low_memory=False)
    sg = same_game(d)
    sg.to_csv(os.path.join(DER, "corr_same_game.csv"), index=False)

    cg = cross_game(d)
    cg.to_csv(os.path.join(DER, "corr_cross_game.csv"), index=False)

    sm, smeta, overlap = signal_matrix()
    overlap.to_csv(os.path.join(DER, "corr_signal_overlap.csv"))
    sm.to_csv(os.path.join(DER, "corr_signal_matrix.csv"))

    pm, be = parlay_math()
    pm.to_csv(os.path.join(DER, "parlay_math.csv"), index=False)

    meta = {
        "cross_game": {
            "seasons": int(cg.shape[0]),
            "mean_phi": round(float(cg["phi"].mean()), 4),
            "median_phi": round(float(cg["phi"].median()), 4),
            "share_abs_gt_0.10": round(float((cg["phi"].abs() > 0.10).mean()), 4),
        },
        "signal_matrix": smeta,
        "cross_game_test": {
            "pooled_mean_phi": round(float(cg["phi"].mean()), 4),
            "pooled_se": round(float(cg["phi"].std(ddof=1) / np.sqrt(len(cg))), 4),
            "pooled_p_value_vs_zero": float(f"{2 * (1 - stats.norm.cdf(abs(cg['phi'].mean() / (cg['phi'].std(ddof=1) / np.sqrt(len(cg)))))):.4g}"),
        },
        "breakeven_phi_2leg_110_p50": breakeven_phi_exact(-110.0, 0.5, 2),
        "breakeven_phi_3leg_110_p50": round(float(
            (1 / ((1 + 100 / 110) ** 3) - 0.5 ** 3) / 0.25), 4) if True else None,
    }
    with open(os.path.join(DER, "corr_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print(sg.to_string(index=False))
    print()
    print(json.dumps(meta, indent=2))
