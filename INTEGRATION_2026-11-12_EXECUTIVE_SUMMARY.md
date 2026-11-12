# Executive summary — 2026-11-12 integration, decision support and availability design

**Session:** `arena/96b33d36-korea3` · **Branch:** `arena/96b33d36-korea3` → `main` · **Base commit:** `9a3fc041` (PR #57)
**Live dashboard:** <https://karagemop466-tech.github.io/Korea3/hub/index.html> · **Review register:** <https://karagemop466-tech.github.io/Korea3/hub/flagged.html>
**Repository:** <https://github.com/karagemop466-tech/Korea3>

> Independent research. **Not betting advice.** No strategy in this repository has demonstrated skill at a
> pre-registered significance level. No prize is funded, offered or implied. A blank cell means
> **unverified**, never zero.

---

## 1. Bottom line

1. **The site now supports a decision instead of only reporting research.** Four new pages publish
   22 suggestions with scores and prerequisites, 12 questions answered from official sources,
   26 blocking questions with a concrete route to each answer, and three funding paths. The
   recommendation is **Path B — a small licensed data pilot**; no path is approved by publishing it.
2. **Injuries and depth-chart deficiencies are specified, not fabricated.** Ten official rules are
   quoted and verified. **Zero** player-level injury, inactive, depth-order or 2nd/3rd/4th-string
   values are published, because no licensed feed or dated depth-order archive exists. The page
   states this on its face (flags B02, B07, B09, N14, N16).
3. **The competition is designed to pay for skill only after luck is bounded.** Ten promotion gates,
   a locked holdout, false-discovery control, calibration, a lower confidence bound and closing-line
   value. Sample-size arithmetic shows why: a true 55% win rate needs about **2,242 settled bets**
   (≈8.2 seasons at one bet per game) to be distinguished from the 52.381% break-even at −110 with
   80% power. No entry is eligible and no prize amount is published.

---

## 2. What was added

| Page | Purpose | Key content | Honest boundary |
|---|---|---|---|
| [Suggestions & decision paths](https://karagemop466-tech.github.io/Korea3/hub/suggestions.html) | Choose a path before implementing | 22 suggestions scored 1–5 on impact/confidence/effort, a six-stage decision ladder, nine site upgrades, five "do not do yet" rules, three funding paths, a recommended order | Scores are **owner-judgment proposals**, not measurements |
| [Questions & missing information](https://karagemop466-tech.github.io/Korea3/hub/questions.html) | Know whether a decision is ready | 12 answers quotable from official pages; 26 open questions with what we know, what is missing, how to answer, what it blocks; an information inventory; eight discovery methods; a readiness summary | Open means unanswered, not unanswerable |
| [Injuries & depth chart](https://karagemop466-tech.github.io/Korea3/hub/injuries.html) | Track availability honestly | 10 verified roster/injury rules, a five-layer data status table, a Deficiency Index specification, eight availability gates, six claim boundaries, five acquisition options, direct official links | **No player-level values.** Weights, counts and returns are blank |
| [Competition, rewards & luck](https://karagemop466-tech.github.io/Korea3/hub/competition.html) | Reward skill, not variance | Ten promotion gates, eight anti-luck mechanisms, a seven-row sample-size table, a proposed unfunded reward schedule, anti-gaming rules, a five-step launch path | **No funded pool, no open entries, no amounts** (flag N15) |

Supporting changes: seven new official sources (34 in the register), seven new flags (41 total),
eight new requirement rows (43 total), a `<code>hub/check_decisions.py</code>` fail-closed verifier,
a CI step for it, refreshed repository review snapshot, and an additive root-page banner.

---

## 3. Official facts verified on 2026-11-12 (with links)

Every statement below was read on the publisher's own page in this session.

| Fact | Exact statement | Official source |
|---|---|---|
| NFL content may not be compiled | "Systematic retrieval of data or other content from the Services, whether to create or compile, directly or indirectly, a collection, compilation, database, or directory, is prohibited absent our express prior written consent." | [NFL Terms §1.3](https://www.nfl.com/legal/terms/) |
| Game status labels | "Questionable means it is uncertain as to whether the player will play in the game; Doubtful means it is unlikely the player will participate; and Out means the player will not play." | [NFL Injury Report Policy revision](https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693) |
| Practice labels | "Did Not Participate, Limited Participation (defined as less than 100 percent of a player's normal repetitions) or Full Participation (defined as 100 percent of a player's normal repetitions)." | [Same official revision](https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693) |
| Official injury report exists | Page title on 2026-11-12: "Official Latest NFL Injury Report for Players - Week 10 of the 2026 Season"; per-club tables with Player, Position, Injuries, Practice Status, Game Status | [NFL injury report](https://www.nfl.com/injuries/) |
| Injured reserve | No limit on placements; "up to eight players to return"; a player may be designated twice; "at least four games prior to returning to the active roster" | [NFL roster FAQ](https://www.nfl.com/news/nfl-training-camp-roster-faqs-defining-injured-reserve-pup-list-nfi-and-more) |
| PUP and NFI | Reserve/PUP players "must miss at least the team's first four games"; NFI players can be activated after the first four regular-season games | [Same roster FAQ](https://www.nfl.com/news/nfl-training-camp-roster-faqs-defining-injured-reserve-pup-list-nfi-and-more) |
| Roster sizes | 53 active/inactive; 48 game-day with at least eight offensive linemen, otherwise 47; 54/55 only via elevation | [NFL Football Operations contract language](https://operations.nfl.com/calendar-events/nfl-free-agency/contract-language) |
| Practice squad | 16 in 2026, 17 with an International Pathway player; at most three regular-season elevations per player per League Year | [Same Football Operations page](https://operations.nfl.com/calendar-events/nfl-free-agency/contract-language) |
| 2025 designated-to-return bylaw | Two designations at the cut to 53; the eight-transaction limit applies only to the regular season, with two extra in the postseason | [2025 Rules Changes](https://operations.nfl.com/rules-officiating/featured-rules) |
| Roster status codes lack a legend | Official club roster lists number, position, status code (ACT, DEV, CUT, PUP observed), height, weight, experience, college; no definition on the page | [Official 2026 Broncos roster](https://www.nfl.com/teams/denver-broncos/roster) |
| Sample size formula | N = (z(1−α/2)+z(1−β))²(σ/δ)² (two-sided) or with z(1−α) (one-sided); inputs α, β and σ must be assumed | [NIST/SEMATECH 7.2.2.2](https://www.itl.nist.gov/div898/handbook/prc/section2/prc222.htm) |
| Standard price | "Most often, the betting odds for point spread are -110." | [NFL Support](https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line) |
| −110 payout | "in order to 'win' (profit) $100, you would need to wager $110" (article v4.0, 2026-10-06) | [DraftKings Understanding Odds](https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466) |
| Correlated legs | "Parlays containing selections where the outcome of one selection directly affects the outcome or pricing of another selection are not permitted, unless explicitly offered ... as a Same Game Parlay" | [FanDuel House Rules CT §19](https://www.fanduel.com/fanduel-sportsbook-house-rules-ct) |
| Parlay settlement | "All added bets must win"; a push "is removed from the parlay and the odds are recalculated accordingly" | [DraftKings parlay article](https://support.draftkings.com/dk/en-us/what-is-a-parlay-bet?id=kb_article_view&sysparm_article=KB0010683) |
| Multiplicity | Doing pairwise comparisons repeatedly means "the overall significance level is not as specified"; contrasts should be determined in advance | [NIST 7.4.7](https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm) |
| Bonferroni | Maintains an overall confidence coefficient across a finite set of comparisons; valid for equal and unequal sample sizes | [NIST 7.4.7.3](https://www.itl.nist.gov/div898/handbook/prc/section4/prc473.htm) |
| Confidence intervals | A 95% interval does not mean a 95% probability that the interval contains the true mean; the level is a property of the method | [NIST 1.3.5.2](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm) |
| Bootstrap | Estimates uncertainty by resampling with replacement, typically 500–1,000 subsamples; "not appropriate for all distributions and statistics" | [NIST 1.3.3.4](https://www.itl.nist.gov/div898/handbook/eda/section3/bootplot.htm) |
| Correlation | Measures the linear relationship; a perfect linear relationship gives +1/−1 and no linear relationship gives 0 | [NIST Dataplot CORRELATION](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/correlat.htm) |
| Schedule size | "Each NFL team plays 17 games over the 18-week season. The league uses a formula to determine all 272 matchups." | [NFL Football Operations](https://operations.nfl.com/calendar-events/nfl-schedule/making-the-schedule) |

The full register, including the exact quote and the check date for every source, is at
[hub/sources.html](https://karagemop466-tech.github.io/Korea3/hub/sources.html).

---

## 4. Arithmetic recomputed independently

| Quantity | Value | Method | Cross-check |
|---|---|---|---|
| Break-even win rate at −110 | **52.381%** | 110 ÷ 210 | DraftKings payout statement |
| Two-leg parlay decimal at −110 | **3.644628** | (1 + 100/110)² | DraftKings −110 statement |
| Break-even joint probability | **27.4376%** | 1 ÷ 3.644628 | Arithmetic |
| φ needed with two independent 50% legs | **0.097506** | (0.274376 − 0.25) ÷ 0.25 | Published as 0.0975 |
| Bets to detect 55% vs 52.381% | **2,242** | NIST formula, α=0.05 one-sided, power=0.80 | Re-run with SciPy `norm.ppf`: 2,242.30 |
| Bets to detect 53% | **40,223** | Same | SciPy: 40,223.30 |
| Bets to detect 60% | **262** | Same | SciPy: 262.23 |

`hub/check_decisions.py` recomputes the seven published rows from the formula on every build and fails
if any row differs by more than one bet. These are arithmetic under stated assumptions; they are not a
forecast that any strategy has such an edge.

---

## 5. Injuries and depth-chart deficiencies — what is and is not known

**Verified.** The league publishes a weekly injury report; practice participation and game status are
separate fields; IR guarantees at least four games; each club has eight designated-to-return slots;
the active roster is 53 and the game-day list 47 or 48; the practice squad is 16 or 17.

**Not known from an official source opened here.** Who is the 2nd, 3rd or 4th player at a position on a
given date; how many games a specific injury will cost; how much worse a backup performs; which
practice-squad player will be elevated; and how the market has already repriced any of it.

**Why nothing is filled in.** The official injury page has no machine-readable export, revision
timestamp or licence statement, and the Terms prohibit systematic compilation. Official roster pages
show a current status code without a legend. Publishing a player list, a "2nd-string" label or a
games-missed estimate would therefore be fabrication.

**Design that would fix it.** A licensed feed with timestamped practice, game status, inactives,
depth order and snap share; a pre-registered Deficiency Index with declared position weights; and
eight validation gates (completeness, causality, provenance, revision handling, sample size,
stability, multiplicity, holdout). All weights and values remain blank until an owner signs the protocol.

---

## 6. Suggestions and the recommended path

Five that should come first on readiness and leverage (the judgment score is a reading aid, not evidence):

| Rank | Suggestion | Why it comes first | Status |
|---|---|---|---|
| 1 | Freeze a data-rights register (S03) | Prevents spending on data that cannot be used | Ready now |
| 2 | Require a minimum sample before ranking (S09) | Stops a 30-bet hot streak from becoming a "winner" | Ready now |
| 3 | Control FDR across the family (S10) | Makes the number of tested rules part of the cost | Ready now |
| 4 | Hash-lock an untouched holdout (S12) | Converts an in-sample fit into a test | Ready now |
| 5 | Pre-register the competition (S07) | Defines promotion before results exist | Ready now |

**Three paths.** A (research only) is the safe default. **B (licensed pilot)** is recommended: one
season of licensed data, a frozen protocol, a locked holdout, and no public entries. C (full
competition) adds a funded pool and legal review and should only follow a B that passes. Costs are
blank because no vendor quote exists.

---

## 7. Verification performed

All commands were run in this checkout on 2026-11-12 (UTC).

| Check | Result |
|---|---|
| `python3 hub/build_hub.py` | built 24 pages; 34 sources; 41 flags |
| `python3 hub/check_hub.py` | **PASS** — 24 pages, 979 table rows, 1,398 official row links, 1,048 blank markers, 1,837 internal links, 1,422 external links |
| `python3 hub/check_decisions.py` | **PASS** — 4 pages, 7 sample-size rows recomputed, 7 new sources date-checked |
| `python3 line_lab/check_site.py` | **OK** — 16 pages, 47 GitHub source links, all internal links resolve |
| `python3 scripts/verify_site.py` | **11/11 checks passed** — 7,075 games reconciled, 450 sourced rows |
| `python3 pipeline/link_check.py` | **PASS** — 13 pages, 0 broken internal links |
| `python3 -m nfl_lab.check_verified` | **OK** — 12 pages, 146 rows, one unverified source (`nws_metrics`) |
| `python3 -m pytest tests/test_lab_*.py -q` | **24 passed** |
| Deterministic rebuild | `git diff --exit-code -- hub` clean after rebuild |
| Source re-openings | 21 sources now carry a 2026-11-12 check date; 10 keep 2026-11-02 |

Repository review: the frozen snapshot was refreshed so the row-by-row table audit includes all
current pages; each row links to the file or official publisher it describes.

---

## 8. Irregularities and flags (published, non-blocking)

| ID | Severity | Item | Status |
|---|---|---|---|
| N01 | High | NFL Terms restrict systematic retrieval and compilation | Rights boundary; site links, does not compile |
| B02 | High | No injury or inactive data | Design only; no values |
| B07 | High | No licensed injury, inactive or depth-chart feed | New this session; blocking |
| B08 | High | No timestamped executable quote archive | Blocks CLV and ROI |
| B09 | Medium | No historical depth-chart order archive | New this session |
| N14 | Medium | Roster status codes published without a legend | New this session; not interpreted |
| N15 | High | No legal or contest review for a rewards competition | New this session; no entries |
| N16 | Medium | Injury report has no visible update timestamp or export | New this session |
| N17 | Medium | Two DraftKings help pages returned a loading placeholder on retry | New this session; prior check date retained, no new page relies on them |
| F08 | Medium | Two NFL Support article bodies are swapped relative to their titles | Re-confirmed on 2026-11-12 |
| N05/N06 | High | No licensed official event data; no funded reward pool | Unchanged; blocking for empirical/reward claims |

The full register with a source link on every row is at
[hub/flagged.html](https://karagemop466-tech.github.io/Korea3/hub/flagged.html).

---

## 9. Coordination and publication

The claim was written to `COORDINATION.md` and pushed before implementation. No other session had an
active claim; every earlier scope was preserved byte-identical. The brief asks for a
`session-<id>/<task>` branch, but Arena fixes this session to `arena/96b33d36-korea3`; the deviation
is logged on the board rather than hidden.

**Pull request:** recorded in `COORDINATION.md` after merge (D08). **Merge and Pages result:** also
recorded there, with the deployment run and the live-page checks.

---

## 10. What is not claimed

- No claim that any strategy is profitable, skilful or reward-eligible.
- No claim that the proposed Deficiency Index predicts anything; it is an untested specification.
- No claim that a 2nd-string player is worse by any particular number.
- No claim about injury recovery time, game-day availability beyond the official status, or a team's
  depth order.
- No prize, entry, payment or contest is offered. Publication of a proposal is not authorisation.
- No official endorsement by the NFL, DraftKings, FanDuel, NIST or any cited publisher.
