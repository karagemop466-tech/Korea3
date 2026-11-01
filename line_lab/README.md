# line_lab — the root dashboard's pipeline

This package builds the dashboard served at the repository root: eleven pre-registered strategies, nine
validation gates, measured correlation structure, a luck band, live model lines and a full audit trail.

Everything published is generated from one file, `data/derived/summary.json`, which is itself produced from the
pinned snapshot in `data/raw/` (sha256 in `MANIFEST.json`).

## Run it

```bash
python3 line_lab/fetch_data.py          # pinned nflverse/nfldata snapshot + hashes
python3 line_lab/tests/test_causality.py  # provenance, causality, settlement, odds checks
python3 -m line_lab.run_all             # backtests, gates, correlations, summary.json, bets.csv
python3 -m line_lab.build_site          # rewrite the 14 root pages from summary.json
python3 line_lab/check_site.py          # links, per-row sources, blank flags, number reconciliation
```

Requires Python 3.11 with `pandas` and `numpy`. Fixed seeds, pinned commit, deterministic output.

## Map

| File | Role |
|---|---|
| `fetch_data.py` | download + hash the pinned snapshot |
| `core.py` | strictly pre-game features (Elo, EWMA scoring, rest, weather, referee, QB change) and unplayed-game state |
| `markets.py` | odds conversion, de-vig, model probabilities, settlement |
| `strategies.py` | the eleven pre-registered strategies with walk-forward refits |
| `evaluation.py` | metrics, week-block bootstrap, permutation test, nine gates, BH-FDR, reward scoring |
| `correlations.py` | same-game, cross-game and parlay dependence measurements |
| `extras.py` | threshold sensitivity, best-of-N luck band, power table, bookmaker hold |
| `props.py` | player-prop layer: blocked, with the required schema and estimator |
| `run_all.py` | orchestration, live line origination, `summary.json` |
| `build_site.py` | renders the 14 pages (including `sessions.html`) from `summary.json` |
| `check_site.py` | build verification: broken links, missing sources, unflagged blanks, number drift |
| `tests/test_causality.py` | truncation test, hash verification, independent settlement recomputation |
| `docs/preregistration.md` | the protocol, frozen before the first backtest |
| `docs/requirements.md` | every requirement mapped to its evidence |

## Headline results

0 of 11 strategies passed all nine gates. Best full-sample ROI +0.58% (95% CI −7.51% to +8.17%) against a
measured best-of-11 luck band centred at +5.45%. Same-game moneyline×spread dependence φ = 0.671; cross-game
φ = 0.006; home×away scoring r = −0.051. Full detail on the live site.

Research only. Not betting advice.
