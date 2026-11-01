#!/usr/bin/env python3
"""Check the isolated audit page's rows, official links, and local targets.

This is structural validation only; it cannot prove claim accuracy, source
availability, licensing, or betting skill. External sources require review.
"""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent
PAGE = ROOT / "audit" / "flagged.html"
OFFICIAL_HOSTS = {
    "www.nfl.com", "static.www.nfl.com", "support.nfl.com", "support.draftkings.com",
    "www.weather.gov", "www.itl.nist.gov", "tsapps.nist.gov", "www.cdc.gov", "docs.github.com",
}


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.rows = []
        self.row = None
        self.cell = None
        self.in_body = False
        self.h1 = ""
        self.in_h1 = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "h1":
            self.in_h1 = True
        elif tag == "tbody":
            self.in_body = True
        elif tag == "tr" and self.in_body:
            self.row = []
        elif tag == "td" and self.row is not None:
            self.cell = {"text": "", "links": []}
        if tag in {"a", "link"}:
            href = attrs.get("href", "")
            self.links.append(href)
            if self.cell is not None and tag == "a":
                self.cell["links"].append(href)
            if attrs.get("target") == "_blank":
                rel = set(attrs.get("rel", "").split())
                if not {"noopener", "noreferrer"} <= rel:
                    raise AssertionError(f"unsafe external target: {href}")

    def handle_data(self, data):
        if self.in_h1:
            self.h1 += data
        if self.cell is not None:
            self.cell["text"] += data

    def handle_endtag(self, tag):
        if tag == "h1":
            self.in_h1 = False
        elif tag == "td" and self.cell is not None:
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        elif tag == "tbody":
            self.in_body = False


def main():
    page = Page()
    page.feed(PAGE.read_text(encoding="utf-8"))
    assert page.h1.strip() == "Flagged for Review"
    assert len(page.rows) == 19, len(page.rows)
    for row in page.rows:
        assert len(row) == 5, row
        assert not row[2]["text"].strip(), ("unverified value must be blank", row)
        assert row[3]["text"].strip(), ("missing status", row)
        assert any(urlsplit(href).scheme == "https" and
                   urlsplit(href).hostname in OFFICIAL_HOSTS
                   for cell in row for href in cell["links"]), ("missing official link", row)
    for href in page.links:
        parsed = urlsplit(href)
        if parsed.scheme:
            assert parsed.scheme == "https", href
            continue
        if not parsed.path:
            continue
        target = (PAGE.parent / unquote(parsed.path)).resolve()
        assert target.is_relative_to(ROOT) and target.is_file(), (href, target)
    print("OK: 19 audit rows have official-domain links, blank unverified values, and valid local targets")
    print("Note: external availability and factual support are not proven by this check.")


if __name__ == "__main__":
    main()
