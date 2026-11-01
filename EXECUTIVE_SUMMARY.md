# Executive summary

**Project:** originate NFL lines, build a competition that rewards skilled strategies, and remove luck from the
selection process.
**Delivered:** a reproducible research pipeline, a 13-page dashboard published on GitHub Pages, and a full audit trail
from raw file hash to on-page number.
**Result:** no strategy is reward-eligible. Zero of eleven pre-registered strategies passed all nine validation gates.
**Published site:** https://karagemop466-tech.github.io/Korea3/

---

## 1. What was built

| Layer | What it does | Where |
|---|---|---|
| Ingestion | One pinned nflverse snapshot, hashed on download, with row counts and source URLs recorded | `pipeline/fetch_data.py`, `data/raw/MANIFEST.json` |
| Features | Elo ratings, 4-game EWMA scoring profiles, rest, weather, referee tendency, quarterback change — all strictly pre-game | `pipeline/core.py` |
| Models | Walk-forward margin and totals regressions refit for every season on prior seasons only | `pipeline/strategies.py` |
| Strategies | 11 pre-registered candidates across spread, total, moneyline, parlays and season-win futures | `docs/preregistration.md` |
| Validation | 9 gates: provenance, causality, sample, holdout, significance, market test, stability, execution, luck | `pipeline/evaluation.py` |
| Correlation | phi for every measurable leg pair, plus conditional probabilities, with week-block bootstrap intervals | `pipeline/correlations.py` |
| Luck control | Week-block bootstrap, permutation test, Benjamini–Hochberg across the family, and a measured "best-of-11" null | `pipeline/extras.py` |
| Line origination | Model spread, total and win probabilities for unplayed games | `lines.html` |
| Site | Dashboard generated entirely from `summary.json`, verified by a build check | `pipeline/build_site.py`, `pipeline/check_site.py` |

## 2. Headline numbers

| Metric | Value |
|---|---|
| Completed regular-season games in the snapshot | 7,075 (1999–2026) |
| Games in the priced evaluation window | 5,199 (2006–2025) |
| Games with two-sided ATS prices | 5,065 (97.4%) |
| Selections evaluated in-window | 16,112 |
| Strategies passing all nine gates | 0 of 11 |
| Best full-sample ROI | +0.58% per unit (S6 weather under), 95% CI −7.51% to +8.17% |
| Worst full-sample ROI | −14.72% (S11 win-total futures) |
| Average bookmaker hold in the data | 2.66% ATS / 2.87% totals / 2.72% moneyline |
| Best-of-11 no-skill ROI (2,000 simulations) | +5.45% mean; +16.28% at the 95th percentile; a profitable "winner" 93% of the time |
| Bets needed to detect a 3% edge at 80% power | ≈ 6,200 (≈ 8 seasons at 750 bets per season) |
| Spread model vs market | RMSE 13.53 vs 13.21 points; correlation with result 0.389 vs 0.437 |
| Brier skill vs de-vigged market | −3.2% (spread), −3.9% (moneyline), −1.9% (totals) |

## 3. What the research found

1. **The market is not beaten by public game-level data at this sample.** Every model strategy lost between 0.9% and
   1.6% per bet before costs; the signal strategies ranged from +0.6% to −4.3%. Nothing is close to the vig-adjusted
   break-even line in a statistically meaningful way.
2. **Being nearly as accurate as the market is worth nothing.** The spread model's error is 0.33 points worse than the
   closing line. That is small in football terms and fatal in betting terms, because the ROI is already negative before
   that error is priced in.
3. **A small leaderboard manufactures winners.** Eleven no-skill strategies of the same size produce a best-ROI
   distribution centred at +5.45%, and a profitable top entry 93% of the time. Any competition that ranks raw backtest
   ROI without a null model is selling noise. Our gates exist to prevent exactly that.
4. **Same-game legs are not independent; cross-game legs are.** Measured phi: moneyline × spread **0.671**,
   spread × total **0.016**, moneyline × total **0.0003**, two different games in the same week **0.006**. Pricing an
   "ML + spread" same-game parlay by multiplying marginals understates the joint probability by roughly half
   (43.8% measured joint against 27.1% product).
5. **"Shootout" narratives are not supported.** Home and away scoring are slightly *negatively* correlated
   (r = −0.051, 95% CI −0.077 to −0.024), so combo legs that both require high scoring in the same game do not get the
   positive boost the story implies.
6. **Cross-game parlays are structurally fair and still bad value.** Legs are effectively independent
   (phi 0.006), so there is no mispricing to exploit — only the multiplicative hold. The S9 card lost 0.47% per card
   over 338 cards; the S10 card lost 7.92%.
7. **Selectivity is not the same as skill.** Raising the edge threshold makes the headline ROI look better
   (+1.2% at a 7-point threshold for S1, +2.4% at 10 points for S3) while shrinking the sample. Those gains sit inside
   the measured luck band, so they are published as exploratory, never as reward-eligible.

## 4. What is blocked

| Item | Why | Consequence |
|---|---|---|
| Player-prop combos and prop correlations | No reachable official player-level game log, and no licensed prop line/price archive | All prop values blank; estimator written and ready |
| Closing-line value over time | Only 2021 has opening lines (one book) | Cannot prove any strategy beats the close across years |
| Executable-price realism | Settlement uses recorded closing prices | Every ROI is an upper bound |
| Monetary rewards | No funded pool, sponsor or escrow | Reward points only; prize money blank |
| Odds vendor identity | Publisher does not document the source of the price columns | Price provenance is flagged |

## 5. Recommendation

Do not stake money on any strategy in this repository. The correct next steps, in order of expected value:

1. **Buy or licence intraday and prop price history** (opening, mid, close, and player props by book). The pipeline
   already consumes closing prices; adding timestamps converts every ROI from an upper bound into a measurement.
2. **Re-run the same gates on the new price data.** The code is deterministic and the gates are frozen, so the
   comparison across rounds is legitimate rather than retrospective.
3. **Attack the market test first.** Strategies should be judged on Brier skill against the de-vigged market before any
   ROI is discussed; the current family fails that test everywhere, which is why the ROI discussion is moot.
4. **Keep the competition closed until a candidate passes all nine gates.** With a 93% chance that a no-skill family
   produces a profitable winner, paying prizes on raw ROI is equivalent to paying for luck.

## 6. Verification and sources

- Input data: nflverse `nfldata` at commit `a270278f3ac4e937295fe6a27814b3c4a2b62645`, sha256 recorded per file in
  `data/raw/MANIFEST.json` and re-verified by `tests/test_causality.py`.
- Field definitions: nflverse `dictionary_schedules.csv` (spread sign, rest, roof, temperature, wind, referee).
- Every table row on the site carries a source link; the build check fails if a row has none or if a blank is rendered
  without a link to the review page.
- External citations (NFL.com, NIST, sportsbook help pages) are unreachable from the research sandbox and are marked
  as unverified citations, not as verified facts. They are enumerated on `flagged.html`.
- Full limitations list: [`flagged.html`](https://karagemop466-tech.github.io/Korea3/flagged.html).

**This is research, not betting advice. Betting loses money for most participants.**
