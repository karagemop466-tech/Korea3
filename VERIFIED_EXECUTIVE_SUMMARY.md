# Verified workbench — executive summary

**Date:** 2026-11-02 UTC  
**Scope:** official-evidence-only layer for NFL line origination, signal research, validation, correlations, parlays, player-prop combinations and leaderboard eligibility.  
**Live path:** `/verified/` under the repository GitHub Pages site.

## Bottom line

- **Verified empirical values published: 0.** No licensed, event-level official NFL dataset, timestamped executable operator quote archive, archived settlement-rule snapshot, or admitted player-prop dataset was available under the project’s verification and data-rights rules.
- **Reward-eligible strategies: 0.** The workbench is fail-closed: missing evidence blocks promotion; it never becomes a pass.
- **Real-money execution: 0.** No sportsbook account access, no bet placement, no funded prize pool. Reward allocation is disabled in code until funding, sponsor, jurisdiction and payout terms are verified.
- **Exploratory work is preserved, not promoted.** Earlier sessions produced third-party-data backtests and dashboards. They remain reachable from the main repository dashboard and session index, but their prices, correlations, ROI and rankings are not treated as official verification here.

## What changed in this hardening pass

1. **Settlement-rule admission (R1).** Rules must be official, same operator, market/jurisdiction-specific, versioned, effective at acceptance, licensed/public-domain and hash-pinned. A link-only or wrong-publisher rules entry is rejected. Source context: [DraftKings player-settlement guidance](https://support.draftkings.com/dk/en-us/how-will-my-bet-be-settled-if-a-player-doesn-t-start-or-is-removed-from-a?id=kb_article_view&sysparm_article=KB0010795).
2. **Quote-to-settlement identity (R2).** Each settlement resolves an admitted executable quote and checks event, market, selection, threshold, operator, jurisdiction, acceptance time, accepted price and recomputed profit. Parlay repricing requires an officially evidenced adjusted price. Source context: [DraftKings odds](https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466).
3. **Forecast binding (R3).** Each bet resolves a forecast ID, artifact hash, model version, feature snapshot, contemporaneous baseline quote pair and pre-acceptance issue time. Probability scoring uses the matched forecast and is conditional on action. Source context: [NIST confidence limits](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm).
4. **No caller shortcuts.** External family p-values and executable-quote booleans are rejected. Multiplicity is computed across the complete registered family; execution is evidence-checked. Source context: [NIST Bonferroni](https://www.itl.nist.gov/div898/handbook/prc/section4/prc473.htm).
5. **Stake-weighted economics and availability-time causality.** ROI uses profit/stake sums with season-week cluster resampling. Team/player models filter on result/stats availability timestamps, not merely kickoff. Source context: [NIST bootstrap](https://www.itl.nist.gov/div898/handbook/eda/section3/bootplot.htm).
6. **Row-level source semantics (R4).** Generated table rows carry registry source IDs; the checker validates the ID/URL pair and publishes support scope. Live source-content drift remains a scheduled/manual review flag. Source context: [NFL terms](https://www.nfl.com/legal/terms/).
7. **Attribution and unverified sources (R5–R6).** The responsible-betting story is attributed to Associated Press content hosted by NFL.com. The NWS Brier-score PDF could not be directly retrieved; its claim is blank and flagged. Sources: [NFL.com-hosted AP story](https://www.nfl.com/news/nfl-is-kicking-off-a-6-2m-responsible-betting-campaign), [NWS PDF](https://www.weather.gov/media/owp/oh/rfcdev/docs/Glossary_Forecast_Verification_Metrics.pdf).

## Validation gates

Every gate must pass before leaderboard eligibility: preregistration; evidence and rights; chronology; sample; probability quality; economics; multiplicity; stability; execution and risk; forward freeze. The current default build has a loaded project protocol freeze but no admitted observations, so empirical gates remain blocked and no strategy is eligible. Gate design references: [NIST multiple comparisons](https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm), [NIST Bonferroni](https://www.itl.nist.gov/div898/handbook/prc/section4/prc473.htm), [NIST bootstrap](https://www.itl.nist.gov/div898/handbook/eda/section3/bootplot.htm).

## Luck policy

Luck cannot be eliminated. The workbench estimates uncertainty and refuses promotion without strong out-of-sample evidence: untouched holdout, season-week cluster bootstrap, paired probability-score comparison, Bonferroni multiplicity control, price stress, drawdown/exposure limits and a post-freeze forward sample. These are project controls, not an official NFL or sportsbook standard. Source context: [NIST confidence limits](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm).

## Open blockers

- Licensed event-level official NFL outcomes.
- Timestamped executable historical operator quotes and archived settlement rules.
- Licensed official player game logs and operator prop quotes.
- Matched official leg outcomes for threshold-specific correlation estimates.
- Verified holdout/forward performance for any strategy.
- Funded reward pool, sponsor, jurisdiction, age and licensing verification.
- Direct re-verification of the NWS forecast-metrics PDF.

These are published on `verified/flagged.html` and do not block publication of the research workbench. They do block any verified empirical claim, betting signal or reward.

## Verification performed

- `python -m pytest tests/test_lab_*.py tests/test_evidence_hardening.py -q` → **34 passed**.
- `python -m nfl_lab.run` → **0** admitted games/quotes/bets/forecasts/player games; **0** eligible strategies; **0** verified empirical values.
- `python -m nfl_lab.check_verified` → **12 pages, 146 table rows**, every row has a matching official registry source; local links resolve; **1** unverified source (`nws_metrics`).
- Source register: **20** official-publisher references; **19** claims verified, **1** blank/unverified. NIH FDR text was retrieved through official NCBI E-utilities after the PMC HTML cookie challenge.

## Reproduce

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/test_lab_*.py tests/test_evidence_hardening.py -q
.venv/bin/python -m nfl_lab.run
.venv/bin/python -m nfl_lab.check_verified
```

The default input set is intentionally empty. Optional licensed inputs belong in `nfl_lab/inputs/*.jsonl` with pinned source artifacts and forecast artifacts; they must pass the same contracts. No manual user input is required to build or check the verified view.
