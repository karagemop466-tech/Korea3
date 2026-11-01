# COORDINATION.md — shared task board

**Repo:** `karagemop466-tech/Korea3`
**Project:** NFL line origination, signal research, strategy validation gates, correlation work, GitHub Pages site.
**Last updated:** 2026-11-01 (UTC)

## Protocol (read before working)

1. Read this file before starting any task.
2. Claim a task by writing your `session_id`, the date, and your **file scope** into the table below. Commit + push the claim immediately.
3. Never start a task another session has claimed. A claim older than **60 minutes with no commits** may be taken over — note the handoff in the log.
4. Work on your own branch named `session-<id>/<task>`. Edit **only** the files inside your claimed scope. If you need a change in a file owned by another session, write a request in the *Requests* section rather than editing it.
5. Shared outputs — `docs/index.html`, the nav, `data/derived/*` combined tables, and anything under `docs/data/` — are changed **only** by the integration session, after all other tasks are done.
6. `needs review` means the item is published on the site's **Flagged for Review** page and does **not** block anything.
7. Make small, frequent commits. Run `git pull --rebase` before every push. On a merge conflict: stop, resolve without discarding the other session's work, then log what happened below.
8. Never mark anything `verified` without an official source link recorded in `research/sources.md`.

## Session registry

| session_id | branch | role | started (UTC) |
|---|---|---|---|
| `session-c70bdb9d` | `arena/c70bdb9d-korea3` | research + build + integration (single session for this run) | 2026-11-01 13:23 |

> Note: this run had exactly one agent session. All tasks are claimed by `session-c70bdb9d`; the board is maintained anyway so that a future parallel session can pick up the open items in the *Backlog* section without duplicating work.

## Task board

| # | Task | Status | Owner | File scope | Commit |
|---|---|---|---|---|---|
| T01 | Repo review, baseline audit, irregularity log | in progress | session-c70bdb9d | `research/00-repo-review.md`, `README.md` | — |
| T02 | Source registry (tiered, official-first) | in progress | session-c70bdb9d | `research/sources.md` | — |
| T03 | Data layer + provenance pinning | in progress | session-c70bdb9d | `data/raw/**`, `data/provenance.json`, `scripts/fetch_data.sh` | — |
| T04 | Modelling dataset build (leak-free) | in progress | session-c70bdb9d | `scripts/build_dataset.py`, `data/derived/model_dataset.csv` | — |
| T05 | Line-origination model (walk-forward ratings) | in progress | session-c70bdb9d | `scripts/model.py`, `data/derived/model_predictions.csv` | — |
| T06 | Signal library + backtests | in progress | session-c70bdb9d | `scripts/signals.py`, `data/derived/signals_*.csv` | — |
| T07 | Validation gates + luck-removal statistics | in progress | session-c70bdb9d | `scripts/gates.py`, `data/derived/gates_*.csv` | — |
| T08 | Correlation lab (single / parlay / SGP) | in progress | session-c70bdb9d | `scripts/correlation.py`, `data/derived/corr_*.csv` | — |
| T09 | Player-prop combo framework | in progress | session-c70bdb9d | `scripts/props.py`, `data/derived/props_*.csv` | — |
| T10 | Leaderboard competition spec + scoring | in progress | session-c70bdb9d | `research/leaderboard.md` | — |
| T11 | Executive summary | in progress | session-c70bdb9d | `EXECUTIVE_SUMMARY.md` | — |
| T12 | Static site generator (landing + category pages) | in progress | session-c70bdb9d | `scripts/build_site.py`, `docs/**` | — |
| T13 | Link + provenance verifier | in progress | session-c70bdb9d | `scripts/verify_site.py`, `research/verification-log.md` | — |
| T14 | CI: verify + GitHub Pages deploy | in progress | session-c70bdb9d | `.github/workflows/**` | — |
| T15 | Integration: merge, PR, deploy, post-deploy check | in progress | session-c70bdb9d | `COORDINATION.md` | — |

## Backlog (unclaimed — open for a parallel session)

| # | Task | Why it is open |
|---|---|---|
| B01 | Player-prop **line** verification | No official NFL or operator source is machine-readable. Values are blank + flagged on the site. A human must collect them from operator rule/odds pages by hand, or connect a licensed odds API. |
| B02 | Injury / inactive reports | Not in the dataset. Requires official NFL injury-report pages (`nfl.com` team reports), which are published as PDFs weekly. |
| B03 | Weather ground truth | Dataset has `temp`/`wind` but no source field. Cross-check against an official station record before any weather signal is promoted past `needs review`. |
| B04 | Referee/penalty signals | Dataset carries `referee` but no penalty data. Needs official gamebook PDFs. |
| B05 | Travel / time-zone signals | Blocked: no verified venue-coordinate source in the dataset. Do not hardcode coordinates. |

## Requests (cross-scope)

_None yet._

## Log

| UTC | session_id | entry |
|---|---|---|
| 2026-11-01 13:23 | session-c70bdb9d | Board created. Repo cloned at `8c20600` (initial commit, only `README.md`, 8 bytes). All T01–T15 claimed by this session; claims committed before work started. |
