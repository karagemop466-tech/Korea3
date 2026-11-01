"""T6 — Line movement, closing-line value and the price of a point.

What this module measures, and why it matters
---------------------------------------------
A backtest ROI can be earned by luck. Closing-line value (CLV) cannot, or at least not easily: the closing line is
the market's final, money-weighted opinion, so consistently getting a better number than the close is the closest
thing to a direct measurement of skill. This module answers three questions with the data we actually have:

  1. How much does the market move between an earlier line and the close? (data/sc_lines.csv, 2013-2020, and
     data/initial_lines.csv, 2021)
  2. Does our own line anticipate that movement? (model edge versus the earlier line, compared with the observed
     move to the close)
  3. What is one point of a better number actually worth in win probability? (measured, not assumed)

Sign conventions (a documented source of bugs — see F-05)
--------------------------------------------------------
* data/games_1999_2026_nflverse.csv: `spread_line` positive = home team favoured.
* data/sc_lines.csv / data/initial_lines.csv: side handicap, negative = that side is favoured.
* data/derived/model_predictions.csv: `model_spread` is a home *margin*, negative = home favoured.
Everything below is converted to ONE convention: `home_handicap` = points added to the home score.
Negative home_handicap = home favoured. So:

    home_handicap(dataset close) = -spread_line
    home_handicap(early line)    = sc_lines[home_team]
    home_handicap(model)         = -model_spread

A bet's CLV in points is (handicap we took) - (handicap at the close); positive = we beat the close.
"""
from __future__ import annotations

import csv
import json
import math
import os
import statistics as st
from collections import defaultdict

from lib_core import DATA, REPORTS, load_games, write_csv

SC_LINES = os.path.join(DATA, "sc_lines.csv")
INITIAL_LINES = os.path.join(DATA, "initial_lines.csv")
PREDICTIONS = os.path.join(DATA, "derived", "model_predictions.csv")
BETS = os.path.join(REPORTS, "bets_all.csv")   # every strategy bet, written by run_strategies.py

KEY_NUMBERS = (3, 7, 10, 14)


# --------------------------------------------------------------------------- loading
def load_early_lines():
    """data/sc_lines.csv -> {game_id(old id): {'home_handicap': x, 'away_handicap': y, 'side_lines': {...}}}."""
    games = {g["old_game_id"]: g for g in load_games() if g.get("old_game_id")}
    out = {}
    per_game = defaultdict(dict)
    with open(SC_LINES, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                per_game[r["game_id"]][r["side"]] = float(r["line"])
            except (TypeError, ValueError):
                continue
    for gid, sides in per_game.items():
        g = games.get(gid)
        if not g or not g["played"]:
            continue
        h, a = g["home_team"], g["away_team"]
        if h not in sides or a not in sides:
            continue
        out[g["game_id"]] = {
            "home_handicap": sides[h],
            "away_handicap": sides[a],
            "side_lines": sides,
            "season": g["season"],
            "week": g["week"],
        }
    return out


def load_open_2021():
    """data/initial_lines.csv -> {nflverse game_id: {'home_handicap': x, 'total': x}} (2021, one book)."""
    per_game = defaultdict(dict)
    totals = defaultdict(dict)
    with open(INITIAL_LINES, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                line = float(r["line"])
            except (TypeError, ValueError):
                continue
            if r["type"] == "SPREAD":
                per_game[r["about"]][r["side"]] = (line, r["season"], r["sportsbook"])
            elif r["type"] == "TOTAL":
                totals[r["about"]][r["side"]] = line
    games = {g["game_id"]: g for g in load_games()}
    out = {}
    for gid, sides in per_game.items():
        g = games.get(gid)
        if not g or not g["played"]:
            continue
        h = g["home_team"]
        if h not in sides:
            continue
        line, season, book = sides[h]
        tot = next(iter(totals.get(gid, {}).values()), None)
        out[gid] = {"home_handicap": line, "total": tot, "season": int(season), "book": book}
    return out


def load_predictions():
    """{game_id: {'model_spread': x, 'model_total': x}} — home-margin convention."""
    out = {}
    if not os.path.exists(PREDICTIONS):
        return out
    with open(PREDICTIONS, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                out[r["game_id"]] = {
                    "model_spread": float(r["model_spread"]),
                    "model_total": float(r["model_total"]),
                    "season": int(r["season"]),
                }
            except (TypeError, ValueError):
                continue
    return out


# --------------------------------------------------------------------------- helpers
def mean(xs):
    xs = [x for x in xs if x is not None]
    return round(st.mean(xs), 4) if xs else None


def quantiles(xs, qs=(0.05, 0.25, 0.5, 0.75, 0.95)):
    xs = sorted(x for x in xs if x is not None)
    if not xs:
        return {}
    return {f"p{int(q * 100)}": round(xs[min(len(xs) - 1, int(q * len(xs)))], 3) for q in qs}


def pearson(xs, ys):
    pairs = [(x, y) for x, y in zip(xs, ys) if x is not None and y is not None]
    if len(pairs) < 3:
        return None
    xs2 = [p[0] for p in pairs]
    ys2 = [p[1] for p in pairs]
    mx, my = st.mean(xs2), st.mean(ys2)
    num = sum((x - mx) * (y - my) for x, y in pairs)
    den = math.sqrt(sum((x - mx) ** 2 for x in xs2) * sum((y - my) ** 2 for y in ys2))
    return round(num / den, 4) if den else None


def ats_points(handicap, margin):
    """Handicap result in 'wins' where a push counts 0.5 (the standard expected-value convention)."""
    d = margin + handicap          # handicap negative = home favoured
    if d > 0:
        return 1.0
    if d < 0:
        return 0.0
    return 0.5


def per_point_value(games, lo=None, hi=None):
    """Empirical value of one point of line, measured by re-pricing every game one point better.

    ATS result at the actual home handicap vs at (handicap - 1) = the same bet with one extra point.
    Reported as the change in expected win share (pushes counted 0.5).
    """
    base, better, flips = [], [], 0
    for g in games:
        if not g["played"] or g["spread_line"] is None:
            continue
        if lo is not None and g["season"] < lo:
            continue
        if hi is not None and g["season"] > hi:
            continue
        hc = -g["spread_line"]
        margin = g["home_score"] - g["away_score"]
        # one point BETTER for the home side means the handicap moves toward zero, i.e. hc + 1
        a, b = ats_points(hc, margin), ats_points(hc + 1.0, margin)
        base.append(a)
        better.append(b)
        if b > a:
            flips += 1
    if not base:
        return None
    return {
        "n_games": len(base),
        "win_share_at_line": round(st.mean(base), 4),
        "win_share_one_point_better": round(st.mean(better), 4),
        "value_of_one_point_pp": round((st.mean(better) - st.mean(base)) * 100, 3),
        "games_improved": flips,
        "share_games_improved": round(flips / len(base), 4),
    }


def key_number_profile(games):
    """How often a game lands exactly on the numbers a line-maker must not move through."""
    rows = []
    played = [g for g in games if g["played"]]
    for k in KEY_NUMBERS:
        exact = sum(1 for g in played if abs(g["home_score"] - g["away_score"]) == k)
        within1 = sum(1 for g in played if abs(abs(g["home_score"] - g["away_score"]) - k) <= 1)
        rows.append({
            "key_number": k,
            "games_exactly": exact,
            "share_exactly": round(exact / len(played), 4),
            "share_within_one": round(within1 / len(played), 4),
        })
    return rows


def margin_distribution(games):
    played = [g for g in games if g["played"]]
    margins = [abs(g["home_score"] - g["away_score"]) for g in played]
    hist = defaultdict(int)
    for m in margins:
        hist[m] += 1
    top = sorted(hist.items(), key=lambda kv: -kv[1])[:12]
    return {
        "n_games": len(margins),
        "mean_abs_margin": round(st.mean(margins), 3),
        "sd_abs_margin": round(st.pstdev(margins), 3),
        "share_decided_by_one_score_8_or_less": round(sum(1 for m in margins if m <= 8) / len(margins), 4),
        "top_margins": [{"margin": m, "games": c, "share": round(c / len(margins), 4)} for m, c in top],
    }


# --------------------------------------------------------------------------- analyses
def early_vs_close(games_by_id, early):
    """Movement between the earlier line in data/sc_lines.csv and the dataset closing line."""
    moves, moves_home, same_lines, season_rows = [], [], 0, defaultdict(list)
    price_point = []
    close_err, early_err = [], []
    for gid, e in early.items():
        g = games_by_id.get(gid)
        if not g or not g["played"] or g["spread_line"] is None:
            continue
        close_hc = -g["spread_line"]
        move = close_hc - e["home_handicap"]       # negative = market moved toward home
        margin = g["home_score"] - g["away_score"]
        moves.append(move)
        moves_home.append(-move)                    # positive = line moved toward home
        if move == 0:
            same_lines += 1
        season_rows[e["season"]].append(move)
        close_err.append(abs(margin + close_hc))    # margin - spread_line, expressed with the home handicap
        early_err.append(abs(margin + e["home_handicap"]))
    if not moves:
        return {}
    absmoves = [abs(m) for m in moves]
    return {
        "source": "data/sc_lines.csv (earlier line) vs closing spread_line in the game dataset",
        "seasons": [min(s for s in season_rows), max(s for s in season_rows)],
        "n_games_with_both": len(moves),
        "share_identical_to_close": round(same_lines / len(moves), 4),
        "mean_abs_move_points": round(st.mean(absmoves), 3),
        "median_abs_move_points": round(st.median(absmoves), 3),
        "share_moved_at_least": {f"{t}": round(sum(1 for m in absmoves if m >= t) / len(absmoves), 4)
                                 for t in (0.5, 1, 1.5, 2, 3)},
        "abs_move_quantiles": quantiles(absmoves),
        "share_move_toward_home": round(sum(1 for m in moves_home if m > 0) / max(1, sum(1 for m in moves_home if m != 0)), 4),
        "market_error_vs_result": {
            "earlier_line_mae": round(st.mean(early_err), 3),
            "closing_line_mae": round(st.mean(close_err), 3),
            "improvement_points": round(st.mean(early_err) - st.mean(close_err), 3),
            "note": "MAE of the line against the actual home margin. The close should beat the earlier line if the "
                    "market learns anything between them — a sanity check on this data source, not a claim about our model.",
        },
        "by_season": [
            {"season": s, "n": len(v), "mean_abs_move": round(st.mean(abs(x) for x in v), 3),
             "share_moved": round(sum(1 for x in v if x != 0) / len(v), 4)}
            for s, v in sorted(season_rows.items())
        ],
    }


def model_vs_movement(games_by_id, early, preds):
    """Does our model's disagreement with the earlier line point the way the market eventually moved?"""
    edges, moves, rows = [], [], []
    for gid, e in early.items():
        g = games_by_id.get(gid)
        p = preds.get(gid)
        if not g or not p or not g["played"] or g["spread_line"] is None:
            continue
        close_hc = -g["spread_line"]
        model_hc = -p["model_spread"]
        edge = model_hc - e["home_handicap"]        # negative = model makes home stronger than the earlier line
        move = close_hc - e["home_handicap"]        # negative = market moved toward home
        edges.append(edge)
        moves.append(move)
        rows.append((edge, move))
    if len(rows) < 50:
        return {}
    # quintiles of the model edge, with the mean move observed in each
    rows.sort(key=lambda r: r[0])
    n = len(rows)
    quint = []
    for i in range(5):
        chunk = rows[i * n // 5:(i + 1) * n // 5]
        quint.append({
            "quintile": i + 1,
            "model_edge_range": [round(chunk[0][0], 2), round(chunk[-1][0], 2)],
            "n": len(chunk),
            "mean_model_edge": round(st.mean(c[0] for c in chunk), 3),
            "mean_move_to_close": round(st.mean(c[1] for c in chunk), 3),
        })
    toward = sum(1 for e, m in rows if e != 0 and m != 0 and (e > 0) == (m > 0))
    both = sum(1 for e, m in rows if e != 0 and m != 0)
    return {
        "n_games": len(rows),
        "pearson_model_edge_vs_move": pearson(edges, moves),
        "share_movements_in_models_direction": round(toward / both, 4) if both else None,
        "n_with_nonzero_edge_and_move": both,
        "by_quintile": quint,
        "reading": ("A positive correlation means the market tends to move toward our line. Even a small positive "
                    "value here is evidence of information, not of profit: a book's margin still has to be beaten."),
    }


def open_2021(games_by_id, opens):
    """The 2021 opening snapshot: bigger moves, one book, and its (limited) evidentiary value."""
    spreads, totals = [], []
    rows = []
    for gid, o in opens.items():
        g = games_by_id.get(gid)
        if not g or not g["played"] or g["spread_line"] is None:
            continue
        close_hc = -g["spread_line"]
        mv = close_hc - o["home_handicap"]
        spreads.append(mv)
        if o["total"] is not None and g["total_line"] is not None:
            totals.append(g["total_line"] - o["total"])
        rows.append(mv)
    if not spreads:
        return {}
    absm = [abs(x) for x in spreads]
    return {
        "source": "data/initial_lines.csv (2021, book WSGT) vs closing lines in the game dataset",
        "n_spreads": len(spreads),
        "mean_abs_move_points": round(st.mean(absm), 3),
        "median_abs_move_points": round(st.median(absm), 3),
        "abs_move_quantiles": quantiles(absm),
        "share_moved_at_least": {f"{t}": round(sum(1 for m in absm if m >= t) / len(absm), 4) for t in (0.5, 1, 2, 3, 5)},
        "n_totals": len(totals),
        "mean_abs_total_move_points": round(st.mean(abs(x) for x in totals), 3) if totals else None,
        "caveat": ("Only one season, one book, and the mean absolute move is far larger than the same-book early-to-close "
                   "movement measured above for 2013-2020. Treated as an earlier line of uncertain provenance and never "
                   "used to claim closing-line value (F-05)."),
    }


def clv_by_construction(early, games_by_id):
    """Why per-strategy CLV is zero here, stated rather than dressed up.

    Every strategy in pipeline/run_strategies.py is priced at the closing line carried in the dataset. Measured against
    that same closing line, closing-line value is therefore exactly zero for every bet — the number is not evidence
    about anything. Real CLV needs a bet placed at a number that still exists at kickoff, so the analysis that follows
    prices the bets at the *earlier* line instead and then measures how far the close moved.
    """
    if not os.path.exists(BETS):
        return {}
    n, zero = 0, 0
    with open(BETS, newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            g = games_by_id.get(r["game_id"])
            if r["market"] not in ("ATS", "SPREAD") or not g or g["spread_line"] is None:
                continue
            n += 1
            zero += 1
    return {
        "n_ats_bets": n,
        "n_with_zero_clv_by_construction": zero,
        "explanation": ("Bets are priced at the dataset closing line, so CLV against that same close is 0.000 for every "
                        "bet by construction. Any report of non-zero CLV from this bet stream would be a bug. The "
                        "early-line strategies below are the analysis that can actually measure CLV."),
    }


def early_line_value(games_by_id, early, preds):
    """Bet the side our line prefers against the EARLIER line, then measure both P&L and the CLV captured.

    This is the only place in the project where a bet is priced at a number a bettor could actually have taken before
    the market moved, which makes closing-line value measurable. Windows: 2013-2018 (design) and 2019-2020 (holdout
    relative to those thresholds, both inside the data available from data/sc_lines.csv).
    """
    rows = []
    for gid, e in early.items():
        g = games_by_id.get(gid)
        p = preds.get(gid)
        if not g or not p or not g["played"] or g["spread_line"] is None:
            continue
        model_hc = -p["model_spread"]          # home handicap implied by our line
        edge = model_hc - e["home_handicap"]   # negative = we make home stronger than the earlier line
        rows.append({
            "game_id": gid, "season": g["season"], "edge": edge,
            "early_home": e["home_handicap"], "close_home": -g["spread_line"],
            "margin": g["home_score"] - g["away_score"],
        })
    out = []
    for thr in (1.0, 2.0, 3.0, 4.0):
        for window, lo, hi in (("design_2013_2018", 2013, 2018), ("holdout_2019_2020", 2019, 2020),
                               ("all_2013_2020", 2013, 2020)):
            bets = [r for r in rows if abs(r["edge"]) >= thr and lo <= r["season"] <= hi]
            if len(bets) < 25:
                out.append({"threshold_pts": thr, "window": window, "bets": len(bets), "note": "too few bets to report"})
                continue
            profit, clv, wins, pushes = [], [], 0, 0
            for r in bets:
                side = "home" if r["edge"] < 0 else "away"
                taken = r["early_home"] if side == "home" else -r["early_home"]
                close = r["close_home"] if side == "home" else -r["close_home"]
                res = ats_points(taken, r["margin"] if side == "home" else -r["margin"])
                if res == 1.0:
                    wins += 1
                elif res == 0.5:
                    pushes += 1
                profit.append(res - 1.0 if res != 0.5 else 0.0)   # -110 pricing: a win pays 0.909, a loss costs 1
                clv.append(taken - close)
            # reprice profits at -110 explicitly
            pnl = []
            for r in bets:
                side = "home" if r["edge"] < 0 else "away"
                taken = r["early_home"] if side == "home" else -r["early_home"]
                res = ats_points(taken, r["margin"] if side == "home" else -r["margin"])
                pnl.append(0.909 if res == 1.0 else (0.0 if res == 0.5 else -1.0))
            units = sum(pnl)
            out.append({
                "threshold_pts": thr,
                "window": window,
                "bets": len(bets),
                "wins": wins,
                "pushes": pushes,
                "losses": len(bets) - wins - pushes,
                "units_at_minus110": round(units, 2),
                "roi_at_minus110": round(units / len(bets), 4),
                "mean_clv_points": round(st.mean(clv), 3),
                "share_beating_close": round(sum(1 for c in clv if c > 0) / len(clv), 4),
                "share_at_close": round(sum(1 for c in clv if c == 0) / len(clv), 4),
            })
    return {
        "definition": ("Side with the larger model edge against the earlier line, staked 1 unit at -110 on the earlier "
                       "line. CLV = handicap taken minus handicap at the close, positive = we beat the close."),
        "results": out,
        "reading": ("A strategy can show positive ROI at the earlier line and still be a loser once the number is gone; "
                    "the CLV column is what separates the two. A positive ROI with negative CLV means the profit came "
                    "from results, not from information."),
    }


def main():
    games = load_games()
    games_by_id = {g["game_id"]: g for g in games}
    early = load_early_lines()
    opens = load_open_2021()
    preds = load_predictions()

    res = {
        "generated_utc": "2026-11-01",
        "conventions": {
            "home_handicap": "points added to the home score; negative = home favoured",
            "clv_points": "handicap taken minus handicap at the close; positive = we beat the close",
        },
        "early_vs_close_2013_2020": early_vs_close(games_by_id, early),
        "model_vs_movement": model_vs_movement(games_by_id, early, preds),
        "open_2021_snapshot": open_2021(games_by_id, opens),
        "clv_by_construction": clv_by_construction(early, games_by_id),
        "early_line_strategies": early_line_value(games_by_id, early, preds),
        "value_of_one_point": {
            "all_games": per_point_value(games),
            "holdout_2024_2026": per_point_value(games, 2024, 2026),
            "design_1999_2018": per_point_value(games, 1999, 2018),
        },
        "key_numbers": key_number_profile(games),
        "margin_distribution": margin_distribution(games),
    }
    os.makedirs(REPORTS, exist_ok=True)
    with open(os.path.join(REPORTS, "movement.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1)

    write_csv(os.path.join(REPORTS, "movement_by_season.csv"),
              res["early_vs_close_2013_2020"].get("by_season", []))
    write_csv(os.path.join(REPORTS, "early_line_strategies.csv"),
              res["early_line_strategies"].get("results", []))

    ev = res["early_vs_close_2013_2020"]
    print("early vs close:", ev.get("n_games_with_both"), "games, mean abs move", ev.get("mean_abs_move_points"),
          "pts, identical to close", ev.get("share_identical_to_close"))
    print("market error:", ev.get("market_error_vs_result"))
    mv = res["model_vs_movement"]
    print("model edge vs movement: r =", mv.get("pearson_model_edge_vs_move"),
          "share in model's direction", mv.get("share_movements_in_models_direction"), "n =", mv.get("n_games"))
    print("value of one point (pp):", res["value_of_one_point"]["all_games"])
    print("key numbers:", [(k["key_number"], k["share_exactly"]) for k in res["key_numbers"]])
    print("CLV by construction:", res["clv_by_construction"].get("n_ats_bets"), "ATS bets, all zero by construction")
    for r in res["early_line_strategies"]["results"]:
        print("  early-line thr", r["threshold_pts"], r["window"], "bets", r["bets"],
              "roi", r.get("roi_at_minus110"), "mean clv", r.get("mean_clv_points"),
              "beat close", r.get("share_beating_close"))
    op = res["open_2021_snapshot"]
    print("2021 open snapshot:", op.get("n_spreads"), "games, mean abs move", op.get("mean_abs_move_points"))


if __name__ == "__main__":
    main()
