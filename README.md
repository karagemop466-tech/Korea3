# NFL Line Lab — line origination, tested signals, validation gates

**Published site:** <https://karagemop466-tech.github.io/Korea3/> — the dashboard generated from
[`line_lab/`](line_lab/) (Pages serves the repository root)
**Executive summary:** [`EXECUTIVE_SUMMARY.md`](EXECUTIVE_SUMMARY.md) (pipeline in `pipeline/`/`data/`) and
[`line_lab/EXECUTIVE_SUMMARY.md`](line_lab/EXECUTIVE_SUMMARY.md) (root dashboard)
**Task board and integration log:** [`COORDINATION.md`](COORDINATION.md)

This repository holds five bodies of work produced by different sessions on 2026-11-01.
**All are kept. No site directory was deleted.** The root now serves the `line_lab` dashboard; every
other build stays in place and is reachable from `/sessions.html`.

| Body of work | Session | Source in repo | Served at |
|---|---|---|---|
| **Root dashboard** (13 pages, generated from one `summary.json`) | `arena/9f5e9cb5-korea3` | `line_lab/`, root `*.html`, `assets/` | `/` |
| Empirical pipeline + site | `arena/c70bdb9d-korea3` | `site/`, `scripts/`, `data/`, `research/` | `/site/` |
| Earlier research brief | `arena/9febee68-korea3` | root pages, preserved byte-identical | `/site/prior/` |
| Second Line Lab build | `arena/d118ca7e-korea3` | `docs/`, `pipeline/`, `reports/` — untouched | `/docs/` |
| Independent audit | `arena/65d448da-korea3` | `audit/` — untouched | `/audit/` |

The root pages were replaced by the `line_lab` dashboard; the previous root pages remain byte-identical in
`site/prior/` and in git history, so nothing was lost. Every build is reachable from `/sessions.html`.

---

## 1. The empirical work (`site/`)

A walk-forward model that originates its own spread and total, 18 pre-registered signals, eight
mandatory validation gates, a correlation lab, a player-prop framework and a leaderboard
specification — with a verifier that fails the build if any table row lacks a source link.

| | |
|---|---|
| Games modelled | 7,075 regular-season games (1999–2026, priced and completed) |
| Own-line error | 10.670 pts vs 10.247 for the closing line (p ≈ 4.9e-24 against us) |
| Signals tested / passed all 8 gates | 18 / **0** (4 provisional, 14 failed) |
| Best raw result | +8.41% ROI over 607 bets — q = 0.288, not significant after multiplicity |
| Spread × total correlation | φ = +0.0086 (95% CI −0.0162 … +0.0332) |
| Correlation a 2-leg parlay needs at −110 | φ ≥ 0.0975 |
| Own lines published for unplayed fixtures | 164 (28 with a posted market line to compare) |

### Reproduce it

Python 3.11 with `numpy`, `pandas`, `scipy`; ~2 minutes (the model refits 486 times).

```bash
bash scripts/fetch_data.sh       # pinned + checksummed dataset (no NFL.com scraping)
python3 scripts/build_dataset.py # modelling table, leak-free, sign convention enforced
python3 scripts/model.py         # own lines: 4 variants + 9-setting sensitivity grid
python3 scripts/blend.py         # information test / out-of-sample blend
python3 scripts/signals.py       # the 18-rule family
python3 scripts/gates.py         # 8 gates, FDR control, empirical-Bayes shrinkage
python3 scripts/correlation.py   # correlation lab
python3 scripts/props.py         # player-prop framework
python3 scripts/own_lines.py     # own lines for unplayed fixtures
python3 scripts/summary.py       # league baselines
python3 scripts/build_site.py    # generate site/ (also refreshes site/prior*/)
python3 scripts/verify_site.py   # verify — non-zero exit on any failure
```

`scripts/verify_site.py` is a gate, not a report. It currently checks 450 table rows for a
source cell, 729 internal links, every external source URL, and reconciles margin/total/cover on
all 7,075 rows against the pinned, checksummed raw files. `.github/workflows/verify.yml` runs it
in CI.

### Sources

Rules, scoring, overtime and settlement mechanics are cited to **official NFL** and
**licensed-operator** pages with the exact sentence each supports (`research/sources.md`).
NFL market numbers have no official publication, so they come from one open dataset, **pinned by
commit and checksummed**, with every table row linking to it. Anything unverifiable is **blank**
and listed on the site's *Flagged for Review* page.

### Limitations

No injury data. No player-level data. 26.9% of prices imputed at −110. One primary book. No
pre-2021 opening lines. Details in `research/methodology.md` §6.

---

## 2. The earlier brief (root-level, untouched)

`index.html`, `strategies.html`, `validation.html`, `correlations.html`, `leaderboard.html`,
`sources.html`, `flagged.html`, `style.css` — a deliberately non-empirical research brief with
its own source register. Build and check it with `python3 scripts/build.py` and
`python3 scripts/check.py`. Republished at `/prior/`.

## 3. The second build (`docs/`, `pipeline/`, `reports/`, untouched)

A separate pipeline and 11-page site from session `arena/d118ca7e-korea3`, including its own
reports and a CI gate (`git diff --exit-code -- reports docs`). Republished at
`/prior-d118ca7e/`. Its `docs/` directory is left exactly as merged so that gate keeps passing.

---

## Layout

```
site/              the published site (generated — edit scripts/build_site.py, not the HTML)
site/prior/        byte-identical copy of the first research brief + audit
site/prior-d118ca7e/  byte-identical copy of the second build
docs/  pipeline/  reports/  LINE_LAB.md   the second build, untouched
*.html  style.css  audit/                 the first brief, untouched
data/raw/          this session's pinned, checksummed source CSVs
data/derived/      every generated table, metric and report
scripts/           pipeline, site generator, verifier (+ the other sessions' build/check scripts)
research/          source registry, repo audit, methodology, leaderboard spec, flags
```

## Disclaimer

Research and engineering sample. **Nothing here is betting advice.** No strategy in this
repository has demonstrated skill at the required significance level. The bundled dataset
carries its own terms — see `data/provenance.json`; NFL.com content is not scraped, compiled or
redistributed (see flag F10).
