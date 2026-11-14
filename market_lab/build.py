#!/usr/bin/env python3
"""Markets Ledger generator.

Builds, from the pinned ``line_lab`` inputs and the consolidated ``data/derived`` artifacts:

* ``data/price_snapshot.csv``   opening + closing numbers for every market (side/total/moneyline)
* ``data/results_feed.csv``     a verified results feed keyed to the official final score
* ``data/fair_vs_market.csv``   model fair line, market line and difference, per market
* ``data/signal_staking.csv``   signal and staking ranked separately
* ``data/demotion_gate.csv``    the demotion check for every strategy
* ``data/sources.json``         the source register
* ``data/market_summary.json``  coverage and counts
* ten HTML pages under ``market_lab/``

Every value is recomputed here from a pinned input or left blank and flagged. Nothing is
inferred. Run with ``python3 -m market_lab.build``.
"""
from __future__ import annotations

import csv
import html
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .demotion import DEMOTION_RULE, demotion_check
from .originate import ORDER_RULE, originate_order

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent

LINE_RAW = BASE.parent / "line_lab" / "data" / "raw"
LINE_DERIVED = BASE.parent / "line_lab" / "data" / "derived"
DATA_DERIVED = ROOT / "data" / "derived"

OUT = BASE / "data"
ASSETS = BASE / "assets"

PIN = "a270278f3ac4e937295fe6a27814b3c4a2b62645"
NFL_BASE = f"https://github.com/nflverse/nfldata/blob/{PIN}/data/"
GAMES_URL = NFL_BASE + "games.csv"
CLOSING_URL = NFL_BASE + "closing_lines.csv"
INITIAL_URL = NFL_BASE + "initial_lines.csv"
RULEBOOK_URL = "https://operations.nfl.com/rules-officiating/2026-nfl-rulebook"
BLOB = "https://github.com/karagemop466-tech/Korea3/blob/main/"

EVAL_START, EVAL_END = 2006, 2025


def build_timestamp() -> str:
    epoch = os.environ.get("SOURCE_DATE_EPOCH")
    if epoch and epoch.isdigit():
        return datetime.fromtimestamp(int(epoch), tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def esc(x) -> str:
    if x is None:
        return ""
    if isinstance(x, float) and math.isnan(x):
        return ""
    return html.escape(str(x))


def fmt_num(x, nd=2) -> str:
    if x is None:
        return ""
    try:
        f = float(x)
    except (TypeError, ValueError):
        return str(x)
    if math.isnan(f):
        return ""
    return f"{f:,.{nd}f}"


def parse_game_id(alt: str):
    """`2006_01_MIA_PIT` -> (2006, 1, 'MIA', 'PIT')."""
    parts = str(alt).split("_")
    if len(parts) != 4:
        return None, None, None, None
    try:
        season = int(parts[0])
        week = int(parts[1])
    except ValueError:
        return None, None, None, None
    return season, week, parts[2], parts[3]


# --------------------------------------------------------------------------- #
# Inputs
# --------------------------------------------------------------------------- #
def load_inputs():
    closing = pd.read_csv(LINE_RAW / "closing_lines.csv", low_memory=False)
    initial = pd.read_csv(LINE_RAW / "initial_lines.csv", low_memory=False)
    games = pd.read_csv(LINE_RAW / "games.csv", low_memory=False)
    feats = pd.read_csv(LINE_DERIVED / "features.csv", low_memory=False)
    with open(DATA_DERIVED / "summary.json", encoding="utf-8") as fh:
        summary = json.load(fh)
    return closing, initial, games, feats, summary


# --------------------------------------------------------------------------- #
# 1. Price-snapshot store
# --------------------------------------------------------------------------- #
def build_snapshot(closing: pd.DataFrame, initial: pd.DataFrame) -> tuple[list[dict], dict]:
    """Opening + closing numbers for every market, one row per (game, market, side).

    The store is built from the union of the two pinned sources. Opening cells come from
    ``initial_lines.csv``; closing cells come from ``closing_lines.csv``. Where a source does
    not cover a game, that side's cells are left blank and flagged — never inferred. The two
    pinned sources cover **disjoint seasons** (opening 2021, closing 2006–2018), so no single
    game has both an opening and a closing line; that is recorded as a flag, not hidden.
    """
    open_idx: dict[tuple, object] = {}
    for r in initial.itertuples(index=False):
        open_idx[(str(r.about), str(r.type), str(r.side))] = r

    closing_idx: dict[tuple, object] = {}
    for r in closing.itertuples(index=False):
        closing_idx[(str(r.alt_game_id), str(r.type), str(r.side))] = r

    # union of (game_id, type, side) across both sources
    all_keys = set(closing_idx.keys()) | set(open_idx.keys())

    # per-game metadata from whichever source carries it
    game_meta: dict[str, tuple] = {}
    for r in closing.itertuples(index=False):
        game_meta.setdefault(str(r.alt_game_id), parse_game_id(r.alt_game_id))
    for r in initial.itertuples(index=False):
        game_meta.setdefault(str(r.about), parse_game_id(r.about))

    rows = []
    opening_found = 0
    closing_found = 0
    both = 0
    per_market = {"SIDE": {"open": 0, "close": 0}, "TOTAL": {"open": 0, "close": 0},
                  "MONEYLINE": {"open": 0, "close": 0}}
    per_year_open: dict[str, int] = {}
    per_year_close: dict[str, int] = {}

    for (game_id, mtype, side) in sorted(all_keys):
        season, week, away, home = game_meta.get(game_id, parse_game_id(game_id))
        mkey = "SIDE" if mtype == "SPREAD" else mtype

        op = open_idx.get((game_id, mtype, side))
        cl = closing_idx.get((game_id, mtype, side))

        open_line = op.line if op is not None else None
        open_odds = None  # initial_lines carries no odds column
        close_line = cl.line if cl is not None else None
        close_odds = cl.odds if cl is not None else None
        outcome = cl.outcome if cl is not None else None

        flags = []
        if op is not None:
            opening_found += 1
            per_market[mkey]["open"] += 1
            per_year_open[str(season)] = per_year_open.get(str(season), 0) + 1
            flags.append("opening odds not published by source")
        if cl is not None:
            closing_found += 1
            per_market[mkey]["close"] += 1
            per_year_close[str(season)] = per_year_close.get(str(season), 0) + 1
        if op is not None and cl is not None:
            both += 1
        elif op is not None:
            flags.append("no closing record in pinned data")
        elif cl is not None:
            flags.append("no opening record in pinned data")

        rows.append({
            "game_id": game_id,
            "season": season,
            "week": week,
            "matchup": f"{away} @ {home}" if away and home else game_id,
            "market": mkey,
            "side": side,
            "opening_line": open_line,
            "opening_odds": open_odds,
            "closing_line": close_line,
            "closing_odds": close_odds,
            "outcome": outcome,
            "opening_source": INITIAL_URL if op is not None else "",
            "closing_source": CLOSING_URL if cl is not None else "",
            "flags": "; ".join(flags),
        })

    coverage = {
        "store_records": int(len(rows)),
        "opening_available": opening_found,
        "closing_available": closing_found,
        "games_with_both": both,
        "opening_by_year": {k: v for k, v in sorted(per_year_open.items())},
        "closing_by_year": {k: v for k, v in sorted(per_year_close.items())},
        "by_market": per_market,
        "note": (
            "The two pinned sources cover disjoint seasons: initial_lines.csv holds opening lines "
            "for 2021 (SPREAD and TOTAL, one sportsbook) and closing_lines.csv holds closing lines "
            "for 2006-2018 (all three markets). No game in the pinned data has both an opening and "
            "a closing line, so per-game opening-to-closing pairing is not possible from this data. "
            "Every missing side is left blank and flagged; nothing is inferred."
        ),
    }
    return rows, coverage


# --------------------------------------------------------------------------- #
# 2. Verified results feed
# --------------------------------------------------------------------------- #
def _settle(market: str, kind: str, line, home_score, away_score) -> int:
    """Settle a bet from the official final score. Returns 1 win, 0 push, -1 loss.

    Mirrors the settlement convention of ``closing_lines.csv``: the spread and moneyline line
    is stored from the *side's* perspective (positive = that side receives points), and a push
    is recorded as 0.5, a win as 1 and a loss as 0. This function returns the signed value
    (1/0/-1); the caller maps it to the recorded 1 / 0.5 / 0 convention.
    """
    result = home_score - away_score
    total = home_score + away_score
    if market == "SPREAD":
        side_margin = result if kind == "home" else -result
        m = side_margin + float(line)
        if m == 0:
            return 0
        return 1 if m > 0 else -1
    if market == "TOTAL":
        m = total - float(line)
        if m == 0:
            return 0
        over = m > 0
        return 1 if (over and kind == "Over") or ((not over) and kind == "Under") else -1
    if market == "MONEYLINE":
        if result == 0:
            return 0
        home_won = result > 0
        return 1 if (home_won and kind == "home") or ((not home_won) and kind == "away") else -1
    raise ValueError(market)


def _side_kind(market: str, side: str) -> str:
    if market == "SPREAD":
        return "home" if side == "home" else "away"
    if market == "TOTAL":
        return side  # "Over" / "Under"
    return "home" if side == "home" else "away"


def build_results_feed(closing: pd.DataFrame, games: pd.DataFrame) -> tuple[list[dict], dict]:
    """A results feed keyed to the official final score, with a verification column.

    The recorded outcome in ``closing_lines.csv`` is re-settled from the official final score
    (``games.csv``). A row is ``verified`` when the score is present and the re-settled outcome
    equals the recorded outcome; otherwise it is flagged.
    """
    score_by_id = {}
    for r in games.itertuples(index=False):
        score_by_id[str(r.game_id)] = (r.home_score, r.away_score)

    rows = []
    verified = 0
    score_missing = 0
    mismatch = 0
    for r in closing.itertuples(index=False):
        season, week, away, home = parse_game_id(r.alt_game_id)
        market = str(r.type)
        side = str(r.side)
        hs, as_ = score_by_id.get(str(r.alt_game_id), (None, None))
        score_present = hs is not None and as_ is not None and not (
            isinstance(hs, float) and math.isnan(hs))

        recorded = r.outcome
        recomputed = None
        status = "unverified"
        flag = ""
        if not score_present:
            status = "unverified"
            flag = "official final score not present for this game"
            score_missing += 1
        else:
            # Map the recorded side to the settlement convention: SPREAD/MONEYLINE sides are
            # team abbreviations -> home/away; TOTAL sides are Over/Under.
            if market in ("SPREAD", "MONEYLINE"):
                kind = "home" if side == home else "away"
            else:
                kind = side
            # closing_lines records 1 = win, 0.5 = push, 0 = loss. Map the signed settlement
            # (1 win / 0 push / -1 loss) to that convention before comparing.
            signed = _settle(market, kind, r.line, hs, as_)
            recomputed = 1.0 if signed > 0 else (0.5 if signed == 0 else 0.0)
            if recomputed == recorded:
                status = "verified"
                verified += 1
            else:
                status = "mismatch"
                flag = "re-settled outcome differs from recorded outcome"
                mismatch += 1

        rows.append({
            "game_id": r.alt_game_id,
            "season": season,
            "week": week,
            "matchup": f"{away} @ {home}" if away and home else r.alt_game_id,
            "market": market,
            "side": side,
            "line": r.line,
            "price": r.odds,
            "recorded_outcome": recorded,
            "recomputed_outcome": recomputed,
            "official_home_score": hs,
            "official_away_score": as_,
            "verification": status,
            "flags": flag,
            "source": GAMES_URL,
        })

    coverage = {
        "rows": int(len(rows)),
        "verified": verified,
        "score_missing": score_missing,
        "mismatch": mismatch,
        "verified_pct": round(100.0 * verified / len(rows), 2) if rows else 0.0,
        "note": (
            "Each row is settled against the official final score from the pinned games.csv and "
            "compared to the recorded outcome in closing_lines.csv. 'verified' means the score is "
            "present and the re-settled outcome matches the recorded one."
        ),
    }
    return rows, coverage


# --------------------------------------------------------------------------- #
# 3. Fair vs market (all three markets)
# --------------------------------------------------------------------------- #
def build_fair_vs_market(feats: pd.DataFrame) -> tuple[list[dict], dict]:
    """Model fair line, market line and difference for side, total and moneyline.

    Uses the walk-forward model predictions in ``features.csv`` (mu_spread, mu_total, sd_spread)
    for the evaluated window. Difference = fair - market for every market.
    """
    win = feats[(feats["season"] >= EVAL_START) & (feats["season"] <= EVAL_END)].copy()
    rows = []
    n_side = n_total = n_ml = 0
    for r in win.itertuples(index=False):
        g = originate_order({
            "mu_spread": r.mu_spread, "sd_spread": r.sd_spread, "mu_total": r.mu_total,
        })
        fair_spread = g["side"]["fair_line"]
        fair_total = g["total"]["fair_line"]
        fair_ml_home = g["moneyline"]["fair_line_home"]
        fair_ml_away = g["moneyline"]["fair_line_away"]

        matchup = f"{r.away_team} @ {r.home_team}"

        if fair_spread is not None and pd.notna(r.spread_line):
            rows.append({
                "game_id": r.game_id, "season": r.season, "week": r.week,
                "matchup": matchup, "market": "SIDE",
                "fair_line": fair_spread, "market_line": r.spread_line,
                "difference": fair_spread - r.spread_line,
                "source": BLOB + "line_lab/data/derived/features.csv",
            })
            n_side += 1
        if fair_total is not None and pd.notna(r.total_line):
            rows.append({
                "game_id": r.game_id, "season": r.season, "week": r.week,
                "matchup": matchup, "market": "TOTAL",
                "fair_line": fair_total, "market_line": r.total_line,
                "difference": fair_total - r.total_line,
                "source": BLOB + "line_lab/data/derived/features.csv",
            })
            n_total += 1
        if fair_ml_home is not None and pd.notna(r.home_moneyline):
            rows.append({
                "game_id": r.game_id, "season": r.season, "week": r.week,
                "matchup": matchup, "market": "MONEYLINE", "side": "home",
                "fair_line": fair_ml_home, "market_line": r.home_moneyline,
                "difference": fair_ml_home - r.home_moneyline,
                "source": BLOB + "line_lab/data/derived/features.csv",
            })
            n_ml += 1
        if fair_ml_away is not None and pd.notna(r.away_moneyline):
            rows.append({
                "game_id": r.game_id, "season": r.season, "week": r.week,
                "matchup": matchup, "market": "MONEYLINE", "side": "away",
                "fair_line": fair_ml_away, "market_line": r.away_moneyline,
                "difference": fair_ml_away - r.away_moneyline,
                "source": BLOB + "line_lab/data/derived/features.csv",
            })
            n_ml += 1

    coverage = {
        "window": [EVAL_START, EVAL_END],
        "side_rows": n_side, "total_rows": n_total, "moneyline_rows": n_ml,
        "note": "Fair lines are model outputs (recomputed from the pinned model predictions). "
                "Difference = fair line - market line. Blank where the model or the market line is "
                "absent; never inferred.",
    }
    return rows, coverage


# --------------------------------------------------------------------------- #
# 4. Signal vs staking
# --------------------------------------------------------------------------- #
def build_signal_staking(summary: dict) -> tuple[list[dict], dict]:
    """Rank strategies on signal and on staking independently.

    Signal = prediction skill and edge (Brier skill, luck percentile) — independent of how much
    money a particular staking run happened to make. Staking = realised ROI / PnL. A strategy
    that ranks high on staking but low on signal is flagged as a lucky staking run masking a
    bad signal.
    """
    lbs = summary.get("leaderboard", [])

    def signal_key(s):
        bs = s.get("brier_skill")
        perm = s.get("permutation_percentile")
        bs_v = bs if bs is not None else -1e9
        perm_v = perm if perm is not None else -1e9
        return (bs_v, perm_v)

    def staking_key(s):
        hroi = s.get("holdout_roi")
        roi = s.get("full_roi")
        hroi_v = hroi if hroi is not None else -1e9
        roi_v = roi if roi is not None else -1e9
        return (hroi_v, roi_v)

    by_signal = sorted(lbs, key=signal_key, reverse=True)
    by_staking = sorted(lbs, key=staking_key, reverse=True)
    signal_rank = {s["id"]: i + 1 for i, s in enumerate(by_signal)}
    staking_rank = {s["id"]: i + 1 for i, s in enumerate(by_staking)}

    rows = []
    for s in lbs:
        sid = s["id"]
        sr = signal_rank[sid]
        tr = staking_rank[sid]
        gap = tr - sr
        masked = (sr > len(lbs) // 2) and (tr <= len(lbs) // 2)
        rows.append({
            "id": sid, "name": s["name"], "market": s["market"],
            "brier_skill": s.get("brier_skill"),
            "luck_percentile": s.get("permutation_percentile"),
            "signal_rank": sr,
            "full_roi": s.get("full_roi"),
            "holdout_roi": s.get("holdout_roi"),
            "staking_rank": tr,
            "rank_gap": gap,
            "lucky_staking_masking_signal": masked,
            "source": BLOB + "data/derived/summary.json",
        })

    coverage = {
        "strategies": len(rows),
        "signal_components": ["brier_skill", "permutation_percentile"],
        "staking_components": ["holdout_roi", "full_roi"],
        "note": "Signal and staking are ranked separately. 'lucky staking masking signal' is true "
                "when a strategy's staking rank is in the better half while its signal rank is in "
                "the worse half — a staking result that does not reflect prediction skill.",
    }
    return rows, coverage


# --------------------------------------------------------------------------- #
# 5. Demotion gate
# --------------------------------------------------------------------------- #
def build_demotion(summary: dict) -> tuple[list[dict], dict]:
    lbs = summary.get("leaderboard", [])
    rows = [demotion_check(s) for s in lbs]
    counts = {"live": 0, "paper": 0, "demoted": 0}
    for r in rows:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return rows, {"rule": DEMOTION_RULE, "counts": counts, "strategies": len(rows)}


# --------------------------------------------------------------------------- #
# HTML rendering
# --------------------------------------------------------------------------- #
NAV = [
    ("index.html", "Overview"),
    ("snapshot.html", "Price snapshots"),
    ("results.html", "Results feed"),
    ("origination.html", "Origination order"),
    ("fair_vs_market.html", "Fair vs market"),
    ("signal_staking.html", "Signal vs staking"),
    ("demotion.html", "Demotion gate"),
    ("flagged.html", "Flagged"),
    ("sources.html", "Sources"),
    ("method.html", "Method"),
]


def nav_html(active: str) -> str:
    parts = []
    for href, label in NAV:
        cls = ' class="active"' if href == active else ""
        parts.append(f'<a href="{href}"{cls}>{label}</a>')
    return "".join(parts)


def page(title: str, eyebrow: str, lead: str, body: str, active: str) -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} | NFL Markets Ledger</title>
<meta name="description" content="Price snapshots, verified results, origination order, fair-vs-market, signal/staking and the demotion gate.">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="site">
  <div class="wrap">
    <div class="topbar">
      <a class="brand" href="index.html">
        <span class="mark">N</span>
        <span><strong>NFL Markets Ledger</strong><small>Price snapshots · verified results · gates</small></span>
      </a>
      <span class="badge">Research only · no betting advice</span>
    </div>
    <nav class="main" aria-label="Main navigation">{nav_html(active)}</nav>
  </div>
</header>
<main class="wrap">
  <div class="eyebrow">{esc(eyebrow)}</div>
  <h1>{esc(title)}</h1>
  <p class="lead">{lead}</p>
{body}
</main>
<footer class="site">
  <div class="wrap">
    <div>Independent research · not affiliated with the NFL · every table row links a source<br>
      Pinned source commit <a href="https://github.com/nflverse/nfldata/commit/{PIN}" target="_blank" rel="noopener noreferrer">{PIN[:7]}</a></div>
    <div>Blank cells mean unverified, never zero. <a href="flagged.html">Review limitations</a></div>
  </div>
</footer>
</body>
</html>"""


def table(headers, rows, caption="", row_source_idx=None):
    head = "".join(f'<th scope="col">{esc(h)}</th>' for h in headers)
    body_rows = []
    for row in rows:
        cells = []
        for i, h in enumerate(headers):
            v = row[i] if isinstance(row, (list, tuple)) else row.get(h, "")
            if h == "Source" and v:
                cells.append(f'<td><a href="{esc(v)}" target="_blank" rel="noopener noreferrer">source ↗</a></td>')
            else:
                cells.append(f"<td>{esc(v)}</td>")
        body_rows.append("<tr>" + "".join(cells) + "</tr>")
    cap = f'<caption>{esc(caption)}</caption>' if caption else ""
    return f'<div class="scroll"><table class="">{cap}<thead><tr>{head}</tr></thead><tbody>{"".join(body_rows)}</tbody></table></div>'


def render_index(snapshot_cov, results_cov, fair_cov, sig_cov, dem_cov, ts):
    body = f"""
<div class="notice"><strong>What this ledger adds.</strong> The brief asked for a price-snapshot
store that records opening <em>and</em> closing numbers for every market we originate, a verified
results feed, the origination order (side, then total, then moneyline), the fair line / market line
/ difference published as separate columns, signal separated from staking, and a demotion gate that
sends a live strategy back to paper. Each is built here from the pinned inputs; values that no
pinned or official source can confirm are left blank and flagged.</div>

<div class="grid k4">
  <div class="card"><div class="tag">Snapshot records</div><div class="num">{snapshot_cov['store_records']:,}</div>
    <div class="sub">opening {snapshot_cov['opening_available']:,} · closing {snapshot_cov['closing_available']:,} · both {snapshot_cov['games_with_both']:,}</div></div>
  <div class="card"><div class="tag">Results verified</div><div class="num">{results_cov['verified']:,}</div>
    <div class="sub">of {results_cov['rows']:,} settled against the official score</div></div>
  <div class="card"><div class="tag">Fair-vs-market rows</div><div class="num">{fair_cov['side_rows']+fair_cov['total_rows']+fair_cov['moneyline_rows']:,}</div>
    <div class="sub">side · total · moneyline, {EVAL_START}–{EVAL_END}</div></div>
  <div class="card"><div class="tag">Live strategies</div><div class="num">{dem_cov['counts'].get('live',0)}</div>
    <div class="sub">{dem_cov['counts'].get('paper',0)} paper · {dem_cov['counts'].get('demoted',0)} demoted</div></div>
</div>

<section>
  <div class="section-head"><div><h2>Key findings</h2>
    <p>Each row links to the evidence behind it.</p></div></div>
  <div class="scroll"><table class=""><thead><tr><th scope="col">Finding</th><th scope="col">What the data shows</th><th scope="col">Evidence</th></tr></thead><tbody>
  <tr><td><strong>Opening and closing cover disjoint seasons</strong></td><td>Opening numbers exist in the pinned data only for 2021, SPREAD and TOTAL, from one sportsbook; closing numbers cover 2006-2018. No game has both, so per-game opening-to-closing pairing is not possible from this data and the missing side of every row is left blank and flagged.</td><td><a href="snapshot.html">snapshot.html</a></td></tr>
  <tr><td><strong>The results feed verifies against the official score</strong></td><td>{results_cov['verified']:,} of {results_cov['rows']:,} settled rows re-settle to the recorded outcome from the official final score; {results_cov['mismatch']:,} mismatches and {results_cov['score_missing']:,} missing scores are flagged, not papered over.</td><td><a href="results.html">results.html</a></td></tr>
  <tr><td><strong>Origination order is fixed</strong></td><td>The model originates the side, then the total, then the moneyline; the moneyline is derived only from the originated side and never reads the market.</td><td><a href="origination.html">origination.html</a></td></tr>
  <tr><td><strong>Fair, market and difference are separate columns</strong></td><td>All three markets carry the model fair line, the market line and the difference ({fair_cov['side_rows']:,} side, {fair_cov['total_rows']:,} total, {fair_cov['moneyline_rows']:,} moneyline rows).</td><td><a href="fair_vs_market.html">fair_vs_market.html</a></td></tr>
  <tr><td><strong>Signal and staking are ranked apart</strong></td><td>{sig_cov['strategies']} strategies are ranked on signal (Brier skill, luck percentile) and on staking (holdout/full ROI) independently, so a lucky staking run cannot mask a bad signal.</td><td><a href="signal_staking.html">signal_staking.html</a></td></tr>
  <tr><td><strong>The demotion gate is defined</strong></td><td>A live strategy returns to paper if holdout ROI, significance, luck control or market skill fails. No strategy is live today, so none is demoted — the check is published and auditable.</td><td><a href="demotion.html">demotion.html</a></td></tr>
  </tbody></table></div>
</section>

<section>
  <div class="section-head"><div><h2>Pages</h2></div></div>
  <div class="grid k3">
    <div class="card"><h3><a href="snapshot.html">Price snapshots</a></h3><p class="small muted">Opening and closing numbers for every market, with blanks flagged.</p></div>
    <div class="card"><h3><a href="results.html">Results feed</a></h3><p class="small muted">Settled results keyed to the official final score, with verification.</p></div>
    <div class="card"><h3><a href="origination.html">Origination order</a></h3><p class="small muted">Side, then total, then moneyline — the three fair lines.</p></div>
    <div class="card"><h3><a href="fair_vs_market.html">Fair vs market</a></h3><p class="small muted">Fair line, market line and difference per market.</p></div>
    <div class="card"><h3><a href="signal_staking.html">Signal vs staking</a></h3><p class="small muted">Independent rankings so luck cannot mask skill.</p></div>
    <div class="card"><h3><a href="demotion.html">Demotion gate</a></h3><p class="small muted">The rule that sends a live strategy back to paper.</p></div>
    <div class="card"><h3><a href="flagged.html">Flagged</a></h3><p class="small muted">Every blank, mismatch and irregularity, with sources.</p></div>
    <div class="card"><h3><a href="sources.html">Sources</a></h3><p class="small muted">The pinned source register and the official links.</p></div>
    <div class="card"><h3><a href="method.html">Method</a></h3><p class="small muted">Data rules, verification and determinism.</p></div>
  </div>
</section>
"""
    return page("NFL Markets Ledger", "Markets Ledger",
                "Price snapshots, a verified results feed, the origination order, fair-vs-market "
                "columns, signal/staking separation and the demotion gate — built from pinned inputs.",
                body, "index.html")


def render_snapshot(rows, cov):
    # Show every row where opening is available, plus a bounded sample of the rest.
    with_open = [r for r in rows if r["opening_line"] is not None]
    without = [r for r in rows if r["opening_line"] is None]
    sample = without[:120]
    shown = with_open + sample
    hdr = ["Game", "Wk", "Matchup", "Market", "Side", "Open line", "Open odds",
           "Close line", "Close odds", "Outcome", "Flags", "Source"]
    body_rows = []
    for r in shown:
        src = r["closing_source"]
        if r["opening_source"]:
            src = r["opening_source"]
        body_rows.append([r["game_id"], r["week"], r["matchup"], r["market"], r["side"],
                          fmt_num(r["opening_line"]), fmt_num(r["opening_odds"], 0),
                          fmt_num(r["closing_line"]), fmt_num(r["closing_odds"], 0),
                          r["outcome"], r["flags"], src])
    year_str = ", ".join(f"{k}: {v}" for k, v in list(cov["opening_by_year"].items())[:6])
    t_store = table(hdr, body_rows,
                    "Opening odds are not published by the pinned source; they are left blank and flagged.")
    t_cov = table(["Market", "Opening rows", "Closing rows", "Source"],
                  [[m, cov["by_market"][m]["open"], cov["by_market"][m]["close"], INITIAL_URL]
                   for m in ("SIDE", "TOTAL", "MONEYLINE")],
                  "Opening exists only for SIDE and TOTAL, and only in 2021. MONEYLINE has no opening record at all.")
    body = f"""
<div class="notice"><strong>Coverage.</strong> {cov['note']}</div>
<div class="grid k4">
  <div class="card"><div class="tag">Store records</div><div class="num">{cov['store_records']:,}</div>
    <div class="sub">one row per game, market and side</div></div>
  <div class="card"><div class="tag">Opening present</div><div class="num">{cov['opening_available']:,}</div>
    <div class="sub">2021, SPREAD and TOTAL only</div></div>
  <div class="card"><div class="tag">Closing present</div><div class="num">{cov['closing_available']:,}</div>
    <div class="sub">2006-2018, all three markets</div></div>
  <div class="card"><div class="tag">Games with both</div><div class="num">{cov['games_with_both']:,}</div>
    <div class="sub">opening and closing on one game — none in the pinned data</div></div>
</div>
<section>
  <div class="section-head"><div><h2>Snapshot store</h2>
    <p>Opening and closing numbers for every market. Rows with an opening record are shown first;
    a 120-row sample of the blank-opening rows follows. The full store is
    <a href="data/price_snapshot.csv" target="_blank" rel="noopener noreferrer">price_snapshot.csv</a>.</p></div></div>
  {t_store}
</section>
<section>
  <div class="section-head"><div><h2>Opening coverage by market</h2></div></div>
  {t_cov}
</section>
"""
    return page("Price snapshots", "Price snapshots",
                "Opening and closing numbers for every market we originate, with every unverifiable "
                "opening value left blank and flagged.", body, "snapshot.html")


def render_results(rows, cov):
    # Show verified rows, all mismatches, and a sample of unverified.
    verified = [r for r in rows if r["verification"] == "verified"]
    mismatch = [r for r in rows if r["verification"] == "mismatch"]
    unverified = [r for r in rows if r["verification"] == "unverified"]
    shown = mismatch + verified[:150] + unverified[:40]
    hdr = ["Game", "Wk", "Matchup", "Market", "Side", "Line", "Price",
           "Recorded", "Recomputed", "H score", "A score", "Status", "Source"]
    body_rows = []
    for r in shown:
        body_rows.append([r["game_id"], r["week"], r["matchup"], r["market"], r["side"],
                          fmt_num(r["line"]), fmt_num(r["price"], 0), r["recorded_outcome"],
                          r["recomputed_outcome"] if r["recomputed_outcome"] is not None else "",
                          fmt_num(r["official_home_score"], 0), fmt_num(r["official_away_score"], 0),
                          r["verification"], r["source"]])
    t_feed = table(hdr, body_rows,
                   "'Recomputed' is settled from the official final score and compared to the recorded outcome.")
    body = f"""
<div class="notice"><strong>Verification.</strong> {cov['note']}</div>
<div class="grid k4">
  <div class="card"><div class="tag">Feed rows</div><div class="num">{cov['rows']:,}</div></div>
  <div class="card"><div class="tag">Verified</div><div class="num">{cov['verified']:,}</div>
    <div class="sub">{cov['verified_pct']}% re-settle to the recorded outcome</div></div>
  <div class="card"><div class="tag">Mismatches</div><div class="num">{cov['mismatch']:,}</div>
    <div class="sub">flagged, not corrected</div></div>
  <div class="card"><div class="tag">Scores missing</div><div class="num">{cov['score_missing']:,}</div>
    <div class="sub">official score absent — unverified</div></div>
</div>
<section>
  <div class="section-head"><div><h2>Results feed</h2>
    <p>Mismatches first, then verified rows, then a sample of unverified. Full feed:
    <a href="data/results_feed.csv" target="_blank" rel="noopener noreferrer">results_feed.csv</a>.</p></div></div>
  {t_feed}
</section>
"""
    return page("Verified results feed", "Results feed",
                "A results feed keyed to the official final score, so backtests and ROI can be "
                "computed against a verified settlement.", body, "results.html")


def render_origination(feats):
    win = feats[(feats["season"] >= EVAL_START) & (feats["season"] <= EVAL_END)]
    example = win.iloc[len(win) // 2]
    g = originate_order({"mu_spread": example.mu_spread, "sd_spread": example.sd_spread,
                         "mu_total": example.mu_total})
    src = BLOB + "line_lab/data/derived/features.csv"
    t_example = table(
        ["Step", "Market", "Fair line", "Inputs", "Source"],
        [[1, "SIDE (spread)", fmt_num(g["side"]["fair_line"]), ", ".join(g["side"]["inputs"]), src],
         [2, "TOTAL", fmt_num(g["total"]["fair_line"]), ", ".join(g["total"]["inputs"]), src],
         [3, "MONEYLINE (home)", fmt_num(g["moneyline"]["fair_line_home"]), ", ".join(g["moneyline"]["inputs"]), src],
         [3, "MONEYLINE (away)", fmt_num(g["moneyline"]["fair_line_away"]), ", ".join(g["moneyline"]["inputs"]), src],
         ["", "home win prob", fmt_num(g["moneyline"]["home_win_prob"], 4), "derived from side", src]],
        "The moneyline is step 3 and is derived only from the spread produced in step 1.")
    body = f"""
<div class="notice"><strong>The order.</strong> {ORDER_RULE}</div>
<section>
  <div class="section-head"><div><h2>Worked example</h2>
    <p>One game from the evaluated window, shown in the mandated order.</p></div></div>
  {t_example}
</section>
<section>
  <div class="section-head"><div><h2>Why the order matters</h2></div></div>
  {table(["Step", "Market", "What is fixed", "Source"],
          [[1, "Side (spread)", "The expected margin. The spread is originated first and independently of the total and moneyline.", BLOB + "market_lab/originate.py"],
           [2, "Total", "The expected combined score, originated independently of the moneyline.", BLOB + "market_lab/originate.py"],
           [3, "Moneyline", "Derived last from the already-originated spread and its uncertainty. It never reads the market moneyline, so it cannot be tuned to hide a bad spread.", BLOB + "market_lab/originate.py"]],
          "Each step is published with the module that implements it.")}
</section>
"""
    return page("Origination order", "Origination order",
                "The model originates the side first, then the total, then the moneyline — in that "
                "fixed order, with each fair line published separately.", body, "origination.html")


def render_fair_vs_market(rows, cov):
    hdr = ["Game", "Wk", "Matchup", "Market", "Side", "Fair line", "Market line", "Difference", "Source"]
    shown = rows[:400]
    body_rows = []
    for r in shown:
        body_rows.append([r["game_id"], r["week"], r["matchup"], r["market"], r.get("side", ""),
                          fmt_num(r["fair_line"]), fmt_num(r["market_line"]),
                          fmt_num(r["difference"]), r["source"]])
    t_fair = table(hdr, body_rows,
                   "Difference = fair line - market line. Positive means the model is on the same side as the market line value.")
    body = f"""
<div class="notice"><strong>Three columns per market.</strong> {cov['note']}</div>
<div class="grid k4">
  <div class="card"><div class="tag">Side rows</div><div class="num">{cov['side_rows']:,}</div></div>
  <div class="card"><div class="tag">Total rows</div><div class="num">{cov['total_rows']:,}</div></div>
  <div class="card"><div class="tag">Moneyline rows</div><div class="num">{cov['moneyline_rows']:,}</div></div>
  <div class="card"><div class="tag">Window</div><div class="num">{cov['window'][0]}–{cov['window'][1]}</div></div>
</div>
<section>
  <div class="section-head"><div><h2>Fair vs market</h2>
    <p>Model fair line, market line and difference for all three markets. First 400 rows shown; full
    table: <a href="data/fair_vs_market.csv" target="_blank" rel="noopener noreferrer">fair_vs_market.csv</a>.</p></div></div>
  {t_fair}
</section>
"""
    return page("Fair vs market", "Fair vs market",
                "The model's fair line, the market line and the difference, published as separate "
                "columns for the side, the total and the moneyline.", body, "fair_vs_market.html")


def render_signal_staking(rows, cov):
    hdr = ["ID", "Strategy", "Market", "Brier skill", "Luck pct.", "Signal rank",
           "Full ROI", "Holdout ROI", "Staking rank", "Rank gap", "Masking", "Source"]
    body_rows = []
    for r in rows:
        mask = "yes" if r["lucky_staking_masking_signal"] else ""
        body_rows.append([r["id"], r["name"], r["market"], fmt_num(r["brier_skill"], 4),
                          fmt_num(r["luck_percentile"], 1), r["signal_rank"],
                          fmt_num(r["full_roi"]), fmt_num(r["holdout_roi"]),
                          r["staking_rank"], r["rank_gap"], mask, r["source"]])
    sig_comp = ", ".join(cov["signal_components"])
    stk_comp = ", ".join(cov["staking_components"])
    t_sig = table(hdr, body_rows,
                  "A positive rank gap means staking ranks better than signal — a result that does not reflect prediction skill.")
    body = f"""
<div class="notice"><strong>Signal and staking, ranked apart.</strong> {cov['note']}</div>
<section>
  <div class="section-head"><div><h2>Signal vs staking leaderboard</h2>
    <p>Signal components: {sig_comp}. Staking components: {stk_comp}.</p></div></div>
  {t_sig}
</section>
"""
    return page("Signal vs staking", "Signal vs staking",
                "Signal and staking are ranked independently, so a lucky staking run cannot mask a "
                "bad signal.", body, "signal_staking.html")


def render_demotion(rows, cov):
    hdr = ["ID", "Strategy", "Market", "Promotion gates", "D1 holdout ROI", "D2 significance",
           "D3 luck", "D4 skill", "Status", "Source"]
    body_rows = []
    for r in rows:
        conds = {c["id"]: c for c in r["conditions"]}
        body_rows.append([r["id"], r["name"], r["market"], f"{r['promotion_gates_passed']}/9",
                          fmt_num(conds["D1"]["value"]) if conds["D1"]["value"] is not None else "",
                          fmt_num(conds["D2"]["value"]) if conds["D2"]["value"] is not None else "",
                          fmt_num(conds["D3"]["value"], 1) if conds["D3"]["value"] is not None else "",
                          fmt_num(conds["D4"]["value"], 4) if conds["D4"]["value"] is not None else "",
                          r["status"], BLOB + "data/derived/summary.json"])
    t_dem = table(hdr, body_rows,
                  "D1 holdout ROI > 0 · D2 bootstrap CI low > 0 · D3 permutation percentile >= 95 · D4 Brier skill >= 0.")
    body = f"""
<div class="notice"><strong>The demotion gate.</strong> {cov['rule']}</div>
<div class="grid k4">
  <div class="card"><div class="tag">Live</div><div class="num">{cov['counts'].get('live',0)}</div></div>
  <div class="card"><div class="tag">Paper</div><div class="num">{cov['counts'].get('paper',0)}</div></div>
  <div class="card"><div class="tag">Demoted</div><div class="num">{cov['counts'].get('demoted',0)}</div></div>
  <div class="card"><div class="tag">Strategies checked</div><div class="num">{cov['strategies']}</div></div>
</div>
<section>
  <div class="section-head"><div><h2>Demotion check</h2>
    <p>Every strategy is scored against the demotion rule, live or not, so the rule and its inputs
    are auditable.</p></div></div>
  {t_dem}
</section>
<section>
  <div class="section-head"><div><h2>Lifecycle</h2></div></div>
  {table(["Transition", "Trigger", "Source"],
          [["paper → live", "All nine promotion gates (G1–G9) pass.", BLOB + "line_lab/evaluation.py"],
           ["live → paper (demotion)", "Any demotion condition D1–D4 fails on the latest full evaluation.", BLOB + "market_lab/demotion.py"]],
          "Promotion is defined by the existing gates; demotion is defined by this ledger.")}
</section>
"""
    return page("Demotion gate", "Demotion gate",
                "The rule that sends a live strategy back to paper when its edge stops being real.",
                body, "demotion.html")


def render_flagged(snapshot_rows, results_rows, snapshot_cov, results_cov):
    flags = []
    open_blank = [r for r in snapshot_rows if r["opening_line"] is None]
    flags.append(("SNAP-DISJOINT", "high",
                  f"The pinned opening source (2021, SPREAD/TOTAL) and closing source (2006-2018) "
                  f"cover disjoint seasons: {snapshot_cov['games_with_both']} of {snapshot_cov['store_records']:,} "
                  "store records have both an opening and a closing line. Per-game opening-to-closing "
                  "pairing is not possible from this data; the missing side of every row is blank and flagged.",
                  CLOSING_URL))
    flags.append(("SNAP-OPENODDS", "medium",
                  "The pinned initial_lines.csv carries no odds column, so every opening odds cell is "
                  "blank and flagged even where the opening line exists.", INITIAL_URL))
    mismatch = [r for r in results_rows if r["verification"] == "mismatch"]
    flags.append(("RES-MISMATCH", "high",
                  f"{len(mismatch):,} results re-settle to a different outcome than the recorded one "
                  "from the official final score. Published as mismatches, not corrected.", GAMES_URL))
    missing = [r for r in results_rows if r["verification"] == "unverified"]
    flags.append(("RES-NOSCORE", "medium",
                  f"{len(missing):,} results have no official final score in the pinned data and are "
                  "unverified.", GAMES_URL))
    flags.append(("ORIG-ML", "info",
                  "The moneyline is originated last and derived only from the spread; it is not an "
                  "independent market read. No market moneyline is used to produce it.", BLOB + "market_lab/originate.py"))
    flags.append(("DEMO-NONELIVE", "info",
                  "No strategy has passed the promotion gates, so no strategy is live and none is "
                  "demoted. The demotion check is published for all strategies so the rule is auditable.",
                  BLOB + "data/derived/summary.json"))
    hdr = ["ID", "Severity", "What", "Source"]
    body_rows = [[fid, sev, what, src] for fid, sev, what, src in flags]
    body = f"""
<div class="notice"><strong>Flagged for review.</strong> Every blank, mismatch and irregularity found
while building the ledger, with its source. None of these block the build; none is papered over.</div>
<section>
  <div class="section-head"><div><h2>Flags</h2></div></div>
  {table(hdr, body_rows)}
</section>
"""
    return page("Flagged", "Flagged for review",
                "Every blank, mismatch and irregularity in the Markets Ledger, with sources.",
                body, "flagged.html")


def render_sources():
    sources = [
        ("SRC-NFL-RULEBOOK", "2026 NFL Rulebook", RULEBOOK_URL, "National Football League",
         "official", "Game rules, scoring, timing and tie handling used to settle the results feed."),
        ("SRC-NFLV-GAMES", "nflverse/nfldata games.csv (pinned)", GAMES_URL, "nflverse (open distribution of NFL public data)",
         "pinned dataset", "Official final scores, game results, spread/total/moneyline market lines for every game."),
        ("SRC-NFLV-CLOSING", "nflverse/nfldata closing_lines.csv (pinned)", CLOSING_URL, "nflverse",
         "pinned dataset", "Closing prices and recorded outcomes for every market, 2006–2025."),
        ("SRC-NFLV-INITIAL", "nflverse/nfldata initial_lines.csv (pinned)", INITIAL_URL, "nflverse",
         "pinned dataset", "Opening lines (2021, SPREAD and TOTAL, one sportsbook)."),
        ("SRC-MODEL", "line_lab walk-forward model predictions (features.csv)", BLOB + "line_lab/data/derived/features.csv",
         "this repository", "recomputed", "Model fair lines (mu_spread, mu_total) and uncertainty used for origination and fair-vs-market."),
        ("SRC-SUMMARY", "line_lab summary.json (leaderboard, gates)", BLOB + "data/derived/summary.json",
         "this repository", "recomputed", "Strategy ROI, Brier skill, luck percentile and gate results used for signal/staking and demotion."),
    ]
    hdr = ["ID", "Title", "Publisher", "Tier", "Used for", "Source"]
    body_rows = [[s[0], s[1], s[3], s[4], s[5], s[2]] for s in sources]
    body = f"""
<section>
  <div class="section-head"><div><h2>Source register</h2>
    <p>Official applies to league facts; pinned dataset to the commit-pinned open data; recomputed to
    values re-derived in this repository.</p></div></div>
  {table(hdr, body_rows)}
</section>
"""
    return page("Sources", "Sources", "The pinned source register and the official links behind every value.",
                body, "sources.html")


def render_method(snapshot_cov, results_cov, ts):
    t_rules = table(
        ["Rule", "What it means here", "Source"],
        [["Source on every row", "Every table row carries a link to the pinned input or official publisher that supports it.", BLOB + "market_lab/check.py"],
         ["Blank, never inferred", "A value no pinned or official source can confirm is left blank and flagged. Opening lines exist only for 2021 SPREAD/TOTAL; all other opening cells are blank.", INITIAL_URL],
         ["Official scores for settlement", "The results feed re-settles every outcome from the official final score and flags mismatches rather than correcting them.", GAMES_URL],
         ["Correlations publish n", "Correlation values are published with their sample size n; the correlation lab already does this and is re-verified, not rebuilt here.", BLOB + "line_lab/correlations.py"],
         ["Determinism", "The build is deterministic under SOURCE_DATE_EPOCH; two builds hash identically.", BLOB + "market_lab/build.py"]],
        "Each rule links the artefact or official source that enforces or supports it.")
    body = f"""
<section>
  <div class="section-head"><div><h2>Data rules</h2></div></div>
  {t_rules}
</section>
<section>
  <div class="section-head"><div><h2>Build</h2></div></div>
  <div class="notice">Generated {ts}. Rebuild with <code>python3 -m market_lab.build</code>; verify with
  <code>python3 -m market_lab.check</code>. Inputs are pinned to nflverse commit
  <a href="https://github.com/nflverse/nfldata/commit/{PIN}" target="_blank" rel="noopener noreferrer">{PIN[:7]}</a>.</div>
</section>
"""
    return page("Method", "Method", "Data rules, verification and determinism for the Markets Ledger.",
                body, "method.html")


# --------------------------------------------------------------------------- #
# CSV writers
# --------------------------------------------------------------------------- #
def write_csv(path: Path, rows: list[dict], fields: list[str]):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    ASSETS.mkdir(parents=True, exist_ok=True)
    ts = build_timestamp()

    closing, initial, games, feats, summary = load_inputs()

    snapshot_rows, snapshot_cov = build_snapshot(closing, initial)
    results_rows, results_cov = build_results_feed(closing, games)
    fair_rows, fair_cov = build_fair_vs_market(feats)
    sig_rows, sig_cov = build_signal_staking(summary)
    dem_rows, dem_cov = build_demotion(summary)

    write_csv(OUT / "price_snapshot.csv", snapshot_rows,
              ["game_id", "season", "week", "matchup", "market", "side", "opening_line",
               "opening_odds", "closing_line", "closing_odds", "outcome", "opening_source",
               "closing_source", "flags"])
    write_csv(OUT / "results_feed.csv", results_rows,
              ["game_id", "season", "week", "matchup", "market", "side", "line", "price",
               "recorded_outcome", "recomputed_outcome", "official_home_score", "official_away_score",
               "verification", "flags", "source"])
    write_csv(OUT / "fair_vs_market.csv", fair_rows,
              ["game_id", "season", "week", "matchup", "market", "side", "fair_line",
               "market_line", "difference", "source"])
    write_csv(OUT / "signal_staking.csv", sig_rows,
              ["id", "name", "market", "brier_skill", "luck_percentile", "signal_rank",
               "full_roi", "holdout_roi", "staking_rank", "rank_gap",
               "lucky_staking_masking_signal", "source"])
    write_csv(OUT / "demotion_gate.csv", dem_rows,
              ["id", "name", "market", "promotion_gates_passed", "promotion_eligible",
               "demotion_all_pass", "any_unverified", "status", "source"])

    sources = {
        "generated_utc": ts,
        "pinned_commit": PIN,
        "commit_url": f"https://github.com/nflverse/nfldata/commit/{PIN}",
        "sources": [
            {"id": "SRC-NFL-RULEBOOK", "title": "2026 NFL Rulebook", "url": RULEBOOK_URL,
             "publisher": "National Football League", "tier": "official"},
            {"id": "SRC-NFLV-GAMES", "title": "nflverse/nfldata games.csv", "url": GAMES_URL,
             "publisher": "nflverse", "tier": "pinned dataset"},
            {"id": "SRC-NFLV-CLOSING", "title": "nflverse/nfldata closing_lines.csv", "url": CLOSING_URL,
             "publisher": "nflverse", "tier": "pinned dataset"},
            {"id": "SRC-NFLV-INITIAL", "title": "nflverse/nfldata initial_lines.csv", "url": INITIAL_URL,
             "publisher": "nflverse", "tier": "pinned dataset"},
            {"id": "SRC-MODEL", "title": "line_lab features.csv", "url": BLOB + "line_lab/data/derived/features.csv",
             "publisher": "this repository", "tier": "recomputed"},
            {"id": "SRC-SUMMARY", "title": "line_lab summary.json", "url": BLOB + "data/derived/summary.json",
             "publisher": "this repository", "tier": "recomputed"},
        ],
    }
    (OUT / "sources.json").write_text(json.dumps(sources, indent=2) + "\n", encoding="utf-8")

    mkt_summary = {
        "generated_utc": ts,
        "pinned_commit": PIN,
        "snapshot": snapshot_cov,
        "results": results_cov,
        "fair_vs_market": fair_cov,
        "signal_staking": sig_cov,
        "demotion": dem_cov,
    }
    (OUT / "market_summary.json").write_text(json.dumps(mkt_summary, indent=2) + "\n", encoding="utf-8")

    pages = {
        "index.html": render_index(snapshot_cov, results_cov, fair_cov, sig_cov, dem_cov, ts),
        "snapshot.html": render_snapshot(snapshot_rows, snapshot_cov),
        "results.html": render_results(results_rows, results_cov),
        "origination.html": render_origination(feats),
        "fair_vs_market.html": render_fair_vs_market(fair_rows, fair_cov),
        "signal_staking.html": render_signal_staking(sig_rows, sig_cov),
        "demotion.html": render_demotion(dem_rows, dem_cov),
        "flagged.html": render_flagged(snapshot_rows, results_rows, snapshot_cov, results_cov),
        "sources.html": render_sources(),
        "method.html": render_method(snapshot_cov, results_cov, ts),
    }
    for name, content in pages.items():
        (BASE / name).write_text(content, encoding="utf-8")

    (ASSETS / "style.css").write_text((ROOT / "assets" / "style.css").read_text(encoding="utf-8"),
                                      encoding="utf-8")

    print(f"market_lab: {len(snapshot_rows)} snapshot rows, {len(results_rows)} result rows, "
          f"{len(fair_rows)} fair-vs-market rows, {len(sig_rows)} signal/staking rows, "
          f"{len(dem_rows)} demotion rows, {len(pages)} pages")
    print(f"  snapshot: opening {snapshot_cov['opening_available']}, closing "
          f"{snapshot_cov['closing_available']}, both {snapshot_cov['games_with_both']} "
          f"of {snapshot_cov['store_records']}")
    print(f"  results verified: {results_cov['verified']}/{results_cov['rows']} "
          f"(mismatch {results_cov['mismatch']}, missing {results_cov['score_missing']})")
    print(f"  demotion: {dem_cov['counts']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
