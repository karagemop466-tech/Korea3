#!/usr/bin/env python3
"""Build the skill_lab pages from the repository's pinned artifacts.

Deterministic: output depends only on the input files (SHA-256 stamped on the
pages). No wall clock is read, so two builds on the same inputs are
byte-identical. Run `python3 -m skill_lab.build` (or `python3 skill_lab/build.py`).

Inputs (all read-only):
  data/derived/bets.csv       per-bet ledger, probabilities and settlement (line_lab)
  data/derived/summary.json   protocol constants + pinned nflverse commit + leaderboard
  data/raw/closing_lines.csv  pinned nflverse closing lines (control universe)
  data/raw/games.csv          pinned nflverse scores (settlement of control bets)

Outputs:
  skill_lab/data/skill_table.json, controls.json, flags.json, meta.json
  skill_lab/index.html, method.html, flagged.html
"""
from __future__ import annotations

import csv
import hashlib
import html
import json
import math
import sys
from pathlib import Path
from urllib.parse import quote

import numpy as np

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from skill_lab import core
else:
    from . import core

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
BETS = ROOT / "data" / "derived" / "bets.csv"
SUMMARY = ROOT / "data" / "derived" / "summary.json"
CLOSING = ROOT / "data" / "raw" / "closing_lines.csv"
GAMES = ROOT / "data" / "raw" / "games.csv"
DATA = HERE / "data"

REPO = "https://github.com/karagemop466-tech/Korea3"
BLOB = REPO + "/blob/main/"
SEED = core.SEED
N_BOOT = core.N_BOOT

CTRL_WINDOW = (2006, 2025)  # pre-registered control universe window (protocol window)


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def e(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def fnum(x, d=4):
    if x is None:
        return None
    if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
        return None
    return round(float(x), d)


def pct(x, d=2):
    return None if x is None else round(100.0 * float(x), d)


def fcell(x, d=4, signed=False):
    """Format a float cell; None renders as a blank marker (never zero)."""
    if x is None:
        return '<span class="blank">—</span>'
    s = f"{float(x):+.{d}f}" if signed else f"{float(x):.{d}f}"
    return s


# --------------------------------------------------------------------------- #
# Load the ledger
# --------------------------------------------------------------------------- #
def load_bets() -> list[dict]:
    out = []
    with BETS.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            mp = r["model_prob"]
            kp = r["market_prob"]
            out.append({
                "strategy_id": r["strategy_id"],
                "strategy_name": r["strategy_name"],
                "market": r["market"],
                "season": int(r["season"]),
                "week": int(r["week"]),
                "game_id": r["game_id"],
                "side": r["side"],
                "line": r["line"],
                "price": float(r["price"]) if r["price"] else None,
                "model_prob": float(mp) if mp else None,
                "market_prob": float(kp) if kp else None,
                "edge": float(r["edge"]) if r["edge"] else None,
                "outcome": int(float(r["outcome"])),
                "pnl": float(r["pnl"]) if r["pnl"] else 0.0,
            })
    return out


def strategy_rows(bets: list[dict]) -> dict[str, dict]:
    """Score every ranked single-bet strategy (rules R2-R5, R7)."""
    rows: dict[str, dict] = {}
    p_fam: dict[str, float | None] = {}
    for sid in core.SINGLES:
        sub = [b for b in bets if b["strategy_id"] == sid]
        name = sub[0]["strategy_name"] if sub else sid
        market = sub[0]["market"] if sub else ""
        scored = [b for b in sub if b["model_prob"] is not None and b["outcome"] != 0]
        p_m = np.array([b["model_prob"] for b in scored], float)
        p_k = np.array([b["market_prob"] for b in scored], float)
        y = np.array([1.0 if b["outcome"] > 0 else 0.0 for b in scored])
        gk = [b["game_id"] for b in scored]
        wk = [(b["season"], b["week"]) for b in scored]

        bs_model = core.brier(p_m, y) if len(y) else None
        bench_p = {
            "market": p_k,
            "coin": np.full(len(y), 0.5),
            "favourite": core.favourite_prob(p_k) if len(y) else p_k,
        }
        bs = {k: (core.brier(v, y) if len(y) else None) for k, v in bench_p.items()}
        # game and week clusterings; paired resamples across benchmarks
        game = (core.bootstrap_bss_multi(p_m, bench_p, y, gk, N_BOOT, SEED)
                if len(y) else None)
        week = (core.bootstrap_bss_multi(p_m, bench_p, y, wk, N_BOOT, SEED)
                if len(y) else None)

        row = {
            "id": sid, "name": name, "market": market,
            "n_bets": len(sub),
            "n_pushes": sum(1 for b in sub if b["outcome"] == 0),
            "n_no_prob": sum(1 for b in sub if b["model_prob"] is None),
            "n_scored": len(scored),
            "bs_model": fnum(bs_model),
            "bs_market": fnum(bs["market"]),
            "bs_coin": fnum(bs["coin"]),
            "bs_favourite": fnum(bs["favourite"]),
        }
        if game is not None and len(y):
            for k in bench_p:
                gb, wb_ = game[k], week[k]
                low_g, low_w = gb["ci_low"], wb_["ci_low"]
                # more conservative (lower) of the two 2.5th-percentile bounds
                lows = [x for x in (low_g, low_w) if x is not None]
                bound = min(lows) if lows else None
                if k == "market":
                    ps = [x for x in (gb["p"], wb_["p"]) if x is not None]
                    row["ranking_p"] = max(ps) if ps else None
                    row["ranking_bound"] = fnum(bound)
                    se_c = [gb["se"], wb_["se"]]
                    se_c = [s for s in se_c if s is not None]
                    row["se_conservative"] = fnum(max(se_c)) if se_c else None
                    cm = core.change_mind(
                        gb["point"], max([s for s in (gb["se"], wb_["se"]) if s is not None], default=None),
                        len(scored), bound)
                    row["confirm_more_bets"] = cm["confirm_more_bets"]
                    row["overturn_level"] = fnum(cm["overturn_level"])
                    row["eligible_now"] = bool(bound is not None and bound > 0)
                row[f"bss_{k}"] = fnum(gb["point"])
                row[f"low_{k}_game"] = fnum(low_g)
                row[f"low_{k}_week"] = fnum(low_w)
                row[f"high_{k}_game"] = fnum(gb["ci_high"])
                row[f"high_{k}_week"] = fnum(wb_["ci_high"])
                row[f"p_{k}_game"] = fnum(gb["p"], 4)
                row[f"p_{k}_week"] = fnum(wb_["p"], 4)
                row[f"se_{k}_game"] = fnum(gb["se"])
                row[f"se_{k}_week"] = fnum(wb_["se"])
        rows[sid] = row
        p_fam[sid] = row.get("ranking_p")

    qvals = core.bh_fdr(p_fam, core.FDR_Q)
    for sid, r in rows.items():
        r["q_skill"] = fnum(qvals.get(sid), 4)
        if r.get("ranking_p") is not None:
            r["bonf_threshold"] = round(0.05 / len(core.SINGLES), 5)
            r["bonf_pass"] = bool(r["ranking_p"] <= 0.05 and r["ranking_p"] <= r["bonf_threshold"])
        else:
            r["bonf_pass"] = None
        if r.get("ranking_bound") is not None and r.get("q_skill") is not None:
            r["eligible"] = bool(r["ranking_bound"] > 0 and r["q_skill"] <= core.FDR_Q)
        else:
            r["eligible"] = None
    return rows


# --------------------------------------------------------------------------- #
# Global control baselines (R6) over the pinned closing-line universe
# --------------------------------------------------------------------------- #
def load_games() -> dict[str, dict]:
    out = {}
    with GAMES.open(newline="", encoding="utf-8") as fh:
        for g in csv.DictReader(fh):
            try:
                hs, as_ = int(float(g["home_score"])), int(float(g["away_score"]))
            except (ValueError, KeyError):
                continue
            out[g["game_id"]] = {"home": g["home_team"], "away": g["away_team"],
                                 "hs": hs, "as": as_}
    return out


def load_closing() -> dict[tuple, dict]:
    """(alt_game_id, type) -> list of side rows."""
    out: dict[tuple, dict] = {}
    with CLOSING.open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            key = (r["alt_game_id"], r["type"])
            out.setdefault(key, {"sides": [], "nflverse_outcome_ok": None})
            out[key]["sides"].append({
                "side": r["side"], "line": r["line"], "odds": r["odds"],
                "outcome_col": r["outcome"],
            })
    return out


def settle(market: str, side: str, line: float | None, g: dict) -> int | None:
    """Settlement from pinned scores: 1 win, 0 loss, 2 push. None = undecidable."""
    if market == "MONEYLINE":
        won = g["hs"] > g["as"] if side == g["home"] else g["as"] > g["hs"]
        if g["hs"] == g["as"]:
            return 2  # tie: moneyline pushes (nflverse records 0.5)
        return 1 if won else 0
    if market == "SPREAD":
        pts = g["hs"] if side == g["home"] else g["as"]
        opp = g["as"] if side == g["home"] else g["hs"]
        diff = pts + line - opp
        return 1 if diff > 0 else (2 if diff == 0 else 0)
    if market == "TOTAL":
        tot = g["hs"] + g["as"]
        over = side == "Over"
        if tot == line:
            return 2
        if over:
            return 1 if tot > line else 0
        return 1 if tot < line else 0
    raise ValueError(market)


FALLBACK_PRICE = -110.0  # repo's documented price fallback where no odds exist


def season_week_of(alt_id: str):
    parts = alt_id.split("_")
    if len(parts) >= 3:
        try:
            return int(parts[0]), int(parts[1])
        except ValueError:
            return None
    return None


def validate_outcome_column(games: dict, closing: dict) -> dict:
    """Cross-check the dataset's own outcome column against recomputed settlement
    over every recorded row of closing_lines.csv (not just the priced subset)."""
    agree = {"SPREAD": [0, 0], "TOTAL": [0, 0], "MONEYLINE": [0, 0]}
    mismatch = {"SPREAD": [], "TOTAL": [], "MONEYLINE": []}
    for (gid, mtype), rec in closing.items():
        g = games.get(gid)
        if g is None:
            continue
        for s in rec["sides"]:
            col = s["outcome_col"]
            if col not in ("1", "0", "0.5"):
                continue
            line = float(s["line"]) if s["line"] else None
            if mtype in ("SPREAD", "TOTAL") and line is None:
                continue
            res = settle(mtype, s["side"], line, g)
            if res is None:
                continue
            col_val = {"1": 1, "0": 0, "0.5": 2}[col]
            agree[mtype][1] += 1
            if col_val == res:
                agree[mtype][0] += 1
            elif len(mismatch[mtype]) < 100:
                mismatch[mtype].append({
                    "game": gid, "side": s["side"], "line": s["line"],
                    "odds": s["odds"], "nflverse": col,
                    "recomputed": {0: "loss", 1: "win", 2: "push"}[res],
                })
    return {"agree": agree, "mismatch": mismatch}


def control_universe_a(games: dict, closing: dict) -> dict:
    """Universe A: events where BOTH sides carry closing odds (de-vig possible).

    SPREAD/TOTAL odds exist only for part of the pinned window; that restriction
    is published as the universe definition, never hidden.
    """
    events = {"SPREAD": [], "TOTAL": [], "MONEYLINE": []}
    for (gid, mtype), rec in closing.items():
        sw = season_week_of(gid)
        if sw is None or not (CTRL_WINDOW[0] <= sw[0] <= CTRL_WINDOW[1]):
            continue
        g = games.get(gid)
        if g is None:
            continue
        sides = rec["sides"]
        if len(sides) != 2:
            continue
        if any(s["odds"] == "" for s in sides):
            continue
        if mtype in ("SPREAD", "TOTAL") and any(s["line"] == "" for s in sides):
            continue
        settled = []
        for s in sides:
            line = float(s["line"]) if s["line"] else None
            res = settle(mtype, s["side"], line, g)
            if res is None:
                settled = []
                break
            settled.append((s, res))
        if not settled:
            continue
        p1, _p2 = core.devig_two_way(float(settled[0][0]["odds"]),
                                     float(settled[1][0]["odds"]))
        events[mtype].append({
            "gid": gid, "season": sw[0], "week": sw[1],
            "side0": settled[0][0]["side"], "side1": settled[1][0]["side"],
            "price0": float(settled[0][0]["odds"]), "price1": float(settled[1][0]["odds"]),
            "line0": settled[0][0]["line"], "line1": settled[1][0]["line"],
            "r0": settled[0][1], "r1": settled[1][1], "p0": p1, "p1": 1 - p1,
            "imputed": 0,
        })
    return events


def load_preds() -> list[dict]:
    out = []
    with (ROOT / "data" / "derived" / "model_predictions.csv").open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            try:
                out.append({
                    "game_id": r["game_id"], "season": int(r["season"]),
                    "week": int(r["week"]),
                    "home": r["home_team"], "away": r["away_team"],
                    "hs": r["home_score"], "as_": r["away_score"],
                    "mkt_spread": float(r["mkt_spread"]) if r["mkt_spread"] else None,
                    "mkt_total": float(r["mkt_total"]) if r["mkt_total"] else None,
                })
            except (ValueError, KeyError):
                continue
    return out


def control_universe_b(games: dict, preds: list[dict]) -> dict:
    """Universe B: every 2006-2025 game with a market spread/total line in the
    pinned modelling table, priced at the repo's documented -110 fallback
    (imputed share = 1.0, published). No odds exist here, so a de-vigged
    majority forecast is impossible: majority mode = favourite by line sign,
    and only its win rate and ROI are meaningful."""
    events = {"SPREAD": [], "TOTAL": []}
    score_mismatch = 0
    score_checked = 0
    for p in preds:
        if not (CTRL_WINDOW[0] <= p["season"] <= CTRL_WINDOW[1]):
            continue
        g = games.get(p["game_id"])
        if g is None:
            continue
        try:
            hs_p, as_p = int(float(p["hs"])), int(float(p["as_"]))
        except (ValueError, KeyError, TypeError):
            hs_p, as_p = None, None
        if hs_p is not None:
            score_checked += 1
            if hs_p != g["hs"] or as_p != g["as"]:
                score_mismatch += 1
        gg = {"home": g["home"], "away": g["away"], "hs": g["hs"], "as": g["as"]}
        if p["mkt_spread"] is not None:
            res_h = settle("SPREAD", g["home"], p["mkt_spread"], gg)
            res_a = settle("SPREAD", g["away"], -p["mkt_spread"], gg)
            if res_h is not None and res_a is not None:
                events["SPREAD"].append({
                    "gid": p["game_id"], "season": p["season"], "week": p["week"],
                    "side0": g["home"], "side1": g["away"],
                    "price0": FALLBACK_PRICE, "price1": FALLBACK_PRICE,
                    "line0": p["mkt_spread"], "line1": -p["mkt_spread"],
                    "r0": res_h, "r1": res_a, "p0": None, "p1": None, "imputed": 1,
                })
        if p["mkt_total"] is not None:
            res_o = settle("TOTAL", "Over", p["mkt_total"], gg)
            res_u = settle("TOTAL", "Under", p["mkt_total"], gg)
            if res_o is not None and res_u is not None:
                events["TOTAL"].append({
                    "gid": p["game_id"], "season": p["season"], "week": p["week"],
                    "side0": "Over", "side1": "Under",
                    "price0": FALLBACK_PRICE, "price1": FALLBACK_PRICE,
                    "line0": p["mkt_total"], "line1": p["mkt_total"],
                    "r0": res_o, "r1": res_u, "p0": None, "p1": None, "imputed": 1,
                })
    return {"events": events, "score_mismatch": score_mismatch,
            "score_checked": score_checked}


def control_metrics(evts: list[dict], mode: str) -> dict:
    """Metrics for one control over one universe slice. mode: majority|random."""
    rng = np.random.default_rng(SEED)  # one seeded realisation (R6)
    pnls, decided_p, decided_y = [], [], []
    wk = []
    n_push = 0
    n_wins = 0
    for evk in evts:
        if mode == "majority":
            if evk["p0"] is not None:
                pick = 0 if evk["p0"] >= evk["p1"] else 1
                forecast = max(evk["p0"], evk["p1"])
            else:  # universe B: favourite by line sign
                pick = 0 if evk["line0"] < 0 else 1
                forecast = None
        else:
            pick = int(rng.integers(0, 2))
            forecast = 0.5
        r = evk[f"r{pick}"]
        price = evk[f"price{pick}"]
        pnls.append(core.pnl(price, 1 if r == 1 else (0 if r == 2 else -1)))
        if r != 2:
            n_wins += 1 if r == 1 else 0
            if forecast is not None:
                decided_p.append(forecast)
                decided_y.append(1.0 if r == 1 else 0.0)
        else:
            n_push += 1
        wk.append((evk["season"], evk["week"]))
    roi = core.roi_ci(pnls, wk, N_BOOT, SEED) if pnls else {}
    bs = core.brier(np.array(decided_p), np.array(decided_y)) if decided_p else None
    bs_coin = core.brier(np.full(len(decided_y), 0.5), np.array(decided_y)) if decided_y else None
    return {
        "mode": mode,
        "n_events": len(evts),
        "n_pushes": n_push,
        "n_decided": len(decided_y) + n_push,
        "wins": n_wins,
        "win_rate": fnum(n_wins / (n_wins + (len(evts) - n_push - n_wins)), 4)
        if (n_wins + (len(evts) - n_push - n_wins)) else None,
        "imputed_share": fnum(sum(ev["imputed"] for ev in evts) / len(evts), 4) if evts else None,
        "roi": fnum(roi.get("point")),
        "roi_pct": pct(roi.get("point")),
        "roi_ci_low": fnum(roi.get("ci_low")),
        "roi_ci_high": fnum(roi.get("ci_high")),
        "roi_p": fnum(roi.get("p"), 4),
        "bs": fnum(bs),
        "bs_coin": fnum(bs_coin),
        "bss_vs_coin": fnum(core.bss(bs, bs_coin) if bs is not None and bs_coin else None),
    }


# --------------------------------------------------------------------------- #
# Unranked ledger rows (combos, futures) and the backtest ledger
# --------------------------------------------------------------------------- #
def combo_futures_rows(bets: list[dict]) -> list[dict]:
    out = []
    for sid in core.COMBOS + [core.FUTURES]:
        sub = [b for b in bets if b["strategy_id"] == sid]
        if not sub:
            continue
        wk = [(b["season"], b["week"]) for b in sub]
        roi = core.roi_ci([b["pnl"] for b in sub], wk, N_BOOT, SEED)
        out.append({
            "id": sid, "name": sub[0]["strategy_name"], "market": sub[0]["market"],
            "n_bets": len(sub),
            "n_no_prob": sum(1 for b in sub if b["model_prob"] is None),
            "roi": fnum(roi.get("point")), "roi_pct": pct(roi.get("point")),
            "roi_ci_low": fnum(roi.get("ci_low")),
            "roi_ci_high": fnum(roi.get("ci_high")),
            "roi_p": fnum(roi.get("p"), 4),
            "seasons": len(set(b["season"] for b in sub)),
        })
    return out


def backtest_ledger(summary: dict) -> list[dict]:
    out = []
    for entry in summary.get("leaderboard", []):
        out.append({
            "id": entry.get("id"), "name": entry.get("name"),
            "market": entry.get("market"),
            "bets": entry.get("bets"), "seasons": entry.get("seasons"),
            "full_roi": fnum(entry.get("full_roi")),
            "full_ci_low": fnum(entry.get("full_ci_low")),
            "holdout_roi": fnum(entry.get("holdout_roi")),
            "holdout_ci_low": fnum(entry.get("holdout_ci_low")),
            "gates_passed": entry.get("gates_passed"),
            "eligible": entry.get("eligible"),
            "brier_skill_published": fnum(entry.get("brier_skill")),
        })
    return out


# --------------------------------------------------------------------------- #
# Flags
# --------------------------------------------------------------------------- #
def build_flags(rows, ctrl, summary) -> list[dict]:
    mm = {k: len(v) for k, v in ctrl["mismatch"].items()}
    games_mm = sorted({m["game"] for v in ctrl["mismatch"].values() for m in v})
    return [
        {"id": "L01", "severity": "high", "status": "open",
         "title": "Parlay probabilities are products of leg marginals; combos stay unranked",
         "detail": ("S9/S10 model_prob values in bets.csv are np.prod of leg probabilities "
                    "(line_lab/strategies.py _add_parlays). Under dependence, the product is not "
                    "a joint probability, so the joint-evidence gate (C01) is not satisfied and "
                    "the combos are published unranked with skill columns blank."),
         "sources": [BLOB + "line_lab/strategies.py", BLOB + "data/derived/bets.csv"]},
        {"id": "L02", "severity": "medium", "status": "open",
         "title": "Futures strategy has no model probability; skill columns blank",
         "detail": (f"S11 (season win-total futures) rows in bets.csv carry market_prob but no "
                    f"model_prob, so no proper score can be computed. {sum(1 for b in load_bets() if b['strategy_id']=='S11')} ledger rows; "
                    "staking metrics only."),
         "sources": [BLOB + "data/derived/bets.csv"]},
        {"id": "L03", "severity": "medium", "status": "open",
         "title": "Strategy-ID collision across builds (audit flag X01)",
         "detail": ("data/derived/bets.csv uses S1-S11 (line_lab definitions) while "
                    "data/derived/gates_results.csv uses S01-S18 (pipeline definitions) with "
                    "different meanings. This lab scores only the bets.csv family and labels it "
                    "as such on every page; never score one ledger from the other."),
         "sources": [BLOB + "audit/line-by-line.md", BLOB + "data/derived/gates_results.csv"]},
        {"id": "L04", "severity": "medium", "status": "open",
         "title": "Benchmarks are the repository's pinned third-party dataset, not official league data",
         "detail": ("All inputs derive from the pinned nflverse/nfldata commit "
                    f"{summary.get('pinned_commit','')} (checksummed in data/derived/summary.json). "
                    "The NFL publishes no closing lines, prices or probability forecasts; every "
                    "'market' benchmark is therefore the pinned dataset's market, not an official "
                    "league number."),
         "sources": [f"https://github.com/nflverse/nfldata/blob/{summary.get('pinned_commit','')}/data/games.csv",
                     f"https://github.com/nflverse/nfldata/blob/{summary.get('pinned_commit','')}/data/closing_lines.csv"]},
        {"id": "L05", "severity": "low", "status": "open",
         "title": "CONTROL random is one seeded realisation, not a distribution",
         "detail": (f"Side draws use numpy default_rng seed {SEED}. A different seed draws a "
                    "different path; the row exists as a luck anchor (C04), not as an estimate."),
         "sources": [BLOB + "skill_lab/core.py"]},
        {"id": "L06", "severity": "low", "status": "open",
         "title": "Ranking uses one benchmark family; supplementary benchmarks are shown but not FDR-controlled",
         "detail": ("The multiplicity adjustment (BH q=0.10) is applied to the 8 p-values of the "
                    "ranking benchmark (market) only. Coin and favourite benchmark p-values are "
                    "published raw and labelled as outside the ranking family."),
         "sources": [BLOB + "skill_lab/method.html"]},
        {"id": "L07", "severity": "medium", "status": "open",
         "title": "nfl.com unreachable from this sandbox; no official league value republished",
         "detail": ("Outbound access is limited to GitHub/npm/PyPI, so no official NFL value was "
                    "re-read or republished by this lab. The capture/ pipeline (GitHub runners) is "
                    "the official-source channel; this lab consumes none of it."),
         "sources": [BLOB + "COORDINATION.md"]},
        {"id": "L08", "severity": "high", "status": "open",
         "title": f"Pinned closing-lines outcome column contradicts pinned scores on {mm['SPREAD']+mm['TOTAL']+mm['MONEYLINE']} rows",
         "detail": ("Recomputing settlement from data/raw/closing_lines.csv (line, odds) joined to "
                    "data/raw/games.csv (scores) disagrees with the outcome column of "
                    "closing_lines.csv itself on "
                    f"{mm['SPREAD']} SPREAD, {mm['TOTAL']} TOTAL and {mm['MONEYLINE']} MONEYLINE rows "
                    f"(of {sum(a[1] for a in nflverse_row_counts(ctrl))} with a recorded outcome). "
                    "Moneyline ties recorded as 0.5 are pushes and are treated as such; the "
                    "remaining rows flip the recorded winner of the bet. This lab settles control "
                    "bets from the pinned scores and publishes the agreement rate; the affected "
                    "rows are listed in skill_lab/data/flags.json (L08.mismatch_rows). The "
                    "line_lab ledger settles from scores too and is not affected."),
         "sources": [f"https://github.com/nflverse/nfldata/blob/{summary.get('pinned_commit','')}/data/closing_lines.csv",
                     f"https://github.com/nflverse/nfldata/blob/{summary.get('pinned_commit','')}/data/games.csv"]},
        {"id": "L11", "severity": "medium", "status": "open",
         "title": "Control universe B prices are 100% imputed at the documented -110 fallback",
         "detail": ("data/raw/closing_lines.csv carries closing odds only for part of the window "
                    "(moneylines throughout 2006-2018; spread/total odds only 2017-2018), so "
                    "universe A is restricted to priced events and published as such. To give the "
                    "favourite control full-window coverage, universe B prices every bet at the "
                    "flat -110 fallback documented in research/methodology.md. Its ROI is therefore "
                    "a standard-vig anchor, not a market-price outcome, and no de-vigged forecast "
                    "exists (Brier columns blank)."),
         "sources": [BLOB + "research/methodology.md",
                     f"https://github.com/nflverse/nfldata/blob/{summary.get('pinned_commit','')}/data/closing_lines.csv",
                     BLOB + "data/derived/model_predictions.csv"]},
        {"id": "L09", "severity": "medium", "status": "open",
         "title": "Pre-registration status of the ranked family is inherited, not new",
         "detail": ("S1-S11 were defined in line_lab's committed protocol before their evaluation "
                    "window closed for those builds; this lab adds scoring rules (R1-R7) fixed "
                    "before computing them, but the underlying strategies are not new "
                    "pre-registrations. Full pre-registration (A10) remains open on the readiness "
                    "register."),
         "sources": [BLOB + "line_lab/docs/preregistration.md", BLOB + "readiness/index.html"]},
        {"id": "L10", "severity": "medium", "status": "open",
         "title": "summary.json leaderboard publishes market-level brier_skill under per-strategy labels",
         "detail": ("In the leaderboard block of data/derived/summary.json, every TOTAL strategy "
                    "(S3, S7, S6) carries the identical brier_skill -0.019496..., every ATS strategy "
                    "(S1, S4, S5, S8) carries -0.031634..., and the ML strategy S2 carries "
                    "-0.038775... — the value is constant within market, so it is a market-level "
                    "estimate, not a per-strategy one. This lab's per-strategy BSS with bounds "
                    "supersedes it; the backtest ledger here quotes the published column verbatim "
                    "and labels it accordingly."),
         "sources": [BLOB + "data/derived/summary.json"]},
    ]


def nflverse_row_counts(ctrl) -> list[tuple[str, int]]:
    return [(k, v[1]) for k, v in ctrl["agree"].items()]


# --------------------------------------------------------------------------- #
# Pages
# --------------------------------------------------------------------------- #
NAV = [("index.html", "Skill leaderboard"), ("method.html", "Method"),
       ("flagged.html", "Flagged for Review")]


def page(title: str, active: str, body: str) -> str:
    links = []
    for h, t in NAV:
        cls = ' class="on"' if h == active else ""
        links.append(f'<a href="{h}"{cls}>{e(t)}</a>')
    nav = "".join(links)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · skill_lab</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="top">
  <div class="wrap">
    <div class="brand"><a href="../index.html">Korea3</a> <span>/ skill_lab · proper-score leaderboard</span></div>
    <nav>{nav}<a href="../index.html">Site home</a></nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="foot wrap">Deterministic build from pinned inputs — no clock is read. Recompute everything with
<code>python3 skill_lab/check.py</code>. Nothing on these pages is betting advice; no strategy here has
demonstrated skill at the required significance level.</footer>
</body>
</html>
"""


def src_cell(links: list[tuple[str, str]]) -> str:
    return "<td>" + " · ".join(f'<a href="{e(u)}">{e(t)}</a>' for t, u in links) + "</td>"


def blank(flag_id: str) -> str:
    return f'<span class="blank" title="not computed — see flagged.html#{e(flag_id)}">—</span><a class="flagref" href="flagged.html#{e(flag_id)}">⚠</a>'


def build_index(rows, ctrl, cm_rows, cf_rows, bt, flags, meta) -> str:
    # rank eligible-first by conservative bound
    ranked = sorted(
        [r for r in rows.values() if r.get("ranking_bound") is not None],
        key=lambda r: (-(r["ranking_bound"]), r.get("ranking_p") or 1))
    lead_rows = []
    for i, r in enumerate(ranked, 1):
        elig = r["eligible"]
        pill = '<span class="pill ok">eligible</span>' if elig else '<span class="pill bad">not eligible</span>'
        lead_rows.append(
            f"<tr><td>{i}</td>"
            f"<td><b>{e(r['id'])}</b> {e(r['name'])}</td>"
            f"<td>{e(r['market'])}</td>"
            f'<td class="num">{r["n_scored"]:,}</td>'
            f'<td class="num">{r["bs_model"]:.4f}</td>'
            f'<td class="num">{r["bs_market"]:.4f}</td>'
            f'<td class="num">{r["bss_market"]:+.4f}</td>'
            f'<td class="num">{r["low_market_week"]:+.4f}</td>'
            f'<td class="num">{r["low_market_game"]:+.4f}</td>'
            f'<td class="num">{r["ranking_p"]:.4f}</td>'
            f'<td class="num">{r["q_skill"]:.4f}</td>'
            f"<td>{pill}</td>"
            + src_cell([
                ("bets.csv", BLOB + "data/derived/bets.csv"),
                ("protocol", BLOB + "line_lab/docs/preregistration.md"),
                ("pinned dataset", f"https://github.com/nflverse/nfldata/blob/{meta['pinned_commit']}/data/games.csv"),
            ]) + "</tr>")
    lead_table = f"""<div class="card"><h2>Skill leaderboard — ranked by benchmark-relative Brier skill (C03)</h2>
<p class="sub">Ranking metric: Brier skill score against the <b>de-vigged market probability</b> on the strategy's
own scored events. Uncertainty: cluster bootstrap ({N_BOOT:,} resamples, seed {SEED}) — the week-cluster bound is the
ranking bound when it is the more conservative of the two. Multiplicity: Benjamini–Hochberg FDR at
q&nbsp;=&nbsp;{core.FDR_Q} across the {len(core.SINGLES)} ranked strategies. <b>Eligible</b> = lower bound &gt; 0 and
q ≤ {core.FDR_Q}. Pushes excluded from scoring; counts below. Win rate and ROI are deliberately absent here —
they live in the separated backtest ledger.</p>
<div class="scroll"><table>
<thead><tr><th>Rank</th><th>Strategy</th><th>Market</th><th>n scored</th><th>BS model</th><th>BS market</th>
<th>BSS vs market</th><th>Lower bound (week)</th><th>Lower bound (game)</th><th>p (one-sided)</th><th>q (BH)</th>
<th>Status</th><th>Source</th></tr></thead>
<tbody>{"".join(lead_rows)}</tbody></table></div>
<p class="sub">BS = Brier score (lower is better). BSS = 1 − BS_model/BS_market. p = share of bootstrap
resamples with BSS ≤ 0; the reported p is the larger (more conservative) of the week- and game-cluster
values. No strategy is eligible: every lower bound is ≤ 0, which is the honest current answer.</p></div>"""

    bench_rows = []
    for r in ranked:
        bench_rows.append(
            f"<tr><td><b>{e(r['id'])}</b></td>"
            f'<td class="num">{r["bss_market"]:+.4f}</td>'
            f'<td class="num">{r["low_market_game"]:+.4f}</td>'
            f'<td class="num">{r["bss_coin"]:+.4f}</td>'
            f'<td class="num">{r["low_coin_game"]:+.4f}</td>'
            f'<td class="num">{r["bss_favourite"]:+.4f}</td>'
            f'<td class="num">{r["low_favourite_game"]:+.4f}</td>'
            + src_cell([("bets.csv", BLOB + "data/derived/bets.csv")]) + "</tr>")
    bench_table = f"""<div class="card"><h2>Benchmark comparison (supplementary — outside the ranking family)</h2>
<p class="sub">Same scored events, same outcomes. <b>coin</b>: p = 0.5 on every event. <b>favourite</b>: the
majority-side probability on that event (p_market if ≥ 0.5, else 1 − p_market) — it answers "did this side
choice beat always taking the majority side?". Bounds shown are game-cluster 2.5th percentiles; the
p-values are <b>not</b> FDR-adjusted (flag L06).</p>
<div class="scroll"><table>
<thead><tr><th>Strategy</th><th>BSS vs market</th><th>bound (game)</th><th>BSS vs coin</th><th>bound (game)</th>
<th>BSS vs favourite</th><th>bound (game)</th><th>Source</th></tr></thead>
<tbody>{"".join(bench_rows)}</tbody></table></div></div>"""

    ctrl_rows = []
    label = {"SPREAD": "ATS (spread)", "TOTAL": "Totals (over/under)", "MONEYLINE": "Moneyline"}
    uni_label = {
        "A": f"A · closing-priced events (both odds present)",
        "B": f"B · every game with a market line, flat {meta['fallback_price']:.0f} fallback (flag L11)",
    }
    for key in sorted(ctrl["metrics"]):
        uni, mtype, mode = key.split(":")
        m = ctrl["metrics"][key]
        tag = "CONTROL majority side" if mode == "majority" else "CONTROL random picks"
        bs_cell = (f'<td class="num">{fcell(m["bs"])}</td><td class="num">{fcell(m["bss_vs_coin"], signed=True)}</td>')
        ctrl_rows.append(
            f"<tr><td>{e(uni_label[uni])}</td><td>{e(label.get(mtype, mtype))}</td><td>{e(tag)}</td>"
            f'<td class="num">{m["n_events"]:,}</td>'
            f'<td class="num">{m["n_decided"]:,}</td>'
            f'<td class="num">{fcell(m["win_rate"])}</td>'
            f'<td class="num">{fcell(m["imputed_share"])}</td>'
            f'<td class="num">{fcell(m["roi_pct"], 2, signed=True)}%</td>'
            f'<td class="num">{fcell(m["roi_ci_low"], 4, signed=True)}</td>'
            f'<td class="num">{fcell(m["roi_ci_high"], 4, signed=True)}</td>'
            f'<td class="num">{fcell(m["roi_p"])}</td>'
            + bs_cell
            + src_cell([
                ("closing_lines.csv", f"https://github.com/nflverse/nfldata/blob/{meta['pinned_commit']}/data/closing_lines.csv"),
                ("games.csv", f"https://github.com/nflverse/nfldata/blob/{meta['pinned_commit']}/data/games.csv"),
                ("model_predictions.csv", BLOB + "data/derived/model_predictions.csv"),
            ]) + "</tr>")
    agree = ctrl["agree"]
    agree_line = (" · ".join(
        f"{k}: {v[0]}/{v[1]}" for k, v in agree.items()))
    score_line = (f'model_predictions score columns agree with games.csv on '
                  f'{ctrl["universe_b_scores"]["checked"] - ctrl["universe_b_scores"]["mismatch"]:,} of '
                  f'{ctrl["universe_b_scores"]["checked"]:,} joined games')
    ctrl_table = f"""<div class="card"><h2>Control baselines (C04) — shown with every leaderboard run, never ranked</h2>
<p class="sub">Two labeled universes, both settled from the pinned scores. <b>Universe A</b>: events where the
pinned closing-line file carries odds for both sides (moneylines 2006–2018; spread/total odds 2017–2018) —
the <b>majority side</b> control bets the de-vigged majority side at the closing price with that de-vigged
probability as its forecast, so its BSS vs market is 0 by construction and the informative skill number is
BSS vs coin. <b>Universe B</b>: every {CTRL_WINDOW[0]}–{CTRL_WINDOW[1]} game with a market line in the pinned
modelling table, priced at the documented flat −110 fallback (100% imputed — flag L11): <b>favourite by
line sign</b> and <b>random picks</b>; Brier columns are blank because no de-vigged forecast exists without
odds. <b>random picks</b> draws sides 50/50 with seed {SEED} — one seeded realisation (flag L05). ROI is per
unit staked, week-cluster bootstrap CI. Settlement cross-check against the file's own outcome column:
{agree_line} — the disagreement rows are flag L08. {score_line}.</p>
<div class="scroll"><table>
<thead><tr><th>Universe</th><th>Market</th><th>Control</th><th>n events</th><th>Decided</th><th>Win rate</th>
<th>Imputed price share</th><th>ROI</th><th>ROI CI low</th><th>ROI CI high</th><th>p(ROI≤0)</th>
<th>BS (decided)</th><th>BSS vs coin</th><th>Source</th></tr></thead>
<tbody>{"".join(ctrl_rows)}</tbody></table></div></div>"""

    combo_rows = []
    for r in cf_rows:
        if r["id"] in core.COMBOS:
            combo_rows.append(
                f"<tr><td><b>{e(r['id'])}</b> {e(r['name'])}</td><td>{e(r['market'])}</td>"
                f'<td class="num">{r["n_bets"]:,}</td>'
                f'<td class="num">{r["seasons"]}</td>'
                f'<td class="num">{r["roi_pct"]:+.2f}%</td>'
                f'<td class="num">{r["roi_ci_low"]:+.4f}</td>'
                f'<td>{blank("L01")}</td>'
                f'<td>{blank("L01")}</td>'
                + src_cell([("bets.csv", BLOB + "data/derived/bets.csv"),
                            ("joint-evidence gate", BLOB + "hub/competition.html")]) + "</tr>")
    combo_table = f"""<div class="card"><h2>Combos — behind the joint-evidence gate (C01), unranked</h2>
<p class="sub">Two-leg cross-game parlays. Their published probabilities are products of leg marginals, which is
invalid under dependence; the joint-evidence gate requires a directly validated joint probability and the
operator's void/push rules before a combo may be ranked. Skill columns are blank by design, not missing by
accident.</p>
<div class="scroll"><table>
<thead><tr><th>Strategy</th><th>Market</th><th>n bets</th><th>Seasons</th><th>ROI (backtest)</th>
<th>ROI CI low</th><th>BSS</th><th>Rank</th><th>Source</th></tr></thead>
<tbody>{"".join(combo_rows) or '<tr><td colspan="9">none</td></tr>'}</tbody></table></div></div>"""

    fut_rows = []
    for r in cf_rows:
        if r["id"] == core.FUTURES:
            fut_rows.append(
                f"<tr><td><b>{e(r['id'])}</b> {e(r['name'])}</td><td>{e(r['market'])}</td>"
                f'<td class="num">{r["n_bets"]:,}</td>'
                f'<td class="num">{r["n_no_prob"]:,}</td>'
                f'<td class="num">{r["roi_pct"]:+.2f}%</td>'
                f'<td class="num">{r["roi_ci_low"]:+.4f}</td>'
                f'<td>{blank("L02")}</td>'
                + src_cell([("bets.csv", BLOB + "data/derived/bets.csv")]) + "</tr>")
    fut_table = f"""<div class="card"><h2>Futures — no model probability, unranked</h2>
<p class="sub">The futures ledger carries market probabilities but no model probability, so no proper score
exists. Blank by design (flag L02).</p>
<div class="scroll"><table>
<thead><tr><th>Strategy</th><th>Market</th><th>n bets</th><th>Rows without model prob</th><th>ROI (backtest)</th>
<th>ROI CI low</th><th>BSS</th><th>Source</th></tr></thead>
<tbody>{"".join(fut_rows) or '<tr><td colspan="8">none</td></tr>'}</tbody></table></div></div>"""

    mind_rows = []
    for r in ranked:
        more = r.get("confirm_more_bets")
        confirm = (f"≈{more:,} further bets at the observed BSS ({r['bss_market']:+.4f}) would move the lower bound to 0"
                   if more is not None and more > 0
                   else ("already eligible under the observed sample" if more == 0 else
                         "no sample size clears it at the observed effect — the effect itself must be larger"))
        ovl, sev = r.get("overturn_level"), r.get("se_conservative")
        if ovl is None or sev is None:
            overturn = "not computable from the bootstrap distribution — see method.html"
        else:
            overturn = (f"BSS ≤ {ovl:+.4f} on a prospective window drops the ranking bound to ≤ 0 "
                        f"(= 1.645 × SE {sev:.4f})")
        mind_rows.append(
            f"<tr><td><b>{e(r['id'])}</b> {e(r['name'])}</td>"
            f"<td>{e(confirm)}</td>"
            f"<td>{e(overturn)}</td>"
            + src_cell([("bets.csv", BLOB + "data/derived/bets.csv")]) + "</tr>")
    mind_table = f"""<div class="card"><h2>What would change our mind (A16) — two-sided, per ranked strategy</h2>
<p class="sub">Left: <b>confirm</b> — the additional settled bets at the observed BSS that would move the
lower bound to exactly 0 (delta-method approximation (z·SE/BSS)², documented in method.html; approximate, not
a promise). Right: <b>overturn</b> — the BSS level at or below which the strategy falls under the
eligibility line on the next window.</p>
<div class="scroll"><table>
<thead><tr><th>Strategy</th><th>Would confirm (promotion evidence)</th><th>Would overturn (demotion evidence)</th><th>Source</th></tr></thead>
<tbody>{"".join(mind_rows)}</tbody></table></div></div>"""

    bt_rows = []
    for r in bt:
        bt_rows.append(
            f"<tr><td><b>{e(r['id'])}</b> {e(r['name'])}</td><td>{e(r['market'])}</td>"
            f'<td class="num">{r["bets"]:,}</td>'
            f'<td class="num">{r["seasons"]}</td>'
            f'<td class="num">{fcell(r["full_roi"], 4, signed=True)}</td>'
            f'<td class="num">{fcell(r["full_ci_low"], 4, signed=True)}</td>'
            f'<td class="num">{fcell(r["holdout_roi"], 4, signed=True)}</td>'
            f'<td class="num">{fcell(r["holdout_ci_low"], 4, signed=True)}</td>'
            f'<td class="num">{r["gates_passed"]}/8</td>'
            f'<td class="num">{fcell(r["brier_skill_published"], 4, signed=True)}</td>'
            + src_cell([("summary.json (leaderboard)", BLOB + "data/derived/summary.json"),
                        ("protocol", BLOB + "line_lab/docs/preregistration.md")]) + "</tr>")
    bt_table = f"""<div class="card"><h2>Historical backtest ledger — NOT the ranking (A09 support)</h2>
<p class="sub">These are <b>backtest</b> numbers quoted verbatim from the pinned
<code>data/derived/summary.json</code> leaderboard block (produced by line_lab, protocol seed 20261101).
They are historical descriptions, never a promotion: the ranking above uses only proper scores with
uncertainty, and staking metrics cannot move a strategy up (the signal/staking split). The
<code>brier_skill</code> column is line_lab's own published point estimate (no uncertainty there — this
lab's bound column above supersedes it).</p>
<div class="scroll"><table>
<thead><tr><th>Strategy</th><th>Market</th><th>Bets</th><th>Seasons</th><th>Full ROI</th><th>Full CI low</th>
<th>Holdout ROI</th><th>Holdout CI low</th><th>Gates passed</th><th>BSS (line_lab point)</th><th>Source</th></tr></thead>
<tbody>{"".join(bt_rows)}</tbody></table></div></div>"""

    cov_rows = []
    for sid in core.SINGLES:
        r = rows[sid]
        cov_rows.append(
            f"<tr><td><b>{e(sid)}</b> {e(r['name'])}</td>"
            f'<td class="num">{r["n_bets"]:,}</td>'
            f'<td class="num">{r["n_pushes"]:,}</td>'
            f'<td class="num">{r["n_no_prob"]:,}</td>'
            f'<td class="num">{r["n_scored"]:,}</td>'
            + src_cell([("bets.csv", BLOB + "data/derived/bets.csv")]) + "</tr>")
    cov_table = f"""<div class="card"><h2>Scoring coverage per strategy</h2>
<p class="sub">Every excluded row is counted, never silently dropped (rule R2).</p>
<div class="scroll"><table>
<thead><tr><th>Strategy</th><th>Ledger rows</th><th>Pushes (excluded)</th><th>Rows without model prob (excluded)</th>
<th>Scored</th><th>Source</th></tr></thead>
<tbody>{"".join(cov_rows)}</tbody></table></div></div>"""

    flags_index = "".join(
        f'<li><b>{e(f["id"])} ({e(f["severity"])})</b> — {e(f["title"])} '
        f'<a href="flagged.html#{e(f["id"])}">detail</a></li>' for f in flags)
    head = f"""<div class="hero">
<h1>Skill leaderboard — proper scores, uncertainty, controls</h1>
<p>Requirement C03 ("rank with proper scores and uncertainty, not win rate") and C04 ("add a control
baseline to every leaderboard run"), computed offline from the repository's pinned, checksummed
artifacts. The ranking metric is the <b>Brier skill score against the de-vigged market probability</b>
with a cluster-bootstrap lower bound and Benjamini–Hochberg multiplicity control. Control baselines
(coin-flip, majority side, seeded random) are shown with every run. Combos stay unranked behind the
joint-evidence gate; the historical backtest ledger is kept visually and structurally separate.</p>
<p class="sub">Inputs: <code>data/derived/bets.csv</code> ({meta["bets_rows"]:,} rows, SHA-256
<code>{meta["sha_bets"][:16]}…</code>), pinned nflverse commit <code>{meta["pinned_commit"][:12]}…</code>.
Verification rule: every number on this page is recomputed independently by
<code>skill_lab/check.py</code>; anything that cannot be computed is blank and flagged.</p>
<div class="kpis">
<div class="kpi"><div class="k">Strategies ranked (singles)</div><div class="v">{len(core.SINGLES)}</div><div class="n">S1–S8 of the bets.csv ledger</div></div>
<div class="kpi"><div class="k">Eligible by skill</div><div class="v">{sum(1 for r in rows.values() if r.get("eligible"))}</div><div class="n">lower bound &gt; 0 and q ≤ {core.FDR_Q}</div></div>
<div class="kpi"><div class="k">Best ranking bound</div><div class="v">{max((r["ranking_bound"] for r in rows.values() if r.get("ranking_bound") is not None), default=0):+.4f}</div><div class="n">{max((r["id"] for r in rows.values() if r.get("ranking_bound") is not None), key=lambda s: rows[s]["ranking_bound"], default="—")} · week-cluster lower bound</div></div>
<div class="kpi"><div class="k">Bootstrap resamples</div><div class="v">{N_BOOT:,}</div><div class="n">seed {SEED}, game + week clusters</div></div>
</div>
<p><b>Open flags:</b></p><ul>{flags_index}</ul>
</div>"""

    return page("Skill leaderboard", "index.html",
                head + lead_table + ctrl_table + bench_table + mind_table
                + combo_table + fut_table + bt_table + cov_table)


def build_method(meta) -> str:
    body = f"""<div class="hero"><h1>Method — proper-score skill ranking</h1>
<p>Every rule below was fixed before any number was computed; the same text is the docstring of
<code>skill_lab/core.py</code>. Inputs are read-only pinned artifacts; nothing is fetched.</p></div>
<div class="card prose">
<h2>Inputs and identity</h2>
<ul>
<li><code>data/derived/bets.csv</code> — the per-bet ledger ({meta["bets_rows"]:,} rows, S1–S11, line_lab
build; SHA-256 <code>{meta["sha_bets"]}</code>).</li>
<li><code>data/derived/summary.json</code> — protocol constants (seed 20261101, evaluation window
2006–2025, FDR level 0.10) and the pinned nflverse commit <code>{meta["pinned_commit"]}</code>.</li>
<li><code>data/raw/closing_lines.csv</code> and <code>data/raw/games.csv</code> — the pinned
third-party dataset used only for the global control universe and its settlement.</li>
<li><code>market_prob</code> in the ledger is the proportionally de-vigged two-way closing probability
(line_lab <code>markets.devig_two_way</code>); this lab re-derives nothing else about the market.</li>
</ul>
<h2>Rules (R1–R8)</h2>
<ul>
<li><b>R1 family.</b> Ranked: singles S1–S8 (markets ATS, TOTAL, ML). S9/S10 parlays: unranked (flag L01,
joint-evidence gate C01). S11 futures: unranked, no model probability (flag L02).</li>
<li><b>R2 scored subset.</b> Rows with a model probability and a decided outcome (pushes excluded); every
exclusion counted and published.</li>
<li><b>R3 score.</b> Brier: BS = mean((p−y)²), y = 1 win / 0 loss. Benchmarks on the same events:
<b>market</b> (de-vigged market probability of the same side), <b>coin</b> (0.5), <b>favourite</b>
(majority-side probability on that event). BSS(x) = 1 − BS_model/BS_x.</li>
<li><b>R4 uncertainty.</b> Cluster bootstrap, {N_BOOT:,} resamples, seed {SEED}, two clusterings —
game (<code>game_id</code>) and week (<code>season, week</code>). Numerator and denominator resampled
together; the same resample sets are reused across benchmarks (paired). Reported per benchmark: 2.5/97.5
percentiles, one-sided p = P(BSS* ≤ 0), SE. Ranking bound = the more conservative (lower) of the two
2.5th percentiles; ranking p = the larger of the two one-sided p-values.</li>
<li><b>R5 multiplicity.</b> Benjamini–Hochberg at q = {core.FDR_Q} across the {len(core.SINGLES)} ranked
strategies on the ranking p-values; Bonferroni threshold 0.05/{len(core.SINGLES)} shown for reference.
Eligibility: ranking bound &gt; 0 AND q ≤ {core.FDR_Q}. No minimum-n rule — the bound carries the
sample-size penalty.</li>
<li><b>R6 controls.</b> Coin-flip and majority-side columns on each strategy's own events; global CONTROL
rows in two labelled universes: <b>A</b> — events where the pinned closing-line file carries odds for both
sides (moneylines 2006–2018; spread/total odds 2017–2018), majority side bet at the closing price with its
de-vigged probability as forecast; <b>B</b> — every {CTRL_WINDOW[0]}–{CTRL_WINDOW[1]} game with a market line
in the pinned modelling table, priced at the documented flat −110 fallback (100% imputed, flag L11),
favourite-by-line and one seeded random realisation (flag L05). Controls are never ranked.</li>
<li><b>R7 what would change our mind.</b> Confirm: additional bets at the observed BSS for the lower bound
to reach 0, n = (z·SE/BSS)² (z = 1.645 one-sided), delta-method approximation. Overturn: BSS ≤
1.645·SE on a prospective window drops the bound to ≤ 0.</li>
<li><b>R8 determinism.</b> No wall clock anywhere; the build identity is the SHA-256 of the inputs.
Two builds on the same inputs are byte-identical (checked by <code>skill_lab/check.py</code>).</li>
</ul>
<h2>Settlement of the control universe</h2>
<ul>
<li>Spread: cover margin = side points + line − opponent points (&gt;0 win, =0 push, &lt;0 loss).</li>
<li>Total: over wins if total &gt; line; push at equality; under the mirror.</li>
<li>Moneyline: more points wins; ties (two in the pinned window: 2008 PHI@CIN, 2012 STL@SF) push.</li>
<li>Cross-check: the dataset's own <code>outcome</code> column agrees with this recomputation on
{sum(v[0] for v in meta["agree"].values())} of {sum(v[1] for v in meta["agree"].values())} recorded rows
({100*sum(v[0] for v in meta["agree"].values())/max(1,sum(v[1] for v in meta["agree"].values())):.2f}%) —
every disagreement row is listed in <code>skill_lab/data/flags.json</code> and flagged (L08). The
modelling table's own score columns agree with <code>games.csv</code> on
{meta.get("ub_checked", 0):,} of {meta.get("ub_checked", 0):,} joined games (flag L11 for its missing odds).</li>
</ul>
<h2>What this page does not claim</h2>
<ul>
<li>No official NFL number appears here: the dataset is the pinned nflverse commit (flag L04); the NFL
publishes no closing lines, prices or probability forecasts.</li>
<li>Ranking is by skill only; ROI is shown in the separated backtest ledger and cannot promote a strategy
(signal/staking split).</li>
<li>Pre-registration of the underlying strategies is line_lab's committed protocol; this lab adds scoring
rules only (flag L09). Full pre-registration (A10) remains open on the readiness register.</li>
</ul>
<h2>Reproduce</h2>
<pre>python3 -m skill_lab.build    # deterministic rebuild
python3 -m skill_lab.check    # independent recomputation of every published number
python3 -m pytest tests/test_skill_lab.py -q</pre>
</div>"""
    return page("Method", "method.html", body)


def build_flagged(flags) -> str:
    items = []
    for f in flags:
        srcs = " · ".join(f'<a href="{e(u)}">{e(u.split("/")[-1])}</a>' for u in f["sources"])
        items.append(f"""<div class="card" id="{e(f['id'])}"><h2>{e(f['id'])} · {e(f['title'])}</h2>
<p><span class="pill {'bad' if f['severity'] in ('high',) else 'chg'}">{e(f['severity'])}</span>
<span class="pill">{e(f['status'])}</span></p>
<p>{e(f['detail'])}</p><p class="sub">Sources: {srcs}</p></div>""")
    head = """<div class="hero"><h1>Flagged for review</h1>
<p>Every blank cell on the leaderboard maps to one of these flags. A blank means "not computed because a
pre-registered rule forbids it or the input does not exist" — never zero, never inferred.</p></div>"""
    return page("Flagged for review", "flagged.html", head + "".join(items))


# --------------------------------------------------------------------------- #
def main() -> int:
    summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
    bets = load_bets()
    rows = strategy_rows(bets)
    games = load_games()
    closing = load_closing()

    # L08: full-file cross-check of the dataset's own outcome column
    validation = validate_outcome_column(games, closing)
    # Universe A: events with both closing odds; Universe B: line-imputed at -110
    ev_a = control_universe_a(games, closing)
    preds = load_preds()
    ub = control_universe_b(games, preds)

    ctrl = {
        "agree": validation["agree"],
        "mismatch": validation["mismatch"],
        "universe_b_scores": {"checked": ub["score_checked"],
                              "mismatch": ub["score_mismatch"]},
        "metrics": {},
    }
    for mtype, evts in ev_a.items():
        for mode in ("majority", "random"):
            if evts:
                ctrl["metrics"][f"A:{mtype}:{mode}"] = control_metrics(evts, mode)
    for mtype, evts in ub["events"].items():
        # universe B has no odds: a de-vigged majority side is undefined for
        # totals (the two sides' line values are equal), so only SPREAD gets a
        # majority (favourite-by-line-sign) mode.
        modes = ("majority", "random") if mtype == "SPREAD" else ("random",)
        for mode in modes:
            if evts:
                ctrl["metrics"][f"B:{mtype}:{mode}"] = control_metrics(evts, mode)

    cf_rows = combo_futures_rows(bets)
    bt = backtest_ledger(summary)
    flags = build_flags(rows, ctrl, summary)

    meta = {
        "bets_rows": len(bets),
        "sha_bets": sha256_of(BETS),
        "sha_closing": sha256_of(CLOSING),
        "sha_games": sha256_of(GAMES),
        "sha_summary": sha256_of(SUMMARY),
        "sha_preds": sha256_of(ROOT / "data" / "derived" / "model_predictions.csv"),
        "pinned_commit": summary.get("pinned_commit", ""),
        "seed": SEED, "n_boot": N_BOOT, "fdr_q": core.FDR_Q,
        "agree": ctrl["agree"],
        "controls_window": list(CTRL_WINDOW),
        "fallback_price": FALLBACK_PRICE,
        "ub_checked": ctrl["universe_b_scores"]["checked"],
        "ub_mismatch": ctrl["universe_b_scores"]["mismatch"],
    }
    for f in flags:
        if f["id"] == "L08":
            f["mismatch_rows"] = {k: v for k, v in ctrl["mismatch"].items()}
            f["agree"] = ctrl["agree"]

    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "skill_table.json").write_text(json.dumps(rows, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (DATA / "controls.json").write_text(
        json.dumps({"metrics": ctrl["metrics"], "agree": ctrl["agree"],
                    "universe_b_scores": ctrl["universe_b_scores"],
                    "window": CTRL_WINDOW, "fallback_price": FALLBACK_PRICE},
                   indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (DATA / "flags.json").write_text(json.dumps(flags, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    (DATA / "meta.json").write_text(json.dumps(meta, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    (HERE / "index.html").write_text(build_index(rows, ctrl, cf_rows, cf_rows, bt, flags, meta), encoding="utf-8")
    (HERE / "method.html").write_text(build_method(meta), encoding="utf-8")
    (HERE / "flagged.html").write_text(build_flagged(flags), encoding="utf-8")

    print(f"skill_lab built: {len(rows)} ranked strategies, "
          f"{sum(1 for r in rows.values() if r.get('eligible'))} eligible, "
          f"{len(flags)} flags, inputs sha-stamped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
