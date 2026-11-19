#!/usr/bin/env python3
"""The drift rule, in one place, shared by the page builder and the alarm.

`readback.py` publishes a set of drift events; `check_drift.py` fails on that same set. If the two
implemented the rule separately they would drift apart and the published page would quietly stop
being what the alarm enforces -- the exact failure mode this repository keeps flagging in other
people's numbers. So both import `drift_events()` here and nothing else decides.

Rule
----
For one source, over its runs in time order, with a band pinned from that source's own history:

  * a run is a **pinned-band** event when its row-tag count leaves [lo, hi] *and* it is a robust
    outlier: |count - median| / (1.4826 x MAD) > Z_BREACH, or the MAD is 0 so any movement is
    unbounded surprise. The second condition is what stops one bad run becoming the baseline;
  * a source whose history is all zeros is a **no-structure** event: the page returns 200 with the
    marker present but carries no parsable table at all, which is the Texans case;
  * a run whose required marker is absent is a **marker-missing** event;
  * a run recorded as `result=fail` is a **failed-run** event.

An empty-but-honest result (a club with no injuries this week) is deliberately *not* an event:
zero is a real number when the page says so. What is an event is a page that used to have a table
and now does not.
"""
from __future__ import annotations

Z_BREACH = 3.0
BAND_TOL = 0.15
MIN_RUNS_FOR_BAND = 3


def median(xs: list[float]) -> float:
    s = sorted(xs)
    if not s:
        return 0.0
    mid = len(s) // 2
    return float(s[mid]) if len(s) % 2 else (s[mid - 1] + s[mid]) / 2.0


def band_from(tags: list[float], tol: float = BAND_TOL, min_runs: int = MIN_RUNS_FOR_BAND) -> dict:
    n = len(tags)
    if n < min_runs:
        return {"state": "insufficient", "n_runs": n, "median": None, "lo": None, "hi": None,
                "mad": None, "z": [None] * n, "degenerate_scale": False}
    med = median([float(t) for t in tags])
    mad = median([abs(float(t) - med) for t in tags])
    scale = 1.4826 * mad
    zs = [(abs(float(t) - med) / scale if scale > 0 else (0.0 if float(t) == med else None)) for t in tags]
    degenerate = scale == 0 and any(float(t) != med for t in tags)
    if med == 0:
        return {"state": "no-structure", "n_runs": n, "median": 0.0, "lo": 0.0, "hi": 0.0,
                "mad": mad, "z": zs, "degenerate_scale": degenerate}
    return {"state": "pinned", "n_runs": n, "median": med,
            "lo": float(max(0.0, (1 - tol) * med)), "hi": float((1 + tol) * med),
            "mad": mad, "z": zs, "degenerate_scale": degenerate, "z_threshold": Z_BREACH}


def drift_events(rows: list[dict], band: dict, z_breach: float = Z_BREACH) -> list[dict]:
    """rows: one source's manifest rows in time order. band: from band_from()."""
    tags = [float(r["row_tags"] or 0) for r in rows]
    events: list[dict] = []
    if band["state"] == "no-structure" and all(t == 0 for t in tags):
        events.append({"run_id": rows[-1]["run_id"], "kind": "no-structure", "row_tags": tags[-1],
                       "median": band["median"], "lo": band["lo"], "hi": band["hi"], "z": None,
                       "detail": f"no parsable table in {len(tags)} of {len(tags)} runs"})
    for r, t, z in zip(rows, tags, band.get("z") or []):
        if band["state"] != "pinned":
            continue
        outside = t < band["lo"] or t > band["hi"]
        strong = (z is None) or (z > z_breach)
        if outside and strong:
            events.append({"run_id": r["run_id"], "kind": "pinned-band", "row_tags": t,
                           "median": band["median"], "lo": band["lo"], "hi": band["hi"], "z": z,
                           "detail": (f"{t:.0f} rows against a band of [{band['lo']:.0f}, {band['hi']:.0f}] "
                                      f"(median {band['median']:.0f}), robust z "
                                      + ("unbounded (MAD is 0)" if z is None else f"{z:.2f}"))})
        if not r.get("marker_found"):
            events.append({"run_id": r["run_id"], "kind": "marker-missing", "row_tags": t,
                           "median": band["median"], "lo": band["lo"], "hi": band["hi"], "z": z,
                           "detail": f"required marker {r.get('marker')!r} absent from the body"})
        if r.get("result") == "fail":
            events.append({"run_id": r["run_id"], "kind": "failed-run", "row_tags": t,
                           "median": band["median"], "lo": band["lo"], "hi": band["hi"], "z": z,
                           "detail": f"capture recorded a failure: {r.get('reason') or 'no reason given'}"})
    return events


def key(e: dict) -> tuple:
    return (e["source_id"], e["run_id"], e["kind"])
