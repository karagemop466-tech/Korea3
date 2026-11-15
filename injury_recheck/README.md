# Week 10 2026 official injury report: per-club re-check

Session `arena/eff9eafd-korea3` (task W02–W04). Checked 2026-11-15 (UTC).

## Sources (official, nfl.com)

- Injury report, all 8 chunks: https://www.nfl.com/injuries/league/2026/reg10
- Week 10 schedule, including the "Teams on Bye" block: https://www.nfl.com/schedules

## What was verified

| Check | Result | Method |
|---|---|---|
| Clubs with an injury table | 28 | Each club heading read across chunks 0–6 |
| Rows per club | 347 total (per-club counts in `data/week10_official.json`) | Counted by hand from the rendered table; not parsed by a program |
| Clubs with no table | CHI, DEN, PHI, TB | Official schedule lists these four under "Teams on Bye" for Week 10 |
| Games | 14 (28 teams) | Listed on the official schedule and injury page |
| Repo capture vs live | 27 of 28 clubs match by row count; BAL differs (8 vs 10) | `depth_lab/data/raw/nfl_injury_w10_2026.json` (read only) |

## Limits

- Counts were made by hand, not by a parser. Cell values (designations, practice status) were not re-checked row by row.
- The sandbox has no route to nfl.com except through the page-fetch tool, so `check.py` verifies internal consistency and the recorded counts only. It cannot re-fetch the page.

## Irregularities

1. **BAL capture is incomplete.** The repo capture has 8 BAL rows. The official page has 10. Missing: Calais Campbell (DT, Did Not Participate In Practice, game status blank) and Ronnie Stanley (T, Did Not Participate In Practice, game status blank).
2. **Published hub figures are stale.** The hub page reports 254 rows and four "no injuries reported" clubs (SEA, CIN, LAC, BAL). The live page lists 15, 9, 19 and 10 players for those clubs.
3. **The brief's 279 figure** matches neither the live page (347) nor the capture (345). It is not used.

## Files

- `data/week10_official.json`: per-club record (32 rows), games, comparisons.
- `build.py`: writes the JSON and `index.html`. Counts are typed in from the reads above and are not re-derived.
- `check.py`: fail-closed consistency check (exit 1 on failure). Known BAL diff is the only permitted repo-vs-live difference.
- `index.html`: the per-club table, with a source link on every row. Served at `/injury_recheck/`.
