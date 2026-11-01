"""Validation gates and luck-removal statistics.

The point of this module is to separate *skill* from *variance*:

  gate G5  -- market-efficiency null test.  For every bet we re-simulate the
              outcome using the DE-VIGGED MARKET PROBABILITY of the side we
              took (i.e. a bettor with zero skill making exactly the same bets).
              10,000 simulations give the ROI distribution that pure luck would
              produce; the p-value is how often luck matches or beats us.
  gate G6  -- Benjamini-Hochberg FDR across all strategies, because we tried
              many rules and some will look good by chance.
  gate G7  -- season consistency (a real edge should not be one season).
  gate G8  -- drop-the-best-season robustness.

Plus three descriptive statistics used on the leaderboard:
  * luck_band        -- how wide the zero-skill ROI band is at this sample size
  * deflated_sharpe  -- Sharpe haircut for the number of strategies tried
  * edge_monotonicity-- does profit rise with model edge? (a skill signature)
"""
import numpy as np
import pandas as pd

from common import (bootstrap_mean_ci, cluster_bootstrap_ci, bh_fdr, sharpe,
                    skew_kurt, deflated_sharpe)

HOLDOUT_SEASONS = [2023, 2024, 2025]
MIN_BETS = 200
MIN_SEASONS = 5
N_SIMS = 10000


def roi(profits, stakes):
    profits = np.asarray(profits, float)
    stakes = np.asarray(stakes, float)
    if stakes.sum() == 0:
        return float("nan")
    return float(profits.sum() / stakes.sum())


def market_null_roi(bets, n_sims=N_SIMS, seed=31):
    """ROI distribution under zero skill: outcomes drawn at the market's own
    de-vigged probability."""
    p = np.clip(bets.p_market.values.astype(float), 1e-6, 1 - 1e-6)
    dec = bets.odds_dec.values.astype(float)
    push = bets.get("p_push", pd.Series(np.zeros(len(bets)))).values.astype(float)
    stake = bets.stake.values.astype(float)
    rng = np.random.default_rng(seed)
    n = len(bets)
    total_stake = stake.sum()
    sims = np.empty(n_sims)
    for i in range(n_sims):
        u = rng.random(n)
        win = (u < p).astype(float)
        psh = (u >= p) & (u < p + push)
        sims[i] = np.sum((win * (dec - 1) - (1 - win - psh)) * stake) / total_stake
    return sims


def edge_monotonicity(bets):
    """Does realised profit increase with the model's edge over the market?"""
    b = bets.dropna(subset=["p_model", "p_market"]).copy()
    if len(b) < 300:
        return None
    b["edge"] = b.p_model - b.p_market
    b = b[b.edge > 0]
    if len(b) < 200:
        return None
    q = np.quantile(b.edge, [0.2, 0.4, 0.6, 0.8])
    b["q"] = np.digitize(b.edge, q)
    grp = b.groupby("q").apply(
        lambda d: pd.Series({"n": len(d), "edge": d.edge.mean(),
                             "roi": d.profit.sum() / d.stake.sum()}),
        include_groups=False)
    # rank correlation between decile index and ROI
    from numpy import corrcoef
    if grp.roi.notna().sum() >= 3:
        r = float(corrcoef(grp.index.values, grp.roi.values)[0, 1])
    else:
        r = float("nan")
    return {"buckets": [{"bucket": int(i), "n": int(row.n),
                         "mean_edge": float(row.edge), "roi": float(row.roi)}
                        for i, row in grp.iterrows()],
            "quintile_roi_rank_corr": None if not np.isfinite(r) else r}


def evaluate_strategy(sid, bets, meta=None):
    b = bets[bets.outcome.isin(["win", "loss", "push", "void"])].copy()
    observed = True
    if "price_source" in b.columns:
        observed = bool((b.price_source == "observed").all())
    n = len(b)
    decided = b[b.outcome.isin(["win", "loss"])]
    res = dict(strategy_id=sid, n_bets=int(n), n_decided=int(len(decided)),
               prices_observed=observed,
               seasons=sorted(int(s) for s in b.season.unique()),
               n_seasons=int(b.season.nunique()),
               stake=float(b.stake.sum()), profit=float(b.profit.sum()),
               roi=roi(b.profit, b.stake),
               hit_rate=float((decided.outcome == "win").mean()) if len(decided) else None,
               avg_dec=float(b.odds_dec.mean()) if n else None,
               avg_model_prob=float(b.p_model.mean()) if n else None,
               avg_market_prob=float(b.p_market.mean()) if n else None)

    if n >= 30:
        lo, hi = bootstrap_mean_ci(b.profit.values, n_boot=6000)
        res["roi_ci_bet"] = [lo, hi]
        slo, shi = cluster_bootstrap_ci(b.profit.values, b.season.values, n_boot=4000)
        res["roi_ci_season"] = [slo, shi]
    else:
        res["roi_ci_bet"] = res["roi_ci_season"] = None

    # season-by-season
    per = []
    for s, g in b.groupby("season"):
        per.append({"season": int(s), "n": int(len(g)),
                    "roi": roi(g.profit, g.stake),
                    "profit": float(g.profit.sum())})
    res["by_season"] = per
    prof_seasons = [p for p in per if p["n"] >= 10]
    res["pct_seasons_profitable"] = (float(np.mean([p["roi"] > 0 for p in prof_seasons]))
                                     if prof_seasons else None)

    # holdout
    ho = b[b.season.isin(HOLDOUT_SEASONS)]
    res["holdout_roi"] = roi(ho.profit, ho.stake) if len(ho) >= 30 else None
    res["holdout_n"] = int(len(ho))

    # luck / variance decomposition
    if n >= 100:
        sims = market_null_roi(b)
        obs = res["roi"]
        res["null_roi_mean"] = float(sims.mean())
        res["null_roi_sd"] = float(sims.std(ddof=1))
        res["null_roi_p05"] = float(np.quantile(sims, 0.05))
        res["null_roi_p95"] = float(np.quantile(sims, 0.95))
        res["p_value_vs_market"] = float((1 + np.sum(sims >= obs)) / (1 + len(sims)))
        res["luck_band"] = [res["null_roi_p05"], res["null_roi_p95"]]
        # share of observed ROI that sits inside the luck band
        band = res["null_roi_p95"] - res["null_roi_p05"]
        res["luck_band_width"] = band
        res["roi_vs_band"] = (obs - res["null_roi_mean"]) / band if band else None
    else:
        res["p_value_vs_market"] = None

    sr = sharpe(b.profit.values)
    sk, ku = skew_kurt(b.profit.values)
    res["sharpe_per_bet"] = sr
    res["skew"] = sk
    res["kurtosis"] = ku

    res["edge_monotonicity"] = edge_monotonicity(b)

    # robustness: drop the best season
    if per:
        best = max(per, key=lambda p: p["profit"])
        rest = [p for p in per if p is not best]
        if rest:
            res["roi_drop_best_season"] = float(np.mean([p["roi"] for p in rest]))
    return res


GATE_DEFS = [
    ("G1", "Sample size", f"at least {MIN_BETS} settled bets"),
    ("G2", "Coverage", f"bets spread over at least {MIN_SEASONS} seasons"),
    ("G3", "No leakage", "pre-game features only; point-in-time rebuild test passes"),
    ("G4", "Out-of-sample holdout", "non-negative ROI on the held-out 2023-2025 seasons"),
    ("G5", "Beats the luck null", "p < 0.05 vs the zero-skill (de-vigged market) simulation"),
    ("G6", "Multiple-testing", "survives Benjamini-Hochberg FDR at q = 0.10 across all strategies"),
    ("G7", "Season consistency", "profitable in at least 60% of seasons with >= 10 bets"),
    ("G8", "Robustness", "still non-negative after dropping the best season"),
    ("G9", "Observed prices", "every bet was priced from a two-way market actually present in the "
                              "source data (no assumed prices)"),
]


def apply_gates(results, leakage_ok=True, fdr_q=0.10):
    """Add gate pass/fail to each result dict.  FDR is applied across all
    model-based strategies in `results` (controls are excluded from the FDR
    family because they are benchmarks, not candidates)."""
    pvals = [r.get("p_value_vs_market") if r["strategy_id"].startswith(("S", "P", "T")) else None
             for r in results]
    idx = [i for i, p in enumerate(pvals) if p is not None]
    rejects = bh_fdr([pvals[i] for i in idx], q=fdr_q) if idx else []
    fdr_map = {idx[k]: bool(rejects[k]) for k in range(len(idx))} if idx else {}

    for i, r in enumerate(results):
        g = {}
        g["G1"] = r["n_bets"] >= MIN_BETS
        g["G2"] = r["n_seasons"] >= MIN_SEASONS
        g["G3"] = bool(leakage_ok)
        g["G4"] = (r.get("holdout_roi") is not None and r["holdout_roi"] >= 0)
        g["G5"] = (r.get("p_value_vs_market") is not None and r["p_value_vs_market"] < 0.05)
        g["G6"] = fdr_map.get(i, False)
        g["G7"] = (r.get("pct_seasons_profitable") is not None
                   and r["pct_seasons_profitable"] >= 0.60)
        g["G8"] = (r.get("roi_drop_best_season") is not None
                   and r["roi_drop_best_season"] >= 0)
        g["G9"] = bool(r.get("prices_observed", True))
        r["gates"] = {k: bool(v) for k, v in g.items()}
        r["gates_passed"] = int(sum(g.values()))
        r["gates_total"] = len(GATE_DEFS)
        r["passes_all"] = bool(all(g.values()))
        r["is_control"] = r["strategy_id"].startswith("C")
    return results, {k: v for k, v in fdr_map.items()}
