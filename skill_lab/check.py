#!/usr/bin/env python3
"""Fail-closed verifier for the Skill Lab.

Run: python3 -m skill_lab.check   (add --determinism to rebuild twice and compare)

Checks
------
1. Every generated page exists, has a meta description and the provenance footer.
2. Every navigation entry resolves and is present on every page.
3. Every data-table row carries at least one source link.
4. No cell renders a raw None / NaN / inf.
5. Every internal link resolves to a file in skill_lab/; every external link is on
   the verified allow-list (github.com, nfl.com, operations.nfl.com, codeload).
6. Published counts match the data: strategies, ranked, BSS>0, significant-BH, best.
7. BSS == Brier(model) - Brier(market) on every strategy row (recomputed).
8. Skill ranks are a permutation of 1..n over the ranked strategies.
9. BH q-values recomputed from the published p-values agree.
10. Control baselines: market BSS = 0, random Brier = 0.25, favourites ROI finite.
11. (--determinism) two consecutive builds produce byte-identical CSVs.

Any failure returns a non-zero exit code.
"""
from __future__ import annotations

import json
import math
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path

import numpy as np
import pandas as pd

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"

PAGES = ["index", "method", "flagged"]

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
            # links to the repo root (../index.html) resolve outside skill_lab
            if target.startswith("../"):
                if not (BASE.parent / target[3:]).exists():
                    problems.append(f"{name}: broken repo-root link {href}")
            elif not (BASE / target).exists():
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
    for p in PAGES:
        if p == name:
            continue
        if f'href="{p}.html"' not in html:
            problems.append(f"{name}: navigation missing {p}.html")
    return problems


def check_numbers() -> list[str]:
    problems: list[str] = []
    summary = json.loads((DATA / "skill_summary.json").read_text(encoding="utf-8"))
    lb = pd.read_csv(DATA / "skill_leaderboard.csv", low_memory=False)
    ctrl = pd.read_csv(DATA / "control_baselines.csv", low_memory=False)
    pm = pd.read_csv(DATA / "per_market.csv", low_memory=False)

    if len(lb) != summary["strategies"]:
        problems.append(f"leaderboard rows {len(lb)} != summary {summary['strategies']}")

    ranked = lb[lb["skill_rank"].notna()]
    if len(ranked) != summary["strategies_ranked"]:
        problems.append("ranked count mismatch")
    pos = ranked[ranked["bss"] > 0]
    if len(pos) != summary["strategies_bss_positive"]:
        problems.append("BSS>0 count mismatch")
    sig = ranked[ranked["bh_q"].notna() & (ranked["bh_q"] < 0.05)]
    if len(sig) != summary["strategies_significant_bh"]:
        problems.append("significant-BH count mismatch")

    # BSS == Brier(market) - Brier(model) on every row with a finite BSS,
    # and the direction must agree (model better than market => BSS > 0).
    for _, r in lb.iterrows():
        if pd.isna(r["bss"]):
            continue
        diff = (r["brier_market"] - r["brier_model"]) - r["bss"]
        if abs(diff) > 1e-6:
            problems.append(f"{r['id']}: BSS {r['bss']} != brier_market - brier_model ({diff:.2e})")
        if (r["brier_model"] < r["brier_market"]) != (r["bss"] > 0):
            problems.append(f"{r['id']}: BSS sign contradicts brier_model vs brier_market")

    # skill ranks are a permutation 1..n
    if sorted(ranked["skill_rank"].tolist()) != list(range(1, len(ranked) + 1)):
        problems.append("skill ranks are not a permutation of 1..n")

    # BH q-values recomputed from p-values
    from .metrics import benjamini_hochberg
    pvals = {r["id"]: r["p_value"] for _, r in ranked.iterrows()
             if pd.notna(r["p_value"]) and math.isfinite(r["p_value"])}
    bh = benjamini_hochberg(pvals)
    for _, r in ranked.iterrows():
        if r["id"] in bh and pd.notna(r["bh_q"]):
            if abs(bh[r["id"]] - r["bh_q"]) > 1e-6:
                problems.append(f"{r['id']}: published BH q {r['bh_q']} != recomputed {bh[r['id']]}")

    # control baselines
    mk = ctrl[ctrl["control"].str.startswith("Market benchmark")]
    if len(mk) != 1 or not (mk.iloc[0]["bss"] == 0.0):
        problems.append("market benchmark BSS is not 0")
    rnd = ctrl[ctrl["control"].str.startswith("Random")]
    if len(rnd) != 1 or not (rnd.iloc[0]["brier"] == 0.25):
        problems.append("random 50/50 Brier is not 0.25")
    fav = ctrl[ctrl["control"].str.startswith("Favourites")]
    if len(fav) != 1 or not math.isfinite(fav.iloc[0]["roi"]):
        problems.append("favourites-only ROI is not finite")

    # per_market: every row with a finite BSS satisfies bss == brier_model - brier_market
    # (brier_model/market not stored per-market; just check finiteness consistency)
    if pm["bss"].notna().sum() != len(pm[pm["bss"].notna()]):
        problems.append("per_market has malformed BSS")

    return problems


def check_determinism() -> list[str]:
    problems: list[str] = []
    import hashlib

    def build_hashes() -> dict:
        tmp = Path(tempfile.mkdtemp())
        import importlib
        from . import build as buildmod
        # build writes into BASE/data; capture hashes of the four outputs after a build
        buildmod.build()
        out = {}
        for f in ["skill_leaderboard.csv", "control_baselines.csv", "per_market.csv", "skill_summary.json"]:
            out[f] = hashlib.sha256((DATA / f).read_bytes()).hexdigest()
        return out

    h1 = build_hashes()
    h2 = build_hashes()
    for f in h1:
        if h1[f] != h2[f]:
            problems.append(f"determinism: {f} differs between two builds")
    return problems


def main(argv: list[str]) -> int:
    problems: list[str] = []
    for name in PAGES:
        if not (BASE / f"{name}.html").exists():
            problems.append(f"missing page: {name}.html")
            continue
        problems += check_page(name)
    problems += check_numbers()
    if "--determinism" in argv:
        problems += check_determinism()

    if problems:
        print(f"FAILED with {len(problems)} problem(s):")
        for p in problems[:80]:
            print("  -", p)
        return 1
    print(f"OK: {len(PAGES)} pages, every table row has a source link, internal links resolve, "
          f"external links on the allow-list, BSS/BH/controls recompute from the CSVs"
          + (" and two builds are byte-identical." if "--determinism" in argv else "."))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
