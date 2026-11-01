# Flagged for review (plain-text mirror of the site page)

Generated from `scripts/build_site.py` → `docs/flagged.html`. This file exists so a reader
in the repository sees the same list as a reader on the site.

Statuses: **resolved** (found and fixed) · **mitigated** (found, contained by a second test) ·
**unverified** (could not be confirmed from an official source; the value is blank or labelled) ·
**flagged** (needs a human's judgement) · **skipped** (deliberately not attempted) ·
**published** (a finding, not a defect).

## Data irregularities

- **F01 — Spread sign convention inverted in the source dataset.** `spread_line` is signed opposite to the conventional home spread; positive means the home team is favoured. *Resolved:* conventional home spread = `−spread_line`, verified two independent ways (home-margin split by sign; agreement with the per-side closing file at 67.3% vs 0.6%).
- **F02 — Two in-dataset line sources disagree.** Spreads match exactly on 67.3% of overlapping games (91.1% within 0.5 pt); totals on 61.7%. *Mitigated:* gate G7 re-scores every rule against the second source.
- **F03 — Trailing-space duplicate in `surface`** (`'grass '` vs `'grass'`, 93 rows). *Resolved:* normalised to `surface_clean`.
- **F04 — Missing environment values.** roof 26 rows, surface 87, temp/wind 2,213. *Not imputed.*
- **F05 — `temp` and `wind` have no provenance field** (no station, no timestamp). *Unverified:* labelled wherever shown; weather signal S14 carries the caveat.
- **F06 — 2026 season live and incomplete** (136 of 272 games played). *Resolved:* excluded by construction; unplayed fixtures used only for the own-lines forecast.
- **F07 — 26.9% of games have no recorded price.** The −110 standard is substituted; the imputed share is published per rule. The largest methodological compromise on the site.

## Source anomalies

- **F08 — Two NFL Support article bodies are swapped.** The article titled "What is a money line?" explains the point spread and vice versa. Both cited, both flagged. Content is consistent; titles are crossed.
- **F09 — DraftKings house-rules copy is dated 2023-06-01** and may be superseded. Rule text quoted as published; confirm against the live page.

## Gaps — values that could not be confirmed

- **B01 — No verifiable player-prop line source.** All prop correlation values are blank. 8 combos documented with mechanism and required φ only.
- **B02 — No injury or inactive data.** The largest omission in the feature set.
- **B03 — Weather not independently verified** (see F05).
- **B04 — Referee and penalty signals untested** (no penalty data in the dataset).
- **B05 — No verified venue coordinates**, so no travel/time-zone signal was tested. Deliberately not hardcoded.
- **B06 — No opening-line archive before 2021**, so no full-history CLV study.

## Results that are uncomfortable but published

- **R01 — No strategy cleared all eight gates.** Best raw result +8.41% over 607 bets, q = 0.288. Four rules are provisional; multiplicity is the binding constraint for all of them.
- **R02 — The own line is significantly worse than the closing line.** MAE 10.670 vs 10.247 (p ≈ 4.9e-24), consistent across nine hyper-parameter settings.
- **R03 — Same-game spread × total correlation is effectively zero** (φ = +0.0086, 95% CI −0.0162 to +0.0332), contradicting a common assumption about same-game parlays.

## Repository / process

- **V01 — The repository contained only an 8-byte README** at session start. Reviewed and recorded in `research/00-repo-review.md`; nothing deleted.
- **V02 — The repository is named `Korea3`** but the project is NFL research. Not renamed (repository identity left untouched); noted for the owner.
- **V03 — Single agent session for this run.** `COORDINATION.md` created and all tasks claimed by one session. Board maintained anyway so a future session can pick up the backlog.
