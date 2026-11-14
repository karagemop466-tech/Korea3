#!/usr/bin/env python3
"""Requirement 6 — track the depth of the replacement, not just the fact of a replacement.

The distinction that matters
----------------------------
"A starter is out" is one bit. "A starter is out and the club's own chart names a fourth-string
player as the next man" is a different statement entirely, and only the second one can be priced.
This module publishes, for every starter on the league's official injury report whose club also
publishes an ordered depth chart:

    replacement_string   the column the replacement sits in, in the club's own ordering
    depth_published      how many names the club prints at that position at all
    depth_cost           replacement_string - 1, i.e. how far down the chart the club must reach
    beyond_published_depth   true when the club prints no further name, so the replacement is blank

Reused, not re-derived
----------------------
The two inputs were transcribed from official pages by session arena/3436db70-korea3 and are read
here without modification:

    depth_lab/data/raw/nfl_injury_w10_2026.json   the league's own injury report
    depth_lab/data/depth.json                     parsed from 31 club-published depth charts

One extension to that session's join: it published Out and Doubtful only (43 rows). Questionable is
added here (33 further rows), because a coach's own depth chart is exactly the artefact that says
who plays if a Questionable starter does not. The two sets are reported separately so a reader can
see which rows are new and can drop them if they disagree.

What is still not known, and is not guessed: no official publisher states who will start. A depth
chart is a club's own ordering; the league's report is a designation. Neither is a lineup.
"""
from __future__ import annotations

import json
import re

import lib

DEPTH = lib.ROOT / "depth_lab" / "data" / "depth.json"
INJURY = lib.ROOT / "depth_lab" / "data" / "raw" / "nfl_injury_w10_2026.json"
OUT = lib.DATA / "replacement_depth.json"

# club codes as the club charts print them -> codes as the dataset/league print them
CLUB_ALIAS = {"LAR": "LA", "AZ": "ARI", "ARZ": "ARI", "JAC": "JAX", "SL": "LA", "SD": "LAC"}

SUFFIXES = {"jr", "jr.", "sr", "sr.", "ii", "iii", "iv", "v"}


def norm(name: str) -> str:
    s = re.sub(r"[^a-z ]", "", (name or "").lower()).strip()
    parts = [p for p in s.split() if p not in SUFFIXES]
    return " ".join(parts)


def main():
    depth = json.loads(DEPTH.read_text(encoding="utf-8"))
    inj = json.loads(INJURY.read_text(encoding="utf-8"))

    # ---- index the league's official injury report
    report = {}
    for club in inj["clubs"]:
        code = CLUB_ALIAS.get(club["code"], club["code"])
        for row in club["rows"]:
            name, pos, injury, practice, status, url = (list(row) + [""] * 6)[:6]
            report.setdefault(code, {})[norm(name)] = {
                "club_name": club["name"], "player": name, "position": pos,
                "injury": injury, "practice": practice, "game_status": status or "",
                "player_url": url,
                "report_url": inj["_meta"]["source_url"],
            }

    # ---- index the club charts.
    # A position label is not unique: a club can print two rows both headed "TE". The parser emits
    # rows in column order, so a new row begins wherever string 1 appears. Grouping on that rather
    # than on the position label alone is what stops one row's players being overwritten by the
    # next row's - which is exactly the bug that silently dropped 11 starters on the first pass.
    charts = []
    current = None
    for r in depth["rows"]:
        if r.get("empty_slot") or not r.get("player"):
            continue
        club = CLUB_ALIAS.get(r["club_code"], r["club_code"])
        if r["string"] == 1:
            current = {
                "club": club, "club_name": r["club_name"], "unit": r["unit"],
                "position": r["position"], "by_string": {},
                "source_url": r["source_url"], "source_page_title": r["source_page_title"],
            }
            charts.append(current)
        if current is None:
            continue
        current["by_string"].setdefault(r["string"], []).append(r)

    statuses = ("Out", "Doubtful", "Questionable")

    def unavailable(club, player, strict):
        """Is this player listed on the official report as someone who may not play?"""
        hit = report.get(club, {}).get(norm(player))
        if not hit:
            return False, None
        s = hit["game_status"].strip()
        pool = ("Out", "Doubtful", "Questionable") if strict else ("Out", "Doubtful")
        return (s in pool), (hit if s in pool else None)

    rows, unmatched_starters = [], []
    for grp in charts:
        firsts = grp["by_string"].get(1, [])
        for st in firsts:
            hit = report.get(grp["club"], {}).get(norm(st["player"]))
            if not hit:
                continue
            status = hit["game_status"].strip()
            if status not in statuses:
                unmatched_starters.append({
                    "club": grp["club"], "unit": grp["unit"], "position": grp["position"],
                    "starter": st["player"], "game_status": status,
                    "note": "On the official report with a Game Status that is not Out, Doubtful or Questionable, or with the league's own blank. Not joined: a blank is not a designation.",
                })
                continue

            published = max(grp["by_string"])

            def walk(strict):
                s = 2
                while s <= published + 1:
                    cands = grp["by_string"].get(s, [])
                    for cand in cands:
                        bad, _ = unavailable(grp["club"], cand["player"], strict)
                        if not bad:
                            return s, cand
                    s += 1
                return None, None

            rs, repl = walk(False)
            rs_strict, repl_strict = walk(True)

            rows.append({
                "club": grp["club"], "club_name": grp["club_name"], "unit": grp["unit"],
                "position": grp["position"],
                "starter": st["player"], "starter_url": st["player_url"],
                "starter_game_status": status,
                "starter_practice": hit["practice"], "starter_injury": hit["injury"],
                "starter_report_url": hit["report_url"],
                "replacement": "" if repl is None else repl["player"],
                "replacement_url": "" if repl is None else repl["player_url"],
                "replacement_string": rs,
                "replacement_string_strict": rs_strict,
                "replacement_strict": "" if repl_strict is None else repl_strict["player"],
                "skip_count": None if rs is None else rs - 2,
                "depth_published": published,
                "depth_cost": None if rs is None else rs - 1,
                "beyond_published_depth": repl is None,
                "status_group": "Out/Doubtful" if status in ("Out", "Doubtful") else "Questionable",
                "co_listed_replacement": None if repl is None else bool(repl.get("co_listed")),
                "sources": [grp["source_url"], hit["report_url"]],
                "source_page_title": grp["source_page_title"],
            })

    charted = {g["club"] for g in charts}
    # ---- per-club roll-up
    clubs = {}
    for r in rows:
        c = clubs.setdefault(r["club"], {
            "club": r["club"], "club_name": r["club_name"],
            "replacements": 0, "by_string": {2: 0, 3: 0, 4: 0, 5: 0},
            "depth_cost_total": 0, "offense": 0, "defense": 0, "special_teams": 0,
            "beyond_published": 0, "questionable": 0, "out_doubtful": 0,
        })
        c["replacements"] += 1
        c["depth_cost_total"] += r["depth_cost"] or 0
        if r["replacement_string"] in c["by_string"]:
            c["by_string"][r["replacement_string"]] += 1
        elif r["replacement_string"]:
            c["by_string"][r["replacement_string"]] = 1
        key = {"Offense": "offense", "Defense": "defense"}.get(r["unit"], "special_teams")
        c[key] += 1
        if r["beyond_published_depth"]:
            c["beyond_published"] += 1
        c["questionable" if r["status_group"] == "Questionable" else "out_doubtful"] += 1

    # clubs on the official report but absent from it, and clubs with no chart
    report_only = sorted(set(report) - charted)
    no_report = sorted(charted - set(report))

    out = {
        "_meta": {
            "generated_by": "origin_lab/build_depth.py",
            "session": "arena/5f341290-korea3",
            "inputs": {
                "club_depth_charts": "depth_lab/data/depth.json, parsed by session arena/3436db70-korea3 from 31 club-published pages captured 2026-11-13",
                "official_injury_report": "depth_lab/data/raw/nfl_injury_w10_2026.json, transcribed from https://www.nfl.com/injuries/ captured 2026-11-13",
            },
            "join_rule": "A row appears when the player listed at string 1 of a position in a club's own published depth chart also appears on the league's official Week 10 injury report for that club with a Game Status of Out, Doubtful or Questionable. The replacement is the next name the same club printed at the same position, in the club's own column order.",
            "depth_cost": "replacement_string - 1. It is a count of columns in a club's own publication, not a judgement about how good the replacement is. No ability, snap count or grade is attached to it anywhere in this repository.",
            "not_known": "No official publisher states who will start. A depth chart is the club's own ordering and carries no designation; the league's injury report carries a designation and no ordering. Nothing here predicts a lineup.",
            "extension": "Session arena/3436db70-korea3 joined Out and Doubtful only. Questionable is added here and reported in a separate column group so the two sets can be told apart.",
            "clubs_absent_from_the_official_report": inj["_meta"].get("absent_clubs", []),
            "absent_note": inj["_meta"].get("absent_clubs_note", ""),
        },
        "totals": {
            "rows": len(rows),
            "out_doubtful": sum(1 for r in rows if r["status_group"] == "Out/Doubtful"),
            "questionable": sum(1 for r in rows if r["status_group"] == "Questionable"),
            "by_string": {str(k): sum(1 for r in rows if r["replacement_string"] == k)
                          for k in (2, 3, 4, 5)},
            "beyond_published": sum(1 for r in rows if r["beyond_published_depth"]),
            "depth_cost_total": sum(r["depth_cost"] or 0 for r in rows),
            "offense": sum(1 for r in rows if r["unit"] == "Offense"),
            "defense": sum(1 for r in rows if r["unit"] == "Defense"),
            "special_teams": sum(1 for r in rows if r["unit"] not in ("Offense", "Defense")),
            "blank_game_status_rows": len(unmatched_starters),
            "clubs_with_a_chart_but_no_report": no_report,
            "clubs_on_the_report_with_no_chart": report_only,
        },
        "rows": rows,
        "by_club": sorted(clubs.values(), key=lambda c: (-c["depth_cost_total"], c["club"])),
        "blank_game_status": unmatched_starters[:200],
    }
    OUT.write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")

    t = out["totals"]
    print("replacement depth: %d rows (%d Out/Doubtful, %d Questionable)" % (
        t["rows"], t["out_doubtful"], t["questionable"]))
    print("  by replacement string:", t["by_string"])
    print("  beyond published depth (no replacement printed):", t["beyond_published"])
    print("  total depth cost:", t["depth_cost_total"],
          "| offense %d defense %d special teams %d" % (t["offense"], t["defense"], t["special_teams"]))
    print("  starters on the report with a blank Game Status, not joined:", t["blank_game_status_rows"])
    print("  clubs with a chart but no report row:", no_report)
    print("  clubs on the report with no chart:", report_only)


if __name__ == "__main__":
    main()
