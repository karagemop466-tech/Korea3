"""Feature engineering and own-line (spread/total) origination model.

STRICT POINT-IN-TIME CONTRACT
-----------------------------
Everything attached to a game in `build()` is computed from games that kicked off
strictly before that game. Ratings are updated *after* a game's features are
emitted. Standings/points totals are trailing, never season-final.

Model coefficients are estimated only on the DESIGN window (1999-2018); the
validation (2019-2023) and holdout (2024-2026) windows never influence a
coefficient reported for them.
"""
from __future__ import annotations

from collections import defaultdict

from lib_core import load_games, mean

DESIGN = (1999, 2018)
VALIDATION = (2019, 2023)
HOLDOUT = (2024, 2026)

ELO_START = 1500.0
ELO_K = 20.0
ELO_REVERT = 1 / 3.0        # regression to the mean between seasons
EWMA_ALPHA = 0.25
EWMA_SHRINK = 0.6           # weight on last season's level at a new season start
LEAGUE_PPG_PRIOR = 21.8     # only used until a league average exists in the data


def ols(X, y):
    """Ordinary least squares via normal equations (stdlib only). Returns (beta, r2)."""
    n, k = len(X), len(X[0])
    A = [[0.0] * k for _ in range(k)]
    b = [0.0] * k
    for i in range(n):
        for j in range(k):
            b[j] += X[i][j] * y[i]
            for m in range(k):
                A[j][m] += X[i][j] * X[i][m]
    # Gauss-Jordan with partial pivoting
    M = [row[:] + [b[i]] for i, row in enumerate(A)]
    for c in range(k):
        piv = max(range(c, k), key=lambda r: abs(M[r][c]))
        if abs(M[piv][c]) < 1e-12:
            continue
        M[c], M[piv] = M[piv], M[c]
        pv = M[c][c]
        M[c] = [v / pv for v in M[c]]
        for r in range(k):
            if r != c and M[r][c]:
                f = M[r][c]
                M[r] = [vr - f * vc for vr, vc in zip(M[r], M[c])]
    beta = [M[i][k] for i in range(k)]
    yh = [sum(beta[j] * X[i][j] for j in range(k)) for i in range(n)]
    my = sum(y) / n
    sst = sum((v - my) ** 2 for v in y)
    sse = sum((y[i] - yh[i]) ** 2 for i in range(n))
    return beta, (1 - sse / sst if sst else None)


def _season_of(g):
    return g["season"]


def build(games=None):
    """Return list of dicts, one per PLAYED game, with point-in-time features."""
    games = games or load_games()
    games = [g for g in games if g["played"]]
    games.sort(key=lambda g: (g["gameday"] or "", g["game_id"]))

    elo = defaultdict(lambda: ELO_START)
    off = {}
    dfn = {}
    last_seen_season = {}
    prior_season_off = {}
    prior_season_def = {}
    league_pts = []           # running list of team-points for league average
    team_last_game = {}
    team_last_margin = {}
    team_last_ats = {}
    games_in_season = defaultdict(int)

    feats = []
    for g in games:
        s = _season_of(g)
        h, a = g["home_team"], g["away_team"]

        # ------- season boundary housekeeping (uses only completed seasons) -------
        for t in (h, a):
            if last_seen_season.get(t) not in (None, s):
                prior_season_off[t] = off.get(t)
                prior_season_def[t] = dfn.get(t)
                la = mean(list(off.values())) or LEAGUE_PPG_PRIOR
                off[t] = EWMA_SHRINK * (off.get(t) or la) + (1 - EWMA_SHRINK) * la
                dfn[t] = EWMA_SHRINK * (dfn.get(t) or la) + (1 - EWMA_SHRINK) * la
                elo[t] = ELO_START + (1 - ELO_REVERT) * (elo[t] - ELO_START)
            last_seen_season[t] = s

        la = mean(list(off.values())) or LEAGUE_PPG_PRIOR
        off_h = off.get(h, la)
        off_a = off.get(a, la)
        def_h = dfn.get(h, la)
        def_a = dfn.get(a, la)
        elo_h, elo_a = elo[h], elo[a]

        lh = team_last_game.get(h) or {}
        la_ = team_last_game.get(a) or {}

        f = {
            "game_id": g["game_id"], "season": s, "week": g["week"], "game_type": g["game_type"],
            "gameday": g["gameday"], "home_team": h, "away_team": a,
            "home_score": g["home_score"], "away_score": g["away_score"],
            "margin": g["margin"], "tot": g["tot"],
            "spread_line": g["spread_line"], "total_line": g["total_line"],
            "home_ml": g["home_moneyline"], "away_ml": g["away_moneyline"],
            "home_spread_odds": g["home_spread_odds"], "away_spread_odds": g["away_spread_odds"],
            "over_odds": g["over_odds"], "under_odds": g["under_odds"],
            "div_game": g["div_game"], "roof": g.get("roof") or "",
            "temp": g["temp"], "wind": g["wind"],
            "home_rest": g["home_rest"], "away_rest": g["away_rest"],
            "location": g.get("location") or "",
            # ---- point-in-time features ----
            "elo_h": elo_h, "elo_a": elo_a, "elo_diff": elo_h - elo_a,
            "off_h": off_h, "off_a": off_a, "def_h": def_h, "def_a": def_a,
            "league_ppg": la,
            "rest_diff": (g["home_rest"] - g["away_rest"]
                          if g["home_rest"] is not None and g["away_rest"] is not None else None),
            "min_rest": (min(g["home_rest"], g["away_rest"])
                         if g["home_rest"] is not None and g["away_rest"] is not None else None),
            "home_off_bye": 1 if (g["home_rest"] or 0) >= 13 else 0,
            "away_off_bye": 1 if (g["away_rest"] or 0) >= 13 else 0,
            "last_margin_h": team_last_margin.get(h),
            "last_margin_a": team_last_margin.get(a),
            "last_ats_h": team_last_ats.get(h),
            "last_ats_a": team_last_ats.get(a),
            "exp_home_pts": off_h + def_a - la,
            "exp_away_pts": off_a + def_h - la,
            "wind_flag": 1 if (g["wind"] or 0) >= 15 else 0,
            "cold_flag": 1 if (g["temp"] is not None and g["temp"] <= 32) else 0,
            "dome_flag": 1 if (g.get("roof") or "").lower() in ("dome", "closed") else 0,
        }
        f["exp_total"] = f["exp_home_pts"] + f["exp_away_pts"]
        feats.append(f)

        # ------------------- update ratings AFTER emitting features -------------------
        elo_diff = elo_h - elo_a
        exp_home = 1.0 / (1.0 + 10 ** (-(elo_diff + 48.0) / 400.0))  # 48 ≈ home field
        mov = abs(g["margin"])
        mult = ((mov + 3.0) ** 0.8) / (7.5 + 0.006 * elo_diff * (1 if g["margin"] > 0 else -1))
        score = 1.0 if g["margin"] > 0 else (0.0 if g["margin"] < 0 else 0.5)
        delta = ELO_K * mult * (score - exp_home)
        elo[h] += delta
        elo[a] -= delta

        off[h] = EWMA_ALPHA * g["home_score"] + (1 - EWMA_ALPHA) * off_h
        dfn[h] = EWMA_ALPHA * g["away_score"] + (1 - EWMA_ALPHA) * def_h
        off[a] = EWMA_ALPHA * g["away_score"] + (1 - EWMA_ALPHA) * off_a
        dfn[a] = EWMA_ALPHA * g["home_score"] + (1 - EWMA_ALPHA) * def_a
        league_pts.extend([g["home_score"], g["away_score"]])

        ats = (g["margin"] - g["spread_line"]) if g["spread_line"] is not None else None
        team_last_game[h] = g
        team_last_game[a] = g
        team_last_margin[h] = g["margin"]
        team_last_margin[a] = -g["margin"]
        team_last_ats[h] = ats
        team_last_ats[a] = (-ats if ats is not None else None)
    return feats


def fit_model(feats):
    """Estimate own spread/total model on the DESIGN window only."""
    tr = [f for f in feats if DESIGN[0] <= f["season"] <= DESIGN[1]]
    # spread: margin = b0 + b1 * elo_diff
    X = [[1.0, f["elo_diff"]] for f in tr]
    y = [f["margin"] for f in tr]
    bs, r2s = ols(X, y)
    # totals: total = c0 + c1*exp_total + c2*wind + c3*cold + c4*dome
    Xt = [[1.0, f["exp_total"], float(f["wind_flag"]), float(f["cold_flag"]), float(f["dome_flag"])] for f in tr]
    yt = [f["tot"] for f in tr]
    bt, r2t = ols(Xt, yt)
    return {
        "spread_beta": bs, "spread_r2": r2s,
        "total_beta": bt, "total_r2": r2t,
        "n_train": len(tr),
        "train_window": DESIGN,
        "spread_formula": "model_margin = b0 + b1 * (elo_home - elo_away)",
        "total_formula": "model_total = c0 + c1*exp_total + c2*wind>=15 + c3*temp<=32F + c4*dome",
    }


def apply_model(feats, model):
    bs, bt = model["spread_beta"], model["total_beta"]
    for f in feats:
        f["model_margin"] = bs[0] + bs[1] * f["elo_diff"]
        f["model_total"] = (bt[0] + bt[1] * f["exp_total"] + bt[2] * f["wind_flag"]
                            + bt[3] * f["cold_flag"] + bt[4] * f["dome_flag"])
        if f["spread_line"] is not None:
            f["model_edge_home"] = f["model_margin"] - f["spread_line"]
        if f["total_line"] is not None:
            f["model_total_edge"] = f["model_total"] - f["total_line"]
    return feats
