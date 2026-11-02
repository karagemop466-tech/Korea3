"""Structural, row-source and blank-value checks for the verified dashboard.

This does not re-fetch external sources. Source claims are reviewed separately
and recorded in nfl_lab/sources.json. The checker enforces row-local official
source IDs/URLs, local link resolution, blank-value discipline and JSON validity.
"""
from __future__ import annotations

import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlparse

from .evidence import official_publisher

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "verified"


def _strict_json(text):
    def bad(x):
        raise ValueError(f"Non-finite JSON constant: {x}")
    return json.loads(text, parse_constant=bad)


class Checker(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[str] = []
        self.ids: set[str] = set()
        self.rows: list[dict] = []
        self.row = None
        self.in_body = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get("id"):
            self.ids.add(attrs["id"])
        if tag == "tbody":
            self.in_body = True
        if tag == "tr" and self.in_body:
            self.row = {"sources": [], "links": []}
        if tag == "a":
            href = attrs.get("href", "")
            self.links.append(href)
            if self.row is not None:
                self.row["links"].append(href)
                if attrs.get("data-source-id"):
                    self.row["sources"].append({
                        "id": attrs["data-source-id"],
                        "href": href,
                        "declared_url": attrs.get("data-source-url", ""),
                    })

    def handle_endtag(self, tag):
        if tag == "tr" and self.row is not None:
            self.rows.append(self.row)
            self.row = None
        if tag == "tbody":
            self.in_body = False


def main() -> int:
    pages = sorted(SITE.glob("*.html"))
    assert len(pages) == 12, f"expected 12 pages, found {len(pages)}"
    registry = {r["evidence_id"]: r for r in _strict_json((ROOT / "nfl_lab" / "sources.json").read_text(encoding="utf-8"))}
    broken = []
    bad_anchor = []
    rows_total = 0
    row_errors = []
    external_non_official = []
    page_reports = []
    for path in pages:
        text = path.read_text(encoding="utf-8")
        assert "<<<<<<<" not in text and ">>>>>>>" not in text, path
        parser = Checker()
        parser.feed(text)
        rows_total += len(parser.rows)
        for i, row in enumerate(parser.rows, 1):
            if len(row["sources"]) != 1:
                row_errors.append((path.name, i, "expected exactly one registry source link", row["sources"]))
                continue
            s = row["sources"][0]
            rec = registry.get(s["id"])
            if rec is None:
                row_errors.append((path.name, i, "unknown source id", s["id"]))
            elif s["href"] != rec["url"] or s["declared_url"] != rec["url"]:
                row_errors.append((path.name, i, "source URL mismatch", s))
            elif official_publisher(s["href"]) is None:
                row_errors.append((path.name, i, "non-official source", s["href"]))
        for href in parser.links:
            p = urlparse(href)
            if p.scheme in {"http", "https"}:
                if official_publisher(href) is None:
                    external_non_official.append((path.name, href))
            elif href.startswith("#"):
                if href[1:] and href[1:] not in parser.ids:
                    bad_anchor.append((path.name, href))
            else:
                target = (path.parent / p.path).resolve()
                if not target.exists():
                    broken.append((path.name, href))
                elif p.fragment:
                    # Fragment checks across pages are best-effort; local file existence is required.
                    pass
        page_reports.append({"page": path.name, "rows": len(parser.rows), "links": len(parser.links)})
    assert rows_total > 0
    assert not row_errors, row_errors[:10]
    assert not broken, broken
    assert not bad_anchor, bad_anchor
    assert not external_non_official, external_non_official
    for path in (SITE / "data").glob("*.json"):
        _strict_json(path.read_text(encoding="utf-8"))
    status = _strict_json((SITE / "data" / "status.json").read_text())
    assert status["network_fetch"] is False
    assert status["real_money_execution"] is False
    assert status["verified_empirical_values"] == 0
    assert status["eligible_strategies"] == 0
    assert status["reward_pool"] is None
    board = _strict_json((SITE / "data" / "leaderboard.json").read_text())
    assert all(r["rank"] is None and r["reward"] is None for r in board)
    unverified_sources = []
    for sid, rec in registry.items():
        if rec["review_status"] == "unverified":
            assert rec["claim"] == "", f"unverified source {sid} has a claim"
            unverified_sources.append(sid)
        else:
            assert rec["claim"], f"verified source {sid} has blank claim"
    report = {
        "pages": len(pages),
        "table_rows": rows_total,
        "row_source_errors": 0,
        "broken_local_links": 0,
        "unverified_sources": sorted(unverified_sources),
        "live_source_refetch": False,
        "page_reports": page_reports,
    }
    (SITE / "data" / "row_audit.json").write_text(json.dumps(report, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(f"OK: {len(pages)} pages, {rows_total} table rows, every row has a matching official registry source; "
          f"local links resolve; verified empirical values remain blank/zero; unverified sources: {', '.join(sorted(unverified_sources)) or 'none'}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
