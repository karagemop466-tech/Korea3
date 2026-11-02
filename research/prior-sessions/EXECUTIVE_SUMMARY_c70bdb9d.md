# Executive summary

**Project:** NFL line origination, signal research, validation, correlation and a strategy leaderboard
**Snapshot:** 2026-11-01 (UTC) · **Session:** `session-c70bdb9d` · **Site:** <https://karagemop466-tech.github.io/Korea3/>
**Full version with tables and sources:** [`docs/executive-summary.html`](docs/executive-summary.html)

---

## Bottom line

1. **We built a real own line and the market beat it.** The model produces a spread and a total with no market input, walk-forward, on 6,827 games. Its spread error is 10.670 points per game against 10.247 for the closing line — a 0.423-point deficit, p ≈ 4.9e-24, and consistent across nine hyper-parameter settings. Origination works as research; it does not work as edge.
2. **Nothing passed all eight validation gates.** 18 rules were tested; the best raw result is +8.41% ROI over 607 bets, which fails only the multiplicity gate (q = 0.288). Four rules clear seven of eight and sit in a *provisional* tier: worth tracking, not worth staking.
3. **Parlays are worse, and now we can say exactly why.** Spread × total correlation measures φ = +0.0086 (95% CI −0.0162 to +0.0332) — zero. A two-leg parlay priced at −110 needs φ ≥ 0.0975 to break even. The gap between those two numbers is the house's margin on same-game parlays.
4. **The one genuinely correlated pair is already priced.** Moneyline × spread on the same team correlates at φ = 0.672 (joint 43.9% vs 27.2% if independent). Every licensed operator either re-prices it as a same-game parlay or reserves the right to void it.
5. **Player props are framework-only, deliberately.** No verifiable prop-line source exists in this environment, so no prop correlation is claimed. Eight combos are documented with mechanism and required φ; every measured value is blank and flagged.

## What was delivered

| Deliverable | Where |
|---|---|
| Own-line model (4 variants, 9-setting sensitivity grid, out-of-sample blend test) | `scripts/model.py`, `scripts/blend.py`, site → *Our Own Line* |
| 18 pre-registered signals with discovery/confirmation split | `scripts/signals.py`, site → *Signal Library* |
| 8 validation gates incl. FDR control and empirical-Bayes shrinkage | `scripts/gates.py`, site → *Validation Gates* |
| Correlation lab (same-game, cross-game, strategy-pair, parlay arithmetic) | `scripts/correlation.py`, site → *Correlation Lab*, *Parlays* |
| Player-prop combo framework | `scripts/props.py`, site → *Player Props* |
| Leaderboard competition: scoring, tiers, rewards, anti-gaming rules | `research/leaderboard.md`, site → *Leaderboard* |
| Pinned, checksummed data with row-level provenance | `data/provenance.json`, `data/derived/checksums.txt` |
| Verification pipeline that fails the build | `scripts/verify_site.py`, site → *Verification Log* |
| Flagged-for-review register (24 items) | site → *Flagged for Review*, `research/flagged.md` |

## Key numbers

| Metric | Value | Source |
|---|---|---|
| Games modelled (regular season, priced, completed) | 7,075 | pinned `games.csv` |
| Games with walk-forward own lines | 6,827 (2000–2026) | `model_predictions.csv` |
| Own spread MAE / market spread MAE | 10.670 / 10.247 | `model_metrics.json` |
| Own total MAE / market total MAE | 10.859 / 10.593 | `model_metrics.json` |
| Correlation of own spread with the close | 0.7996 | `model_metrics.json` |
| Side agreement with the market | 81.66% | `model_metrics.json` |
| Own-line information beyond the close (spread) | coefficient +0.118, p = 0.011 | `blend_results.json` |
| Out-of-sample blend improvement | **none** (−0.008 pts worse, p = 0.30) | `blend_results.json` |
| Rules tested / passed / provisional / failed | 18 / 0 / 4 / 14 | `gates_meta.json` |
| Best rule (S14, wind unders) | +8.41% ROI, n = 607, q = 0.288, luck-adj. +2.48% | `gates_results.csv` |
| Share of measured edge attributable to luck | 31.8% (family mean shrink) | `gates_meta.json` |
| Home cover rate / over rate | 48.87% / 49.53% | `market_summary.json` |
| Spread × total φ | +0.0086 (−0.0162 … +0.0332) | `corr_same_game.csv` |
| Cross-game pooled φ | −0.0239, p = 0.10 → independent | `corr_meta.json` |
| Break-even φ (2 legs @ −110 / 3 legs) | 0.0975 / 0.0749 | `corr_meta.json` |
| Own lines published for unplayed fixtures | 164 (28 with a market line to compare) | `own_lines_upcoming.csv` |

## Validation gates

| Gate | Requirement | Rules passing |
|---|---|---|
| G1 Sample size | n ≥ 200 (≥ 100 confirmation) | 17 / 18 |
| G2 Positive expectation | ROI > 0 | 5 / 18 |
| G3 Both windows | ROI > 0 in 2000–15 **and** 2016–26 | 5 / 18 |
| G4 Multiplicity | BH q ≤ 0.10 | **0 / 18** |
| G5 Concentration | no season > 50% of profit; ≥ 50% positive seasons | 13 / 18 |
| G6 Price stress | profitable at −115 | 5 / 18 |
| G7 Line-source robustness | profitable vs second line source | 9 / 18 (2 n/a) |
| G8 Luck-adjusted edge | shrunk ROI ≥ 0.5% | 6 / 18 |

G4 is the binding constraint for every serious candidate. That is the honest outcome of searching an 18-rule family: **the search itself is the reason nothing can be promoted yet.**

## Irregularities and unverified items (published, not hidden)

**Found in the data**

- The source dataset signs spreads **opposite** to the conventional home spread. Undetected, this inverts every ATS result. Caught because the first build produced a 59.99% home cover rate; verified two independent ways and fixed in `build_dataset.py`.
- Two in-dataset line sources disagree: 67.3% exact agreement on spreads, 61.7% on totals. Handled as gate G7 rather than ignored.
- `'grass '` trailing-space duplicate (93 rows), missing environment values, and 2,213 rows where temperature/wind exist with **no provenance field at all**.
- 26.9% of games have no recorded price; −110 is substituted and the imputed share is published per rule.

**Found in official sources**

- Two NFL Support article bodies are **swapped** (the "money line" article explains the point spread and vice versa). Both are cited, both are flagged.
- The DraftKings house-rules copy used for prop participation rules is dated **2023-06-01** and may be superseded.
- The repository is named `Korea3` and contained only an 8-byte README at the start of this session. Neither was changed; both are recorded.

**Deliberately left blank** (no official source available): all player-prop prices and prop correlations, weather ground truth, injury/inactive status, venue coordinates/travel, and pre-2021 opening lines.

## What a follow-up session should do first

1. **Prop lines** — a licensed feed turns the prop framework into research. Until then B01 stays open.
2. **Injuries/inactives** — the largest single gap in the feature set.
3. **More sample on the four provisional rules** — each needs a specific number of additional bets (published per rule); this is a data-collection problem, not a modelling one.
4. **A fixed-horizon snapshot design** so multiplicity stays controlled across time, not just within one run.

## Honest statement of what is not claimed

- No claim that any strategy here is profitable.
- No claim that a rule which failed here cannot work — only that *this* rule, on *this* data, does not clear *this* bar.
- No prop correlation values, because none could be verified.
- No claim of parallel-session work: this run was one session, and `COORDINATION.md` says so.
