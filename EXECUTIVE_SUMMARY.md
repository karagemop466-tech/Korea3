# Executive summary — NFL line origination, signals, validation and leaderboard

**Project:** originate NFL lines, research signals, test single bets, parlays and player-prop combos,
gate every strategy, measure correlation, remove luck, run it as a leaderboard competition.
**Published site:** <https://karagemop466-tech.github.io/Korea3/> · **Audit page:** [`verification.html`](verification.html)
**Verification snapshot:** 2026-11-02 (UTC) · **Session:** `arena/81beef04-korea3` (final integration)
**Board and claims:** [`COORDINATION.md`](COORDINATION.md) · **Second independent audit:** [`verification/REPORT.md`](verification/REPORT.md) (66/66) · **Consolidated page:** [`executive.html`](executive.html) · **Prior summaries preserved:** [`research/prior-sessions/`](research/prior-sessions/)

> This document supersedes earlier session-level summaries as the single front-door summary. The previous
> version of this file is preserved byte-identical at
> [`research/prior-sessions/EXECUTIVE_SUMMARY_c70bdb9d.md`](research/prior-sessions/EXECUTIVE_SUMMARY_c70bdb9d.md).

---

## 1. Bottom line

1. **Four independent research builds, one conclusion: nothing passed its own gates.** Five strategy
   families were tested across the repository — 11, 15, 18 and 28 strategies in three separate
   pipelines, plus 8 hypotheses in the official-evidence workbench. **Zero** strategies were eligible
   for reward in any of them. The results are not contradictory: they agree on the outcome and differ
   only in family size and gate definitions.
2. **The luck band is larger than every edge measured.** In the root dashboard's own simulation, simply
   taking the best of 11 coin-flip strategies produces a mean ROI of **+5.45%** and a profitable "winner"
   **93%** of the time (95th percentile +16.3%). The best real strategy measured **+0.58%**, inside that
   band. A leaderboard that ranks raw backtests would hand the prize to noise.
3. **Origination works; beating the market does not.** The root model's spread error is 13.53 points
   against the closing line's 13.21, and its correlation with the actual margin is 0.389 versus 0.437.
   The empirical build reached the same place with a different model: 10.670 points of error against
   10.247, a 0.423-point deficit (p below 1e-20, stored as 0.0 in the metrics file). Reproducing the market is achievable; adding
   information to it is what failed.
4. **Correlation is measured, not assumed, and it is mostly zero where the public thinks it is not.**
   Same-game moneyline × spread is genuinely dependent (φ = 0.671) and already priced by operators.
   Spread × total is not (φ = 0.016, 95% CI −0.016 to +0.033, n = 4,853 priced games). Cross-game legs are
   independent (φ = 0.006). A two-leg parlay at −110 needs φ ≥ 0.0975 to break even on correlation
   alone, so ordinary parlays are a pure vig play.
5. **Player props are blocked, and therefore blank.** No licensed prop line/price was obtainable from a
   source that can be redistributed here. The estimator and its required schema are committed; every
   prop value on the site is blank and flagged. One archive publishes a +45.69% prop-parlay ROI on
   prices that were never observed — it is labelled `price-unverified`, scores zero reward points, and
   is called out in this summary rather than buried.
6. **The deliverable that is actually trustworthy is the measurement.** Honest numbers for the vig
   (mean two-way hold 2.66% ATS / 2.87% totals), the sample needed to detect an edge (~6,200 settled
   bets for 3% at 80% power), and the dependence structure of the legs — plus a verification layer
   that re-derives every published headline number independently.

## 2. What this session verified

Every number below was recomputed by `verify/recompute_claims.py`, which reads the pinned raw snapshot
and **does not import the pipeline** that produced the pages.

| Check | Result |
|---|---|
| Headline numbers re-derived independently | **39 of 40** reconciled, 0 discrepancies (the 40th is a seeded simulation, reproduced not re-derived) |
| Published HTML pages link-checked | **112**, 3,374 local links, **0 broken** (6,500 external links across 20 hosts, 417 on official domains) |
| Table rows audited for source provenance | **5,572** — 372 official, 5,154 dataset/code, **46 unsourced**, all in two other sessions' archives (0 in this repository's own builds) |
| Official sources opened and read live | 4, including the NFL rulebook, the NFL terms, and both NFL "what is…" articles |
| Defects found and repaired | **7**, each reproduced before being fixed |

A **second, independent re-verification** was built in parallel by session `arena/d7d4d48d-korea3` and is
published on the same site: [`verification/REPORT.md`](verification/REPORT.md) with 66 checks and its own
repository-wide link audit. It reports **66/66 pass** and **112 pages, 0 broken links**, which agrees with this
session's independent 39/40 claim reconciliation and link check. Two audits written separately, on separate code,
agreeing on the same numbers is worth more than either alone.

**Official-source finding, confirmed live on 2026-11-02:** the NFL Support article titled
*"What is a money line?"* actually explains the **point spread**, and *"What is the point spread?"*
explains the **moneyline** — the two bodies are swapped at the publisher. Both are cited here for what
they say, not for their titles. Separately, [NFL.com Terms §1.1 and §1.3](https://www.nfl.com/legal/terms/)
(updated 2024-05-16) prohibit reproduction and systematic retrieval to compile a database without prior
written consent, which is why **no NFL.com content is scraped, compiled or redistributed** in this
repository and why prices come from a pinned open dataset instead.

## 3. What each build found

| Build | Family | Gates | Eligible | Best measured result | Status |
|---|---|---|---|---|---|
| Root dashboard (`line_lab/`) | 11 strategies | 9 | **0** | S6 weather under: **+0.58%** ROI, n = 600, CI [−7.51%, +8.17%] | 4/9 gates |
| Empirical site (`site/`) | 18 rules | 8 | **0** | S14 wind unders: **+8.41%** ROI, n = 607, q = 0.288, shrunk +2.48% | 1 gate failed (multiplicity) |
| Second build (`docs/`) | 15 strategies | 6 | **0** | S08 wind under: **+10.05%** full sample, **−7.90%** holdout, n = 684 | 3/6 gates |
| Archive (`session-398c4b58/`) | 28 strategies | 9 | **0** | S08 fade-the-favourite: **+7.60%**, n = 494, holdout +0.04% | 7/9 gates |
| Verified workbench (`verified/`) | 8 hypotheses | 10 | **0** | none admissible — 0 admitted inputs, official-evidence-only by design | fail-closed |

The pattern across independent pipelines is the finding: **an edge that survives one window does not
survive the next.** The `docs/` build's best strategy made +10% on the full sample and lost 7.9% in the
holdout. The `site/` build's best cleared seven of eight gates and died on multiplicity (q = 0.288 vs a
0.10 bar) — exactly the correction that exists to stop "best of N" from being reported as skill.

## 4. Correlation and luck: the numbers that decide the design

| Quantity | Measured | What it implies |
|---|---|---|
| φ(moneyline, spread), same game | **0.671** | Real dependence; operators price or void it in same-game parlays |
| φ(spread, total), same game | **0.016** (−0.016 … +0.033) | Effectively zero; "correlated" total/ATS parlays are not correlated |
| φ(moneyline, total), same game | **0.000** | Zero |
| φ across two different games | **0.006** | Independent — cross-game parlays multiply honestly, and pay the vig twice |
| r(home points, away points) | **−0.051** | Slightly negative; "both teams score a lot" legs do not co-move |
| Break-even φ, 2 legs at −110 | **0.0975** | Needs six times the correlation the data shows |
| Mean two-way hold, ATS / totals | **2.66% / 2.87%** | The wall every strategy has to clear before it is measured at all |
| Bets needed to detect a 3% edge at 80% power | **≈ 6,200** | Roughly eight seasons at 750 bets; short backtests cannot resolve a real edge from noise |

## 5. Requirements coverage

| Requirement | Status | Where |
|---|---|---|
| Originate own NFL lines | **Met** — walk-forward spread/total model, 4 variants, 9-setting sensitivity grid, 164 published lines for unplayed fixtures | `line_lab/`, site → *Live lines*, `site/` own-line model |
| Signals from research | **Met** — 18-rule pre-registered family and a 56-test mechanical scan | `line_lab/strategies.py`, `pipeline/scan.py` |
| Single bets | **Met** — settled ledger of 16,112 selections with prices, outcomes and P&L | `line_lab/data/derived/bets.csv` |
| Parlays | **Met** — two-leg cross-game strategies plus measured joint-vs-independent hit rates | site → *Parlays* |
| Player-prop combos | **Blocked, published as blocked** — framework, schema and required φ documented; all values blank | site → *Player props*, `verify/` |
| Validation gates | **Met** — 9 gates (root) / 8 (empirical) / 6 (second build) / 10 fail-closed (workbench) | site → *Validation* |
| Correlation values | **Met** — same-game, cross-game, home/away, per-season, with CIs and n | site → *Correlations* |
| Remove luck | **Met** — permutation tests, bootstrap CIs, BH-FDR, empirical-Bayes shrinkage, no-skill band | site → *Validation*, *Leaderboard* |
| Leaderboard with rewards | **Met as specification** — scoring, tiers, anti-gaming rules, eligibility; **no funded prize pool** (flagged) | site → *Leaderboard* |
| Full list of requirements | **Met** — traced requirement by requirement | site → *Requirements* |
| Executive summary | **This document** | `EXECUTIVE_SUMMARY.md` |
| GitHub Pages site, category subpages | **Met** — 15-page dashboard at the repo root | `/` |
| Every table row sourced; blanks flagged | **Met on 5,526 of 5,572 rows**; 46 archive rows flagged | site → *Verification* |
| Flagged-for-review page | **Met** — 19 open items plus this session's additions | site → *Flagged for review* |

## 6. Defects found and repaired in this session

| # | Defect | Repair |
|---|---|---|
| D1 | `audit/flagged.html` loaded `../style.css`, which no longer exists — the page rendered unstyled and the audit's own checker failed | Repointed to `../assets/style.css`; checker passes |
| D2 | **933 published table rows had no source link** in the `docs/` build (previously reported by the independent audit, not fixed) | One provenance column added in the shared table helper; 933 → 0 |
| D3 | The build was not reproducible: `last_completed_game` flipped between runs due to an unstable sort, and the timestamp was wall-clock only | Stable sort on (kickoff, game_id); `SOURCE_DATE_EPOCH` now makes rebuilds byte-identical |
| D4 | `tests/test_causality.py` could not be imported at all (stale duplicate pointing at `pipeline.core`) — it tested nothing | Replaced with a forwarding entry point to the canonical suite |
| D5 | Compiled bytecode `scripts/__pycache__/lib.cpython-311.pyc` was committed | Untracked |
| D6 | A CI workflow triggered on `arena/cbcd97cc-korea3`, a branch that no longer exists | Trigger reduced to `main` |
| D7 | `site/prior/` mirrored a version of the root site older than the live one | Regenerated from the current root |

## 7. Provenance: what "verified" means on this site

No official source publishes NFL betting prices or the outputs of a model, so no price or analytical
value here can ever be *officially* verified. Conflating that with "sourced" is the most common way a
research site misleads, so every table row is classified:

- **official** — published by the NFL, a licensed operator, a standards body or a government, and linked
  on the row. Only rules, scoring, settlement mechanics and operator terms can be in this class.
- **recomputed** — arithmetic re-derived from the commit-pinned, SHA-256-checked open dataset or from
  this repository's own reports. Reproducible by anyone; not an official league publication.
- **unverified** — no artifact supports the value. It is **blank** and listed on *Flagged for review*.
  Never zero, never inferred, never back-filled.

## 8. What is not claimed

- No claim that any strategy here is profitable, or that any is ready to stake.
- No claim that a rule that failed here cannot work — only that this rule, on this data, does not clear
  this bar.
- No player-prop correlation values, because no prop line or price could be verified.
- No funded rewards: reward points are a scoring construct with no money behind them.
- No claim of official verification for any price, ROI, or model output.
- No legal or eligibility advice; jurisdiction and licensing were not assessed.

## 9. Reproduce everything

```bash
pip install -r requirements.txt                 # numpy, pandas, scipy, scikit-learn, pytest
python3 -m line_lab.run_all                     # rebuild the root dashboard's data (~80s)
python3 -m line_lab.build_site                  # re-render the 15 root pages
bash    pipeline/run_all.sh                     # rebuild reports/ and docs/ (deterministic)
python3 scripts/build_dataset.py && python3 scripts/model.py   # empirical build (slower)
python3 verify/recompute_claims.py              # independent re-derivation of 39 numbers
python3 verify/linkcheck_all.py                 # every local link on every published page
python3 verify/source_audit.py                  # per-row provenance classes
python3 line_lab/check_site.py                  # dashboard gate
python3 scripts/verify_site.py                  # empirical site's 11 checks
python3 -m nfl_lab.check_verified               # verified workbench gate
python3 -m pytest tests/test_lab_*.py -q        # 24 synthetic unit tests
```

## 10. Sources

Primary and pinned sources, with the sentence each supports, are registered in
[`research/sources.md`](research/sources.md), [`data/sources.json`](data/sources.json),
[`nfl_lab/sources.json`](nfl_lab/sources.json) and [`data/provenance.json`](data/provenance.json).
Market data is pinned to nflverse/nfldata commit `a270278f3ac4e937295fe6a27814b3c4a2b62645` and
verified by SHA-256 on every build ([manifest](line_lab/data/raw/MANIFEST.json)). Official citations
opened and read on 2026-11-02:

- NFL Support, [What is a money line?](https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line) — body explains the point spread (publisher defect, recorded)
- NFL Support, [What is the point spread?](https://support.nfl.com/hc/en-us/articles/35869774194324-What-is-the-point-spread) — body explains the moneyline (publisher defect, recorded)
- NFL.com, [Terms and Conditions](https://www.nfl.com/legal/terms/) §1.1, §1.3 — reproduction and systematic-retrieval restrictions
- NFL Football Operations, [2026 NFL Rulebook](https://operations.nfl.com/rules-officiating/2026-nfl-rulebook) — playing rules; no rulebook text is redistributed
- nflverse [`DATASETS.md`](https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/DATASETS.md) — field semantics and the spread-sign convention

## 11. Open items for the next session, in priority order

1. **Licensed prop lines and prices** — the only thing standing between the committed prop framework and
   real prop correlation research.
2. **A dated, rights-cleared price archive** — turns every "recomputed" price row into something that can
   be independently checked, and would let ROI be measured at an executable, pre-close timestamp.
3. **Injury / inactive data** — the largest missing feature class in every model here.
4. **One integrated pipeline** — four families and five sites is four times the maintenance and makes the
   leaderboard hard to read. Keep the archives, but score one family.
5. **Regenerate the `session-398c4b58` archive with a provenance column** — the last 36 unsourced rows.
