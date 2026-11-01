# Requirement traceability

Every requirement from the project brief, what was actually delivered, and where the evidence lives. Status values:
`done` (delivered and evidenced), `done / negative` (delivered, the research answer was negative), `partial`,
`blocked` (cannot be delivered without data that is not reachable).

| # | Requirement | Delivered | Status | Evidence |
|---|---|---|---|---|
| R1 | Collect, organise and analyse against a full requirement list | This table plus the site's Requirements page; inputs pinned and hashed | done | `docs/requirements.md`, `requirements.html` |
| R2 | Originate own NFL lines | Model spread, total and win probability for every unplayed game (164 in the snapshot) | done | `lines.html`, `pipeline/run_all.py::predict_live` |
| R3 | Research and develop strategies that generate useful signals | 11 pre-registered strategies: Elo margin, Elo moneyline, scoring-profile totals, rest asymmetry, divisional home dog, weather under, referee tendency, backup-QB fade, two parlay cards, win-total futures | done | `docs/preregistration.md`, `pipeline/strategies.py` |
| R4 | Leaderboard competition with rewards for top strategies | Pre-registered reward rule, ranking and eligibility; **no strategy became eligible**, no prize money is funded | partial | `leaderboard.html` |
| R5 | Single bets | S1–S8 settle single bets at recorded closing prices | done | `data/derived/bets.csv` |
| R6 | Parlays | S9/S10 two-leg cross-game cards, plus measured dependence for pricing multi-leg cards | done | `parlays.html` |
| R7 | Player prop bet combos | Blocked: no reachable official player logs or licensed prop prices; input schema and estimator committed, all values blank | blocked | `props.html`, `pipeline/props.py` |
| R8 | Each strategy must pass validation gates | Nine gates implemented and applied; 0 of 11 passed all nine | done / negative | `validation.html`, `pipeline/evaluation.py` |
| R9 | Determine correlation values | phi for same-game pairs, cross-game dependence, team-scoring correlation, three-leg joint vs product, strategy-return matrix — each with n and bootstrap interval | done | `correlations.html`, `pipeline/correlations.py` |
| R10 | Remove luck from the equation | Week-block bootstrap intervals, permutation test, Benjamini–Hochberg across 11 tests, untouched holdout, and a simulated best-of-11 luck band | done | `methodology.html`, `pipeline/extras.py` |
| R11 | Build strategies that are selectively skill based | Selectivity measured (share of games bet, win rate, Brier skill vs market); no candidate showed positive Brier skill or a positive lower bound | done / negative | `leaderboard.html` |
| R12 | Executive summary of important details | `EXECUTIVE_SUMMARY.md` plus the dashboard landing page | done | `EXECUTIVE_SUMMARY.md`, `index.html` |
| R13 | Review the repository line by line and flag irregularities | Repository was a bare README when the first session started; the previous session's placeholder site was audited, then replaced by generated pages. Irregularities listed individually | done | `COORDINATION.md`, `flagged.html` |
| R14 | Verify against official, trusted sources, with links | nflverse snapshot hashed and re-verified; field semantics checked against the nflverse dictionary; every table row links a source; external hosts marked unverified | done | `sources.html`, `data.html` |
| R15 | GitHub Pages site: clean dashboard, subpages by category, all findings in tables | 13 generated pages, responsive CSS, no external dependencies, table filter script | done | https://karagemop466-tech.github.io/Korea3/ |
| R16 | Never infer or fill values; blank + flag when unconfirmed | Blank renderer links every unknown to the review page; the site check fails on a blank without that link or a table row without a source | done | `pipeline/check_site.py` |
| R17 | Parallel-session coordination | `COORDINATION.md` task board with owner, scope, status and a session log | done | `COORDINATION.md` |
| R18 | Open a PR, merge it, deploy and confirm Pages | Session branch merged to `main` through a PR, Pages deployment verified | done | `COORDINATION.md` session log |

## Notes on scope

- **Staking and bankroll:** deliberately out of scope. Every bet is 1 unit flat, so results are comparable and cannot be
  flattered by a staking plan.
- **R4 partial:** the competition mechanics (eligibility, ranking, reward formula) exist and run. The reward *payment*
  does not exist because no strategy qualified and no pool is funded. Both facts are published rather than papered over.
- **R7 blocked:** the blocker is data availability, not method. `pipeline/props.py` contains the required schema and the
  estimator; it exits cleanly while the inputs are absent.
