# NFL Line Lab — line origination, tested signals, validation gates

**Published site:** <https://karagemop466-tech.github.io/Korea3/>
**Prior research brief (preserved, root-level):** <https://karagemop466-tech.github.io/Korea3/prior/>
**Executive summary:** [`EXECUTIVE_SUMMARY.md`](EXECUTIVE_SUMMARY.md)
**Task board and integration log:** [`COORDINATION.md`](COORDINATION.md)

This repository contains two bodies of work produced by different sessions on 2026-11-01.
Both are kept, neither replaces the other.

## 1. NFL Line Lab (published site, `docs/`)

An empirical research pipeline and a dashboard: a walk-forward model that originates its own
spread and total, 18 pre-registered signals, eight mandatory validation gates, a correlation
lab, a player-prop framework and a leaderboard specification.

| | |
|---|---|
| Games modelled | 7,075 regular-season games (1999–2026, priced and completed) |
| Own-line error | 10.670 pts vs 10.247 for the closing line (p ≈ 4.9e-24 against us) |
| Signals tested / passed all 8 gates | 18 / **0** (4 provisional, 14 failed) |
| Best raw result | +8.41% ROI over 607 bets — q = 0.288, not significant after multiplicity |
| Spread × total correlation | φ = +0.0086 (95% CI −0.0162 … +0.0332) |
| Correlation a 2-leg parlay needs at −110 | φ ≥ 0.0975 |

Reproduce everything (Python 3.11, `numpy`/`pandas`/`scipy`, ~2 minutes):

```bash
bash scripts/fetch_data.sh       # pinned + checksummed dataset
python3 scripts/build_dataset.py # modelling table (leak-free)
python3 scripts/model.py         # own lines, 4 variants, sensitivity grid
python3 scripts/blend.py         # information test / out-of-sample blend
python3 scripts/signals.py       # 18-rule family
python3 scripts/gates.py         # 8 gates, FDR, empirical-Bayes shrinkage
python3 scripts/correlation.py   # correlation lab
python3 scripts/props.py         # player-prop framework
python3 scripts/own_lines.py     # own lines for unplayed fixtures
python3 scripts/summary.py       # league baselines
python3 scripts/build_site.py    # generate docs/
python3 scripts/verify_site.py   # verify (non-zero exit on any failure)
```

`scripts/verify_site.py` is a gate, not a report: CI fails if any check fails. It currently
audits 448 table rows for a source cell, 723 internal links, all external source URLs, and
reconciles margin/total/cover on all 7,075 rows against the pinned checksummed files.

**Sources.** Rules, scoring, overtime and settlement mechanics are cited to official NFL and
licensed-operator pages with the exact sentence each supports (`research/sources.md`). NFL
market numbers have no official publication, so they come from one open dataset pinned by
commit and checksummed, with every table row linking to it. Anything unverifiable is blank and
listed on the site's *Flagged for Review* page.

**Limitations.** No injury data, no player-level data, 26.9% of prices imputed at −110, one
primary book, no pre-2021 opening lines. Details in `research/methodology.md` §6.

## 2. NFL Research Lab brief (root-level, preserved)

The root-level site (`index.html`, `strategies.html`, `validation.html`, `correlations.html`,
`leaderboard.html`, `sources.html`, `flagged.html`, `style.css`) is an earlier, deliberately
non-empirical research brief by a concurrent session, with an independent audit under
`audit/`. It is preserved byte-identical and republished at `/prior/` so it stays reachable.
Build and check it with `python3 scripts/build.py` and `python3 scripts/check.py`.

## Repository layout

```
docs/          published site (generated — edit scripts/build_site.py, not the HTML)
docs/prior/    preserved copy of the earlier root-level brief + audit
data/raw/      pinned source CSVs (checksummed)
data/derived/  every generated table, metric and report
scripts/       pipeline, site generator, verifier (+ the prior session's build.py/check.py)
research/      source registry, repo audit, methodology, leaderboard spec, flags
audit/         independent audit of the earlier brief (unchanged)
```

## Disclaimer

Research and engineering sample. **Nothing here is betting advice.** No strategy on this site
has demonstrated skill at the required significance level. The bundled dataset carries its own
terms — see `data/provenance.json`.
