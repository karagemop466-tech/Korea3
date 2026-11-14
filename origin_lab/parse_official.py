#!/usr/bin/env python3
"""Turn the verbatim official capture into a verified 2026 results feed.

Reads (never writes):
    origin_lab/data/raw/official_capture_2026.json   — transcribed by hand from NFL.com
    data/raw/games.csv                               — pinned nflverse snapshot

Writes:
    origin_lab/data/official_results_2026.json

The point of this file is the reconciliation at the bottom. The league publishes, for every club,
how many points it has scored and how many it has conceded this season. The pinned dataset publishes
the same thing game by game. If the feed is right, the two must agree for all 32 clubs. They do not
agree for Weeks 9 and 10, and the size of the disagreement is the size of the gap between the pinned
dataset and the league's own page. That gap is published, not papered over.
"""
from __future__ import annotations

import collections
import json
from pathlib import Path

import lib

RAW_OFFICIAL = lib.DATA / "raw" / "official_capture_2026.json"
OUT = lib.DATA / "official_results_2026.json"

TEAM_NAMES = {
    "ARI": "Arizona Cardinals", "ATL": "Atlanta Falcons", "BAL": "Baltimore Ravens",
    "BUF": "Buffalo Bills", "CAR": "Carolina Panthers", "CHI": "Chicago Bears",
    "CIN": "Cincinnati Bengals", "CLE": "Cleveland Browns", "DAL": "Dallas Cowboys",
    "DEN": "Denver Broncos", "DET": "Detroit Lions", "GB": "Green Bay Packers",
    "HOU": "Houston Texans", "IND": "Indianapolis Colts", "JAX": "Jacksonville Jaguars",
    "KC": "Kansas City Chiefs", "LV": "Las Vegas Raiders", "LAC": "Los Angeles Chargers",
    "LA": "Los Angeles Rams", "MIA": "Miami Dolphins", "MIN": "Minnesota Vikings",
    "NE": "New England Patriots", "NO": "New Orleans Saints", "NYG": "New York Giants",
    "NYJ": "New York Jets", "PHI": "Philadelphia Eagles", "PIT": "Pittsburgh Steelers",
    "SF": "San Francisco 49ers", "SEA": "Seattle Seahawks", "TB": "Tampa Bay Buccaneers",
    "TEN": "Tennessee Titans", "WAS": "Washington Commanders",
    # the standings page prints Arizona as AZ; the schedule prints ARI. Both are transcribed as
    # printed and reconciled here rather than silently unified.
    "AZ": "Arizona Cardinals",
}
CANON = {"AZ": "ARI"}


def canon(code: str) -> str:
    return CANON.get(code, code)


def main() -> dict:
    cap = json.loads(RAW_OFFICIAL.read_text(encoding="utf-8"))
    games = lib.load_csv(lib.RAW / "games.csv")

    # ---------------------------------------------------------------- dataset rows, 2026
    ds_rows = []
    arith_fail = []
    for r in games:
        if r.get("season") != "2026" or r.get("game_type") != "REG":
            continue
        a, h = lib.fint(r, "away_score"), lib.fint(r, "home_score")
        if a is None or h is None:
            continue
        res, tot = lib.fint(r, "result"), lib.fint(r, "total")
        ok = (res == h - a) and (tot == h + a)
        if not ok:
            arith_fail.append(r["game_id"])
        ds_rows.append({
            "game_id": r["game_id"], "season": 2026, "week": lib.fint(r, "week"),
            "away": r["away_team"], "home": r["home_team"],
            "away_score": a, "home_score": h,
            "margin": h - a, "total": h + a,
            "overtime": lib.fint(r, "overtime"),
            "gameday": r.get("gameday", ""),
            "source_id": "S05",
            "source_url": lib.SOURCES["S05"]["url"],
            "verification": "official_type_dataset",
            "verification_note": "Final score. Only the league produces this figure; carried in the pinned third-party dataset and reconciled in aggregate against the official standings.",
            "arithmetic_ok": ok,
        })

    ds_weeks = sorted({r["week"] for r in ds_rows if r["week"]})
    last_ds_week = max(ds_weeks) if ds_weeks else None

    # ---------------------------------------------------------------- official rows, 2026 W8-W10
    off_rows = []
    for block_key, sid in (("week8_scores", "S13"), ("week9_scores", "S03"), ("week10_scores", "S01")):
        blk = cap[block_key]
        for row in blk["rows"]:
            a, h = row["away_score"], row["home_score"]
            off_rows.append({
                "game_id": f"2026_{blk['week']:02d}_{row['away']}_{row['home']}",
                "season": 2026, "week": blk["week"],
                "away": row["away"], "home": row["home"],
                "away_score": a, "home_score": h,
                "margin": h - a, "total": h + a,
                "overtime": None,
                "gameday": "",
                "source_id": sid,
                "source_url": row["game_url"],
                "verification": "official_direct",
                "verification_note": "Transcribed from the NFL.com page named on the row, which prints the final score.",
                "arithmetic_ok": True,
            })
    off_weeks = sorted({r["week"] for r in off_rows})

    # Where the league's own page and the dataset both carry a game, the league's page wins: it is
    # the publisher of record for a final score. The dataset copy is dropped, and the count is
    # published so a reader can see how much of the feed came from each class.
    off_keys = {(r["week"], canon(r["away"]), canon(r["home"])) for r in off_rows}
    kept_ds, dropped_ds = [], []
    for r in ds_rows:
        key = (r["week"], canon(r["away"]), canon(r["home"]))
        (dropped_ds if key in off_keys else kept_ds).append(r)

    feed = sorted(kept_ds + off_rows, key=lambda r: (r["week"] or 0, r["game_id"]))

    # ---------------------------------------------------------------- aggregate reconciliation
    def tally(rows):
        pf, pa, w, l, t, gp = (collections.Counter() for _ in range(6))
        for r in rows:
            A, H = canon(r["away"]), canon(r["home"])
            a, h = r["away_score"], r["home_score"]
            pf[A] += a; pa[A] += h; gp[A] += 1
            pf[H] += h; pa[H] += a; gp[H] += 1
            if h > a:
                w[H] += 1; l[A] += 1
            elif a > h:
                w[A] += 1; l[H] += 1
            else:
                t[A] += 1; t[H] += 1
        return pf, pa, w, l, t, gp

    feed_pf, feed_pa, feed_w, feed_l, feed_t, feed_gp = tally(feed)
    ds_pf, ds_pa, ds_w, ds_l, ds_t, ds_gp = tally(kept_ds)

    stand_rows = []
    mismatch_pf, mismatch_pa, mismatch_wlt = [], [], []
    for code, w, l, t, pct, pf, pa, net in cap["standings"]["rows"]:
        c = canon(code)
        f_pf, f_pa = feed_pf.get(c), feed_pa.get(c)
        d_pf, d_pa = ds_pf.get(c), ds_pa.get(c)
        rec = {
            "team": c, "team_name": TEAM_NAMES.get(c, c),
            "official_w": w, "official_l": l, "official_t": t,
            "official_pf": pf, "official_pa": pa,
            "feed_w": feed_w.get(c, 0), "feed_l": feed_l.get(c, 0), "feed_t": feed_t.get(c, 0),
            "feed_pf": f_pf, "feed_pa": f_pa,
            "dataset_only_pf": d_pf, "dataset_only_pa": d_pa,
            "delta_pf": None if f_pf is None else f_pf - pf,
            "delta_pa": None if f_pa is None else f_pa - pa,
            "dataset_gap_pf": None if d_pf is None else pf - d_pf,
            "feed_games": feed_gp.get(c, 0),
            "dataset_games": ds_gp.get(c, 0),
            "record_matches": (feed_w.get(c, 0) == w and feed_l.get(c, 0) == l and feed_t.get(c, 0) == t),
            "source_id": "S02",
            "source_url": lib.SOURCES["S02"]["url"],
        }
        if rec["delta_pf"] not in (0, None):
            mismatch_pf.append(c)
        if rec["delta_pa"] not in (0, None):
            mismatch_pa.append(c)
        if not rec["record_matches"]:
            mismatch_wlt.append(c)
        stand_rows.append(rec)

    stand_rows.sort(key=lambda r: r["team"])

    result = {
        "_meta": {
            "generated_by": "origin_lab/parse_official.py",
            "session": "arena/5f341290-korea3",
            "capture_utc": cap["_meta"]["capture_utc"],
            "rule": "A game enters the feed once an official page prints a final score for it, or once the pinned dataset carries one. Rows from the dataset are marked official_type_dataset; rows transcribed from NFL.com are marked official_direct. Neither class is used as if it were the other.",
        },
        "coverage": {
            "dataset_completed_weeks": ds_weeks,
            "dataset_last_completed_week": last_ds_week,
            "dataset_completed_games": len(ds_rows),
            "dataset_rows_replaced_by_official": len(dropped_ds),
            "dataset_rows_used": len(kept_ds),
            "official_transcribed_weeks": off_weeks,
            "official_transcribed_games": len(off_rows),
            "feed_games": len(feed),
            "feed_weeks": sorted({r["week"] for r in feed if r["week"]}),
            "official_current_week": 10,
            "stale_weeks": sorted(set(range(1, 11)) - set(off_weeks) - {w for w in ds_weeks}),
            "weeks_covered_only_by_dataset": sorted(set(ds_weeks) - set(off_weeks)),
            "arithmetic_failures": arith_fail,
        },
        "reconciliation": {
            "teams_compared": len(stand_rows),
            "pf_mismatches": mismatch_pf,
            "pa_mismatches": mismatch_pa,
            "record_mismatches": mismatch_wlt,
            "feed_total_pf": sum(feed_pf.values()),
            "feed_total_pa": sum(feed_pa.values()),
            "official_total_pf": sum(r["official_pf"] for r in stand_rows),
            "official_total_pa": sum(r["official_pa"] for r in stand_rows),
            "dataset_only_total_pf": sum(ds_pf.values()),
            "verdict": (
                "Feed matches the official standings for every club."
                if not (mismatch_pf or mismatch_pa or mismatch_wlt)
                else "Feed does NOT match the official standings; see the delta columns."
            ),
        },
        "standings_check": stand_rows,
        "feed": feed,
    }

    OUT.write_text(json.dumps(result, indent=1, sort_keys=False) + "\n", encoding="utf-8")

    r = result["reconciliation"]
    print(f"official results feed: {len(kept_ds)} dataset rows + {len(off_rows)} transcribed rows "
          f"= {len(feed)}  ({len(dropped_ds)} dataset rows replaced by the league's own page)")
    print(f"dataset last completed week: {last_ds_week}; official current week: 10; "
          f"stale weeks: {result['coverage']['stale_weeks']}")
    print(f"arithmetic failures in the dataset rows: {len(arith_fail)}")
    print(f"reconciliation vs official standings: PF mismatches {len(r['pf_mismatches'])}, "
          f"PA mismatches {len(r['pa_mismatches'])}, W-L-T mismatches {len(r['record_mismatches'])}")
    print(f"feed total PF {r['feed_total_pf']} vs official {r['official_total_pf']}")
    return result


if __name__ == "__main__":
    main()
