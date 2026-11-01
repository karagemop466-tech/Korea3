# Leaderboard competition — specification

**Status:** design published, board live at <https://karagemop466-tech.github.io/Korea3/leaderboard.html>
**Owner:** `session-c70bdb9d` · **Snapshot:** 2026-11-01

## 1. The problem being solved

A strategy leaderboard is easy to build and almost always wrong. Rank by return and you rank luck: run 20 backtests and the best one will look excellent even if every rule is worthless. The design constraint is therefore not "how do we order the winners" but **"how do we stop luck from being ordered at all"**.

Three mechanisms do the work here:

1. **A luck-adjusted score as the primary ranking key**, not raw return.
2. **A hard gate set** that a strategy must clear before it is ranked at all.
3. **A multiplicity penalty that grows with the number of strategies tested**, so a crowded board is harder to win than an empty one — which is the opposite of how most leaderboards behave.

## 2. Gates

Eight mandatory gates, defined in `scripts/gates.py` and published on the site:

| Gate | Requirement |
|---|---|
| G1 Sample size | n ≥ 200 settled bets overall, ≥ 100 in the confirmation window |
| G2 Positive expectation | ROI > 0 over the full window |
| G3 Both-window stability | ROI > 0 in 2000–2015 **and** 2016–2026 |
| G4 Multiplicity | Benjamini–Hochberg q ≤ 0.10 across the whole tested family |
| G5 Concentration | No season > 50% of total profit; ≥ 50% of seasons positive |
| G6 Price stress | Still profitable at a flat −115 |
| G7 Line-source robustness | Still profitable scored against the second in-dataset line source |
| G8 Luck-adjusted edge | Empirical-Bayes shrunk ROI ≥ 0.5% |

A gate that cannot be evaluated for lack of a source is reported as `n/a` — never as a pass. That rule exists because the natural failure mode of a gate system is to treat missing data as good news.

## 3. Scoring

```
score = 0.60 × shrunk_roi_rank
      + 0.20 × confirmation_roi_rank
      + 0.10 × robustness (G5, G6, G7 all pass)
      + 0.10 × coverage_rank (settled bets, capped at 1,000)
```

- `shrunk_roi` is the empirical-Bayes posterior mean: `observed × τ²/(τ² + SE²)`, with τ² estimated across the family. It is the only component that penalises a small sample for being small.
- Coverage is **capped** at 1,000 bets so that volume cannot buy a top rank on its own.
- Ranks, not raw values, are used inside each component so that one extreme number cannot dominate the blend.

## 4. Tiers

| Tier | Requirement | What it earns |
|---|---|---|
| Challenger | Tests complete, listed with full numbers | Nothing but publication |
| Provisional | 7 of 8 gates | Priority re-test at the next snapshot |
| Verified | 8 of 8 gates | Leaderboard slot, eligible for rewards |
| Defended | 8 of 8 at two consecutive snapshots | Top tier; drops immediately on failure |

**Rewards are paid only to Verified and Defended tiers, and are split evenly across them rather than weighted by return.** Weighting by return would reintroduce the exact bias the gates exist to remove: a strategy with a 12% ROI on 300 bets would out-earn a 3% ROI on 5,000 bets, which is backwards.

## 5. Anti-gaming rules

1. **Pre-registration.** A rule must be written and committed before its evaluation window is run. Family size feeds the FDR penalty, so adding rules after the fact taxes everyone — including the person who added them.
2. **No dropping losers.** Every tested rule is published, including the ones that fail. This is why the current snapshot shows 14 failures alongside 4 provisional results.
3. **Declared snapshot cadence.** Evaluation happens at fixed snapshots. Looking repeatedly at a live record is the temporal version of testing many rules.
4. **Price honesty.** Only the recorded price counts. Beating the close with a price nobody could get is not skill.
5. **No post-hoc trimming.** No convenient start dates, no silently excluded weeks.
6. **Audit trail.** Each entry carries its data hash, its code, and its window. Anything not reproducible is ineligible.

## 6. Current standings (snapshot 2026-11-01)

| Rank | ID | Strategy | Bets | ROI | Luck-adj. ROI | Tier |
|---|---|---|---|---|---|---|
| 1 | S14 | Wind 15+ mph: unders | 607 | +8.41% | +2.48% | Provisional |
| 2 | S16 | Week 1 unders | 425 | +5.42% | +1.22% | Provisional |
| 3 | S05 | Away team off a bye | 346 | +4.71% | +0.90% | Provisional |
| 4 | S10 | Rest edge of 4+ days to the away team | 372 | +4.30% | +0.86% | Provisional |
| 5–18 | — | Remaining rules | — | negative | negative | Fail |

No strategy is in a paid tier. That is the correct state for an honest board: **the competition can only pay out when something clears the bar, and the bar is the product.**

## 7. What would change the standings

The four provisional rules fail only G4. Two honest paths:

1. **More sample at the same edge.** Required bet counts at the observed and the shrunk edge are computed per rule in `scripts/gates.py` and published on the Single Bets page.
2. **A smaller family.** Fewer tested rules means a smaller multiplicity penalty. This is the uncomfortable implication of a statistically honest board: *the more you search, the higher the bar each result must clear*, so disciplined pre-registration is worth more than extra searching.

Both are legitimate. Neither is "run the backtest until something looks good".
