"""Bet generation + settlement.

Every strategy is a mechanical rule over pre-game information only.  A bet is
only placed when the market price actually exists in the source data -- we
never invent a price for spread / total / moneyline markets.

Stake model: flat 1.00 unit per bet (headline).  Fractional Kelly is recorded
alongside for information but is not the headline metric.
"""
import math

import numpy as np
import pandas as pd

from common import (american_to_decimal, american_to_prob, devig_two_way,
                    prob_from_spread)

UNITS = 1.0


# --------------------------------------------------------------------------
# market plumbing
# --------------------------------------------------------------------------
def _pair(row, market):
    """Return (odds_side_a, odds_side_b, devig_p_a, devig_p_b, hold) or None."""
    if market == "SPREAD":
        oa, ob = row.home_spread_odds, row.away_spread_odds
    elif market == "TOTAL":
        oa, ob = row.over_odds, row.under_odds
    elif market == "ML":
        oa, ob = row.home_moneyline, row.away_moneyline
    else:
        return None
    if any(pd.isna(v) or v == 0 for v in (oa, ob)):
        return None
    pa, pb = american_to_prob(oa), american_to_prob(ob)
    da, db, hold = devig_two_way(pa, pb)
    return dict(odds_a=float(oa), odds_b=float(ob), p_a=float(da), p_b=float(db), hold=float(hold))


def model_probs(row, market):
    """Model probability for side A and side B of a two-way market."""
    if market == "SPREAD":
        line = row.spread_line
        if pd.isna(line):
            return None
        ph, push = prob_from_spread(row.mu_margin, row.sigma_margin, line)
        pa, push_a = prob_from_spread(-row.mu_margin, row.sigma_margin, -line)
        return dict(p_a=ph, p_b=pa, push=push)
    if market == "TOTAL":
        line = row.total_line
        if pd.isna(line):
            return None
        po, push = prob_from_spread(row.mu_total, row.sigma_total, line)
        pu, _ = prob_from_spread(-row.mu_total, row.sigma_total, -line)
        return dict(p_a=po, p_b=pu, push=push)
    if market == "ML":
        ph = float(np.clip(0.5 * (1 + math.erf((row.mu_margin / row.sigma_margin) / math.sqrt(2))), 1e-6, 1 - 1e-6))
        # ties reduce to a void in the NFL only in the regular season; treat as
        # half-win for pricing conservatism
        ph = ph + (1 - ph) * 0.0
        return dict(p_a=ph, p_b=1 - ph, push=0.0)
    return None


def ev_of(dec, p_win, p_push=0.0):
    """Expected profit per unit staked."""
    p_lose = max(0.0, 1 - p_win - p_push)
    return p_win * (dec - 1) - p_lose


def kelly_fraction(dec, p_win, cap=0.05, frac=0.25):
    b = dec - 1
    if b <= 0:
        return 0.0
    f = (p_win * dec - 1) / b
    return float(np.clip(f * frac, 0.0, cap))


def make_single(row, strategy, market, side, dec, p_win, p_market, ev, p_push=0.0, note=""):
    return dict(
        strategy_id=strategy, bet_type="single", market=market, side=side,
        season=int(row.season), week=int(row.week), game_id=row.game_id,
        game_ids=row.game_id, n_legs=1, line=float(row.spread_line if market == "SPREAD"
                                                else row.total_line if market == "TOTAL" else np.nan)
        if market != "ML" else np.nan,
        odds_dec=float(dec), p_model=float(p_win), p_market=float(p_market),
        p_push=float(p_push), ev=float(ev), stake=UNITS,
        kelly=kelly_fraction(dec, p_win), note=note, price_source="observed",
        home_team=row.home_team, away_team=row.away_team, gameday=row.gameday,
    )


# --------------------------------------------------------------------------
# strategy rule book
# --------------------------------------------------------------------------
def _edge_side(row, market, prefer=None):
    """Pick the side with the larger positive model edge; return (side, dec, p_model,
    p_market, ev, push, edge_points)."""
    mk = _pair(row, market)
    mp = model_probs(row, market)
    if mk is None or mp is None:
        return None
    if market == "SPREAD":
        pts_a = row.mu_margin - row.spread_line      # home edge in points
        pts_b = -pts_a
    elif market == "TOTAL":
        pts_a = row.mu_total - row.total_line
        pts_b = -pts_a
    else:
        pts_a = mp["p_a"] - mk["p_a"]
        pts_b = mp["p_b"] - mk["p_b"]

    cand = []
    for side, dec, p, pm, pts in (
        ("A", american_to_decimal(mk["odds_a"]), mp["p_a"], mk["p_a"], pts_a),
        ("B", american_to_decimal(mk["odds_b"]), mp["p_b"], mk["p_b"], pts_b),
    ):
        push = mp.get("push", 0.0)
        ev = ev_of(dec, p, push)
        cand.append(dict(side=side, dec=dec, p=p, pm=pm, ev=ev, pts=pts, push=push))
    if prefer == "A" or prefer == "B":
        return next(c for c in cand if c["side"] == prefer)
    return max(cand, key=lambda c: c["ev"])


SIDE_LABEL = {
    ("SPREAD", "A"): "home", ("SPREAD", "B"): "away",
    ("TOTAL", "A"): "over", ("TOTAL", "B"): "under",
    ("ML", "A"): "home ML", ("ML", "B"): "away ML",
}


def build_singles(pred):
    """Generate every single-bet strategy."""
    bets = []
    for _, row in pred.iterrows():
        if pd.isna(row.result):
            continue
        abs_edge = abs(row.edge_spread) if not pd.isna(row.edge_spread) else 0.0
        abs_edge_t = abs(row.edge_total) if not pd.isna(row.edge_total) else 0.0

        def add(sid, market, min_edge, ev_min=0.02, extra=None, prefer=None):
            if extra is not None and not extra(row):
                return
            e = _edge_side(row, market, prefer=prefer)
            if e is None:
                return
            if e["pts"] < min_edge or e["ev"] < ev_min:
                return
            bets.append(make_single(row, sid, market, SIDE_LABEL[(market, e["side"])],
                                    e["dec"], e["p"], e["pm"], e["ev"], e["push"]))

        # --- core model-edge singles -------------------------------------
        add("S01", "SPREAD", 2.0)
        add("S02", "TOTAL", 2.5)
        add("S03", "SPREAD", 1.0)
        add("S04", "SPREAD", 4.0)
        add("S05", "TOTAL", 4.0)

        # --- situational filters -----------------------------------------
        add("S06", "SPREAD", 1.0, extra=lambda x: abs(x.rest_diff) >= 4)
        add("S07", "SPREAD", 2.0, extra=lambda x: x.div_game == 1 and x.spread_line <= 0)
        add("S08", "SPREAD", 1.5, extra=lambda x: x.spread_line >= 9)
        add("S09", "TOTAL", 2.0, extra=lambda x: x.dome == 1)
        add("S10", "TOTAL", 2.0, extra=lambda x: x.dome == 0)

        # --- moneyline ----------------------------------------------------
        add("S11", "ML", 0.03, ev_min=0.02)
        add("S12", "ML", 0.08, ev_min=0.05)

        # --- controls (no model) ------------------------------------------
        mk = _pair(row, "SPREAD")
        if mk is not None:
            dec = american_to_decimal(mk["odds_a"])
            bets.append(make_single(row, "C01", "SPREAD", "home", dec, mk["p_a"], mk["p_a"], 0.0,
                                    note="control: always home ATS"))
            fav_home = (not pd.isna(row.spread_line)) and row.spread_line < 0
            dec_f = dec if fav_home else american_to_decimal(mk["odds_b"])
            pf = mk["p_a"] if fav_home else mk["p_b"]
            bets.append(make_single(row, "C02", "SPREAD", "home" if fav_home else "away", dec_f,
                                    pf, pf, 0.0, note="control: always favourite ATS"))
        mk_t = _pair(row, "TOTAL")
        if mk_t is not None:
            bets.append(make_single(row, "C03", "TOTAL", "over",
                                    american_to_decimal(mk_t["odds_a"]),
                                    mk_t["p_a"], mk_t["p_a"], 0.0, note="control: always over"))
        rng = np.random.default_rng(abs(hash(row.game_id)) % (2 ** 32))
        if mk is not None:
            side = "A" if rng.random() < 0.5 else "B"
            bets.append(make_single(row, "C04", "SPREAD", SIDE_LABEL[("SPREAD", side)],
                                    american_to_decimal(mk[f"odds_{side.lower()}"]),
                                    mk[f"p_{side.lower()}"], mk[f"p_{side.lower()}"], 0.0,
                                    note="control: coin-flip side ATS"))
    return pd.DataFrame(bets)


# --------------------------------------------------------------------------
# parlays
# --------------------------------------------------------------------------
def build_parlays(singles):
    """Cross-game parlays built from the strongest edges each week.

    Legs come from different games, and cross-game independence is tested in
    correlations.py before this pricing assumption is used.
    """
    out = []
    base = singles[(singles.strategy_id.isin(["S01", "S02"])) & (singles.ev > 0)].copy()
    base["abspts"] = base.ev
    for (season, week), grp in base.groupby(["season", "week"]):
        g = grp.drop_duplicates("game_id").sort_values("ev", ascending=False)
        for k, sid in ((2, "P01"), (3, "P02")):
            if len(g) < k:
                continue
            legs = g.head(k)
            dec = float(np.prod(legs.odds_dec.values))
            p = float(np.prod(legs.p_model.values))
            pm = float(np.prod(legs.p_market.values))
            out.append(dict(
                strategy_id=sid, bet_type="parlay", market="MIXED", side=f"{k}-leg parlay",
                season=int(season), week=int(week), game_id="+".join(legs.game_id),
                game_ids="|".join(legs.game_id), n_legs=k, line=np.nan,
                odds_dec=dec, p_model=p, p_market=pm, p_push=0.0,
                ev=ev_of(dec, p), stake=UNITS, kelly=kelly_fraction(dec, p), price_source="observed",
                note=f"legs: " + "; ".join(f"{a} {b} {c} {d}" for a, b, c, d in
                                          zip(legs.market, legs.side, legs.line, legs.home_team)),
                home_team="", away_team="", gameday="",
                _legs=list(legs.to_dict("records")),
            ))
    return out


def build_sgp(predrows, strategy_id, min_edge=1.5, side_mode="opposing"):
    """Same-game parlay: spread + total from the same game.

    Pricing assumption (documented, flagged as ASSUMED): the simulated book
    price is the product of the two leg prices (i.e. the book ignores the
    correlation).  Our settlement probability uses the empirically estimated
    margin/total correlation, so the edge measured here is the correlation
    edge only.
    """
    out = []
    for _, row in predrows.iterrows():
        if pd.isna(row.result) or pd.isna(row.edge_spread) or pd.isna(row.edge_total):
            continue
        if abs(row.edge_spread) < min_edge or abs(row.edge_total) < min_edge:
            continue
        e_s = _edge_side(row, "SPREAD")
        e_t = _edge_side(row, "TOTAL")
        if e_s is None or e_t is None or e_s["ev"] <= 0 or e_t["ev"] <= 0:
            continue
        out.append(dict(strategy_id=strategy_id, game_id=row.game_id, season=int(row.season),
                        week=int(row.week), spread_side=SIDE_LABEL[("SPREAD", e_s["side"])],
                        total_side=SIDE_LABEL[("TOTAL", e_t["side"])],
                        dec_s=e_s["dec"], dec_t=e_t["dec"],
                        p_s=e_s["p"], p_t=e_t["p"], pm_s=e_s["pm"], pm_t=e_t["pm"],
                        line_s=row.spread_line, line_t=row.total_line,
                        mu_margin=row.mu_margin, sigma_margin=row.sigma_margin,
                        mu_total=row.mu_total, sigma_total=row.sigma_total,
                        home_team=row.home_team, away_team=row.away_team,
                        result=row.result, total=row.total))
    return pd.DataFrame(out)


# --------------------------------------------------------------------------
# settlement
# --------------------------------------------------------------------------
def settle_spread(result, line, side):
    if side == "home":
        v = result - line
    else:
        v = line - result
    if abs(v) < 1e-9:
        return "push"
    return "win" if v > 0 else "loss"


def settle_total(total, line, side):
    v = (total - line) if side == "over" else (line - total)
    if abs(v) < 1e-9:
        return "push"
    return "win" if v > 0 else "loss"


def settle_ml(result, side):
    if abs(result) < 1e-9:
        return "void"
    return "win" if ((result > 0) == (side == "home ML")) else "loss"


def settle_bets(bets, pred):
    """Attach outcome + profit to single bets."""
    idx = pred.set_index("game_id")
    rows = []
    for b in bets.to_dict("records"):
        g = idx.loc[b["game_id"]]
        if pd.isna(g.result):
            continue
        if b["market"] == "SPREAD":
            o = settle_spread(g.result, g.spread_line, b["side"])
        elif b["market"] == "TOTAL":
            o = settle_total(g.total, g.total_line, b["side"])
        else:
            o = settle_ml(g.result, b["side"])
        profit = (b["odds_dec"] - 1) * b["stake"] if o == "win" else (
            0.0 if o in ("push", "void") else -b["stake"])
        b["outcome"] = o
        b["profit"] = profit
        rows.append(b)
    return pd.DataFrame(rows)


def settle_parlays(parlays, pred):
    idx = pred.set_index("game_id")
    rows = []
    for p in parlays:
        legs = p.pop("_legs")
        win = True
        live_dec = 1.0
        any_live = False
        for leg in legs:
            g = idx.loc[leg["game_id"]]
            if leg["market"] == "SPREAD":
                o = settle_spread(g.result, g.spread_line, leg["side"])
            else:
                o = settle_total(g.total, g.total_line, leg["side"])
            if o == "loss":
                win = False
            if o in ("win", "loss"):
                live_dec *= leg["odds_dec"]
                any_live = True
        if not win:
            o_all, profit = "loss", -p["stake"]
        elif not any_live:
            o_all, profit = "void", 0.0
        else:
            o_all, profit = "win", (live_dec - 1) * p["stake"]
        p["outcome"] = o_all
        p["profit"] = profit
        p["odds_dec_settled"] = live_dec if win else 0.0
        rows.append(p)
    return pd.DataFrame(rows)
