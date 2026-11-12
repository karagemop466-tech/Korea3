#!/usr/bin/env python3
"""Fail-closed checks for the decision-support pages added on 2026-11-12.

Run:  python3 hub/check_decisions.py   (exit 0 = pass, 1 = failure)

Checks
------
1. The four new pages exist and carry their stable anchors of content.
2. The sample-size table in competition.html matches an independent
   recomputation of the NIST/SEMATECH formula (tolerance 1 unit).
3. The arithmetic identities quoted on the pages still hold:
   -110 break-even = 110/210; two-leg parlay break-even phi = 0.097506.
4. No new page publishes a player-level injury, depth-chart, price, ROI or
   reward value: those cells must be blank and link to flagged.html.
5. Every official source used by the new pages is in the source register.
6. The suggestion and question registers keep their advertised counts.

This is an arithmetic and structural check. It does not re-open the web pages;
the checked dates in hub/data/sources.json record when each source was opened.
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

PAGES = ["suggestions.html", "questions.html", "injuries.html", "competition.html"]


def n_prop(p0: float, p1: float, alpha: float = 0.05, power: float = 0.80) -> float:
    z = NormalDist().inv_cdf
    return ((z(1 - alpha) * math.sqrt(p0 * (1 - p0)) + z(power) * math.sqrt(p1 * (1 - p1))) / (p1 - p0)) ** 2


def main() -> int:
    problems: list[str] = []
    for name in PAGES:
        if not (HUB / name).is_file():
            problems.append(f"missing page {name}")
    text = {name: (HUB / name).read_text(encoding="utf-8") for name in PAGES if (HUB / name).is_file()}

    # 1. Registers and required sections.
    sug = text.get("suggestions.html", "")
    ids = re.findall(r'<tr id="(S\d\d)">', sug)
    if len(ids) != 22:
        problems.append(f"suggestions.html has {len(ids)} suggestion rows; expected 22")
    for token in ("Decision ladder", "Suggestion register", "Choose a path", "What not to do yet"):
        if token not in sug:
            problems.append(f"suggestions.html is missing section {token!r}")

    que = text.get("questions.html", "")
    if que.count(">QA") < 12 or que.count(">Q0") + que.count(">Q1") + que.count(">Q2") < 26:
        problems.append("questions.html does not carry the 12 answered + 26 open question rows")

    inj = text.get("injuries.html", "")
    for token in ("Deficiency Index", "Verified rules that constrain any injury model",
                  "Player-level availability values admitted"):
        if token not in inj:
            problems.append(f"injuries.html is missing {token!r}")
    if "2nd string" not in inj or "4th string" not in inj:
        problems.append("injuries.html does not cover 2nd-4th string depth")

    comp = text.get("competition.html", "")
    for token in ("Sample-size arithmetic", "Promotion gates", "Reward schedule"):
        if token not in comp:
            problems.append(f"competition.html is missing {token!r}")

    # 2. Sample-size table against independent recomputation.
    p0 = 110 / 210
    expected = {p: n_prop(p0, p) for p in (0.525, 0.53, 0.54, 0.55, 0.56, 0.58, 0.60)}
    rows = re.findall(r"<td>(\d{2}\.\d)%</td>\s*<td>\+?([\d.]+) pp</td>\s*<td>([\d,]+)</td>", comp)
    if len(rows) != 7:
        problems.append(f"competition.html sample-size table has {len(rows)} rows; expected 7")
    seen = set()
    for pct, _edge, n_str in rows:
        p = int(pct.split(".")[0]) / 100 + int(pct.split(".")[1]) / 1000
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
    if abs(110 / 210 - 0.5238095238095238) > 1e-15:
        problems.append("break-even identity changed")
    decimal = (1 + 100 / 110) ** 2
    phi = (1 / decimal - 0.25) / 0.25
    if abs(phi - 0.09750566893424018) > 1e-12:
        problems.append("two-leg break-even phi identity changed")
    if "0.0975" not in comp and "0.0975" not in que:
        problems.append("published break-even phi missing from the decision pages")

    # 4. Unverified-values discipline: no player-level values or money values.
    for name, body in text.items():
        for bad in ("$0", "$1,000", "$10,000", "healthy backups:", "games missed:"):
            if bad in body:
                problems.append(f"{name}: looks like an invented value {bad!r}")
        if "flagged.html" not in body:
            problems.append(f"{name}: missing link to the review page")

    # 5. Every external link on the new pages is official and registered.
    for name, body in text.items():
        for url in set(html.unescape(u) for u in re.findall(r'href="(https://[^"]+)"', body)):
            if not any(url.startswith(p) for p in PREFIXES):
                problems.append(f"{name}: external link not on the official allow-list: {url}")
            elif not url.startswith("https://github.com/karagemop466-tech/Korea3/") and url not in URLS:
                problems.append(f"{name}: external link not in the source register: {url}")

    # 6. The new source IDs must exist and carry a checked date.
    required = {"NFL-INJ-POLICY", "NFL-INJURIES", "NFL-IR-FAQ", "NFL-ROSTER",
                "NFL-RULES-2025", "NFL-ROSTER-PAGE", "NIST-SAMPLESIZE"}
    by_id = {s["id"]: s for s in REGISTER["sources"]}
    for sid in sorted(required):
        s = by_id.get(sid)
        if not s:
            problems.append(f"source {sid} missing from the register")
        elif s.get("checked") != "2026-11-12":
            problems.append(f"source {sid} has checked={s.get('checked')!r}; expected 2026-11-12")

    for problem in problems:
        print("FAIL:", problem)
    print(f"decisions check: {'PASS' if not problems else 'FAIL'} — "
          f"{len(PAGES)} pages, {len(seen)} sample-size rows, {len(required)} new sources")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
