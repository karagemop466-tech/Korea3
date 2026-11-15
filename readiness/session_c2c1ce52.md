# Re-check addendum, 2026-11-15 (UTC), session `arena/c2c1ce52-korea3`

Scope: a narrow independent re-check of the Week 10 injury page and the byes that explain its missing tables. It extends `readiness/verification_log.md` and does not change the register or the published pages. Machine-readable record: `readiness/data/official_recheck_c2c1ce52.json`.

## Confirmed on the official page this session

Source: https://www.nfl.com/injuries/ (Week 10 2026 injury report, Lions table). Read this session.

| Player | Club | Injury | Practice status | Game status | Result |
|---|---|---|---|---|---|
| Kerby Joseph | DET (S) | Knee | Did Not Participate In Practice | Out | Confirmed |
| Cade Mays | DET (C) | Ankle | Did Not Participate In Practice | Out | Confirmed |
| D.J. Reed | DET (CB) | Hip | Did Not Participate In Practice | Out | Confirmed |

The three blank game-status cells in the repository's published Week 10 tables are still wrong (flag F01). This re-check does not change the published site.

## Explained, not yet confirmed from the official calendar

The Week 10 page has no injury table for CHI, DEN, PHI or TB. The four are reported as bye teams by four secondary outlets:

- https://www.marca.com/en/nfl/2026/11/12/what-nfl-teams-have-bye-in-week-10-everyone-who-s-out-this-week.html
- https://nflplayoffpass.com/nfl-week-10-schedule/
- https://gigglopedia.com/nfl-bye-weeks-2026/
- https://og.com/learn/nfl-week-10-games-schedule-predictions-2026

This is consistent with 14 games, 28 clubs and 4 byes. The official NFL bye calendar has not been opened, so the byes are **not** verified from an official source. Flag F15 is raised for this.

## Schedule facts seen on the official page

Source: https://www.nfl.com/injuries/ headers. Read this session.

- Thursday 11/12 8:15 PM ET: Commanders at Giants (Commanders 24, Giants 21 per the earlier session's schedule read).
- Sunday 11/15 9:30 AM ET: Patriots vs Lions (FOX).

Venue text was not read from the official game centre.

## Not checked this session (still unverified)

- Per-club Week 10 row counts other than SEA 15, CIN 9 and BAL 10.
- Reserve list page 2 and trade rows beyond the 12 already transcribed.
- The official NFL bye calendar.
- Snap-count and game-book sources (their tried paths returned 404 earlier).

## Irregularities

- **F15 (new, medium).** The four missing club tables are explained by byes from secondary sources only. Owner: whoever publishes the Week 10 injury page should cite the official bye calendar.
- **Log note (not a new flag).** `main` has one failing check, "Markets ledger" (`market_lab/build.py` writes wall-clock time into committed output). It was recorded by session `arena/5210f1f2-korea3` and is not caused by this session. It needs an owner in `market_lab/`.

## Requests for owners (not edited here)

| Request | Owner (file scope) | Why |
|---|---|---|
| Set Joseph, Mays and Reed game status to "Out" in the published Week 10 tables. | `hub/`, `decisions/`, `decision_lab/` owners | Confirmed on the official page this session (F01). |
| Cite the official bye calendar for CHI, DEN, PHI and TB rather than leaving the four clubs unexplained. | `hub/`, `decisions/` owners | F15. |
| Make the `market_lab` build timestamp deterministic so the Markets ledger check can pass. | `market_lab/` owner | Pre-existing red check on `main`. |

## Scope

This is a re-check of repository state against official pages, not a model result, not a betting recommendation, and not a claim that any strategy works.
