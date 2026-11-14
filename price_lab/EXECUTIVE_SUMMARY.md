# Snapshot Desk — Executive Summary

**Session:** `arena/88791c5c-korea3` · **Date:** 2026-11-14 (UTC) · **Branch:** `arena/88791c5c-korea3` → `main`
**Base:** `77c0b9e` (merge of PR #85) · **Claim:** `COORDINATION.md`, tasks P01–P11

## What this session built

A self-contained settlement layer for the repository's NFL line-origination research, in `price_lab/`:

| Deliverable | What it is | Where |
|---|---|---|
| **Price-snapshot store** | 47,583 rows: one row per originated market per snapshot — **open** (2021 WSGT, 1,088 rows), **close** (all seasons, 25,686 rows), **fair** (the model's own lines, 20,809 rows). Every row names its book and links its source file. | `price_lab/data/snapshots.csv`, `price_lab/snapshots.html` |
| **Verified results feed** | All **137** officially final 2026 games transcribed from the official NFL.com week pages (opened 2026-11-14) and compared row by row with the pinned dataset: **108/108 match exactly**; **29** finals postdate the 2026-11-01 pin and are published with official links plus a gap flag. Plus a **7,384-row** history feed (1999–2026) for backtests. | `price_lab/data/results_feed_2026.csv`, `price_lab/data/results_history.csv`, `price_lab/results.html` |
| **Origination order** | Side → total → moneyline, enforced by column layout, per-row order fields and check.py completeness rules. Sign conventions stated and asserted (pipeline = −games.csv; WSGT side rows = exact negations). | `price_lab/origination-order.html` |
| **Fair / market / difference columns** | `origination_ledger.csv` (6,991 rows) publishes fair spread, market spread, diff, fair total, market total, diff, fair ML, market ML and ML diff as **separate columns** for every originated market; populated wherever a market line exists (28 of the 164 originated unplayed fixtures), blanks elsewhere. | `price_lab/data/origination_ledger.csv` |
| **Leaderboard: signal vs staking** | 11 strategies (line_lab ledger S1–S11, 16,439 bets) scored on two separated axes: **signal** (hit rate, mean edge, flat-unit ROI, flat drawdown — the only axis that can earn rewards) and **staking** (a documented 2%-cap fractional-Kelly overlay — can never promote). | `price_lab/data/leaderboard_signal_staking.csv`, `price_lab/leaderboard.html` |
| **Demotion gate** | Six automatic triggers (rolling ROI, CLV, drawdown, consecutive windows, feed integrity, own-vs-market error decay) with windows, arithmetic and restoration rules — defined before anything is live. Status: **proposed spec; 0 strategies live; nothing demoted.** | `price_lab/demotion.html` |
| **Suggestions section** | 10 proposals (S-G01…S-G10), each with a problem, a proposed path and a decision status — **nothing implemented**; the canonical board remains `hub/suggestions.html`. | `price_lab/suggestions.html` |
| **Open questions register** | 8 questions (Q-P01…Q-P08) with information **held**, information **missing**, the **way to discover** it, and the decision each **blocks**. Canonical register remains `hub/questions.html`. | `price_lab/open-questions.html` |
| **Flagged for review** | Irregularities G01–G10 with sources, including two high-severity data findings below. | `price_lab/flagged.html` |
| **Fail-closed checks + CI** | `check.py` re-derives every published number from the committed data and fails the build otherwise; workflow `price-lab.yml` runs build + checks + the repo-wide source and link audits. | `price_lab/check.py`, `.github/workflows/price-lab.yml` |

## The eight named requirements

1. **Price-snapshot store (open + close for every market we originate)** — delivered. Open snapshots exist only for the 2021 season (WSGT, the only opening series in any reachable source); closes exist for 1999–2026.
2. **Verified results feed** — delivered: 137 official finals cross-checked against the pin (108 exact matches), 7,384-row history feed so backtests and ROI are computable at all.
3. **Originate side first, then total, then moneyline** — published as an enforced order with asserted conventions.
4. **Fair line, market line, difference as separate columns** — delivered in the origination ledger.
5. **Signal separated from staking** — delivered; reward eligibility rides on the signal axis only.
6. **Track the depth of the replacement, not just the fact** — already delivered by the Depth Lab (43 replacement rows with string depth); linked, not duplicated.
7. **Correlations from officially sourced numbers with n published** — already delivered on `hub/correlations.html`; linked, not duplicated.
8. **Demotion gate back to paper** — defined as a proposal with six mechanical triggers.

## Findings that need an owner decision

- **G01/G02 (high).** The 2021 opening-line series is recorded only as "WSGT" — the upstream dataset never expands the abbreviation — and several 2021 open→close movements are implausible (mean |move| 3.40 pts, max 15.0; e.g. `2021_15_GB_BAL` opens home BAL −5.5 and is recorded closing away GB −9.5). No official archive reachable from this environment can adjudicate, so both series are published **as recorded, uncorrected, and flagged**. Consequence: CLV (demotion trigger D2) cannot be computed from the 2021 opens until the series is authenticated.
- **G04 (high).** The pinned dataset (2026-11-01) is missing 29 officially final games (weeks 8–10). Advancing the pin re-bases every prior session's numbers, so it is logged as suggestion S-G05, not acted on.
- **G06 (medium).** The fair moneyline is a labelled derivation — Φ(−fair_spread / 13.618) with the model's measured spread RMSE — not an independent model. Whether to build a dedicated ML model is open question Q-P03.
- **Signal finding.** Two of eleven strategies show positive flat ROI (S4 +0.33% over 1,084 bets; S6 +0.58% over 600); none is reward-eligible, consistent with the hub's multiplicity analysis (zero strategies cleared all gates).

## Verification performed

- Pinned raw files re-hashed against `data/raw/MANIFEST.json` — all match.
- The official 2026 transcription is re-compared against the pinned feed on every build; **any single disagreement fails the build**.
- Every diff column, the fair-ML derivation, the 2021 movement arithmetic and the leaderboard arithmetic are re-derived in `check.py` (fail-closed).
- Every table row on every desk page carries at least one source link; the repo-wide gates (`verify/source_audit.py --max-unsourced 0`, `verify/linkcheck_all.py`) are run in CI.

## Sources

- Pinned dataset: `nflverse/nfldata` @ `a270278f3ac4e937295fe6a27814b3c4a2b62645` (`games.csv`, `initial_lines.csv`, `closing_lines.csv`) — checksummed in `data/raw/MANIFEST.json`.
- Official pages opened 2026-11-14 with the page-fetch tool: `nfl.com/schedules/2026/by-week/week-1` … `week-10` (all 137 finals).
- Repository artifacts: `data/derived/model_predictions.csv`, `own_lines_upcoming.csv`, `model_metrics.json`, `bets.csv`.
- Canonical boards linked, not modified: `hub/suggestions.html`, `hub/questions.html`, `hub/competition.html`, `hub/leaderboard.html`, `depth_lab/`.

## Scope discipline

Only `price_lab/**`, `.github/workflows/price-lab.yml`, the root `index.html` nav line, the README banner and this file were touched. No file owned by another session was edited. Concurrent-session check at claim time found no overlapping claim.
