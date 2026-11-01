# NFL Line Lab

Origination of our own NFL numbers, mechanical betting strategies, a luck-adjusted leaderboard, and
the validation gates that decide whether any of it is real.

**Live dashboard:** https://karagemop466-tech.github.io/Korea3/

---

## What this repository contains

| Path | What it is |
|---|---|
| `docs/` | The published dashboard (GitHub Pages). Landing page plus 15 category pages. |
| `docs/data/*.json` | Every number on the site, as data. The site is rendered from these files. |
| `scripts/` | The full pipeline: acquisition → features → model → bets → gates → site. |
| `data/raw/` | Raw inputs, pinned to a git commit. |
| `data/PROVENANCE.json` | Source URLs, commit SHAs, SHA-256 per file, row counts. |
| `data/verification.json` | External spot checks, whole-file integrity checks, independent re-settlement. |
| `research/` | Executive summary and research notes. |
| `COORDINATION.md` | Shared task board, verification log, handoffs and merge record. |

## Reproduce it

```bash
git clone https://github.com/karagemop466-tech/Korea3.git
cd Korea3
python3 -m venv .venv && . .venv/bin/activate
pip install numpy pandas

python3 scripts/fetch_data.py       # re-download pinned data + verify SHA-256
python3 scripts/run_all.py          # features, model, bets, gates, JSON
python3 scripts/verify_external.py  # external + integrity verification
python3 scripts/make_site.py        # rebuild the site from the JSON
python3 -m http.server -d docs 8080 # view at http://localhost:8080
```

Runtime is a couple of minutes; everything is seeded and deterministic.

## The nine validation gates

A strategy is only "validated" if it passes **all** of them:

1. **G1 Sample size** — at least 200 settled bets.
2. **G2 Coverage** — at least 5 seasons.
3. **G3 No leakage** — point-in-time features, verified by rebuilding ratings from truncated history.
4. **G4 Out-of-sample** — non-negative ROI on the held-out 2023–2025 seasons.
5. **G5 Beats the luck null** — p < 0.05 against a 10,000-draw zero-skill simulation priced at the
   de-vigged market probability of the side taken.
6. **G6 Multiple testing** — survives Benjamini–Hochberg FDR at q = 0.10 across all strategies.
7. **G7 Season consistency** — profitable in at least 60% of seasons.
8. **G8 Robustness** — still non-negative after dropping the best season.
9. **G9 Observed prices** — every bet was priced from a market actually present in the source data.

## Current result

**0 of 28 strategies pass all nine gates.** The best is *Fade the big favourite* (S08): +7.60% ROI over
494 bets, 95% CI −0.73% … +15.84%, p = 0.023, 7/9 gates. Its held-out return is +0.04%.

That is the finding, not a failure of the pipeline. See `research/EXECUTIVE_SUMMARY.md` and the
**Flagged for Review** page for every value that could not be verified.

## Honesty rules this repo follows

* Every table row links to its source. Computed values link to the pinned dataset **and** the script.
* A value that could not be confirmed is rendered as `—` and listed on the Flagged for Review page.
  It is never inferred, interpolated, or filled from memory.
* Prices that do not exist in the data (player props, same-game combos) are labelled **assumed** and
  those strategies are excluded from the leaderboard ranking.
* Failed strategies are published alongside the successful ones.

## Data sources

* **nflverse/nfldata** — games, closing/opening line files, team metadata. Pinned commit and hashes
  in `data/PROVENANCE.json`. nflverse is an independent open-data project, **not** an official NFL or
  sportsbook publication; the sportsbook behind the line columns is undocumented (flagged as IR-01).
* **DevinOgrady/NFL-Player-Projections** — weekly player box scores (third-party mirror, provenance
  unverified, IR-02).
* **Pro-Football-Reference** — used only for external spot checks of final scores
  (`https://www.pro-football-reference.com/years/2024/games.htm`).

## Disclaimer

Research output. Not betting advice. Nothing here has been validated as profitable; the study's
conclusion is the opposite.
