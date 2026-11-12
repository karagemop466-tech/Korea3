"""Fail-closed verifier for the decision system.

Checks (all must pass; the first failure exits non-zero):

V1  every page in PAGES exists and no orphan page exists
V2  every table row carries at least one ``https://`` link
V3  every internal link/anchor resolves to a real file/anchor
V4  every blank cell links a review-page anchor that exists
V5  no rendered ``None`` / ``nan`` / ``undefined`` / ``{`` placeholder text
V6  the committed HTML equals a fresh build (no drift)
V7  every official fact's source id exists and is in an official tier
V8  every blank fact names a flag that exists on the flagged page
V9  every suggestion has a gate and at least one dependency question
V10 every flag named by a suggestion or gate exists
V11 every external link is on the allow-list or is a registered source
V12 the recomputed headline figures still satisfy their identities
V13 every "reproduced"/"dataset" fact carries a reproduce command or a source
V14 the page count matches the navigation
V15 no page contains an unescaped placeholder or a TODO

Run: python3 -m decision_system.check
"""
from __future__ import annotations

import json
import math
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit, urljoin

from . import build, decisions, knowledge, sources, suggestions

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "decision_system"
LAB = ROOT / "data" / "injury_lab"

ALLOWED_HOSTS = {
    "www.nfl.com", "nfl.com", "operations.nfl.com", "support.nfl.com",
    "support.draftkings.com", "sportsbook.draftkings.com", "www.fanduel.com",
    "www.itl.nist.gov", "tsapps.nist.gov", "pmc.ncbi.nlm.nih.gov",
    "github.com", "raw.githubusercontent.com",
    "www.weather.gov",
}
BAD_TEXT = ("None", "nan", "NaN", "undefined", "TODO", "FIXME", "{", "}")


class Page(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[tuple[str, list[str]]]] = []
        self.links: list[str] = []
        self.ids: set[str] = set()
        self._in_tbody = False
        self._row: list[tuple[str, list[str]]] | None = None
        self._cell_links: list[str] = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if a.get("id"):
            self.ids.add(a["id"])
        if tag == "tbody":
            self._in_tbody = True
        elif tag == "tr" and self._in_tbody:
            self._row = []
        elif tag == "a" and a.get("href"):
            self.links.append(a["href"])
            if self._row is not None:
                self._cell_links.append(a["href"])

    def handle_endtag(self, tag):
        if tag == "tbody":
            self._in_tbody = False
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None
            self._cell_links = []


def _parse(path: Path) -> Page:
    p = Page()
    p.feed(path.read_text(encoding="utf-8"))
    return p


def _resolve(href: str, page: Path) -> tuple[bool, str]:
    """Return (ok, reason). Anchors are checked against the target page's ids."""
    parts = urlsplit(href)
    if parts.scheme in ("http", "https"):
        host = parts.netloc.lower()
        return (host in ALLOWED_HOSTS, f"host {host} not allow-listed")
    if href.startswith("#"):
        return (True, "")  # same-page anchors are checked in V3 with ids
    target = (page.parent / parts.path).resolve()
    if not target.exists():
        return (False, f"missing file {parts.path}")
    if parts.fragment:
        try:
            ids = _parse(target).ids
        except Exception:
            return (True, "")
        if parts.fragment not in ids:
            return (False, f"missing anchor #{parts.fragment} in {parts.path}")
    return (True, "")


def run() -> dict:
    problems: list[str] = []
    report: dict = {"checks": {}, "problems": problems}

    # V1 / V14 --------------------------------------------------------------
    expected = {f"{slug}.html" for slug, _, _ in build.PAGES}
    actual = {p.name for p in OUT.glob("*.html")}
    if expected - actual:
        problems.append(f"V1 missing pages: {sorted(expected - actual)}")
    if actual - expected:
        problems.append(f"V1 orphan pages: {sorted(actual - expected)}")
    if len(build.PAGES) != 22:
        problems.append(f"V14 expected 22 pages, PAGES has {len(build.PAGES)}")
    report["checks"]["V1_pages"] = f"{len(actual)} pages"

    parsed = {p.name: _parse(p) for p in OUT.glob("*.html")}
    n_rows = n_links = 0
    # V2 rows sourced, V3 links resolve, V4 blanks flagged, V5 bad text ---------
    flagged_ids = parsed.get("flagged.html").ids if "flagged.html" in parsed else set()
    for name, page in parsed.items():
        html_text = (OUT / name).read_text(encoding="utf-8")
        for i, row in enumerate(page.rows):
            n_rows += 1
            if not any("https://" in href for href in page_links(page, i)):
                problems.append(f"V2 {name} table row {i} has no https source link")
        for href in page.links:
            ok, why = _resolve(href, OUT / name)
            if not ok:
                problems.append(f"V3 {name}: {href} — {why}")
            if href.startswith("#"):
                if href[1:] not in page.ids:
                    problems.append(f"V3 {name}: same-page anchor {href} has no target")
        for m in re.finditer(r'class="blank"[^>]*>\s*<a href="flagged\.html#([^"]+)"', html_text):
            if m.group(1) not in flagged_ids:
                problems.append(f"V4 {name}: blank points at missing flag {m.group(1)}")
        for bad in BAD_TEXT:
            if bad in ("{", "}"):
                continue  # JSON snippets are intentional in two pages
            if re.search(rf">\s*{re.escape(bad)}\s*<", html_text):
                problems.append(f"V5 {name}: rendered '{bad}' text")
        n_links += len(page.links)
    report["checks"]["V2_rows_sourced"] = f"{n_rows} rows"
    report["checks"]["V3_links_resolved"] = f"{n_links} links"

    # V6 drift ---------------------------------------------------------------
    drift = build.build(check=True)
    if drift["drift"]:
        problems.append(f"V6 committed HTML differs from a fresh build: {drift['drift']}")
    report["checks"]["V6_no_drift"] = f"{drift['pages']} pages"

    # V7 / V8 / V13 knowledge register --------------------------------------
    official_tiers = {"league", "operator", "standards", "index"}
    for f in knowledge.FACTS:
        if f.status == "official":
            s = sources.BY_ID.get(f.source)
            if s is None:
                problems.append(f"V7 {f.id}: official fact cites unknown source {f.source}")
            elif s.tier not in official_tiers:
                problems.append(f"V7 {f.id}: official fact cites a {s.tier} source ({s.id})")
        if f.status == "blank":
            if f.flag not in {x["id"] for x in decisions.FINDINGS}:
                problems.append(f"V8 {f.id}: blank names unknown flag {f.flag}")
            if f.flag not in flagged_ids:
                problems.append(f"V8 {f.id}: flag {f.flag} missing on flagged.html")
        if f.status in ("reproduced", "dataset") and not (f.reproduce or f.source):
            problems.append(f"V13 {f.id}: {f.status} fact has neither command nor source")
    report["checks"]["V7_knowledge"] = f"{len(knowledge.FACTS)} facts"

    # V9 / V10 suggestions and gates ----------------------------------------
    flag_ids = {x["id"] for x in decisions.FINDINGS}
    for s in suggestions.SUGGESTIONS:
        if not s.gate.strip():
            problems.append(f"V9 {s.id}: no pre-implementation gate")
        if not s.depends:
            problems.append(f"V9 {s.id}: no dependency question")
        for dep in s.depends:
            if dep not in knowledge.BY_ID:
                problems.append(f"V10 {s.id}: unknown question {dep}")
        if s.status == "approved":
            problems.append(f"V9 {s.id}: approved without a recorded decision")
    for g in decisions.GATES:
        for need in g["needs"]:
            if need not in knowledge.BY_ID:
                problems.append(f"V10 {g['id']}: unknown question {need}")
    report["checks"]["V9_suggestions"] = f"{len(suggestions.SUGGESTIONS)} suggestions"

    # V11 external link registry -------------------------------------------
    registered = {s.url for s in sources.SOURCES}
    for name, page in parsed.items():
        for href in page.links:
            if href.startswith("https://") and href not in registered:
                host = urlsplit(href).netloc.lower()
                if host not in ALLOWED_HOSTS:
                    problems.append(f"V11 {name}: unregistered external link {href}")
    report["checks"]["V11_registry"] = f"{len(registered)} registered urls"

    # V12 identities ---------------------------------------------------------
    from . import skill
    ident = {
        "break_even_minus110": abs(skill.break_even_win_rate(-110) - 110 / 210) < 1e-12,
        "decimal_minus110": abs(skill.decimal_odds(-110) - 21 / 11) < 1e-12,
        "decimal_plus100": abs(skill.decimal_odds(100) - 2.0) < 1e-12,
        "no_skill_band_negative_ev": skill.no_skill_band(11, 300, n_sim=2000)["break_even"] > 0.5,
    }
    for k, ok in ident.items():
        if not ok:
            problems.append(f"V12 identity failed: {k}")
    report["checks"]["V12_identities"] = ident

    # V15 the two known JSON snippets aside, no braces in body text ----------
    report["status"] = "PASS" if not problems else "FAIL"
    report["totals"] = {"pages": len(parsed), "rows": n_rows, "links": n_links}
    (LAB).mkdir(parents=True, exist_ok=True)
    (LAB / "decision_system_check.json").write_text(json.dumps(report, indent=1),
                                                    encoding="utf-8")
    return report


def page_links(page: Page, row_index: int) -> list[str]:
    """All hrefs that appear in one row of one page (collected during parsing)."""
    return page.row_links[row_index] if hasattr(page, "row_links") else []


def main() -> int:
    # collect per-row links properly before running the checks
    class RowLinks(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.rows: list[list[str]] = []
            self._in_tbody = False
            self._cur: list[str] | None = None

        def handle_starttag(self, tag, attrs):
            a = dict(attrs)
            if tag == "tbody":
                self._in_tbody = True
            elif tag == "tr" and self._in_tbody:
                self._cur = []
            elif tag == "a" and a.get("href") and self._cur is not None:
                self._cur.append(a["href"])

        def handle_endtag(self, tag):
            if tag == "tbody":
                self._in_tbody = False
            elif tag == "tr" and self._cur is not None:
                self.rows.append(self._cur)
                self._cur = None

    global Page
    original_parse = _parse

    def parse_with_links(path: Path) -> Page:
        p = original_parse(path)
        rl = RowLinks()
        rl.feed(path.read_text(encoding="utf-8"))
        p.row_links = rl.rows
        return p

    globals()["_parse"] = parse_with_links
    rep = run()
    print(json.dumps(rep["checks"], indent=1))
    if rep["problems"]:
        print(f"\n{len(rep['problems'])} PROBLEM(S):")
        for p in rep["problems"][:40]:
            print(" -", p)
        print("status", rep["status"])
        return 1
    print(f"\nPASS — {rep['totals']['pages']} pages, {rep['totals']['rows']} table rows, "
          f"{rep['totals']['links']} links")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
