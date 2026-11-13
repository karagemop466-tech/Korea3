# Executive summary — 2026-11-13, injury and depth layer (`injury_lab/`)

Session `arena/7acec358-korea3`. Read this first if you have five minutes; the site is
[`injury_lab/index.html`](injury_lab/index.html) and lives at
<https://karagemop466-tech.github.io/Korea3/injury_lab/>.

Two sentences on what happened. The repository had spent eleven sessions concluding that the injury and
depth part of this brief **could not be done from official sources**. It can, partly, and the part that
cannot be done cannot for a different and more interesting reason than the one on the books: not because the
data is missing, but because there is not enough of it to satisfy the repository's own gates without
hundreds of page reads. That number is now measured, so it is a decision rather than an excuse.

---

## 1. What was asked for, and what exists now

| The ask | Before today | Now |
|---|---|---|
| Track injuries against lines | `README.md` §Limitations: “No injury data.” `decision_lab/data/injuries.json`: 254 transcribed rows, no capture, no join, no rule | 3 dated, hashed captures of the official weekly report; **139 player rows** parsed deterministically; 9 fixtures joined to the pinned market data |
| Track 2nd/3rd/4th-string backups | Recorded as *not satisfiable* (flag D14, question Q04) | **Refuted for the current season**: 3 club charts with ordered strings captured; **17 absence-to-replacement rows** published with both sources on every row |
| Originate lines, compete, reward | 18 pipeline rules and 11 dashboard strategies, 0 eligible for reward | 9 further pre-registered injury rules, **0 promotable**, no reward amounts published anywhere |
| Remove luck / measure skill | Gates G1–G8 in two registers with different contents | Same gates cited by file, one prefixed register (IG1–IG9), stricter value used where the two disagree |
| Suggestions a human picks from | Three boards with disjoint numbering | A fourth register, `injury_lab/decisions.html`: **6 decisions, 20 options, 0 implemented** |
| Register of questions and answers | Q01–Q18 in `decision_lab` | **Q19–Q25** with known / unknown / what-it-blocks / how-to-find-out / who-can-answer, cross-linked to the decisions |
| Repo review, line by line, official links | Narrative flags in COORDINATION | Cross-capture audit of the repository's only prior injury table, plus a computed index of 11 surfaces, 18 registers and every id collision |
| Flag irregularities | ~50 flags across registers | **30 new flags** (H01–H30) in this lab, each with severity, evidence and what would close it |
| Live Pages site, tables with analysis | 4 surfaces, no injury surface | 13 pages under `/injury_lab/`, added to the shared navigation |
| No broken links, no merged broken site | — | Every gate that can run in this sandbox passes; see §8 |

## 2. Three standing conclusions are now wrong, and the board should say so

1. **“The official injury report is a current-week snapshot only.”** Not true.
   `https://www.nfl.com/injuries/league/{season}/reg{week}` is week-addressable and returns a complete
   historical report — 2015 W10 and 2025 W1 were both read in full during this session. This falsifies the
   rationale behind D13/Q12 and backlog item **B02** ("weekly PDFs only, no API").
2. **“The 2nd/3rd/4th-string requirement is not satisfiable from official sources.”** Not true for a
   current season: `detroitlions.com`, `patriots.com` and `dallascowboys.com` each publish an ordered chart
   on the club's own domain. It remains true **for historical seasons**, where no such archive was found.
   D14 and Q04 should be amended to that narrower sentence, which is still a blocker and is now a precise one.
3. **“Depth charts are a usable league-wide feature.”** Also not true, in the other direction. Three charts
   are three kinds of object: Detroit's is compiled by its football communications staff; New England's
   states on the page that it is written by site staff and does not reflect the organization; Dallas's prints
   no statement at all. Column counts differ (5 / 4 / mostly 2). A feature that reads these as one source is
   wrong by construction — which is why this lab publishes a **tiered coverage matrix** instead of
   “available”.

Amending the decision pack's rows is the register owner's call, not this session's: the entries exist here,
and the merge request is logged in `COORDINATION.md`.

## 3. What the injury data actually supports today

| Measure | Value |
|---|---|
| Captured weekly reports | 3 (2015 W10, 2025 W1, 2026 W10), each hashed and retained verbatim |
| Player rows | **139**, every one published with the page, the capture and the capture date |
| Rows placed in a unit by a captured page | 116; **23 blank** because no captured page defines the code (DE, T, G …) — flag H30 |
| Rows with a designation | Out 23, Questionable 25, Doubtful 3, Probable 27 (the last two appear only in 2015), and **61 blank** because no designation had been published when the page was read |
| Fixtures joined to the pinned market file | **9 of 10 captured** matched on date + both club codes; the 10th is published as not attempted, because only one club was in its capture |
| Absence → replacement rows | **17**, each with ≥3 shared players proving chart attribution |
| Refusals, published not hidden | 16 joins refused (mostly: no same-season chart exists for that club) |
| Ambiguities preserved | 3 chart cells with two names in one string; 5 designations with no slot on the chart |

## 4. Why nothing is promoted, in one table

Six completed fixtures in the pinned dataset match a retained official capture. The published sample gate is
300 settled bets across ≥8 seasons with 40 holdout bets (`docs/preregistration.md`, `scripts/gates.py`).

| Rule | Fires in the captured set | Weeks of capture IG3 would need |
|---|---|---|
| F05 designation-count (deliberate **negative control**) | 6 of 6 | 22 |
| F03 two first-string defenders out | 2 of 6 | 65 |
| F02 charted first-string QB out | 1 of 6 | 129 |

Every row on the signals page hard-codes `reward_eligible: false` and `IG3: FAIL`.

The control is the finding. **F05 — a rule written to contain no information — “wins” 5 of 6 bets and shows
+0.625 units per bet at the recorded closing prices.** Meanwhile F02, the rule with an actual hypothesis
behind it, shows +0.909 on a single bet, and F03 shows −1.000 on two. Anyone quoting any of those numbers as
evidence is quoting noise. That single paragraph is the strongest argument in this repository for why the
gates exist, and it is published on the site rather than kept in this file.

## 5. The collisions, now counted

The board has carried flag X01 (“two builds share strategy IDs with different meanings”) as a narrative for a
week. It is now arithmetic, and there is a second one nobody had recorded:

* **15 strategy IDs** are claimed by more than one ledger; the clashing ones attach **different rule names**
  (S1 is *Elo margin vs closing spread* in two ledgers and *Own line vs close: 3+ pt edge* in a third).
* **8 gate IDs** — all of G1–G8 — mean different rules in `scripts/gates.py` and `docs/preregistration.md`.
  G1 is “Sample size” in one and “Provenance” in the other. **“Passed G4” is not a claim until the file is
  named.** This lab therefore uses IG1–IG9 and cites the file behind every threshold.

Both tables are on [`injury_lab/leaderboard.html`](injury_lab/leaderboard.html), computed by
`injury_lab/builds.py` from the ledgers themselves.

## 6. The cross-capture audit

The repository held exactly one prior transcription of the same official page
(`decision_lab/data/injuries.json`, captured 2026-11-12, 254 rows, **no retained page text**). This lab
captured the same URL on 2026-11-13 (49 rows for the overlapping clubs, **with** retained text). Comparing
them field by field is the only test available that can catch an error in a capture rather than in a parse:

* **49 of 49 rows in common** — no row exists in one record and not the other for those clubs.
* **31 identical on all five compared fields**; **0** position-code differences and **0** player-URL
  differences. The parser is not the weak link.
* **15 rows gained a designation** (and injury text) between the two days; 3 practice statuses changed; 2
  fixture record fields moved.
* Reading: the report is *updated through the week*, so two captures one day apart are two datasets. Both
  readings — page changed vs earlier bucketing choice — are printed; this lab does not pick one, because the
  older file cannot be re-verified.

Consequence for the gate register: a rule must state **which day's snapshot** it reads (suggestion **S19**),
and every published row anywhere in the repository should require a retained capture (**S18**, enforced here
as rule P7: each of the 139 rows must appear byte-verbatim in its capture or the build fails).

## 7. Six decisions, none implemented

[`injury_lab/decisions.html`](injury_lab/decisions.html) — each with options, cost, reversibility, risk, the
flag that raised it, and `chosen_option` left blank because no choice has been made.

| id | the question | recommendation |
|---|---|---|
| S15 | Namespace strategy and gate IDs at the generator | yes — before the injury family's IDs join the ledgers |
| S16 | Publish depth as a provenance tier; refuse the tiers a model may not read | yes — **refuse** weighting by invention |
| S17 | Commit to capture-at-scale, or stay descriptive, or spend ~32 fetches settling Q21/Q22 first | settle Q21/Q22 first, then full run |
| S18 | Require a retained capture for every published injury row repository-wide | yes for new rows; a separate authorised pass for the old file |
| S19 | Freeze the snapshot day in the gate register | yes — 18 of 49 rows moved in one day |
| S20 | State the unit-scope rule once; map the rest only from an official definition | label the scope now, retrieve the definition as the target |

Seven questions (Q19–Q25) block them; five are marked blocking, and none was answered by guessing. Q19 (what
each designation *means*, officially, and whether the vocabulary changed in 2016) is the one that gates the
most, because four of the nine rules are written in its terms.

## 8. Verification status

Ran green in this sandbox: `injury_lab.check_site` (**16 rules, 0 violations** over 13 pages; the rule set is P1–P17, P12 being reserved for the live
re-check this sandbox cannot run, and the counts each rule reports are printed by the command rather
than restated here, so this file cannot go stale against a rebuild),
`injury_lab.capture verify` (6 captures, hashes match), `decision_lab/check.py` (R1–R14 PASS),
`scripts/verify_site.py` (11/11), `pipeline/link_check.py` (PASS), `verify/linkcheck_all.py`
(**0 broken local links** across 173 pages / 7,926 local links / 10,373 external), `verify/source_audit.py`
with `--max-unsourced 0` (**0 gated unsourced rows**), `audit/check_audit_page.py` (OK).

**Cannot run in this sandbox and therefore not claimed as run here:** `verify/recompute_claims.py` and
`nfl_lab.check_verified` (both import numpy/pandas; `pip install -r requirements.txt` is blocked by PEP 668
here). They are unchanged by this session's edits — nothing in `injury_lab/` is imported by them, and the
root HTML diff is a single navigation link per page — and CI runs them. Also not run here, by necessity:
`capture verify --live`, which re-opens the official URLs to report rows the live page no longer prints
verbatim. This sandbox has no route to nfl.com; that is why P12 is reserved rather than silently dropped, and
why the second verification layer is documented on the site as an operator step.

## 9. Deliberately not done

* **No choice was made on the owner's behalf.** No suggestion is implemented, no flag closed, no gate
  loosened, no reward assigned.
* **No value was inferred.** 23 unit blanks, 55 blank designations, 5 chart slots with no name after them,
  3 ambiguous cells, all market fields for the three 2026 fixtures. Each is printed as a blank with the
  reason and the flag, and the checker refuses a bare placeholder.
* **No other session's file was rewritten.** `decision_lab/*`, `hub/*`, `docs/*` and the root generators are
  untouched except one additive `NAV` entry in `line_lab/build_site.py` and the regenerated root pages it
  produces — the integration privilege this session claimed in advance on the board.
* **No sportsbook page, pick site or third-party depth chart** was used as evidence. Lines and prices come
  from the pinned community dataset the repository already pins by commit, and every row that uses one says
  so, because the NFL publishes no betting lines.
* **No 2026 result was invented.** The three current-week fixtures are unplayed in the pinned file, so the
  join carries them with blank market fields and the pilot simply does not include them.

## 10. Where to click

| | |
|---|---|
| Start | [`injury_lab/index.html`](injury_lab/index.html) |
| What the source is and how it moves | [`injury_lab/capture.html`](injury_lab/capture.html) |
| The rows | [`injury_lab/injuries.html`](injury_lab/injuries.html) |
| Backups, in each club's own words | [`injury_lab/depth.html`](injury_lab/depth.html) |
| The brief's central question, answered | [`injury_lab/replacements.html`](injury_lab/replacements.html) |
| Rules, gates, pilot | [`injury_lab/signals.html`](injury_lab/signals.html) |
| Every ledger and both collisions | [`injury_lab/leaderboard.html`](injury_lab/leaderboard.html) |
| Two captures of one page | [`injury_lab/audit.html`](injury_lab/audit.html) |
| What a human must choose | [`injury_lab/decisions.html`](injury_lab/decisions.html) |
| What is wrong, including with this lab | [`injury_lab/flagged.html`](injury_lab/flagged.html) |
| What was checked, by which command | [`injury_lab/verification.html`](injury_lab/verification.html) |
