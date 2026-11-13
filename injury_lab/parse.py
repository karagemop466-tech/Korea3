#!/usr/bin/env python3
"""Turn the retained official captures into structured rows. Deterministic, stdlib-only, no inference.

    python3 -m injury_lab.parse

Reads every file in ``injury_lab/raw/`` and writes ``data/captures.json`` (injury-report rows) and
``data/depth.json`` (club depth-chart strings). It never contacts the network and never adds a value:

* an empty cell on the page is an empty string here, and the site prints it as a blank marker;
* a code no captured page places in a unit gets unit ``""`` (see ``conventions.py``), not a guess;
* a club table cut off by the chunk boundary is recorded in ``capture_gaps`` and no row is invented to
  fill it - the gap is the finding;
* a pipe line that matches no row shape is counted in ``unparsed_table_lines``, so a page that changes
  shape cannot quietly drop rows.

The point of doing this in code instead of writing JSON by hand is the round trip: ``check_site.py`` P7
re-derives every published row from the capture file and requires it to equal the line on the page, so a
transcription slip anywhere in the chain fails the build.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from . import conventions

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = HERE / "raw"
DATA = HERE / "data"

DAY_HEAD = re.compile(r"^##\s+([A-Z]+,\s+[A-Z]+ \d+(?:ST|ND|RD|TH))$")
KICKOFF = re.compile(r"^\d{1,2}:\d{2}\s+[AP]M[A-Z]{2,4}$")
FIXTURE_HEAD = re.compile(
    r"^\[!\[.*?\]\(https://static\.www\.nfl\.com/t_q-best/league/api/clubs/logos/([A-Z]{2,3})\)\]"
    r"\(https://www\.nfl\.com/teams/([a-z-]+)/\)\s+([A-Z]{2,3})\s+\[([^\]]+)\]"
    r"\(https://www\.nfl\.com/teams/([a-z-]+)/\)")
RECORD = re.compile(r"^\((\d+-\d+(?:-\d+)?)\)$")
PLAYER_ROW = re.compile(
    r"^\|\s*\[([^\]]+)\]\((https://www\.nfl\.com/players/([^)]+)/)?\)"
    r"\s*\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*([^|]*)\|\s*$")
CAPTION = re.compile(r"^([A-Z][A-Za-z .'-]+)$")
# The report prints this literal line in place of a table for a club with nothing to report. It is a row
# type, not prose, and an earlier transcription in this repository (decision_lab/data/injuries.json)
# records it as one, so the parser looks for it rather than leaving the distinction to a reader.
NO_INJ_PHRASE = re.compile(r"no injuries reported", re.I)
DEPTH_CELL = re.compile(r"\[([^\]]+)\]\((https?://[^)]+?)\s*/?\)")
HEADER_KV = re.compile(r"^([a-z][a-z_ ]*?)\s*:\s*(.+)$")


def body_lines(path: Path) -> list[str]:
    """The capture text after its leading HTML comment block.

    The comment is this lab's own provenance header. Parsing it as page content would let a header line
    masquerade as page prose - which is exactly how the first version of this parser recorded
    ``url : ...`` as the chart's prose and then failed to find the club's own season label.
    """
    text = path.read_text(encoding="utf-8")
    return (text.split("-->", 1)[1] if "-->" in text else text).splitlines()


def capture_header(path: Path) -> dict[str, str]:
    """Read the ``key : value`` lines inside a capture's leading HTML comment."""
    head = path.read_text(encoding="utf-8").split("-->", 1)[0]
    out: dict[str, str] = {}
    for line in head.splitlines():
        m = HEADER_KV.match(line.strip().lstrip("!").strip())
        if m:
            out[" ".join(m.group(1).split())] = m.group(2).strip()
    return out


def _new_game(day: str = "") -> dict:
    """One fixture block.

    The official page starts every fixture with its own kickoff line, and a day heading can cover several
    fixtures, so the kickoff - not the day heading - is what separates two games. Getting this wrong makes
    a parser attach the second game's club tables to the first game's identity, which is the kind of error
    that survives a manual review of the output and destroys a backtest.
    """
    return {"day": day, "kickoff": "", "broadcast": "", "clubs": [], "records": []}


def parse_injury_capture(path: Path, mapping: dict) -> tuple[list[dict], list[dict], dict]:
    head = capture_header(path)
    url = head["url"]
    season = int(re.search(r"/injuries/league/(\d{4})/", url).group(1))
    week = int(re.search(r"/(?:reg|pre|post)(\d+)", url).group(1))
    rows: list[dict] = []
    gaps: list[dict] = []
    variants: dict[str, str] = {}
    games: list[dict] = []
    ctx = _new_game()
    expect_broadcast = False
    club = club_side = ""
    unparsed = 0
    no_injuries: list[dict] = []
    unparsed_lines: list[dict] = []
    body = body_lines(path)
    # The last line that looks like a table line is where a truncated fetch leaves off, so it is classified
    # differently from a line in the middle of a table that simply does not match a known shape.
    last_table_line = max((i for i, x in enumerate(body) if x.lstrip().startswith("|")), default=-1)
    table_lines = [i for i, x in enumerate(body) if x.lstrip().startswith("|")]


    def close() -> None:
        if ctx["clubs"]:
            ctx["index"] = len(games) + 1
            games.append(dict(ctx))
    for idx, raw_line in enumerate(body):
        line = raw_line.rstrip()
        if not line:
            continue
        if line.startswith("<!-- CAPTURE TRUNCATED HERE"):
            gaps.append({"capture": path.name, "season": season, "week": week,
                         "fixture_no": len(games) + 1,
                         "kind": "chunk-boundary truncation",
                         "clubs_captured_in_this_fixture": [c["code"] for c in ctx["clubs"]],
                         "detail": "the retained chunk ends mid-page. Every fixture and club table after "
                                   "this point is uncaptured, which is not the same as those clubs having "
                                   "nothing to report."})
            continue
        m = DAY_HEAD.match(line)
        if m:
            close()                               # a day heading can follow an unclosed Thursday game
            ctx = _new_game(m.group(1))
            expect_broadcast = False
            club = ""
            continue
        if KICKOFF.match(line):
            if ctx["clubs"]:                      # second fixture under the same day heading
                close()
                ctx = _new_game(ctx["day"])
            ctx["kickoff"] = line
            expect_broadcast = True
            club = ""
            continue
        m = FIXTURE_HEAD.match(line)
        if m:
            logo_code, _s1, printed_code, name, _s2 = m.groups()
            if logo_code != printed_code:
                variants[printed_code] = logo_code
            ctx["clubs"].append({"code": printed_code, "name": name, "logo_code": logo_code})
            expect_broadcast = False
            club = ""
            continue
        m = RECORD.match(line)
        if m:
            ctx["records"].append(m.group(1))
            continue
        if expect_broadcast:
            ctx["broadcast"] = line.strip()
            expect_broadcast = False
            continue
        m = CAPTION.match(line)
        if m and not line.startswith("|"):
            name = line.strip()
            match = [(s, c) for s, c in zip(("away", "home"), ctx["clubs"]) if c["name"] == name]
            if match:
                club, club_side = match[0][1]["name"], match[0][0]
            else:
                club = club_side = ""
            continue
        if NO_INJ_PHRASE.search(line) and not line.startswith("|"):
            no_injuries.append({"club": club or "(no club heading above it)",
                                "fixture_no": len(games) + 1, "line": line[:120]})
            continue
        if line.startswith("|"):
            if "---" in line or line.startswith("| Player"):
                continue
            m = PLAYER_ROW.match(line)
            if m and club:
                name, purl, _slug, pos, injury, practice, status = (g.strip() for g in m.groups())
                fixture_no = len(games) + 1
                rows.append({
                    "capture": path.name, "season": season, "week": week, "fixture_no": fixture_no,
                    "day": ctx["day"], "kickoff": ctx["kickoff"], "broadcast": ctx["broadcast"],
                    "away": ctx["clubs"][0]["code"] if len(ctx["clubs"]) > 0 else "",
                    "home": ctx["clubs"][1]["code"] if len(ctx["clubs"]) > 1 else "",
                    "away_name": ctx["clubs"][0]["name"] if len(ctx["clubs"]) > 0 else "",
                    "home_name": ctx["clubs"][1]["name"] if len(ctx["clubs"]) > 1 else "",
                    "club": club, "club_side": club_side,
                    "record_at_capture": (ctx["records"][0 if club_side == "away" else 1]
                                          if len(ctx["records"]) > (0 if club_side == "away" else 1)
                                          else ""),
                    "player": name, "player_url": purl, "position_code": pos,
                    "injury_text": injury, "practice_status": practice, "game_status": status,
                    "unit": (mapping.get(pos, {}) or {}).get("unit", ""),
                    "raw_line": line,
                })
                continue
            unparsed += 1
            tail_after = len([i for i in range(idx + 1, len(body)) if body[i].strip()]) - \
                sum(1 for i in range(idx + 1, len(body)) if body[i].lstrip().startswith("|"))
            if idx == last_table_line and not line.rstrip().endswith("|"):
                cls = ("the last table line in the retained text, and it does not end on a pipe: a row cut "
                       "off where the fetch stopped. This is a retrieval gap (flag H04), not an unknown page "
                       "shape")
            elif idx == last_table_line:
                cls = ("the last table line in the retained text and complete in form, yet it matches no "
                       "row shape - open the page and check before publishing this week")
            else:
                cls = ("a line inside the table that matches no row shape: either the page changed or this "
                       "parser is wrong. It is counted, quoted and published, never dropped quietly")
            unparsed_lines.append({
                "line": line[:200], "line_index": idx, "line_columns_present": line.count("|"),
                "columns_a_row_needs": 6, "lines_of_prose_after_it_before_the_end": tail_after,
                "at_last_table_line": idx == last_table_line, "classification": cls,
            })
    close()
    for g in gaps:
        g["club_code_variants"] = dict(sorted(variants.items()))
    meta = {"capture": path.name, "url": url, "season": season, "week": week,
            "retrieved_utc": head.get("retrieved_utc", ""), "chunk": head.get("chunk", ""),
            "fixtures": [{k: v for k, v in g.items() if k != "records"} | {"records": g["records"],
                          "rows": sum(1 for r in rows if r["fixture_no"] == g["index"])}
                         for g in games],
            "fixtures_captured": len(games), "player_rows": len(rows),
            # An empty list must never be read as "no club printed the phrase". It means the phrase was not
            # seen in the chunks retained here, which is a different claim entirely.
            "no_injuries_reported": no_injuries,
            "no_injuries_reported_scope": ("the retained text was searched for the literal phrase 'No "
                                          "Injuries Reported'; a hit is recorded per club, and an empty "
                                          "result means not seen in the chunks retained, never that no "
                                          "club printed it"),
            "clubs_captured": sorted({r["club"] for r in rows}),
            "club_code_variants": dict(sorted(variants.items())),
            "unparsed_table_lines": unparsed, "unparsed_lines": unparsed_lines,
            "truncated": bool(gaps),
            "page_title": head.get("page <title>", ""), "page_h2": head.get("page <h2>", "")}
    return rows, gaps, meta


def parse_depth_capture(path: Path) -> dict:
    """Ordered strings for one club chart, exactly as printed. The column index is the string number."""
    head = capture_header(path)
    unit = ""
    out = {"capture": path.name, "url": head.get("url", ""),
           "retrieved_utc": head.get("retrieved_utc", ""), "title": head.get("page <title>", ""),
           "provenance_lines": [], "prose_lines": [],
           "units": {"Offense": [], "Defense": [], "Special Teams": []},
           "chunk": head.get("chunks", head.get("chunk", ""))}
    for raw_line in body_lines(path):
        line = raw_line.rstrip()
        if line.startswith("#") and "Unofficial" in line:
            out["provenance_lines"].append(line.lstrip("# ").strip())
        if (line and not line.startswith(("#", "|", "<", "-", "[")) and "CAPTURE" not in line
                and len(out["prose_lines"]) < 2):
            out["prose_lines"].append(line.strip())
        hit = next((v for k, v in (("## Offense", "Offense"), ("## Defense", "Defense"),
                                   ("## Special Teams", "Special Teams")) if line.startswith(k)), None)
        if hit:
            unit = hit
            continue
        if line.startswith("#"):
            unit = ""
            continue
        if not unit or not line.startswith("|") or "---" in line:
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not cells or not re.fullmatch(r"[A-Z-]{1,4}", cells[0]):
            continue
        strings = [[{"name": n, "url": u} for n, u in DEPTH_CELL.findall(cell)] for cell in cells[1:]]
        while strings and not strings[-1]:
            strings.pop()
        out["units"][unit].append({"position_label": cells[0], "raw_line": line, "strings": strings,
                                   "ambiguous_cells": [i + 1 for i, s in enumerate(strings) if len(s) > 1]})
    out["row_count"] = sum(len(v) for v in out["units"].values())
    return out


def main() -> int:
    mapping = conventions.unit_map()
    injury_rows: list[dict] = []
    gaps: list[dict] = []
    charts: list[dict] = []
    metas: list[dict] = []
    for path in sorted(RAW.glob("*.md")):
        url = capture_header(path).get("url", "")
        if "/injuries/league/" in url:
            rows, cap_gaps, meta = parse_injury_capture(path, mapping)
            injury_rows.extend(rows)
            gaps.extend(cap_gaps)
            metas.append(meta)
        elif "/team/depth-chart" in url:
            charts.append(parse_depth_capture(path))
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "captures.json").write_text(json.dumps({
        "_comment": ["Generated by injury_lab/parse.py from injury_lab/raw/*.md. Do not edit by hand.",
                     "Every field is a transcription of a retained official capture. An empty string means "
                     "the official page printed nothing in that cell - it does not mean healthy, and it "
                     "does not mean zero."],
        "generated_by": "injury_lab/parse.py",
        "unit_map_source": "injury_lab/conventions.py over the captured legend and chart section headings",
        "captures": metas,
        "injury_rows": injury_rows,
        "capture_gaps": gaps,
    }, indent=2) + "\n", encoding="utf-8")
    (DATA / "depth.json").write_text(json.dumps({
        "_comment": ["Generated by injury_lab/parse.py. String number = printed column index, a reading "
                     "rule published for audit: none of these clubs prints the words '1st string'.",
                     "An empty cell stays empty; a name is never carried across from a neighbouring slot."],
        "generated_by": "injury_lab/parse.py",
        "charts": charts,
    }, indent=2) + "\n", encoding="utf-8")
    print(f"parse: {len(injury_rows)} injury rows from "
          f"{len({r['capture'] for r in injury_rows})} captures; {len(charts)} depth charts; "
          f"{len(gaps)} capture-gap records")
    for m in metas:
        print(f"  {m['capture']:28s} rows={m['player_rows']:3d} fixtures={m['fixtures_captured']:2d} "
              f"clubs={','.join(m['clubs_captured'])}")
    blank = sum(1 for r in injury_rows if not r["unit"])
    print(f"  unit coverage: {len(injury_rows) - blank}/{len(injury_rows)} rows placed in a unit by a "
          f"captured page; {blank} blank and flagged")
    return 0


if __name__ == "__main__":
    sys.exit(main())
