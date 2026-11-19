#!/usr/bin/env python3
"""Build the capture pages from capture/data/manifest.jsonl and capture/data/sources.json.

Deterministic: the output depends only on the two data files. No clock is read, so two builds
on the same data produce byte-identical HTML. Publishes hashes, clock times, HTTP statuses,
byte counts and deltas. It does NOT publish any injury, depth or player value.
"""
from __future__ import annotations

import html
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
MANIFEST = DATA / "manifest.jsonl"
SOURCES = DATA / "sources.json"
REPO_BLOB = "https://github.com/karagemop466-tech/Korea3/blob/main/capture/data/manifest.jsonl"
SCHEDULE_FILE = "https://github.com/karagemop466-tech/Korea3/blob/main/.github/workflows/capture.yml"

NAV = [
    ("index.html", "Dashboard"),
    ("history.html", "Run history"),
    ("sources.html", "Sources"),
    ("method.html", "Method"),
    ("flagged.html", "Flagged for Review"),
]


def e(value) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def load_manifest() -> list[dict]:
    if not MANIFEST.exists():
        return []
    return [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]


def page(title: str, active: str, body: str, depth: str = "") -> str:
    links = []
    for href, label in NAV:
        cls = ' class="on"' if href == active else ""
        links.append(f'<a href="{depth}{href}"{cls}>{e(label)}</a>')
    nav = "".join(links)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} · Official availability capture</title>
<link rel="stylesheet" href="{depth}assets/style.css">
</head>
<body>
<header class="top">
  <div class="wrap">
    <div class="brand"><a href="{depth}../index.html">Korea3</a> <span>/ official availability capture</span></div>
    <nav>{nav}<a href="{depth}../index.html">Site home</a></nav>
  </div>
</header>
<main class="wrap">
{body}
</main>
<footer class="wrap foot">
  Every value on this site is a hash, a clock time, a status code, a byte count or a delta between two
  captures. No injury, depth or player value is published here. Built from
  <a href="{depth}data/manifest.jsonl">capture/data/manifest.jsonl</a> by <code>capture/build.py</code>.
</footer>
</body>
</html>
"""


def kpi(label: str, value: str, note: str = "") -> str:
    return f'<div class="kpi"><div class="k">{e(label)}</div><div class="v">{e(value)}</div><div class="n">{e(note)}</div></div>'


def latest_per_source(rows: list[dict]) -> dict[str, dict]:
    latest: dict[str, dict] = {}
    for row in rows:
        latest[row["source_id"]] = row  # rows are appended in run order
    return latest


def has_depth_tag_evidence(row: dict) -> bool:
    """Return whether a successful depth response contains table AND row tags.

    This is a raw-HTML shape check only. It does not verify that any names, positions,
    slots or values are present or correct.
    """
    if not row or row.get("result") != "ok":
        return False
    counts = (row.get("table_tags"), row.get("row_tags"))
    return all(isinstance(value, int) and not isinstance(value, bool) and value > 0 for value in counts)


def structure_alert_id(source: dict) -> str:
    club = source.get("club") or source.get("id", "unknown").replace("club-depth-", "").upper()
    return f"C-08-{club}"


def structural_alerts(sources: list[dict], rows: list[dict]) -> list[dict]:
    """Find depth sources with successful captures that lacked positive counts for both table and row tags.

    A successful raw fetch is still retained as such. This warning prevents a hash or
    broad text marker from being mistaken for structured depth evidence.
    """
    alerts = []
    latest = latest_per_source(rows)
    for source in sources:
        if source.get("kind") != "club-depth-chart":
            continue
        successful = [
            row for row in rows
            if row.get("source_id") == source.get("id") and row.get("result") == "ok"
        ]
        missing = [row for row in successful if not has_depth_tag_evidence(row)]
        if not missing:
            continue
        alerts.append({
            "id": structure_alert_id(source),
            "source": source,
            "latest": latest.get(source["id"]),
            "successful_count": len(successful),
            "missing_count": len(missing),
        })
    return alerts


def depth_shape_cell(source: dict, row: dict | None, alert: dict | None) -> str:
    """Render observed HTML tag counts without treating them as parsed depth values."""
    if source.get("kind") != "club-depth-chart":
        return '<span class="sub">not a depth chart</span>'
    if row is None:
        return '<span class="sub">not observed</span>'
    if row.get("result") != "ok":
        return '<span class="flag">not observed (capture failed)</span>'
    table_tags = row.get("table_tags")
    row_tags = row.get("row_tags")
    table_text = e(table_tags) if isinstance(table_tags, int) and not isinstance(table_tags, bool) else "blank"
    row_text = e(row_tags) if isinstance(row_tags, int) and not isinstance(row_tags, bool) else "blank"
    summary = f"{table_text} table tags · {row_text} row tags"
    if not has_depth_tag_evidence(row):
        summary += ' <span class="flag">— no structured depth evidence</span>'
    else:
        summary += ' <span class="sub">(HTML tag counts only; values not parsed)</span>'
    if alert:
        summary += f' <a href="flagged.html#{e(alert["id"])}">review {e(alert["id"])}</a>'
    return summary


def runs_of(rows: list[dict]) -> list[str]:
    seen: list[str] = []
    for row in rows:
        if row["run_id"] not in seen:
            seen.append(row["run_id"])
    return sorted(seen)


def build_index(sources: list[dict], rows: list[dict]) -> str:
    runs = runs_of(rows)
    latest_run = runs[-1] if runs else None
    last_rows = [r for r in rows if r["run_id"] == latest_run] if latest_run else []
    ok_last = sum(1 for r in last_rows if r["result"] == "ok")
    fail_last = sum(1 for r in last_rows if r["result"] == "fail")
    changed_last = sum(1 for r in last_rows if r["delta"] == "changed")
    unchanged_last = sum(1 for r in last_rows if r["delta"] == "unchanged")
    latest = latest_per_source(rows)
    alert_by_source = {alert["source"]["id"]: alert for alert in structural_alerts(sources, rows)}
    if latest_run:
        clock = min(r["fetch_start_utc"] for r in last_rows)
        status_note = f"{ok_last} ok · {fail_last} fail of {len(last_rows)} sources"
    else:
        clock = "no capture yet"
        status_note = "the first scheduled run has not written a row"
    kpis = "".join([
        kpi("Sources tracked", str(len(sources)), "official pages, from capture/data/sources.json"),
        kpi("Captures on record", str(len(runs)), "runs with at least one manifest row"),
        kpi("Latest run (UTC)", clock, status_note),
        kpi("Changed in latest run", str(changed_last) if latest_run else "", f"{unchanged_last} unchanged vs previous capture"),
    ])
    trs = []
    for src in sources:
        r = latest.get(src["id"])
        if r is None:
            trs.append(
                f'<tr><td><a href="{e(src["url"])}">{e(src["name"])}</a><div class="sub">{e(src["publisher"])}</div></td>'
                f'<td>{e(src["tier"])}</td><td></td><td></td><td></td><td></td><td class="flag">not yet captured</td>'
                f'<td></td><td>{depth_shape_cell(src, None, None)}</td></tr>'
            )
            continue
        digest = r["sha256"] or ""
        cls = {"changed": "chg", "unchanged": "same", "first": "new", "failed": "bad"}.get(r["delta"], "")
        result_cls = "ok" if r["result"] == "ok" else "bad"
        trs.append(
            f'<tr><td><a href="{e(src["url"])}">{e(src["name"])}</a><div class="sub">{e(src["publisher"])}</div></td>'
            f'<td>{e(src["tier"])}</td>'
            f'<td class="mono">{e(r["fetch_start_utc"])}</td>'
            f'<td>{e(r["http_status"] if r["http_status"] is not None else "")}</td>'
            f'<td class="num">{e(r["bytes"])}</td>'
            f'<td class="mono" title="{e(digest)}">{e(digest[:16])}</td>'
            f'<td><span class="pill {cls}">{e(r["delta"])}</span></td>'
            f'<td><span class="pill {result_cls}">{e(r["result"])}</span>'
            f'{("<div class=sub>" + e(r["reason"]) + "</div>") if r["reason"] else ""}</td>'
            f'<td>{depth_shape_cell(src, r, alert_by_source.get(src["id"]))}</td></tr>'
        )
    table = (
        '<div class="card"><h2>Latest capture of every source</h2>'
        '<p class="sub">Each row links to the official page that was fetched. "Delta" compares the body hash with the '
        'previous successful capture of the same page. HTML table/row tag counts are diagnostic only: they do not '
        'verify player names, positions, slots or completeness. A blank cell means the capture did not produce that value.</p>'
        '<div class="scroll"><table><thead><tr><th>Source (official link)</th><th>Tier</th><th>Fetched (UTC)</th>'
        '<th>HTTP</th><th>Bytes</th><th>SHA-256 (first 16)</th><th>Delta</th><th>Raw capture</th>'
        '<th>HTML tags (not parsed)</th></tr></thead><tbody>'
        + "".join(trs) + "</tbody></table></div></div>"
    )
    alerts = list(alert_by_source.values())
    if alerts:
        alert_links = ", ".join(
            f'<a href="flagged.html#{e(alert["id"])}">{e(alert["source"].get("club", alert["source"]["id"]))}</a>'
            for alert in alerts
        )
        structural_notice = (
            '<div class="card"><strong class="flag">Structured-depth evidence alert</strong>'
            f'<p>{len(alerts)} club depth source(s) have one or more successful raw captures missing a positive count for either table tags or row tags: '
            f'{alert_links}. The HTTP/hash capture may be valid, but those snapshots do not provide structured depth evidence. '
            'No values have been inferred or transcribed. See the per-source flags.</p></div>'
        )
    else:
        structural_notice = ""
    body = f"""<section class="hero">
  <h1>Official availability capture</h1>
  <p>A scheduled, dated record of the NFL injury report and club depth-chart pages. Each capture keeps the raw
  body's SHA-256, the UTC fetch time and the status. A successful hash/marker check confirms only that a response was
  captured; it does not confirm that the response contains complete, usable injury or depth data.</p>
  <p class="sub">Schedule: <a href="{SCHEDULE_FILE}">.github/workflows/capture.yml</a>. Manifest:
  <a href="{REPO_BLOB}">capture/data/manifest.jsonl</a>. Structure tags are reported only as diagnostics; values are not parsed.</p>
</section>
<section class="kpis">{kpis}</section>
{structural_notice}
{table}"""
    return page("Dashboard", "index.html", body)


def build_history(rows: list[dict]) -> str:
    runs = runs_of(rows)
    trs = []
    for run_id in reversed(runs):
        rr = [r for r in rows if r["run_id"] == run_id]
        trigger = rr[0]["run_trigger"]
        start = min(r["fetch_start_utc"] for r in rr)
        end = max(r["fetch_end_utc"] for r in rr)
        ok = sum(1 for r in rr if r["result"] == "ok")
        fail = len(rr) - ok
        changed = sum(1 for r in rr if r["delta"] == "changed")
        unchanged = sum(1 for r in rr if r["delta"] == "unchanged")
        trs.append(
            f'<tr><td class="mono">{e(run_id)}</td><td>{e(trigger)}</td><td class="mono">{e(start)}</td>'
            f'<td class="mono">{e(end)}</td><td class="num">{ok}</td><td class="num">{fail}</td>'
            f'<td class="num">{changed}</td><td class="num">{unchanged}</td>'
            f'<td><a href="data/manifest.jsonl">manifest rows</a></td></tr>'
        )
    table = (
        '<div class="card"><h2>Every capture run</h2>'
        '<p class="sub">One row per scheduled or manual run, newest first. The links point to the committed manifest, '
        'which is the record; the raw bodies are kept as workflow artifacts for 90 days (see Method).</p>'
        '<div class="scroll"><table><thead><tr><th>Run ID (UTC)</th><th>Trigger</th><th>First fetch (UTC)</th>'
        '<th>Last fetch (UTC)</th><th>OK</th><th>Fail</th><th>Changed</th><th>Unchanged</th><th>Source</th>'
        '</tr></thead><tbody>' + ("".join(trs) if trs else '<tr><td colspan="9" class="flag">No run has been recorded yet. Source: <a href="data/manifest.jsonl">capture/data/manifest.jsonl</a> (empty).</td></tr>')
        + "</tbody></table></div></div>"
    )
    body = f'<section class="hero"><h1>Run history</h1><p>Every capture run, with its result counts.</p></section>{table}'
    return page("Run history", "history.html", body)


def build_sources(sources: list[dict]) -> str:
    trs = []
    for s in sources:
        trs.append(
            f'<tr><td><a href="{e(s["url"])}">{e(s["name"])}</a></td><td>{e(s["publisher"])}</td>'
            f'<td>{e(s["tier"])}</td><td>{e(s["kind"])}</td><td class="mono">{e(s["marker"])}</td>'
            f'<td class="mono">{e(s["id"])}</td></tr>'
        )
    body = (
        '<section class="hero"><h1>Sources</h1><p>Every URL the capture fetches. The URL list was copied from '
        '<code>depth_lab/data/sources.json</code> (captured 2026-11-13). Tier is the publisher type recorded there; '
        'the shared <code>verify/source_audit.py</code> allow-list still classifies club domains as dataset rows (see '
        'Flagged for Review).</p></section>'
        '<div class="card"><div class="scroll"><table><thead><tr><th>Official page (link)</th><th>Publisher</th>'
        '<th>Tier</th><th>Kind</th><th>Required marker</th><th>Source ID</th></tr></thead><tbody>'
        + "".join(trs) + "</tbody></table></div></div>"
    )
    return page("Sources", "sources.html", body)


def build_method() -> str:
    body = """<section class="hero"><h1>Method</h1><p>Exactly what the capture does, and what it does not.</p></section>
<div class="card prose">
<h2>Schedule</h2>
<ul>
<li>Daily at 16:20 UTC, and at 01:20 UTC on Thursday, Friday and Saturday (UTC), which is the Wednesday, Thursday and
Friday evening in US Pacific time. The cadence is this repository's choice. It is <strong>not</strong> an NFL rule
until an NFL-published policy page is opened and cited (see Flagged for Review, C-02).</li>
<li>Manual runs are possible from the Actions tab (workflow_dispatch). Pull requests run only the offline checks; they
do not fetch anything.</li>
</ul>
<h2>What is recorded, per source, per run</h2>
<ul>
<li><strong>fetch_start_utc / fetch_end_utc</strong>: the UTC clock read before and after the request.</li>
<li><strong>http_status, final_url, content_type, bytes</strong>: what the server returned, after redirects.</li>
<li><strong>sha256</strong>: SHA-256 of the exact response body. This is the immutable fingerprint.</li>
<li><strong>marker_found</strong>: whether the required text (for example <code>Practice Status</code> for the injury
report, <code>depth</code> for a club depth page) appears in the body. A missing marker is a failure, because it means
the page changed shape or was replaced.</li>
<li><strong>table_tags, row_tags</strong>: counts of <code>&lt;table</code> and <code>&lt;tr</code> tags, shown for
structure only. They are not a parsed value.</li>
<li><strong>Structural alert</strong>: if a successful club depth capture has a zero or missing table-tag or row-tag count, the dashboard labels it
as unavailable for structured depth use and adds a per-club flag. A positive tag count is not proof that required fields,
players, positions, slots or all 32 clubs were captured.</li>
<li><strong>previous_sha256 and delta</strong>: the hash of the last <em>successful</em> capture of the same source, and
whether this capture is <code>first</code>, <code>unchanged</code>, <code>changed</code> or <code>failed</code>. If a
source failed in between, "changed" compares against the last success, so the gap is not hidden.</li>
<li><strong>result and reason</strong>: <code>ok</code>, or <code>fail</code> with every reason listed.</li>
</ul>
<h2>Failure rules (fail loudly)</h2>
<ul>
<li>Any non-200 status, any network error, any body smaller than 2,000 bytes, or any missing marker is a
<code>fail</code> row.</li>
<li>The scheduled job runs <code>capture/check.py --strict-run</code> after the manifest is committed. A failed run turns
the job red, which is the alarm. GitHub notifies the repository's workflow actors of failed scheduled runs.</li>
</ul>
<h2>Storage: what is durable and what is not</h2>
<ul>
<li><strong>Durable (in git):</strong> <code>capture/data/manifest.jsonl</code>, append-only. It holds the hashes, times,
statuses and deltas, and nothing else.</li>
<li><strong>Not durable (workflow artifact, 90 days):</strong> the raw response bodies. They are too large for git and the
brief says to keep large data out of git. A durable off-repository store for raw bodies is an owner decision and is
recorded as C-01 on Flagged for Review. Until it is made, a body older than 90 days can be checked only against its
recorded hash, not re-read.</li>
<li>The hash proves a body was the same bytes at capture time. It does not prove the page is correct, and it does not
say anything about who will play.</li>
</ul>
<h2>What this page does not do</h2>
<ul>
<li>It parses no injury, designation, depth or player value. Parsing the 32 depth tables and the injury rows into
publishable values is a separate task with its own verification (see the depth lab).</li>
<li>It does not infer a starter, a replacement or a play probability from a delta.</li>
</ul>
</div>"""
    return page("Method", "method.html", body)


FLAGS = [
    ("C-01", "Raw bodies are not durable", "Raw response bodies are workflow artifacts with 90-day retention. Only hashes are kept in git. Owner decision needed: where raw bodies live long-term.", "https://docs.github.com/en/actions/using-workflows/storing-workflow-data-as-artifacts", "GitHub Docs: artifact retention"),
    ("C-02", "The schedule is the repository's choice, not a published NFL rule", "The cadence (Wed–Fri, daily) was set by this capture. No NFL-published injury-report policy page was opened in this session that states the cadence. The NFL's page is titled 'Official Latest NFL Injury Report … Week 10' and lists games by day. It does not state a release schedule, so the schedule was not taken from it.", "https://www.nfl.com/injuries/", "NFL.com: 2026 NFL Injury Report"),
    ("C-03", "Runner egress to nfl.com and club sites is unverified", "The sandbox that wrote this capture cannot reach nfl.com (HTTP 000 from curl). The first real capture happens on a GitHub runner. If a publisher blocks runners, the job fails loudly; it is not replaced by a copy.", "https://github.com/karagemop466-tech/Korea3/blob/main/.github/workflows/capture.yml", "This repository: capture workflow"),
    ("C-04", "Injury report page is still titled Week 10 on the capture date", "On 2026-11-15 (UTC) the NFL page is titled 'Injuries - WEEK 10' and lists games dated Thursday 12 November and Sunday 15 November 2026. No Week 11 page was visible in this session. Captures will show this as 'unchanged' or 'changed' bytes, not as a week change, until the page moves.", "https://www.nfl.com/injuries/", "NFL.com: 2026 NFL Injury Report"),
    ("C-05", "Club pages are not all the same shape", "The capture checks HTTP status, body size, hash and a broad text marker; it does not validate page semantics. A zero or missing table-tag or row-tag count on a successful depth capture now triggers a per-club structural alert below. Positive tag counts remain diagnostics only and do not establish that player names, slots or values were captured correctly.", "https://github.com/karagemop466-tech/Korea3/blob/main/depth_lab/flagged.html", "This repository: depth_lab/flagged.html"),
    ("C-06", "Shared source-audit allow-list classifies club domains as dataset", "verify/source_audit.py does not admit club domains as official. Left unchanged here. This is the owner question already recorded in depth_lab (Q15/S13).", "https://github.com/karagemop466-tech/Korea3/blob/main/depth_lab/sources.html", "This repository: depth_lab/sources.html"),
    ("C-07", "GitHub may pause scheduled workflows in a quiet repository", "Scheduled workflows can be disabled after a period without repository activity. The daily capture commits to main, which counts as activity, but this has not been observed in this repository and is recorded as a risk to watch.", "https://docs.github.com/en/actions/using-workflows/events-that-trigger-workflows#schedule", "GitHub Docs: schedule event"),
]


def build_flagged(sources: list[dict] | None = None, rows: list[dict] | None = None) -> str:
    if sources is None:
        sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    if rows is None:
        rows = load_manifest()
    trs = []
    for fid, title, text, url, label in FLAGS:
        trs.append(f'<tr id="{e(fid)}"><td class="mono">{e(fid)}</td><td><strong>{e(title)}</strong><div class="sub">{e(text)}</div></td>'
                   f'<td><a href="{e(url)}">{e(label)}</a></td><td class="flag">unverified / open</td></tr>')
    for alert in structural_alerts(sources, rows):
        source = alert["source"]
        latest = alert["latest"] or {}
        latest_digest = (latest.get("sha256") or "")[:16]
        if latest.get("result") == "ok":
            latest_shape = (
                f'Latest successful capture {e(latest.get("run_id", ""))} at '
                f'{e(latest.get("fetch_end_utc", ""))}: HTTP {e(latest.get("http_status", ""))}, '
                f'{e(latest.get("table_tags", "blank"))} table tags, {e(latest.get("row_tags", "blank"))} row tags, '
                f'SHA-256 prefix {e(latest_digest)}.'
            )
        elif latest:
            latest_shape = (
                f'Latest attempt {e(latest.get("run_id", ""))} at {e(latest.get("fetch_end_utc", ""))} '
                'did not yield a successful capture; its structure is not assessed.'
            )
        else:
            latest_shape = 'No latest capture row is available.'
        title = f'{source.get("club", source["id"])} depth source has no verified structured data'
        text = (
            f'A positive table-tag AND row-tag count was not observed in {alert["missing_count"]} of '
            f'{alert["successful_count"]} successful raw capture(s). {latest_shape} '
            'This is a raw HTML diagnostic, not a statement about the depth values published by the club. '
            'The hash/HTTP result does not establish a parseable chart. Keep player, position and slot values blank; '
            'do not transcribe an image or infer depth. Gate to clear: identify an authorized structured source and '
            'validate its required fields before using this club in a depth feature.'
        )
        source_links = (
            f'<a href="{e(source["url"])}">Official club depth page</a><br>'
            f'<a href="{REPO_BLOB}">Captured manifest evidence</a><br>'
            '<a href="https://github.com/karagemop466-tech/Korea3/blob/main/depth_lab/flagged.html">Depth Lab review notes</a>'
        )
        trs.append(
            f'<tr id="{e(alert["id"])}"><td class="mono">{e(alert["id"])}</td>'
            f'<td><strong>{e(title)}</strong><div class="sub">{e(text)}</div></td>'
            f'<td>{source_links}</td><td class="flag">blocked for structured use; raw capture retained</td></tr>'
        )
    body = (
        '<section class="hero"><h1>Flagged for Review</h1>'
        '<p>Irregularities and limits calculated from the manifest. A raw HTTP/hash success is not proof that a page '
        'contains complete, usable or correctly parsed data. Some flags block use of that source as structured evidence; '
        'they do not block retaining the raw response hash.</p></section>'
        '<div class="card"><div class="scroll"><table><thead><tr><th>ID</th><th>Irregularity</th><th>Official source / evidence</th>'
        '<th>Status</th></tr></thead><tbody>' + "".join(trs) + "</tbody></table></div></div>"
    )
    return page("Flagged for Review", "flagged.html", body)


def main() -> int:
    sources = json.loads(SOURCES.read_text(encoding="utf-8"))["sources"]
    rows = load_manifest()
    outputs = {
        "index.html": build_index(sources, rows),
        "history.html": build_history(rows),
        "sources.html": build_sources(sources),
        "method.html": build_method(),
        "flagged.html": build_flagged(sources, rows),
    }
    for name, text in outputs.items():
        (HERE / name).write_text(text, encoding="utf-8")
    print(f"built {len(outputs)} pages from {len(rows)} manifest rows and {len(sources)} sources")
    return 0


if __name__ == "__main__":
    sys.exit(main())
