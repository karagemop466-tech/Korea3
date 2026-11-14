#!/usr/bin/env python3
"""Fail-closed verification for origin_lab.

This is a gate, not a report. It exits non-zero on any of the following, and the CI job fails:

  1.  a page is missing
  2.  two consecutive builds differ (the build is not deterministic)
  3.  a table row carries no link at all — the row has no source
  4.  an external link points at a host that is not a registered source
  5.  a blank cell was rendered without a link to flagged.html
  6.  a flag id referenced by a blank cell does not exist in flags.json
  7.  the origination identity fails on any row
  8.  the 2026 results feed does not reconcile to the transcribed official standings
  9.  a headline number on a page disagrees with a recomputation from the raw inputs
  10. a value that must be blank is present (CLV, prop figures, capture timestamps)

Recomputations are written from the raw inputs, not read back out of the JSON the page was built from.
A check that reads its own output is not a check.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import subprocess
import sys
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path

import lib

PAGES = [href for href, _ in lib.NAV]
FLAGS_FILE = lib.DATA / "flags.json"


class Rows(HTMLParser):
    """Collect tbody rows with their links and cell text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = []
        self._tbody = False
        self._row = False
        self._links = []
        self._cells = []
        self._buf = []
        self._href = None
        self._in_a = False

    def handle_data(self, data):
        if self._row:
            self._buf.append(data)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tbody":
            self._tbody = True
        elif tag == "tr" and self._tbody:
            self._row, self._links, self._cells = True, [], []
        elif tag == "a" and self._row and a.get("href"):
            self._links.append(a["href"])
            self._in_a = True
        elif tag in ("td", "th") and self._row:
            self._buf = []

    def handle_endtag(self, tag):
        if tag == "tbody":
            self._tbody = False
        elif tag == "a":
            self._in_a = False
        elif tag in ("td", "th") and self._row:
            self._cells.append("".join(self._buf).strip())
            self._buf = []
        elif tag == "tr" and self._row:
            self.rows.append({"cells": self._cells, "links": self._links})
            self._row = False


def fail(msg):
    print("FAIL: " + msg)
    FAILS.append(msg)


def ok(msg):
    print("  ok  " + msg)


FAILS: list[str] = []


# --------------------------------------------------------------------------------------------
def check_pages_exist():
    for p in PAGES:
        if not (lib.OUT / p).exists():
            fail(f"missing page {p}")
    ok(f"{len(PAGES)} pages present")


def check_determinism():
    before = {p: hashlib.sha256((lib.OUT / p).read_bytes()).hexdigest() for p in PAGES}
    subprocess.run([sys.executable, "build.py"], cwd=str(lib.BASE), check=True,
                   stdout=subprocess.DEVNULL)
    after = {p: hashlib.sha256((lib.OUT / p).read_bytes()).hexdigest() for p in PAGES}
    diff = [p for p in PAGES if before[p] != after[p]]
    if diff:
        fail(f"build is not deterministic: {diff}")
    else:
        ok("two consecutive builds are byte-identical")


def check_rows_sourced():
    allowed = set()
    for d in lib.SOURCES.values():
        host = re.sub(r"^https?://", "", d["url"]).split("/")[0]
        allowed.add(host)
    allowed |= {"github.com", "www.nfl.com", "static.www.nfl.com"}
    club_hosts = set()
    depth = lib.ROOT / "depth_lab" / "data" / "depth.json"
    if depth.exists():
        for r in json.loads(depth.read_text(encoding="utf-8"))["rows"]:
            club_hosts.add(re.sub(r"^https?://", "", r["source_url"]).split("/")[0])

    total_rows = 0
    unsourced = 0
    bad_host = Counter()
    for p in PAGES:
        parser = Rows()
        parser.feed((lib.OUT / p).read_text(encoding="utf-8"))
        for row in parser.rows:
            total_rows += 1
            if not row["links"]:
                unsourced += 1
                fail(f"{p}: row with no source link: {row['cells'][:3]}")
            for href in row["links"]:
                if href.startswith(("http://", "https://")):
                    host = re.sub(r"^https?://", "", href).split("/")[0]
                    if host not in allowed and host not in club_hosts:
                        bad_host[host] += 1
    if unsourced:
        fail(f"{unsourced} table rows carry no source link")
    for host, c in bad_host.items():
        fail(f"external host not in the source register: {host} ({c} links)")
    ok(f"{total_rows:,} table rows checked, every one carries a source link")
    return total_rows


def check_blanks():
    """Every absent value is either the blank renderer (links flagged.html) or a dash in a dense
    table, in which case the page carries the standing note that a dash means no source printed it.
    Every row must carry a source link regardless - that is checked in check_rows_sourced."""
    flags = json.loads(FLAGS_FILE.read_text(encoding="utf-8"))["flags"]
    ids = {f["id"] for f in flags}
    pattern = re.compile(r'<span class="blank"[^>]*>\u2014</span>\s*<a class="blank-link" href="([^"]+)"', re.S)
    bad_id = Counter()
    total = 0
    note = "A dash in a table cell means no source"
    for p in PAGES:
        html = (lib.OUT / p).read_text(encoding="utf-8")
        spans = len(re.findall(r'<span class="blank"', html))
        links = len(re.findall(r'<a class="blank-link" href="flagged\.html[^"]*">unverified</a>', html))
        if spans != links:
            fail(f"{p}: {spans} blank markers but {links} blank links")
        dashes = len(re.findall(r"<td>\s*\u2014\s*</td>", html))
        if dashes and note not in html:
            fail(f"{p}: {dashes} bare dash cells but the page does not carry the dash note")
        for m in pattern.finditer(html):
            total += 1
            target = m.group(1)
            if "#" in target:
                fid = target.split("#")[1]
                if fid not in ids:
                    bad_id[fid] += 1
    for fid, c in bad_id.items():
        fail(f"blank cell points at flag id {fid} which is not in flags.json ({c} cells)")
    if not bad_id:
        ok(f"{total} explicitly-unverified cells, all linked to flagged.html with a resolving id")


def check_must_be_blank():
    board = json.loads((lib.DATA / "leaderboard.json").read_text(encoding="utf-8"))
    for s in board["strategies"]:
        if s.get("clv") is not None:
            fail(f"{s['id']}: CLV must be blank until bet-time prices exist, got {s['clv']}")
        if s.get("blocked"):
            for k, v in s.items():
                if k in ("id", "name", "market", "kind", "rule", "blocked",
                         "blocked_reason", "bets_generated", "rank_signal", "rank_staking",
                         "mask_gap"):
                    continue
                if v not in (None, "", 0, False):
                    fail(f"{s['id']}: blocked strategy carries a value for {k}: {v!r}")
    snap = json.loads((lib.DATA / "price_snapshots.json").read_text(encoding="utf-8"))
    for r in snap["rows"]:
        if r["captured_at_open"] is not None or r["captured_at_close"] is not None:
            fail(f"{r['game_id']}: a capture timestamp was invented")
            break
    ok("CLV, prop figures and capture timestamps are all blank")


def check_identity():
    orig = json.loads((lib.DATA / "origination.json").read_text(encoding="utf-8"))
    bad = 0
    for r in orig["rows"]:
        if r["fair_total"] is None:
            if r["implied_home_points"] is not None or r["identity_ok"]:
                bad += 1
            continue
        h, a = r["implied_home_points"], r["implied_away_points"]
        if abs((h - a) - r["fair_side"]) > 1e-3 or abs((h + a) - r["fair_total"]) > 1e-3:
            bad += 1
    if bad:
        fail(f"{bad} rows violate the side/total identity")
    else:
        ok(f"side/total identity holds on all {len(orig['rows']):,} origination rows")


def check_reconciliation():
    """Recompute the 2026 standings reconciliation from the feed, independently of parse_official."""
    cap = json.loads((lib.DATA / "raw" / "official_capture_2026.json").read_text(encoding="utf-8"))
    off = json.loads((lib.DATA / "official_results_2026.json").read_text(encoding="utf-8"))
    canon = {"AZ": "ARI"}
    pf, pa, w, l, t = (defaultdict(int) for _ in range(5))
    for r in off["feed"]:
        A = canon.get(r["away"], r["away"])
        H = canon.get(r["home"], r["home"])
        a, h = r["away_score"], r["home_score"]
        pf[A] += a; pa[A] += h
        pf[H] += h; pa[H] += a
        if h > a:
            w[H] += 1; l[A] += 1
        elif a > h:
            w[A] += 1; l[H] += 1
        else:
            t[A] += 1; t[H] += 1
    bad = []
    for code, ow, ol, ot, _pct, opf, opa, _net in cap["standings"]["rows"]:
        c = canon.get(code, code)
        if pf[c] != opf or pa[c] != opa or (w[c], l[c], t[c]) != (ow, ol, ot):
            bad.append((c, pf[c], opf, pa[c], opa, (w[c], l[c], t[c]), (ow, ol, ot)))
    if bad:
        for b in bad[:5]:
            fail(f"standings reconciliation mismatch: {b}")
    else:
        ok(f"2026 feed reconciles to the official standings for all {len(cap['standings']['rows'])} clubs "
           f"({sum(pf.values()):,} points for, {sum(pa.values()):,} against)")


def check_counts_from_raw():
    """Recount the headline coverage numbers straight from the raw CSVs."""
    games = [r for r in lib.load_csv(lib.RAW / "games.csv") if r["game_type"] == "REG"]
    initial = lib.load_csv(lib.RAW / "initial_lines.csv")
    closing = lib.load_csv(lib.RAW / "closing_lines.csv")

    reg = len(games)
    priced_side = sum(1 for r in games if r["spread_line"])
    priced_total = sum(1 for r in games if r["total_line"])
    priced_ml = sum(1 for r in games if r["home_moneyline"] and r["away_moneyline"])
    open_games = len({r["about"] for r in initial})

    snap = json.loads((lib.DATA / "price_snapshots.json").read_text(encoding="utf-8"))
    cov = snap["coverage"]
    exp = {"SIDE": (reg, priced_side, open_games), "TOTAL": (reg, priced_total, open_games),
           "MONEYLINE": (reg, priced_ml, 0)}
    for m, (g, c, o) in exp.items():
        if cov[m]["games_total"] != g:
            fail(f"{m} games_total {cov[m]['games_total']} != {g} counted from games.csv")
        if cov[m]["close"] != c:
            fail(f"{m} close {cov[m]['close']} != {c} counted from games.csv")
        if cov[m]["open"] != o:
            fail(f"{m} open {cov[m]['open']} != {o} counted from initial_lines.csv")

    # open-to-close movement recomputed from the two raw files
    init = {}
    for r in initial:
        if r["type"] == "SPREAD":
            init.setdefault(r["about"], {})[r["side"]] = float(r["line"])
    moves = []
    for g in games:
        row = init.get(g["game_id"])
        if not row or not g["spread_line"]:
            continue
        home_line = row.get(g["home_team"])
        if home_line is None:
            continue
        moves.append(float(g["spread_line"]) - (-home_line))
    if moves:
        m_mean = sum(moves) / len(moves)
        m_sd = (sum((x - m_mean) ** 2 for x in moves) / len(moves)) ** 0.5
        mv = snap["movement"]
        if mv["n"] != len(moves):
            fail(f"movement n {mv['n']} != {len(moves)}")
        if abs((mv["mean"] or 0) - m_mean) > 1e-3:
            fail(f"movement mean {mv['mean']} != {m_mean:.6f}")
        if abs((mv["pstdev"] or 0) - m_sd) > 1e-3:
            fail(f"movement sd {mv['pstdev']} != {m_sd:.6f}")
    ok(f"coverage and movement recomputed from the raw CSVs "
       f"({reg:,} games, {open_games} with an opening number, n={len(moves)} moves)")

    # results feed settlement counts
    feed = json.loads((lib.DATA / "results_feed.json").read_text(encoding="utf-8"))
    completed_csv = sum(1 for g in games if g["home_score"] and g["away_score"])
    off = json.loads((lib.DATA / "official_results_2026.json").read_text(encoding="utf-8"))
    added = off["coverage"]["feed_games"] - off["coverage"]["dataset_completed_games"]
    settled_expect = 3 * (completed_csv + added)
    transcribed = sum(1 for r in off["feed"] if r["verification"] == "official_direct")
    if feed["checks"]["settled"] != settled_expect:
        fail(f"settled {feed['checks']['settled']} != {settled_expect} "
             f"({completed_csv} from games.csv + {added} added by the official capture)")
    if transcribed != 30:
        fail(f"expected 30 officially transcribed 2026 rows, found {transcribed}")
    ok(f"results feed: {feed['checks']['settled']:,} settled market rows, {transcribed} of them transcribed "
       f"from NFL.com")


def check_correlation_recomputation():
    """Recompute one published r straight from the raw scores."""
    corr = json.loads((lib.DATA / "correlations.json").read_text(encoding="utf-8"))
    games = []
    for r in lib.load_csv(lib.RAW / "games.csv"):
        if r["game_type"] != "REG":
            continue
        h, a = lib.fint(r, "home_score"), lib.fint(r, "away_score")
        if h is None or a is None:
            continue
        games.append((h, a))
    xs = [h for h, a in games]
    ys = [a for h, a in games]
    r_expect = lib.pearson(xs, ys)
    row = next(r for r in corr["table_a_official"] if r["pair"].startswith("Home points vs away"))
    if abs((row["r"] or 0) - r_expect) > 1e-5:
        fail(f"home vs away points r {row['r']} != recomputed {r_expect:.6f}")
    if row["n"] != len(games):
        fail(f"home vs away points n {row['n']} != {len(games)}")
    for r in corr["table_a_official"] + corr["table_b_parlay_legs"]:
        if r["n"] is None:
            fail(f"correlation row without n: {r['pair']}")
    for r in corr["table_c_not_computable"]:
        pass
    ok(f"correlation recomputed from the raw scores (r={r_expect:.5f}, n={len(games):,}); "
       f"every published row carries n")


def check_leaderboard_recomputation():
    """Recompute S4's flat ROI from scratch. It is the simplest rule, so it is the cleanest test."""
    orig = json.loads((lib.DATA / "origination.json").read_text(encoding="utf-8"))
    board = json.loads((lib.DATA / "leaderboard.json").read_text(encoding="utf-8"))
    pnl, wins, losses, pushes = [], 0, 0, 0
    for r in orig["rows"]:
        if r["season"] < 2006 or not r["played"]:
            continue
        if r["market_side"] is None or r["div_game"] != 1 or r["market_side"] >= 0:
            continue
        price = r["home_spread_odds"]
        if price is None:
            continue
        d = r["margin"] - r["market_side"]
        if abs(d) < 1e-9:
            pushes += 1
            pnl.append(0.0)
            continue
        dec = lib.american_to_decimal(price)
        if d > 0:
            wins += 1
            pnl.append(dec - 1.0)
        else:
            losses += 1
            pnl.append(-1.0)
    roi = sum(pnl) / len(pnl)
    s4 = next(s for s in board["strategies"] if s["id"] == "S4")
    if abs(roi - s4["roi_flat"]) > 1e-5:
        fail(f"S4 roi_flat {s4['roi_flat']} != recomputed {roi:.6f}")
    if s4["n_bets"] != len(pnl):
        fail(f"S4 n_bets {s4['n_bets']} != recomputed {len(pnl)}")
    if s4["wins"] != wins or s4["losses"] != losses or s4["pushes"] != pushes:
        fail(f"S4 win/loss/push {s4['wins']}/{s4['losses']}/{s4['pushes']} != "
             f"{wins}/{losses}/{pushes}")
    ok(f"S4 recomputed from the origination rows (n={len(pnl)}, ROI {roi:+.5f})")


def check_gates_consistency():
    gates = json.loads((lib.DATA / "gates.json").read_text(encoding="utf-8"))
    board = json.loads((lib.DATA / "leaderboard.json").read_text(encoding="utf-8"))
    for r in gates["promotion_results"]:
        if r.get("promotable"):
            fail(f"{r['id']} is marked promotable while P10 is unevaluable")
    if gates["live_count"] != 0:
        fail(f"{gates['live_count']} strategies are marked live")
    for k, v in gates["demotion_status"].items():
        if "NOT APPLICABLE" not in v:
            fail(f"demotion gate {k} claims a live status: {v}")
    ids = {g["id"] for g in gates["demotion_gates"]}
    if len(ids) != len(gates["demotion_gates"]):
        fail("duplicate demotion gate ids")
    ok(f"{len(gates['demotion_gates'])} demotion gates defined, all not applicable; "
       f"0 of {len(board['strategies'])} strategies promotable")


def check_depth_integrity():
    depth = json.loads((lib.DATA / "replacement_depth.json").read_text(encoding="utf-8"))
    for r in depth["rows"]:
        if r["replacement_string"] is not None:
            if r["replacement_string"] < 2:
                fail(f"{r['club']} {r['position']}: replacement string {r['replacement_string']} < 2")
            if r["depth_cost"] != r["replacement_string"] - 1:
                fail(f"{r['club']} {r['position']}: depth cost does not equal string - 1")
            if not r["replacement"]:
                fail(f"{r['club']} {r['position']}: string given but replacement name blank")
        else:
            if r["replacement"]:
                fail(f"{r['club']} {r['position']}: replacement named with no string")
            if not r["beyond_published_depth"]:
                fail(f"{r['club']} {r['position']}: no replacement but not marked beyond published depth")
        if not r["sources"] or len(r["sources"]) < 2:
            fail(f"{r['club']} {r['position']}: row without both sources")
    ok(f"{len(depth['rows'])} replacement rows internally consistent "
       f"({depth['totals']['beyond_published']} with no name published)")


def check_no_invented_designations():
    """No row may state who will start. Only what a club printed and what the league designated."""
    depth = json.loads((lib.DATA / "replacement_depth.json").read_text(encoding="utf-8"))
    banned = ("will start", "expected to start", "probable starter", "listed starter")
    for r in depth["rows"]:
        for k, v in r.items():
            if isinstance(v, str) and any(b in v.lower() for b in banned):
                fail(f"row predicts a lineup: {r['club']} {r['position']} {k}={v!r}")
    ok("no replacement row states who will start")


def main():
    print("origin_lab verification")
    print("-" * 70)
    check_pages_exist()
    check_determinism()
    check_rows_sourced()
    check_blanks()
    check_must_be_blank()
    check_identity()
    check_reconciliation()
    check_counts_from_raw()
    check_correlation_recomputation()
    check_leaderboard_recomputation()
    check_gates_consistency()
    check_depth_integrity()
    check_no_invented_designations()
    print("-" * 70)
    if FAILS:
        print(f"FAILED — {len(FAILS)} problem(s)")
        for f in FAILS:
            print("  - " + f)
        return 1
    print("PASS — all checks held")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
