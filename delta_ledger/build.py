#!/usr/bin/env python3
"""Render the delta-ledger pages from the committed ledger.json and pins.json.

Deterministic: no clock, no network, no third-party imports. Two runs of this file on the same
manifest produce byte-identical HTML, which is what lets `check.py` treat a stale page as a failure.
The one number that must depend on a clock -- how old the newest capture is -- is deliberately not on
these pages; it is computed by check_drift.py --ci inside the scheduled job, where the clock is real.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
ROOT = HERE.parent
BLOB = "https://github.com/karagemop466-tech/Korea3/blob/main"

NAV = [
    ("index.html", "Read-back"),
    ("runs.html", "Run ledger"),
    ("sources.html", "Per source"),
    ("drift.html", "Delta quality & drift"),
    ("gates.html", "Readiness rows"),
    ("method.html", "Method"),
    ("flagged.html", "Flagged for review"),
]

LINKS = {
    "manifest": (f"{BLOB}/capture/data/manifest.jsonl", "capture/data/manifest.jsonl (the record)"),
    "sources": (f"{BLOB}/capture/data/sources.json", "capture/data/sources.json (the 33 configured sources)"),
    "capture": (f"{BLOB}/capture/index.html", "the capture dashboard"),
    "capture_check": (f"{BLOB}/capture/check.py", "capture/check.py (what the existing gate verifies)"),
    "capture_py": (f"{BLOB}/capture/capture.py", "capture/capture.py (what is fetched and stored)"),
    "workflow": (f"{BLOB}/.github/workflows/capture.yml", ".github/workflows/capture.yml (the cron lines)"),
    "ledger": (f"{BLOB}/delta_ledger/data/ledger.json", "delta_ledger/data/ledger.json"),
    "pins": (f"{BLOB}/delta_ledger/data/pins.json", "delta_ledger/data/pins.json"),
    "drift": (f"{BLOB}/delta_ledger/drift.py", "delta_ledger/drift.py (the single shared rule)"),
    "nfl_injuries": ("https://www.nfl.com/injuries/", "NFL official injury report (official-league)"),
    "club": ("https://www.nfl.com/teams/", "NFL clubs index (official-league)"),
    "readiness": (f"{BLOB}/readiness/index.html", "the decision-readiness register"),
}


def esc(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def link(key: str, label: str | None = None) -> str:
    url, title = LINKS[key]
    return '<a href="' + esc(url) + '" title="' + esc(title) + '">' + esc(label or key) + "</a>"


def blank(why="the manifest does not carry this") -> str:
    return ('<span class="blank" title="' + esc(why) + '">[blank]</span> '
            + '<a class="blank-link" href="flagged.html">' + esc(why) + "</a>")


def num_cell(v, nd=0, signed=False):
    if v is None:
        return "<td>" + blank() + "</td>"
    s = ("{:+." + str(nd) + "f}") if signed else ("{:." + str(nd) + "f}")
    return '<td class="num">' + s.format(v) + "</td>"


def tds(v) -> str:
    return "<td>" + str(v) + "</td>"


def pill(text, kind="info") -> str:
    return '<span class="pill ' + kind + '">' + esc(text) + "</span>"


def table(headers, rows, note=""):
    if not headers or headers[-1] != "Source":
        raise AssertionError("every table must end with a Source column")
    if any(len(r) != len(headers) for r in rows):
        bad = [i for i, r in enumerate(rows) if len(r) != len(headers)]
        raise AssertionError(f"row/header mismatch in {headers[:3]} at rows {bad[:4]}")
    head = "".join("<th>" + esc(h) + "</th>" for h in headers)
    body = "".join("<tr>" + "".join(r) + "</tr>" for r in rows)
    return ('<div class="table-wrap"><table><thead><tr>' + head + "</tr></thead><tbody>" + body
            + "</tbody></table></div>" + (f'<p class="table-note">{note}</p>' if note else ""))


def kpi(label, value, sub=""):
    return ('<div class="kpi"><div class="kpi-label">' + esc(label) + '</div><div class="kpi-value">'
            + value + '</div><div class="kpi-sub">' + sub + "</div></div>")


def page(title, active, body, lede=""):
    nav = "".join('<a class="nav-link' + (" on" if h == active else "") + '" href="' + h + '">' + esc(lbl)
                  + "</a>" for h, lbl in NAV)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} | Availability capture read-back</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="site-header">
  <a class="brand" href="../index.html">Korea3</a>
  <span class="muted">availability capture read-back</span>
  <nav class="nav">{nav}</nav>
</header>
<main class="wrap">
<h1>{title}</h1>
{f'<p class="lede">{lede}</p>' if lede else ''}
{body}
</main>
<footer class="site-footer wrap">
  <p>Nothing on this page is an injury, a depth chart or a player value. It is a read-back of what the
  scheduled capture recorded about itself: run times, HTTP statuses, byte counts, hashes, HTML element
  counts and the deltas between them. <a href="../capture/index.html">Capture dashboard</a> ·
  <a href="../index.html">Site home</a> · <a href="../hub/flagged.html">Site review board</a>.</p>
</footer>
</body>
</html>
"""


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def build_index(led, pins) -> str:
    cov = led["coverage"]
    dq = led["delta_quality"]
    runs = led["runs"]
    n_sources = len(led["sources"])
    events = led["drift_events"]
    fp = dq["false_positive_rate_of_the_byte_delta"]
    inj = next((s for s in led["sources"] if s["source_id"] == "nfl-injuries-week"), None)
    cards = "".join([
        kpi("Scheduled runs read back", str(cov["distinct_runs"]), link("manifest", "the manifest, not the intent")),
        kpi("Dated rows", f'{cov["rows_total"]}', f'{n_sources} sources x {cov["distinct_days"]} days'),
        kpi("Days covered", str(cov["distinct_days"]), esc(", ".join(cov["days"]))),
        kpi("Fetch failures", str(sum(r["fail"] for r in runs)), "every source returned HTTP 200 in every run"),
        kpi("Byte-delta false-positive rate", "—" if fp is None else f"{100 * fp:.1f}%",
            f'{dq["structure_unchanged_while_bytes_changed"]} of {dq["transitions"]} transitions were labelled '
            f'"changed" with an unchanged structural signature'),
        kpi("Drift events the pipeline missed", str(len(events)), link("drift", "listed with the numbers")),
    ])
    verdict = f"""
<h2>What changed since the last session looked</h2>
<div class="callout">
<p><strong>The gate that was open is now partly cleared.</strong> Every readiness row about the capture was
written against an empty manifest ("0 of 33 per day recorded"). The manifest now holds
{cov["rows_total"]} rows over {cov["distinct_runs"]} scheduled runs on {cov["distinct_days"]} distinct days, so
the "two or more timestamped reads" precondition is met for {cov["gate_multi_day_2_reads"]["met"]} of
{cov["gate_multi_day_2_reads"]["of"]} sources. That is a number, not an intention, and it is the first
one of its kind in this repository.</p>
<p><strong>The mechanism it clears is useless as built.</strong> The only change detector the capture has is
a SHA-256 over the raw body. {dq["byte_changed"]} of {dq["transitions"]} transitions were labelled
"changed" and {dq["structure_unchanged_while_bytes_changed"]} of them had an identical table and row count,
a {100 * fp:.1f}% false-positive rate. "Publish the delta, never the level" and "make the injury signal a
surprise, not a level" cannot be satisfied by that signal: a page with a nonce or a timestamp in it looks
brand new every four hours. The structural signature recorded at capture time (table and row counts) is the
detector that works, and it is what this desk pins bands on.</p>
<p><strong>The alarm the brief asked for did not exist, and it would have fired.</strong> Between the runs of
2026-11-18 and 2026-11-19 the injury page's row count moved {inj["row_tags"][2]:.0f} against a median of
{inj["band"]["median"]:.0f} and back; the earlier value was 92% below the median and was recorded as
<code>result=ok</code> with the marker present, so the byte-level check passed it. Two drift events are now
named on the <a href="drift.html">drift page</a>, and <code>check_drift.py</code> turns them red.</p>
<p><strong>What is still not true.</strong> No value is parsed anywhere: a value-level delta -- "Joseph went
from Questionable to Out between Wednesday and Friday" -- is still 0 of what it needs, and it will stay 0
until the owner decides the terms question (readiness B33), because parsing is exactly what the private/public
split is about. This desk publishes the *shape* of the pages, which is a fact about our capture, not about
any club's roster.</p>
</div>
"""
    rows = []
    for r in runs:
        rows.append([
            tds("<code>" + esc(r["run_id"]) + "</code>"),
            tds(esc(", ".join(r["trigger"]))),
            tds(esc(r["utc_date"])), tds(esc(r["utc_weekday"])),
            num_cell(r["sources"], signed=False), num_cell(r["ok"], signed=False), num_cell(r["fail"], signed=False),
            num_cell(r["wall_minutes"], 2), num_cell((r["bytes_total"] or 0) / 1_000_000, 2),
            tds(link("manifest", "132 rows appended")),
        ])
    t = table(["run id", "trigger", "date", "weekday", "sources", "ok", "fail", "wall clock (min)",
               "MiB fetched", "Source"], rows,
              "Run ids are the capture's own UTC stamps. The weekday column matters: the requirement names "
              "Wednesday, Thursday and Friday, and these runs land on Tuesday to Friday, with gaps of "
              f'{cov["min_gap_hours"]}h to {cov["max_gap_hours"]}h -- see the schedule finding on the '
              '<a href="method.html">method page</a>.')
    gaps = []
    for g in cov["gaps"]:
        gaps.append([tds("<code>" + esc(g["from"]) + "</code>"), tds("<code>" + esc(g["to"]) + "</code>"),
                     num_cell(g["hours"], 2), num_cell(g["days"], 2), tds(link("workflow", "cron lines"))])
    t2 = table(["previous run", "next run", "hours between", "days", "Source"], gaps,
               "Scheduled GitHub Actions runs are best-effort: they can be late by many hours. Any freshness "
               "alarm written against the cron time rather than the recorded fetch time will cry on a normal "
               "day, which is why the limit here is 30h and not 26h.")
    body = cards + verdict + "<h2>Run ledger</h2>" + t + "<h2>Gaps between runs</h2>" + t2
    return page("Capture read-back", "index.html", body,
                "The scheduled availability capture has run four times. This desk reads its own record back and "
                "says what it can and cannot prove -- including the two ways it is broken.")


def build_runs(led) -> str:
    runs = {r["run_id"]: r for r in led["runs"]}
    rows = []
    for rid in sorted(runs):
        r = runs[rid]
        rows.append([
            tds("<strong>" + esc(rid) + "</strong>"), tds(esc(r["utc_weekday"]) + " " + esc(r["utc_date"])),
            num_cell(r["sources"], signed=False), num_cell(r["ok"], signed=False), num_cell(r["fail"], signed=False),
            num_cell(r["non200"], signed=False), num_cell(r["wall_minutes"], 2),
            num_cell(r["bytes_total"], 0),
            tds(("all sources returned 200 with the required marker present" if r["fail"] == 0
                 else "some sources failed; see the manifest")),
            tds(link("manifest", "manifest rows")),
        ])
    t = table(["run", "when", "sources", "ok", "fail", "non-200", "wall clock (min)", "bytes",
               "What the run proves", "Source"], rows,
              "'What the run proves' is deliberately modest. A run of 33 successful fetches proves the fetcher "
              "works and the pages exist. It proves nothing about any roster, because nothing is parsed.")
    per_run = {}
    for s in led["sources"]:
        for rid, tags in zip(s["runs"], s["row_tags"]):
            per_run.setdefault(rid, []).append((s["source_id"], tags))
    rows2 = []
    for rid in sorted(per_run):
        pairs = per_run[rid]
        zeros = [sid for sid, t in pairs if (t or 0) == 0]
        total = sum(t for _, t in pairs)
        rows2.append([tds("<code>" + esc(rid) + "</code>"), num_cell(len(pairs), signed=False),
                     num_cell(total, signed=False), num_cell(total / len(pairs), 1),
                     num_cell(len(zeros), signed=False),
                     tds(esc(", ".join(sorted(zeros))[:120]) if zeros else "none"),
                     tds(link("manifest", "row tags per source"))])
    t2 = table(["run", "sources", "row tags total", "mean rows", "sources with zero rows", "which",
                "Source"], rows2,
               "The total row-tag count is the only quantity here that behaves like a signal: it moved from "
               "375-tag runs to a 28-tag run and back, and that movement is the capture telling us something "
               "broke or changed, not the league.")
    return page("Run ledger", "runs.html", t + "<h2>Per-run structural totals</h2>" + t2,
                "Four runs, 132 rows, every one of them an HTTP 200 with its marker present -- and two of them "
                "structurally unlike the others.")


def build_sources(led, pins) -> str:
    rows = []
    for s in led["sources"]:
        band = s["band"]
        rows.append([
            tds("<strong>" + esc(s["source_id"]) + "</strong><br><span class='muted'>" + esc(s["publisher"]) + "</span>"),
            tds('<a href="' + esc(s["url"]) + '">' + esc(s["url"].replace("https://", "")) + "</a>"),
            tds(esc(s["tier"])), num_cell(s["n_runs"], signed=False),
            tds("<code>" + esc(", ".join(str(int(t)) for t in s["row_tags"])) + "</code>"),
            tds("<code>" + esc(", ".join(s["hashes8"])) + "</code>"),
            num_cell(band["median"], 1), num_cell(band["lo"], 1), num_cell(band["hi"], 1),
            tds(esc(band["state"])),
            num_cell(s["n_breaches"], signed=False),
            tds(pill("no structure", "no") if s["no_structure"] else (
                pill("marker always found", "ok") if s["marker_found_all"] else pill("marker missing", "no"))),
            tds(link("manifest", "manifest") + " · " + link("club" if "club" in s["source_id"] else "nfl_injuries",
                                                            "the page itself")),
        ])
    t = table(["Source", "URL", "Tier", "runs", "row tags by run", "hash prefix by run", "median", "band lo",
               "band hi", "Band state", "breaches", "Marker", "Source"], rows,
              "Every hash prefix differs from its neighbour while most row-tag series do not move at all. Read "
              "the two columns side by side and the byte-delta problem is self-evident; the arithmetic is on the "
              "<a href=\"drift.html\">delta-quality page</a>.")
    return page("Per source", "sources.html", t,
                "One row per configured source: how many times it was captured, how many table rows the capture "
                "saw each time, and the band pinned from that history.")


def build_drift(led) -> str:
    dq = led["delta_quality"]
    t1rows = [
        [tds("transitions between consecutive runs"), num_cell(dq["transitions"], signed=False),
         tds("33 sources x (4-1) transitions, plus the injury page"), tds(link("manifest", "manifest"))],
        [tds("labelled <code>changed</code> on bytes"), num_cell(dq["byte_changed"], signed=False),
         tds("the only change signal the capture produces"), tds(link("capture_check", "capture/check.py"))],
        [tds("labelled <code>unchanged</code> on bytes"), num_cell(dq["byte_unchanged"], signed=False),
         tds("zero: no two runs of any source have ever hashed alike"), tds(link("manifest", "manifest"))],
        [tds("structure unchanged while bytes changed"), num_cell(dq["structure_unchanged_while_bytes_changed"], signed=False),
         tds("false positives of the byte delta, counted"), tds(link("ledger", "ledger.json"))],
        [tds("both changed"), num_cell(dq["both_changed"], signed=False),
         tds("byte change with a structural change behind it"), tds(link("ledger", "ledger.json"))],
        [tds("false-positive rate"), num_cell(100 * dq["false_positive_rate_of_the_byte_delta"], 1),
         tds("of the transitions the pipeline reported as an event, this share had no structural change at all"),
         tds(link("drift", "drift.py"))],
    ]
    t1 = table(["Quantity", "Value", "What it means", "Source"], t1rows,
               "A detector that fires on every observation carries no information. This is the arithmetic that "
               "says so about our own pipeline, using only its own committed record.")
    ev = []
    for e in led["drift_events"]:
        src = next((s for s in led["sources"] if s["source_id"] == e["source_id"]), {})
        ev.append([
            tds("<strong>" + esc(e["source_id"]) + "</strong>"), tds(esc(e["kind"])),
            tds("<code>" + esc(e["run_id"]) + "</code>"),
            tds(esc(src.get("clock_times", [None])[(src.get("runs") or []).index(e["run_id"])]
                  if e["run_id"] in (src.get("runs") or []) else "")),
            num_cell(e["row_tags"], 0), num_cell(e["median"], 1), num_cell(e["lo"], 1), num_cell(e["hi"], 1),
            num_cell(e["z"], 2) if e["z"] is not None else tds(blank("MAD is 0: any movement is unbounded surprise")),
            tds(link("manifest", "the row in question")),
        ])
    t2 = table(["Source", "Event", "run", "fetched at", "row tags", "median", "band lo", "band hi", "robust z",
                "Source"], ev,
               "Both events are pages the capture called <code>ok</code>. The first is a source that has never "
               "produced a parsable table; the second is a run where the official report's row count collapsed "
               "to a fraction of its neighbours and back.")
    ser = []
    for i, p in enumerate(led["injury_series"]):
        ser.append([
            tds("<code>" + esc(p["clock_utc"]) + "</code>"), num_cell(p["row_tags"], 0, signed=False),
            num_cell(p["delta_from_level"], 0, signed=True),
            tds(esc(p["byte_delta_label"])), tds(esc(p["structural_delta_label"])),
            tds("the level, published as the series -- with the delta column beside it, which is what the "
                "requirement asks for and what no single-capture repository can produce"),
            tds(link("nfl_injuries", "official page") + " · " + link("manifest", "record")),
        ])
    t3 = table(["fetched at (UTC)", "row tags", "delta from previous read", "byte delta label",
                "structural delta", "Note", "Source"], ser,
               "This is the whole 'surprise, not level' story that the data currently supports: four timestamped "
               "reads of the report page, the change between them, and the honest statement that a *player's* "
               "designation delta needs parsed values, which the capture does not store and this repository must "
               "not publish before the terms decision.")
    body = (t1 + "<h2>Drift events found in the history</h2>" + t2
            + "<h2>The injury report as a time series</h2>" + t3
            + '<div class="callout warn"><p><strong>Where this is enforced.</strong> '
              '<code>python3 delta_ledger/check_drift.py</code> exits non-zero on these events, and '
              '<code>--ci</code> adds the age of the newest capture against a 30-hour limit. It is run by its own '
              'workflow rather than by <code>capture.yml</code>, because that file belongs to another session; '
              'the request to fold the same rule into the capture job is logged on the board. '
              'The rule lives in one function (<a href="' + esc(LINKS["drift"][0]) + '">drift.py</a>) shared by the '
              'page and the alarm, so the published count and the alarm count cannot diverge.</p></div>')
    return page("Delta quality and drift", "drift.html", body,
                "Two questions the four runs can answer: does the change signal carry information, and does the "
                "pipeline notice when a page stops being a page.")


def build_method(led, pins) -> str:
    cov = led["coverage"]
    items = [
        ("What the capture stores, exactly",
         "One JSON line per source per run: run id, trigger, source id, requested and final URL, publisher, tier, "
         "fetch start and end in UTC, HTTP status, content type, byte count, SHA-256 of the body, the marker string "
         "it must contain and whether it did, the count of <table> and <tr> tags, the previous successful hash, and "
         "a delta label of first/unchanged/changed/failed. Raw bodies go to a 90-day workflow artifact, not to git. "
         "No player, injury or depth value is stored anywhere in it."),
        ("Structural signature",
         "The pair (table-tag count, row-tag count) recorded at capture time. Two captures with the same signature "
         "may still differ in content -- a club can rename a player without adding a row -- so the signature is a "
         "floor on change, not a ceiling. It is used here for one purpose: deciding whether a byte change was worth "
         "reporting."),
        ("Band pinning",
         f"For each source, the median of its row-tag counts across runs, plus or minus "
         f"{int(pins['tolerance'] * 100)}%, asserted only once {pins['min_runs']} runs exist. A source whose median "
         f"is 0 is labelled no-structure rather than 'stable at zero': a page that has never yielded a table is a "
         f"known gap, not a steady state."),
        ("Robust outlier test",
         "|count - median| / (1.4826 x MAD) > 3.0, with MAD the median absolute deviation. Median and MAD are used "
         "instead of mean and standard deviation because the broken run must not be allowed to move the baseline it "
         "is being compared against: with four observations, one 28-row run inside a mean-and-sigma rule absorbs "
         "itself and hides the break. When MAD is 0 the band is degenerate and any movement is reported as "
         "unbounded surprise rather than divided by zero."),
        ("Why the alarm is not inside capture.yml",
         "That workflow and capture/check.py belong to the session that built them. Editing them here would be a "
         "scope violation, and silently replacing another session's gate with mine would be worse than adding one. "
         "So the rule ships as delta_ledger/check_drift.py with its own workflow, and the board carries the request "
         "to fold it into the capture job."),
        ("Freshness",
         f"Age is not published on these pages: a page that reads the clock cannot be rebuilt byte-identically, and "
         f"a stale 'fresh' claim is exactly the failure this repository keeps flagging. check_drift.py --ci computes "
         f"age inside the scheduled job against a {cov and 30}-hour limit. The limit is 30h because the observed run "
         f"gaps are {cov['min_gap_hours']}h to {cov['max_gap_hours']}h: Actions schedule times are advisory, so an "
         f"alarm written against the cron line would fire on ordinary days and stop being believed."),
        ("Tiers",
         "official-league (nfl.com), official-club (a club site), dataset (a file in this repository), internal (a "
         "computation over those). Nothing here is tier official except the URLs the capture is configured to fetch; "
         "the values on these pages are about our own fetches."),
        ("Limits of this session",
         "The sandbox reaches github.com, npmjs.org and pypi.org only. No official page was fetched here to confirm "
         "a row count or a designation: the numbers are read back from the manifest the Actions runner wrote, and "
         "the capture's own claim that a marker string was found is the capture's, not this session's."),
    ]
    dl = "".join("<h3>" + esc(t) + "</h3><p>" + esc(b) + "</p>" for t, b in items)
    pins_rows = []
    for sid, pin in sorted(pins["sources"].items()):
        pins_rows.append([tds("<strong>" + esc(sid) + "</strong>"), tds(esc(pin["state"])),
                          num_cell(pin["median"], 1), num_cell(pin["lo"], 1), num_cell(pin["hi"], 1),
                          num_cell(pin["n_runs"], signed=False),
                          tds("<code>" + esc(pin["marker"]) + "</code>"),
                          tds(link("pins", "pins.json") + " · " + link("manifest", "derived from"))])
    t = table(["Source", "Band state", "median", "lo", "hi", "runs", "Required marker", "Source"], pins_rows,
              "Derived from the manifest by readback.py, never hand-set: check_drift.py recomputes every band from "
              "the manifest and fails if a pinned number no longer matches, so an edited threshold is caught rather "
              "than trusted.")
    return page("Method", "method.html", dl + "<h2>Pinned bands, all sources</h2>" + t,
                "What is captured, how the drift rule is defined, and why the alarm lives outside the capture job.")


def build_gates(led) -> str:
    rows = []
    for g in led["gate_updates"]:
        kind = {"moved": "warn", "unchanged": "no",
                "cleared-for-the-stated-denominator": "ok"}.get(g["verdict"], "info")
        rows.append([
            tds("<strong>" + esc(g["id"]) + "</strong>"),
            tds('<a href="../readiness/index.html#' + esc(g["id"]) + '">' + esc(g["requirement"]) + "</a>"),
            tds(esc(g["register_status"])),
            tds(esc(g["gate"])),
            tds(esc(g["clears_target"])),
            tds(esc(g["this_desk"])),
            tds(pill(g["verdict"], kind)),
            tds(link("manifest", "the record") + " · " + link("ledger", "this desk's arithmetic")),
        ])
    t = table(["Row", "Requirement", "Register status", "The gate as the register states it",
               "What would clear it", "What the four runs now produce", "Verdict", "Source"], rows,
              "Read-only beside the register: readiness/** belongs to other sessions, so nothing there is "
              "edited. The row's own words are quoted from "
              "<code>readiness/data/register.json</code> at build time and the new number is computed from the "
              "capture manifest. 'moved' means the denominator changed; it does not mean the requirement is met.")
    n_moved = sum(1 for g in led["gate_updates"] if g["verdict"] == "moved")
    n_unch = sum(1 for g in led["gate_updates"] if g["verdict"] == "unchanged")
    n_clear = sum(1 for g in led["gate_updates"] if g["verdict"] == "cleared-for-the-stated-denominator")
    callout = (f'<div class="callout"><p>Of {len(led["gate_updates"])} capture-related readiness rows, '
               f'{n_moved} have a denominator that moved because the manifest stopped being empty, {n_clear} '
               f'has met the number its own text asked for, and {n_unch} are unchanged because they need '
               f'parsing, a source that is not configured, or a decision that has not been taken. The last group '
               f'is the important one: a longer history of pages does not by itself create a single verified '
               f'player value.</p></div>')
    return page("Readiness rows against the record", "gates.html", callout + t,
                "One row per requirement the capture was supposed to advance, with the gate that blocks it and "
                "the number this repository can now put against it.")

def build_flagged(led) -> str:
    cov = led["coverage"]
    dq = led["delta_quality"]
    flags = [
        ("byte-level delta", "the change signal fires on every run", "high",
         f'{dq["byte_changed"]} of {dq["transitions"]} transitions labelled changed, '
         f'{dq["structure_unchanged_while_bytes_changed"]} with no structural change. Do not build a "surprise" '
         f'feature on this field. Fix: record a normalised content hash at capture time (strip tags, collapse '
         f'whitespace) and label the delta on that; capture/capture.py would need a schema change, which is the '
         f'request on the board.', "capture/data/manifest.jsonl"),
        ("club-depth-hou", "no parsable table in 4 of 4 runs", "high",
         "The Texans publish depth as an image, so the capture returns 200 with the marker present and zero rows. "
         "This corroborates the earlier hand-checked finding with a machine record: n=4 runs, not one look. "
         "The fix is an authorised structured source, not a transcription by eye.", "capture/data/sources.json"),
        ("nfl-injuries-week", "a run 92% below its neighbours was recorded as ok", "high",
         "28 row tags against a median of 326 (the runs either side were 375 and 277). capture/check.py passed it "
         "because it checks bytes, status and a marker string; nothing checks structure. Either the page changed "
         "shape or the fetch raced a partially rendered page, and at present the repository cannot tell which.",
         "capture/data/manifest.jsonl"),
        ("schedule", "run times do not match the cron lines", "medium",
         f"Observed gaps: {cov['min_gap_hours']}h to {cov['max_gap_hours']}h, with the last interval under 10h. "
         f"Actions schedules are best-effort and can be late. Any claim of a 'daily' or 'Wednesday/Thursday/Friday' "
         f"cadence must be computed from the recorded fetch times, not from the workflow file.",
         ".github/workflows/capture.yml"),
        ("coverage", "no values are parsed, so no player-level delta exists", "blocking",
         "The requirement to store every injury read with its clock time and publish the delta is met at page level "
         "and not at value level. Parsing is the owner's terms decision (readiness B33); until it is recorded, "
         "publishing parsed rows would move raw third-party data onto the public site, which the split-layer "
         "requirement forbids.", "readiness register B33"),
        ("depth pages", "row-tag counts are a floor, not a measure of depth", "medium",
         "A stable row count is consistent with a club swapping a starter in the same cell. Nothing on this desk "
         "supports a claim about who is starting; the only safe inference from these numbers is about our own "
         "capture.", "capture/capture.py"),
    ]
    rows = []
    for who, what, sev, why, where in flags:
        rows.append([tds("<strong>" + esc(who) + "</strong>"), tds(esc(what)),
                     tds(pill(sev, "no" if sev in ("high", "blocking") else "warn")), tds(esc(why)),
                     tds(esc(where)), tds(link("manifest", "the record") )])
    t = table(["Item", "Finding", "Severity", "Why it matters and what fixes it", "Where it shows", "Source"], rows,
              "Everything on this page is a defect in our own pipeline found from its own record. None of it is a "
              "claim about a club's roster, and none of it was resolved by this session inside another session's "
              "files -- the fixes are specified here and requested on the board.")
    return page("Flagged for review", "flagged.html", t,
                "What the capture's history shows about the capture, including the parts that are broken.")


def main() -> int:
    led = load("ledger.json")
    pins = load("pins.json")
    pages = {
        "index.html": build_index(led, pins),
        "runs.html": build_runs(led),
        "sources.html": build_sources(led, pins),
        "drift.html": build_drift(led),
        "gates.html": build_gates(led),
        "method.html": build_method(led, pins),
        "flagged.html": build_flagged(led),
    }
    for name, text in pages.items():
        (HERE / name).write_text(text, encoding="utf-8")
    print(f"built {len(pages)} pages in delta_ledger")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
