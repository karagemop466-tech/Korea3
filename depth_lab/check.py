#!/usr/bin/env python3
"""Fail-closed verifier for the Depth Lab build.

Run after build.py. It re-derives the headline numbers from the data files and compares them with
what the generated pages actually contain, so a page cannot go live showing a number the data does
not support. It also checks the two rules the brief sets: every table row carries a source link,
and a value that no official source states is printed as a flagged blank rather than a number.

Exit 0 = all checks pass. Exit 1 = at least one check failed; the pages must not be published.

Usage:
    python3 depth_lab/check.py
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
RAW = DATA / "raw"

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


def main() -> int:
    depth = json.loads((DATA / "depth.json").read_text(encoding="utf-8"))
    repl = json.loads((DATA / "replacements.json").read_text(encoding="utf-8"))
    inj = json.loads((RAW / "nfl_injury_w10_2026.json").read_text(encoding="utf-8"))
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))

    pages = {p.name: p.read_text(encoding="utf-8")
             for p in sorted(HERE.glob("*.html"))}

    print("Depth Lab verification\n")

    # ---------------------------------------------------------------- structure
    print("structure")
    expected_pages = ["index.html", "depth.html", "replacements.html", "questionable.html",
                      "injuries.html", "flagged.html", "sources.html", "method.html"]
    for name in expected_pages:
        check(f"page exists: {name}", name in pages)
    check("stylesheet exists", (HERE / "assets" / "style.css").exists())

    # ---------------------------------------------------------------- no broken internal links
    print("\ninternal links")
    internal = set()
    for html_text in pages.values():
        for href in re.findall(r'href="([^"]+)"', html_text):
            if href.startswith(("http", "mailto:", "#", "javascript:")):
                continue
            internal.add(href.split("#")[0])
    broken = sorted(h for h in internal
                    if h and not h.startswith("../") and not (HERE / h).exists())
    check("no broken internal links", not broken, f"missing: {broken}")
    outside = sorted(h for h in internal if h.startswith("../"))
    for h in outside:
        target = (HERE.parent / h[3:].split("#")[0])
        check(f"parent link resolves: {h}", target.exists() or target.is_dir())

    # ---------------------------------------------------------------- every row has a source
    print("\nsource links")
    external_hosts = set()
    for html_text in pages.values():
        for href in re.findall(r'href="(https?://[^"]+)"', html_text):
            external_hosts.add(href.split("/")[2])
    official_hosts = {s["url"].split("/")[2] for s in sources["sources"] if s["url"]}
    official_hosts.add("www.nfl.com")
    non_official = sorted(h for h in external_hosts if h not in official_hosts)
    check("every external link points at a registered official host",
          not non_official, f"unregistered hosts: {non_official}")

    # every table row on the data pages must contain at least one anchor
    for name in ("replacements.html", "questionable.html", "flagged.html", "sources.html",
                 "injuries.html"):
        text = pages.get(name, "")
        bodies = re.findall(r"<tbody>(.*?)</tbody>", text, re.S)
        rows = [r for body in bodies for r in re.findall(r"<tr>(.*?)</tr>", body, re.S)]
        no_link = [r for r in rows if "<a " not in r]
        check(f"{name}: every data row carries a source link ({len(rows)} rows)",
              not no_link, f"{len(no_link)} rows with no anchor")

    # ---------------------------------------------------------------- blanks are flagged, not filled
    print("\nblank handling")
    blank_marks = sum(len(re.findall(r'class="blank"', t)) for t in pages.values())
    check("published blanks are marked, not filled in", blank_marks > 0,
          "no blank markers found - the build may be filling cells it should leave empty")
    # a replacement row with no replacement must not show a name
    empty_repl = [r for r in repl["rows"] if not r["replacement"]]
    repl_html = pages["replacements.html"]
    check(f"replacements page shows {len(empty_repl)} blank replacement cells",
          repl_html.count("the club published no further name at this position") >= len(empty_repl))

    # ---------------------------------------------------------------- numbers agree with the data
    print("\nnumbers agree with the data files")
    clubs_captured = depth["clubs_captured"]
    players = [r for r in depth["rows"] if r["player"]]
    co_listed = [r for r in depth["rows"] if r["co_listed"]]
    out_rows = len(repl["rows"])
    named = sum(1 for r in repl["rows"] if r["replacement"])
    q = len(repl["questionable"])
    inj_rows = sum(len(c["rows"]) for c in inj["clubs"])

    idx = pages["index.html"]
    checks = [
        ("clubs captured", f"{clubs_captured} of 32", idx),
        ("player entries", f"{len(players):,}", idx),
        ("co-listed entries", str(len(co_listed)), idx),
        ("outdoubtful count", str(out_rows), idx),
        ("questionable count", str(q), idx),
        ("injury rows", f"{inj_rows:,}", idx),
    ]
    for label, needle, haystack in checks:
        check(f"index states {label} = {needle}", needle in haystack)

    check("replacements page row count matches data",
          repl_html.count('<span class="code">') >= out_rows)
    check("questionable page row count matches data",
          pages["questionable.html"].count('<span class="code">') >= q)

    # ---------------------------------------------------------------- coverage gap is honoured
    print("\ncoverage and honesty")
    gap_codes = [g["code"] for g in depth["coverage_gaps"]]
    for code in gap_codes:
        check(f"{code} absent from the depth tables (no values invented)",
              f'id="{code}"' not in pages["depth.html"])
        check(f"{code} listed on the flagged page", code in pages["flagged.html"])
    for code in inj["_meta"]["absent_clubs"]:
        check(f"{code} absent from the injury tables", f'id="inj-{code}"' not in pages["injuries.html"])
    check("the join rule is printed on the replacements page",
          "A row appears when the 1st-string player named" in repl_html)
    check("the replacements page states it is not an official designation",
          "not an official depth designation" in repl_html)
    check("the clubs' own disclaimer is quoted",
          "unofficial and is published by the writers of Patriots.com" in pages["flagged.html"])
    check("the shared allow-list question is disclosed on the sources page",
          "OFFICIAL_HOSTS" in pages["sources.html"])

    # ---------------------------------------------------------------- no invented currency
    print("\nno fabricated values")
    # The brief forbids inventing prices, correlations, ROI or probabilities.
    banned = [r"\bROI\b", r"\bBrier\b", r"-\d+\.\d+%", r"\bspread\b", r"\bmoneyline\b", r"\bparlay\b"]
    for name in ("depth.html", "injuries.html"):
        hits = [b for b in banned if re.search(b, pages[name])]
        check(f"{name} carries no price/edge/correlation language", not hits, f"found {hits}")

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} of {CHECKS} checks")
        for f in FAILURES:
            print("  -", f)
        return 1
    print(f"OK: all {CHECKS} checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
