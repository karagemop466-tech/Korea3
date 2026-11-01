# Executive summary

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

The own spread model (`model_margin = 2.59 + 0.0601 × Elo difference`) is consistently 0.25–0.45 points worse than the closing line and over-predicts the home margin by ~0.92 points in the 2024–2026 holdout (bias = model minus actual). The honest read: a public-data rating model is a starting point for line origination, not a substitute for the market's information set.

## 2b. Line movement and closing-line value — the anti-luck test

- Earlier lines exist for 2,043 games (2013–2020). Mean absolute move to the close: **0.984 points**; 23.9% of games never move at all.
- The close is a better forecast than the earlier line, but only just: MAE against the actual margin improves from 10.126 to 10.049 points.
- One point of a better number is worth **4.26 percentage points** of win probability (measured by re-pricing every game, 7,384 games; 6.5% of games change result). At −110 a point must be worth more than ~2.4 pp, so line shopping is not a rounding error.
- Our line does **not** anticipate the move: correlation between model edge over the earlier line and the observed move is **0.0106**, and the directions agree on 51.0% of games.
- Betting the side our line prefers at the *earlier* line (the only way CLV is measurable here): ROI -2.2% on 1,801 bets with mean CLV +0.09 points, of which 38.8% beat the close. No skill signal.
- Closing-line value inside the main strategy backtest is exactly zero by construction, because every bet is priced at the close. Any non-zero number there would be a bug, and this is why gate G6 can only ever report n/a (F-05).

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

Pool: 1,000.0 units, paid only to strategies that pass **every** gate. Eligible strategies: **0**. The best-ranked strategy is S08 (Wind ≥ 15 mph under, full-sample ROI +10.1%, holdout -7.9%, gates 3/6).

| Rank | Strategy | Score | Gates | Full ROI | Holdout ROI | Reward |
|---|---|---|---|---|---|---|
| 1 | S08 Wind ≥ 15 mph under | 1.69 | 3/6 | +10.1% | -7.9% | 0.0 |
| 2 | S06 Divisional home dog ATS | -5.57 | 1/6 | -4.0% | +7.1% | 0.0 |
| 3 | S05 Short-week under | -6.7 | 1/6 | -1.0% | -2.0% | 0.0 |
| 4 | S02 Elo ATS edge ≥ 5 | -6.91 | 1/6 | +3.8% | -5.4% | 0.0 |
| 5 | S01 Elo ATS edge ≥ 3 | -7.75 | 3/6 | +2.5% | -5.8% | 0.0 |
| 6 | S15 Rest advantage + model agreement | -11.66 | 2/6 | -1.3% | -3.6% | 0.0 |
| 7 | S12 Fade 14+ point cover ATS | -12.35 | 1/6 | -1.7% | -0.6% | 0.0 |
| 8 | S04 Rest differential ≥ 3 days | -15.4 | 1/6 | -1.1% | -5.5% | 0.0 |

A leaderboard that pays nobody is the correct outcome here: the gates exist to stop a 1999–2023 artefact from being funded as a live edge.

## 7. Irregularities published for review

12 items are published on the Flagged for review page with their sources, including the weather-coverage discontinuity in 2022/2026, the 2021-only opening-line snapshot, and the model's holdout bias. Values that could not be confirmed were left blank rather than filled in.

## 8. What to do next (highest expected value first)

- Acquire a verified player-week dataset and a closing-prop-line feed; that unblocks the entire prop and SGP module (F-04).
- Supply a true same-week opening line for spreads and totals so closing-line value can be measured properly (F-05) — CLV is the fastest way to separate skill from luck.
- Keep the wind/under family on probation: it is the only family with a positive full-sample edge and a defensible mechanism (weather → fewer plays), and it is currently negative in the holdout.
