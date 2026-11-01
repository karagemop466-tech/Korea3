"""Walk-forward model that originates our own number for every game.

For season S the coefficients are estimated on seasons < S only, so no game
ever informs its own prediction.  Two linear models, both ordinary least
squares solved with numpy:

    margin  ~ 1 + elo_diff + form_diff + rest_diff + div_game
    total   ~ 1 + off_home + def_away + off_away + def_home + dome

Specification note: the two feature sets above were chosen once, using only the
2003-2014 walk-forward RMSE as the selection criterion (see
research/03_strategies.md).  They were then applied unchanged to every later
season, so the betting results reported for 2015+ were not part of the
selection decision.

Residual standard deviations from the training window become the sigmas used
for probability estimates.  Everything is deterministic.
"""
import numpy as np
import pandas as pd

from common import DERIVED, write_json, r
from features import build_features, assert_point_in_time

FIRST_PREDICT_SEASON = 2003     # needs ~4 seasons of history behind it
MIN_TRAIN = 400


def fit_ols(X, y):
    coef, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ coef
    return coef, resid


def build_predictions(df):
    """Predict EVERY game in the frame, including games with no result yet
    (that is how the 2026 line board is produced).  Coefficients are always fit
    on completed games only, from seasons strictly before the game's season."""
    df = df.copy()
    out = []
    params = {}
    for season in sorted(df.season.unique()):
        if season < FIRST_PREDICT_SEASON:
            continue
        train = df[(df.season < season) & df.result.notna()]
        if len(train) < MIN_TRAIN:
            continue

        Xm = np.column_stack([
            np.ones(len(train)),
            train.elo_diff.values,
            train.form_diff.values,
            np.nan_to_num(train.rest_diff.values),
            (train.div_game == 1).astype(float).values,
        ])
        ym = train.result.values.astype(float)
        cm, rm = fit_ols(Xm, ym)
        sig_m = float(np.std(rm, ddof=1))

        Xt = np.column_stack([
            np.ones(len(train)),
            train.off_home.values, train.def_away.values,
            train.off_away.values, train.def_home.values, train.dome.values,
        ])
        yt = train.total.values.astype(float)
        ct, rt = fit_ols(Xt, yt)
        sig_t = float(np.std(rt, ddof=1))

        params[int(season)] = dict(
            train_games=int(len(train)),
            margin_coefs=[float(v) for v in cm], sigma_margin=sig_m,
            total_coefs=[float(v) for v in ct], sigma_total=sig_t,
        )

        cur = df[df.season == season]
        Xc = np.column_stack([
            np.ones(len(cur)),
            cur.elo_diff.values,
            cur.form_diff.values,
            np.nan_to_num(cur.rest_diff.values),
            (cur.div_game == 1).astype(float).values,
        ])
        Xct = np.column_stack([
            np.ones(len(cur)),
            cur.off_home.values, cur.def_away.values,
            cur.off_away.values, cur.def_home.values, cur.dome.values,
        ])
        part = cur.copy()
        part["mu_margin"] = Xc @ cm
        part["sigma_margin"] = sig_m
        part["mu_total"] = Xct @ ct
        part["sigma_total"] = sig_t
        out.append(part)

    pred = pd.concat(out, ignore_index=True)
    # our own number, expressed the way a sportsbook quotes it (home perspective)
    pred["my_spread"] = [round_half(x) for x in pred.mu_margin]
    pred["my_total"] = [round_half(x) for x in pred.mu_total]
    pred["edge_spread"] = pred.mu_margin - pred.spread_line
    pred["edge_total"] = pred.mu_total - pred.total_line
    return pred, params


def round_half(x):
    """Round to the nearest half point (books quote halves / integers)."""
    if pd.isna(x):
        return np.nan
    return float(np.round(x * 2) / 2)


def quality_report(pred):
    d = pred[pred.spread_line.notna() & pred.result.notna()]
    mkt_rmse = float(np.sqrt(np.mean((d.spread_line - d.result) ** 2)))
    mod_rmse = float(np.sqrt(np.mean((d.mu_margin - d.result) ** 2)))
    mkt_corr = float(np.corrcoef(d.spread_line, d.result)[0, 1])
    mod_corr = float(np.corrcoef(d.mu_margin, d.result)[0, 1])
    dt = pred[pred.total_line.notna() & pred.total.notna()]
    mkt_t_rmse = float(np.sqrt(np.mean((dt.total_line - dt.total) ** 2)))
    mod_t_rmse = float(np.sqrt(np.mean((dt.mu_total - dt.total) ** 2)))
    return dict(
        n_games=int(len(d)),
        market_spread_rmse=mkt_rmse, model_spread_rmse=mod_rmse,
        market_spread_corr=mkt_corr, model_spread_corr=mod_corr,
        market_total_rmse=mkt_t_rmse, model_total_rmse=mod_t_rmse,
        mae_gap_points=float(np.mean(np.abs(d.edge_spread))),
        share_games_edge_ge_2=float((d.edge_spread.abs() >= 2).mean()),
    )


if __name__ == "__main__":
    df = build_features()
    guard = assert_point_in_time(df)
    pred, params = build_predictions(df)
    pred.to_csv(f"{DERIVED}/predictions.csv", index=False)
    rep = quality_report(pred)
    write_json(f"{DERIVED}/model_quality.json", {"report": rep, "season_params": params,
                                                "leakage_guard": guard})
    print("games predicted:", len(pred))
    for k, v in rep.items():
        print(f"  {k}: {r(v,4)}")
    print("leakage guard:", guard)
