# Skill Lab — Executive Summary

**Session:** `arena/3d29863c-korea3` (2026-11-19, UTC) · **Branch:** `arena/3d29863c-korea3` → `main`
**Surface:** `skill_lab/` — live at `https://karagemop466-tech.github.io/Korea3/skill_lab/index.html`

## What this is

The Skill Lab ranks NFL line-origination strategies by **prediction skill, not win rate or ROI**, and
publishes **no-skill control baselines** beside every strategy so skill can be separated from luck. It
satisfies two readiness-register requirements that were marked **NOT BUILT**:

- **C03** — *Rank with proper scores and uncertainty, not win rate*: benchmark-relative Brier skill
  against the closing line, a game-cluster bootstrap confidence interval, and a multiplicity adjustment.
- **C04** — *Add a control baseline (random picks; favourites only) to every leaderboard run*.

It is built entirely on data already pinned and committed in the repository. **No network, no nfl.com
access, no manual input.** Every number is deterministic arithmetic over the pinned nflverse commit
`a270278f3ac4e937295fe6a27814b3c4a2b62645`.

## The metric

The headline metric is the **benchmark-relative Brier skill score (BSS)**:

```
BSS = Brier(market_prob, outcome) − Brier(model_prob, outcome)
```

computed over **settled** bets (pushes excluded from Brier and counted separately as *n push*).
`model_prob` is a strategy's predicted probability for the side it selected; `market_prob` is the
closing line's implied probability for that same side. **BSS > 0 = the strategy predicts the outcome it
bet on better than the market; BSS < 0 = worse.** This is the standard Brier Skill Score direction
(reference minus model).

- **Uncertainty:** game-cluster bootstrap (resample by season-week), 2,000 replicates, 95% percentile
  interval and a one-sided p-value (skill > 0).
- **Multiplicity:** Benjamini–Hochberg FDR across the ranked strategies; Bonferroni published alongside.
- **n is published with every value** (requirement A07): settled n and push n on every row.

## Control baselines (C04)

Computed on the verified, settled results-feed universe (`market_lab/data/results_feed.csv`, 20,490
rows; 20,190 verified). The market benchmark and favourites-only predict at the market's own implied
probability, so their BSS is 0 by construction; their value is the **ROI floor** a no-skill bettor realises.

| Control | Brier | BSS vs market | ROI | n |
|---|---|---|---|---|
| Market benchmark (closing implied prob) | 0.2203 | 0.0000 (reference) | — | 8,540 |
| Favourites-only | 0.2205 | 0.0000 | **−0.0413** | 4,254 |
| Random 50/50 picks | 0.2500 (analytic) | **−0.0294** | −0.0644 (seeded) | 4,254 |

Favourites-only loses to the vig (−4.13% per unit, game-cluster bootstrapped). Random 50/50 sits below
the market on Brier. These are the no-skill lines every strategy is measured against.

## Result — strategy leaderboard

11 pre-registered strategies; **8 ranked** (parlays held behind the joint-evidence gate, futures left
blank). **5 of 8 are significantly better than the market after BH FDR**; 3 are worse.

| Rank | Strategy | Market | n settled | BSS | 95% CI | p | BH q |
|---|---|---|---|---|---|---|---|
| 1 | S2 Elo margin vs closing moneyline | ML | 991 | **+0.1073** | [0.1035, 0.1112] | 0.0000 | 0.0000 |
| 2 | S1 Elo margin vs closing spread | ATS | 1,989 | **+0.0748** | [0.0720, 0.0775] | 0.0000 | 0.0000 |
| 3 | S3 Scoring-profile totals | TOTAL | 1,850 | **+0.0731** | [0.0709, 0.0752] | 0.0000 | 0.0000 |
| 4 | S4 Rest asymmetry | ATS | 547 | **+0.0242** | [0.0212, 0.0273] | 0.0000 | 0.0000 |
| 5 | S7 Referee crew total tendency | TOTAL | 1,076 | **+0.0140** | [0.0118, 0.0161] | 0.0000 | 0.0000 |
| 6 | S8 Backup-quarterback fade | ATS | 370 | −0.0028 | [−0.0052, −0.0006] | 0.9925 | 1.0000 |
| 7 | S6 Weather under | TOTAL | 289 | −0.0044 | [−0.0107, 0.0014] | 0.9290 | 1.0000 |
| 8 | S5 Divisional home underdog | ATS | 332 | −0.0266 | [−0.0300, −0.0232] | 1.0000 | 1.0000 |

**Key finding — skill ≠ profit.** The Brier skill results and the project's earlier ROI results are not
contradictory: a strategy can predict an outcome better than the market (lower Brier) and still not
profit, because it bets selectively on underdogs whose vig consumes the edge. This is precisely why the
brief separates **signal** from **staking** and ranks by **skill, not ROI**. The control baselines show
the no-skill ROI floor (−4.1% for favourites) that any profitable staking plan must beat.

**Gated / unverified (not ranked):** S9 and S10 (two-leg parlays) carry a computed BSS but are held
behind the **joint-evidence gate (C01, NOT MET)** — a combo may only be ranked when a validated joint
probability and the operator's void/push rules are both available. S11 (season win-total futures) has
no `model_prob` in the pinned data, so its Brier is **blank and flagged**, never inferred.

## Verification performed

- `python3 -m skill_lab.build` → 11 strategies, 8 ranked, 5 with BSS > 0, 5 significant after BH.
- `python3 -m skill_lab.check --determinism` → **PASS**: 3 pages, every table row carries a source
  link, internal links resolve, external links on the allow-list, BSS = Brier(market) − Brier(model) on
  every row with the sign enforced, skill ranks are a permutation, BH q-values recompute from the
  published p-values, controls are well-formed, and **two consecutive builds are byte-identical**.
- Repo-wide gates on the tree, both **PASS**: `verify/source_audit.py --max-unsourced 0`
  (0 gated unsourced rows; skill_lab rows classified *dataset* via the pinned GitHub source) and
  `verify/linkcheck_all.py` (253 pages, 0 broken local links).
- CI: new `.github/workflows/skill-lab.yml` rebuilds, runs the fail-closed checker with determinism,
  asserts `git diff --exit-code -- skill_lab/`, then runs the repo-wide source audit and link check.

## Irregularities / flags (published on `skill_lab/flagged.html`, non-blocking)

- **S11 UNVERIFIED** — no `model_prob` in the pinned bets.csv; Brier and BSS left blank.
- **S9, S10 GATED** — parlay joint-evidence gate (C01) not met; computed but not ranked.
- **CTRL-RND SEED-DEPENDENT** — the random-pick ROI is a single seeded realisation (seed 20261119); its
  Brier (0.25) is analytic and stable, the ROI is not.
- **A09 open** — these are *backtest* skill metrics. Requirement A09 (forbid backtest numbers from the
  *live* promotion leaderboard) remains open; this surface is the separate skill-evaluation layer and is
  labelled as such on the page.

## Sources (pinned)

- `line_lab/data/derived/bets.csv` — per-bet `model_prob`, `market_prob`, `outcome` for the 11 strategies.
- `market_lab/data/results_feed.csv` — verified, settled market-side universe (re-settled against the
  official final score) for the control baselines.
- nflverse/nfldata @ `a270278f3ac4e937295fe6a27814b3c4a2b62645` — the pinned source of all market
  numbers and scores. Tier 3 open dataset (the NFL does not publish spreads/totals/prices); see
  `data/provenance.json`.

**Disclaimer.** Research and engineering sample. **Nothing here is betting advice.** Brier skill
measures prediction accuracy on the historical bet universe; it does not guarantee future profit, and
no strategy here is promoted to live staking.
