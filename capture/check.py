#!/usr/bin/env python3
"""Fail-closed checks for the capture.

Offline checks (run on every pull request and every push):
  1. every manifest line is valid JSON with exactly the agreed keys;
  2. every row names a source that exists in capture/data/sources.json, with the same URL and tier;
  3. every ok row has a 64-hex SHA-256, a non-empty body and a status of 200;
  4. every fail row has a reason; every ok row has an empty reason;
  5. delta labels are consistent with the previous successful hash of the same source;
  6. each source's URL is https and the host is one of the hosts named in sources.json;
  7. successful rows carry valid non-negative HTML tag counts;
  8. the built pages exist, contain a link to every configured source, and publish a visible,
     official-source-linked warning for any successful depth capture with a zero or missing table-tag or row-tag count;
  9. the page builder is deterministic: rebuilding in memory gives the committed HTML.

Strict run check (scheduled jobs, after the capture wrote its rows):
  python3 capture/check.py --strict-run <run_id>
  exits non-zero if any raw fetch row of that run has result=fail. Structural warnings are
  printed separately and block use as structured depth evidence; a successful hash is not a parsed chart.

Exit 0 only when every check passes. Failures are listed one per line.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import build  # noqa: E402  (same directory; deterministic page builder)

MANIFEST_KEYS = {
    "run_id", "run_trigger", "source_id", "url", "final_url", "publisher", "tier",
    "fetch_start_utc", "fetch_end_utc", "http_status", "content_type", "bytes", "sha256",
    "marker", "marker_found", "table_tags", "row_tags", "previous_sha256", "delta", "result",
    "reason",
}
HEX64 = re.compile(r"^[0-9a-f]{64}$")
UTC = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
OFFICIAL_TIERS = {"official-league", "official-club"}


def check_all(strict_run: str | None) -> list[str]:
    problems: list[str] = []
    sources_doc = json.loads(build.SOURCES.read_text(encoding="utf-8"))
    sources = {s["id"]: s for s in sources_doc["sources"]}
    if len(sources) != len(sources_doc["sources"]):
        problems.append("duplicate source id in sources.json")
    for s in sources.values():
        if not s["url"].startswith("https://"):
            problems.append(f"{s['id']}: url is not https")
        if s["tier"] not in OFFICIAL_TIERS:
            problems.append(f"{s['id']}: tier '{s['tier']}' is not an official tier")

    rows: list[dict] = []
    if build.MANIFEST.exists():
        for n, line in enumerate(build.MANIFEST.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError as exc:
                problems.append(f"manifest line {n}: not JSON ({exc})")
                continue
            rows.append(row)
            if set(row) != MANIFEST_KEYS:
                problems.append(f"manifest line {n}: keys differ by {sorted(set(row) ^ MANIFEST_KEYS)}")
                continue
            sid = row["source_id"]
            if sid not in sources:
                problems.append(f"manifest line {n}: unknown source '{sid}'")
                continue
            src = sources[sid]
            if row["url"] != src["url"] or row["tier"] != src["tier"]:
                problems.append(f"manifest line {n}: url or tier differs from sources.json for '{sid}'")
            for key in ("table_tags", "row_tags"):
                value = row[key]
                if value is not None and (not isinstance(value, int) or isinstance(value, bool) or value < 0):
                    problems.append(f"manifest line {n}: {key} must be a non-negative integer or blank")
                if row["result"] == "ok" and value is None:
                    problems.append(f"manifest line {n}: successful row has no {key} diagnostic")
            for key in ("fetch_start_utc", "fetch_end_utc"):
                if not UTC.match(row[key] or ""):
                    problems.append(f"manifest line {n}: {key} is not a UTC timestamp")
            if row["result"] not in ("ok", "fail"):
                problems.append(f"manifest line {n}: result must be ok or fail")
            if row["delta"] not in ("first", "unchanged", "changed", "failed"):
                problems.append(f"manifest line {n}: delta '{row['delta']}' is not allowed")
            if row["result"] == "ok":
                if row["http_status"] != 200:
                    problems.append(f"manifest line {n}: ok row without HTTP 200")
                if not HEX64.match(row["sha256"] or ""):
                    problems.append(f"manifest line {n}: ok row without a SHA-256")
                if not row["bytes"] or row["bytes"] < 2000:
                    problems.append(f"manifest line {n}: ok row with an empty or undersized body")
                if not row["marker_found"]:
                    problems.append(f"manifest line {n}: ok row whose marker was not found")
                if row["reason"]:
                    problems.append(f"manifest line {n}: ok row carries a reason")
            else:
                if not row["reason"]:
                    problems.append(f"manifest line {n}: fail row without a reason")
            host = urlparse(row["url"]).hostname or ""
            if not row["url"].startswith("https://") or not host:
                problems.append(f"manifest line {n}: non-https or hostless url")

    # delta consistency: replay the manifest in order
    last_ok: dict[str, str] = {}
    for n, row in enumerate(rows, 1):
        if set(row) != MANIFEST_KEYS or row["source_id"] not in sources:
            continue
        sid = row["source_id"]
        expected_prev = last_ok.get(sid)
        if row["previous_sha256"] != expected_prev:
            problems.append(f"manifest row {n} ({sid}): previous_sha256 does not match the last ok capture")
        if row["result"] == "fail":
            if row["delta"] != "failed":
                problems.append(f"manifest row {n} ({sid}): fail row must have delta 'failed'")
        else:
            want = "first" if expected_prev is None else ("unchanged" if expected_prev == row["sha256"] else "changed")
            if row["delta"] != want:
                problems.append(f"manifest row {n} ({sid}): delta is '{row['delta']}', expected '{want}'")
            last_ok[sid] = row["sha256"]

    if strict_run is not None:
        run_rows = [r for r in rows if r.get("run_id") == strict_run]
        if not run_rows:
            problems.append(f"strict run {strict_run}: no manifest rows were written")
        for r in run_rows:
            if r.get("result") != "ok":
                problems.append(f"strict run {strict_run}: {r['source_id']} failed: {r.get('reason')}")
        if run_rows and len(run_rows) != len(sources):
            problems.append(f"strict run {strict_run}: {len(run_rows)} rows for {len(sources)} sources")

    # pages: deterministic rebuild equals committed; every source linked
    rebuilt = {
        "index.html": build.build_index(list(sources.values()), rows),
        "history.html": build.build_history(rows),
        "sources.html": build.build_sources(list(sources.values())),
        "method.html": build.build_method(),
        "flagged.html": build.build_flagged(list(sources.values()), rows),
    }
    for name, text in rebuilt.items():
        path = HERE / name
        if not path.exists():
            problems.append(f"page missing: capture/{name} (run capture/build.py)")
            continue
        if path.read_text(encoding="utf-8") != text:
            problems.append(f"capture/{name} differs from a fresh build: run capture/build.py and commit")
    index = (HERE / "index.html").read_text(encoding="utf-8") if (HERE / "index.html").exists() else ""
    for sid, src in sources.items():
        if f'href="{src["url"]}"' not in index:
            problems.append(f"dashboard has no official link for '{sid}'")

    # A successful raw capture with no table/row tags is not parseable depth evidence.
    # It remains a successful hash capture, but the warning must be visible and source-linked.
    flagged = (HERE / "flagged.html").read_text(encoding="utf-8") if (HERE / "flagged.html").exists() else ""
    for alert in build.structural_alerts(list(sources.values()), rows):
        aid = alert["id"]
        src = alert["source"]
        if f'id="{aid}"' not in flagged:
            problems.append(f"structural alert '{aid}' is not published on capture/flagged.html")
        if f'href="{src["url"]}"' not in flagged:
            problems.append(f"structural alert '{aid}' has no direct official-source link")
        if f'href="{build.REPO_BLOB}"' not in flagged:
            problems.append(f"structural alert '{aid}' has no captured-manifest evidence link")
        if f'href="flagged.html#{aid}"' not in index:
            problems.append(f"dashboard does not link to structural alert '{aid}'")
        latest_row = alert.get("latest") or {}
        if latest_row.get("run_id") and latest_row["run_id"] not in flagged:
            problems.append(f"structural alert '{aid}' does not identify its latest capture run")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--strict-run", default=None, help="fail if any row of this run id is not ok")
    args = ap.parse_args(argv)
    sources_doc = json.loads(build.SOURCES.read_text(encoding="utf-8"))
    structural = build.structural_alerts(sources_doc["sources"], build.load_manifest())
    for alert in structural:
        source = alert["source"]
        print(
            f"NOTICE {alert['id']}: {source.get('club', source['id'])} has a zero or missing table-tag or row-tag count in "
            f"{alert['missing_count']} of {alert['successful_count']} successful raw capture(s); "
            "do not use as structured depth evidence."
        )
    problems = check_all(args.strict_run)
    if problems:
        for p in problems:
            print("FAIL", p)
        print(f"capture check FAILED: {len(problems)} problem(s)")
        return 1
    if structural:
        print(f"capture check PASS: raw manifest and pages are consistent; {len(structural)} structural-depth warning(s) published and blocked from structured use")
    else:
        print("capture check PASS: manifest, delta chain, sources, pages and links all consistent")
    return 0


if __name__ == "__main__":
    sys.exit(main())
