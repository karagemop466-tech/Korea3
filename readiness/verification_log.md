# Official re-check log, 2026-11-15 (UTC)

Session: `arena/5210f1f2-korea3`. Task R02 in COORDINATION.md.
Machine-readable record: `readiness/data/official_recheck.json`. Rendered page: `readiness/verification.html`.

Method: the sandbox has no direct internet route to nfl.com; pages were read with the page-fetch tool, which returns rendered text. Images are not transcribed. Counts are manual counts of the fetched text and have not yet been checked by a parser. Each value below is marked **confirmed** (read again and matched) or **unverified** (read once, not re-checked).

## Pages read

| # | Official URL | What was read | Result |
|---|---|---|---|
| 1 | https://www.nfl.com/injuries/league/2026/reg10 | Week 10 2026 injury report, 8 chunks | 28 clubs have injury tables. CHI, DEN, PHI and TB have no table on the page. |
| 2 | https://www.nfl.com/injuries/ | Same report, chunks 0 to 7 | Same content as #1. |
| 3 | https://www.nfl.com/schedules/ | 2026 schedule, page 1 of 3 | Week pages and game-centre links (nfl.com/games/<away>-at-<home>-2026-reg-<week>). Venue text not read. Week 10 finals include Commanders 24 at Giants 21 (Thu 11/12), and Patriots 10 at Lions 35 (Sun 11/15, Munich). |
| 4 | https://www.nfl.com/transactions/ | 2026 transactions, full | November trades table: 12 rows (11/10 x9, 11/09 x2, 11/06 x1). Unverified beyond the row count. |
| 5 | https://www.nfl.com/transactions/league/reserve-list/2026/11 | Reserve list, page 1 of 2 | 17 rows with "Reserve/Injured" (11/09 to 11/14). Page 2 not read. |
| 6 | https://operations.nfl.com/rules-officiating/2026-nfl-rulebook | 2026 rulebook, page 1 of 3 | Rule changes table includes 6-1-6: onside kick may be declared at any time. Other rule changes listed (6-1-3, 6-1-5, 19-2). |
| 7 | https://www.baltimoreravens.com/team/depth-chart | Ravens depth chart, full | QB order: Jacoby Brissett, Joe Fagnano, Kedon Slovis. Lamar Jackson and Tyler Huntley are not listed at QB. |
| 8 | https://www.houstontexans.com/team/depth-chart | Texans depth chart | Headed "Unofficial Depth Chart". Depth table is an image; no table text. Not transcribed. |
| 9 | https://www.weather.gov/ | NWS root | Reachable. No stadium forecast retrieved; the stadium overlay is not verified. |
| 10 | https://www.nfl.com/news/nfl-week-9-inactives-players-ruled-out-sunday-2026-season | Linked from the injury page | Headline only; not re-opened. |
| 11 | https://www.nfl.com/news/dolphins-place-qb-malik-willis-groin-on-injured-reserve-kyle-mccord-in-line-for-first-start | Linked headline | Headline only: Malik Willis (groin) on injured reserve. |
| 12 | https://www.nfl.com/news/sam-darnold-ruled-out-for-seahawks-week-10-game-vs-raiders-drew-lock-expected-to-start-again | Linked headline | Headline only. |
| 13 | https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-thursday-nov-5 | Linked headline | Headline only: Ravens place Lamar Jackson on injured reserve. |

Paths that do not resolve (404): `https://www.nfl.com/snap-counts/`, `https://operations.nfl.com/gameday/nfl-game-book`, `https://www.nfl.com/official-game-books/`, `https://operations.nfl.com/rules-official-playing-rules/`. None is cited as a source.

## Week 10 injury cells (DET and BAL, compared by cell)

| Club | Player | Live: injury / practice / game status | Repository capture | Result |
|---|---|---|---|---|
| DET | Kerby Joseph | Knee / Did Not Participate / **Out** | `hub/data/injuries.json` blank game status; `depth_lab/data/raw` says Out | **Confirmed** against the page. Published hub blank: flag F01. |
| DET | Cade Mays | Ankle / Did Not Participate / **Out** | same | **Confirmed**. Same flag. |
| DET | D.J. Reed | Hip / Did Not Participate / **Out** | same | **Confirmed**. Same flag. |
| BAL | Calais Campbell | (blank) / Did Not Participate / (blank) | Missing from raw capture | **Confirmed**: missing row (F03). |
| BAL | Ronnie Stanley | (blank) / Did Not Participate / (blank) | Missing from raw capture | **Confirmed**: missing row (F03). |
| BAL | Jaylinn Hawkins | Knee / Limited / **Out** | Raw injury and game cells blank | **Confirmed** against the page (F03). |
| BAL | Adam Randall | Neck, Hamstring / Full / **Questionable** | Raw injury and game cells blank | **Confirmed** against the page (F03). |

## Week 10 per-club row counts

- Live page, manual count of the 28 clubs with tables: **347** rows (sum of the per-club values in `official_recheck.json`).
- **Confirmed** against the page: SEA 15, CIN 9, BAL 10.
- All other per-club counts are **unverified**: they were read once from the rendered text and have not been re-fetched or parsed.
- Repository raw capture (`depth_lab/data/raw/nfl_injury_w10_2026.json`): **345** rows across 28 clubs. Baltimore has 8 there.
- Published hub (`hub/data/injuries.json`): 254 players. Its "no injuries reported" list is SEA, CIN, LAC and BAL. The live page lists players for all four. LAC's live count is unverified.
- The brief's 279 figure matches none of these counts.
- CHI, DEN, PHI and TB: no table on chunks 1 to 7 of the live page. Chunk 0 was not checked for these four clubs (see open items).

## Trades and reserves

- Trades (12 rows, transcribed from the page): Jessie Bates (ATL to JAX), Jordan Davis (PHI to JAX), Amani Hooker (TEN to BUF), Keenan Allen (IND to SF), Kirk Cousins (LV to MIN), Daiyan Henley (LAC to DEN), Josh Downs (IND to KC), Ryan Neuzil (ATL to BAL), Andrew Vorhees (BAL to ATL) (all 11/10); Andre Cisco (NYJ to DET) and Davon Godchaux (NO to JAX) (11/09); Jacoby Brissett (AZ to BAL, 11/06). **Unverified**: transcription not parser-checked.
- Reserve list page 1 (17 "Reserve/Injured" rows, 11/09 to 11/14). Includes Malik Willis (MIA, 11/10). Willis is not in MIA's injury table. **Unverified**: transcription not parser-checked.

## Open items (not verified; do not cite as verified)

1. Per-club Week 10 counts other than SEA, CIN and BAL (25 clubs, including LAC).
2. CHI, DEN, PHI and TB: chunk 0 of the live page not yet checked.
3. Reserve list page 2 and trades beyond page 1 of the reserve log.
4. Official per-club depth tables for 32 clubs: only BAL confirmed. HOU is image-only.
5. Snap-count source: not located (404 at the tried path).
6. Official game-book URL: not located (404 at the tried paths).
7. Venue text per fixture from the game centre: not transcribed.
8. Stadium forecast and roof designations: not retrieved.

## Result

Nothing was confirmed in the repository beyond the cells in the table above. Flags F01, F02, F03, F12 and F09 stand. Items 1 to 8 are open and are recorded as unverified in `readiness/register.py` and on the register page.
