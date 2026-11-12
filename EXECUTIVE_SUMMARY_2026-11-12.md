# Executive summary — 12 November 2026

**Session:** `arena/6cbe5d15-korea3` · **Branch:** `arena/6cbe5d15-korea3` → `main`
**Dashboard:** <https://karagemop466-tech.github.io/Korea3/hub/index.html>
**New pages:** [Injuries & depth](https://karagemop466-tech.github.io/Korea3/hub/injuries.html) ·
[Suggestions](https://karagemop466-tech.github.io/Korea3/hub/suggestions.html) ·
[Questions & decisions](https://karagemop466-tech.github.io/Korea3/hub/questions.html)
**Board:** [`COORDINATION.md`](COORDINATION.md) · **Flags:** <https://karagemop466-tech.github.io/Korea3/hub/flagged.html>

---

## 1. Bottom line

The repository already contained a full line-origination research stack, a fail-closed leaderboard and an
official-evidence dashboard. This revision adds the four things the brief asked for that were still missing:
injury tracking with a backup-deficiency read, a suggestions section that must be reviewed before anything is
implemented, a questions register that states what is known and unknown before a decision, and this summary.

Three conclusions matter for a decision:

1. **Injuries can now be tracked from an official source, but only as a dated snapshot.** The NFL publishes a
   weekly injury report with practice and game status; there is no licensed machine-readable feed and no
   archive. 44 rows across four clubs are published, dated, and linked to the live page.
2. **“2nd/3rd/4th string” cannot be published as an official fact.** The league publishes no depth chart.
   Depth charts are club pages, and New England and Detroit label theirs *unofficial* in the page itself.
   The site therefore prints the club's order as published, marks the read as recomputed, and flags the five
   players who appear on an injury report but on no depth row.
3. **The competition still cannot rank or pay anything.** Ten questions block a defensible decision,
   including the data licence, the quote archive, the power target, the gate thresholds and the reward terms.
   These are published as blank answers with sources, not filled with plausible values.

## 2. What was verified line by line (all opened 2026-11-12 UTC)

| What | Official page | What it establishes |
|---|---|---|
| Injury report | <https://www.nfl.com/injuries/> | The report's exact columns are Player, Position, Injuries, Practice Status, Game Status. Week 10 of the 2026 season was live at retrieval. |
| Designation definitions | <https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693> | DNP / Limited / Full, and Out / Doubtful / Questionable, are defined by the league. “Probable” was eliminated; a player certain to play is not listed. |
| Player-stat categories | <https://www.nfl.com/stats/player-stats/> | 11 categories, **none** of them snap counts; the direct snap-counts URL returns the official 404. |
| Commanders depth chart | <https://www.commanders.com/team/depth-chart> | C Allegretti / Gulbin; TE Bates / Yankoff with no third string; CB Robertson / Douglas. |
| Giants depth chart | <https://www.giants.com/team/depth-chart> | QB McCarthy / Winston; RB Skattebo / Singletary; LB Harrison not listed. |
| Patriots depth chart | <https://www.patriots.com/team/depth-chart> | Self-labelled **unofficial**. LG Ben Brown / Rouse; C Wilson / Brown; RB Stevenson / Henderson / Kiner / Larison. |
| Lions depth chart | <https://www.detroitlions.com/team/depth-chart> | Self-labelled **unofficial**. C Mays / Scruggs; S Branch / Izien; S Joseph not listed. |

Every table row on the three new pages links one of these pages or a repository artifact. Where a value could
not be confirmed, it is blank and links to *Flagged for Review*; nothing was inferred.

## 3. The six findings the two official sources actually support

1. **New England left guard is depleted at both levels** — Ben Brown (listed 1st) is Out; Walter Rouse
   (listed 2nd) did not practise, and no third guard is listed.
2. **New England running back is depleted at the top two** — Stevenson (1st) did not practise; Henderson
   (2nd) is Out; Kiner (3rd) and Larison (4th) are the listed alternatives.
3. **Washington's only listed tight-end backup is Out** — Colson Yankoff sits behind Bates, with no third
   string published.
4. **Detroit's starting centre is uncertain** — Cade Mays did not practise with no game-status designation;
   Scruggs is the only listed backup.
5. **Detroit's reported safety injury cannot be placed in the depth order** — Kerby Joseph (limited) is on no
   depth row, while Branch (listed 1st at the other safety slot) is also limited.
6. **Five players do not join at all** (F12) — Patrick (WAS), Harrison (NYG), Gilliam and Van Roten (NE),
   Joseph (DET). The two official pages are not a joinable key set, so an automated join must fail closed.

A **Depth Deficiency Index** is specified on the injuries page (availability load, depth thinness, replacement
exposure, persistence) but **no score is published**: coverage is 4 of 32 clubs, no official snap count exists,
and no threshold has been validated. Publishing a number from that sample would be a guess dressed as a
measurement.

## 4. Questions that must be answered before a decision (10 of 18 block)

Full register with the information held and missing: [`hub/questions.html`](hub/questions.html).

| # | Blocking question | Why it blocks |
|---|---|---|
| Q01 | Do we hold written permission or a licence for official NFL data? | Nothing empirical can be published lawfully without it. |
| Q05 | Is there an official snap-count source? | Replacement exposure cannot be measured, only asserted. |
| Q06 | Is the official inactive list archived? | The injury report is not the final availability list. |
| Q07 | How is “starter” defined? | The whole backup question depends on it. |
| Q08 | What sample separates skill from luck? | A leaderboard that ranks noise is worse than none. |
| Q09 | Which gates are mandatory, at what thresholds? | Without fixed thresholds everything can be declared a pass. |
| Q10 | What are the reward-pool terms? | No sponsor, pool, jurisdiction or payout exists. |
| Q11 | Which operators and markets are in scope? | A signal is only defined against a named market. |
| Q16 | What is the false-discovery policy? | Ranking many rules without it manufactures winners. |
| Q17 | What wins when two official pages disagree? | Five rows already fail to join; each case would be ad hoc. |

Seven questions are answered from official pages (designation meanings, report structure, parlay pushes,
prop settlement on a non-starter, absence of a depth field, absence of a snap category, snapshot
irreproducibility). One (Q15, signal strength) is non-blocking.

## 5. Suggestions — pick a path, not a pile of items

Full register with impact, effort, risk and dependencies: [`hub/suggestions.html`](hub/suggestions.html).
**Nothing on it has been implemented.**

| Path | Sequence | What it buys | Cost | Recommendation |
|---|---|---|---|---|
| **A — Evidence first** | S01 → S02 → S09 → S08 → S11 | Lawful data, a quote archive and a real skill test: the only route to a defensible leaderboard | Highest; needs a licence and a vendor | do **third** |
| **B — Coverage first** | S03 → S04 → S06 → S05 → S15 | A dated, league-wide availability and depth record from pages we can already verify | Medium; engineering | do **first** |
| **C — Governance first** | S07 → S12 → S13 → S10 → S14 | One authoritative surface, live link checks, no implied prizes, reversible changes | Low; immediate | do **second** |

**Recommendation: B, then C, then A.** Do not start reward terms (S11) before the licence position (S01)
and Q10 are resolved. Any path can be recorded in the decision table on the suggestions page; an empty cell
there is an unmade decision, not an unverified fact.

Highest-leverage single items: **S03** (archive the injury report daily — it fixes the mutability problem and
is the only way to test the signal) and **S07** (a source-precedence rule — five rows already conflict).
Cheapest: **S13** (check every official URL live in CI, not just against an allow-list) and **S15** (date
every mutable table).

## 6. What was deliberately not done

* No scraping, harvesting or storage of NFL content beyond the 44 dated rows transcribed for verification,
  under the NFL Terms boundary already flagged as N01/F17.
* No invented depth chart, no inferred starter status, no imputed injury severity.
* No reward amount, rank, ROI, correlation or “edge” published: every such value remains blank.
* No other session's directory edited; no site deleted; no shared file changed outside the dashboard scope.

## 7. Verification performed (console results, this checkout)

| Check | Result |
|---|---|
| `python3 hub/build_hub.py` | built 23 pages; 34 sources; 42 flags (deterministic) |
| `python3 hub/check_hub.py` | **PASS** — 23 pages, 971 table rows, 1,412 official row links, 1,039 blank markers, 1,775 internal links, 1,435 external links, 0 problems |
| `python3 line_lab/check_site.py` | OK — 16 pages, links resolve, hashes and recomputed numbers match |
| `python3 scripts/verify_site.py` | 11/11 checks passed |
| `python3 pipeline/link_check.py` | PASS |
| `python3 -m nfl_lab.check_verified` | OK — 12 pages, 146 rows, official source on every row |
| `python3 verification/reproduce.py` | 66/66 PASS, 0 FAIL |
| `python3 verification/link_audit.py` | 137 pages, 0 broken internal links, 7,981 external links across 27 domains |
| `python3 -m pytest tests/test_lab_*.py tests/test_evidence_hardening.py` | 34 passed |

## 8. Irregularities published for review

F10 official club depth charts are self-labelled unofficial · F11 no league-wide official depth chart ·
F12 five injury-report players absent from their club's depth chart · F13 no official snap-count category ·
F14 injury report is live and unarchived · F15 no official inactive-list archive · F16 suggestions await a
decision · F17 injury transcription sits close to the NFL Terms boundary.

All are published with source links on <https://karagemop466-tech.github.io/Korea3/hub/flagged.html> and do
not block publication. Nothing here is betting advice, and no strategy in this repository has demonstrated
skill at the required significance level.
