#!/usr/bin/env python3
"""Generate a dependency-free GitHub Pages research dashboard."""
from html import escape
from pathlib import Path

NFL='https://support.nfl.com/hc/en-us/articles/35869694725268-Stats-Records'
NGS='https://nextgenstats.nfl.com/stats/passing'
DK='https://help.draftkings.com/hc/en-us/articles/4405235694739-What-is-a-parlay-bet-US'
NIST='https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm'
COR='https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=921446'
OPS='https://operations.nfl.com/game-operations-logistics/preparation-safety/game-and-stadium-prep'
POL='https://www.nfl.com/news/nfl-increases-gambling-policy-education-integrity-monitoring-efforts-following-successful-offseason'
RG='https://www.nfl.com/news/nfl-is-kicking-off-a-6-2m-responsible-betting-campaign'
PAGES={
'index':('Executive summary','A decision-ready research brief, not a betting service.',[
('Current state','No strategy has passed validation; no picks, real lines, measured correlations or rewards are published.','Needs review',NFL),
('Core limitation','Luck cannot be eliminated. Historical out-of-sample evidence and uncertainty estimates can only help distinguish skill from noise.','Research design',NIST),
('Priorities','Obtain timestamped official outcomes and licensed historical executable odds and settlement rules before training or ranking.','Blocked',NFL),
('Competition','Rank only strategies that pass every gate using a pre-registered, risk-adjusted out-of-sample score; award no prizes before validation.','Proposed',NIST),
('Risk','Betting can lose money. Set limits and follow applicable laws and league policies.','Safety',RG),
]),
'strategies':('Strategy lab','Hypotheses and proposed methods, not established edges or recommendations.',[
('Single-game lines','Estimate a pregame distribution of score margin and total from historical team performance and availability; translate the distribution into cover and total probabilities. Compare against timestamped executable prices.','Unvalidated',NFL),
('Player props','Model player participation, opportunity and conditional production. Forecast the full distribution, including the chance of nonparticipation; reconcile book-specific settlement.','Unvalidated',NGS),
('Cross-game parlays','Estimate joint win probability from aligned outcomes; do not assume independence just because games differ. Compare the full joint price and rule-specific expected return.','Unvalidated',DK),
('Same-game player combinations','Model jointly from shared game scenarios and player usage. Measure leg outcome dependence at matched thresholds; do not multiply marginal probabilities without evidence.','Unvalidated',DK),
('Market benchmark','Compare probability forecasts to a timestamped market baseline and evaluate calibration and proper scoring rules; account for the bookmaker margin.','Unvalidated',DK),
]),
'validation':('Validation gates','All thresholds below are proposals, not externally verified standards. No gate has passed.',[
('1 · Data integrity','Require source, timestamp, event ID, market, line, price, book and actual settlement; quarantine missing, revised or duplicate records. No post-decision features.','Blocked: data unavailable',NFL),
('2 · Chronology','Freeze the model and selection criteria before each forward test. Train on earlier games; tune on a later period and reserve a final untouched future holdout.','Not run',NIST),
('3 · Probability quality','Evaluate Brier score and log loss versus a market baseline; inspect calibration by probability bucket and sample size. Include uncertainty and pushes/voids.','Not run',NIST),
('4 · Returns and uncertainty','Calculate settled net returns at executable prices, fees and void rules. Use game-clustered or week-block bootstrap confidence intervals; report sensitivity to selection and price.','Not run',NIST),
('5 · Selection bias','Register every candidate and tuning trial. Correct for multiple comparisons and assess the selected winner on untouched data; no rewards for an in-sample winner.','Not run',NIST),
('6 · Stability and deployment','Require positive lower confidence bound on holdout return, improved probability score vs baseline, and robustness across seasons, markets and realistic price slippage. Freeze thresholds before evaluation.','Not run',NIST),
]),
'correlations':('Correlation & pricing','A measurement plan; no empirical coefficients are available in this repository.',[
('Player leg pairs','Compute Pearson correlation of binary leg outcomes (phi) at the actual quoted thresholds, by leg type and pregame snapshot. Report n, uncertainty and missingness.','',COR),
('Cross-game returns','Measure correlation of settled strategy returns by aligned week, including zero-exposure weeks; assess shared conditions and use block uncertainty.','',COR),
('Joint probabilities','Estimate P(A and B) directly from joint outcomes or a validated joint simulation; a single correlation is not enough for arbitrary multileg pricing.','',DK),
('Fair price','For a simple no-push binary wager, fair decimal odds = 1 / p and expected net return per unit = p × decimal odds − 1. Model pushes, voids and fees separately.','',DK),
('Interpretation','Correlation is not causation; historical fit does not guarantee prediction. Pair estimates may be unstable or unavailable with small samples.','',COR),
]),
'leaderboard':('Leaderboard','No fabricated rankings: candidates are listed without scores until all gates pass.',[
('Single-game distribution model','Holdout score: ; return: ; reward: .','Not eligible',NFL),
('Player opportunity model','Holdout score: ; return: ; reward: .','Not eligible',NGS),
('Cross-game joint model','Holdout score: ; return: ; reward: .','Not eligible',DK),
('Same-game joint player model','Holdout score: ; return: ; reward: .','Not eligible',DK),
('Proposed ranking','Among eligible candidates, rank by lower confidence bound of holdout net return per unit; use out-of-sample log loss relative to market as a tie-breaker. Pre-register budget, prizes, ties and exposures.','Not implemented',NIST),
]),
'sources':('Source register','Primary-source references checked for the specific statements described; links are for manual review.',[
('NFL stats and records','NFL directs readers to official player, team and historical records.','Official league',NFL),
('NFL Next Gen Stats','The NFL describes passing metrics including attempts, yards and air yards.','Official league',NGS),
('Game-day operations','The NFL describes game-day administrative reports including inactive lists; historical publication timestamps still need verification.','Official league',OPS),
('Parlay rules','DraftKings describes parlays and restrictions on correlated selections; same-game settlement requires sport-specific rules.','Official operator',DK),
('Uncertainty','NIST explains confidence limits and discusses bootstrap intervals for other estimators. The proposed block procedure is a project design, not a NIST endorsement.','Official government',NIST),
('Correlation caution','NIST notes correlation is not causation and historical fit does not assure prediction.','Official government',COR),
('Integrity','NFL describes gambling-policy restrictions for players and personnel; consult current policy and local law.','Official league',POL),
]),
'flagged':('Flagged for review','Unverified values remain blank. These issues do not imply the strategies work.',[
('Historical odds and execution','Official timestamped, executable historical prices, quote availability and transaction costs have not been obtained.','Unverified / blocked',DK),
('Official event-level outcomes','No official historical dataset has been ingested, reconciled or independently audited line by line.','Unverified / blocked',NFL),
('Correlations and samples','Coefficient: ; sample size: ; interval: . No qualified matched dataset is available.','Unverified',COR),
('Strategy performance','Win rate: ; ROI: ; calibrated probabilities: ; holdout score: . No backtest or forward test has been run.','Unverified',NIST),
('Specific settlement rules','NFL player nonparticipation, voids, pushes and same-game repricing depend on operator, jurisdiction, date and market. No complete rules archive is in the repo.','Unverified',DK),
('Rewards','Prize amount: ; funding: ; sponsor: . No competition or funded rewards exist.','Unverified',NIST),
('Legal and eligibility','Applicable jurisdiction, age, licensing and current policy have not been established. Do not place wagers based on this research.','Needs review',POL),
])}
nav=''.join(f'<a href="{k}.html">{escape(v[0])}</a>' for k,v in PAGES.items())
for slug,(title,subtitle,rows) in PAGES.items():
    table=''.join('<tr>'+''.join(f'<td>{escape(x)}</td>' for x in (name,detail,status))+f'<td><a href="{escape(url,quote=True)}" target="_blank" rel="noopener noreferrer">Official source ↗</a></td></tr>' for name,detail,status,url in rows)
    html=f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="description" content="NFL line research and validation dashboard"><title>{escape(title)} | NFL Research Lab</title><link rel="stylesheet" href="style.css"></head><body><header><div class="top"><a class="brand" href="index.html"><span class="mark">N</span><span>NFL <strong>Research Lab</strong><small>INDEPENDENT ANALYSIS</small></span></a><span class="badge">RESEARCH ONLY</span></div><nav aria-label="Main navigation">{nav}</nav></header><main><div class="eyebrow">NFL / {escape(title.upper())}</div><h1>{escape(title)}</h1><p class="lead">{escape(subtitle)}</p><div class="notice"><strong>Evidence first.</strong> No live betting signals or verified strategy performance are available. Blank values mean unverified, not zero.</div><section><div class="section-head"><div><span class="eyebrow">RESEARCH REGISTER</span><h2>Details &amp; evidence</h2></div><span class="count">{len(rows):02} ENTRIES</span></div><div class="scroll"><table><thead><tr><th scope="col">Item</th><th scope="col">Finding / proposed approach</th><th scope="col">Status / value</th><th scope="col">Source</th></tr></thead><tbody>{table}</tbody></table></div></section><p class="footnote">Proposals are our research designs, not claims that a source endorses them. Sources substantiate the relevant underlying facts or method context. Last research review: 2026-11-01.</p></main><footer>Independent research · Not affiliated with the NFL · <a href="flagged.html">Review limitations</a></footer></body></html>'''
    Path(slug+'.html').write_text(html,encoding='utf-8')
