# Addendum — competition, rewards and luck (2026-11-12)

**Session:** `arena/96b33d36-korea3` · **Branch:** `arena/96b33d36-korea3` → `main`
**Base commit:** `9a3fc041` (PR #57) · **Merged main:** `e281a63` (PRs #59, #61)
**Dashboard:** <https://karagemop466-tech.github.io/Korea3/hub/index.html>
**New page:** [Competition, rewards & luck](https://karagemop466-tech.github.io/Korea3/hub/competition.html)
**Main summary for this brief:** [`EXECUTIVE_SUMMARY_2026-11-12.md`](EXECUTIVE_SUMMARY_2026-11-12.md)

> Independent research. **Not betting advice.** No prize is funded, offered or implied. A blank cell means
> **unverified**, never zero.

---

## 1. Why this addendum exists, and what happened to the concurrent work

Two sessions worked the same 2026-11-12 brief. Session `arena/6cbe5d15-korea3` claimed first on the
shared board and merged its injury, suggestions and questions pages (PRs #59 and #61). This session
started from base commit `9a3fc041`, when that claim was not yet visible on `origin/main`, and built its
own drafts of the same three pages.

On discovering the concurrent claim, this branch **merged `origin/main`** rather than rebasing over it:

- The other session's pages, sources, flags, summaries and board sections are **preserved byte-identical**.
  The dashboard is rebuilt only from **its** generator.
- This session's duplicate drafts of `suggestions.html`, `questions.html` and `injuries.html` were
  **withdrawn**, not published over theirs.
- The only merge conflict was the append-only `COORDINATION.md`; both claims and results are kept in full,
  and no conflict marker remains.
- What this session adds is what did not exist on `main`: **one competition page**, an **arithmetic
  verifier**, a **CI step**, the root banner link and this addendum. It also re-opened 14 official sources
  used by the page set and recorded a 2026-11-12 check date on them.

## 2. What the new page decides

The page turns "pay the best strategy" into a testable rule instead of a leaderboard of returns.

| Element | Rule | Why it exists |
|---|---|---|
| Entry | One fully specified strategy: market, selection rule, stake, settlement source, hashed before the window | Stops rules changing after results |
| Evaluation | A locked, untouched holdout; one unblinding | Stops tuning on the test |
| Ranking | Lower confidence bound on closing-line value, then calibration, then stability | Stops variance being paid as skill |
| Multiplicity | The whole strategy family counts in false-discovery control | Stops "best of 100" being called a winner |
| Sample | A pre-registered minimum number of settled bets | Stops a 30-bet streak |
| Reward | Paid only after all ten gates; no amount published | No funded pool or legal review exists |

**Ten promotion gates:** registration before the window, every tested rule published, family size
declared, minimum sample, calibration, positive lower bound, multiplicity control, two-snapshot
stability, untouched holdout, and an operational audit of prices, timestamps and settlement.

## 3. Sample-size arithmetic (recomputed on every build)

Break-even at −110 is **110 ÷ 210 = 52.381%**. With a one-sided 5% test and 80% power, using the NIST
formula N = (z(1−α)√(p₀(1−p₀)) + z(1−β)√(p₁(1−p₁)))² ÷ (p₁−p₀)²:

| True win rate | Edge vs break-even | Settled bets needed | Seasons at one bet per game |
|---|---|---|---|
| 52.5% | +0.12 pp | 1,088,044 | 4,000.2 |
| 53.0% | +0.62 pp | 40,223 | 147.9 |
| 54.0% | +1.62 pp | 5,875 | 21.6 |
| 55.0% | +2.62 pp | 2,242 | 8.2 |
| 56.0% | +3.62 pp | 1,173 | 4.3 |
| 58.0% | +5.62 pp | 485 | 1.8 |
| 60.0% | +7.62 pp | 262 | 1.0 |

`hub/check_decisions.py` parses the published table, recomputes all seven rows, and fails if any differs by
more than one bet. A SciPy cross-check gives 2,242.30 bets at 55%, 40,223.30 at 53% and 262.23 at 60%.

The page also states the parlay identity precisely: two true coin-flip legs at −110 need a phi coefficient
of at least **0.097506** just to break even. This is arithmetic under a stated assumption, not a finding
about any game. The exploratory measurement of spread × total dependence is **+0.0086** (95% CI −0.0162 to
+0.0332, n = 6,784) on the pinned third-party dataset; it is labelled exploratory, not official.

## 4. Official sources and dates

**New source opened for this page:** [NIST/SEMATECH 7.2.2.2, Sample sizes required](https://www.itl.nist.gov/div898/handbook/prc/section2/prc222.htm)
— read on 2026-11-12; it states that the calculation depends on α, β and σ, and gives the two-sided and
one-sided formulas.

**Re-opened and matched on 2026-11-12:** NFL Terms; NFL Support money-line and stats pages; DraftKings
odds, parlay and player-settlement pages; FanDuel House Rules CT §19; the NFL responsible-betting article;
the NFL schedule page; and NIST confidence-limit, multiple-comparison, Bonferroni, bootstrap and
correlation pages. Two DraftKings help pages (SGP, prop) returned only a loading placeholder on retry;
they are **not** relied on by the new page, and their earlier check date stands.

The register now holds **35 sources**, of which **22 carry a 2026-11-12 check date**. Every table row on
every dashboard page links to its official source or to the repository artifact that computes it.

## 5. Verification performed

| Check | Result |
|---|---|
| `python3 hub/build_hub.py` | built **24 pages; 35 sources; 43 flags** |
| `python3 hub/check_hub.py` | **PASS** — 24 pages, 1,024 table rows, 1,498 official row links, 1,046 blank markers, 1,835 internal links, 1,522 external links |
| `python3 hub/check_decisions.py` | **PASS** — 1 page, 7 sample-size rows recomputed, formula source date-checked |
| `python3 line_lab/check_site.py` | **OK** — 16 pages, every row sourced, hashes and recomputed numbers match |
| `python3 scripts/verify_site.py` | **11/11 checks passed** — 7,075 games reconciled |
| `python3 pipeline/link_check.py` | **PASS** — 13 pages, 0 broken links |
| `python3 -m nfl_lab.check_verified` | **OK** — 12 pages, 146 rows, one unverified source (`nws_metrics`) |
| `python3 -m pytest tests/test_lab_*.py tests/test_evidence_hardening.py -q` | **34 passed** |
| `git diff --exit-code -- hub` after rebuild | clean |

## 6. Flags and boundaries

- **N15 (new, high):** the reward structure is unfunded and no contest rules, jurisdiction, eligibility,
  tax treatment or dispute process has been reviewed. Every award cell is blank; no entry is open.
- **N05 / N06 (existing, high):** no licensed event-level dataset or timestamped quote archive; no funded
  reward pool. Both block every empirical and reward claim.
- The other session's flags F10–F17 remain as published, including F17 (the injury transcription sitting
  close to the NFL Terms boundary) and F16 (suggestions awaiting a decision).
- No file under `audit/**`, `docs/**`, `reports/**`, `pipeline/**`, `scripts/**`, `data/**`, `line_lab/**`,
  `nfl_lab/**`, `verified/**`, `site/**`, `qa/**`, `reviews/**`, `verification/**` or `session-*/**` was
  edited by this session.

## 7. Publication record

**Pull request, merge and Pages deployment:** recorded in `COORDINATION.md` (D05) after the merge, with the
live-page checks. Nothing in this addendum is a claim that a strategy is profitable, skilful or eligible
for a prize.
