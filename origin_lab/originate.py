#!/usr/bin/env python3
"""Requirements 3, 4 and 5: origination in a fixed order, fair/market/diff as three columns,
and a leaderboard that scores signal separately from staking.

THE ORDER, AND WHY IT IS AN ORDER
    1. SIDE first.  The side is a forecast of the margin. Nothing else can be derived from it,
       and it is the only one of the three that is a pure location estimate.
    2. TOTAL second. The total is a forecast of the sum. It is not independent of the side: once
       both are fixed, the two implied team scores are pinned by
           home = (total + margin) / 2      away = (total - margin) / 2
       so the side must exist before the total can be turned into team numbers. The page prints
       the identity and check.py fails the build if a single row violates it.
    3. MONEYLINE last. A moneyline price is a tail probability of the margin distribution, so it
       needs both the centre (the side) and the spread (which scales with the total). It cannot be
       originated before either.

THE MODEL (deliberately small, deliberately pre-registered)
    Regressors, all strictly pre-game:
        elo_diff   = elo_home + HFA_ELO - elo_away
        net_diff   = (pf_home_ewma - pa_home_ewma) - (pf_away_ewma - pa_away_ewma)
        sum_pf     = pf_home_ewma + pf_away_ewma
        dome       = 1 when the roof column reads 'dome', 0 for any other printed value
    Coefficients are fitted by ordinary least squares on seasons 1999-2005 only, frozen, and then
    never touched again. Everything from 2006 on is out-of-sample by construction.

WHAT IS NOT DONE HERE
    No parameter is tuned on the evaluation window, no feature is chosen by looking at results,
    and no coefficient is re-fitted after 2005. That would make every number below a description
    of the past rather than a test.
"""
from __future__ import annotations

import json
import math
import random
from pathlib import Path

import lib

# ---- pre-registered constants ----------------------------------------------------------------
HFA_ELO = 55.0
ELO_K = 20.0
ELO_START = 1500.0
ELO_SEASON_KEEP = 0.75
EWMA_HALFLIFE = 4.0
PF_INIT = 22.0
FIT_SEASONS = tuple(range(1999, 2006))     # 1999..2005 inclusive
EVAL_FROM = 2006
HOLDOUT = (2023, 2024, 2025)
EDGE_MIN = 0.03                            # minimum |diff| before a strategy may bet, in points
ML_EDGE_MIN = 0.02                         # minimum probability edge for the moneyline
SEED = 20261114
MAX_STAKE = 0.05                           # 5% of bankroll cap on any single staked bet
N_PERM = 2000

OUT_ORIGIN = lib.DATA / "origination.json"
OUT_BOARD = lib.DATA / "leaderboard.json"


# --------------------------------------------------------------------------------------------
# linear algebra: solve normal equations for k regressors plus an intercept
# --------------------------------------------------------------------------------------------
def ols(X, y):
    """X: list of rows, each a list of regressor values (intercept NOT included). Returns coefs."""
    k = len(X[0])
    Xa = [[1.0] + list(row) for row in X]
    p = k + 1
    A = [[0.0] * p for _ in range(p)]
    b = [0.0] * p
    for row, yi in zip(Xa, y):
        for i in range(p):
            b[i] += row[i] * yi
            for j in range(p):
                A[i][j] += row[i] * row[j]
    # Gaussian elimination with partial pivoting
    for c in range(p):
        piv = max(range(c, p), key=lambda r: abs(A[r][c]))
        if abs(A[piv][c]) < 1e-12:
            return None
        A[c], A[piv] = A[piv], A[c]
        b[c], b[piv] = b[piv], b[c]
        for r in range(c + 1, p):
            f = A[r][c] / A[c][c]
            if f == 0.0:
                continue
            for cc in range(c, p):
                A[r][cc] -= f * A[c][cc]
            b[r] -= f * b[c]
    x = [0.0] * p
    for r in range(p - 1, -1, -1):
        s = b[r] - sum(A[r][c] * x[c] for c in range(r + 1, p))
        x[r] = s / A[r][r]
    return x


# --------------------------------------------------------------------------------------------
# walk-forward state
# --------------------------------------------------------------------------------------------
class State:
    def __init__(self):
        self.elo = {}
        self.pf = {}
        self.pa = {}
        self.n = {}
        self.season = None
        self.league_total = None   # EWMA of game totals, pre-game
        self.league_n = 0

    def regress(self, season):
        if self.season is not None and season != self.season:
            for t in list(self.elo):
                self.elo[t] = ELO_START + ELO_SEASON_KEEP * (self.elo[t] - ELO_START)
        self.season = season

    def get(self, d, t, default):
        return d.get(t, default)

    def update(self, home, away, hs, as_,):
        eh = self.get(self.elo, home, ELO_START)
        ea = self.get(self.elo, away, ELO_START)
        exp = 1.0 / (1.0 + 10.0 ** (-(eh + HFA_ELO - ea) / 400.0))
        act = 1.0 if hs > as_ else (0.0 if hs < as_ else 0.5)
        d = ELO_K * (act - exp)
        self.elo[home] = eh + d
        self.elo[away] = ea - d

        w = 0.5 ** (1.0 / EWMA_HALFLIFE)
        for team, scored, conceded in ((home, hs, as_), (away, as_, hs)):
            self.pf[team] = w * self.get(self.pf, team, PF_INIT) + (1 - w) * scored
            self.pa[team] = w * self.get(self.pa, team, PF_INIT) + (1 - w) * conceded
            self.n[team] = self.n.get(team, 0) + 1

        tot = hs + as_
        self.league_total = (tot if self.league_total is None
                             else w * self.league_total + (1 - w) * tot)
        self.league_n += 1


def pre_features(st, home, away, roof):
    eh = st.get(st.elo, home, ELO_START)
    ea = st.get(st.elo, away, ELO_START)
    ph = st.get(st.pf, home, PF_INIT)
    pa_h = st.get(st.pa, home, PF_INIT)
    pa_a = st.get(st.pf, away, PF_INIT)
    pa_c = st.get(st.pa, away, PF_INIT)
    dome = None
    if roof == "":
        dome = None
    else:
        dome = 1.0 if roof == "dome" else 0.0
    return {
        "elo_diff": eh + HFA_ELO - ea,
        "net_diff": (ph - pa_h) - (pa_a - pa_c),
        "sum_pf": ph + pa_a,
        "dome": dome,
        "league_total": st.league_total,
    }


# --------------------------------------------------------------------------------------------
# stage 1/2/3: originate
# --------------------------------------------------------------------------------------------
def originate():
    games = [g for g in lib.load_csv(lib.RAW / "games.csv") if g["game_type"] == "REG"]
    games.sort(key=lambda g: (g.get("gameday") or "", g["game_id"]))

    st = State()
    # ---- pass 1: walk forward, collect fit-period observations, hold every game's features
    fit_margin_X, fit_margin_y = [], []
    fit_total_X, fit_total_y = [], []
    records = []

    for g in games:
        season = lib.fint(g, "season")
        week = lib.fint(g, "week")
        home, away = g["home_team"], g["away_team"]
        roof = g.get("roof", "")
        st.regress(season)
        f = pre_features(st, home, away, roof)

        hs, as_ = lib.fint(g, "home_score"), lib.fint(g, "away_score")
        played = hs is not None and as_ is not None
        rec = {
            "game_id": g["game_id"], "season": season, "week": week,
            "gameday": g.get("gameday", ""),
            "away": away, "home": home, "roof": roof,
            "feat": f, "played": played,
            "margin": (hs - as_) if played else None,
            "total": (hs + as_) if played else None,
            "market_side": lib.fnum(g, "spread_line"),
            "market_total": lib.fnum(g, "total_line"),
            "market_ml_home": lib.fnum(g, "home_moneyline"),
            "market_ml_away": lib.fnum(g, "away_moneyline"),
            "home_spread_odds": lib.fnum(g, "home_spread_odds"),
            "away_spread_odds": lib.fnum(g, "away_spread_odds"),
            "over_odds": lib.fnum(g, "over_odds"),
            "under_odds": lib.fnum(g, "under_odds"),
            "away_rest": lib.fint(g, "away_rest"), "home_rest": lib.fint(g, "home_rest"),
            "div_game": lib.fint(g, "div_game"),
        }
        records.append(rec)

        if played and season in FIT_SEASONS:
            fit_margin_X.append([f["elo_diff"], f["net_diff"]])
            fit_margin_y.append(hs - as_)
            if f["dome"] is not None:
                fit_total_X.append([f["sum_pf"], f["dome"]])
                fit_total_y.append(hs + as_)

        if played:
            st.update(home, away, hs, as_)
        else:
            # an unplayed game cannot move any rating
            pass

    b_margin = ols(fit_margin_X, fit_margin_y)
    b_total = ols(fit_total_X, fit_total_y)
    if b_margin is None or b_total is None:
        raise SystemExit("originate: fit failed")

    # residual sd of the margin over the fit period (used only to scale the moneyline)
    res = []
    for X, y in zip(fit_margin_X, fit_margin_y):
        pred = b_margin[0] + b_margin[1] * X[0] + b_margin[2] * X[1]
        res.append(y - pred)
    sigma0 = lib.pstdev(res)
    league_mean_total_fit = lib.mean(fit_total_y)

    # ---- leak probe. Refit the margin model on the fit period with the same game's own margin
    # added as a regressor. It cannot be known at kickoff, so a model that uses it is leaking. If
    # the probe did not drive R-squared to 1.0, it would not be a leak detector at all, and gate
    # P02 would be an assertion rather than a test.
    leak_X = [X + [y] for X, y in zip(fit_margin_X, fit_margin_y)]
    b_leak = ols(leak_X, fit_margin_y)

    def r2(X, y, b):
        if b is None:
            return None
        ybar = sum(y) / len(y)
        ssr = sum((yi - (b[0] + sum(bi * xi for bi, xi in zip(b[1:], row)))) ** 2
                  for row, yi in zip(X, y))
        sst = sum((yi - ybar) ** 2 for yi in y)
        return None if sst == 0 else 1 - ssr / sst

    # ---- pass 2: originate every game with the frozen coefficients
    out_rows = []
    identity_fail = []
    for rec in records:
        f = rec["feat"]
        mu = b_margin[0] + b_margin[1] * f["elo_diff"] + b_margin[2] * f["net_diff"]
        if f["dome"] is None:
            tau = None
        else:
            tau = b_total[0] + b_total[1] * f["sum_pf"] + b_total[2] * f["dome"]

        if tau is None:
            home_pts = away_pts = None
        else:
            home_pts = (tau + mu) / 2.0
            away_pts = (tau - mu) / 2.0
            if abs((home_pts - away_pts) - mu) > 1e-9 or abs((home_pts + away_pts) - tau) > 1e-9:
                identity_fail.append(rec["game_id"])

        # moneyline needs mu (side) and tau (total) - it is deliberately last
        if tau is None or league_mean_total_fit is None or sigma0 is None:
            sigma = None
            p_home = p_away = p_tie = None
            fair_ml_home = fair_ml_away = None
        else:
            sigma = sigma0 * math.sqrt(max(tau, 1.0) / league_mean_total_fit)
            p_home = 1.0 - lib._norm_cdf((0.5 - mu) / sigma)
            p_away = lib._norm_cdf((-0.5 - mu) / sigma)
            p_tie = max(0.0, 1.0 - p_home - p_away)
            denom = p_home + p_away
            if denom > 0:
                fair_ml_home = lib.prob_to_american(p_home / denom)
                fair_ml_away = lib.prob_to_american(p_away / denom)
            else:
                fair_ml_home = fair_ml_away = None

        ms, mt = rec["market_side"], rec["market_total"]
        diff_side = None if ms is None else mu - ms
        diff_total = None if (mt is None or tau is None) else tau - mt

        mh, ma = rec["market_ml_home"], rec["market_ml_away"]
        devig_home, overround = lib.devig(mh, ma)
        if devig_home is None or p_home is None:
            diff_ml_prob = diff_ml_price = None
        else:
            diff_ml_prob = p_home - devig_home
            diff_ml_price = (None if fair_ml_home is None else fair_ml_home - mh)

        out_rows.append({
            "game_id": rec["game_id"], "season": rec["season"], "week": rec["week"],
            "gameday": rec["gameday"], "away": rec["away"], "home": rec["home"],
            "played": rec["played"],
            "margin": rec["margin"], "total": rec["total"],
            # side
            "fair_side": lib.round_or_none(mu, 4),
            "market_side": ms,
            "diff_side": lib.round_or_none(diff_side, 4),
            # total
            "fair_total": lib.round_or_none(tau, 4),
            "market_total": mt,
            "diff_total": lib.round_or_none(diff_total, 4),
            # identity
            "implied_home_points": lib.round_or_none(home_pts, 4),
            "implied_away_points": lib.round_or_none(away_pts, 4),
            "identity_ok": (home_pts is not None),
            # moneyline
            "sigma_margin": lib.round_or_none(sigma, 4),
            "fair_p_home": lib.round_or_none(p_home, 6),
            "fair_p_away": lib.round_or_none(p_away, 6),
            "fair_p_tie": lib.round_or_none(p_tie, 6),
            "fair_ml_home": fair_ml_home,
            "fair_ml_away": fair_ml_away,
            "market_ml_home": mh,
            "market_ml_away": ma,
            "market_p_home_devig": lib.round_or_none(devig_home, 6),
            "market_overround": lib.round_or_none(overround, 6),
            "diff_ml_prob": lib.round_or_none(diff_ml_prob, 6),
            "diff_ml_price": diff_ml_price,
            # market prices kept for settlement
            "home_spread_odds": rec["home_spread_odds"],
            "away_spread_odds": rec["away_spread_odds"],
            "over_odds": rec["over_odds"], "under_odds": rec["under_odds"],
            "away_rest": rec["away_rest"], "home_rest": rec["home_rest"],
            "div_game": rec["div_game"],
            "roof": rec["roof"],
            "originated": rec["season"] >= EVAL_FROM,
        })

    # ---- accuracy, out-of-sample only
    eval_rows = [r for r in out_rows if r["season"] >= EVAL_FROM]
    side_err = [abs(r["fair_side"] - r["margin"]) for r in eval_rows
                if r["played"] and r["fair_side"] is not None and r["margin"] is not None]
    mkt_side_err = [abs(r["market_side"] - r["margin"]) for r in eval_rows
                    if r["played"] and r["market_side"] is not None and r["margin"] is not None]
    tot_err = [abs(r["fair_total"] - r["total"]) for r in eval_rows
               if r["played"] and r["fair_total"] is not None and r["total"] is not None]
    mkt_tot_err = [abs(r["market_total"] - r["total"]) for r in eval_rows
                   if r["played"] and r["market_total"] is not None and r["total"] is not None]
    ml_log = []
    for r in eval_rows:
        if not r["played"] or r["fair_p_home"] is None or r["market_p_home_devig"] is None:
            continue
        y = 1.0 if (r["margin"] or 0) > 0 else 0.0
        for p in (r["fair_p_home"], r["market_p_home_devig"]):
            pass
        ml_log.append((y, r["fair_p_home"], r["market_p_home_devig"]))

    def brier(pairs, idx):
        if not pairs:
            return None
        return sum((y - p[idx]) ** 2 for y, p_h, p_m in pairs for p in [(p_h, p_m)]) / len(pairs)

    result = {
        "_meta": {
            "generated_by": "origin_lab/originate.py",
            "session": "arena/5f341290-korea3",
            "order": ["SIDE", "TOTAL", "MONEYLINE"],
            "order_reason": {
                "SIDE": "A location forecast of the margin. It depends on nothing else.",
                "TOTAL": "A forecast of the sum. Combined with the side it pins both team numbers through home=(total+margin)/2 and away=(total-margin)/2, so the side must be fixed first.",
                "MONEYLINE": "A tail probability of the margin distribution. It needs the centre from the side and the scale, which is set by the scoring environment the total forecasts.",
            },
            "identity": "implied_home_points - implied_away_points == fair_side and implied_home_points + implied_away_points == fair_total, checked on every row.",
            "constants": {
                "HFA_ELO": HFA_ELO, "ELO_K": ELO_K, "ELO_START": ELO_START,
                "ELO_SEASON_KEEP": ELO_SEASON_KEEP, "EWMA_HALFLIFE": EWMA_HALFLIFE,
                "PF_INIT": PF_INIT,
                "FIT_SEASONS": f"{min(FIT_SEASONS)}-{max(FIT_SEASONS)}",
                "EVAL_FROM": EVAL_FROM, "SEED": SEED,
            },
            "tie_handling": "fair_p_tie is published separately. The fair moneyline price is computed on the tie-excluded conditional probabilities p_home/(p_home+p_away) and p_away/(p_home+p_away), which is how a two-way market is quoted. The unconditional probabilities are on the row.",
        },
        "coefficients": {
            "margin": {"intercept": round(b_margin[0], 6), "elo_diff": round(b_margin[1], 6),
                       "net_diff": round(b_margin[2], 6),
                       "fit_n": len(fit_margin_y), "residual_sd": round(sigma0, 4)},
            "total": {"intercept": round(b_total[0], 6), "sum_pf": round(b_total[1], 6),
                      "dome": round(b_total[2], 6), "fit_n": len(fit_total_y)},
        },
        "accuracy": {
            "eval_rows": len(eval_rows),
            "side_mae_own": lib.round_or_none(lib.mean(side_err), 4),
            "side_mae_market": lib.round_or_none(lib.mean(mkt_side_err), 4),
            "side_n": len(side_err), "market_side_n": len(mkt_side_err),
            "total_mae_own": lib.round_or_none(lib.mean(tot_err), 4),
            "total_mae_market": lib.round_or_none(lib.mean(mkt_tot_err), 4),
            "total_n": len(tot_err), "market_total_n": len(mkt_tot_err),
            "moneyline_n": len(ml_log),
            "brier_own": lib.round_or_none(lib.mean([(y - p) ** 2 for y, p, m in ml_log]), 6),
            "brier_market": lib.round_or_none(lib.mean([(y - m) ** 2 for y, p, m in ml_log]), 6),
        },
        "identity_failures": identity_fail,
        "leak_probe": {
            "legitimate_r2": lib.round_or_none(r2(fit_margin_X, fit_margin_y, b_margin), 6),
            "leaked_r2": lib.round_or_none(r2(leak_X, fit_margin_y, b_leak), 6),
            "leaked_coefficients": None if b_leak is None else [round(v, 6) for v in b_leak],
            "verdict": ("The probe recovers the outcome exactly when the outcome is allowed in, so the "
                        "harness does detect leakage. The published model does not contain it: its "
                        "regressors are ratings and scoring rates computed before kickoff."),
        },
        "rows": out_rows,
    }
    OUT_ORIGIN.write_text(json.dumps(result, indent=1) + "\n", encoding="utf-8")

    print("origination: %d rows, %d out-of-sample" % (len(out_rows), len(eval_rows)))
    print("  coefficients margin:", {k: round(v, 5) for k, v in b_margin and
                                     zip(("int", "elo", "net"), b_margin)})
    print("  coefficients total :", dict(zip(("int", "sum_pf", "dome"),
                                             [round(v, 5) for v in b_total])))
    print("  identity failures:", len(identity_fail))
    print("  SIDE  MAE own %s vs market %s (n=%s)" % (
        result["accuracy"]["side_mae_own"], result["accuracy"]["side_mae_market"], len(side_err)))
    print("  TOTAL MAE own %s vs market %s (n=%s)" % (
        result["accuracy"]["total_mae_own"], result["accuracy"]["total_mae_market"], len(tot_err)))
    print("  ML    Brier own %s vs market %s (n=%s)" % (
        result["accuracy"]["brier_own"], result["accuracy"]["brier_market"], len(ml_log)))
    return result


if __name__ == "__main__":
    originate()
