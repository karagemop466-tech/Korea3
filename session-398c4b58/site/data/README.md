# Site data dictionary

Every number rendered on the dashboard comes from one of these files. They are produced by
`scripts/run_all.py` and `scripts/verify_external.py`; nothing on the site is typed by hand.

| File | Contents |
|---|---|
| `meta.json` | Run metadata: counts, dataset commit, model quality, leakage-guard result, software versions. |
| `market.json` | Hold by market, break-even rates, base rates, favourite–longshot table, margin distribution, line movement. |
| `model.json` | Model quality metrics and the fitted coefficients/sigmas per season. |
| `strategies.json` | The strategy registry (id, name, category, verbatim rule) and every strategy's full result record. |
| `leaderboard.json` | Luck-adjusted scores, tiers, reward points, allocation weights and ranks. |
| `parlays.json` | Parlay/SGP results plus the cross-game independence and same-game joint-probability tests. |
| `props.json` | Prop-market diagnostics (push rate, calibration bins, Brier scores), probability maps, results. |
| `correlations.json` | All correlation estimates with bootstrap confidence intervals. |
| `validation.json` | Gate definitions and the per-strategy gate matrix. |
| `luck.json` | Zero-skill simulation bands, p-values, Sharpe/skew/kurtosis, edge-monotonicity buckets. |
| `lineboard.json` | Our originated spread/total for every 2026 game, with the market number where one exists. |
| `sources.json` | Copy of the data provenance record (URLs, commits, SHA-256, row counts). |

Field notes:
* `roi` is always profit ÷ total stake, flat 1.00 unit per bet.
* `p_value_vs_market` is one-sided: the share of 10,000 zero-skill simulations whose ROI matched or
  beat the observed ROI.
* `prices_observed` is false when a strategy's price had to be assumed (props, same-game combos).
* A JSON `null` means the value could not be computed or verified. The site renders it as `—`.
