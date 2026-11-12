# Executive summary — NFL decision system (2026-11-12)

**Live site:** <https://karagemop466-tech.github.io/Korea3/decision_system/index.html>
**Code:** `decision_system/` · **Evidence:** `data/injury_lab/` · **Board:** `COORDINATION.md` (section
`arena/c15a0006-korea3`) · **Session:** `arena/c15a0006-korea3`

---

## 1. Bottom line

1. **No strategy in this repository has demonstrated skill.** All 11 pre-registered strategy
   families were re-audited against seven gates; **0 of 11 pass all seven**. The best raw return
   is **+0.58% ROI over 600 settled selections**, and its bootstrap 95% interval and
   season-block interval both contain zero.
2. **The leaderboard problem is luck, not effort.** Simulating 11 zero-edge strategies with the
   same bet counts produces a *mean best* ROI of **+6.2%** and a profitable "winner" in **99.9%**
   of simulations (95th percentile **+10.1%**). Any ranking that is not multiplicity-corrected
   rewards the luckiest of eleven tries.
3. **An edge is expensive to prove.** Detecting a 3% per-bet edge at 80% power needs **7,953**
   settled bets (two-sided; 6,264 one-sided). That arithmetic, not a modelling preference,
   is why the recommendation is to build a forward record before claiming anything.
4. **Only one same-game dependence is large.** Home-win × home-cover φ = **0.79**; spread × total
   φ = **−0.01** (−0.03…+0.02); cross-game same-week legs φ = **−0.00**. A two-leg −110 parlay
   needs φ ≥ **0.0975** before correlation starts to favour the bettor; the measured
   moneyline/spread dependence is far above that, so those legs must never be priced as
   independent.
5. **The injury report is a pre-game document with no probabilities in it.** The four 2026 statuses
   were transcribed verbatim from the official page; the policy itself attaches no percentage to
   *Questionable* or *Doubtful*. The site therefore measures what a status was *worth* by joining
   it to actual participation, and leaves every unmeasurable value blank.

## 2. What was asked for, and where it is answered

| Brief item | Where it is answered | State |
|---|---|---|
| Suggestions section to review and choose before implementing | `decision_system/suggestions.html` (16 scored proposals, 5 paths) | done |
| Clear list of questions / information / answers before a decision | `decision_system/questions.html` (22 questions: 9 official, 4 dataset, 9 blank) | done |
| Suggestions that discover missing information | 9 blank questions → 8 decision gates → 16 suggestions, each with a pre-implementation gate | done |
| Originate own NFL lines, research signal strategies | `own-lines.html` + the repository's walk-forward model (read-only) | done |
| Leaderboard competition with rewards for top strategies | `leaderboard.html` — 7 skill gates, deflated Sharpe, no-skill band, reward rule | done |
| Single bets, parlays, player-prop combos | `strategies.html`, `parlays.html`, `props.html` | **partial** — no licensed prop price exists, so prop edges/ROIs are blank |
| Validation gates for each strategy | `gates.html` — seven skill gates per strategy, all results published | done |
| Determine correlation values | `correlations.html` — five measured dependencies with 95% CIs | done |
| Remove luck, select skill | `leaderboard.html` / `skill.py` — bootstrap, season-block bootstrap, no-skill band, BH, deflated Sharpe, holdout | done |
| Track injuries | `injuries.html` — live official transcription + measured status→participation | done |
| Know 2nd/3rd/4th string deficiencies, offence and defence | `depth.html`, `availability.html` — snap-rank strings, separate O/D indices | done |
| Executive summary | this file + `executive.html` | done |
| No manual input; finish autonomously | every page is generated; `python3 -m decision_system.build` | done |
| Verify line by line from official sources, with links, no hallucination | `sources.html` — 25 sources with the exact quoted wording | done |
| Review the repo, flag irregularities | `repo-review.html`, `flagged.html` — 12 findings | done |
| Clean GitHub Pages dashboard with category subpages | 22 pages under `decision_system/` | done |
| Every table row official-sourced or blank+flagged | enforced in code: `render.table()` raises without a source; `check.py` V2 | done |
| Read/update coordination board, avoid conflicts | `COORDINATION.md`, claim J01–J09 pushed before work | done |
| PR → merge → Pages confirmed → recorded | see the board section `J09` | done |

## 3. The nine things this project does **not** know

Each is blank on every page and linked to the review page. None was filled by inference.

| Flag | Gap | Why it matters |
|---|---|---|
| DS-F01 | No official numbered depth chart found (NFL.com club depth-chart route returns 404) | every "string" label is derived from snap rank and is labelled unofficial |
| DS-F02 | 48-active / 90-minute inactive mechanics not read at an official source | availability modelling cannot use them yet |
| DS-F03 | Two operator articles render client-side only | same-game-parlay and non-starter settlement cannot be quoted |
| DS-F05 | No licensed player-prop price anywhere | every prop edge, ROI and combo is blank |
| DS-F06 | In-game injuries invisible | pre-game report cannot see a first-drive injury |
| DS-F07 | Club record on the injury page is point-in-time | it is never quoted as a final record |
| DS-F08 | Injury dataset never reconciled with official pages | an unknown transcription error would move every injury number |
| DS-F09 | No funded reward terms | "top performing" is undefined until the owner sets a budget |
| K21 | (same as DS-F09) | the competition cannot pay or promise anything |

## 4. Sources

25 sources are registered in `decision_system/sources.py`; each carries the **verbatim wording**
it supports and the date it was opened. Tier counts: 9 league (NFL.com, NFL Support, NFL Football
Operations), 5 licensed operator (DraftKings, FanDuel), 4 standards body (NIST), 1 peer-reviewed
index (PubMed Central — located but **not read**, so it supports nothing), 6 datasets/repository.

Key pages opened and read this session:

- <https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-policy-for-2016-season> — Out/Doubtful/Questionable definitions, practice codes, removal of *Probable*
- <https://www.nfl.com/injuries/> — live 2026 Week 10 report (transcribed verbatim)
- <https://www.nfl.com/injuries/league/2025/reg9> — 2025 Week 9 report (blank-status example)
- <https://www.nfl.com/legal/terms/> — systematic-retrieval prohibition (data boundary)
- <https://www.nfl.com/teams/kansas-city-chiefs/roster> — roster membership (no depth order)
- <https://support.draftkings.com/dk/en-us/understanding-odds?...KB0010466> — American odds
- <https://support.draftkings.com/dk/en-us/what-is-a-parlay-bet?...KB0010683> — parlay and push rules, correlation restriction
- <https://www.fanduel.com/fanduel-sportsbook-house-rules-ct> — jurisdiction-specific house rules
- <https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm> — confidence limits and t-test
- <https://www.itl.nist.gov/div898/handbook/eda/section3/bootplot.htm> — bootstrap
- <https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm> — multiple comparisons

## 5. Measurements added this session

| Measurement | Value | Denominator | Where |
|---|---|---|---|
| Strategies audited | 11 | 16,439 settled selections | `leaderboard.html` |
| Strategies passing all seven gates | 0 | 11 | `gates.html` |
| Best raw ROI | +0.58% | 600 selections (S6) | `strategies.html` |
| Best-of-11 no-skill ROI (mean / p95) | +6.17% / +10.09% | 20,000 simulations | `leaderboard.html` |
| Bets needed for a 3% edge | 7,953 two-sided / 6,264 one-sided | 80% power | `methodology.html` |
| Home-win × home-cover φ | 0.7877 (0.7644…0.8110) | 7,075 games | `correlations.html` |
| Break-even φ for a 2-leg −110 parlay | 0.09751 | arithmetic | `parlays.html` |
| Current official report rows transcribed | 44 | 4 clubs | `injuries.html` |

### The injury and depth measurements, once computed

The pinned release assets cannot be downloaded from the analysis sandbox, so
`python3 -m decision_system.injury_engine` runs in CI and commits its output back. It has now
run, on **93,827 injury-report rows (2009–2026)** joined to **323,169 snap-count rows
(2013–2026)**, across 7,075 regular-season games.

| Measurement | Result | What it means |
|---|---|---|
| P(plays \| listed **Out**) | 0.05% (6 of 13,304) | the label is almost deterministic |
| P(plays \| listed **Doubtful**) | 0.72% (17 of 2,350) | also close to deterministic |
| P(plays \| listed **Questionable**) | **63.3%** (11,551 of 18,258) | one label covers two-thirds of a coin flip |
| P(plays \| **no** game status) | 90.0% (26,510 of 29,463) | a blank is not a risk signal |
| Offence, 2nd string Out | **−1.59 pts** vs the closing line, raw p = 0.010, **q = 0.080** | does **not** survive the 8-test family |
| Offence, 1st/3rd/4th string Out | +0.05 / −0.01 / −0.59 pts | indistinguishable from zero |
| Defence, any string Out | −0.98 to +0.08 pts | indistinguishable from zero |
| Depletion regression (6,160 team-weeks) | all four coefficients span zero | the market prices the absence |

The single interesting row is the one that does not survive correction. Eight strings were
tested at once, so the chance of at least one raw p below 0.05 is 34% even if nothing is
there; Benjamini–Hochberg puts the 2nd-string result at q = 0.080. It is published as a miss,
with the raw and adjusted values side by side, because reporting only the first number would
be the exact error NIST 7.4.7 describes.

Two bugs were found only because real data was finally run through this code, and both are now
locked by regression tests: the closing line was being *added* to the result instead of
subtracted (producing an average "cover margin" of +55 points), and the depletion index used
the same week's snap counts, which is circular — a player listed Out has no snaps that week, so
the exposure was identically zero for the weeks it was meant to describe. Exposure is now
measured on the previous week's snaps (mean 1.5%, max 29%).

This is recorded as finding DS-F08 (dataset never reconciled against the official pages) and in
the board log.

## 6. Honest non-claims

- **Not betting advice.** No game is predicted, no pick is recommended, no stake is suggested.
- **No prop numbers.** Not one licensed prop price exists in the repository, so not one prop
  edge does either.
- **No official depth chart.** The string labels are a measured proxy and say so on every row.
- **No reward.** No budget exists; the leaderboard publishes *entry rules*, not a prize.
- **No reconciliation of the injury dataset** against the official pages — that is suggestion
  SG02, the highest-value verification task remaining.
- **No claim that any published number beats the market.** The only comparison in the
  repository that reaches significance does so in the market's favour.

## 7. Recommended first decision

**SG05 — pre-register every future strategy in a signed, timestamped file before it is run**
(weighted score 4.75/5). It is cheap, reversible, needs no external data, invalidates no
published result, and it is the precondition for the leaderboard's multiplicity correction to
mean anything. Second: **SG12**, a decision log so that a reviewer's choice is auditable.
