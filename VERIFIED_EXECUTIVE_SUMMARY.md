# Verified workbench — executive summary

**Date:** 2026-11-01 UTC  
**Scope:** official-evidence-only layer for NFL line origination, signal research, validation, correlations, parlays, player-prop combinations and leaderboard eligibility.  
**Live path after merge:** `/verified/` under the repository GitHub Pages site.

## Bottom line

- **Verified empirical values published: 0.** No licensed, event-level official NFL dataset, timestamped executable operator quote archive, or admitted player-prop dataset was available under the project’s verification and data-rights rules.
- **Reward-eligible strategies: 0.** The workbench is fail-closed: missing evidence blocks promotion; it never becomes a pass.
- **Real-money execution: 0.** No sportsbook account access, no bet placement, no funded prize pool.
- **Exploratory work is preserved, not promoted.** Earlier sessions produced third-party-data backtests and dashboards. They remain reachable from the main repository dashboard and session index, but their prices, correlations, ROI and rankings are not treated as official verification here.

## What was delivered

| Deliverable | Location | Verification boundary |
|---|---|---|
| Typed contracts for games, quotes, forecasts, settlements and evidence | `nfl_lab/contracts.py` | Rejects missing lines, non-finite values, post-kickoff pregame quotes and future feature timestamps. |
| Evidence admission and official publisher allowlist | `nfl_lab/evidence.py` | A URL is not a redistribution licence. Stored data requires licensed/public-domain evidence and a pinned hash. |
| Exact odds, settlement, parlay and dependence arithmetic | `nfl_lab/pricing.py` | American/decimal conversion, push/void handling, explicit SGP rules, phi, joint bounds and required phi. |
| Causal line-origination and player-prop model specifications | `nfl_lab/models.py` | Expanding-window team ratings; participation mixture; scenario-based joint probabilities. Emits nothing without admitted inputs. |
| Ten fail-closed validation gates | `nfl_lab/validation.py` | Preregistration, evidence/rights, chronology, sample, probability quality, economics, multiplicity, stability, execution/risk, forward freeze. |
| Eight pre-registered strategy hypotheses | `nfl_lab/strategies.py` | Singles, player props, parlays, joint-player combos, market baseline and correlation stability filter. |
| Official source register | `nfl_lab/sources.json` | 19 primary league/operator/government sources reviewed for the exact claims shown. |
| Static verified dashboard | `verified/` | 12 pages; every table row links to an official source; unverified values are blank. |
| Synthetic unit tests | `tests/test_lab_*.py` | 24 tests pass. Fixtures are synthetic and are never published as NFL findings. |
| CI workflow | `.github/workflows/lab-validate.yml` | Rebuilds the verified dashboard, runs tests and checks, and fails on generated-output drift. |

## Key decisions

1. **No NFL scraping.** NFL.com Terms §§1.1 and 1.3 restrict reproduction and systematic compilation without express prior written consent. A proposed collector was stopped before execution and removed.
2. **No imputed prices.** Missing operator quotes remain blank. Community closing lines are not substituted for official executable quotes.
3. **No unverified correlations.** Earlier third-party phi/r estimates remain in the exploratory archive. The verified correlation register is blank until matched official leg outcomes at quoted thresholds are admitted.
4. **Luck is not “removed.”** The workbench estimates uncertainty: season-week cluster bootstrap, paired probability-score comparison, Bonferroni multiplicity control, price stress, drawdown/exposure limits and a post-freeze forward sample.
5. **Rewards are eligibility-only.** No rank, score or prize is published for a strategy that has not passed every gate. Reward amounts remain blank until funding, sponsor, legal eligibility and payout terms are verified.

## Validation gates

| Gate | Requirement |
|---|---|
| Preregistration | Frozen protocol digest and complete registered trial family. |
| Evidence and rights | Official event evidence, operator rules and redistribution rights for every settled bet. |
| Chronology | Features ≤ forecast < kickoff; disjoint train/tune/holdout/forward windows; no duplicate parlay legs. |
| Sample | Minimum untouched holdout bets, season-week clusters and seasons. |
| Probability quality | Paired Brier improvement lower bound > 0 and no worse log loss versus a timestamped baseline. |
| Economics | Holdout net ROI lower confidence bound > 0 and mean ROI ≥ protocol floor. |
| Multiplicity | Bonferroni-adjusted cluster p ≤ alpha across the full registered family; BH q reported as secondary. |
| Stability | Positive in ≥2/3 holdout seasons, no season >50% of profit, positive after decimal slippage. |
| Execution and risk | Verified executable quotes; drawdown and weekly exposure within pre-registered unit limits. |
| Forward freeze | Post-freeze forward/paper sample meets minimum size and has positive net ROI; no real-money execution. |

## Open blockers

- Licensed event-level official NFL outcomes.
- Timestamped executable historical operator quotes and archived settlement rules.
- Licensed official player game logs and operator prop quotes.
- Matched official leg outcomes for threshold-specific correlation estimates.
- Verified holdout/forward performance for any strategy.
- Funded reward pool, sponsor, jurisdiction, age and licensing verification.

These are published on `verified/flagged.html` and do not block publication of the research workbench. They do block any verified empirical claim, betting signal or reward.

## Sources

Primary sources are listed row-by-row in `verified/sources.html` and machine-readably in `nfl_lab/sources.json`. They include NFL.com terms and stats guidance, NFL Football Operations rulebook/game-day preparation, DraftKings odds/spread/parlay/SGP/prop settlement help, NIST confidence/bootstrap/correlation/multiple-comparison references, NWS forecast-verification metrics, and an NIH-hosted FDR article. Sources support the specific statements shown; they do not endorse the project or verify betting performance.

## Reproduce

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m pytest tests/test_lab_*.py -q
.venv/bin/python -m nfl_lab.run
.venv/bin/python -m nfl_lab.check_verified
```

The default input set is intentionally empty. Optional licensed inputs belong in `nfl_lab/inputs/*.jsonl` and must pass the same contracts. No manual user input is required to build or check the verified view.
