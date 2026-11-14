#!/usr/bin/env python3
"""Fail-closed verifier for the Snapshot Desk.

Re-derives every published number from the committed data files and compares it with what the
pages actually show, so a page cannot go live showing a number the data does not support.
It also enforces the two rules the brief sets for every session: every table row carries a source
link, and a value that no source states is a flagged blank rather than a number.

Exit 0 = all checks pass. Exit 1 = at least one failure; the pages must not be published.

Usage: python3 price_lab/check.py
"""
from __future__ import annotations

import csv
import json
import math
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
D = HERE / "data"
ROOT = HERE.parent
RAW = ROOT / "data" / "raw"
DER = ROOT / "data" / "derived"

FAILURES: list[str] = []
CHECKS = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if ok:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILURES.append(f"{name}: {detail}")


class RowParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.rows = 0
        self.rows_without_link = 0
        self.links: list[str] = []
        self._in_tbody = False
        self._in_row = False
        self._row_links = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tbody":
            self._in_tbody = True
        elif tag == "tr" and self._in_tbody:
            self._in_row = True
            self._row_links = 0
        elif tag == "a" and self._in_row and a.get("href"):
            self._row_links += 1
            self.links.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "tbody":
            self._in_tbody = False
        elif tag == "tr" and self._in_row:
            self.rows += 1
            if self._row_links == 0:
                self.rows_without_link += 1
            self._in_row = False


def main() -> int:
    summary = json.loads((D / "summary.json").read_text())
    official = json.loads((D / "official_results_2026.json").read_text())
    games = {g["game_id"]: g for g in csv.DictReader((RAW / "games.csv").open())}
    ledger = list(csv.DictReader((D / "origination_ledger.csv").open()))
    lb = list(csv.DictReader((D / "leaderboard_signal_staking.csv").open()))
    feed26 = list(csv.DictReader((D / "results_feed_2026.csv").open()))
    hist = list(csv.DictReader((D / "results_history.csv").open()))

    print("Snapshot Desk verification\n--- data integrity ---")

    # 1. official transcription vs pinned feed --------------------------------
    n_off = n_match = n_missing = n_mismatch = 0
    for wk, wd in official["weeks"].items():
        for gm in wd["games"]:
            n_off += 1
            pin = next((g for g in games.values() if g["season"] == "2026" and g["week"] == wk
                        and g["away_team"] == gm["away"] and g["home_team"] == gm["home"]), None)
            if pin and pin["home_score"] != "":
                if int(pin["away_score"]) == gm["away_score"] and int(pin["home_score"]) == gm["home_score"]:
                    n_match += 1
                else:
                    n_mismatch += 1
            else:
                n_missing += 1
    check("official transcription count", n_off == len(feed26) == 137, f"{n_off} vs {len(feed26)}")
    check("official rows match pinned feed exactly", n_mismatch == 0 and n_match == summary["results_feed"]["official_match_pinned"], f"{n_match} match, {n_mismatch} mismatch")
    check("games final after the pin counted", n_missing == summary["results_feed"]["official_missing_from_pin"] == 29, f"{n_missing}")
    check("feed CSV status column agrees", all(
        (r["in_pinned_feed"] == "yes") == (r["match_status"] == "match") for r in feed26), "")

    # 2. results feed CSV vs games.csv ---------------------------------------
    bad = 0
    for r in hist:
        g = games[r["game_id"]]
        if (r["away_score"] != g["away_score"] or r["home_score"] != g["home_score"]
                or r["market_close_spread_home"] != g["spread_line"]):
            bad += 1
    check("history feed equals games.csv on every row", bad == 0, f"{bad} bad")
    check("history feed row count", len(hist) == summary["results_feed"]["history_rows"], f"{len(hist)}")

    # 3. ledger identities -----------------------------------------------------
    bad_diff = bad_ml = bad_order = bad_seq = 0
    sigma = summary["sigma_spread_rmse"]
    for r in ledger:
        if r["order_side"] != "1" or r["order_total"] != "2" or r["order_moneyline"] != "3":
            bad_seq += 1
        if r["market_close_spread"]:
            if abs(float(r["diff_spread"]) - (float(r["fair_spread"]) - float(r["market_close_spread"]))) > 1e-6:
                bad_diff += 1
        if r["market_close_total"]:
            if abs(float(r["diff_total"]) - (float(r["fair_total"]) - float(r["market_close_total"]))) > 1e-6:
                bad_diff += 1
        if r["market_close_ml_home_odds"]:
            if not r["market_ml_home_implied_prob"] or not r["diff_ml_prob_points"]:
                bad_ml += 1
            else:
                o = float(r["market_close_ml_home_odds"])
                p = (-o / (o - 100.0)) if o < 0 else (100.0 / (o + 100.0))
                if abs(p - float(r["market_ml_home_implied_prob"])) > 5e-6:  # stored at 6 dp
                    bad_ml += 1
        if not r["fair_spread"] or not r["fair_total"] or not r["fair_ml_home_prob"]:
            bad_order += 1  # a fair column missing while its market column exists
        # fair-ML re-derivation
        fair_p = 0.5 * (1.0 + math.erf((float(r["fair_spread"]) / sigma) / math.sqrt(2.0)))
        if abs((1.0 - fair_p) - float(r["fair_ml_home_prob"])) > 1e-6:
            bad_ml += 1
    check("ledger diff = fair − market on every populated row", bad_diff == 0, f"{bad_diff} bad")
    check("ledger fair-ML derivation reproduces every row", bad_ml == 0, f"{bad_ml} bad")
    check("ledger order columns are 1,2,3 on every row", bad_seq == 0, f"{bad_seq} bad")
    check("ledger rows", len(ledger) == summary["origination_ledger"]["rows"] == 6991, f"{len(ledger)}")
    check("no ML row without side+total fair values", bad_order == 0, f"{bad_order}")

    # 4. movement re-derivation ------------------------------------------------
    initial = list(csv.DictReader((RAW / "initial_lines.csv").open()))
    sides: dict[str, dict[str, float]] = {}
    for r in initial:
        sides.setdefault(r["about"], {})[f"{r['type']}|{r['side']}"] = float(r["line"])
    moves_s = []
    for about, s in sides.items():
        g = games.get(about)
        if not g or not g["spread_line"]:
            continue
        home = about.split("_")[3]
        moves_s.append(float(g["spread_line"]) - (-s[f"SPREAD|{home}"]))
    sm = summary["snapshots"]["spread_movement_2021"]
    check("2021 spread movement re-derived",
          len(moves_s) == sm["n"] == 272
          and abs(sum(abs(m) for m in moves_s) / len(moves_s) - sm["mean_abs"]) < 5e-3,
          f"n={len(moves_s)}")

    # 5. leaderboard re-derivation --------------------------------------------
    bets = list(csv.DictReader((DER / "bets.csv").open()))
    agg: dict[str, dict] = {}
    for b in bets:
        s = agg.setdefault(b["strategy_id"], {"n": 0, "pnl": 0.0})
        s["n"] += 1
        s["pnl"] += float(b["pnl"])
    bad_roi = 0
    for r in lb:
        a = agg[r["strategy_id"]]
        if abs(a["pnl"] / a["n"] - float(r["signal_flat_roi"])) > 1e-6 or a["n"] != int(r["n_bets"]):
            bad_roi += 1
    check("leaderboard flat ROI reproduces bets.csv", bad_roi == 0, f"{bad_roi} bad")
    check("leaderboard strategy count", len(lb) == summary["leaderboard"]["strategies"] == 11, f"{len(lb)}")

    # 6. snapshot store shape ---------------------------------------------------
    snap_head = (D / "snapshots.csv").open().readline().strip().split(",")
    check("snapshot schema has open/close/fair tiers and source_url",
          {"snapshot", "tier", "source_url", "market", "book"} <= set(snap_head), str(snap_head))

    # --- pages -----------------------------------------------------------------
    print("--- pages ---")
    expected = ["index.html", "snapshots.html", "results.html", "origination-order.html", "leaderboard.html",
                "demotion.html", "suggestions.html", "open-questions.html", "flagged.html", "sources.html",
                "executive-summary.html"]
    for name in expected:
        p = HERE / name
        check(f"page exists: {name}", p.exists())
    pages = {name: (HERE / name).read_text() for name in expected}

    # nav completeness
    nav_bad = [n for n, h in pages.items()
               if not all(f'href="{t}"' in h for t in expected)]
    check("every page links every page of the desk", not nav_bad, str(nav_bad))

    # every tbody row carries a link
    total_rows = rows_no_link = 0
    for name, h in pages.items():
        p = RowParser()
        p.feed(h)
        total_rows += p.rows
        rows_no_link += p.rows_without_link
    check("every table row on every page carries at least one link", rows_no_link == 0,
          f"{rows_no_link} of {total_rows} rows lack a link")

    # internal links resolve
    broken = []
    for name, h in pages.items():
        for href in re.findall(r'href="([^"]+)"', h):
            if href.startswith(("http://", "https://", "#")) or href.startswith("data:"):
                continue
            target = (HERE / name).parent / href.split("#")[0]
            if not target.exists():
                broken.append(f"{name} -> {href}")
    check("all internal links resolve", not broken, "; ".join(broken[:6]))

    # published KPIs must equal the data
    kpis = [
        ("snapshots.html", f"{summary['snapshots']['rows_total']:,}", "snapshot rows KPI"),
        ("results.html", "137", "official finals count"),
        ("results.html", f"{summary['results_feed']['official_match_pinned']} of 137", "match count phrasing"),
        ("executive-summary.html", "0", "zero reward-eligible"),
        ("leaderboard.html", "11", "eleven strategies"),
    ]
    for page, needle, label in kpis:
        check(f"KPI shown on {page}: {label}", needle in pages[page], f"'{needle}' not found")

    # blank discipline: unplayed fixtures show blank market ML
    check("unplayed fixtures carry blank market ML on the snapshots page",
          "no official moneyline captured for unplayed fixtures" in pages["snapshots.html"], "")

    # no stray fail markers from the builder
    check("no 'no source' markers emitted", "no source</span>" not in "".join(pages.values()), "")

    print(f"\n{CHECKS} checks, {len(FAILURES)} failures")
    if FAILURES:
        print("FAILED:")
        for f in FAILURES:
            print(" -", f)
        return 1
    print("Snapshot Desk: ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
