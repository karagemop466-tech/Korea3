# Executive summary: NFL line-origination repository, 2026-11-15

Branch `arena/5210f1f2-korea3`. Built from the readiness section in `readiness/`. Live pages: `readiness/index.html` (decision-readiness table), `readiness/questions.html`, `readiness/suggestions.html`, `readiness/flagged.html`, `readiness/verification.html`.

## Bottom line

- **No strategy is live.** The lifecycle file records 0 of 18 strategies live. Nothing in this session changes that, and nothing is recommended for betting.
- **Two rules in the brief are contradicted by the repository today.** Backtest numbers appear on the leaderboard (F05), and two parlay strategies are ranked with no joint-evidence gate (F06).
- **Three Week 10 injury cells are wrong on the published site.** Kerby Joseph, Cade Mays and D.J. Reed are blank in the game-status column; the official NFL page lists all three as Out (F01).
- **Four clubs are shown as having no injuries when the official page lists players.** Seattle, Cincinnati, the Chargers and Baltimore are shown as "no injuries reported" (F02).
- **The repository's own injury capture is incomplete.** It is missing two Baltimore players, and two others have blank cells (F03).

## What the decision-readiness register says

The register holds 76 rows, one per requirement in the brief. Each row gives its status in this repository, the gate that blocks it, the number that would clear it, and its official source where one exists.

| Status | Rows |
|---|---|
| Built and gated as described | 11 |
| Partly built | 26 |
| Not built | 22 |
| Blocked on a source or decision | 9 |
| Contradicted by the repository | 3 |
| Need an owner decision | 2 |
| Not checked this session | 2 |
| Rejected by the brief (recorded as policy) | 1 |

Another session's scheduled capture job (`.github/workflows/capture.yml`, PR #95, merged to main while this session was in progress) now fetches the injury report and 32 club depth pages on a schedule and records hashes and UTC times. It does not parse values, and its manifest had no rows at this check, so the register marks the scheduling and hash rows (B26 to B32) as partly built, not complete.

The three contradicted rows are: backtest numbers on the leaderboard (A09), the Lions game-status cells (B04), and parlays ranked without a joint gate (C01).

## Blocked by sources that are missing

- **Depth order (backup-deficiency feature).** Only the Baltimore depth chart was confirmed on the official club page. The Houston chart is an image and is labelled "Unofficial". The NFL snap-count page returns 404. The feature stays blocked until one route is verified for all 32 clubs (B15).
- **Game books.** The official game-book URLs tried return 404. The game-book link has not been located (B35, Q10).
- **Prices.** For 2026 the store has 1,632 rows, and none has both an opening and a closing number (A01, Q03). The price-settlement policy is an owner decision (A13).

## Decisions only the owner can make (blocking)

Nine blocking questions are in `readiness/questions.html`. The most important:

1. Are club-published depth charts an official source? (Q01)
2. Which price settles bets: opening, closing or executable? (Q03)
3. Should backtest numbers ever appear on the leaderboard? (Q06)
4. Can parlays and prop combinations be ranked, and under which operator rules? (Q05)
5. Should the site split into a public analysis layer and a private data layer? (Q13)

## Flagged for review

Sixteen flags are on `readiness/flagged.html`, seven of them High. Flags do not block the merge. Each names the evidence and the official page. Three are about the same data problem: the hub, the raw capture and the live page disagree on Week 10 injuries (F01 to F03). Two are about the strategy register: three builds give three different strategy counts (F04), and the source-link gates pass even when the value is wrong (F11).

## What was verified, and what was not

Verified against official pages on 2026-11-15 (see `readiness/verification_log.md`):

- Lions Joseph, Mays and Reed: Out.
- Baltimore's live rows, cell by cell, for Campbell, Stanley, Hawkins and Randall.
- Seattle 15 rows, Cincinnati 9 rows, Baltimore 10 rows.
- Ravens QB order: Brissett, Fagnano, Slovis.
- The 2026 rule change permitting an onside kick at any time (6-1-6).

Not verified, and not claimed as verified:

- The live per-club row counts for the other 25 clubs, and the 347 total. The total is a manual count.
- Trades (12 rows) and reserve-list rows (17 on page 1). Both were transcribed from the page without a parser.
- Chunk 0 of the live injury page for CHI, DEN, PHI and TB.
- Venue text per fixture, and stadium roof and weather data.

The two register rows marked "Not checked this session" (A18, C07) are the vig-free consensus and fair-line formula checks. Neither was reviewed in this session.

## Suggestions (not implemented)

Twelve suggestions are on `readiness/suggestions.html`, each with a path and an effort estimate. Repair-now items: fix the Week 10 injury tables (S01), add a parser with row-count assertions (S02), add a live comparison to each scraper's check (S03), and pause the parlay rankings (S05). Owner-decision items: the depth-source ruling (S08), the price policy (S10) and the data split (S12). Nothing has been changed in the other builds (`hub/`, `decisions/`, `desk/`, `depth_lab/`). Those changes wait for the integration session, as the coordination rules require.

## Scope note

This is a review of repository state and a readiness register. It is not a model result, not a betting recommendation, and not a claim that any strategy works.
