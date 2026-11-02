# Executive summary — independent verification, 2026-11-02

**Session:** `arena/d4478fd5-korea3` · **Published site:** <https://karagemop466-tech.github.io/Korea3/qa/index.html>
**Machine-readable record:** [`qa/verification.json`](verification.json), [`qa/links.json`](links.json),
[`qa/flags.json`](flags.json), [`qa/sources.json`](sources.json)

---

## 1. What this session did, and what it deliberately did not do

Six independent sessions had already merged six bodies of work into this repository by 2026-11-01:
a root dashboard, an empirical pipeline site, a second build, an independent audit, a
verified workbench, and a `session-398c4b58/` build. All six are live.

This session did **not** rebuild them, and it did not re-do their research. It did the one job
nobody had done: it checked the combined result, line by line, against committed artefacts and
against the upstream source, then fixed what was actually broken.

That is also what the shared board required. The final integration role is to re-verify the
combined data, confirm the site builds with no broken links, publish, and record the outcome.

## 2. Method — five kinds of check, no trust

| Check type | What it means | Result |
|---|---|---|
| **Upstream re-derivation** | Re-download the pinned dataset at its exact commit through the GitHub API and compare SHA-256 with both the recorded hash and the local file | **5/5 files matched byte for byte** |
| **Recomputation** | Recompute published numbers from committed data with an independent implementation | **16,439/16,439** settlements exact; **11/11** strategy ROIs and bet counts exact; MAE **10.670 vs 10.247** exact; **18** rules, **0** pass all 8 gates; best **+8.41%** on **607** bets at **q = 0.288** exact |
| **Arithmetic identity** | Values that must hold by definition | break-even at −110 = **52.381%**; parlay dependence needed at −110 = **φ ≥ 0.09751** (published 0.0975) |
| **Structural crawl** | Parse every page and resolve every `href`/`src`, case-sensitively, including anchors and cross-site links | **108 pages · 2,991 internal links · 197 assets · 4,269 external link instances · 0 broken** |
| **Platform API** | Ask GitHub for deployment and CI state instead of assuming it | Pages **built** from `main:/`; latest Actions run **success** |

Status of all 38 checks: **30 verified, 4 unverified, 2 blocked, 2 informational, 0 mismatches.**

## 3. The finding that matters

**No strategy in any of the six builds demonstrates skill.**

- Root dashboard: **0 of 11** strategies eligible. Best full-sample ROI **+0.58%** over 703 bets,
  95% CI **−7.5% to +8.2%** — reproduced exactly from the committed bet file.
- Empirical pipeline: **0 of 18** rules pass all eight gates. Best raw result **+8.41%** over 607 bets,
  multiplicity-adjusted **q = 0.288** — which is what the best of many coin-flips looks like.
- `session-398c4b58`: **0 of 28** rules pass nine gates. Its best (**+7.60%** on 494 bets) falls to
  **+0.04%** out of sample.
- Own-line models are **worse than the closing line** in every build: MAE 10.670 vs 10.247.
- Same-game **spread × total** dependence is roughly zero in every build (published +0.0086 to +0.020;
  recomputed here −0.0085 to −0.0039). A 2-leg parlay at −110 needs **φ ≈ 0.0975** before dependence
  alone helps. Nothing is close.
- The one large dependence — moneyline × spread **φ ≈ 0.671** — is real but already priced by books;
  it is a reason independent-multiplication parlay pricing is wrong, not a reason to bet.

That is the honest answer to "originate lines, find signals, remove luck": after three independent
pipelines, eighteen to twenty-eight pre-registered rules each, and full gate systems, **nothing clears
the bar**. The repository now says so in every build, with the arithmetic exposed.

## 4. Defects found and fixed (5)

| ID | Defect | Fix |
|---|---|---|
| F-01 | Live audit page had **no stylesheet** — it linked `../style.css`, deleted when the root was regenerated | Restored `style.css` verbatim from the commit before deletion; the audit's own checker passes |
| F-02 | **56 dead source links** on two live tables (28 + 28) pointing at `scripts/leaderboard.py` and `scripts/strategies.py`, which never existed | Repointed to `scripts/run_all.py` in both the generated HTML and the generator |
| F-03 | Compiled bytecode tracked in git | Removed from index and tree |
| F-04 | **Non-deterministic test output**: a shadowed variable iterated an unordered set, so the "last completed game" flipped between runs, and the published page said `2026_07_DAL_PHI` when the data contained week 8's `2026_08_CAR_GB` | Fixed the test (deterministic, date-ordered), regenerated the artefact and the page |
| F-05 | Two committed copies of the same test report **disagreed**; one had no writer | Both now carry the verified value |

## 5. Open for review (4) — published, none blocking

| ID | Item | Why it stays open |
|---|---|---|
| F-06 | Three different spread × total φ values, none reproducible from the committed raw file | Filters are not documented row by row; all values are within ±0.025 of zero so the conclusion holds, but the point estimates stay **unverified** |
| F-07 | "6,340 completed games with closing lines" | No filter tried reproduces it (7,384 completed; 5,403 priced). Left visible, marked unverified |
| F-08 | `session-398c4b58` cannot be rebuilt from the repository | Its derived JSON and bet records are not committed; its figures are shown as *its report*, never as independently verified |
| F-10 | Every non-GitHub citation | This sandbox reaches `github.com`/`api.github.com` only. All 4,269 external links are counted and listed, **none marked checked** |

Two documented notes (not defects): five legitimate "number of games" figures from five filters (F-09),
and a preserved-site mirror whose navigation resolves against the live root (F-11).

## 6. What is still not true, and is not claimed

- **No betting performance is verified.** Every return is a backtest on a third-party open dataset,
  not a settlement record.
- **No player props were ever priced.** No official prop feed and no licensed prop price exists here;
  the prop pages publish method and blanks.
- **No opening-line history before 2021**, no injury data, no weather ground truth with provenance,
  one primary book.
- **No data-rights clearance was obtained.** The repository holds no NFL.com-sourced data; the market
  data is nflverse, pinned and hashed. That is a consistency check, not legal advice.
- **This is not betting advice.**

## 7. Reproduce everything

```bash
python3 qa/check_links.py     # crawl all six deployments: 108 pages, 0 broken
python3 qa/verify.py          # recompute every claim  -> qa/verification.json
python3 qa/build_site.py      # render the published pages from that JSON
```

Dependencies: Python 3.11 with `pandas` and `numpy`, plus the `gh` CLI for the platform checks.
Without network access the upstream and deployment rows report **BLOCKED** rather than guessing.

## 8. Sources

Tier 1 (official league): NFL.com terms, NFL support, NFL operations — **blocked from this sandbox,
inherited and unverified here**. Tier 2 (licensed operator): DraftKings help centre — **blocked**.
Tier 3 (open data / third-party): nflverse/nfldata at commit `a270278f` — **verified by hash
re-download**; Pro-Football-Reference — **blocked**. Tier 4: repository artefacts and the GitHub
API — **verified**. Tier 5 (standards): NIST — **blocked**. Full register with what each source
supports: [`qa/sources.json`](sources.json) and the live [Sources page](https://karagemop466-tech.github.io/Korea3/qa/sources.html).
