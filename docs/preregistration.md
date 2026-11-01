# Pre-registration (written before any backtest was executed)

Timestamp: 2026-11-01, before `pipeline/run_all.py` was first run. This file fixes the protocol,
the parameters, the gates and the reward rule. Nothing below was chosen after seeing results.

## 1. Universe and data

- Input: pinned `nflverse/nfldata` snapshot, commit `a270278f3ac4e937295fe6a27814b3c4a2b62645`
  (hashes in `data/raw/MANIFEST.json`, written by `pipeline/fetch_data.py`).
- Games: regular season (`game_type == "REG"`), completed games only. Postseason is evaluated
  separately as a secondary, non-rewarded cut.
- Pricing window: 2006–2025, because `games.csv` carries spread/total prices and moneylines from
  2006 onward. Games from 1999–2005 are used only to warm up ratings and to fit early models.
- Holdout: seasons 2023, 2024, 2025. These are never used to choose a parameter or a threshold.

## 2. Causality rules

- Every feature is computed from games that kicked off strictly before the game being predicted.
- Model coefficients for season *S* are fitted on seasons `< S` only (walk-forward, annual refit).
- Ratings are updated after each game in kickoff order; games at the same kickoff time are ordered
  by `game_id` for determinism (documented bias: a same-slot game cannot influence another game in
  the same slot).
- `tests/test_causality.py` recomputes the feature table on data truncated at a season boundary and
  asserts the surviving rows are identical. A strategy whose features fail this test is ineligible.

## 3. Fair-probability convention

- Two-way market prices are de-vigged with the proportional (multiplicative) method.
- Model probabilities come from a normal margin/total distribution whose mean is a walk-forward
  regression and whose sigma is the residual standard deviation of the same fit.
- Integer lines keep a modelled push probability; pushes settle at 0 units, are excluded from win
  rate, and are reported as a push rate.

## 4. Bet rule (fixed, not tuned)

A bet is placed when all of the following hold:

1. `edge = model_conditional_probability − de_vigged_market_conditional_probability ≥ 0.03`.
2. The offered price is inside `[-125, +400]` American.
3. One selection per game per market (the largest edge).
4. Flat stake of 1 unit. Profit at American odds: `+X` → `X/100`, `−Y` → `100/Y`, push → 0.

No staking plan, no bankroll model, and no bet-size scaling is evaluated; those are out of scope and
flagged as such.

## 5. Strategies (pre-registered family)

| ID | Strategy | Market |
|---|---|---|
| S1 | Elo margin model vs closing spread | ATS |
| S2 | Elo margin model vs closing moneyline | ML |
| S3 | Scoring-profile total model vs closing total | TOTAL |
| S4 | Rest asymmetry (bye/short week) | ATS |
| S5 | Divisional home underdog | ATS |
| S6 | Weather under (wind ≥ 15 mph or temp ≤ 32 °F, outdoor) | TOTAL |
| S7 | Referee crew total tendency (prior seasons only) | TOTAL |
| S8 | Backup-quarterback fade | ATS |
| S9 | Two-leg cross-game moneyline parlay built from S2 | PARLAY |
| S10 | Two-leg cross-game ATS parlay built from S1 | PARLAY |
| S11 | Season win-total futures vs scored results (2003–2020 only) | FUTURES |

S4–S8, S11 are signal rules without a fitted model; they still obey the price filter and the
one-selection-per-game rule. S9/S10 legs must come from different games (SGP dependence is measured
in `pipeline/correlations.py`, not bet here).

## 6. Metrics

Per strategy, on the evaluation window and on the holdout: bets, win rate, push rate, ROI per unit,
week-block bootstrap 95% CI (2,000 resamples, seed 20261101), one-sided bootstrap p-value,
Brier score and log loss against the de-vigged market, Brier skill score, per-season ROI,
max drawdown in units, share of profit from the best season, closing-line value where opening lines
exist, and a random-selection permutation percentile (2,000 simulations with the same weekly bet
count and side mix).

## 7. Gates (all nine must pass for reward eligibility)

| Gate | Requirement |
|---|---|
| G1 Provenance | Every bet traces to a row in the hashed input; no price or line is imputed. |
| G2 Causality | `tests/test_causality.py` passes for the features the strategy uses. |
| G3 Sample | ≥ 300 bets overall, ≥ 8 seasons, ≥ 40 holdout bets. |
| G4 Holdout | Holdout ROI > 0. |
| G5 Significance | Full-sample bootstrap CI lower bound > 0 **and** BH-FDR q ≤ 0.10 across the family. |
| G6 Market test | Brier skill ≥ 0 against the de-vigged market on all priced games in the window. |
| G7 Stability | ROI > 0 in ≥ 60 % of evaluated seasons and best season ≤ 50 % of total profit. |
| G8 Execution | ≥ 95 % of candidates priced and settled; flat stakes; push and void handling stated. |
| G9 Luck control | Random-selection permutation percentile ≥ 95. |

A gate that cannot be evaluated (for example, no opening lines in the era) is recorded as
`unverified`, never as `pass`.

## 8. Reward rule (fixed)

- Only strategies passing G1–G9 are reward-eligible.
- Eligible strategies are ranked by the holdout ROI lower confidence bound, then by Brier skill.
- Reward points: 100 × (0.6 × normalised holdout lower bound + 0.4 × normalised Brier skill),
  normalised across eligible strategies only. Ineligible strategies score blank, not zero.
- Monetary prize pool, sponsor and funding: **not established**; those cells stay blank and are
  flagged. No money is promised by this document.

## 9. Known limitations declared up front

- Bets are settled at the recorded closing price. That is the best available historical price and it
  is mildly optimistic as an execution assumption. Opening-line history exists only for 2021
  (`initial_lines.csv`, single book), so closing-line value is measurable for 2021 only.
- Player-level prop markets are outside this pre-registration because no reachable source in this
  environment provides licensed player-prop prices or official player-level game logs. They are
  published as a method + data-requirement page, with every value blank, on the Flagged page.
- A positive backtest is not a promise of future profit. Betting loses money for most participants.
