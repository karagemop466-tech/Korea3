#!/usr/bin/env python3
"""Requirement 5 — a leaderboard that scores signal separately from staking.

The split
---------
SIGNAL is scored on flat one-unit bets only. No stake sizing enters it, so a strategy cannot rise
by betting bigger on the bets that happened to win. The score is a 95% lower bound on flat ROI:

    signal_score = roi_flat - 1.96 * sd(per-bet returns) / sqrt(n)

which punishes small samples and noisy return streams as well as losing ones.

STAKING is scored separately, on the same bets bet a second time with a Kelly fraction derived from
our own fair probability against the market price. Because stake sizing is order-dependent, the
staking lift is compared against a permutation band: the bets are reshuffled N_PERM times with a
fixed seed and the lift recomputed, so a reader can see whether the staking number is bigger than
what the same bets in a lucky order would have produced.

    mask_gap = rank_by_staking - rank_by_signal

A positive mask_gap means the strategy looks better under staking than it is.

Two things this leaderboard deliberately does not claim
-------------------------------------------------------
* CLV is blank on every row. Every bet here is struck at the recorded closing price, because the
  price store has no opening number for 5,971 of 5,971 priced games outside 2021. A bet cannot have
  closing-line value if it was placed at the close; the column is left blank and flagged rather
  than reported as zero.
* Player-prop combinations are blank on every row. No official publisher prints player-prop prices
  or the player logs they settle against, so there is nothing to compute with. The schema is
  published so the row exists and the gap is visible.
"""
from __future__ import annotations

import json
import math
import random

import lib

ORIGIN = lib.DATA / "origination.json"
OUT = lib.DATA / "leaderboard.json"

SIDE_MIN = 1.0        # points of disagreement with the market before a side bet is struck
TOTAL_MIN = 1.5       # points before a total bet is struck
ML_MIN = 0.02         # probability points before a moneyline bet is struck
N_PERM = 2000
SEED = lib.__dict__.get("SEED", 20261114)
SEED = 20261114
MAX_STAKE = 0.05


def phi(z):
    return lib._norm_cdf(z)


def settle_side(margin, spread, pick_home):
    """returns 1 win, 0 loss, None push (margin relative to home)."""
    if margin is None or spread is None:
        return None
    d = margin - spread
    if abs(d) < 1e-9:
        return None
    won = (d > 0) if pick_home else (d < 0)
    return 1 if won else 0


def settle_total(total, line, pick_over):
    if total is None or line is None:
        return None
    d = total - line
    if abs(d) < 1e-9:
        return None
    won = (d > 0) if pick_over else (d < 0)
    return 1 if won else 0


def payout(price, won):
    """Profit on a one-unit bet. Push returns 0."""
    if won is None:
        return 0.0
    dec = lib.american_to_decimal(price)
    if dec is None:
        return None
    if won:
        return dec - 1.0
    return -1.0


# --------------------------------------------------------------------------------------------
def build_bets(rows):
    """Return {strategy_id: [bet, ...]} — every bet carries its own source ids."""
    by_week = {}
    for r in rows:
        if not r["played"]:
            continue
        by_week.setdefault((r["season"], r["week"]), []).append(r)

    bets = {sid: [] for sid in STRATEGIES}

    def add(sid, r, market, pick, price, fair_p, source_note):
        if price is None or price == 0:
            return
        bets[sid].append({
            "game_id": r["game_id"], "season": r["season"], "week": r["week"],
            "market": market, "pick": pick, "price": price,
            "fair_p": fair_p, "note": source_note,
        })

    for r in rows:
        if not r["played"]:
            continue
        s = r["season"]
        if s < 2006:
            continue

        margin, total = r["margin"], r["total"]
        ms, mt = r["market_side"], r["market_total"]
        mu, tau, sigma = r["fair_side"], r["fair_total"], r["sigma_margin"]

        # ---- S1 side edge
        if ms is not None and r["diff_side"] is not None and mu is not None and sigma:
            if abs(r["diff_side"]) >= SIDE_MIN:
                pick_home = r["diff_side"] > 0
                price = r["home_spread_odds"] if pick_home else r["away_spread_odds"]
                p = 1.0 - phi((ms - mu) / sigma) if pick_home else phi((ms - mu) / sigma)
                add("S1", r, "SIDE", "home" if pick_home else "away", price, p,
                    "Bet the side our fair line disagrees with by at least %.1f points." % SIDE_MIN)

        # ---- S2 total edge
        if mt is not None and r["diff_total"] is not None and tau is not None and sigma:
            if abs(r["diff_total"]) >= TOTAL_MIN:
                over = r["diff_total"] > 0
                price = r["over_odds"] if over else r["under_odds"]
                # P(total > line) via the margin/total decomposition: treat total as normal
                # around tau with the league-typical total sd estimated from sigma_margin.
                sd_tot = sigma * 1.35
                p = 1.0 - phi((mt - tau) / sd_tot) if over else phi((mt - tau) / sd_tot)
                add("S2", r, "TOTAL", "over" if over else "under", price, p,
                    "Bet the total our fair number disagrees with by at least %.1f points." % TOTAL_MIN)

        # ---- S3 moneyline edge
        if r["diff_ml_prob"] is not None and r["market_ml_home"] is not None:
            if abs(r["diff_ml_prob"]) >= ML_MIN:
                home = r["diff_ml_prob"] > 0
                price = r["market_ml_home"] if home else r["market_ml_away"]
                p = r["fair_p_home"] if home else r["fair_p_away"]
                add("S3", r, "MONEYLINE", "home" if home else "away", price, p,
                    "Bet the moneyline side our fair probability disagrees with by at least %.2f." % ML_MIN)

        # ---- S4 divisional home underdog
        if ms is not None and r["div_game"] == 1 and ms < 0 and r["market_side"] is not None:
            price = r["home_spread_odds"]
            p = None
            if mu is not None and sigma:
                p = 1.0 - phi((ms - mu) / sigma)
            add("S4", r, "SIDE", "home", price, p,
                "Divisional game and the home team is the market underdog. Rule is market-side only; our own number is carried for the staking leg but does not select the bet.")

        # ---- S5 rest asymmetry against the home team
        hr, ar = r["home_rest"], r["away_rest"]
        if hr is not None and ar is not None and (ar - hr) >= 3 and ms is not None:
            price = r["away_spread_odds"]
            p = phi((ms - mu) / sigma) if (mu is not None and sigma) else None
            add("S5", r, "SIDE", "away", price, p,
                "Away team has at least three more days of rest than the home team.")

    # ---- S6 same-game two-leg parlay: the side and total legs of one game, when both clear
    for r in rows:
        if not r["played"] or r["season"] < 2006:
            continue
        if r["market_side"] is None or r["market_total"] is None:
            continue
        if r["diff_side"] is None or r["diff_total"] is None:
            continue
        if abs(r["diff_side"]) < SIDE_MIN or abs(r["diff_total"]) < TOTAL_MIN:
            continue
        pick_home = r["diff_side"] > 0
        over = r["diff_total"] > 0
        p1 = r["home_spread_odds"] if pick_home else r["away_spread_odds"]
        p2 = r["over_odds"] if over else r["under_odds"]
        if p1 is None or p2 is None:
            continue
        sig = r["sigma_margin"]
        mu, tau, ms, mt = r["fair_side"], r["fair_total"], r["market_side"], r["market_total"]
        if None in (sig, mu, tau, ms, mt):
            continue
        fp1 = (1.0 - phi((ms - mu) / sig)) if pick_home else phi((ms - mu) / sig)
        sd_tot = sig * 1.35
        fp2 = (1.0 - phi((mt - tau) / sd_tot)) if over else phi((mt - tau) / sd_tot)
        bets["S6"].append({
            "game_id": r["game_id"], "season": r["season"], "week": r["week"],
            "market": "PARLAY_2_SAME_GAME",
            "pick": "%s side + %s" % ("home" if pick_home else "away", "over" if over else "under"),
            "price": lib.decimal_to_american(
                (lib.american_to_decimal(p1) or 1.0) * (lib.american_to_decimal(p2) or 1.0)),
            "fair_p": None if None in (fp1, fp2) else fp1 * fp2,
            "legs": [
                {"game_id": r["game_id"], "market": "SIDE", "pick": "home" if pick_home else "away", "price": p1, "fair_p": fp1},
                {"game_id": r["game_id"], "market": "TOTAL", "pick": "over" if over else "under", "price": p2, "fair_p": fp2},
            ],
            "note": "Two legs on the same game, priced at the product of the two leg prices. The correlation adjustment is on correlations.html and is NOT applied here.",
        })

    # ---- S7 cross-game two-leg parlay: two strongest side edges in the same week
    for (season, week), grp in sorted(by_week.items()):
        if season < 2006:
            continue
        cands = []
        for r in grp:
            if r["diff_side"] is None or r["market_side"] is None or abs(r["diff_side"]) < SIDE_MIN:
                continue
            pick_home = r["diff_side"] > 0
            price = r["home_spread_odds"] if pick_home else r["away_spread_odds"]
            if price is None:
                continue
            sig = r["sigma_margin"]
            fp = None
            if sig and r["fair_side"] is not None and r["market_side"] is not None:
                fp = ((1.0 - phi((r["market_side"] - r["fair_side"]) / sig)) if pick_home
                      else phi((r["market_side"] - r["fair_side"]) / sig))
            cands.append((abs(r["diff_side"]), r, pick_home, price, fp))
        cands.sort(key=lambda c: (-c[0], c[1]["game_id"]))
        if len(cands) < 2:
            continue
        legs = []
        fps = []
        for _, r, pick_home, price, fp in cands[:2]:
            legs.append({"game_id": r["game_id"], "market": "SIDE",
                         "pick": "home" if pick_home else "away", "price": price, "fair_p": fp})
            fps.append(fp)
        bets["S7"].append({
            "game_id": "%s/%s" % (legs[0]["game_id"], legs[1]["game_id"]),
            "season": season, "week": week,
            "market": "PARLAY_2_CROSS_GAME",
            "pick": " + ".join("%s %s" % (l["game_id"], l["pick"]) for l in legs),
            "price": lib.decimal_to_american(
                (lib.american_to_decimal(legs[0]["price"]) or 1.0)
                * (lib.american_to_decimal(legs[1]["price"]) or 1.0)),
            "fair_p": None if any(f is None for f in fps) else fps[0] * fps[1],
            "legs": legs,
            "note": "The two largest side disagreements of the week, priced at the product of the two leg prices. No correlation adjustment is applied here.",
        })

    return bets


STRATEGIES = {
    "S1": {"name": "Own side vs market spread", "market": "SIDE", "kind": "single",
           "rule": "Bet the side our fair line disagrees with by >= 1.0 point."},
    "S2": {"name": "Own total vs market total", "market": "TOTAL", "kind": "single",
           "rule": "Bet the total our fair number disagrees with by >= 1.5 points."},
    "S3": {"name": "Own moneyline vs market price", "market": "MONEYLINE", "kind": "single",
           "rule": "Bet the moneyline side whose fair probability differs from the de-vigged market by >= 0.02."},
    "S4": {"name": "Divisional home underdog", "market": "SIDE", "kind": "single",
           "rule": "In a divisional game, back the home team when the market makes it the underdog."},
    "S5": {"name": "Rest asymmetry, away side", "market": "SIDE", "kind": "single",
           "rule": "Back the away team when it has at least three more days of rest than the home team."},
    "S6": {"name": "Same-game two-leg parlay", "market": "PARLAY_2_SAME_GAME", "kind": "parlay",
           "rule": "When both the side and the total clear their thresholds in the same game, play both as a two-leg card."},
    "S7": {"name": "Cross-game two-leg parlay", "market": "PARLAY_2_CROSS_GAME", "kind": "parlay",
           "rule": "Play the week's two largest side disagreements as a two-leg card."},
    "S8": {"name": "Player-prop combination", "market": "PLAYER_PROP", "kind": "prop",
           "rule": "Blocked. No official publisher prints player-prop prices or the player logs they settle against. Schema only; every value is blank."},
}


# --------------------------------------------------------------------------------------------
def settle_leg(lg, row_index):
    """Settle one leg of any market. Returns 1 win, 0 loss, None push."""
    r = row_index.get(lg["game_id"])
    if r is None:
        return None
    m = lg["market"]
    if m == "SIDE":
        return settle_side(r["margin"], r["market_side"], lg["pick"] == "home")
    if m == "TOTAL":
        return settle_total(r["total"], r["market_total"], lg["pick"] == "over")
    if m == "MONEYLINE":
        mg = r["margin"]
        if mg is None:
            return None
        if mg == 0:
            return None
        return 1 if (mg > 0) == (lg["pick"] == "home") else 0
    return None


def settle(bet, row_index):
    """Return (pnl on one unit, 1/0/None). A push anywhere on a card voids it: see note."""
    if bet["market"] == "SIDE":
        r = row_index[bet["game_id"]]
        won = settle_side(r["margin"], r["market_side"], bet["pick"] == "home")
        return payout(bet["price"], won), won
    if bet["market"] == "TOTAL":
        r = row_index[bet["game_id"]]
        won = settle_total(r["total"], r["market_total"], bet["pick"] == "over")
        return payout(bet["price"], won), won
    if bet["market"] == "MONEYLINE":
        r = row_index[bet["game_id"]]
        m = r["margin"]
        if m is None:
            return None, None
        if m == 0:
            return 0.0, None            # a tie is graded a push on a two-way moneyline
        won = 1 if (m > 0) == (bet["pick"] == "home") else 0
        return payout(bet["price"], won), won
    if bet["market"].startswith("PARLAY_2"):
        results, prices = [], []
        for lg in bet["legs"]:
            results.append(settle_leg(lg, row_index))
            prices.append(lg["price"])
        bet["_leg_results"] = results
        if any(w is None for w in results):
            return None, None            # a pushed leg is dropped, never scored as a loss
        if all(w == 1 for w in results):
            dec = 1.0
            for p in prices:
                d = lib.american_to_decimal(p)
                if d is None:
                    return None, None
                dec *= d
            return dec - 1.0, 1
        return -1.0, 0
    return None, None


def kelly_fraction(p, price):
    dec = lib.american_to_decimal(price)
    if dec is None or p is None:
        return None
    b = dec - 1.0
    if b <= 0:
        return None
    f = (b * p - (1.0 - p)) / b
    return f


def max_drawdown(seq):
    peak, dd, cur = 0.0, 0.0, 0.0
    for x in seq:
        cur += x
        peak = max(peak, cur)
        dd = min(dd, cur - peak)
    return dd


def score_strategy(sid, bet_list, row_index):
    spec = STRATEGIES[sid]
    if spec["kind"] == "prop":
        return {
            "id": sid, "name": spec["name"], "market": spec["market"], "kind": spec["kind"],
            "rule": spec["rule"], "blocked": True,
            "blocked_reason": "No official publisher prints player-prop prices, and no official player-level log is reachable from this repository. Every numeric field is blank rather than estimated.",
        }

    pnl, wins, losses, pushes, decided, stakes = [], 0, 0, 0, 0, []
    fair_ps, prices, drops = [], [], 0
    for b in bet_list:
        p, won = settle(b, row_index)
        if p is None:
            drops += 1
            continue
        pnl.append(p)
        if won is None:
            pushes += 1
        elif won == 1:
            wins += 1
        else:
            losses += 1
        decided += 1 if won is not None else 0
        prices.append(b["price"])
        fair_ps.append(b.get("fair_p"))
        # Kelly stake, capped and floored
        f = kelly_fraction(b.get("fair_p"), b["price"])
        if f is None:
            f = 0.0
        stakes.append(min(MAX_STAKE, max(0.0, f)))

    n = len(pnl)
    if n == 0:
        return {"id": sid, "name": spec["name"], "market": spec["market"], "kind": spec["kind"],
                "rule": spec["rule"], "blocked": False, "n_bets": 0, "note": "No bet met the rule."}

    turnover_flat = float(n)
    roi_flat = sum(pnl) / turnover_flat
    sd = lib.pstdev(pnl)
    se = (sd / math.sqrt(n)) if sd and n else None
    signal_score = roi_flat - 1.959963984540054 * (se or 0.0)

    # breakeven hit rate implied by the average price actually taken
    avg_price = lib.mean([lib.american_to_decimal(p) for p in prices if lib.american_to_decimal(p)])
    be = (1.0 / avg_price) if avg_price else None
    hit = (wins / decided) if decided else None
    z = None
    p_value = None
    if be is not None and decided and be > 0 and be < 1:
        z = (hit - be) / math.sqrt(be * (1 - be) / decided)
        p_value = 2.0 * (1.0 - lib._norm_cdf(abs(z)))

    # ---- staking: same bets, sized by capped Kelly, run in the order they occurred
    def run_staked(order, frac):
        bank, seq, turn = 1.0, [], 0.0
        for i in order:
            f = min(MAX_STAKE, max(0.0, stakes[i] * frac))
            stake = bank * f
            if stake <= 0:
                seq.append(0.0)
                continue
            turn += stake
            profit = stake * pnl[i]
            bank += profit
            seq.append(profit)
        return (sum(seq) / turn) if turn else None, bank - 1.0, seq

    half_roi, half_growth, half_seq = run_staked(range(n), 0.5)
    full_roi, full_growth, _ = run_staked(range(n), 1.0)
    quarter_roi, quarter_growth, _ = run_staked(range(n), 0.25)

    staking_score = (half_roi - 1.959963984540054 * (lib.pstdev(half_seq) / math.sqrt(n))) if half_roi is not None and n else None
    lift = None if half_roi is None else half_roi - roi_flat

    # ---- permutation band on the staking lift: does the ordering, not the betting, carry it?
    rng = random.Random(SEED)
    lifts = []
    for _ in range(N_PERM):
        order = list(range(n))
        rng.shuffle(order)
        r_, _, _ = run_staked(order, 0.5)
        if r_ is not None:
            lifts.append(r_ - roi_flat)
    lifts.sort()
    if lift is not None and lifts:
        below = sum(1 for x in lifts if x <= lift)
        pct = below / len(lifts)
        band_lo, band_hi = lifts[int(0.025 * len(lifts))], lifts[int(0.975 * len(lifts)) - 1]
    else:
        pct = band_lo = band_hi = None

    holdout = [pnl[i] for i in range(n) if bet_list[i]["season"] in (2023, 2024, 2025)]
    ho_roi = (sum(holdout) / len(holdout)) if holdout else None

    per_season = {}
    for i in range(n):
        per_season.setdefault(bet_list[i]["season"], []).append(pnl[i])
    season_roi = {str(s): round(sum(v) / len(v), 5) for s, v in sorted(per_season.items())}
    pos = sum(1 for v in per_season.values() if sum(v) > 0)
    positive_share = pos / len(per_season) if per_season else None

    return {
        "id": sid, "name": spec["name"], "market": spec["market"], "kind": spec["kind"],
        "rule": spec["rule"], "blocked": False,
        "n_bets": n, "wins": wins, "losses": losses, "pushes": pushes, "dropped": drops,
        "hit_rate": lib.round_or_none(hit, 5),
        "avg_price": lib.round_or_none(avg_price, 5),
        "breakeven_hit_rate": lib.round_or_none(be, 5),
        "z_vs_breakeven": lib.round_or_none(z, 4),
        "p_value": lib.round_or_none(p_value, 5),
        # --- signal (flat one unit)
        "roi_flat": lib.round_or_none(roi_flat, 5),
        "roi_sd": lib.round_or_none(sd, 5),
        "signal_score": lib.round_or_none(signal_score, 5),
        "holdout_roi": lib.round_or_none(ho_roi, 5),
        "holdout_n": len(holdout),
        "seasons_bet": len(per_season),
        "positive_season_share": lib.round_or_none(positive_share, 4),
        "season_roi": season_roi,
        "max_drawdown_flat": lib.round_or_none(max_drawdown(pnl), 3),
        # --- staking (same bets, Kelly-sized)
        "roi_kelly_full": lib.round_or_none(full_roi, 5),
        "roi_kelly_half": lib.round_or_none(half_roi, 5),
        "roi_kelly_quarter": lib.round_or_none(quarter_roi, 5),
        "bankroll_growth_half": lib.round_or_none(half_growth, 5),
        "staking_score": lib.round_or_none(staking_score, 5),
        "staking_lift_half": lib.round_or_none(lift, 5),
        "staking_lift_pct": lib.round_or_none(pct, 4),
        "staking_luck_band_lo": lib.round_or_none(band_lo, 5),
        "staking_luck_band_hi": lib.round_or_none(band_hi, 5),
        "max_drawdown_staked": lib.round_or_none(max_drawdown(half_seq), 3),
        # --- explicitly not available
        "clv": None,
        "clv_note": "Blank. Every bet is struck at the recorded closing price, so closing-line value is undefined rather than zero. See flagged.html F-A02.",
    }


def benjamini_hochberg(rows):
    items = [(i, r["p_value"]) for i, r in enumerate(rows)
             if not r.get("blocked") and r.get("p_value") is not None and r.get("n_bets")]
    items.sort(key=lambda t: t[1])
    m = len(items)
    if m == 0:
        return
    prev = 1.0
    for rank in range(m - 1, -1, -1):
        idx, p = items[rank]
        q = min(prev, p * m / (rank + 1))
        prev = q
        rows[idx]["q_value_fdr"] = round(q, 5)


def main():
    origin = json.loads(ORIGIN.read_text(encoding="utf-8"))
    rows = origin["rows"]
    row_index = {r["game_id"]: r for r in rows}

    bets = build_bets(rows)
    results = []
    for sid in STRATEGIES:
        res = score_strategy(sid, bets[sid], row_index)
        res["bets_generated"] = len(bets[sid])
        results.append(res)

    benjamini_hochberg(results)

    # two rankings, published side by side
    scorable = [r for r in results if not r.get("blocked") and r.get("n_bets")]
    by_signal = sorted(scorable, key=lambda r: -(r["signal_score"] or -9))
    by_staking = sorted(scorable, key=lambda r: -(r["staking_score"] if r["staking_score"] is not None else -9))
    r_signal = {r["id"]: i + 1 for i, r in enumerate(by_signal)}
    r_staking = {r["id"]: i + 1 for i, r in enumerate(by_staking)}
    for r in results:
        r["rank_signal"] = r_signal.get(r["id"])
        r["rank_staking"] = r_staking.get(r["id"])
        if r["rank_signal"] and r["rank_staking"]:
            r["mask_gap"] = r["rank_signal"] - r["rank_staking"]
        else:
            r["mask_gap"] = None

    # ---- parlay leg outcomes, for correlations.py to measure dependence on
    leg_rows = []
    for sid in ("S6", "S7"):
        for b in bets[sid]:
            res = b.get("_leg_results")
            if not res or len(res) != 2 or any(x is None for x in res):
                continue
            leg_rows.append({
                "strategy": sid, "game_id": b["game_id"], "season": b["season"], "week": b["week"],
                "leg1": b["legs"][0]["market"] + ":" + b["legs"][0]["pick"],
                "leg2": b["legs"][1]["market"] + ":" + b["legs"][1]["pick"],
                "leg1_win": res[0], "leg2_win": res[1],
                "leg1_price": b["legs"][0]["price"], "leg2_price": b["legs"][1]["price"],
                "card_win": 1 if res[0] == 1 and res[1] == 1 else 0,
            })
    (lib.DATA / "parlay_legs.json").write_text(
        json.dumps({"_meta": {
            "generated_by": "origin_lab/leaderboard.py",
            "note": "One row per two-leg card whose legs both resolved without a push. Leg outcomes are functions of official final scores only, so the dependence measured from them is a fact about the league's results, not about any price.",
        }, "rows": leg_rows}, indent=1) + "\n", encoding="utf-8")

    out = {
        "_meta": {
            "generated_by": "origin_lab/leaderboard.py",
            "session": "arena/5f341290-korea3",
            "signal_definition": "Flat one unit per bet. signal_score = roi_flat - 1.96 * sd(returns)/sqrt(n), a 95% lower bound. No stake sizing enters it.",
            "staking_definition": "Same bets, sized by the Kelly fraction from our own fair probability against the market price, capped at 5% of bankroll, run in the order the games occurred.",
            "luck_test": "The bet order is permuted %d times with seed %d and the half-Kelley lift recomputed. staking_lift_pct is the share of permutations whose lift is at or below the observed one; the band is its 2.5th to 97.5th percentile." % (N_PERM, SEED),
            "mask_gap": "rank_signal - rank_staking. Positive means the strategy looks better once stake sizing is applied than it is.",
            "prices": "Every bet is settled at the recorded closing price. That is the only price the store holds. It is an optimistic convention and is flagged, not defended.",
            "window": "Seasons 2006 onward, the out-of-sample window set in originate.py. Holdout 2023-2025.",
        },
        "strategies": results,
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")

    print("%-4s %-30s %6s %8s %9s %9s %8s %6s %6s" % (
        "id", "name", "n", "roiFlat", "sigScore", "stkScore", "lift", "rSig", "rStk"))
    for r in results:
        if r.get("blocked"):
            print("%-4s %-30s  BLOCKED (no official prop prices or player logs)" % (r["id"], r["name"][:30]))
            continue
        if not r.get("n_bets"):
            print("%-4s %-30s %6d  no bets met the rule" % (r["id"], r["name"][:30], 0))
            continue
        print("%-4s %-30s %6d %8s %9s %9s %8s %6s %6s" % (
            r["id"], r["name"][:30], r["n_bets"], r["roi_flat"], r["signal_score"],
            r["staking_score"], r["staking_lift_half"], r["rank_signal"], r["rank_staking"]))


if __name__ == "__main__":
    main()
