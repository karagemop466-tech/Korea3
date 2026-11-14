#!/usr/bin/env python3
"""Build the Snapshot Desk data artifacts from pinned + derived repo data and the official transcription.

Deterministic: stdlib only, no network, no clock, no randomness. Re-running it on the committed
inputs reproduces the committed outputs byte-for-byte (check.py enforces this).

Sources
-------
1. data/raw/games.csv            — pinned nflverse/nfldata @ a270278f3ac4e937295fe6a27814b3c4a2b62645
                                   (scores, closing spread_line / total_line / moneylines, schedule)
2. data/raw/initial_lines.csv    — same pin: WSGT opening spread/total for the 2021 season (272 games)
3. data/derived/model_predictions.csv — the repo's own walk-forward model fair lines (2000–2026)
4. data/derived/own_lines_upcoming.csv — the repo's originated lines for unplayed 2026 fixtures
5. data/derived/model_metrics.json     — the model's measured error (variant B: MAE 10.670 / RMSE 13.618)
6. data/derived/bets.csv               — the line_lab 11-strategy ledger (S1–S11)
7. price_lab/data/official_results_2026.json — session transcription of the official NFL.com week pages,
                                   opened 2026-11-14 (used by check.py to fail on disagreement)

Sign conventions (printed on the pages, enforced here)
------------------------------------------------------
* games.csv `spread_line` is a home-margin line: positive = home favoured; the home side covers when
  result > spread_line. Verified on every pinned season: mean(result − spread_line) ≈ 0.
* The repo's pipeline convention (model_predictions.csv, own_lines_upcoming.csv) negates that:
  mkt_spread == −spread_line on every row (asserted below), so a NEGATIVE pipeline spread means the
  home side is favoured.
* WSGT initial lines are side-specific: the row's `line` is what that side gives (negative) or gets
  (positive); the home-margin opening line is −line (identical from either side's row).

Every emitted row carries its source URL and a tier: dataset (pinned nflverse file), official
(NFL.com page opened this session) or recomputed (derived here from the above by a formula printed
on the page). A value with no source is left blank, never inferred.
"""
from __future__ import annotations

import csv
import json
import math
import statistics as st
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = ROOT / "data" / "raw"
DER = ROOT / "data" / "derived"
OUT = HERE / "data"

PIN = "a270278f3ac4e937295fe6a27814b3c4a2b62645"
PIN_URL = f"https://github.com/nflverse/nfldata/blob/{PIN}"
CHECKED = "2026-11-14"

# --------------------------------------------------------------------------- #
# load
# --------------------------------------------------------------------------- #
games = list(csv.DictReader((RAW / "games.csv").open()))
games_by_id = {g["game_id"]: g for g in games}
initial = list(csv.DictReader((RAW / "initial_lines.csv").open()))
model = list(csv.DictReader((DER / "model_predictions.csv").open()))
upcoming = list(csv.DictReader((DER / "own_lines_upcoming.csv").open()))
metrics = json.loads((DER / "model_metrics.json").read_text())
bets = list(csv.DictReader((DER / "bets.csv").open()))
official = json.loads((HERE / "data" / "official_results_2026.json").read_text())

SIGMA = float(metrics["variants"][metrics["primary_variant"]]["spread"]["model_rmse"])  # 13.618

DATASET_SPREAD_URL = f"{PIN_URL}/data/games.csv"
DATASET_INITIAL_URL = f"{PIN_URL}/data/initial_lines.csv"
DATASET_MODEL_URL = "https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/model_predictions.csv"
DATASET_UPCOMING_URL = "https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/own_lines_upcoming.csv"
DATASET_BETS_URL = "https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/bets.csv"

# ---- hard assertions on the sign conventions ------------------------------
_conv_bad = 0
for r in model:
    g = games_by_id[r["game_id"]]
    if g["spread_line"] and abs(float(r["mkt_spread"]) + float(g["spread_line"])) > 1e-9:
        _conv_bad += 1
assert _conv_bad == 0, f"pipeline/game sign convention mismatch on {_conv_bad} rows"

# --------------------------------------------------------------------------- #
# 1. price-snapshot store
# --------------------------------------------------------------------------- #
snap_rows: list[dict] = []


def snap(game_id, season, week, gameday, away, home, market, side, kind, line, odds, book, url):
    snap_rows.append({
        "game_id": game_id, "season": season, "week": week, "gameday": gameday,
        "away_team": away, "home_team": home, "market": market, "side": side,
        "snapshot": kind, "line": line, "odds": odds, "book": book, "tier": "dataset",
        "source_url": url,
    })


open_2021: dict[str, dict[str, float]] = {}
for r in initial:
    about = r["about"]
    season, week, away, home = about.split("_")[0], about.split("_")[1], about.split("_")[2], about.split("_")[3]
    open_2021.setdefault(about, {})[f"{r['type']}|{r['side']}"] = float(r["line"])
    snap("", season, week, "", away, home, r["type"], r["side"], "open", r["line"], "",
         f"{r['sportsbook']} (as recorded by the dataset; expansion not documented upstream)",
         DATASET_INITIAL_URL)

open_close_games = 0
spread_moves: list[float] = []
total_moves: list[float] = []
open_only_games = 0
for about, sides in sorted(open_2021.items()):
    # games.csv in this pinned commit uses the alt format ("2021_01_DAL_TB") as game_id for 2021,
    # so the about key joins directly and exactly.
    gid = about if about in games_by_id else None
    if not gid:
        open_only_games += 1
        continue
    g = games_by_id[gid]
    _, _, away, home = about.split("_")
    if not g["spread_line"]:
        open_only_games += 1
        continue
    open_close_games += 1
    # WSGT rows are side-specific: the HOME side's row (l_h) means the home team gives |l_h| when
    # negative; the home-margin line (positive = home favoured) is -l_h. The AWAY row equals -l_h
    # exactly, asserted below.
    assert abs(sides[f"SPREAD|{away}"] + sides[f"SPREAD|{home}"]) < 1e-9, f"WSGT sides disagree: {about}"
    home_open = -sides[f"SPREAD|{home}"]
    home_close = float(g["spread_line"])
    spread_moves.append(home_close - home_open)
    tot_open = sides["TOTAL|Over"]
    tot_close = float(g["total_line"]) if g["total_line"] else ""
    if tot_close != "":
        total_moves.append(tot_close - tot_open)
assert open_only_games == 0, f"{open_only_games} 2021 opening-line games did not join to games.csv"

# close snapshots for every pinned game with a line
for g in games:
    if g["spread_line"]:
        snap(g["game_id"], g["season"], g["week"], g["gameday"], g["away_team"], g["home_team"],
             "SPREAD", "HOME-MARGIN-LINE", "close", g["spread_line"], "", "closing line as recorded by the dataset",
             DATASET_SPREAD_URL)
    if g["total_line"]:
        snap(g["game_id"], g["season"], g["week"], g["gameday"], g["away_team"], g["home_team"],
             "TOTAL", "BOTH-SIDES", "close", g["total_line"], "", "closing line as recorded by the dataset",
             DATASET_SPREAD_URL)
    if g["home_moneyline"]:
        snap(g["game_id"], g["season"], g["week"], g["gameday"], g["away_team"], g["home_team"],
             "MONEYLINE", g["home_team"], "close", "", g["home_moneyline"], "closing price as recorded by the dataset",
             DATASET_SPREAD_URL)
        snap(g["game_id"], g["season"], g["week"], g["gameday"], g["away_team"], g["home_team"],
             "MONEYLINE", g["away_team"], "close", "", g["away_moneyline"], "closing price as recorded by the dataset",
             DATASET_SPREAD_URL)

# fair snapshots: the markets we originate
def american_from_p(p: float) -> int:
    if p >= 0.5:
        return int(round(-100.0 * p / (1.0 - p)))
    return int(round(100.0 * (1.0 - p) / p))


fair_games = 0
for r in model:
    fair_games += 1
    fair_p = 0.5 * (1.0 + math.erf((-float(r["model_spread"]) / SIGMA) / math.sqrt(2.0)))
    snap(r["game_id"], r["season"], r["week"], r["gameday"], r["away_team"], r["home_team"],
         "SPREAD", "MODEL-FAIR", "fair", r["model_spread"], "", "this repository's model (variant B)", DATASET_MODEL_URL)
    snap(r["game_id"], r["season"], r["week"], r["gameday"], r["away_team"], r["home_team"],
         "TOTAL", "MODEL-FAIR", "fair", r["model_total"], "", "this repository's model (variant B)", DATASET_MODEL_URL)
    snap(r["game_id"], r["season"], r["week"], r["gameday"], r["away_team"], r["home_team"],
         "MONEYLINE", "HOME-FAIR-DERIVED", "fair", f"{fair_p:.6f}", str(american_from_p(fair_p)),
         f"derived: P(home win) = Phi(-model_spread/{SIGMA:.3f})", DATASET_MODEL_URL)

for r in upcoming:
    snap(r["game_id"], r["season"], r["week"], r["gameday"], r["away_team"], r["home_team"],
         "SPREAD", "MODEL-FAIR", "fair", r["own_spread"], "", "this repository's originated line", DATASET_UPCOMING_URL)
    snap(r["game_id"], r["season"], r["week"], r["gameday"], r["away_team"], r["home_team"],
         "TOTAL", "MODEL-FAIR", "fair", r["own_total"], "", "this repository's originated line", DATASET_UPCOMING_URL)

with (OUT / "snapshots.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(snap_rows[0].keys()))
    w.writeheader()
    w.writerows(snap_rows)

# --------------------------------------------------------------------------- #
# 2. origination ledger — fair line, market line, difference as separate columns
# --------------------------------------------------------------------------- #
ledger: list[dict] = []


def norm_line(x: str) -> str:
    return x.strip()


ledger_rows = 0
for r in model:
    g = games_by_id[r["game_id"]]
    fair_spread = round(float(r["model_spread"]), 2)
    fair_total = round(float(r["model_total"]), 2)
    mkt_spread = float(r["mkt_spread"]) if norm_line(r["mkt_spread"]) else None
    mkt_total = float(r["mkt_total"]) if norm_line(r["mkt_total"]) else None
    fair_p = 0.5 * (1.0 + math.erf((fair_spread / SIGMA) / math.sqrt(2.0)))
    ml = g["home_moneyline"]
    mkt_ml_p = None
    if ml:
        o = float(ml)
        mkt_ml_p = (-o / (o - 100.0)) if o < 0 else (100.0 / (o + 100.0))
    completed = g["home_score"] != ""
    ledger_rows += 1
    ledger.append({
        "game_id": r["game_id"], "season": r["season"], "week": r["week"], "gameday": r["gameday"],
        "away_team": r["away_team"], "home_team": r["home_team"], "completed": "yes" if completed else "no",
        "order_side": "1", "fair_spread": f"{fair_spread:.2f}",
        "market_close_spread": f"{mkt_spread:.2f}" if mkt_spread is not None else "",
        "diff_spread": f"{fair_spread - mkt_spread:.2f}" if mkt_spread is not None else "",
        "order_total": "2", "fair_total": f"{fair_total:.2f}",
        "market_close_total": f"{mkt_total:.2f}" if mkt_total is not None else "",
        "diff_total": f"{fair_total - mkt_total:.2f}" if mkt_total is not None else "",
        "order_moneyline": "3", "fair_ml_home_prob": f"{1.0 - fair_p:.6f}",
        "fair_ml_home_odds": str(american_from_p(1.0 - fair_p)),
        "market_close_ml_home_odds": ml,
        "market_ml_home_implied_prob": f"{mkt_ml_p:.6f}" if mkt_ml_p is not None else "",
        "diff_ml_prob_points": f"{(1.0 - fair_p) - mkt_ml_p:.6f}" if mkt_ml_p is not None else "",
        "tier": "recomputed", "source_url": DATASET_MODEL_URL,
    })

for r in upcoming:
    mkt_spread = float(r["market_spread_if_posted"]) if norm_line(r["market_spread_if_posted"]) else None
    mkt_total = float(r["market_total_if_posted"]) if norm_line(r["market_total_if_posted"]) else None
    fair_spread = round(float(r["own_spread"]), 2)
    fair_total = round(float(r["own_total"]), 2)
    fair_p = 0.5 * (1.0 + math.erf((fair_spread / SIGMA) / math.sqrt(2.0)))
    ledger_rows += 1
    ledger.append({
        "game_id": r["game_id"], "season": r["season"], "week": r["week"], "gameday": r["gameday"],
        "away_team": r["away_team"], "home_team": r["home_team"], "completed": "no",
        "order_side": "1", "fair_spread": f"{fair_spread:.2f}",
        "market_close_spread": f"{mkt_spread:.2f}" if mkt_spread is not None else "",
        "diff_spread": f"{fair_spread - mkt_spread:.2f}" if mkt_spread is not None else "",
        "order_total": "2", "fair_total": f"{fair_total:.2f}",
        "market_close_total": f"{mkt_total:.2f}" if mkt_total is not None else "",
        "diff_total": f"{fair_total - mkt_total:.2f}" if mkt_total is not None else "",
        "order_moneyline": "3", "fair_ml_home_prob": f"{1.0 - fair_p:.6f}",
        "fair_ml_home_odds": str(american_from_p(1.0 - fair_p)),
        "market_close_ml_home_odds": "",
        "market_ml_home_implied_prob": "",
        "diff_ml_prob_points": "",
        "tier": "recomputed", "source_url": DATASET_UPCOMING_URL,
    })

with (OUT / "origination_ledger.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(ledger[0].keys()))
    w.writeheader()
    w.writerows(ledger)

# --------------------------------------------------------------------------- #
# 3. verified results feed
# --------------------------------------------------------------------------- #
official_rows: list[dict] = []
pin_missing = 0
match_ok = 0
mismatch: list[str] = []
for wk, wkdata in sorted(official["weeks"].items(), key=lambda kv: int(kv[0])):
    for gm in wkdata["games"]:
        key_away, key_home = gm["away"], gm["home"]
        pin = next((g for g in games if g["season"] == "2026" and g["week"] == wk
                    and g["away_team"] == key_away and g["home_team"] == key_home), None)
        in_pin = pin is not None and pin["home_score"] != ""
        status = "match" if in_pin else "pin-missing"
        if in_pin:
            if (int(pin["away_score"]) == gm["away_score"] and int(pin["home_score"]) == gm["home_score"]):
                match_ok += 1
            else:
                status = "MISMATCH"
                mismatch.append(f"{pin['game_id']}")
                pin_missing += 0
        else:
            pin_missing += 1
        official_rows.append({
            "season": "2026", "week": wk, "gameday": "", "away_team": key_away, "home_team": key_home,
            "away_score": gm["away_score"], "home_score": gm["home_score"],
            "total": gm["away_score"] + gm["home_score"],
            "home_margin": gm["home_score"] - gm["away_score"],
            "in_pinned_feed": "yes" if in_pin else "no",
            "match_status": status,
            "tier": "official", "source_url": wkdata["source_url"], "game_url": gm["game_url"],
            "checked_utc": CHECKED,
        })
assert not mismatch, f"official transcription disagrees with pinned feed: {mismatch}"

with (OUT / "results_feed_2026.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(official_rows[0].keys()))
    w.writeheader()
    w.writerows(official_rows)

hist_rows: list[dict] = []
for g in games:
    if g["home_score"] == "":
        continue
    hist_rows.append({
        "game_id": g["game_id"], "season": g["season"], "week": g["week"], "gameday": g["gameday"],
        "away_team": g["away_team"], "home_team": g["home_team"], "away_score": g["away_score"],
        "home_score": g["home_score"], "total": g["total"], "home_margin": g["result"],
        "market_close_spread_home": g["spread_line"], "market_close_total": g["total_line"],
        "market_close_ml_home": g["home_moneyline"], "market_close_ml_away": g["away_moneyline"],
        "tier": "dataset", "source_url": DATASET_SPREAD_URL,
    })
with (OUT / "results_history.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(hist_rows[0].keys()))
    w.writeheader()
    w.writerows(hist_rows)

# --------------------------------------------------------------------------- #
# 4. leaderboard — signal separated from staking
# --------------------------------------------------------------------------- #
KELLY_CAP = 0.02  # documented staking variant: fractional Kelly, capped at 2% of bankroll per bet


def decimal_odds(price: str) -> float:
    p = float(price)
    return (1.0 + 100.0 / (-p)) if p < 0 else (1.0 + p / 100.0)


strat: dict[str, dict] = {}
for r in bets:
    s = strat.setdefault(r["strategy_id"], {
        "strategy_id": r["strategy_id"], "name": r["strategy_name"], "markets": set(),
        "n": 0, "wins": 0, "pnl": 0.0, "kelly_units": 1.0, "peak": 1.0, "maxdd": 0.0,
        "edge_sum": 0.0, "flat_path": 0.0, "flat_peak": 0.0, "flat_maxdd": 0.0,
    })
    n = s["n"] + 1
    win = int(r["outcome"])
    pnl = float(r["pnl"])
    dec = decimal_odds(r["price"]) if norm_line(r["price"]) else None
    p = float(r["model_prob"]) if norm_line(r["model_prob"]) else None
    kelly_pnl_units = 0.0
    if dec is not None and p is not None:
        b = dec - 1.0
        f_star = (p * b - (1.0 - p)) / b
        f = max(0.0, min(KELLY_CAP, f_star))
        kelly_pnl_units = f * (b if win == 1 else -1.0)
    s["markets"].add(r["market"])
    s["n"] = n
    s["wins"] += win
    s["pnl"] += pnl
    s["kelly_units"] *= (1.0 + kelly_pnl_units)
    s["peak"] = max(s["peak"], s["kelly_units"])
    s["maxdd"] = max(s["maxdd"], s["peak"] - s["kelly_units"])
    s["edge_sum"] += float(r["edge"]) if norm_line(r["edge"]) else 0.0
    s["flat_path"] += pnl
    s["flat_peak"] = max(s["flat_peak"], s["flat_path"])
    s["flat_maxdd"] = max(s["flat_maxdd"], s["flat_peak"] - s["flat_path"])

lb_rows = []
for sid in sorted(strat):
    s = strat[sid]
    lb_rows.append({
        "strategy_id": s["strategy_id"], "strategy_name": s["name"],
        "markets": "+".join(sorted(s["markets"])), "n_bets": s["n"],
        "signal_hit_rate": f"{s['wins'] / s['n']:.6f}",
        "signal_mean_edge": f"{s['edge_sum'] / s['n']:.6f}",
        "signal_flat_roi": f"{s['pnl'] / s['n']:.6f}",
        "signal_flat_pnl_units": f"{s['pnl']:.2f}",
        "signal_flat_max_drawdown_units": f"{s['flat_maxdd']:.2f}",
        "staking_variant": f"fractional Kelly, cap {int(KELLY_CAP * 100)}% of bankroll",
        "staking_growth_multiple": f"{s['kelly_units']:.4f}",
        "staking_roi_per_bet_pct_of_bankroll": f"{(s['kelly_units'] ** (1.0 / s['n']) - 1.0):.6f}",
        "staking_max_drawdown_frac": f"{s['maxdd'] / s['peak']:.4f}",
        "tier": "recomputed", "source_url": DATASET_BETS_URL,
    })
with (OUT / "leaderboard_signal_staking.csv").open("w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(lb_rows[0].keys()))
    w.writeheader()
    w.writerows(lb_rows)

# --------------------------------------------------------------------------- #
# 5. summary
# --------------------------------------------------------------------------- #
def mv_stats(vals: list[float]) -> dict:
    return {
        "n": len(vals),
        "mean_abs": round(st.mean(abs(v) for v in vals), 3),
        "median_abs": round(st.median(abs(v) for v in vals), 3),
        "moved_off_open": sum(1 for v in vals if abs(v) > 1e-9),
        "moved_3pt_or_more": sum(1 for v in vals if abs(v) >= 3),
        "max_abs": round(max(abs(v) for v in vals), 2),
        "mean_signed": round(st.mean(vals), 3),
    }


seasons_close = sorted({r["season"] for r in snap_rows if r["snapshot"] == "close" and r["market"] == "SPREAD"})
ml_seasons = sorted({r["season"] for r in snap_rows if r["snapshot"] == "close" and r["market"] == "MONEYLINE"})
upcoming_with_market = sum(1 for r in upcoming if norm_line(r["market_spread_if_posted"]))

summary = {
    "generated_from": "pinned nflverse/nfldata @ " + PIN + " + repo derived artifacts + official NFL.com pages opened " + CHECKED,
    "sigma_spread_rmse_variant": metrics["primary_variant"],
    "sigma_spread_rmse": SIGMA,
    "snapshots": {
        "rows_total": len(snap_rows),
        "open_rows": sum(1 for r in snap_rows if r["snapshot"] == "open"),
        "close_rows": sum(1 for r in snap_rows if r["snapshot"] == "close"),
        "fair_rows": sum(1 for r in snap_rows if r["snapshot"] == "fair"),
        "games_with_open_and_close": open_close_games,
        "close_seasons_spread": [seasons_close[0], seasons_close[-1]],
        "close_seasons_ml": [ml_seasons[0], ml_seasons[-1]],
        "open_season": "2021",
        "open_book_recorded_as": "WSGT (expansion not documented upstream — flagged)",
        "spread_movement_2021": mv_stats(spread_moves),
        "total_movement_2021": mv_stats(total_moves),
    },
    "origination_ledger": {
        "rows": ledger_rows,
        "model_rows": len(model),
        "upcoming_rows": len(upcoming),
        "upcoming_with_market_line": upcoming_with_market,
        "order": ["side (spread)", "total", "moneyline"],
        "fair_ml_derivation": f"P(home win) = Phi(-fair_spread/{SIGMA:.3f}); sigma = the model's own measured spread RMSE (variant {metrics['primary_variant']}, model_metrics.json)",
    },
    "results_feed": {
        "official_finals_checked": len(official_rows),
        "official_match_pinned": match_ok,
        "official_missing_from_pin": pin_missing,
        "history_rows": len(hist_rows),
        "history_seasons": [hist_rows[0]["season"], hist_rows[-1]["season"]],
        "week5_ties": sum(1 for r in official_rows if r["week"] == "5" and r["away_score"] == r["home_score"]),
    },
    "leaderboard": {
        "strategies": len(lb_rows),
        "reward_eligible_signal": sum(1 for r in lb_rows if float(r["signal_flat_roi"]) > 0 and r["strategy_id"] != ""),
        "positive_flat_roi": [r["strategy_id"] for r in lb_rows if float(r["signal_flat_roi"]) > 0],
        "kelly_cap": KELLY_CAP,
    },
}
(OUT / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")

print("price_lab data build OK")
print(json.dumps(summary, indent=1))
