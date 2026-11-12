# Executive summary — 12 November 2026

**Session:** `arena/0b4c7c27-korea3` · **Branch:** `arena/0b4c7c27-korea3` → `main`
**Live dashboard:** <https://karagemop466-tech.github.io/Korea3/hub/index.html>
**This page in HTML:** [`hub/executive-summary.html`](hub/executive-summary.html) ·
**Decision register:** [`hub/decisions.html`](hub/decisions.html) ·
**Suggestions:** [`hub/suggestions.html`](hub/suggestions.html) ·
**Injuries:** [`hub/injuries.html`](hub/injuries.html) ·
**Recomputation:** [`hub/recompute.html`](hub/recompute.html) ·
**Flagged for Review:** [`hub/flagged.html`](hub/flagged.html)

---

## The bottom line in five sentences

1. **The repository's numbers hold up.** Fourteen published figures — break-even prices, the
   spread-by-total correlation, the cross-game independence test, the bet and strategy counts, the
   gate results and the parlay arithmetic — were re-derived in this session with independent
   arithmetic rather than the code that produced them. All fourteen reproduce.
2. **Nothing in the repository has demonstrated an edge.** All 18 tested rules fail their gates. The
   best raw result (+8.41% ROI) carries a q-value of 0.288 and fails multiplicity control, so it is
   indistinguishable from the luckiest of a large family of coin flips.
3. **The injury half of the brief is built on official data; the depth half is only partly possible.**
   254 players were transcribed from the NFL's own Week 10 2026 injury report and re-checked against
   the league's published status vocabulary. Depth order has no *league-wide* official source — the
   official `/depth-charts/` URL returns HTTP 404 — but official **club** sites do publish depth
   charts, and four clubs are verified in the register. So 2nd/3rd/4th string can be verified club by
   club, never assumed league-wide. The other 28 clubs are left blank.
4. **Twenty decisions are still open.** They are listed with what we have, what we lack, the
   provisional position where one exists, and the cheapest way to discover what is missing. Four are
   blocked on evidence that does not exist in this repository; none were closed by guessing.
5. **Twelve suggestions are on the board, each with a decision attached.** The highest-value ones are
   integrity fixes: two builds currently share strategy IDs `S01`–`S18` with different meanings, and
   this session measured a 13-percentage-point error from exactly that collision.

---

## What was asked, and where it now lives

| Requirement from the 12 November brief | Status | Where |
|---|---|---|
| Collect, organise and analyse against a full requirement list | done | `hub/requirements.html` (44 rows, R01–R44) |
| Suggestions to improve decision making | done | `hub/suggestions.html` (12 rows, S01–S12) |
| A dedicated suggestions section to choose a path **before** implementing | done | `hub/suggestions.html`, `suggestions.html`, `suggestions.json` |
| A clear list of questions, information and answers needed before any decision | done | `hub/decisions.html` (20 rows, Q01–Q20) |
| Suggestions to discover missing information | done | the *How to discover it* column on every decision row |
| Originate own NFL lines | built by an earlier session, verified here | `hub/own-lines.html` |
| Strategies for useful signals | built, **0 of 18 pass** | `hub/strategies.html` |
| Leaderboard competition with rewards for top strategies | specified, **no funded pool** | `hub/leaderboard.html`, decision Q18 |
| Single bets, parlays, player-prop combos | done | `hub/single-bets.html`, `hub/parlays.html`, `hub/player-props.html` |
| Each strategy must pass validation gates | done, fail-closed | `hub/validation.html` |
| Determine correlation values | measured | `hub/correlations.html` |
| Remove luck from the equation; selectively skill-based | done as uncertainty control | `hub/validation.html`, recomputation C02–C11 |
| Track injuries | **done, official snapshot** | `hub/injuries.html` |
| Know 2nd/3rd/4th-string deficiencies | **partial: 4 of 32 clubs verified from official club charts** | `hub/injuries.html`, flags F11/F12/X03 |
| Same for offence using starters or backups | **partial: same limit** | flag X03, question Q02/Q07 |
| Executive summary | this document | `hub/executive-summary.html` |
| No manual input; finish autonomously | done | board record in `COORDINATION.md` |
| Verify line by line from official sources; no hallucination | done | `hub/verification.html`, `hub/recompute.html` |
| Flag irregularities | done | `hub/flagged.html` (44 items, X01–X10 new) |

---

## The numbers, and what each one rests on

| Figure | Value | How it was checked | What it does **not** prove |
|---|---|---|---|
| Break-even win rate at −110 | 52.38% | 110/210, from the operator's own price definition | anything about a strategy |
| Break-even correlation, 2 legs at −110 | φ ≥ 0.0975 | closed-form on the posted price | that any pair reaches it |
| Break-even correlation, 3 legs at −110 | φ ≥ 0.0749 | closed-form on the posted price | same |
| Spread × total correlation, same game | **+0.0086** (95% CI −0.0162 … +0.0332) | hand-computed Pearson φ over 6,784 settled games | official prices — the data is third-party |
| Cross-game correlation | −0.0239, p = 0.102 | recomputed from 28 season values | that cross-game legs are independent for *all* markets |
| Settled bets in the ledger | 16,439 | row count of `data/derived/bets.csv` | profitability |
| Strategies clearing every gate | **0 of 18** | verdict column re-read gate by gate | — |
| Players on the official injury report | 254 | transcribed, then re-checked against official vocabulary | that the list is final — it is a mid-week report |
| Clubs with a verified official depth chart | **4 of 32** | the league-wide URL 404s; club sites publish charts | — |

The gap between **0.0086** and **0.0975** is the whole parlay question, and it is an order of
magnitude wide. That conclusion does not depend on the exact value of either number.

---

## What is missing, stated plainly

| Missing | Why it matters | Can it be fixed? |
|---|---|---|
| Depth charts for the other 28 clubs | the 2nd/3rd/4th-string request is only answered for 4 clubs | yes — walk all 32 official club sites once (suggestion S03) |
| Official snap counts (who actually played) | proves a backup replaced a starter | official endpoints returned 404 |
| Historical injury archive aligned to games | without it the injury hypothesis cannot be backtested at all | yes, but it must be pre-registered first (suggestion S04) |
| Licensed official price archive | every ROI and correlation rests on third-party prices | yes, at cost |
| A prop-line archive | player-prop combinations are documented, not measured | yes, at cost |
| A funded reward pool and terms | the competition currently has no funded prize | an owner decision (Q18, S06) |
| A stated use, stake and jurisdiction | changes the pass/fail bar entirely | an owner decision (Q01, Q02) |

---

## Irregularities found in this session

Ten new items (X01–X10) were added to the review register, which now holds 44. The ones that matter:

- **X01 (high)** — `data/derived/bets.csv` and `data/derived/gates_results.csv` both use strategy IDs
  `S01`–`S18` for **different rules**. Joining them silently mixes 11 strategies with 18. Scoring one
  rule from the wrong ledger produced −0.0873 instead of +0.0430.
- **X02 (medium)** — `corr_same_game.csv` is labelled 2006–2025 but its published n = 6,784 is the
  all-season count. Over the documented window the same computation gives n = 4,996, φ = +0.0163.
  Both values are far below the 0.0975 requirement, so the conclusion stands; the label is wrong.
- **X03 (medium, partly resolved)** — no *league-wide* official depth chart exists (the URL 404s),
  but official club depth charts do, and four are verified. 28 clubs remain unverified.
- **X04, X05** — the official injury page is a rolling mid-week report rather than a final inactive
  list, and four clubs are absent from it; the official schedule confirms all four are on bye, so
  X05 is resolved.
- **X06, X07 (medium/low)** — a third-party injury/depth dataset exists but could not be downloaded
  or checksummed here, and official snap-count pages returned 404. No value from either is used.

None of these blocked publication. All are published with their source links for review.

---

## Where the previous work stands

The repository holds six generations of dashboards from earlier sessions. This session added to the
consolidated one rather than replacing anything, and did not edit another session's files. The
practical position is unchanged from 2026-11-02 and should be said without decoration:

> **No strategy in this repository has demonstrated skill at the required significance level.** The
> own-line model was less accurate than the closing line. The most popular same-game combination is
> an order of magnitude below the correlation needed to price a parlay fairly. The honest output of
> this project so far is a rigorous way of saying *not yet*, plus a clear list of what to settle and
> what to build next.

---

## Sources used in this session

Every row on every page carries a link to the publisher that supports it. The sources opened and read
on 2026-11-12 are:

- Injury report, official week 10 2026: <https://www.nfl.com/injuries/league/2026/reg10>
- Injury report, official week 10 2025 (proves the URL format is durable): <https://www.nfl.com/injuries/league/2025/reg10>
- Injury policy, official: <https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693>
- Official reserves and trades, November 2026: <https://www.nfl.com/transactions/league/reserve-list/2026/11> · <https://www.nfl.com/transactions/league/trades/2026/11>
- Official roster format: <https://www.nfl.com/teams/buffalo-bills/roster>
- Official week 10 2026 schedule: <https://www.nfl.com/schedules/2026/REG/10/>
- Official terms of use (the rights boundary for any data copying): <https://www.nfl.com/legal/terms/>
- Operator settlement rules: <https://sportsbook.draftkings.com/help/general-betting-rules/market-rules> · <https://www.fanduel.com/fanduel-sportsbook-house-rules-ct>
- Statistical method: <https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm> (multiplicity) · <https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm> (intervals)
- Documented failures, recorded as evidence: <https://www.nfl.com/depth-charts/> (HTTP 404) · <https://nextgenstats.nfl.com/stats/snap-counts/2025/REG/10> (HTTP 404)
- Official club depth chart, verified this session: <https://www.commanders.com/team/depth-chart>

## A note on parallel work

Another session working the same brief at the same time published its own decision register
(`hub/questions.html`, 18 questions) and suggestions board (`hub/suggestions.html`), and its
32-club injury page (`hub/injuries.html`). Those pages are kept as the canonical ones for this
repository; this session's contribution is the pages that did not exist — an independent
**recomputation log** (`hub/recompute.html`) and this summary — plus ten new review flags. Its own
draft register and suggestions board are preserved in `decisions.json`, `suggestions.json` and
`suggestions.html` for review rather than merged over the other session's work. When the two
sessions disagreed, the official page was opened again and the other session's finding was adopted
where it was right: see X03.

---

## How to check this yourself

```bash
python3 hub/data_injuries.py     # re-checks all 254 transcribed rows against the official vocabulary
python3 hub/verify_numbers.py    # re-derives all 14 published numbers; exits non-zero on any drift
python3 hub/build_hub.py         # builds 24 pages, deterministically, with no network access
python3 hub/check_hub.py         # fails if any table row lacks an official link, or any link breaks
```

---

**Disclaimer.** Research and engineering sample. **Nothing here is betting advice.** No strategy in
this repository has demonstrated skill at the required significance level. This project is not
affiliated with the NFL or any sportsbook. NFL.com content is cited and linked, not redistributed;
the one small transcription exists to verify a specific published claim and is timestamped.
