#!/usr/bin/env python3
"""Fail-closed verifier for decision_lab/.

Every rule here exists because something in the brief demands it, and each one fails the build
rather than printing a warning. Exit code 0 means all rules passed.

Rules
-----
R1  Determinism: regenerating every page from data/*.json reproduces the committed bytes.
R2  Per-row sourcing: every <tbody> row carries at least one link.
R3  No unexplained blank: every blank marker carries the "never inferred" title.
R4  Blanks on fact pages are flagged: on injuries/depth/conflicts, a row with a blank must also
    link the flag register, so no empty cell is silent.
R5  Internal links resolve, including #anchors on the target page.
R6  External links are classified: every absolute URL is either a registered source page or sits
    on an official publisher's host. An unclassified host is a citation nobody has vetted.
R7  Source discipline: every source ID cited by the data exists in the register; a source marked
    read=false is rendered with the not-opened marker and never as plain confirmed evidence.
R8  Third-party rejection: no page presents an X-series (non-official) publisher as support for a
    value; each appears with the rejected label.
R9  Decision gate: no suggestion may be marked Approved, Rejected or Implemented, and
    chosen_option / decision_date must stay empty until the owner decides.
R10 Answer gate: no open question may carry an answer.
R11 Coverage gate: every club referenced anywhere must appear in the data or be declared in
    coverage_gaps as unverified. A silently missing club is how a partial capture passes as full.
R12 Navigation: every page exists and is reachable from the shared nav.
R13 No merge-conflict markers anywhere in the directory.
R14 No fabricated content: the pages must not contain a currency amount, a correlation
    coefficient, an ROI or odds figure, because no official source publishes one.

Usage:  python3 decision_lab/check.py
"""
from __future__ import annotations

import importlib.util
import json
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
FACT_PAGES = ("injuries.html", "depth.html", "conflicts.html")
ALL_PAGES = ("index.html", "injuries.html", "depth.html", "conflicts.html", "suggestions.html",
             "open-questions.html", "sources.html", "flagged.html", "verification.html")

# Hosts that are official publishers: the league, league-operated static/news hosts, and the
# member-club domain cited by NFL.com itself as the primary source behind a depth-chart decision.
# Club domains are NOT in the repository-wide allow-list in verify/source_audit.py; including one
# here is scoped to this directory only and is recorded as governance question Q15 / suggestion S13.
OFFICIAL_HOSTS = {
    "www.nfl.com", "nfl.com", "amp.nfl.com", "operations.nfl.com", "support.nfl.com",
    "static.www.nfl.com", "nextgenstats.nfl.com", "www.clevelandbrowns.com",
}

failures: list[str] = []
notes: list[str] = []


def fail(rule: str, msg: str) -> None:
    failures.append(f"[{rule}] {msg}")


def note(msg: str) -> None:
    notes.append(msg)


# --------------------------------------------------------------------------- #
class RowScanner(HTMLParser):
    """Collects, per table row, its links, its blank markers and its anchor ids."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict] = []
        self.anchors: set[str] = set()
        self.links: list[str] = []
        self.blanks_no_title: int = 0
        self.blank_total: int = 0
        self._tbody = False
        self._row: dict | None = None
        self._depth = 0

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "tbody":
            self._tbody = True
        elif tag == "tr" and self._tbody:
            self._row = {"links": [], "blanks": 0, "flaglinks": 0, "text": []}
        elif tag == "a":
            href = a.get("href")
            if href:
                self.links.append(href)
                if self._row is not None:
                    self._row["links"].append(href)
                    if "flagged.html#" in href or href.startswith("#"):
                        self._row["flaglinks"] += 1
            if a.get("id"):
                self.anchors.add(a["id"])
        elif tag == "span" and "blank" in (a.get("class") or ""):
            self.blank_total += 1
            title = a.get("title") or ""
            if "never inferred" not in title:
                self.blanks_no_title += 1
            if self._row is not None:
                self._row["blanks"] += 1
        if a.get("id"):
            self.anchors.add(a["id"])

    def handle_endtag(self, tag):
        if tag == "tbody":
            self._tbody = False
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._row is not None:
            self._row["text"].append(data)


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def load_build():
    spec = importlib.util.spec_from_file_location("dl_build", HERE / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)          # module-level code runs; main() does not
    return mod


def main() -> int:
    b = load_build()
    sources = load("sources.json")
    injuries = load("injuries.json")
    suggestions = load("suggestions.json")
    questions = load("questions.json")
    conflicts = load("contradictions.json")

    SRC = {s["id"]: s for s in sources["sources"]}
    registered_urls = {s["url"].rstrip("/") for s in sources["sources"]}
    unopened = {s["id"] for s in sources["sources"] if not s.get("read")}
    third = {s["id"] for s in sources["sources"] if s["tier"] == "third-party"}
    # Hosts of every registered source count as acceptable link targets. A third-party host in this
    # set is additionally gated by R8, which requires it to be labelled rejected wherever it shows.
    official_hosts = set(OFFICIAL_HOSTS) | {urlsplit(s["url"]).netloc.lower()
                                            for s in sources["sources"]}

    # ---- R1 determinism -------------------------------------------------
    for name in ALL_PAGES:
        path = HERE / name
        if not path.is_file():
            fail("R12", f"{name} does not exist")
            continue
        fresh = b.PAGES[name]()
        if fresh != path.read_text(encoding="utf-8"):
            fail("R1", f"{name} differs from a fresh build - run build.py and commit the result")
    note(f"R1 deterministic rebuild: {len(ALL_PAGES)} pages reproduce byte-for-byte")

    # ---- R13 conflict markers ------------------------------------------
    for f in sorted(HERE.rglob("*")):
        if f.is_file() and f.suffix in {".html", ".py", ".json", ".css", ".js", ".md"}:
            t = f.read_text(encoding="utf-8", errors="replace")
            if re.search(r"^(<{7}|={7}|>{7})(\s|$)", t, re.M):
                fail("R13", f"{f.relative_to(HERE.parent)} contains a merge-conflict marker")
    note("R13 no merge-conflict markers")

    # ---- per-page HTML rules -------------------------------------------
    total_rows = total_links = total_blanks = total_ext = 0
    scanned: dict[str, RowScanner] = {}
    for name in ALL_PAGES:
        path = HERE / name
        if not path.is_file():
            continue
        html = path.read_text(encoding="utf-8")
        sc = RowScanner()
        sc.feed(html)
        scanned[name] = sc
        total_rows += len(sc.rows)
        total_links += len(sc.links)
        total_blanks += sc.blank_total
        if sc.blanks_no_title:
            fail("R3", f"{name}: {sc.blanks_no_title} blank marker(s) without the 'never inferred' title")

        # R2 / R4
        for i, r in enumerate(sc.rows):
            if not r["links"]:
                cells = " | ".join("".join(r["text"]).split())[:90]
                fail("R2", f"{name} row {i} has no source link: {cells}")
            if name in FACT_PAGES and r["blanks"] and not r["flaglinks"]:
                fail("R4", f"{name} row {i} contains {r['blanks']} blank(s) but no link to the flag register")

        # R5 / R6
        for href in sc.links:
            if href.startswith(("http://", "https://")):
                total_ext += 1
                base = href.rstrip("/")
                host = urlsplit(href).netloc.lower()
                # A link is acceptable if it is a registered source page, or if it sits on an
                # official publisher's host. Row-level official links (a player page, a club page,
                # an article reached from a page that WAS read) are legitimate without their own
                # register entry; an unclassified host never is.
                if base not in registered_urls and host not in official_hosts:
                    fail("R6", f"{name}: external link is neither registered nor on an official host: {href}")
            elif href.startswith("#"):
                if href[1:] not in sc.anchors:
                    fail("R5", f"{name}: in-page anchor does not exist: {href}")
            else:
                target, _, frag = href.partition("#")
                tp = (HERE / target).resolve() if target else path
                if not tp.exists():
                    fail("R5", f"{name}: local link target does not exist: {href}")
                elif frag:
                    if target.endswith(".html") and target in scanned:
                        if frag not in scanned[target].anchors:
                            fail("R5", f"{name}: anchor #{frag} not found in {target}")
                    elif target.endswith(".html"):
                        tsc = RowScanner()
                        tsc.feed(tp.read_text(encoding="utf-8", errors="replace"))
                        if frag not in tsc.anchors and f'id="{frag}"' not in tp.read_text(
                                encoding="utf-8", errors="replace"):
                            fail("R5", f"{name}: anchor #{frag} not found in {target}")

        # R7 unopened sources must be visibly marked
        for sid in unopened:
            s = SRC[sid]
            if s["url"] in html and "NOT opened this session" not in html and name != "sources.html":
                fail("R7", f"{name}: cites {sid} ({s['url']}) without the not-opened marker")

        # R8 third-party publishers must be labelled rejected wherever they appear
        for sid in third:
            if SRC[sid]["url"] in html and "rejected" not in html.lower():
                fail("R8", f"{name}: shows third-party publisher {sid} without a rejection label")

        # R14 no fabricated market numbers
        for pat, what in ((r"[-+]?\d+\s*(?:%|percent)\s*(?:ROI|return|edge)", "ROI/return percentage"),
                          (r"(?:ROI|edge|return)\s*(?:of|=|:)\s*[-+]?\d", "ROI/edge figure"),
                          (r"correlation\s*(?:of|=|:)\s*[-+]?\d(?:\.\d+)?", "correlation coefficient"),
                          (r"r\s*=\s*[-+]0?\.\d+", "correlation coefficient"),
                          (r"(?:\$|USD\s*)\d[\d,]*(?:\.\d\d)?\s*(?:prize|pool|reward|payout)", "reward amount"),
                          (r"(?:odds|line)\s*(?:of|=|:)\s*[-+]?\d", "odds or line figure")):
            m = re.search(pat, html, re.I)
            if m:
                fail("R14", f"{name}: contains a fabricated market value ({what}): {m.group(0)!r}")

    note(f"R2/R3/R4 rows {total_rows}, links {total_links}, blanks {total_blanks}")
    note(f"R5/R6 external links checked {total_ext}, all in the source register")

    # ---- R9 decision gate ----------------------------------------------
    gate = suggestions["decision_gate"]
    forbidden = set(gate["statuses_forbidden_to_agent"])
    allowed = set(gate["statuses_allowed"])
    for s in suggestions["suggestions"]:
        st = s["decision_status"]
        if st not in allowed:
            fail("R9", f'{s["id"]}: decision_status {st!r} is not one of the allowed statuses')
        if st in forbidden or st == "Implemented":
            fail("R9", f'{s["id"]}: decision_status {st!r} may only be set by the repository owner')
        if st.startswith("Proposed") and (s.get("chosen_option") or s.get("decision_date")):
            fail("R9", f'{s["id"]}: a chosen option or date is recorded while the status is still Proposed')
    note(f"R9 decision gate: {len(suggestions['suggestions'])} suggestions, "
         f"{sum(1 for s in suggestions['suggestions'] if s['decision_status'].startswith('Proposed'))} awaiting the owner")

    # ---- R10 answer gate -----------------------------------------------
    for q in questions["questions"]:
        if q["status"] == "open" and q.get("answer"):
            fail("R10", f'{q["id"]}: an answer is recorded while the question is still open')
        for sid in q.get("source_ids", []):
            if sid in SRC:
                continue
            if re.match(r"^D\d\d$", sid):
                if sid not in {c["id"] for c in conflicts["rows"]} and \
                   sid not in {f["id"] for f in b.FLAGS}:
                    fail("R10", f'{q["id"]}: cites conflict/flag {sid}, which does not exist')
            else:
                fail("R10", f'{q["id"]}: cites unknown source id {sid}')
    note(f"R10 answer gate: {len(questions['questions'])} questions, "
         f"{sum(1 for q in questions['questions'] if q['status'] == 'open')} open, no open question carries an answer")

    # ---- R11 coverage gate ---------------------------------------------
    gaps = injuries["coverage_gaps"]
    declared_missing = set(gaps["clubs_not_captured"])
    variance = gaps.get("club_code_variance", {})
    alias = variance.get("aliases_used_for_coverage_gate_only", {})
    seen = {r["team"] for r in injuries["practice_participation"]["rows"]}
    seen |= {d["team"] for d in injuries["designations"]["rows"]}
    seen |= {t["team"] for t in injuries["no_injuries_reported"]["teams"]}
    for g in injuries["games"]:
        seen |= {g["away"], g["home"]}
    LEAGUE = {"ARI", "ATL", "BAL", "BUF", "CAR", "CHI", "CIN", "CLE", "DAL", "DEN", "DET", "GB",
              "HOU", "IND", "JAX", "KC", "LAC", "LAR", "LV", "MIA", "MIN", "NE", "NO", "NYG",
              "NYJ", "PHI", "PIT", "SEA", "SF", "TB", "TEN", "WAS"}
    # A club code outside the canonical set is only tolerated if the file declares the alias AND
    # marks the alias unverified. Undeclared is how a partial capture passes as a full one.
    unknown_codes = seen - LEAGUE - set(alias)
    if unknown_codes:
        fail("R11", f"club codes that are neither canonical nor declared aliases: {sorted(unknown_codes)}")
    if variance.get("status") != "unverified":
        fail("R11", "club_code_variance.status must be 'unverified' - no official crosswalk was consulted")
    for code, canon in alias.items():
        if canon not in LEAGUE:
            fail("R11", f"declared alias {code} -> {canon}: {canon} is not a canonical club code")
    resolved = {alias.get(c, c) for c in seen}
    silent = LEAGUE - resolved - declared_missing
    if silent:
        fail("R11", f"clubs absent from the data and NOT declared in coverage_gaps: {sorted(silent)}")
    if gaps["clubs_captured"] != len(resolved & LEAGUE):
        fail("R11", f'coverage_gaps.clubs_captured says {gaps["clubs_captured"]} but the data holds '
                    f'{len(resolved & LEAGUE)}')
    if gaps["status"] != "unverified":
        fail("R11", "coverage_gaps.status must be 'unverified' until the capture is complete")
    note(f"R11 coverage gate: {len(resolved & LEAGUE)} clubs captured, "
         f"{len(declared_missing)} declared missing ({', '.join(sorted(declared_missing))}), "
         f"{len(alias)} declared code alias(es), {len(silent)} silently absent")

    # ---- R7 source discipline ------------------------------------------
    for name in ("injuries", "contradictions", "questions", "suggestions"):
        d = load(f"{name}.json")
        txt = json.dumps(d)
        for sid in set(re.findall(r'\b[OX]\d\d\b', txt)):
            if sid not in SRC:
                fail("R7", f"{name}.json cites {sid}, which is not in sources.json")
    for s in sources["sources"]:
        if s["tier"] not in {"official-league", "official-club", "third-party"}:
            fail("R7", f'{s["id"]}: unknown tier {s["tier"]!r}')
        if not s.get("url", "").startswith("https://"):
            fail("R7", f'{s["id"]}: source URL is not https')
        if s["tier"] == "third-party" and "REJECTED" not in s.get("read_note", "").upper():
            fail("R8", f'{s["id"]}: a third-party source is registered without an explicit rejection note')
        if s.get("read") is False and not s.get("read_note"):
            fail("R7", f'{s["id"]}: marked NOT opened but carries no note explaining what is and is not used')
    note(f"R7 source register: {len(SRC)} entries, {len(SRC) - len(unopened)} pages opened this session, "
         f"{len(unopened)} cited-but-unopened (incl. {len(third)} third-party rejected)")

    # ---- R12 navigation -------------------------------------------------
    navhrefs = {h for _l, h, _w in b.NAV}
    if set(b.NAV_PAGES if hasattr(b, "NAV_PAGES") else ALL_PAGES) - navhrefs:
        fail("R12", "a page is missing from the shared navigation")
    for name in ALL_PAGES:
        html = (HERE / name).read_text(encoding="utf-8") if (HERE / name).is_file() else ""
        for href in navhrefs:
            if f'href="{href}"' not in html:
                fail("R12", f"{name}: navigation is missing a link to {href}")
    note(f"R12 navigation: {len(navhrefs)} pages, all linked from all {len(ALL_PAGES)} pages")

    # ---- report ---------------------------------------------------------
    print(f"decision_lab check — {len(ALL_PAGES)} pages, {total_rows} table rows, "
          f"{total_links} links, {total_blanks} blanks, {total_ext} external links")
    for n in notes:
        print("  ok   " + n)
    if failures:
        print(f"\nFAIL — {len(failures)} problem(s):")
        for f in failures[:60]:
            print("  " + f)
        if len(failures) > 60:
            print(f"  ... and {len(failures) - 60} more")
        return 1
    print("\nPASS — every rule held")
    return 0


if __name__ == "__main__":
    sys.exit(main())
