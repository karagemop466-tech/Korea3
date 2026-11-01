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

**Cross-scope observation (no edit made).** `site/index.html` (session `c70bdb9d`) still says the root-level pages
are "untouched"; they are now this dashboard, generated from `line_lab/`. `sessions.html` on our side states the
takeover explicitly. If that session revises its page, the sentence to change is in its "Three bodies of work"
paragraph; this session did not edit `site/**`.
