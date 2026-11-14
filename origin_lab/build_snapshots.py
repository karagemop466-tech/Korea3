#!/usr/bin/env python3
"""Requirement 1 — the price-snapshot store, and Requirement 2 — the results feed.

PRICE SNAPSHOTS
    One row per (game, market, side). Each row records the opening number and price, the closing
    number and price, every source that carries them, and the open-to-close move. Where a number does
    not exist in any source this repository holds, the cell is blank and the row is flagged; it is
    never filled in from a model, a memory or a plausible guess.

    What "opening" and "closing" can actually mean here is itself a finding, and it is published on
    the page rather than buried:

    * Opening numbers exist for 272 games. One season (2021), one book (Westgate), two markets
      (spread and total). There is no opening moneyline anywhere in this repository.
    * Closing numbers exist for 7,412 spread rows and 7,412 total rows from games.csv, and a second,
      independent closing source (closing_lines.csv) covers 2006-2018.
    * Neither file carries a capture timestamp. A price snapshot without a time is a price with an
      unknown age; that is flagged, not smoothed over.

RESULTS FEED
    One row per (game, market): the settled outcome as the published rules define it, plus the
    official league figures (final score) that decide it. Rows are checked against internal
    arithmetic and, for 2026, against the league's own standings page.

Writes: origin_lab/data/price_snapshots.json, origin_lab/data/results_feed.json,
        origin_lab/data/price_snapshots.csv, origin_lab/data/results_feed.csv
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import lib

MARKETS = ("SIDE", "TOTAL", "MONEYLINE")


def _wcsv(path: Path, header, rows):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(header)
        w.writerows(rows)


def load_inputs():
    games = [r for r in lib.load_csv(lib.RAW / "games.csv")]
    closing = lib.load_csv(lib.RAW / "closing_lines.csv")
    initial = lib.load_csv(lib.RAW / "initial_lines.csv")
    sc = lib.load_csv(lib.RAW / "sc_lines.csv")
    return games, closing, initial, sc


def index_closing(closing):
    """alt_game_id -> {'SPREAD': {side: line}, 'TOTAL': {side: line}, 'MONEYLINE': {side: odds}}"""
    out = {}
    for r in closing:
        g = out.setdefault(r["alt_game_id"], {"SPREAD": {}, "TOTAL": {}, "MONEYLINE": {}, "OUTCOME": {}})
        t = r["type"]
        if t == "MONEYLINE":
            g["MONEYLINE"][r["side"]] = r["odds"]
        else:
            g[t][r["side"]] = r["line"]
        g["OUTCOME"][(t, r["side"])] = r["outcome"]
    return out


def index_initial(initial):
    out = {}
    for r in initial:
        g = out.setdefault(r["about"], {"SPREAD": {}, "TOTAL": {}, "book": r["sportsbook"], "season": r["season"]})
        if r["type"] == "TOTAL":
            g["TOTAL"][r["side"]] = r["line"]
        else:
            g["SPREAD"][r["side"]] = r["line"]
    return out


def index_sc(sc):
    out = {}
    for r in sc:
        out.setdefault(r["game_id"], {})[r["side"]] = r["line"]
    return out


def american_to_favoured(american):
    """American price/spread for a side -> points that side is favoured by (negative = underdog)."""
    if american is None or american == "":
        return None
    try:
        return -float(american)
    except (TypeError, ValueError):
        return None


def build_price_snapshots(games, closing, initial, sc):
    clx, inx, scx = index_closing(closing), index_initial(initial), index_sc(sc)

    rows = []
    coverage = {m: {"games_total": 0, "open": 0, "close": 0, "close_second": 0, "both": 0,
                    "seasons": set()} for m in MARKETS}

    for g in games:
        if g["game_type"] != "REG":
            continue
        gid = g["game_id"]
        season = lib.fint(g, "season")
        week = lib.fint(g, "week")
        home, away = g["home_team"], g["away_team"]

        init = inx.get(gid)
        cl = clx.get(gid)
        scline = scx.get(gid)

        mkt_close = {
            "SIDE": lib.fnum(g, "spread_line"),
            "TOTAL": lib.fnum(g, "total_line"),
            "MONEYLINE": None,
        }
        # games.csv moneylines are American prices, not numbers
        ml_home = lib.fnum(g, "home_moneyline")
        ml_away = lib.fnum(g, "away_moneyline")

        for market in MARKETS:
            # sides and what the "number" means for each
            if market == "SIDE":
                sides = [("home", home), ("away", away)]
            elif market == "TOTAL":
                sides = [("over", "Over"), ("under", "Under")]
            else:
                sides = [("home", home), ("away", away)]

            for side_label, team in sides:
                cov = coverage[market]
                if side_label in ("home", "over"):
                    cov["games_total"] += 1
                    cov["seasons"].add(season)

                close_num = None
                close_price = None
                close_src = []
                if market == "SIDE":
                    base = mkt_close["SIDE"]
                    if base is not None:
                        close_num = base if side_label == "home" else -base
                    close_price = (lib.fnum(g, "home_spread_odds") if side_label == "home"
                                   else lib.fnum(g, "away_spread_odds"))
                    if close_price is not None:
                        close_src.append("S05")
                elif market == "TOTAL":
                    close_num = mkt_close["TOTAL"]
                    close_price = (lib.fnum(g, "over_odds") if side_label == "over"
                                   else lib.fnum(g, "under_odds"))
                    if close_price is not None:
                        close_src.append("S05")
                else:
                    close_price = ml_home if side_label == "home" else ml_away
                    if close_price is not None:
                        close_src.append("S05")

                # second closing source: closing_lines.csv, American per side
                alt_num = None
                alt_price = None
                alt_src = []
                if cl:
                    if market == "MONEYLINE":
                        v = cl["MONEYLINE"].get(team)
                        if v not in (None, ""):
                            alt_price = lib.fnum({"v": v}, "v")
                            alt_src.append("S06")
                    else:
                        key = team if market == "SIDE" else side_label.capitalize()
                        v = cl["SPREAD" if market == "SIDE" else market].get(key)
                        if v not in (None, ""):
                            alt_num = american_to_favoured(v)
                            alt_src.append("S06")

                open_num = None
                open_price = None
                open_src = []
                open_book = None
                if init and market in ("SIDE", "TOTAL"):
                    key = team if market == "SIDE" else side_label.capitalize()
                    v = init["SPREAD" if market == "SIDE" else market].get(key)
                    if v not in (None, ""):
                        open_num = american_to_favoured(v)
                        open_book = init["book"]
                        open_src.append("S07")

                # sc_lines is a secondary-book spread only; published as a cross-check, never as
                # an opening number, because the file does not say when it was captured.
                sc_num = None
                if market == "SIDE" and scline and team in scline:
                    sc_num = american_to_favoured(scline[team])

                has_open = open_num is not None
                has_close = close_num is not None or (market == "MONEYLINE" and close_price is not None)
                primary = side_label in ("home", "over")
                if primary:
                    if has_open:
                        cov["open"] += 1
                    if has_close:
                        cov["close"] += 1
                    if alt_num is not None or alt_price is not None:
                        cov["close_second"] += 1
                    if has_open and has_close:
                        cov["both"] += 1

                move = None if not (has_open and has_close and close_num is not None) else round(close_num - open_num, 4)

                if has_open and has_close:
                    status = "complete"
                elif has_open:
                    status = "open_only"
                elif has_close:
                    status = "close_only"
                else:
                    status = "none"

                rows.append({
                    "game_id": gid, "season": season, "week": week,
                    "gameday": g.get("gameday", ""),
                    "away": away, "home": home, "market": market, "side": side_label,
                    "side_team": team,
                    "open_number": open_num, "open_price": open_price,
                    "open_book": open_book, "open_sources": open_src,
                    "close_number": close_num, "close_price": close_price,
                    "close_sources": close_src,
                    "alt_close_number": alt_num, "alt_close_price": alt_price,
                    "alt_close_sources": alt_src,
                    "sc_check_number": sc_num,
                    "move": move,
                    "captured_at_open": None, "captured_at_close": None,
                    "status": status,
                })

    for m in MARKETS:
        coverage[m]["seasons"] = sorted({s for s in coverage[m]["seasons"] if s})

    # open-to-close movement distribution, for the SIDE market where both exist
    moves = [r["move"] for r in rows if r["market"] == "SIDE" and r["side"] == "home" and r["move"] is not None]

    out = {
        "_meta": {
            "generated_by": "origin_lab/build_snapshots.py",
            "session": "arena/5f341290-korea3",
            "convention": "SIDE number = points the listed side is favoured by, positive = favoured, negative = underdog. TOTAL number = the game total, identical on both sides. MONEYLINE has no number, only a price. Prices are American. move = close_number - open_number.",
            "why_blank": "An opening number is printed in only one file (initial_lines.csv: 2021, Westgate, spread and total). Every opening moneyline cell is blank because no source in this repository prints one. No file carries a capture timestamp, so both captured_at fields are blank.",
        },
        "coverage": coverage,
        "movement": {
            "n": len(moves),
            "mean": lib.round_or_none(lib.mean(moves), 4),
            "pstdev": lib.round_or_none(lib.pstdev(moves), 4),
            "min": lib.round_or_none(min(moves), 2) if moves else None,
            "max": lib.round_or_none(max(moves), 2) if moves else None,
            "note": "Computed only over SIDE rows that carry both an opening and a closing number.",
        },
        "rows": rows,
    }

    (lib.DATA / "price_snapshots.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    _wcsv(lib.DATA / "price_snapshots.csv",
          ["game_id", "season", "week", "gameday", "away", "home", "market", "side", "side_team",
           "open_number", "open_price", "open_book", "status", "close_number", "close_price",
           "alt_close_number", "alt_close_price", "sc_check_number", "move"],
          [[r["game_id"], r["season"], r["week"], r["gameday"], r["away"], r["home"], r["market"],
            r["side"], r["side_team"], "" if r["open_number"] is None else r["open_number"],
            "" if r["open_price"] is None else r["open_price"], r["open_book"] or "", r["status"],
            "" if r["close_number"] is None else r["close_number"],
            "" if r["close_price"] is None else r["close_price"],
            "" if r["alt_close_number"] is None else r["alt_close_number"],
            "" if r["alt_close_price"] is None else r["alt_close_price"],
            "" if r["sc_check_number"] is None else r["sc_check_number"],
            "" if r["move"] is None else r["move"]] for r in rows])
    return out


def build_results_feed(games, official):
    """One row per (game, market): what the market paid out, and the official figures that decided it."""
    feed26 = {r["game_id"]: r for r in official["feed"]}
    rows = []
    checks = {"arith": 0, "settled": 0, "pending": 0, "pushes": 0, "ties": 0}

    for g in games:
        if g["game_type"] != "REG":
            continue
        gid = g["game_id"]
        season = lib.fint(g, "season")
        week = lib.fint(g, "week")
        home, away = g["home_team"], g["away_team"]

        off = feed26.get(gid)
        if off:
            a, h = off["away_score"], off["home_score"]
            src_ids = [off["source_id"]]
            ver = off["verification"]
            url = off["source_url"]
        else:
            a, h = lib.fint(g, "away_score"), lib.fint(g, "home_score")
            src_ids = ["S05"]
            ver = "official_type_dataset"
            url = lib.SOURCES["S05"]["url"]

        margin = None if (a is None or h is None) else h - a
        total = None if (a is None or h is None) else h + a

        # internal arithmetic check against the dataset's own published columns
        ds_res, ds_tot = lib.fint(g, "result"), lib.fint(g, "total")
        arith_ok = True
        if a is not None and h is not None and off is None:
            arith_ok = (ds_res == margin) and (ds_tot == total)
        if not arith_ok:
            checks["arith"] += 1

        spread = lib.fnum(g, "spread_line")
        tot_line = lib.fnum(g, "total_line")

        settled = a is not None and h is not None
        for market in MARKETS:
            outcome = None
            basis = None
            if market == "SIDE":
                basis = spread
                if settled and spread is not None:
                    d = margin - spread
                    outcome = "home_cover" if d > 0 else ("away_cover" if d < 0 else "push")
                    if d == 0:
                        checks["pushes"] += 1
            elif market == "TOTAL":
                basis = tot_line
                if settled and tot_line is not None:
                    d = total - tot_line
                    outcome = "over" if d > 0 else ("under" if d < 0 else "push")
                    if d == 0:
                        checks["pushes"] += 1
            else:
                basis = None
                if settled:
                    outcome = "home" if h > a else ("away" if a > h else "tie")
                    if outcome == "tie":
                        checks["ties"] += 1

            if settled:
                checks["settled"] += 1
            else:
                checks["pending"] += 1

            rows.append({
                "game_id": gid, "season": season, "week": week,
                "gameday": g.get("gameday", ""),
                "away": away, "home": home, "market": market,
                "away_score": a, "home_score": h,
                "margin": margin, "total": total,
                "market_number": basis,
                "outcome": outcome,
                "status": "final" if settled else "pending",
                "verification": ver if settled else "not_applicable",
                "sources": src_ids,
                "source_url": url,
                "arithmetic_ok": arith_ok,
            })

    by_season = {}
    for r in rows:
        s = by_season.setdefault(r["season"], {"games": 0, "final": 0, "pending": 0,
                                               "official_direct": 0, "dataset": 0})
        if r["market"] == "SIDE":
            s["games"] += 1
            if r["status"] == "final":
                s["final"] += 1
            else:
                s["pending"] += 1
            if r["verification"] == "official_direct":
                s["official_direct"] += 1
            elif r["verification"] == "official_type_dataset":
                s["dataset"] += 1

    out = {
        "_meta": {
            "generated_by": "origin_lab/build_snapshots.py",
            "session": "arena/5f341290-korea3",
            "settlement_rule": "SIDE: home covers when (home_score - away_score) > spread, where spread is positive when the home team is favoured. TOTAL: over when (home + away) > total. MONEYLINE: the team with more points wins; equal scores is a tie. A tie or an exact landing on the number settles as a push for SIDE and TOTAL and as a tie for MONEYLINE.",
            "rule_source": "https://operations.nfl.com/rules-officiating/2026-nfl-rulebook",
            "verification_note": "official_direct = transcribed from the NFL.com page named on the row. official_type_dataset = a figure only the league produces (a final score), carried in the pinned nflverse snapshot; for 2026 it is reconciled club by club against the official standings in parse_official.py. not_applicable = the game has not been played.",
        },
        "checks": checks,
        "by_season": by_season,
        "rows": rows,
    }
    (lib.DATA / "results_feed.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    _wcsv(lib.DATA / "results_feed.csv",
          ["game_id", "season", "week", "gameday", "away", "home", "market", "away_score",
           "home_score", "margin", "total", "market_number", "outcome", "status",
           "verification", "source_url"],
          [[r["game_id"], r["season"], r["week"], r["gameday"], r["away"], r["home"], r["market"],
            "" if r["away_score"] is None else r["away_score"],
            "" if r["home_score"] is None else r["home_score"],
            "" if r["margin"] is None else r["margin"], "" if r["total"] is None else r["total"],
            "" if r["market_number"] is None else r["market_number"], r["outcome"] or "",
            r["status"], r["verification"], r["source_url"]] for r in rows])
    return out


def main():
    games, closing, initial, sc = load_inputs()
    official = json.loads((lib.DATA / "official_results_2026.json").read_text(encoding="utf-8"))
    snap = build_price_snapshots(games, closing, initial, sc)
    feed = build_results_feed(games, official)

    print("price snapshots: %d rows" % len(snap["rows"]))
    for m in MARKETS:
        c = snap["coverage"][m]
        print(f"  {m}: {c['games_total']} priced games | open {c['open']} | close {c['close']} | "
              f"second close {c['close_second']} | both {c['both']}")
    print("  SIDE open->close: n=%s mean=%s sd=%s" % (
        snap["movement"]["n"], snap["movement"]["mean"], snap["movement"]["pstdev"]))
    print("results feed: %d rows (games x markets)" % len(feed["rows"]))
    print("  settled %d, pending %d, pushes %d, ties %d, arithmetic failures %d" % (
        feed["checks"]["settled"], feed["checks"]["pending"], feed["checks"]["pushes"],
        feed["checks"]["ties"], feed["checks"]["arith"]))


if __name__ == "__main__":
    main()
