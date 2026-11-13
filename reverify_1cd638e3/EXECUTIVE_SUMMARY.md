# Executive summary — independent re-verification (2026-11-13)

**Session:** `arena/1cd638e3-korea3` · **Branch:** `arena/1cd638e3-korea3` → `main`
**Role:** fresh, independent, line-by-line re-verification of the committed state, plus consolidation.
**Verdict:** all **28** independent checks pass; the committed headline numbers are reproducible, the
pinned dataset is intact, and one open irregularity (F-06 / X02) is **resolved**.

> Research and engineering sample. **Nothing here is betting advice.** No strategy in this repository
> has demonstrated skill at the required significance level.

## 1. What was verified, and how

The verifier (`reverify_1cd638e3/verify.py`) is **self-contained**: it reads the committed raw and
derived CSV/JSON artefacts directly and **does not import** `line_lab`, `scripts`, `pipeline`, `hub`
or `decision_lab`. A bug in the producing pipeline therefore cannot certify its own output. Each check
recomputes a published value from first principles and compares it to the committed value.

| Area | Method | Result |
|---|---|---|
| Dataset pin | SHA-256 of every committed `data/raw/*.csv` vs `data/provenance.json` | **5/5 match** |
| Dataset pin (live) | Re-downloaded pinned commit `a270278` from `codeload.github.com` | **5/5 checksums match byte for byte** |
| Same-game correlation | Home-cover × Over φ recomputed from `model_dataset.csv` | **φ = 0.0086, n = 6,784, χ² = 0.503, p = 0.478 — exact match** |
| Arithmetic identities | −110 break-even; 2-leg −110 parlay decimal; break-even φ | **0.52381 · 3.6446 · 0.097506 — exact** |
| Own-line error | Model/market MAE + paired p-values from `model_predictions_B.csv` | **spread 10.6698 vs 10.2470, diff 0.4229, p = 4.89e-24 — exact** |
| Own-line error (total) | same | **total 10.8587 vs 10.5929, diff 0.2657, p = 1.33e-14 — exact** |

All 28 checks: **28 pass · 0 fail · 0 skipped**. Machine-readable results:
[`reverify_1cd638e3/results.json`](reverify_1cd638e3/results.json). Live dashboard page:
[`/reverify_1cd638e3/index.html`](https://karagemop466-tech.github.io/Korea3/reverify_1cd638e3/index.html).

## 2. Irregularity resolved — F-06 / X02 (spread × total correlation)

A prior session flagged that the same-game spread×total φ was *"not reproducible from the committed
raw file"* and reported independent estimates of −0.0085 / −0.0083 / −0.0039. **The cause is now
identified and the flag is resolved.**

- The correlation is computed from the **derived** `data/derived/model_dataset.csv`, **not** from raw
  `data/raw/games.csv`. The earlier non-reproduction used the wrong source file.
- Recomputed from `model_dataset.csv`, the published value reproduces **exactly**: φ = 0.0086,
  n = 6,784 (the 6,784 rows of `model_dataset.csv` that have both `home_cover` and `over` defined),
  cover rate 0.4888, over rate 0.4947, joint 0.2440, χ² = 0.503, p = 0.4783.
- The substantive conclusion is unchanged: 0.0086 is far below the **φ ≥ 0.0975** a 2-leg −110 parlay
  needs to break even, so same-game spread×total legs are **not** dependent enough to pay.

## 3. Requirement coverage (brief → delivered)

The brief's requirements are implemented across the repository. This session re-verified the numeric
core; the dashboard and decision surfaces are owned by prior sessions and were not rebuilt.

| Brief requirement | Where it lives | Status |
|---|---|---|
| Full list of requirements; collect/organize/analyze | `hub/requirements.html`, `docs/requirements.md` | delivered |
| Suggestions section to review & choose a path before implementing | `hub/suggestions.html` (15), `decision_lab/suggestions.html` (14, gate R9) | delivered — **nothing implemented until a path is chosen** |
| Clear questions / information / answers before decisions | `hub/questions.html` (18), `decision_lab/open-questions.html` (18, gate R10) | delivered |
| Originate own NFL lines | `scripts/model.py`, `pipeline/build_model.py`, `hub/own-lines.html` | delivered |
| Signal strategies + leaderboard + rewards | `hub/leaderboard.html`, `hub/competition.html`, `hub/strategies.html` | delivered (rewards unfunded by design) |
| Single bet / parlay / player-prop combos | `hub/single-bets.html`, `hub/parlays.html`, `hub/player-props.html` | delivered |
| Validation gates per strategy | `hub/validation.html`, `scripts/gates.py`, `pipeline/run_strategies.py` | delivered — **0 of 18 rules pass all gates** |
| Correlation values | `hub/correlations.html`, `scripts/correlation.py` | delivered — re-verified here |
| Remove luck; selectively skill-based | `hub/competition.html` (anti-luck mechanisms, sample-size band) | delivered |
| Track injuries + depth deficiencies (2nd/3rd/4th string) | `hub/injuries.html`, `decision_lab/injuries.html`, `decision_lab/depth.html` | delivered — **string ordering flagged blank** (D09) |
| Executive summary | `EXECUTIVE_SUMMARY.md`, `hub/executive-summary.html`, this file | delivered |
| Clean GitHub Pages dashboard, category subpages, tables | `hub/index.html` (25 pages) + root dashboard | live |
| Per-row source links; blank + flagged if unverifiable | `hub/check_hub.py`, `verify/source_audit.py`, `decision_lab/check.py` | enforced |

## 4. Headline findings (re-verified)

- **Own-line accuracy trails the market.** Spread MAE 10.6698 vs the closing line's 10.2470
  (paired diff 0.4229, p = 4.9e-24); total MAE 10.8587 vs 10.5929 (p = 1.3e-14). The model is close
  but not better than the market on accuracy.
- **No strategy earns a reward.** 0 of 18 tested rules pass all validation gates; the best full-sample
  ROI (+0.58%) has a week-block 95% interval containing zero.
- **The leaderboard is a luck trap.** Simulating 11 no-skill strategies with the same bet counts yields
  a "winner" averaging +5.4% ROI, profitable 93% of the time (95th percentile +16.3%). Any ranking of
  a handful of backtests must clear this band.
- **The vig is the wall.** Average two-way hold ≈ 2.75%; detecting a 3% edge at 80% power needs ~6,200
  settled bets (~8 seasons at 750/season).
- **Same-game legs are dependent; cross-game legs are not.** Moneyline×spread φ = 0.671;
  spread×total φ = 0.0086 (re-verified); moneyline×total φ = 0.000; two games in the same week φ = 0.006.
- **Player props could not be measured.** No reachable official source provides player-level logs or
  licensed prop prices; every prop value is blank and flagged, never estimated.

## 5. Open items — flagged, not smoothed over

These remain published on the relevant **Flagged for Review** pages and do **not** block the merge:

- **D09 (decision_lab):** the brief's 2nd/3rd/4th-string requirement is **not satisfiable from
  official sources**. NFL.com rosters publish membership and status but no string ordering; ordered
  depth charts exist only on third-party sites the project rejects. Every depth-string cell is blank
  and flagged. Starter-to-replacement *events* are officially sourceable via the weekly injury report.
- **B01:** player-prop line verification — no machine-readable official source; values blank + flagged.
- **B03:** weather (`temp`/`wind`) has no provenance in the dataset; labelled unverified.
- **B04/B05:** no penalty data; no verified venue coordinates (not hardcoded).
- **B06:** no pre-2021 opening-line archive; blocks a full-history closing-line-value study.
- **F-10:** external link availability is not re-verified from this sandbox (egress is restricted to
  GitHub and package registries); official URLs are linked for manual review.

## 6. Scope and discipline

This session edited only: the new `reverify_1cd638e3/**` directory, **one additive navigation entry**
in `line_lab/build_site.py` (the generator, not a generated file — lesson N11), the regenerated root
pages, and this board. No pipeline, data, strategy, dashboard or decision-lab file was modified. No
betting price, correlation, ROI or strategy number was invented; no funded reward was created; nothing
was placed on a sportsbook.

**Reproduce:**

```bash
python3 reverify_1cd638e3/verify.py      # 28 checks -> results.json
python3 reverify_1cd638e3/build_page.py  # render index.html from results.json
```
