# Methodology — research notes

The authoritative, reader-facing version is on the site: **`docs/methodology.html`**.
This file records the decisions and the reasoning behind them.

## 1. Definition of "originating a line"

An own line is a number produced **before** the market's number is allowed to influence it. Concretely:

- The model is fitted on games strictly earlier than the first kickoff of the week being predicted.
- No market input of any kind enters the model's features (no closing spread, no total, no moneyline).
- Competing models are compared on out-of-sample error, not on betting profit — profit is noisier than error and would let a lucky model look good.

## 2. Model

```
points(team) = μ + offence[team] + defence[opponent] + hfa·home + β·situational
own_spread   = −(pred_home_pts − pred_away_pts)      # conventional home orientation
own_total    = pred_home_pts + pred_away_pts
```

- Ridge penalty λ = 4.0 on team-rating columns, ~0 on the intercept and situational terms.
- Recency weighting: `w = 0.5 ** (days_before_cutoff / 365)`.
- Three seasons of history; a minimum of 240 prior games before any prediction is published.
- Neutral-site games carry no home-field term.
- 486 refits (27 seasons × ~18 weeks).

Hyper-parameters were fixed **before** evaluation. The nine-setting sensitivity grid
(λ ∈ {1, 4, 16} × half-life ∈ {180, 365, 730}) is published so a reader can confirm the
conclusion does not depend on the choice.

## 3. Backtest discipline

| Rule | Implementation |
|---|---|
| Price | Actual recorded price per side; −110 fallback where missing (share published per rule) |
| Pushes | Stake returned; excluded from win-rate and ROI denominators |
| Bet size | Flat 1 unit |
| Windows | Discovery 2000–2015; Confirmation 2016–2026; fixed before evaluation |
| Rule count | 18 rules, all published, none dropped |
| Benchmark | Closing line, not opening line — the hardest benchmark available |

## 4. Statistics

- Break-even at −110: `110/210 = 0.52381`.
- Exact one-sided binomial test per rule against that break-even.
- Percentile bootstrap (10,000 resamples, seed 20261101) for ROI confidence intervals.
- Benjamini–Hochberg FDR across the whole family, q ≤ 0.10.
- Coin-flip Monte Carlo: 20,000 simulated break-even bettors over the same bet count and prices.
- Empirical Bayes: `τ² = max(0, Var(observed edges) − mean(SE²))`, shrink factor `τ²/(τ² + SE²)`.
- Paired t-tests for model-vs-market absolute error.

## 5. Why these choices

**Why the closing line as benchmark?** Because it is the number that reflects everything
informed money knew. Beating an opening line that later moved against you is not skill.

**Why FDR rather than a stricter family-wise correction?** Because the output of this
exercise is a *ranked list of candidates*, not a single yes/no claim. FDR controls the
share of false claims among the things promoted, which matches the leaderboard's purpose.

**Why empirical Bayes on top of the p-values?** They answer different questions. The
p-value asks "could this be luck?" The shrunk estimate asks "how much edge should I
believe in, given that I searched and most edges are noise?" A leaderboard needs the
second number, because it has to rank things rather than accept or reject them.

**Why publish failures?** A board that only shows winners measures survivorship, not skill.
14 of 18 rules lose money and they are all on the site.

## 6. Known limitations

1. **No injury/inactive data** — probably the single biggest modelling gap.
2. **No player-level data at all**, so props were framework-only.
3. **26.9% price imputation** at −110.
4. **One dataset, one primary book** — cross-book disagreement is real and measured (67.3% exact match).
5. **No CLV study before 2021** (opening lines unavailable).
6. **Survivorship** is not an issue for this dataset (complete seasons), but must be re-checked on any future scrape.
7. **Multiplicity over time** is not controlled — repeated monthly snapshots are many looks at one process; a fixed-horizon design would be stricter.
