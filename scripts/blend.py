"""blend.py — the only way an own line can be useful: as an extra input to the market.

Two questions, answered out of sample:
  Q1  Does our own line carry information that the closing line does not?
      -> OLS of the actual result on (market line, own line). A significant own-line
         coefficient means yes.
  Q2  Does a blend beat the market on forecast error?
      -> Fit the blend weight on DISCOVERY only (2000-2015), evaluate on
         CONFIRMATION only (2016-2026). Report MAE, RMSE and a paired test.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DER = os.path.join(ROOT, "data", "derived")
DISC = (2000, 2015)
CONF = (2016, 2026)


def _ols(y, X):
    X = np.column_stack([np.ones(len(X)), X])
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    n, k = X.shape
    s2 = resid @ resid / (n - k)
    cov = s2 * np.linalg.inv(X.T @ X)
    se = np.sqrt(np.diag(cov))
    t = beta / se
    p = 2 * (1 - stats.t.cdf(np.abs(t), n - k))
    return beta, se, p, resid


def analyse(target: str, model_col: str, mkt_col: str) -> dict:
    d = pd.read_csv(os.path.join(DER, "model_predictions.csv"))
    d = d[d[target].notna()].copy()
    y = d[target].to_numpy(float)
    # Orient so that "higher = better for the home team". Spreads are stored in the
    # conventional home-spread orientation (positive = home receiving points), so they
    # are negated; totals need no flip.
    sign = -1.0 if target == "margin" else 1.0
    mk = sign * d[mkt_col].to_numpy(float)
    md = sign * d[model_col].to_numpy(float)

    # Q1 full-sample information test
    beta, se, p, _ = _ols(y, np.column_stack([mk, md]))
    q1 = {
        "intercept": round(float(beta[0]), 4),
        "market_coef": round(float(beta[1]), 4), "market_p": float(f"{p[1]:.4g}"),
        "own_coef": round(float(beta[2]), 4), "own_p": float(f"{p[2]:.4g}"),
        "n": int(len(d)),
        "interpretation": ("own line adds independent information beyond the close"
                           if p[2] < 0.05 and beta[2] > 0 else
                           "no significant independent information beyond the close"),
    }

    # Q2 out-of-sample blend
    tr = (d.season >= DISC[0]) & (d.season <= DISC[1])
    te = (d.season >= CONF[0]) & (d.season <= CONF[1])
    w_fit = float(beta[2] / (beta[1] + beta[2])) if (beta[1] + beta[2]) != 0 else 0.0
    w_fit = float(np.clip(w_fit, 0.0, 1.0))
    blend_tr = w_fit * md[tr] + (1 - w_fit) * mk[tr]
    blend_te = w_fit * md[te] + (1 - w_fit) * mk[te]

    def err_metrics(pred, yy):
        e = pred - yy
        return float(np.abs(e).mean()), float(np.sqrt((e ** 2).mean()))

    mae_m, rmse_m = err_metrics(mk[te], y[te])
    mae_o, rmse_o = err_metrics(md[te], y[te])
    mae_b, rmse_b = err_metrics(blend_te, y[te])
    diff = np.abs(blend_te - y[te]) - np.abs(mk[te] - y[te])
    tt = stats.ttest_1samp(diff, 0.0)

    q2 = {
        "train_window": list(DISC), "test_window": list(CONF),
        "blend_weight_on_own_line": round(w_fit, 4),
        "market_only_mae": round(mae_m, 4), "market_only_rmse": round(rmse_m, 4),
        "own_only_mae": round(mae_o, 4), "own_only_rmse": round(rmse_o, 4),
        "blend_mae": round(mae_b, 4), "blend_rmse": round(rmse_b, 4),
        "blend_minus_market_mae": round(mae_b - mae_m, 4),
        "blend_beats_market_pvalue": float(f"{tt.pvalue:.4g}"),
        "n_test": int(te.sum()),
    }
    return {"information_test": q1, "out_of_sample_blend": q2}


if __name__ == "__main__":
    res = {
        "spread": analyse("margin", "model_spread", "mkt_spread"),
        "total": analyse("total_score", "model_total", "mkt_total"),
    }
    with open(os.path.join(DER, "blend_results.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print(json.dumps(res, indent=2))
