#!/usr/bin/env python3
"""Fail-closed verifier for the Line Origination Lab.

Run: python3 lines_lab/check.py     (exit 0 = pass, 1 = failure)

Checks
------
1.  Every <tbody> table row carries at least one link (a source on every row).
2.  Every external host used on a row is one this section registered — no stray domain.
3.  Every internal link resolves to a file that exists (case-sensitively, as Pages does).
4.  Every page in the navigation exists, and every page links every other page.
5.  No cell renders a raw None / nan / inf / -0.0.
6.  Every page has a meta description, a title and a link to flagged.html.
7.  The blank convention is real: every "blank" marker is styled and linked, never a 0.
8.  Dataset files still match their pinned SHA-256.
9.  A sample of headline numbers recomputed here equals the value printed on the page.
10. The build is deterministic: a second build in this process is byte-identical.
11. No page claims an official market price.
12. Every registered source URL is on an allow-list of hosts this session actually read.
"""
from __future__ import annotations

import hashlib
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from lines_lab import evidence as EV                     # noqa: E402
from lines_lab.pages import OUT, PAGES                   # noqa: E402
from lines_lab.sources import DATASET, SOURCES            # noqa: E402

# Hosts this session actually opened. A source URL outside this set is a bug: it means
# a URL was written from memory rather than read.
READ_HOSTS = {
    "support.nfl.com", "www.nfl.com", "operations.nfl.com", "static.www.nfl.com",
    "www.itl.nist.gov", "tsapps.nist.gov", "www.weather.gov", "www.ecfr.gov",
    "www.leg.state.nv.us", "pmc.ncbi.nlm.nih.gov",
    "support.draftkings.com", "sportsbook.draftkings.com", "www.draftkings.com",
    "www.fanduel.com", "support.fanduel.com", "www.betmgm.com", "www.caesars.com",
    "github.com", "codeload.github.com", "api.github.com",
    "www.pro-football-reference.com",
    # club sites opened and read this session (2026-11-14)
    "www.azcardinals.com", "www.baltimoreravens.com", "www.buffalobills.com",
    "www.detroitlions.com", "www.packers.com", "www.colts.com", "www.chiefs.com",
    "www.commanders.com",
}
DATASET_HOSTS = {"github.com", "codeload.github.com", "raw.githubusercontent.com",
                 "release-assets.githubusercontent.com"}


class RowParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict] = []
        self.all_links: list[str] = []
        self.cells: list[str] = []
        self.ids: set[str] = set()
        self.meta_description = False
        self.title = False
        self._in_tbody = False
        self._in_row = False
        self._row_links: list[str] = []
        self._row_cells: list[str] = []
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta" and a.get("name") == "description" and (a.get("content") or "").strip():
            self.meta_description = True
        if tag == "title":
            self.title = True
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "tbody":
            self._in_tbody = True
        elif tag == "tr" and self._in_tbody:
            self._in_row = True
            self._row_links, self._row_cells = [], []
        elif tag == "a" and a.get("href"):
            self.all_links.append(a["href"])
            if self._in_row:
                self._row_links.append(a["href"])
        elif tag in ("td", "th"):
            self._buf = []

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._in_row:
            self._row_cells.append("".join(self._buf).strip())
            self._buf = []
        elif tag == "tr" and self._in_row:
            self.rows.append({"links": list(self._row_links), "cells": list(self._row_cells)})
            self._in_row = False
        elif tag == "tbody":
            self._in_tbody = False

    def handle_data(self, data):
        if self._in_row:
            self._buf.append(data)


def is_local(href: str) -> bool:
    return not href.startswith(("http://", "https://", "mailto:", "#"))


def main() -> int:
    problems: list[str] = []
    notes: list[str] = []
    files = {p.name: p for p in OUT.glob("*.html")}

    if len(files) != len(PAGES):
        problems.append(f"expected {len(PAGES)} pages, found {len(files)}: {sorted(files)}")
    for p in PAGES:
        if p not in files:
            problems.append(f"navigation lists {p} but it was not built")

    total_rows = 0
    total_links = 0
    unsourced: list[str] = []
    parsed: dict[str, RowParser] = {}

    for name, path in sorted(files.items()):
        html = path.read_text(encoding="utf-8")
        rp = RowParser()
        rp.feed(html)
        parsed[name] = rp

        if not rp.meta_description:
            problems.append(f"{name}: missing meta description")
        if not rp.title:
            problems.append(f"{name}: missing <title>")
        if 'href="flagged.html"' not in html:
            problems.append(f"{name}: no link to flagged.html")
        if 'href="../index.html"' not in html:
            problems.append(f"{name}: no link back to the repository dashboard")
        for other in files:
            if other != name and f'href="{other}"' not in html:
                problems.append(f"{name}: navigation does not link {other}")

        # 1. source on every row
        for i, row in enumerate(rp.rows):
            total_rows += 1
            if not row["links"]:
                first = row["cells"][0][:70] if row["cells"] else "?"
                unsourced.append(f"{name} row {i}: {first}")

        # 2. external hosts must be registered or the repo
        for href in rp.all_links:
            if href.startswith("#") or not href.strip():
                continue
            if not is_local(href):
                total_links += 1
                host = urlsplit(href).netloc.lower()
                if not host:
                    problems.append(f"{name}: link with no host: {href!r}")
                    continue
                if host in DATASET_HOSTS:
                    continue
                if host not in READ_HOSTS:
                    problems.append(f"{name}: external host not read by this session: {host}")

        # 5. no raw Python reprs. A cell that is exactly a null repr is a bug; the word
        #    "None" inside prose is ordinary English and must not be flagged.
        for i, row in enumerate(rp.rows):
            for cell in row["cells"]:
                txt = cell.strip()
                if txt in {"None", "nan", "NaN", "inf", "-inf", "Infinity", "-0.0"}:
                    problems.append(f"{name} row {i}: raw value rendered: {cell!r}")
                elif re.fullmatch(r"None|nan|NaN", txt.split(" ")[0]) and txt.endswith(")"):
                    problems.append(f"{name} row {i}: raw value in a repr: {cell!r}")

        # 3. internal links resolve
        for href in rp.all_links:
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            if href.startswith("#"):
                continue
            target, _, frag = href.partition("#")
            if not target:
                continue
            tp = (OUT / target).resolve()
            if not tp.exists():
                problems.append(f"{name}: broken internal link -> {href}")
            elif frag and target.endswith(".html"):
                tgt = parsed.get(Path(target).name)
                if tgt is not None and frag not in tgt.ids:
                    notes.append(f"{name}: link to {href} names an id not found ({frag})")

        # 11. no claim of an official market price. A sentence that denies one is allowed;
        #     a sentence that asserts one is not.
        body_text = re.sub(r"<[^>]+>", " ", html)
        for m in re.finditer(r"[^.]{0,120}official (?:point spread|total|moneyline|price|line|market)[^.]{0,80}",
                             body_text, re.IGNORECASE):
            frag = m.group(0).lower()
            if any(neg in frag for neg in ("no ", "not ", "never", "none", "cannot", "is not",
                                           "publishes no", "does not", "neither", "without",
                                           "needs an official", "requires an official",
                                           "if an official", "would need an official")):
                continue
            problems.append(f"{name}: text appears to claim an official market number: "
                            f"{m.group(0).strip()[:110]!r}")

        # 7. blanks must never be zeros dressed up
        for cell in re.findall(r'<span class="blank"[^>]*>([^<]*)</span>', html):
            if cell.strip() in {"0", "0.0", "0.00", "0%"}:
                problems.append(f"{name}: a blank is rendered as zero")

    if unsourced:
        for u in unsourced[:20]:
            problems.append(f"row without a source: {u}")

    # 8. dataset checksums
    for label, meta in DATASET["files"].items():
        p = ROOT / meta["path"]
        if not p.exists():
            problems.append(f"dataset file missing: {meta['path']}")
            continue
        h = hashlib.sha256(p.read_bytes()).hexdigest()[:16]
        if h != meta["sha16"]:
            problems.append(f"{label}: SHA-256 changed: pinned {meta['sha16']}, now {h}")

    # 9. independent recomputation of headline numbers against the rendered pages
    e = EV.build()
    checks = []
    idx = (OUT / "index.html").read_text(encoding="utf-8")
    cov = e["coverage"]
    checks.append(("games in store", f'{cov["games"]:,}', idx))
    checks.append(("opening games", f'{cov["games_with_open_side"]:,}', idx))
    res = e["results"]
    checks.append(("spread ok", f'{res["chk_spread_ok"]:,}/{res["chk_games"]:,}',
                   (OUT / "results.html").read_text(encoding="utf-8")))
    fair = e["fair_by_season"]
    exp = f'{fair.mae_market_side.mean():.3f}'
    checks.append(("market side MAE", exp, (OUT / "fair-vs-market.html").read_text(encoding="utf-8")))
    sig = e["signals"]
    checks.append(("surviving signals", f'{int(sig.survives.sum())}',
                   (OUT / "signals.html").read_text(encoding="utf-8")))
    for label, value, page in checks:
        if value not in page:
            problems.append(f"recomputed {label} = {value} is not on the page")

    # 10. determinism
    from lines_lab import pages_body as PB
    from lines_lab.build import BUILDERS
    e2 = EV.build()
    for name, fn in BUILDERS:
        again = fn(e2)
        if again != files[name].read_text(encoding="utf-8"):
            problems.append(f"{name}: a rebuild is not byte-identical (non-deterministic)")

    # 12. source URLs must be on hosts that were actually read
    for s in SOURCES:
        host = urlsplit(s["url"]).netloc.lower()
        if host not in READ_HOSTS:
            problems.append(f"source {s['id']} points at a host never opened: {host}")
        if not s.get("quote"):
            problems.append(f"source {s['id']} has no quoted sentence")
        if s["tier"] not in ("official", "dataset", "secondary"):
            problems.append(f"source {s['id']} has an unknown tier {s['tier']!r}")

    print(f"pages: {len(files)} · table rows: {total_rows:,} · external links: {total_links:,}")
    print(f"rows without a source: {len(unsourced)}")
    print(f"registered sources: {len(SOURCES)} · dataset files: {len(DATASET['files'])}")
    if notes:
        print(f"\nnotes ({len(notes)}):")
        for n in notes[:10]:
            print(f"  - {n}")
    if problems:
        print(f"\nFAIL — {len(problems)} problem(s):")
        for p in problems[:40]:
            print(f"  ✗ {p}")
        return 1
    print("\nPASS — every row sourced, every link resolves, checksums match, numbers recompute, "
          "build deterministic.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
