# Availability, questions and suggestions — line-by-line report

**Session:** `arena/d49013ad-korea3` · **Date:** 2026-11-12 (UTC) · **Base commit:** `9a3fc04` (PR #57)
**Branch note:** Arena fixes this session to `arena/d49013ad-korea3`. The brief's `session-<id>/<task>`
branch convention cannot be honoured; this is logged on the board, as earlier sessions did.

## 1. Why this work was needed

The board recorded requirements R01–R35 as `done`. Reading the current brief line by line showed
three statements with no published deliverable anywhere in the tree:

| Brief statement | Status before | Evidence of the gap |
|---|---|---|
| "create a section dedicated for suggestions so someone can review suggestions and choose the best path before implementing any changes" | not delivered | `grep -ril suggestion --include=*.html` over the repository returned **zero** site pages |
| "a clear list of questions, informations and answers that need to be addressed… Suggestions need to be made to discover missing information" | not delivered | no questions register page existed on any of the builds |
| "tracking injuries … 2nd,3rd or 4th string backups having to replace starters … same for offenses" | mentioned only as a blocked input | no page transcribed any official injury or depth data |

Reporting those as done would have been inaccurate, so they are now R36–R41 on the requirements
page (R40 is honestly `partial`).

## 2. Official sources opened and read this session

Every row below was read on the page itself, not quoted from memory or from another source.

| # | Publisher | Page | What it establishes here |
|---|---|---|---|
| 1 | NFL | <https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693> | The current injury-report vocabulary, quoted verbatim: Out/Doubtful/Questionable definitions, the three practice labels, the removal of "Probable", and the rule that a player certain to play is not listed on the Game Status Report. |
| 2 | NFL | <https://www.nfl.com/injuries/> | Official Week 10 2026 injury report, per-club tables with Player / Position / Injuries / Practice Status / Game Status. All four clubs in scope transcribed. |
| 3 | NFL | <https://www.nfl.com/news/nfl-week-10-injury-report-2026-season> | Game-status narrative for all 14 Week 10 games: Commanders OUT (Yankoff, knee; Patrick, concussion), Giants QUESTIONABLE (Harrison, groin), Patriots OUT (Brown, knee; Davis, knee; Henderson, illness). No status line printed for the Lions or the other 10 clubs listed in the source claim. |
| 4 | NFL | <https://www.nfl.com/inactives/> | "Please check back soon for NFL Inactive Reports for this Season" — activation is unverifiable today. |
| 5 | NFL Football Operations | <https://operations.nfl.com/calendar-events/nfl-free-agency/contract-language> | 53-man active/inactive list; practice-squad standard elevation capped at three regular-season games per player per league year. |
| 6 | Washington Commanders | <https://www.commanders.com/team/depth-chart> | The club's own depth chart, 23 rows transcribed in printed order, including the blank slot in the second LB row. |
| 7 | New York Giants | <https://www.giants.com/team/depth-chart> | 23 rows transcribed; LB rows show McFadden/Barnes, Reese/Kelly, Carter/Thibodeaux. |
| 8 | New England Patriots | <https://www.patriots.com/team/depth-chart> | 23 rows transcribed plus the club's own disclaimer: "The 2026 depth chart is unofficial… reflects the opinions of the Patriots.com writers and don't necessarily reflect those of the organization." |
| 9 | Detroit Lions | <https://www.detroitlions.com/team/depth-chart> | 22 rows transcribed; the page is titled "2026 Unofficial Depth Chart Compiled by Lions Football Communications". |
| 10 | NFL | <https://www.nfl.com/teams/washington-commanders/roster> | Membership codes ACT/RES/TRC/TRD; used to check who is on the active roster. |
| 11 | Washington Commanders | <https://www.commanders.com/team/players-roster/> | Jersey numbers 30 (Ekeler), 34 (Henry), 63 (Lucas Patrick, position G). |

Four further URLs were tried and returned a 404 page on this date, which is itself recorded (A09):
`operations.nfl.com/game-operations-logistics/in-game-operations/injury-report`,
`operations.nfl.com/the-players/injury-report-policy`,
`nfl.com/news/nfl-injury-report-policy`, `nfl.com/teams/<club>/depth-chart`.

## 3. What could not be verified, and was therefore left blank

| Item | Why it is blank | Where it is published |
|---|---|---|
| Any probability of a player playing | The NFL defines its labels qualitatively only and publishes no percentage | `hub/availability.html`, Q03 |
| Snap counts / true starter designation | Not published on any page read; requires licensed participation data | Q04, suggestion S05 |
| Realised availability behind each label | Requires the official inactive list, which is not published for 2026 | Q07, A07 |
| Weight of a missing left tackle vs a missing third corner | No official source ranks positions by importance | Q17 |
| The other 28 clubs | Not transcribed, so not implied | A10 |
| Every ROI, edge, correlation and leaderboard rank | No licensed timestamped price archive | Q01 (unchanged from earlier sessions) |

## 4. Irregularities flagged this session

`A01`–`A10` on `hub/availability.html` and, in the same wording, on `hub/flagged.html`:

| ID | Irregularity |
|---|---|
| A01 | Lucas Patrick (WAS): printed **Out** (concussion), active on the NFL.com roster as C with an empty jersey number, active on the club roster as G with number 63, and absent from every row of the club depth chart. |
| A02 | Malik Harrison (NYG): printed **Questionable** (groin) and absent from every row of the club depth chart. |
| A03 | Austin Ekeler (WAS): NFL.com jersey-number cell empty; club prints 30. |
| A04 | Robert Henry Jr. (WAS): NFL.com prints 30; club prints 34. |
| A05 | Patriots.com labels its own depth chart **unofficial** in its own words. |
| A06 | DetroitLions.com labels its own depth chart **unofficial**. |
| A07 | No 2026 inactive report is published; activation cannot be verified. |
| A08 | Kerby Joseph (DET): limited participant, absent from every row of the club depth chart. |
| A09 | Four official-looking injury/depth URLs return 404. |
| A10 | Coverage limit: 4 of 32 clubs. |

## 5. Verification performed on the built site

| Check | Command | Result |
|---|---|---|
| Dashboard build | `python3 hub/build_hub.py` | 23 pages, 38 sources, 44 flags |
| Dashboard gate | `python3 hub/check_hub.py` | **PASS** — 1014 table rows, 1391 official row links, 1785 internal links, 1414 external links, 0 broken |
| Root site gate | `python3 line_lab/check_site.py` | OK — 16 pages, 47 GitHub source links |
| Root site gate | `python3 scripts/verify_site.py` | 11/11 checks passed |
| Root site gate | `python3 pipeline/link_check.py` | PASS |
| Verified workbench | `python3 -m nfl_lab.check_verified` | OK — 12 pages, 146 rows, every row registry-matched |
| Test suite | `python3 -m pytest tests/ -q` | 34 passed |
| Pages served | `python3 -m http.server` + `curl` | 200 for `/`, `/hub/index.html`, `/hub/availability.html`, `/hub/questions.html`, `/hub/suggestions.html`, `/hub/flagged.html` |

New gates added to `hub/check_hub.py` so these pages cannot silently regress: page count 23;
row floors per page; all four club depth sources present; `a01`…`a10` anchors present; the club
"unofficial" disclaimers present; a block-list of invented-availability phrasings
("probability of playing", "likely to start", "snap share of", "projected starter"); q01…q20 and
s01…s14 present; the Suggestions page must label effort/risk as judgement.

## 6. What this session did not do

* No price, ROI, correlation, win rate or ranking is claimed anywhere new — the existing blanks stand.
* No file outside the claimed scope was edited; `hub/assets/` was not touched.
* `line_lab/build_site.py` was edited for one reason: its banner hard-coded "20 pages" and would
  have published a false count after this change. It now derives the count.
