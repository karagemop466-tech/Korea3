# Official-source access and data-rights review

**Reviewed:** 2026-11-01 UTC. This is a source and project-status review, not legal advice or a grant of data rights.

| Item | Finding | Official source |
|---|---|---|
| NFL website use | NFL.com section 1.3 states that its services are for individual non-commercial informational use, and that systematic retrieval to create or compile a collection or database is prohibited without express prior written consent. | [NFL.com terms, section 1.3](https://www.nfl.com/legal/terms/) |
| Reproduction and redistribution | NFL.com section 1.1 states restrictions on copying, displaying, and transmitting its services or content except as expressly provided. The repository contains no evidence that the project has received an NFL license or written permission. | [NFL.com terms, section 1.1](https://www.nfl.com/legal/terms/) |
| NFL gamebook | The example gamebook states that its summary and play-by-play are for media coverage and other use requires written permission. A URL is not permission to ingest or redistribute the material. | [NFL gamebook, Denver at Kansas City, 2025](https://static.www.nfl.com/image/upload/v1766722063/gamecenter/f91b71fe-311e-11f0-b670-ae1250fadad1.pdf) |
| Single event cross-check | One Denver-at-Kansas-City 2025 regular-season game score in parallel-session snapshot `99832574` agreed with the official NFL schedule. This is a **single spot-check only**; it does not validate the remaining games, point spreads, odds, event timestamps, payouts, or dataset licensing. No collection of NFL schedule results is reproduced in this report. | [Official 2025 Denver schedule](https://www.nfl.com/schedules/2025/by-team/denver-broncos) |
| Sportsbook evidence | An NFL final score is not evidence of a historical quoted price, execution, or the terms under which a wager was settled. Those fields remain unverified without an appropriate operator record and applicable rules. | [DraftKings settlement glossary](https://support.draftkings.com/dk/en-us/glossary-of-betting-terms?id=kb_article_view&sysparm_article=KB0010398) |

## Integration request

Do not build or publish a systematically retrieved NFL.com database, or automate NFL.com scraping, unless the relevant rights and terms are satisfied. Quarantine copied official-site datasets where permission cannot be established, and consult the rights holder or a properly licensed provider before distribution or commercial/reward use. Linking to an official source and verifying one item does not establish permission to compile, redistribute, or use an entire dataset. The spot-check and all outstanding data-rights questions should be represented accurately on the site's Flagged for Review page.

The user-facing dashboard can continue to publish methodology, source links, and blank/unverified empirical values while data access and rights remain unresolved. The single spot-check does not justify a backtest, a correlation coefficient, a validated betting signal, or a reward.
