"""Market-structure research: what the book charges, and how efficient it is.

Answers the questions you need before writing a single strategy:
  * what is the hold (vig) on each market?
  * what hit rate is required to break even?
  * how often does the underdog / home team / over win?
  * is there a favourite-longshot bias in the moneyline?
  * how far does a line move between the opener and the close?
"""
import numpy as np
import pandas as pd

from common import (RAW, american_to_prob, devig_two_way, american_to_decimal)


def hold_stats(pred):
    d = pred[pred.result.notna()]
    out = {}
    for name, (a, b) in {
        "spread": ("home_spread_odds", "away_spread_odds"),
        "total": ("over_odds", "under_odds"),
        "moneyline": ("home_moneyline", "away_moneyline"),
    }.items():
        sub = d[d[a].notna() & d[b].notna()]
        if not len(sub):
            continue
        pa = american_to_prob(sub[a].values)
        pb = american_to_prob(sub[b].values)
        sump = pa + pb
        out[name] = {
            "n": int(len(sub)),
            "mean_overround": float(np.mean(sump)),
            "median_hold_pct": float(np.median(sump - 1) * 100),
            "mean_hold_pct": float(np.mean(sump - 1) * 100),
            "typical_price": float(sub[a].median()),
            "sample_prices": [float(x) for x in sub[a].head(5)],
        }
    # break-even hit rate at the most common price
    for price in (-110, -105, -120):
        dec = float(american_to_decimal(np.array([price]))[0])
        out.setdefault("breakeven_by_price", {})[str(price)] = {
            "decimal": dec, "required_hit_rate": 1 / dec,
            "required_hit_rate_pct": round(100 / dec, 2)}
    return out


def base_rates(pred):
    d = pred[pred.result.notna()]
    r = {
        "n_games": int(len(d)),
        "seasons": [int(d.season.min()), int(d.season.max())],
        "home_win_rate": float((d.result > 0).mean()),
        "away_win_rate": float((d.result < 0).mean()),
        "tie_rate": float((d.result == 0).mean()),
        "home_cover_rate": float((d.result > d.spread_line).mean()),
        "ats_push_rate": float((d.result == d.spread_line).mean()),
        "over_rate": float((d.total > d.total_line).mean()),
        "total_push_rate": float((d.total == d.total_line).mean()),
        "mean_total_points": float(d.total.mean()),
        "mean_abs_margin": float(d.result.abs().mean()),
        "sd_margin": float(d.result.std(ddof=1)),
        "sd_total": float(d.total.std(ddof=1)),
        "mean_abs_closing_line": float(d.spread_line.abs().mean()),
    }
    return r


def favourite_longshot(pred):
    """Classic test: does the moneyline over-price longshots?"""
    d = pred[pred.result.notna() & pred.home_moneyline.notna()].copy()
    rows = []
    edges = [(-10000, -300), (-300, -200), (-200, -150), (-150, -100),
             (100, 150), (150, 250), (250, 10000)]
    for lo, hi in edges:
        m = d[(d.home_moneyline > lo) & (d.home_moneyline <= hi)]
        if len(m) < 40:
            continue
        pa = american_to_prob(m.home_moneyline.values)
        pb = american_to_prob(m.away_moneyline.values)
        dev_a, dev_b, hold = devig_two_way(pa, pb)
        dec = american_to_decimal(m.home_moneyline.values)
        win = (m.result.values > 0).astype(float)
        roi = float(np.mean(win * (dec - 1) - (1 - win)))
        rows.append({
            "bucket": f"{lo} to {hi}", "n": int(len(m)),
            "implied_raw": float(np.mean(pa)), "implied_devig": float(np.mean(dev_a)),
            "actual_home_win_rate": float(np.mean(win)),
            "home_ml_roi": roi,
        })
    return rows


def line_movement(pred):
    """Open -> close movement.

    Convention note: games.csv quotes the spread from the HOME perspective with
    the favourite POSITIVE.  Both movement files quote each team's own line with
    the favourite NEGATIVE, so the home-perspective opener is -line(home row).

    Result = closing_home_spread - opening_home_spread (points).
    """
    out = {}
    try:
        init = pd.read_csv(f"{RAW}/initial_lines.csv")
        sp = init[init.type == "SPREAD"].copy()
        home_rows = sp.merge(pred[["alt_game_id", "home_team"]], left_on="about",
                             right_on="alt_game_id", how="inner")
        home_rows = home_rows[home_rows.side == home_rows.home_team]
        m = home_rows.merge(pred[["alt_game_id", "spread_line"]], on="alt_game_id",
                            how="inner")
        m["open_home"] = -m.line
        m["move"] = m.spread_line - m.open_home
        out["opening_vs_closing"] = {
            "file": "initial_lines.csv",
            "publisher_note": "nflverse/nfldata; sportsbook column = WSGT; season 2021 only",
            "n_games": int(m.alt_game_id.nunique()),
            "mean_abs_move_pts": float(m.move.abs().mean()),
            "median_abs_move_pts": float(m.move.abs().median()),
            "share_moved_half_pt_or_more": float((m.move.abs() >= 0.5).mean()),
            "share_moved_1pt_or_more": float((m.move.abs() >= 1).mean()),
            "share_moved_2pt_or_more": float((m.move.abs() >= 2).mean()),
            "corr_open_close": float(np.corrcoef(m.open_home, m.spread_line)[0, 1]),
            "sample_rows": [
                {"game": r.alt_game_id, "open_home_spread": float(r.open_home),
                 "close_home_spread": float(r.spread_line), "move": float(r.move)}
                for r in m.head(5).itertuples()],
        }
    except Exception as e:                                   # pragma: no cover
        out["opening_vs_closing"] = {"error": str(e), "status": "unverified"}

    try:
        sc = pd.read_csv(f"{RAW}/sc_lines.csv")
        h = sc.merge(pred[["game_id", "home_team"]], on="game_id", how="inner")
        h = h[h.side == h.home_team]
        m = h.merge(pred[["game_id", "spread_line"]], on="game_id", how="inner")
        m["open_home"] = -m.line
        m["move"] = m.spread_line - m.open_home
        out["secondary_line_file"] = {
            "file": "sc_lines.csv",
            "publisher_note": "nflverse/nfldata; book not documented (see IR-01); 2013-2020",
            "n_games": int(m.game_id.nunique()),
            "mean_abs_move_pts": float(m.move.abs().mean()),
            "median_abs_move_pts": float(m.move.abs().median()),
            "share_moved_1pt_or_more": float((m.move.abs() >= 1).mean()),
            "corr_open_close": float(np.corrcoef(m.open_home, m.spread_line)[0, 1]),
        }
    except Exception as e:                                   # pragma: no cover
        out["secondary_line_file"] = {"error": str(e), "status": "unverified"}
    return out


def quarter_lines(pred):
    """Do key numbers (3 and 7) still matter?  Frequency of margins by value."""
    d = pred[pred.result.notna()]
    vc = d.result.abs().round().astype(int).value_counts().sort_index()
    tot = len(d)
    return [{"margin": int(k), "n": int(v), "share": float(v / tot)}
            for k, v in vc.items() if v / tot >= 0.01]
