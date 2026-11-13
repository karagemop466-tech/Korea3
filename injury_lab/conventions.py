#!/usr/bin/env python3
"""Position-code to unit mapping, built only from pages in this capture set.

Why this file exists as code over data rather than as a dict of my own opinions: both the injury report
and the club depth charts print a bare position code and no unit, and every injury-aware feature the brief
asks for ("2nd, 3rd or 4th string backups in the **defenses**") needs a unit. So the rule has to be
auditable, and it has to fail loudly rather than guess.

Two sources of evidence, in that order of preference:

1. ``legend`` - the LEGEND block printed on the captured New England depth chart, which defines codes such
   as ``OLB : Outside Linebacker`` and groups them under a DEFENSE heading.
2. ``chart heading`` - a code that appears as a row label under a club's own ``## Offense`` / ``## Defense``
   / ``## Special Teams`` section is in that unit on that club's page. Nothing is inferred; the
   publisher put the row under the heading.

A code with evidence in more than one unit is marked ``conflict`` and printed blank. A code with no
evidence at all is marked ``undefined`` and printed blank. Both are reported, because the size of that
hole is itself a finding: the report's ``DE`` cannot be joined to the clubs' ``EDGE`` / ``DL`` / ``LDE`` /
``RDE`` from any page in this capture set, and the report's ``T`` / ``G`` cannot be joined to ``LT`` /
``RT`` / ``LG`` / ``RG``. A "defensive front depleted" feature is therefore not computable across clubs
from these sources, and this module says so instead of quietly deciding that DE means EDGE.

Usage:  python3 -m injury_lab.conventions
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
RAW = HERE / "raw"
LEGEND_CAPTURE = RAW / "2026-depth-ne.md"
CHART_CAPTURES = ("2026-depth-ne.md", "2026-depth-det.md", "2026-depth-dal.md")

UNITS = ("Offense", "Defense", "Special Teams")
_SECTION = {"## Offense": "Offense", "## Defense": "Defense", "## Special Teams": "Special Teams"}
_CODE_ROW = re.compile(r"^\|\s*([A-Z-]{1,4})\s*\|")


def legend_from_capture(path: Path = LEGEND_CAPTURE) -> dict[str, dict[str, str]]:
    """Read the LEGEND block of the captured New England chart.

    Inside the ``## LEGEND`` block, a bare unit heading sets the current unit and a ``CODE  : Full name``
    line defines one code. Matched on literal text, so a change on the club's page breaks this instead of
    passing unnoticed.
    """
    text = path.read_text(encoding="utf-8")
    body = text.split("## LEGEND (as printed on the page)", 1)
    if len(body) != 2:
        raise ValueError("LEGEND block not found in the captured chart - the capture changed shape")
    block = body[1].split("<!--", 1)[0]
    out: dict[str, dict[str, str]] = {}
    unit = ""
    for raw_line in block.splitlines():
        line = raw_line.strip().lstrip("-").strip()
        if not line:
            continue
        if ":" not in line:
            upper = line.upper()
            if upper in ("OFFENSE", "DEFENSE", "SPECIAL TEAMS"):
                unit = upper.title() if upper != "SPECIAL TEAMS" else "Special Teams"
            continue
        code, _, defines = line.partition(":")
        code, defines = code.strip(), defines.strip()
        if code and code.upper() == code:
            out[code] = {"unit": unit, "defines": defines, "source": str(path.name), "source_line": line}
    if not out:
        raise ValueError("no position codes parsed from the LEGEND block")
    return out


def chart_headings() -> dict[str, list[dict[str, str]]]:
    """Every row label each captured chart prints, with the section heading it sits under."""
    out: dict[str, list[dict[str, str]]] = {}
    for name in CHART_CAPTURES:
        path = RAW / name
        if not path.is_file():
            continue
        section = ""
        rows: list[dict[str, str]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            line = line.rstrip()
            if line in _SECTION:
                section = _SECTION[line]
                continue
            if line.startswith("#"):
                section = ""
                continue
            m = _CODE_ROW.match(line)
            if section and m:
                rows.append({"code": m.group(1), "unit": section, "source": name, "source_line": line})
        out[name] = rows
    return out


def unit_map() -> dict[str, dict[str, object]]:
    """code -> {unit, basis, evidence}. unit is '' whenever the basis is conflict or undefined."""
    legend = legend_from_capture()
    headings = chart_headings()
    evidence: dict[str, list[dict[str, str]]] = {}
    for code, hit in legend.items():
        evidence.setdefault(code, []).append({"code": code, "unit": hit["unit"],
                                              "source": hit["source"], "source_line": hit["source_line"],
                                              "basis": "legend"})
    for rows in headings.values():
        for hit in rows:
            evidence.setdefault(hit["code"], []).append(hit)
    out: dict[str, dict[str, object]] = {}
    for code, hits in sorted(evidence.items()):
        units = sorted({h["unit"] for h in hits if h["unit"]})
        if len(units) == 1:
            out[code] = {"unit": units[0], "basis": "legend" if any(h.get("basis") == "legend" for h in hits)
                         else "chart section heading", "evidence": hits}
        elif len(units) > 1:
            out[code] = {"unit": "", "basis": "conflict", "evidence": hits,
                         "why_blank": f"printed under {', '.join(units)} on different captured pages"}
        else:
            out[code] = {"unit": "", "basis": "undefined", "evidence": hits,
                         "why_blank": "no unit heading or legend entry on any captured page"}
    return out


def unit_of(code: str, mapping: dict | None = None) -> str:
    mapping = mapping if mapping is not None else unit_map()
    hit = mapping.get((code or "").strip())
    return hit["unit"] if hit else ""


def main() -> None:
    m = unit_map()
    print(json.dumps({"codes": len(m),
                      "mapped": sum(1 for v in m.values() if v["unit"]),
                      "blank_conflict": sum(1 for v in m.values() if v["basis"] == "conflict"),
                      "blank_undefined": sum(1 for v in m.values() if v["basis"] == "undefined"),
                      "table": {k: {"unit": v["unit"], "basis": v["basis"]} for k, v in m.items()}},
                     indent=2))
    print("\ncodes the injury report prints that this mapping cannot place - printed blank, never guessed:")
    print("  " + ", ".join(sorted({"DE", "DT", "G", "T", "CB", "S", "LB", "QB", "WR", "TE", "RB", "FB",
                                  "K", "C", "P", "LS"} - set(m))))


if __name__ == "__main__":
    main()
