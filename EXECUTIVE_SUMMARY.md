# Executive summary

<<<<<<< HEAD
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
=======
**Scope.** Originate NFL lines, research signals, test single bets, parlays and player-prop structures, and only promote a strategy that passes every validation gate. Everything below is computed by the scripts in `pipeline/` from the files in `data/`; the build date is 2026-11-01.

## 1. Data is verified before anything is modelled

- 7,384 played games, 1999–2026, 35 distinct team codes (relocations included), 0 duplicate game ids.
- Team-aggregate reconciliation against nfl.com official standings (2025 season and the 2026 games played at build time): **64/64 rows matched** (match rate 100.0%), covering the outcome of 380 games. This is a W/L/T/PF/PA reconciliation, **not** a per-game official verification (F-11).
- Data rights: NFL.com's terms restrict systematic retrieval and reproduction and this project holds no NFL licence, so the official values used for that check were removed from the repository and only an attestation (counts, URLs, date) remains (F-10). Published tables contain our own arithmetic from the open dataset plus the match status and the official link.
- Sign conventions were confirmed against the upstream field documentation and empirically: `spread_line` positive = home team favoured; mean(home margin − spread) = 0.062 points and the cover rate excluding pushes is 48.9%.
- Market base rates in this dataset: home cover 48.9%, over 49.5% — i.e. the closing market is efficient to within rounding.

## 2. Own lines can be originated, but they are not yet good enough to beat the market

| Window | Model MAE (points) | Market MAE | Model corr | Market corr |
|---|---|---|---|---|
| design (n=5,316) | 10.670 | 10.435 | 0.371 | 0.415 |
| validation (n=1,390) | 10.344 | 9.878 | 0.380 | 0.438 |
| holdout (n=678) | 10.174 | 9.635 | 0.384 | 0.474 |

The own spread model (`model_margin = 2.59 + 0.0601 × Elo difference`) is consistently 0.25–0.45 points worse than the closing line and under-predicts home margin by ~1 point in the 2024–2026 holdout. The honest read: a public-data rating model is a starting point for line origination, not a substitute for the market's information set.

## 3. Signal research: 56 mechanical tests, one survives multiplicity control, none survives the holdout

- Tests run: **56**; positive in the full sample: **15**; surviving Benjamini-Hochberg at 5%: **1**; positive in *both* out-of-sample windows: **4**.
- At a 5% false-discovery rate you would expect about 2.8 false positives from 56 tests with no real signal — which is exactly the scale of what survives.
- The strongest raw signal is **Wind ≥ 12 mph → under**: n=1,304, ROI +8.5%, t=3.227, BH-adjusted p=0.035. But the holdout says -7.0% — the edge is a 1999–2023 phenomenon, not a live edge.

## 4. Parlays and same-game correlation: the only place with large, repeatable structure

- Spread and total legs are effectively independent: phi(home cover, over) = 0.0159 (95% CI -0.0074 to 0.0392), n=7,080.
- Moneyline and spread legs on the same team are strongly dependent: phi = 0.6721 (95% CI 0.6591 to 0.6847), measured joint probability 44.1% versus 27.4% if multiplied.
  - `Home wins outright  +  home covers`: a book that multiplied two -110 legs independently would pay 3.645 decimal against a fair 2.270; measured EV per unit at that price +60.6%. Real books apply correlation-aware pricing, so this is a map of pricing error, not a free bet (F-07).
  - `Home team covers  +  game goes OVER`: a book that multiplied two -110 legs independently would pay 3.645 decimal against a fair 4.064; measured EV per unit at that price -10.3%. Real books apply correlation-aware pricing, so this is a map of pricing error, not a free bet (F-07).
- Cross-game control: two unrelated games in the same week agree on the home-cover outcome 49.4% of the time — independence holds across games, so correlation work must be done inside a game.
- Team scoring is over-dispersed (variance/mean = 4.72), so prop models need a negative-binomial / mixture structure rather than Poisson.

## 5. Player props: framework and gates delivered, numbers withheld

- Player-week statistics could not be obtained from any verifiable source in this build environment (the nflverse release host is blocked from the build sandbox and every reachable mirror is a truncated or synthetic fixture). **No prop line, prop baseline or prop correlation is published as a number** (F-04).
- What is delivered: market-by-market model specification, the five-gate prop validation set, the sample sizes needed to measure a prop-pair correlation to ±0.10, and the verified team-level anchors (home/away points correlation, total dispersion, key numbers) that any prop model must reproduce.

## 6. Leaderboard and rewards

Pool: 1,000.0 units, paid only to strategies that pass **every** gate. Eligible strategies: **0**. The best-ranked strategy is S08 (Wind ≥ 15 mph under, full-sample ROI +10.1%, holdout -7.9%, gates 4/7).

| Rank | Strategy | Score | Gates | Full ROI | Holdout ROI | Reward |
|---|---|---|---|---|---|---|
| 1 | S08 Wind ≥ 15 mph under | 1.69 | 4/7 | +10.1% | -7.9% | 0.0 |
| 2 | S06 Divisional home dog ATS | -5.57 | 2/7 | -4.0% | +7.1% | 0.0 |
| 3 | S05 Short-week under | -6.7 | 2/7 | -1.0% | -2.0% | 0.0 |
| 4 | S02 Elo ATS edge ≥ 5 | -6.91 | 2/7 | +3.8% | -5.4% | 0.0 |
| 5 | S01 Elo ATS edge ≥ 3 | -7.75 | 4/7 | +2.5% | -5.8% | 0.0 |
| 6 | S15 Rest advantage + model agreement | -11.66 | 3/7 | -1.3% | -3.6% | 0.0 |
| 7 | S12 Fade 14+ point cover ATS | -12.35 | 2/7 | -1.7% | -0.6% | 0.0 |
| 8 | S04 Rest differential ≥ 3 days | -15.4 | 1/7 | -1.1% | -5.5% | 0.0 |

A leaderboard that pays nobody is the correct outcome here: the gates exist to stop a 1999–2023 artefact from being funded as a live edge.

## 7. Irregularities published for review

12 items are published on the Flagged for review page with their sources, including the weather-coverage discontinuity in 2022/2026, the 2021-only opening-line snapshot, and the model's holdout bias. Values that could not be confirmed were left blank rather than filled in.

## 8. What to do next (highest expected value first)

- Acquire a verified player-week dataset and a closing-prop-line feed; that unblocks the entire prop and SGP module (F-04).
- Supply a true same-week opening line for spreads and totals so closing-line value can be measured properly (F-05) — CLV is the fastest way to separate skill from luck.
- Keep the wind/under family on probation: it is the only family with a positive full-sample edge and a defensible mechanism (weather → fewer plays), and it is currently negative in the holdout.
>>>>>>> origin/main
