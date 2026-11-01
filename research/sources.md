# Source registry — tiered, with the exact sentence each citation supports

**Check date for every item below: 2026-11-01 (UTC).**
Machine-readable copy: `data/derived/verified_external.json`.

Tiers are disclosed because they are not equivalent:

- **Tier 1 — Official NFL.** Rules, scoring, timing, tie handling, and the league's own explanation of how spread pricing works.
- **Tier 2 — Licensed operator.** The actual counterparty for a bet: void rules, re-pricing, correlated-leg policy, minimum participation.
- **Tier 3 — Open dataset.** The only machine-readable record of NFL lines. Not official, fully disclosed, pinned by commit and checksummed.

---

## Tier 1 — Official NFL

### 1. 2026 NFL Rulebook
<https://operations.nfl.com/rules-officiating/2026-nfl-rulebook>
*Supports:* game rules, field dimensions, timing, and the 2026 rule changes.
*Verified content:* the 2026 rule-change table lists four changes — **6-1-3** (alignment of receiving-team players in the setup zone on a kickoff or safety kick), **6-1-5** (dead-ball spot after a touchback when the kickoff is from the 50-yard line), **6-1-6** (kicking team may declare an onside kick at any time), **19-2** (League personnel may consult on-field officials when considering disqualification for flagrant football and non-football acts). Official PDF: <https://static.www.nfl.com/image/upload/fl_attachment/league/tqivdkzt9mu6wdgsh1ku.pdf>
*Status:* verified — page read in full.

### 2. NFL Tiebreaking Procedures
<https://www.nfl.com/standings/tie-breaking-procedures>
*Supports:* tie handling. Exact sentence: *"Tie games count as one-half win and one-half loss for both clubs."* Also the full division / wild-card / draft-order procedures.
*Why it matters here:* ties are excluded from win-rate denominators (16 ties in 7,075 games = 0.23%), and this is the official rule that makes a tie not a loss.
*Status:* verified — page read in full.

### 3. NFL Support — "What is a money line?"
<https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line>
*Supports:* the **−110 standard price** and the **push rule**. Exact sentences: *"Most often, the betting odds for point spread are -110."* and *"if the point spread was +10/-10 and the favored team wins by exactly 10 or the underdog loses by exactly 10, you would push and get your initial wager returned."*
*Used for:* the break-even win rate 110/210 = 52.38%, which every gate and ROI on the site is measured against.
*⚠ Anomaly:* the page titled "What is a money line?" explains the **point spread**. The article bodies of this page and the next one appear to be swapped. Content is internally consistent; the titles are not. Flagged as F08.
*Status:* verified with caveat.

### 4. NFL Support — "What is the point spread?"
<https://support.nfl.com/hc/en-us/articles/35869774194324-What-is-the-point-spread>
*Supports:* moneyline pricing, and the tie-is-a-push rule. Exact sentence: *"If the game ends in a tie, the bettor's wager is returned with no loss or profit."*
*⚠ Anomaly:* as above — this page's body explains the **moneyline**.
*Status:* verified with caveat.

### 5. Creating the NFL Schedule (NFL Football Operations)
<https://operations.nfl.com/calendar-events/nfl-schedule/making-the-schedule>
*Supports:* the 272-game regular-season schedule, referenced for the rest and short-week variables. The Operations homepage describes the season as a *"272-game masterpiece"*.
*Status:* verified — link and description confirmed on <https://operations.nfl.com/>.

---

## Tier 2 — Licensed operators

### 6. FanDuel Sportsbook House Rules (Connecticut)
<https://www.fanduel.com/fanduel-sportsbook-house-rules-ct>
*Supports:* correlated-parlay policy. Exact sentence: *"Parlays containing selections where the outcome of one selection directly affects the outcome or pricing of another selection are not permitted, unless explicitly offered by FanDuel Sportsbook, e.g., as a Same Game Parlay bet."*
*Used for:* the conclusion that the only NFL leg pair clearing the correlation bar (moneyline × spread, φ = 0.672) is already re-priced rather than exploitable.
*Status:* verified.

### 7. FanDuel Sportsbook House Rules (Ontario)
<https://www.fanduel.com/fanduel-sportsbook-house-rules-on>
*Supports:* settlement *"according to the result declared by the relevant governing body at the end of the match (including any overtime played)"*; parlay void and re-calculation rules; maximum payout.
*Used for:* the statement that overtime counts for totals and props.
*Status:* verified.

### 8. DraftKings House Rules (regulator-hosted copy, dated 2023-06-01)
<https://massgaming.com/wp-content/uploads/DraftKings-House-Rules-6.1.23.pdf>
*Supports:* player-prop participation and correlated-leg policy.
*Quoted:* *"On any player prop market, player(s) must play at least one snap for bets to have action. If a player is listed as 'inactive' or 'did not play' for the relevant game, bets on that player/market will be void."* Also: pre-live Same Game Parlays are re-priced at bet-placement odds when a leg is voided; DraftKings reserves the right to void correlated legs.
*⚠ Anomaly:* the copy is dated **2023-06-01** and may have been superseded. Flagged as F09 — confirm against the live DraftKings page before relying on it.
*Status:* verified as of that copy, with caveat. A non-regulator mirror of the same text exists at <https://beta.goldennugget.com/lake-charles/casino/draftkings-sportsbook/draftkings-sportsbook-house-rules/>.

---

## Tier 3 — Open dataset

### 9. nflverse/nfldata @ `a270278f3ac4e937295fe6a27814b3c4a2b62645`
<https://github.com/nflverse/nfldata/tree/a270278f3ac4e937295fe6a27814b3c4a2b62645>
*Files used (checksums in `data/derived/checksums.txt`):*

| File | SHA-256 (first 16) | What it provides |
|---|---|---|
| `games.csv` | `ba34f3619067eb44` | Scores, closing spread/total, moneylines, prices, rest days, roof, surface, temp, wind, division flags, referee, coaches, QBs |
| `closing_lines.csv` | `3571e1c9fc8d7396` | Per-side closing lines and prices with outcome (2006+) |
| `initial_lines.csv` | `654770173d11fdb2` | Opening lines (2021+), used for the open/close comparison |
| `sc_lines.csv` | `384039e92630831e` | Secondary book spreads (2013+), cross-book sanity check only |
| `teams.csv` | `b7cfab98e6ac35c6` | Team code disambiguation across providers |

*Status:* pinned at the commit above (dated 2026-11-01T13:05:15Z), downloaded via a codeload tarball, checksummed, and re-downloadable with `scripts/fetch_data.sh`.
*Licence:* see the repository's own terms. Redistribution here is limited to what the analysis needs, with attribution and a pinned commit.

---

## What has no official source — and is therefore not published

| Item | Why it is missing | Where it is flagged |
|---|---|---|
| Player-prop prices and prop correlations | Operators publish props behind logins; the open dataset has no player box scores. **No correlation value is claimed anywhere on the site.** | `flagged.html` B01 |
| Historical closing lines "as published by the books" | Books do not publish archives. The Tier 3 dataset is the only record available. | `sources.html` §What has no official source |
| Injury reports / inactives | Published weekly as PDFs; not machine-readable here. Not used at all. | B02 |
| Weather ground truth | Dataset carries `temp`/`wind` with no source, station or timestamp field. | F05 / B03 |
| Venue coordinates, travel distance, time zones | No verified coordinate field in the dataset. Deliberately **not** hardcoded. | B05 |
| Opening lines before 2021 | Not in the dataset, so no full-history CLV study was possible. | B06 |

## Rules applied when citing

1. Every citation states the exact claim it supports, not just a link.
2. A source that contradicts itself (F08) is cited *and* flagged, never quietly dropped.
3. A source that may be stale (F09) is cited with its date.
4. Where no source exists, the number is left **blank** and the row is flagged. Nothing is filled in from general knowledge.
