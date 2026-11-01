# COORDINATION.md — Shared Task Board

This is the shared task board for every agent session working on this repository.
Read this file before starting. Claim a task by writing your session ID + file scope,
then commit and push that claim **before** you start work.

**Session ID format:** `sess-<branch-suffix>`. Branch format: `session-<id>/<task>`
(or `arena/<suffix>` when the platform fixes the branch name — see note below).

---

## Session registry

| Session ID | Branch | Started (UTC) | Status | Notes |
|---|---|---|---|---|
| `sess-398c4b58` | `arena/398c4b58-korea3` | 2026-11-01T13:23Z | active | Branch name is fixed by the platform and cannot be renamed; scope rule (non-overlapping files) still applies. |

> **Branch-name note (irregularity, logged):** The platform binds this session to the
> branch `arena/398c4b58-korea3` and forbids creating/renaming branches. The required
> naming convention `session-<id>/<task>` could therefore not be used for this session.
> No other branch was created or pushed to.

---

## Task board

Status values: `unclaimed` · `in progress` · `done` · `needs review`.
`needs review` = published on the *Flagged for Review* page; it does not block other work.

| # | Task | Status | Owner | File scope |
|---|---|---|---|---|
| T01 | Data acquisition + provenance/checksum layer | done | `sess-398c4b58` | `scripts/fetch_data.py`, `data/raw/*`, `data/PROVENANCE.json` |
| T02 | Feature engineering + leakage-safe power ratings | done | `sess-398c4b58` | `scripts/features.py`, `data/derived/features.csv` |
| T03 | Market-structure research (vig, hold, break-even, line distribution) | done | `sess-398c4b58` | `scripts/market.py`, `research/02_market_structure.md` |
| T04 | Strategy registry + mechanical rule specs | done | `sess-398c4b58` | `scripts/strategies.py`, `research/03_strategies.md` |
| T05 | Bet engine (singles / parlays / SGP) + walk-forward simulation | done | `sess-398c4b58` | `scripts/engine.py` |
| T06 | Validation gates + luck-removal statistics (bootstrap, permutation, FDR, deflated Sharpe) | done | `sess-398c4b58` | `scripts/validate.py` |
| T07 | Correlation estimates (game-level markets + player props) | done | `sess-398c4b58` | `scripts/correlations.py` |
| T08 | Leaderboard scoring + reward rubric | done | `sess-398c4b58` | `scripts/leaderboard.py` |
| T09 | External spot-verification against Pro-Football-Reference | done | `sess-398c4b58` | `scripts/verify_external.py`, `data/verification.json` |
| T10 | Site (landing + category subpages + tables with per-row sources) | done | `sess-398c4b58` | `docs/**` |
| T11 | Executive summary | done | `sess-398c4b58` | `research/EXECUTIVE_SUMMARY.md` |
| T12 | Integration: merge, link check, Pages deploy, PR | done | `sess-398c4b58` | `docs/**`, `COORDINATION.md`, PR |

**Concurrency note (2026-11-01T13:23Z):** a scan of `git branch -a` showed only `main`
and this session's branch — no other session had claimed work when T01–T11 were claimed.
All claims above were made by `sess-398c4b58` in commit #1 of this branch. If a second
session joins later, it must not edit files listed in a `done` row without logging a
change request here first.

---

## Change requests between sessions

| Date | Requesting session | File | Requested change | Status |
|---|---|---|---|---|
| — | — | — | none logged | — |

---

## Verification log

Every row records what was checked, against which source, and what came out.

### V1 — Dataset provenance (T01)
- **What:** `data/raw/games.csv`, `closing_lines.csv`, `sc_lines.csv`, `initial_lines.csv`,
  `win_totals.csv`, `teams.csv` from the public nflverse/nfldata repository.
- **Source URL:** https://github.com/nflverse/nfldata/tree/a270278f3ac4e937295fe6a27814b3c4a2b62645/data
- **Method:** pinned commit SHA, SHA-256 of every downloaded file recorded in
  `data/PROVENANCE.json`, re-downloadable with `scripts/fetch_data.py`.
- **Result:** verified as *the bytes we used* (self-consistent + reproducible).
  **Not** verified as an *official NFL or sportsbook* publication — nflverse is an
  independent open-data project. Line provenance (which book each number came from) is
  **not documented by the publisher** ⇒ logged as irregularity **IR-01**, published on
  the Flagged for Review page.

### V2 — Sign conventions and internal consistency (T01/T02)
- **Checked:** `result = home_score − away_score`, `total = home_score + away_score`,
  `spread_line` sign (positive = home favoured).
- **Method:** arithmetic recomputation over all rows + correlation test
  (`corr(spread_line, result) > 0`).
- **Result:** conventions hold; see `data/verification.json`.

### V3 — External spot-check vs Pro-Football-Reference (T09)
- **What:** sampled game rows (scores + closing spread/total) compared to the PFR
  season schedule page for the same season.
- **Sources:** per-season `https://www.pro-football-reference.com/years/<season>/games.htm`.
- **Result:** recorded per-row in `data/verification.json` with status
  `match` / `mismatch` / `unconfirmed`. Mismatches and unconfirmed rows are published on
  the Flagged for Review page. A value that could not be confirmed is left blank in the
  site tables rather than inferred.

### V4 — Player-level props data provenance (T07)
- **What:** weekly player box-score mirror used for prop correlation estimation
  (`weekly_player_stats_offense_smaller.csv`, 75,368 player-weeks, seasons 2015–2023).
- **Source URL:** https://github.com/DevinOgrady/NFL-Player-Projections
- **Method:** schema `game_id` values match the nflverse game identifier format; a random
  sample of player-weeks is spot-checked against PFR box scores.
- **Result:** structural consistency confirmed; **publisher documentation absent** ⇒
  provenance is *unverified* and marked as such everywhere it is used
  (**IR-02**, Flagged for Review). Correlation numbers derived from it are reported with
  bootstrap confidence intervals and are explicitly labelled *provisional*.

### V5 — Site integrity (T12)
- Link check over all generated pages (internal + external), JSON schema check of every
  table row (source URL present), and build reproducibility check.
- **Result:** recorded in the PR body and in the merge record at the bottom of this file.

---

## Integrations, merges and deploys

| Date (UTC) | Action | Result | Link |
|---|---|---|---|
| 2026-11-01 | PR from `arena/398c4b58-korea3` → `main` | see PR body | _(recorded in PR + below)_ |
