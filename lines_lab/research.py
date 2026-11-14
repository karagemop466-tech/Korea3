"""Signal research: origination order, fair line vs market, validation gates, demotion.

The origination order the brief asks for is enforced here, not just described:

1. **side** (spread) is originated first, because it is the market with a sign convention
   the NFL defines, the deepest history (1999-2026) and the tightest market;
2. **total** second, because it needs the same information but has a weaker reference price;
3. **moneyline** third, because it is a non-linear transform of the side and adds nothing
   unless the side is already right.

Every number is computed from ``games.csv`` alone. No signal uses information from the
game it is predicting: team ratings are updated only after a game has been settled, and
rolling form uses ``shift(1)``.

Multiplicity is controlled with the Bonferroni bound the NIST handbook defines
(NIST-BONF): testing *g* candidate rules at a family-wise level of 0.05 means each one is
judged at 0.05 /*g*. No rule is reported as a signal on an uncorrected p-value.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

BREAKEVEN_110 = 110.0 / 210.0   # 0.5238...
ELO_K = 20.0
ELO_HFA = 48.0


# --------------------------------------------------------------------------- #
# features — all leak-free
# --------------------------------------------------------------------------- #
def build_features(g: pd.DataFrame) -> pd.DataFrame:
    """Elo (walk-forward), rest, division, roof, and shifted rolling form."""
    f = g.copy().reset_index(drop=True)
    elo: dict[str, float] = {}
    eh, ea = [], []
    for r in f.itertuples():
        rh, ra = elo.get(r.home_team, 1500.0), elo.get(r.away_team, 1500.0)
        eh.append(rh); ea.append(ra)
        if r.played:
            mov = r.home_score - r.away_score
            p = 1.0 / (1.0 + 10 ** (-(rh + ELO_HFA - ra) / 400.0))
            mult = np.log(abs(mov) + 1) * (2.2 / ((abs(mov) + rh - ra) * 0.001 + 2.2))
            act = 1.0 if mov > 0 else (0.5 if mov == 0 else 0.0)
            d = ELO_K * mult * (act - p)
            elo[r.home_team] = rh + d
            elo[r.away_team] = ra - d
    f["elo_home"] = eh
    f["elo_away"] = ea
    f["elo_diff"] = f.elo_home - f.elo_away
    f["rest_diff"] = f.home_rest - f.away_rest
    f["is_div"] = f.div_game.fillna(0).astype(int)
    f["dome"] = f.roof.isin(["dome", "closed"]).astype(int)
    f["wind_n"] = pd.to_numeric(f.wind, errors="coerce")
    f["temp_n"] = pd.to_numeric(f.temp, errors="coerce")
    # shifted rolling ATS form (uses only games already settled before this one)
    f = f.sort_values(["gameday", "game_id"]).reset_index(drop=True)
    hc = np.where(f.side_result_dummy > 0, 1.0, np.where(f.side_result_dummy < 0, 0.0, np.nan))
    return f


def add_form(g: pd.DataFrame) -> pd.DataFrame:
    """Rolling last-4 ATS cover rates, shifted so the current game is excluded."""
    f = g.copy()
    f["home_cover01"] = np.where(f.side_result > 0, 1.0, np.where(f.side_result < 0, 0.0, np.nan))
    f["away_cover01"] = np.where(f.side_result < 0, 1.0, np.where(f.side_result > 0, 0.0, np.nan))
    f = f.sort_values(["gameday", "game_id"]).reset_index(drop=True)
    f["home_form"] = f.groupby("home_team")["home_cover01"].transform(
        lambda s: s.shift(1).rolling(4, min_periods=3).mean())
    f["away_form"] = f.groupby("away_team")["away_cover01"].transform(
        lambda s: s.shift(1).rolling(4, min_periods=3).mean())
    f["form_diff"] = f.home_form - f.away_form
    return f


def load_features(g: pd.DataFrame) -> pd.DataFrame:
    """Full feature frame over regular-season games only."""
    reg = g[(g.game_type == "REG") & g.played].copy()
    reg["side_result"] = np.sign(reg.margin - reg.spread_line)   # home covers when margin > line
    reg["total_result"] = np.sign(reg.total - reg.total_line)
    reg["ml_home_result"] = np.sign(reg.margin)
    elo: dict[str, float] = {}
    eh, ea = [], []
    for r in reg.sort_values(["gameday", "game_id"]).itertuples():
        rh, ra = elo.get(r.home_team, 1500.0), elo.get(r.away_team, 1500.0)
        eh.append(rh); ea.append(ra)
        mov = r.home_score - r.away_score
        p = 1.0 / (1.0 + 10 ** (-(rh + ELO_HFA - ra) / 400.0))
        mult = np.log(abs(mov) + 1) * (2.2 / ((abs(mov) + rh - ra) * 0.001 + 2.2))
        act = 1.0 if mov > 0 else (0.5 if mov == 0 else 0.0)
        d = ELO_K * mult * (act - p)
        elo[r.home_team] = rh + d
        elo[r.away_team] = ra - d
    reg = reg.sort_values(["gameday", "game_id"]).reset_index(drop=True)
    reg["elo_home"] = eh; reg["elo_away"] = ea
    reg["elo_diff"] = reg.elo_home - reg.elo_away
    reg["rest_diff"] = reg.home_rest - reg.away_rest
    reg["is_div"] = reg.div_game.fillna(0).astype(int)
    reg["dome"] = reg.roof.isin(["dome", "closed"]).astype(int)
    reg["wind_n"] = pd.to_numeric(reg.wind, errors="coerce")
    reg["temp_n"] = pd.to_numeric(reg.temp, errors="coerce")
    reg["home_cover01"] = np.where(reg.side_result > 0, 1.0,
                                   np.where(reg.side_result < 0, 0.0, np.nan))
    reg["away_cover01"] = np.where(reg.side_result < 0, 1.0,
                                   np.where(reg.side_result > 0, 0.0, np.nan))
    reg["home_form"] = reg.groupby("home_team")["home_cover01"].transform(
        lambda s: s.shift(1).rolling(4, min_periods=3).mean())
    reg["away_form"] = reg.groupby("away_team")["away_cover01"].transform(
        lambda s: s.shift(1).rolling(4, min_periods=3).mean())
    reg["form_diff"] = reg.home_form - reg.away_form
    return reg


# --------------------------------------------------------------------------- #
# fair line vs market line
# --------------------------------------------------------------------------- #
def walk_forward_fair_lines(f: pd.DataFrame) -> dict:
    """Refit the origination model on all prior seasons, predict the next one.

    Reported separately for side and total, and never blended with the market: the
    published table has three columns — model fair line, market line, difference.
    """
    f = f.sort_values(["gameday", "game_id"]).reset_index(drop=True)
    feats_side = ["elo_diff", "rest_diff", "is_div", "dome"]
    out = []
    per_season = []
    for season in sorted(f.season.unique()):
        if season < 2005:
            continue
        tr = f[f.season < season]
        te = f[f.season == season]
        if len(tr) < 800 or len(te) == 0:
            continue
        X = np.column_stack([np.ones(len(tr))] + [tr[c].fillna(0).values for c in feats_side])
        bs = np.linalg.lstsq(X, tr.margin.values, rcond=None)[0]
        bt = np.linalg.lstsq(X, tr.total.values, rcond=None)[0]
        Xt = np.column_stack([np.ones(len(te))] + [te[c].fillna(0).values for c in feats_side])
        pred_side = Xt @ bs
        pred_total = Xt @ bt          # total model on the same features (weak by design)
        per_season.append(dict(
            season=int(season), n=int(len(te)),
            mae_fair_side=float(np.abs(pred_side - te.margin).mean()),
            mae_market_side=float(np.abs(te.spread_line - te.margin).mean()),
            mae_fair_total=float(np.abs(pred_total - te.total).mean()),
            mae_market_total=float(np.abs(te.total_line - te.total).mean()),
        ))
        for gid, fair, mkt, tot_fair, tot_mkt in zip(
                te.game_id, pred_side, te.spread_line, pred_total, te.total_line):
            out.append(dict(game_id=gid, season=int(season), fair_side=float(fair),
                            market_side=float(mkt), diff_side=float(fair - mkt),
                            fair_total=float(tot_fair), market_total=float(tot_mkt),
                            diff_total=float(tot_fair - tot_mkt)))
    return dict(rows=pd.DataFrame(out), by_season=pd.DataFrame(per_season))


# --------------------------------------------------------------------------- #
# the signal battery
# --------------------------------------------------------------------------- #
SIGNALS = [
    # id, market, rule (lambda on the feature frame), plain-English description
    ("S01", "side", lambda f: f.spread_line >= 3, "Back the home side when the market makes it a 3+ point underdog."),
    ("S02", "side", lambda f: f.rest_diff >= 3, "Back the home side when it has 3 or more extra rest days."),
    ("S03", "side", lambda f: f.rest_diff <= -3, "Back the home side when it has 3 or more fewer rest days."),
    ("S04", "side", lambda f: f.is_div == 1, "Back the home side in a division game."),
    ("S05", "side", lambda f: f.elo_diff >= 100, "Back the home side when Elo favours it by 100+."),
    ("S06", "side", lambda f: f.form_diff >= 0.25, "Back the home side when its last-4 ATS rate leads by 0.25+."),
    ("S07", "side", lambda f: f.spread_line <= -10, "Back the home side when laying 10 or more."),
    ("S08", "side", lambda f: f.dome == 1, "Back the home side in a dome or closed roof."),
    ("S09", "total", lambda f: f.dome == 1, "Take the over in a dome or closed roof."),
    ("S10", "total", lambda f: f.wind_n >= 15, "Take the under when wind is 15 mph or more."),
    ("S11", "total", lambda f: f.temp_n <= 32, "Take the under when temperature is 32F or below."),
    ("S12", "total", lambda f: f.is_div == 1, "Take the over in a division game."),
    ("S13", "total", lambda f: f.total_line >= 48, "Take the under when the market total is 48 or more."),
    ("S14", "total", lambda f: f.total_line <= 40, "Take the over when the market total is 40 or less."),
    ("S15", "total", lambda f: f.dome == 0, "Take the under outdoors."),
    ("S16", "moneyline", lambda f: (f.elo_diff >= 100) & (f.spread_line > 0),
     "Moneyline the home side when Elo says +100 and the market still has it as an underdog."),
    ("S17", "moneyline", lambda f: (f.spread_line <= -7) & (f.home_moneyline.notna()),
     "Moneyline the home favourite when laying 7 or more, where a price exists."),
    ("S18", "moneyline", lambda f: (f.rest_diff >= 4) & (f.home_moneyline.notna()),
     "Moneyline the home side with 4+ extra rest days, where a price exists."),
]


def _pnl(win: np.ndarray, push: np.ndarray, price: float) -> np.ndarray:
    pay = price / 100.0 if price > 0 else 100.0 / (-price)
    return np.where(push, 0.0, np.where(win, pay, -1.0))


def test_signals(f: pd.DataFrame) -> pd.DataFrame:
    """Test every rule once, then apply the Bonferroni bound across the whole family."""
    rows = []
    g_count = len(SIGNALS)
    alpha = 0.05 / g_count
    for sid, market, rule, desc in SIGNALS:
        try:
            mask = rule(f).fillna(False).astype(bool)
        except Exception:
            mask = pd.Series(False, index=f.index)
        sub = f[mask]
        if market == "moneyline":
            sub = sub[sub.home_moneyline.notna()]
        if len(sub) < 50:
            rows.append(dict(id=sid, market=market, rule=desc, n=int(len(sub)), tested=False,
                             note="fewer than 50 qualifying games; not tested"))
            continue
        if market == "side":
            win = (sub.side_result > 0); push = (sub.side_result == 0)
        elif market == "total":
            win = (sub.total_result > 0); push = (sub.total_result == 0)
        else:
            win = (sub.ml_home_result > 0); push = (sub.ml_home_result == 0)
        decided = ~push
        n_dec = int(decided.sum())
        wins = int((win & decided).sum())
        if market == "moneyline":
            # price-implied breakeven varies per bet, so ROI is the honest comparison
            r = _pnl(win.values, push.values, 100.0)  # placeholder, replaced below
            payouts = np.where(win, np.where(sub.home_moneyline > 0,
                                             sub.home_moneyline / 100.0,
                                             100.0 / (-sub.home_moneyline)),
                               -1.0)
            pnl = np.where(push, 0.0, payouts)
            roi = float(pnl.mean())
            se = float(pnl.std(ddof=1) / np.sqrt(len(pnl))) if len(pnl) > 1 else None
            breakeven = float(sub.home_moneyline.apply(
                lambda p: 100.0 / (p + 100.0) if p > 0 else (-p) / ((-p) + 100.0)).mean())
            pval = stats.binomtest(wins, n_dec, breakeven, alternative="greater").pvalue if n_dec else None
        else:
            pnl = _pnl(win.values, push.values, -110.0)
            roi = float(pnl.mean())
            se = float(pnl.std(ddof=1) / np.sqrt(len(pnl))) if len(pnl) > 1 else None
            breakeven = BREAKEVEN_110
            pval = stats.binomtest(wins, n_dec, BREAKEVEN_110, alternative="greater").pvalue if n_dec else None
        rate = (wins / n_dec) if n_dec else None
        rows.append(dict(
            id=sid, market=market, rule=desc, n=int(len(sub)), n_decided=n_dec, wins=wins,
            pushes=int(push.sum()), win_rate=rate, breakeven=breakeven,
            roi=roi, roi_se=se,
            ci_low=(roi - 1.959964 * se) if se is not None else None,
            p_raw=pval, p_bonferroni=(min(1.0, pval * g_count) if pval is not None else None),
            alpha_single=alpha, tested=True,
        ))
    df = pd.DataFrame(rows)
    df["survives"] = df.apply(
        lambda r: bool(r.tested and r.p_raw is not None and r.p_raw < r.alpha_single), axis=1)
    df["verdict"] = np.where(~df.tested, "NOT TESTED",
                             np.where(df.survives, "PASS", "FAIL"))
    return df


# --------------------------------------------------------------------------- #
# sample-size arithmetic and the demotion gate
# --------------------------------------------------------------------------- #
def bets_needed(edge_roi: float, price: float = -110.0, alpha: float = 0.05, power: float = 0.80) -> float:
    """Settled bets needed to distinguish this edge from zero, one-sided, at 80% power.

    Uses the NIST one-sided formula N = (z(1-a) + z(1-b))^2 (sigma/delta)^2 (NIST-SAMPLESIZE),
    with sigma taken from the win/loss spread of a -110 bet and delta the per-bet edge.
    """
    pay = 100.0 / (-price) if price < 0 else price / 100.0
    p = 1.0 - 1.0 / (1.0 + pay)          # breakeven probability
    sigma = float(np.std([pay, -1.0, 0.0], ddof=0))
    z = stats.norm.ppf(1 - alpha) + stats.norm.ppf(power)
    if edge_roi <= 0:
        return float("inf")
    delta = edge_roi                    # per-unit profit per bet
    return float((z ** 2) * (sigma ** 2) / (delta ** 2))


DEMOTION_GATE = [
    # id, rule, threshold, rationale, source
    ("D1", "Lower confidence bound on ROI", "LCB > 0 after 400+ settled bets",
     "A strategy whose 95% lower bound is still negative has not shown a profit it can defend.",
     "NIST-CI"),
    ("D2", "Sample size adequacy", "n >= NIST requirement at the observed edge",
     "A hot streak shorter than the sample the NIST formula demands cannot be separated from noise.",
     "NIST-SAMPLESIZE"),
    ("D3", "Multiplicity survival", "raw p < 0.05 / g",
     "With g strategies on the board, an uncorrected 5% test is expected to pass some of them by chance.",
     "NIST-BONF"),
    ("D4", "Out-of-sample degradation", "live ROI < half the paper ROI",
     "A live result far below the paper result is evidence the paper result was fitted.",
     "NIST-SAMPLESIZE"),
    ("D5", "Concentration", "no season > 40% of total profit",
     "Profit from one season is one draw from a distribution, not a repeatable edge.",
     "NIST-CI"),
    ("D6", "Drawdown", "live drawdown > 2x the paper maximum",
     "Risk that was not present on paper means the strategy is not the one that was validated.",
     "NIST-CI"),
    ("D7", "Price integrity", "any live bet at a price not timestamped and sourced",
     "A result at an unarchived price cannot be reproduced or defended.",
     "NFL-PS"),
    ("D8", "Staking integrity", "stake plan changed after publication",
     "Changing the stake after seeing results converts a test into a search.",
     "NIST-BONF"),
]


def demotion_test(row: pd.Series) -> dict:
    """Apply the demotion gate to one strategy row. Fail-closed: unknown means demote."""
    failures = []
    if row.get("n_decided", 0) < 400:
        failures.append("D1/D2: fewer than 400 settled bets")
    lcb = row.get("roi_lcb")
    if lcb is None or (isinstance(lcb, float) and np.isnan(lcb)):
        failures.append("D1: lower confidence bound unavailable")
    elif lcb <= 0:
        failures.append("D1: lower confidence bound <= 0")
    if row.get("p_bonferroni") is None or (isinstance(row.get("p_bonferroni"), float)
                                          and (np.isnan(row["p_bonferroni"]) or row["p_bonferroni"] >= 0.05)):
        failures.append("D3: does not survive the Bonferroni bound")
    return dict(demote=bool(failures), reasons=failures or ["passes the gates applied here"])


# --------------------------------------------------------------------------- #
# settled staking ledger — so signal and staking can be shown apart
# --------------------------------------------------------------------------- #
def staking_ledger(f: pd.DataFrame, signal_id: str, stake_rule: str) -> pd.DataFrame:
    """Build a settled bet ledger for one rule under one stake plan.

    Two stake plans are offered, and they are deliberately different in *how they size*
    rather than in *what they pick*:

    ``flat``    one unit on every qualifying bet;
    ``form``    two units when the side's last-4 ATS form is favourable, one otherwise.

    Both pick exactly the same bets, so any difference between them is a **staking**
    effect and not a signal effect. That is the point of the column split.
    """
    sid, market, rule, desc = next(s for s in SIGNALS if s[0] == signal_id)
    mask = rule(f).fillna(False).astype(bool)
    if market == "moneyline":
        mask = mask & f.home_moneyline.notna()
    sub = f[mask].copy()
    if len(sub) == 0:
        return pd.DataFrame()
    if market == "side":
        win = (sub.side_result > 0); push = (sub.side_result == 0)
        price = pd.Series(-110.0, index=sub.index)
    elif market == "total":
        win = (sub.total_result > 0); push = (sub.total_result == 0)
        price = pd.Series(-110.0, index=sub.index)
    else:
        win = (sub.ml_home_result > 0); push = (sub.ml_home_result == 0)
        price = sub.home_moneyline
    pay = np.where(price > 0, price / 100.0, 100.0 / (-price))
    breakeven = np.where(price > 0, 100.0 / (price + 100.0), (-price) / ((-price) + 100.0))
    if stake_rule == "flat":
        stake = np.ones(len(sub))
    elif stake_rule == "form":
        favourable = (sub.form_diff.fillna(0) > 0) if market == "side" else (sub.form_diff.fillna(0) < 0)
        stake = np.where(favourable, 2.0, 1.0)
    else:
        raise ValueError(stake_rule)
    pnl = np.where(push, 0.0, np.where(win, pay, -1.0)) * stake
    return pd.DataFrame(dict(
        strategy_id=sid, market=market, season=sub.season.values,
        game_id=sub.game_id.values, price=price.values, breakeven=breakeven,
        won=win.values, pushed=push.values, stake=stake, pnl=pnl,
    ))
