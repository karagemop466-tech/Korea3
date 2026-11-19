# delta_ledger — read-back of the scheduled availability capture, and the drift alarm

`capture/` (another session's subsystem) fetches 33 official availability pages on a GitHub Actions
schedule and appends one row per source per run to `capture/data/manifest.jsonl`: fetch time, HTTP
status, byte count, SHA-256 of the body, `<table>`/`<tr>` counts, the previous hash and a delta label.
Until `main` reached `0c54486` that manifest had **zero rows**, so about ten readiness gates were
written against "nothing recorded yet". This desk reads the history back and answers each one with a
number, including the two answers that are uncomfortable.

## Findings this desk publishes

| Finding | Arithmetic |
|---|---|
| Multi-day history now exists | 132 rows, 4 runs, 3 days, 0 failed fetches, every source returned 200 with its required marker |
| The byte-level delta is not a signal | 99 of 99 transitions labelled `changed`; 96 of them with an unchanged (tables, rows) signature → 97.0% false-positive rate |
| The pipeline does not notice a broken page | one run captured 28 row tags on the injury report against a median of 326; `result=ok`, all byte checks passed |
| One club's depth page has never been parsable | `club-depth-hou`: 0 rows in 4 of 4 runs — machine corroboration of the "published as an image" finding |
| Scheduled run times are advisory | gaps of 9.96h to 23.44h, two runs on one date → a freshness alarm must use recorded fetch times, not the cron line |
| Value-level delta still impossible | no value is parsed anywhere, so "surprise, not level" at player level is 0 of what it needs; it waits on the owner's terms decision |

## Files

```
delta_ledger/drift.py        the single definition of "this run broke", shared by the page and the alarm
delta_ledger/readback.py     capture manifest -> data/ledger.json + data/pins.json  (deterministic)
delta_ledger/build.py        the 7 pages, from the JSON only                        (deterministic)
delta_ledger/check_drift.py  the alarm: pinned bands, markers, freshness (--ci reads the clock)
delta_ledger/check.py        the consistency gate used by CI (pages, reproducibility, event-set agreement)
.github/workflows/drift-alarm.yml   consistency on push/PR; alarm on the schedule only
```

## What is deliberately not here

* **No clock on any page.** Age-of-capture lives only in `check_drift.py --ci`, inside the scheduled job.
  A published "fresh" badge that cannot be rebuilt byte-identically is how this repository's other
  surfaces went stale.
* **No parsed values, and no invented ones.** The capture stores bytes and element counts; this desk
  publishes what those say about our pipeline, and nothing about any club's roster.
* **No edits to `capture/**`.** The same rule as a step inside `capture.yml` is logged on
  `COORDINATION.md` as a request to that file's owner, because replacing another session's gate
  silently is worse than adding a second one.
* A red **scheduled** alarm job is the deliverable working, not a defect to mute: it means a source
  left its pinned band and nobody looked.

## Reproduce

```bash
python3 delta_ledger/readback.py && python3 delta_ledger/build.py
python3 delta_ledger/check.py            # consistency gate (green when the pages match the record)
python3 delta_ledger/check_drift.py      # the alarm (red while the two open drift events exist)
```
