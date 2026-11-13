#!/usr/bin/env python3
"""Join the two official captures into a starter-replacement view, and publish the join rule.

Two official sources are combined here:

  1. the club's own published depth chart (string order), and
  2. the NFL's official Week 10 injury report (practice status and game status).

THE JOIN RULE, stated before any result is shown:

  A row is emitted when the 1st-string player named by a club's own depth chart appears in the
  NFL's official injury report for the same club with a Game Status of Out or Doubtful. The
  "replacement" column is then the next name the same club published at the SAME position row,
  taken in the club's own published order.

What this is NOT:
  - It is not an official designation. No official publisher says "player X will start".
  - It is not a prediction, a projection, a rating or a betting value.
  - Where the club published no further name at that position, the replacement cell is left
    BLANK and flagged. It is never filled from a roster, a news article or memory.

Name matching is deliberately conservative and auditable. Names are normalised (case,
punctuation, spacing) and only then compared; a match that only works after stripping a
generational suffix (Jr/II/III) is emitted but flagged "normalised". A name that does not
match is NOT joined: it is listed in the unmatched audit so a human can check it.

Usage:
    python3 depth_lab/join_replacements.py
Writes depth_lab/data/replacements.json and prints the join audit.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEPTH = HERE / "data" / "depth.json"
INJ = HERE / "data" / "raw" / "nfl_injury_w10_2026.json"
OUT = HERE / "data" / "replacements.json"

INJURY_SOURCE_URL = "https://www.nfl.com/injuries/"
SUFFIXES = {"jr", "sr", "ii", "iii", "iv", "v"}

# Name variants where the club's own depth chart and the league's own injury report print the
# same person differently. Each entry was checked by hand against both pages and is recorded
# with the two printed spellings, so the alias is auditable rather than a silent fuzzy match.
# Anything NOT on this list is left unmatched on purpose - including two pairs that a fuzzy
# match would have wrongly joined (GB "Evan Williams" vs "Savion Williams", and MIN
# "Jordan Mason" vs "Jordan Addison"), which are different people.
ALIASES: dict[tuple[str, str], tuple[str, str, str]] = {
    ("BAL", "vega ioane"): ("olaivavega ioane",
                            "Baltimore's own chart prints 'Vega Ioane'; the league's report prints 'Olaivavega Ioane'. Same position group (G/RG), one player on each page.",
                            "https://www.baltimoreravens.com/team/depth-chart"),
    ("BAL", "matt hibner"): ("matthew hibner",
                             "Baltimore's own chart prints 'Matt Hibner'; the league's report prints 'Matthew Hibner'. Same club, same TE group.",
                             "https://www.baltimoreravens.com/team/depth-chart"),
    ("MIN", "joshua metellus"): ("josh metellus",
                                 "Minnesota's own chart prints 'Joshua Metellus'; the league's report prints 'Josh Metellus'. Same club, same S group.",
                                 "https://www.vikings.com/team/depth-chart"),
}


def norm(name: str, strip_suffix: bool = True) -> str:
    s = name.lower().replace("\u2019", "'")
    s = s.replace(".", "")  # A.J. Haulcy and AJ Haulcy must land on the same key
    s = re.sub(r"[,]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    if not strip_suffix:
        return s
    parts = [p for p in s.split(" ") if p]
    while parts and parts[-1] in SUFFIXES:
        parts.pop()
    return " ".join(parts)


def main() -> int:
    depth = json.loads(DEPTH.read_text(encoding="utf-8"))
    inj = json.loads(INJ.read_text(encoding="utf-8"))

    # ---- index the official injury report by (club, normalised name) -----------------------
    status_index: dict[tuple[str, str], dict] = {}
    for club in inj["clubs"]:
        for player, pos, injury, practice, game_status, url in club["rows"]:
            key = (club["code"], norm(player))
            status_index[key] = {
                "club": club["code"], "player": player, "pos": pos, "injury": injury,
                "practice": practice, "game_status": game_status, "player_url": url,
                "game_slot": club.get("game_slot", ""), "opponent": club.get("opponent", ""),
            }

    # ---- walk the depth chart ---------------------------------------------------------------
    by_key: dict[tuple[str, str, str], list[dict]] = {}
    for r in depth["rows"]:
        by_key.setdefault((r["club_code"], r["unit"], r["position"]), []).append(r)

    rows: list[dict] = []
    unmatched: list[dict] = []
    no_status: list[dict] = []
    questionable: list[dict] = []

    for club_code, unit, position in sorted(by_key):
        entries = sorted(by_key[(club_code, unit, position)], key=lambda r: (r["string"], r["player"]))
        firsts = [e for e in entries if e["string"] == 1 and e["player"]]
        if not firsts:
            continue
        for first in firsts:
            alias_used = None
            key = (club_code, norm(first["player"]))
            if key in ALIASES:
                canonical, alias_why, alias_url = ALIASES[key]
                alias_used = {"printed_on_chart": first["player"], "printed_by_league": canonical,
                              "why": alias_why, "chart_source": alias_url,
                              "league_source": INJURY_SOURCE_URL}
                key = (club_code, canonical)
            hit = status_index.get(key)
            if hit is None:
                # try the un-normalised form to see whether the match is suffix-dependent
                hit_strict = status_index.get((club_code, norm(first["player"], strip_suffix=False)))
                if hit_strict is None:
                    unmatched.append({
                        "club": club_code, "unit": unit, "position": position,
                        "depth_name": first["player"],
                        "why": "no player of this name on the official NFL injury report for this club",
                        "depth_source": first["source_url"], "injury_source": INJURY_SOURCE_URL,
                    })
                    continue
                hit = hit_strict
                match_kind = "alias" if alias_used else "exact"
            else:
                strict = status_index.get((club_code, norm(first["player"], strip_suffix=False)))
                match_kind = "exact" if strict else ("alias" if alias_used else "normalised")

            gs = hit["game_status"]
            if gs == "":
                no_status.append({
                    "club": club_code, "unit": unit, "position": position,
                    "player": first["player"], "practice": hit["practice"],
                    "injury": hit["injury"], "player_url": hit["player_url"],
                    "why": "the official report prints no Game Status for this player",
                })
                continue
            if gs == "Questionable":
                nxt = [e for e in entries if e["string"] == 2 and e["player"]]
                questionable.append({
                    "club": club_code, "unit": unit, "position": position,
                    "starter": first["player"], "starter_url": hit["player_url"],
                    "game_status": gs, "practice": hit["practice"], "injury": hit["injury"],
                    "next_string_name": nxt[0]["player"] if nxt else "",
                    "next_string": 2 if nxt else None,
                    "depth_published": max((e["string"] for e in entries if e["player"]), default=1),
                    "name_match": match_kind,
                    "alias": alias_used,
                    "sources": [first["source_url"], INJURY_SOURCE_URL],
                })
                continue
            if gs not in ("Out", "Doubtful"):
                no_status.append({
                    "club": club_code, "unit": unit, "position": position,
                    "player": first["player"], "practice": hit["practice"], "injury": hit["injury"],
                    "player_url": hit["player_url"],
                    "why": f"game status {gs!r} is neither Out/Doubtful nor Questionable",
                })
                continue

            # Out or Doubtful -> the replacement is the next name the club published.
            deeper = sorted([e for e in entries if e["string"] > 1 and e["player"]],
                            key=lambda r: r["string"])
            replacement = deeper[0] if deeper else None
            rows.append({
                "club": club_code,
                "club_name": first["club_name"],
                "unit": unit,
                "position": position,
                "starter": first["player"],
                "starter_url": hit["player_url"],
                "starter_game_status": gs,
                "starter_practice": hit["practice"],
                "starter_injury": hit["injury"],
                "replacement": replacement["player"] if replacement else "",
                "replacement_string": replacement["string"] if replacement else None,
                "replacement_url": replacement["player_url"] if replacement else "",
                "replacement_co_listed": bool(replacement and replacement["co_listed"]),
                "depth_published": max((e["string"] for e in entries if e["player"]), default=1),
                "name_match": match_kind,
                "alias": alias_used,
                "derived": True,
                "sources": [first["source_url"], INJURY_SOURCE_URL],
            })

    rows.sort(key=lambda r: (r["club"], r["unit"], r["position"]))

    print("starter-replacement join")
    print(f"  position rows walked          {len(by_key)}")
    print(f"  Out / Doubtful starters        {len(rows)}")
    print(f"    of those, replacement named  {sum(1 for r in rows if r['replacement'])}")
    print(f"    of those, replacement BLANK  {sum(1 for r in rows if not r['replacement'])}")
    print(f"  Questionable starters          {len(questionable)}")
    print(f"  starters with no game status   {len(no_status)}")
    print(f"  names not matched at all       {len(unmatched)}")
    print(f"  name matches needing a suffix strip: "
          f"{sum(1 for r in rows if r['name_match'] == 'normalised')}")
    print(f"  name matches via a hand-checked alias: "
          f"{sum(1 for r in rows if r['name_match'] == 'alias')}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "captured_utc": "2026-11-13",
        "season": 2026, "week": 10,
        "join_rule": (
            "A row appears when the 1st-string player named by a club's own published depth "
            "chart also appears on the NFL's official Week 10 injury report for that club with "
            "a Game Status of Out or Doubtful. The replacement is the next name the same club "
            "published at the same position, in the club's own column order. Neither column is "
            "an official designation: no official publisher states who will start. Where the "
            "club published no further name, the replacement is blank and flagged."
        ),
        "sources": {
            "club_depth_charts": "one page per club, linked on every row",
            "nfl_injury_report": INJURY_SOURCE_URL,
        },
        "rows": rows,
        "questionable": questionable,
        "no_status": no_status,
        "unmatched": unmatched,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(HERE.parent)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
