# NFL Line Origination & Strategy Research — Executive Summary

**Project:** originate our own NFL numbers, generate tradeable signals, rank strategies on a
leaderboard, and separate skill from luck.
**Session:** `sess-398c4b58` · **Generated:** 2026-11-01 · **Repo:** `karagemop466-tech/Korea3`
**Live site:** GitHub Pages (see repository Pages URL)

---

## 1. What was built

A reproducible research pipeline (Python, stdlib + numpy/pandas only) that runs end to end with
`python3 scripts/run_all.py` and regenerates every number shown on the site.

| Component | Output |
|---|---|
| Data acquisition, pinned to a commit, SHA-256 per file | `data/raw/*`, `data/PROVENANCE.json` |
| Point-in-time feature layer (Elo + off/def form + rest + venue) | `data/derived/features.csv` |
| Walk-forward model that originates its own spread and total | `data/derived/predictions.csv` |
| 28 mechanical strategies: singles, parlays, same-game, player props | `data/derived/bets.csv` |
| 9 validation gates + luck-removal statistics | `docs/data/validation.json`, `luck.json` |
| Correlation estimates for parlay and same-game pricing | `docs/data/correlations.json` |
| External verification + whole-file integrity checks | `data/verification.json` |

Backtest universe: **6,340 completed games (2003–2026)** with a closing spread and total, and
**73,265 individual bet records**. All bets are settled against real closing prices where those
prices exist in the source data.

## 2. Headline findings

1. **Our own number is good, but not better than the market.** The model's spread error is
   13.58 points RMSE versus the market's 13.16; correlation with the actual margin is 0.367
   versus the market's 0.432. Line origination is credible (it tracks the market closely), but
   it is *not* a superior forecast on average. Any edge has to come from specific situations,
   not from general accuracy.

2. **Nothing survives the full validation gauntlet.** Of 28 strategies, **zero pass all nine
   gates**. The strongest is *fade the big favourite* (S08): +7.60% ROI on 494 bets, bootstrap
   95% CI −0.7% to +15.8%, p = 0.024 against the zero-skill (de-vigged market) simulation — but
   it fails the multiple-testing gate and the season-consistency gate (profitable in 55% of
   seasons, below the 60% threshold). Its held-out ROI (2023–2025) is +0.04%, i.e. nothing.

3. **The vig is the whole game.** Median hold is ~2.4–2.9% depending on market; at a −110 price
   you need **52.38%** to break even. Benchmark strategies land where theory says they should:
   always-home **−4.88%**, always-over **−3.41%**, coin-flip **−5.73%**, always-favourite
   **+0.21%**. Anything under about 1% ROI is indistinguishable from noise at these sample sizes.

4. **Spread and total are essentially uncorrelated.** Measured r = **0.020** (95% CI −0.003 to
   0.043) across 6,340 games; the joint empirical probability of "home ATS + over" is 2.2%
   *higher* than the product of the two rates. Practical consequence: the popular
   "same-game correlation edge" on spread/total combos **does not exist**. A book that prices
   them multiplicatively is roughly correct.

5. **Legs from different games really are independent** (r = −0.003, 95% CI −0.029 to 0.022),
   so standard cross-game parlay multiplication is sound. Parlay ROI is dominated by variance:
   the 3-leg parlay shows +13.5% ROI on 370 bets with a CI lower bound of −13.7%. That is a
   coin-flip dressed up as an edge.

6. **Player props have the largest raw "edge" and the least evidence.** Against a *synthetic*
   stale line (trailing 8-game median), under-bets return +13% to +18% with p < 0.0001. But the
   model's Brier score is 0.2439–0.2484 versus 0.25 for a coin flip: a ~1–2% improvement in
   forecasting skill. The apparent ROI measures **how stale the synthetic line is**, not skill
   against a real book. No verifiable prop price exists in this environment, so these strategies
   are flagged *price-unverified* and excluded from the leaderboard rankings.

7. **Prop co-movement is where real correlation lives.** Team-mate receivers are *positively*
   correlated (+0.136, contrary to the "target competition" intuition), QB attempts and lead
   receiver yards +0.293, and the same player's targets/receptions +0.920. A book that multiplied
   same-player legs naively would be beaten badly — which is why real books adjust those prices.

8. **Mature markets are efficient in the way textbooks say.** Favourites priced −200 to −150 won
   57.7% against a de-vigged 61.8% (a −9.2% ROI for favourite backers); home dogs at +250 or
   longer won 23.4% against a de-vigged 22.1% (+4.2% ROI). The favourite–longshot bias is small
   but visible.

## 3. Leaderboard (ranked by luck-adjusted score, observed prices only)

| Rank | Strategy | ROI | 95% CI (bets) | p vs luck | Gates | Tier |
|---|---|---|---|---|---|---|
| 1 | S08 Fade the big favourite | +7.60% | −0.7% … +15.8% | 0.024 | 7/9 | B |
| 2 | S05 Selective total edge | +3.89% | −1.8% … +9.8% | 0.032 | 6/9 | C |
| 3 | P02 Three-leg parlay | +13.48% | −13.7% … +41.4% | 0.057 | 6/9 | C |
| 4 | S09 Dome totals | −3.51% | −10.4% … +3.4% | 0.690 | 5/9 | D |
| 5 | S06 Rest advantage | +0.91% | −7.7% … +9.6% | 0.324 | 5/9 | D |

Score = 40% gates passed + 30% ROI confidence-interval lower bound + 15% luck-null evidence +
15% season consistency. Tier A (all gates) is empty.

## 4. Correlation values (for pricing combos)

| Combo | r | 95% CI | n |
|---|---|---|---|
| Game margin × game total | 0.020 | −0.003 … 0.043 | 6,340 |
| Home ATS × over | 0.019 | −0.007 … 0.043 | 6,340 |
| Moneyline winner × ATS winner | 0.649 | 0.629 … 0.669 | 5,403 |
| Same-week cross-game ATS | −0.003 | −0.029 … 0.022 | 5,703 |
| Team-mate #1 × #2 receiver yards | 0.136 | 0.113 … 0.158 | 7,658 |
| QB attempts × lead receiver yards | 0.293 | 0.272 … 0.313 | 7,876 |
| Lead RB carries × lead receiver yards | −0.009 | −0.032 … 0.013 | 7,657 |
| Same player targets × receptions | 0.920 | 0.918 … 0.921 | 75,368 |
| Same player carries × rushing yards | 0.842 | 0.837 … 0.847 | 31,031 |
| Same player carries × receiving yards | −0.162 | −0.167 … −0.157 | 75,368 |

## 5. Validation gates

| Gate | Test | Strategies passing |
|---|---|---|
| G1 | ≥ 200 settled bets | 26/28 |
| G2 | ≥ 5 seasons covered | 25/28 |
| G3 | Point-in-time features (leakage rebuild test) | 28/28 |
| G4 | Non-negative ROI on held-out 2023–2025 | 8/28 |
| G5 | p < 0.05 vs zero-skill simulation | 7/28 |
| G6 | Survives Benjamini–Hochberg FDR (q = 0.10) | 4/28 |
| G7 | Profitable in ≥ 60% of seasons | 6/28 |
| G8 | Non-negative after dropping the best season | 7/28 |
| G9 | Prices observed, not assumed | 19/28 |

## 6. Verification performed

* **Pro-Football-Reference score spot-check: 11/11 rows match** (2024 weeks 2–4, source URL per row).
* **43,111 single bets re-settled by an independent implementation: 0 mismatches.**
* **Whole-file integrity checks** (result/total arithmetic, valid American odds, de-vig closure,
  quote granularity, plausibility guards) pass on 100% of rows.
* **Cross-file check:** the publisher's two independent line files agree exactly on 67.3% of
  3,368 games and within half a point on 91.1%; mean absolute difference 0.23 points.
* **Leakage guard:** pre-game Elo rebuilt from truncated history for 25 games, maximum difference 0.0.

## 7. What is *not* verified — published on the Flagged for Review page

1. **IR-01 Line provenance.** The publisher does not document which sportsbook the closing lines
   come from, or when they were captured. The implied hold (2.4–2.9%) is lower than a typical
   retail book, which suggests a sharp or consensus source. All ROI figures inherit this.
2. **IR-02 Player-week data.** Third-party mirror with no publisher documentation. Schema matches
   the nflverse game-ID format; spot checks are consistent, but provenance is unverified.
3. **IR-03 No prop prices.** Prop ROI is simulated at an assumed −110. Hit rates are real; ROI is not.
4. **IR-04 De-vig method.** The market-null simulation uses proportional de-vigging, which has a
   known favourite–longshot bias. It flatters longshot sides and penalises favourites; the
   always-favourite control shows p = 0.016 for a +0.2% ROI, which is the symptom.
5. **IR-05 Line-movement anomaly.** Open→close movement in the 2021 opening-line file averages
   3.40 points, roughly double the 1–2 points usually reported. Flagged; not used by any strategy.
6. **IR-06 Extreme lines.** Two closing spreads reach 24 (NE, 2007) and 27 (DEN, 2013). Reviewed
   and retained — internally consistent, historically plausible, not externally confirmed.
7. **IR-07 Partial 2026 season.** 164 of 272 scheduled games are unplayed, so the 2026 line board
   has our number for every game but a market comparison only where one exists.
8. **IR-08 Selection disclosure.** The model's two feature sets were chosen using 2003–2014
   walk-forward RMSE only; all reported betting results are from later seasons.
9. **IR-09 Branch naming.** The platform fixed this session to `arena/398c4b58-korea3`; the
   requested `session-<id>/<task>` convention could not be used.

## 8. Bottom line

The pipeline produces genuine, reproducible line origination and a full competitive framework
with hard validation. The honest answer to "can these strategies beat the NFL market" is **not
yet**: after correcting for multiple testing and sampling error, no strategy clears every gate,
and the one that comes closest (fading big favourites) has a confidence interval that straddles
zero and a holdout return of 0.0%.

The parts worth keeping: the origination engine, the gate framework, the FDR and luck-null
machinery, and the measured correlation table — particularly the finding that spread/total
same-game correlation is ~0.02, while same-player prop legs are 0.92.
