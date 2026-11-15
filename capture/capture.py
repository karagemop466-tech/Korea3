#!/usr/bin/env python3
"""Scheduled capture of official availability pages: raw bytes, SHA-256, UTC clock time.

What it does, and nothing more:

* fetches every URL in capture/data/sources.json (or --sources FILE) once;
* writes the raw response body to <out>/<run_id>/<source_id>.bin (kept as a workflow
  artifact, NOT committed, because the bodies are large);
* appends one JSON line per source to capture/data/manifest.jsonl (committed, append-only):
  run id, fetch time (UTC, start and end), final URL after redirects, HTTP status, byte count,
  SHA-256 of the body, the previous successful hash for the same source, and a delta label
  (first / unchanged / changed / failed);
* checks a required marker string per source. A missing marker, a non-200 status, or a body
  smaller than MIN_BYTES is recorded as result=fail with the reason. Nothing is silently
  dropped and nothing is parsed into a published value.

The delta is computed on bytes, never on what the page says. The page built from the
manifest publishes "changed / unchanged since the previous capture" and the hashes, not the
injury or depth values themselves.

Exit status: 0 whenever the run completed and wrote its manifest rows, even if some sources
failed (the failures are the record). capture/check.py --strict-run turns a failed run into a
red job. Only an unexpected crash exits non-zero here.

Standard library only. No randomness; the clock is read once per fetch and is the only
non-deterministic input, which is the point of a capture.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_SOURCES = HERE / "data" / "sources.json"
MANIFEST = HERE / "data" / "manifest.jsonl"

MIN_BYTES = 2000
TIMEOUT_S = 45
PAUSE_S = 2.0
USER_AGENT = (
    "Korea3-capture/1.0 (read-only official-page snapshot; "
    "https://karagemop466-tech.github.io/Korea3/capture/)"
)
MANIFEST_KEYS = [
    "run_id", "run_trigger", "source_id", "url", "final_url", "publisher", "tier",
    "fetch_start_utc", "fetch_end_utc", "http_status", "content_type", "bytes", "sha256",
    "marker", "marker_found", "table_tags", "row_tags", "previous_sha256", "delta", "result",
    "reason",
]


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_manifest(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def previous_ok_hash(rows: list[dict], source_id: str) -> str | None:
    """SHA-256 of the most recent successful capture of this source, or None."""
    for row in reversed(rows):
        if row["source_id"] == source_id and row["result"] == "ok":
            return row["sha256"]
    return None


def fetch(url: str) -> tuple[int | None, str, str, bytes, str]:
    """Return (status, final_url, content_type, body, error). Never raises for HTTP errors."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:  # noqa: S310 - https only, from sources.json
            body = resp.read()
            return resp.status, resp.geturl(), resp.headers.get("Content-Type", ""), body, ""
    except urllib.error.HTTPError as exc:
        return exc.code, url, exc.headers.get("Content-Type", "") if exc.headers else "", b"", f"HTTP {exc.code}"
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return None, url, "", b"", f"{type(exc).__name__}: {exc}"


def run(sources_path: Path, out_root: Path, manifest_path: Path, run_id: str, trigger: str,
        only: set[str] | None, pause: float) -> int:
    doc = json.loads(sources_path.read_text(encoding="utf-8"))
    sources = doc["sources"]
    if only:
        sources = [s for s in sources if s["id"] in only]
    run_dir = out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    prior = load_manifest(manifest_path)
    counts = {"ok": 0, "fail": 0}
    new_rows = []
    for i, src in enumerate(sources):
        if i and pause:
            time.sleep(pause)
        start = utc_now()
        status, final_url, ctype, body, err = fetch(src["url"])
        end = utc_now()
        digest = hashlib.sha256(body).hexdigest() if body else None
        marker = src.get("marker", "")
        text = body.decode("utf-8", errors="replace") if body else ""
        marker_found = bool(marker) and marker.lower() in text.lower()
        reasons = []
        if err:
            reasons.append(err)
        if status is not None and status != 200:
            reasons.append(f"non-200 status {status}")
        if status == 200 and len(body) < MIN_BYTES:
            reasons.append(f"body {len(body)} bytes is below the {MIN_BYTES}-byte floor")
        if status == 200 and not marker_found:
            reasons.append(f"required marker '{marker}' not found: possible schema or page change")
        result = "ok" if not reasons else "fail"
        prev = previous_ok_hash(prior + new_rows, src["id"])
        if result == "fail":
            delta = "failed"
        elif prev is None:
            delta = "first"
        else:
            delta = "unchanged" if prev == digest else "changed"
        if body:
            (run_dir / f"{src['id']}.bin").write_bytes(body)
        row = {
            "run_id": run_id, "run_trigger": trigger, "source_id": src["id"], "url": src["url"],
            "final_url": final_url, "publisher": src["publisher"], "tier": src["tier"],
            "fetch_start_utc": start, "fetch_end_utc": end, "http_status": status,
            "content_type": ctype, "bytes": len(body), "sha256": digest, "marker": marker,
            "marker_found": marker_found, "table_tags": text.lower().count("<table"),
            "row_tags": text.lower().count("<tr"), "previous_sha256": prev, "delta": delta,
            "result": result, "reason": "; ".join(reasons),
        }
        assert list(row) == MANIFEST_KEYS, "manifest schema drift in capture.py"
        new_rows.append(row)
        counts[result] += 1
        print(f"{src['id']:<22} {result:<4} {delta:<9} http={status} bytes={len(body)} "
              f"sha256={(digest or '-')[:12]} {('; '.join(reasons))}")
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    with manifest_path.open("a", encoding="utf-8") as fh:
        for row in new_rows:
            fh.write(json.dumps(row, sort_keys=True) + "\n")
    (run_dir / "run.json").write_text(json.dumps({
        "run_id": run_id, "run_trigger": trigger, "sources": len(sources),
        "ok": counts["ok"], "fail": counts["fail"],
        "changed": sum(1 for r in new_rows if r["delta"] == "changed"),
        "unchanged": sum(1 for r in new_rows if r["delta"] == "unchanged"),
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"run {run_id}: {counts['ok']} ok, {counts['fail']} fail, "
          f"{len(sources)} sources, manifest +{len(new_rows)} rows")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sources", type=Path, default=DEFAULT_SOURCES)
    ap.add_argument("--out", type=Path, default=HERE.parent / "capture_out")
    ap.add_argument("--manifest", type=Path, default=MANIFEST)
    ap.add_argument("--run-id", default=os.environ.get("CAPTURE_RUN_ID") or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    ap.add_argument("--trigger", default=os.environ.get("CAPTURE_TRIGGER", "manual"))
    ap.add_argument("--only", default="", help="comma-separated source ids (testing only)")
    ap.add_argument("--pause", type=float, default=PAUSE_S)
    args = ap.parse_args(argv)
    only = {s for s in args.only.split(",") if s} or None
    return run(args.sources, args.out, args.manifest, args.run_id, args.trigger, only, args.pause)


if __name__ == "__main__":
    sys.exit(main())
