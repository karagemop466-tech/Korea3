#!/usr/bin/env python3
"""Structural checks for the static research dashboard.

External pages are reviewed manually; this script checks markup and link shape,
not whether third-party websites remain reachable or whether they endorse claims.
"""

from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import NAV_LABELS, SOURCES  # noqa: E402


ALLOWED_HOSTS = {
    "docs.github.com",
    "nextgenstats.nfl.com",
    "operations.nfl.com",
    "sportsbook.draftkings.com",
    "support.draftkings.com",
    "support.nfl.com",
    "the-odds-api.com",
    "www.itl.nist.gov",
    "www.nfl.com",
    "www.weather.gov",
}


class AuditParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.nav_links = []
        self.rows = []
        self.row = None
        self.cell = None
        self.in_tbody = False
        self.in_nav = False
        self.in_h1 = False
        self.h1_text = ""
        self.title_text = ""
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "nav":
            self.in_nav = True
        elif tag == "tbody":
            self.in_tbody = True
        elif tag == "tr" and self.in_tbody:
            self.row = []
        elif tag == "td" and self.row is not None:
            self.cell = {"text": "", "links": []}
        elif tag == "a":
            href = attrs.get("href", "")
            self.links.append(href)
            if self.in_nav:
                self.nav_links.append((href, attrs.get("aria-current")))
            if self.cell is not None:
                self.cell["links"].append(href)
        elif tag == "h1":
            self.in_h1 = True
        elif tag == "title":
            self.in_title = True

    def handle_data(self, data):
        if self.cell is not None:
            self.cell["text"] += data
        if self.in_h1:
            self.h1_text += data
        if self.in_title:
            self.title_text += data

    def handle_endtag(self, tag):
        if tag == "td" and self.cell is not None:
            self.row.append(self.cell)
            self.cell = None
        elif tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        elif tag == "tbody":
            self.in_tbody = False
        elif tag == "nav":
            self.in_nav = False
        elif tag == "h1":
            self.in_h1 = False
        elif tag == "title":
            self.in_title = False


def audit():
    expected = {f"{slug}.html" for slug in NAV_LABELS}
    actual = {path.name for path in Path(".").glob("*.html")}
    assert actual == expected, f"Expected {sorted(expected)}, found {sorted(actual)}"

    source_urls = {source["url"] for source in SOURCES.values()}
    source_register = AuditParser()
    source_register.feed(Path("sources.html").read_text(encoding="utf-8"))
    registered_urls = {
        href
        for row in source_register.rows
        for cell in row
        for href in cell["links"]
    }
    assert registered_urls == source_urls, (
        "Source register must list every and only registered primary reference",
        registered_urls ^ source_urls,
    )

    for source_id, source in SOURCES.items():
        parsed = urlparse(source["url"])
        assert parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS, (
            source_id,
            source["url"],
        )

    row_count = 0
    for filename in sorted(expected):
        parser = AuditParser()
        parser.feed(Path(filename).read_text(encoding="utf-8"))
        assert parser.h1_text.strip(), f"Missing h1 in {filename}"
        assert parser.title_text.strip(), f"Missing title in {filename}"
        assert parser.rows, f"No table body rows in {filename}"

        expected_nav = {f"{slug}.html" for slug in NAV_LABELS}
        found_nav = {url for url, _ in parser.nav_links}
        assert found_nav == expected_nav, (filename, found_nav, expected_nav)
        assert sum(current == "page" for _, current in parser.nav_links) == 1, (
            filename,
            parser.nav_links,
        )

        for row in parser.rows:
            row_count += 1
            assert len(row) == 5, (filename, row)
            # The verified-value column must remain literally empty until the
            # project has a source-backed measurement to publish.
            assert not row[2]["text"].strip(), (filename, row)
            source_links = row[4]["links"]
            assert source_links, (filename, "table row has no source", row)
            assert row[4]["text"].strip(), (filename, "source link has no visible label", row)
            for href in source_links:
                parsed = urlparse(href)
                assert parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS, (
                    filename,
                    href,
                )
                assert href in source_urls, (filename, "unregistered source", href)

        for href in parser.links:
            parsed = urlparse(href)
            if parsed.scheme:
                assert parsed.scheme == "https" and parsed.hostname in ALLOWED_HOSTS, (
                    filename,
                    href,
                )
            elif not href.startswith("#"):
                local_path = Path(parsed.path)
                assert local_path.is_file(), (filename, "broken local link", href)

    assert Path("style.css").is_file()
    print(
        f"OK: {len(expected)} pages; {row_count} table rows; one or more registered "
        "HTTPS primary-source links per row; all verified-value cells intentionally blank; "
        "navigation and local assets resolve. External link reachability is not tested."
    )


if __name__ == "__main__":
    audit()
