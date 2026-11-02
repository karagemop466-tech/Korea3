# NFL Line Origination — Consolidated Executive Summary

**Date:** 2026-11-02 (UTC) · **Session:** `arena/d7d4d48d-korea3` (independent re-verification + final integration)
**Live site:** <https://karagemop466-tech.github.io/Korea3/> · **This summary as a page:** <https://karagemop466-tech.github.io/Korea3/executive.html>
**Verification evidence:** [`verification/REPORT.md`](verification/REPORT.md) · [`verification/report.json`](verification/report.json) · [`verification/link_audit.json`](verification/link_audit.json)

> Every number below was **independently recomputed on 2026-11-02** from the pinned
> dataset by fresh code (`verification/reproduce.py`, 66/66 checks PASS). Prior
> sessions' summaries remain in place: [`EXECUTIVE_SUMMARY.md`](EXECUTIVE_SUMMARY.md)
> (empirical pipeline), [`LINE_LAB_EXECUTIVE_SUMMARY.md`](LINE_LAB_EXECUTIVE_SUMMARY.md)
> (root dashboard), [`VERIFIED_EXECUTIVE_SUMMARY.md`](VERIFIED_EXECUTIVE_SUMMARY.md)
> (official-evidence-only workbench). This document consolidates, it does not replace.

---

## 1. Bottom line — the five findings that matter

| # | Finding | Evidence (recomputed 2026-11-02) | Source |
|---|---|---|---|
| 1 | **The own line works as research, not as edge.** Walk-forward spread MAE 10.670 pts vs 10.247 for the closing line (paired p ≈ 4.9×10⁻²⁴); total 10.859 vs 10.593. The market is better, consistently. | `data/derived/model_predictions.csv` (n = 6,827) | [Pinned dataset](https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv) |
| 2 | **No strategy passed validation — in either family.** 0 of 18 rules cleared all 8 gates (scripts family); 0 of 11 cleared all 9 gates (root-dashboard family). Best raw ROI +8.41% (n = 607) fails multiplicity (q = 0.288). | `data/derived/gates_results.csv`; `line_lab/data/derived/summary.json` | [Break-even −110 price: NFL Support](https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line) |
| 3 | **Same-game parlays have no hidden correlation to harvest.** Spread × total φ = +0.0086 (95% CI −0.0162 … +0.0332, n = 6,784) — zero. A 2-leg parlay at −110 needs φ ≥ 0.0975 to break even. That gap is the margin. | `data/derived/corr_same_game.csv`; analytic break-even | [Pinned dataset](https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv); [DraftKings odds](https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466) |
| 4 | **The one real correlation is already priced.** Moneyline × spread (same team) φ = 0.6724. Operators re-price it as a same-game parlay or refuse correlated legs. | `data/derived/corr_same_game.csv` | [FanDuel House Rules (CT)](https://www.fanduel.com/fanduel-sportsbook-house-rules-ct); [DraftKings SGP](https://support.draftkings.com/dk/en-us/what-is-a-same-game-parlay-sgp-bet?id=kb_article_view&sysparm_article=KB0010719) |
| 5 | **Player props: framework only, no numbers claimed.** No licensed, machine-readable prop-line source exists here. All 8 documented combos have measured φ **blank / UNVERIFIED**. | `data/derived/props_framework.csv` (8 rows, φ blank) | [Flagged B01](flagged.html) |

**Leaderboard consequence:** 0 reward-eligible strategies. The board pays only
gate-clearing tiers by design, so the correct current payout is zero. Simulated
no-skill families produce a "best" strategy averaging +5.4% ROI — luck, ranked,
looks exactly like skill; the gates exist to refuse that ranking.

## 2. Requirements checklist (brief → delivery)

| Requirement | Status | Where | Verification |
|---|---|---|---|
| Originate own NFL lines (no market input) | **Done** | `scripts/model.py` (4 variants, walk-forward, 6,827 games); `line_lab/` Elo/rating model | MAE reproduced exactly (§1.1) |
| Own lines for upcoming fixtures | **Done** | `data/derived/own_lines_upcoming.csv` — 164 games, 28 with a posted market line | Row counts reproduced |
| Single-bet signals | **Done** | 18 pre-registered rules (`scripts/signals.py`) + 11 (`line_lab/strategies.py`) | ROI/n/win-rate reproduced per rule |
| Parlays | **Done** | Joint-hit-rate + EV grid (`data/derived/parlay_math.csv`); 2 cross-game parlay strategies (S9/S10 root family) | Break-even φ derived analytically; EV at φ=0: 2-leg −8.88%, 3-leg −13.03% |
| Player-prop combos | **Framework done; values blank** | `scripts/props.py`, 8 combos with mechanism + required φ | Blank-φ discipline verified programmatically |
| Validation gates per strategy | **Done** | 8 gates (`scripts/gates.py`), 9 gates (`line_lab/evaluation.py`), 10 fail-closed gates (`nfl_lab/validation.py`) | 0 pass in every family — reproduced |
| Correlation values | **Done (team markets)** | Same-game, cross-game, signal-pair (`scripts/correlation.py`) | φ recomputed to 4 decimals |
| Remove luck / skill-selective strategies | **Done (as far as statistics allows)** | BH FDR, empirical-Bayes shrinkage (31.8% family shrink), block bootstrap, permutation luck band, price stress at −115, second-source robustness | Shrunk ROI published per rule; best shrunk +2.48% still fails G4 |
| Leaderboard competition + rewards | **Spec + live board; 0 eligible** | `research/leaderboard.md`; `/leaderboard.html`; eligibility-only rewards in `verified/` | Eligible count = 0 in all three systems |
| Executive summary | **Done** | This file + three prior summaries | — |
| GitHub Pages dashboard, tables, sourced rows | **Live** | Root (14 pp.), `/site/`, `/docs/`, `/verified/` (12 pp., 131 rows), `/audit/`, `/qa/` | 0 broken internal links across 109 pages (base-aware audit; cross-confirmed by `qa/check_links.py`) |
| Line-by-line official-source verification | **Done** | `research/sources.md`, `nfl_lab/sources.json` (19 primary sources), re-opened 2026-11-02 | See §6 |

## 3. Own-line origination (headline model, variant B)

| Metric | Own line | Closing line | n | Source |
|---|---|---|---|---|
| Spread MAE (pts) | 10.670 | 10.247 | 6,827 | [Pinned dataset](https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv) |
| Total MAE (pts) | 10.859 | 10.593 | 6,827 | [Pinned dataset](https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv) |
| Corr. (own spread vs close) | 0.7996 | — | 6,827 | [Pinned dataset](https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv) |
| Side agreement with market | 81.66% | — | 6,827 | [Pinned dataset](https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv) |
| Out-of-sample blend gain | **none** (+0.008 pts worse, p = 0.30) | — | 2,747 | `data/derived/blend_results.json` |

Market baselines (7,075 regular-season games, 1999–2026): home cover **48.87%**,
over **49.53%**, home win **55.94%**, ties **16**, OT games **424**. Break-even at
−110 is **52.381%** (110/210) — the bar every ROI below is measured against
([NFL Support](https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line);
[DraftKings Understanding Odds](https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466) — both re-opened and confirmed verbatim 2026-11-02).

## 4. Single bets, parlays, props — what the tests say

**Singles (18-rule family, gates G1–G8).** 0 pass; 4 provisional (7/8, failing only
multiplicity G4): S14 Wind 15+ mph unders (+8.41%, n = 607, q = 0.288, luck-adjusted
+2.48%), S16 Week 1 unders (+5.42%), S05 Away off a bye (+4.71%), S10 Rest edge ≥ 4
days to away team (+4.30%). Gate pass counts: G1 17/18 · G2 5/18 · G3 5/18 · **G4 0/18**
· G5 13/18 · G6 5/18 · G7 9/18 (2 n/a) · G8 6/18. The own-line disagreement rules
(S01/S02) are the *worst* performers (−6.95%, −6.54%) — when our line fights the close,
the close wins.

**Singles (11-strategy root-dashboard family, 9 gates, 2006–2025).** 0 eligible; best
full-sample ROI +0.58% (S6 Weather under, 95% CI −7.51% … +8.17%); every model
strategy has negative Brier skill vs the de-vigged market. A simulated best-of-11
*no-skill* family averages +5.4% ROI (95th pct +16.3%) — the luck band any real
candidate must clear.

**Parlays.** Measured same-game φ values: home cover × over **+0.0086**, favourite
cover × over −0.0011, home ML × over −0.0139, home ML × home cover **+0.6724**
(joint 43.9% vs 27.2% independent). Cross-game pooled φ = −0.0239 (p = 0.10 →
independent). At φ = 0 the vig compounds to EV −8.88% (2 legs) / −13.03% (3 legs) at
−110. Conclusion: cross-game parlays donate compounded vig; same-game spread×total
offers no correlation compensation; the one compensated pair is re-priced by
operators ([FanDuel CT correlated-parlay rule](https://www.fanduel.com/fanduel-sportsbook-house-rules-ct);
[DraftKings SGP rules](https://support.draftkings.com/dk/en-us/what-is-a-same-game-parlay-sgp-bet?id=kb_article_view&sysparm_article=KB0010719)).

**Player-prop combos.** Eight combos documented (P01–P08) with expected sign,
mechanism, pricing risk and required break-even φ (0.0975 at −110/−110). Measured φ:
**blank in every row — UNVERIFIED.** No prop price, hit-rate or correlation is claimed
anywhere in this repository. Participation/void mechanics cite operator house rules
only (see F09 caveat on the dated DraftKings copy).

## 5. Leaderboard & rewards — current state

| System | Family | Gates | Eligible | Rewards |
|---|---|---|---|---|
| `scripts/` + `site/` | 18 rules | 8 | **0** (4 provisional) | Verified/Defended tiers only → none paid |
| `line_lab/` root dashboard | 11 strategies | 9 | **0** (max 4/9) | Reward points blank (not zero) |
| `nfl_lab/` verified workbench | 8 hypotheses | 10, fail-closed | **0** (0 admitted inputs) | Pool/sponsor/legal unverified → blank |

Scoring is luck-adjusted by construction (empirical-Bayes shrunk ROI is the primary
rank key; coverage capped; rewards split evenly across qualifying tiers, never
return-weighted). Full spec: `research/leaderboard.md`. Honest paths to a paid tier:
more sample at the observed edge (per-rule required counts published) or a smaller
pre-registered family (cheaper multiplicity penalty). "Search until something looks
good" is precisely what the gates refuse.

## 6. Verification — what "line by line" meant here

- **Independent reproduction (this session): 66/66 checks PASS** — checksums, sign
  convention, baselines, both models' MAE/correlation/agreement, φ values, break-even
  arithmetic, per-rule ROI/n/win-rate in *both* families, gate counts, leaderboard
  eligibility, own-line counts, prop-blank discipline. (`verification/reproduce.py`)
- **Builders re-run byte-identical:** `nfl_lab.run`, `pipeline/run_all.sh`,
  `line_lab.build_site` (before this session's additive nav entry).
- **Checkers:** `scripts/verify_site.py` 11/11 · `line_lab/check_site.py` OK ·
  `nfl_lab.check_verified` OK (12 pages, 131 rows) · `pipeline/link_check.py` PASS ·
  24 synthetic unit tests pass.
- **Link audit (new, repo-wide, `<base>`-aware):** 109 HTML pages, 4,303 external links
  inventoried, **0 broken internal links anywhere** (`verification/link_audit.py`;
  independently cross-confirmed by session `d4478fd5`'s `qa/` crawl: 108 pages, 0 broken,
  38 checks, 0 mismatches — same substantive conclusions).
- **Official sources re-opened 2026-11-02:** NFL Terms §§1.1/1.3 (verbatim ✓),
  NFL Support −110/push article (verbatim ✓; F08 title/body swap confirmed still
  live), NFL Tiebreaking Procedures (verbatim ✓), DraftKings Understanding Odds
  KB0010466 v4.0 (verbatim ✓), nflverse pinned commit (exists ✓), FanDuel CT House
  Rules (page live; exact sentence not re-located this session → partial, I‑05),
  live Pages site (serving current `main` ✓).
- **Source tiers are disclosed, never blurred:** T1 official NFL (rules/terms/ties),
  T2 licensed operators (prices-as-defined, settlement, SGP policy), T3 pinned open
  dataset (all line *values* — the NFL publishes none). A URL is not a redistribution
  licence; that is why the verified layer stays blank.

## 7. Flagged register (consolidated; live on /flagged.html)

Full text: [`research/flagged.md`](research/flagged.md) and the site's **Flagged for
Review** pages (root + `/verified/flagged.html`). These do not block publication;
they block *claims*.

| ID | Item | Status |
|---|---|---|
| F01 | Dataset `spread_line` sign inverted vs convention | Resolved; re-confirmed this session (favourites +10.81 vs dogs −8.89 mean margin) |
| F02 | Two in-dataset line sources agree only 67.3% (spreads) / 61.7% (totals) | Mitigated via gate G7 |
| F03 | `'grass '` trailing-space duplicate, 93 rows | Resolved (normalised); count re-confirmed |
| F04–F05 | Missing roof/surface; `temp`/`wind` with **no provenance** (2,213 rows) | Unverified; labelled; S14 carries the caveat |
| F06 | 2026 season in progress at snapshot | Resolved by exclusion |
| F07 | 26.9% of games lack a recorded price → −110 imputed, share published per rule | Largest methodological compromise; disclosed |
| F08 | Two NFL Support article bodies swapped (moneyline ↔ point spread) | Flagged; **still live 2026-11-02** |
| F09 | DraftKings house-rules copy dated 2023-06-01 | Flagged; confirm against live page |
| B01–B06 | No prop lines · no injuries · no weather ground truth · no penalties · no venue coords · no pre-2021 openers | Blank + flagged; nothing inferred |
| R01–R03 | 0 strategies pass · own line worse than close · spread×total φ ≈ 0 | Published findings |
| R1–R6 (`92c7b263`) | Evidence-chain gaps in `nfl_lab` admission (rules/quote/forecast provenance resolution); NWS PDF content unconfirmed; AP attribution on NFL.com RG story | Fix before any licensed input is admitted; routed to `nfl_lab` owner; empty-input results unaffected ([review](reviews/92c7b263/independent-review.md)) |
| I‑01 | Root `tests/test_causality.py` imported non-existent `pipeline.*` modules | **Fixed this session** (2-line import fix; outputs byte-identical) |
| I‑02 | `data/derived/blend_results.json` contains bare `NaN` (invalid strict JSON; not site-rendered) | Flagged; fix requested in COORDINATION.md |
| I‑03 | Internal links in `site/prior/**` mirrors didn't resolve from the mirror path | **Fixed by `d4478fd5` (PR #42)** via `<base href="/Korea3/">` on preserved copies; 0 broken repo-wide |
| I‑04 | `audit/flagged.html` → `../style.css` 404 | **Fixed by `d4478fd5` (PR #42)** (root `style.css` restored); PR #19 separately open/conflicting (audit-owned styling) |
| I‑05 | FanDuel CT correlated-parlay sentence not re-located in this session's partial read | Partial re-check; prior verbatim check stands (2026-11-01) |
| V‑items | Repo named `Korea3`; started as an 8-byte README | Recorded; identity untouched |

## 8. How to use this — and what is *not* claimed

- **Use it as measurement:** vig size, luck-band width, which leg pairs are actually
  dependent, and the exact sample sizes an edge claim would need.
- **Do not use it as picks.** No strategy here is claimed profitable; no prop
  correlation exists to trade on; the verified layer deliberately publishes zero
  empirical values until licensed official data arrives.
- **Next honest steps** (backlog B01–B06): licensed prop-line feed → injuries/inactives
  → weather ground truth → fixed snapshot cadence so multiplicity stays controlled
  over time. Each turns a flagged blank into research; none is shortcut by inference.

## 9. Reproduce everything (no manual input)

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python verification/reproduce.py        # 66/66 independent checks
.venv/bin/python verification/link_audit.py       # 100-page link audit
.venv/bin/python -m pytest tests/test_lab_*.py -q # 24 synthetic tests
.venv/bin/python -m nfl_lab.run && .venv/bin/python -m nfl_lab.check_verified
.venv/bin/python line_lab/check_site.py && .venv/bin/python scripts/verify_site.py
bash pipeline/run_all.sh                          # byte-identical docs/reports
```

**Site map:** root dashboard `/` · this summary `/executive.html` · empirical site
`/site/` · second build `/docs/` · verified workbench `/verified/` · audit `/audit/`
· archives `/site/prior/`, `/site/prior-d118ca7e/` · session index `/sessions.html`.
**Task board & merge record:** [`COORDINATION.md`](COORDINATION.md).
