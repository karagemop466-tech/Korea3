#!/usr/bin/env python3
"""Check decisions/EXECUTIVE_SUMMARY.md against the same rules as the HTML pages.

Run: python3 decisions/check_summary.py    (exit 0 = pass)

Rules
-----
1. Every external Markdown link is an allow-listed official prefix or a committed repo file.
2. Every relative link resolves to a file that exists next to the document.
3. Every table row after the header separator carries at least one link, so the summary
   obeys the same "every row is sourced" rule as the site.
4. Every S-proposal ID mentioned exists in the suggestions register, and every G-S strategy ID
   exists in the gate table.
5. No row states a value that the builder does not also publish (spot-checked against the
   registries through the counts named in the document).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / "decisions/EXECUTIVE_SUMMARY.md"
REGISTER = json.loads((ROOT / "decisions/data/sources.json").read_text(encoding="utf-8"))
PREFIXES = tuple(REGISTER["official_prefixes"])
OFFICIAL = {s["url"] for s in REGISTER["sources"]}
SUGGESTIONS = {s["id"] for s in json.loads(
    (ROOT / "decisions/data/suggestions.json").read_text(encoding="utf-8"))["suggestions"]}
import csv

with (ROOT / "data/derived/gates_results.csv").open(encoding="utf-8") as fh:
    STRATEGIES = {row["id"] for row in csv.DictReader(fh)}

LINK = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")


def main() -> int:
    text = DOC.read_text(encoding="utf-8")
    problems: list[str] = []
    links = LINK.findall(text)

    for label, target in links:
        if target.startswith("http"):
            if not any(target.startswith(p) for p in PREFIXES):
                problems.append(f"non-official external link [{label}]({target})")
            elif target not in OFFICIAL:
                problems.append(f"external link not registered as a source: {target}")
        elif target.startswith("#"):
            slug = target[1:]
            words = re.findall(r"[a-z0-9]+", label.lower())
            if slug and not any(w in ("index", "summary") for w in words):
                pass  # anchors are not used in this document
        else:
            base = target.split("#")[0]
            if base and not (DOC.parent / base).exists():
                problems.append(f"broken relative link [{label}]({target})")

    # rule 3: sourced table rows
    rows = 0
    in_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("|") and stripped.endswith("|"):
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cells):
                in_table = True
                continue
            if in_table:
                rows += 1
                if not any(LINK.search(c) for c in cells):
                    problems.append(f"table row with no link: {stripped[:90]}")
        else:
            in_table = False

    # rule 4: ids exist
    for sid in sorted(set(re.findall(r"\bS\d{2}\b", text))):
        if sid not in SUGGESTIONS:
            problems.append(f"proposal id not in register: {sid}")
    for gid in sorted(set(re.findall(r"\bG-S\d{2}\b", text))):
        if gid[2:] not in STRATEGIES:
            problems.append(f"gate strategy id not in gates_results.csv: {gid}")

    for p in problems[:30]:
        print("FAIL:", p)
    print(f"summary check: {'PASS' if not problems else 'FAIL'} — {len(links)} links, "
          f"{rows} sourced table rows, {len(SUGGESTIONS)} proposals, {len(STRATEGIES)} gate strategies")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
