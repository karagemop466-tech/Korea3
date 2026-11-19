# Executive summary — NFL line-origination repository, 2026-11-19

Session `arena/0c139968-korea3`, branched from commit `0c54486d` of `main`. On entry the branch was identical to `main` and `origin/main`; the working tree was clean. All prior session work (root dashboard, consolidated hub, verified workbench, price-snapshot desk, decision readiness, capture, lifecycle, depth lab, line/market/origin labs) is already committed in this checkout.

## Scope limitation — official sources could not be re-opened live

This sandbox's outbound egress is limited to `github.com`, `api.github.com`, `codeload.github.com`, `registry.npmjs.org`, `pypi.org` and `files.pythonhosted.org`. Official NFL / club / weather publishers (`nfl.com`, `operations.nfl.com`, `weather.gov`, club depth-chart pages, etc.) **could not be opened live**. No value in this summary is claimed as officially re-verified. Consistent with the repository's standing rule, any value that cannot be confirmed from an official source is left **blank and flagged**; nothing is inferred or filled in.

## What this session verified from committed files only

| Check | Result | What it covers |
|---|---|---|
| `python3 price_lab/check.py` | **36/36 PASS** | Price-snapshot store (47,583 rows: open, close, fair per originated market; fair / market / difference as separate columns; origination order side → total → moneyline enforced 1-2-3 on every row). Verified results feed (137 official 2026 finals; 108 pinned matches exact; 29 finals post-date the pin and are flagged; 7,384-row history feed equals `games.csv` row-for-row). Signal-vs-staking leaderboard (11 strategies on two axes). Demotion gate (6 automatic triggers). Every table row carries a link; no broken internal links; all published KPIs match the data. |
| `python3 readiness/check.py` | **all pass** | Decision-readiness register (76 requirements, one row each: 11 built, 26 partial, 22 not built, 9 blocked, 3 contradicted, 2 owner decision, 2 not checked). Questions & information register, suggestions board (not implemented until the owner chooses a path), flagged-for-review page, official re-checks page. |
| `python3 hub/check_hub.py` | **PASS** | 25 pages; 1,275 table rows; 1,720 official row links; 1,597 blank markers. |
| `python3 pipeline/link_check.py` | **PASS** | 13 pages; 15 internal links (0 broken); 11 external links (0 unregistered). |

`line_lab/check_site.py` and `scripts/verify_site.py` could not be executed here because `pandas`/`scipy` are not installed in the sandbox; CI installs the pinned `requirements.txt` and runs them.

## Irregularities published for review (not hidden, do not block publication)

The repository's Flagged for Review pages record these open items, each with evidence and an official source link:

- **F01** (High) — Week 10 game-status cells blank for Kerby Joseph, Cade Mays and D.J. Reed; the official page lists all three as Out.
- **F02** (High) — Seattle, Cincinnati, the Chargers and Baltimore shown "no injuries reported" although the official page lists players.
- **F03** (High) — Raw injury capture missing 2 Baltimore players (Campbell, Stanley) and 2 blank cells (Hawkins, Randall); row counts disagree across sources (254 / 345 / 347 / the brief's 279 — none agree).
- **F04** (High) — Three builds give three strategy counts (8 / 7 / 18).
- **F05** (High) — Backtest numbers appear on the leaderboard, which the brief forbids.
- **F06** (High) — Two parlay strategies ranked with no joint-probability gate.
- **F07** (High) — 179 depth rows carry an "Unofficial Depth Chart" title; Houston's page is image-only and "Unofficial".
- **F08–F16** (Medium/Low) — Depth-group definition unsettled; no game-book or snap-count source (both paths tried return 404); capture manifest has 0 recorded rows; source-link gates check link presence, not value agreement; the stale Ravens QB example is not reproduced; Colts trades are not parser-verified; Malik Willis's reserve/injured listing is not captured.

## Site — GitHub Pages, landing page and category subpages

The GitHub Pages site serves the repository root (`/`). The landing page (`index.html`) is a clean, simple dashboard with category subpages:

Overview · Decision readiness · Executive summary · Leaderboard · Strategies · Validation · Correlations · Parlays · Player props · Live lines · Data · Sources · Flagged for review · Method · Requirements · Verification · All sessions · Verified workbench · QA · Decisions · Depth Lab · Capture · Lifecycle · Line origination · Markets Ledger · Origination desk

Every build in the repository is reachable from `/sessions.html`. Each page carries its own sources; unverified values are blank and listed for review. Nothing is recommended for betting; no strategy is live (lifecycle records 0 of 18 strategies live).

## Owner decisions still needed (blocking)

Nine blocking questions are open in `readiness/questions.html`, including: whether club-published depth charts count as an official source (Q01), which price settles bets — opening, closing or executable (Q03), whether backtest numbers may ever appear on the leaderboard (Q06), parlay / prop-combination ranking and operator void/push rules (Q05), and the public analysis layer vs private data layer split (Q13).

## Publication

This session commits to `arena/0c139968-korea3`, pushes it, opens a pull request to `main`, merges it, and confirms GitHub Pages deploys successfully. Flagged irregularities and unverified items do not block the merge; they remain on the Flagged for Review page for owner review after the site is live.
