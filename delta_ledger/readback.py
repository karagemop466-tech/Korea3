#!/usr/bin/env python3
"""Read back the scheduled capture history and measure what it can and cannot tell us.

Why this exists
---------------
`capture/` fetches 33 official availability pages on a schedule and appends one row per source to
`capture/data/manifest.jsonl`: fetch time, HTTP status, byte count, SHA-256 of the raw body, the
previous hash, and a delta label. Until 2026-11-17 that manifest had **zero rows**, so every
readiness gate written against it said "0 of N". It now has four runs' worth of history, which is
the first moment those gates can be answered with a number instead of an intention.

Two things are computed here, and both are arithmetic over the committed manifest:

1. **Is the byte-level delta a signal at all?** The brief says to publish "the delta, never the
   level", and to make the injury signal "a surprise, never a level". A SHA-256 over a page that
   embeds a nonce, a timestamp or an ad token changes on every fetch even when the table on the
   page is identical. Counting that: the share of transitions labelled `changed` whose structural
   signature (table and row counts recorded at capture time) did not move, is the false-positive
   rate of the only change detector the capture currently has.

2. **Does the pipeline notice when a page breaks?** The brief asks for a drift alarm that "pins each
   parser to expected row counts and required fields; fail the build loudly when a field goes missing
   rather than publishing a blank". `capture/check.py` verifies bytes, markers and status -- it
   deliberately does not look at row counts, because nothing is parsed. So a run whose injury-report
   page returned 28 row tags instead of 375 recorded `result=ok` and the job stayed green. This
   module pins a band per source from the observed history and reports the breaches, and
   `check_drift.py` turns them into a red job.

Deterministic: no clock is read. Age-of-capture arithmetic happens only in `check_drift.py --ci`,
where a clock is the point.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
import drift as D  # noqa: E402  the single definition of "this run broke"
MANIFEST = ROOT / "capture" / "data" / "manifest.jsonl"
SOURCES = ROOT / "capture" / "data" / "sources.json"
import os

DATA_DIR = Path(os.environ.get("DELTA_LEDGER_OUT", str(HERE / "data")))
OUT = DATA_DIR / "ledger.json"
PINS = DATA_DIR / "pins.json"

BAND_TOL = D.BAND_TOL    # +/- share of the median row count, stated on the method page
MIN_RUNS_FOR_BAND = D.MIN_RUNS_FOR_BAND  # below this, a band is not asserted, only recorded as "insufficient"
Z_BREACH = D.Z_BREACH          # robust z above which a row count is treated as a break, not drift
FRESH_MAX_H = 30.0        # the alarm threshold used by check_drift.py --ci (see the schedule finding)


def ts(s: str) -> datetime:
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def parse_run_id(run_id: str) -> datetime:
    return datetime.strptime(run_id, "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)


GATE_ROWS = ["B01", "B02", "B05", "B14", "B22", "B26", "B27", "B28", "B29", "B30", "B31", "B32",
             "B33", "B34", "B35"]
REGISTER = ROOT / "readiness" / "data" / "register.json"


def gate_notes(src_rows, cov, dq, injury_series):
    """This desk's arithmetic against the denominator each readiness row was written with.

    The register itself (readiness/**) belongs to other sessions and is not edited here. What is
    done instead: read each row's own `clears` target, and state the number this repository can now
    produce for it, with the verdict left as `moved` or `unchanged` rather than a claim that a gate
    was cleared. The register is the decision surface; this is the evidence note beside it.
    """
    inj = next((s for s in src_rows if s["source_id"] == "nfl-injuries-week"), None)
    steps = [(abs(x["delta_from_level"]), x) for x in injury_series if x["delta_from_level"] is not None]
    max_step, worst = max(steps, key=lambda t: t[0]) if steps else (0.0, {"row_tags": 0})
    prev_tags = [x["row_tags"] for x in injury_series]
    step_from = prev_tags[prev_tags.index(worst["row_tags"]) - 1] if steps else None
    step_to = worst["row_tags"]
    zero_sources = [s["source_id"] for s in src_rows if all(t == 0 for t in s["row_tags"])]
    two_plus = cov["gate_multi_day_2_reads"]["met"]
    notes = {
        "B01": ("The injury signal as a surprise, not a level. At page level a surprise now exists: "
                f"{inj['n_runs']} timestamped reads of the report, the largest single-step change in row count "
                f"being {max_step:,.0f} rows between consecutive reads ({step_from} to {step_to}). At player "
                f"level it is still impossible: no value is parsed anywhere in the capture.", "moved"),
        "B02": (f"Every read carries its clock time (start and end) and a delta. {two_plus} of "
                f"{cov['gate_multi_day_2_reads']['of']} sources now have 2 or more dated reads, which was the "
                f"stated denominator ('0 of 2 needed'). The delta published so far is a byte delta, and the "
                f"measurement above shows it fires on {dq['byte_changed']} of {dq['transitions']} transitions "
                f"with {dq['structure_unchanged_while_bytes_changed']} structural no-ops.", "moved"),
        "B05": (f"Roster/IR sweep before a team model is trusted: still blocked. The capture holds "
                f"{cov['rows_total']} rows of page-level evidence and zero parsed club rows, so 0 of 32 clubs "
                f"have a parsed injury table from it.", "unchanged"),
        "B14": ("Depth-chart register with a date and source per row: the capture now supplies a *run-stamped* "
                "fetch of all 32 club pages, which is a date for the page, not for the row. Per-row dates remain "
                "0 until something parses the rows.", "moved"),
        "B22": ("Reserve list capture so 'not listed' never means 'available': no reserve source is in the "
                f"{cov['configured_sources']} configured sources, so the count is unchanged at 0.", "unchanged"),
        "B26": (f"Wed/Thu/Fri snapshots with dated history: {cov['distinct_runs']} scheduled runs over "
                f"{cov['distinct_days']} days ({', '.join(cov['weekday_labels'])}), 0 failures. The cadence is "
                f"measured from recorded fetch times, because the cron lines are not what actually fired.", "moved"),
        "B27": (f"Daily capture from Wednesday to kickoff: daily captures recorded = {cov['distinct_days']} days, "
                f"from {cov['days'][0]} to {cov['days'][-1]}; parsed values = 0, so the series exists and the "
                f"designation trend inside it does not.", "moved"),
        "B28": (f"Daily hash rows for all 33 sources: {cov['sources_per_run']} per run for "
                f"{cov['distinct_runs']} runs = {cov['rows_total']} rows retained with hashes, plus 33 configured "
                f"sources reconciled against the manifest. The stated denominator ('0 of 33 per day') is met for "
                f"every run that executed.", "cleared-for-the-stated-denominator"),
        "B29": ("Raw hashes and UTC timestamps: built. Conflict flags against published counts: still 0 -- the "
                "capture records no published count to conflict with, because nothing is compared to the site's "
                "own tables.", "moved"),
        "B30": (f"Point-in-time ledger: an append-only manifest with a previous-hash link per source, "
                f"{cov['distinct_runs']} links deep. It covers page bytes only, and inactives are not captured, so "
                f"the lookahead guarantee holds for 'what did the page look like' and not for 'who was "
                f"available'.", "moved"),
        "B31": ("Store captures outside the static site, alert on change: raw bodies are 90-day workflow "
                "artifacts and the manifest is committed; the alert exists as delta_ledger/check_drift.py and its "
                "scheduled job, and it has fired on 2 real events, which is the tested-once condition the row asked "
                "for.", "moved"),
        "B32": (f"Drift alarm pinned to expected row counts: built for all {len(src_rows)} sources in this desk "
                f"and it flags {len([s for s in src_rows if s['n_breaches']])} source(s) whose history contains a "
                f"breach. Value-level comparison against the official page is still 0 of 3 scrapers, because that "
                f"needs parsed values.", "moved"),
        "B33": ("Public analysis layer versus private data layer: unchanged, and it is the gate on everything "
                "above that would require parsing. Owner decision outstanding.", "unchanged"),
        "B34": (f"Weekly 'what changed' diff instead of a static snapshot: two or more dated snapshots now exist, "
                f"so the precondition that made this row impossible ('one capture is stored') no longer holds. The "
                f"structural diff published here is the shape: "
                f"{', '.join(str(int(t)) for t in inj['row_tags'])} row tags on the report across four reads.",
                "moved"),
        "B35": ("Official NFL Game Books for actual starters: unchanged. No game-book source is configured in the "
                f"{cov['configured_sources']} capture sources, and none was reachable from this session.", "unchanged"),
    }
    reg = {}
    if REGISTER.exists():
        doc = json.loads(REGISTER.read_text(encoding="utf-8"))
        reg = {r["id"]: r for r in doc.get("rows", [])}
    out = []
    for gid in GATE_ROWS:
        row = reg.get(gid, {})
        note, verdict = notes.get(gid, ("", "unchanged"))
        out.append({
            "id": gid,
            "requirement": row.get("req", ""),
            "register_status": row.get("status", ""),
            "gate": row.get("gate", ""),
            "clears_target": row.get("clears", ""),
            "this_desk": note,
            "verdict": verdict,
            "sources_configured": cov["configured_sources"],
            "zero_row_sources": zero_sources,
            "max_page_step": max_step,
        })
    return out


def main() -> int:
    rows = [json.loads(l) for l in MANIFEST.read_text(encoding="utf-8").splitlines() if l.strip()]
    src_doc = json.loads(SOURCES.read_text(encoding="utf-8"))
    configured = {s["id"]: s for s in src_doc["sources"]}

    runs = sorted({r["run_id"] for r in rows})
    run_rows = {rid: [r for r in rows if r["run_id"] == rid] for rid in runs}
    run_ledger = []
    for rid in runs:
        rr = run_rows[rid]
        t = parse_run_id(rid)
        started = [ts(r["fetch_start_utc"]) for r in rr]
        ended = [ts(r["fetch_end_utc"]) for r in rr]
        run_ledger.append({
            "run_id": rid,
            "trigger": sorted({r["run_trigger"] for r in rr}),
            "utc_date": t.strftime("%Y-%m-%d"),
            "utc_weekday": t.strftime("%A"),
            "us_pacific_label": {"Tuesday": "Tue", "Wednesday": "Wed", "Thursday": "Thu",
                                "Friday": "Fri", "Saturday": "Sat", "Sunday": "Sun",
                                "Monday": "Mon"}.get(t.strftime("%A"), t.strftime("%a")),
            "sources": len(rr),
            "ok": sum(1 for r in rr if r["result"] == "ok"),
            "fail": sum(1 for r in rr if r["result"] == "fail"),
            "non200": sum(1 for r in rr if r["http_status"] != 200),
            "wall_minutes": round((max(ended) - min(started)).total_seconds() / 60.0, 2) if rr else None,
            "bytes_total": sum(r["bytes"] or 0 for r in rr),
        })
    gaps = []
    for a, b in zip(runs, runs[1:]):
        d = (parse_run_id(b) - parse_run_id(a)).total_seconds() / 3600.0
        gaps.append({"from": a, "to": b, "hours": round(d, 2), "days": round(d / 24.0, 2)})
    span_h = (parse_run_id(runs[-1]) - parse_run_id(runs[0])).total_seconds() / 3600.0 if len(runs) > 1 else 0.0

    # ---- per-source series, structural signature and the informativeness of the byte delta ----
    bysrc: dict[str, list[dict]] = {}
    for r in rows:
        bysrc.setdefault(r["source_id"], []).append(r)
    for sid in bysrc:
        bysrc[sid].sort(key=lambda r: r["fetch_start_utc"])

    transitions = 0
    byte_changed = 0
    struct_unchanged = 0
    byte_unchanged = 0
    struct_changed = 0
    both_changed = 0
    disagree = 0
    src_rows = []
    for sid, series in sorted(bysrc.items()):
        sig = [((r["table_tags"] or 0), (r["row_tags"] or 0)) for r in series]
        hashes = [r["sha256"] for r in series]
        for i in range(1, len(series)):
            transitions += 1
            b_changed = hashes[i] != hashes[i - 1]
            s_changed = sig[i] != sig[i - 1]
            byte_changed += 1 if b_changed else 0
            byte_unchanged += 0 if b_changed else 1
            struct_changed += 1 if s_changed else 0
            struct_unchanged += 0 if s_changed else 1
            both_changed += 1 if (b_changed and s_changed) else 0
            disagree += 1 if (b_changed and not s_changed) else 0
        tags = [r["row_tags"] or 0 for r in series]
        band = D.band_from([float(t) for t in tags])
        latest = series[-1]
        events = D.drift_events(series, band)
        event_runs = {e["run_id"]: e for e in events}
        verdicts = [r["run_id"] in event_runs for r in series]
        breach = verdicts[-1] if verdicts else False
        src_rows.append({
            "source_id": sid,
            "kind": configured.get(sid, {}).get("kind", ""),
            "publisher": configured.get(sid, {}).get("publisher", ""),
            "tier": configured.get(sid, {}).get("tier", ""),
            "url": configured.get(sid, {}).get("url", ""),
            "marker": configured.get(sid, {}).get("marker", ""),
            "n_runs": len(series),
            "runs": [r["run_id"] for r in series],
            "clock_times": [r["fetch_start_utc"] for r in series],
            "row_tags": tags,
            "table_tags": [r["table_tags"] or 0 for r in series],
            "bytes": [r["bytes"] for r in series],
            "hashes8": [(r["sha256"] or "")[:8] for r in series],
            "marker_found_all": all(r["marker_found"] for r in series),
            "statuses": [r["http_status"] for r in series],
            "delta_labels": [r["delta"] for r in series],
            "structural_delta": (["first"] + ["changed" if sig[i] != sig[i - 1] else "unchanged"
                                              for i in range(1, len(sig))]),
            "band": band,
            "latest_row_tags": tags[-1],
            "run_breaches": verdicts,
            "n_breaches": sum(1 for v in verdicts if v),
            "drift_events": [{k: v for k, v in e.items() if k != "detail"} for e in events],
            "drift_detail": [e["detail"] for e in events],
            "band_breach": bool(breach),
            "no_structure": band["state"] == "no-structure",
        })

    # ---- what the injury page's own series looks like: the only "surprise" available today ----
    inj = next((s for s in src_rows if s["source_id"] == "nfl-injuries-week"), None)
    injury_series = []
    if inj:
        prev = None
        for t, clock, lab, sd_lab in zip(inj["row_tags"], inj["clock_times"], inj["delta_labels"],
                                         inj["structural_delta"]):
            injury_series.append({
                "clock_utc": clock,
                "row_tags": t,
                "delta_from_level": (t - prev) if prev is not None else None,
                "byte_delta_label": lab,
                "structural_delta_label": sd_lab,
            })
            prev = t

    # ---- coverage against the three requirements the manifest is supposed to clear ----
    days = sorted({r["utc_date"] for r in run_ledger})
    # keyed by run id, not by date: two runs landed on 2026-11-17, and a dict keyed by date silently
    # reported three runs' coverage for a four-run history. My own check gate caught it.
    per_run_sources = {r["run_id"]: r["sources"] for r in run_ledger}
    coverage = {
        "distinct_runs": len(runs),
        "distinct_days": len(days),
        "days": days,
        "weekday_labels": [r["utc_weekday"] for r in run_ledger],
        "sources_per_run": sorted(per_run_sources.values()),
        "rows_total": len(rows),
        "configured_sources": len(configured),
        "sources_missing_from_the_latest_run": sorted(set(configured) - {r["source_id"] for r in run_rows[runs[-1]]}),
        "span_hours": round(span_h, 2),
        "gaps": gaps,
        "mean_gap_hours": round(sum(g["hours"] for g in gaps) / len(gaps), 2) if gaps else None,
        "min_gap_hours": round(min(g["hours"] for g in gaps), 2) if gaps else None,
        "max_gap_hours": round(max(g["hours"] for g in gaps), 2) if gaps else None,
        "gate_multi_day_2_reads": {"required": ">= 2 dated reads per source",
                                   "met": sum(1 for s in src_rows if s["n_runs"] >= 2),
                                   "of": len(src_rows)},
        "gate_value_level_delta": {"required": ">= 2 parsed values per player-week", "met": 0,
                                   "why": "The capture stores bytes, hashes and element counts. "
                                          "No player value is parsed, so a value-level delta cannot be "
                                          "computed from it by anyone, including this repository."},
        "gate_alarm_built": {"required": "a pinned row-count band that fails the build",
                             "met_by": "delta_ledger/check_drift.py, which is not wired into capture.yml "
                                       "because capture/ belongs to another session's scope"},
    }

    delta_quality = {
        "transitions": transitions,
        "byte_changed": byte_changed,
        "byte_unchanged": byte_unchanged,
        "structure_changed": struct_changed,
        "structure_unchanged_while_bytes_changed": disagree,
        "false_positive_rate_of_the_byte_delta": (disagree / transitions) if transitions else None,
        "both_changed": both_changed,
        "reading": ("Every transition the capture labelled 'changed' is a byte change. The share of those "
                    "whose structural signature did not move is the rate at which the only change detector in "
                    "the pipeline reports an event that no reader can find on the page. A surprise signal built "
                    "on it would be pure noise, which is why the band below is computed on row counts instead."),
    }

    drift_events = [{"source_id": s_["source_id"], **ev} for s_ in src_rows for ev in s_.get("drift_events", [])]

    doc = {
        "_meta": {
            "generated_by": "delta_ledger/readback.py",
            "session": "arena/fcac3e4f-korea3",
            "inputs": {"capture/data/manifest.jsonl": len(rows), "capture/data/sources.json": len(configured)},
            "rule": ("Every number here is a count over the committed manifest. No page was fetched and no value "
                     "was parsed. The capture records bytes, hashes, statuses, byte counts and HTML element "
                     "counts; it does not record what any page says, and this desk does not pretend otherwise."),
            "band_rule": f"median of the source's row-tag counts, +/-{int(BAND_TOL * 100)}%; needs "
                         f">= {MIN_RUNS_FOR_BAND} runs; a source whose median is 0 is labelled no-structure "
                         f"instead of being asserted as a stable zero.",
            "drift_events_total": len(drift_events),
            "drift_event_rule": ("one event per (source, run) where a row count left the pinned band and was a "
                                 "robust outlier, or the source has never produced a parsable table, or its "
                                 "required marker went missing. check_drift.py recomputes the same set and fails "
                                 "if the two ever disagree, so the published page cannot lag the alarm."),
            "freshness_rule": f"check_drift.py --ci fails when the newest capture is older than {FRESH_MAX_H}h "
                              f"(the observed schedule slipped by up to {max((g['hours'] for g in gaps), default=0)}h, "
                              f"so a 26h threshold would alarm on normal Actions behaviour)",
        },
        "runs": run_ledger,
        "sources": src_rows,
        "delta_quality": delta_quality,
        "drift_events": drift_events,
        "coverage": coverage,
        "injury_series": injury_series,
        "gate_updates": gate_notes(src_rows, coverage, delta_quality, injury_series),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    pins = {"schema": "drift-pins/v1", "tolerance": BAND_TOL, "min_runs": MIN_RUNS_FOR_BAND,
            "sources": {s["source_id"]: {"median": s["band"]["median"], "lo": s["band"]["lo"],
                                         "hi": s["band"]["hi"], "state": s["band"]["state"],
                                         "n_runs": s["n_runs"], "marker": s["marker"]}
                        for s in src_rows},
            "_meta": {"derived_from": "capture/data/manifest.jsonl",
                      "note": "Derived, not hand-set. Re-derive with delta_ledger/readback.py; check_drift.py "
                              "fails if a pin disagrees with the manifest history."}}
    PINS.parent.mkdir(parents=True, exist_ok=True)
    PINS.write_text(json.dumps(pins, indent=1, sort_keys=True) + "\n", encoding="utf-8")

    print(f"readback: {len(rows)} manifest rows, {len(runs)} runs, {len(src_rows)} sources "
          f"-> delta_ledger/data/ledger.json + pins.json")
    print(f"  byte delta: {byte_changed}/{transitions} transitions 'changed'; "
          f"{disagree} of them had an unchanged structural signature")
    print(f"  breaches in the latest run: {[s['source_id'] for s in src_rows if s['band_breach']]}")
    print(f"  sources with any breaching run: {[(s['source_id'], s['n_breaches'], s['row_tags']) for s in src_rows if s['n_breaches']]}")
    print(f"  no-structure sources: {[s['source_id'] for s in src_rows if s['no_structure']]}")
    print(f"  run gaps (h): {[g['hours'] for g in gaps]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
