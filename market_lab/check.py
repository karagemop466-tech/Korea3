#!/usr/bin/env python3
"""Fail-closed verifier for the Markets Ledger.

Run: python3 -m market_lab.check

Checks
------
1. Every generated page exists, has a meta description and the provenance footer.
2. Every navigation entry resolves and is present on every page.
3. Every data-table row carries at least one source link.
4. No cell renders a raw None / NaN / inf.
5. Every internal link resolves to a file in market_lab/; every external link is on the
   verified allow-list (github.com, nfl.com, operations.nfl.com).
6. The published counts match the data: snapshot, results-feed and demotion numbers
   recomputed from the CSVs agree with market_summary.json.
7. fair_vs_market difference == fair_line - market_line on every row.
8. signal_staking ranks are a permutation of 1..n and the masking flag is consistent.
9. demotion status follows the rule from the demotion module.

Any failure returns a non-zero exit code.
"""
from __future__ import annotations

import json
import math
import re
import sys
from html.parser import HTMLParser
from pathlib import Path

import pandas as pd

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
DATA = BASE / "data"

PAGES = ["index", "snapshot", "results", "origination", "fair_vs_market",
         "signal_staking", "demotion", "flagged", "sources", "method"]

EXTERNAL_ALLOWED_PREFIXES = (
    "https://github.com/",
    "https://www.nfl.com/",
    "https://operations.nfl.com/",
    "https://codeload.github.com/",
)


class Rows(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.rows: list[dict] = []
        self.links: list[str] = []
        self._in_row = False
        self._in_tbody = False
        self._cell_text: list[str] = []
        self._links: list[str] = []
        self._current_row: dict | None = None

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
        if tag in ("td", "th"):
            self._cell_text = []

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
        if self._current_row is not None or self._cell_text is not None:
            self._cell_text.append(data)


def check_page(name: str) -> list[str]:
    problems: list[str] = []
    html = (BASE / f"{name}.html").read_text(encoding="utf-8")
    parser = Rows()
    parser.feed(html)

    for href in parser.links:
        if href.startswith("http"):
            if not href.startswith(EXTERNAL_ALLOWED_PREFIXES):
                problems.append(f"{name}: external link not on the allow-list: {href}")
        elif not href.startswith("#"):
            target = href.split("#")[0].split("?")[0]
            if not (BASE / target).exists():
                problems.append(f"{name}: broken internal link {href}")

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
    # navigation present
    for p in PAGES:
        if p == name:
            continue
        if f'href="{p}.html"' not in html:
            problems.append(f"{name}: navigation missing {p}.html")
    return problems


def check_data_files() -> list[str]:
    problems: list[str] = []
    required = {
        "price_snapshot.csv": ["game_id", "market", "side", "opening_line", "closing_line",
                               "opening_source", "closing_source", "flags"],
        "results_feed.csv": ["game_id", "market", "side", "recorded_outcome", "recomputed_outcome",
                             "official_home_score", "official_away_score", "verification", "source"],
        "fair_vs_market.csv": ["game_id", "market", "fair_line", "market_line", "difference", "source"],
        "signal_staking.csv": ["id", "signal_rank", "staking_rank", "rank_gap", "source"],
        "demotion_gate.csv": ["id", "status", "source"],
    }
    for fname, cols in required.items():
        path = DATA / fname
        if not path.exists():
            problems.append(f"missing data file: {fname}")
            continue
        df = pd.read_csv(path, low_memory=False)
        for c in cols:
            if c not in df.columns:
                problems.append(f"{fname}: missing column {c}")
    return problems


def check_numbers() -> list[str]:
    problems: list[str] = []
    summary = json.loads((DATA / "market_summary.json").read_text(encoding="utf-8"))

    snap = pd.read_csv(DATA / "price_snapshot.csv", low_memory=False)
    res = pd.read_csv(DATA / "results_feed.csv", low_memory=False)
    fair = pd.read_csv(DATA / "fair_vs_market.csv", low_memory=False)
    sig = pd.read_csv(DATA / "signal_staking.csv", low_memory=False)
    dem = pd.read_csv(DATA / "demotion_gate.csv", low_memory=False)

    # snapshot counts (moneyline rows carry odds but no line, so count by source column)
    if len(snap) != summary["snapshot"]["store_records"]:
        problems.append(f"snapshot rows {len(snap)} != summary {summary['snapshot']['store_records']}")
    if int((snap["opening_source"].fillna("") != "").sum()) != summary["snapshot"]["opening_available"]:
        problems.append("snapshot opening count mismatch")
    if int((snap["closing_source"].fillna("") != "").sum()) != summary["snapshot"]["closing_available"]:
        problems.append("snapshot closing count mismatch")

    # results counts
    if len(res) != summary["results"]["rows"]:
        problems.append(f"results rows {len(res)} != summary {summary['results']['rows']}")
    if int((res["verification"] == "verified").sum()) != summary["results"]["verified"]:
        problems.append("results verified count mismatch")
    if int((res["verification"] == "mismatch").sum()) != summary["results"]["mismatch"]:
        problems.append("results mismatch count mismatch")

    # every verified row must have a score present
    verified = res[res["verification"] == "verified"]
    if verified["official_home_score"].isna().any() or verified["official_away_score"].isna().any():
        problems.append("a verified row has no official score")
    # every mismatch must be flagged
    if (res[res["verification"] == "mismatch"]["flags"] == "").any():
        problems.append("a mismatch row is not flagged")

    # fair_vs_market arithmetic
    bad = fair[(fair["fair_line"].notna()) & (fair["market_line"].notna())]
    diff = (bad["fair_line"] - bad["market_line"]) - bad["difference"]
    if not (diff.abs() < 1e-6).all():
        problems.append("fair_vs_market difference != fair_line - market_line on some rows")

    # signal/staking ranks are a permutation
    if sorted(sig["signal_rank"].tolist()) != list(range(1, len(sig) + 1)):
        problems.append("signal ranks are not a permutation of 1..n")
    if sorted(sig["staking_rank"].tolist()) != list(range(1, len(sig) + 1)):
        problems.append("staking ranks are not a permutation of 1..n")
    # masking flag consistency: staking in better half, signal in worse half
    n = len(sig)
    for _, r in sig.iterrows():
        expected = (r["staking_rank"] <= n // 2) and (r["signal_rank"] > n // 2)
        if bool(r["lucky_staking_masking_signal"]) != expected:
            problems.append(f"{r['id']}: masking flag inconsistent with ranks")

    # demotion status follows the rule
    for _, r in dem.iterrows():
        eligible = bool(r["promotion_eligible"])
        all_pass = bool(r["demotion_all_pass"])
        expected = "live" if (eligible and all_pass) else ("demoted" if eligible else "paper")
        if r["status"] != expected:
            problems.append(f"{r['id']}: demotion status {r['status']} != expected {expected}")

    return problems


def check_sources_register() -> list[str]:
    problems: list[str] = []
    src = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
    for s in src["sources"]:
        if not s["url"].startswith(EXTERNAL_ALLOWED_PREFIXES):
            problems.append(f"sources.json: {s['id']} url not on allow-list: {s['url']}")
    return problems


def main() -> int:
    problems: list[str] = []
    for name in PAGES:
        if not (BASE / f"{name}.html").exists():
            problems.append(f"missing page: {name}.html")
            continue
        problems += check_page(name)
    problems += check_data_files()
    problems += check_numbers()
    problems += check_sources_register()

    if problems:
        print(f"FAILED with {len(problems)} problem(s):")
        for p in problems[:80]:
            print("  -", p)
        return 1
    print(f"OK: {len(PAGES)} pages, every table row has a source link, internal links resolve, "
          f"external links on the allow-list, and all published numbers recompute from the CSVs.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
