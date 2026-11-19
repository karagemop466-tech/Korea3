# Skill Re-check — Executive Summary

**Session:** `arena/ae3c9f8b-korea3` (2026-11-19, UTC) · **Branch:** `arena/ae3c9f8b-korea3` → `main`
**Surface:** `skill_recheck/` — the independent recomputation layer beside the canonical `skill_lab/` (PR #115)

## The finding (L12, high)

Two sessions built the same requirement pair (C03 proper-score ranking, C04 control baselines)
concurrently. PR #115's `skill_lab` merged first and is canonical; this lab does not modify it.
**But its per-strategy leaderboard is invalid**, and the defect is proven, not suspected:

- `skill_lab/metrics.py` defines `settled()` as `outcome ∈ {0, 1}` and scores `y = outcome`.
- The ledger codes **−1 = loss, 0 = push, +1 = win** (`line_lab/evaluation.py`; pnl settles −1 to the
  full stake and 0 to zero).
- Consequence: every losing bet — **8,653 of 16,439 rows** — is excluded from scoring, and every push
  (296) is relabelled as a loss. The published Brier skill is computed **on winning bets only**:
  selection on the outcome. The published "5 of 8 strategies significantly better than the market"
  is an artifact of that filter.
- **Proof by reproduction:** this lab re-derives each published BSS under their own filter and
  matches it to 10 decimal places for all 8 strategies (see the reconciliation table on
  `index.html`; verified on every rebuild by `skill_recheck/check.py`).
- Two secondary defects in the same file: its bootstrap receives the full group (including pushes
  and excluded rows) while its point estimate uses the settled subset, so its CI is not an interval
  for its point; and its controls read `market_lab/data/results_feed.csv`, whose outcome coding
  differs from the ledger's, making controls and strategy rows incomparable. The controls themselves
  are internally consistent and unaffected by the headline defect.

## The corrected leaderboard

Computed on the full settled set (losses included, pushes properly excluded), scoring each
strategy's `model_prob` against the **de-vigged market probability** of the same side on the same
events (`line_lab/markets.devig_two_way` — the repository's own convention, and the one the brief's
vig-free decomposition requirement calls for):

| Rank | Strategy | n scored | BS model | BS market | BSS (ratio) | Week-cluster bound | Game-cluster bound | p | BH q | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | S7 Referee crew total tendency | 2,130 | 0.2506 | 0.2499 | −0.0027 | −0.0070 | −0.0071 | 0.9080 | 1.0000 | not eligible |
| 2 | S8 Backup-quarterback fade | 718 | 0.2505 | 0.2496 | −0.0036 | −0.0089 | −0.0093 | 0.8920 | 1.0000 | not eligible |
| 3 | S5 Divisional home underdog | 640 | 0.2507 | 0.2502 | −0.0020 | −0.0129 | −0.0136 | 0.6490 | 1.0000 | not eligible |
| 4 | S4 Rest asymmetry | 1,017 | 0.2509 | 0.2498 | −0.0043 | −0.0151 | −0.0140 | 0.8130 | 1.0000 | not eligible |
| 5 | S6 Weather under | 536 | 0.2528 | 0.2493 | −0.0140 | −0.0256 | −0.0238 | 0.9985 | 1.0000 | not eligible |
| 6 | S3 Scoring-profile totals | 3,592 | 0.2580 | 0.2501 | −0.0314 | −0.0439 | −0.0442 | 1.0000 | 1.0000 | not eligible |
| 7 | S1 Elo margin vs closing spread | 3,733 | 0.2608 | 0.2504 | −0.0417 | −0.0568 | −0.0559 | 1.0000 | 1.0000 | not eligible |
| 8 | S2 Elo margin vs closing moneyline | 2,707 | 0.2346 | 0.2224 | −0.0545 | −0.0743 | −0.0741 | 1.0000 | 1.0000 | not eligible |

**0 of 8 eligible: every ranking bound is negative.** This agrees with line_lab's own published
per-market evaluation (its `brier_skill` values, constant within market — flag L10 — are all
negative) and with the repository's standing conclusion. It disagrees with PR #115's table for the
reason given above.

## Controls (C04) and the luck anchor

Nine global CONTROL rows in two labeled universes, settled from the pinned scores, never ranked:

- **Universe A** (events where the pinned closing-line file carries both odds; moneylines
  2006–2018, spread/total odds 2017–2018): majority side loses −2.0% to −4.7% ROI; random
  (seed 20261119) −3.4% to +4.2%.
- **Universe B** (every 2006–2025 game with a market line, flat −110 fallback per
  `research/methodology.md`; imputed share 1.0 published): favourite-by-line **−6.76%** over 5,199
  games; random −8.12% (spread) / −2.66% (totals).

Every control loses roughly the vig: the no-skill ROI floor is now published beside the leaderboard,
which is what "remove luck from the equation" requires.

## A16 — two-sided what-would-change-our-mind

Per ranked strategy, computed deterministically: the additional bets at the observed BSS that would
move the lower bound to zero (delta method), and the BSS level that would drop the bound to ≤ 0
(1.645 × SE). Published on `index.html`.

## Verification

- `python3 -m skill_recheck.check` — **PASS**: independent recomputation of every published number
  from the raw CSVs at published precision (checksums, counts, Brier scores, all 24 bootstrap cells,
  q-values, A16, both control universes, the L08 cross-check, the L12 reproduction, page discipline:
  63 table rows all source-linked, every blank flag-referenced, no wall-clock stamp), and
  determinism (second build byte-identical).
- `tests/test_skill_recheck.py` — 16 unit tests on synthetic fixtures; full suite 40 passed.
- `verify/source_audit.py --max-unsourced 0 --allow-dirs session-398c4b58,qa` — PASS (0 gated rows).
- `verify/linkcheck_all.py` — PASS (0 broken local links).

## Other irregularities published here (flags L01–L11)

L08 (high): the pinned `closing_lines.csv` outcome column is inverted for 5 games (18 rows) versus
the pinned scores — settlement recomputed from scores, disagreement rows published.
L10: `summary.json` publishes market-level brier_skill under per-strategy labels.
L11: closing odds exist only for part of the window; universe B is 100% −110-imputed (labeled).
L01–L07, L09: parlay marginal-product probabilities, futures without model probabilities, the
S1–S11/S01–S18 ID collision, third-party dataset provenance, single-seed random control,
supplementary benchmarks outside the FDR family, sandbox egress limits, inherited pre-registration.

**Request logged for the `skill_lab` owner:** adopt the corrected filter or withdraw the 5-of-8
claim; nothing here overwrites their files.

**Disclaimer.** Research and engineering sample. **Nothing here is betting advice.** No strategy in
this repository has demonstrated skill at the required significance level.
