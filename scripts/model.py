"""model.py — originate our own NFL spread and total (the "own line").

Design (fixed before any evaluation, to avoid selection bias):
  * One coherent points model, two outputs. For every (game, team) pair we model
    points scored:
        pts = mu + off[team] + def[opponent] + hfa*home + beta·(situational)
    Own spread = pred_home_pts - pred_away_pts;  Own total = pred_home_pts + pred_away_pts.
  * Walk-forward: for each (season, week) we fit ONLY on games whose gameday is
    strictly earlier than the first gameday of that week. No look-ahead.
  * Recency weighting: exponential decay, half-life 365 days.
  * Ridge penalty lambda = 4.0 on team ratings (a priori; never tuned on test data).
  * Neutral-site games get no home-field term.

Variants reported (an honest model-comparison table, not one cherry-picked spec):
  A  ratings only
  B  A + rest differential (home_rest - away_rest)
  C  B + division indicator
  D  C + dome indicator (totals only makes sense, applied to both for simplicity)
Sensitivity: lambda in {1, 4, 16} x half-life in {180, 365, 730} days.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DER = os.path.join(ROOT, "data", "derived")

HALF_LIFE_DAYS = 365.0
LAMBDA = 4.0
MIN_PRIOR_GAMES = 240  # do not publish an own-line until the model has real history


def _design(g: pd.DataFrame, teams: list[str], variant: str) -> tuple[np.ndarray, np.ndarray]:
    """Stacked design: two rows per game (home scoring, away scoring)."""
    n = len(g)
    idx = {t: i for i, t in enumerate(teams)}
    p = 2 * len(teams)
    n_extra = {"A": 0, "B": 1, "C": 2, "D": 3}[variant]
    X = np.zeros((2 * n, p + 2 + n_extra))
    # columns: off[0..T-1], def[T..2T-1], mu, hfa, extras...
    mu_c, hfa_c = p, p + 1
    X[:, mu_c] = 1.0
    hi = g["home_team"].map(idx).to_numpy()
    ai = g["away_team"].map(idx).to_numpy()
    home_pts = g["home_score"].to_numpy(float)
    away_pts = g["away_score"].to_numpy(float)

    rows_h = np.arange(n)
    rows_a = np.arange(n) + n
    X[rows_h, hi] = 1.0
    X[rows_h, len(teams) + ai] = 1.0
    X[rows_a, ai] = 1.0
    X[rows_a, len(teams) + hi] = 1.0

    neutral = (g["location"] == "Neutral").to_numpy()
    X[rows_h, hfa_c] = np.where(neutral, 0.0, 1.0)

    if n_extra >= 1:
        rd = g["rest_diff"].fillna(0).to_numpy(float)
        rd = np.clip(rd, -7, 7) / 7.0
        X[rows_h, hfa_c + 1] = rd
        X[rows_a, hfa_c + 1] = -rd
    if n_extra >= 2:
        dv = g["div_game"].fillna(0).to_numpy(float)
        X[rows_h, hfa_c + 2] = dv
        X[rows_a, hfa_c + 2] = dv
    if n_extra >= 3:
        dm = g["is_dome"].fillna(0).to_numpy(float)
        X[rows_h, hfa_c + 3] = dm
        X[rows_a, hfa_c + 3] = dm

    y = np.concatenate([home_pts, away_pts])
    return X, y


def fit_ridge(X: np.ndarray, y: np.ndarray, w: np.ndarray, n_teams: int, lam: float) -> np.ndarray:
    """Weighted ridge. Team-rating columns are penalised; mu/hfa/extras get a tiny penalty."""
    p = X.shape[1]
    pen = np.full(p, 1e-6)
    pen[: 2 * n_teams] = lam
    Xw = X * w[:, None]
    A = X.T @ Xw + np.diag(pen)
    b = Xw.T @ y
    return np.linalg.solve(A, b)


def predict(beta: np.ndarray, teams: list[str], g: pd.DataFrame, variant: str) -> tuple[np.ndarray, np.ndarray]:
    idx = {t: i for i, t in enumerate(teams)}
    T = len(teams)
    mu = beta[2 * T]
    hfa = beta[2 * T + 1]
    off = beta[:T]
    dfn = beta[T : 2 * T]
    hi = g["home_team"].map(idx).to_numpy()
    ai = g["away_team"].map(idx).to_numpy()
    neutral = (g["location"] == "Neutral").to_numpy()

    h = mu + off[hi] + dfn[ai] + np.where(neutral, 0.0, hfa)
    a = mu + off[ai] + dfn[hi]
    if variant != "A":
        rd = np.clip(g["rest_diff"].fillna(0).to_numpy(float), -7, 7) / 7.0
        b = beta[2 * T + 2]
        h = h + b * rd
        a = a - b * rd
    if variant in ("C", "D"):
        dv = g["div_game"].fillna(0).to_numpy(float)
        b = beta[2 * T + 3]
        h = h + b * dv
        a = a + b * dv
    if variant == "D":
        dm = g["is_dome"].fillna(0).to_numpy(float)
        b = beta[2 * T + 4]
        h = h + b * dm
        a = a + b * dm
    return h, a


def run(variant: str = "A", lam: float = LAMBDA, half_life: float = HALF_LIFE_DAYS) -> pd.DataFrame:
    d = pd.read_csv(os.path.join(DER, "model_dataset.csv"), low_memory=False)
    d["gameday"] = pd.to_datetime(d["gameday"])
    teams = sorted(set(d["home_team"]) | set(d["away_team"]))
    d = d.sort_values(["gameday", "game_id"]).reset_index(drop=True)

    out = []
    for (season, week), grp in d.groupby(["season", "week"], sort=True):
        cutoff = grp["gameday"].min()
        prior = d[(d["gameday"] < cutoff) & (d["season"] >= season - 3)]
        if len(prior) < MIN_PRIOR_GAMES:
            continue
        # weight: exponential decay by days before cutoff
        age = (cutoff - prior["gameday"]).dt.days.to_numpy(float)
        w = 0.5 ** (age / half_life)
        X, y = _design(prior, teams, variant)
        w2 = np.concatenate([w, w])          # stacked design: same weight for both team rows
        beta = fit_ridge(X, y, w2, len(teams), lam)
        ph, pa = predict(beta, teams, grp, variant)
        g2 = grp.copy()
        g2["pred_home_pts"] = ph
        g2["pred_away_pts"] = pa
        g2["model_spread"] = -(ph - pa)          # conventional home spread (>0 => home getting points)
        g2["model_total"] = ph + pa
        out.append(g2)
    res = pd.concat(out, ignore_index=True)

    res["mkt_spread"] = res["home_spread"]
    res["mkt_total"] = res["total_line"]
    res["edge_spread"] = res["model_spread"] - res["mkt_spread"]   # >0 => model likes HOME
    res["edge_total"] = res["model_total"] - res["mkt_total"]      # >0 => model likes OVER
    res["err_spread_model"] = res["model_spread"] - (-res["margin"])
    res["err_spread_mkt"] = res["mkt_spread"] - (-res["margin"])
    res["err_total_model"] = res["model_total"] - res["total_score"]
    res["err_total_mkt"] = res["mkt_total"] - res["total_score"]
    res["row_source"] = res["row_source"]
    return res


def metrics(res: pd.DataFrame) -> dict:
    m = {}
    m["n_games"] = int(len(res))
    m["seasons"] = [int(res.season.min()), int(res.season.max())]
    for k in ["spread", "total"]:
        em = res[f"err_{k}_model"]
        ek = res[f"err_{k}_mkt"]
        m[k] = {
            "model_mae": round(float(em.abs().mean()), 3),
            "market_mae": round(float(ek.abs().mean()), 3),
            "model_rmse": round(float(np.sqrt((em ** 2).mean())), 3),
            "market_rmse": round(float(np.sqrt((ek ** 2).mean())), 3),
            "model_bias": round(float(em.mean()), 3),
            "market_bias": round(float(ek.mean()), 3),
            "corr_model_vs_market": round(float(res[f"model_{k}"].corr(res[f"mkt_{k}"])), 4),
            "corr_model_vs_actual": round(
                float(res[f"model_{k}"].corr(res["margin" if k == "spread" else "total_score"])), 4
            ),
            "corr_market_vs_actual": round(
                float(res[f"mkt_{k}"].corr(res["margin" if k == "spread" else "total_score"])), 4
            ),
            "pct_within_1pt_of_market": round(float((res[f"model_{k}"] - res[f"mkt_{k}"]).abs().le(1).mean()), 4),
            "pct_within_3pt_of_market": round(float((res[f"model_{k}"] - res[f"mkt_{k}"]).abs().le(3).mean()), 4),
            "mean_abs_edge": round(float((res[f"model_{k}"] - res[f"mkt_{k}"]).abs().mean()), 3),
        }
    # side agreement with the market
    side_model = np.sign(-res["model_spread"])   # +1 => model favours home
    side_mkt = np.sign(-res["mkt_spread"])
    m["side_agreement_with_market"] = round(float((side_model == side_mkt).mean()), 4)
    # paired test: is model MAE worse than market MAE, spread?
    dm = res["err_spread_model"].abs() - res["err_spread_mkt"].abs()
    t = stats.ttest_1samp(dm, 0.0)
    m["mae_diff_spread_model_minus_market"] = round(float(dm.mean()), 3)
    m["mae_diff_spread_pvalue"] = float(f"{t.pvalue:.4g}")
    dt = res["err_total_model"].abs() - res["err_total_mkt"].abs()
    t2 = stats.ttest_1samp(dt, 0.0)
    m["mae_diff_total_model_minus_market"] = round(float(dt.mean()), 3)
    m["mae_diff_total_pvalue"] = float(f"{t2.pvalue:.4g}")
    return m


def by_season(res: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for s, g in res.groupby("season"):
        rows.append({
            "season": int(s),
            "games": int(len(g)),
            "model_mae_spread": round(float(g["err_spread_model"].abs().mean()), 2),
            "market_mae_spread": round(float(g["err_spread_mkt"].abs().mean()), 2),
            "model_mae_total": round(float(g["err_total_model"].abs().mean()), 2),
            "market_mae_total": round(float(g["err_total_mkt"].abs().mean()), 2),
            "bias_spread": round(float(g["err_spread_model"].mean()), 2),
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    variants = {}
    for v in ["A", "B", "C", "D"]:
        r = run(variant=v)
        variants[v] = metrics(r)
        r.to_csv(os.path.join(DER, f"model_predictions_{v}.csv"), index=False)
        print(f"variant {v}: n={variants[v]['n_games']} spread MAE {variants[v]['spread']['model_mae']} "
              f"(mkt {variants[v]['spread']['market_mae']}) | total MAE {variants[v]['total']['model_mae']} "
              f"(mkt {variants[v]['total']['market_mae']})")

    # primary published model = variant B (ratings + rest), chosen on the *training* era
    # only (1999-2015) inside signals.py; we persist all variants so the choice is auditable.
    base = run(variant="B")
    base.to_csv(os.path.join(DER, "model_predictions.csv"), index=False)
    by_season(base).to_csv(os.path.join(DER, "model_by_season.csv"), index=False)

    sens = []
    for lam in (1.0, 4.0, 16.0):
        for hl in (180.0, 365.0, 730.0):
            r = run(variant="B", lam=lam, half_life=hl)
            mm = metrics(r)
            sens.append({
                "lambda": lam, "half_life_days": hl,
                "model_mae_spread": mm["spread"]["model_mae"],
                "market_mae_spread": mm["spread"]["market_mae"],
                "model_mae_total": mm["total"]["model_mae"],
                "market_mae_total": mm["total"]["market_mae"],
            })
    pd.DataFrame(sens).to_csv(os.path.join(DER, "model_sensitivity.csv"), index=False)

    with open(os.path.join(DER, "model_metrics.json"), "w", encoding="utf-8") as fh:
        json.dump({"primary_variant": "B", "variants": variants,
                   "sensitivity": sens}, fh, indent=2)
    print(json.dumps(metrics(base), indent=2))
