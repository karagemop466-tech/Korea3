# luck_lab — control baselines, proper-score skill, pre-registration and escrow

Adds the two measurement layers the brief asked for that no other page in this repository had:

| Requirement (brief) | Where it is met |
|---|---|
| "Add a control baseline (random picks; favorites only) to every leaderboard run" | `controls.html` — 9 baselines on the same games and the same closing prices, incl. a closed-form coin flip per market |
| "Rank with proper scores and uncertainty, not win rate: Brier skill against a benchmark, game-cluster lower bound, multiplicity adjustment" | `skill.html` — Brier and log-loss skill vs the de-vigged closing line, game-cluster bootstrap bounds, Benjamini-Hochberg across the tested family |
| "Compute and publish the removal-of-luck panel on the site dashboard" | `index.html` — the panel, rendered from the two files above |
| "Pre-register every strategy … freeze a rule before it sees data; the commit hash is the registration" | `prereg.html` — 19 registrations, `rule_hash` over rule text + gates + window, recomputed from source by the gate |
| "Add a two-sided 'what would change our mind' field to every strategy entry" | `prereg.html` — both sides frozen per row |
| "Two-stage skill leaderboard: proper-score qualification, then prospective CLV/ROI escrow" | `escrow.html` — stage, shortfall, demotion verdict, empty prospective ledger |
| "Define a demotion gate that sends a live strategy back to paper" | `escrow.html` — applied to all 11 scored strategies |
| "Publish every reward cell or leave it blank with a reason" | `escrow.html` — blank with the reason, per row |

## Layout

```
luck_lab/lib.py         stdlib statistics: devig, settlement, Wilson, cluster bootstrap, BH, n-to-significance
luck_lab/controls.py    -> data/controls.json   control baselines + the vig they pay
luck_lab/skill.py       -> data/skill.json       proper scores, bounds, calibration, luck statistics
luck_lab/registry.py     -> data/preregistration.json + data/escrow_ledger.jsonl
luck_lab/build.py       -> the 8 pages, from the JSON only
luck_lab/check.py       the gate: determinism, reproducibility, rule-freeze, reconciliation, identities
.github/workflows/luck-lab.yml  runs check.py on every push and pull request
```

## Rules this desk follows

* Standard library only. No pandas/numpy/scipy, no network, no clock in the compute path, so the CI job
  installs nothing and a rebuild is byte-identical.
* Prices are tier `dataset` (the pinned nflverse files). They may score a strategy; they may not be cited as
  a league fact. The brief's "officially sourced numbers" requirement is **not** met by any price on this desk,
  and every page says so.
* A value no source printed is blank with a link to `flagged.html`. Never 0, never a guess.
* Backtest numbers are labelled backtest and are never promoted. The promotion path is the escrow ledger,
  which starts empty by construction.

## Reproduce

```bash
python3 luck_lab/controls.py && python3 luck_lab/skill.py && python3 luck_lab/registry.py
python3 luck_lab/build.py && python3 luck_lab/check.py
```
