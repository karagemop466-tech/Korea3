# Coordination board

Shared task board for concurrent agent sessions. Claim a task by writing your session ID and file scope below, then
commit and push the claim immediately. Do not start a task another session has claimed. If a task needs a file owned by
another session, log a request here instead of editing the file.

## Board

| ID | Task | Status | Owner (session) | File scope | Claimed (UTC) |
|---|---|---|---|---|---|
| T0 | Static research-plan site (first pass, placeholder rows only) | done | arena/9febee68-korea3 | `*.html`, `style.css`, `scripts/*` | 2026-11-01 13:22 |
| T1 | Data ingestion + provenance manifest (pinned snapshot, sha256, row counts) | done | arena/9f5e9cb5-korea3 | `pipeline/fetch_data.py`, `data/raw/*` | 2026-11-01 13:30 |
| T2 | Feature engineering + causality (no-lookahead) test | done | arena/9f5e9cb5-korea3 | `pipeline/core.py`, `tests/test_causality.py` | 2026-11-01 13:30 |
| T3 | Strategy backtests, walk-forward evaluation, validation gates | done | arena/9f5e9cb5-korea3 | `pipeline/strategies.py`, `pipeline/evaluation.py` | 2026-11-01 13:30 |
| T4 | Correlation + parlay dependence study | done | arena/9f5e9cb5-korea3 | `pipeline/correlations.py` | 2026-11-01 13:30 |
| T5 | Player-prop layer (blocked: no reachable official player-level data) | needs review | arena/9f5e9cb5-korea3 | `pipeline/props.py`, `props.html` | 2026-11-01 13:30 |
| T6 | Leaderboard / reward rules | done | arena/9f5e9cb5-korea3 | `pipeline/evaluation.py` (reward scoring), `leaderboard.html` | 2026-11-01 13:30 |
| T7 | Site rebuild from generated data (13 pages, nav, CSS) | done | arena/9f5e9cb5-korea3 | `*.html`, `assets/*`, `pipeline/build_site.py` | 2026-11-01 13:30 |
| T8 | Executive summary + methodology + requirements traceability | done | arena/9f5e9cb5-korea3 | `EXECUTIVE_SUMMARY.md`, `README.md`, `docs/*` | 2026-11-01 13:30 |
| T9 | Build/link verification, PR, merge, Pages deploy | in progress | arena/9f5e9cb5-korea3 | `pipeline/check_site.py`, `COORDINATION.md` | 2026-11-01 13:30 |

## Rules in force

- One session per file scope. `data/derived/*` and the root `*.html` files are shared outputs and are written only by the
  integration session (T7/T9), which is this session for the current run.
- No value is published unless a committed script reproduces it from a pinned input file.
- Blank means unverified. Never infer or backfill a value.

## Session log

### arena/9febee68-korea3 — 2026-11-01 13:22 UTC (complete)

- Repo contained only `README.md` at claim time. Built a seven-page research-plan site plus `scripts/build.py` /
  `scripts/check.py`. Published **no** empirical results: every performance, correlation and reward value was left blank
  and flagged.
- PR [#1](https://github.com/karagemop466-tech/Korea3/pull/1) merged (merge commit `8771eec`); PR
  [#2](https://github.com/karagemop466-tech/Korea3/pull/2) merged (merge commit `89ded77`).
- Left T1–T8 open. That is the work this session picked up.

### arena/9f5e9cb5-korea3 — 2026-11-01 13:30 UTC (this session)

**Claim.** T1–T8, with T7/T9 acting as the integration session because no other session is active. Branch
`arena/9f5e9cb5-korea3`, merged `origin/main` (`89ded77`) before starting; no conflicts.

**Environment constraint discovered and logged.** The research sandbox can only reach `github.com`,
`codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org` and `files.pythonhosted.org`. GitHub **release
assets** (`release-assets.githubusercontent.com`, `objects.githubusercontent.com`) are blocked, so the nflverse
play-by-play, player-stats and Next Gen Stats releases cannot be downloaded. Only git-committed data is reachable. This
is what makes T5 (player props) blocked rather than unfinished.

**What was built.** A dependency-light Python pipeline under `pipeline/` that downloads one pinned nflverse/nfldata
snapshot, hashes it, engineers strictly pre-game features, refits models per season, evaluates 11 pre-registered
strategies, applies nine gates, measures correlation structure, and generates the 13-page dashboard from a single
`summary.json`. See `README.md` for the map.

**Sources used (all reachable and checked in this session).**

| Source | Use | Verification |
|---|---|---|
| `nflverse/nfldata` @ `a270278f3ac4e937295fe6a27814b3c4a2b62645` | games, closing lines, opening lines (2021), win totals, teams | sha256 + row counts recorded in `data/raw/MANIFEST.json`, re-checked by `tests/test_causality.py` |
| `nflverse/nflreadr` `data-raw/dictionary_schedules.csv` | field semantics (spread sign, rest, roof, temp, wind, referee) | read from the pinned file |
| `nflverse/nflreadr` `R/load_schedules.R` | confirms schedules are served from `nflverse/nfldata` | read from source |
| `nflverse/nfldata` `DATASETS.md` | publisher notes on the games dataset | read from source |
| `nflverse/nflverse-data` release `player_stats` | proves the canonical player log exists but is unreachable here | release listing via GitHub API (1,822 assets) |

**Verification performed.**

- `python3 tests/test_causality.py` → passes: input hashes match the manifest; features rebuilt with data truncated at
  2022 are identical to the full-history features (max delta 0.0 over 6,151 rows); unplayed-game state equals the
  post-game rating of the last completed game; settlement recomputed independently on 400 random games; odds conversion
  and de-vig identities checked.
- `python3 -m pipeline.run_all` from a clean `data/derived/` reproduces every published number (fixed seeds).
- `python3 pipeline/check_site.py` → OK: 13 pages, all internal links resolve, every table row carries a source link,
  every blank carries a link to the review page, and strategy ROI/counts recomputed from `bets.csv` match `summary.json`.
- Site numbers cross-checked against `data/derived/summary.json` (e.g. best ROI +0.58%, luck band +5.45% mean / +16.28%
  p95, phi 0.671 same-game ML×spread vs 0.006 cross-game).

**Irregularities recorded** (published on `flagged.html`): player-prop inputs unreachable; price-column vendor
undocumented by the publisher; `closing_lines.csv`, `initial_lines.csv`, `win_totals.csv` have no published field
documentation; settlement at closing price is an upper bound; only 2021 has opening lines; same-game parlay pricing
rules unreachable; no funded reward pool; external method citations (NFL.com, NIST, operator help) unreachable and marked
unverified; S11 cannot be evaluated on the 2023–2025 holdout because win totals stop in 2020; the 2026 forward cut is a
partial season; referee tendency uses head officials only; weather fields exist only for outdoor/open roofs; week-1 rest
values are placeholders in the source; ingestion is a script, not a scheduled job; legal/eligibility not verified.

**Handoff note for T5.** If a session with broader network access resumes, run `pipeline/props.py` against the nflverse
`player_stats` release plus a licensed prop archive. The required schema, the estimator and the gate wiring are already
committed and skip cleanly while the inputs are absent.

**Files removed as superseded** (scope of this integration session): `scripts/build.py`, `scripts/check.py` and the
root `style.css` from T0. Their replacement is `pipeline/build_site.py`, `pipeline/check_site.py` and
`assets/style.css`. No T0 content was lost: every page was regenerated from data.

**T9 status.** Verification passed locally; PR, merge and Pages deploy recorded below once complete.

| Step | Result |
|---|---|
| PR to `main` | pending |
| Merge commit | pending |
| GitHub Pages deploy | pending |
