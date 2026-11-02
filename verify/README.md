# `verify/` — the integration audit

Three tools, one driver. They exist because every other checker in this repository validates only its
own directory: `line_lab/check_site.py` checks the 15 root pages, `scripts/verify_site.py` checks
`site/`, `pipeline/link_check.py` checks `docs/`, `nfl_lab/check_verified.py` checks `verified/`,
`audit/check_audit_page.py` checks `audit/`. GitHub Pages here is a legacy branch deploy from
`main:/`, so **every** directory is published. Nothing was checking the union.

| File | What it does |
|---|---|
| `recompute_claims.py` | Re-derives every headline number the root dashboard prints, reading the pinned raw snapshot directly. It does **not** import `line_lab`, so a bug in the pipeline cannot certify itself. |
| `linkcheck_all.py` | Resolves every local `href`/`src` on every tracked `*.html`, honouring `<base href>` in the preserved mirrors and site-absolute `/Korea3/` links. Reports external links by host and classifies each host official / dataset / secondary / other. |
| `source_audit.py` | Walks every table on every page and classifies each **row** by the strongest source it links: `official`, `dataset`, `internal`, or `none`. `none` is the failure case. |
| `run_all.sh` | Rebuilds dashboard data, `reports/`, `docs/`, the root pages and the mirrors; iterates the render/measure cycle to a fixed point; then runs every gate in the repository. |

## Results at this commit

| Metric | Value |
|---|---|
| Headline claims re-derived | 39 of 40 pass, 0 discrepancies (the 40th is a seeded simulation, reproduced not re-derived) |
| Pages link-checked | 102 |
| Local links resolved | 3,156 · broken **0** |
| External links | 6,297 across 18 hosts · 388 on official domains |
| Table rows audited | 5,366 · official 343 · dataset/code 4,987 · unsourced 36 |

## The three provenance classes

No official source publishes NFL betting prices or model outputs, so **no price or analytical value in
this repository can be officially verified**. Conflating "sourced" with "official" is the most common
way a research site misleads, so each row is classified instead:

* **official** — published by the NFL, a licensed operator, a standards body or a government, and linked
  on the row. Only rules, scoring, settlement mechanics and operator terms can be in this class.
* **recomputed** — re-derived from the commit-pinned, SHA-256-checked open dataset or from this
  repository's own reports. Reproducible by anyone; not an official league publication.
* **unverified** — no artifact supports it. Blank, and listed on `flagged.html`. Never zero, never
  inferred.

The 36 remaining unsourced rows are a documented defect in the `session-398c4b58/` archive (non-numeric
page-inventory and flag rows). `run_all.sh` passes `--max-unsourced 36`, so the number cannot grow
silently; the default budget is 0.

## Reproducing a byte-identical build

`line_lab/data/derived/summary.json` records a build stamp. It is wall-clock by default and honours the
standard `SOURCE_DATE_EPOCH` variable, so a rebuild can be made byte-identical to a commit:

```bash
SOURCE_DATE_EPOCH=1793640562 python3 -m line_lab.run_all   # reproduces generated_utc 2026-11-02T17:29:22Z
```

`pipeline/run_all.sh` (which regenerates `reports/` and `docs/`) is already deterministic: two
consecutive runs produce byte-identical output, and CI enforces it with `git diff --exit-code`.

## Running it in CI

Every tool exits non-zero on failure, so they can be used as gates:

```bash
python3 verify/recompute_claims.py      # exit 1 on any mismatch
python3 verify/linkcheck_all.py         # exit 1 on any broken local link
python3 verify/source_audit.py          # exit 1 on any unsourced row (--max-unsourced to allow a budget)
bash    verify/run_all.sh               # full rebuild + every gate
```
