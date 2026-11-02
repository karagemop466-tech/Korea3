# Session `arena/15b03d7f-korea3` — verification sweep, defect fixes and irregularity register

**Date:** 2026-11-02 (UTC) · **Branch:** `arena/15b03d7f-korea3` · **Board:** [`COORDINATION.md`](../COORDINATION.md)

This session ran a full line-by-line verification sweep over every checker, test suite and CI
equivalent in the repository, took over the stale PR #19 under the board's 60-minute rule, fixed two
reproducibility defects it found, verified the deployed GitHub Pages site page by page, and
published its new findings on the audit **Flagged for Review** page
([`/audit/flagged.html`](https://karagemop466-tech.github.io/Korea3/audit/flagged.html), rows 22–25).
No empirical value was inferred, filled in, or promoted; unverified cells remain blank.

---

## 1. Local verification sweep (all run at the rebased head)

| # | Check | Command | Result |
|---|---|---|---|
| S1 | Full test suite (synthetic fixtures) | `python3 -m pytest tests/ -q` | **24/24 passed** (after fix §3.1; before the fix it failed collection) |
| S2 | Root dashboard site checker | `python3 line_lab/check_site.py` | **PASS** |
| S3 | Empirical-pipeline site verifier (11 gates) | `python3 scripts/verify_site.py` | **11/11 checks passed** |
| S4 | Docs pipeline link checker | `python3 pipeline/link_check.py` | **PASS** — 13 pages, structural errors none |
| S5 | Official-evidence workbench checker | `python3 -m nfl_lab.check_verified` | **OK** — 12 pages, 131 sourced rows, blanks intact |
| S6 | Audit page row checker | `python3 audit/check_audit_page.py` | **OK** — 25 rows (21 from PR #19 + 4 new this session) |
| S7 | Pinned merged-snapshot row scan | `python3 audit/check_merged_rows.py` | **REPRODUCED** — 872/949 rows without links in the pinned snapshot |
| S8 | Pinned PR #13 row scan | `python3 audit/check_pr13_rows.py` | **REPRODUCED** — 767/773 rows lack an official-domain link |
| S9 | Standings attestation QA | `python3 audit/reproduce_standings_qa.py` | **REPRODUCED** — both historical defects reproduce |
| S10 | Attestation inheritance QA | `python3 audit/reproduce_attestation_qa.py` | **REPRODUCED** — old-MATCH inheritance reproduces; snapshot fixes confirmed |
| S11 | CI `verify-and-build` equivalent | `bash pipeline/run_all.sh` + JSON assertions + `git diff --exit-code -- reports docs` | **PASS** — verification 64/64 official rows, link check PASS (13 pages), regeneration byte-identical |
| S12 | CI `Verified workbench` equivalent | `python3 -m nfl_lab.run` + `git diff --exit-code -- verified nfl_lab` | **PASS** — 0 admitted inputs / 0 eligible / 0 verified values, regeneration byte-identical |
| S13 | Independent QA recomputation | `python3 qa/verify.py` | **exit 0** — 30 verified, 4 unverified, 2 blocked, 0 mismatches (outputs reverted; `qa/**` belongs to another session) |
| S14 | Repository-wide link census | `python3 qa/check_links.py` | **PASS** — orphan notes for `site/prior/` pages only (informational) |
| S15 | Prior-session full reproduction (temp copy) | `session-398c4b58/scripts/run_all.py` + `verify_external.py` in `/tmp` | **PASS after workaround** — see §3.2; every published number matched |

Workflow definitions (`.github/workflows/{verify,ci,lab-validate}.yml`) were read line by line;
S3/S4/S11/S12/S1+S5 are their local equivalents. CI on `main` was green for every merge
observed during this session (PRs #38–#48).

## 2. Live GitHub Pages verification (read back from the deployed site)

| Page | Status | Notes |
|---|---|---|
| <https://karagemop466-tech.github.io/Korea3/> | OK | Root dashboard + “Start here” banner to `/hub/` |
| `…/hub/index.html` | OK | 20-page consolidated official-source dashboard |
| `…/hub/flagged.html` | OK | 34-item register, blank unverified values |
| `…/site/index.html` | OK | Empirical pipeline dashboard (15 pages) |
| `…/docs/index.html` | OK | Second Line Lab build (13 pages) |
| `…/session-398c4b58/site/index.html` | OK | 28-strategy study, per-row sources |
| `…/qa/index.html` | OK | 38-check independent QA dashboard |
| `…/verified/index.html`, `…/verified/flagged.html` | OK | Official-evidence workbench; 10 flags |
| `…/audit/flagged.html` | OK (pre-takeover: 19 items) | Becomes 25 items after this session's PR merges |
| `…/executive.html` | OK | Consolidated executive summary (66/66 recomputed) |
| `…/review/index.html` | OK | PR #47 addendum |
| `…/sessions.html` | OK | Index of all bodies of work |
| `…/style.css` | OK | Serves; same stylesheet PR #19's audit copy uses |

Sandbox network policy blocks direct `curl` to `github.io`, so each page was fetched and read
through the session's page-fetch tool (content returned in full, see tool log).

## 3. Irregularities found (published on `/audit/flagged.html` rows 22–25)

### 3.1 FIXED — the documented G2 test entry point was broken (row 22)

`python3 tests/test_causality.py` — the command printed on the root dashboard
(`line_lab/build_site.py`) and cited by `docs/preregistration.md` as gate G2 — imported
`pipeline.markets` / `pipeline.core`, modules PR #13 moved into `line_lab/`, and **failed on a
clean checkout**. CI never caught it because the workflows only collect `tests/test_lab_*.py`.
PR #41 repaired the two imports but kept a duplicate of the whole implementation, which still
contains the set-order nondeterminism (F-04): running it flips `last_completed_game`
`2026_08_CAR_GB` → `2026_07_DEN_ARI` and dirties `data/derived/tests.json`
(reproduced in this session, then reverted). This session replaced the file with a wrapper that
executes the maintained `line_lab/tests/test_causality.py` implementation and mirrors
`tests.json` + the flag back to `data/derived/` (restoring the root copy's only writer, the
gap the QA session recorded as F-05). Result: `pytest tests/` 24/24, wrapper exit 0,
`git status data/derived/` clean after a run.

### 3.2 FLAGGED — `session-398c4b58` snapshot not runnable from a clean checkout (row 23)

`session-398c4b58/scripts/run_all.py` never creates `data/derived/` (or `docs/data/`), so a
fresh clone crashes (`OSError: Cannot save file into a non-existent directory`), and
`verify_external.py` then cannot find `bets.csv` (its generated inputs are not committed).
**Workaround used for verification:** a temp copy in `/tmp` with the two directories created.
With that, every number the session published reproduced exactly:

| Published claim (board + site) | Reproduced |
|---|---|
| Final scores vs Pro-Football-Reference, 2024 wk 2–4 — 11/11, 0 mismatch | **11/11, 0 mismatch, 0 unconfirmed** |
| Whole-file integrity — pass on 100% of rows | **pass, 6 checks, 0 failures** |
| Cross-file line comparison, n=3,368 — 67.3% exact, 91.1% within 0.5 pt, mean 0.23 pt | **identical** |
| Independent re-settlement of every single bet — 43,111 match, 0 mismatch | **43,111 match, 0 mismatch, 30,154 n/a** |
| Full study — 7,548 games, 73,265 bets, 28 strategies, 0 pass all gates | **identical** |

Fix belongs to that session's scope (`session-398c4b58/**`); this session only logged it.

### 3.3 FLAGGED — verification summary prints `null` for two checks (row 24)

`verify_external.py`'s console summary reads `v.get("pass")`, a key `V_A_pfr_scores` and
`V_C_cross_file` never define, so both print `null` although the underlying JSON is complete.
Cosmetic; no value affected.

### 3.4 RESOLVED — stale PR #19 taken over (row 25)

PR #19 was open ≈18 h with no owner activity and `CONFLICTING` with `main`. Under the board's
60-minute rule this session took over **only** `audit/**` (+ the required byte-identical mirror
in `site/prior/audit/`), re-applied all five file changes, preserved the PR's two board-note
sections verbatim in the coordination log (they existed nowhere on `main`), ran every audit
checker, and closed PR #19 as superseded with a cross-reference. No other session's files were
edited.

### 3.5 Other observations (no action taken; other sessions' scopes)

- `qa/check_links.py` reports ORPHAN notes for `site/prior/*.html` (informational; overall PASS).
- Backlog items B01–B06 (prop lines, injuries, weather provenance, referee data, travel
  coordinates, pre-2021 opening lines) remain open for lack of official machine-readable
  sources; they stay blank and flagged on the live registers.
- During this session `main` advanced six times (PRs #38–#48, sessions `92c7b263`, `d4478fd5`,
  `d7d4d48d`, `25ea8ac4`, `776b83f1`). Every `COORDINATION.md` conflict was resolved by keeping
  **both** sides in full; no other session's board text was dropped, and each resolution is
  recorded in the board.

## 4. Sources used for verification (official / primary)

- NFL stats directory — <https://support.nfl.com/hc/en-us/articles/35869694725268-Stats-Records>
- NFL terms (data-use boundary) — <https://www.nfl.com/legal/terms/>
- NFL official 2025 standings (64-row digest check target) — <https://www.nfl.com/standings/division/2025/REG>
- Pro-Football-Reference 2024 schedule (V-A spot-check rows) — <https://www.pro-football-reference.com/years/2024/games.htm>
- DraftKings parlay rules — <https://support.draftkings.com/dk/en-us/what-is-a-parlay-bet?id=kb_article_view&sysparm_article=KB0010683>
- DraftKings odds explanation — <https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466>
- NIST confidence intervals — <https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm>
- NIST multiple comparisons — <https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm>
- GitHub Pages source configuration — <https://docs.github.com/en/pages/getting-started-with-github-pages/configuring-a-publishing-source-for-your-github-pages-site>
- Pinned market dataset (Tier-3, by-design provenance) — <https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv>

Every table row added by this session carries a source link on the published register; values
that could not be confirmed from an official source were left blank and flagged, never inferred.

## 5. Reproduce this session's checks

```bash
python3 -m pytest tests/ -q                 # 24 passed
python3 tests/test_causality.py             # all causality/settlement/provenance checks passed; clean diff
python3 scripts/verify_site.py              # 11/11
python3 line_lab/check_site.py              # OK
python3 pipeline/link_check.py              # PASS
python3 -m nfl_lab.check_verified           # 12 pages, 131 rows
bash pipeline/run_all.sh && git diff --exit-code -- reports docs
python3 -m nfl_lab.run && git diff --exit-code -- verified nfl_lab
python3 audit/check_audit_page.py           # 25 rows
python3 audit/check_pr13_rows.py            # 767/773 reproduced
```
