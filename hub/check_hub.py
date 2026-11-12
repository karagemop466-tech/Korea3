#!/usr/bin/env python3
"""Fail-closed verifier for the consolidated dashboard (hub/).

Run: python3 hub/check_hub.py   (exit code 0 = pass, 1 = failure)

Checks
------
1.  Every <tbody> table row has at least one link to an official publisher.
2.  Every external link is on the official publisher allow-list.
3.  Every blank/unverified marker links to flagged.html, and every anchor used
    by another page resolves to an id on the target page.
4.  Every internal link resolves to a file in this repository.
5.  Every GitHub blob/tree source link names a path that exists in the checkout.
6.  Every page has a meta description, the shared navigation and a link to the
    Flagged for Review page.
7.  No cell renders a raw None / NaN / inf.
8.  The machine-readable source register matches the links used on the pages.
9.  All 24 pages exist and are linked from the navigation (EXPECTED_PAGES).

The report is written to hub/data/verification.json. Output is deterministic.
"""
from __future__ import annotations

import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "hub"
REGISTER = json.loads((HUB / "data/sources.json").read_text(encoding="utf-8"))
OFFICIAL_PREFIXES = tuple(REGISTER["official_prefixes"])
REGISTER_URLS = {s["url"] for s in REGISTER["sources"]}
PAGES = sorted(p.name for p in HUB.glob("*.html"))
EXPECTED_PAGES = 25
REPO_BLOB = "https://github.com/karagemop466-tech/Korea3/blob/main/"
REPO_TREE = "https://github.com/karagemop466-tech/Korea3/tree/main/"


class Page(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []  # (href, class)
        self.rows: list[list[str]] = []
        self.ids: set[str] = set()
        self._in_tbody = False
        self._in_row = False
        self._row_links: list[str] = []
        self._cells: list[str] = []
        self._cell: list[str] | None = None
        self.meta_description = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("name") == "description":
            self.meta_description = True
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "tbody":
            self._in_tbody = True
        if tag == "tr" and self._in_tbody:
            self._in_row = True
            self._row_links = []
        if tag == "a" and a.get("href"):
            href = a["href"]
            self.links.append((href, a.get("class") or ""))
            if self._in_row:
                self._row_links.append(href)
        if tag in ("td", "th"):
            self._cell = []

    def handle_data(self, data):
        if self._cell is not None:
            self._cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None:
            text = "".join(self._cell).strip()
            if re.fullmatch(r"(None|nan|NaN|inf|-inf|Infinity)", text):
                self.rows.append(["__INVALID_CELL__", text])
            self._cell = None
        if tag == "tr" and self._in_row:
            self.rows.append(self._row_links)
            self._in_row = False
        if tag == "tbody":
            self._in_tbody = False


def is_official(url: str) -> bool:
    return any(url.startswith(p) for p in OFFICIAL_PREFIXES)


def check() -> int:
    problems: list[str] = []
    parsed: dict[str, Page] = {}
    stats = {"pages": len(PAGES), "table_rows": 0, "official_links": 0,
             "blank_markers": 0, "internal_links": 0, "external_links": 0,
             "repo_links": 0, "anchors": 0}

    if len(PAGES) != EXPECTED_PAGES:
        problems.append(f"expected {EXPECTED_PAGES} hub pages, found {len(PAGES)}: {PAGES}")

    for name in PAGES:
        html = (HUB / name).read_text(encoding="utf-8")
        p = Page()
        p.feed(html)
        parsed[name] = p
        if not p.meta_description:
            problems.append(f"{name}: missing meta description")
        if 'href="flagged.html"' not in html:
            problems.append(f"{name}: missing link to flagged.html")
        if 'href="../index.html"' not in html:
            problems.append(f"{name}: missing link back to the repository dashboard")
        # navigation completeness
        for other in PAGES:
            if f'href="{other}"' not in html and other != name:
                problems.append(f"{name}: navigation does not link {other}")

        for i, row in enumerate(p.rows):
            if row and row[0] == "__INVALID_CELL__":
                problems.append(f"{name}: table row renders an invalid value {row[1]!r}")
                continue
            stats["table_rows"] += 1
            official = [u for u in row if u.startswith("http") and is_official(u)]
            stats["official_links"] += len(official)
            if not official:
                problems.append(f"{name}: table row {i} has no official source link (links: {row})")

        for href, cls in p.links:
            if "flag" in cls.split():
                stats["blank_markers"] += 1
                if href != "flagged.html":
                    problems.append(f"{name}: blank marker points at {href}")
            if href.startswith("http"):
                stats["external_links"] += 1
                if not is_official(href):
                    problems.append(f"{name}: external link not on official allow-list: {href}")
                if href.startswith(REPO_BLOB):
                    stats["repo_links"] += 1
                    rel = unquote(href[len(REPO_BLOB):]).split("#")[0].split("?")[0]
                    if rel and not (ROOT / rel).is_file():
                        problems.append(f"{name}: GitHub blob link points at a missing file: {rel}")
                elif href.startswith(REPO_TREE):
                    stats["repo_links"] += 1
                    rel = unquote(href[len(REPO_TREE):]).split("#")[0].split("?")[0]
                    if rel and not (ROOT / rel).is_dir():
                        problems.append(f"{name}: GitHub tree link points at a missing directory: {rel}")
                elif href not in REGISTER_URLS:
                    problems.append(f"{name}: external link is not in the source register: {href}")
            elif href.startswith("#"):
                stats["anchors"] += 1
                if href[1:] not in p.ids:
                    problems.append(f"{name}: broken same-page anchor {href}")
            else:
                stats["internal_links"] += 1
                path, _, frag = href.partition("#")
                if not path:
                    continue
                target = (HUB / unquote(path)).resolve()
                if not target.is_file():
                    problems.append(f"{name}: broken internal link {href}")
                elif frag:
                    stats["anchors"] += 1
                    target_html = target.read_text(encoding="utf-8")
                    if f'id="{frag}"' not in target_html:
                        problems.append(f"{name}: broken anchor {href} (no id in target)")

    # Every source in the register must be used at least once (except the two
    # project/provenance entries, which are used through repo links).
    used = {href for p in parsed.values() for href, _ in p.links}
    for s in REGISTER["sources"]:
        if s["url"] not in used and s["url"] not in (REPO_TREE,):
            problems.append(f"source register entry never linked: {s['id']}")

    # The review page must exist and carry a substantial register.
    flagged = parsed.get("flagged.html")
    if not flagged:
        problems.append("flagged.html missing")
    elif len(flagged.rows) < 30:
        problems.append(f"flagged.html has only {len(flagged.rows)} rows; expected the full register")
    if "Flagged for Review" not in (HUB / "flagged.html").read_text(encoding="utf-8"):
        problems.append("flagged.html is not clearly labelled")

    report = {
        "status": "PASS" if not problems else "FAIL",
        "snapshot_utc": REGISTER["snapshot_utc"],
        "session": REGISTER["session"],
        "pages": PAGES,
        "stats": stats,
        "sources_in_register": len(REGISTER["sources"]),
        "sources_verified": sum(1 for s in REGISTER["sources"] if s["status"] == "verified"),
        "problems": problems,
    }
    (HUB / "data/verification.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    for problem in problems[:40]:
        print("FAIL:", problem)
    if len(problems) > 40:
        print(f"... and {len(problems) - 40} more")
    print(f"hub check: {report['status']} — {stats['pages']} pages, {stats['table_rows']} table rows, "
          f"{stats['official_links']} official row links, {stats['blank_markers']} blank markers, "
          f"{stats['internal_links']} internal links, {stats['external_links']} external links")
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(check())
