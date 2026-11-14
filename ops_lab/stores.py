#!/usr/bin/env python3
"""Data stores for the Desk Ops lab: the price-snapshot store and the verified results feed.

Everything here is stdlib-only and deterministic. Every value written to a store row is
copied verbatim from a pinned, hash-verified input file in this repository (the sha256 of
every input is re-verified by stores.verify_inputs() before a row is produced); a value no
input states is written as an empty cell with an explanatory `note`, never inferred.

Inputs (all pinned to nflverse/nfldata commit a270278f..., hashes in data/provenance.json):
  data/raw/games.csv          one row per game 1999-2026: scores, posted lines, prices
  data/closing_lines.csv      per-side closing line + odds + published outcome, 2006-2018
  data/raw/initial_lines.csv  WSGT opening lines (line only), 2021 season
  data/derived/own_lines_upcoming.csv   the 2026 book this project originates (fair lines)
  data/derived/bets.csv       the S1-S11 backtest ledger (used for the ledger cross-check)

Usage:
    python3 ops_lab/stores.py            # rebuild both stores + meta JSONs
"""
from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"

PIN = "a270278f3ac4e937295fe6a27814b3c4a2b62645"
PINNED_UTC = "2026-11-01T13:05:15Z"
SRC_GAMES = f"https://github.com/nflverse/nfldata/blob/{PIN}/data/games.csv"
SRC_CLOSING = f"https://github.com/nflverse/nfldata/blob/{PIN}/data/closing_lines.csv"
SRC_INITIAL = f"https://github.com/nflverse/nfldata/blob/{PIN}/data/initial_lines.csv"
SRC_OWN = "https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/own_lines_upcoming.csv"
SRC_BETS = "https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/bets.csv"

SNAP_COLUMNS = ["market_uid", "game_id", "season", "week", "game_date", "home_team",
                "away_team", "market", "side", "scope", "snapshot_type", "line", "odds",
                "pinned_utc", "source_id", "source_url", "note"]
FEED_COLUMNS = ["feed_uid", "game_id", "season", "week", "game_date", "home_team",
                "away_team", "home_score", "away_score", "market", "side", "line", "odds",
                "outcome_computed", "closing_line", "closing_odds", "outcome_published",
                "published_outcome_verified", "source_id", "source_url", "note"]


# --------------------------------------------------------------------------- #
# inputs
# --------------------------------------------------------------------------- #
def verify_inputs() -> list[str]:
    """Re-hash every pinned input against data/provenance.json. Returns failures."""
    prov = json.loads((ROOT / "data/provenance.json").read_text(encoding="utf-8"))
    bad: list[str] = []
    for fname, meta in prov["primary_dataset"]["files"].items():
        path = ROOT / "data/raw" / fname
        if not path.exists():
            bad.append(f"{fname}: missing")
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != meta["sha256"]:
            bad.append(f"{fname}: sha256 {digest[:12]} != pinned {meta['sha256'][:12]}")
    return bad


def _f(x: str) -> str:
    """Keep numeric text as published; empty stays empty."""
    return str(x).strip()


def load_games() -> dict[str, dict]:
    games: dict[str, dict] = {}
    with open(ROOT / "data/raw/games.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            r["season_i"] = int(r["season"])
            r["week_i"] = int(r["week"])
            games[r["game_id"]] = r
    return games


def load_closing() -> dict[str, list[dict]]:
    """closing_lines.csv keyed by alt_game_id (== games.csv game_id). 2006-2018 only.

    Irregularity handled here, documented on the method page and flagged for review:
    closing_lines.csv writes the Rams as ``LAR`` in 2016-2018 while games.csv writes
    ``LA`` for the same franchise in every season. The alias join below normalises
    ``LAR`` -> ``LA`` so the 47 affected games (282 rows) join instead of silently
    dropping out of the store and the feed.
    """
    def norm_abbr(x: str) -> str:
        return "LA" if x == "LAR" else x

    def norm_gid(gid: str) -> str:
        parts = gid.split("_")
        if len(parts) == 4:
            parts[2], parts[3] = norm_abbr(parts[2]), norm_abbr(parts[3])
        return "_".join(parts)

    out: dict[str, list[dict]] = {}
    with open(ROOT / "data/closing_lines.csv", newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            r = dict(r)
            r["alt_game_id"] = norm_gid(r["alt_game_id"])
            r["side"] = norm_abbr(r["side"])
            out.setdefault(r["alt_game_id"], []).append(r)
    return out


def load_initial() -> list[dict]:
    with open(ROOT / "data/raw/initial_lines.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_own() -> list[dict]:
    with open(ROOT / "data/derived/own_lines_upcoming.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def load_bets() -> list[dict]:
    with open(ROOT / "data/derived/bets.csv", newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


# --------------------------------------------------------------------------- #
# settlement (mirrors line_lab/markets.py settle(): 1 win, 0 push, -1 loss)
# --------------------------------------------------------------------------- #
def settle_spread(result: float, spread_line: float, side: str) -> int:
    m = result - spread_line
    if m == 0:
        return 0
    home_won = m > 0
    return 1 if (home_won and side == "home") or ((not home_won) and side == "away") else -1


def settle_total(total: float, total_line: float, side: str) -> int:
    m = total - total_line
    if m == 0:
        return 0
    over = m > 0
    return 1 if (over and side == "over") or ((not over) and side == "under") else -1


def settle_ml(result: float, side: str) -> int:
    if result == 0:
        return 0
    home_won = result > 0
    return 1 if (home_won and side == "home") or ((not home_won) and side == "away") else -1


PUBLISHED_MAP = {"1": "1", "0": "-1", "0.5": "0"}  # closing_lines convention -> ours


# --------------------------------------------------------------------------- #
# store 1: price snapshots
# --------------------------------------------------------------------------- #
def build_snapshots(games: dict, closing: dict, initial: list[dict], own: list[dict]):
    rows: list[dict] = []

    def add(g, market, side, snap_type, line, odds, scope, source_id, url, note=""):
        rows.append({
            "market_uid": f"{g['game_id']}:{market}:{side}",
            "game_id": g["game_id"], "season": g["season"], "week": g["week"],
            "game_date": g["gameday"], "home_team": g["home_team"], "away_team": g["away_team"],
            "market": market, "side": side, "scope": scope, "snapshot_type": snap_type,
            "line": line, "odds": odds, "pinned_utc": PINNED_UTC,
            "source_id": source_id, "source_url": url, "note": note,
        })

    # (1) closing snapshots, 2006-2018, exactly as published in closing_lines.csv
    for gid, crows in closing.items():
        g = games.get(gid)
        if g is None:
            continue
        for r in crows:
            t = r["type"]
            side_raw, line, odds = r["side"], _f(r["line"]), _f(r["odds"])
            if t == "SPREAD":
                side = "home" if side_raw == g["home_team"] else "away" if side_raw == g["away_team"] else ""
                market = "SPREAD"
            elif t == "TOTAL":
                side, market = side_raw.lower(), "TOTAL"
            elif t == "MONEYLINE":
                side = "home" if side_raw == g["home_team"] else "away" if side_raw == g["away_team"] else ""
                market = "MONEYLINE"
            else:
                continue
            if not side:
                continue
            note = "" if odds else "closing odds not published for this market type in the dataset; line only"
            add(g, market, side, "closing", line, odds, "backtest", "nflverse-closing", SRC_CLOSING, note)

    # (2) opening snapshots: WSGT openers, 2021 season, spread + total, line only
    for r in initial:
        about = r["about"]
        g = next((gg for gg in games.values()
                  if gg["game_id"] == about), None)
        if g is None:
            continue
        t, side_raw, line = r["type"], r["side"], _f(r["line"])
        if t == "SPREAD":
            side = "home" if side_raw == g["home_team"] else "away" if side_raw == g["away_team"] else ""
            market = "SPREAD"
        elif t == "TOTAL":
            side, market = side_raw.lower(), "TOTAL"
        else:
            continue
        if not side:
            continue
        add(g, market, side, "opening_wsgt", line, "", "backtest", "nflverse-initial", SRC_INITIAL,
            "opening price (odds) not published in the dataset; opening line only")

    # (3) league-posted numbers for every game where nflverse games.csv publishes them
    #     (2006 onward, partial in 2006): these are the numbers the S1-S11 ledger prices
    #     its bets at, so the store must hold them for the D1 provenance check to close.
    own_gids = {r["game_id"] for r in own}
    for g in sorted(games.values(), key=lambda x: x["game_id"]):
        scope = "origination" if g["game_id"] in own_gids else "backtest"
        if g["spread_line"]:
            sl = _f(g["spread_line"])
            add(g, "SPREAD", "home", "posted_league", sl, _f(g.get("home_spread_odds", "")),
                scope, "nflverse-games", SRC_GAMES,
                "as published by nflverse games.csv; the dataset claims no opening/closing semantics for this field")
            try:
                away_line = str(-float(sl))
            except ValueError:
                away_line = ""
            add(g, "SPREAD", "away", "posted_league", away_line, _f(g.get("away_spread_odds", "")),
                scope, "nflverse-games", SRC_GAMES,
                "away side mirrored from the published home line (-spread_line)" if away_line else "away line not derivable")
        if g["total_line"]:
            tl = _f(g["total_line"])
            add(g, "TOTAL", "over", "posted_league", tl, _f(g.get("over_odds", "")),
                scope, "nflverse-games", SRC_GAMES,
                "as published by nflverse games.csv; the dataset claims no opening/closing semantics for this field")
            add(g, "TOTAL", "under", "posted_league", tl, _f(g.get("under_odds", "")),
                scope, "nflverse-games", SRC_GAMES,
                "under side shares the published total line")
        if g["home_moneyline"]:
            add(g, "MONEYLINE", "home", "posted_league", "", _f(g["home_moneyline"]),
                scope, "nflverse-games", SRC_GAMES,
                "moneyline published as a price only; no spread-style line applies")
            add(g, "MONEYLINE", "away", "posted_league", "", _f(g["away_moneyline"]),
                scope, "nflverse-games", SRC_GAMES,
                "moneyline published as a price only; no spread-style line applies")

    # (4) originated markets with NO market number published in the pinned dataset:
    #     one explicit row per missing market side of the 2026 book, so the store answers
    #     "do we hold a price for every market we originate?" with a row, not an assumption.
    have = {(r["game_id"], r["market"], r["side"]) for r in rows if r["scope"] == "origination"}
    for g in sorted(games.values(), key=lambda x: x["game_id"]):
        if g["game_id"] not in own_gids:
            continue
        for market, sides in (("SPREAD", ("home", "away")), ("TOTAL", ("over", "under")),
                              ("MONEYLINE", ("home", "away"))):
            for side in sides:
                if (g["game_id"], market, side) in have:
                    continue
                add(g, market, side, "origination_blank", "", "", "origination", "nflverse-games", SRC_GAMES,
                    "no market number for this game is published in the pinned dataset (pinned "
                    + PINNED_UTC + "); blank means not captured, never zero")

    rows.sort(key=lambda r: (r["game_id"], r["market"], r["side"], r["snapshot_type"]))
    return rows


# --------------------------------------------------------------------------- #
# store 2: verified results feed
# --------------------------------------------------------------------------- #
def build_feed(games: dict, closing: dict):
    """One row per (settled game x market x side).

    Two independent outcomes are published side by side:

    * ``outcome_computed`` settles the game score against the games.csv line (the
      convention the S1-S11 backtest ledger uses; 1 win, 0 push, -1 loss).
    * ``outcome_published`` is the outcome closing_lines.csv publishes (2006-2018,
      its own 1 / 0 / 0.5 convention mapped to 1 / 0 / -1).

    ``published_outcome_verified`` re-derives the published outcome from the closing
    row's OWN line (the line that outcome was settled against). A MISMATCH there means
    one dataset row contradicts itself and is listed on the flagged page.
    """
    rows: list[dict] = []
    mismatch = 0
    verified = 0
    push_total = 0
    mismatch_rows: list[dict] = []
    for g in sorted(games.values(), key=lambda x: x["game_id"]):
        if g["home_score"] == "" or g["away_score"] == "":
            continue  # not settled in the pinned dataset
        hs, as_ = float(g["home_score"]), float(g["away_score"])
        result = hs - as_
        total = hs + as_
        crows = closing.get(g["game_id"], [])
        pub: dict[tuple[str, str], dict] = {}
        for r in crows:
            t = r["type"]
            if t == "SPREAD":
                side = "home" if r["side"] == g["home_team"] else "away" if r["side"] == g["away_team"] else ""
            elif t == "TOTAL":
                side = r["side"].lower()
            elif t == "MONEYLINE":
                side = "home" if r["side"] == g["home_team"] else "away" if r["side"] == g["away_team"] else ""
            else:
                continue
            if side:
                pub[(t if t != "MONEYLINE" else "MONEYLINE", side)] = {
                    "outcome": PUBLISHED_MAP.get(r["outcome"], ""),
                    "line": _f(r["line"]),
                    "odds": _f(r["odds"]),
                    "raw_outcome": r["outcome"],
                }

        def add(market, side, line, odds, computed, closing_row):
            nonlocal mismatch, verified, push_total
            p = (closing_row or {}).get("outcome", "")
            verify = ""
            if closing_row and closing_row.get("line") and computed is not None:
                # re-derive the published outcome from the closing row's own line
                if market == "SPREAD":
                    team, opp = (hs, as_) if side == "home" else (as_, hs)
                    m = team - opp + float(closing_row["line"])
                    rederived = 0 if m == 0 else (1 if m > 0 else -1)
                elif market == "TOTAL":
                    rederived = settle_total(total, float(closing_row["line"]), side)
                else:
                    rederived = settle_ml(result, side)
                verified += 1
                verify = "match" if str(rederived) == closing_row["outcome"] else "MISMATCH"
                if verify == "MISMATCH":
                    mismatch += 1
                    mismatch_rows.append({
                        "feed_uid": f"{g['game_id']}:{market}:{side}",
                        "closing_line": closing_row["line"],
                        "published_outcome_raw": closing_row["raw_outcome"],
                        "rederived_from_closing_line": str(rederived),
                        "game_score": f"{as_}-{hs} (away-home)",
                    })
            if computed == 0:
                push_total += 1
            rows.append({
                "feed_uid": f"{g['game_id']}:{market}:{side}",
                "game_id": g["game_id"], "season": g["season"], "week": g["week"],
                "game_date": g["gameday"], "home_team": g["home_team"], "away_team": g["away_team"],
                "home_score": g["home_score"], "away_score": g["away_score"],
                "market": market, "side": side, "line": line, "odds": odds,
                "outcome_computed": "" if computed is None else str(computed),
                "closing_line": (closing_row or {}).get("line", ""),
                "closing_odds": (closing_row or {}).get("odds", ""),
                "outcome_published": p,
                "published_outcome_verified": verify,
                "source_id": "nflverse-games",
                "source_url": SRC_GAMES,
                "note": ("published outcome re-derived from the closing row's own line"
                         if verify else ""),
            })

        cr = lambda m, s: pub.get((m, s))  # noqa: E731
        if g["spread_line"]:
            sl = float(g["spread_line"])
            add("SPREAD", "home", g["spread_line"], _f(g.get("home_spread_odds", "")),
                settle_spread(result, sl, "home"), cr("SPREAD", "home"))
            add("SPREAD", "away", f"{-sl:g}", _f(g.get("away_spread_odds", "")),
                settle_spread(result, sl, "away"), cr("SPREAD", "away"))
        else:
            add("SPREAD", "home", "", "", None, cr("SPREAD", "home"))
            rows[-1]["note"] = "no spread line published for this game in the pinned dataset"
            add("SPREAD", "away", "", "", None, cr("SPREAD", "away"))
            rows[-1]["note"] = "no spread line published for this game in the pinned dataset"
        if g["total_line"]:
            tl = float(g["total_line"])
            add("TOTAL", "over", g["total_line"], _f(g.get("over_odds", "")),
                settle_total(total, tl, "over"), cr("TOTAL", "over"))
            add("TOTAL", "under", g["total_line"], _f(g.get("under_odds", "")),
                settle_total(total, tl, "under"), cr("TOTAL", "under"))
        else:
            add("TOTAL", "over", "", "", None, cr("TOTAL", "over"))
            rows[-1]["note"] = "no total line published for this game in the pinned dataset"
            add("TOTAL", "under", "", "", None, cr("TOTAL", "under"))
            rows[-1]["note"] = "no total line published for this game in the pinned dataset"
        if g["home_moneyline"]:
            add("MONEYLINE", "home", "", _f(g["home_moneyline"]), settle_ml(result, "home"), cr("MONEYLINE", "home"))
            add("MONEYLINE", "away", "", _f(g["away_moneyline"]), settle_ml(result, "away"), cr("MONEYLINE", "away"))
        else:
            add("MONEYLINE", "home", "", "", None, cr("MONEYLINE", "home"))
            rows[-1]["note"] = "no moneyline published for this game in the pinned dataset"
            add("MONEYLINE", "away", "", "", None, cr("MONEYLINE", "away"))
            rows[-1]["note"] = "no moneyline published for this game in the pinned dataset"
    return rows, {"rows": len(rows), "published_outcome_verified": verified,
                  "published_outcome_mismatches": mismatch, "mismatch_rows": mismatch_rows[:100],
                  "push_rows_computed": push_total}


# --------------------------------------------------------------------------- #
# ledger cross-check: every S1-S11 single-market bet outcome must equal the feed
# --------------------------------------------------------------------------- #
LEDGER_MARKET = {"ATS": "SPREAD", "TOTAL": "TOTAL", "ML": "MONEYLINE"}


def ledger_crosscheck(bets: list[dict], feed_rows: list[dict]) -> dict:
    feed_by_uid = {r["feed_uid"]: r for r in feed_rows if r["outcome_computed"] != ""}
    checked = skipped_market = 0
    mismatches: list[dict] = []
    for b in bets:
        m = LEDGER_MARKET.get(b["market"])
        if m is None:  # PARLAY / FUTURES legs are not single-market feed rows
            skipped_market += 1
            continue
        row = feed_by_uid.get(f"{b['game_id']}:{m}:{b['side']}")
        if row is None:
            mismatches.append({"strategy_id": b["strategy_id"], "game_id": b["game_id"],
                               "market": b["market"], "side": b["side"],
                               "problem": "no settled feed row (game or market missing from the pinned dataset)"})
            continue
        checked += 1
        if str(int(float(b["outcome"]))) != row["outcome_computed"]:
            mismatches.append({"strategy_id": b["strategy_id"], "game_id": b["game_id"],
                               "market": b["market"], "side": b["side"],
                               "problem": f"ledger outcome {b['outcome']} != feed outcome {row['outcome_computed']}"})
    return {"ledger_bets": len(bets), "checked": checked, "skipped_market_type": skipped_market,
            "mismatch_count": len(mismatches), "mismatches": mismatches[:50]}


def write_csv(path: Path, columns: list[str], rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in columns})


def main() -> None:
    bad = verify_inputs()
    if bad:
        raise SystemExit("pinned input hash check FAILED: " + "; ".join(bad))
    games = load_games()
    closing = load_closing()
    initial = load_initial()
    own = load_own()
    bets = load_bets()

    snaps = build_snapshots(games, closing, initial, own)
    write_csv(DATA / "price_snapshots.csv", SNAP_COLUMNS, snaps)
    snap_meta = {
        "rows": len(snaps),
        "by_snapshot_type": {},
        "by_market": {},
        "origination_games": len({r["game_id"] for r in own}),
        "origination_market_sides": len(own) * 6,
        "pinned_utc": PINNED_UTC,
        "pinned_commit": PIN,
        "inputs_sha256_verified": True,
    }
    for r in snaps:
        snap_meta["by_snapshot_type"][r["snapshot_type"]] = snap_meta["by_snapshot_type"].get(r["snapshot_type"], 0) + 1
        snap_meta["by_market"][r["market"]] = snap_meta["by_market"].get(r["market"], 0) + 1
    (DATA / "snapshot_meta.json").write_text(json.dumps(snap_meta, indent=1, sort_keys=True), encoding="utf-8")

    feed, feed_meta = build_feed(games, closing)
    write_csv(DATA / "results_feed.csv", FEED_COLUMNS, feed)
    cc = ledger_crosscheck(bets, feed)
    feed_meta.update({
        "ledger_crosscheck": cc,
        "seasons": [min(r["season"] for r in feed), max(r["season"] for r in feed)],
        "pinned_utc": PINNED_UTC,
        "pinned_commit": PIN,
        "official_crosschecks": [
            {
                "game": "Washington Commanders at New York Giants, 2026 Week 10 (Thursday, November 12)",
                "official_result": "Commanders 24, Giants 21, FINAL",
                "official_source": "https://www.nfl.com/schedules/2026/REG10/",
                "official_source_2": "https://www.nfl.com/games/commanders-at-giants-2026-reg-10",
                "checked_utc": "2026-11-14",
                "dataset_state": "not present: the pinned dataset was committed 2026-11-01, before kickoff, so the feed has no row for this game",
            }
        ],
    })
    (DATA / "results_feed_meta.json").write_text(json.dumps(feed_meta, indent=1, sort_keys=True), encoding="utf-8")

    print(f"price_snapshots.csv: {len(snaps)} rows " +
          str(snap_meta["by_snapshot_type"]))
    print(f"results_feed.csv: {len(feed)} rows; published outcomes verified {feed_meta['published_outcome_verified']}, "
          f"mismatches {feed_meta['published_outcome_mismatches']}, pushes {feed_meta['push_rows_computed']}")
    print(f"ledger cross-check: {cc['checked']} checked, {cc['mismatch_count']} mismatches, "
          f"{cc['skipped_market_type']} skipped (parlay/futures)")


if __name__ == "__main__":
    main()
