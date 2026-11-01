#!/usr/bin/env python3
"""Build the dependency-free, evidence-first NFL research dashboard."""

from html import escape
from pathlib import Path


SOURCES = {
    "nfl_stats": {
        "organization": "NFL",
        "title": "Stats & Records",
        "url": "https://support.nfl.com/hc/en-us/articles/35869694725268-Stats-Records",
        "scope": "The NFL directs users to official player statistics, team statistics, and select historical records. This page does not establish that a bulk machine-readable archive is available.",
        "kind": "NFL primary source",
    },
    "nfl_gamebooks": {
        "organization": "NFL",
        "title": "Game Books",
        "url": "https://support.nfl.com/hc/en-us/articles/35869678028180-Game-Books",
        "scope": "The NFL says game-center Game Book PDFs contain every score and statistic from a game. Historical bulk extraction and a stable API were not verified.",
        "kind": "NFL primary source",
    },
    "nfl_ngs": {
        "organization": "NFL Next Gen Stats",
        "title": "Passing Stats",
        "url": "https://nextgenstats.nfl.com/stats/passing",
        "scope": "The NFL describes passing metrics such as attempts, yards, air yards, time to throw, and completion percentage. The page is not a complete player-prop settlement archive.",
        "kind": "NFL primary source",
    },
    "nfl_injuries": {
        "organization": "NFL",
        "title": "Official Injury Report",
        "url": "https://www.nfl.com/injuries/",
        "scope": "The current NFL injury page displays player practice and game status. The page is dynamic; a complete point-in-time historical archive was not verified.",
        "kind": "NFL primary source; dynamic page",
    },
    "nfl_operations": {
        "organization": "NFL Football Operations",
        "title": "Game and Stadium Prep",
        "url": "https://operations.nfl.com/game-operations-logistics/preparation-safety/game-and-stadium-prep",
        "scope": "The NFL describes Game Day Administration Reports that include a club's inactive list. This operational description does not establish a public timestamped historical feed.",
        "kind": "NFL primary source",
    },
    "dk_parlay": {
        "organization": "DraftKings",
        "title": "What Is a Parlay Bet?",
        "url": "https://support.draftkings.com/dk/en-us/what-is-a-parlay-bet?id=kb_article_view&sysparm_article=KB0010683",
        "scope": "DraftKings describes its parlay, push, and correlated-selection rules and directs users to sport-specific rules for same-game settlement. Rules are operator- and market-specific.",
        "kind": "Sportsbook operator source; US help page",
    },
    "dk_odds": {
        "organization": "DraftKings",
        "title": "Understanding Odds",
        "url": "https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466",
        "scope": "DraftKings explains American, multiplier/decimal, and fractional odds, including that multiplier odds show total payout including stake. This is the operator's description, not a universal settlement rule.",
        "kind": "Sportsbook operator source; US help page",
    },
    "dk_rules": {
        "organization": "DraftKings Sportsbook",
        "title": "Sport-Specific Rules",
        "url": "https://sportsbook.draftkings.com/help/sport-rules/",
        "scope": "DraftKings' official rules directory. Rules can vary by market, product, jurisdiction, and date; no complete historical rule archive was ingested.",
        "kind": "Sportsbook operator source; dynamic page",
    },
    "odds_api": {
        "organization": "The Odds API",
        "title": "Historical Odds Data",
        "url": "https://the-odds-api.com/historical-odds-data/",
        "scope": "The provider documents timestamped historical bookmaker snapshots, market coverage, and paid-plan access. It is a commercial third-party provider, not an NFL source; no subscription, license, or data was obtained for this project.",
        "kind": "Commercial provider documentation; not NFL",
    },
    "nist_ci": {
        "organization": "NIST",
        "title": "Confidence Limits for the Mean",
        "url": "https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm",
        "scope": "NIST explains confidence intervals for a mean and the repeated-sampling interpretation. This reference does not validate an NFL backtest or a clustered-return interval.",
        "kind": "US government statistical reference",
    },
    "nist_bootstrap": {
        "organization": "NIST",
        "title": "Bootstrap Plot",
        "url": "https://www.itl.nist.gov/div898/handbook/eda/section3/bootplot.htm",
        "scope": "NIST describes bootstrap resampling for estimating uncertainty and cautions that bootstrap use is not appropriate for every statistic. It does not establish the project's proposed game/week block-bootstrap design.",
        "kind": "US government statistical reference",
    },
    "nist_multiple": {
        "organization": "NIST",
        "title": "Multiple Comparisons",
        "url": "https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm",
        "scope": "NIST explains that repeated unadjusted comparisons do not preserve the nominal overall significance level and discusses multiple-comparison procedures.",
        "kind": "US government statistical reference",
    },
    "nist_correlation": {
        "organization": "NIST",
        "title": "Statistics Handbook Glossary: Correlation",
        "url": "https://www.itl.nist.gov/div898/handbook/glossary.htm#correlation",
        "scope": "NIST defines the Pearson correlation coefficient and its range. A Pearson coefficient alone is not a complete multileg joint-probability model.",
        "kind": "US government statistical reference",
    },
    "nist_causality": {
        "organization": "NIST",
        "title": "Experiments and Experimental Design",
        "url": "https://www.itl.nist.gov/div898/handbook/ppc/section1/ppc136.htm",
        "scope": "NIST distinguishes correlation from causality and notes that an observed association alone does not establish cause; its handbook discusses designed experiments as one way to investigate causal relationships.",
        "kind": "US government statistical reference",
    },
    "nist_validation": {
        "organization": "NIST",
        "title": "Validate the Fitted Model",
        "url": "https://www.itl.nist.gov/div898/handbook/pri/section6/pri619.htm",
        "scope": "NIST discusses checking residuals, omitted structure, and time-related patterns when validating a fitted model. The project-specific holdout design remains a proposal.",
        "kind": "US government statistical reference",
    },
    "nist_cross_validation": {
        "organization": "NIST",
        "title": "Cross-Validation Example",
        "url": "https://www.itl.nist.gov/div898/handbook/pri/section6/catapult/pri636.htm",
        "scope": "A NIST case study demonstrates validation on observations excluded from model fitting and warns against trusting poor interpolation. It is a case study, not a sports-specific standard.",
        "kind": "US government statistical reference",
    },
    "noaa_verification": {
        "organization": "National Weather Service / NOAA",
        "title": "Glossary of Forecast Verification Metrics",
        "url": "https://www.weather.gov/media/owp/oh/rfcdev/docs/Glossary_Forecast_Verification_Metrics.pdf",
        "scope": "The official glossary defines the Brier score as mean squared error for probabilistic two-category forecasts, describes Brier skill score references, and lists reliability/verification metrics. This is a weather-forecasting reference, not NFL performance evidence.",
        "kind": "US government forecast-verification reference; non-sports example",
    },
    "nfl_policy": {
        "organization": "NFL",
        "title": "Gambling Policy Education and Integrity Monitoring (2024)",
        "url": "https://www.nfl.com/news/nfl-increases-gambling-policy-education-integrity-monitoring-efforts-following-successful-offseason",
        "scope": "An NFL article published in 2024 describes gambling restrictions for NFL players, coaches, staff, and personnel. It is not legal advice and does not establish rules for the user or their jurisdiction.",
        "kind": "NFL primary source; 2024 article",
    },
    "nfl_responsible": {
        "organization": "NFL.com / Associated Press",
        "title": "Responsible Betting Campaign (2021)",
        "url": "https://www.nfl.com/news/nfl-is-kicking-off-a-6-2m-responsible-betting-campaign",
        "scope": "An AP report hosted on NFL.com in 2021 describes responsible-betting messaging about setting limits and understanding risk. It is historical context, not current jurisdictional guidance.",
        "kind": "NFL.com-hosted Associated Press report; 2021",
    },
    "github_pages": {
        "organization": "GitHub Docs",
        "title": "Configure a GitHub Pages Publishing Source",
        "url": "https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site",
        "scope": "GitHub documents branch-based Pages publishing from a repository root or docs folder. The repository's actual Pages settings were separately checked through the GitHub API.",
        "kind": "Official platform documentation",
    },
}


def entry(item, finding, status, sources, value=""):
    """Return a table row. Leave `value` empty unless it is verified data."""
    return {
        "item": item,
        "finding": finding,
        "value": value,
        "status": status,
        "sources": list(sources),
    }


PAGES = {
    "index": {
        "title": "Executive summary",
        "subtitle": "A decision-ready research brief, not a betting service.",
        "rows": [
            entry(
                "Project state",
                "The repository contains a static research dashboard. It has no live line engine, feed, picks, backtest, measured correlation values, or recurring data-ingestion job.",
                "Repository audit; no empirical engine",
                ["github_pages", "nfl_gamebooks"],
            ),
            entry(
                "Luck and skill",
                "Luck cannot be removed. Pre-registered, time-ordered out-of-sample evaluation can test whether forecasts add evidence of skill beyond a baseline; it cannot guarantee future profit.",
                "Research principle; not tested here",
                ["nist_validation", "nist_cross_validation"],
            ),
            entry(
                "Required inputs",
                "Use official game records and point-in-time player availability plus licensed, timestamped, executable market prices and the matching operator rules before training or ranking.",
                "Blocked: no qualifying data ingested",
                ["nfl_gamebooks", "nfl_injuries", "odds_api", "dk_rules"],
            ),
            entry(
                "Competition",
                "Compare single-game, player-prop, cross-game parlay, and same-game player-combo candidates only after every gate passes. Log every trial and reserve an untouched forward holdout.",
                "Proposed; no eligible entries",
                ["nist_multiple", "nist_cross_validation"],
            ),
            entry(
                "Leaderboard rewards",
                "No competition, sponsor, prize pool, funded rewards, or validated ranking exists. Keep reward values blank until governance and validation requirements are met.",
                "Not implemented; no funding verified",
                ["nist_multiple", "nfl_responsible"],
            ),
            entry(
                "Risk and limits",
                "Betting outcomes remain uncertain and losses are possible. This project publishes no picks; any future use must comply with local law, operator rules, and applicable policies.",
                "Research only; local rules not assessed",
                ["nfl_responsible", "nfl_policy"],
            ),
        ],
    },
    "data": {
        "title": "Data requirements",
        "subtitle": "Provenance, point-in-time availability, licensing, and settlement are prerequisites—not optional polish.",
        "rows": [
            entry(
                "Official game outcomes",
                "Stable event ID, season/week, scheduled kickoff, home/away teams, final score, game status, and gamebook statistics; retain the source URL and retrieval time.",
                "NFL Game Books are described as PDFs in Game Centers; bulk extraction not verified",
                ["nfl_gamebooks", "nfl_stats"],
            ),
            entry(
                "Player and team features",
                "Versioned pregame team/player statistics, usage/opportunity variables, and metric definitions. Never use a statistic published after the forecast timestamp.",
                "Official stats pages exist; no project ingestion or point-in-time archive",
                ["nfl_stats", "nfl_ngs"],
            ),
            entry(
                "Availability snapshots",
                "Player identity, practice status, game status/inactive status, report timestamp, event ID, and each revision. Preserve the exact version available at each forecast time.",
                "Current NFL injury page confirmed; historical snapshots not verified",
                ["nfl_injuries", "nfl_operations"],
            ),
            entry(
                "Executable market prices",
                "Book/operator, jurisdiction, event and market IDs, side, threshold/line, odds format, price, quote timestamp, accepted/executable status, and collection provenance. A historical snapshot is not proof a quote was accepted or executable.",
                "Unverified; no licensed odds archive acquired or ingested",
                ["odds_api", "dk_odds"],
            ),
            entry(
                "Market and parlay settlement",
                "Archive the exact operator, jurisdiction, market-specific rules, pushes/voids, nonparticipation, same-game restrictions, and rule version for each observation.",
                "Unverified; no complete dated rules archive",
                ["dk_parlay", "dk_rules"],
            ),
            entry(
                "Forecast and experiment ledger",
                "Store frozen model/code version, input-data hash, forecast time, intended market/price, candidate configuration, selection history, outcomes, and all tuning trials.",
                "Not implemented",
                ["nist_validation", "nist_multiple"],
            ),
            entry(
                "Rights and jurisdiction",
                "Confirm data-use rights, allowed retention/redistribution, relevant licensing, and local legal eligibility before ingestion, publication, or any wagering use.",
                "Not reviewed; no legal conclusion made",
                ["odds_api", "nfl_policy", "nfl_responsible"],
            ),
            entry(
                "Automated refresh",
                "A production service would need a documented source, scheduler, freshness checks, retry policy, versioned snapshots, monitoring, and secrets management.",
                "Not built; this site is static",
                ["github_pages", "odds_api"],
            ),
        ],
    },
    "strategies": {
        "title": "Strategy lab",
        "subtitle": "Concrete model families and signal definitions. All are hypotheses, not proven edges or betting recommendations.",
        "rows": [
            entry(
                "Straight moneyline",
                "Forecast the full home/away score-margin distribution from pregame team and player features; derive win probabilities, account for ties/push rules where relevant, and compare to a timestamped market benchmark.",
                "Proposed; unvalidated",
                ["nfl_stats", "nfl_gamebooks", "nist_validation", "dk_odds"],
            ),
            entry(
                "Straight spread and total",
                "Model the joint distribution of score margin and game total, then price the actual quoted spread/total threshold. Handle pushes, alternate lines, and price changes explicitly.",
                "Proposed; unvalidated",
                ["nfl_stats", "nfl_gamebooks", "nist_validation", "dk_odds"],
            ),
            entry(
                "Player props",
                "Separate chance of participation from role/opportunity, then model conditional production and its full distribution. Price the offered threshold using the matching nonparticipant/void rules.",
                "Proposed; unvalidated",
                ["nfl_ngs", "nfl_injuries", "dk_rules"],
            ),
            entry(
                "Cross-game parlays",
                "Estimate the joint probability that all legs win from matched event outcomes or a validated joint simulation. Do not multiply marginal probabilities unless independence is supported for those legs.",
                "Proposed; unvalidated",
                ["dk_parlay", "nist_correlation"],
            ),
            entry(
                "Same-game player combinations",
                "Simulate shared game scripts, team scoring, and player usage together; estimate the probability of the complete leg combination, then reconcile operator-specific parlay settlement and repricing.",
                "Proposed; unvalidated",
                ["dk_parlay", "dk_rules", "nfl_ngs"],
            ),
            entry(
                "Market-relative signal",
                "For each candidate, compare a calibrated model probability with a pre-registered, margin-adjusted market baseline at the same timestamp and exact threshold. Report uncertainty and execution price, not just a point edge.",
                "Proposed; no price or probability values",
                ["dk_odds", "noaa_verification"],
            ),
            entry(
                "Eligibility filter",
                "Advance a candidate only if data, chronology, probability quality, settlement, uncertainty, multiple-testing, and stability gates all pass. No numeric cutoffs are asserted without pre-registration and power analysis.",
                "No candidates eligible",
                ["nist_validation", "nist_multiple", "nist_bootstrap"],
            ),
        ],
    },
    "validation": {
        "title": "Validation gates",
        "subtitle": "Every gate is a proposed research control. None has passed; thresholds are deliberately unset pending data and pre-registration.",
        "rows": [
            entry(
                "0 · Rights and scope",
                "Document jurisdiction, data licenses, source terms, publication limits, market scope, and responsible-use policy before collection or deployment.",
                "Not reviewed",
                ["odds_api", "nfl_policy", "nfl_responsible"],
            ),
            entry(
                "1 · Data integrity",
                "Require source, event ID, forecast time, market, threshold, price, operator, applicable rules, and settled outcome. Detect duplicates, revisions, missingness, and mismatched events.",
                "Blocked: no qualified joined dataset",
                ["nfl_gamebooks", "nfl_injuries", "odds_api", "dk_rules"],
            ),
            entry(
                "2 · Point-in-time discipline",
                "At every forecast timestamp, use only records known then. Preserve event time and publication/observation time separately; audit revisions and prevent future-information leakage.",
                "Not run; no archived snapshots",
                ["nfl_injuries", "odds_api", "nist_validation"],
            ),
            entry(
                "3 · Frozen chronological test",
                "Pre-register features, candidate families, selection rules, and outcomes. Train earlier, tune on a later period, and assess the chosen model once on an untouched future holdout.",
                "Not run; no frozen model or data",
                ["nist_cross_validation", "nist_validation"],
            ),
            entry(
                "4 · Probability quality",
                "Evaluate binary probability forecasts with the Brier score against fixed and market baselines; inspect reliability/calibration and sample sizes, and handle pushes/voids consistently.",
                "Not run; no forecasts or outcomes",
                ["noaa_verification", "dk_parlay", "dk_rules"],
            ),
            entry(
                "5 · Executable returns and settlement",
                "Compute net returns only from prices available at the recorded decision time, including settlement, stake return, fees, rejected quotes, pushes, voids, and realistic slippage.",
                "Blocked: prices and rule archive absent",
                ["dk_odds", "dk_parlay", "dk_rules", "odds_api"],
            ),
            entry(
                "6 · Uncertainty and dependence",
                "Report sample size and uncertainty for every score, return, and coefficient. A game/week block-resampling procedure is only a proposal; ordinary independent-row intervals are not treated as validated for clustered NFL outcomes.",
                "Not run; no qualified sample",
                ["nist_ci", "nist_bootstrap"],
            ),
            entry(
                "7 · Selection bias",
                "Log all strategies and tuning attempts, correct for repeated comparisons using a pre-specified procedure, and evaluate the selected winner on untouched data rather than rewarding the in-sample winner.",
                "Not run; no experiment ledger",
                ["nist_multiple", "nist_cross_validation"],
            ),
            entry(
                "8 · Stability and release",
                "Before release, pre-register acceptable uncertainty, robustness across seasons/markets, price sensitivity, monitoring, stop conditions, and a reproducible model version. Do not imply that a passed backtest guarantees future results.",
                "Not run; no deployment or thresholds",
                ["nist_validation", "nist_cross_validation", "noaa_verification"],
            ),
        ],
    },
    "correlations": {
        "title": "Correlation & pricing",
        "subtitle": "No empirical coefficients, sample sizes, intervals, or fair prices are available. Empty value cells are intentionally blank.",
        "rows": [
            entry(
                "Same-game player legs",
                "For matched binary outcomes at the exact quoted thresholds, estimate the phi/Pearson correlation: (n11·n00 − n10·n01) / sqrt[(n11+n10)(n01+n00)(n11+n01)(n10+n00)]. Record all four joint counts, n, snapshot, missingness, and uncertainty; the coefficient is undefined if a marginal has no variation.",
                "Unverified; no matched data",
                ["nist_correlation", "dk_parlay"],
            ),
            entry(
                "Cross-game legs",
                "Estimate pairwise dependence from matched outcomes for the exact leg types and thresholds at aligned forecast times. Treat correlation as descriptive, not proof of a stable or causal edge.",
                "Unverified; no matched data",
                ["nist_correlation", "nist_causality", "nist_cross_validation"],
            ),
            entry(
                "Strategy return dependence",
                "Measure net-return co-movement on a shared, pre-specified calendar/game-block panel. Report zero-exposure blocks and an active-exposure sensitivity separately, with the sampling unit and uncertainty method.",
                "Unverified; no settled returns",
                ["nist_correlation", "nist_bootstrap"],
            ),
            entry(
                "Parlay joint probability",
                "Price P(all legs win) directly from observed joint outcomes or a validated joint simulation. A single pairwise correlation does not determine arbitrary multi-leg probabilities.",
                "Unverified; no joint sample or model",
                ["dk_parlay", "nist_correlation"],
            ),
            entry(
                "Fair price and net return",
                "For a simple binary no-push wager with decimal total-return odds d and forecast probability p, the project-defined fair decimal price is 1/p and expected net return per unit stake is p × d − 1. Model pushes, voids, fees, and parlay rules separately.",
                "Formula only; no p, d, or return measured",
                ["dk_odds", "dk_parlay"],
            ),
            entry(
                "Correlation interpretation",
                "Report coefficient, n, confidence interval, market/threshold, and source version together. Correlation is not causation; a fit to past data does not establish predictive performance.",
                "General caution; no NFL-specific coefficient",
                ["nist_correlation", "nist_causality", "nist_cross_validation"],
            ),
        ],
    },
    "leaderboard": {
        "title": "Leaderboard",
        "subtitle": "No fabricated rankings. Scores, returns, sample sizes, intervals, and rewards remain blank until verified.",
        "rows": [
            entry(
                "Single-game moneyline/spread/total model",
                "Required report: holdout probability score, score versus baseline, net return at executable prices, n, uncertainty, and market/season coverage.",
                "Not run; not eligible",
                ["nfl_gamebooks", "noaa_verification", "dk_odds"],
            ),
            entry(
                "Player-prop distribution model",
                "Required report: participation handling, Brier score, calibration, settlement-adjusted return, n, uncertainty, and rule/version coverage.",
                "Not run; not eligible",
                ["nfl_ngs", "nfl_injuries", "dk_rules", "noaa_verification"],
            ),
            entry(
                "Cross-game parlay joint model",
                "Required report: joint-probability calibration, actual accepted price, settled return, n, uncertainty, and correlated-leg handling.",
                "Not run; not eligible",
                ["dk_parlay", "noaa_verification"],
            ),
            entry(
                "Same-game player-combination model",
                "Required report: matched joint legs, book-specific accepted price/rules, joint score, settled return, n, uncertainty, and season/market coverage.",
                "Not run; not eligible",
                ["dk_parlay", "dk_rules", "noaa_verification"],
            ),
            entry(
                "Proposed ranking rule",
                "Only gate-passing, pre-registered candidates enter. Report Brier skill against a fixed baseline and uncertainty-aware net returns; rank within comparable bet classes and show all trials.",
                "Not implemented; cutoffs unset",
                ["nist_multiple", "noaa_verification", "nist_bootstrap"],
            ),
            entry(
                "Prizes and payout governance",
                "Publish eligibility, measurement window, ties, stake/exposure limits, audit rights, funding, prize amount, and responsible-use safeguards before competition begins.",
                "No competition or funded reward",
                ["nist_multiple", "nfl_responsible"],
            ),
        ],
    },
    "sources": {
        "title": "Source register",
        "subtitle": "Primary sources and method references checked for the limited scope stated here; links are provided for manual review.",
        "rows": [
            entry("NFL player/team statistics", SOURCES["nfl_stats"]["scope"], SOURCES["nfl_stats"]["kind"], ["nfl_stats"]),
            entry("NFL game books", SOURCES["nfl_gamebooks"]["scope"], SOURCES["nfl_gamebooks"]["kind"], ["nfl_gamebooks"]),
            entry("NFL Next Gen Stats", SOURCES["nfl_ngs"]["scope"], SOURCES["nfl_ngs"]["kind"], ["nfl_ngs"]),
            entry("NFL injury reports", SOURCES["nfl_injuries"]["scope"], SOURCES["nfl_injuries"]["kind"], ["nfl_injuries"]),
            entry("NFL inactive-list operations", SOURCES["nfl_operations"]["scope"], SOURCES["nfl_operations"]["kind"], ["nfl_operations"]),
            entry("DraftKings odds formats", SOURCES["dk_odds"]["scope"], SOURCES["dk_odds"]["kind"], ["dk_odds"]),
            entry("DraftKings parlay rules", SOURCES["dk_parlay"]["scope"], SOURCES["dk_parlay"]["kind"], ["dk_parlay"]),
            entry("DraftKings sport-specific rules", SOURCES["dk_rules"]["scope"], SOURCES["dk_rules"]["kind"], ["dk_rules"]),
            entry("Commercial historical odds documentation", SOURCES["odds_api"]["scope"], SOURCES["odds_api"]["kind"], ["odds_api"]),
            entry("NIST confidence intervals", SOURCES["nist_ci"]["scope"], SOURCES["nist_ci"]["kind"], ["nist_ci"]),
            entry("NIST bootstrap method", SOURCES["nist_bootstrap"]["scope"], SOURCES["nist_bootstrap"]["kind"], ["nist_bootstrap"]),
            entry("NIST multiple comparisons", SOURCES["nist_multiple"]["scope"], SOURCES["nist_multiple"]["kind"], ["nist_multiple"]),
            entry("NIST correlation definition", SOURCES["nist_correlation"]["scope"], SOURCES["nist_correlation"]["kind"], ["nist_correlation"]),
            entry("NIST correlation and causality", SOURCES["nist_causality"]["scope"], SOURCES["nist_causality"]["kind"], ["nist_causality"]),
            entry("NIST model validation", SOURCES["nist_validation"]["scope"], SOURCES["nist_validation"]["kind"], ["nist_validation"]),
            entry("NIST cross-validation example", SOURCES["nist_cross_validation"]["scope"], SOURCES["nist_cross_validation"]["kind"], ["nist_cross_validation"]),
            entry("NOAA Brier score and forecast verification", SOURCES["noaa_verification"]["scope"], SOURCES["noaa_verification"]["kind"], ["noaa_verification"]),
            entry("NFL gambling policy", SOURCES["nfl_policy"]["scope"], SOURCES["nfl_policy"]["kind"], ["nfl_policy"]),
            entry("NFL responsible-betting information", SOURCES["nfl_responsible"]["scope"], SOURCES["nfl_responsible"]["kind"], ["nfl_responsible"]),
            entry("GitHub Pages publishing", SOURCES["github_pages"]["scope"], SOURCES["github_pages"]["kind"], ["github_pages"]),
        ],
    },
    "flagged": {
        "title": "Flagged for review",
        "subtitle": "Unverified items remain blank and are explicitly blocked from signals, rankings, and rewards.",
        "rows": [
            entry(
                "Historical odds and execution",
                "No timestamped, licensed NFL price archive, accepted quote history, market limits, or transaction-cost record is present in the repository. A provider's documented product is not a dataset license or evidence of coverage for every market.",
                "Unverified / blocked",
                ["odds_api", "dk_odds"],
            ),
            entry(
                "Official outcome ingestion",
                "The NFL documents Game Book PDFs in Game Centers and official stats pages, but this repository contains no extracted, reconciled, or audited historical event dataset.",
                "Not ingested / blocked",
                ["nfl_gamebooks", "nfl_stats"],
            ),
            entry(
                "Availability history",
                "The current official injury page is dynamic. Historical publication times, revisions, and the availability snapshot that was visible before each forecast are not captured.",
                "Unverified / blocked",
                ["nfl_injuries", "nfl_operations"],
            ),
            entry(
                "Settlement archive",
                "Operator, jurisdiction, market, date, push/void, nonparticipation, and same-game rules need a dated source for each wager. No complete archive is present.",
                "Unverified / blocked",
                ["dk_parlay", "dk_rules"],
            ),
            entry(
                "Correlation and sample sizes",
                "No matched binary leg outcomes or settled return series are available. Coefficients, n, intervals, and missingness summaries are intentionally blank.",
                "Unverified",
                ["nist_correlation", "nist_bootstrap"],
            ),
            entry(
                "Strategy performance",
                "No backtest or forward test has been run. Win rates, Brier scores, ROI, calibration, holdout results, and uncertainty intervals are intentionally blank.",
                "Unverified / not tested",
                ["noaa_verification", "nist_validation"],
            ),
            entry(
                "Rewards and sponsor",
                "There is no competition, prize amount, sponsor, funding evidence, or published payout rule in the repository.",
                "Not implemented; no funding verified",
                ["nist_multiple", "nfl_responsible"],
            ),
            entry(
                "Legal and responsible-use scope",
                "No user jurisdiction, age/eligibility, operator license, local law, or current local responsible-gambling requirements were assessed. The linked NFL policy article applies to league personnel, not the user's legal status.",
                "Needs jurisdiction-specific review",
                ["nfl_policy", "nfl_responsible"],
            ),
            entry(
                "Automated ingestion and alerts",
                "No live source connector, schedule, secrets, monitoring, or alerting job exists. GitHub Pages publishes the static files; it does not ingest odds or compute lines.",
                "Not built; site is static",
                ["github_pages", "odds_api"],
            ),
        ],
    },
}


NAV_LABELS = {
    "index": "Executive summary",
    "data": "Data requirements",
    "strategies": "Strategy lab",
    "validation": "Validation gates",
    "correlations": "Correlation & pricing",
    "leaderboard": "Leaderboard",
    "sources": "Source register",
    "flagged": "Flagged for review",
}



def render_source_links(source_ids):
    links = []
    for source_id in source_ids:
        source = SOURCES[source_id]
        label = f"{source['organization']} · {source['title']} ↗"
        href = escape(source["url"], quote=True)
        links.append(
            f'<a class="source-link" href="{href}" target="_blank" '
            f'rel="noopener noreferrer">{escape(label)}</a>'
        )
    return '<div class="source-links">' + "".join(links) + "</div>"


def render_row(row):
    value = row["value"]
    value_cell = (
        f'<td class="value-cell">{escape(value)}</td>'
        if value
        else '<td class="value-cell blank-value" aria-label="Unverified; intentionally blank"></td>'
    )
    return (
        "<tr>"
        f"<td>{escape(row['item'])}</td>"
        f"<td>{escape(row['finding'])}</td>"
        f"{value_cell}"
        f'<td class="status-cell">{escape(row["status"])}</td>'
        f"<td>{render_source_links(row['sources'])}</td>"
        "</tr>"
    )


def render_page(slug, page):
    nav_links = []
    for nav_slug, label in NAV_LABELS.items():
        current = ' aria-current="page"' if nav_slug == slug else ""
        nav_links.append(
            f'<a href="{escape(nav_slug)}.html"{current}>{escape(label)}</a>'
        )
    nav = "".join(nav_links)
    rows = "".join(render_row(row) for row in page["rows"])
    title = escape(page["title"])
    subtitle = escape(page["subtitle"])
    count = len(page["rows"])
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Evidence-first NFL line research, validation, and data-readiness dashboard">
  <title>{title} | NFL Research Lab</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <header>
    <div class="top">
      <a class="brand" href="index.html" aria-label="NFL Research Lab home">
        <span class="mark" aria-hidden="true">N</span>
        <span>NFL <strong>Research Lab</strong><small>INDEPENDENT ANALYSIS</small></span>
      </a>
      <span class="badge">RESEARCH ONLY · NO PICKS</span>
    </div>
    <nav aria-label="Main navigation">{nav}</nav>
  </header>
  <main>
    <div class="eyebrow">NFL / {escape(page['title'].upper())}</div>
    <h1>{title}</h1>
    <p class="lead">{subtitle}</p>
    <div class="notice"><strong>Evidence first.</strong> This is a static research dashboard, not a live line engine. No picks, empirical signals, or verified performance are available. Blank values mean unverified, not zero.</div>
    <section aria-labelledby="register-heading">
      <div class="section-head">
        <div><span class="eyebrow">RESEARCH REGISTER</span><h2 id="register-heading">Details &amp; evidence</h2></div>
        <span class="count">{count:02} ENTRIES</span>
      </div>
      <div class="scroll" role="region" aria-label="Scrollable research table" tabindex="0">
        <table>
          <thead><tr>
            <th scope="col">Item</th>
            <th scope="col">Finding / proposed approach</th>
            <th scope="col">Verified value</th>
            <th scope="col">Status</th>
            <th scope="col">Primary source / method reference</th>
          </tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </section>
    <p class="footnote">Source links support the stated source or methodological context. Project-specific statuses are from this repository audit, not claims made by external sources. Proposed methods are not endorsements or proof of an edge. Last review: 2026-11-01 UTC.</p>
  </main>
  <footer>Independent research · Not affiliated with the NFL · <a href="flagged.html">Review limitations</a></footer>
</body>
</html>
'''


def build_pages():
    for slug, page in PAGES.items():
        Path(f"{slug}.html").write_text(render_page(slug, page), encoding="utf-8")


if __name__ == "__main__":
    build_pages()
