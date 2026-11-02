# Evidence-chain hardening review — session `arena/0e0fd66d-korea3`

Date: 2026-11-02 UTC. Scope: `nfl_lab/**`, `verified/**`, lab tests, `VERIFIED_EXECUTIVE_SUMMARY.md`, and this review. Root navigation, audit, docs, data and QA scopes owned by other sessions were not edited.

## Method

1. Read `COORDINATION.md` and active remote claims before editing; pushed an isolated claim first.
2. Reviewed the existing workbench line by line: contracts, evidence admission, pricing, models, strategies, validation, runner, source register, site generator and checker.
3. Re-opened official league/operator/government sources for the exact claims used. A domain match or search snippet was not treated as verification.
4. Added synthetic adversarial tests. Synthetic fixtures are code tests only and are never published as NFL findings.
5. Kept all empirical outputs blank because no licensed event-level official dataset, executable operator quote archive or archived settlement-rule snapshot was admitted.

## Findings and disposition

| ID | Prior defect / risk | Disposition | Official reference |
|---|---|---|---|
| R1 | Settlement rules could be accepted by ID alone, without operator/market/jurisdiction/date/version/rights checks. | Fixed: rules evidence must be official, same operator, market/jurisdiction-specific, versioned, effective at acceptance, licensed/public-domain and hash-pinned. | [DraftKings player-settlement guidance](https://support.draftkings.com/dk/en-us/how-will-my-bet-be-settled-if-a-player-doesn-t-start-or-is-removed-from-a?id=kb_article_view&sysparm_article=KB0010795) |
| R2 | Settlement did not resolve the quoted ticket or prove accepted price/identity/profit. | Fixed: settlement resolves an admitted executable quote and checks event, market, selection, threshold, operator, jurisdiction, acceptance time, accepted price and recomputed profit. Parlay repricing requires an evidenced adjusted price. | [DraftKings odds](https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466) |
| R3 | Forecast probabilities were not bound to settlement rows or artifacts. | Fixed: each bet resolves a forecast ID, artifact hash, model version, feature snapshot, baseline quote pair and pre-acceptance issue time. Scoring uses the matched forecast, conditional on action. | [NIST confidence limits](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm) |
| R4 | Checker proved only an official-host link, not registry identity or support scope. | Mitigated: rows carry `data-source-id`/`data-source-url`; checker validates the pair and publishes support scope. Live content drift still requires scheduled/manual re-review. | [NFL terms (changes)](https://www.nfl.com/legal/terms/) |
| R5 | Responsible-betting story was attributed as NFL-authored. | Fixed: source register attributes it to Associated Press content hosted by NFL.com. | [NFL.com-hosted AP story](https://www.nfl.com/news/nfl-is-kicking-off-a-6-2m-responsible-betting-campaign) |
| R6 | NWS Brier-score PDF was cited but not independently retrievable in the prior review. | Still unverified: direct fetch failed; claim is blank and flagged. Project scoring definitions do not rely on it as verified evidence. | [NWS PDF](https://www.weather.gov/media/owp/oh/rfcdev/docs/Glossary_Forecast_Verification_Metrics.pdf) |
| E07 | Validation accepted caller-supplied family p-values and an execution boolean. | Fixed: p-values are computed inside `evaluate_family`; execution is proved by admission. External shortcuts raise `TypeError`. | [NIST Bonferroni](https://www.itl.nist.gov/div898/handbook/prc/section4/prc473.htm) |
| E08 | ROI used mean per-bet ROI rather than stake-weighted profit/stake. | Fixed: cluster bootstrap and sign permutation operate on profit/stake sums. | [NIST bootstrap](https://www.itl.nist.gov/div898/handbook/eda/section3/bootplot.htm) |
| E09 | Models could train on games whose final result was not yet available at the cutoff. | Fixed: team/player history filters on result/stats availability timestamps. | [NFL game operations timeline](https://operations.nfl.com/game-operations-logistics/preparation-safety/game-and-stadium-prep) |
| E10 | Reward allocation could compute prizes from an unverified pool. | Fixed: `leaderboard(..., reward_pool=...)` raises until funding/legal terms are verified; default rewards remain blank. | [NFL.com-hosted responsible-betting context](https://www.nfl.com/news/nfl-is-kicking-off-a-6-2m-responsible-betting-campaign) |

## Official-source re-check

| Source ID | Exact claim checked | Result | Link |
|---|---|---|---|
| `nfl_terms` | §§1.1/1.3 restrict reproduction and systematic compilation without express prior written consent. | Verified | [NFL terms](https://www.nfl.com/legal/terms/) |
| `nfl_stats` | NFL Support directs readers to player/team stats and the Record and Fact Book. | Verified | [NFL Support](https://support.nfl.com/hc/en-us/articles/35869694725268-Stats-Records) |
| `nfl_rulebook` | NFL Football Operations publishes the 2026 rulebook and 2026 rule changes. | Verified | [2026 rulebook](https://operations.nfl.com/rules-officiating/2026-nfl-rulebook) |
| `nfl_ops` | Game Operations checklist begins seven days before kickoff and continues through the game. | Verified | [Game and stadium prep](https://operations.nfl.com/game-operations-logistics/preparation-safety/game-and-stadium-prep) |
| `dk_odds` | -110 means wager $110 to win $100 profit; multiplier odds include returned stake. | Verified, v4.0 2026-10-06 | [DraftKings odds](https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466) |
| `dk_spread` | Favorite negative, underdog positive; adjusted tie pushes. | Verified, v5.0 2026-06-29 | [DraftKings spread](https://support.draftkings.com/dk/en-us/what-is-a-point-spread-bet?id=kb_article_view&sysparm_article=KB0010595) |
| `dk_market_rules` | Two-way spread/moneyline/total push definitions. | Verified | [DraftKings market rules](https://sportsbook.draftkings.com/help/general-betting-rules/market-rules) |
| `dk_parlay` | All legs must win; losing leg loses ticket; push removed/repriced; correlated selections may be restricted. | Verified, v4.0 2026-06-29 | [DraftKings parlay](https://support.draftkings.com/dk/en-us/what-is-a-parlay-bet?id=kb_article_view&sysparm_article=KB0010683) |
| `dk_sgp` | SGP odds calculated differently; applicable-state void legs adjust odds; sport-specific rules apply. | Verified, v5.0 2026-08-18 | [DraftKings SGP](https://support.draftkings.com/dk/en-us/what-is-a-same-game-parlay-sgp-bet?id=kb_article_view&sysparm_article=KB0010719) |
| `dk_prop` | Prop bet definition and link to settlement rules. | Verified, v3.0 2026-06-29 | [DraftKings prop](https://support.draftkings.com/dk/en-us/what-is-a-prop-bet?id=kb_article_view&sysparm_article=KB0010778) |
| `dk_player_settlement` | Directs to sport-specific house rules; generally bets stand if player starts/meets playing-time requirements. | Verified, v5.0 2026-06-29 | [DraftKings player settlement](https://support.draftkings.com/dk/en-us/how-will-my-bet-be-settled-if-a-player-doesn-t-start-or-is-removed-from-a?id=kb_article_view&sysparm_article=KB0010795) |
| `dk_football_rules` | Participation means playing in at least one play in the applicable event. | Verified | [DraftKings football rules](https://sportsbook.draftkings.com/help/sport-rules/football) |
| `nist_ci` | Confidence coefficient is a long-run property of the interval method. | Verified | [NIST CI](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm) |
| `nist_bootstrap` | Resampling with replacement; bootstrap not appropriate for all statistics/distributions. | Verified | [NIST bootstrap](https://www.itl.nist.gov/div898/handbook/eda/section3/bootplot.htm) |
| `nist_correlation` | Pearson correlation measures linear relationship; zero is no linear relationship. | Verified | [NIST correlation](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/correlat.htm) |
| `nist_multiple` | Repeated pairwise comparisons do not generally preserve the single-comparison significance level. | Verified | [NIST multiple comparisons](https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm) |
| `nist_bonferroni` | Bonferroni maintains an overall confidence coefficient across a finite set of comparisons. | Verified | [NIST Bonferroni](https://www.itl.nist.gov/div898/handbook/prc/section4/prc473.htm) |
| `nih_fdr` | FDR definition and BH step-up; dependence conditions. | Verified via official NCBI E-utilities XML after PMC HTML cookie challenge. | [E-utilities PMC XML](https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pmc&id=3496575) |
| `nws_metrics` | Brier/skill-score definitions. | Unverified: direct PDF fetch failed; claim blank. | [NWS PDF](https://www.weather.gov/media/owp/oh/rfcdev/docs/Glossary_Forecast_Verification_Metrics.pdf) |
| `nfl_rg` | Responsible-betting initiative summary. | Verified as AP wire copy hosted by NFL.com, not NFL-authored. | [NFL.com-hosted AP story](https://www.nfl.com/news/nfl-is-kicking-off-a-6-2m-responsible-betting-campaign) |

## Verification performed

- `python -m pytest tests/test_lab_*.py tests/test_evidence_hardening.py -q` → 34 passed.
- `python -m nfl_lab.run` → 0 admitted games/quotes/bets/forecasts/player games; 0 eligible strategies; 0 verified empirical values.
- `python -m nfl_lab.check_verified` → 12 pages, 146 table rows, every row has a matching official registry source; local links resolve; one unverified source (`nws_metrics`).
- No NFL.com scraping, no sportsbook account access, no bet placement, no funded reward.

## Remaining blockers

Licensed official event data, executable historical operator quotes, archived operator rules, player-prop inputs, matched official leg outcomes, verified holdout/forward performance, and funded/legal reward terms remain absent. These block empirical claims and rewards, not publication of the research workbench.
