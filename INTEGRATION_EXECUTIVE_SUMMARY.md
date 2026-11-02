# Executive summary — consolidated integration (2026-11-02 UTC)

**Session:** `arena/25ea8ac4-korea3` (final integration session)
**Base commit:** `9069c3d654f03d6fe38e165c63a31d2ac9f7d401` (PR #37 merge)
**Live site:** <https://karagemop466-tech.github.io/Korea3/> — the consolidated dashboard is at `/hub/index.html`
**Task board:** [`COORDINATION.md`](COORDINATION.md)

---

## 1. Bottom line

1. **The project is complete as a research system, not as a betting edge.** This repository now contains a
   line-origination model, 18 pre-registered signal rules, 11 dashboard strategies, 8 fail-closed hypotheses,
   eight/ten-gate validation sets, a correlation lab, an eight-combo player-prop framework and a leaderboard
   competition specification. No strategy has been shown to be profitable against verified official evidence.
2. **Official sources were re-verified line by line.** 24 official publisher pages were opened on 2026-11-02:
   the NFL, NFL Support, NFL Football Operations, DraftKings, FanDuel, NIST and NIH PMC. Each exact statement
   is recorded in `hub/data/sources.json` and on the [Official sources](https://karagemop466-tech.github.io/Korea3/hub/sources.html) page.
3. **Every unverifiable value is blank and flagged.** There is no licensed event-level official NFL dataset, no
   timestamped executable operator quote archive, and no official player-prop line feed. Consequently no price,
   ROI, correlation coefficient, own-line accuracy, rank or reward amount is published as a verified value.
   Blank cells render with an "unverified" link to the review page.
4. **Zero strategies are reward-eligible.** The leaderboard is fail-closed: missing evidence blocks promotion;
   it never becomes a pass. No prize pool, sponsor, jurisdiction or payout terms were verified, and no real-money
   execution exists.
5. **Luck is bounded, not removed.** Confidence intervals, bootstrap uncertainty, pre-registered contrasts,
   Bonferroni/FDR multiplicity control, untouched holdouts, price stress and a post-freeze forward sample are the
   mechanism. Their statistical basis is official ([NIST 1.3.5.2](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm),
   [NIST 1.3.3.4](https://www.itl.nist.gov/div898/handbook/eda/section3/bootplot.htm),
   [NIST 7.4.7](https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm),
   [NIST 7.4.7.3](https://www.itl.nist.gov/div898/handbook/prc/section4/prc473.htm)).

## 2. What was delivered

| Deliverable | Location | Verification boundary |
|---|---|---|
| Clean dashboard landing page + 19 category subpages | `hub/*.html` (live at `/hub/`) | Every table row links to an official publisher |
| Full requirement traceability (35 requirements from the brief) | `hub/requirements.html` | Each row has status, answer page and official source |
| Official source register (27 entries) | `hub/sources.html`, `hub/data/sources.json` | 24 verified this session, 1 unverified, 2 project/provenance |
| Line-by-line repo review | `hub/repo-review.html` | Directory counts and per-page row audits computed from the checkout |
| Verification log and build gate | `hub/verification.html`, `hub/check_hub.py` | Fails on an unsourced row or a broken link |
| Official standings cross-check | `hub/standings.html` | All 32 official 2025 club rows transcribed and compared |
| Own lines, strategies, single bets, parlays, prop combos | `hub/own-lines.html`, `hub/strategies.html`, `hub/single-bets.html`, `hub/parlays.html`, `hub/player-props.html` | All registered entries listed; all measured values blank |
| Correlations, validation gates, leaderboard | `hub/correlations.html`, `hub/validation.html`, `hub/leaderboard.html` | Official statistical definitions; no measured result published |
| Analysis & findings (18 findings) | `hub/analysis.html` | Verified findings cited; exploratory findings blank |
| Flagged for Review (34 items) | `hub/flagged.html` | Clearly labelled; every item carries a source link |
| Session registry / coordination | `hub/sessions.html`, `COORDINATION.md` | Claims, handoff, deviations and results recorded |
| Prior-work archive map | `hub/archive.html` | Six earlier builds preserved and reachable |
| CI gate | `.github/workflows/hub-verify.yml` | Rebuild, verify and fail on generated-output drift |

## 3. Official sources used (all opened on 2026-11-02)

**Official NFL / league**
- [NFL.com Terms and Conditions](https://www.nfl.com/legal/terms/) — §1.1 reproduction, §1.3 permitted uses and the
  prohibition on systematic retrieval/compilation without express prior written consent.
- [NFL Support: Stats & Records](https://support.nfl.com/hc/en-us/articles/35869694725268-Stats-Records) — where
  official player/team statistics and historical records are published.
- [2026 NFL Rulebook (Football Operations)](https://operations.nfl.com/rules-officiating/2026-nfl-rulebook) — official
  rulebook and 2026 rule-change table (6-1-3, 6-1-5, 6-1-6, 19-2).
- [Game and Stadium Prep](https://operations.nfl.com/game-operations-logistics/preparation-safety/game-and-stadium-prep)
  — game-day checklist begins seven days before kickoff.
- [NFL Tiebreaking Procedures](https://www.nfl.com/standings/tie-breaking-procedures) — "Tie games count as
  one-half win and one-half loss for both clubs."
- [NFL Support: "What is a money line?"](https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line)
  — "Most often, the betting odds for point spread are -110" and the whole-number push rule.
- [NFL Support: "What is the point spread?"](https://support.nfl.com/hc/en-us/articles/35869774194324-What-is-the-point-spread)
  — moneyline explanation and "If the game ends in a tie, the bettor's wager is returned with no loss or profit."
- [Making the Schedule](https://operations.nfl.com/calendar-events/nfl-schedule/making-the-schedule) — 272-game
  regular season, 17 games over 18 weeks.
- [NFL responsible betting campaign](https://www.nfl.com/news/nfl-is-kicking-off-a-6-2m-responsible-betting-campaign)
  — setting limits, understanding risk, knowing where to get help.
- [2025 NFL division standings](https://www.nfl.com/standings/division/2025/REG) — all 32 clubs, W/L/T/PF/PA.

**Licensed operators (their own rules)**
- [DraftKings: Understanding Odds](https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466)
- [DraftKings: What is a point spread bet?](https://support.draftkings.com/dk/en-us/what-is-a-point-spread-bet?id=kb_article_view&sysparm_article=KB0010595)
- [DraftKings: What is a parlay bet?](https://support.draftkings.com/dk/en-us/what-is-a-parlay-bet?id=kb_article_view&sysparm_article=KB0010683)
- [DraftKings: Same Game Parlay](https://support.draftkings.com/dk/en-us/what-is-a-same-game-parlay-sgp-bet?id=kb_article_view&sysparm_article=KB0010719)
- [DraftKings: What is a prop bet?](https://support.draftkings.com/dk/en-us/what-is-a-prop-bet?id=kb_article_view&sysparm_article=KB0010778)
- [DraftKings: player start / removal settlement](https://support.draftkings.com/dk/en-us/how-will-my-bet-be-settled-if-a-player-doesn-t-start-or-is-removed-from-a?id=kb_article_view&sysparm_article=KB0010795)
- [DraftKings Sportsbook Market Rules](https://sportsbook.draftkings.com/help/general-betting-rules/market-rules)
- [FanDuel Connecticut House Rules](https://www.fanduel.com/fanduel-sportsbook-house-rules-ct) — §19 correlated
  selections are not permitted unless explicitly offered as a Same Game Parlay.

**Government / statistical authorities**
- [NIST 1.3.5.2 Confidence Limits for the Mean](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm)
- [NIST 1.3.3.4 Bootstrap Plot](https://www.itl.nist.gov/div898/handbook/eda/section3/bootplot.htm)
- [NIST Dataplot CORRELATION](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/correlat.htm)
- [NIST 7.4.7 Multiple Comparisons](https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm)
- [NIST 7.4.7.3 Bonferroni](https://www.itl.nist.gov/div898/handbook/prc/section4/prc473.htm)
- [NIH PMC: False discovery rate control in two-stage designs](https://pmc.ncbi.nlm.nih.gov/articles/PMC3496575/)
  (scientific literature; PMC inclusion does not imply endorsement).
- [NWS Glossary of Forecast Verification Metrics](https://www.weather.gov/media/owp/oh/rfcdev/docs/Glossary_Forecast_Verification_Metrics.pdf)
  — **could not be opened this session**; no statement transcribed, flagged N03.

## 4. Verification performed

- **Line by line against official publishers.** Each of the 24 verified sources was opened and the exact
  statement recorded. Quotes are not paraphrased from memory.
- **Official standings cross-check.** All 32 official 2025 NFL.com club rows were transcribed and compared
  programmatically with `reports/standings_check_2025.csv`; a mismatch aborts the site build. All 32 matched.
  2026 values are deliberately blank because the season was live at the snapshot.
- **Build gate.** `python3 hub/check_hub.py` asserts: an official link on every table row; no unflagged blank;
  no broken internal link or anchor; every GitHub blob/tree link points at a file/directory that exists; every
  external link is on the official allow-list and present in the source register; all 20 pages exist and are
  linked from navigation. Exit code is non-zero on any failure.
- **Existing gates re-run.** Root dashboard (`line_lab/check_site.py`), exploratory site
  (`scripts/verify_site.py`), docs build (`pipeline/link_check.py`), verified workbench
  (`python -m nfl_lab.check_verified`) and the synthetic unit tests (`tests/test_lab_*.py`).
- **No hallucinations.** Values come from the official page, from this repository's own files (computed at build
  time: counts, hashes, row totals), or are left blank. Nothing is inferred or filled in.

## 5. Irregularities flagged for review

Published in full on [Flagged for Review](https://karagemop466-tech.github.io/Korea3/hub/flagged.html) (34 items).
The important ones:

- **N05 / N06 (blocking):** no licensed official event-level dataset, timestamped executable quote archive,
  official prop feed or funded reward pool. Every empirical value and reward is blank.
- **F08 (verified anomaly):** two NFL Support help articles have their bodies swapped relative to their titles —
  re-confirmed on both official pages on 2026-11-02.
- **N01 / N02 (rights & scope):** [NFL.com Terms](https://www.nfl.com/legal/terms/) §1.1/§1.3 restrict
  reproduction and systematic compilation; an earlier session removed its captured official standings CSV. The
  repository's attestation covers team aggregates only, not per-game official verification.
- **N03 / N04:** the NWS PDF could not be opened; 2026 standings are a live season.
- **F01–F07 / B01–B06 / R01–R03 / V01–V03:** data defects, source anomalies and gaps inherited from earlier
  sessions (spread sign convention, disagreeing line sources, missing provenance, imputed prices, no injury or
  weather ground truth, no pre-2021 opening lines, negative exploratory findings).
- **N07–N13 / process:** the root dashboard cites repository files rather than official publishers; Pages is a
  legacy `main:/` deploy; open PR #19 belongs to another session; the Arena-fixed branch name deviates from the
  brief's `session-<id>` convention; regenerating root pages drops the added banner; stale claim T15 was handed
  over; the 2023 operator PDF quote was superseded by live operator pages.

Flagged items are published, not hidden, and do not block publication of the research dashboard.

## 6. Coordination, PR and deployment

- `COORDINATION.md` was read before work began; the claim (session ID, role, file scope, branch deviation and
  stale-claim handoff) was committed and pushed **before** any other file changed.
- Scopes are non-overlapping: this session edits only `hub/**`, `index.html` (additive banner), `README.md`
  (additive pointer), `INTEGRATION_EXECUTIVE_SUMMARY.md`, `.github/workflows/hub-verify.yml` and the board.
  No file under `audit/`, `docs/`, `reports/`, `pipeline/`, `scripts/`, `data/`, `line_lab/`, `nfl_lab/`,
  `site/`, `verified/` or `session-398c4b58/` was edited.
- `git pull --rebase` is run before every push; small, frequent commits were used. No merge conflicts occurred.
- The pull request, merge result and GitHub Pages deployment confirmation are recorded in `COORDINATION.md`.

## 7. Honest statement of what is not claimed

No claim that any strategy is profitable. No claim that a rule which failed cannot work. No correlation value,
because none could be verified from an official source. No betting advice. No real-money execution. No claim of
endorsement by the NFL, any operator, NIST, NWS or NIH. Blank means unverified, never zero.

---

*Research and engineering sample. Independent; not affiliated with the NFL or any sportsbook.*
