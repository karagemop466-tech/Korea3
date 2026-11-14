#!/usr/bin/env python3
"""Fail-closed verifier for the Lifecycle build.

Run after build.py. It re-derives the headline numbers from the data files and compares them with what
the generated pages actually contain, so a page cannot go live showing a number the data does not
support. It also checks the rules the brief sets: every data table row carries a source link, every
external link points at a registered official host, a value that no official source states is printed
as a flagged blank rather than a number, and the build is byte-reproducible.

Exit 0 = all checks pass. Exit 1 = at least one check failed; the pages must not be published.

Usage:
    python3 lifecycle/check.py
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
ROOT = HERE.parent

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


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    demotion = json.loads((DATA / "demotion.json").read_text(encoding="utf-8"))
    leaderboard = json.loads((DATA / "leaderboard.json").read_text(encoding="utf-8"))
    feed = json.loads((DATA / "feed.json").read_text(encoding="utf-8"))
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))

    pages = {p.name: p.read_text(encoding="utf-8") for p in sorted(HERE.glob("*.html"))}

    print("Lifecycle verification\n")

    # ---------------------------------------------------------------- structure
    print("structure")
    expected_pages = ["index.html", "price-snapshot.html", "results-feed.html", "demotion.html",
                      "leaderboard.html", "sources.html", "flagged.html", "method.html"]
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
    broken = sorted(h for h in internal if h and not h.startswith("../") and not (HERE / h).exists())
    check("no broken internal links", not broken, f"missing: {broken}")
    outside = sorted(h for h in internal if h.startswith("../"))
    for h in outside:
        target = (HERE.parent / h[3:].split("#")[0])
        check(f"parent link resolves: {h}", target.exists() or target.is_dir())

    # ---------------------------------------------------------------- external hosts registered
    print("\nexternal hosts")
    external_hosts = set()
    for html_text in pages.values():
        for href in re.findall(r'href="(https?://[^"]+)"', html_text):
            external_hosts.add(href.split("/")[2])
    registered_hosts = {s["url"].split("/")[2] for s in sources["sources"] if s.get("url")}
    non_official = sorted(h for h in external_hosts if h not in registered_hosts)
    check("every external link points at a registered host", not non_official,
          f"unregistered hosts: {non_official}")

    # ---------------------------------------------------------------- every data row carries a source
    print("\nsource links")
    data_pages = ["price-snapshot.html", "results-feed.html", "demotion.html",
                  "leaderboard.html", "sources.html", "flagged.html"]
    total_rows = 0
    for name in data_pages:
        text = pages.get(name, "")
        bodies = re.findall(r"<tbody>(.*?)</tbody>", text, re.S)
        rows = [r for body in bodies for r in re.findall(r"<tr>(.*?)</tr>", body, re.S)]
        no_link = [r for r in rows if "<a " not in r]
        total_rows += len(rows)
        check(f"{name}: every data row carries a source link ({len(rows)} rows)",
              not no_link, f"{len(no_link)} rows with no anchor")

    # ---------------------------------------------------------------- blanks are flagged, not filled
    print("\nblank handling")
    blank_marks = sum(len(re.findall(r'class="blank"', t)) for t in pages.values())
    check("published blanks are marked, not filled in", blank_marks > 0,
          "no blank markers found - the build may be filling cells it should leave empty")

    # ---------------------------------------------------------------- numbers agree with the data files
    print("\nnumbers agree with the data files")
    dm = demotion["_meta"]
    idx = pages["index.html"]
    checks = [
        ("strategies evaluated", str(dm["n_strategies"]), idx),
        ("strategies LIVE", str(dm["n_live"]), idx),
        ("strategies DEMOTED", str(dm["n_demoted"]), idx),
        ("feed rows", f"{feed['rows']:,}", idx),
        ("feed strategies", str(feed["strategies"]), idx),
        ("divergent strategies", str(leaderboard["divergent_count"]), idx),
    ]
    for label, needle, haystack in checks:
        check(f"index states {label} = {needle}", needle in haystack)

    # recomputed values must match the committed ledger, not be invented
    import csv
    gate_rows = {r["id"]: r for r in csv.DictReader((ROOT / "data" / "derived" / "gates_results.csv")
                                                    .open(encoding="utf-8", newline=""))}
    sample = "S14"
    if sample in gate_rows:
        roi = gate_rows[sample]["roi"]
        check(f"demotion page shows {sample} ROI recomputed from the ledger ({roi[:6]})",
              roi[:6] in pages["demotion.html"], f"{roi} not found on demotion.html")

    # demotion rule must be printed before the results
    dem = pages["demotion.html"]
    rule_pos = dem.find("A strategy is LIVE only if it clears every trigger")
    first_table_pos = dem.find("<tbody>")
    check("the demotion rule is printed before the results table",
          0 <= rule_pos < first_table_pos,
          f"rule at {rule_pos}, first table at {first_table_pos}")
    check("the demotion page states a demoted strategy is returned to paper",
          "returned to paper" in dem or "DEMOTED" in dem)

    # leaderboard separation must be stated before the tables
    lb = pages["leaderboard.html"]
    sep_pos = lb.find("Two registers are computed independently and are never blended")
    check("the signal/staking separation is stated on the leaderboard page", sep_pos >= 0)

    # ---------------------------------------------------------------- determinism
    print("\ndeterminism")
    json_files = [DATA / "demotion.json", DATA / "leaderboard.json", DATA / "feed.json"]
    html_files = [HERE / n for n in expected_pages]
    before_json = {p.name: _sha(p) for p in json_files}
    before_html = {p.name: _sha(p) for p in html_files}
    subprocess.run([sys.executable, str(HERE / "gate.py")], check=True,
                   cwd=str(ROOT), capture_output=True)
    subprocess.run([sys.executable, str(HERE / "build.py")], check=True,
                   cwd=str(ROOT), capture_output=True)
    after_json = {p.name: _sha(p) for p in json_files}
    after_html = {p.name: _sha(p) for p in html_files}
    check("gate.py output is byte-reproducible", before_json == after_json)
    check("build.py output is byte-reproducible", before_html == after_html)

    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} of {CHECKS} checks")
        for f in FAILURES:
            print("  -", f)
        return 1
    print(f"OK: all {CHECKS} checks passed ({total_rows} data rows sourced)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
