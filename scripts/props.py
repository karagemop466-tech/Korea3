"""Player-prop origination, prop strategies and prop-combo correlation inputs.

Design (important, and the reason the numbers are interpretable)
--------------------------------------------------------------
We have NO verifiable player-prop price data in this environment (see IR-03).
So we do not pretend a real market exists.  Instead every prop market is
defined by an explicit, pre-registered pair:

  * NAIVE LINE   L = trailing 8-game MEDIAN of the stat (rounded to a half point).
                   Median, not mean: these stats are strongly right-skewed (many
                   zero-usage games), and a mean-based line is biased high -- we
                   measured that bias and it is reported on the market page.
                   This stands in for "what a simple book would hang".
  * OUR NUMBER   E = median of the player's last 4 games.  Deliberately the same
                   functional (a median) as the naive line, so the comparison is
                   not contaminated by the mean/median gap that right-skewed
                   usage stats create.  The hypothesis under test is only "does a
                   faster-reacting estimate beat a slow one".

A bet is placed only when our number differs from the naive line by enough to
clear the assumed -110 price.  The hit rate that follows is a real, verifiable
number; the ROI is conditional on the assumed price and is labelled as such.

Everything used for game g comes only from games before g (expanding history,
reset at each season boundary).  Pooled dispersion is estimated from prior
seasons only.
"""
import math

import numpy as np
import pandas as pd

from common import RAW, american_to_decimal

ASSUMED_DEC = float(american_to_decimal(np.array([-110.0]))[0])
BREAKEVEN_HIT = 1.0 / ASSUMED_DEC      # 0.5238
LOOKBACK = 8
EWMA_HALFLIFE = 3.0
MIN_PRIOR_GAMES = 3


def load_playerweeks():
    d = pd.read_csv(f"{RAW}/weekly_player_stats_offense_smaller.csv")
    d = d.drop(columns=[c for c in d.columns if c.startswith("Unnamed")], errors="ignore")
    d = d.drop_duplicates(["player_name", "season", "week", "game_id"])
    d["team"] = d.team.astype(str)
    return d.sort_values(["player_name", "season", "week"]).reset_index(drop=True)


def _half_line(x):
    """Nearest half point.  Integer results are KEPT (a line equal to the median is
    the honest naive quote); pushes on those lines are refunded, not counted as
    losses -- forcing the line off the median silently biased 'over' downward."""
    return round(float(x) * 2) / 2


def build_priors(d, stat, min_games=MIN_PRIOR_GAMES):
    """Trailing mean, trailing sd, EWMA projection and trailing volume per player.

    Season boundary resets the history (conservative: no cross-season carry-over).
    """
    out_mu, out_sd, out_ew, out_n = [], [], [], []
    for player, grp in d.groupby("player_name", sort=False):
        history, prev_season = [], None
        for _, row in grp.iterrows():
            if prev_season is not None and row.season != prev_season:
                history = []
            prev_season = row.season
            hist = history[-LOOKBACK:]
            if len(hist) >= min_games:
                out_mu.append(float(np.median(hist)))
                out_sd.append(float(np.std(hist, ddof=1)))
                out_ew.append(float(np.median(hist[-4:])))
                out_n.append(len(hist))
            else:
                out_mu.append(np.nan)
                out_sd.append(np.nan)
                out_ew.append(np.nan)
                out_n.append(len(hist))
            history.append(float(row[stat]))
    d[f"{stat}_mu"] = out_mu
    d[f"{stat}_sd"] = out_sd
    d[f"{stat}_recent"] = out_ew
    d[f"{stat}_n"] = out_n
    return d


def _pooled_sd_by_season(d, stat):
    """Median within-player sd per (position, season) using only EARLIER seasons."""
    tmp = d.dropna(subset=[f"{stat}_sd"]).copy()
    pooled = {}
    for pos in tmp.position.dropna().unique():
        sub = tmp[(tmp.position == pos)]
        for s in sorted(sub.season.unique()):
            prior = sub[sub.season < s][f"{stat}_sd"]
            pooled[(pos, s)] = float(np.median(prior)) if len(prior) >= 200 else np.nan
    return pooled


def _predictive_sd(d, stat):
    """Empirical sd of (actual - recent_median) per (position, season), using only
    seasons strictly before that season.  This is the dispersion our probability
    model needs; estimating it from prior seasons keeps it out-of-sample."""
    tmp = d.dropna(subset=[f"{stat}_recent"]).copy()
    tmp["resid"] = tmp[stat] - tmp[f"{stat}_recent"]
    out = {}
    for pos in tmp.position.dropna().unique():
        sub = tmp[tmp.position == pos]
        for s in sorted(sub.season.unique()):
            prior = sub[sub.season < s].resid
            out[(pos, s)] = float(prior.std(ddof=1)) if len(prior) >= 300 else np.nan
    return out


def build_prop_markets(d, stat, min_prior_games=MIN_PRIOR_GAMES):
    from math import erf, sqrt

    def Phi(x):
        return 0.5 * (1.0 + erf(x / sqrt(2.0)))

    sdmap = _predictive_sd(d, stat)
    d = d[d[f"{stat}_n"] >= min_prior_games].copy()
    tmp = d.dropna(subset=[f"{stat}_recent"]).copy()
    tmp["resid"] = tmp[stat] - tmp[f"{stat}_recent"]
    global_sd = float(tmp.resid.std(ddof=1))

    sig = []
    for _, row in d.iterrows():
        v = sdmap.get((row.position, row.season))
        sig.append(v if (v is not None and np.isfinite(v) and v > 0.5) else global_sd)
    d["sigma"] = np.clip(np.array(sig, dtype=float), 0.5, None)
    d["line"] = [_half_line(v) for v in d[f"{stat}_mu"]]   # mu is the trailing 8-game median
    d["p_over"] = [1 - Phi((ln - e) / s) for ln, e, s in
                   zip(d["line"], d[f"{stat}_recent"], d["sigma"])]
    d["over_won"] = (d[stat] > d["line"]).astype(int)
    d["push"] = (d[stat] == d["line"]).astype(int)
    d["stat"] = stat
    return d


PROP_SPECS = {
    "receiving_yards": [
        dict(id="T01", side="over", min_edge=0.05, vol=lambda x: x.targets_mu >= 4.0,
             label="Rec yds OVER vs naive trailing line, prior targets >= 4, edge >= 5pp"),
        dict(id="T02", side="under", min_edge=0.05, vol=lambda x: x.targets_mu >= 4.0,
             label="Rec yds UNDER vs naive trailing line, prior targets >= 4, edge >= 5pp"),
        dict(id="T03", side="over", min_edge=0.08, vol=lambda x: x.targets_mu >= 6.0,
             label="Rec yds OVER, high-usage (prior targets >= 6), edge >= 8pp (selective)"),
    ],
    "receptions": [
        dict(id="T04", side="over", min_edge=0.05, vol=lambda x: x.targets_mu >= 4.0,
             label="Receptions OVER vs naive trailing line, prior targets >= 4, edge >= 5pp"),
        dict(id="T05", side="under", min_edge=0.05, vol=lambda x: x.targets_mu >= 4.0,
             label="Receptions UNDER vs naive trailing line, prior targets >= 4, edge >= 5pp"),
    ],
    "rush_attempts": [
        dict(id="T06", side="over", min_edge=0.05, vol=lambda x: x.rush_attempts_mu >= 8.0,
             label="Rush attempts OVER, prior carries >= 8, edge >= 5pp"),
        dict(id="T07", side="under", min_edge=0.05, vol=lambda x: x.rush_attempts_mu >= 8.0,
             label="Rush attempts UNDER, prior carries >= 8, edge >= 5pp"),
    ],
}


def apply_prop_spec(mk, spec):
    side = spec["side"]
    m = mk[mk.apply(spec["vol"], axis=1)].copy()
    edge = (m.p_over - 0.5) if side == "over" else (0.5 - m.p_over)
    m = m[edge >= spec["min_edge"]].copy()
    if m.empty:
        return m
    m["strategy_id"] = spec["id"]
    m["side"] = side
    m["odds_dec"] = ASSUMED_DEC
    m["p_model"] = np.where(side == "over", m.p_over, 1 - m.p_over)
    m["p_market"] = 0.5
    m["ev"] = m.p_model * (ASSUMED_DEC - 1) - (1 - m.p_model)
    m["won"] = np.where(side == "over", m.over_won, 1 - m.over_won)
    m.loc[m.push == 1, "won"] = 0
    m["profit"] = np.where(m.push == 1, 0.0,
                           np.where(m.won == 1, ASSUMED_DEC - 1, -1.0))
    return m


def build_prop_market_table():
    """Return dict stat -> market dataframe with priors attached."""
    d = load_playerweeks()
    for stat in ["receiving_yards", "receptions", "rush_attempts", "targets"]:
        d = build_priors(d, stat)
    out = {}
    for stat in ["receiving_yards", "receptions", "rush_attempts"]:
        out[stat] = build_prop_markets(d, stat)
    return d, out


# --------------------------------------------------------------------------
# probability calibration (fitted on PRIOR seasons only)
# --------------------------------------------------------------------------
# probability model: empirical, binned on prior seasons only
# --------------------------------------------------------------------------
def empirical_probability(d, stat, n_bins=15, prior_strength=25.0, col="p_over"):
    """Replace the normal-model probability with an empirical frequency map.

    z = (line - recent_median) / sigma  is the standardized distance between the
    naive line and our number.  For each season we take the empirical over-rate
    inside each z-bin from PRIOR seasons (shrunk toward 50/50 and forced
    monotone non-decreasing).  This is what removes the tail over-confidence the
    normal model showed (predicted 75% over, realised 52%)."""
    d = d.copy()
    d["z"] = (d[f"{stat}_recent"] - d["line"]) / d["sigma"]
    p = np.full(len(d), np.nan)
    season_map = {}
    for s in sorted(d.season.unique()):
        train = d[(d.season < s) & (d.push == 0)]
        cur = (d.season == s).values
        if len(train) < 2000:
            p[cur] = 0.5
            season_map[int(s)] = {"bins": None, "rate": None, "n_train": int(len(train))}
            continue
        edges = np.quantile(train.z.values, np.linspace(0, 1, n_bins + 1))
        edges[0], edges[-1] = -1e9, 1e9
        b = np.clip(np.digitize(train.z.values, edges[1:-1]), 0, n_bins - 1)
        hits = np.bincount(b, weights=train.over_won.values, minlength=n_bins)
        tot = np.bincount(b, minlength=n_bins)
        rate = (hits + prior_strength * 0.5) / (tot + prior_strength)
        rate = np.maximum.accumulate(rate)          # monotone in z
        bc = np.clip(np.digitize(d.loc[cur, "z"].values, edges[1:-1]), 0, n_bins - 1)
        p[cur] = rate[bc]
        season_map[int(s)] = {"n_train": int(len(train)),
                              "bin_edges": [float(x) for x in edges[1:-1]],
                              "rate": [float(x) for x in rate],
                              "bin_n": [int(x) for x in tot]}
    d["p_over_raw"] = d[col]
    d["p_over"] = p
    return d, season_map
