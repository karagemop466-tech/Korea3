#!/usr/bin/env python3
"""Fail-closed consistency gate for the read-back desk.

This gate does NOT assert that the capture is healthy -- the capture is not healthy, and
check_drift.py says so on purpose. This file asserts that what this desk *publishes* is what the
record says, which is a different claim and must not be conflated with it:

  1. every page equals a fresh in-memory build of the committed ledger.json and pins.json;
  2. ledger.json and pins.json are reproducible from capture/data/manifest.jsonl and
     capture/data/sources.json (recomputed into a temp tree and compared byte for byte), so a
     published count can never be stale relative to the manifest it claims to read back;
  3. the drift-event set published on the page equals the set the alarm recomputes (shared rule),
     and the alarm's exit code is the one the page predicts: if the page says two events, the
     alarm must exit 1 and print two DRIFT lines;
  4. every table row links something, every blank links the flag page, every internal href resolves;
  5. coverage arithmetic: rows_total = runs x sources for the runs present, and the per-source run
     counts sum to the same total.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import build as B  # noqa: E402
import drift as D  # noqa: E402

PAGES = ["index.html", "runs.html", "sources.html", "drift.html", "gates.html", "method.html", "flagged.html"]


def alarm_events(ledger_rows, pins_doc):
    pins = pins_doc["sources"]
    bysrc: dict[str, list[dict]] = {}
    for r in ledger_rows:
        bysrc.setdefault(r["source_id"], []).append(r)
    out = []
    for sid, series in sorted(bysrc.items()):
        series.sort(key=lambda r: r["fetch_start_utc"])
        band = D.band_from([float(r["row_tags"] or 0) for r in series],
                           tol=float(pins_doc.get("tolerance", D.BAND_TOL)),
                           min_runs=int(pins.get(sid, {}).get("min_runs", D.MIN_RUNS_FOR_BAND)))
        for e in D.drift_events(series, band):
            e["source_id"] = sid
            out.append(D.key(e))
    return set(out)


def main() -> int:
    problems: list[str] = []
    led = B.load("ledger.json")
    pins = B.load("pins.json")

    # 1 -- renderers are pure
    rebuilt = {
        "index.html": B.build_index(led, pins),
        "runs.html": B.build_runs(led),
        "sources.html": B.build_sources(led, pins),
        "drift.html": B.build_drift(led),
        "gates.html": B.build_gates(led),
        "method.html": B.build_method(led, pins),
        "flagged.html": B.build_flagged(led),
    }
    for name, text in rebuilt.items():
        path = HERE / name
        if not path.exists():
            problems.append(f"page missing: delta_ledger/{name}")
        elif path.read_text(encoding="utf-8") != text:
            problems.append(f"delta_ledger/{name} differs from a fresh build of the committed data: "
                            f"run python3 delta_ledger/build.py and commit")
    extra = sorted(p.name for p in HERE.glob("*.html") if p.name not in PAGES)
    if extra:
        problems.append(f"pages not in the build list: {extra}")

    # 2 -- the data is reproducible from the manifest
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        env = {"PATH": "/usr/bin:/bin", "DELTA_LEDGER_OUT": str(tdp)}
        r = subprocess.run([sys.executable, str(HERE / "readback.py")], env=env, capture_output=True,
                           text=True, cwd=str(ROOT))
        if r.returncode != 0:
            problems.append(f"readback.py exited {r.returncode}: {r.stderr.strip()[:300]}")
        for name in ["ledger.json", "pins.json"]:
            new = tdp / name
            if not new.exists():
                problems.append(f"recompute produced no {name} (readback.py ignored DELTA_LEDGER_OUT)")
                continue
            if new.read_bytes() != (HERE / "data" / name).read_bytes():
                problems.append(f"delta_ledger/data/{name} is not reproducible from the manifest: the capture "
                                f"moved and the pages did not. Run readback.py then build.py.")

    # 3 -- page and alarm must agree about the event set
    manifest = ROOT / "capture" / "data" / "manifest.jsonl"
    rows = [json.loads(l) for l in manifest.read_text(encoding="utf-8").splitlines() if l.strip()]
    now = alarm_events(rows, pins)
    published = {D.key({**e, "source_id": e.get("source_id", "")}) for e in led.get("drift_events", [])}
    if now != published:
        problems.append(f"published drift events {sorted(published - now)} vs alarm {sorted(now - published)}")
    if led["_meta"].get("drift_events_total") != len(now):
        problems.append(f'drift_events_total says {led["_meta"].get("drift_events_total")}, the rule finds {len(now)}')

    # 4 -- link discipline
    for name in PAGES:
        text = (HERE / name).read_text(encoding="utf-8")
        body_rows = [r for r in re.findall(r"<tr>(.*?)</tr>", text, re.S) if "<td" in r]
        for i, r in enumerate(body_rows):
            if "href=" not in r:
                problems.append(f"{name}: table row {i + 1} has no link")
        for m in re.finditer(r"\[blank\]", text):
            if 'href="flagged.html"' not in text[m.end():m.end() + 400]:
                problems.append(f"{name}: a [blank] marker at offset {m.start()} does not link the flag page")
        for m in re.finditer(r'href="([^"#]+)(?:#[^"]*)?"', text):
            href = m.group(1)
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            if not (HERE / href).resolve().exists():
                problems.append(f"{name}: broken internal link {href}")

    # 5 -- coverage arithmetic
    runs = {r["run_id"] for r in rows}
    per_run = {rid: sum(1 for r in rows if r["run_id"] == rid) for rid in runs}
    if led["coverage"]["rows_total"] != len(rows):
        problems.append('coverage.rows_total disagrees with the manifest')
    if sorted(per_run.values()) != sorted(led["coverage"]["sources_per_run"]):
        problems.append(f'coverage.sources_per_run {led["coverage"]["sources_per_run"]} != actual {sorted(per_run.values())}')
    summed = sum(s["n_runs"] for s in led["sources"])
    if summed != len(rows):
        problems.append(f"per-source run counts sum to {summed}, the manifest has {len(rows)} rows")
    for s in led["sources"]:
        if len(s["runs"]) != s["n_runs"] or len(s["row_tags"]) != s["n_runs"]:
            problems.append(f'{s["source_id"]}: run lists disagree with n_runs')
    return_ = subprocess.run([sys.executable, str(HERE / "check_drift.py")], capture_output=True, text=True,
                             cwd=str(ROOT))
    drift_lines = [l for l in return_.stdout.splitlines() if l.startswith("DRIFT")]
    if len(drift_lines) != len(now):
        problems.append(f"the alarm printed {len(drift_lines)} DRIFT lines for {len(now)} events")
    if now and return_.returncode == 0:
        problems.append("the alarm exited 0 while events exist: the loud part of the deliverable is not loud")
    if not now and return_.returncode != 0:
        problems.append("the alarm exited non-zero with no events: it is alarming on something else")

    if problems:
        for p in problems:
            print("FAIL", p)
        print(f"delta_ledger check FAILED: {len(problems)} problem(s)")
        return 1
    print(f"delta_ledger check PASS: {len(PAGES)} pages, {len(rows)} manifest rows read back, "
          f"{len(runs)} runs, {len(now)} drift event(s) published and confirmed by the alarm, "
          f"links and blanks consistent")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
