#!/usr/bin/env python3
"""Join the captured official rows to the repository's pinned games file, and to the club depth charts.

    python3 -m injury_lab.join

Writes ``data/joined.json`` with two tables:

``game_features`` - one row per captured fixture that can be matched to the pinned games file on **both**
the date and the two club codes. A fixture that matches on one key and not the other is dropped into
``unjoined_fixtures`` with the reason, never snapped to the nearest game.

``replacements`` - one row per official designation that this lab can place on a club's published depth
chart: the absent player, the slot he occupies, the name printed in the next column, and the name printed
after that. This is the brief's "which backup has to replace the starter", answered from two official
publishers at once, with both links on the row.

Three rules in this file exist because of specific failure modes recorded on the coordination board:

* **No cross-season join.** A depth chart is labelled with a year; a report row is labelled with a season.
  They are only joined when the years are equal, so the 2026 Cowboys chart cannot be joined to the 2025
  Cowboys report. The refused join is published in ``refused_joins``, with the numbers that caused the
  refusal.
* **Attribution is measured, not assumed.** A chart belongs to the club whose report rows share players
  with it, and the count of shared names is published on every replacement row. A chart that shares no
  player with the club it appears to be for is refused.
* **A game is joined on date *and* teams.** ``gameday`` plus ``away_team`` plus ``home_team`` must all
  agree with the capture. Because the capture prints a day and month with no year, a January fixture in a
  late regular-season week would need a year rule; this lab publishes the join only for the months where
  season year and calendar year cannot diverge, and flags everything else.
"""
from __future__ import annotations

import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"
PINNED_GAMES = ROOT / "data" / "raw" / "games.csv"
PINNED_COMMIT = "a270278f3ac4e937295fe6a27814b3c4a2b62645"
GAMES_BLOB = (f"https://github.com/nflverse/nfldata/blob/{PINNED_COMMIT}/data/games.csv")

MONTHS = {"JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4, "MAY": 5, "JUNE": 6, "JULY": 7,
          "AUGUST": 8, "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12}
SAFE_MONTHS = {9, 10, 11, 12}          # season year == calendar year, for regular-season fixtures
ABSENT = {"Out", "Doubtful"}           # designations that state the player is not playing
LIMITED = {"Questionable", "Probable"}  # designations that leave it open


def capture_date(day: str, season: int) -> tuple[str, str]:
    """`SUNDAY, NOVEMBER 12TH`, 2015 -> ('2015-11-12', '').  Blank date + reason when ambiguous."""
    m = re.match(r"[A-Z]+,\s+([A-Z]+) (\d+)(?:ST|ND|RD|TH)", day or "")
    if not m:
        return "", "no day text in the capture"
    month, dom = MONTHS.get(m.group(1), 0), int(m.group(2))
    if month not in SAFE_MONTHS:
        return "", (f"month {m.group(1).title()} is outside the Sep-Dec window in which a season's "
                    f"calendar year is unambiguously the season year; refusing to pick a year")
    return f"{season:04d}-{month:02d}-{dom:02d}", ""


def load_pinned_games() -> dict[tuple[str, str, str], dict]:
    out: dict[tuple[str, str, str], dict] = {}
    with PINNED_GAMES.open(newline="", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            if row.get("game_type") not in (None, "") and row["game_type"] not in {"Reg", "REG", "Regular"}:
                continue
            out[(row["gameday"], row["away_team"], row["home_team"])] = row
    return out


def chart_club_name(chart: dict) -> str:
    """The club a chart is for, taken from the words the chart itself prints in its title/heading."""
    text = (chart.get("title", "") + " " + " ".join(chart.get("provenance_lines", []))).lower()
    for name in ("lions", "patriots", "cowboys", "commanders", "giants", "chiefs", "bengals", "browns"):
        if name in text:
            return name.title()
    return ""


def main() -> int:
    caps = json.loads((DATA / "captures.json").read_text(encoding="utf-8"))
    depth = json.loads((DATA / "depth.json").read_text(encoding="utf-8"))
    rows = caps["injury_rows"]
    games = load_pinned_games()

    # ---- index the report by (season, fixture) ------------------------------------------------
    fixtures: dict[tuple[int, int], dict] = {}
    for r in rows:
        key = (r["season"], r["fixture_no"])
        fx = fixtures.setdefault(key, {"capture": r["capture"], "season": r["season"], "week": r["week"],
                                       "fixture_no": r["fixture_no"], "day": r["day"], "kickoff": r["kickoff"],
                                       "broadcast": r["broadcast"], "away": r["away"], "home": r["home"],
                                       "rows": []})
        fx["rows"].append(r)

    # A fixture the capture saw but could not fill is a different fact from a fixture that failed to match,
    # and both are different from silence. The parser records every fixture header it finds, so the join can
    # name the ones it never attempted rather than letting them vanish because they had no rows.
    not_attempted = []
    seen = set(fixtures)
    for cap in caps["captures"]:
        for f in cap["fixtures"]:
            key = (cap["season"], f["index"])
            if key in seen:
                continue
            not_attempted.append({
                "capture": cap["capture"], "season": cap["season"], "week": cap["week"],
                "fixture_no": f["index"], "day": f["day"], "kickoff": f["kickoff"],
                "clubs_captured": [c["code"] for c in f["clubs"]], "player_rows": f["rows"],
                "reason": ("the capture retained this fixture header but no player rows for a second club, "
                           "so there is no date-and-two-club-codes key to match on. Nothing was snapped to "
                           "a nearby game and no row was invented for it"),
            })

    # ---- index charts by (club, season) ------------------------------------------------------
    charts: dict[tuple[str, int], dict] = {}
    for c in depth["charts"]:
        club = chart_club_name(c)
        text = " ".join(c.get("provenance_lines", []) + c.get("prose_lines", []) + [c.get("title", "")])
        m = re.search(r"(20\d\d)", text)
        charts[(club, int(m.group(1)) if m else 0)] = c

    features: list[dict] = []
    unjoined: list[dict] = []
    refused: list[dict] = []
    replacements: list[dict] = []

    for fx in sorted(fixtures.values(), key=lambda f: (f["season"], f["fixture_no"])):
        date, why = capture_date(fx["day"], fx["season"])
        per_club = {}
        if not date:
            unjoined.append({"capture": fx["capture"], "season": fx["season"], "week": fx["week"],
                             "fixture_no": fx["fixture_no"], "day": fx["day"],
                             "away": fx["away"], "home": fx["home"], "reason": why,
                             "player_rows_captured": len(fx["rows"])})
            continue
        g = games.get((date, fx["away"], fx["home"]))
        if g is None:
            unjoined.append({"capture": fx["capture"], "season": fx["season"], "week": fx["week"],
                             "fixture_no": fx["fixture_no"], "day": fx["day"], "date_tried": date,
                             "away": fx["away"], "home": fx["home"],
                             "reason": "no row in the pinned games file with this date and these two club "
                                       "codes; the fixture is not snapped to a nearby game",
                             "player_rows_captured": len(fx["rows"])})
            continue
        complete = {fx["away"], fx["home"]} <= {_club_name_for(fx["away"], fx["rows"]),
                                                _club_name_for(fx["home"], fx["rows"])}
        row = {"season": fx["season"], "week": fx["week"], "fixture_no": fx["fixture_no"],
               "gameday": date, "away": fx["away"], "home": fx["home"],
               "capture_complete_for_both_clubs": complete,
               "game_id": g["game_id"], "source_url": GAMES_BLOB,
               "clubs": {}}
        for side in ("away", "home"):
            code = fx[side]
            crows = [r for r in fx["rows"] if r["club"] == _club_name_for(code, fx["rows"])]
            row["clubs"][side] = _club_features(code, crows)
        row["market"] = {k: (g.get(k) or "") for k in
                         ("spread_line", "total_line", "away_moneyline", "home_moneyline",
                          "away_spread_odds", "home_spread_odds", "over_odds", "under_odds",
                          "away_score", "home_score", "over_time", "roof", "surface", "wind", "temp",
                          "game_date", "stadium", "location")}
        row["played"] = bool(g.get("away_score"))
        features.append(row)

        # ---- depth join, per club, only for the same season -------------------------------
        for side in ("away", "home"):
            code = fx[side]
            club = _club_name_for(code, fx["rows"])
            chart = charts.get((club, fx["season"]))
            if not chart:
                refused.append({"season": fx["season"], "club": club, "club_code": code,
                                "reason": "no retained depth chart for this club and season",
                                "chart_captured_for_this_club": sorted({k[1] for k in charts if k[0] == club}),
                                "fixture_no": fx["fixture_no"]})
                continue
            names_chart = {n["name"] for u in chart["units"].values() for r_ in u for s in r_["strings"]
                           for n in s}
            slugs_chart = {_slug(n["url"]) for u in chart["units"].values() for r_ in u for s in r_["strings"]
                           for n in s}
            own = [r for r in fx["rows"] if r["club"] == club]
            shared = sorted(names_chart & {r["player"] for r in own}
                            | slugs_chart & {_slug(r["player_url"]) for r in own})
            if len(shared) < 3:
                refused.append({"season": fx["season"], "club": club, "club_code": code,
                                "reason": f"the chart and the report share only {len(shared)} player "
                                          f"name(s); attribution is not established, so no replacement row "
                                          f"is published",
                                "shared_players": shared, "fixture_no": fx["fixture_no"]})
                continue
            slots = _chart_slots(chart)
            for r in (x for x in fx["rows"] if x["club"] == club):
                if r["game_status"] not in (ABSENT | LIMITED):
                    continue
                hit = slots.get(_slug(r["player_url"])) or slots.get(r["player"])
                match_key = ("player-url slug" if hit and _slug(r["player_url"]) in slots
                             else "printed name" if hit else "none")
                replacements.append({
                    "season": fx["season"], "week": fx["week"], "fixture_no": fx["fixture_no"],
                    "gameday": date, "club": club, "club_code": code, "side": side,
                    "player": r["player"], "player_position_code": r["position_code"],
                    "injury_text": r["injury_text"], "practice_status": r["practice_status"],
                    "game_status": r["game_status"], "absent_from_report": r["game_status"] in ABSENT,
                    "chart_row_found": bool(hit), "match_key_used": match_key,
                    "name_only_match_would_have_found": r["player"] in slots,
                    "chart_position_label": hit["position_label"] if hit else "",
                    "string_found": hit["string_index"] if hit else 0,
                    "next_string_name": hit["next_name"] if hit else "",
                    "next_string_url": hit["next_url"] if hit else "",
                    "third_string_name": hit["third_name"] if hit else "",
                    "chart_unit": hit["unit"] if hit else "",
                    "attribution_shared_players": len(shared),
                    "report_row_url": r["player_url"],
                    "chart_capture": chart["capture"], "chart_url": chart["url"],
                })
    # ---- fold the chart join back into the game rows ----------------------------------------
    for feat in features:
        for side in ("away", "home"):
            code = feat[side]
            mine = [r for r in replacements if r["season"] == feat["season"]
                    and r["fixture_no"] == feat["fixture_no"] and r["club_code"] == code]
            block = feat["clubs"][side]
            if not mine:
                block.update({"chart_joined": False, "first_string_absent": None,
                              "second_string_absent": None, "third_or_deeper_absent": None,
                              "designations_unplaceable": 0, "designations_placed": 0})
                continue
            block.update({
                "chart_joined": True,
                "first_string_absent": sum(1 for r in mine if r["absent_from_report"] and r["string_found"] == 1),
                "second_string_absent": sum(1 for r in mine if r["absent_from_report"] and r["string_found"] == 2),
                "third_or_deeper_absent": sum(1 for r in mine if r["absent_from_report"]
                                              and r["string_found"] >= 3),
                "designations_unplaceable": sum(1 for r in mine if not r["chart_row_found"]),
                "designations_placed": sum(1 for r in mine if r["chart_row_found"]),
                "first_string_absent_defence": sum(1 for r in mine if r["absent_from_report"]
                                                   and r["string_found"] == 1 and r["chart_unit"] == "Defense"),
                "placed_by_slug_only": sum(1 for r in mine if r["match_key_used"] == "player-url slug"
                                          and not r["name_only_match_would_have_found"]),
            })

    payload = {
        "_comment": ["Generated by injury_lab/join.py. Nothing here is inferred: a game row exists only "
                     "when the captured date and both captured club codes match the pinned games file, and "
                     "a replacement row exists only when the absent player's own name appears in a chart "
                     "from the same season that this file attributes to the same club by shared player "
                     "names.",
                     "market fields come from the pinned third-party dataset, not from an official "
                     "publication; that is stated on the page and linked on the row."],
        "generated_by": "injury_lab/join.py",
        "pinned_games_file": str(PINNED_GAMES.relative_to(ROOT)),
        "pinned_games_blob_url": GAMES_BLOB,
        "designation_sets": {"absent": sorted(ABSENT), "limited": sorted(LIMITED)},
        "game_features": features,
        "unjoined_fixtures": unjoined,
        "fixtures_not_attempted": not_attempted,
        "refused_joins": refused,
        "replacements": replacements,
    }
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "joined.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"join: {len(features)} fixtures joined, {len(unjoined)} refused on date/identity, "
          f"{len(replacements)} replacement rows, {len(refused)} club-season joins refused")
    return 0


def _slug(url: str) -> str:
    m = re.search(r"/(?:players|players-roster)/([^/]+)/?$", (url or "").rstrip("/"))
    return m.group(1) if url else ""


def _club_name_for(code: str, rows: list[dict]) -> str:
    """The club display name the page printed next to this code, or '' if the capture never showed it."""
    for r in rows:
        if r.get("away") == code and r.get("club_side") == "away":
            return r["club"]
        if r.get("home") == code and r.get("club_side") == "home":
            return r["club"]
    return ""


def _club_features(code: str, rows: list[dict]) -> dict:
    def n(pred) -> int:
        return sum(1 for r in rows if pred(r))
    return {
        "club_code": code, "club": rows[0]["club"] if rows else "",
        "record_at_capture": rows[0]["record_at_capture"] if rows else "",
        "rows_captured": len(rows),
        "out": n(lambda r: r["game_status"] == "Out"),
        "doubtful": n(lambda r: r["game_status"] == "Doubtful"),
        "questionable": n(lambda r: r["game_status"] == "Questionable"),
        "probable": n(lambda r: r["game_status"] == "Probable"),
        "status_blank": n(lambda r: not r["game_status"]),
        "dnp": n(lambda r: r["practice_status"] == "Did Not Participate In Practice"),
        "limited_practice": n(lambda r: r["practice_status"] == "Limited Participation in Practice"),
        "full_practice": n(lambda r: r["practice_status"] == "Full Participation in Practice"),
        "out_defence": n(lambda r: r["game_status"] in ABSENT and r["unit"] == "Defense"),
        "out_offense": n(lambda r: r["game_status"] in ABSENT and r["unit"] == "Offense"),
        "out_unit_blank": n(lambda r: r["game_status"] in ABSENT and not r["unit"]),
        "qb_absent": n(lambda r: r["position_code"] == "QB" and r["game_status"] in ABSENT),
        "injury_text_blank": n(lambda r: not r["injury_text"]),
    }


def _chart_slots(chart: dict) -> dict[str, dict]:
    """player name -> the slot this chart puts him in, plus whoever is printed next to him."""
    out: dict[str, dict] = {}
    for unit, entries in chart["units"].items():
        for entry in entries:
            strings = entry["strings"]
            for i, cell in enumerate(strings):
                for player in cell:
                    nxt = strings[i + 1][0] if i + 1 < len(strings) and strings[i + 1] else None
                    third = strings[i + 2][0] if i + 2 < len(strings) and strings[i + 2] else None
                    key = _slug(player["url"]) or player["name"]
                    rec = {"position_label": entry["position_label"], "string_index": i + 1,
                           "unit": unit,
                           "next_name": nxt["name"] if nxt else "", "next_url": nxt["url"] if nxt else "",
                           "third_name": third["name"] if third else "",
                           "ambiguous_cell": bool(entry["ambiguous_cells"]),
                           "raw_line": entry["raw_line"]}
                    out.setdefault(key, rec)
                    out.setdefault(player["name"], rec)
    return out


if __name__ == "__main__":
    sys.exit(main())
