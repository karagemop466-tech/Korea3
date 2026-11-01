# Coordination board

Shared task board for concurrent agent sessions. Claim a task by writing your session ID and
file scope below, then commit and push the claim immediately. Do not start a task another
session has claimed. If a task needs a file owned by another session, log a request here
instead of editing the file.

## Board

| ID | Task | Status | Owner (session) | File scope | Claimed (UTC) |
|---|---|---|---|---|---|
| T0 | Static research-plan site (first pass, placeholder rows only) | done | arena/9febee68-korea3 | `*.html`, `style.css`, `scripts/*` | 2026-11-01 13:22 |
| T1 | Data ingestion + provenance manifest (pinned official-mirror snapshot, hashes) | in progress | arena/9f5e9cb5-korea3 | `pipeline/fetch_data.py`, `data/raw/*`, `data/raw/MANIFEST.json` | 2026-11-01 13:30 |
| T2 | Feature engineering + causality (no-lookahead) test | in progress | arena/9f5e9cb5-korea3 | `pipeline/features.py`, `tests/test_causality.py` | 2026-11-01 13:30 |
| T3 | Strategy backtests, walk-forward evaluation, validation gates | in progress | arena/9f5e9cb5-korea3 | `pipeline/strategies.py`, `pipeline/gates.py` | 2026-11-01 13:30 |
| T4 | Correlation + parlay dependence study | in progress | arena/9f5e9cb5-korea3 | `pipeline/correlations.py` | 2026-11-01 13:30 |
| T5 | Player-prop layer (blocked: no reachable official player-level lines/stats) | needs review | arena/9f5e9cb5-korea3 | `pipeline/props.py`, `props.html` | 2026-11-01 13:30 |
| T6 | Leaderboard / reward rules | in progress | arena/9f5e9cb5-korea3 | `pipeline/leaderboard.py` | 2026-11-01 13:30 |
| T7 | Site rebuild from generated data (all pages, nav, CSS) | in progress | arena/9f5e9cb5-korea3 | `*.html`, `style.css`, `assets/*` | 2026-11-01 13:30 |
| T8 | Executive summary + methodology + requirements traceability | in progress | arena/9f5e9cb5-korea3 | `EXECUTIVE_SUMMARY.md`, `docs/*` | 2026-11-01 13:30 |
| T9 | Build/link verification, PR, merge, Pages deploy | unclaimed | — | `scripts/check_site.py`, `COORDINATION.md` | — |

## Rules in force

- One session per file scope. `data/derived/*` and the root `*.html` files are shared outputs and are
  written only by the integration session (T7/T9), which is this session for the current run.
- No value is published unless it is reproduced by a committed script from a pinned input file.
- Blank means unverified. Never infer or backfill a value.

## Session log

### arena/9febee68-korea3 — 2026-11-01 13:22 UTC (complete)

- Repo contained only `README.md` at claim time. Built a seven-page research-plan site and
  `scripts/build.py` / `scripts/check.py`. Published **no** empirical results: every performance,
  correlation and reward value was left blank and flagged.
- PR [#1](https://github.com/karagemop466-tech/Korea3/pull/1) merged (merge commit `8771eec`),
  PR [#2](https://github.com/karagemop466-tech/Korea3/pull/2) merged (merge commit `89ded77`).
- Left T1–T8 open. That is the work this session picks up.

### arena/9f5e9cb5-korea3 — 2026-11-01 13:30 UTC (this session)

Claim: T1–T8, with T7/T9 acting as the integration session because no other session is active.
Branch `arena/9f5e9cb5-korea3`, merged `origin/main` (`89ded77`) before starting; no conflicts.

Environment constraint discovered and logged (see Flagged for Review): the research sandbox can
only reach `github.com`, `codeload.github.com`, `api.github.com`, `registry.npmjs.org`, `pypi.org`,
`files.pythonhosted.org`. GitHub **release assets** (`release-assets.githubusercontent.com`) are
blocked, so the canonical nflverse release files (play-by-play, player weekly stats, Next Gen Stats)
cannot be downloaded. Only git-committed data is reachable. This decides T5's status.

Handoff note: if a session with broader network access resumes, T5 should re-run
`pipeline/props.py` against the nflverse `player_stats` release plus licensed prop odds; the
script and gate wiring are committed and skip cleanly when the inputs are absent.
