# Executive summary — decision readiness

**Snapshot 2026-11-12 (UTC)** · session `arena/7f33cb21-korea3` · site: `decisions/index.html`
Research only, not betting advice. Blank means unverified, never zero.

A parallel surface, separate from the consolidated `hub/`, with one purpose: let a path be
examined and chosen **before** anything is built. Every table row links an official publisher or
the committed file the number came from; `decisions/check.py` fails the build otherwise.

---

## Bottom line

The project has built a real line-origination pipeline, and it does not have an edge.
That is the finding, and it is a useful one: it reproduces, it is stated plainly, and it stops
money being spent chasing a signal that is not there.

Nothing on this surface has been implemented. All 15 proposals are `proposed`.

| Measure | Value | Meaning | Source |
|---|---|---|---|
| Independent checks run | 24 | re-derived from committed data, no project imports | [recompute.py](recompute.py) |
| Exact matches | 21 | including every headline number | [recompute.py](recompute.py) |
| Mismatches | 0 | no fabricated number found | [recompute.py](recompute.py) |
| Definitional issues | 1 | D01: `10.670` is an MAE, published beside an RMSE | [defects.json](data/defects.json) |
| Blocked / unknowable | 2 | no official quantity exists to check against | [recompute.py](recompute.py) |
| Official injury rows transcribed | 254 | 2026 Week 10, read 2026-11-12 | [injuries.html](injuries.html) |
| Proposals registered | 15 | scored, ranked, **none implemented** | [suggestions.json](data/suggestions.json) |
| Questions registered | 18 | **10 block** a decision | [questions.json](data/questions.json) |
| This session's claims withdrawn | 4 | published on the defect register | [defects.json](data/defects.json) |

---

## What this session adds

1. **Decision readiness.** 15 scored proposals and 18 questions, 10 of which block a verdict,
   so a path can be chosen before anything is built.
2. **Injury intelligence.** The first injury data in the project: 254 official player rows for
   2026 Week 10, with an explicit confidence tier on every finding.
3. **Independent recomputation.** 24 checks re-derived from committed data; 21 matched exactly;
   no fabricated number found.
4. **Honest failure.** Four of this session's own claims were wrong and are published as
   withdrawn — including one caught while this very page was being built.

---

## The five findings that matter for a decision

| # | Finding | Evidence | What it means | Source |
|---|---|---|---|---|
| 1 | **No lawful data basis and no price archive** | NFL Terms 1.1/1.3; no quote file anywhere in the repository | No empirical claim can be published as a product until S01 (licence) and S02 (price archive) are resolved. This is the root blocker. | [NFL Terms](https://www.nfl.com/legal/terms/) | [registry](data/suggestions.json) |
| 2 | **The best rule does not survive multiplicity** | Gate strategy G-S14: +8.41% over 607 bets, q = 0.288; 0 of 18 rules pass | The leaderboard cannot rank skill today. Ranking it would publish luck as merit. | [gates_results.csv](../data/derived/gates_results.csv) | [registry](data/suggestions.json) |
| 3 | **Availability is the biggest missing input, and it is half-obtainable now** | 254 official rows available; only 2.4% carry a game status | Build the two-field data model (S11) and archive daily (S04). Do not treat DNP as an absence. | [NFL injury policy](https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693) | [registry](data/suggestions.json) |
| 4 | **No official depth chart or snap count exists** | `nfl.com/depth-charts` 404; NGS `/stats/participation` 404; NE and DET label their own charts unofficial | The 2nd/3rd/4th-string requirement can only ever be club-sourced opinion. State that limit or drop the claim. | [NE depth chart](https://www.patriots.com/team/depth-chart) | [registry](data/suggestions.json) |
| 5 | **The site is stale and fragmented** | Dataset ends 2026-10-29; seven parallel builds live in one repository | Freeze the data date (S12) and pick one canonical surface (S13) before adding anything. | [games.csv](../data/raw/games.csv) | [registry](data/suggestions.json) |

---

## Recommended next three actions

| Order | Action | Why now | Where | Blocked by | Source |
|---|---|---|---|---|---|
| 1 | Add two separate fields, **practice status** and **game status**, and never merge them | The snapshot already shows why: most non-participants have no game status. | [S11](suggestions.html) | nothing | [registry](data/suggestions.json) |
| 2 | Archive one dated injury snapshot per day with the read time | There is no history, so no injury signal can be tested until archiving starts. | [S04](suggestions.html) | Q01 (licence), Q03 (storage) | [NFL injury policy](https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693) | [registry](data/suggestions.json) |
| 3 | Freeze the stale dataset date on every page and auto-flag staleness | The site presents two-week-old data with no warning. | [S12](suggestions.html) | nothing | [games.csv](../data/raw/games.csv) | [registry](data/suggestions.json) |

---

## Recommended path order

**P2 Coverage first → P3 Governance first → P1 Evidence first.**

- **P2 first** because it is the only path that both answers the brief's availability requirement
  and can be completed with official public sources that verify today.
- **P3 second** because it is cheap, immediate, and protects everything built after it.
- **P1 last** because it depends on a contract the project does not control. No amount of
  engineering substitutes for a licence.

Choosing a path does not authorise data acquisition the NFL Terms prohibit.

---

## Full ranking by weighted score

Weights: decision value 0.40, evidence gained 0.25, feasibility today 0.20, risk control 0.15.
A high score is not permission to implement — each row is still blocked on its questions.

| Rank | ID | Proposal | Weighted | Effort | Source |
|---|---|---|---|---|---|
| 1 | S08 | Publish a power and minimum-detectable-effect calculator beside the leaderboard | 4.50 | low | [registry](data/suggestions.json) |
| 2 | S11 | Separate "practice status" from "availability" in the data model | 4.50 | low | [registry](data/suggestions.json) |
| 3 | S04 | Archive a dated snapshot of the official injury report every day | 4.35 | low | [registry](data/suggestions.json) |
| 4 | S02 | Contract an executable, timestamped quote archive | 4.25 | high (cost) | [registry](data/suggestions.json) |
| 5 | S01 | Obtain written permission or a licence for official NFL data at scale | 4.20 | high (legal, time) | [registry](data/suggestions.json) |
| 6 | S12 | Freeze the stale dataset date on every page and auto-flag staleness | 3.95 | low | [registry](data/suggestions.json) |
| 7 | S15 | Make the verifier able to fail on a stale artifact, not only on a stale value | 3.95 | medium | [registry](data/suggestions.json) |
| 8 | S13 | Consolidate the seven parallel site builds into one canonical surface | 3.90 | medium | [registry](data/suggestions.json) |
| 9 | S07 | Write and publish the source-precedence rule for conflicting official pages | 3.70 | low | [registry](data/suggestions.json) |
| 10 | S14 | Publish a decision log that accepts, rejects or defers each proposal | 3.70 | low | [registry](data/suggestions.json) |
| 11 | S06 | Pre-register a Depth Deficiency Index and validate it through the eight gates | 3.65 | medium | [registry](data/suggestions.json) |
| 12 | S09 | Keep the leaderboard non-monetary until written reward terms exist | 3.60 | low | [registry](data/suggestions.json) |
| 13 | S03 | Replace own-line accuracy headlines with closing-line value | 3.50 | medium | [registry](data/suggestions.json) |
| 14 | S05 | Extend the availability and depth record from 4 clubs to all 32 | 3.50 | medium | [registry](data/suggestions.json) |
| 15 | S10 | State the settlement and push convention on every ROI table | 3.30 | low | [registry](data/suggestions.json) |

Note the collision: proposal **S14** (rank 10, a decision log) is a different object from gate
strategy **G-S14** (the +8.41% wind-unders rule). The site writes the gate prefix wherever both
could be confused.

---

## The four withdrawn claims

Published on the defect register rather than deleted. The pattern is the same each time: a true
observation was carried one inference too far.

| ID | What was raised | Why it was wrong | Source |
|---|---|---|---|
| W01 | "26.9% of bets sit at −110" | 26.88% is the share of priced-line **games** with no spread price (1,902 / 7,075), not bets. Only 8.78% of bets sit at −110. | [recompute](../decisions/recompute.html) |
| W02 | "The correlation script's cover flag is inverted" | The committed `home_cover` / `over` flags are correct; re-deriving them from `margin + spread_line` is what changes the sign (φ +0.0086 → −0.0072). | [recompute](../decisions/recompute.html) |
| W03 | "The 2-leg parlay algebra is wrong" | It is correct: decimal 1.909, squared 3.645, φ 0.097506. The error was mine, three times. | [recompute](../decisions/recompute.html) |
| W04 | "At least eight injury-report players appear on no depth row" | Only five are verified. The draft reached eight by counting three New England defenders whose rows were never rendered — a truncated fetch is a gap, not evidence. | [recompute](../decisions/recompute.html) |

The live defect register carries D01–D07 (repo defects) and V01–V06 (the other session's six
injury findings, all independently **confirmed**). D04 is the only above-low open item.

---

## What this summary does not claim

- That any injury signal works — no history, no prices, and the game status field is mostly blank.
- That any player will or will not play — availability is the league's declaration, not a prediction.
- That the depth tiers are official — two of the four clubs call their own charts unofficial.
- That a leaderboard should be funded — no power target, no quotes, no terms.
- That the project's numbers are wrong — they reproduced. What matters is what they support.

---

## Where to go next

| Page | Answers |
|---|---|
| [`suggestions.html`](suggestions.html) | What could we change, and in what order? |
| [`questions.html`](questions.html) | What must be answered before a verdict is reasonable? |
| [`paths.html`](paths.html) | Which coherent path, and why in that order? |
| [`injuries.html`](injuries.html) | What do the official injury pages actually say? |
| [`recompute.html`](recompute.html) | Which published numbers reproduce? |
| [`defects.html`](defects.html) | What is broken, and what did I get wrong? |
| [`flagged.html`](flagged.html) | What is unverified and deliberately blank? |
| [`method.html`](method.html) | What rules make a row publishable? |

Verification: `python3 decisions/check.py` → PASS, 11 pages, 286 table rows, 394 row source
links, 0 broken internal links, 0 non-official external links, 20 registry sources.
