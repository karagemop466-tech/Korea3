"""Computed inputs for the decision-readiness register.

Every number shown on the readiness pages is computed here from files in the
repository at build time, or from the official-page re-check record in
readiness/data/official_recheck.json. Nothing is typed in by hand except the
per-club row counts that were counted from the fetched official page
(recorded in official_recheck.json with the page URL and fetch date).
"""
import csv
import json
import collections
import os
import re

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def p(*parts):
    return os.path.join(ROOT, *parts)


def _load(path):
    with open(p(path), encoding="utf-8") as f:
        return json.load(f)


def _csv_rows(path):
    with open(p(path), newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def compute():
    n = {}

    # ---- price-snapshot store (origin_lab) ----
    rows = _csv_rows("origin_lab/data/price_snapshots.csv")
    n["price_rows"] = len(rows)
    n["price_open"] = sum(1 for r in rows if (r.get("open_number") or "").strip())
    n["price_close"] = sum(1 for r in rows if (r.get("close_number") or "").strip())
    n["price_both"] = sum(
        1 for r in rows
        if (r.get("open_number") or "").strip() and (r.get("close_number") or "").strip())
    r26 = [r for r in rows if r.get("season") == "2026"]
    n["price_2026"] = len(r26)
    n["price_2026_both"] = sum(
        1 for r in r26
        if (r.get("open_number") or "").strip() and (r.get("close_number") or "").strip())
    n["price_2026_blank_market"] = sum(
        1 for r in r26 if not (r.get("close_number") or "").strip())

    # ---- results feed (origin_lab) ----
    rf = _csv_rows("origin_lab/data/results_feed.csv")
    n["results_rows"] = len(rf)
    rf26 = [r for r in rf if r.get("season") == "2026"]
    n["results_2026_rows"] = len(rf26)
    n["results_2026_games"] = len({r["game_id"] for r in rf26})
    vc = collections.Counter(r.get("verification", "") for r in rf26)
    n["results_2026_official_direct"] = vc.get("official_direct", 0)
    n["results_2026_dataset"] = vc.get("official_type_dataset", 0)
    n["results_2026_verification_values"] = dict(vc)

    # ---- fair vs market (market_lab) ----
    fvm = _csv_rows("market_lab/data/fair_vs_market.csv")
    n["fvm_rows"] = len(fvm)
    n["fvm_markets"] = dict(collections.Counter(r.get("market", "") for r in fvm))
    n["fvm_with_market_line"] = sum(1 for r in fvm if (r.get("market_line") or "").strip())
    n["fvm_with_all_three"] = sum(
        1 for r in fvm
        if all((r.get(k) or "").strip() for k in ("fair_line", "market_line", "difference")))

    # ---- strategy leaderboard (origin_lab) ----
    lb = _load("origin_lab/data/leaderboard.json")["strategies"]
    n["strategies_origin"] = len(lb)
    n["strategy_kinds"] = dict(collections.Counter(s.get("kind") for s in lb))
    n["strategies_unblocked"] = sum(1 for s in lb if str(s.get("blocked")) == "False")
    n["parlay_ids_ranked"] = [s["id"] for s in lb if s.get("kind") == "parlay"
                              and str(s.get("blocked")) == "False"]
    lc = _load("lifecycle/data/demotion.json")["_meta"]
    n["strategies_lifecycle"] = lc.get("n_strategies")
    n["live_lifecycle"] = lc.get("n_live")
    n["demotion_params"] = lc.get("parameters")
    og = _load("origin_lab/data/gates.json")["_meta"]
    n["origin_gate_state"] = og.get("state_of_the_world")
    lbm = _load("origin_lab/data/leaderboard.json")["_meta"]
    n["lb_window"] = lbm.get("window")
    n["lb_luck_test"] = lbm.get("luck_test")

    # joint-evidence and control terms in the gate/leaderboard code
    code = ""
    for f in ("origin_lab/leaderboard.py", "origin_lab/data/gates.json",
              "origin_lab/build_gates.py"):
        try:
            with open(p(f), encoding="utf-8") as h:
                code += h.read()
        except FileNotFoundError:
            pass
    n["joint_mentions_gate_code"] = len(re.findall(r"joint", code, re.I))
    n["brier_mentions_gate_code"] = len(re.findall(r"brier", code, re.I))
    n["control_mentions_gate_code"] = len(re.findall(r"random|favou?rite", code, re.I))

    # ---- depth (depth_lab) ----
    dep = _load("depth_lab/data/depth.json")
    drows = dep["rows"]
    n["depth_clubs"] = len({r["club_code"] for r in drows})
    n["depth_clubs_with_data_list"] = len(dep.get("clubs_with_data", []))
    n["depth_rows"] = len(drows)
    n["depth_coverage_gaps"] = [g["code"] for g in dep.get("coverage_gaps", [])]
    n["depth_captured_utc"] = dep.get("captured_utc")
    n["depth_rows_with_source_url"] = sum(1 for r in drows if r.get("source_url"))
    n["depth_rows_with_per_row_date"] = sum(1 for r in drows if r.get("captured_utc"))
    n["depth_unofficial_title_rows"] = sum(
        1 for r in drows if "nofficial" in (r.get("source_page_title") or ""))
    n["depth_unofficial_title_clubs"] = sorted({
        r["club_code"] for r in drows if "nofficial" in (r.get("source_page_title") or "")})
    slots = collections.defaultdict(set)
    for r in drows:
        if r.get("string") == 1 and not r.get("empty_slot"):
            slots[(r["club_code"], r["unit"], r["position"])].add(r["player"])
    n["rank1_slots"] = len(slots)
    n["rank1_multi_slots"] = sum(1 for v in slots.values() if len(v) > 1)
    n["co_listed_rows"] = sum(1 for r in drows if r.get("co_listed"))
    n["empty_slot_rows"] = sum(1 for r in drows if r.get("empty_slot"))
    sea = [(r["position"], r["string"], r["player"]) for r in drows
           if r["club_code"] == "SEA" and r.get("co_listed")]
    was = [(r["unit"], r["position"], r["string"]) for r in drows
           if r["club_code"] == "WAS" and r.get("empty_slot")]
    n["sea_co_listed_examples"] = sea
    n["was_empty_slot_examples"] = was

    # BAL club depth as captured (QB rows)
    n["bal_qb_depth"] = [r["player"] for r in sorted(
        (r for r in drows if r["club_code"] == "BAL" and r["position"] == "QB"),
        key=lambda r: r["string"])]

    rd = _load("origin_lab/data/replacement_depth.json")
    n["replacement_rows"] = len(rd.get("rows", []))
    n["replacement_clubs"] = len(rd.get("by_club", []))
    n["replacement_blank_game_status"] = len(rd.get("blank_game_status", []))

    # parser: jersey-number stripping (Packers) and its comment
    with open(p("depth_lab/parse_depth.py"), encoding="utf-8") as h:
        pd = h.read()
    n["parser_jersey_strip"] = "jersey number" in pd

    # ---- Week 10 injury capture (depth_lab raw) and published hub copy ----
    raw = _load("depth_lab/data/raw/nfl_injury_w10_2026.json")
    raw_rows = {c["code"]: c["rows"] for c in raw["clubs"]}
    n["raw_clubs"] = len(raw_rows)
    n["raw_rows"] = sum(len(v) for v in raw_rows.values())
    n["raw_bal_rows"] = len(raw_rows.get("BAL", []))
    n["raw_absent_clubs"] = raw["_meta"]["absent_clubs"]
    n["raw_captured_utc"] = raw["_meta"]["captured_utc"]
    n["raw_bal_names"] = [r[0] for r in raw_rows.get("BAL", [])]
    hub = _load("hub/data/injuries.json")
    n["hub_players_listed"] = hub.get("players_listed")
    n["hub_clubs_listed"] = hub.get("clubs_listed")
    n["hub_no_injuries"] = hub.get("clubs_no_injuries_reported")
    n["hub_absent"] = hub.get("clubs_absent_from_page")

    # Lions game-status cells as published in the hub and decisions builds
    hub_rows = hub.get("players", hub.get("rows", []))
    def find_hub(name):
        for r in hub_rows if isinstance(hub_rows, list) else []:
            if r.get("player") == name:
                return r.get("game")
        return "(not found)"
    n["hub_lions_game_status"] = {x: find_hub(x) for x in
                                  ("Kerby Joseph", "Cade Mays", "D.J. Reed")}
    dec = _load("decisions/data/injuries_week10_2026.json")
    dec_rows = dec.get("rows", [])
    n["decisions_lions_game_status"] = {
        x: next((r.get("game_status") for r in dec_rows if r.get("player") == x), "(not found)")
        for x in ("Kerby Joseph", "Cade Mays", "D.J. Reed")}
    raw_lions = {r[0]: r[4] for r in raw_rows.get("DET", []) if r[0] in
                 ("Kerby Joseph", "Cade Mays", "D.J. Reed")}
    n["raw_lions_game_status"] = raw_lions

    # ---- coordination board and workflows ----
    with open(p("COORDINATION.md"), encoding="utf-8") as h:
        coord = h.read()
    n["claim_headings"] = len(re.findall(r"^## .*CLAIM", coord, re.M | re.I))
    wf = [f for f in os.listdir(p(".github/workflows")) if f.endswith(".yml")]
    n["workflows"] = len(wf)
    n["workflow_cron_triggers"] = sum(
        open(p(".github/workflows", f), encoding="utf-8").read().count("cron") for f in wf)

    # ---- official re-check record (fetched 2026-11-15) ----
    rc = _load("readiness/data/official_recheck.json")
    n["live_clubs_with_tables"] = len(rc["live_week10_club_counts"])
    n["live_rows_manual"] = sum(rc["live_week10_club_counts"].values())
    n["live_absent"] = rc["live_week10_absent"]
    n["trades_nov2026"] = len(rc["trades_nov2026"])
    n["reserve_nov2026_seen"] = len(rc["reserve_nov2026_seen"])
    return n


if __name__ == "__main__":
    print(json.dumps(compute(), indent=1, default=str)[:4000])
