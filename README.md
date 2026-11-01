# NFL Line Lab

Own NFL lines, 18 tested signals, eight validation gates, measured correlations, and a
leaderboard designed so that luck cannot get ranked.

**Site:** <https://karagemop466-tech.github.io/Korea3/>
**Executive summary:** [`EXECUTIVE_SUMMARY.md`](EXECUTIVE_SUMMARY.md)
**Task board:** [`COORDINATION.md`](COORDINATION.md)

---

## What this is

A reproducible research project, not a tip service.

- **Origination.** A walk-forward team-ratings model produces its own spread and total for every game, using nothing published after the week's first kickoff. It is benchmarked against the closing line, and it loses.
- **Signal research.** 18 rules across spreads, totals and moneylines, pre-registered and all published — 14 of them lose money, and they are on the site.
- **Validation.** Eight mandatory gates, including Benjamini–Hochberg false-discovery control and empirical-Bayes shrinkage, applied to the whole family.
- **Correlation.** Same-game leg correlations measured on 6,784 settled games, cross-game independence tested, and the exact correlation a parlay needs in order to be worth its price.
- **Player props.** Mechanism and required correlation documented; every measured value left **blank** and flagged, because no verifiable prop source exists here.

## Headline numbers

| | |
|---|---|
| Games modelled | 7,075 regular-season games, 1999–2026, all priced and completed |
| Own-line error (spread) | 10.670 pts vs 10.247 for the closing line (p ≈ 4.9e-24 against us) |
| Rules tested | 18 · **0 pass all eight gates** · 4 provisional · 14 fail |
| Best raw result | +8.41% ROI over 607 bets, q = 0.288 — not significant after multiplicity |
| Spread × total correlation | φ = +0.0086 (95% CI −0.0162 to +0.0332) — indistinguishable from zero |
| Correlation a parlay needs | φ ≥ 0.0975 at −110 to break even |

## Reproduce it

```bash
bash scripts/fetch_data.sh          # downloads the dataset at a pinned commit
python3 scripts/build_dataset.py    # leak-free modelling table
python3 scripts/model.py            # own lines + accuracy tables
python3 scripts/blend.py            # information test / blend
python3 scripts/signals.py          # the 18-rule family
python3 scripts/gates.py            # the eight gates + shrinkage
python3 scripts/correlation.py      # correlation lab
python3 scripts/props.py            # prop framework
python3 scripts/own_lines.py        # own lines for unplayed fixtures
python3 scripts/summary.py          # league baselines
python3 scripts/build_site.py       # generate docs/
python3 scripts/verify_site.py      # verify the site (non-zero exit on failure)
```

Requires Python 3.11 with `numpy`, `pandas`, `scipy`. Runtime ≈ 2 minutes (the model refits 486 times).

## Layout

```
data/raw/          pinned source CSVs (checksummed)
data/derived/      every generated table, metric and report
scripts/           the whole pipeline, plus the site generator and verifier
docs/              the published GitHub Pages site (generated — do not hand-edit)
research/          source registry, repo audit, methodology, leaderboard design, flags
```

## Sources

Every claim is traceable. Rules, scoring, overtime and bet-settlement mechanics are cited to
**official NFL** and **licensed-operator** sources with the exact sentence each supports
(`research/sources.md`). NFL market numbers have no official publication, so they come from
one open dataset, **pinned by commit and checksummed**, with every table row linking to it.

Anything that could not be confirmed from an official source is **blank** and listed on the
site's *Flagged for Review* page — including two anomalies found in official NFL pages and a
dated operator rulebook.

## Honest limitations

No injury data. No player-level data. 26.9% of prices imputed at −110. One primary book. No
pre-2021 opening lines. Details in `research/methodology.md` §6 and on the site.

## Licence and disclaimer

Research and engineering sample. **Nothing here is betting advice.** The bundled dataset
carries its own terms — see `data/provenance.json`.
