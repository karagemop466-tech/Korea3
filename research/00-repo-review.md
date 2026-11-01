# Repository review — baseline audit

**Session:** `session-c70bdb9d` · **Branch:** `arena/c70bdb9d-korea3` · **Audit date:** 2026-11-01 (UTC)
**Base commit:** `8c20600ecfe30504ad0c70873f1240914f697773` ("Initial commit", `main`)

## 1. What was actually in the repository

Reviewed file by file. There was exactly one tracked file.

| # | Path | Size | Content | Verdict |
|---|---|---|---|---|
| 1 | `README.md` | 8 bytes | The literal string `# Korea3` with no trailing newline | Empty placeholder. Reviewed, not deleted; replaced with a real README in this session. |

Everything else is new in this session. Nothing was deleted, renamed or overwritten.

`git log` at baseline:

```
8c20600 Initial commit
```

Branches at baseline: `main`, `origin/main`, and the working branch `arena/c70bdb9d-korea3` (branched from `8c20600`). Working tree clean. Remote: `https://github.com/karagemop466-tech/Korea3.git`.

## 2. Irregularities found in the repository itself

| ID | Finding | Severity | Action taken |
|---|---|---|---|
| V01 | The repository contained only an 8-byte README — no code, data, licence, CI, or task board. Any claim of prior work would be fabricated. | — | Recorded here; all work in this session is new and cited. |
| V02 | The repository is named `Korea3` but the project is NFL line research. The name carries no information and will confuse a reader arriving from GitHub Pages. | Low | **Not renamed** — repository identity was left untouched as instructed. Flagged for the owner. |
| | No `LICENSE` file. The project depends on a third-party dataset whose terms must be respected on redistribution. | Medium | The dataset is redistributed under its own terms with provenance recorded in `data/provenance.json`. Owner should add an explicit licence. |
| | No `.gitignore`. | Low | Added, so generated caches do not enter history. |
| | No CI. Nothing verified the site before publishing. | Medium | Added `.github/workflows/pages.yml`, which runs the verifier and **refuses to deploy** if any check fails. |
| | No `COORDINATION.md` (required by the project brief for parallel sessions). | Medium | Created, with the task board, claims, and handoff rules. |

## 3. Data-level irregularities found during the build

These came from verifying the dataset line by line rather than trusting it. All are published on the site's Flagged for Review page.

### 3.1 The spread sign convention is inverted (the important one)

`games.csv` column `spread_line` is signed **opposite** to the conventional home spread: a **positive** value means the home team is **favoured**.

Left undetected, this inverts every ATS result on the site. It was caught because the first build produced a home cover rate of **59.99%**, which is not a plausible football number. Verified two independent ways:

1. **Against the data's own outcomes.** Mean home margin is +2.20 over 7,075 games. Splitting on the sign of `spread_line`:
   - `spread_line > 0` → mean home margin **+5.95** (n = 4,545)
   - `spread_line < 0` → mean home margin **−4.61** (n = 2,500)
   So positive `spread_line` tracks a home-team advantage → it is a home-favoured sign.
2. **Against the per-side closing file.** For every game present in both `games.csv` and `closing_lines.csv`, the home team's own line equals `−spread_line` on 67.3% of rows and `+spread_line` on 0.6% of rows. The residual 33% are genuine cross-book differences, not a convention issue.

The correct transformation is `home_spread = −spread_line` and `home_ats_margin = margin − spread_line`, which restores a home cover rate of **48.87%**. Both are enforced in `scripts/build_dataset.py` and asserted in `scripts/verify_site.py`.

### 3.2 Two in-dataset line sources disagree

| Comparison | Exact match | Within 0.5 pt | Within 1.0 pt |
|---|---|---|---|
| Home spread (`games.csv` vs `closing_lines.csv`), n = 3,368 | 67.3% | 91.1% | 97.2% |
| Total (`games.csv` vs `closing_lines.csv`), n = 3,368 | 61.7% | — | — |

Handled by making this a validation gate (G7): every rule is re-scored against the second source, and both results are published.

### 3.3 Other data defects

| Finding | Rows affected | Handling |
|---|---|---|
| `surface` contains a trailing-space duplicate (`'grass '` vs `'grass'`) | 93 | Normalised to `surface_clean`; no published number depends on the raw string. |
| `roof` missing | 26 | Not imputed; environment signals report their own n. |
| `surface` missing | 87 | Not imputed. |
| `temp` / `wind` missing | 2,213 | Not imputed; labelled UNVERIFIED wherever shown. |
| `temp` / `wind` have no provenance field (no station, no timestamp) | all | Labelled UNVERIFIED; weather-based signal S14 carries this caveat. |
| 2026 season incomplete (136 of 272 games played at snapshot) | 136 unplayed | Excluded from every calculation; unplayed fixtures are used only for the separate "own lines" forecast table. |
| No price recorded | 26.9% of games | Standard −110 substituted and the imputed share published per rule. |

## 4. Source-level irregularities found while verifying citations

| ID | Finding |
|---|---|
| F08 | Two NFL Support articles have their **bodies swapped**: the page titled *"What is a money line?"* explains the point spread, and the page titled *"What is the point spread?"* explains the moneyline. Content is correct in both; the titles are crossed. Both are cited (they are the source for the −110 standard and the push rule), and both are flagged. |
| F09 | The DraftKings house-rules copy used for the prop-participation rule and correlated-leg policy is a regulator-hosted PDF dated **2023-06-01**. It may have been superseded. The rule text is quoted as published in that copy and flagged for confirmation against the live page. |

## 5. What was verified, and how

- **Rules and mechanics:** read on the official page during this session; the exact sentence each citation supports is recorded in `research/sources.md`.
- **Market data:** pinned by commit, checksummed (`data/derived/checksums.txt`), and re-downloadable with `scripts/fetch_data.sh`. No official NFL publication of lines exists, so this is disclosed as a Tier 3 source rather than dressed up as official.
- **Every number on the site:** regenerated by script from the pinned files. No number was typed by hand.

## 6. Deviation from the requested parallel-session protocol

The brief assumes multiple agent sessions claiming tasks in `COORDINATION.md`. This run had **one** session. The board was still created, every task was claimed before work started, and the claim was committed and pushed first (`8541cf5`), because a second session arriving mid-run must be able to see what is taken. The backlog in `COORDINATION.md` lists the five tasks that were deliberately left unclaimed because they need a source this environment cannot reach.
