# Verification log

Two verification layers, both machine-runnable: the **pipeline checks** (do the numbers
reconcile?) and the **site checks** (`scripts/verify_site.py`, does every published row
carry a source and does every link resolve?).

## 1. Automated site verification

Run: `python3 scripts/verify_site.py` → `data/derived/verification_report.json`.
Current result is published on the site at `docs/verification.html`.

Checks performed:

| Check | What it proves |
|---|---|
| Data artifacts present | 26 derived files exist and are non-empty |
| Raw data checksums match provenance | the five raw CSVs are byte-identical to the pinned commit |
| Dataset reconciliation | margin, total and cover flags recomputed on all 7,075 rows; no unplayed game present; game ids unique |
| Internal links resolve | every relative link across 15 pages points at a file that exists |
| Every table row has a source cell | 447 audited rows, each with a resolvable source link |
| No placeholder text | no `None`, `nan`, `TODO` or unrendered `{variable}` in the output |
| Static assets and explorer data present | CSS, JS, `data/games.json`, `data/games.csv` |
| External GitHub links resolve live | live HTTP check of every GitHub source link |
| Repo-internal source links point at real files | every link into this repository maps to an existing path |
| Non-GitHub sources recorded as verified | every official/operator URL appears in `data/derived/verified_external.json` with the sentence it supports |
| Gate results reconcile with metadata | 18 rule rows vs declared family size 18 |

## 2. Data-level checks (enforced in the pipeline, not just reported)

`scripts/build_dataset.py` asserts, on every row:

- `margin == home_score − away_score`
- `total_score == home_score + away_score`
- `home_cover` consistent with `home_ats_margin = margin − spread_line`
- no game without a final score
- unique `game_id`

`scripts/verify_site.py` re-runs these from the written file, so a corrupted artifact
cannot pass.

## 3. Line-by-line verification of official claims

Each Tier 1 / Tier 2 citation is recorded in `research/sources.md` with:

- the exact URL;
- the exact sentence or table the citation supports;
- the date it was checked;
- any anomaly found while checking it.

Two anomalies were found this way and both are flagged rather than smoothed over:
the swapped NFL Support article bodies (F08) and the dated DraftKings rules copy (F09).

## 4. What could NOT be verified — and is therefore blank

| Value | Reason | Flag |
|---|---|---|
| Player-prop prices | no official or machine-readable source | B01 |
| Player-prop correlations | no player-level data; values would be invented | B01 |
| Weather ground truth | dataset field has no provenance | F05 / B03 |
| Injury/inactive status | not in the dataset | B02 |
| Venue coordinates / travel | no verified source; deliberately not hardcoded | B05 |
| Pre-2021 opening lines | not in the dataset | B06 |

No value on the site was inferred, interpolated, or supplied from general knowledge.

## 5. Verification limits stated plainly

An automated check can prove a link resolves; it cannot prove a human-readable page still
says what it said today. For the seven sources that carry rules, prices and settlement
claims, the supporting sentence is quoted in the registry so a human can re-check it in
seconds. For the market dataset, the entire file is pinned by commit and checksum, so any
single row can be inspected at source.
