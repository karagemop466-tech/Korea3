"""Structural and evidence checks for the verified dashboard.

This does not re-fetch external sources.  Source claims were reviewed separately
and recorded in nfl_lab/sources.json.  The checker enforces row-local official
links, local link resolution, blank-value discipline and JSON validity.
"""
from __future__ import annotations

import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from .evidence import official_publisher

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "verified"


class Checker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self.rows: list[list[str]] = []
        self.row = None
        self.in_body = False
        self.cell = None
        self.rows_no_source = 0
        self.rows_total = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "tbody":
            self.in_body = True
        if tag == "tr" and self.in_body:
            self.row = []
        if tag in {"td", "th"} and self.row is not None:
            self.cell = []
        if tag == "a":
            href = attrs.get("href", "")
            self.links.append(href)
            if self.cell is not None:
                self.cell.append(href)

    def handle_endtag(self, tag):
        if tag in {"td", "th"} and self.cell is not None:
            self.row.append(" ".join(self.cell))
            self.cell = None
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.rows_total += 1
            if not any(official_publisher(x) for x in self.row):
                self.rows_no_source += 1
            self.row = None
        if tag == "tbody":
            self.in_body = False


def main() -> int:
    pages = sorted(SITE.glob("*.html"))
    assert len(pages) == 12, f"expected 12 pages, found {len(pages)}"
    broken = []
    rows_total = 0
    rows_no_source = 0
    external_non_official = []
    for path in pages:
        text = path.read_text(encoding="utf-8")
        assert "<<<<<<<" not in text and ">>>>>>>" not in text, path
        parser = Checker()
        parser.feed(text)
        rows_total += parser.rows_total
        rows_no_source += parser.rows_no_source
        for href in parser.links:
            p = urlparse(href)
            if p.scheme in {"http", "https"}:
                if official_publisher(href) is None:
                    external_non_official.append((path.name, href))
            elif not href.startswith("#"):
                target = (path.parent / p.path).resolve()
                if not target.exists():
                    broken.append((path.name, href))
    assert rows_total > 0
    assert rows_no_source == 0, f"{rows_no_source} rows lack an official source link"
    assert not broken, broken
    assert not external_non_official, external_non_official
    for path in (SITE / "data").glob("*.json"):
        json.loads(path.read_text(encoding="utf-8"))
    status = json.loads((SITE / "data" / "status.json").read_text())
    assert status["network_fetch"] is False
    assert status["real_money_execution"] is False
    assert status["verified_empirical_values"] == 0
    assert status["eligible_strategies"] == 0
    assert status["reward_pool"] is None
    board = json.loads((SITE / "data" / "leaderboard.json").read_text())
    assert all(r["rank"] is None and r["reward"] is None for r in board)
    print(f"OK: {len(pages)} pages, {rows_total} table rows, every row has an official source link; "
          f"local links resolve; verified empirical values remain blank/zero.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
