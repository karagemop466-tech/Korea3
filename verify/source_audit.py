#!/usr/bin/env python3
"""Per-row source provenance for every published table.

The standing requirement is that each published value can be traced to a source. This audit
makes the trace explicit and classifies it, because on this project "sourced" is not one
thing:

``official``
    The row links a page published by the NFL, a licensed operator, a standards body or a
    government. Only rules, scoring, schedule, settlement mechanics and operator terms can
    legitimately appear in this class. **No official source publishes NFL betting prices or
    the outputs of a model**, so no analytical row can ever be official.

``dataset``
    The row links the pinned open dataset (nflverse) and/or the code that computes the value
    from it. Reproducible by anyone; not an official league publication.

``internal``
    The row links only another page of this site. Acceptable for navigation and summaries,
    recorded separately so it is not mistaken for external evidence.

``none``
    The row has no link at all. This is the failure case: the value must be blanked and
    flagged, never inferred.

Usage:
    python3 verify/source_audit.py [--json]
Exit code 1 if any row has no source link.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}

OFFICIAL_HOSTS = {
    "www.nfl.com", "nfl.com", "operations.nfl.com", "support.nfl.com", "static.www.nfl.com",
    "nextgenstats.nfl.com", "www.weather.gov", "www.itl.nist.gov", "tsapps.nist.gov",
    "www.ecfr.gov", "www.leg.state.nv.us", "www.draftkings.com", "sportsbook.draftkings.com",
    "support.draftkings.com", "help.draftkings.com", "www.fanduel.com", "support.fanduel.com",
    "www.betmgm.com", "www.caesars.com",
}
SECONDARY_HOSTS = {
    "www.pro-football-reference.com": "Reputable third-party reference — NOT a league or operator publication",
    "docs.github.com": "Platform documentation",
}
DATASET_HOSTS = {"github.com", "raw.githubusercontent.com", "codeload.github.com",
                 "release-assets.githubusercontent.com",
                 # government / standards bodies are official (see OFFICIAL_HOSTS), not dataset
                 }


class RowParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict] = []
        self._in_tbody = False
        self._in_row = False
        self._links: list[str] = []
        self._cells: list[str] = []
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tbody":
            self._in_tbody = True
        elif tag == "tr" and self._in_tbody:
            self._in_row = True
            self._links, self._cells = [], []
        elif tag == "a" and a.get("href") and self._in_row:
            self._links.append(a["href"])
        elif tag in ("td", "th"):
            self._buf = []

    def handle_endtag(self, tag):
        if tag == "tbody":
            self._in_tbody = False
        elif tag in ("td", "th") and self._in_row:
            self._cells.append("".join(self._buf).strip())
        elif tag == "tr" and self._in_row:
            self.rows.append({"cells": self._cells, "links": self._links})
            self._in_row = False

    def handle_data(self, data):
        if self._in_row:
            self._buf.append(data)


def classify(links: list[str]) -> str:
    if not links:
        return "none"
    classes = set()
    for href in links:
        if href.startswith(("http://", "https://")):
            host = urlsplit(href).netloc.lower()
            if host in OFFICIAL_HOSTS:
                classes.add("official")
            elif host in DATASET_HOSTS or host in SECONDARY_HOSTS:
                classes.add("dataset")
            else:
                classes.add("dataset")  # an unclassified external host is not official
        elif href.startswith("#"):
            continue
        else:
            classes.add("internal")
    if "official" in classes:
        return "official"
    if "dataset" in classes:
        return "dataset"
    if "internal" in classes:
        return "internal"
    return "none"


def audit() -> dict:
    pages: list[dict] = []
    for path in sorted(ROOT.rglob("*.html")):
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        rel = path.relative_to(ROOT).as_posix()
        p = RowParser()
        p.feed(path.read_text(encoding="utf-8", errors="replace"))
        if not p.rows:
            continue
        counts = Counter(classify(r["links"]) for r in p.rows)
        unsourced = [
            {"row_index": i, "first_cell": (r["cells"][0][:80] if r["cells"] else ""),
             "cells": r["cells"][:3]}
            for i, r in enumerate(p.rows) if classify(r["links"]) == "none"
        ]
        pages.append({
            "page": rel,
            "section": rel.rsplit("/", 1)[0] if "/" in rel else ".",
            "rows": len(p.rows),
            "official": counts.get("official", 0),
            "dataset": counts.get("dataset", 0),
            "internal": counts.get("internal", 0),
            "none": counts.get("none", 0),
            "unsourced": unsourced,
        })
    totals = {
        "pages": len(pages),
        "rows": sum(p["rows"] for p in pages),
        "official": sum(p["official"] for p in pages),
        "dataset": sum(p["dataset"] for p in pages),
        "internal": sum(p["internal"] for p in pages),
        "none": sum(p["none"] for p in pages),
    }
    by_section: dict[str, dict] = {}
    for p in pages:
        s = by_section.setdefault(p["section"], {"rows": 0, "official": 0, "dataset": 0,
                                                 "internal": 0, "none": 0})
        for k in ("rows", "official", "dataset", "internal", "none"):
            s[k] += p[k]
    return {
        "pages": pages,
        "totals": totals,
        "by_section": by_section,
        "status": "PASS" if totals["none"] == 0 else "FAIL",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--max-unsourced", type=int, default=0,
                    help="tolerated number of unsourced rows OUTSIDE the allowed archive directories; default 0")
    ap.add_argument("--allow-dirs", default="",
                    help="comma-separated prefixes of other sessions' archives whose unsourced rows are "
                         "reported but not gated, e.g. session-398c4b58,qa")
    args = ap.parse_args()
    allowed = tuple(d.strip().strip("/") for d in args.allow_dirs.split(",") if d.strip())
    rep = audit()
    gated = [u for p_ in rep["pages"] if not (allowed and p_["page"].startswith(allowed))
             for u in p_["unsourced"]]
    rep["gated_unsourced"] = len(gated)
    rep["allowed_dirs"] = list(allowed)
    rep["unsourced_budget"] = args.max_unsourced
    rep["over_budget"] = len(gated) > args.max_unsourced
    (ROOT / "verify" / "sources.report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    ok = not rep["over_budget"]
    if args.json:
        print(json.dumps(rep, indent=2))
        return 0 if ok else 1
    t = rep["totals"]
    print(f"{t['pages']} pages with tables · {t['rows']} body rows")
    print(f"  official per-row source  {t['official']:>5}")
    print(f"  dataset/code source      {t['dataset']:>5}")
    print(f"  internal link only       {t['internal']:>5}")
    print(f"  no source link           {t['none']:>5}")
    print("\nby directory:")
    for sec, s in sorted(rep["by_section"].items(), key=lambda kv: -kv[1]["rows"]):
        print(f"  {sec:<32}{s['rows']:>6} rows  official {s['official']:>4}  "
              f"dataset {s['dataset']:>5}  internal {s['internal']:>4}  none {s['none']:>3}")
    if t["none"]:
        print("\nrows without any source link:")
        for p in rep["pages"]:
            for u in p["unsourced"][:5]:
                print(f"  {p['page']} row {u['row_index']}: {u['cells']}")
    print(f"\ngated unsourced rows {rep['gated_unsourced']} (budget {args.max_unsourced})"
          f" · reported-only in {', '.join(allowed) or 'none'}: "
          f"{rep['totals']['none'] - rep['gated_unsourced']}")
    print(f"status {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
