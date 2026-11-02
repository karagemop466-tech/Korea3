# Coordination board — NFL line research repository

## ACTIVE CLAIM — final integration session `arena/25ea8ac4-korea3` (2026-11-02 17:14 UTC)

This section is the current board. Everything below it is preserved history.

**Role:** final integration session. **Source branch and target branch:** `arena/25ea8ac4-korea3` → `main`.
**Base commit:** `9069c3d654f03d6fe38e165c63a31d2ac9f7d401` (PR #37 merge). `origin/main` was fetched
and is at the same commit; no other session has pushed since. Open PR #19 (`arena/65d448da-korea3`,
audit styling) is unrelated to this scope and is left untouched.

**Branch-name deviation (logged, not hidden):** the brief asks each session to work on a
`session-<id>/<task>` branch or worktree. Arena fixes this session to `arena/25ea8ac4-korea3` and
forbids switching to, creating or pushing any other branch, so all work and all commits stay on the
assigned branch. No worktree is used. This matches how earlier sessions recorded the same constraint.

**Stale-claim handoff:** T15 (`arena/c70bdb9d-korea3`, "Integration: merge, PR, Pages") is marked
`in progress` with a last commit on 2026-11-01, i.e. more than 60 minutes old with no commits.
Its work (PRs #9/#15/#17, `/site/`, Pages deploy) is in fact complete and recorded as done later in
this file. Under the handoff rule this session takes over the *integration* role and notes the
handoff here; no files were removed or overwritten. No other task is claimed by another session.

| # | Task | Status | Owner | File scope |
|---|---|---|---|---|
| I01 | Board claim + branch/deviation + handoff record | done | `arena/25ea8ac4-korea3` | `COORDINATION.md` (additive sections only) |
| I02 | Line-by-line repo and source re-verification against official publishers | in progress | `arena/25ea8ac4-korea3` | `hub/data/sources.json`, `hub/data/verification.json`, `hub/verification.html`, `hub/repo-review.html` |
| I03 | Consolidated executive summary + full requirement traceability | unclaimed→in progress | `arena/25ea8ac4-korea3` | `INTEGRATION_EXECUTIVE_SUMMARY.md`, `hub/requirements.html`, `hub/analysis.html` |
| I04 | Clean dashboard landing page + category subpages (official-source-only rows) | in progress | `arena/25ea8ac4-korea3` | `hub/**` (new directory), `index.html` (additive "Start here" link), `README.md` (additive pointer) |
| I05 | Flagged for Review page, verifier and build/link checks | in progress | `arena/25ea8ac4-korea3` | `hub/flagged.html`, `hub/build_hub.py`, `hub/check_hub.py`, `.github/workflows/hub-verify.yml` (new file) |
| I06 | Final integration: PR, merge, Pages deploy confirmation, board record | unclaimed→pending I02–I05 | `arena/25ea8ac4-korea3` | `COORDINATION.md` |

**Scope boundary:** no file under `audit/**`, `docs/**`, `reports/**`, `pipeline/**`, `scripts/**`,
`data/**`, `line_lab/**`, `nfl_lab/**`, `site/**`, `verified/**`, `session-398c4b58/**` is edited.
Those remain owned by their original sessions. `docs/`, `reports/`, `verified/`, `nfl_lab/` are
covered by CI drift gates and are deliberately left byte-identical. Request logged (not acted on):
the owner of open PR #19 should rebase it separately; this session will not edit `audit/**`.

> **Integration notice — 2026-11-01, session `arena/c70bdb9d-korea3`.**
>
> Three sessions published a site to this repository concurrently and each wrote its own board.
> The audit session flagged the collision explicitly and asked for reconciliation before any
> integration. This file is that reconciliation. **Nothing was deleted, renamed or overwritten.**
>
> | Body of work | Session | Source in the repo | Served at |
> |---|---|---|---|
> | Empirical pipeline + dashboard (this session) | `c70bdb9d` | `site/` (generated), `scripts/`, `data/` | `/site/` |
> | First research brief | `9febee68` | root `*.html`, `style.css` (untouched) | `/prior/` (byte-identical copy) |
> | Second Line Lab build | `d118ca7e` | `docs/` (untouched) | `/prior-d118ca7e/` (byte-identical copy) |
> | Independent audit | `65d448da` | `audit/` (untouched) | `/prior/audit/` (copy) |
>
> **How the collision was resolved without a Pages setting change.** GitHub Pages here is a
> legacy branch deploy from `main:/`, which serves *every* directory, so all three sites can be
> live at once. The dashboard is at `/site/`, the first brief stays at `/`, the second stays at
> `/docs/`. The only edit made to another session's file is an additive "Start here →" banner at
> the top of the root `index.html`, added by this integration session because the integration
> role owns site navigation; every other byte of that file is unchanged and all its content
> renders as before. The Pages source setting could **not** be changed from this session (the
> API returns 403 "Resource not accessible by integration"), which is why the root page carries a
> link instead of the site being repointed. `docs/` and `reports/` are byte-identical to `main`,
> so `d118ca7e`'s CI gate (`git diff --exit-code -- reports docs`) still passes.
>
> ⚠ **Risk to note:** running `python3 scripts/build.py` regenerates the root pages and would
> drop that banner. If you regenerate, re-add it or re-point Pages.
>
> **Requests to any later session:** re-point the Pages source rather than overwrite a site
> directory; if you edit `docs/` or the root pages, mirror them into `site/prior-d118ca7e/` and
> `site/prior/` so the published copies stay in step.

## Session registry

| session_id | role | claimed scope (as recorded by that session) | status |
|---|---|---|---|
| `arena/9febee68-korea3` | first brief + root site | root `*.html`, `style.css`, `scripts/build.py`, `scripts/check.py` | merged (PR #1); root later regenerated by `9f5e9cb5`, brief preserved in git history |
| `arena/65d448da-korea3` | independent audit + QA | `audit/**`, this board | merged (PRs #3,#4,#5,#7,#8); preserved |
| `arena/d118ca7e-korea3` | second site + pipeline | `docs/**`, `pipeline/**`, `reports/**`, `LINE_LAB.md`, `ci.yml` | merged (PR #6); preserved at `/prior-d118ca7e/` |
| `arena/c70bdb9d-korea3` | empirical pipeline + site + this integration | `data/**`, `scripts/**` (own files), `site/**`, `research/**`, `EXECUTIVE_SUMMARY.md`, this board | merged (PRs #9, #15, #17); site live at `/site/` |
| `arena/9f5e9cb5-korea3` | root dashboard + `line_lab/` pipeline | `line_lab/**`, root `*.html`, `assets/**`, this board | merged (PR #13, `5eddec4b`); dashboard live at `/`, deploy verified |
| `arena/398c4b58-korea3`, `arena/44bf7e85-korea3`, `arena/cbcd97cc-korea3` | claimed by the audit session as overlapping | — | not visible on `main`; no files found |

## Task board — session `arena/c70bdb9d-korea3`

Claimed in commit `8541cf5` **before** any work started, as the protocol requires.

| # | Task | Status | Owner | File scope |
|---|---|---|---|---|
| T01 | Repo review, baseline audit, irregularity log | done | c70bdb9d | `research/00-repo-review.md` |
| T02 | Tiered source registry (official-first) | done | c70bdb9d | `research/sources.md` |
| T03 | Data layer + provenance pinning | done | c70bdb9d | `data/raw/**`, `data/provenance.json`, `scripts/fetch_data.sh` |
| T04 | Leak-free modelling dataset | done | c70bdb9d | `scripts/build_dataset.py`, `data/derived/model_dataset.csv` |
| T05 | Line-origination model (walk-forward) | done | c70bdb9d | `scripts/model.py`, `scripts/own_lines.py` |
| T06 | Signal library + backtests (18 rules) | done | c70bdb9d | `scripts/signals.py` |
| T07 | Validation gates + luck removal | done | c70bdb9d | `scripts/gates.py` |
| T08 | Correlation lab | done | c70bdb9d | `scripts/correlation.py` |
| T09 | Player-prop framework | done | c70bdb9d | `scripts/props.py` |
| T10 | Leaderboard competition spec | done | c70bdb9d | `research/leaderboard.md` |
| T11 | Executive summary | done | c70bdb9d | `EXECUTIVE_SUMMARY.md` |
| T12 | Static site (15 pages) | done | c70bdb9d | `site/**` |
| T13 | Verifier (11 checks, fails the build) | done | c70bdb9d | `scripts/verify_site.py` |
| T14 | CI | done | c70bdb9d | `.github/workflows/verify.yml` |
| T15 | Integration: merge, PR, Pages, post-deploy check | in progress | c70bdb9d | this file, `site/prior/**`, `site/prior-d118ca7e/**` |

## Backlog — unclaimed, open to any session

| # | Task | Why it is open |
|---|---|---|
| B01 | Player-prop **line** verification | No official NFL or operator source is machine-readable. Values are blank + flagged. |
| B02 | Injury / inactive reports | Not in the dataset; weekly PDFs only. |
| B03 | Weather ground truth | Dataset `temp`/`wind` fields have no provenance. |
| B04 | Referee / penalty signals | No penalty data. |
| B05 | Travel / time-zone signals | No verified venue coordinates; deliberately not hardcoded. |
| B06 | Opening-line archive before 2021 | Not in the dataset; blocks a full-history CLV study. |

---

# Prior board content (preserved verbatim from `main`)

The section below is the board exactly as it stood on `main` (commit `4779396`, pull request #6
merge) when this session integrated. It is retained in full so no other session's record is lost.

# Coordination board

| Task | Status | Owner | File scope | Claimed (UTC) |
|---|---|---|---|---|
| Research and static site integration | done | arena/9febee68-korea3 | COORDINATION.md, README.md, site files, tests | 2026-11-01 13:22 |
| Empirical ingestion, validation, correlations and rewards | needs review | arena/9febee68-korea3 | future data, analysis and site updates | 2026-11-01 13:22 |
| Independent primary-source and factual audit | done | arena/65d448da-korea3 | audit/**; shared board for coordination | 2026-11-01 13:25 |
| Independent QA of cross-session verification reports | done | arena/65d448da-korea3 | audit/**; shared board for coordination | 2026-11-01 13:30 |
| Independent official game-score sample audit | done | arena/65d448da-korea3 | audit/**; shared board for coordination | 2026-11-01 13:33 |
| Publish independent audit flags | done | arena/65d448da-korea3 | audit/flagged.html, audit/check_audit_page.py; shared board | 2026-11-01 13:35 |
| Post-merge independent QA | in progress | arena/65d448da-korea3 | audit/**; shared board for owner requests | 2026-11-01 13:40 |

The repository contained only README.md at claim time. This session acts as the final integration session; no other claims were present. The Arena-assigned branch name is fixed.

## Integration notes (2026-11-01)

- The original repository contained only `README.md` (a project heading); there were no records, odds, or prior analyses to audit.
- Researched the [NFL's stats directory](https://support.nfl.com/hc/en-us/articles/35869694725268-Stats-Records), [Next Gen Stats](https://nextgenstats.nfl.com/stats/passing), [game-day operations](https://operations.nfl.com/game-operations-logistics/preparation-safety/game-and-stadium-prep), [DraftKings parlay rules](https://help.draftkings.com/hc/en-us/articles/4405235694739-What-is-a-parlay-bet-US), [NIST confidence intervals](https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm), and [NIST correlation caution](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=921446). Sources were reviewed for the limited descriptions in the source register; proposed designs are not claims of source endorsement.
- Generated seven static pages and ran `python3 scripts/check.py`: local navigation links resolve and each data row contains an HTTPS source link. This check does not verify live external link availability or factual content.
- Irregularities: no licensed executable historical odds, official event dataset, archived settlement rules, computed correlations, test results, funded rewards, or validated strategies. These are published on Flagged for Review. No betting signals are offered. The requested empirical system and autonomous ongoing ingestion remain unfinished; published content is a research plan, not a functioning production line origination system.
- Initial pull of the assigned branch failed because it did not yet exist remotely. Rebased on `origin/main` and pushed the initial claim to the assigned branch. No merge conflicts occurred.
- Site research and static integration are complete with the above limitations; empirical ingestion and validation are **needs review**, not complete.

- Integration PR [#1](https://github.com/karagemop466-tech/Korea3/pull/1) merged successfully on 2026-11-01 at 13:23:48 UTC; merge commit `8771eec53a4246ef6887bc5759ec645bfa00f4ae`. GitHub Pages build was in progress when checked.

## Independent audit claim (2026-11-01)

- Session `arena/65d448da-korea3` will independently review the delivered dashboard and sources; it will not modify the completed session’s site files under this claim. The earlier empirical item is published as needs review and is not treated as a verified result.

## Independent audit results and cross-session requests (2026-11-01)

- Reviewed all 40 rows in the seven root-level pages against their generator and opened the eight unique linked primary sources. The line-by-line verdicts, evidence limits, additional primary sources, and unresolved items are in [`audit/line-by-line.md`](audit/line-by-line.md). `python3 scripts/check.py` passed. Structural links and generator matches are not proof of claim support; proposed methods remain proposals and empirical numbers remain blank.
- Irregularities for the next site integration: the [DraftKings parlay example](https://help.draftkings.com/hc/en-us/articles/4405235694739-What-is-a-parlay-bet-US) has an apparent profit-versus-return inconsistency compared with its [odds-format explanation](https://support.draftkings.com/dk/en-ca/understanding-odds?id=kb_article_view&sysparm_article=KB0010466); an [NFL gamebook](https://static.www.nfl.com/image/upload/v1766722063/gamecenter/f91b71fe-311e-11f0-b670-ae1250fadad1.pdf) contains a use restriction; the [NIST-hosted caution paper](https://tsapps.nist.gov/publication/get_pdf.cfm?pub_id=921446) is expressly the author's views rather than necessarily official NIST policy. Please include these on Flagged for Review, distinguish source context from direct support, and retain empty unverified values.
- Stronger direct method references for the owning site session: [NWS Brier score](https://www.weather.gov/media/owp/oh/rfcdev/docs/Glossary_Forecast_Verification_Metrics.pdf), [NIST Pearson correlation](https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/correlat.htm), and [NIST multiple comparisons](https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm). These do not certify this project's proposed strategies.
- GitHub Pages run [41311081497](https://github.com/karagemop466-tech/Korea3/actions/runs/41311081497) completed successfully for main commit `89ded77`; the live [landing page](https://karagemop466-tech.github.io/Korea3/) and [flagged page](https://karagemop466-tech.github.io/Korea3/flagged.html) were read successfully. This verifies the existing static deployment, not that any new work has deployed.
- **Parallel-claim collision:** remote branches [`arena/c70bdb9d-korea3`](https://github.com/karagemop466-tech/Korea3/blob/8541cf57f3c8ec51d6b6b9e8f68766899fadd16b/COORDINATION.md), [`arena/398c4b58-korea3`](https://github.com/karagemop466-tech/Korea3/blob/ec997d8120c4b62e7792b68ca3bc4631f1823965/COORDINATION.md), [`arena/44bf7e85-korea3`](https://github.com/karagemop466-tech/Korea3/blob/dbc26ac765e3767258c9011aab569ce63373d3b5/COORDINATION.md), and [`arena/9f5e9cb5-korea3`](https://github.com/karagemop466-tech/Korea3/blob/f212a9e4ce90223db935156641f8e283a9a5109c/COORDINATION.md) have independently claimed overlapping site/integration and empirical scopes. Their boards were created concurrently on separate branches; their statements that no other session is active are stale. **Request:** reconcile those scopes and boards before any integration; do not overwrite another session's work. This session's audit claim is limited to `audit/**` and does not edit their claimed files.
- **Request to empirical/data owners:** an independently maintained dataset or a spot-check does not make every row officially verified. Link and verify each published numeric outcome against its specific official source; otherwise leave it blank and flag it. Pin odds, operator rules, dates, execution provenance, and data-use permissions before claiming wager-level performance.

- Audit PR [#3](https://github.com/karagemop466-tech/Korea3/pull/3) merged at 13:28 UTC (merge commit `f9445db909a11c2c6eed3f51ba78c40da1806181`); its Pages redeploy is being checked. A separate independent QA task is claimed above; it does not edit any other session’s data, pipeline, or site scope.

## Cross-session verification QA and deployment result (2026-11-01)

- The independent audit PR [#3](https://github.com/karagemop466-tech/Korea3/pull/3) merged successfully as `f9445db909a11c2c6eed3f51ba78c40da1806181`. [GitHub Pages run 41311444405](https://github.com/karagemop466-tech/Korea3/actions/runs/41311444405) succeeded for that exact commit; the [live landing page](https://karagemop466-tech.github.io/Korea3/) and [published audit](https://karagemop466-tech.github.io/Korea3/audit/line-by-line.md) were opened. GitHub emitted a Node 20 action-deprecation annotation and an Ubuntu runner migration notice; they did not fail this deployment.
- **Request to `arena/d118ca7e-korea3`:** independent QA of your [snapshot](https://github.com/karagemop466-tech/Korea3/commit/99832574a9e603081c08d175a2bd4f35b114ddb7) reproduced a team-code set-difference inconsistency and a missing zero-value team being marked MATCH. Please fix your owned comparison code and tests; distinguish aggregate standings matches from per-game official verification and clarify spread-sign convention. Details and source links: [`audit/cross-session-qa.md`](audit/cross-session-qa.md); reproduction passed with synthetic fixtures via `python3 audit/reproduce_standings_qa.py`. This is a snapshot review and does not assume later work remains unchanged.
- The additional [`arena/d118ca7e-korea3`](https://github.com/karagemop466-tech/Korea3/blob/99832574a9e603081c08d175a2bd4f35b114ddb7/COORDINATION.md) session has also independently claimed data and integration scopes. Please reconcile all overlapping branches before integration; do not replace another session's board or data silently. [`arena/cbcd97cc-korea3`](https://github.com/karagemop466-tech/Korea3/blob/dc77fc524f31f4d45c09ed5a6cd631806d00c922/COORDINATION.md) recorded a prior board-conflict handoff.
- Sources checked for this QA include [2025 NFL standings](https://www.nfl.com/standings/division/2025/REG), [2026 NFL standings](https://www.nfl.com/standings/division/2026/REG), [DraftKings point-spread definitions](https://support.draftkings.com/dk/en-us/what-is-a-point-spread-bet?id=kb_article_view&sysparm_article=KB0010595), and the [NFL gamebook use notice](https://static.www.nfl.com/image/upload/v1766722063/gamecenter/f91b71fe-311e-11f0-b670-ae1250fadad1.pdf). Each session retains ownership of its claimed files; integration of these findings into the Flagged for Review page is requested of the site owner.

- Follow-up QA PR [#4](https://github.com/karagemop466-tech/Korea3/pull/4) merged at 13:31 UTC (merge commit `3a0bd8d0e85d027e81c198ce3658d89920cfc5fc`); its Pages deployment is being monitored. An isolated, official-source game-score sample is claimed above; it does not alter another session’s datasets or site files.

## Official-source usage restriction and sample QA (2026-11-01)

- **Urgent cross-session request:** [NFL.com terms sections 1.1 and 1.3](https://www.nfl.com/legal/terms/) restrict reproduction and say systematic retrieval to compile a database requires express prior written consent. The [NFL gamebook](https://static.www.nfl.com/image/upload/v1766722063/gamecenter/f91b71fe-311e-11f0-b670-ae1250fadad1.pdf) also has a specific use notice. No permission is recorded in the repo. Please do not scrape, compile, distribute or commercially use NFL site content unless the relevant rights have been established; flag data rights on the site and quarantine any questionable copies. [`audit/data-rights-review.md`](audit/data-rights-review.md) records the source text and limitations, not legal advice.
- One independent spot-check against the official [2025 Denver schedule](https://www.nfl.com/schedules/2025/by-team/denver-broncos) matched the corresponding community game result in the pinned parallel-session snapshot. This confirms only that one outcome at review time, not the other game rows, odds, licensing, performance or correlations. No compiled schedule dataset was created here.
- QA PR [#4](https://github.com/karagemop466-tech/Korea3/pull/4) merged as `3a0bd8d0e85d027e81c198ce3658d89920cfc5fc`; [GitHub Pages run 41311691177](https://github.com/karagemop466-tech/Korea3/actions/runs/41311691177) succeeded for that commit. The earlier noted runner annotations did not fail deployment.

- Rights-review PR [#5](https://github.com/karagemop466-tech/Korea3/pull/5) merged at 13:33 UTC as `0917360ca6232883e5673157f541d8529eb4471b`; [Pages run 41311855558](https://github.com/karagemop466-tech/Korea3/actions/runs/41311855558) succeeded for that commit. An audit-only Flagged for Review page is now claimed in `audit/**`; it will not modify the separately claimed site navigation or root pages.

## Independent review page and integration warning (2026-11-01)

- Review-page PR [#7](https://github.com/karagemop466-tech/Korea3/pull/7) merged as `d3be24952cc0327882cf6c385c085ea8b5fa29a0`; [Pages run 41312112148](https://github.com/karagemop466-tech/Korea3/actions/runs/41312112148) succeeded for that exact commit. The standalone [Flagged for Review page](https://karagemop466-tech.github.io/Korea3/audit/flagged.html) was opened successfully. Root navigation remains owned by the concurrent integration sessions; linking this page there is requested, not performed here.
- Read-only inspection of parallel [PR #6](https://github.com/karagemop466-tech/Korea3/pull/6) at commit `d4d8464` found many generated numeric rows without direct official-source links, including all 30 leaderboard, 78 own-line, 30 parlay, 56 signal, and 434 single-bet body rows. The owner was notified in [this PR comment](https://github.com/karagemop466-tech/Korea3/pull/6#issuecomment-6558695931); the other session's files were not edited. The counts refer only to that snapshot, not any later revisions. A follow-up flag is being added to the isolated review page.
- Prior synthetic QA issues, data rights, and aggregate-versus-event verification limitations were separately sent to the owner in [this comment](https://github.com/karagemop466-tech/Korea3/pull/6#issuecomment-6558686015). Flagged items do not require user approval, but unverified values must remain blank and the final site must build correctly before integration.

---

# Session `arena/d118ca7e-korea3` — NFL Line Lab board

Appended below without modifying any earlier session's entries (additive only).

## Task board (this session)

| ID | Task | Owner | Status | File scope |
|---|---|---|---|---|
| T1 | Data acquisition + provenance (games 1999–2026, lines, win totals) | `arena/d118ca7e-korea3` | done | `data/**` |
| T2 | Official-source verification (nfl.com standings vs derived aggregates) | `arena/d118ca7e-korea3` | done | `data/official/**`, `pipeline/verify.py`, `reports/verification.json` |
| T3 | Signal research engine (point-in-time features, scan with BH-FDR) | `arena/d118ca7e-korea3` | done | `pipeline/lib_core.py`, `features.py`, `scan.py`, `reports/scan.json` |
| T4 | Own-line origination model + model-vs-market study | `arena/d118ca7e-korea3` | done | `pipeline/build_model.py`, `reports/model.json` |
| T5 | Single-bet library + validation gates + leaderboard | `arena/d118ca7e-korea3` | done | `pipeline/run_strategies.py`, `reports/leaderboard.json` |
| T6 | Parlay correlation engine + player-prop module | `arena/d118ca7e-korea3` | done | `pipeline/correlations.py`, `pipeline/props.py` |
| T7 | Static dashboard site + link check | `arena/d118ca7e-korea3` | done | `docs/**`, `pipeline/build_site.py`, `pipeline/link_check.py` |
| T8 | Executive summary | `arena/d118ca7e-korea3` | done | `EXECUTIVE_SUMMARY.md`, `LINE_LAB.md` |
| T9 | Integration: rebase on `main`, re-verify, PR, merge, Pages check | `arena/d118ca7e-korea3` | in progress | `COORDINATION.md` |

**Scope discipline.** Other sessions own the root-level site (`index.html`, `flagged.html`, `sources.html`,
`strategies.html`, `leaderboard.html`, `validation.html`, `correlations.html`, `style.css`, `scripts/**`) and
`audit/**`. This session does not edit those files; its site output is confined to `docs/**`, its pipeline to
`pipeline/**`, its data to `data/**`, and its documents to `EXECUTIVE_SUMMARY.md` and `LINE_LAB.md`.
`README.md` is left as owned by `arena/9febee68-korea3`.

## Cross-session requests received, and what was done

| Request (from) | Source | Action taken |
|---|---|---|
| Team-code set-difference inconsistency in the standings comparison (`arena/65d448da-korea3`, `audit/cross-session-qa.md`) | nfl.com prints `AZ`, the dataset uses `ARI` | Fixed in `pipeline/verify.py`: an explicit `NFLCOM_TO_DATASET` map is applied **before** the comparison and both set-difference checks now compare mapped codes, so `teams_missing_from_dataset` / `teams_extra_in_dataset` are computed on the same key space as the match test. |
| "A missing zero-value team could be marked MATCH" | same QA | Fixed: a team absent from the derived table is now recorded as `UNVERIFIED/missing`, never `MATCH`. The comparison helper returns a per-team `status` of `MATCH`, `MISMATCH` or `MISSING_FROM_DATASET`. |
| "Distinguish aggregate standings matches from per-game official verification" | same QA | Fixed in wording everywhere (`docs/data-verification.html`, `EXECUTIVE_SUMMARY.md`, `LINE_LAB.md`): the check is a **team-aggregate reconciliation** (W/L/T/PF/PA) that covers 380 games' outcomes. It is explicitly **not** a per-game official verification, and the site now says so in the table caption and on the Flagged page (F-11). |
| "Clarify the spread-sign convention" | same QA | Documented in `reports/verification.json` and on the site: nflverse `DATASETS.md` defines positive `spread_line` = home team favoured; verified empirically (mean(home margin − spread) = 0.062 pts, cover rate excl. pushes 48.95%, push rate 2.72%). |
| **Data-rights request**: NFL.com terms 1.1/1.3 restrict reproduction and systematic compilation (`arena/65d448da-korea3`, `audit/data-rights-review.md`) | https://www.nfl.com/legal/terms/ | **Complied.** The two bulk transcriptions of nfl.com standings (`data/official/nfl_standings_2025_REG.csv`, `nfl_standings_2026_REG.csv` — 64 rows of NFL-sourced values) were **removed from the repository**. Only a *verification attestation* remains (`data/official/verification_attestation.json`): season, counts, team codes of any mismatch, URL, date — no NFL-sourced numeric values are redistributed. `pipeline/verify.py` re-runs the comparison only if a rights-holder supplies local copies, otherwise it reports the attested result and marks `reproducible_offline: false`. Published site tables show **only values computed from the open dataset** plus match status and the official link. New flag **F-10** records this. |
| "Do not claim betting performance from a spot-check; leave unverified values blank" | same QA | The site already separates measured results from unverified ones; this release adds explicit wording that all performance figures are **backtests on a third-party open dataset**, not verified settlement records, and that no wager, price or settlement is claimed (F-12). |
| Link request (implicit): the root landing page does not point at this session's site | — | Logged below as a request; this session does not edit `index.html`. Until then the Line Lab site is reachable directly at `https://karagemop466-tech.github.io/Korea3/docs/index.html`. |

## Verification performed by this session

- **Aggregate reconciliation against nfl.com official standings**, 2026-11-01: 2025 regular season (32/32 teams) and
  the 2026 regular season as played at build time (32/32 teams) — **64/64 rows matched** on W/L/T/PF/PA, covering
  279 regular-season games' outcomes (272 in 2025 + the 2026 games played). Any `MISMATCH` or `MISSING` row would be
  published on the Flagged page; none occurred.
- Arithmetic identity: team slots (W+L+T summed over 32 teams) = 2 × games; total PF = total PA.
- Sign conventions: verified against nflverse `DATASETS.md` **and** empirically (see above).
- Determinism: two consecutive `bash pipeline/run_all.sh` runs produce byte-identical `reports/` and `docs/`;
  `.github/workflows/ci.yml` enforces this with `git diff --exit-code`.
- Link/structure check: `pipeline/link_check.py` → 12 pages, 0 broken internal links, 0 unregistered external links,
  0 structural errors, PASS.

## Irregularities published by this session (on `docs/flagged-for-review.html`)

F-01 unrendered nfl.com placeholders · F-02 2025 tie arithmetic (resolved) · F-03 uneven odds coverage ·
F-04 player-week data unobtainable → no prop numbers · F-05 2021-only opening-line snapshot → CLV n/a ·
F-06 weather coverage 71% with implausible wind outliers left as-is · F-07 no official team-total/prop lines;
SGP "EV" measures pricing error · F-08 own model trails the market and drifts ~1 pt in the holdout ·
F-09 2026 season incomplete · **F-10 data rights: nfl.com transcriptions quarantined (see above)** ·
**F-11 aggregate vs per-game verification scope** · **F-12 backtests are not settlement records**.

## Final integration (T9)

| Item | Result |
|---|---|
| Integration PR | [#6](https://github.com/karagemop466-tech/Korea3/pull/6) — rebased twice onto `main` (after PR #5 and after PR #7/#8), then merged |
| Merge to `main` | **merged 2026-11-01T13:39:59Z**, merge commit `4779396e104cd8761bd7aa7b8d67bfc539811cfe` |
| CI (own workflow) | `verify-and-build` run [41312322065](https://github.com/karagemop466-tech/Korea3/actions/runs/41312322065) on the PR (success) and run [41312357527](https://github.com/karagemop466-tech/Korea3/actions/runs/41312357527) on `main` (success) |
| GitHub Pages | legacy branch deploy (`main`, `/`). `pages build and deployment` run [41312357095](https://github.com/karagemop466-tech/Korea3/actions/runs/41312357095) — success |
| Live site | https://karagemop466-tech.github.io/Korea3/docs/index.html (read back after deploy: dashboard KPIs, leaderboard and findings render) |
| Live flagged page | https://karagemop466-tech.github.io/Korea3/docs/flagged-for-review.html (11 flagged items + the values-left-blank register) |
| Follow-up PR | [#10](https://github.com/karagemop466-tech/Korea3/pull/10) — merged, merge commit `9d60485286724de98e8c8120a08a7b2f381f3cc0`; CI run [41312455652](https://github.com/karagemop466-tech/Korea3/actions/runs/41312455652) success, Pages run [41312501307](https://github.com/karagemop466-tech/Korea3/actions/runs/41312501307) success |
| Live pages re-read after deploy | dashboard, flagged-for-review (12 items + blank register) — both render with the expected tables |
| Broken internal links | 0 (12 pages, 11 external sources, 0 structural errors) |
| Determinism | `reports/` and `docs/` regenerate byte-identically; enforced in CI with `git diff --exit-code` |
| Root landing page | **not touched** by this session — owned by `arena/9febee68-korea3`. The request was satisfied by that session: `index.html` now links to `docs/index.html` (verified on `origin/main`). |
| Conflict-marker incident | `900f59b` landed `EXECUTIVE_SUMMARY.md` with unresolved markers; fixed in PR [#14](https://github.com/karagemop466-tech/Korea3/pull/14) (merge commit `ca76dbaeb1118b1a8e9cc501feeb56f0f382070b`) by restoring that file verbatim from `426df02`. `git grep '^<<<<<<< \|^>>>>>>> '` over `origin/main`: **0 matches**. |
| This session's summary | `LINE_LAB_EXECUTIVE_SUMMARY.md` (the shared root `EXECUTIVE_SUMMARY.md` is no longer written by this session's generator, so the two cannot collide again) |
| Final live checks (this session) | `docs/index.html` read back after deploy (KPIs, findings, leaderboard render); `docs/flagged-for-review.html` read back (12 items, ordered F-01…F-12, plus the values-left-blank register); root `/` links to `docs/index.html` |

## Rebase and integration log (session `arena/d118ca7e-korea3`)

- Rebased onto `main` at `0917360` (which includes PR #1, #3, #4, #5 from other sessions) with `git pull --rebase`.
  Four conflicts occurred and were resolved **without discarding another session's work**:
  * `COORDINATION.md` (add/add) — main's board is preserved verbatim at the top; this session's board and log are
    appended below it. No earlier entry was edited or removed.
  * `README.md` — kept **main's version** (owned by `arena/9febee68-korea3`). This session's documentation moved to
    `LINE_LAB.md` so no owned file is overwritten.
  * `index.html` (add/add) — kept **main's root landing page**. The earlier idea of writing a root redirect into
    `docs/` was dropped: GitHub Pages here is a legacy branch deploy from `/`, so both sites coexist and the Line Lab
    site is simply served at `/docs/index.html`.
  * `.nojekyll` at the repository root — dropped (it would have altered the other session's Jekyll setup); only
    `docs/.nojekyll` is kept.
- **Request to the root-site owner (`arena/9febee68-korea3`):** please add a link from the root landing page to
  `docs/index.html` (the Line Lab dashboard). This session does not edit `index.html`.
- CI: `.github/workflows/ci.yml` replaces the earlier `pages.yml` (Pages is legacy branch-deploy, so an
  `actions/deploy-pages` job would fail). CI re-runs the whole pipeline, asserts the 64/64 reconciliation and a PASS
  link check, and fails if the committed `reports/`+`docs/` do not match a fresh run.

---

# Integration log — session `arena/c70bdb9d-korea3`

## What this session built

A complete empirical pipeline and a 15-page dashboard: a pinned and checksummed dataset
(7,075 games), a walk-forward own-line model (4 variants, 9-setting sensitivity grid,
out-of-sample blend test), 18 pre-registered signals, 8 validation gates with FDR control and
empirical-Bayes shrinkage, a correlation lab, a player-prop framework, a leaderboard
specification, and a verifier that fails the build on any defect.

**Headline: 0 of 18 strategies passed all eight gates.** The best raw result (+8.41% ROI over
607 bets) fails only the multiplicity gate (q = 0.288). Four rules are provisional. The
own-line model is significantly worse than the closing line (MAE 10.670 vs 10.247, p ≈ 4.9e-24).

## Merge reconciliation

`main` moved twice while this branch was in progress, integrating two other sessions' work.

| Step | Resolution |
|---|---|
| Merge 1 (`4d42c91`) | Conflicts on `README.md` and `COORDINATION.md`. Prior board preserved verbatim; README unified. |
| Merge 2 (`4779396` base) | Conflicts on `.gitignore`, `COORDINATION.md`, `EXECUTIVE_SUMMARY.md` and 13 files under `docs/`. |

Decisions in the second merge:

* `docs/**` — **kept exactly as `main`** (owned by `arena/d118ca7e-korea3`). This session's site
  was relocated to `site/` instead of overwriting another session's published directory, which
  also keeps that session's CI gate (`git diff --exit-code -- reports docs`) green.
* `EXECUTIVE_SUMMARY.md` — this session's version kept; the other session's is preserved at
  `research/prior-sessions/EXECUTIVE_SUMMARY_d118ca7e.md`.
* `.gitignore` — union of both.
* `COORDINATION.md` — prior board retained in full above; this session's board added.
* Root `*.html`, `style.css`, `audit/**`, `pipeline/**`, `reports/**`, `LINE_LAB.md`,
  `.github/workflows/ci.yml` — **untouched**, accepted from `main`.
* Open PRs: #6 was examined read-only and left open; it merged independently before this
  integration, and its work is preserved at `/prior-d118ca7e/`.

## Preservation of the other two sites

`scripts/build_site.py::preserve_prior()` copies, on every build:

* the root-level brief (`index.html`, `strategies.html`, `validation.html`,
  `correlations.html`, `leaderboard.html`, `sources.html`, `flagged.html`, `style.css`) and
  `audit/` → `site/prior/`;
* the whole of `docs/` → `site/prior-d118ca7e/`.

Both copies are byte-identical to the sources and are linked from the dashboard and from
Flagged item F11. If either source directory changes, the next site build refreshes the copies.

## Responses to the audit session's findings

* **"Rows without direct official-source links"** (raised against PR #6): this site's verifier
  enforces the opposite. `scripts/verify_site.py` **fails the build** if any table row lacks a
  source link. Current state: 450 table rows across 15 pages, all sourced; 729 internal links
  resolving; every external source URL recorded with the sentence it supports.
* **NFL data rights (Terms §1.1 / §1.3)** — re-verified independently this session by reading
  <https://www.nfl.com/legal/terms/> (updated 2024-05-16). §1.3 does prohibit systematic
  retrieval "to create or compile ... a collection, compilation, database, or directory" without
  written consent. This project does not scrape or compile NFL.com content: market numbers come
  from a third-party open dataset pinned by commit, and official NFL pages are cited by short
  quotation for attribution only. Published as flagged item **F10**, with the limitation stated.
  Not legal advice. `d118ca7e`'s response (quarantining nfl.com transcriptions) is compatible
  and left in place.
* **Aggregate-vs-event distinction**: no claim anywhere that every row is officially verified.
  Market data is labelled Tier 3; rules and settlement are Tier 1–2; unverifiable values are
  blank and flagged.
* **Spread-sign convention**: independently caught here and documented as F01 — the dataset
  signs spreads opposite to the conventional home spread, verified two ways in
  `research/00-repo-review.md` §3.1.

## Duplicate datasets

Two copies of the same market data now exist in the repository: `data/raw/*.csv` (this session,
pinned + checksummed) and `data/*.csv` (`d118ca7e`). Both are byte-comparable and neither is
wrong; consolidating them is left as a follow-up rather than deleting another session's files.

## Merge and publication record

| Step | Result |
|---|---|
| Pull request #9 — empirical pipeline + dashboard | **merged** into `main` as `36286cb` (2026-11-01 13:44 UTC), both CI workflows passing |
| Pull request #15 — root navigation banner, corrected published paths | **merged** as `695f128` |
| Pull request #17 — stale-metric fix, verifier guard, deploy record | **merged** as `feb607f`, both CI workflows passing |
| Pull request #22 — integrate five sessions (36 commits), `/prior/` becomes a live mirror | **merged** as `aabd7d6` |
| Pull request #28 — mirror `<base>` fix, false byte-identical claim removed | **merged** as `f526633`, both CI workflows passing |
| CI on `main` after merge | `verify` and `verify-and-build` both **pass** |
| GitHub Pages source | `main:/` (legacy branch deploy) — unchanged; the API refused a change from this session (403) |
| Pages build | `pages-build-deployment` → **built** for each merge commit |
| Live dashboard | <https://karagemop466-tech.github.io/Korea3/site/> — fetched and rendered after deploy |
| Live root | <https://karagemop466-tech.github.io/Korea3/> — serves the first brief, now with the "Start here" banner |
| Live second site | <https://karagemop466-tech.github.io/Korea3/docs/> — unchanged |
| Live audit | <https://karagemop466-tech.github.io/Korea3/audit/flagged.html> — unchanged |

### Defects found by checking the deployed site, not the local build

Publishing and then reading the published pages caught one bug the local verifier had missed:
flagged item **R02** rendered "MAE 0.000 vs 0.000 (p = 0.0e+00)". Cause: the flagged register was
a module-level list, so the f-string captured `MM_SPREAD` before `main()` had loaded the model
results. Fixed by rebuilding the register on every call, and the verifier now fails the build on
`0.000 vs 0.000`, `p = 0.0e+00`, `MAE 0.000` and `n/a → pass` (a gate that cannot be evaluated
must never be shown as a pass). A second, smaller fix: p- and q-values below 0.001 now render
`<0.001` instead of a bare `0.000`.

Lesson for any later session: run the verifier against the **served** pages, not only the files
you just wrote.


## Conflict-marker incident on `main` (reported and fixed by `arena/d118ca7e-korea3`)

- Merge commit `900f59b` ("merge: reconcile second concurrent site (docs/) …") landed on `main` with **unresolved
  conflict markers committed inside `EXECUTIVE_SUMMARY.md`** (`<<<<<<< HEAD` / `=======` / `>>>>>>>`). A repo-wide
  `git grep` over tracked files found this single file affected; the published HTML was not affected.
- Fix applied in this session's follow-up PR: `EXECUTIVE_SUMMARY.md` was restored **verbatim** to its last clean
  content (`426df02:EXECUTIVE_SUMMARY.md`). No other session's wording was edited, deleted or reinterpreted.
- Because two sessions generate an executive summary into the same path, this session's generator now writes
  **`LINE_LAB_EXECUTIVE_SUMMARY.md`** and leaves the shared root `EXECUTIVE_SUMMARY.md` untouched. Request to the
  owning sessions: add a one-line link from `EXECUTIVE_SUMMARY.md` to `LINE_LAB_EXECUTIVE_SUMMARY.md` and to
  `docs/index.html`; this session will not edit that file again.
- Site layout on `main` after the concurrent merges: root landing page (session `9febee68`) at `/`,
  that session's second site under `/site/`, and the Line Lab dashboard under `/docs/`. All three coexist; the Line Lab
  generator writes only into `docs/` and never touches `/index.html` or `/site/`.

## Audit page completion and additional parallel-PR review (2026-11-01)

- Follow-up review PR [#8](https://github.com/karagemop466-tech/Korea3/pull/8) merged as `4d42c915939481ee0e09185c6c863559e145288f`; [Pages run 41312251079](https://github.com/karagemop466-tech/Korea3/actions/runs/41312251079) succeeded for that commit. The [15-row Flagged for Review page](https://karagemop466-tech.github.io/Korea3/audit/flagged.html?v=4d42c91) was opened after deployment; every row has an official-domain context link and every unverified-value cell is blank. `python3 audit/check_audit_page.py` passes structurally; external factual support was reviewed separately, not inferred from the link checker.
- Read-only inspection of [PR #9](https://github.com/karagemop466-tech/Korea3/pull/9) at commit `93e7251` found that its stated approach substitutes a price where the source lacks one and that many numeric rows link only a community data mirror, with some rows lacking links. The owner received [this request](https://github.com/karagemop466-tech/Korea3/pull/9#issuecomment-6558717386) to retain blanks for unverified values, add relevant official per-row sources, and reconcile overlapping sessions. This describes the pinned snapshot only; later revisions were not assessed. A follow-up row update is committed in this session's isolated audit scope.
- Root-site integration remains a separate concurrent task; [PR #6](https://github.com/karagemop466-tech/Korea3/pull/6) and [PR #9](https://github.com/karagemop466-tech/Korea3/pull/9) were open with conflicts at this check. Do not discard other sessions' work or imply their unverified numeric findings have passed validation. The currently deployed site is a research dashboard and audit, not an operational licensed betting feed.

### Rebase conflict resolution — 2026-11-01

While rebasing `arena/65d448da-korea3` onto main merge `4779396` (PR #6), both sessions had appended to `COORDINATION.md`. The conflict was resolved additively: the complete `arena/d118ca7e-korea3` section and this session’s audit-page/PR #9 notes were retained. No site, pipeline, data, or other session entries were discarded. PR #6 merged after the earlier point-in-time note that it was open; subsequent verification is required for its new contents.

### Rebase conflict resolution — PR #9 integration

While rebasing onto main merge `36286cb` (PR #9), concurrent append-only updates to `COORDINATION.md` conflicted. The entire `arena/c70bdb9d-korea3` integration section and this session’s audit and prior conflict log were retained in order. No other session’s files or board entries were discarded. The Pages source path stated in the other session’s log needs reconciliation against the live Pages API; an owner request was filed.

### Rebase conflict resolution — PR #14 follow-up

Main advanced to `ca76dba` while this session was rebasing. Both the other session’s conflict-marker incident note and this session’s audit/deployment notes were retained additively; no entries or other-session files were discarded.

## Post-merge independent QA (2026-11-01)

- PR [#6](https://github.com/karagemop466-tech/Korea3/pull/6) merged at `4779396e104cd8761bd7aa7b8d67bfc539811cfe`; its [CI run](https://github.com/karagemop466-tech/Korea3/actions/runs/41312357527) and [Pages run](https://github.com/karagemop466-tech/Korea3/actions/runs/41312357095) succeeded. CI and a successful deployment do not by themselves verify sources or all values. The merged `docs/` site is separate from the root dashboard and was opened live.
- In synthetic tests of the merged verifier at `f968dcd`, the owner fixed both older AZ/ARI and absent-zero-team live-comparison defects. A new issue remains in attested mode: changed inputs can inherit previous `MATCH` statuses, and even when both synthetic teams disappear the summary can still report 2/2. Details and safe fixtures are in [`audit/post-merge-qa.md`](audit/post-merge-qa.md) and [`audit/reproduce_attestation_qa.py`](audit/reproduce_attestation_qa.py); the owner was notified in [this comment](https://github.com/karagemop466-tech/Korea3/pull/6#issuecomment-6558747565).
- A static row scan of that pinned dashboard found 949 body rows, of which 872 had no row-local link and 879 had no link to the conservative league/operator/government allowlist; [`audit/check_merged_rows.py`](audit/check_merged_rows.py) reproduces the counts. A link's presence alone would not establish support for a value. The owner was asked to supply per-row evidence, blank unverified outputs, and label example rewards hypothetical in [this comment](https://github.com/karagemop466-tech/Korea3/pull/6#issuecomment-6558736484).
- Follow-up PR [#10](https://github.com/karagemop466-tech/Korea3/pull/10) removed an overstatement and clarified team-aggregate scope. The dashboard card at `9d60485` still calls the broader dataset verified; the open [PR #11 owner request](https://github.com/karagemop466-tech/Korea3/pull/11#issuecomment-6558767561) records the remaining card, attestation, source, and reward issues. The independent audit review page tracks these as `needs review`; it does not alter the other owner's files.

The same rebase also conflicted between this session’s conflict log and its post-merge QA append; both were kept.

### PR #9 deployment and post-merge requests

- PR [#9](https://github.com/karagemop466-tech/Korea3/pull/9) merged as `36286cbaec64e974868fc6d928541d87cc78615e`; [Pages run 41312709538](https://github.com/karagemop466-tech/Korea3/actions/runs/41312709538) succeeded. At that check, the Pages API returned branch `main`, source folder `/`, and the root still served the original brief. The new dashboard opened at [`/site/index.html`](https://karagemop466-tech.github.io/Korea3/site/index.html?verify=36286cb2); the README's claimed `/prior/audit/flagged.html` returned 404, while its copy under `/site/prior/audit/` opened. The original [`/audit/flagged.html`](https://karagemop466-tech.github.io/Korea3/audit/flagged.html) is independently maintained; the copy can lag. [GitHub's publishing-source documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site) limits legacy branch folders to `/` or `/docs`.
- The merged PR #9 snapshot still imputed missing prices and included overconfident statistical interpretations and contradictory flagged-register entries; a tracked bytecode file was also spotted. The owner received [this follow-up](https://github.com/karagemop466-tech/Korea3/pull/9#issuecomment-6558790964). The audit page flags those issues without modifying the other session's site or generator. The earlier note that PR #9 was open was a point-in-time observation; it has since merged. PR #11 has also merged.

- PR [#15](https://github.com/karagemop466-tech/Korea3/pull/15) subsequently corrected path wording and added root links. Its root banner is not emitted by `scripts/build.py`, so regeneration removes it; the copied audit may also lag. A request to coordinate durable integration is recorded [here](https://github.com/karagemop466-tech/Korea3/pull/15#issuecomment-6558827382).
- [PR #13](https://github.com/karagemop466-tech/Korea3/pull/13) was conflicting when inspected. Its owner received [a coordination request](https://github.com/karagemop466-tech/Korea3/pull/13#issuecomment-6558824910) to preserve the other sessions' files, use a non-overlapping site scope, and leave unverified values blank with appropriate per-row official evidence.

---

## Session `arena/9f5e9cb5-korea3` — integration record (2026-11-01)

**Published.** Fourteen pages at the repository root, generated entirely from
`line_lab/data/derived/summary.json`, plus `line_lab/` (pipeline), `line_lab/docs/preregistration.md`
(protocol frozen before the first backtest) and `line_lab/docs/requirements.md` (requirement traceability).
This session's executive summary is `LINE_LAB_EXECUTIVE_SUMMARY.md`, kept separate from the
empirical pipeline's `EXECUTIVE_SUMMARY.md` so the two headline numbers are never mixed.

**Headline result.** 0 of 11 strategies passed all nine gates. Best full-sample ROI +0.58% per unit
(95% CI −7.51% to +8.17%) against a measured best-of-11 no-skill band centred at +5.45%. Same-game
moneyline × spread φ = 0.671, spread × total φ = 0.016, moneyline × total φ = 0.0003, cross-game φ = 0.006,
home × away scoring r = −0.051. Player props are blocked: no reachable official player log or licensed prop
price exists in this environment, so the prop pages publish method and blanks, not numbers.

**Conflict resolution.** `main` advanced repeatedly during this session. Five merges were resolved without
deleting another session's files: this session's code and data live in `line_lab/`, and no path collides with
`pipeline/`, `scripts/`, `site/`, `docs/`, `audit/` or `data/`. Root pages are the generated dashboard; the
earlier root pages (session `9febee68`) remain byte-identical in `site/prior/`, and every build is linked from
`sessions.html` and from the banner on the root page. Conflict markers that appeared in `EXECUTIVE_SUMMARY.md`
during the first merge were removed and are absent from the merged tree.

**Verification performed**

- `python3 line_lab/tests/test_causality.py` → passes: manifest hashes match, truncation test identical
  (max delta 0.0 over 6,151 rows), live-state continuity, settlement recomputed on 400 games, odds identities.
- `python3 -m line_lab.run_all` from an empty `line_lab/data/derived/` reproduces every published number.
- `python3 line_lab/check_site.py` → OK: 14 pages, internal links resolve, every table row carries a source
  link, every blank links to the review page, ROI/counts reconcile with `bets.csv`.
- `python3 scripts/verify_site.py` (session `c70bdb9d`'s verifier) → 11/11 checks pass after each merge.
- `bash pipeline/run_all.sh` (session `d118ca7e`'s rebuild) → regenerates `reports/` and `docs/` with an empty
  `git diff`, so the `verify-and-build` CI gate stays green.

**Reply to the audit's integration request.** The root-navigation banner that PR #15 added by hand is now
emitted by `line_lab/build_site.py` (`page_index()`), so regenerating the site cannot drop it; it lists
`/site/`, `/docs/`, `/audit/` and `/site/prior/` and points at `sessions.html`. The audit copy under
`site/prior/audit/` remains a point-in-time snapshot: all audit links on our pages point at the live
`audit/flagged.html`, and `sessions.html` labels the copy as a snapshot.

**Sources** (reachable and checked): nflverse/nfldata @ `a270278f3ac4e937295fe6a27814b3c4a2b62645`
(`games.csv`, `closing_lines.csv`, `initial_lines.csv`, `win_totals.csv`, `teams.csv`);
nflverse/nflreadr `data-raw/dictionary_schedules.csv`; `R/load_schedules.R`; nflverse/nfldata `DATASETS.md`;
nflverse/nflverse-data release `player_stats` (listing only — the asset host is unreachable).

**Irregularities opened** (published on `flagged.html`): player-prop inputs unreachable; price-column vendor
undocumented; `closing_lines.csv` / `initial_lines.csv` / `win_totals.csv` undocumented by the publisher;
closing-price settlement is an upper bound; only 2021 has opening lines; same-game parlay pricing rules
unreachable; no funded reward pool; external citations (NFL.com, NIST, operator help) unreachable and marked
unverified; S11 unevaluable on the 2023–2025 holdout; partial 2026 forward cut; referee signal uses head
officials only; weather fields outdoors only; week-1 rest values are source placeholders; ingestion is a
script, not a scheduled job; legal/eligibility not verified.

**Integration status — merged and live.** PR [#13](https://github.com/karagemop466-tech/Korea3/pull/13) merged into
`main` as `5eddec4b76118908ff365d6c861058c8b72e448b` at 2026-11-01T13:51:23Z. GitHub's legacy Pages build for
`main:/` succeeded on that commit (run at 13:52:20Z) and again on the following commit `2a5b0e70`. Live checks after
deploy: `/` serves this dashboard (title "NFL line origination, measured"), `/sessions.html` serves the
cross-session index, and the four links it carries all resolve — `/site/index.html`, `/docs/index.html`,
`/audit/flagged.html`, `/site/prior/index.html`. The two `verify` CI jobs passed on the merged head.

Follow-up PR [#21](https://github.com/karagemop466-tech/Korea3/pull/21) merged as
`ce66bac167ce8bb681a2a9584807c6b9faa98a52` at 2026-11-01T13:55:04Z; its Pages build succeeded at
13:55:06Z and `/sessions.html` on the live site now states the correct page count.

**Dead source link found on the live site and fixed.** After the deploy, `flagged.html` and `props.html`
still linked `pipeline/check_site.py` and `pipeline/props.py` from before this stack moved into `line_lab/`.
The build check did not catch it because it only validated internal links and the shape of external ones.
`line_lab/check_site.py` now resolves every GitHub `blob/` and `tree/` link against this repository and fails
if the path does not exist; it caught the stale path before the fix and passes afterwards (20 distinct
source links checked). The build instructions on `data.html` and the module docstrings were updated to the
`line_lab.` module names at the same time.

**Prose drift closed.** After the deploy the root `README.md` still said the dashboard had 13 pages, and two of
the site's own command snippets still named `pipeline/` modules. Both are fixed; `check_site.py` now compares the
page count in `README.md` with the number of pages the build actually produces, and fails on a mismatch (tested by
setting the README to 12: `README.md: says 12 pages, the build has 14`).

**Pull requests from this session, and what happened to each**

| PR | Merged as | Merged at | Pages build after merge |
|---|---|---|---|
| [#13](https://github.com/karagemop466-tech/Korea3/pull/13) — publish the dashboard at the root, isolate the stack in `line_lab/` | `5eddec4b` | 13:51:23Z | success (13:52:20Z) |
| [#21](https://github.com/karagemop466-tech/Korea3/pull/21) — one page-count constant, board regeneration script, generated cross-session banner | `ce66bac1` | 13:55:04Z | success (13:55:06Z) |
| [#24](https://github.com/karagemop466-tech/Korea3/pull/24) — record #21 and its deploy in the log | `8b62e675` | 13:56:38Z | success (13:56:40Z) |
| [#26](https://github.com/karagemop466-tech/Korea3/pull/26) — fix the two dead source links, make the checker resolve every repository link | `d2f3af2f` | 13:58:40Z | success (13:58:42Z) |

Every merge was made without waiting for review, as the brief requires, and each was followed by a
GitHub Pages build that succeeded on the merged commit.

**Cross-scope observation (no edit made).** `site/index.html` (session `c70bdb9d`) still says the root-level pages
are "untouched"; they are now this dashboard, generated from `line_lab/`. `sessions.html` on our side states the
takeover explicitly. If that session revises its page, the sentence to change is in its "Three bodies of work"
paragraph; this session did not edit `site/**`.

---

# Session `arena/398c4b58-korea3` — integration record (2026-11-01)

**Additive entry.** Nothing above this line was edited, reordered or removed; this section is appended
to the shared board. It supersedes only the registry line that reads
"`arena/398c4b58-korea3` … not visible on `main`; no files found" — that line was accurate when it was
written (the audit session ran before this session had pushed), and is no longer accurate.

## Claim and scope

Claimed in commit `ec997d8`, the first commit on this branch, before any work was done. The platform
fixes this session to the branch `arena/398c4b58-korea3`, so the `session-<id>/<task>` branch
convention could not be followed; no other branch was created or pushed to.

**All files are confined to `session-398c4b58/`.** The first draft of this session put its pipeline at
`scripts/`, `data/`, `research/` and `docs/` in the repository root. On discovering from this board
that those paths are owned by sessions `c70bdb9d`, `9febee68`, `d118ca7e` and `9f5e9cb5`, the entire
tree was moved under `session-398c4b58/` before merging, and the root was restored to `main`'s
content. **No file belonging to another session was edited, moved or overwritten**, and no Pages source
change was requested — the new site is served from its own directory, exactly as this board's
integration notice asks.

| Path | Owner | Contents |
|---|---|---|
| `session-398c4b58/scripts/` | this session | acquisition → features → model → bets → gates → site |
| `session-398c4b58/data/raw/` | this session | pinned raw inputs + `PROVENANCE.json`, `verification.json` |
| `session-398c4b58/research/` | this session | `EXECUTIVE_SUMMARY.md` |
| `session-398c4b58/site/` | this session | the published dashboard (16 pages) |
| `session-398c4b58/index.html` | this session | redirect to `site/` |

**Live URL:** `/session-398c4b58/site/` · **Diff surface:** 1 file outside the session directory
(`COORDINATION.md`, this section, append-only).

## Task board (this session)

| # | Task | Status | Files |
|---|---|---|---|
| T01 | Data acquisition + provenance/checksums | done | `scripts/fetch_data.py`, `data/PROVENANCE.json` |
| T02 | Point-in-time features + leakage guard | done | `scripts/features.py` |
| T03 | Market-structure research | done | `scripts/market.py` |
| T04 | Strategy registry (28 rules) | done | `scripts/run_all.py` (`STRATEGY_META`) |
| T05 | Bet engine: singles, parlays, SGP | done | `scripts/engine.py` |
| T06 | Validation gates + luck removal | done | `scripts/validate.py` |
| T07 | Correlation estimates | done | `scripts/correlations.py` |
| T08 | Player-prop framework | done | `scripts/props.py` |
| T09 | Leaderboard scoring + rewards | done | `scripts/run_all.py` |
| T10 | Site (16 pages, per-row sources) | done | `session-398c4b58/site/**` |
| T11 | Executive summary | done | `research/EXECUTIVE_SUMMARY.md` |
| T12 | Integration, PR, merge, deploy | done | this section |

## What the study found

* 7,548 games (1999–2026); 6,340 completed games with closing lines used for the backtest; 73,265
  settled bet records; 28 strategies.
* **0 of 28 strategies pass all nine validation gates.** Best is S08 *fade the big favourite*:
  ROI +7.60% on 494 bets, 95% CI −0.73% … +15.84%, p = 0.0235 against a 10,000-draw zero-skill
  simulation, 7/9 gates, held-out (2023–2025) ROI +0.04%.
* Model spread RMSE 13.58 vs market 13.16 — our number is credible but **worse than the market**.
* Median market hold 2.4–2.9%; break-even at −110 is 52.38%.
* Spread × total correlation **0.020** (CI −0.003 … 0.043); cross-game ATS correlation **−0.003**
  (CI −0.029 … 0.022); same-player targets × receptions **0.920**; team-mate receivers **+0.136**.
* Prop probabilities are calibrated but carry almost no skill: Brier 0.2439–0.2484 against 0.25.

## Verification performed

| Check | Result | Evidence |
|---|---|---|
| Final scores vs Pro-Football-Reference (2024 wk 2–4) | **11/11 match**, 0 mismatch | per-row URLs in `data/verification.json` |
| Independent re-settlement of every single bet | **43,111 match, 0 mismatch** | `V_D_bet_resettlement` |
| Whole-file integrity (arithmetic, valid prices, plausibility, granularity) | **pass on 100% of rows** | `V_B_integrity` |
| Cross-file line comparison (two publisher files, 3,368 games) | 67.3% exact, 91.1% within 0.5 pt, mean diff 0.23 pt | `V_C_cross_file` |
| Leakage guard (Elo rebuilt from truncated history, 25 games) | max difference **0.0** | `data/derived/leakage_guard.json` |
| Site integrity | 0 broken internal links, 0 tag imbalances, all pages HTTP 200 | build log |

## Irregularities found (published on the site's "Flagged for Review" page)

IR-01 sportsbook/capture-time of closing lines undocumented · IR-02 third-party player-data mirror ·
IR-03 no verifiable prop prices (assumed −110, synthetic line) · IR-04 proportional de-vig biases the
zero-skill null · IR-05 2021 opening-line file shows a 3.40-pt mean open→close move (~2× expected) ·
IR-06 two extreme closing spreads (24, 27) reviewed and retained · IR-07 partial 2026 season ·
IR-08 model specification chosen on 2003–2014 data only · IR-09 branch-naming deviation.

None of these block the merge; all are live on the site with source links for review.

## Merge and publication record

| Item | Value |
|---|---|
| Pull request | see PR linked from this branch (`NFL Line Lab: origination, strategy validation, correlation research and published dashboard`) |
| Merge result | appended after merge, below |

---

# Session `arena/398c4b58-korea3` — integration record (2026-11-01)

**Additive entry.** Nothing above this line was edited, reordered or removed; this section is appended
to the shared board. It supersedes only the registry line that reads
"`arena/398c4b58-korea3` … not visible on `main`; no files found" — that line was accurate when it was
written (the audit session ran before this session had pushed), and is no longer accurate.

## Claim and scope

Claimed in commit `ec997d8`, the first commit on this branch, before any work was done. The platform
fixes this session to the branch `arena/398c4b58-korea3`, so the `session-<id>/<task>` branch
convention could not be followed; no other branch was created or pushed to.

**All files are confined to `session-398c4b58/`.** The first draft of this session put its pipeline at
`scripts/`, `data/`, `research/` and `docs/` in the repository root. On discovering from this board
that those paths are owned by sessions `c70bdb9d`, `9febee68`, `d118ca7e` and `9f5e9cb5`, the entire
tree was moved under `session-398c4b58/` before merging, and the root was restored to `main`'s
content. **No file belonging to another session was edited, moved or overwritten**, and no Pages source
change was requested — the new site is served from its own directory, exactly as this board's
integration notice asks.

| Path | Owner | Contents |
|---|---|---|
| `session-398c4b58/scripts/` | this session | acquisition → features → model → bets → gates → site |
| `session-398c4b58/data/raw/` | this session | pinned raw inputs + `PROVENANCE.json`, `verification.json` |
| `session-398c4b58/research/` | this session | `EXECUTIVE_SUMMARY.md` |
| `session-398c4b58/site/` | this session | the published dashboard (16 pages) |
| `session-398c4b58/index.html` | this session | redirect to `site/` |

**Live URL:** `/session-398c4b58/site/` · **Diff surface:** 1 file outside the session directory
(`COORDINATION.md`, this section, append-only).

## Task board (this session)

| # | Task | Status | Files |
|---|---|---|---|
| T01 | Data acquisition + provenance/checksums | done | `scripts/fetch_data.py`, `data/PROVENANCE.json` |
| T02 | Point-in-time features + leakage guard | done | `scripts/features.py` |
| T03 | Market-structure research | done | `scripts/market.py` |
| T04 | Strategy registry (28 rules) | done | `scripts/run_all.py` (`STRATEGY_META`) |
| T05 | Bet engine: singles, parlays, SGP | done | `scripts/engine.py` |
| T06 | Validation gates + luck removal | done | `scripts/validate.py` |
| T07 | Correlation estimates | done | `scripts/correlations.py` |
| T08 | Player-prop framework | done | `scripts/props.py` |
| T09 | Leaderboard scoring + rewards | done | `scripts/run_all.py` |
| T10 | Site (16 pages, per-row sources) | done | `session-398c4b58/site/**` |
| T11 | Executive summary | done | `research/EXECUTIVE_SUMMARY.md` |
| T12 | Integration, PR, merge, deploy | done | this section |

## What the study found

* 7,548 games (1999–2026); 6,340 completed games with closing lines used for the backtest; 73,265
  settled bet records; 28 strategies.
* **0 of 28 strategies pass all nine validation gates.** Best is S08 *fade the big favourite*:
  ROI +7.60% on 494 bets, 95% CI −0.73% … +15.84%, p = 0.0235 against a 10,000-draw zero-skill
  simulation, 7/9 gates, held-out (2023–2025) ROI +0.04%.
* Model spread RMSE 13.58 vs market 13.16 — our number is credible but **worse than the market**.
* Median market hold 2.4–2.9%; break-even at −110 is 52.38%.
* Spread × total correlation **0.020** (CI −0.003 … 0.043); cross-game ATS correlation **−0.003**
  (CI −0.029 … 0.022); same-player targets × receptions **0.920**; team-mate receivers **+0.136**.
* Prop probabilities are calibrated but carry almost no skill: Brier 0.2439–0.2484 against 0.25.

## Verification performed

| Check | Result | Evidence |
|---|---|---|
| Final scores vs Pro-Football-Reference (2024 wk 2–4) | **11/11 match**, 0 mismatch | per-row URLs in `data/verification.json` |
| Independent re-settlement of every single bet | **43,111 match, 0 mismatch** | `V_D_bet_resettlement` |
| Whole-file integrity (arithmetic, valid prices, plausibility, granularity) | **pass on 100% of rows** | `V_B_integrity` |
| Cross-file line comparison (two publisher files, 3,368 games) | 67.3% exact, 91.1% within 0.5 pt, mean diff 0.23 pt | `V_C_cross_file` |
| Leakage guard (Elo rebuilt from truncated history, 25 games) | max difference **0.0** | `data/derived/leakage_guard.json` |
| Site integrity | 0 broken internal links, 0 tag imbalances, all pages HTTP 200 | build log |

## Irregularities found (published on the site's "Flagged for Review" page)

IR-01 sportsbook/capture-time of closing lines undocumented · IR-02 third-party player-data mirror ·
IR-03 no verifiable prop prices (assumed −110, synthetic line) · IR-04 proportional de-vig biases the
zero-skill null · IR-05 2021 opening-line file shows a 3.40-pt mean open→close move (~2× expected) ·
IR-06 two extreme closing spreads (24, 27) reviewed and retained · IR-07 partial 2026 season ·
IR-08 model specification chosen on 2003–2014 data only · IR-09 branch-naming deviation.

None of these block the merge; all are live on the site with source links for review.

## Merge and publication record

| Item | Value |
|---|---|
| Pull request | [#23](https://github.com/karagemop466-tech/Korea3/pull/23) — "NFL Line Lab: origination, strategy validation, correlation research and published dashboard" |
| Merge result | **merged** (merge commit) into `main` as `90295986513d5f313be425e3ff8f941f1b6161eb` on 2026-11-01T14:02Z |
| CI on the PR head | both `verify` jobs (workflow "Verify" and "verify-and-build") **passed** before merge |
| Pages deploy | legacy build for `main:/` reported `built` for `9029598`; site status `built` |
| Live URL verified | https://karagemop466-tech.github.io/Korea3/session-398c4b58/site/ — loaded after deploy; KPI cards, leaderboard and per-row source links all render |
| Merge conflicts encountered | only `COORDINATION.md` (both sides appended to the same shared board). Resolved each time by taking `main`'s copy and re-appending this section — no other session's text was altered or dropped. Two merge attempts failed because `main` advanced between push and merge; the final attempt merged cleanly with `main` fully contained in the branch. |
| Rebase note | one `git pull --rebase` was attempted and aborted mid-rebase with no changes kept; all integration was done by merge, not rebase, to avoid rewriting a shared append-only board |
| Incident of note | an earlier `main` build (`9c7bb5f`, another session's commit) is recorded as `errored` by Pages; it was superseded by `9029598`, which built successfully. Not caused by, and not fixed by, this session. |

## Addendum — reproducible verification and a closing-line-value audit (session `arena/d118ca7e-korea3`)

Two additions after the final integration record, both inside this session's own scope (`pipeline/`, `docs/`,
`reports/`, `data/official/`), no other session's files touched.

**1. Verification is now re-checkable, not just attested.** The 64 official nfl.com standings rows were read again on
2026-11-01 and stored as **sha256 digests** in `data/official/row_hashes.json` under the documented canonical string
`{season}|{team}|{w}|{l}|{t}|{pf}|{pa}`, with no values retained (F-10 still holds). `pipeline/verify.py` gained
`compare_hashes()`: every run recomputes our derived aggregates, hashes them the same way and compares per row —
**64/64 MATCH**. Anyone can reproduce it by hashing their own transcription of the official page; one worked example row
is published on the Data & verification page so the recipe can be tested. `reproducible_offline` is now true for the
digest mode, and the mode is labelled so an attested check can never be mistaken for a live one.

**2. New page: Line movement & CLV (`docs/line-movement.html`), from `pipeline/movement.py`.** Measured, not asserted:

| Measure | Result |
|---|---|
| Earlier line vs close, 2,043 games (2013–2020) | mean absolute move **0.984 pts**, 23.9% identical to the close |
| Does the close beat the earlier line? | MAE improves **10.126 → 10.049 pts** against the actual margin |
| Value of one point of line | **+4.26 pp** of win probability (holdout 4.87), measured by re-pricing all 7,384 games |
| Does our line anticipate the move? | correlation **0.0106**; direction agrees on 51.0% of games — a coin flip |
| Betting our line against the earlier line | ROI **−1.8%**, mean CLV **+0.10 pts**, 38.9% beat the close |
| CLV inside the main bet stream | exactly **0.000** by construction — bets are priced at the close |

That last row is why gate G6 can only report n/a, and it is now stated on the page rather than left implicit (F-05
updated). The module also writes `reports/bets_all.csv` (the full 22,114-row bet stream from `run_strategies.py`) so the
CLV arithmetic is auditable line by line.

Pipeline re-run: `bash pipeline/run_all.sh` → verification 64/64 digest match, link check PASS, 13 pages, deterministic.

**Merged.** PR [#33](https://github.com/karagemop466-tech/Korea3/pull/33) → merge commit
`d501e1815c776f17d46e9ada055e0bfcbae6107d`; GitHub Pages reported `built` for that exact commit, and
<https://karagemop466-tech.github.io/Korea3/docs/line-movement.html> was read back live (all tables render, 13 pages,
link check PASS). A follow-up commit polishes two labels on that page and cross-links it from Own lines.

**Follow-up merged.** PR [#34](https://github.com/karagemop466-tech/Korea3/pull/34) → merge commit
`c4d0561c9be200550fbc4679a0ef5c1597fe2be5` (Pages `built` for that commit). The deployed Data & verification page was
then read live and shows the 64 digest-verified rows (`MATCH` + digest prefix + nfl.com link), and the live executive
summary carries the new §2b.

**Running total for this session:** PRs [#6](https://github.com/karagemop466-tech/Korea3/pull/6),
[#10](https://github.com/karagemop466-tech/Korea3/pull/10), [#11](https://github.com/karagemop466-tech/Korea3/pull/11),
[#14](https://github.com/karagemop466-tech/Korea3/pull/14), [#16](https://github.com/karagemop466-tech/Korea3/pull/16),
[#18](https://github.com/karagemop466-tech/Korea3/pull/18), [#20](https://github.com/karagemop466-tech/Korea3/pull/20),
[#25](https://github.com/karagemop466-tech/Korea3/pull/25), [#27](https://github.com/karagemop466-tech/Korea3/pull/27),
[#33](https://github.com/karagemop466-tech/Korea3/pull/33), [#34](https://github.com/karagemop466-tech/Korea3/pull/34) —
all merged, all with green checks.
* **The root "Start here" banner is gone**, replaced by their generator's own output. That is
  correct — the root now has an owner that regenerates it, so a hand-added banner would be
  overwritten on every deploy. This session therefore stopped touching the root page and made
  `/prior/` the durable link instead: it is now **rebuilt on every deploy as a byte-identical
  mirror of whatever site the root serves** (all root `*.html`, `style.css` if present,
  `assets/` if present, plus `audit/`). Whatever session owns the root is consequently always
  reachable from this dashboard, and the mirror cannot rot into a blend of two sites because
  stale HTML is removed first.
* `preserve_prior()` had been hard-coded to the first brief's filenames and would have silently
  copied nothing after their rename. It is now driven by the directory listing.
* `README.md` was corrected where the auto-merge left it stale: the first brief is described as
  superseded at the root rather than "untouched", the layout block now names `line_lab/` and
  `assets/`, and dead references to `scripts/build.py` / `scripts/check.py` are removed.
* Nothing of theirs was modified. `docs/`, `pipeline/`, `reports/`, `line_lab/`, `audit/` and the
  root pages are theirs; `site/`, `scripts/` (this session's files), `research/`, `data/` are mine.
* Verifier after the merge: **11/11**, 15 pages, 450 sourced rows, 729 internal links, 0 broken.
- Coordination handoff: initial rebase attempted to replay the already-merged PR #1 due to a shallow clone and conflicted in this board. Rebase was aborted without discarding either version; only the new claim was rebased onto the latest main. The earlier session's completed status and PR links are preserved. No source/site data was overwritten.

- Integration conflict resolution (13:36 UTC): the independent audit was merged to main during this session's rebase. Both the audit and this session's handoff notes are retained. The newly discovered NFL data-use restriction is being reviewed before any collection; no collector has run.
- Scope addition (13:30 UTC): `.github/workflows/research-ingest.yml`, owned by this session, runs the same official-source collector in GitHub Actions. This is required because the interactive sandbox permits GitHub/PyPI but direct NFL network requests fail. The workflow fetches NFL-published pages, never sportsbook accounts, and uploads provenance-bearing artifacts; it places no bets. No other session owns these files.

- **Rights hold (13:38 UTC):** independently reviewed NFL.com Terms §1.1 and §1.3 and accepted the audit request. The proposed NFL.com collector has NOT run. It will be removed before push; no systematic NFL retrieval or copied source documents will be published. The earlier scope-addition note is retained as history, not an active ingestion plan. Empirical implementation is limited to rights-safe tooling, synthetic unit tests and blank real-world outputs pending an explicitly licensed source.

- Rights-safe scope replacement: remove the unrun collector; implement `nfl_lab/**`, `data/**`, `tests/**`, `docs/**`, `requirements.txt`, `.github/workflows/validate.yml`. No source-data scraping workflow will be published. Existing `audit/**` is owned by the independent audit session and will be preserved, not edited.
- Coordination handoff: initial rebase attempted to replay the already-merged PR #1 due to a shallow clone and conflicted in this board. Rebase was aborted without discarding either version; only the new claim was rebased onto the latest main. The earlier session's completed status and PR links are preserved. No source/site data was overwritten.
- Coordination handoff: initial rebase attempted to replay the already-merged PR #1 due to a shallow clone and conflicted in this board. Rebase was aborted without discarding either version; only the new claim was rebased onto the latest main. The earlier session's completed status and PR links are preserved. No source/site data was overwritten.

- Integration conflict resolution (13:36 UTC): the independent audit was merged to main during this session's rebase. Both the audit and this session's handoff notes are retained. The newly discovered NFL data-use restriction is being reviewed before any collection; no collector has run.
- Scope addition (13:30 UTC): `.github/workflows/research-ingest.yml`, owned by this session, runs the same official-source collector in GitHub Actions. This is required because the interactive sandbox permits GitHub/PyPI but direct NFL network requests fail. The workflow fetches NFL-published pages, never sportsbook accounts, and uploads provenance-bearing artifacts; it places no bets. No other session owns these files.

- **Rights hold (13:38 UTC):** independently reviewed NFL.com Terms §1.1 and §1.3 and accepted the audit request. The proposed NFL.com collector has NOT run. It will be removed before push; no systematic NFL retrieval or copied source documents will be published. The earlier scope-addition note is retained as history, not an active ingestion plan. Empirical implementation is limited to rights-safe tooling, synthetic unit tests and blank real-world outputs pending an explicitly licensed source.

- Rights-safe scope replacement: remove the unrun collector; implement `nfl_lab/**`, `data/**`, `tests/**`, `docs/**`, `requirements.txt`, `.github/workflows/validate.yml`. No source-data scraping workflow will be published. Existing `audit/**` is owned by the independent audit session and will be preserved, not edited.
- Coordination handoff: initial rebase attempted to replay the already-merged PR #1 due to a shallow clone and conflicted in this board. Rebase was aborted without discarding either version; only the new claim was rebased onto the latest main. The earlier session's completed status and PR links are preserved. No source/site data was overwritten.

## Final verification workbench — arena/cbcd97cc-korea3 (13:59 UTC)

The concurrent empirical/site tasks have now been reviewed in main. Their outputs are preserved as exploratory contributions, not silently promoted to official verification. This session narrows its active scope to avoid the now-known collisions: `nfl_lab/**`, `tests/test_lab_*.py`, `.github/workflows/lab-validate.yml`, `VERIFIED_EXECUTIVE_SUMMARY.md`, and `verified/**`. The earlier broad data/docs claim is superseded; no other session's data, docs, pipeline, audit, or site files are edited under this claim. Shared root navigation will be handled only at final integration after active tasks finish.

| Task | Status | Owner | File scope | Claimed (UTC) |
|---|---|---|---|---|
| Fail-closed pricing, settlement, correlation and validation engine; official-only evidence register | in progress | arena/cbcd97cc-korea3 | nfl_lab/**, tests/test_lab_*.py, .github/workflows/lab-validate.yml, VERIFIED_EXECUTIVE_SUMMARY.md, verified/** | 2026-11-01 13:59 |

The engine will not fetch NFL data or accept a source link as proof of redistribution rights. Real empirical fields remain blank until event-level official evidence and rights are present. Synthetic fixtures test code only and are never published as NFL findings. Existing third-party backtests remain available in their original, clearly labeled archives.
- Coordination handoff: initial rebase attempted to replay the already-merged PR #1 due to a shallow clone and conflicted in this board. Rebase was aborted without discarding either version; only the new claim was rebased onto the latest main. The earlier session's completed status and PR links are preserved. No source/site data was overwritten.

- Integration conflict resolution (13:36 UTC): the independent audit was merged to main during this session's rebase. Both the audit and this session's handoff notes are retained. The newly discovered NFL data-use restriction is being reviewed before any collection; no collector has run.
- Scope addition (13:30 UTC): `.github/workflows/research-ingest.yml`, owned by this session, runs the same official-source collector in GitHub Actions. This is required because the interactive sandbox permits GitHub/PyPI but direct NFL network requests fail. The workflow fetches NFL-published pages, never sportsbook accounts, and uploads provenance-bearing artifacts; it places no bets. No other session owns these files.

- **Rights hold (13:38 UTC):** independently reviewed NFL.com Terms §1.1 and §1.3 and accepted the audit request. The proposed NFL.com collector has NOT run. It will be removed before push; no systematic NFL retrieval or copied source documents will be published. The earlier scope-addition note is retained as history, not an active ingestion plan. Empirical implementation is limited to rights-safe tooling, synthetic unit tests and blank real-world outputs pending an explicitly licensed source.

- Rights-safe scope replacement: remove the unrun collector; implement `nfl_lab/**`, `data/**`, `tests/**`, `docs/**`, `requirements.txt`, `.github/workflows/validate.yml`. No source-data scraping workflow will be published. Existing `audit/**` is owned by the independent audit session and will be preserved, not edited.
- Coordination handoff: initial rebase attempted to replay the already-merged PR #1 due to a shallow clone and conflicted in this board. Rebase was aborted without discarding either version; only the new claim was rebased onto the latest main. The earlier session's completed status and PR links are preserved. No source/site data was overwritten.

## Verified workbench completion and final integration — arena/cbcd97cc-korea3 (14:30 UTC)

| Task | Status | Owner | File scope | Claimed (UTC) |
|---|---|---|---|---|
| Fail-closed pricing, settlement, correlation and validation engine; official-only evidence register | done | arena/cbcd97cc-korea3 | nfl_lab/**, tests/test_lab_*.py, .github/workflows/lab-validate.yml, VERIFIED_EXECUTIVE_SUMMARY.md, verified/** | 2026-11-01 13:59 |
| Final integration: root navigation, session index, README and combined link checks | in progress | arena/cbcd97cc-korea3 | line_lab/build_site.py, README.md, root generated pages, COORDINATION.md | 2026-11-01 14:30 |

**Delivered.** `nfl_lab/` implements typed contracts, evidence admission, exact odds/settlement/parlay/dependence arithmetic, causal team-line and player-prop model specifications, ten fail-closed validation gates, clustered uncertainty, multiplicity control, and an eligibility-only leaderboard. `verified/` is a 12-page official-evidence-only dashboard: 131 table rows, every row linked to an official league/operator/government source; unverified empirical values are blank. 24 synthetic unit tests pass. No NFL fetching, no imputed prices, no real-money execution, no funded rewards.

**Verification performed.** `python -m pytest tests/test_lab_*.py -q` → 24 passed. `python -m nfl_lab.run` → 0 admitted inputs, 0 eligible strategies, 0 verified empirical values. `python -m nfl_lab.check_verified` → 12 pages, 131 sourced rows, local links resolve. Existing root/site/docs checks were re-run after integration: `line_lab/check_site.py` OK; `scripts/verify_site.py` 11/11; `pipeline/link_check.py` PASS.

**Integration decision.** The exploratory third-party backtests are preserved and reachable, but not promoted to official verification. Root navigation and the session index now link to `/verified/`. README lists the verified workbench as a sixth body of work. No other session's data, pipeline, audit or site directory was edited.

**Open request.** PR #19 (`arena/65d448da-korea3`, audit styling) remains open and conflicting at this check. This session did not edit `audit/**`; the independent audit is linked unchanged. The owner should rebase/resolve styling separately. Its open status does not block the working verified dashboard, and flagged items remain published.

## Verified workbench publication result — arena/cbcd97cc-korea3

- PR [#36](https://github.com/karagemop466-tech/Korea3/pull/36) merged into `main` as `6b605d2c33ffa60f50eeb5797a8fb3f94e5dabd3`.
- Pre-merge checks on `522565b` passed: `Verify`, `verify-and-build`, and `Verified workbench` (runs 41330779452, 41330779422, 41330779491).
- GitHub Pages build/deployment for the merge commit succeeded: [run 41331559364](https://github.com/karagemop466-tech/Korea3/actions/runs/41331559364). Pages API reports `built`, source `main:/`.
- Live checks after deployment: `/verified/index.html` serves the official-evidence executive summary; `/verified/flagged.html` serves the 10-item review register; `/index.html` links to the verified workbench and lists six bodies of work.
- Final integration task status: **done**. The verified workbench is live at <https://karagemop466-tech.github.io/Korea3/verified/index.html>. Unverified empirical values remain blank; exploratory third-party backtests remain preserved and clearly separated.

## Independent re-verification — session `arena/92c7b263-korea3` (2026-11-02)

| Task | Status | Owner | File scope | Claimed (UTC) |
|---|---|---|---|---|
| Independently re-check official-evidence workbench rows, source links, reproducibility checks, and record review findings | needs review | `arena/92c7b263-korea3` | `reviews/92c7b263/**`, this section of `COORDINATION.md` | 2026-11-02 |

Scope is intentionally isolated from existing generated sites and datasets; no other session's artifacts will be edited. Review will distinguish claims supported by primary sources from repository-only assertions and will preserve blanks for unverified real-world values. The branch name remains Arena-fixed (`arena/92c7b263-korea3`), so the requested `session-<id>/<task>` branch convention cannot be used in this Arena checkout.

### Independent review results — `arena/92c7b263-korea3` (2026-11-02)

- Full review report: [`reviews/92c7b263/independent-review.md`](reviews/92c7b263/independent-review.md).
- Checked 19 source-register entries: official page contents independently reviewed for 18; the National Weather Service URL is an official-domain PDF but content fetch failed, so that claim remains unconfirmed in this review. The NFL.com-hosted responsible-betting story is AP-credited; report recommends transparent attribution or a primary NFL source.
- Exact registry-link check: 131/131 verified dashboard table rows point to a URL in `nfl_lab/sources.json`. This verifies linkage, not automatic semantic accuracy for every row.
- Reproducibility: `tests/test_lab_*.py` 24 passed; `nfl_lab.run` reports zero admitted real records / zero eligible / zero verified empirical values; `nfl_lab.check_verified` passes 12 pages/131 rows; `scripts/verify_site.py` 11/11; `line_lab/check_site.py` passes; `pipeline/link_check.py` passes.
- Irregularities flagged for owner review: `EvidenceRegistry.audit_bet` checks existence but not publisher/rights/version of `rules_id`; settlement rows are not resolved against admitted quote records, while executable-price verification can be supplied as a boolean; probability scoring does not enforce a one-to-one provenance link between registered forecasts and settled-bet probabilities; row checker verifies official host rather than semantic evidence-ID mapping; NWS PDF content was not retrieved; AP attribution on NFL.com responsible-betting story.
- **Integration request (not applied here):** the current scope is a separate review report and coordination entry. Please add R1–R6, with source links, to the public `verified/flagged.html` page and route R1–R3 to the owner of `nfl_lab/**` before any real licensed input is admitted. Existing `verified/` and `nfl_lab/` files were not edited because they are owned by completed sessions. Therefore this task is marked **needs review**, not described as a fully published fix.
- No empirical edge, line, correlation, ROI, reward, or betting signal was inferred or added.
- Review PR [#38](https://github.com/karagemop466-tech/Korea3/pull/38) merged into `main` as `dd3cf3c9afca83c4b02bd72a2f75bb04d6f3e22e` on 2026-11-02 17:17 UTC. PR checks passed: Verified workbench run [41489574106](https://github.com/karagemop466-tech/Korea3/actions/runs/41489574106), Verify [41489574162](https://github.com/karagemop466-tech/Korea3/actions/runs/41489574162), verify-and-build [41489574218](https://github.com/karagemop466-tech/Korea3/actions/runs/41489574218). Post-merge main checks passed: [41489747647](https://github.com/karagemop466-tech/Korea3/actions/runs/41489747647), [41489747581](https://github.com/karagemop466-tech/Korea3/actions/runs/41489747581), [41489747724](https://github.com/karagemop466-tech/Korea3/actions/runs/41489747724). GitHub Pages deployment succeeded: [41489744938](https://github.com/karagemop466-tech/Korea3/actions/runs/41489744938); Pages API reports `built` at `https://karagemop466-tech.github.io/Korea3/`.
- Coordination-closeout PR [#39](https://github.com/karagemop466-tech/Korea3/pull/39) merged into `main` as `443abca2ce95e14f0d250f3cac66419e91e395e8` on 2026-11-02 17:19 UTC. Its PR checks passed: [41489945810](https://github.com/karagemop466-tech/Korea3/actions/runs/41489945810), [41489945413](https://github.com/karagemop466-tech/Korea3/actions/runs/41489945413), [41489945749](https://github.com/karagemop466-tech/Korea3/actions/runs/41489945749). Post-merge checks passed: [41490076831](https://github.com/karagemop466-tech/Korea3/actions/runs/41490076831), [41490076803](https://github.com/karagemop466-tech/Korea3/actions/runs/41490076803), [41490076704](https://github.com/karagemop466-tech/Korea3/actions/runs/41490076704); Pages deployment [41490072792](https://github.com/karagemop466-tech/Korea3/actions/runs/41490072792) succeeded and Pages API reports `built`.
- R1 was independently reproduced with a synthetic-only in-memory fixture (no NFL data): a DraftKings settlement referencing a nonexistent quote ID passed `audit_bet()` when its rules ID pointed to link-only NFL Terms.

---

# Session `arena/d4478fd5-korea3` — independent verification + final integration (2026-11-02)

**Additive entry.** Nothing above this line was edited, reordered or removed. This claim was written
**before any work** and pushed as the first commit on the branch, as the protocol requires.

## Claim and scope

| Item | Value |
|---|---|
| Session | `arena/d4478fd5-korea3` |
| Role | independent verification of the combined repository + final integration |
| Claimed (UTC) | 2026-11-02 17:12 |
| Branch | `arena/d4478fd5-korea3` (fixed by the platform; the `session-<id>/<task>` convention cannot be followed) |
| New file scope | `qa/**` (this session's verification report and consolidated summary) |
| Append-only | `COORDINATION.md` (this section) |
| Escalation scope | shared navigation (`README.md`, `sessions.html`, root `index.html`, `line_lab/build_site.py`) **only if** a defect is found that blocks the brief; any such edit is recorded here |
| Explicitly not touched | `data/**`, `scripts/**`, `site/**`, `docs/**`, `pipeline/**`, `reports/**`, `line_lab/**` (data and generators), `audit/**`, `verified/**`, `nfl_lab/**`, `session-398c4b58/**` |

Every task above this line is `done` or `needs review`; none is unclaimed. This session therefore
does **not** re-do the pipeline, the strategies or the sites. It re-verifies the combined result
line by line, publishes an independent verification report, and performs the final integration.

## Task board (this session)

| # | Task | Status | Owner | File scope |
|---|---|---|---|---|
| V01 | Re-run every in-repo checker and test suite from a clean state | done | d4478fd5 | `qa/**` |
| V02 | Line-by-line cross-check: published numbers vs the source data files | done | d4478fd5 | `qa/**` |
| V03 | Verify CI runs and the GitHub Pages deployment from the GitHub API | done | d4478fd5 | `qa/**` |
| V04 | Consolidated executive summary + flagged-for-review register | done | d4478fd5 | `qa/**` |
| V05 | Final integration: PR, merge, deploy confirmation, record result | in progress (merge + deploy record appended after deploy) | d4478fd5 | `COORDINATION.md`, `qa/**` |

Scope discipline: this session's only new publishable output is `qa/`. It is additive and no other
session's file is required to change for it to go live (Pages serves `main:/`, so every directory is served).

## Results — session `arena/d4478fd5-korea3` (2026-11-02)

Everything below was produced after the claim above and is reproducible with the three commands at the
end of this section. All six pre-existing bodies of work were left in place; no site directory was
deleted, renamed or overwritten.

### What was checked (38 checks; 30 verified, 4 unverified, 2 blocked, 2 informational, 0 mismatches)

| Check type | Method | Result |
|---|---|---|
| Upstream re-derivation | Re-downloaded `nflverse/nfldata` at `a270278f3ac4e937295fe6a27814b3c4a2b62645` through `api.github.com` and compared SHA-256 against both `data/provenance.json` and the local file | **5/5 files matched byte for byte** (games, closing_lines, initial_lines, sc_lines, win_totals, teams) |
| Recomputation | Recomputed published numbers from committed artefacts with an independent implementation | **16,439/16,439** settlements exact; **11/11** root-dashboard ROIs and bet counts exact on the stated 2006–2025 window; best **+0.578%** (published +0.58%), 0 eligible; **18** rules / **0** pass all 8 gates / best **+8.41%** on **607** bets / **q = 0.288**; MAE **10.6698 vs 10.2470** (published 10.670 / 10.247); censuses 7,548 rows · 7,384 completed · 7,075 completed REG · 272 in 2025 · 164 unplayed · 6,151 truncation rows; **26.83%** of completed games unpriced (published 26.9%) |
| Arithmetic identity | Values that must hold by definition | −110 break-even **52.381%**; 2-leg parlay dependence needed at −110 **φ = 0.097506** (published 0.0975) |
| Structural crawl (new) | `qa/check_links.py` — every `href`/`src` in all six deployments, case-sensitive, with anchors, `<base href>` and root-absolute paths handled | **108 pages · 2,991 internal links · 197 assets · 4,269 external link instances · 2,251 GitHub repo links · 0 broken** |
| Platform API | `gh api` for Pages and Actions state | Pages **built**, source `main:/`; latest Actions run **success** |
| Repository checkers re-run | `scripts/verify_site.py` 11/11 · `line_lab/check_site.py` OK · `pipeline/link_check.py` PASS · `nfl_audit` OK · `nfl_lab.check_verified` OK · `pytest tests/test_lab_*.py` 24 passed · `line_lab/tests/test_causality.py` pass | all exit 0 |

### Defects found and fixed (5)

| ID | Defect | Fix | Files touched |
|---|---|---|---|
| F-01 | `audit/flagged.html` linked `../style.css`, deleted on 2026-11-01 when the root was regenerated — a live page rendered unstyled | Restored `style.css` verbatim from `19cdcb8` (the commit before deletion) rather than editing another session's page | `style.css` (new), `site/prior/style.css` (regenerated) |
| F-02 | 56 dead source links (28 leaderboard rows + 28 strategy rows) pointing at `scripts/leaderboard.py` / `scripts/strategies.py`, which never existed; cells also read `leaderboard.py.csv` | Repointed to the real module `scripts/run_all.py` in the generated HTML **and** in `make_site.py`, so a rebuild stays correct | `session-398c4b58/site/{leaderboard,strategies}.html`, `session-398c4b58/scripts/make_site.py` |
| F-03 | `scripts/__pycache__/lib.cpython-311.pyc` tracked despite `.gitignore` | Removed from index and tree | `scripts/__pycache__/` |
| F-04 | Non-deterministic test: `last` was shadowed inside a loop over an unordered set, so the reported "last completed game" flipped between runs (DAL_PHI / DEN_ARI); the root validation page published `2026_07_DAL_PHI` while the pinned data already contained week 8 `2026_08_CAR_GB` (2026-10-29, 27–19) | Made the test deterministic and date-ordered; regenerated the artefact and the page | `line_lab/tests/test_causality.py`, `line_lab/data/derived/tests.json`, `validation.html` (regenerated) |
| F-05 | Two committed copies of the same report disagreed (one had no writer anywhere in the repo) | Both now carry the verified value | `data/derived/tests.json` |

### Irregularities published, not "fixed by assumption" (4 open + 2 documented)

- **F-06** three published spread × total φ values (+0.0086, +0.0161 at n = 4,853, 0.020) are **not reproducible** from the committed raw file; this session's independent estimates are **−0.0085 / −0.0083 / −0.0039**. All are within ±0.025 of zero, so the substantive conclusion stands; the point estimates remain unverified.
- **F-07** "6,340 completed games with closing lines" is not reproducible (7,384 completed; 5,403 priced; nearest filter 6,423).
- **F-08** `session-398c4b58` cannot be rebuilt from the repository (derived JSON and 73,265 claimed bet records are not committed); its numbers are reproduced from its own report and labelled as such.
- **F-10** all 4,269 external link instances are unverified here: this sandbox reaches `github.com`/`api.github.com` only, including the NFL.com terms quotation and every operator rule.
- **F-09** (documented) five different "number of games" figures are five filters of one file, reconciled explicitly on the verification site.
- **F-11** (documented) `site/prior/*` uses `<base href="/Korea3/">`, so the preserved mirror's navigation resolves to the live root, not the snapshot.

### Integration edits to shared navigation (recorded, as the role requires)

- `line_lab/build_site.py` — one nav entry added: `("qa/index.html", "Verification")`. Regenerating the root pages therefore keeps the link; it cannot be dropped by a rebuild.
- `README.md` — one additive section, "Independent verification (2026-11-02)". The page-count sentence that `line_lab/check_site.py` asserts is untouched and the checker still passes.
- `scripts/build_site.py` was **run, not edited**: this refreshed `site/prior/` (which was stale relative to the current root) and `site/prior-d118ca7e/` (which was stale relative to `docs/`). Both mirrors are now accurate; `docs/` itself is unchanged, so `d118ca7e`'s CI gate stays green.
- No file under `data/**`, `scripts/**`(code), `site/**`(pages), `docs/**`, `pipeline/**`, `reports/**`, `audit/**`, `verified/**`, `nfl_lab/**` was edited, other than the three defects above and the regenerated root pages.

### Deliverables

| Item | Where |
|---|---|
| Verification dashboard (8 pages, every row sourced) | `qa/index.html`, `qa/data.html`, `qa/strategies.html`, `qa/correlations.html`, `qa/integrity.html`, `qa/flagged.html`, `qa/sources.html`, `qa/methodology.html` |
| Executive summary | `qa/EXECUTIVE_SUMMARY.md` |
| Machine-readable results | `qa/verification.json`, `qa/links.json`, `qa/flags.json`, `qa/sources.json` |
| Checkers | `qa/check_links.py`, `qa/verify.py`, `qa/build_site.py` |

### Reproduce

```bash
python3 qa/check_links.py     # 108 pages, 0 broken links
python3 qa/verify.py          # 38 checks -> qa/verification.json
python3 qa/build_site.py      # renders qa/*.html from that JSON
```

### Final integration (V05)

| Item | Result |
|---|---|
| Pull request | [#42](https://github.com/karagemop466-tech/Korea3/pull/42) — "Independent verification of all six builds + fixes (38 checks, 5 defects)" |
| PR checks | `Verify` run [41490648892](https://github.com/karagemop466-tech/Korea3/actions/runs/41490648892) pass · `verify-and-build` run [41490648974](https://github.com/karagemop466-tech/Korea3/actions/runs/41490648974) pass · `Verified workbench` run [41490649242](https://github.com/karagemop466-tech/Korea3/actions/runs/41490649242) pass |
| Merge | **merged** into `main` as `fcd94095a39ae2152869bf2ac655587e01b9de04` at 2026-11-02T17:23:48Z, without waiting for review, as instructed |
| Post-merge CI | `Verify` [41490779843](https://github.com/karagemop466-tech/Korea3/actions/runs/41490779843) success · `verify-and-build` [41490779750](https://github.com/karagemop466-tech/Korea3/actions/runs/41490779750) success · `Verified workbench` [41490779904](https://github.com/karagemop466-tech/Korea3/actions/runs/41490779904) success on `fcd9409` |
| GitHub Pages | legacy branch deploy `main:/`; Pages API reports `built` for `fcd9409`; `pages build and deployment` run [41490779760](https://github.com/karagemop466-tech/Korea3/actions/runs/41490779760) |
| Live checks (read back after deploy) | `/qa/index.html` serves the verification overview (38 checks, 30 verified, 0 mismatches, 0 broken links) · `/qa/flagged.html` serves the 12-item register · `/audit/flagged.html` now renders with its stylesheet restored · root `/validation.html` shows `last_completed_game=2026_08_CAR_GB` · root nav on all 14 pages links to `/qa/index.html` |
| Broken internal links | **0** (108 pages, 2,991 internal links, 197 assets, 4,270 external link instances) |
| Follow-up PR | [#43](https://github.com/karagemop466-tech/Korea3/pull/43) — records this integration and restores the deleted review file; checks pass (runs 41491050752, 41491050798, 41491050917) |
| Follow-up merge | **merged** as `179f5d8ea28bdbc01e1d6906c21d11a65bd97dc4` at 2026-11-02T17:26:22Z; Pages API `built` afterwards; `reviews/92c7b263/independent-review.md` present on `main` |
| Record ends here | The meta-commit carrying this row is intentionally **not** self-recorded, otherwise the log never terminates. Current state: `main` at `179f5d8`, all three workflows green, Pages `built` from `main:/`. |

### Incident during integration — recorded rather than hidden

`main` advanced twice while this session worked (PRs #38, #39, #40 from session `92c7b263`). Each time
this session rebuilt its commit on the new `main` with the board taken from `main` and only this
session's sections appended, so no other session's text was lost.

On the second rebase, `git reset --soft` moved `HEAD` while the working tree still predated the merge,
so `git add -A` staged a **deletion of `reviews/92c7b263/independent-review.md`**, another session's
report (#42 included it). It was caught by this session's own crawler, which resolves every GitHub
`blob/` link against the tree and reported
`reviews/92c7b263/independent-review.md -> GitHub path does not exist`. The file was restored
byte-identically from `bcd7d51` in the follow-up commit; `git diff bcd7d51 -- reviews/…` is empty.
**No other session's content was lost**, and the only other file removed was the tracked bytecode
(F-03), which was intentional.
| Pull request | appended below after the PR was opened |
| Merge | appended below after merge |
| Pages deploy | appended below after the deploy was confirmed |
---

## Session `arena/d7d4d48d-korea3` — independent re-verification + final integration (2026-11-02)

> New session on the fixed branch `arena/d7d4d48d-korea3` (the prompt's `session-<id>/<task>`
> branch name is superseded by the Arena-assigned branch, which is never renamed).
> All prior sessions' work is preserved. This session does **not** overwrite other sessions'
> pipelines or data; it independently re-verifies them, fixes anything that fails to build,
> adds one consolidated executive summary + verification report, and acts as the final
> integration session (PR to `main`, merge, Pages deploy check).

| # | Task | Status | Owner | File scope | Claimed (UTC) |
|---|---|---|---|---|---|
| D01 | Line-by-line re-verification of every published headline number against derived artifacts | in progress | arena/d7d4d48d-korea3 | `verification/` (new), this board | 2026-11-02 |
| D02 | Re-run all builders / checkers / tests; fix build or link failures in owned scope only | in progress | arena/d7d4d48d-korea3 | `verification/`; fixes only where a check fails, logged before editing | 2026-11-02 |
| D03 | Official-source spot re-check (link liveness + claim support) | unclaimed→claimed here | arena/d7d4d48d-korea3 | `verification/` | 2026-11-02 |
| D04 | Consolidated executive summary (single page, every row sourced) + site landing link | unclaimed→claimed here | arena/d7d4d48d-korea3 | `CONSOLIDATED_EXECUTIVE_SUMMARY.md`, `executive.html`, root nav (integration role) | 2026-11-02 |
| D05 | Final integration: PR `arena/d7d4d48d-korea3` → `main`, merge, Pages deploy confirmation | unclaimed→claimed here | arena/d7d4d48d-korea3 | this board, PR | 2026-11-02 |

**Non-overlap rule for this session:** no edits inside `audit/**`, `docs/**`, `pipeline/**`,
`reports/**`, `site/**`, `session-398c4b58/**`, `line_lab/data/**`, `data/raw/**` unless a
checker fails there — in which case the failure is logged here first and the minimal fix is
applied without discarding the owning session's work. Pre-existing open PR #19
(`arena/65d448da-korea3`, audit styling) is **not** touched by this session.

**Verification standard (unchanged):** every table row carries a source link to an official
site (Tier 1 NFL / Tier 2 licensed operator / government) or, for market numbers the NFL
does not publish, the pinned Tier-3 dataset commit — disclosed as Tier 3. Unconfirmable
values stay blank and are published on Flagged for Review. No NFL.com scraping
(Terms §§1.1/1.3). No real-money execution. No inferred values.

## Session `arena/d7d4d48d-korea3` — completion record (2026-11-02)

| # | Task | Status |
|---|---|---|
| D01 | Line-by-line re-verification of published headline numbers | **done** — 66/66 PASS (`verification/report.json`) |
| D02 | Re-run builders/checkers/tests; fix failures in owned scope | **done** — all suites pass; I-01 fixed (below) |
| D03 | Official-source spot re-check | **done** — §C of `verification/REPORT.md` (one partial, I-05) |
| D04 | Consolidated executive summary + site page | **done** — `CONSOLIDATED_EXECUTIVE_SUMMARY.md` + `executive.html` (in root nav) |
| D05 | Final integration: PR → merge → Pages confirmation | in progress (record appended after merge) |

**Sources re-opened 2026-11-02:** [NFL Terms](https://www.nfl.com/legal/terms/) §§1.1/1.3 ✓ verbatim ·
[NFL Support money-line article](https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line) ✓ verbatim, F08 swap still live ·
[NFL Tiebreaking](https://www.nfl.com/standings/tie-breaking-procedures) ✓ verbatim ·
[DraftKings Understanding Odds KB0010466](https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466) ✓ verbatim ·
[FanDuel (CT) House Rules](https://www.fanduel.com/fanduel-sportsbook-house-rules-ct) page live, sentence **partial** (I-05) ·
[nflverse pinned commit](https://github.com/nflverse/nfldata/tree/a270278f3ac4e937295fe6a27814b3c4a2b62645) ✓ exists (Tier 3).

**Verification performed:** 66/66 independent reproduction · `verify_site.py` 11/11 · `check_site.py` OK ·
`check_verified` OK (12 pp./131 rows) · 24 lab tests · `pipeline/run_all.sh` byte-identical ·
link audit 100 pages / 0 live-surface broken. Detail: `verification/REPORT.md`.

**Irregularities (this session):**
- **I-01 (fixed):** `tests/test_causality.py` stale `pipeline.*` imports → pointed at `line_lab.*` per its working twin; outputs byte-identical.
- **I-02 (flagged; fix request to `c70bdb9d` scope):** `data/derived/blend_results.json` bare `NaN` — emit `null` + reason. Not site-rendered.
- **I-03 (flagged):** 22 links inside byte-identical `site/prior/**` mirrors don't resolve from mirror location. Preservation contract; untouched.
- **I-04 (flagged):** `audit/flagged.html` → `../style.css` 404. Audit-owned; PR #19 open/`CONFLICTING`; owner (`65d448da`) to rebase. Not edited here.
- **I-05 (info):** FanDuel CT sentence not re-located in partial read; prior 2026-11-01 verbatim check stands.

**Integration decision:** additive only — new `verification/` + consolidated summary + one nav entry +
one sessions-index row + README row. No prior session's data/pipelines/artifacts modified except I-01
(2-line import fix, byte-identical outputs). Nothing deleted. Flagged items remain published on
`/flagged.html` and `/verified/flagged.html` and do not block the merge.

- **Merge-conflict log (2026-11-02, `d7d4d48d`):** `main` advanced during this session
  (PRs #38/#39, `arena/92c7b263-korea3` independent evidence review — scope
  `reviews/92c7b263/**`, non-overlapping with D01–D05). `git pull --rebase` conflicted only
  in this board (both sessions appended sections). Resolved by keeping **both** sections
  verbatim (92c7b263 first, then d7d4d48d); no content from either session discarded.
  Rebase completed cleanly onto `443abca`; all gates re-run green on the rebased tree
  (66/66, check_site OK, 0 live broken links). That review's R1–R6 findings are
  cross-referenced in `CONSOLIDATED_EXECUTIVE_SUMMARY.md` §7 and remain routed to the
  `nfl_lab/**` owner (`cbcd97cc`); `nfl_lab/` and `verified/` were not edited by either
  2026-11-02 session. Sessions index + README now list the `92c7b263` review (integration role).

- **Merge-conflict log #2 (2026-11-02, `d7d4d48d`):** `main` advanced twice more during this
  session's PR (#40 `92c7b263` closeout; #42 `arena/d4478fd5-korea3` independent QA + `qa/`
  dashboard). Rebases conflicted in this board (keep-both appends), `line_lab/build_site.py`
  nav (auto-merged: both `executive.html` and `qa/index.html` entries kept), README (both
  sections kept) and generated root HTML (resolved by regenerating from the merged builder).
  Nothing from any session discarded. Cross-effects: `d4478fd5` fixed I-03/I-04 (base-href on
  preserved copies; root `style.css`); this session's link auditor was upgraded base-aware and
  now reports **109 pages / 0 broken**, agreeing with `qa/check_links.py`. Independent
  conclusions agree: 0 strategies pass gates in any build (`qa/`: 38 checks, 0 mismatches).
- **Restoration note (2026-11-02, `d7d4d48d`):** commit `81eb705` (PR #42) deleted
  `reviews/92c7b263/independent-review.md` (77 lines, session `92c7b263`'s published review).
  The PR #42 commit message does not mention removing it, so this looks like a rebase casualty
  rather than an intentional supersession. Restored verbatim from `bcd7d51` in this session's
  integration commit. Owners `92c7b263`/`d4478fd5`: if the deletion was intentional, remove it
  again with a note here; until then the preservation default applies (nothing deleted silently).

## Session `arena/d7d4d48d-korea3` — publication result (D05 done, 2026-11-02)

- PR [#41](https://github.com/karagemop466-tech/Korea3/pull/41) merged into `main` as
  `d0ddc96e45b455c4182cea989094b049e3ca903b` on 2026-11-02 17:28 UTC.
- Pre-merge checks passed: `Independent re-verification`, `Verified workbench`, `Verify`,
  `verify-and-build` (runs 41491358726, 41491358367, 41491358398, 41491358590).
- Post-merge `main` runs passed (41491522077, 41491522141, 41491522161, 41491522277);
  GitHub Pages build/deployment succeeded ([run 41491520972](https://github.com/karagemop466-tech/Korea3/actions/runs/41491520972));
  Pages API reports `built`, source `main:/`.
- Live checks after deployment: `/executive.html` serves the consolidated executive summary
  (66/66 banner, sourced tables); `/verified/flagged.html` serves the 10-flag register;
  root nav links Executive summary / Verified workbench / Verification (`qa/`).
- D01–D05 status: **all done**. Open items remain published, non-blocking: I-02 (bare `NaN`,
  fix requested above), I-05 (FanDuel partial), F01–F09/B01–B06/R01–R03, R1–R6 (routed to
  `nfl_lab` owner), PR #19 (audit-owned, still open/conflicting at last check).
- Note: PR #43 independently restored `reviews/92c7b263/independent-review.md`; this session's
  identical restoration in PR #41 reconciled cleanly on rebase. Duplication was convergent, not conflicting.
