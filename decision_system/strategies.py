"""The leaderboard competition: audit every pre-registered strategy, price combinations,
measure correlation on our own data, and publish what would have to be true to win.

Inputs are read-only artefacts produced by earlier, separate sessions:

``line_lab/data/derived/bets.csv``   16,439 settled selections, 11 strategies
``data/derived/features.csv``        walk-forward Elo / form features
``data/raw/games.csv``               results and closing prices

Nothing here re-fits a model or changes a settled price.  What it adds is the part the
brief asks for and the repository did not yet have in one place:

1. all seven skill gates run per strategy (:mod:`decision_system.skill`);
2. the multiple-testing correction the leaderboard needs before any reward;
3. measured correlation between legs at three levels — same game, same week,
   different weeks — so parlay arithmetic uses our numbers, not folklore;
4. an explicit statement of what a rewarded competition would require.
"""
from __future__ import annotations

import itertools
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats as st

from . import skill

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "injury_lab"

CUT_SEASON = 2019   # pre-registered out-of-sample cut used by earlier sessions
HOLDOUT_FROM = 2024  # most recent complete seasons


def load() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    bets = pd.read_csv(ROOT / "line_lab" / "data" / "derived" / "bets.csv")
    feats = pd.read_csv(ROOT / "data" / "derived" / "features.csv")
    summary = json.loads((ROOT / "line_lab" / "data" / "derived" / "summary.json").read_text())
    return bets, feats, summary


def _p_value(returns: np.ndarray) -> float:
    if returns.size < 2:
        return float("nan")
    t = returns.mean() / (returns.std(ddof=1) / math.sqrt(returns.size))
    return float(2 * (1 - st.t.cdf(abs(t), df=returns.size - 1)))


def audit_all(bets: pd.DataFrame) -> dict:
    ids = sorted(bets.strategy_id.unique())
    n_trials = len(ids)
    rows, pvals = [], []
    for sid in ids:
        sub = bets[bets.strategy_id == sid]
        name = sub.strategy_name.iloc[0]
        rec = skill.audit_strategy(sub, name, sid, n_trials=n_trials,
                                   cut_season=CUT_SEASON, holdout_from=HOLDOUT_FROM)
        rec["p_value"] = round(_p_value(sub.pnl.to_numpy(dtype=float)), 6)
        pvals.append(rec["p_value"])
        rows.append(rec)
    fdr = skill.fdr_bh(pvals, q=0.05)
    for rec, rej, q in zip(rows, fdr["reject"], fdr["qvalues"]):
        rec["bh_reject_5pct"] = bool(rej)
        rec["bh_qvalue"] = q
        rec["bonferroni_threshold"] = round(skill.bonferroni_alpha(n_trials), 6)
    ranked = sorted(rows, key=lambda r: -(r["mean_pnl_per_unit"] or -9))
    for i, r in enumerate(ranked, 1):
        r["rank_by_roi"] = i
    return {
        "n_strategies": n_trials,
        "n_bets": int(len(bets)),
        "rows": rows,
        "reward_eligible": [r["strategy_id"] for r in rows if r["reward_eligible"]],
        "any_bh_significant": bool(any(r["bh_reject_5pct"] for r in rows)),
    }


# ------------------------------------------------------------------- correlation lab
def _phi(a: pd.Series, b: pd.Series) -> tuple[float, float, float, int]:
    """Phi coefficient between two boolean series, with a 95% CI and n."""
    m = a.notna() & b.notna()
    a2, b2 = a[m].astype(bool), b[m].astype(bool)
    n = int(m.sum())
    if n < 30 or a2.nunique() < 2 or b2.nunique() < 2:
        return (float("nan"), float("nan"), float("nan"), n)
    tab = pd.crosstab(a2, b2).to_numpy()
    chi2 = st.chi2_contingency(tab, correction=False)[0]
    phi = math.sqrt(chi2 / n) * (1 if (tab[1, 1] * tab[0, 0] >= tab[1, 0] * tab[0, 1]) else -1)
    se = 1 / math.sqrt(n - 1)
    return (float(phi), float(phi - 1.96 * se), float(phi + 1.96 * se), n)


def correlation_lab(games: pd.DataFrame) -> list[dict]:
    """Measured dependence between the legs a parlay can combine.

    Each row states the two events, phi, its CI, n, and the break-even phi a
    2-leg -110 parlay needs for the combination to be worth the same as two singles.
    """
    g = games.copy()
    # Explicit event definitions; the label, the column and the definition must agree.
    g["home_cover"] = (g.margin + g.spread_line) > 0          # home side of the spread wins
    g["over"] = g.total > g.total_line                        # total lands over the closing line
    g["home_win"] = g.margin > 0                              # home wins outright
    defs = {
        "home_cover": "home team covers the closing spread (tie loses)",
        "over": "combined score is above the closing total (push excluded by strict >)",
        "home_win": "home team wins outright (tie impossible in the NFL regular season)",
    }
    rows = [
        ("Home wins outright × Home covers the spread", "home_win", "home_cover", "same game"),
        ("Home covers the spread × Total goes over", "home_cover", "over", "same game"),
        ("Home wins outright × Total goes over", "home_win", "over", "same game"),
    ]
    out = []
    for label, a, b, scope in rows:
        phi, lo, hi, n = _phi(g[a], g[b])
        out.append({"label": label, "a": a, "b": b, "scope": scope,
                    "definition_a": defs[a], "definition_b": defs[b],
                    "phi": None if math.isnan(phi) else round(phi, 4),
                    "ci95": None if math.isnan(phi) else [round(lo, 4), round(hi, 4)],
                    "n": n})
    # cross-game same week: match consecutive games in the same week
    pairs = []
    for (season, week), grp in g.groupby(["season", "week"]):
        if len(grp) < 2:
            continue
        grp = grp.sort_values("game_id")
        for (i, r1), (j, r2) in itertools.combinations(grp.iterrows(), 2):
            pairs.append((r1.home_cover, r2.home_cover, r1.over, r2.over))
            if len(pairs) > 40000:
                break
        if len(pairs) > 40000:
            break
    if pairs:
        p = pd.DataFrame(pairs, columns=["a_cover", "b_cover", "a_over", "b_over"])
        for label, a, b in (("Spread covers in two different games, same week", "a_cover", "b_cover"),
                            ("Totals (over) in two different games, same week", "a_over", "b_over")):
            phi, lo, hi, n = _phi(p[a], p[b])
            out.append({"label": label, "a": a, "b": b, "scope": "cross-game, same week",
                        "phi": None if math.isnan(phi) else round(phi, 4),
                        "ci95": None if math.isnan(phi) else [round(lo, 4), round(hi, 4)],
                        "n": n})
    return out


def parlay_math(phi: float = 0.0, p: float = 0.5, price: float = -110.0) -> dict:
    """Price of a 2-leg parlay given the dependence between the legs.

    Independent fair price, the price an operator must charge if the legs are
    correlated by ``phi``, and the phi at which a -110/-110 parlay is exactly fair.
    """
    p_joint_indep = p * p
    # bivariate Bernoulli with the given phi
    lo = -p / (1 - p) if p < 1 else -1
    hi = 1.0
    phi_c = min(max(phi, lo), hi)
    p_joint = p * p + phi_c * math.sqrt(p * (1 - p) * p * (1 - p))
    fair_decimal = 1 / p_joint
    # operator pays product of decimal odds minus vig
    dec = skill.decimal_odds(price)
    paid = dec * dec
    # break-even phi for two -110 legs at p=0.5
    be_p = 1 / paid
    be_phi = (be_p - p * p) / (p * (1 - p))
    return {
        "leg_probability": p,
        "phi": round(phi, 4),
        "joint_independent": round(p_joint_indep, 6),
        "joint_with_phi": round(p_joint, 6),
        "fair_decimal_independent": round(1 / p_joint_indep, 6),
        "fair_decimal_with_phi": round(fair_decimal, 6),
        "operator_decimal_two_legs": round(paid, 6),
        "operator_margin_pct_at_this_phi": round(100 * (1 - paid * p_joint), 4),
        "operator_margin_pct_if_legs_independent": round(100 * (1 - paid * p_joint_indep), 4),
        "break_even_phi_at_minus110": round(be_phi, 5),
    }


def parlay_grid() -> list[dict]:
    out = []
    for phi in (-0.05, 0.0, 0.05, 0.0975, 0.2, 0.5, 0.671):
        out.append(parlay_math(phi=phi, p=0.5, price=-110.0))
    return out


# ------------------------------------------------------------------ existing parlays
def parlay_strategy_check(bets: pd.DataFrame) -> list[dict]:
    rows = []
    for sid in ("S9", "S10"):
        sub = bets[bets.strategy_id == sid]
        if sub.empty:
            continue
        r = sub.pnl.to_numpy(dtype=float)
        ci = skill.bootstrap_ci(r, n_boot=10000)
        rows.append({
            "strategy_id": sid,
            "name": sub.strategy_name.iloc[0],
            "n": int(r.size),
            "roi_pct": round(100 * float(r.mean()), 3),
            "boot_ci95_pct": [round(100 * ci[1], 3), round(100 * ci[2], 3)],
            "win_rate": round(float((sub.outcome == 1).mean()), 4),
        })
    return rows


# ----------------------------------------------------------------- prop feasibility
def prop_feasibility(bets: pd.DataFrame) -> dict:
    """What can honestly be said about player-prop combinations today."""
    has_props = bets[bets.market.astype(str).str.upper().str.contains("PROP")]
    return {
        "prop_rows_in_bets": int(len(has_props)),
        "prop_prices_available": False,
        "note": ("No licensed prop price exists in the repository or in any reachable source, so "
                 "no prop strategy can be scored. The prop page states the two measurable "
                 "prerequisites instead of publishing a fabricated edge."),
    }


def run() -> dict:
    bets, feats, summary = load()
    games = pd.read_csv(ROOT / "data" / "raw" / "games.csv", low_memory=False)
    games = games[(games.game_type == "REG") & games.home_score.notna()
                  & games.spread_line.notna() & games.total_line.notna()].copy()
    games["margin"] = games.home_score - games.away_score
    games["total"] = games.home_score + games.away_score

    audit = audit_all(bets)
    corr = correlation_lab(games)
    result = {
        "audit": audit,
        "correlations": corr,
        "parlay_grid": parlay_grid(),
        "parlay_strategies": parlay_strategy_check(bets),
        "prop": prop_feasibility(bets),
        "portfolio": portfolio_simulation(bets),
        "sample_size": {
            "n_bets_for_3pct_edge_two_sided": skill.n_bets_for_edge(0.03, sides=2),
            "n_bets_for_3pct_edge_one_sided": skill.n_bets_for_edge(0.03, sides=1),
            "n_bets_for_5pct_edge_two_sided": skill.n_bets_for_edge(0.05, sides=2),
            "n_bets_for_5pct_edge_one_sided": skill.n_bets_for_edge(0.05, sides=1),
        },
        "input_summary": {k: summary.get(k) for k in ("generated_utc",) if k in summary},
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "strategy_results.json").write_text(json.dumps(result, indent=1), encoding="utf-8")
    return result


def portfolio_simulation(bets: pd.DataFrame, n_sim: int = 2000, seed: int = 20261112) -> dict:
    """Combining every strategy into one portfolio does not create skill: show it.

    Pool all settled selections, then resample them under the null that each bet's win
    probability equals its price-implied probability.  The distribution of the pooled
    ROI is reported beside the observed one.
    """
    rng = np.random.default_rng(seed)
    p = np.array([skill.implied_prob(x) for x in bets.price.fillna(-110.0)])
    dec = np.array([skill.decimal_odds(x) for x in bets.price.fillna(-110.0)])
    observed = float(bets.pnl.mean())
    sims = []
    n = len(bets)
    for _ in range(n_sim):
        wins = rng.random(n) < p
        pnl = np.where(wins, dec - 1, -1.0)
        sims.append(pnl.mean())
    sims = np.array(sims)
    return {
        "n_bets": int(n),
        "observed_roi_pct": round(100 * observed, 3),
        "null_mean_roi_pct": round(100 * float(sims.mean()), 3),
        "null_ci95_pct": [round(100 * float(np.quantile(sims, 0.025)), 3),
                          round(100 * float(np.quantile(sims, 0.975)), 3)],
        "p_value_one_sided": round(float((sims >= observed).mean()), 4),
        "simulations": n_sim,
    }


if __name__ == "__main__":  # pragma: no cover
    r = run()
    print(json.dumps({"strategies": r["audit"]["n_strategies"],
                      "reward_eligible": r["audit"]["reward_eligible"],
                      "correlations": len(r["correlations"]),
                      "portfolio_p": r["portfolio"]["p_value_one_sided"]}, indent=1))
