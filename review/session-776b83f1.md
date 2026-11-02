# Current-state verification addendum — `arena/776b83f1-korea3`

**Review date:** 2026-11-02 UTC
**Scope:** additive follow-up to the independent review in [earlier independent review](https://github.com/karagemop466-tech/Korea3/pull/38/files). This review does not replace it and does not edit `nfl_lab/`, `verified/`, `line_lab/`, the shared data, or another session's pages.
**Purpose:** re-run the available checks, retrieve the source page that the prior review could not retrieve, check the live Pages site, reproduce the validation-chain concern with synthetic records, and document site-wide source/navigation gaps. No NFL betting outcomes or signals were added.

## Executive result

- **Verified workbench:** the empty-input path still reports 0 admitted games, quotes, bets, forecasts, or player logs; 0 reward-eligible strategies; and 0 verified empirical values. The official-evidence view remains blank rather than inferring NFL prices, outcomes, correlations, ROI, or rewards.
- **Important code warning:** I reproduced a synthetic call to `evaluate_strategy` that returned `eligible=True` while its records intentionally mismatched the requested strategy, quote IDs, rule evidence, forecast identity, forward seasons, and multiplicity p-values. This is a code-path finding only; the fixture is synthetic and is not an NFL result. The default `nfl_lab.run` does not produce such a result because its inputs are empty and it does not supply a complete family p-value set.
- **Source boundary:** the `/verified/` and newly consolidated `/hub/` dashboards require an official-publisher source link on each table row. The legacy root dashboard and some archived exploratory pages still contain third-party/community backtest findings whose row-level links point to repository artifacts; those pages do not meet the same strict source standard and must remain clearly separated from the official-evidence views.
- **Jurisdiction:** no project-specific Norwegian legal/contest eligibility review is present. The official Norwegian regulator's page is included below as a manual-review starting point, not as a legal conclusion about this project.
- **Reproducibility:** rerunning the root `line_lab` build changes its generated timestamp. In this run, some serialized floating-point values also changed in the last digits; displayed rounded results and checks passed. The regenerated files were restored, so no generated-output churn is included in this review.
- **Pre-merge deployment baseline:** Pages was `built` from `main:/` at `d95fc7152f938c2da3425af800c7b899e7cc3da3`; deployment [41493795356](https://github.com/karagemop466-tech/Korea3/actions/runs/41493795356), Consolidated dashboard [41493795600](https://github.com/karagemop466-tech/Korea3/actions/runs/41493795600), Verify [41493795619](https://github.com/karagemop466-tech/Korea3/actions/runs/41493795619), verify-and-build [41493795599](https://github.com/karagemop466-tech/Korea3/actions/runs/41493795599), Independent re-verification [41493795686](https://github.com/karagemop466-tech/Korea3/actions/runs/41493795686), and Verified workbench [41493795592](https://github.com/karagemop466-tech/Korea3/actions/runs/41493795592) succeeded. I read back the pre-existing live root, `/hub/index.html`, `/hub/flagged.html`, `/verified/`, `/qa/index.html`, session index, prior route and earlier review.
- **Publication result:** PR [#47](https://github.com/karagemop466-tech/Korea3/pull/47) merged at `e86b6110b8c0c8e8f1e387559178fde75f2c025a` from head `8af68b7`; all five PR checks passed. The six post-merge main workflows all succeeded: Pages deployment [41494275972](https://github.com/karagemop466-tech/Korea3/actions/runs/41494275972), Consolidated dashboard [41494277094](https://github.com/karagemop466-tech/Korea3/actions/runs/41494277094), Independent re-verification [41494276999](https://github.com/karagemop466-tech/Korea3/actions/runs/41494276999), Verified workbench [41494276996](https://github.com/karagemop466-tech/Korea3/actions/runs/41494276996), verify-and-build [41494276981](https://github.com/karagemop466-tech/Korea3/actions/runs/41494276981), and Verify [41494276980](https://github.com/karagemop466-tech/Korea3/actions/runs/41494276980). Pages API build [1335582453](https://api.github.com/repos/karagemop466-tech/Korea3/pages/builds/1335582453) is `built` for `e86b611`. Cache-busted fetches of the live [review hub](https://karagemop466-tech.github.io/Korea3/review/index.html?cb=e86b611), [flag register](https://karagemop466-tech.github.io/Korea3/review/flagged.html?cb=e86b611), and [full report](https://karagemop466-tech.github.io/Korea3/review/session-776b83f1.md?cb=e86b611) succeeded.

## Review method and verified sources

I read the coordination board before claiming T16, then found that session `arena/92c7b263-korea3` had independently completed a closely related source review and merged PR #38 while this review was in progress. I narrowed this work to the synthetic adversarial reproduction, live deployment check, supplemental source/page checks, and findings below. Concurrent additions to `COORDINATION.md` conflicted during rebases onto the PR #38, PR #42 and PR #45 main histories. An early local resolution briefly committed conflict-marker lines; that commit was superseded during rebase. The subsequent rebases onto PR #46 and PR #48 main commits completed cleanly. In the final tree I retained the full latest main-board text and appended the T16 claim/results; no other session sections or files were discarded, and the board has no conflict markers. The earlier report is accessible through [PR #38](https://github.com/karagemop466-tech/Korea3/pull/38/files).

I retrieved all **19** URLs in `nfl_lab/sources.json` using the page-reading tool. The earlier report already records source-by-source findings for the NFL, DraftKings, NIST and PMC references. In particular, this follow-up successfully retrieved the National Weather Service PDF. Its glossary defines Brier score as mean squared error for probabilistic binary forecasts and describes Brier Skill Score relative to a reference forecast. This confirms the content of that source in this review; it does not validate the workbench's use of the metric or its empirical results. The [NWS source](https://www.weather.gov/media/owp/oh/rfcdev/docs/Glossary_Forecast_Verification_Metrics.pdf) is an official-domain URL.

Other source-specific caveats remain: the NFL.com responsible-betting article is credited to the Associated Press; DraftKings settlement and odds rules are operator-specific and current-page text does not establish historical rule versions; NIST sources explain statistical methods but do not certify this project's chosen thresholds or prove skill. See the [19-source review and R1–R6 findings](https://github.com/karagemop466-tech/Korea3/pull/38/files).

For Norway-specific review, the [Norwegian Gaming and Foundation Authority (Lotteritilsynet)](https://lottstift.no/for-spillere/mye-av-pengespillreklamen-du-ser-er-ulovlig/) says its published guidance concerns marketing and offering of gambling without Norwegian permission. This link is not a determination that this research site, a future contest, or any particular person is or is not compliant.

## Reproduction and build checks

Dependencies were installed from the pinned `requirements.txt` into ignored `.venv/`.

| Check | Result |
|---|---|
| `.venv/bin/python -m pytest tests/test_lab_*.py -q` | **24 passed** |
| `.venv/bin/python -m nfl_lab.run` | **0 admitted games, quotes, bets, forecasts, or player-game records; 0 eligible strategies; 0 verified empirical values** |
| `.venv/bin/python -m nfl_lab.check_verified` | **12 pages, 131 table rows, official-host links present, local links resolve, empty/blank discipline holds** |
| `python3 scripts/verify_site.py` | **11/11 checks passed**; checksums and arithmetic reconciliation passed for the pinned third-party archive |
| `.venv/bin/python line_lab/check_site.py` | **14 pages, links and reported-number checks passed** |
| `bash pipeline/run_all.sh` | **Pipeline complete**; 64/64 digest comparisons matched, 13 pages, link check PASS |
| Main `Consolidated dashboard` workflow [41494277094](https://github.com/karagemop466-tech/Korea3/actions/runs/41494277094) | **Passed after merge**; its `hub/check_hub.py` gate verifies the 20-page official-source hub, all table-row sources, navigation and flagged register. |
| `python3 qa/check_links.py --json /tmp/korea3-qa-links-final.json` | **131 HTML pages, 4,677 internal links, 0 broken links**; 11 orphan pages are preserved `site/prior/` copies, none are under `review/` or `hub/`. The committed `qa/links.json` remains an older 108-page snapshot and was not regenerated because it belongs to another session's scope. |
| `.venv/bin/python -m line_lab.run_all && .venv/bin/python -m line_lab.build_site && .venv/bin/python line_lab/check_site.py` | **Completed; checker passed.** The regenerated root outputs had a new build timestamp and last-digit float serialization changes. Those generated files were restored after inspection. |

The checks establish reproducibility of selected local arithmetic and link structure; they do **not** make the community dataset an official NFL data source, verify redistribution rights, or prove strategy skill. The full source/row-scope limitation is flagged below.

## Synthetic fail-open reproduction — R7

A synthetic call to `nfl_lab.validation.evaluate_strategy` returned **eligible: `True`** and all ten gate statuses as `pass` while these deliberately invalid relationships were present:

1. The call evaluated strategy `A`, but its settled-bet records identified strategy `B`.
2. Each `quote_id` was a nonexistent `NO-QUOTE-*` value.
3. The `rules_id` pointed to a link-only NIST record, not an operator rule snapshot.
4. The only supplied forecast identified strategy `B` and an unmatched event.
5. Forward records were labelled with 2013 clusters even though the protocol's forward window was 2016.
6. The code-computed cluster sign-permutation p-value was **0.27860696517412936**, but the separately supplied family p-values were both `0.000001`; the Bonferroni gate used the supplied value (**0.000002**) without checking that it matched the computed value.
7. `executable_quotes_verified=True` was supplied even though no quote object was linked to the bets.

The records were synthetic, and no real NFL data, ROI, or strategy result was involved. This is a reproducible **API/validation integrity issue**, not evidence that any published strategy is profitable. Relevant code: [`evaluate_strategy`](https://github.com/karagemop466-tech/Korea3/blob/main/nfl_lab/validation.py#L203-L344), [`audit_bet`](https://github.com/karagemop466-tech/Korea3/blob/main/nfl_lab/evidence.py#L87-L90), and the [`SettledBet` contract](https://github.com/karagemop466-tech/Korea3/blob/main/nfl_lab/contracts.py#L180-L223). The independent review's R1–R3 already request linkage for rules, quotes and forecasts; this run demonstrates that the gaps can combine into an all-gates pass under malformed input.

**Requested remediation, not applied here:** check that each bet belongs to the evaluated strategy and a protocol holdout/forward season; derive cluster identity from admitted event records; join each settlement to its exact executable quote, event, market, selection, line, operator and archived rules version; match the scored forecast one-to-one to the same bet/event/time; and compute multiplicity values from a frozen complete family instead of accepting unbound caller values/booleans. Add adversarial tests that assert each mismatch blocks promotion.

## Additional flags published at [`/review/flagged.html`](flagged.html)

| ID | Finding | Status |
|---|---|---|
| R7 | Synthetic malformed records can satisfy all ten strategy gates. | Needs review before any real licensed input is admitted. |
| R8 | The official-source-per-row standard now applies to `/verified/` and the new `/hub/`, but not to every legacy root/archive table. | Needs review; keep the exploratory pages explicitly separated from official-evidence findings. |
| R9 | No Norway-specific eligibility review for a future funded betting/leaderboard competition is recorded. | Needs review; no legal conclusion is made. |
| R10 | Root rebuild changes generated timestamp and last-digit float serialization, despite a deterministic-output claim. | Needs review; visible rounded metrics were stable in this run. |
| R11 | The session index headline now says “Several bodies,” but its “First research brief” and “Prior copies” rows still point to the same `/site/prior/index.html`; that page is the current measured root dashboard, not the original plan-only brief. The count wording was corrected in PR #43/#44; the route/content mismatch remains. | Partially resolved upstream; request the owner to restore/link the original brief or correct the row label/route. |

## Live Pages and limitations

The pre-merge Pages baseline was `built` at `d95fc7152f938c2da3425af800c7b899e7cc3da3`; deployment workflow [41493795356](https://github.com/karagemop466-tech/Korea3/actions/runs/41493795356) succeeded. The new root banner links the consolidated 20-page official-source dashboard at `/hub/`, whose review page lists 34 items. I read the live root dashboard, `/hub/index.html`, `/hub/flagged.html`, `/verified/index.html`, `/verified/flagged.html`, `/qa/index.html`, `/sessions.html`, `/site/prior/index.html`, and the restored earlier review. The current session index says “Several bodies” and lists ten rows. However, both “First research brief” and “Prior copies” still link to `/site/prior/index.html`; the live target is the current root dashboard titled “NFL line origination, measured,” not the original plan-only brief. This is the remaining R11 route/content mismatch. After PR #47 merged, Pages build 1335582453 completed successfully for `e86b611`; the new review index, flagged register and full report were fetched from the live site with cache-busting and returned the expected content.

- [Root dashboard](https://karagemop466-tech.github.io/Korea3/)
- [Official-evidence workbench](https://karagemop466-tech.github.io/Korea3/verified/index.html)
- [Existing verified flags](https://karagemop466-tech.github.io/Korea3/verified/flagged.html)
- [Consolidated QA dashboard](https://karagemop466-tech.github.io/Korea3/qa/index.html)
- [Session index](https://karagemop466-tech.github.io/Korea3/sessions.html)
- [Prior route](https://karagemop466-tech.github.io/Korea3/site/prior/index.html)
- [Supplemental review hub](https://karagemop466-tech.github.io/Korea3/review/index.html?cb=e86b611) — live and fetched after Pages build 1335582453
- [Supplemental review flags](https://karagemop466-tech.github.io/Korea3/review/flagged.html?cb=e86b611) — live and fetched after Pages build 1335582453
- [Full verification report](https://karagemop466-tech.github.io/Korea3/review/session-776b83f1.md?cb=e86b611) — live and fetched after Pages build 1335582453

No live source data is ingested, no NFL pages are scraped by the verified workbench, no sportsbook account is accessed, no bets are placed, and no prize is funded. A future owner should address the R1–R6 requests in the independent report and R7–R11 here before enabling any real data or reward eligibility. This session did not edit another session's models, data, site generator, or official-evidence dashboard.
