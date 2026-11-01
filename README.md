# NFL Research Lab

**Live static dashboard:** [Executive summary](https://karagemop466-tech.github.io/Korea3/)

An evidence-first research brief for NFL line origination. It catalogs proposed single-game, player-prop, cross-game parlay, and same-game player-combination strategies; data requirements; validation gates; correlation measurements; and leaderboard rules.

## Honest status

This repository is a static research dashboard—not a live betting service or line engine. It currently has **no licensed historical odds, no ingested event-level dataset, no trained model, no empirical correlation coefficients, no backtest/forward test, no picks/signals, no eligible leaderboard entries, and no funded rewards**. Values that cannot be verified are intentionally blank and flagged for review. Luck cannot be removed; validation can only test whether evidence is consistent with skill and whether performance beats a pre-specified baseline.

The NFL's official pages describe player/team statistics, Next Gen Stats, current injury reports, and per-game Game Book PDFs. They do not establish that a complete, timestamped, bulk historical feed is available to this project. The commercial historical-odds provider documented in the source register is only a possible acquisition route: its page describes paid snapshots, and this project has not obtained a subscription, license, or data. Operator rules also vary by market, jurisdiction, and date.

No scheduled ingestion or automated line generation is configured. A live system must not be claimed until those data, rights, and validation prerequisites are satisfied.

## Site map

- `index.html` — executive summary
- `data.html` — data requirements and provenance
- `strategies.html` — signal hypotheses
- `validation.html` — validation gates
- `correlations.html` — correlation and pricing methods
- `leaderboard.html` — eligibility, ranking, and reward status
- `sources.html` — source register with scope notes
- `flagged.html` — blocked/unverified items

Every table row has one or more named HTTPS primary-source or method-reference links. External references support the cited facts or methodological context; project-specific statuses are based on repository inspection. The dashboard does not imply that a linked source endorses a proposed strategy.

## Build and check

Requires Python 3; no third-party packages.

```sh
python3 scripts/build.py
python3 scripts/check.py
```

The checker verifies expected pages, table structure, navigation and local assets, registered HTTPS source links for every row, and blank verified-value cells. It does not crawl external websites or certify that a source proves an internal project status; primary links were reviewed separately and their limits are recorded in the source register and `COORDINATION.md`.

GitHub Pages is configured to publish the repository root from `main`; the current Pages status and URL were checked through the GitHub API. The site is published at the link above.
