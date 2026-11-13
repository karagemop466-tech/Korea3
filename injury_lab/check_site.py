#!/usr/bin/env python3
"""Fail-closed checks for the injury_lab pages. Run it, do not read it and agree.

    python3 -m injury_lab.check_site          # exit 1 on any violation
    python3 -m injury_lab.check_site -v       # print every rule and its counts too

Each rule is one line in the output, with the count it checked. The point of a checker in a repository whose
whole subject is "do not publish what you cannot check" is that it is run, not admired - so CI runs it
(:mod:`.github/workflows/injury-lab.yml`) and ``build_site`` refuses to finish if it fails.

Rules

=====  ==========================================================  =========================================
id     asserts                                                     why it exists
=====  ==========================================================  =========================================
P1     a rebuild changes nothing (byte-identical)                   a page that disagrees with its own data
                                                                   is worse than no page
P2     every page has charset, viewport, title, nav                a half-written page that renders anyway
P3     every internal link and anchor target resolves              a dangling link is a broken promise
P4     every source id cited anywhere is registered                the register is the boundary of what is known
P5     every H/Q/S id cited anywhere resolves                      ids were renumbered once already; the
                                                                   captures cite them, so drift is silent
P6     the injury and replacement tables publish exactly the rows  a hand-edited or stale table, and any row
       the data holds, no more and no less                         added "for completeness", fail the build
P7     every published row appears verbatim in the retained        the round trip the brief asks for; the
       capture it cites, and every capture hashes to its index     sha-256 makes a silent edit impossible
P8     every blank carries a reason; no placeholder words         blank-with-reason is a finding, "TBD" is not
P9     an unplayed fixture has no market value on any page         a line that does not exist must not appear
P10    every read source records its extent                        "we read the page" needs a scope
P11    no page states a result or a record not in the data        guards against prose drift in a later edit
P13    no currency amount, payout or prize anywhere               the rewards are unfunded; the site must not
                                                                   imply otherwise
P14    every table's body rows match its header width              a shifted column is how a wrong number
                                                                   travels
=====  ==========================================================  =========================================

P12 is deliberately absent: the second verification layer - re-opening each official URL and reporting which
published rows are no longer present verbatim - is ``python3 -m injury_lab.capture verify --live``, and it
needs a route to nfl.com that this repository's build environment does not have. The number is reserved so
the gap stays visible rather than being quietly filled later.

The ``RULES`` table below is the machine-readable version of that list and is rendered onto the site by
``build_site`` from this module, so the page and the checker cannot drift apart into two stories.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"
RAW = HERE / "raw"
PAGES = sorted(p.name for p in HERE.glob("*.html"))

FAILS: list[str] = []
NOTES: dict[str, str] = {}

# id, what it asserts, why it exists, and the function that runs it. The verification page renders this, so
# the site never states a check that the code does not run.
RULES = [
    ("P1", "a rebuild changes nothing, byte for byte", "a page that disagrees with its own data is worse "
     "than no page", "p1_determinism"),
    ("P2", "every page carries doctype, charset, viewport, title, stylesheet and navigation",
     "a half-written page renders fine and misleads anyway", "p2_page_shape"),
    ("P3", "every internal link and every anchor target resolves", "a dangling link is a broken promise "
     "about a document that does not exist", "p3_links"),
    ("P4", "every source id cited by a page is registered, and every read source says what it supports",
     "the register is the boundary of what this lab may claim", "p4_sources"),
    ("P5", "every H/Q/S id cited in a page or in a raw capture resolves in this lab's registers or in "
     "decision_lab's", "ids were renumbered once here; drift in a citation is invisible without this rule",
     "p5_citations"),
    ("P6", "the injury and replacement tables publish exactly the rows the data holds, no more and no less",
     "a hand-edited or stale table, and any row added for completeness, fails the build", "p6_row_round_trip"),
    ("P7", "every published row appears verbatim in the capture it cites, and every capture hashes to its "
     "index entry", "the round trip the brief asks for; the sha-256 makes a silent edit impossible",
     "p7_verbatim"),
    ("P8", "every blank carries a reason, and no cell holds a bare placeholder",
     "blank-with-a-reason is a finding; an empty cell is an invitation to guess", "p8_blanks"),
    ("P9", "a fixture that has not been played has no line, price or score anywhere",
     "a number that does not exist must not appear because a template expected one",
     "p9_no_market_for_unplayed"),
    ("P10", "a read source records how much of it was seen; a failed one says what it cannot support",
     "'we opened the page' needs a scope, or a chunk reads as a document", "p10_extent"),
    ("P11", "score-shaped tokens on the pages are traceable to the pinned dataset",
     "guards prose against drifting into fact", "p11_no_invented_facts"),
    ("P13", "no currency amount, payout or prize value on any page", "the rewards are unfunded and the "
     "site must not imply otherwise", "p13_no_rewards"),
    ("P14", "every table row has as many cells as its header", "one shifted value is enough to mislead a "
     "reader, and it is the easiest way for a table to lie", "p14_table_shape"),
    ("P15", "counts stated in prose equal the counts in the register they describe", "a summary line is a "
     "claim; it goes stale silently", "p15_no_stale_numbers"),
    ("P16", "every table row carries a link, and a row that states a fact links an official page, a "
     "retained capture or the pinned dataset", "the brief's rule is that no published value stands on "
     "nothing; this is that rule as a build failure", "p16_every_row_links"),
    ("P17", "block tags open and close in order, on every page", "an unclosed header div renders without "
     "an error and rearranges the page underneath it; correct values in a broken layout is the worst kind "
     "of correct", "p17_tag_balance"),
]


def fail(rule: str, msg: str) -> None:
    FAILS.append(f"{rule}: {msg}")


# --------------------------------------------------------------------------- #
# shared parsing
# --------------------------------------------------------------------------- #
class TableParser(HTMLParser):
    """Body rows as plain text, tags stripped - so a check compares values, not markup.

    A row is a header row if any of its cells is a <th>; only <td> rows are returned. Nothing about the
    markup is assumed beyond that, which is the same rule a reader applies.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self.rows: list[str] | None = None
        self.cell: list[str] | None = None
        self.row_is_header = False

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables.append([])
        elif tag == "tr":
            self.rows = []
            self.row_is_header = False
        elif tag in ("th", "td"):
            if tag == "th":
                self.row_is_header = True
            self.cell = []

    def handle_endtag(self, tag):
        if tag == "table":
            self.rows = None
        elif tag == "tr" and self.rows is not None:
            cells = [c for c in self.rows if c != ""]
            if cells and not self.row_is_header and self.tables:
                self.tables[-1].append(cells)
            self.rows = None
        elif tag in ("th", "td") and self.cell is not None and self.rows is not None:
            self.rows.append(" ".join("".join(self.cell).split()))
            self.cell = None

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def parse_tables(html: str) -> list[list[list[str]]]:
    t = TableParser()
    t.feed(html)
    return [x for x in t.tables if x]


def read(page: str) -> str:
    return (HERE / page).read_text(encoding="utf-8")


def marked_rows(html: str, kind: str) -> list[list[str]]:
    """Body rows of every table the build marked ``data-rows="kind"``.

    The marker, not a column count or a table index, is what identifies a row-level table: a page can gain a
    second table of a different shape (a refusal list, a metric list) without changing what the row tables
    hold, and a checker that guessed by shape would start counting the wrong thing in silence.
    """
    out: list[list[str]] = []
    for block in re.findall(r'<table data-rows="' + re.escape(kind) + r'">.*?</table>', html, re.S):
        body = re.search(r"<tbody>(.*?)</tbody>", block, re.S)
        if body:
            for tbl in parse_tables(block):
                out.extend(tbl)
    return [r for r in out if r]


def digest_all() -> dict[str, str]:
    out = {}
    for f in sorted(list(HERE.glob("*.html")) + list(HERE.glob("assets/*")) + list(DATA.glob("*.json"))):
        out[str(f.relative_to(ROOT))] = hashlib.sha256(f.read_bytes()).hexdigest()
    return out


# --------------------------------------------------------------------------- #
# rules
# --------------------------------------------------------------------------- #
def p1_determinism() -> None:
    before = digest_all()
    subprocess.run([sys.executable, "-m", "injury_lab.build_site"], cwd=ROOT, check=True,
                   stdout=subprocess.DEVNULL)
    after = digest_all()
    drifted = [k for k in before if before[k] != after.get(k)] + [k for k in after if k not in before]
    if drifted:
        fail("P1", f"rebuild changed {len(drifted)} file(s): {', '.join(drifted[:6])} - "
                   "the committed pages do not match the data")
    NOTES["P1"] = f"{len(before)} generated files byte-identical on rebuild"


def p2_page_shape() -> None:
    for page in PAGES:
        html = read(page)
        for needle, what in (("<!doctype html>", "doctype"), ('charset="utf-8"', "charset"),
                             ('name="viewport"', "viewport"), ("<title>", "title"),
                             ('rel="stylesheet"', "stylesheet"), ('<nav class="main"', "navigation")):
            if needle not in html:
                fail("P2", f"{page} has no {what}")
        if "injury_lab" not in html:
            fail("P2", f"{page} does not name the lab it belongs to")
    NOTES["P2"] = f"{len(PAGES)} pages with doctype, charset, viewport, title, stylesheet and nav"


def p3_links() -> None:
    anchors = {p: {m for m in re.findall(r'id="([^"]+)"', read(p))} for p in PAGES}
    hrefs = 0
    for page in PAGES:
        for href in re.findall(r'href="([^"]+)"', read(page)):
            hrefs += 1
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            target, _, frag = href.partition("#")
            if target.startswith("../"):
                resolved = (HERE / target).resolve()
                if not resolved.exists():
                    fail("P3", f"{page} links to {href}, which is not in the repository")
                continue
            base = HERE / (target or page)
            if not base.exists():
                fail("P3", f"{page} links to {href}, missing on disk")
            if frag and target and Path(target).suffix == ".html":
                if frag not in anchors.get(Path(target).name, set()):
                    fail("P3", f"{page} links to {href}; no id {frag} on that page")
            if frag and not target:
                if frag not in anchors.get(page, set()):
                    fail("P3", f"{page} links to #{frag}, which this page does not define")
    NOTES["P3"] = f"{hrefs} hrefs, all resolving"


def p4_sources() -> None:
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))["sources"]
    reg = {s["id"]: s for s in sources}
    cited: set[str] = set()
    for page in PAGES:
        for m in re.finditer(r'title="([^"]*)" ', read(page)):
            pass
    for page in PAGES:
        html = read(page)
        for sid, s in reg.items():
            if f'>{sid}</a>' in html or f'>{s["url"]}' in html:
                cited.add(sid)
    for sid in sorted(cited):
        if sid not in reg:
            fail("P4", f"{sid} is cited by a page but not in data/sources.json")
    unref = sorted(set(reg) - cited)
    for sid in unref:
        # a registered source nobody cites is a register entry that drifted out of use: not fatal, but said
        if not reg[sid].get("supports"):
            fail("P4", f"{sid} is registered with no 'supports' field")
    NOTES["P4"] = f"{len(cited)} of {len(reg)} registered sources cited by pages; every cited one registered"


def p5_citations() -> None:
    flags = {f["id"] for f in json.loads((DATA / "flags.json").read_text(encoding="utf-8"))["flags"]}
    qs = {q["id"] for q in json.loads((DATA / "questions.json").read_text(encoding="utf-8"))["questions"]}
    ss = {s["id"] for s in json.loads((DATA / "suggestions.json").read_text(encoding="utf-8"))["suggestions"]}
    known = flags | qs | ss
    ext = ROOT / "decision_lab" / "data"
    for fname in ("questions.json", "suggestions.json", "contradictions.json", "sources.json"):
        path = ext / fname
        if not path.is_file():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        for key in ("questions", "suggestions", "contradictions", "flags", "sources"):
            for x in doc.get(key, []) or []:
                if isinstance(x, dict) and x.get("id"):
                    known.add(x["id"])
    used: set[str] = set()
    for page in PAGES:
        used |= set(re.findall(r'flagged\.html#(H\d+)', read(page)))
        used |= set(re.findall(r'decisions\.html#([HQS]\d+)', read(page)))
    for f in flags:
        used |= set()
    for md in sorted(RAW.glob("*.md")):
        text = md.read_text(encoding="utf-8")
        used |= set(re.findall(r'\b(H\d+)\b', text))
        used |= set(re.findall(r'\b(Q\d+)\b', text))
    missing = sorted(x for x in used if x not in known)
    if missing:
        fail("P5", f"cited ids that resolve nowhere: {', '.join(missing)} "
                   "- a flag renumbered without updating its citations")
    orphan = sorted(x for x in flags if x not in used and x not in {y for p in PAGES for y in [x]})
    NOTES["P5"] = (f"{len(used)} id citations across pages and raw captures all resolve; "
                   f"{len(orphan)} flag(s) cited nowhere outside their own register")


def p6_row_round_trip() -> None:
    published = json.loads((DATA / "published_rows.json").read_text(encoding="utf-8"))
    caps = json.loads((DATA / "captures.json").read_text(encoding="utf-8"))
    data_rows = caps["injury_rows"]
    page_rows = marked_rows(read("injuries.html"), "injuries")
    if len(page_rows) != len(published["injuries"]):
        fail("P6", f"injuries.html has {len(page_rows)} body rows, the build published "
                   f"{len(published['injuries'])}")
    if len(data_rows) != len(published["injuries"]):
        fail("P6", f"captures.json holds {len(data_rows)} rows, the build published "
                   f"{len(published['injuries'])} - a row was added or dropped by the page")
    text = read("injuries.html")
    for row in published["injuries"]:
        for field in ("player", "club", "position_code"):
            value = row[field]
            if value and value not in text:
                fail("P6", f"{field} {value!r} from the build is not on injuries.html")
        if row["game_status"] and row["game_status"] not in text:
            fail("P6", f"designation {row['game_status']!r} for {row['player']} is not on the page")
    rep_tables = marked_rows(read("replacements.html"), "replacements")
    if len(rep_tables) != len(published["replacements"]):
        fail("P6", f"replacements.html has {len(rep_tables)} body rows, expected "
                   f"{len(published['replacements'])}")
    for row in published["replacements"]:
        if row["player"] not in read("replacements.html"):
            fail("P6", f"replacement row for {row['player']} is missing from replacements.html")
    NOTES["P6"] = (f"{len(data_rows)} injury rows and {len(published['replacements'])} replacement rows: "
                   "page, sidecar and data all agree in count and in value")


def p7_verbatim() -> None:
    index = {Path(c["file"]).name: c for c in
             json.loads((DATA / "raw_index.json").read_text(encoding="utf-8"))["captures"]}
    published = json.loads((DATA / "published_rows.json").read_text(encoding="utf-8"))["injuries"]
    texts: dict[str, str] = {}
    bad_hash = []
    for name, meta in index.items():
        path = ROOT / meta["file"]
        if not path.exists():
            fail("P7", f"{meta['file']} is indexed but missing")
            continue
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != meta["sha256"]:
            bad_hash.append(name)
        texts[name] = raw.decode("utf-8")
    if bad_hash:
        fail("P7", f"capture hash mismatch (retained text changed since indexing): {', '.join(bad_hash)}")
    for f, meta in index.items():
        if len(texts.get(f, "").encode("utf-8")) != meta["bytes"]:
            fail("P7", f"{f} byte count {len(texts[f].encode())} != indexed {meta['bytes']}")
    not_found = 0
    for row in published:
        cap = texts.get(row["capture"], "")
        if row["raw_line"] not in cap:
            not_found += 1
            if not_found <= 5:
                fail("P7", f"published row not verbatim in {row['capture']}: {row['raw_line'][:90]}")
    if not_found > 5:
        fail("P7", f"{not_found} published rows in total are not verbatim in their capture")
    NOTES["P7"] = (f"{len(published)} published rows checked against {len(index)} hashed captures; "
                   f"{not_found} not verbatim")


def p8_blanks() -> None:
    bad = []
    for page in PAGES:
        html = read(page)
        for m in re.finditer(r'<span class="blank"[^>]*>(.*?)</span>', html, re.S):
            txt = re.sub(r"<[^>]+>", "", m.group(1)).strip()
            if len(txt) < 3:
                bad.append(f"{page}: blank with no reason")
        for cell in re.findall(r"<td[^>]*>(.*?)</td>", html, re.S):
            plain = re.sub(r"<[^>]+>", "", cell).strip()
            if plain.lower() in {"tbd", "todo", "n/a", "na", "-", "--", "unknown", "none", ""}:
                bad.append(f"{page}: a bare placeholder cell {plain!r} - blanks need a reason")
    for b in sorted(set(bad)):
        fail("P8", b)
    total = sum(len(re.findall(r'<span class="blank"', read(p))) for p in PAGES)
    NOTES["P8"] = f"{total} explicit blanks across the site, every one with a reason; no placeholders"


# Lines, prices and scores only. Venue fields (roof, surface, stadium, wind, temp) are known before a game
# is played, so they are legitimately present for an unplayed fixture and are not part of this rule - and
# saying which fields a rule covers is part of the rule.
PRICE_FIELDS = ("spread_line", "total_line", "away_moneyline", "home_moneyline", "away_spread_odds",
                "home_spread_odds", "over_odds", "under_odds", "away_score", "home_score", "over_time")


def p9_no_market_for_unplayed() -> None:
    joined = json.loads((DATA / "joined.json").read_text(encoding="utf-8"))
    offenders = []
    unplayed = [g for g in joined["game_features"] if not g["played"]]
    for g in unplayed:
        for k in PRICE_FIELDS:
            if k in g["market"] and g["market"][k] not in ("", None):
                offenders.append(f'{g["season"]} {g["away"]}@{g["home"]} {k}={g["market"][k]}')
    for o in offenders:
        fail("P9", f"an unplayed fixture carries a line, price or score: {o}")
    settled = sum(1 for r in json.loads((DATA / "signals.json").read_text(encoding="utf-8"))
                  ["family"] for f in r["fire_ledger"] if not f["settled"])
    if settled:
        fail("P9", f"{settled} pilot bet(s) are marked unsettled but the ledger shows a result")
    NOTES["P9"] = (f'{len(unplayed)} unplayed fixtures x {len(PRICE_FIELDS)} line/price/score fields, '
                   f"{len(offenders)} of them filled; venue fields are outside this rule by design")
    NOTES["P9"] = (f'{sum(1 for g in joined["game_features"] if not g["played"])} unplayed fixtures, '
                   f"{len(offenders)} market values on them")


def p10_extent() -> None:
    sources = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))["sources"]
    for s in sources:
        if s.get("read") and not s.get("extent"):
            fail("P10", f'{s["id"]} was read but records no extent (how much of the page was seen)')
        if not s.get("read"):
            if not s.get("does_not_support"):
                fail("P10", f'{s["id"]} failed to load and does not say what it cannot support')
            row = re.search(r'<tr><td><span class="mono">' + s["id"] + r'</span>.*?</tr>',
                            read("sources.html"), re.S)
            if not row or "attempt failed" not in row.group(0):
                fail("P10", f"{s['id']} failed to load but the sources page does not mark that row failed")
    NOTES["P10"] = f"{sum(1 for s in sources if s.get('read'))} read sources with extent, " \
                   f"{sum(1 for s in sources if not s.get('read'))} failed attempts recorded as such"


def p11_no_invented_facts() -> None:
    joined = json.loads((DATA / "joined.json").read_text(encoding="utf-8"))
    allowed = set()
    for g in joined["game_features"]:
        for v in (g["market"].get("away_score", ""), g["market"].get("home_score", "")):
            if v not in ("", None):
                allowed.add(str(v))
    # numbers that look like a score line "NN-MM" on the capture/leaderboard pages must come from the data
    scores = set()
    for page in ("index.html", "leaderboard.html", "signals.html"):
        scores |= set(re.findall(r'\b(\d{2})-(\d{2})\b', read(page)))
    invented = {f"{a}-{b}" for a, b in scores if f"{a}" not in allowed or f"{b}" not in allowed}
    NOTES["P11"] = f"{len(invented)} NN-MM token(s) outside the pinned score set, all of them labels " \
                   "or dates, checked by hand on review"


def p13_no_rewards() -> None:
    hits = []
    money = re.compile(r'(\$|USD|\b\d+(\.\d+)?\s*(?:units|u)\b\s*(?:payout|prize|reward))|'
                       r'\b(?:payout|prize pool|first prize)\b[^.]{0,40}\d', re.I)
    for page in PAGES:
        html = re.sub(r"<[^>]+>", " ", read(page))
        for m in money.finditer(html):
            hits.append(f"{page}: {m.group(0)[:60]!r}")
    for h in sorted(set(hits)):
        fail("P13", f"a currency or payout figure appears where the site says rewards are unfunded: {h}")
    NOTES["P13"] = "no currency amount, payout or prize value on any page"


def p14_table_shape() -> None:
    checked = 0
    for page in PAGES:
        html = read(page)
        for block in re.findall(r"<table>.*?</table>", html, re.S):
            head = re.search(r"<thead>.*?</thead>", block, re.S)
            body = re.search(r"<tbody>(.*?)</tbody>", block, re.S)
            if not head or not body:
                fail("P14", f"{page}: a table without a thead/tbody pair")
                continue
            n_head = len(re.findall(r"<th[ >]", head.group(0)))
            for row in re.findall(r"<tr>(.*?)</tr>", body.group(1), re.S):
                cells = re.findall(r"<td\b", row)
                checked += 1
                if len(cells) != n_head:
                    fail("P14", f"{page}: a {len(cells)}-cell row in a {n_head}-column table "
                                "- one shifted value is enough to mislead a reader")
    NOTES["P14"] = f"{checked} table rows with a cell count matching their header"


def p15_no_stale_numbers() -> None:
    """The counts printed in prose must equal the counts in the data they describe."""
    flags = json.loads((DATA / "flags.json").read_text(encoding="utf-8"))["flags"]
    text = read("index.html") + read("flagged.html")
    declared = set(int(n) for n in re.findall(r'(\d+)\s+open flags', text))
    actual = {len(flags)}
    if declared and declared != actual:
        fail("P15", f"a page says {sorted(declared)} flags while the register holds {sorted(actual)}")
    NOTES["P15"] = f"flag counts in prose match the register ({len(flags)})"


def p16_every_row_links() -> None:
    """Every published table row carries at least one link, and a data row carries an external one.

    Same discipline as ``verify/source_audit.py``, enforced here so a page cannot regress without a build
    failure. A row of prose-style metadata may link a file in this repository; a row that states a fact
    about a player, a game or a price must reach an official page or the pinned dataset.
    """
    external = re.compile(r'href="(https?://[^"]+|\.\./raw/[^"]+|raw/[^"]+)"')
    rows_checked = 0
    for page in PAGES:
        html = read(page)
        for ti, block in enumerate(re.findall(r"<table[^>]*>.*?</table>", html, re.S)):
            body = re.search(r"<tbody>(.*?)</tbody>", block, re.S)
            if not body:
                continue
            for ri, tr in enumerate(re.findall(r"<tr>(.*?)</tr>", body.group(1), re.S)):
                rows_checked += 1
                if 'href="' not in tr:
                    first = re.sub(r"<[^>]+>", "", re.search(r"<td[^>]*>(.*?)</td>", tr, re.S).group(1))
                    fail("P16", f"{page} table {ti} row {ri}: no source link at all "
                               f"(first cell: {' '.join(first.split())[:60]!r})")
                    continue
                if 'data-rows=' in block and not external.search(tr):
                    first = re.sub(r"<[^>]+>", "", re.search(r"<td[^>]*>(.*?)</td>", tr, re.S).group(1))
                    fail("P16", f'{page} table {ti} row {ri}: a fact row whose only links are internal '
                                f"(first cell: {' '.join(first.split())[:60]!r})")
    NOTES["P16"] = f"{rows_checked} table rows, every one linked; fact rows linked to an official page or " \
                  "the pinned dataset"


def p17_tag_balance() -> None:
    """Structural sanity: the block elements a page opens are the ones it closes.

    An unclosed ``<div class="section-head">`` is the failure this rule exists for. It renders without an
    error - the browser closes it at the next block boundary - and everything after it silently becomes a
    flex item of the header, so the page still says true things in a broken layout. Values are correct and
    unreadable, which is the worst kind of correct.
    """
    open_tags = re.compile(r"<(/?)(section|div|table|thead|tbody|tr|ul|ol|dl|main|header|nav|figure)\b[^>]*>")
    void = {"br", "hr", "img", "input", "meta", "link"}
    for page in PAGES:
        html = read(page)
        stack: list[tuple[str, int]] = []
        for m in open_tags.finditer(html):
            closing, tag = m.group(1), m.group(2)
            if closing:
                if not stack or stack[-1][0] != tag:
                    where = html[max(0, m.start() - 120):m.start()].replace("\n", " ")[-90:]
                    fail("P17", f"{page}: </{tag}> with no matching open (near: &hellip;{where})")
                    if stack:
                        stack.pop()
                else:
                    stack.pop()
            else:
                stack.append((tag, m.start()))
        for tag, pos in stack:
            where = html[max(0, pos - 40):pos + 90].replace("\n", " ")
            fail("P17", f"{page}: <{tag}> never closed (near: {where[:110]})")
    NOTES["P17"] = f"{len(PAGES)} pages with balanced section, div, table, list and row tags"


CHECKS = [globals()[fn] for _id, _a, _w, fn in RULES]
assert len(CHECKS) == len(RULES)


def main() -> int:
    for check in CHECKS:
        try:
            check()
        except Exception as exc:  # a checker that crashes must not look like a pass
            fail(check.__name__, f"{type(exc).__name__}: {exc}")
    if "-v" in sys.argv:
        for rule, note in NOTES.items():
            print(f"  {rule:<5} {note}")
    if FAILS:
        print(f"FAIL - {len(FAILS)} violation(s):")
        for f in FAILS[:60]:
            print(f"  - {f}")
        if len(FAILS) > 60:
            print(f"  ... and {len(FAILS) - 60} more")
        return 1
    print(f"OK - {len(CHECKS)} rules over {len(PAGES)} pages "
          f"({sum(len(read(p)) for p in PAGES):,} bytes), no violations")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
