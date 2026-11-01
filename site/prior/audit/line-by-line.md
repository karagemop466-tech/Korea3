# Independent line-by-line evidence audit

**Reviewed:** 2026-11-01 UTC  
**Snapshot:** the seven root-level HTML pages and `scripts/build.py` delivered by PR [#1](https://github.com/karagemop466-tech/Korea3/pull/1), as of main commit `89ded77`. This is a snapshot, not an assertion about changes made by other sessions afterwards.  
**Scope:** every published body row, its exact generated text, its linked official-domain source, and the evidence limits. This audit did not place bets, access private odds, or validate a strategy.

## How to read the verdicts

- **Supported fact** means the cited primary source supports the limited factual description, not the surrounding research program or its outcomes.
- **Proposal** is the project's research design, not an externally verified edge or an endorsement by the source.
- **Project state** was checked against the repository snapshot, not verified by the linked external organization. Its source is context only.
- **Flag** means the citation is insufficient or the material needs further checking. A link to an official domain is not by itself proof that every claim in its row is supported.

The NFL stats directory, Next Gen Stats, NFL operations, DraftKings parlay help, NIST confidence limits, the NIST-hosted correlation-caution PDF, and the two NFL-hosted gambling articles were individually opened. The DraftKings old help link redirected to the operator's new support page. See the source links in each row. These are point-in-time content checks, not a guarantee the URLs will remain available. The two NFL-hosted news items are Associated Press articles, not league policy documents. The NIST-hosted correlation-caution document expressly says it reflects its author's views rather than necessarily NIST's official position.

### Executive summary

| Published item | Audit result | Official source checked |
|---|---|---|
| Current state | **Project state.** The snapshot publishes no ranked performance, odds, correlations, rewards, or picks; the NFL source does not independently attest to this repo's state. | [NFL stats directory](https://support.nfl.com/hc/en-us/articles/35869694725268-Stats-Records) |
| Core limitation | **Proposal / context.** NIST describes uncertainty in estimates, not a proof that a particular betting strategy is skilled. | [NIST confidence limits](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm) |
| Priorities | **Proposal.** NFL lists statistics and records; the proposed odds and chronology requirements are not stated there. | [NFL stats directory](https://support.nfl.com/hc/en-us/articles/35869694725268-Stats-Records) |
| Competition | **Proposal.** NIST explains intervals, not this competition's eligibility, ranking, or rewards. | [NIST confidence limits](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm) |
| Risk | **Supported fact / context.** The NFL-hosted AP report discusses risks and setting limits; applicability of any local laws was not established. | [NFL-hosted AP responsible-betting report](https://www.nfl.com/news/nfl-is-kicking-off-a-6-2m-responsible-betting-campaign) |

### Strategy lab

| Published item | Audit result | Official source checked |
|---|---|---|
| Single-game lines | **Proposal.** The source points to NFL statistics, not evidence that the proposed model works. | [NFL stats directory](https://support.nfl.com/hc/en-us/articles/35869694725268-Stats-Records) |
| Player props | **Proposal.** Passing metrics exist, but the source does not validate this player forecast or settlement model. | [NFL Next Gen Stats](https://nextgenstats.nfl.com/stats/passing) |
| Cross-game parlays | **Proposal.** DraftKings explains parlays, not the proposed joint model or its performance. | [DraftKings parlay help](https://help.draftkings.com/hc/en-us/articles/4405235694739-What-is-a-parlay-bet-US) |
| Same-game player combinations | **Proposal.** DraftKings describes same-game parlays and restrictions on correlated selections; no edge or dependence coefficient is established. | [DraftKings parlay help](https://help.draftkings.com/hc/en-us/articles/4405235694739-What-is-a-parlay-bet-US) |
| Market benchmark | **Proposal / flag.** The parlay page does not define Brier score, log loss, de-vigging, or a benchmark. | [DraftKings parlay help](https://help.draftkings.com/hc/en-us/articles/4405235694739-What-is-a-parlay-bet-US); [NWS Brier-score definition](https://www.weather.gov/media/owp/oh/rfcdev/docs/Glossary_Forecast_Verification_Metrics.pdf) |

### Validation gates

| Published item | Audit result | Official source checked |
|---|---|---|
| 1 · Data integrity | **Proposal / project state.** The NFL directory is not a historical odds audit; blocked status is consistent with the snapshot. | [NFL stats directory](https://support.nfl.com/hc/en-us/articles/35869694725268-Stats-Records) |
| 2 · Chronology | **Proposal / flag.** A time-ordered holdout is not described by the cited confidence-limit page. No gate has been run. | [NIST confidence limits](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm) |
| 3 · Probability quality | **Proposal / flag.** NIST's cited page does not define Brier or log loss. The NWS glossary directly defines the Brier score for binary outcomes; its application here is a project proposal. | [NIST confidence limits](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm); [NWS glossary](https://www.weather.gov/media/owp/oh/rfcdev/docs/Glossary_Forecast_Verification_Metrics.pdf) |
| 4 · Returns and uncertainty | **Proposal / flag.** The cited NIST page explains mean confidence limits and refers to bootstrap for other estimators; it does not prescribe this block bootstrap. NIST research separately discusses dependency-aware resampling in another domain. | [NIST confidence limits](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm); [NIST dependency-aware bootstrap research](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=916517) |
| 5 · Selection bias | **Proposal / flag.** The original NIST page does not specifically establish this rule. A separate NIST page explains multiple-comparison risks and advance contrasts in its own setting. | [NIST multiple comparisons](https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm) |
| 6 · Stability and deployment | **Proposal.** The thresholds and their conjunction are project policy, not NIST standards or proof of skill. | [NIST confidence limits](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm) |

### Correlation and pricing

| Published item | Audit result | Official source checked |
|---|---|---|
| Player leg pairs | **Proposal / flag.** The original NIST-hosted caution paper does not define phi or prove an observed coefficient. NIST defines Pearson correlation separately; the estimate and sample remain blank. | [NIST Pearson correlation](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/correlat.htm); [NIST-hosted caution paper](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=921446) |
| Cross-game returns | **Proposal / flag.** The cited paper cautions about prediction but does not prescribe week-aligned strategy-return correlation or zero-exposure handling. | [NIST-hosted caution paper](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=921446) |
| Joint probabilities | **Proposal / flag.** The operator's parlay page does not define the proposed estimator. No joint probability is available. | [DraftKings parlay help](https://help.draftkings.com/hc/en-us/articles/4405235694739-What-is-a-parlay-bet-US) |
| Fair price | **Derived formula / flag.** The no-push arithmetic is a project derivation, not a specific market quote; the cited parlay article is not the best support. DraftKings separately defines decimal odds as total return including stake. | [DraftKings odds format](https://support.draftkings.com/dk/en-ca/understanding-odds?id=kb_article_view&sysparm_article=KB0010466) |
| Interpretation | **Supported context.** The caution paper explicitly says correlation is not causation and a good historical fit does not ensure prediction; the author disclaims that the presentation necessarily states NIST's position. | [NIST-hosted caution paper](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=921446) |

### Leaderboard

| Published item | Audit result | Official source checked |
|---|---|---|
| Single-game distribution model | **Project state.** No holdout score, return, or reward is present; the NFL link does not certify the project state. | [NFL stats directory](https://support.nfl.com/hc/en-us/articles/35869694725268-Stats-Records) |
| Player opportunity model | **Project state.** Values remain blank; the source provides passing statistics, not this model's results. | [NFL Next Gen Stats](https://nextgenstats.nfl.com/stats/passing) |
| Cross-game joint model | **Project state.** Values remain blank; the source does not verify the project model. | [DraftKings parlay help](https://help.draftkings.com/hc/en-us/articles/4405235694739-What-is-a-parlay-bet-US) |
| Same-game joint player model | **Project state.** Values remain blank; the source does not verify the project model. | [DraftKings parlay help](https://help.draftkings.com/hc/en-us/articles/4405235694739-What-is-a-parlay-bet-US) |
| Proposed ranking | **Proposal.** NIST does not prescribe this reward-ranking rule or certify that it has been implemented. | [NIST confidence limits](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm) |

### Source register

| Published item | Audit result | Official source checked |
|---|---|---|
| NFL stats and records | **Supported fact.** The NFL directs readers to player/team stats and select historical records. | [NFL stats directory](https://support.nfl.com/hc/en-us/articles/35869694725268-Stats-Records) |
| NFL Next Gen Stats | **Supported fact.** The passing page describes air yards and displays attempts and yards. Dynamic season numbers were not audited. | [NFL Next Gen Stats](https://nextgenstats.nfl.com/stats/passing) |
| Game-day operations | **Supported fact.** The NFL page says the administration report includes inactive lists; it does not establish historical public availability times. | [NFL game-day operations](https://operations.nfl.com/game-operations-logistics/preparation-safety/game-and-stadium-prep) |
| Parlay rules | **Supported fact / flag.** The operator defines parlays, correlated-selection restrictions, and a sport-specific exception for SGPs. Its illustrative payout wording has a separate inconsistency noted below. | [DraftKings parlay help](https://help.draftkings.com/hc/en-us/articles/4405235694739-What-is-a-parlay-bet-US) |
| Uncertainty | **Supported fact / context.** NIST discusses mean confidence limits and links bootstrap for other estimators; the block procedure is explicitly a project proposal. | [NIST confidence limits](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm) |
| Correlation caution | **Supported wording / flag.** The statements appear in the cited document, but the author's disclaimer means they should not be characterized as a formal NIST endorsement. | [NIST-hosted caution paper](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=921446) |
| Integrity | **Supported as historical reporting / flag.** The NFL-hosted AP article discusses 2024 restrictions; it is not proof of the current full policy. | [NFL-hosted AP gambling-policy report](https://www.nfl.com/news/nfl-increases-gambling-policy-education-integrity-monitoring-efforts-following-successful-offseason) |

### Flagged for review

| Published item | Audit result | Official source checked |
|---|---|---|
| Historical odds and execution | **Project state.** No qualified executable-odds archive was present in the snapshot; the linked operator page is context, not proof of the repo's contents. | [DraftKings parlay help](https://help.draftkings.com/hc/en-us/articles/4405235694739-What-is-a-parlay-bet-US) |
| Official event-level outcomes | **Project state.** No event-level outcome dataset appeared in the snapshot. The source directory does not itself independently audit the repo. | [NFL stats directory](https://support.nfl.com/hc/en-us/articles/35869694725268-Stats-Records) |
| Correlations and samples | **Project state.** Coefficient, sample size, and interval were blank; no sample was available to independently verify. | [NIST Pearson correlation](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/correlat.htm) |
| Strategy performance | **Project state.** Win rate, ROI, probabilities, and holdout score were blank; no backtest is in the snapshot. | [NIST confidence limits](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm) |
| Specific settlement rules | **Flag.** The general parlay help explicitly sends SGP readers to sport-specific rules. Do not infer NFL settlement from generic or another sport's rules. | [DraftKings parlay help](https://help.draftkings.com/hc/en-us/articles/4405235694739-What-is-a-parlay-bet-US) |
| Rewards | **Project state.** Prize amount, funding, and sponsor were blank; the NIST link does not establish whether funding exists. | [NIST confidence limits](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm) |
| Legal and eligibility | **Flag.** A 2024 report is not a current jurisdiction-specific legal determination. | [NFL-hosted AP gambling-policy report](https://www.nfl.com/news/nfl-increases-gambling-policy-education-integrity-monitoring-efforts-following-successful-offseason) |

## Irregularities and integration requests

1. **Citation scope.** Many rows are correctly labeled as proposals or repository state, but their generic official link cannot verify each project's claims. Label such links **source context** and use the more directly relevant official sources above for methodology. Preserve blanks and **unverified** for empirical values. Do not portray a government-hosted paper's author opinion as institutional endorsement.
2. **Operator example inconsistency.** The current [DraftKings parlay example](https://help.draftkings.com/hc/en-us/articles/4405235694739-What-is-a-parlay-bet-US) labels its example amount as a combined profit; compare its wording and stated odds with DraftKings' own distinction between [profit and total return](https://support.draftkings.com/dk/en-ca/understanding-odds?id=kb_article_view&sysparm_article=KB0010466) and its [American-odds example](https://support.draftkings.com/dk/en-us/what-is-a-moneyline-bet?id=kb_article_view&sysparm_article=KB0010553). The underlying intended payout is **unverified**; do not reproduce the example as a verified calculation.
3. **Usage rights.** The official [NFL gamebook for Denver at Kansas City, 2025-12-25](https://static.www.nfl.com/image/upload/v1766722063/gamecenter/f91b71fe-311e-11f0-b670-ae1250fadad1.pdf) carries an express use restriction for its summary and play-by-play. Link to it for review; do not assume permission for automated extraction, redistribution, or commercial analysis. Check the applicable license and terms before ingestion.
4. **Provenance.** A community dataset is not an NFL-official source merely because it contains NFL outcomes. To label an individual value verified, compare that specific value to an official record and retain the record link, relevant timestamp, revision/version, and usage permission. Otherwise leave the value blank in the official-verified presentation and flag it. A season-wide aggregate or one checked row cannot certify every row.
5. **Settlements.** Archive rules by operator, jurisdiction, market, and effective date. A generic parlay rule is insufficient for a same-game player-prop void, push, injury, or repricing; no dated comprehensive archive has been verified here. See [DraftKings' general parlay help](https://help.draftkings.com/hc/en-us/articles/4405235694739-What-is-a-parlay-bet-US).
6. **Mechanical checks.** The existing checker establishes local link targets and that each row contains an HTTPS link; it does not prove the host is official, the external page is available, the content supports the row, or a value is verified. Independent checks for this snapshot additionally matched all 40 rendered rows to their generator entries and confirmed each original link's host was on an explicit NFL, DraftKings, or NIST allowlist. This is structural assurance only, not factual verification.

## Verification performed

- `python3 scripts/check.py`: passed for the snapshot.
- Parsed `scripts/build.py` without executing its site-writing code; compared each of the seven HTML tables' item, detail, status, and source URL against the generator. All 40 matched exactly.
- Opened each of the eight original unique primary-source URLs through the research page reader, following the DraftKings redirect; opened the additional official methodology and operator sources linked above. The pages' contents, not merely their hostnames, were reviewed for the limited claims described.
- No live external-link crawler was run from the repository, and no odds, payouts, model forecasts, correlations, returns, prize funds, current legal advice, or user-specific eligibility were verified.
