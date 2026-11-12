#!/usr/bin/env python3
"""Fail-closed verifier for the decisions/ section.

Run:  python3 decisions/check.py     (exit 0 = pass)

Checks
------
1.  Every <tbody> row carries at least one link, and that link is either an
    official publisher (allow-list) or a committed file that exists.
2.  Every external link starts with an allow-listed official prefix.
3.  Every internal link resolves to a file that exists, and every anchor
    resolves to an id on the target page.
4.  Every page has a meta description, the shared navigation, and a link to
    flagged.html.
5.  No cell renders a raw None / NaN / inf.
6.  Every registry source is linked from at least one page (dead entries fail).
7.  The build is deterministic: rebuilding produces byte-identical output.
8.  All expected pages exist and are linked from the navigation.

Output: a one-line summary plus, on failure, the first 40 problems.
Exit code is 0 only when there are no problems.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "decisions"
REGISTER = json.loads((OUT / "data/sources.json").read_text(encoding="utf-8"))
PREFIXES = tuple(REGISTER["official_prefixes"])
REGISTER_URLS = {s["url"] for s in REGISTER["sources"]}
REPO_BLOB = "https://github.com/karagemop466-tech/Korea3/blob/main/"
REPO_TREE = "https://github.com/karagemop466-tech/Korea3/tree/main/"

EXPECTED = ["index", "executive-summary", "suggestions", "questions", "paths", "injuries",
            "standings", "recompute", "defects", "flagged", "method"]


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.rows = []
        self.ids = set()
        self.meta = False
        self._in_tbody = False
        self._in_row = False
        self._row = []
        self._cell = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("name") == "description":
            self.meta = True
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "tbody":
            self._in_tbody = True
        if tag == "tr" and self._in_tbody:
            self._in_row, self._row = True, []
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
            if self._in_row:
                self._row.append(a["href"])
        if tag in ("td", "th"):
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            text = "".join(self._cell).strip()
            if re.fullmatch(r"(None|nan|NaN|inf|-inf|Infinity)", text):
                self.rows.append(["__INVALID__", text])
            self._cell = None
        if tag == "tr" and self._in_row:
            self.rows.append(self._row)
            self._in_row = False
        if tag == "tbody":
            self._in_tbody = False


def official(u: str) -> bool:
    return any(u.startswith(p) for p in PREFIXES)


def main() -> int:
    problems = []
    pages = sorted(p.stem for p in OUT.glob("*.html"))
    if sorted(pages) != sorted(EXPECTED):
        problems.append(f"page set mismatch: {pages} != {EXPECTED}")

    parsed = {}
    stats = dict(pages=len(pages), rows=0, rowlinks=0, external=0, internal=0, anchors=0)
    for slug in pages:
        html_text = (OUT / f"{slug}.html").read_text(encoding="utf-8")
        p = Page()
        p.feed(html_text)
        parsed[slug] = p
        if not p.meta:
            problems.append(f"{slug}: missing meta description")
        if 'href="flagged.html"' not in html_text:
            problems.append(f"{slug}: does not link flagged.html")
        if 'href="../index.html"' not in html_text:
            problems.append(f"{slug}: does not link back to the repository dashboard")
        for other in EXPECTED:
            if other != slug and f'href="{other}.html"' not in html_text and f'href="{other}.html#' not in html_text:
                problems.append(f"{slug}: navigation does not link {other}")

        for i, row in enumerate(p.rows):
            if row and row[0] == "__INVALID__":
                problems.append(f"{slug}: row {i} renders invalid value {row[1]!r}")
                continue
            stats["rows"] += 1
            if not row:
                problems.append(f"{slug}: row {i} has no links at all")
                continue
            good = 0
            for u in row:
                if u.startswith("http"):
                    if official(u):
                        good += 1
                    if u.startswith(REPO_BLOB):
                        rel = u[len(REPO_BLOB):].split("#")[0]
                        if not (ROOT / rel).is_file():
                            problems.append(f"{slug}: row {i} links a missing file {rel}")
                    elif u.startswith(REPO_TREE):
                        rel = u[len(REPO_TREE):].split("#")[0]
                        if rel and not (ROOT / rel).is_dir():
                            problems.append(f"{slug}: row {i} links a missing dir {rel}")
                elif u in ("flagged.html",) or u.endswith("#log"):
                    good += 1
            if good == 0:
                problems.append(f"{slug}: row {i} has no official or committed-file link: {row}")
            stats["rowlinks"] += good

        for u in p.links:
            if u.startswith("http"):
                stats["external"] += 1
                if not official(u):
                    problems.append(f"{slug}: external link not official: {u}")
            elif u.startswith("#"):
                stats["anchors"] += 1
                if u[1:] not in p.ids:
                    problems.append(f"{slug}: broken same-page anchor {u}")
            else:
                stats["internal"] += 1
                base, _, frag = u.partition("#")
                if not base:
                    continue
                target = (OUT / base).resolve()
                if not target.is_file():
                    problems.append(f"{slug}: broken internal link {u}")
                elif frag:
                    stats["anchors"] += 1
                    if f'id="{frag}"' not in target.read_text(encoding="utf-8"):
                        problems.append(f"{slug}: broken anchor {u}")

    used = {u for p in parsed.values() for u in p.links}
    for s in REGISTER["sources"]:
        if s["url"] not in used:
            problems.append(f"registry source never linked: {s['id']}")

    # determinism: rebuild and compare hashes
    before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob("*.html")}
    subprocess.run([sys.executable, str(OUT / "build.py")], check=True, capture_output=True)
    after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob("*.html")}
    if before != after:
        changed = [k for k in before if before.get(k) != after.get(k)]
        problems.append(f"build is not deterministic: {changed}")

    for pr in problems[:40]:
        print("FAIL:", pr)
    if len(problems) > 40:
        print(f"... and {len(problems) - 40} more")
    print(f"decisions check: {'PASS' if not problems else 'FAIL'} — {stats['pages']} pages, "
          f"{stats['rows']} table rows, {stats['rowlinks']} row source links, "
          f"{stats['internal']} internal links, {stats['anchors']} anchors, "
          f"{stats['external']} external links, {len(REGISTER['sources'])} registry sources")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
