# Line-by-line verification report — session `arena/d7d4d48d-korea3`

**Date:** 2026-11-02 (UTC) · **Scope:** whole repository at `main` = `9069c3d`
**Method:** fresh code, no imports from any prior session's analysis modules.
Machine-readable results: [`report.json`](report.json) (66 checks) ·
[`link_audit.json`](link_audit.json) (99 pages). Re-run:

```bash
.venv/bin/python verification/reproduce.py
.venv/bin/python verification/link_audit.py
.venv/bin/python -m pytest tests/test_lab_*.py -q
.venv/bin/python line_lab/check_site.py && .venv/bin/python scripts/verify_site.py
```

---

## A. Builds and test suites re-run (2026-11-02)

| Suite | Result | Notes |
|---|---|---|
| `pytest tests/test_lab_*.py` | **24 passed** | Synthetic fixtures only, by design |
| `python -m nfl_lab.run` + `check_verified` | **OK** — 12 pages, 131 rows, all officially sourced; rebuild byte-identical (`git status` clean) | 0 admitted / 0 eligible / 0 verified values (fail-closed) |
| `scripts/verify_site.py` | **11/11 PASS** | Incl. checksums, 731 internal links, 450 sourced rows |
| `line_lab/check_site.py` | **OK** | 14 pages; hashes + recomputed numbers match |
| `pipeline/link_check.py` | **PASS** | 11 external sources registered |
| `bash pipeline/run_all.sh` | **Byte-identical** (`reports/`, `docs/` unchanged) | Same gate as CI `verify-and-build` |
| `python -m line_lab.build_site` | **Deterministic** (no diff before this session's nav edit) | Root dashboard regenerates cleanly |
| `line_lab/tests/test_causality.py` (script) | **Passed** | Leak/settlement/provenance checks |
| `tests/test_causality.py` (script) | **Failed at import → fixed** (see I‑01) | Now passes; outputs byte-identical |
| GitHub Pages API | `built`, source `main:/` | <https://karagemop466-tech.github.io/Korea3/> fetched live; content matches `summary.json` (16,112 selections = Σ eval-window bets) |

## B. Independent numerical reproduction — 66/66 PASS

Fresh pandas/scipy logic against `data/raw/*`, `data/derived/*`,
`line_lab/data/derived/*`. Full table in `report.json`. Highlights:

- **Provenance:** SHA-256 of all 5 raw files match `data/provenance.json` exactly.
- **Universe:** `games.csv` 7,548 rows; 7,075 REG played; seasons 1999–2026.
- **Sign convention (F01):** with home spread = `−spread_line`, home favourites
  (−7 or more) average margin +10.81 vs −8.89 for home dogs (+7 or more). The
  published convention is correct.
- **Baselines:** home cover 0.4887, over 0.4953, home win 0.5594, ties 16, OT 424.
- **Own line (B):** MAE 10.670/10.247, totals 10.859/10.593, corr 0.7996,
  agreement 0.8166, paired-gap p = 4.894×10⁻²⁴ (published ≈ 4.9×10⁻²⁴).
- **Correlations:** φ(cover×over) = 0.0086 (n = 6,784); φ(ML×cover) = 0.6724;
  break-even φ (2 legs @ −110) = 0.0975 — all exact to published precision.
- **Signals:** ROI / n / win-rate reproduced for S14, S16, S05, S10, S01 from
  `signal_bets.csv` under the documented convention (push = `result 0`, stake
  returned, excluded from n and ROI denominator).
- **Gates:** 0 PASS / 4 PROVISIONAL in the 18-rule family — confirmed.
- **Root dashboard:** all 11 strategies' ROI and n reproduced from
  `line_lab/data/derived/bets.csv` inside the registered eval window
  2006–2025. (`bets.csv` is the full ledger and also holds incomplete-2026
  rows; metrics correctly exclude them. Divergent on first pass, fully
  reconciled — not a defect.)
- **Leaderboard eligibility:** 0 in all three systems.
- **Own lines:** 164 published, 28 with market comparison — confirmed.
- **Props:** 8 rows, `measured_phi` entirely blank — confirmed programmatically.
- **F03:** `'grass '` trailing-space rows = 93 — confirmed.

*Convention note (not a defect):* the two empirical families treat pushes
differently in the denominator — `scripts/` excludes pushes from n/ROI;
`line_lab/` includes pushes in n with pnl 0 and excludes them from win-rate.
Both are documented on-site and each is internally consistent, as verified
above. Cross-family ROI comparisons should keep this in mind (effect ≤ ~0.2 pp
at observed push rates).

## C. Official sources re-opened 2026-11-02 (claim → support)

| Source | URL | Claim checked | Verdict |
|---|---|---|---|
| NFL Terms §§1.1, 1.3 | <https://www.nfl.com/legal/terms/> | Reproduction + systematic-retrieval prohibitions (basis for no-scraping rule) | **Verbatim ✓** |
| NFL Support "What is a money line?" | <https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line> | "Most often, the betting odds for point spread are -110" + push-returns-wager; F08 body/title swap | **Verbatim ✓; swap still live** |
| NFL Tiebreaking Procedures | <https://www.nfl.com/standings/tie-breaking-procedures> | "Tie games count as one-half win and one-half loss for both clubs" | **Verbatim ✓** |
| DraftKings Understanding Odds (KB0010466 v4.0, 2026-10-06) | <https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466> | −110 ⇒ wager $110 to profit $100; multiplier incl. stake | **Verbatim ✓** |
| FanDuel House Rules (CT), eff. 2026-07-30 | <https://www.fanduel.com/fanduel-sportsbook-house-rules-ct> | Page live; correlated-parlay sentence relied on prior 2026-11-01 verification | **Partial — see I‑05** |
| nflverse/nfldata pinned commit | <https://github.com/nflverse/nfldata/tree/a270278f3ac4e937295fe6a27814b3c4a2b62645> | Commit exists, dated 2026-11-01, files present | **✓** (Tier 3 — NFL publishes no lines) |
| Live site root | <https://karagemop466-tech.github.io/Korea3/> | Dashboard serving; figures match `summary.json` | **✓** |

19-source register: `nfl_lab/sources.json`; tiered register with exact-claim
mapping: `research/sources.md`. Sources support the specific statements shown;
none endorses this project or any betting performance.

## D. Link audit — 99 pages, 0 live-surface broken links

4,136 external links across 18 domains inventoried. Internal-link findings:

| Category | Count | Disposition |
|---|---|---|
| Live surface (root, `site/`, `docs/`, `verified/`, `session-398c4b58/site/`) | **0** | Merge gate satisfied |
| `site/prior/**` byte-identical archive mirrors | 22 | Known preservation trade-off; not edited (see I‑03) |
| `audit/flagged.html` → `../style.css` | 1 | Audit-owned; open PR #19 (see I‑04) |

## E. Irregularities found **this session**

| ID | Finding | Severity | Action |
|---|---|---|---|
| I‑01 | `tests/test_causality.py` imported non-existent `pipeline.markets` / `pipeline.core` (stale duplicate of `line_lab/tests/test_causality.py`); errored on collection. Not referenced by any CI workflow. | Low (test hygiene) | **Fixed:** 2-line import change to `line_lab.*`, matching its working twin. Test now passes; regenerated `data/derived/tests.json` byte-identical. |
| I‑02 | `data/derived/blend_results.json` contains a bare `NaN` (`total.out_of_sample_blend.blend_beats_market_pvalue`; undefined because the optimal blend weight is 0, so blend ≡ market). Invalid strict JSON; Python's `json` tolerates it; not rendered on the site (`verify_site.py` placeholder scan passes). | Low | **Flagged, not edited** (other session's artifact). Fix request logged in `COORDINATION.md`: emit `null` + reason string. |
| I‑03 | 22 internal links inside `site/prior/**` + copies do not resolve from the mirror location (e.g. `site/index.html` from `/site/prior/`). Consequence of the byte-identical preservation contract. | Low (archive UX) | **Flagged.** Editing would break byte-identity; live surfaces unaffected. |
| I‑04 | `audit/flagged.html` references `../style.css` (404; root stylesheet is `assets/style.css`). Owned by session `65d448da`; **PR #19 open and `CONFLICTING`** at this check. | Low (one page unstyled) | **Flagged, not edited.** Owner to rebase PR #19. |
| I‑05 | FanDuel (CT) correlated-parlay sentence could not be re-located in this session's partial read of the (long) live page; page itself is live (effective 2026-07-30). Prior verbatim verification stands dated 2026-11-01. | Info | **Marked partial.** No claim strengthened on this session's evidence. |

Inherited register (F01–F09, B01–B06, R01–R03, V01–V03) republished in
[`../CONSOLIDATED_EXECUTIVE_SUMMARY.md` §7](../CONSOLIDATED_EXECUTIVE_SUMMARY.md)
and on `/flagged.html` + `/verified/flagged.html`. Statuses unchanged except
F01/F03/F08 independently re-confirmed above.

## F. What this session changed

| File | Change |
|---|---|
| `COORDINATION.md` | Claim (D01–D05) + completion record + I‑02 fix request |
| `verification/reproduce.py`, `report.json` | 66-check independent reproduction |
| `verification/link_audit.py`, `link_audit.json` | 99-page link audit with live/archive classification |
| `verification/REPORT.md` | This report |
| `CONSOLIDATED_EXECUTIVE_SUMMARY.md`, `executive.html` | Consolidated summary (repo + site page) |
| `line_lab/build_site.py` | One nav entry + one sessions-index row (integration role); root pages regenerated deterministically |
| `tests/test_causality.py` | I‑01 import fix (2 lines) |
| `.github/workflows/reverify.yml` | CI: reproduce + link audit on push/PR |
| `README.md` | Seventh body-of-work row + pointers |

No other session's data, pipeline, derived artifacts or site directories were
modified. Nothing was deleted.
