# Desk Ops executive summary — session `arena/ccc36a0d-korea3` (2026-11-14)

**Scope.** The brief's eight numbered additions audited line by line; the four that no prior session
had implemented are now built, verified and live: the **price-snapshot store**, the **verified results
feed**, the **signal/staking leaderboard split**, and the **demotion gate (live → paper)**. All work is
in the new `ops_lab/` directory — additive; no existing page, generator or data file was rewritten
(the one shared edit is a single navigation line in `line_lab/build_site.py`, the precedent set by PR #85).

## What was missing, and why it matters

| Brief requirement | State found (grep + line-by-line check) | Delivered by this session |
|---|---|---|
| Price-snapshot store (opening + closing per originated market) | Did not exist. Opening (WSGT 2021) and closing (2006–2018) numbers sat in separate pinned files, never joined per market. | 62,904-row store: 20,490 closing, 40,510 league-posted (2006–2026), 1,088 opening, **816 explicit blank rows** for originated markets with no market number yet — coverage answered by rows, not assumptions. |
| Verified results feed | Did not exist as an artifact; settlement inputs were unjoined and unverified. | 44,304 market-side rows with two independent outcome columns; 13,660 published outcomes re-derived from their own lines; the S1–S11 ledger re-settles with **0 mismatches**. |
| Originate side → total → moneyline | Order documented nowhere; the 2026 book had **no own-moneyline price**. | Order published as policy; fair moneyline derived as a labelled recomputation from the published win probabilities (no new model, no market input). |
| Fair line / market line / difference columns | Existed for spread and total; not for moneyline; differences not re-verified. | All three columns published for all three markets; spread/total differences re-check against the published disagreement columns on all 164 rows. |
| Signal vs staking separation | One mixed leaderboard table. | Two views from disjoint columns, never ranked together; staking view reproduces the published ROI to 1e-6 on the 2006–2025 window. |
| Depth of replacement | **Already done** by Depth Lab (PR #85) — verified, not duplicated. | Recorded in the brief-coverage table with links. |
| Correlations with n | Verified: every published correlation row carries n (same-game, signal pairs `n_shared`, cross-game per-season `n_pairs`). | Audit row with links; pre-existing flag X02 re-verified (conclusion unchanged). |
| Demotion gate | Did not exist anywhere (grep: no `demotion` in any page, generator or dataset). | Six triggers with week-block bootstrap thresholds; armed; live set empty (0 of 11 strategies pass promotion); dry-run demonstration per strategy. |

Live pages: `ops_lab/index.html` (12 pages), linked from the root navigation as **Desk Ops**.

## Findings the verification surfaced (all published on `ops_lab/flagged.html`)

- **FO1 (high) — 14 published outcomes contradict their own line.** 14 of 13,674 (0.10%) published
  outcomes in `closing_lines.csv` are not reproducible from that row's own published line (e.g. a
  total of 38 against a closing line of 45 published as an over win). Retained as published, excluded
  from settlement claims; the ledger cross-check shows no S1–S11 bet consumed them.
- **FO2 (medium) — the leaderboard's per-strategy "Brier skill" column is the market-universe G6
  value**, identical for every strategy in a market (proven across all four markets). The per-strategy
  value on each strategy's own bets differs (e.g. S5: +0.0003 own-bets vs −0.0316 published) and is
  now published beside it.
- **FO3 — the book had no own moneyline** (closed); **FO4 — dataset lag**: the official week-10
  result (WAS 24–21 NYG, read on nfl.com on 2026-11-14) is absent from the pinned dataset;
  **FO5 — LAR/LA abbreviation mismatch** across the dataset's own files (47 games, joined by a
  documented alias); **FO6–FO10** — opening prices not published (2021 line-only), 2006 partial
  prices, parlay legs not traceable from the ledger alone, plus pointers to pre-existing X01/X02.

## Verification performed

- `ops_lab/check.py` — **34/34 PASS**, including: pinned-input sha256 re-hash; closing store rows
  equal `closing_lines.csv` value-for-value (multiset); feed re-derives byte-identically; ledger
  cross-check 15,666 bets / 0 mismatches; split ROI equals the published leaderboard (tolerance
  0.05 pp, actual ≤ 1e-17); fair-moneyline inverse identity; deterministic rebuild (byte-identical).
  The verifier caught and forced the fix of a real moneyline-conversion bug before publication.
- Shared gates: `line_lab/check_site.py` OK (16 pages) · `verify/source_audit.py --max-unsourced 0
  --allow-dirs session-398c4b58,qa` PASS · `verify/linkcheck_all.py` PASS (0 broken) ·
  `decision_lab/check.py` PASS · `depth_lab/check.py` 41/41 · `decisions/check.py` PASS ·
  `hub/check_hub.py` PASS (25 pages) · `desk/check.py` PASS · `nfl_lab.check_verified` OK ·
  `pytest tests/` 34 passed.
- Official sources re-read on 2026-11-14: the NFL week-10 schedule page and the WAS@NYG game-center
  page (cited on the results page). Dataset files are tier 3 (nflverse), disclosed as such everywhere.

## Questions and suggestions awaiting the owner (nothing implemented)

- **Questions** (`ops_lab/questions.html`, 7): the blocking one is Q-ops1 (club-domain source tier,
  re-raised); others: snapshot cadence, demotion-threshold ratification, upstream treatment of the
  14 self-contradictions, leaderboard relabel, canonical register, opening-price source beyond 2021.
- **Suggestions** (`ops_lab/suggestions.html`, 8, all decision-gated): automated snapshot capture,
  per-strategy Brier column, strategy-ID unification (X01), promote the own moneyline into the book,
  weekly feed re-pin, canonical register, demotion gate wired into CI, opening-price source decision.

## Publication record

| Item | Result |
|---|---|
| Pull request | opened against `main` from `arena/ccc36a0d-korea3` (see COORDINATION.md for the number and merge commit) |
| Checks | `ops-lab` (new, 34 checks) plus the pre-existing CI suites |
| Pages deploy | confirmed after merge (recorded in COORDINATION.md) |
