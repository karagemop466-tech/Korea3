# NFL Line Lab — line origination, tested signals, validation gates

> **Latest integration — 2026-11-02, session `arena/25ea8ac4-korea3`.**
> The consolidated, official-evidence-only dashboard is at
> **<https://karagemop466-tech.github.io/Korea3/hub/index.html>** (also linked from the root page).
> It has a clean landing page and 19 category subpages; every table row links to an official publisher;
> unverifiable values are blank and published on the
> [Flagged for Review](https://karagemop466-tech.github.io/Korea3/hub/flagged.html) page.
> Executive summary: [`INTEGRATION_EXECUTIVE_SUMMARY.md`](INTEGRATION_EXECUTIVE_SUMMARY.md).
> Rebuild with `python3 hub/build_hub.py`; verify with `python3 hub/check_hub.py`.
> All earlier builds below are preserved and untouched.

> **Revision 2026-11-12 — injuries, depth, suggestions and questions.** The dashboard now has **24 pages**.
> Three are new and each is linked from the shared navigation:
> [Injuries & depth](https://karagemop466-tech.github.io/Korea3/hub/injuries.html) (44 official injury-report
> rows for 4 clubs joined to each club's own depth chart, six findings, and every unverified value blank),
> [Suggestions](https://karagemop466-tech.github.io/Korea3/hub/suggestions.html) (15 proposals, three paths,
> a recommendation, **nothing implemented until a path is chosen**) and
> [Questions & decisions](https://karagemop466-tech.github.io/Korea3/hub/questions.html) (18 questions,
> 10 blocking, with the information held and missing) and
> [Competition, rewards & luck](https://karagemop466-tech.github.io/Korea3/hub/competition.html)
> (10 promotion gates, a seven-row sample-size table, and an unfunded reward structure with no amounts).
> Summary: [`EXECUTIVE_SUMMARY_2026-11-12.md`](EXECUTIVE_SUMMARY_2026-11-12.md) ·
> addendum: [`COMPETITION_2026-11-12_ADDENDUM.md`](COMPETITION_2026-11-12_ADDENDUM.md).

**Published site:** <https://karagemop466-tech.github.io/Korea3/> — the dashboard generated from
[`line_lab/`](line_lab/) (Pages serves the repository root)
**Consolidated executive summary (2026-11-02):** [`CONSOLIDATED_EXECUTIVE_SUMMARY.md`](CONSOLIDATED_EXECUTIVE_SUMMARY.md) · live at [`/executive.html`](https://karagemop466-tech.github.io/Korea3/executive.html)
**Integration summary:** [`EXECUTIVE_SUMMARY.md`](EXECUTIVE_SUMMARY.md) (this session: cross-build synthesis, verification results, defects repaired)
**Executive summaries (prior sessions):** [`EXECUTIVE_SUMMARY.md`](EXECUTIVE_SUMMARY.md) (pipeline in `pipeline/`/`data/`),
[`LINE_LAB_EXECUTIVE_SUMMARY.md`](LINE_LAB_EXECUTIVE_SUMMARY.md),
[`line_lab/EXECUTIVE_SUMMARY.md`](line_lab/EXECUTIVE_SUMMARY.md) (root dashboard), and
[`VERIFIED_EXECUTIVE_SUMMARY.md`](VERIFIED_EXECUTIVE_SUMMARY.md) (official-evidence-only workbench)
**Task board and integration log:** [`COORDINATION.md`](COORDINATION.md)

This repository holds the bodies of work below, produced by different sessions (2026-11-01 – 2026-11-02).
**All are kept. No site directory was deleted.** The root now serves the `line_lab` dashboard; every
other build stays in place and is reachable from `/sessions.html`.

| Body of work | Session | Source in repo | Served at |
|---|---|---|---|
| **Root dashboard** (16 pages, generated from one `summary.json`) | `arena/9f5e9cb5-korea3` | `line_lab/`, root `*.html`, `assets/` | `/` |
| Empirical pipeline + site | `arena/c70bdb9d-korea3` | `site/`, `scripts/`, `data/`, `research/` | `/site/` |
| Earlier research brief | `arena/9febee68-korea3` | root pages, preserved byte-identical | `/site/prior/` |
| Second Line Lab build | `arena/d118ca7e-korea3` | `docs/`, `pipeline/`, `reports/` — untouched | `/docs/` |
| Independent audit | `arena/65d448da-korea3` | `audit/` — untouched | `/audit/` |
| **Verified workbench** (official-evidence-only; unverified values blank) | `arena/cbcd97cc-korea3` | `verified/`, `nfl_lab/`, `tests/test_lab_*.py` | `/verified/` |
| Independent evidence review (19-source register re-check; R1–R6 flags) | `arena/92c7b263-korea3` | `reviews/92c7b263/` | repo only |
| **Re-verification + consolidated summary** (66/66 numbers recomputed; link audit; exec page) | `arena/d7d4d48d-korea3` | `verification/`, `CONSOLIDATED_EXECUTIVE_SUMMARY.md`, `executive.html` | `/executive.html` |

The root pages were replaced by the `line_lab` dashboard; the previous root pages remain byte-identical in
`site/prior/` and in git history, so nothing was lost. Every build is reachable from `/sessions.html`.

**Verification.** Two independent audits are published and they agree.
[`/verification.html`](https://karagemop466-tech.github.io/Korea3/verification.html) re-derives 39 published headline
numbers independently of the pipeline that produced them, link-checks all 112 published pages, classifies the source
of all 5,572 table rows, and lists the defects found and repaired. [`verification/REPORT.md`](verification/REPORT.md)
is a second, separately written audit (66/66 checks, 112 pages, 0 broken links). Every published table row is classified
**official** (league/operator/standards body, linked on the row), **recomputed** (re-derived from the pinned
dataset or this repository's reports) or **unverified** (blank, and listed for review). Run it with
`bash verify/run_all.sh`.

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
bash    verify/run_all.sh        # rebuild everything, converge, and run every gate in this repository
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

## 2. The first brief (superseded at the root, preserved)

Session `arena/9febee68-korea3` published a deliberately non-empirical research brief at the
repository root: `index.html`, `strategies.html`, `validation.html`, `correlations.html`,
`leaderboard.html`, `sources.html`, `flagged.html`, `style.css`. The root was later regenerated
as the `line_lab` dashboard, so those files no longer exist at the top level; the brief survives
in git history and inside the `/prior/` mirror of whatever root site was current when the mirror
was last built.

## 3. The second build (`docs/`, `pipeline/`, `reports/`, untouched)

A separate pipeline and 11-page site from session `arena/d118ca7e-korea3`, including its own
reports and a CI gate (`git diff --exit-code -- reports docs`). Republished at
`/prior-d118ca7e/`. Its `docs/` directory is left exactly as merged so that gate keeps passing.

---

## Layout

```
site/               this session's published dashboard (generated — edit scripts/build_site.py, not the HTML)
site/prior/         mirror of whatever site is served at the repository root, plus audit/
site/prior-d118ca7e/  byte-identical copy of the docs/ build
line_lab/  *.html  assets/              the root dashboard and its generator (session 9f5e9cb5)
                                        rebuild: python3 -m line_lab.run_all && python3 -m line_lab.build_site
                                        verify:  python3 line_lab/check_site.py
docs/  pipeline/  reports/  LINE_LAB.md the second build, untouched (session d118ca7e)
audit/                                  the independent audit (session 65d448da)
verify/                                 integration audit: claim recomputation, whole-repo link check,
                                        per-row provenance, and run_all.sh (one command, all gates)
data/raw/           this session's pinned, checksummed source CSVs
data/derived/       every generated table, metric and report
scripts/            this session's pipeline, site generator and verifier
research/           source registry, repo audit, methodology, leaderboard spec, flags
```

## Independent verification (2026-11-02)

A seventh session re-checked the combined result rather than rebuilding it. It re-downloaded the
pinned nflverse commit and matched all five SHA-256 hashes, recomputed every settlement and ROI in
the root dashboard (16,439/16,439 exact, 11/11 strategies), recounted the gate tables, and crawled
every page in all six deployments (108 pages, 2,991 internal links, 0 broken). It found and fixed
a live page with no stylesheet, 56 dead source links, tracked bytecode, and a non-deterministic
test that had published a stale "last completed game".

**Result: 30 checks verified, 4 unverified and left visibly unverified, 2 blocked by the
environment, 0 mismatches.** Nothing changed the substantive conclusion: no strategy in any build
clears its gates.

- Site: <https://karagemop466-tech.github.io/Korea3/qa/index.html>
- Summary: [`qa/EXECUTIVE_SUMMARY.md`](qa/EXECUTIVE_SUMMARY.md) · flags: [`qa/flags.json`](qa/flags.json)
- Reproduce: `python3 qa/check_links.py && python3 qa/verify.py && python3 qa/build_site.py`

## Disclaimer

Research and engineering sample. **Nothing here is betting advice.** No strategy in this
repository has demonstrated skill at the required significance level. The bundled dataset
carries its own terms — see `data/provenance.json`; NFL.com content is not scraped, compiled or
redistributed (see flag F10).
