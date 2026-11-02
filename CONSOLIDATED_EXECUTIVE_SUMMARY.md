# NFL Line Origination — Consolidated Executive Summary

**Date:** 2026-11-02 (UTC) · **Session:** `arena/d7d4d48d-korea3` (independent re-verification + final integration)
**Live site:** <https://karagemop466-tech.github.io/Korea3/> · **This summary as a page:** <https://karagemop466-tech.github.io/Korea3/executive.html>
**Verification evidence:** [`verification/REPORT.md`](verification/REPORT.md) · [`verification/report.json`](verification/report.json) · [`verification/link_audit.json`](verification/link_audit.json)

> Every number below was **independently recomputed on 2026-11-02** from the pinned
> dataset by fresh code (`verification/reproduce.py`, 66/66 checks PASS). Prior
> sessions' summaries remain in place: [`EXECUTIVE_SUMMARY.md`](EXECUTIVE_SUMMARY.md)
> (empirical pipeline), [`LINE_LAB_EXECUTIVE_SUMMARY.md`](LINE_LAB_EXECUTIVE_SUMMARY.md)
> (root dashboard), [`VERIFIED_EXECUTIVE_SUMMARY.md`](VERIFIED_EXECUTIVE_SUMMARY.md)
> (official-evidence-only workbench). This document consolidates, it does not replace.

---

## 1. Bottom line — the five findings that matter

| # | Finding | Evidence (recomputed 2026-11-02) | Source |
|---|---|---|---|
| 1 | **The own line works as research, not as edge.** Walk-forward spread MAE 10.670 pts vs 10.247 for the closing line (paired p ≈ 4.9×10⁻²⁴); total 10.859 vs 10.593. The market is better, consistently. | `data/derived/model_predictions.csv` (n = 6,827) | [Pinned dataset](https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv) |
| 2 | **No strategy passed validation — in either family.** 0 of 18 rules cleared all 8 gates (scripts family); 0 of 11 cleared all 9 gates (root-dashboard family). Best raw ROI +8.41% (n = 607) fails multiplicity (q = 0.288). | `data/derived/gates_results.csv`; `line_lab/data/derived/summary.json` | [Break-even −110 price: NFL Support](https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line) |
| 3 | **Same-game parlays have no hidden correlation to harvest.** Spread × total φ = +0.0086 (95% CI −0.0162 … +0.0332, n = 6,784) — zero. A 2-leg parlay at −110 needs φ ≥ 0.0975 to break even. That gap is the margin. | `data/derived/corr_same_game.csv`; analytic break-even | [Pinned dataset](https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv); [DraftKings odds](https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466) |
| 4 | **The one real correlation is already priced.** Moneyline × spread (same team) φ = 0.6724. Operators re-price it as a same-game parlay or refuse correlated legs. | `data/derived/corr_same_game.csv` | [FanDuel House Rules (CT)](https://www.fanduel.com/fanduel-sportsbook-house-rules-ct); [DraftKings SGP](https://support.draftkings.com/dk/en-us/what-is-a-same-game-parlay-sgp-bet?id=kb_article_view&sysparm_article=KB0010719) |
| 5 | **Player props: framework only, no numbers claimed.** No licensed, machine-readable prop-line source exists here. All 8 documented combos have measured φ **blank / UNVERIFIED**. | `data/derived/props_framework.csv` (8 rows, φ blank) | [Flagged B01](flagged.html) |

**Leaderboard consequence:** 0 reward-eligible strategies. The board pays only
gate-clearing tiers by design, so the correct current payout is zero. Simulated
no-skill families produce a "best" strategy averaging +5.4% ROI — luck, ranked,
looks exactly like skill; the gates exist to refuse that ranking.

## 2. Requirements checklist (brief → delivery)

| Requirement | Status | Where | Verification |
|---|---|---|---|
| Originate own NFL lines (no market input) | **Done** | `scripts/model.py` (4 variants, walk-forward, 6,827 games); `line_lab/` Elo/rating model | MAE reproduced exactly (§1.1) |
| Own lines for upcoming fixtures | **Done** | `data/derived/own_lines_upcoming.csv` — 164 games, 28 with a posted market line | Row counts reproduced |
| Single-bet signals | **Done** | 18 pre-registered rules (`scripts/signals.py`) + 11 (`line_lab/strategies.py`) | ROI/n/win-rate reproduced per rule |
| Parlays | **Done** | Joint-hit-rate + EV grid (`data/derived/parlay_math.csv`); 2 cross-game parlay strategies (S9/S10 root family) | Break-even φ derived analytically; EV at φ=0: 2-leg −8.88%, 3-leg −13.03% |
| Player-prop combos | **Framework done; values blank** | `scripts/props.py`, 8 combos with mechanism + required φ | Blank-φ discipline verified programmatically |
| Validation gates per strategy | **Done** | 8 gates (`scripts/gates.py`), 9 gates (`line_lab/evaluation.py`), 10 fail-closed gates (`nfl_lab/validation.py`) | 0 pass in every family — reproduced |
| Correlation values | **Done (team markets)** | Same-game, cross-game, signal-pair (`scripts/correlation.py`) | φ recomputed to 4 decimals |
| Remove luck / skill-selective strategies | **Done (as far as statistics allows)** | BH FDR, empirical-Bayes shrinkage (31.8% family shrink), block bootstrap, permutation luck band, price stress at −115, second-source robustness | Shrunk ROI published per rule; best shrunk +2.48% still fails G4 |
| Leaderboard competition + rewards | **Spec + live board; 0 eligible** | `research/leaderboard.md`; `/leaderboard.html`; eligibility-only rewards in `verified/` | Eligible count = 0 in all three systems |
| Executive summary | **Done** | This file + three prior summaries | — |
| GitHub Pages dashboard, tables, sourced rows | **Live** | Root (14 pp.), `/site/`, `/docs/`, `/verified/` (12 pp., 131 rows), `/audit/` | 0 live-surface broken links across 99 pages |
| Line-by-line official-source verification | **Done** | `research/sources.md`, `nfl_lab/sources.json` (19 primary sources), re-opened 2026-11-02 | See §6 |

## 3. Own-line origination (headline model, variant B)

| Metric | Own line | Closing line | n | Source |
|---|---|---|---|---|
| Spread MAE (pts) | 10.670 | 10.247 | 6,827 | [Pinned dataset](https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv) |
| Total MAE (pts) | 10.859 | 10.593 | 6,827 | [Pinned dataset](https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv) |
| Corr. (own spread vs close) | 0.7996 | — | 6,827 | [Pinned dataset](https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv) |
| Side agreement with market | 81.66% | — | 6,827 | [Pinned dataset](https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv) |
| Out-of-sample blend gain | **none** (+0.008 pts worse, p = 0.30) | — | 2,747 | `data/derived/blend_results.json` |

Market baselines (7,075 regular-season games, 1999–2026): home cover **48.87%**,
over **49.53%**, home win **55.94%**, ties **16**, OT games **424**. Break-even at
−110 is **52.381%** (110/210) — the bar every ROI below is measured against
([NFL Support](https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line);
[Draf
...[truncated 65 chars]