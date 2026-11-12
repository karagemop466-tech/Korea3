"""Verified source register for the decision system.

Every entry here was opened and read in this session (2026-11-12, UTC) before it
was used to support a claim.  Each record keeps:

``quote``
    A verbatim sentence or table cell from the page, so a reviewer can search the
    live page for the exact words rather than trusting a paraphrase.
``supports``
    What the quote is allowed to be used for on this site.  A link is not a
    licence: an official page that discusses the *existence* of injury reports is
    not evidence of any particular player's status.

Tiers
-----
``league``     NFL / NFL Football Operations / NFL Support — official league publication
``operator``   licensed sportsbook (DraftKings, FanDuel) — official operator terms
``standards``  NIST — official statistical-methodology reference
``index``      peer-reviewed literature index (PubMed Central)
``dataset``    nflverse open-data project — NOT an official publication.  Used only
               for reproducible measurements, never as an official fact.
``repo``       this repository — used for arithmetic identities only.

Any statement that cannot be tied to an entry here is left blank on the site and
published on the Flagged for Review page instead.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class Source:
    id: str
    tier: str
    publisher: str
    url: str
    quote: str
    supports: str
    opened: str = "2026-11-12"


SOURCES: tuple[Source, ...] = (
    # ---------------------------------------------------------------- league
    Source(
        id="NFL-INJ-POLICY-2016",
        tier="league",
        publisher="NFL.com (league news release)",
        url="https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-policy-for-2016-season",
        quote=(
            "The Practice Report has been modified to eliminate the \"Out\" category ... "
            "Questionable means it is uncertain as to whether the player will play in the game; "
            "Doubtful means it is unlikely the player will participate; and Out means the player "
            "will not play."
        ),
        supports=(
            "Semantics of the three game statuses and the three practice codes. Used to state that "
            "no official probability is attached to Questionable or Doubtful, so the site must not "
            "assign one."
        ),
    ),
    Source(
        id="NFL-INJ-POLICY-2016-PROB",
        tier="league",
        publisher="NFL.com (league news release)",
        url="https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-policy-for-2016-season",
        quote=(
            "The \"Probable\" category was eliminated from the Game Status Report because "
            "approximately 95 percent of the players who were listed as \"Probable\" in prior "
            "years did in fact play in the game."
        ),
        supports=(
            "The 2016 removal of 'Probable'. Used to explain why 'Probable' is absent from the "
            "2026 reports and why a 2026 season contains three statuses, not four."
        ),
    ),
    Source(
        id="NFL-INJ-POLICY-2016-CERTAIN",
        tier="league",
        publisher="NFL.com (league news release)",
        url="https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-policy-for-2016-season",
        quote=(
            "if a player is certain to play -- even if he has been listed in the club's practice "
            "report during that week -- the player will no longer be listed in the club's Game "
            "Status Report. However, if such a player is then deactivated for the game, the club "
            "will be required to provide an explanation to the league"
        ),
        supports=(
            "Why a practice-report entry can exist with an empty game status. Used to mark such "
            "cells as 'no game status reported' and never as a probability."
        ),
    ),
    Source(
        id="NFL-INJURIES-LIVE",
        tier="league",
        publisher="NFL.com",
        url="https://www.nfl.com/injuries/",
        quote=(
            "Official Latest NFL Injury Report for Players - Week 10 of the 2026 Season. "
            "Columns: Player | Position | Injuries | Practice Status | Game Status."
        ),
        supports=(
            "The live per-club injury table transcribed for the current-season tracker, and the "
            "column meanings (practice status and game status are separate fields)."
        ),
    ),
    Source(
        id="NFL-INJURIES-2025W9",
        tier="league",
        publisher="NFL.com",
        url="https://www.nfl.com/injuries/league/2025/reg9",
        quote=(
            "Official NFL Injury Report for Players - Week 10 of the 2025 Season. "
            "e.g. 'Lamar Jackson | QB | Full Participation in Practice | (blank game status)'."
        ),
        supports=(
            "The historical example used to demonstrate that a blank game-status cell coexists with "
            "a full practice week, and that a club's win-loss record on the page is the record at "
            "publication time (the page shows 2025 Baltimore as 8-9)."
        ),
    ),
    Source(
        id="NFL-STATS",
        tier="league",
        publisher="NFL Support",
        url="https://support.nfl.com/hc/en-us/articles/35869694725268-Stats-Records",
        quote=(
            "For player stats and select records, please visit the NFL.com Players Statistics page "
            "or the Player Index."
        ),
        supports=(
            "Where official player statistics are published. Used only to explain the data boundary: "
            "this project does not scrape those pages (NFL Terms 1.3) and measures from nflverse "
            "instead, labelled unofficial."
        ),
    ),
    Source(
        id="NFL-ROSTER-KC",
        tier="league",
        publisher="NFL.com",
        url="https://www.nfl.com/teams/kansas-city-chiefs/roster",
        quote=(
            "Kansas City Chiefs 2026 Player Roster. Each row: player, jersey number, position, "
            "status (ACT), height, weight, experience, college."
        ),
        supports=(
            "Team-level roster membership and listed position for the current season. Used to show "
            "that NFL.com publishes roster membership but not a numbered depth order."
        ),
    ),
    Source(
        id="NFL-TERMS",
        tier="league",
        publisher="NFL",
        url="https://www.nfl.com/legal/terms/",
        quote=(
            "Section 1.3: Systematic retrieval of data or other content from the Services, "
            "whether to create or compile, directly or indirectly, a collection, compilation, "
            "database, or directory, is prohibited absent our express prior written consent."
        ),
        supports=(
            "The data-rights boundary: this project does not scrape nfl.com. Live official pages "
            "are read and cited; the measurement dataset comes from nflverse."
        ),
    ),
    Source(
        id="NFL-TIEBREAK",
        tier="league",
        publisher="NFL.com",
        url="https://www.nfl.com/standings/tie-breaking-procedures",
        quote=(
            "The NFL's tie-breaking procedures, applied in the order listed, to break ties within "
            "a division and for conference seeding."
        ),
        supports=(
            "Why division and seeding outcomes are discrete and schedule-dependent; used in the "
            "futures-market caveat rather than in any measured number."
        ),
    ),
    # -------------------------------------------------------------- operator
    Source(
        id="DK-ODDS",
        tier="operator",
        publisher="DraftKings",
        url="https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466",
        quote=(
            "American odds show the amount you must wager, or the amount you can win, based on "
            "$100 increments ... If the odds offered on a particular selection are -110, that "
            "means in order to 'win' (profit) $100, you would need to wager $110."
        ),
        supports="The price convention used everywhere on this site (-110, +105, ...).",
    ),
    Source(
        id="DK-PARLAY",
        tier="operator",
        publisher="DraftKings",
        url="https://support.draftkings.com/dk/en-us/what-is-a-parlay-bet?id=kb_article_view&sysparm_article=KB0010683",
        quote=(
            "A parlay is a bet that combines two or more single wagers into one bet ... All added "
            "bets must win in order for the parlay to win. If one selection in the parlay loses, "
            "the whole parlay loses. If a selection results in a push, it is removed from the "
            "parlay and the odds are recalculated accordingly."
        ),
        supports=(
            "The 'all legs must win' settlement rule and the push-strips-a-leg rule used in the "
            "parlay arithmetic and in every simulated parlay on this site."
        ),
    ),
    Source(
        id="DK-CORRELATED",
        tier="operator",
        publisher="DraftKings",
        url="https://support.draftkings.com/dk/en-us/what-is-a-parlay-bet?id=kb_article_view&sysparm_article=KB0010683",
        quote=(
            "For certain selections, the outcomes can be considered correlated. In these cases, "
            "DraftKings reserves the right to restrict parlay betting on these outcomes."
        ),
        supports=(
            "The only operator-text fact about correlation this site relies on: correlation is an "
            "operator-recognised reason to restrict combinations. The size of any correlation on "
            "this site is measured here, never quoted from an operator."
        ),
    ),
    Source(
        id="FD-HOUSE",
        tier="operator",
        publisher="FanDuel Sportsbook",
        url="https://www.fanduel.com/fanduel-sportsbook-house-rules-ct",
        quote=(
            "Effective Date: July 30, 2026 ... The General Rules apply to all bets unless stated "
            "otherwise in the Specific Sports Rules."
        ),
        supports=(
            "Operator house rules are jurisdiction-specific and time-stamped; used to justify the "
            "rule that no settlement assumption is published without a dated operator quote."
        ),
    ),
    # ------------------------------------------------------------- standards
    Source(
        id="NIST-CI",
        tier="standards",
        publisher="NIST/SEMATECH e-Handbook of Statistical Methods",
        url="https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm",
        quote=(
            "Confidence limits are expressed in terms of a confidence coefficient ... a 95 % "
            "confidence interval does not mean that there is a 95 % probability that the interval "
            "contains the true mean."
        ),
        supports=(
            "How confidence intervals and one-sample t-tests are defined; the estimator used to "
            "decide whether a strategy's mean edge is distinguishable from zero."
        ),
    ),
    Source(
        id="NIST-BOOT",
        tier="standards",
        publisher="NIST/SEMATECH e-Handbook of Statistical Methods",
        url="https://www.itl.nist.gov/div898/handbook/eda/section3/bootplot.htm",
        quote=(
            "The bootstrap ... is used to estimate the uncertainty of a statistic ... This "
            "subsample is generated with replacement so that any data point can be sampled "
            "multiple times or not sampled at all. This process is repeated for many subsamples, "
            "typically between 500 and 1000."
        ),
        supports=(
            "The resampling scheme used for every ROI confidence interval and for the no-skill "
            "band on this site (10,000 resamples, above the handbook's typical range)."
        ),
    ),
    Source(
        id="NIST-MULTI",
        tier="standards",
        publisher="NIST/SEMATECH e-Handbook of Statistical Methods",
        url="https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm",
        quote=(
            "Doing pairwise comparison procedures over and over again for all possible pairs "
            "will not, in general, work. This is because the overall significance level is not "
            "as specified for a single pair comparison."
        ),
        supports=(
            "Why the leaderboard corrects for multiplicity (Benjamini-Hochberg and a deflated "
            "Sharpe ratio) instead of ranking raw ROIs, and why pre-registering the family size "
            "matters."
        ),
    ),
    Source(
        id="NIST-SAMPLE",
        tier="standards",
        publisher="NIST/SEMATECH e-Handbook of Statistical Methods",
        url="https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm#Sample%20Size",
        quote=(
            "the width of the interval is controlled by two factors: As N increases, the interval "
            "gets narrower ... The larger the sample standard deviation, the larger the confidence "
            "interval."
        ),
        supports=(
            "The sample-size arithmetic: how many settled bets are needed before an edge of a "
            "given size can be distinguished from zero."
        ),
    ),
    # ----------------------------------------------------------------- index
    Source(
        id="PMC-QB-VALUE",
        tier="index",
        publisher="PubMed Central (peer-reviewed index)",
        url="https://pmc.ncbi.nlm.nih.gov/articles/PMC3496575/",
        quote=(
            "Search-level identification only: PMID/PMC entry reached on 2026-11-12. The article "
            "text was NOT read in this session, so no sentence is quoted and none is used."
        ),
        supports=(
            "NOTHING YET. Listed so the reviewer can see the candidate reference this project "
            "intends to read next; it supports no claim on any page (flag DS-F04)."
        ),
    ),
    # --------------------------------------------------------------- datasets
    Source(
        id="DS-INJURIES",
        tier="dataset",
        publisher="nflverse/nflverse-data (open community dataset, not an official NFL publication)",
        url="https://github.com/nflverse/nflverse-data/releases/tag/injuries",
        quote="Weekly injury reports 2009-2026 (injuries_YYYY.csv).",
        supports=(
            "Reproducible measurement of how the published game status relates to participation. "
            "Never presented as an official NFL statistic."
        ),
    ),
    Source(
        id="DS-PLAYERSTATS",
        tier="dataset",
        publisher="nflverse/nflverse-data (open community dataset)",
        url="https://github.com/nflverse/nflverse-data/releases/tag/player_stats",
        quote="Weekly player statistics, including offense_snaps, by player and week.",
        supports="Which players actually took offensive/defensive snaps in each game.",
    ),
    Source(
        id="DS-SNAPS",
        tier="dataset",
        publisher="nflverse/nflverse-data (open community dataset)",
        url="https://github.com/nflverse/nflverse-data/releases/tag/snap_counts",
        quote="Per-game snap counts by player, split into offense, defense and special teams.",
        supports="Starter vs backup identification (snap_order) on both sides of the ball.",
    ),
    Source(
        id="DS-DEPTH",
        tier="dataset",
        publisher="nflverse/nflverse-data (open community dataset)",
        url="https://github.com/nflverse/nflverse-data/releases/tag/depth_charts",
        quote="Depth charts 2001-2026; from 2025 the schema carries pos_rank per position slot.",
        supports=(
            "Reading an *unofficial* depth order for the current season, labelled as such "
            "everywhere it appears."
        ),
    ),
    Source(
        id="DS-GAMES",
        tier="dataset",
        publisher="nflverse/nfldata (open community dataset)",
        url="https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv",
        quote=(
            "Game results, closing spread/total/moneyline, home and away starting quarterback ids, "
            "1999-2026, pinned at commit a270278f3ac4e937295fe6a27814b3c4a2b62645."
        ),
        supports=(
            "Every measured number on this site that depends on a price or a result. The pinned "
            "commit's SHA-256 is re-checked by this repository's existing CI."
        ),
    ),
    Source(
        id="DS-ROSTERS",
        tier="dataset",
        publisher="nflverse/nfldata (open community dataset)",
        url="https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/rosters.csv",
        quote=(
            "Season rosters 2006-2019 with games, starts, years and approximate value (av) per player."
        ),
        supports=(
            "Historical within-season 'who was the starter and who backed him up' for 2006-2019. "
            "Coverage ends in 2019 — the gap is flagged, not extrapolated."
        ),
    ),
    Source(
        id="REPO-ARITH",
        tier="repo",
        publisher="this repository",
        url="https://github.com/karagemop466-tech/Korea3/tree/main/decision_system",
        quote="Arithmetic identities that must hold by definition (-110 implies 52.381%, etc.).",
        supports="Internal recomputation only; never used as external evidence.",
    ),
)

BY_ID: dict[str, Source] = {s.id: s for s in SOURCES}

# Hosts that a *claim* may rest on.  Everything else is measurement provenance.
OFFICIAL_TIERS = {"league", "operator", "standards", "index"}


def url(source_id: str) -> str:
    return BY_ID[source_id].url


def as_dicts() -> list[dict]:
    return [asdict(s) for s in SOURCES]


def official_ids() -> list[str]:
    return [s.id for s in SOURCES if s.tier in OFFICIAL_TIERS]


if __name__ == "__main__":  # pragma: no cover - human-readable dump
    for s in SOURCES:
        print(f"{s.id:<22} {s.tier:<10} {s.url}")
    print(f"\n{len(SOURCES)} sources · {len(official_ids())} usable as official evidence")
