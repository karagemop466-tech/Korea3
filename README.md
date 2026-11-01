# NFL Line Lab

Reproducible research on originating NFL lines: eleven pre-registered betting strategies, nine validation gates,
measured correlation structure for parlay and same-game pricing, and a leaderboard that refuses to reward luck.

**Live site:** https://karagemop466-tech.github.io/Korea3/

**Status:** the research ran end to end. None of the eleven pre-registered strategies passed all nine gates, so the
leaderboard has no reward-eligible entries. That is the finding, not a failure of the build: the measured numbers below
are what a public-data model can and cannot do against closing NFL prices.

| Result | Value | Where |
|---|---|---|
| Regular-season games analysed | 7,075 (1999–2026), 5,199 in the priced 2006–2025 window | `data/derived/features.csv` |
| Selections evaluated | 16,112 in-window (16,439 including the 2026 forward cut) | `data/derived/bets.csv` |
| Reward-eligible strategies | 0 of 11 | `leaderboard.html` |
| Best full-sample ROI | +0.58% per unit (S6), 95% interval −7.51% to +8.17% | `data/derived/summary.json` |
| Best-of-11 no-skill ROI | +5.45% mean, 95th percentile +16.28%, profitable 93% of the time | `methodology.html` |
| Average two-way hold in the data | 2.66% ATS, 2.87% totals, 2.72% moneyline | `data/derived/summary.json` |
| Model vs market spread error | RMSE 13.53 vs 13.21 points; correlation 0.389 vs 0.437 | `data.html` |
| Same-game dependence (phi) | moneyline×spread 0.671; spread×total 0.016; moneyline×total 0.0003 | `correlations.html` |
| Cross-game dependence (phi) | 0.006 (two different games, same week) | `correlations.html` |
| Home × away scoring correlation | −0.051 (95% CI −0.077 to −0.024, n = 5,199) | `correlations.html` |

## What is in the repository

```
index.html … requirements.html   generated dashboard (13 pages), served by GitHub Pages from the repo root
assets/                          stylesheet and a small table-filter script, no external dependencies
pipeline/fetch_data.py           downloads the pinned nflverse snapshot and writes hashes
pipeline/core.py                 pre-game feature engineering (Elo, EWMA scoring, rest, weather, referee)
pipeline/strategies.py           the eleven pre-registered strategies, walk-forward models, settlement
pipeline/evaluation.py           metrics, week-block bootstrap, permutation test, gates, BH-FDR
pipeline/correlations.py         dependence measurements for parlays and same-game combos
pipeline/extras.py               threshold sensitivity, luck band, power table, hold calculation
pipeline/props.py                player-prop layer: blocked, with the required input schema and estimator
pipeline/run_all.py              orchestrates everything and writes summary.json
pipeline/build_site.py           renders every page from summary.json
pipeline/check_site.py           link, source and value checks for the generated site
tests/test_causality.py          provenance hashes, truncation test, settlement and odds checks
data/raw/                        pinned input files plus MANIFEST.json (sha256, rows, source URL)
data/derived/                    features, bets, summary, test report, coverage
docs/preregistration.md          the frozen protocol, written before the first backtest
docs/requirements.md             every stated requirement mapped to its evidence
EXECUTIVE_SUMMARY.md             the one-page brief
COORDINATION.md                  parallel-session task board and session log
```

## Reproduce

```bash
python3 pipeline/fetch_data.py     # pinned snapshot + hashes
python3 tests/test_causality.py    # provenance, causality, settlement
python3 -m pipeline.run_all        # backtests, gates, correlations, summary.json
python3 -m pipeline.build_site     # rebuild the 13 pages
python3 pipeline/check_site.py     # links, sources, no fabricated values
```

Requires Python 3.11 with `pandas` and `numpy`. The pipeline is deterministic: seeds are fixed, the input snapshot is
pinned by commit and sha256, and every number on the site is rendered from `data/derived/summary.json`.

## Data and provenance

Inputs are the nflverse `nfldata` files at commit [`a270278`](https://github.com/nflverse/nfldata/commit/a270278f3ac4e937295fe6a27814b3c4a2b62645):

- `games.csv` — schedules, final scores, closing spread/total/moneylines and prices (hashes in `data/raw/MANIFEST.json`)
- `closing_lines.csv`, `initial_lines.csv`, `win_totals.csv`, `teams.csv`

Field meanings were checked against the nflverse data dictionary
([`dictionary_schedules.csv`](https://github.com/nflverse/nflreadr/blob/23f915a5be30415aeaa0c5c80cd23b2c69cda122/data-raw/dictionary_schedules.csv)),
including the sign convention for `spread_line`, which was additionally re-verified against results in this repository.
nflverse is an independent open-source distributor of NFL data, not an NFL-operated service; the site says
"official-derived" for that reason.

## Honest limits

- Bets are settled at the recorded **closing** price, which assumes a bettor could transact at the close. Every ROI is
  therefore an upper bound. Opening-line history exists only for 2021.
- Player-prop markets are **blocked**: no reachable source in this environment provides official player game logs or
  licensed prop prices, so no prop coefficient or ROI is published anywhere.
- The odds vendor behind the price columns is not documented by the publisher.
- External sources (NFL.com, NIST, sportsbook help pages) cannot be reached from the research sandbox and are marked as
  citations rather than verified sources.
- Every one of these items is listed on the [Flagged for review](https://karagemop466-tech.github.io/Korea3/flagged.html) page.

## Not advice

This is research, not betting advice, and not a promise of profit. Betting loses money for most participants; the
measured vig in this dataset is roughly 2.8% per two-way market before any model error is added.
