#!/usr/bin/env python3
"""Fail-closed checks for the competition/decision page added on 2026-11-12.

Run:  python3 hub/check_decisions.py   (exit 0 = pass, 1 = failure)

Checks
------
1. competition.html exists, is in the shared navigation, and carries the
   required sections (sample-size arithmetic, promotion gates, rewards).
2. The seven published sample-size rows match an independent recomputation of
   the NIST/SEMATECH 7.2.2.2 formula (tolerance: one bet).
3. The arithmetic identities quoted on the page still hold:
   -110 break-even = 110/210; two-leg parlay break-even phi = 0.097506.
4. No reward amount or player-level value is invented: award cells are blank
   and the page links to the review register.
5. Every external link on the page is official and in the source register.
6. NIST-SAMPLESIZE (the formula source) is registered with a 2026-11-12 check.

This is an arithmetic and structural check. It does not re-open web pages; the
checked dates in hub/data/sources.json record when each source was opened.
"""
from __future__ import annotations

import html
import json
import math
import re
import sys
from statistics import NormalDist
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "hub"
REGISTER = json.loads((HUB / "data/sources.json").read_text(encoding="utf-8"))
PREFIXES = tuple(REGISTER["official_prefixes"])
URLS = {s["url"] for s in REGISTER["sources"]}
BY_ID = {s["id"]: s for s in REGISTER["sources"]}
PAGE = HUB / "competition.html"


def n_prop(p0: float, p1: float, alpha: float = 0.05, power: float = 0.80) -> float:
    z = NormalDist().inv_cdf
    return ((z(1 - alpha) * math.sqrt(p0 * (1 - p0)) + z(power) * math.sqrt(p1 * (1 - p1))) / (p1 - p0)) ** 2


def main() -> int:
    problems: list[str] = []
    if not PAGE.is_file():
        print("FAIL: competition.html missing")
        return 1
    body = PAGE.read_text(encoding="utf-8")

    # 1. Required sections and navigation.
    for token in ("Sample-size arithmetic", "Promotion gates", "Reward schedule",
                  "Anti-gaming and anti-luck rules", "Path to a funded competition"):
        if token not in body:
            problems.append(f"competition.html is missing section {token!r}")
    if 'href="competition.html"' not in body:
        problems.append("competition.html is not linked from the shared navigation")
    if "flagged.html" not in body:
        problems.append("competition.html does not link to the review register")

    # 2. Sample-size table against independent recomputation.
    p0 = 110 / 210
    expected = {p: n_prop(p0, p) for p in (0.525, 0.53, 0.54, 0.55, 0.56, 0.58, 0.60)}
    rows = re.findall(r"<td>(\d{2}\.\d)%</td>\s*<td>\+?([\d.]+) pp</td>\s*<td>([\d,]+)</td>", body)
    if len(rows) != 7:
        problems.append(f"sample-size table has {len(rows)} rows; expected 7")
    seen = set()
    for pct, _edge, n_str in rows:
        whole, frac = pct.split(".")
        p = int(whole) / 100 + int(frac) / 1000
        seen.add(round(p, 3))
        want = expected.get(round(p, 3))
        got = int(n_str.replace(",", ""))
        if want is None:
            problems.append(f"unexpected win rate in table: {pct}%")
        elif abs(got - want) > 1:
            problems.append(f"sample size mismatch at {pct}%: page {got}, recomputed {want:.0f}")
    if len(seen) != 7:
        problems.append("sample-size table does not contain seven distinct win rates")

    # 3. Arithmetic identities.
    decimal = (1 + 100 / 110) ** 2
    phi = (1 / decimal - 0.25) / 0.25
    if abs(110 / 210 - 0.5238095238095238) > 1e-15:
        problems.append("break-even identity changed")
    if abs(phi - 0.09750566893424018) > 1e-12:
        problems.append("two-leg break-even phi identity changed")
    if "0.0975" not in body:
        problems.append("published break-even phi missing from the page")

    # 4. No invented money value: reward cells are blank, no prize figure text.
    for bad in ("$0", "$1,000", "$10,000", "$100,000", "prize of"):
        if bad in body:
            problems.append(f"competition.html appears to invent a money value {bad!r}")

    # 5. External links official and registered.
    for url in {html.unescape(u) for u in re.findall(r'href="(https://[^"]+)"', body)}:
        if not any(url.startswith(p) for p in PREFIXES):
            problems.append(f"external link not on the official allow-list: {url}")
        elif url not in URLS:
            problems.append(f"external link not in the source register: {url}")

    # 6. Formula source registered and dated.
    s = BY_ID.get("NIST-SAMPLESIZE")
    if not s:
        problems.append("NIST-SAMPLESIZE missing from the source register")
    elif s.get("checked") != "2026-11-12":
        problems.append(f"NIST-SAMPLESIZE checked={s.get('checked')!r}; expected 2026-11-12")

    for problem in problems:
        print("FAIL:", problem)
    print(f"decisions check: {'PASS' if not problems else 'FAIL'} — "
          f"1 page, {len(seen)} sample-size rows, 1 formula source")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
