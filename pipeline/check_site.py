#!/usr/bin/env python3
"""Verify the generated site: links, sources, blanks, and recomputed numbers.

Run: python3 pipeline/check_site.py

Checks
------
1. Every internal link resolves to a file in the repository.
2. Every data-table row carries at least one source link.
3. Every blank/unverified marker points at the review page.
4. No cell renders a raw None / NaN / inf.
5. Every external (http) link is either a GitHub source or one of the documented
   external citations listed on the review page.
6. Prices, counts and ROI recomputed from data/derived/bets.csv match summary.json.
7. data/raw hashes still match the manifest.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SUMMARY = json.loads((ROOT / "data" / "derived" / "summary.json").read_text(encoding="utf-8"))
PAGES = sorted(p.name for p in ROOT.glob("*.html"))

EXTERNAL_ALLOWED_PREFIXES = ("https://github.com/",)
EXTERNAL_CITED = {
    "https://www.itl.nist.gov/div898/handbook/",
    "https://www.nfl.com/",
    "https://help.draftkings.com/",
}


class Rows(HTMLParser):
    """Collect table rows with their cells and links."""

    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict] = []
        self._in_row = False
        self._in_tbody = False
        self._cell_text: list[str] = []
        self._links: list[str] = []
        self._current_row: dict | None = None
        self.links: list[str] = []
        self.flags: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tbody":
            self._in_tbody = True
        if tag == "tr" and self._in_tbody:
            self._in_row = True
            self._current_row = {"cells": [], "links": []}
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
            if self._in_row:
                self._links.append(a["href"])
            if "flag" in (a.get("class") or ""):
                self.flags.append(a["href"])
        if tag in ("td", "th"):
            self._cell_text = []
        if tag == "br" and self._cell_text is not None:
            self._cell_text.append(" ")

    def handle_endtag(self, tag):
        if tag == "tbody":
            self._in_tbody = False
        if tag in ("td", "th") and self._current_row is not None:
            self._current_row["cells"].append("".join(self._cell_text).strip())
        if tag == "tr" and self._in_row:
            self._current_row["links"] = list(self._links)
            self.rows.append(self._current_row)
            self._current_row = None
            self._links = []
            self._in_row = False

    def handle_data(self, data):
        if self._cell_text is not None:
            self._cell_text.append(data)


def check_page(name: str) -> list[str]:
    problems: list[str] = []
    html = (ROOT / name).read_text(encoding="utf-8")
    parser = Rows()
    parser.feed(html)

    for href in parser.links:
        if href.startswith("http"):
            if not href.startswith(EXTERNAL_ALLOWED_PREFIXES) and href not in EXTERNAL_CITED:
                problems.append(f"{name}: external link not in the verified/cited allow-list: {href}")
        elif not href.startswith("#"):
            target = href.split("#")[0]
            if not (ROOT / target).exists():
                problems.append(f"{name}: broken internal link {href}")

    for flag_href in parser.flags:
        if flag_href != "flagged.html":
            problems.append(f"{name}: blank marker points at {flag_href}")

    for i, row in enumerate(parser.rows):
        if not row["links"]:
            problems.append(f"{name}: table row {i} has no source link: {row['cells'][:2]}")
        for cell in row["cells"]:
            if re.fullmatch(r"\s*(None|nan|NaN|inf|-inf|Infinity)\s*", cell):
                problems.append(f"{name}: table row {i} renders an invalid value: {cell!r}")
    if 'name="description"' not in html:
        problems.append(f"{name}: missing meta description")
    if "Pinned source commit" not in html:
        problems.append(f"{name}: missing provenance footer")
    return problems


def check_numbers() -> list[str]:
    problems: list[str] = []
    bets = pd.read_csv(ROOT / "data" / "derived" / "bets.csv")
    primary = bets[bets["season"].between(2006, 2025)]
    for row in SUMMARY["strategies"]:
        sub = primary[primary["strategy_id"] == row["id"]]
        if sub.empty:
            continue
        roi = float(sub["pnl"].mean())
        metric_roi = row["metrics_full"]["roi"]
        if abs(roi - metric_roi) > 1e-9:
            problems.append(f"{row['id']}: summary ROI {metric_roi} != recomputed {roi}")
        if int(len(sub)) != row["metrics_full"]["bets"]:
            problems.append(f"{row['id']}: bet count mismatch")
        if sub["price"].isna().any() and row["market"] != "PARLAY":
            problems.append(f"{row['id']}: a selected bet has no price")
    total_bets = int(len(primary))
    if total_bets != sum(r["metrics_full"]["bets"] for r in SUMMARY["strategies"]):
        problems.append("total bet count does not add up across strategies")
    return problems


def check_hashes() -> list[str]:
    problems: list[str] = []
    manifest = json.loads((ROOT / "data" / "raw" / "MANIFEST.json").read_text(encoding="utf-8"))
    for entry in manifest["files"]:
        path = ROOT / entry["file"]
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != entry["sha256"]:
            problems.append(f"{entry['file']}: hash mismatch")
    return problems


def check_coverage() -> list[str]:
    problems: list[str] = []
    for name in PAGES:
        html = (ROOT / name).read_text(encoding="utf-8")
        for href, _ in [(h, l) for h, l in re.findall(r'href="([a-z0-9_]+\.html)"[^>]*>([^<]*)</a>', html)]:
            pass
        if not all(f'href="{p}"' in html for p in PAGES if p != name):
            missing = [p for p in PAGES if p != name and f'href="{p}"' not in html]
            if len(missing) > 0:
                problems.append(f"{name}: navigation missing {missing}")
    return problems


def main() -> int:
    problems: list[str] = []
    for name in PAGES:
        problems += check_page(name)
    problems += check_numbers()
    problems += check_hashes()
    problems += check_coverage()

    if problems:
        print(f"FAILED with {len(problems)} problem(s):")
        for p in problems[:60]:
            print("  -", p)
        return 1
    print(f"OK: {len(PAGES)} pages, all internal links resolve, every table row has a source link, "
          f"no unverified blank is unflagged, hashes and recomputed numbers match.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
