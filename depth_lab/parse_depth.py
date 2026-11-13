#!/usr/bin/env python3
"""Parse the verbatim club depth-chart captures into one row per (club, unit, position, string).

The capture files in data/raw/ are transcriptions of what each club's own site printed. This
module does the only transformation allowed: turning the published table layout into rows. It
invents nothing. Where a club published an empty cell, the row is emitted with an empty player
and a flag; where it published two players in one cell, both are emitted at the same string
number with a co-listing flag, because the club printed no separator and no ranking between
them.

Usage:
    python3 depth_lab/parse_depth.py
Writes depth_lab/data/depth.json and prints a transcription-consistency report.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "data" / "raw"
OUT = HERE / "data" / "depth.json"

LINK_RE = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
NUM_PREFIX_RE = re.compile(r"^\s*\d{1,2}\s+(?=\S)")

UNIT_KEYS = (("offense", "Offense"), ("defense", "Defense"), ("special_teams", "Special Teams"))


def split_row(line: str) -> list[str]:
    """Split a markdown table row on unescaped pipes. Returns the inner cells only."""
    cells = line.strip().strip("|")
    # A link target can never contain a pipe on these pages, so a plain split is safe here.
    return [c.strip() for c in cells.split("|")]


def parse_cell(cell: str) -> list[dict]:
    """Return the players published in one cell. Two links = a co-listing: no order is implied."""
    if not cell:
        return []
    links = LINK_RE.findall(cell)
    if links:
        out = [{"name": n.strip(), "url": u.strip()} for n, u in links]
        if len(out) > 1:
            for p in out:
                p["co_listed"] = True
        else:
            out[0]["co_listed"] = False
        return out
    # Plain-text cell: clubs that render the chart without hyperlinks prefix a jersey number.
    text = NUM_PREFIX_RE.sub("", cell).strip()
    if not text:
        return []
    return [{"name": text, "url": "", "co_listed": False}]


def parse_club(club: dict) -> tuple[list[dict], list[dict]]:
    rows: list[dict] = []
    notes: list[dict] = []
    for key, unit_label in UNIT_KEYS:
        last_row: dict | None = None
        for line in club.get(key, []):
            if not line.strip().startswith("|"):
                continue
            cells = split_row(line)
            if not cells:
                continue
            pos = cells[0]
            if pos:
                last_row = {"pos": pos, "strings": [], "line": line, "next_string": 1}
                rows.append(last_row)
                target = last_row
                string_offset = 0
                wrapped = False
            else:
                # A wrapped continuation of the previous row (this happens on plain-text clubs).
                if last_row is None:
                    notes.append({"club": club["code"], "unit": unit_label,
                                  "issue": "continuation row with no parent row", "line": line})
                    continue
                target = last_row
                # On a wrapped continuation the empty cells are alignment padding for the
                # columns already filled on the line above, so they carry no string number at
                # all; only the players that actually appear get the next numbers.
                string_offset = last_row["next_string"] - 1
                wrapped = True
                notes.append({"club": club["code"], "unit": unit_label, "pos": last_row["pos"],
                              "issue": "wrapped continuation row", "line": line})
            for i, cell in enumerate(cells[1:]):
                players = parse_cell(cell)
                if wrapped:
                    if not players:
                        continue
                    string_no = string_offset + 1
                    string_offset += 1
                else:
                    string_no = string_offset + i + 1
                if not players:
                    rows_out = {
                        "club_code": club["code"], "club_name": club["name"],
                        "unit": unit_label, "position": target["pos"],
                        "row_label": target["pos"], "string": string_no,
                        "player": "", "player_url": "", "co_listed": False,
                        "source_url": club["url"], "source_page_title": club["page_title"],
                        "empty_slot": True,
                    }
                    target["strings"].append(rows_out)
                    target["next_string"] = string_no + 1
                    continue
                for p in players:
                    rec = {
                        "club_code": club["code"], "club_name": club["name"],
                        "unit": unit_label, "position": target["pos"],
                        "row_label": target["pos"], "string": string_no,
                        "player": p["name"], "player_url": p.get("url", ""),
                        "co_listed": bool(p.get("co_listed", False)),
                        "source_url": club["url"], "source_page_title": club["page_title"],
                        "empty_slot": False,
                    }
                    target["strings"].append(rec)
                    target["next_string"] = string_no + 1
    # Trim trailing padding. Clubs publish a fixed number of player columns (3 to 7) and leave
    # the unused ones blank, so a row with two players shows four empty cells. Those trailing
    # empties are page padding, not a published "4th string exists but is unnamed", and are
    # dropped. An EMPTY CELL BEFORE a named player is kept: that is the club publishing a gap.
    flat: list[dict] = []
    for row in rows:
        strings = row["strings"]
        last_named = max((s["string"] for s in strings if s["player"]), default=0)
        kept = [s for s in strings if s["string"] <= max(last_named, 1)]
        for s in kept:
            s["interior_empty"] = bool(s["empty_slot"] and s["string"] < last_named)
        if last_named == 0:
            # The club published a position row with nobody in it at any string.
            kept[0]["position_row_empty"] = True
        flat.extend(kept)
    return flat, notes


def main() -> int:
    clubs: list[dict] = []
    gaps: list[dict] = []
    for path in sorted(RAW.glob("depth_group*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        clubs.extend(payload.get("clubs", []))
        gaps.extend(payload.get("coverage_gaps", []))

    all_rows: list[dict] = []
    all_notes: list[dict] = []
    for club in clubs:
        rows, notes = parse_club(club)
        all_rows.extend(rows)
        all_notes.extend(notes)

    # ---- transcription consistency report -------------------------------------------------
    print("transcription check")
    print(f"  clubs captured        {len(clubs)}")
    print(f"  coverage gaps         {len(gaps)}  ({', '.join(g['code'] for g in gaps) or 'none'})")
    print(f"  table rows published  {sum(1 for r in all_rows) and len({(r['club_code'], r['unit'], r['row_label'], r['string']) for r in all_rows})}")
    print(f"  player entries        {sum(1 for r in all_rows if r['player'])}")
    print(f"  empty string slots    {sum(1 for r in all_rows if r['empty_slot'])}")
    print(f"  co-listed entries     {sum(1 for r in all_rows if r['co_listed'])}")
    print(f"  rows with a player link   {sum(1 for r in all_rows if r['player_url'])}")
    print(f"  rows without a player link {sum(1 for r in all_rows if r['player'] and not r['player_url'])}")

    by_unit: dict[str, int] = {}
    for r in all_rows:
        by_unit[r["unit"]] = by_unit.get(r["unit"], 0) + 1
    print("  by unit: " + ", ".join(f"{k} {v}" for k, v in sorted(by_unit.items())))

    # Structural checks. These do not verify the transcription against the live page; they
    # verify that the parse produced a coherent structure from what was transcribed.
    problems: list[str] = []
    codes = {c["code"] for c in clubs}
    if len(codes) != len(clubs):
        problems.append("duplicate club codes in the capture files")
    for club in clubs:
        for key, _ in UNIT_KEYS:
            if not club.get(key):
                problems.append(f"{club['code']} has no {key} rows")
        if not club.get("url", "").startswith("https://"):
            problems.append(f"{club['code']} url is not https: {club.get('url')!r}")
    for r in all_rows:
        if r["string"] < 1:
            problems.append(f"string number < 1 for {r['club_code']} {r['position']}")
        if r["player"] and not r["player"].strip():
            problems.append(f"blank player name marked as present: {r}")
    if problems:
        print("\nPROBLEMS:")
        for p in problems:
            print("  -", p)
    else:
        print("\nstructure checks: OK")

    if all_notes:
        print(f"\nformatting notes ({len(all_notes)}):")
        for n in all_notes[:10]:
            print(f"  - {n['club']} {n['unit']}: {n['issue']}")
        if len(all_notes) > 10:
            print(f"  ... and {len(all_notes) - 10} more")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({
        "captured_utc": "2026-11-13",
        "season": 2026,
        "week_label": "Week 10 (club pages captured 2026-11-13)",
        "clubs_captured": len(clubs),
        "clubs_with_data": sorted(codes),
        "coverage_gaps": gaps,
        "formatting_notes": all_notes,
        "rows": all_rows,
    }, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"\nwrote {OUT.relative_to(HERE.parent)} with {len(all_rows)} rows")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
