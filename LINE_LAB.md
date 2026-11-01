# NFL Line Lab — project documentation

> This is the documentation for the analysis project owned by session `arena/d118ca7e-korea3`.
> The repository's top-level `README.md` and root landing page belong to a different session and are not modified here.
> The Line Lab site is published at **https://karagemop466-tech.github.io/Korea3/docs/index.html**.

## What this is

A reproducible research stack that (1) verifies its data, (2) originates its own spread and total lines,
(3) scans signal families with multiplicity control and out-of-sample testing, (4) measures same-game correlation for
parlay pricing, and (5) pays a strategy on the leaderboard only if it passes every validation gate.

**Executive summary:** [LINE_LAB_EXECUTIVE_SUMMARY.md](LINE_LAB_EXECUTIVE_SUMMARY.md) · **Site:** `docs/index.html`

## Results (build 2026-11-01)

| Area | Result |
|---|---|
| Data reconciliation | 64/64 official standings rows matched — team-aggregate W/L/T/PF/PA check covering the outcome of 380 games (2025 season + 2026 games played). Not a per-game official verification (F-11). |
| Own lines | Model spread MAE 10.67 vs market 10.44 (design), 10.17 vs 9.64 (holdout) — real, but behind the market |
| Signal scan | 56 mechanical tests; 1 survives Benjamini-Hochberg at 5%; 4 positive in both out-of-sample windows |
| Strategies | 15 rules; **0** pass all validation gates; the 1,000-unit reward pool allocates **0** |
| Correlation | phi(home ML, home cover) = 0.67 (n=7,080); phi(cover, total) ≈ 0.02; cross-game control 0.494 |
| Player props | Framework, gates and sample-size maths published; **no prop numbers** (player-week data unobtainable — F-04) |

## Layout (this session's scope only)

```
data/                      open game dataset + sources registry + verification attestation
  games_1999_2026_nflverse.csv   results and closing lines (nflverse/nfldata)
  official/verification_attestation.json   counts, team codes, URLs, date — no NFL-sourced values (F-10)
pipeline/                  analysis + site generation (pure standard library, offline, deterministic)
  lib_core.py features.py  loaders, statistics, point-in-time features, own-line model
  verify.py                dataset integrity + aggregate reconciliation vs official standings
  build_model.py           own-line origination and market comparison
  run_strategies.py        15 single-bet strategies, 7 gates, leaderboard scoring
  scan.py                  56-test signal scan with BH-FDR control
  correlations.py          same-game leg correlation + parlay pricing analysis
  props.py                 prop framework, gates, scoring distributions, key numbers
  build_site.py            static site generator → docs/
  link_check.py            link + structure check (fails the build on a broken link)
  run_all.sh               regenerate reports/ and docs/ end to end
reports/                   machine-readable outputs consumed by the site
docs/                      the published site (generated; do not hand-edit)
COORDINATION.md            shared task board (this session's board is appended, additive only)
```

## Reproduce

```bash
bash pipeline/run_all.sh
```

No third-party Python packages, no network access, no manual input. Two consecutive runs produce byte-identical
`reports/` and `docs/`; CI enforces this with `git diff --exit-code`.

## Data rights

NFL.com's terms restrict reproduction and systematic retrieval, and this project holds no NFL licence (see
`audit/data-rights-review.md` from the audit session and flagged item **F-10**). Accordingly:

* no NFL-sourced values are stored or redistributed in this repository;
* the verification check is published as an attestation (counts, team codes, URLs, date);
* the live comparison re-runs only if a rights holder supplies a CSV with the documented schema;
* the pipeline performs no scraping of any kind.

## Rules this project holds itself to

1. No number without a source, and no figure that a script did not compute.
2. If a value cannot be confirmed from a primary source, it is blank and listed on the *Flagged for review* page.
3. Windows are fixed before results are read (design 1999–2018, validation 2019–2023, holdout 2024–2026).
4. Multiplicity is controlled across the whole scan; a single lucky rule is not a discovery.
5. Backtests are not settlement records (F-12), and no strategy is claimed to be profitable.

Research tooling, not betting advice.
