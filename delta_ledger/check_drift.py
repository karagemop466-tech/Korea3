#!/usr/bin/env python3
"""The drift alarm: fail loudly when a captured page stops looking like the page it claims to be.

The brief:

  "Add a drift alarm to every scraper. Pin each parser to expected row counts and required fields;
   fail the build loudly when a field goes missing rather than publishing a blank."

Why a second script next to `capture/check.py`, which already exists and passes: `capture/check.py`
validates the *record* -- manifest schema, that a delta label matches the previous hash, that an ok row
has HTTP 200, a 64-hex hash, a body over the size floor and the required marker string. Those are the
right checks for a byte capture, and nothing in `capture/` parses a value, so nothing there can see a
table disappear. On 2026-11-18 22:58 UTC the official injury report returned 28 row tags against 375
in the two runs before it, and every one of those checks passed: the page still contained the marker
"Practice Status" and was still a 200 over the size floor.

This script adds the missing comparison, and does it with the single shared rule in `drift.py` so the
published page and the alarm cannot disagree about what counts as a break. The band is recomputed from
the manifest every run and compared against the committed pins: a pin that no longer matches the history
it was derived from is treated as an unauthorised edit, not as policy.

Modes
  python3 delta_ledger/check_drift.py        offline: pins vs manifest, drift events, page consistency
  python3 delta_ledger/check_drift.py --ci   the above, plus the age of the newest capture against the
                                             clock. Only CI should use --ci: a sandbox where nothing is
                                             scheduled would alarm on itself and teach nobody anything.
Exit 0 only when nothing breaches. Every failure line names the source, the number and the file.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import drift as D  # noqa: E402  the same rule the published page uses, not a copy of it

MANIFEST = ROOT / "capture" / "data" / "manifest.jsonl"
PINS = HERE / "data" / "pins.json"
LEDGER = HERE / "data" / "ledger.json"
FRESH_MAX_H = 30.0


def ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--ci", action="store_true", help="also check the age of the newest capture against the clock")
    ap.add_argument("--max-age-hours", type=float, default=FRESH_MAX_H)
    args = ap.parse_args(argv)

    problems: list[str] = []
    events: list[dict] = []

    if not MANIFEST.exists():
        print(f"FAIL manifest missing: {MANIFEST}")
        return 1
    rows = [json.loads(line) for line in MANIFEST.read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        print("DRIFT ALARM FAIL: the manifest is empty -- no capture has ever run")
        return 1
    if not PINS.exists():
        print("DRIFT ALARM FAIL: delta_ledger/data/pins.json is missing; run delta_ledger/readback.py")
        return 1
    pin_doc = json.loads(PINS.read_text(encoding="utf-8"))
    pins = pin_doc["sources"]
    ledger = json.loads(LEDGER.read_text(encoding="utf-8")) if LEDGER.exists() else None

    bysrc: dict[str, list[dict]] = {}
    for r in rows:
        bysrc.setdefault(r["source_id"], []).append(r)
    for sid in bysrc:
        bysrc[sid].sort(key=lambda r: r["fetch_start_utc"])

    if set(pins) != set(bysrc):
        problems.append(f"pins cover {len(pins)} sources, the manifest has {len(bysrc)}: "
                        f"symmetric difference {sorted(set(pins) ^ set(bysrc))}")

    for sid, series in sorted(bysrc.items()):
        pin = pins.get(sid)
        tags = [float(r["row_tags"] or 0) for r in series]
        band = D.band_from(tags, tol=float(pin_doc.get("tolerance", D.BAND_TOL)),
                          min_runs=int(pin.get("min_runs", pin_doc.get("min_runs", D.MIN_RUNS_FOR_BAND))))
        if not pin:
            problems.append(f"{sid}: no pin entry in delta_ledger/data/pins.json")
            continue
        # Recompute, never trust: a pin that disagrees with the manifest is an edit, and an unannounced
        # edit of a threshold is how a gate becomes decorative.
        if pin["state"] != band["state"]:
            problems.append(f"{sid}: pinned state '{pin['state']}' but the manifest history says "
                            f"'{band['state']}' ({len(tags)} runs)")
        elif band["state"] == "pinned":
            for k in ("median", "lo", "hi"):
                if abs(float(band[k]) - float(pin[k])) > 1e-9:
                    problems.append(f"{sid}: pinned {k} = {pin[k]} != {band[k]} recomputed from the manifest "
                                     f"(re-run delta_ledger/readback.py)")
        if band["state"] == "insufficient":
            problems.append(f"{sid}: only {band['n_runs']} runs, so no band is asserted and no alarm is "
                             f"claimed for this source yet")
            continue
        if pin["state"] == "no-structure" and any(t > 0 for t in tags):
            problems.append(f"{sid}: pinned as no-structure but a run found {max(tags):.0f} rows -- the source "
                             f"changed shape, which is what this alarm exists to notice")
        for e in D.drift_events(series, band):
            e["source_id"] = sid
            events.append(e)

    if ledger:
        covered = {s["source_id"] for s in ledger["sources"]}
        missing = sorted(set(pins) - covered)
        if missing:
            problems.append(f"ledger.json does not cover {missing}; re-run delta_ledger/readback.py")
        published = {D.key(e) for e in ledger.get("drift_events", [])}
        now = {D.key(e) for e in events}
        if published != now:
            problems.append("the published drift-event set and the alarm disagree "
                            f"(only on the page: {sorted(published - now)[:4]}; "
                            f"only from the alarm: {sorted(now - published)[:4]})")
        if ledger["_meta"].get("drift_events_total") != len(now):
            problems.append(f"ledger.json counts {ledger['_meta'].get('drift_events_total')} drift events, "
                            f"the alarm finds {len(now)}")

    if args.ci:
        newest = max(ts(r["fetch_end_utc"]) for r in rows)
        age = (datetime.now(timezone.utc) - newest).total_seconds() / 3600.0
        if age > args.max_age_hours:
            problems.append(f"freshness: the newest capture is {age:.1f}h old, over the "
                            f"{args.max_age_hours:.0f}h limit. Either the schedule stopped, or it ran and "
                            f"crashed before writing a row.")
        print(f"freshness: newest capture {newest.strftime('%Y-%m-%dT%H:%M:%SZ')}, age {age:.1f}h "
              f"(limit {args.max_age_hours:.0f}h)")

    for e in events:
        row = next(r for r in bysrc[e["source_id"]] if r["run_id"] == e["run_id"])
        print(f"DRIFT {e['source_id']}: {e['run_id']} ({row['fetch_start_utc']}) {e['detail']}; "
              f"the capture recorded result={row['result']} and capture/check.py passed it, because nothing "
              f"in that check looks at row counts")
    for prob in problems:
        print("FAIL", prob)

    if events or problems:
        print(f"drift alarm FAILED: {len(events)} drift event(s), {len(problems)} consistency problem(s)")
        print("The alarm is the deliverable. A capture that keeps reporting 'ok' while a table vanishes is "
              "worse than no capture, because it is trusted.")
        return 1
    print(f"drift alarm PASS: {len(rows)} manifest rows, {len(bysrc)} sources, "
          f"{len({r['run_id'] for r in rows})} runs, latest {max(r['run_id'] for r in rows)}, "
          f"0 drift events, 0 consistency problems"
          + ("" if args.ci else " (age check skipped: offline mode never reads the clock)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
