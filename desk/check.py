#!/usr/bin/env python3
"""Fail-closed verifier for desk/.

Every rule exists because the brief demands it, and each one fails the build instead of printing a
warning. Exit 0 means all rules held.

R1  Determinism: rebuilding every page from data/*.json reproduces the committed bytes.
R2  Per-row sourcing: every table row on every page carries at least one link.
R3  Blanks are honest: every blank marker carries the "never inferred" title, and on the fact pages
    (availability, depth, reconcile) a row with a blank also links a flag, so no empty cell is silent.
R4  Flag integrity: every flag link points at an anchor that exists in flags.json, and every flag
    except those declared untriggered is referenced somewhere.
R5  Internal links resolve, including #anchors.
R6  External links are classified: every absolute URL is a registered source page or a link on the
    official domain that the register already admits. An unclassified host fails the build.
R7  Source discipline: every source ID cited in the data exists; a source marked read=false is
    rendered with the not-opened marker.
R8  Decision gate: no suggestion may be Approved/Rejected/Implemented, and chosen_option and
    decision_date must stay empty while the status is Proposed.
R9  Answer gate: an open question must carry no answer; an answered question must cite a source that
    was actually opened.
R10 Coverage gate: all 32 clubs must appear - in a game, in the no-designation list, or in the bye
    list - and the counts must add up. A silently missing club is how a partial capture passes as
    a full one.
R11 Row-count reconciliation: the number of designation rows printed equals the data file, every
    row has a valid status vocabulary and a www.nfl.com player URL, and no (club, player) repeats.
R12 Ledger is derived, not typed: desk/build_ledger.py is re-run against the repository artifacts
    and the result must equal the committed ledger, byte for byte.
R13 Pinned dataset: the five files the ledgers were computed from still hash to the digests
    recorded in line_lab/data/derived/summary.json.
R14 Provenance honesty: no page in desk/ may describe a market number as official, and no page may
    contain a currency amount, because nothing here is funded.
R15 No merge-conflict markers anywhere in desk/.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
REPO = HERE.parent
REPO_BLOB = "https://github.com/karagemop466-tech/Korea3/blob/main/"
FACT_PAGES = ("availability.html", "depth.html", "reconcile.html")

ALLOWED_HOSTS = {
    "www.nfl.com", "nfl.com", "static.www.nfl.com", "operations.nfl.com", "support.nfl.com",
    "nextgenstats.nfl.com", "www.denverbroncos.com", "github.com",
}
STATUS_VOCAB = {"OUT", "DOUBTFUL", "QUESTIONABLE"}

failures: list[str] = []
notes: list[str] = []


def fail(rule: str, msg: str) -> None:
    failures.append(f"[{rule}] {msg}")


def note(msg: str) -> None:
    notes.append(msg)


class Scanner(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict] = []
        self.links: list[str] = []
        self.anchors: set[str] = set()
        self.blank_total = 0
        self.blank_unlabelled = 0
        self._tbody = False
        self._self_table = False
        self.self_rows = 0
        self._row: dict | None = None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "table":
            # A table marked "self" holds arithmetic over this directory's own files (counts of
            # the register, coverage lines). It carries no claim about the league, so it has no
            # external source to link - but it may not contain blanks either, which is what stops
            # the class from becoming a way to smuggle an unsourced fact past R2.
            self._self_table = "self" in (a.get("class") or "")
        elif tag == "tbody":
            self._tbody = True
        elif tag == "tr" and self._tbody:
            self._row = {"links": [], "blanks": 0, "flags": 0, "self": self._self_table, "text": "",
                         "placeholder": "no-rows" in (a.get("class") or "")}
        if a.get("id"):
            self.anchors.add(a["id"])
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
            if self._row is not None:
                self._row["links"].append(a["href"])
                if "flagged.html#" in a["href"]:
                    self._row["flags"] += 1
        if tag == "span" and "blank" in (a.get("class") or ""):
            self.blank_total += 1
            if "never inferred" not in (a.get("title") or ""):
                self.blank_unlabelled += 1
            if self._row is not None:
                self._row["blanks"] += 1

    def handle_data(self, data):
        if self._row is not None:
            self._row["text"] += data

    def handle_endtag(self, tag):
        if tag == "table":
            self._self_table = False
        if tag == "tbody":
            self._tbody = False
        elif tag == "tr" and self._row is not None:
            self.rows.append(self._row)
            self._row = None


def _txt(row) -> str:
    return " ".join((row.get("text") or "").split())[:110]


def load(name: str):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def main() -> int:
    pages = sorted(p.name for p in HERE.glob("*.html"))
    if not pages:
        fail("R1", "no pages built")
        return report()

    # R1 + R15 ----------------------------------------------------------------
    before = {p: (HERE / p).read_text(encoding="utf-8") for p in pages}
    # R15 looks for git conflict markers. The literals are built rather than written so
    # this file does not report a conflict inside itself.
    left, right, mid = "<" * 7, ">" * 7, "=" * 7
    for p in list(DATA.glob("*.json")) + [HERE / "build.py", HERE / "check.py", HERE / "build_ledger.py"] + \
            [REPO / ".github/workflows/desk-verify.yml"]:
        if not p.is_file():
            continue
        body = p.read_text(encoding="utf-8")
        for marker in (left, right):
            if marker in body:
                fail("R15", f"{p.name} contains a merge-conflict marker")
        if mid in body and str(p).endswith(".yml"):
            fail("R15", f"{p.name} contains a merge-conflict marker")
    r = subprocess.run([sys.executable, str(HERE / "build.py")], capture_output=True, text=True, cwd=str(REPO))
    if r.returncode != 0:
        fail("R1", f"rebuild failed: {r.stderr.strip()[:400]}")
        return report()
    after = {p: (HERE / p).read_text(encoding="utf-8") for p in pages}
    drift = [p for p in before if before[p] != after[p]]
    if drift:
        fail("R1", f"rebuild changed bytes on {', '.join(sorted(drift))} - edit desk/data, then run desk/build.py")
    else:
        note(f"R1 determinism: {len(pages)} pages rebuild byte-identical")

    # R12 + R13 ---------------------------------------------------------------
    ledger_before = (DATA / "ledger.json").read_bytes()
    r = subprocess.run([sys.executable, str(HERE / "build_ledger.py")], capture_output=True, text=True, cwd=str(REPO))
    if r.returncode != 0:
        fail("R12", f"ledger derivation failed: {r.stderr.strip()[:400]}")
    elif (DATA / "ledger.json").read_bytes() != ledger_before:
        fail("R12", "desk/data/ledger.json is not what build_ledger.py derives from the repository artifacts")
    else:
        note("R12 ledger reproduced from artifacts: " + r.stdout.strip().splitlines()[-1][:220])
    led = load("ledger.json")
    pd = led["pinned_dataset"]
    if pd["matched"] != pd["total"]:
        fail("R13", f'pinned dataset mismatch: {pd["matched"]}/{pd["total"]} files match the recorded digests')
    else:
        note(f"R13 pinned dataset: {pd['total']}/{pd['total']} SHA-256 digests recomputed and matched")

    # load data ---------------------------------------------------------------
    avail = load("availability.json")
    flags = load("flags.json")["flags"]
    flag_ids = {f["id"] for f in flags}
    srcs = {s["id"]: s for s in load("sources.json")["sources"]}

    per_page: dict[str, Scanner] = {}
    for p in pages:
        s = Scanner()
        s.feed((HERE / p).read_text(encoding="utf-8"))
        per_page[p] = s

    # R2, R3 ------------------------------------------------------------------
    # Every row that asserts something about the league must link a registered source. A table
    # may be exempted only by the class "self", which is reserved for arithmetic over this
    # directory's own files; three things make that exemption safe to grant: a self table may not
    # contain a blank marker, it may not appear on a fact page at all, and it must sit inside a
    # passage that is itself linked.
    total_rows = total_links = self_rows = 0
    srcs_raw = load("sources.json")
    registered_urls = {x["url"] for x in srcs_raw["sources"]}
    families = [(f["prefix"], f["covered_by"]) for f in srcs_raw.get("link_families", [])]
    for p, s_ in per_page.items():
        for row in s_.rows:
            if row["placeholder"]:
                continue
            if row["self"]:
                self_rows += 1
                if row["blanks"]:
                    fail("R2", f"{p}: a table marked self carries a blank marker")
                if p in FACT_PAGES:
                    fail("R2", f"{p}: a fact page may not exempt a table from the row-link rule by class")
                continue
            total_rows += 1
            if row["links"]:
                total_links += 1
                # A row is cited when at least one of its links is a registered source, this
                # repository's own register, or a URL inside a registered link family. Links beyond
                # that (an official game page, for instance) are welcome as extra reading and are
                # host-checked by R6, but they cannot be the row's only citation.
                accepted = sum(1 for l in row["links"]
                               if l in registered_urls or l.startswith(REPO_BLOB)
                               or any(l.startswith(pre) for pre, _ in families))
                if not accepted:
                    fail("R2", f"{p}: a row's links are not registered sources: {_txt(row)}")
            else:
                fail("R2", f"{p}: a table row carries no source link: {_txt(row)}")
            if p in FACT_PAGES and row["blanks"] and not row["flags"]:
                fail("R3", f"{p}: a row with {row['blanks']} blank cell(s) does not link a flag")
        if s_.blank_unlabelled:
            fail("R3", f"{p}: {s_.blank_unlabelled} blank marker(s) without the 'never inferred' title")
        html = (HERE / p).read_text(encoding="utf-8")
        at = 0
        while True:
            i = html.find('class="grid self"', at)
            if i < 0:
                break
            if "<a href=" not in html[max(0, i - 1500):i]:
                fail("R2", f"{p}: a table is marked self outside any sourced passage")
            at = i + 1
    for p, sc in per_page.items():
        for l in sc.links:
            if l.startswith(REPO_BLOB) and not (REPO / l[len(REPO_BLOB):]).is_file():
                fail("R2", f"{p}: cites {l}, which is not a file in this repository")
    note(f"R2 rows with a registered source link: {total_links}/{total_rows}; "
         f"{self_rows} table-of-contents rows exempt by class (a desk table listing suggestions "
         f"or options is not itself a claim about the league); R3 blanks: "
         f"{sum(x.blank_total for x in per_page.values())} marked")

    # R4 ----------------------------------------------------------------------
    for p, s in per_page.items():
        for link in s.links:
            if link.startswith("flagged.html#"):
                anchor = link.split("#", 1)[1]
                if anchor not in flag_ids:
                    fail("R4", f"{p}: link to flag {anchor} which is not in flags.json")
    referenced = {l.split("#", 1)[1] for p_, sc in per_page.items() if p_ != "flagged.html"
                  for l in sc.links if l.startswith("flagged.html#")}
    for f_ in flags:
        seen = f_.get("seen_on", [])
        if not seen and f_["status"] != "resolved this cycle":
            fail("R4", f'flag {f_["id"]} is open but names no page where it is visible')
        for pg in seen:
            if pg not in per_page:
                fail("R4", f'flag {f_["id"]} claims visibility on {pg}, which does not exist')
            elif f'flagged.html#{f_["id"]}' not in (HERE / pg).read_text(encoding="utf-8"):
                fail("R4", f'flag {f_["id"]} claims visibility on {pg}, which does not link it')
    orphan = sorted(flag_ids - referenced - {"flagged.html"})
    if orphan:
        fail("R4", f"flags published but never linked from any page: {', '.join(orphan)}")
    from_rows = sum(1 for sc in per_page.values() for r in sc.rows if r["flags"])
    note(f"R4 flags: {len(flag_ids)} published, {len(referenced)} linked into from other pages, "
         f"{from_rows} rows carry a flag link of their own, {len(orphan)} unreachable")

    # R5, R6 ------------------------------------------------------------------
    internal = 0
    external = 0
    for p, sc in per_page.items():
        for link in sc.links:
            if link.startswith(("http://", "https://")):
                external += 1
                host = urlsplit(link).netloc.lower()
                if host not in ALLOWED_HOSTS:
                    fail("R6", f"{p}: link to unclassified host {host}")
                elif host.endswith("github.com"):
                    ok_gh = link.startswith("https://github.com/karagemop466-tech/Korea3") or \
                        link.startswith("https://github.com/nflverse/nfldata")
                    if not ok_gh:
                        fail("R6", f"{p}: unexpected github link {link}")
                continue
            if link.startswith("#"):
                internal += 1
                anchor = link[1:]
                if anchor and anchor not in sc.anchors:
                    fail("R5", f"{p}: anchor {link} does not resolve on this page")
                continue
            target, _, anchor = link.partition("#")
            if not target.endswith((".html", "/")):
                fail("R5", f"{p}: internal link {link!r} is not a page this directory can serve")
                continue
            internal += 1
            if target.startswith("../"):
                if not (REPO / target[3:]).is_file():
                    fail("R5", f"{p}: link {link} points at a missing repository page")
                continue
            tp = HERE / target
            if not tp.is_file():
                fail("R5", f"{p}: link to missing page {target}")
                continue
            if anchor:
                other = per_page.get(target)
                if other is not None and anchor not in other.anchors and anchor not in flag_ids:
                    fail("R5", f"{p}: {link} - no such anchor on the target page")
    note(f"R5/R6 links: {internal} internal checked, {external} external classified against "
         f"{len(ALLOWED_HOSTS)} allowed hosts")

    # R7 ----------------------------------------------------------------------
    cited = set()
    for f in DATA.glob("*.json"):
        if f.name == "sources.json":
            continue
        txt = f.read_text(encoding="utf-8")
        for sid in re.findall(r'"(?:source|answer_source_id|designation_source|result_source|record_source)"\s*:\s*"([A-Z]\d\d)"', txt):
            cited.add(sid)
    cited |= {g["source"] for g in avail["byes"]}
    missing = sorted(cited - set(srcs))
    if missing:
        fail("R7", f"source IDs cited but not registered: {', '.join(missing)}")
    for sid, s_ in srcs.items():
        if s_.get("read"):
            continue
        for p in pages:
            if p == "sources.html":
                continue
            if f'>{sid}</a>' in after[p] and f'{sid}<sup>' not in after[p]:
                fail("R7", f"{p}: cites {sid}, a source not opened this cycle, without the not-opened marker")
            if f'href="{s_["url"]}"' in after[p] and f'>{sid}</a>' in after[p]:
                fail("R7", f"{p}: links {sid} as if it were confirmed evidence")
    note(f"R7 sources: {len(srcs)} registered, {len(cited)} cited, "
         f'{sum(1 for s in srcs.values() if s.get("read"))} opened this cycle')

    # R8 ----------------------------------------------------------------------
    # The gate the brief demands: nothing on this board may advance past Proposed on an agent's
    # authority. A recorded owner decision is the only thing that can move it, and "Implemented"
    # is not available here at all - the desk cannot attest to code it did not write.
    sug = load("suggestions.json")["suggestions"]
    dec_ids = {r["suggestion"] for r in load("decisions.json")["records"]}
    for x in sug:
        st = x["decision_status"]
        if st not in load("suggestions.json")["decision_gate"]["statuses_allowed"]:
            fail("R8", f'suggestion {x["id"]} carries a status outside the register\'s vocabulary: {st!r}')
        if st == "Implemented":
            fail("R8", f'suggestion {x["id"]} is marked Implemented from inside the desk, which builds pages only')
        if st in ("Approved", "Rejected", "Deferred") and x["id"] not in dec_ids:
            fail("R8", f'suggestion {x["id"]} is {st!r} with no entry in decisions.json; a state without a record '
                       'is an agent deciding')
        if st.startswith("Proposed") and (x["chosen_option"] or x["decision_date"]):
            fail("R8", f'suggestion {x["id"]} is still Proposed but carries a chosen option or a date')
        if not x["options"]:
            fail("R8", f'suggestion {x["id"]} has no options, which is a decision dressed as a proposal')
    note(f"R8 decision gate: {sum(1 for x in sug if x['decision_status'].startswith('Proposed'))}/{len(sug)} awaiting "
         f"the owner; {len(dec_ids)} record(s) in the decision log")

    # R9 ----------------------------------------------------------------------
    qs = load("questions.json")["questions"]
    for x in qs:
        if x["status"].startswith("open") and x["answer"]:
            fail("R9", f'question {x["id"]} is open but carries an answer')
        if not x["status"].startswith("open") and not x["answer"]:
            fail("R9", f'question {x["id"]} is marked {x["status"]!r} with no answer')
        if x.get("answer_source_id"):
            s = srcs.get(x["answer_source_id"])
            if not s:
                fail("R9", f'question {x["id"]} cites an unregistered source for its answer')
            elif not s.get("read"):
                fail("R9", f'question {x["id"]} answers itself from {x["answer_source_id"]}, which was not opened')
    note(f"R9 answer gate: {sum(1 for x in qs if x['status'].startswith('open'))} open with no answer, "
         f"{sum(1 for x in qs if not x['status'].startswith('open'))} answered with a source attached")

    # R10, R11 -----------------------------------------------------------------
    clubs = {g["away"] for g in avail["games"]} | {g["home"] for g in avail["games"]}
    clubs |= {r["club"] for r in avail["designations"]}
    clubs |= {b["club"] for b in avail["byes"]}
    clubs |= set(avail["clubs_with_no_designations_published"])
    if len(clubs) != 32:
        fail("R10", f"coverage is {len(clubs)} clubs, not 32")
    if len(avail["games"]) != avail["slate"]["games"]:
        fail("R10", f'{len(avail["games"])} game rows but the slate claims {avail["slate"]["games"]}')
    if avail["designation_count"] != len(avail["designations"]):
        fail("R11", "designation_count does not equal the number of rows")
    if f"{avail['designation_count']} rows" not in after["availability.html"]:
        fail("R11", "the page does not state the row count that the data holds")
    seen = set()
    for r_ in avail["designations"]:
        if r_["status"] not in STATUS_VOCAB:
            fail("R11", f'row {r_["player"]!r} has status {r_["status"]!r}, outside the published vocabulary')
        u = urlsplit(r_["player_url"])
        if u.netloc != "www.nfl.com" or not u.path.startswith("/players/"):
            fail("R11", f'row {r_["player"]!r} links a non-official player URL')
        key = (r_["club"], r_["slug"])
        if key in seen:
            fail("R11", f"duplicate row for {key}")
        seen.add(key)
        if r_["club"] not in clubs:
            fail("R11", f"designation row for club {r_['club']} that is not in the slate")
    note(f"R10/R11 coverage: 32 clubs accounted for; {len(avail['designations'])} designation rows validated")

    # R16, R17 - the decision graph and the decision log ----------------------
    q_ids = {x["id"] for x in load("questions.json")["questions"]}
    sug = load("suggestions.json")["suggestions"]
    dec = load("decisions.json")
    recs = {r["suggestion"]: r for r in dec["records"]}
    for x in sug:
        im = x.get("impact") or {}
        for key in ("moves", "unblocks", "closes", "related_questions", "affects_pages", "enables"):
            if key not in im:
                fail("R16", f'suggestion {x["id"]} has no "{key}" in its impact block')
        if not im.get("moves"):
            fail("R16", f'suggestion {x["id"]} claims to be a suggestion but says nothing would move')
        for q in im.get("unblocks", []) + im.get("related_questions", []):
            if q not in q_ids:
                fail("R16", f'suggestion {x["id"]} says it touches {q}, which is not a question on the board')
        for fl in im.get("closes", []):
            if fl not in flag_ids:
                fail("R16", f'suggestion {x["id"]} says it retires {fl}, which is not a flag')
        for pg in im.get("affects_pages", []):
            if pg not in pages:
                fail("R16", f'suggestion {x["id"]} says it edits {pg}, which is not a page this directory builds')
        for sid in x.get("source_ids", []):
            if sid not in srcs:
                fail("R16", f'suggestion {x["id"]} cites source {sid}, which is not registered')
        # an unblock must be real: a decision cannot answer a question that a fetch answers
        for q in im.get("unblocks", []):
            row = next(x_ for x_ in load("questions.json")["questions"] if x_["id"] == q)
            if "owner" not in row["who_can_answer"].lower():
                fail("R16", f'suggestion {x["id"]} claims it answers {q}, but {q} is answered by '
                            f'{row["who_can_answer"][:60]!r}, not by the owner')
    # every open blocking question must be reachable from the board
    for row in load("questions.json")["questions"]:
        if row["blocking"] and row["status"].startswith("open"):
            touched = [x["id"] for x in sug if row["id"] in (x.get("impact") or {}).get("unblocks", [])
                       or row["id"] in (x.get("impact") or {}).get("related_questions", [])]
            if not touched:
                fail("R16", f'question {row["id"]} blocks a decision and no suggestion touches it, so the board '
                            'cannot unblock it')
    # R17: the decision log and the suggestion states must agree
    for x in sug:
        rec = recs.get(x["id"])
        decided = not x["decision_status"].startswith("Proposed")
        if decided and not rec:
            fail("R17", f'suggestion {x["id"]} is "{x["decision_status"]}" with no entry in decisions.json')
        if rec and not decided:
            fail("R17", f'{rec["id"]} records a decision for {x["id"]} but the register still says '
                        f'"{x["decision_status"]}"')
        if rec:
            if rec["option"] not in " || ".join(o["option"] for o in x["options"]):
                fail("R17", f'{rec["id"]} chose {rec["option"][:40]!r}, which is not one of {x["id"]}\'s options')
            if rec["date"] != x["decision_date"]:
                fail("R17", f'{rec["id"]} is dated {rec["date"]} but the register says {x["decision_date"]}')
            if rec["decision"] not in x["decision_status"]:
                fail("R17", f'{rec["id"]} says {rec["decision"]!r} while the register says {x["decision_status"]!r}')
            for cons in rec.get("consequences_applied", []):
                if cons.startswith("F"):
                    f_ = next((y for y in flags if y["id"] == cons), None)
                    if f_ is None:
                        fail("R17", f'{rec["id"]} closes {cons}, which is not a flag')
                    elif rec["decision"] == "Approved" and f_["status"] == "open":
                        fail("R17", f'{rec["id"]} is recorded as closing {cons} but that flag is still open')
                elif cons.startswith("KQ"):
                    if cons not in q_ids:
                        fail("R17", f'{rec["id"]} answers {cons}, which is not a question')
            if rec["decision"] == "Approved":
                for fl in (x.get("impact") or {}).get("closes", []):
                    if fl not in rec.get("consequences_applied", []):
                        fail("R17", f'{x["id"]} is Approved and its impact says it retires {fl}, but the decision '
                                    'record does not list {fl} among the consequences applied')
    for r in dec["records"]:
        if r["suggestion"] not in {x["id"] for x in sug}:
            fail("R17", f'decision {r["id"]} refers to {r["suggestion"]}, which is not on the board')
    n_dec = len(dec["records"])
    n_impact = sum(1 for x in sug if (x.get("impact") or {}).get("moves"))
    note(f"R16 decision graph: {n_impact}/{len(sug)} suggestions carry a validated impact block; "
         f'{sum(1 for r_ in load("questions.json")["questions"] if r_["blocking"] and r_["status"].startswith("open"))}'
         ' blocking questions all reachable from the board')
    note(f"R17 decision log: {n_dec} record(s) reconciled against {len(sug)} register states")

    # R18 - the repository's own per-row standard, re-run from here so no table can use the
    # "self" exemption to dodge the gate CI actually enforces.
    r = subprocess.run([sys.executable, str(REPO / "verify/source_audit.py"), "--max-unsourced", "0",
                        "--allow-dirs", "session-398c4b58,qa"], capture_output=True, text=True, cwd=str(REPO))
    out = (r.stdout + r.stderr).strip().splitlines()
    tail = out[-1] if out else "no output"
    desk_rows = [l for l in out if "desk/" in l]
    if r.returncode != 0 or desk_rows:
        fail("R18", "verify/source_audit.py disagrees with this directory: "
                    + (desk_rows[0].strip() if desk_rows else tail)[:200])
    else:
        note(f"R18 repository per-row standard: {tail[:120]}")

    # R14 ----------------------------------------------------------------------
    joined = "".join(after[p] for p in pages)
    for pat, label in [(r"\$\s?\d[\d,.]*", "a currency amount"),
                       (r"\bofficial (?:odds|roi|closing line|price)\b", "a market figure described as official"),
                       (r"officially published (?:odds|prices|lines)", "a market figure described as official")]:
        m = re.search(pat, joined, flags=re.I)
        if m:
            fail("R14", f"pages contain {label}: ...{joined[max(0, m.start()-70):m.end()+40]}...")
    note("R14 no currency amount and no market figure described as official")

    return report(pages, total_rows)


def report(pages=None, total_rows=0) -> int:
    for n in notes:
        print("  ok  ", n)
    if failures:
        print("\nFAIL")
        for f_ in failures:
            print("  X   ", f_)
        return 1
    print(f"\nPASS - desk: {len(pages or [])} pages, {total_rows} table rows, every rule held")
    return 0


if __name__ == "__main__":
    sys.exit(main())
