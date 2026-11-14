# Origination desk — executive summary

**Session `arena/5f341290-korea3`, 2026-11-14. Branch `arena/5f341290-korea3` → `main`.**
**Live at <https://karagemop466-tech.github.io/Korea3/origin_lab/index.html>**
**Rebuild with `python3 origin_lab/run_all.py`. Verifier: `origin_lab/check.py` (fail-closed).**

---

## What was asked and what exists

Eight numbered requirements, none of which existed anywhere in the repository before this session.
`grep -ril` across every `.py`, `.json`, `.md` and `.html` in the tree returned **zero** files for
`price snapshot`, `demotion` and `fair line`, and the `R1`–`R18` traceability tables in
`docs/requirements.md` and `line_lab/docs/requirements.md` contain none of the eight.

All eight are now built, in a new additive subtree at `origin_lab/`, and every claim below is
recomputed from the raw inputs by `origin_lab/check.py` rather than read back out of its own output.

| # | Requirement | Delivered | The number that matters |
|---|---|---|---|
| 1 | Price-snapshot store with opening and closing numbers for every originated market | **built** | 43,434 rows. **Opening numbers exist for 272 games — 3.76%** — all 2021, one book (Westgate), spread and total only. **No opening moneyline exists anywhere.** |
| 2 | Verified results feed so backtests and ROI can be computed | **built** | 21,312 settled market rows. The 137-game 2026 feed reconciles to the league's own standings for **all 32 clubs with zero mismatches** (6,291 points for, 6,291 against). |
| 3 | Originate side, then total, then moneyline | **built** | 7,239 rows, **0 identity failures**. The identity is `home = (total + margin)/2`, `away = (total − margin)/2`. |
| 4 | Fair line, market line and difference as separate columns | **built** | Three columns per market on 272 2026 rows; the sign convention is printed above the table. |
| 5 | Separate signal from staking in the leaderboard | **built** | Two rankings and the gap between them. **Best signal score: −2.01%.** Largest rank moved by staking alone: 1. |
| 6 | Track the depth of the replacement, not just the fact | **built** | 80 replacement rows. **68 reach string 2, 1 reaches string 3, 11 reach past the last name the club publishes.** Total depth cost 70. |
| 7 | Correlations from officially sourced numbers only, n published | **built** | 8 officially sourced correlations plus 2 parlay-leg dependences, **every one with n and a Fisher interval**. 4 more are blank with a reason. |
| 8 | A demotion gate that sends a live strategy back to paper | **built** | 8 demotion triggers with windows, statistics, thresholds and actions. **All report NOT APPLICABLE — nothing is live.** |

---

## The three findings that should be read before any other number

### 1. The market beats the model, on all three markets

| Market | Our error | Closing market error | Rows |
|---|---|---|---|
| Side (MAE, points) | 10.593 | **10.245** | 5,307 |
| Total (MAE, points) | 10.826 | **10.519** | 5,307 |
| Moneyline (Brier) | 0.2208 | **0.2115** | 5,173 |

Out-of-sample, 2006 onward, coefficients frozen after 2005. This is not a bettable edge and the site
does not present it as one. Whether it is a *defect* depends on what the model is for: if it exists to
beat the market, it is failing; if it exists to be an independent number to measure the market
against, it is doing its job. **That is a question, not a fact — see Q11.**

### 2. Almost no opening numbers exist, so closing-line value cannot be computed

The store holds an opening number for 272 of 7,239 priced games: one season, one book, two of the
three markets, and no moneyline at all. Every bet on the leaderboard is therefore struck at the
recorded **closing** price, which is the optimistic convention.

The consequence is not cosmetic: **closing-line value is undefined, so promotion gate P10 cannot be
evaluated, so no strategy can be promoted, so nothing can go live, so every demotion gate is
inoperative.** One missing data class disables the entire promotion-to-demotion chain. That is the
single most consequential thing on this site, and it is why suggestion **K01** is scored highest.

A related number worth seeing: over the 272 games that do carry both an opening and a closing number,
the open-to-close spread move has a **standard deviation of 4.40 points**, far wider than a weekly NFL
market normally moves. It is published and flagged (F-A11) and used as an input nowhere.

### 3. No official publisher prints an NFL price — and that collides with requirement 7

The NFL publishes rules, schedules, results, standings and player availability. It does not publish
point spreads, totals, moneylines or prop prices, and neither does any club.

Requirement 7 says correlations come from officially sourced numbers. Four correlations the project
would normally publish cannot be computed under that rule, because each needs a market price or a
player feed. They are published as rows with a blank value, a reason, and what would unblock them.

The way out that this repository uses: because requirement 3 says **originate your own lines**, a
parlay leg can be defined against *our* number instead of a book's. Its outcome is then a pure
function of the official final score, and the dependence between legs becomes officially sourced
after all. That works, and it produced the most useful measurement on the site:

| Card | n | φ | 95% interval | Joint observed | Joint if independent |
|---|---|---|---|---|---|
| Same-game: our side leg vs our total leg | 2,521 | **−0.0551** | [−0.0929, −0.0172] | 0.2463 | 0.2601 |
| Cross-game: the week's two largest side legs | 331 | −0.0145 | [−0.1226, +0.0939] | 0.2447 | 0.2483 |

A same-game card priced at the product of its two legs assumes the last two columns are equal. They
are not: the legs win together 1.38 percentage points less often than independence implies. **The card
is worse for the bettor than its price suggests, and that is now a measured, officially sourced
number with n = 2,521 rather than an assumption.**

---

## What the leaderboard says

Eight strategies, ranked twice: once on signal (flat one unit, nothing else) and once on staking
(same bets, Kelly-sized, capped at 5% of bankroll).

| ID | Strategy | Bets | ROI flat | Signal score | Staking score | Lift | Rank signal | Rank staking |
|---|---|---|---|---|---|---|---|---|
| S1 | Own side vs market spread | 3,831 | −2.91% | −5.96% | −3.20% | −0.26% | 3 | 4 |
| S2 | Own total vs market total | 3,525 | +1.18% | −2.01% | −0.29% | −1.12% | 1 | 2 |
| S3 | Own moneyline vs market price | 4,241 | −3.57% | −7.82% | −2.67% | +0.98% | 4 | 3 |
| S4 | Divisional home underdog | 720 | −4.19% | −11.20% | −9.02% | −4.74% | 5 | 6 |
| S5 | Rest asymmetry, away side | 600 | +3.20% | −4.51% | +7.62% | +4.52% | 2 | 1 |
| S6 | Same-game two-leg parlay | 2,521 | −6.81% | −13.18% | −6.05% | +0.82% | 6 | 5 |
| S7 | Cross-game two-leg parlay | 331 | −6.97% | −24.61% | −12.22% | −5.00% | 7 | 7 |
| S8 | Player-prop combination | — | blocked | blocked | blocked | — | blocked | blocked |

**No strategy has a positive signal score.** S2 and S5 have positive flat ROI, but their 95% lower
bounds are below zero, so neither clears the gate.

**The mask works.** S5 ranks 2nd on signal and 1st on staking; S1 ranks 3rd and 4th. The largest
movement caused by stake sizing alone is one place. On this sample, staking is not yet hiding
anything — but the mechanism that would reveal it if it did is now in place, including a permutation
band on the staking lift computed over 2,000 reshuffles with a fixed seed.

**S8 is blocked on data, not method.** No official publisher prints player-prop prices and no official
player-level log is reachable from this repository. Every value is blank and the schema is published.

---

## Replacement depth

80 starter replacements across 28 clubs, joined from two official captures: the league's own Week 10
injury report and each club's own published depth chart.

| Replacement string | Rows |
|---|---|
| 2nd string | 68 |
| 3rd string | 1 |
| 4th string | 0 |
| No further name published by the club | 11 |

Split 35 offence, 40 defence, 5 special teams. 44 Out/Doubtful, 36 Questionable (reported separately,
so the owner can drop the Questionable set with a filter — that is Q08).

This session extended an earlier session's join in one way: it walks *down* the chart, skipping any
name that is itself on the report as Out or Doubtful, so a club that loses both its starter and its
backup is recorded as reaching the third string rather than the second. There is exactly one such case
in this week's data: **New England, running back, Rhamondre Stevenson (Questionable) → the club's
third-string back.**

Two honest limits: no official publisher states who will start, and 12 of the 31 clubs print the word
*unofficial* on the chart they publish.

---

## Verification actually performed

`origin_lab/check.py` recomputes from the raw inputs rather than trusting its own JSON:

| Check | Result |
|---|---|
| Pages present, two consecutive builds byte-identical | 13 pages, identical |
| Every table row carries a source link | **1,968 rows, 0 unsourced** |
| Blank cells link `flagged.html` with a resolving flag id | 1,423 cells, 0 broken |
| Side/total identity | holds on all 7,239 rows |
| 2026 feed vs the league's own standings | **all 32 clubs, 0 mismatches on PF, PA and W-L-T** |
| Coverage and movement recomputed from the raw CSVs | matches |
| Home-points vs away-points correlation recomputed | r = −0.0313, n = 7,075 |
| Strategy S4 flat ROI recomputed from the origination rows | n = 720, ROI −4.188% |
| CLV, prop figures and capture timestamps | all blank, as required |
| Causality leak probe | legitimate R² 0.136; with the same-game margin added, **1.000** |
| Repository-wide audits | `source_audit.py` PASS (0 gated unsourced rows) · `linkcheck_all.py` 0 broken local links |

The leak probe is worth a line: a causality gate that only asserts "no feature is post-kickoff" is not
a test. Refitting with the game's own margin added drives R² to exactly 1.0 and collapses the other
three coefficients to zero, which is what a working leak detector looks like.

---

## What is waiting on the owner

**14 open questions, 4 of them blocking** (`origin_lab/questions.html`):

- **Q03** What price do we bet at? (blocking — disables CLV, promotion and demotion)
- **Q02** Do third-party market prices count as a correlation input? (blocking — see finding 3)
- **Q01** Do club-published depth charts count as official? (blocking — the depth tables rest on them)
- **Q07** Player props: acquire a feed or retire the market? (blocking)

**12 suggestions, all at *Pending owner decision*** (`origin_lab/suggestions.html`). Nothing has been
implemented on the strength of its own suggestion. The four scored highest on decision value:

- **K01** Capture an opening number for every market we originate — the one thing that unblocks the
  whole promotion-to-demotion chain.
- **K02** Schedule the results feed refresh. The pinned dataset was **two weeks stale** when this
  session started: Weeks 9 and 10 were missing entirely and Week 8 was 1 game of 14.
- **K11** Decide what the origination model is for, then act on it.
- **K08** Add a decision inbox as the site's front page, so an arriving owner sees what is waiting.

**11 flags, none blocking the site** (`origin_lab/flagged.html`). Three are high severity and all three
are data-availability gaps rather than errors: the stale feed (F-A01), the missing opening numbers
(F-A02), and the uncomputable correlations (F-A03).

---

## Scope, and what was deliberately not done

**Files touched:** `origin_lab/**` (new, 13 pages + 10 scripts + data), `.github/workflows/origin-lab.yml`
(new), `ORIGINATION_EXECUTIVE_SUMMARY.md` (new), `COORDINATION.md` (append-only), and one navigation
line in the root `index.html`.

**Not touched:** `verify/source_audit.py::OFFICIAL_HOSTS` — the club-versus-league source-tier question
is the owner's call, so the shared allow-list was left alone and the tier is disclosed on the pages
instead. No file under `data/`, `depth_lab/`, `desk/`, `line_lab/`, `hub/`, `site/`, `verified/`,
`docs/`, `pipeline/`, `audit/`, `verification/`, `qa/`, `reviews/` or `session-*/` was modified. Every
input outside `origin_lab/` was read, never written.

**Not done, on purpose:** no forward own-lines published until Q11 is answered (an own line whose
purpose is undecided invites being read as a tip); no reward amounts (no pool exists and no strategy
is eligible); no CLV figure anywhere (it would be zero by construction and would read as a real
measurement); no prediction of any lineup.
