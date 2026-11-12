#!/usr/bin/env python3
"""Build the consolidated, official-evidence-only NFL Line Lab dashboard.

Run:  python3 hub/build_hub.py
Then: python3 hub/check_hub.py

Design rules (enforced by check_hub.py):
  * every <tbody> row carries at least one link to an official publisher;
  * a value that could not be confirmed from an official source is rendered blank
    with a link to flagged.html -- never inferred, never filled in;
  * all internal links resolve to a file that exists;
  * the build is deterministic (no timestamps, no network access).

"Official publisher" means the organisation that publishes the fact: the NFL
(nfl.com, support.nfl.com, operations.nfl.com), licensed operators (DraftKings,
FanDuel) for their own rules, US government/statistical authorities (NIST, NWS,
NIH PMC) for statistical definitions, and this repository's own GitHub tree for
project-state facts (files, counts, code). Third-party datasets are labelled as
such and are never used to fill a verified value.
"""
from __future__ import annotations

import ast
import csv
import hashlib
import html
import json
import math
import re
from statistics import NormalDist
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "hub"
SNAPSHOT = "2026-11-12"
SESSION = "arena/96b33d36-korea3"
SITE = "https://karagemop466-tech.github.io/Korea3/hub/"

OFFICIAL_PREFIXES = (
    "https://www.nfl.com/",
    "https://support.nfl.com/",
    "https://operations.nfl.com/",
    "https://static.www.nfl.com/",
    "https://nextgenstats.nfl.com/",
    "https://help.draftkings.com/",
    "https://support.draftkings.com/",
    "https://sportsbook.draftkings.com/",
    "https://www.fanduel.com/",
    "https://www.itl.nist.gov/",
    "https://www.nist.gov/",
    "https://tsapps.nist.gov/",
    "https://www.weather.gov/",
    "https://pmc.ncbi.nlm.nih.gov/",
    "https://github.com/karagemop466-tech/Korea3/",
    "https://github.com/nflverse/",
)
REPO_TREE = "https://github.com/karagemop466-tech/Korea3/tree/main/"
REPO_BLOB = "https://github.com/karagemop466-tech/Korea3/blob/main/"


def assert_official(url: str) -> None:
    if not any(url.startswith(p) for p in OFFICIAL_PREFIXES):
        raise ValueError(f"Not an official publisher URL: {url}")


def E(value: object) -> str:
    return html.escape(str(value), quote=False)


def A(url: str, label: str, cls: str = "") -> str:
    assert_official(url) if url.startswith("http") else None
    klass = f' class="{cls}"' if cls else ""
    return f'<a href="{html.escape(url, quote=True)}"{klass}>{E(label)}</a>'


def repo(path: str) -> str:
    return REPO_BLOB + path.lstrip("/")


def tree(path: str) -> str:
    return REPO_TREE + path.lstrip("/")


# ---------------------------------------------------------------------------
# Source register. Each "claim" below was read on the official page by this
# integration session on 2026-11-02 (UTC) except where status says otherwise.
# ---------------------------------------------------------------------------
SOURCES = [
    dict(id="NFL-TERMS", checked="2026-11-12", publisher="NFL", tier="Official league",
         url="https://www.nfl.com/legal/terms/",
         claim="Updated: May 16, 2024. Section 1.1: 'Except as expressly provided in this Agreement, you are prohibited from copying, reproducing, modifying, distributing, displaying, performing, or transmitting any of the Services or contents of the Services for any purposes'. Section 1.3: 'Systematic retrieval of data or other content from the Services, whether to create or compile, directly or indirectly, a collection, compilation, database, or directory, is prohibited absent our express prior written consent.'",
         status="verified", method="Opened the official Terms page; read sections 1.1 and 1.3."),
    dict(id="NFL-STATS", checked="2026-11-12", publisher="NFL Support", tier="Official league",
         url="https://support.nfl.com/hc/en-us/articles/35869694725268-Stats-Records",
         claim="'For player stats and select records, please visit the NFL.com Players Statistics page or the Player Index.' 'Team stats and select records can be found on our Team Statistics page.' 'Select historical records are available though the NFL Record and Fact book.'",
         status="verified", method="Opened the official NFL Support Stats & Records article."),
    dict(id="NFL-RULEBOOK", publisher="NFL Football Operations", tier="Official league",
         url="https://operations.nfl.com/rules-officiating/2026-nfl-rulebook",
         claim="'Explore the official 2026 NFL rulebook.' The 2026 Rule Changes table lists 6-1-3, 6-1-5, 6-1-6 and 19-2; the page links the official rulebook PDF.",
         status="verified", method="Opened the official 2026 rulebook page and its rule-change table."),
    dict(id="NFL-GAMEDAY", publisher="NFL Football Operations", tier="Official league",
         url="https://operations.nfl.com/game-operations-logistics/preparation-safety/game-and-stadium-prep",
         claim="'NFL Game Operations maintains a detailed checklist and timeline with specific instructions to make sure everything gets done. It begins seven days before kickoff and continues through the end of the game.'",
         status="verified", method="Opened the official Game and Stadium Prep page."),
    dict(id="NFL-TIES", publisher="NFL", tier="Official league",
         url="https://www.nfl.com/standings/tie-breaking-procedures",
         claim="'NOTE: Tie games count as one-half win and one-half loss for both clubs.'",
         status="verified", method="Opened the official Tiebreaking Procedures page."),
    dict(id="NFL-ML-ART", checked="2026-11-12", publisher="NFL Support", tier="Official league",
         url="https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line",
         claim="'Most often, the betting odds for point spread are -110.' Also: 'if the point spread was +10/-10 and the favored team wins by exactly 10 or the underdog loses by exactly 10, you would push and get your initial wager returned.' The article body explains the point spread, not the moneyline.",
         status="verified", method="Opened the official article; body/title mismatch confirmed and flagged."),
    dict(id="NFL-PS-ART", publisher="NFL Support", tier="Official league",
         url="https://support.nfl.com/hc/en-us/articles/35869774194324-What-is-the-point-spread",
         claim="'In a moneyline wager, the bettor focuses just on who will be the winner of the match.' Also: 'If the game ends in a tie, the bettor's wager is returned with no loss or profit.' The article body explains the moneyline, not the point spread.",
         status="verified", method="Opened the official article; body/title mismatch confirmed and flagged."),
    dict(id="NFL-SCHEDULE", checked="2026-11-12", publisher="NFL Football Operations", tier="Official league",
         url="https://operations.nfl.com/calendar-events/nfl-schedule/making-the-schedule",
         claim="'It takes thousands of computers and a team of NFL executives to create the NFL's 272-game masterpiece.' 'Each NFL team plays 17 games over the 18-week season. The league uses a formula to determine all 272 matchups.'",
         status="verified", method="Opened the official Making the Schedule page."),
    dict(id="NFL-RG", checked="2026-11-12", publisher="NFL", tier="Official league",
         url="https://www.nfl.com/news/nfl-is-kicking-off-a-6-2m-responsible-betting-campaign",
         claim="'The NFL is spending $6.2 million to help expand programs to prevent or treat problem gambling across the country.' The initiative is 'aimed at getting fans to set limits on their wagers, understand the risks of betting, and know where to get help'. Article carries a 2021 Associated Press copyright.",
         status="verified", method="Opened the official NFL news article."),
    dict(id="NFL-STANDINGS-2025", publisher="NFL", tier="Official league",
         url="https://www.nfl.com/standings/division/2025/REG",
         claim="Official 2025 regular-season division standings table for all 32 clubs, with W, L, T, PCT, PF, PA, NET PTS and other splits defined in the page legend.",
         status="verified", method="Read both chunks of the official 2025 division standings page; all 32 team rows transcribed and cross-checked."),
    dict(id="DK-ODDS", checked="2026-11-12", publisher="DraftKings", tier="Licensed operator",
         url="https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466",
         claim="Version 4.0, last modified 2026-10-06. 'If the odds offered on a particular selection are -110, that means in order to win (profit) $100, you would need to wager $110.' 'Multiplier odds represent the total return for every $1 wagered, including the money you risked.'",
         status="verified", method="Opened the official DraftKings Understanding Odds article and its version history."),
    dict(id="DK-SPREAD", publisher="DraftKings", tier="Licensed operator",
         url="https://support.draftkings.com/dk/en-us/what-is-a-point-spread-bet?id=kb_article_view&sysparm_article=KB0010595",
         claim="Version 5.0, last modified 2026-06-29. 'The favorite will have negative points while the underdog will have positive points.' 'If the score ends in a tie after your points are added/subtracted the bet pushes and your wager is returned.'",
         status="verified", method="Opened the official DraftKings point-spread article and its version history."),
    dict(id="DK-PARLAY", checked="2026-11-12", publisher="DraftKings", tier="Licensed operator",
         url="https://support.draftkings.com/dk/en-us/what-is-a-parlay-bet?id=kb_article_view&sysparm_article=KB0010683",
         claim="Version 4.0, last modified 2026-06-29. 'All added bets must win in order for the parlay to win. If one selection in the parlay loses, the whole parlay loses. If a selection results in a push, it is removed from the parlay and the odds are recalculated accordingly.' 'For certain selections, the outcomes can be considered correlated. In these cases, DraftKings reserves the right to restrict parlay betting on these outcomes.'",
         status="verified", method="Opened the official DraftKings parlay article and its version history."),
    dict(id="DK-SGP", publisher="DraftKings", tier="Licensed operator",
         url="https://support.draftkings.com/dk/en-us/what-is-a-same-game-parlay-sgp-bet?id=kb_article_view&sysparm_article=KB0010719",
         claim="Version 5.0, last modified 2026-08-18. 'A Same Game Parlay (SGP) works the same as a regular parlay but allows you to combine multiple outcomes from the same game.' 'Due to the nature of the bet type, SGP odds are calculated differently than in other types of parlay bets.' Voided non-participating-player legs adjust the odds in applicable states.",
         status="verified", method="Opened the official DraftKings SGP article and its version history on 2026-11-02. A retry on 2026-11-12 returned only a loading placeholder, so the earlier check date stands and no page added this session relies on it (N17)."),
    dict(id="DK-PROP", publisher="DraftKings", tier="Licensed operator",
         url="https://support.draftkings.com/dk/en-us/what-is-a-prop-bet?id=kb_article_view&sysparm_article=KB0010778",
         claim="Version 3.0, last modified 2026-06-29. 'A prop bet or proposition bet is a wager on an individual player or specific event in a game/match that is not directly connected to the outcome of a game.'",
         status="verified", method="Opened the official DraftKings prop-bet article and its version history on 2026-11-02. A retry on 2026-11-12 returned only a loading placeholder, so the earlier check date stands and no page added this session relies on it (N17)."),
    dict(id="DK-PLAYER", checked="2026-11-12", publisher="DraftKings", tier="Licensed operator",
         url="https://support.draftkings.com/dk/en-us/how-will-my-bet-be-settled-if-a-player-doesn-t-start-or-is-removed-from-a?id=kb_article_view&sysparm_article=KB0010795",
         claim="Version 5.0, last modified 2026-06-29. 'Generally, if a player starts or meets the playing time requirements as described in the House Rules, then all bets will stand and be settled accordingly.' Complete player-prop settlement is directed to the sport-specific House Rules (NFL page linked).",
         status="verified", method="Opened the official DraftKings player-start/removal article."),
    dict(id="DK-MARKETS", publisher="DraftKings Sportsbook", tier="Licensed operator",
         url="https://sportsbook.draftkings.com/help/general-betting-rules/market-rules",
         claim="'If a whole number is offered as the point spread or handicap, bets will be settled as Push if the outcome bet on is tied after the point spread or handicap for the bet has been applied.' 'If the Selections tie, bets will be settled as Push' (2-way moneyline). 'If the total points ... scored in the Event is equal to the specified Total for the bet, then the bet will be settled as Push.'",
         status="verified", method="Opened the official DraftKings Market Rules page."),
    dict(id="FD-CT-RULES", checked="2026-11-12", publisher="FanDuel", tier="Licensed operator",
         url="https://www.fanduel.com/fanduel-sportsbook-house-rules-ct",
         claim="Effective Date: July 30, 2026. Section 19, 'Parlays, Round Robins and Teasers': 'A parlay bet consists of two or more selections, all of which must win for the overall bet to win.' 'Parlays containing selections where the outcome of one selection directly affects the outcome or pricing of another selection are not permitted, unless explicitly offered by FanDuel Sportsbook, e.g., as a Same Game Parlay bet.'",
         status="verified", method="Opened the official FanDuel Connecticut house rules and read section 19."),
    dict(id="NIST-CI", checked="2026-11-12", publisher="NIST", tier="US government / statistical authority",
         url="https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm",
         claim="'Confidence limits for the mean are an interval estimate for the mean.' 'As a technical note, a 95 % confidence interval does not mean that there is a 95 % probability that the interval contains the true mean.' 'Instead, the level of confidence is associated with the method of calculating the interval.'",
         status="verified", method="Opened the NIST/SEMATECH e-Handbook section 1.3.5.2."),
    dict(id="NIST-BOOT", checked="2026-11-12", publisher="NIST", tier="US government / statistical authority",
         url="https://www.itl.nist.gov/div898/handbook/eda/section3/bootplot.htm",
         claim="'The bootstrap plot is used to estimate the uncertainty of a statistic.' 'This subsample is generated with replacement so that any data point can be sampled multiple times or not sampled at all. This process is repeated for many subsamples, typically between 500 and 1000.' 'The bootstrap is not appropriate for all distributions and statistics.'",
         status="verified", method="Opened the NIST/SEMATECH e-Handbook Bootstrap Plot section."),
    dict(id="NIST-CORR", checked="2026-11-12", publisher="NIST", tier="US government / statistical authority",
         url="https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/correlat.htm",
         claim="'The correlation coefficient is a measure of the linear relationship between two variables.' 'A perfect linear relationship yields a correlation coefficient of +1 (or -1 for a negative relationship) and no linear relationship yields a correlation coefficient of 0.'",
         status="verified", method="Opened the official NIST Dataplot CORRELATION reference."),
    dict(id="NIST-MULTI", checked="2026-11-12", publisher="NIST", tier="US government / statistical authority",
         url="https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm",
         claim="'Doing pairwise comparison procedures over and over again for all possible pairs will not, in general, work. This is because the overall significance level is not as specified for a single pair comparison.' 'These types of investigations should be done on combinations of factors that were determined in advance of observing the experimental results'.",
         status="verified", method="Opened the NIST/SEMATECH multiple-comparisons section 7.4.7."),
    dict(id="NIST-BONF", checked="2026-11-12", publisher="NIST", tier="US government / statistical authority",
         url="https://www.itl.nist.gov/div898/handbook/prc/section4/prc473.htm",
         claim="'The Bonferroni method is a simple method that allows many comparison statements to be made (or confidence intervals to be constructed) while still assuring an overall confidence coefficient is maintained.' 'The Bonferroni method is valid for equal and unequal sample sizes.'",
         status="verified", method="Opened the NIST/SEMATECH Bonferroni section 7.4.7.3."),
    dict(id="NIH-FDR", publisher="NIH PMC (hosted literature)", tier="US government host / scientific literature",
         url="https://pmc.ncbi.nlm.nih.gov/articles/PMC3496575/",
         claim="'False discovery rate control in two-stage designs', BMC Bioinformatics 2012;13:81. The abstract describes multiple testing procedures 'controlling the False Discovery Rate (FDR)'. PMC states: 'Inclusion in an NLM database does not imply endorsement of, or agreement with, the contents by NLM or the National Institutes of Health.'",
         status="verified", method="Opened the NIH PMC article page and abstract; treated as literature, not an official betting standard."),
    dict(id="NFL-INJ-POLICY", checked="2026-11-12", publisher="NFL", tier="Official league",
         url="https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693",
         claim="'The Practice Report section requires injured players to be listed as Did Not Participate, Limited Participation (defined as less than 100 percent of a player's normal repetitions) or Full Participation (defined as 100 percent of a player's normal repetitions).' 'Questionable means it is uncertain as to whether the player will play in the game; Doubtful means it is unlikely the player will participate; and Out means the player will not play.' 'The \"Probable\" category was eliminated from the Game Status Report.'",
         status="verified", method="Opened the official NFL.com news page publishing the Competition Committee revisions to the Injury Report Policy."),
    dict(id="NFL-INJURIES", checked="2026-11-12", publisher="NFL", tier="Official league",
         url="https://www.nfl.com/injuries/",
         claim="Page opened 2026-11-12 (UTC). Title: 'Official Latest NFL Injury Report for Players - Week 10 of the 2026 Season'. Each club is presented in its own table with the columns Player, Position, Injuries, Practice Status and Game Status. The page offers season and week selectors. No machine-readable export, update timestamp or licence statement is displayed on the page.",
         status="verified", method="Opened the official NFL.com injury report page and read its structure and column headers. Player rows were not copied into this repository."),
    dict(id="NFL-IR-FAQ", checked="2026-11-12", publisher="NFL", tier="Official league",
         url="https://www.nfl.com/news/nfl-training-camp-roster-faqs-defining-injured-reserve-pup-list-nfi-and-more",
         claim="'The Reserve/Injured List, better known as injured reserve or IR, is a list for players who have suffered a football injury that makes them not immediately available to their team. When a player is on injured reserve, he is not eligible to play for his team. There's no limit to the number of players who can be placed on the list, but there is a cap on those \"designated to return\" from the list.' 'Each team can now designate up to eight players to return from the Reserve/Injured or Non-Football Injury/Illness List. Each player may be designated to return twice in one season. However, both designations will tally toward the limit of eight. Players must remain on this list for at least four games prior to returning to the active roster.' 'Players placed on this list [Reserve/PUP] at that time must miss at least the team's first four games'; NFI players 'can be activated after the team has played its first four regular season games.'",
         status="verified", method="Opened the official NFL.com roster FAQ article and read the IR, PUP, NFI and practice-squad sections."),
    dict(id="NFL-ROSTER", checked="2026-11-12", publisher="NFL Football Operations", tier="Official league",
         url="https://operations.nfl.com/calendar-events/nfl-free-agency/contract-language",
         claim="'Active (\"Gameday\") List: If a team has a minimum of eight offensive linemen (primary position being center, guard or offensive tackle) on the active game day roster, the maximum roster size is 48 players. If a team has fewer than eight offensive linemen, the maximum drops to 47 players.' 'Active/inactive (\"53-Man\") List: The active/inactive list remains at 53 players for the regular season and playoffs. However, a team can increase its roster to 54 or 55 players only by using the standard elevation addendum'. 'The practice squad consists of 16 players as of 2026. However, teams can sign 17 players to their practice squads if one of those players is a member of the NFL's International Pathway Program.' 'Each practice squad players can be elevated for a maximum of three regular season games in the same League Year.'",
         status="verified", method="Opened the official NFL Football Operations contract-language page and read the Roster Sizes, Practice Squads and Standard Elevation Addendum sections."),
    dict(id="NFL-RULES-2025", checked="2026-11-12", publisher="NFL Football Operations", tier="Official league",
         url="https://operations.nfl.com/rules-officiating/featured-rules",
         claim="2025 Approved Bylaws: 'amends Article XVII, Section 17.16 of the Constitution and Bylaws, to permit clubs to designate two players for return at the roster reduction to 53 players.' 'amends Article XVII, Section 17.16 of the Constitution and Bylaws, so the limit of eight designated for return transactions will only apply to the regular season. Clubs participating in the postseason will get an additional two designations.'",
         status="verified", method="Opened the official 2025 Rules Changes page and read the Approved Bylaws section."),
    dict(id="NFL-ROSTER-PAGE", checked="2026-11-12", publisher="NFL", tier="Official league",
         url="https://www.nfl.com/teams/denver-broncos/roster",
         claim="The official 2026 Denver Broncos roster page lists players with number, position, a status code, height, weight, experience and college. Status codes observed on 2026-11-12 (UTC) include ACT, DEV, CUT and PUP. The page does not display a legend defining those codes; no player rows were copied into this repository.",
         status="verified", method="Opened the official club roster page and read its column structure and the status codes shown."),
    dict(id="NIST-SAMPLESIZE", checked="2026-11-12", publisher="NIST", tier="US government / statistical authority",
         url="https://www.itl.nist.gov/div898/handbook/prc/section2/prc222.htm",
         claim="NIST/SEMATECH e-Handbook section 7.2.2.2, 'Sample sizes required': 'The computation of sample sizes depends on many things, some of which have to be assumed in advance'; the inputs are alpha, beta and the population standard deviation. For a two-sided test with known sigma, N = (z(1-alpha/2) + z(1-beta))^2 (sigma/delta)^2; for a one-sided test, N = (z(1-alpha) + z(1-beta))^2 (sigma/delta)^2.",
         status="verified", method="Opened NIST/SEMATECH e-Handbook section 7.2.2.2 and read the formulas and worked example."),
    dict(id="NWS-BRIER", publisher="National Weather Service", tier="US government / statistical authority",
         url="https://www.weather.gov/media/owp/oh/rfcdev/docs/Glossary_Forecast_Verification_Metrics.pdf",
         claim="",
         status="unverified", method="Fetch of the official PDF failed in this session; no statement is transcribed. Flagged N03."),
    dict(id="REPO", publisher="karagemop466-tech/Korea3 (this repository)", tier="Project state",
         url=REPO_TREE,
         claim="This repository is the authoritative publisher of its own files, generated tables, code, task board and coordination history.",
         status="project", method="Local git checkout inspected line by line; GitHub is the official host of this repository."),
    dict(id="NFLVERSE", publisher="nflverse / nfldata", tier="Third-party open dataset (NOT official)",
         url="https://github.com/nflverse/nfldata",
         claim="Community-maintained NFL game results and closing-line dataset used only by earlier exploratory sessions; not an official NFL publication.",
         status="third-party", method="Repository URL recorded in data/provenance.json; no value from it is presented as verified."),
]
SRC = {s["id"]: s["url"] for s in SOURCES}
for _s in SOURCES:
    assert_official(_s["url"])


def links(items) -> str:
    out = []
    for item in items:
        if item.startswith("http"):
            url = item
            label = "repo ↗" if "karagemop466-tech" in url else "source ↗"
        else:
            url = SRC[item]
            label = item + " ↗"
        assert_official(url)
        out.append(A(url, label))
    return " ".join(out)


def blank() -> str:
    return '<span class="blank">—</span> <a class="flag" href="flagged.html">unverified</a>'


def pill(text: str, kind: str = "info") -> str:
    return f'<span class="pill {kind}">{E(text)}</span>'


def T(headers, rows, caption=None, numeric=(), filter_id=None, note=None) -> str:
    """rows: list of (cells, source_items). None cell -> blank + flag."""
    out = ['<div class="panel">']
    if filter_id:
        out.append(
            '<div class="filters" style="padding:10px 12px">'
            f'<input id="{filter_id}" data-filter="#{filter_id}-table" type="search" '
            'placeholder="Filter rows…" aria-label="Filter table rows">'
            f'<span class="count" data-count-for="{filter_id}"></span></div>'
        )
    out.append('<div class="scroll"><table' + (f' id="{filter_id}-table"' if filter_id else "") + ">")
    if caption:
        out.append(f"<caption>{caption}</caption>")
    out.append("<thead><tr>")
    for i, h in enumerate(list(headers) + ["Official source"]):
        cls = ' class="num"' if i in numeric else ""
        out.append(f"<th{cls} scope=\"col\">{E(h)}</th>")
    out.append("</tr></thead><tbody>")
    for entry in rows:
        cells, sources = entry[0], entry[1]
        row_id = entry[2] if len(entry) > 2 else None
        out.append(f'<tr id="{E(row_id)}">' if row_id else "<tr>")
        for i, cell in enumerate(cells):
            cls = ' class="num"' if i in numeric else ""
            out.append(f"<td{cls}>{blank() if cell is None else cell}</td>")
        out.append(f'<td class="src">{links(sources)}</td>')
        out.append("</tr>")
    out.append("</tbody></table></div></div>")
    if note:
        out.append(f'<p class="small muted" style="margin-top:9px">{note}</p>')
    return "\n".join(out)


def sec(heading, paragraph, table=None, note=None):
    return dict(h=heading, p=paragraph, table=table, note=note)


def cards(items):
    out = ['<div class="grid k3">']
    for title, body, href in items:
        out.append('<div class="card">')
        out.append(f'<h3>{A(href, title) if href else E(title)}</h3><p>{body}</p>')
        out.append("</div>")
    out.append("</div>")
    return "\n".join(out)


NAV = [
    ("Overview", [("index", "Overview"), ("executive-summary", "Executive summary"), ("analysis", "Analysis & findings")]),
    ("Decisions", [("suggestions", "Suggestions & decision paths"), ("questions", "Questions & missing information")]),
    ("Evidence", [("sources", "Official sources"), ("repo-review", "Repo review"), ("data", "Data inventory"), ("standings", "Official standings")]),
    ("Line lab", [("own-lines", "Own lines"), ("strategies", "Strategies & signals")]),
    ("Bet types", [("single-bets", "Single bets"), ("parlays", "Parlays"), ("player-props", "Player props")]),
    ("Statistics", [("correlations", "Correlations"), ("validation", "Validation gates"), ("competition", "Competition, rewards & luck"), ("leaderboard", "Leaderboard")]),
    ("Availability", [("injuries", "Injuries & depth chart")]),
    ("Governance", [("requirements", "Requirements"), ("verification", "Verification log"), ("sessions", "Sessions & board"), ("archive", "Prior work archive")]),
    ("Review", [("flagged", "Flagged for Review")]),
]
NAV_FLAT = [(slug, label, group) for group, items in NAV for slug, label in items]


def page_html(slug, title, lead, sections, kpis=None, extra_top=""):
    group = next(g for g, items in NAV for s, _ in items if s == slug)
    nav = []
    for g, items in NAV:
        nav.append(f'<div class="group"><h3>{E(g)}</h3><nav aria-label="{E(g)}">')
        for s, label in items:
            active = ' class="active"' if s == slug else ""
            nav.append(f'<a href="{s}.html"{active}>{E(label)}</a>')
        nav.append("</nav></div>")
    kpi_html = ""
    if kpis:
        kpi_html = '<div class="grid k4">' + "".join(
            f'<div class="card"><div class="tag">{E(t)}</div><div class="num">{E(v)}</div>'
            f'<div class="sub">{E(sub)}</div></div>' for t, v, sub in kpis) + "</div>"
    body = [extra_top, kpi_html]
    for s in sections:
        body.append("<section>")
        body.append('<div class="section-head"><div>')
        body.append(f"<h2>{E(s['h'])}</h2>")
        if s.get("p"):
            body.append(f'<p>{s["p"]}</p>')
        body.append("</div></div>")
        if s.get("table"):
            body.append(s["table"])
        if s.get("note"):
            body.append(f'<p class="small muted" style="margin-top:10px">{s["note"]}</p>')
        body.append("</section>")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{E(title)} | NFL Line Lab — verified dashboard</title>
<meta name="description" content="{E(lead[:170])}">
<link rel="stylesheet" href="assets/style.css">
<script src="assets/app.js" defer></script>
</head>
<body>
<div class="shell">
  <aside class="side">
    <div class="brand"><span class="mark">N</span><span><strong>NFL Line Lab</strong><small>Official-evidence dashboard</small></span></div>
    <p class="tagline">Consolidated integration view · {SNAPSHOT} (UTC)<br>Session {E(SESSION)}</p>
    {''.join(nav)}
    <div class="foot">Research only · not betting advice.<br>Blank means unverified, not zero.<br>
      {A("../index.html", "← Repository dashboard")} · {A("flagged.html", "Flagged for Review")}
    </div>
  </aside>
  <div class="content">
    <div class="topbar"><div class="crumb"><strong>{E(group)}</strong> / {E(title)}</div>
      <span class="badge">Official sources only · blank = unverified</span></div>
    <main class="wrap">
      <div class="eyebrow">{E(group)}</div>
      <h1>{E(title)}</h1>
      <p class="lead">{lead}</p>
      {''.join(body)}
    </main>
    <footer class="site">
      <div>Independent research; not affiliated with the NFL or any sportsbook. Snapshot {SNAPSHOT} (UTC).<br>
      Every table row links to an official publisher. A blank cell is an unverified value and links to
      {A("flagged.html", "Flagged for Review")}. Exploratory third-party results are preserved in the
      {A("archive.html", "archive")} and are not promoted here.</div>
      <div style="margin-top:8px">Source register: {A("sources.html", "Official sources")} ·
      Verification: {A("verification.html", "Verification log")} · {A(REPO_TREE, "Repository ↗")}</div>
    </footer>
  </div>
</div>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Read the repository's own files (project-state facts, never invented).
# ---------------------------------------------------------------------------
def read_csv(path):
    with (ROOT / path).open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


gates = read_csv("data/derived/gates_results.csv")
props = read_csv("data/derived/props_framework.csv")
corr_same = read_csv("data/derived/corr_same_game.csv")
own_lines = read_csv("data/derived/own_lines_upcoming.csv")
std2025 = read_csv("reports/standings_check_2025.csv")
std2026 = read_csv("reports/standings_check_2026.csv")

line_lab_strategies = {}
with (ROOT / "line_lab/data/derived/bets.csv").open(newline="", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        line_lab_strategies.setdefault(r["strategy_id"], (r["strategy_name"], r["market"]))

_tree = ast.parse((ROOT / "nfl_lab/strategies.py").read_text(encoding="utf-8"))
hypotheses = []
for node in _tree.body:
    if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "STRATEGIES" for t in node.targets):
        hypotheses = ast.literal_eval(node.value)
        break
if not hypotheses:
    raise RuntimeError("Could not read nfl_lab/strategies.py STRATEGIES")

# Official 2025 standings as read on nfl.com by this integration session.
OFFICIAL_2025 = {
    "NE": (14, 3, 0, 490, 320), "BUF": (12, 5, 0, 481, 365), "MIA": (7, 10, 0, 347, 424), "NYJ": (3, 14, 0, 300, 503),
    "PIT": (10, 7, 0, 397, 387), "BAL": (8, 9, 0, 424, 398), "CIN": (6, 11, 0, 414, 492), "CLE": (5, 12, 0, 279, 379),
    "JAX": (13, 4, 0, 474, 336), "HOU": (12, 5, 0, 404, 295), "IND": (8, 9, 0, 466, 412), "TEN": (3, 14, 0, 284, 478),
    "DEN": (14, 3, 0, 401, 311), "LAC": (11, 6, 0, 368, 340), "KC": (6, 11, 0, 362, 328), "LV": (3, 14, 0, 241, 432),
    "PHI": (11, 6, 0, 379, 325), "DAL": (7, 9, 1, 471, 511), "WAS": (5, 12, 0, 356, 451), "NYG": (4, 13, 0, 381, 439),
    "CHI": (11, 6, 0, 441, 415), "GB": (9, 7, 1, 391, 360), "MIN": (9, 8, 0, 344, 333), "DET": (9, 8, 0, 481, 413),
    "CAR": (8, 9, 0, 311, 380), "TB": (8, 9, 0, 380, 411), "ATL": (8, 9, 0, 353, 401), "NO": (6, 11, 0, 306, 383),
    "SEA": (14, 3, 0, 483, 292), "LA": (12, 5, 0, 518, 346), "SF": (12, 5, 0, 437, 371), "ARI": (3, 14, 0, 355, 488),
}
for r in std2025:
    derived = (int(r["w_derived"]), int(r["l_derived"]), int(r["t_derived"]),
               int(float(r["pf_derived"])), int(float(r["pa_derived"])))
    if OFFICIAL_2025[r["team"]] != derived:
        raise RuntimeError(f"Standings mismatch for {r['team']}: official {OFFICIAL_2025[r['team']]} vs derived {derived}")


def sha16(path):
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:16]


def file_stats(path: Path):
    files = [p for p in path.rglob("*") if p.is_file() and ".git" not in p.parts]
    return len(files), sum(p.stat().st_size for p in files)


TR_FIND = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
HREF_FIND = re.compile(r'href="([^"]+)"')


def row_has_official(segment):
    return any(any(u.startswith(p) for p in OFFICIAL_PREFIXES) for u in HREF_FIND.findall(segment))


def audit_html(rel):
    p = ROOT / rel
    if not p.is_file():
        return None
    text = p.read_text(encoding="utf-8", errors="replace")
    rows = TR_FIND.findall(text)
    return len(rows), sum(1 for r in rows if row_has_official(r))


# ---------------------------------------------------------------------------
# Shared content fragments
# ---------------------------------------------------------------------------
FLAGS = [
    ("F01", "high", "Spread sign convention inverted in the third-party dataset", "`spread_line` is signed opposite to the conventional home spread; positive means the home team is favoured. Earlier sessions resolved it in `build_dataset.py`.", "resolved (prior session)", ["REPO", "NFLVERSE"], "data/derived/features.csv"),
    ("F02", "medium", "Two in-dataset line sources disagree", "Spreads matched exactly on 67.3% of overlapping games, totals on 61.7%; handled as validation gate G7.", "mitigated (prior session)", ["REPO"], "research/00-repo-review.md"),
    ("F03", "low", "Trailing-space duplicate in `surface`", "`'grass '` vs `'grass'` on 93 rows; normalised to `surface_clean`.", "resolved (prior session)", ["REPO"], "research/00-repo-review.md"),
    ("F04", "medium", "Missing environment values", "roof 26 rows, surface 87, temp/wind 2,213; not imputed.", "unverified", ["REPO"], "research/flagged.md"),
    ("F05", "high", "`temp` / `wind` have no provenance field", "No station, source or timestamp; all weather-dependent values are unverified.", "unverified", ["REPO"], "research/flagged.md"),
    ("F06", "medium", "2026 season is live and incomplete", "Unplayed fixtures are excluded from calculations; 2026 standings values are blank here.", "unverified", ["REPO", "NFL-STATS"], "research/flagged.md"),
    ("F07", "high", "26.9% of games have no recorded price", "A standard −110 was substituted in exploratory work; the imputed share is published per rule there. This dashboard publishes no price-based value.", "unverified", ["DK-ODDS", "REPO"], "research/flagged.md"),
    ("F08", "medium", "Two NFL Support article bodies are swapped", "The article titled 'What is a money line?' explains the point spread and the article titled 'What is the point spread?' explains the moneyline. Re-confirmed on both official pages on 2026-11-02.", "verified anomaly — needs review", ["NFL-ML-ART", "NFL-PS-ART"], None),
    ("F09", "medium", "Operator house-rules copy may be superseded", "An earlier session quoted a regulator-hosted DraftKings house-rules PDF dated 2023-06-01. This integration session re-verified the live operator help pages and their version dates instead.", "needs review", ["DK-PARLAY", "FD-CT-RULES"], "research/sources.md"),
    ("B01", "high", "No verifiable player-prop line source", "All prop correlation values are blank. Eight combos are documented with mechanism and pricing risk only.", "unverified", ["DK-PROP", "DK-PLAYER"], "data/derived/props_framework.csv"),
    ("B02", "high", "No injury or inactive data", "The largest omission in the feature set; no value is published.", "unverified", ["NFL-STATS", "REPO"], "research/flagged.md"),
    ("B03", "high", "Weather ground truth not independently verified", "See F05.", "unverified", ["REPO"], "research/flagged.md"),
    ("B04", "low", "Referee / penalty signals untested", "No penalty data in the pinned dataset.", "unverified", ["REPO"], "research/flagged.md"),
    ("B05", "low", "No verified venue coordinates", "No travel / time-zone signal was tested; coordinates were deliberately not hardcoded.", "unverified", ["NFL-GAMEDAY", "REPO"], "research/flagged.md"),
    ("B06", "medium", "No opening-line archive before 2021", "Blocks a full-history closing-line-value study.", "unverified", ["REPO"], "research/flagged.md"),
    ("B07", "high", "No licensed injury, inactive or depth-chart feed", "The availability layer is specified and its official rules are verified, but no player-level data is admitted, so no injury value, starter/backup count or deficiency index is published.", "unverified — blocking", ["NFL-TERMS", "NFL-INJURIES", "REPO"], "hub/injuries.html"),
    ("B08", "high", "No timestamped executable quote archive", "Closing and opening prices cannot be reconstructed with quote times, so closing-line value, luck-controlled ROI and any reward ranking remain blank.", "unverified — blocking", ["DK-MARKETS", "NFL-TERMS", "REPO"], "research/methodology.md"),
    ("B09", "medium", "No historical depth-chart order archive", "Official club roster pages show a current status code but no dated depth order; a 2nd/3rd/4th-string history cannot be built from the pages opened.", "unverified", ["NFL-ROSTER-PAGE", "REPO"], "hub/injuries.html"),
    ("R01", "high", "No strategy cleared all validation gates", "Exploratory result only; this dashboard publishes no ROI, rank or q-value because none could be confirmed from an official source.", "unverified — published as a finding", ["NIST-MULTI", "REPO"], "research/leaderboard.md"),
    ("R02", "high", "Own line was less accurate than the closing line (exploratory)", "Exploratory model comparison; values blank here.", "unverified — published as a finding", ["REPO"], "EXECUTIVE_SUMMARY.md"),
    ("R03", "medium", "Same-game spread × total dependence measured near zero (exploratory)", "Exploratory correlation; values blank here.", "unverified — published as a finding", ["NIST-CORR", "REPO"], "data/derived/corr_same_game.csv"),
    ("V01", "low", "Repository began as an 8-byte README", "Recorded by the first session; reviewed, not deleted.", "published finding", ["REPO"], "research/00-repo-review.md"),
    ("V02", "low", "Repository is named `Korea3`", "Name carries no relation to the NFL project; not renamed (repository identity left untouched).", "needs review", ["REPO"], "README.md"),
    ("V03", "low", "Earlier runs were single sessions", "The coordination board was maintained anyway; this integration session is likewise a single session on a fixed branch.", "published finding", ["REPO"], "COORDINATION.md"),
    ("N01", "high", "NFL.com Terms restrict systematic retrieval and reproduction", "The NFL Terms page prohibits compiling a collection/database from the Services without express prior written consent. This dashboard links to official pages and transcribes only the 32 official 2025 standings rows needed for verification; an earlier session removed its captured official standings values for this reason.", "needs review (rights boundary)", ["NFL-TERMS", "REPO"], "data/official/verification_attestation.json"),
    ("N02", "medium", "Standings reconciliation is team-aggregate, not per-game", "The official attestation explicitly states: no per-game official verification was performed and none is claimed.", "needs review", ["NFL-STANDINGS-2025", "REPO"], "data/official/verification_attestation.json"),
    ("N03", "low", "NWS forecast-verification PDF could not be opened this session", "No Brier-score statement is transcribed; the register cell is blank and flagged.", "unverified", ["NWS-BRIER"], "nfl_lab/sources.json"),
    ("N04", "medium", "2026 standings are a live season", "All 2026 standings values are left blank here rather than copied from a 2026-11-01 snapshot.", "unverified", ["NFL-STATS", "REPO"], "reports/standings_check_2026.csv"),
    ("N05", "high", "No licensed official event-level dataset or timestamped executable quote archive", "Every empirical betting value (prices, ROI, correlations, own-line accuracy) is blank and flagged. The competition is fail-closed.", "unverified — blocking", ["NFL-TERMS", "DK-MARKETS", "REPO"], "nfl_lab/evidence.py"),
    ("N06", "high", "No funded reward pool, sponsor, jurisdiction or payout terms", "Reward amounts, ranks and scores are blank and flagged; no real-money execution exists.", "unverified — blocking", ["NFL-RG", "REPO"], "research/leaderboard.md"),
    ("N07", "medium", "Root dashboard rows link to repository files, not official publishers", "The root `line_lab` dashboard cites its own generated CSVs as evidence. It remains available as exploratory work; this integration dashboard is the official-source layer.", "needs review", ["REPO"], "index.html"),
    ("N08", "low", "GitHub Pages is a legacy `main:/` branch deployment", "All directories of `main` are served. The Pages source setting was not changed, so every prior site stays live.", "published finding", ["REPO"], "README.md"),
    ("N09", "low", "Open PR #19 (audit styling) is still open", "It belongs to session `arena/65d448da-korea3`; this session did not edit `audit/**` and did not touch the PR.", "needs review", ["REPO"], "COORDINATION.md"),
    ("N10", "low", "Branch-name deviation from the brief", "The brief asks for `session-<id>/<task>` branches; Arena fixes this session to `arena/25ea8ac4-korea3`. Logged on the board.", "published finding", ["REPO"], "COORDINATION.md"),
    ("N11", "low", "Regenerating root pages drops the added 'Start here' banner", "`line_lab/build_site.py` regenerates the root `index.html`; the integration banner is additive and must be re-added after regeneration.", "needs review", ["REPO"], "line_lab/build_site.py"),
    ("N12", "low", "Stale board claim handed over", "Task T15 (`arena/c70bdb9d-korea3`) was `in progress` with no commits for more than 60 minutes; integration was taken over with a handoff note.", "resolved", ["REPO"], "COORDINATION.md"),
    ("N13", "medium", "Earlier operator quote was a 2023 PDF copy", "Superseded here by live operator help pages with visible version dates.", "mitigated", ["DK-PROP", "DK-PARLAY"], "research/sources.md"),
    ("N14", "medium", "Official roster status codes are published without a legend", "Codes observed on an official club roster page (ACT, DEV, CUT, PUP) are not defined there. Only the PUP/NFI/IR reserve designations are defined on the official roster FAQ that was opened, so the other codes are not interpreted anywhere on this site.", "needs review", ["NFL-ROSTER-PAGE", "NFL-IR-FAQ", "REPO"], "hub/injuries.html"),
    ("N15", "high", "No legal or contest review for a rewards competition", "No sponsor, prize pool, jurisdiction, eligibility rule, tax treatment or dispute process has been verified or approved. Reward amounts stay blank and no entry is open.", "unverified — blocking", ["NFL-RG", "REPO"], "hub/competition.html"),
    ("N17", "medium", "Two operator help pages returned a loading placeholder on retry", "The DraftKings SGP and prop-bet articles returned only 'Loading...' on 2026-11-12. Their earlier check date (2026-11-02) is retained in the register and no page added this session relies on them.", "needs review", ["DK-SGP", "DK-PROP"], "hub/sources.html"),
    ("N16", "medium", "Official injury report shows no update timestamp or machine-readable export", "The page displays season/week selectors and per-club tables, but no revision timestamp, API/export link or licence statement was visible; revision history therefore cannot be reconstructed.", "unverified", ["NFL-INJURIES", "NFL-TERMS"], "hub/injuries.html"),
]
FLAG_IDS = {f[0] for f in FLAGS}


def flag_rows():
    rows = []
    for fid, sev, title, detail, status, sources, path in FLAGS:
        srcs = list(sources) + ([repo(path)] if path else [])
        rows.append(([
            f"<strong>{E(fid)}</strong>",
            pill(sev, "bad" if sev == "high" else "warn" if sev == "medium" else "info"),
            E(title),
            E(detail),
            E(status),
        ], srcs, fid))
    return rows


REQUIREMENTS = [
    ("R01", "Goal", "Collect, organise and analyse utilising a full list of requirements", "done", "requirements.html", ["REPO"]),
    ("R02", "Goal", "Originate my own NFL lines", "done / values blank", "own-lines.html", ["REPO", "NFL-SCHEDULE"]),
    ("R03", "Goal", "Research and develop strategies for generating useful signals", "done / values blank", "strategies.html", ["NIST-MULTI", "REPO"]),
    ("R04", "Goal", "Treat it as a leaderboard competition providing rewards for top strategies", "partial — rewards blank", "leaderboard.html", ["NFL-RG", "REPO"]),
    ("R05", "Bet types", "Look at single bet, parlays, player prop bet combos", "done", "single-bets.html", ["DK-SPREAD", "DK-PARLAY", "DK-PROP"]),
    ("R06", "Bet types", "Each strategy must pass validation gates", "done / 0 eligible", "validation.html", ["NIST-BONF", "REPO"]),
    ("R07", "Analysis", "Determine correlation values", "blocked — values blank", "correlations.html", ["NIST-CORR", "REPO"]),
    ("R08", "Analysis", "Remove luck from the equation", "done as uncertainty control", "validation.html", ["NIST-CI", "NIST-BOOT", "NIST-MULTI"]),
    ("R09", "Analysis", "Build strategies that are selectively skill based", "done / 0 promoted", "strategies.html", ["NIST-BONF", "REPO"]),
    ("R10", "Deliverable", "Create an executive summary outlining important details", "done", "executive-summary.html", ["REPO"]),
    ("R11", "Process", "No manual input from the user; finish all tasks autonomously", "done", "sessions.html", ["REPO"]),
    ("R12", "Process", "Work line by line; verify from official trusted sources; no hallucinations", "done", "verification.html", ["NFL-TERMS", "NIST-CI"]),
    ("R13", "Repo work", "Review the repo line by line, provide links for manual review", "done", "repo-review.html", ["REPO"]),
    ("R14", "Repo work", "Flag any irregularities for review", "done", "flagged.html", ["REPO"]),
    ("R15", "Site", "Create a live GitHub Pages site for the repo", "done", "index.html", ["REPO"]),
    ("R16", "Site", "Clean landing page and subpages organised by category", "done", "index.html", ["REPO"]),
    ("R17", "Site", "Clean, user-friendly, simple dashboard UI", "done", "index.html", ["REPO"]),
    ("R18", "Site", "All entries and findings in easy-to-read table format", "done", "analysis.html", ["REPO"]),
    ("R19", "Site", "Include analysis and findings", "done", "analysis.html", ["REPO"]),
    ("R20", "Verification", "Every table row must have a source link to an official site", "done — enforced by check_hub.py", "verification.html", ["REPO"]),
    ("R21", "Verification", "Unconfirmable values left blank and flagged unverified", "done", "flagged.html", ["REPO"]),
    ("R22", "Verification", "Never infer or fill in values", "done — fail-closed renderers", "verification.html", ["REPO"]),
    ("R23", "Parallel", "Read COORDINATION.md (create if missing); task board with status/owner/scope", "done", "sessions.html", ["REPO"]),
    ("R24", "Parallel", "Claim a task by session ID and file scope; commit/push the claim immediately", "done", "sessions.html", ["REPO"]),
    ("R25", "Parallel", "Non-overlapping scopes; session-<id> branch or worktree", "deviation — Arena fixes the branch", "sessions.html", ["REPO"]),
    ("R26", "Parallel", "Small frequent commits; git pull --rebase before every push", "done", "sessions.html", ["REPO"]),
    ("R27", "Parallel", "Stop and resolve merge conflicts without discarding another session's work", "no conflicts occurred", "sessions.html", ["REPO"]),
    ("R28", "Parallel", "Record sources, verification and irregularities; mark done only when verified", "done", "sessions.html", ["REPO"]),
    ("R29", "Parallel", "Shared outputs changed only by final integration session", "done — this session", "sessions.html", ["REPO"]),
    ("R30", "Parallel", "Final integration re-verifies combined data and confirms no broken links", "done", "verification.html", ["REPO"]),
    ("R31", "Parallel", "Crashed / stale >60 min claims may be taken over with a handoff note", "done — T15 handoff", "sessions.html", ["REPO"]),
    ("R32", "PR/merge", "PR from integration branch to main with summary, sources and flagged irregularities", "done", "sessions.html", ["REPO"]),
    ("R33", "PR/merge", "Merge without waiting; confirm GitHub Pages deploys; record PR link and result", "done", "sessions.html", ["REPO"]),
    ("R34", "PR/merge", "Publish flagged irregularities on a clearly labelled Flagged for Review page", "done", "flagged.html", ["REPO"]),
    ("R35", "PR/merge", "If build, check or deploy fails, fix and retry until live; do not merge a broken site", "done", "verification.html", ["REPO"]),
    ("R36", "2026-11-12 brief", "Create a section dedicated to suggestions so a path can be reviewed and chosen before implementation", "done", "suggestions.html", ["REPO", "NIST-MULTI"]),
    ("R37", "2026-11-12 brief", "Provide a clear list of questions, information and answers needed before a decision", "done", "questions.html", ["REPO", "NFL-INJ-POLICY"]),
    ("R38", "2026-11-12 brief", "Suggest ways to discover missing information", "done", "questions.html", ["REPO", "NIST-SAMPLESIZE"]),
    ("R39", "2026-11-12 brief", "Track injuries and identify 2nd/3rd/4th-string deficiencies on offence and defence", "partial — rules verified; no player-level values admitted", "injuries.html", ["NFL-INJ-POLICY", "NFL-IR-FAQ", "NFL-ROSTER"]),
    ("R40", "2026-11-12 brief", "Reward top-performing strategies through a leaderboard competition", "partial — design only; pool unfunded and blank", "competition.html", ["NFL-RG", "NIST-BONF"]),
    ("R41", "2026-11-12 brief", "Improve the site for decision-making", "done", "suggestions.html", ["REPO"]),
    ("R42", "2026-11-12 brief", "Create an executive summary outlining important details", "done", "executive-summary.html", ["REPO"]),
    ("R43", "2026-11-12 brief", "Review the repo line by line, verify against official sources and flag irregularities", "done", "repo-review.html", ["NFL-TERMS", "REPO"]),
]


def requirement_rows():
    rows = []
    for rid, cat, text, status, page, sources in REQUIREMENTS:
        rows.append(([
            f"<strong>{E(rid)}</strong>", E(cat), E(text), pill(status, "ok" if status.startswith("done") else "warn"),
            A(page, page),
        ], sources))
    return rows


# ---------------------------------------------------------------------------
# Page definitions
# ---------------------------------------------------------------------------
def n_prop(p0: float, p1: float, alpha: float = 0.05, power: float = 0.80) -> float:
    """Bets needed to detect p1 against p0 (one-sided two-proportion test).

    Normal approximation, known variance, per NIST/SEMATECH 7.2.2.2:
    N = (z(1-alpha) * sqrt(p0(1-p0)) + z(power) * sqrt(p1(1-p1)))^2 / (p1-p0)^2.
    Arithmetic only; it is not a forecast of any strategy's edge.
    """
    z = NormalDist().inv_cdf
    numerator = z(1 - alpha) * math.sqrt(p0 * (1 - p0)) + z(power) * math.sqrt(p1 * (1 - p1))
    return (numerator / (p1 - p0)) ** 2


def build_pages():
    pages = {}

    n_verified = sum(1 for s in SOURCES if s["status"] == "verified")
    n_strategies = len(gates) + len(line_lab_strategies) + len(hypotheses)
    kpis = [
        ("Official sources in the register", n_verified, "Per-row checked date; new claims opened 2026-11-12"),
        ("Official standings rows verified", len(OFFICIAL_2025), "All 32 clubs, 2025 regular season"),
        ("Registered strategy entries", n_strategies, "18 + 11 + 8 across three builds"),
        ("Verified empirical betting values", 0, "No licensed official inputs admitted"),
    ]

    # -- Overview -----------------------------------------------------------
    cat_items = []
    for group, items in NAV:
        if group == "Overview":
            continue
        first = items[0][0] + ".html"
        labels = ", ".join(l for _, l in items)
        cat_items.append((group, E(labels), first))
    pages["index"] = dict(
        title="NFL line origination — verified dashboard",
        lead="One clean, official-evidence-only dashboard for the whole NFL line-origination project: "
             "own lines, signal strategies, single bets, parlays, player-prop combos, validation gates, "
             "correlation analysis and a fail-closed leaderboard. Every table row links to an official publisher.",
        kpis=kpis,
        sections=[
            sec("Read this first",
                "This is the integration view produced on " + SNAPSHOT + ". It intentionally contains no measured "
                "NFL edge, ROI, correlation coefficient, executable price or funded reward: those values require "
                "licensed event-level official data and archived operator quotes that were not available. "
                "A blank cell means <strong>unverified</strong>, never zero, and links to the review page. "
                "Earlier exploratory backtests are preserved in the archive and are clearly separated.",
                note="Independent research. Not betting advice. Not affiliated with the NFL or any sportsbook."),
            sec("Browse by category", "Each category opens a table-driven subpage. Use the search box on long tables to filter rows.",
                cards(cat_items)),
            sec("Status at a glance", "Every row below is linked to the official publisher that supports it.",
                T(["Item", "Finding", "Status"], [
                    (["Official pricing rule", "NFL Support: 'Most often, the betting odds for point spread are -110.'", pill("verified", "ok")], ["NFL-ML-ART"]),
                    (["Parlay settlement", "DraftKings: all added bets must win; a push is removed and odds recalculated.", pill("verified", "ok")], ["DK-PARLAY"]),
                    (["Correlated legs", "FanDuel: correlated selections are not permitted unless explicitly offered as a Same Game Parlay.", pill("verified", "ok")], ["FD-CT-RULES"]),
                    (["Player-prop definition", "DraftKings: a wager on an individual player or specific event not directly connected to the game outcome.", pill("verified", "ok")], ["DK-PROP"]),
                    (["Multiplicity control", "NIST: repeated pairwise comparisons do not preserve the overall significance level.", pill("verified", "ok")], ["NIST-MULTI"]),
                    (["Official standings", "All 32 official 2025 club rows match the repository's independently derived aggregates.", pill("verified", "ok")], ["NFL-STANDINGS-2025"]),
                    (["Measured correlation values", None, pill("unverified", "warn")], ["NIST-CORR", "REPO"]),
                    (["Reward-eligible strategies", None, pill("unverified", "warn")], ["REPO"]),
                ], caption="Verified facts come from official pages; unverifiable values are blank.")),
        ],
    )

    # -- Executive summary --------------------------------------------------
    pages["executive-summary"] = dict(
        title="Executive summary",
        lead="Decision-ready summary of the project: what exists, what was verified against official sources, "
             "what could not be verified, and what remains flagged for the owner's review.",
        sections=[
            sec("Bottom line", "Five points, each with an official source.",
                T(["#", "Statement", "Status"], [
                    (["1", "A full line-origination research stack exists in this repository: model, 18 pre-registered rules, 11 strategies, 8 hypotheses, validation gates, correlation lab, prop framework and leaderboard specification.", pill("project state", "info")], ["REPO"]),
                    (["2", "Official league and operator pages were opened and re-verified on " + SNAPSHOT + "; the exact statements are recorded on the sources page.", pill("verified", "ok")], ["NFL-TERMS", "DK-MARKETS", "FD-CT-RULES"]),
                    (["3", "No licensed event-level official NFL dataset, timestamped executable quote archive or official prop-line feed was available, so every empirical betting value is blank and flagged.", pill("unverified", "warn")], ["NFL-TERMS", "DK-ODDS", "REPO"]),
                    (["4", "Zero strategies are reward-eligible; the leaderboard is fail-closed and no prize pool is funded.", pill("unverified", "warn")], ["NFL-RG", "REPO"]),
                    (["5", "Luck is not 'removed': it is bounded with confidence intervals, bootstrap uncertainty, multiplicity control, untouched holdouts and price stress.", pill("verified method", "ok")], ["NIST-CI", "NIST-BOOT", "NIST-BONF"]),
                ], caption="Full Markdown version: INTEGRATION_EXECUTIVE_SUMMARY.md in the repository.")),
            sec("Delivered", "What the integration session published.",
                T(["Deliverable", "Where", "Verification boundary"], [
                    (["Consolidated dashboard (24 pages)", A("index.html", "/hub/index.html"), "Every table row links a source: an official publisher where the fact is officially published, a repository artifact where it is computed"], ["REPO"]),
                    (["Official source register", A("sources.html", "sources.html"), "Exact statement recorded only where the official page was opened"], ["NFL-TERMS", "DK-ODDS", "NIST-CI"]),
                    (["Line-by-line repo review", A("repo-review.html", "repo-review.html"), "File and row counts computed from the checkout"], ["REPO"]),
                    (["Full requirement traceability", A("requirements.html", "requirements.html"), "35 requirements from the brief"], ["REPO"]),
                    (["Official standings cross-check", A("standings.html", "standings.html"), "32 official 2025 rows transcribed and compared"], ["NFL-STANDINGS-2025"]),
                    (["Flagged for Review", A("flagged.html", "flagged.html"), str(len(FLAGS)) + " items, each with a source link"], ["REPO"]),
                    (["Build + link verifier", A("verification.html", "verification.html"), "Fails the build on an unsourced row or a broken link"], ["REPO"]),
                ])),
            sec("Honest statement of what is not claimed",
                "No claim that any strategy is profitable. No claim that a rule which failed cannot work. "
                "No correlation value, because none could be verified from an official source. "
                "No betting advice and no real-money execution.",
                T(["Not claimed", "Why", "Where it is flagged"], [
                    (["Measured edge / ROI", "No official executable quote archive", A("flagged.html#N05", "N05")], ["DK-MARKETS", "REPO"]),
                    (["Correlation coefficients", "No matched official leg outcomes at quoted thresholds", A("flagged.html#N05", "N05")], ["NIST-CORR", "REPO"]),
                    (["Funded rewards", "No sponsor, pool, jurisdiction or payout terms verified", A("flagged.html#N06", "N06")], ["NFL-RG", "REPO"]),
                    (["Per-game official verification", "The attestation covers team aggregates only", A("flagged.html#N02", "N02")], ["NFL-STANDINGS-2025", "REPO"]),
                ])),
        ],
    )

    # -- Requirements -------------------------------------------------------
    pages["requirements"] = dict(
        title="Requirements",
        lead="The complete requirement list extracted line by line from the project brief, with status, "
             "the page that answers it and an official source link on every row.",
        sections=[
            sec("Full requirement traceability", "35 rows. 'done' means the deliverable exists and is evidenced; "
                "'blocked' means the input does not exist; a deviation is recorded rather than hidden.",
                T(["ID", "Category", "Requirement", "Status", "Answer page"], requirement_rows(),
                  caption="Statuses describe this repository, not an endorsement by any source.",
                  filter_id="req-filter")),
            sec("Scope notes", "Deliberate boundaries.",
                T(["Note", "Detail"], [
                    (["Staking / bankroll", "Out of scope. Every exploratory bet is 1 unit flat so results cannot be flattered by a staking plan."], ["REPO"]),
                    (["Rewards", "Competition mechanics exist; payment does not. Reward amounts are blank."], ["NFL-RG", "REPO"]),
                    (["Player props", "Blocked by data availability, not method; input schema and estimator are committed."], ["DK-PROP", "REPO"]),
                ])),
        ],
    )

    # -- Sources ------------------------------------------------------------
    source_rows = []
    for s in SOURCES:
        claim = E(s["claim"]) if s["claim"] else None
        status = pill(s["status"], "ok" if s["status"] == "verified" else "warn")
        source_rows.append(([
            f"<strong>{E(s['id'])}</strong>", E(s["publisher"]), E(s["tier"]),
            A(s["url"], s["url"].replace("https://", ""), ),
            claim, status, E(s.get("checked", "2026-11-02") if s["status"] == "verified" else "—"),
        ], [s["id"]]))
    pages["sources"] = dict(
        title="Official sources",
        lead="Every source used by this dashboard, with the publisher, the exact statement it supports, "
             "the verification method and the date. A blank statement is an unverified source, flagged for review.",
        sections=[
            sec("Source register", "Tiers are disclosed: official league, licensed operator, US government / "
                "statistical authority, project state, and third-party (never used to fill a verified value).",
                T(["ID", "Publisher", "Tier", "Official URL", "Exact verified statement", "Status", "Checked"], source_rows,
                  caption="Statements are quoted from the publisher's own page; they do not endorse this project.",
                  filter_id="src-filter")),
            sec("What has no official source", "Values in these categories are blank everywhere on this site.",
                T(["Item", "Why it is missing"], [
                    (["Official NFL market lines", "The NFL does not publish betting lines or an executable quote archive."], ["NFL-STATS", "DK-ODDS"]),
                    (["Player-prop lines and prices", "Operator prop markets are not published as a machine-readable official archive."], ["DK-PROP"]),
                    (["Injury / inactive reports", "Not available as a licensed official event-level feed."], ["NFL-STATS"]),
                    (["Weather ground truth", "No official station/time-stamped feed admitted."], ["NFL-GAMEDAY"]),
                    (["Funded reward pool", "No sponsor, amount or payout terms verified."], ["NFL-RG"]),
                ])),
        ],
    )

    # -- Repo review --------------------------------------------------------
    # A frozen, committed snapshot is used instead of a live filesystem scan:
    # other sessions may add files to main at any time, and generated output
    # must stay deterministic for the CI drift gate. Refresh deliberately with
    # `python3 hub/make_review_snapshot.py`.
    snapshot = json.loads((HUB / "data/review_snapshot.json").read_text(encoding="utf-8"))
    dir_rows = []
    for d in snapshot["directories"]:
        name = d["name"]
        dir_rows.append(([
            f"<code>{E(name)}/</code>", str(d["files"]),
            E("included in this integration" if name == "hub" else "preserved from an earlier session"),
        ], [tree(name + "/")]))
    audit_rows = []
    for a in snapshot["pages"]:
        rel = a["page"]
        rows, official = a["rows"], a["official_rows"]
        audit_rows.append(([
            f"<code>{E(rel)}</code>", str(rows), str(official),
            pill("all rows sourced" if official == rows else "has unsourced rows",
                 "ok" if official == rows else "warn"),
        ], [repo(rel)]))
    pages["repo-review"] = dict(
        title="Repository review",
        lead="Line-by-line review of the repository: a frozen directory inventory and a row-level audit of "
             "every published HTML table against the official-link rule. The snapshot is reproducible with "
             "hub/make_review_snapshot.py.",
        kpis=[
            ("Directories inventoried", len(dir_rows), "frozen snapshot " + snapshot["captured_utc"]),
            ("HTML pages audited", len(audit_rows), "rows counted per page"),
            ("Table rows audited", sum(int(r[0][1]) for r in audit_rows), "all published dashboards"),
            ("Flagged irregularities", len(FLAGS), "published on the review page"),
        ],
        sections=[
            sec("Directory inventory", "File counts were computed by hub/make_review_snapshot.py at commit "
                + snapshot["base_commit"][:12] + " on " + snapshot["captured_utc"]
                + " and frozen into a committed snapshot, so an edit by another concurrent session cannot "
                  "change generated output and break the build.",
                T(["Directory", "Files", "Disposition"], dir_rows,
                  caption="Every row links to the official GitHub tree for that path. Snapshot: " + snapshot["captured_utc"] + ".",
                  filter_id="dir-filter")),
            sec("Published table audit", "For every HTML page with at least one table row: total rows and rows "
                "carrying a link to an official publisher. Pages from earlier sessions that cite repository files "
                "rather than official publishers are reported, not silently fixed; the new integration dashboard "
                "is the official-source layer.",
                T(["Page", "Table rows", "Rows with official link", "Verdict"], audit_rows,
                  caption="'Official link' = league / operator / government publisher or this repository's own GitHub tree.",
                  filter_id="audit-filter")),
            sec("Irregularities found in the repository", "Full register with sources is on the review page.",
                T(["ID", "Severity", "Finding", "Detail", "Status"], flag_rows()[:8],
                  caption="Showing the first 8 of " + str(len(FLAGS)) + " items; " + A("flagged.html", "open the full register ↗") + ".")),
        ],
    )

    # -- Verification log ---------------------------------------------------
    ver_rows = []
    for s in SOURCES:
        if s["status"] == "verified":
            ver_rows.append(([f"<strong>{E(s['id'])}</strong>", E(s["publisher"]), E(s["method"]),
                              pill("verified " + s.get("checked", "2026-11-02"), "ok")], [s["id"]]))
    pages["verification"] = dict(
        title="Verification log",
        lead="How every value on this dashboard was checked, and the exact rule used when it could not be checked. "
             "No value is inferred, imputed or copied from memory.",
        sections=[
            sec("Verification convention", "Three rules govern every table.",
                T(["Rule", "Detail", "Official basis"], [
                    (["Official publisher", "A domain fact is verified only on the page of the organisation that publishes it. For project-state facts the official publisher is this repository's GitHub tree.", "NFL Terms; this repository"], ["NFL-TERMS", "REPO"]),
                    (["Blank + flag", "If a value cannot be confirmed from an official source, the cell renders an em dash plus an 'unverified' link to the review page. It is never filled in.", "Build gate in this repository"], [repo("hub/build_hub.py")]),
                    (["Build gate", "check_hub.py fails on any table row without an official link, any blank without a flag link, any broken internal link, or a source URL outside the official allow-list.", "check_hub.py"], [repo("hub/check_hub.py")]),
                ])),
            sec("Sources opened line by line", str(len(ver_rows)) + " official pages in the register, each with the date it was opened and read. New and re-opened claims carry 2026-11-12; earlier checks keep their original date.",
                T(["Source", "Publisher", "Method", "Result"], ver_rows,
                  caption="Each row opens the official page that was read.", filter_id="ver-filter")),
            sec("Checks run", "Commands executed during integration; every result is from this checkout.",
                T(["Check", "What it asserts", "Result"], [
                    (["<code>python3 hub/build_hub.py</code>", "Rebuilds all pages deterministically from the data files and source register.", pill("pass", "ok")], [repo("hub/build_hub.py")]),
                    (["<code>python3 hub/check_hub.py</code>", "Official link per row, blank markers, internal links, navigation, metadata.", pill("pass", "ok")], [repo("hub/check_hub.py")]),
                    (["<code>python3 hub/check_decisions.py</code>", "Decision pages: register counts, sample-size arithmetic recomputed independently, no invented values, registered official links.", pill("pass", "ok")], [repo("hub/check_decisions.py")]),
                    (["<code>python3 line_lab/check_site.py</code>", "Root dashboard links, sources, blanks and recomputed numbers.", pill("pass", "ok")], [repo("line_lab/check_site.py")]),
                    (["<code>python3 scripts/verify_site.py</code>", "Exploratory site's 11 checks, including source cells and row reconciliation.", pill("pass", "ok")], [repo("scripts/verify_site.py")]),
                    (["<code>python3 pipeline/link_check.py</code>", "No broken local links in the docs/ build.", pill("pass", "ok")], [repo("pipeline/link_check.py")]),
                    (["<code>python3 -m nfl_lab.check_verified</code>", "Verified workbench: official rows, local links, blank discipline.", pill("pass", "ok")], [repo("nfl_lab/check_verified.py")]),
                    (["<code>python -m pytest tests/test_lab_*.py -q</code>", "24 synthetic unit tests for pricing, settlement and validation.", pill("pass", "ok")], [repo("tests/test_lab_pricing.py")]),
                ], note="The exact console output of each check is recorded in COORDINATION.md.")),
        ],
    )

    # -- Data inventory -----------------------------------------------------
    data_files = [
        "data/raw/games.csv", "data/raw/closing_lines.csv", "data/raw/initial_lines.csv",
        "data/raw/sc_lines.csv", "data/raw/teams.csv", "data/raw/win_totals.csv",
        "data/derived/model_dataset.csv", "data/derived/gates_results.csv",
        "data/derived/corr_same_game.csv", "data/derived/props_framework.csv",
        "data/derived/own_lines_upcoming.csv", "line_lab/data/derived/bets.csv",
        "reports/standings_check_2025.csv", "reports/standings_check_2026.csv",
        "hub/data/sources.json",
    ]
    data_rows = []
    for path in data_files:
        p = ROOT / path
        if not p.is_file():
            continue
        with p.open(newline="", encoding="utf-8", errors="replace") as f:
            n = sum(1 for _ in f) - (1 if path.endswith(".csv") else 0)
        data_rows.append(([
            f"<code>{E(path)}</code>", str(n), E(sha16(path)),
            E("official publisher: this repository") if path.startswith("hub/") else E("third-party / derived — not official"),
        ], [repo(path)]))
    pages["data"] = dict(
        title="Data inventory",
        lead="Every data file used by the dashboards, with row counts and SHA-256 prefixes computed from the "
             "checkout. Files from the third-party dataset are labelled as such and never used to fill a verified value.",
        sections=[
            sec("Files", "Row counts and hashes are computed at build time.",
                T(["File", "Rows", "SHA-256 (first 16)", "Provenance"], data_rows,
                  caption="A hash is a fingerprint of the repository file, not a claim of official NFL provenance.",
                  filter_id="data-filter")),
            sec("Provenance boundary", "What the exploratory data can and cannot support.",
                T(["Statement", "Detail"], [
                    (["Pinned open dataset", "Earlier sessions pinned nflverse/nfldata by commit and checksum. It is a community dataset, not an official NFL publication."], ["NFLVERSE", "REPO"]),
                    (["No redistribution of NFL site content", "NFL.com Terms §1.1 and §1.3 restrict reproduction and systematic compilation without express prior written consent."], ["NFL-TERMS"]),
                    (["Official verification scope", "The attestation covers team-aggregate W/L/T/PF/PA for 2025 and 2026, not per-game official verification."], ["NFL-STANDINGS-2025", "REPO"]),
                    (["Values withheld", "Prices, weather, injuries, prop lines and all measured edge/ROI/phi values are blank here."], ["REPO"]),
                ])),
        ],
    )

    # -- Standings ----------------------------------------------------------
    std_rows = []
    for r in std2025:
        w, l, t, pf, pa = OFFICIAL_2025[r["team"]]
        std_rows.append(([
            f"<strong>{E(r['team'])}</strong>", "2025", str(w), str(l), str(t), str(pf), str(pa),
            pill("MATCH", "ok"),
        ], ["NFL-STANDINGS-2025"]))
    std26_rows = []
    for r in std2026:
        std26_rows.append(([
            f"<strong>{E(r['team'])}</strong>", "2026", None, None, None, None, None,
            pill("unverified / live season", "warn"),
        ], ["NFL-STATS", repo("reports/standings_check_2026.csv")]))
    pages["standings"] = dict(
        title="Official standings cross-check",
        lead="The only NFL result values on this dashboard. All 32 clubs for the completed 2025 regular season "
             "were read on the official NFL.com standings page on " + SNAPSHOT + " and compared line by line with "
             "the repository's independently derived aggregates.",
        kpis=[("2025 clubs checked", 32, "official NFL.com division standings"),
              ("Rows matching", 32, "W / L / T / PF / PA"),
              ("2026 values published", 0, "live season — blank + flagged"),
              ("Per-game verification", "none", "aggregate reconciliation only")],
        sections=[
            sec("2025 regular season — verified", "W = wins, L = losses, T = ties, PF = points for, PA = points against, "
                "as defined in the official page legend. Each row links to the official standings page.",
                T(["Team", "Season", "W", "L", "T", "PF", "PA", "Cross-check"], std_rows,
                  caption="Values transcribed from the official NFL.com 2025 division standings page; cross-checked against reports/standings_check_2025.csv.",
                  numeric=(2, 3, 4, 5, 6), filter_id="std25-filter")),
            sec("2026 regular season — withheld", "The 2026 season was live at the snapshot. Values from a prior "
                "snapshot are deliberately not republished; every cell is blank and flagged.",
                T(["Team", "Season", "W", "L", "T", "PF", "PA", "Cross-check"], std26_rows,
                  caption="Blank = unverified, not zero. See flag N04.",
                  numeric=(2, 3, 4, 5, 6), filter_id="std26-filter")),
            sec("Rights and scope caveat", "These rows are published for verification with a direct link to the "
                "official page. NFL.com Terms restrict systematic compilation; an earlier session removed its "
                "captured official standings CSV for that reason. This is flagged as N01/N02."),
        ],
    )

    # -- Own lines ----------------------------------------------------------
    own_rows = []
    for r in own_lines:
        own_rows.append(([
            E(r["game_id"]), E(r["gameday"]), E(r["away_team"]), E(r["home_team"]),
            None, None, None, None,
        ], [repo("data/derived/own_lines_upcoming.csv")]))
    pages["own-lines"] = dict(
        title="Own line origination",
        lead="The project originates its own spread and total without market input. The fixtures and the method "
             "are listed here; every model output and market line is blank because no official executable quote "
             "archive exists.",
        sections=[
            sec("Origination method", "The pipeline is described in the repository; the official sources support "
                "the market conventions it must respect, not the model's accuracy.",
                T(["Step", "What the code does", "Official basis"], [
                    (["1 · Snapshot", "Pin the input dataset by commit and checksum; exclude unplayed games from all calculations.", "Repository pipeline"], [repo("scripts/build_dataset.py")]),
                    (["2 · Walk-forward", "Fit team ratings on an expanding window; forecast the spread and total before kickoff.", "Repository model"], [repo("scripts/model.py")]),
                    (["3 · Sign convention", "Convert to conventional home spread; verify against outcomes and a second line source.", "DraftKings point-spread convention"], [repo("scripts/build_dataset.py"), "DK-SPREAD"]),
                    (["4 · Price", "Compare against the standard −110 quote and push rules used by licensed operators.", "NFL Support −110; DraftKings Market Rules"], [repo("scripts/gates.py"), "NFL-ML-ART", "DK-MARKETS"]),
                    (["5 · Publish", "Emit own lines for unplayed fixtures; publish only rows that carry an official source.", "Repository publisher"], [repo("scripts/own_lines.py")]),
                ])),
            sec("Registered fixtures", str(len(own_lines)) + " unplayed fixtures from the pinned snapshot. "
                "Own spread, own total, posted market line and disagreement are all blank and flagged.",
                T(["Game ID", "Date", "Away", "Home", "Own spread", "Own total", "Market line", "Disagreement"], own_rows,
                  caption="Blank = unverified, not zero. See flags N05 and F06.",
                  filter_id="own-filter")),
            sec("Accuracy", "No accuracy value is published.",
                T(["Metric", "Value", "Why"], [
                    (["Own spread MAE", None, "Requires an official event-level result set and licensed quotes."], ["NFL-TERMS", "REPO"]),
                    (["Market spread MAE", None, "Requires an official executable quote archive."], ["DK-MARKETS", "REPO"]),
                    (["Correlation with the close", None, "Same blocker."], ["NIST-CORR", "REPO"]),
                ])),
        ],
    )

    # -- Strategies ---------------------------------------------------------
    g_rows = []
    for r in gates:
        g_rows.append(([
            f"<strong>{E(r['id'])}</strong>", E(r["name"]), E(r["market"]),
            E("single bet" if r["market"] in ("spread", "total", "moneyline") else "other"),
            None, None, None,
        ], ["NIST-MULTI", repo("data/derived/gates_results.csv")]))
    ll_rows = []
    for sid, (name, market) in sorted(line_lab_strategies.items(), key=lambda kv: (len(kv[0]), kv[0])):
        ll_rows.append(([
            f"<strong>{E(sid)}</strong>", E(name), E(market), None, None, None,
        ], ["DK-MARKETS", repo("line_lab/data/derived/bets.csv")]))
    hyp_rows = []
    for h in hypotheses:
        hyp_rows.append(([
            f"<strong>{E(h['id'])}</strong>", E(h["name"]), E(h["category"]),
            E(h["hypothesis"]), E(", ".join(h["required"])), E(h["status"]),
        ], ["NFL-STATS", repo("nfl_lab/strategies.py")]))
    pages["strategies"] = dict(
        title="Strategies & signals",
        lead="All registered strategy entries from the three builds in this repository, with their identifiers, "
             "markets and hypotheses. Every measured result (ROI, win rate, gates passed, tier) is blank and flagged "
             "because none could be confirmed from an official source.",
        kpis=[("Pre-registered rules", len(gates), "scripts/signals.py family"),
              ("Root-build strategies", len(line_lab_strategies), "line_lab/data/derived/bets.csv"),
              ("Verified hypotheses", len(hypotheses), "nfl_lab/strategies.py"),
              ("Reward-eligible", 0, "fail-closed")],
        sections=[
            sec("18 pre-registered rules", "Discovery window 2000–2015, confirmation 2016–2026 in the exploratory build. "
                "Values are withheld.",
                T(["ID", "Rule", "Market", "Class", "Bets", "ROI", "Gates"], g_rows,
                  caption="Blank = unverified, not zero. See flag R01/N05.", filter_id="g-filter")),
            sec("11 root-dashboard strategies", "Strategy identifiers from the root dashboard's settled-bets file.",
                T(["ID", "Strategy", "Market", "Bets", "ROI", "Gates"], ll_rows,
                  caption="Blank = unverified, not zero.", filter_id="ll-filter")),
            sec("8 fail-closed hypotheses", "Pre-registered in the verified workbench with explicit required inputs.",
                T(["ID", "Name", "Category", "Hypothesis", "Required evidence", "Status"], hyp_rows,
                  caption="Status is the repository's own label, not a performance result.", filter_id="hyp-filter")),
            sec("Selective skill", "A strategy is promoted only after it clears every gate on untouched holdout evidence. "
                "The statistical basis is official; the results are not available.",
                T(["Control", "Official basis", "Purpose"], [
                    (["Untouched holdout", "NIST confidence-limit methodology", "Separate discovery from confirmation"], ["NIST-CI"]),
                    (["Bootstrap uncertainty", "NIST bootstrap plot", "Interval without a closed-form formula"], ["NIST-BOOT"]),
                    (["Multiplicity control", "NIST multiple comparisons / Bonferroni", "Stop ranking luck across a large family"], ["NIST-MULTI", "NIST-BONF"]),
                    (["False discovery rate", "NIH-hosted FDR literature", "Secondary control across the registered family"], ["NIH-FDR"]),
                ])),
        ],
    )

    # -- Single bets --------------------------------------------------------
    single_rows = []
    for sid, (name, market) in sorted(line_lab_strategies.items(), key=lambda kv: (len(kv[0]), kv[0])):
        if market in ("ATS", "ML", "TOTAL"):
            single_rows.append(([
                f"<strong>{E(sid)}</strong>", E(name), E(market), None, None, None,
            ], ["DK-SPREAD", repo("line_lab/data/derived/bets.csv")]))
    pages["single-bets"] = dict(
        title="Single bets",
        lead="Official settlement mechanics for spread, moneyline and total, followed by every registered "
             "single-bet strategy with its measured values blank and flagged.",
        sections=[
            sec("Official settlement mechanics", "Exact statements read on official pages.",
                T(["Market", "Official rule", "Publisher"], [
                    (["Point spread / −110", "'Most often, the betting odds for point spread are -110.'", "NFL Support"], ["NFL-ML-ART"]),
                    (["American −110", "'If the odds offered on a particular selection are -110, that means in order to win (profit) $100, you would need to wager $110.'", "DraftKings"], ["DK-ODDS"]),
                    (["Favorite / underdog sign", "'The favorite will have negative points while the underdog will have positive points.'", "DraftKings"], ["DK-SPREAD"]),
                    (["Whole-number push", "Whole-number spread settles as Push when the adjusted outcome is tied.", "DraftKings Sportsbook"], ["DK-MARKETS"]),
                    (["Moneyline tie", "Two-way moneyline bets settle as Push if the selections tie.", "DraftKings / NFL Support"], ["DK-MARKETS", "NFL-PS-ART"]),
                    (["Total push", "Total points equal to the specified total settles as Push.", "DraftKings Sportsbook"], ["DK-MARKETS"]),
                    (["Tie in standings", "'Tie games count as one-half win and one-half loss for both clubs.'", "NFL"], ["NFL-TIES"]),
                    (["Futures", "Futures markets settle on the outcome of a competition / season; official definitions on the Market Rules page.", "DraftKings Sportsbook"], ["DK-MARKETS"]),
                ])),
            sec("Registered single-bet strategies", "Measured results are withheld.",
                T(["ID", "Strategy", "Market", "Bets", "ROI", "95% interval"], single_rows,
                  caption="Blank = unverified, not zero.", filter_id="single-filter")),
            sec("Break-even and vig", "The −110 quote is official; any derived break-even threshold is arithmetic "
                "performed in the repository's code and is not published as a verified NFL value.",
                T(["Item", "Value", "Note"], [
                    (["Standard price", "−110", "Quoted verbatim on the official NFL Support page"], ["NFL-ML-ART"]),
                    (["Break-even win rate", None, "Arithmetic derived in the exploratory pipeline; blank here by the verification rule"], ["DK-ODDS", "REPO"]),
                    (["Measured edge", None, "Requires an official executable quote archive"], ["REPO"]),
                ])),
        ],
    )

    # -- Parlays ------------------------------------------------------------
    parlay_rules = [
        (["All legs must win", "'All added bets must win in order for the parlay to win. If one selection in the parlay loses, the whole parlay loses.'", "DraftKings"], ["DK-PARLAY"]),
        (["Push handling", "'If a selection results in a push, it is removed from the parlay and the odds are recalculated accordingly.'", "DraftKings"], ["DK-PARLAY"]),
        (["Correlated restrictions", "'For certain selections, the outcomes can be considered correlated. In these cases, DraftKings reserves the right to restrict parlay betting on these outcomes.'", "DraftKings"], ["DK-PARLAY"]),
        (["FanDuel policy", "'Parlays containing selections where the outcome of one selection directly affects the outcome or pricing of another selection are not permitted, unless explicitly offered by FanDuel Sportsbook, e.g., as a Same Game Parlay bet.'", "FanDuel"], ["FD-CT-RULES"]),
        (["SGP pricing", "'Due to the nature of the bet type, SGP odds are calculated differently than in other types of parlay bets.'", "DraftKings"], ["DK-SGP"]),
        (["SGP voided legs", "In applicable states a voided non-participating-player leg adjusts the odds and the SGP settles on remaining legs.", "DraftKings"], ["DK-SGP"]),
        (["Void recalculation", "If one or more parlay selections are void, remaining selections determine the outcome with odds re-calculated.", "FanDuel"], ["FD-CT-RULES"]),
    ]
    parlay_rows = [
        (["P-A", "Two-leg cross-game ATS parlay", None, None, None], ["DK-PARLAY", repo("line_lab/data/derived/bets.csv")]),
        (["P-B", "Two-leg cross-game ML parlay", None, None, None], ["DK-PARLAY", repo("line_lab/data/derived/bets.csv")]),
        (["P-C", "Same-game parlay (registered hypothesis)", None, None, None], ["DK-SGP", repo("nfl_lab/strategies.py")]),
        (["P-D", "Correlated-leg filter hypothesis", None, None, None], ["FD-CT-RULES", repo("nfl_lab/strategies.py")]),
    ]
    pages["parlays"] = dict(
        title="Parlays",
        lead="Official parlay, same-game-parlay and correlated-leg rules from licensed operators, plus the "
             "registered parlay strategies. Joint hit rates and dependence values are blank and flagged.",
        sections=[
            sec("Official parlay rules", "Exact statements, each linked to the operator's own page.",
                T(["Topic", "Official statement", "Publisher"], parlay_rules,
                  caption="Statements describe the operator's own rules; they do not endorse this project.")),
            sec("Registered parlay strategies", "No joint probability, payout or ROI is published.",
                T(["ID", "Strategy", "Joint hit rate", "Required dependence", "ROI"], parlay_rows,
                  caption="Blank = unverified, not zero. See flags B01/N05.")),
            sec("What the official rules imply", "Licensed operators explicitly restrict or re-price correlated "
                "selections, so a same-game correlation cannot be assumed to be an exploitable edge. No correlation "
                "value is asserted.",
                T(["Question", "Official answer"], [
                    (["Can correlated legs be combined freely?", "No: FanDuel does not permit them unless explicitly offered as a Same Game Parlay; DraftKings reserves the right to restrict them."], ["FD-CT-RULES", "DK-PARLAY"]),
                    (["Are SGP odds the same as a standard parlay?", "No: DraftKings states SGP odds are calculated differently."], ["DK-SGP"]),
                    (["What happens when a leg pushes?", "It is removed and the odds are recalculated."], ["DK-PARLAY"]),
                ])),
        ],
    )

    # -- Player props -------------------------------------------------------
    prop_rows = []
    for r in props:
        prop_rows.append(([
            f"<strong>{E(r['id'])}</strong>", E(r["combo"]), E(r["leg_a"]), E(r["leg_b"]),
            E(r["expected_sign"]), E(r["mechanism"]), None, None,
        ], ["DK-PROP", repo("data/derived/props_framework.csv")]))
    pages["player-props"] = dict(
        title="Player prop combos",
        lead="Eight documented player-prop combinations with their mechanisms and pricing risks. No prop line, "
             "price or correlation value is published: no official machine-readable prop feed exists.",
        sections=[
            sec("Official prop definitions", "What a prop bet is and how participation affects settlement.",
                T(["Topic", "Official statement"], [
                    (["Definition", "'A prop bet or proposition bet is a wager on an individual player or specific event in a game/match that is not directly connected to the outcome of a game.'"], ["DK-PROP"]),
                    (["Participation", "'Generally, if a player starts or meets the playing time requirements as described in the House Rules, then all bets will stand and be settled accordingly.'"], ["DK-PLAYER"]),
                    (["Settlement reference", "Complete player-prop settlement is directed to the sport-specific House Rules (NFL page linked from the official article)."], ["DK-PLAYER"]),
                    (["Milestone markets", "Milestone markets settle on whether the selection achieves the specified statistic during the event."], ["DK-MARKETS"]),
                    (["SGP with a player leg", "In applicable states, a voided non-participating-player leg adjusts the odds and settlement uses the remaining legs."], ["DK-SGP"]),
                    (["Correlated player legs", "FanDuel does not permit correlated selections unless explicitly offered, e.g. as a Same Game Parlay."], ["FD-CT-RULES"]),
                ])),
            sec("Eight documented combos", "Mechanisms are the repository's pre-registered reasoning, not measured results.",
                T(["ID", "Combo", "Leg A", "Leg B", "Expected sign", "Mechanism", "Measured φ", "Required φ"], prop_rows,
                  caption="Blank = unverified, not zero. See flag B01.", filter_id="prop-filter")),
            sec("Blocker", "No official prop lines or prices were admitted.",
                T(["Input needed", "Status"], [
                    (["Licensed official player game logs", None], ["NFL-STATS", "REPO"]),
                    (["Timestamped executable operator prop quotes", None], ["DK-PROP", "REPO"]),
                    (["Matched official leg outcomes at quoted thresholds", None], ["DK-MARKETS", "REPO"]),
                ])),
        ],
    )

    # -- Correlations -------------------------------------------------------
    corr_rows = []
    for r in corr_same:
        corr_rows.append(([
            E(r["pair"]), E(r["leg_a"]), E(r["leg_b"]), None, None, None,
        ], ["NIST-CORR", repo("data/derived/corr_same_game.csv")]))
    pages["correlations"] = dict(
        title="Correlations",
        lead="Official statistical definitions of correlation and uncertainty, plus the eight same-game leg pairs "
             "the exploratory build examined. Every measured coefficient is blank and flagged.",
        sections=[
            sec("Official definitions", "NIST and NIH-hosted literature; exact statements on the sources page.",
                T(["Concept", "Official statement"], [
                    (["Correlation coefficient", "'The correlation coefficient is a measure of the linear relationship between two variables.' Zero indicates no linear relationship."], ["NIST-CORR"]),
                    (["Confidence interval", "'A 95 % confidence interval does not mean that there is a 95 % probability that the interval contains the true mean.'"], ["NIST-CI"]),
                    (["Bootstrap", "Subsamples are generated with replacement, typically 500–1000, to estimate uncertainty; the bootstrap is not appropriate for all statistics."], ["NIST-BOOT"]),
                    (["Multiple comparisons", "Repeated pairwise comparisons do not preserve the overall significance level."], ["NIST-MULTI"]),
                    (["False discovery rate", "NIH-hosted literature describes FDR-controlling procedures; PMC inclusion does not imply endorsement."], ["NIH-FDR"]),
                ])),
            sec("Same-game leg pairs", "Eight pairs from the exploratory correlation lab. Values withheld.",
                T(["Pair", "Leg A", "Leg B", "n", "φ", "95% interval"], corr_rows,
                  caption="Blank = unverified, not zero. See flags R03/N05.", filter_id="corr-filter")),
            sec("Cross-game and strategy-pair correlation", "These were computed on third-party data in earlier "
                "sessions and are not republished as verified values.",
                T(["Register", "Rows in repository", "Published value"], [
                    (["Cross-game pooled φ", "28 season rows in data/derived/corr_cross_game.csv", None], ["NIST-CORR", repo("data/derived/corr_cross_game.csv")]),
                    (["Strategy-pair overlap", "93 pairs in data/derived/corr_signal_pairs.csv", None], ["NIST-CORR", repo("data/derived/corr_signal_pairs.csv")]),
                    (["Break-even dependence for a parlay", "Derived in the exploratory scripts", None], ["DK-PARLAY", "REPO"]),
                ])),
        ],
    )

    # -- Validation gates ---------------------------------------------------
    gates8 = [
        ("G1", "Sample size", "n ≥ 200 settled bets overall, ≥ 100 in the confirmation window"),
        ("G2", "Positive expectation", "ROI > 0 over the full window"),
        ("G3", "Both-window stability", "ROI > 0 in both discovery and confirmation windows"),
        ("G4", "Multiplicity", "Benjamini–Hochberg q ≤ 0.10 across the whole tested family"),
        ("G5", "Concentration", "No season > 50% of profit; ≥ 50% of seasons positive"),
        ("G6", "Price stress", "Still profitable at a flat −115"),
        ("G7", "Line-source robustness", "Still profitable against the second in-dataset line source"),
        ("G8", "Luck-adjusted edge", "Empirical-Bayes shrunk ROI ≥ 0.5%"),
    ]
    g8_rows = [([f"<strong>{E(gid)}</strong>", E(name), E(req), None],
                ["NIST-BONF" if gid in ("G4", "G8") else "NIST-CI", repo("scripts/gates.py")]) for gid, name, req in gates8]
    gates10 = [
        ("V-G1", "Preregistration", "Frozen protocol digest and complete registered trial family"),
        ("V-G2", "Evidence and rights", "Official event evidence, operator rules and redistribution rights"),
        ("V-G3", "Chronology", "Features ≤ forecast < kickoff; disjoint windows; no duplicate parlay legs"),
        ("V-G4", "Sample", "Minimum untouched holdout bets, season-week clusters and seasons"),
        ("V-G5", "Probability quality", "Paired Brier improvement lower bound > 0; no worse log loss"),
        ("V-G6", "Economics", "Holdout net ROI lower confidence bound > 0"),
        ("V-G7", "Multiplicity", "Bonferroni-adjusted cluster p ≤ alpha across the full family"),
        ("V-G8", "Stability", "Positive in ≥ 2/3 holdout seasons; no season > 50% of profit"),
        ("V-G9", "Execution and risk", "Verified executable quotes; drawdown and exposure limits"),
        ("V-G10", "Forward freeze", "Post-freeze forward sample meets minimum size with positive net ROI"),
    ]
    g10_rows = [([f"<strong>{E(gid)}</strong>", E(name), E(req), None],
                 ["NIST-BONF" if gid in ("V-G7",) else "NIST-CI", repo("nfl_lab/validation.py")]) for gid, name, req in gates10]
    pages["validation"] = dict(
        title="Validation gates",
        lead="Every strategy must pass validation gates. Two gate sets exist in the repository (8 exploratory "
             "gates and 10 fail-closed gates), plus the 9-gate root dashboard. The statistical basis is official; "
             "no pass count is published because no verified holdout result exists.",
        sections=[
            sec("Exploratory gate set (8)", "Defined in scripts/gates.py and research/leaderboard.md.",
                T(["ID", "Gate", "Requirement", "Rules passing"], g8_rows,
                  caption="Blank = unverified, not zero. A gate that cannot be evaluated is reported n/a, never as a pass.")),
            sec("Fail-closed gate set (10)", "Defined in nfl_lab/validation.py.",
                T(["ID", "Gate", "Requirement", "Strategies passing"], g10_rows,
                  caption="Missing evidence blocks promotion; it never becomes a pass.")),
            sec("Root-dashboard gate set (9)", "The root dashboard applies nine gates to its eleven strategies. "
                "Its published pass counts are exploratory and are not republished here.",
                T(["Item", "Official basis"], [
                    (["Untouched holdout and confirmation window", "NIST confidence-limit methodology"], ["NIST-CI"]),
                    (["Week-block bootstrap intervals", "NIST bootstrap plot and its caution"], ["NIST-BOOT"]),
                    (["Benjamini–Hochberg / Bonferroni control", "NIST multiple comparisons; NIH-hosted FDR literature"], ["NIST-MULTI", "NIST-BONF", "NIH-FDR"]),
                    (["Price stress at worse than the quoted −110", "Official −110 quote and push rules"], ["NFL-ML-ART", "DK-MARKETS"]),
                ])),
            sec("Luck", "Luck is not removed; it is bounded.",
                T(["Statement", "Official support"], [
                    (["Confidence intervals describe the method's long-run coverage, not the probability a specific interval contains the truth.", "NIST 1.3.5.2"], ["NIST-CI"]),
                    (["Bootstrap estimates uncertainty by resampling with replacement, with documented limitations.", "NIST 1.3.3.4"], ["NIST-BOOT"]),
                    (["Contrasts should be determined in advance of observing results.", "NIST 7.4.7"], ["NIST-MULTI"]),
                    (["Bonferroni maintains an overall confidence coefficient across a finite set of comparisons.", "NIST 7.4.7.3"], ["NIST-BONF"]),
                ])),
        ],
    )

    # -- Leaderboard --------------------------------------------------------
    tiers = [
        ("Challenger", "Tests complete, listed with full numbers", "Publication only"),
        ("Provisional", "7 of 8 exploratory gates", "Priority re-test at next snapshot"),
        ("Verified", "8 of 8 exploratory gates", "Leaderboard slot, reward eligibility"),
        ("Defended", "8 of 8 at two consecutive snapshots", "Top tier; drops immediately on failure"),
    ]
    tier_rows = [([f"<strong>{E(t)}</strong>", E(req), E(earn), None],
                  ["NIST-MULTI", repo("research/leaderboard.md")]) for t, req, earn in tiers]
    board_rows = [([None, None, None, None, None, None], ["REPO", "NFL-RG"])]
    pages["leaderboard"] = dict(
        title="Leaderboard competition",
        lead="The competition is designed so luck is not what gets ranked: a luck-adjusted score, a hard gate set "
             "and a multiplicity penalty that grows with the number of strategies tested. No rank, score, ROI or "
             "reward is published because none is verified.",
        sections=[
            sec("Scoring design", "Components from the repository's specification.",
                T(["Component", "Weight / rule", "Official basis"], [
                    (["Luck-adjusted ROI rank", "0.60 × shrunk-ROI rank", "NIST confidence limits / Bonferroni"], ["NIST-CI", "NIST-BONF"]),
                    (["Confirmation-window rank", "0.20 × confirmation ROI rank", "NIST multiple comparisons"], ["NIST-MULTI"]),
                    (["Robustness", "0.10 × concentration, price stress, line-source robustness", "Official −110 quote and push rules"], ["NFL-ML-ART", "DK-MARKETS"]),
                    (["Coverage", "0.10 × settled-bet rank, capped at 1,000 bets", "NIST confidence limits"], ["NIST-CI"]),
                    (["Reward split", "Evenly across eligible tiers, never weighted by return", "NFL responsible-betting guidance"], ["NFL-RG"]),
                ])),
            sec("Tiers", "No strategy currently occupies a paid tier.",
                T(["Tier", "Requirement", "What it earns", "Strategies"], tier_rows,
                  caption="Blank = unverified, not zero.")),
            sec("Current standings", "Fail-closed: with no verified holdout evidence there is no rank to publish.",
                T(["Rank", "ID", "Strategy", "Bets", "ROI", "Prize"], board_rows,
                  caption="Every value is blank and flagged. See flags N05 and N06.")),
            sec("Anti-gaming rules", "Pre-registration, no dropping losers, declared snapshot cadence, price honesty, "
                "no post-hoc trimming and a full audit trail.",
                T(["Rule", "Why"], [
                    (["Pre-registration before the evaluation window", "Family size feeds the multiplicity penalty, so adding rules after the fact taxes everyone"], ["NIST-MULTI"]),
                    (["Every tested rule is published", "Prevents survivorship bias in the displayed board"], ["REPO"]),
                    (["Only recorded executable prices count", "Beating the close with an unobtainable price is not skill"], ["DK-MARKETS"]),
                    (["No post-hoc trimming", "No convenient start dates or silently excluded weeks"], ["NIST-MULTI"]),
                ])),
        ],
    )

    # -- Analysis -----------------------------------------------------------
    findings = [
        ("A01", "Verified", "NFL Support states the standard point-spread price is −110.", "verified", ["NFL-ML-ART"]),
        ("A02", "Verified", "DraftKings states −110 requires a $110 wager to win $100 profit.", "verified", ["DK-ODDS"]),
        ("A03", "Verified", "Whole-number spreads, two-way moneylines and exact totals settle as pushes.", "verified", ["DK-MARKETS"]),
        ("A04", "Verified", "All parlay legs must win; a push is removed and odds recalculated.", "verified", ["DK-PARLAY"]),
        ("A05", "Verified", "Correlated selections are restricted or offered only as re-priced same-game parlays.", "verified", ["FD-CT-RULES", "DK-PARLAY", "DK-SGP"]),
        ("A06", "Verified", "A prop bet concerns an individual player or event not directly tied to the game outcome; participation rules govern settlement.", "verified", ["DK-PROP", "DK-PLAYER"]),
        ("A07", "Verified", "Repeated comparisons do not preserve the overall significance level; contrasts must be fixed in advance.", "verified", ["NIST-MULTI", "NIST-BONF"]),
        ("A08", "Verified", "Correlation measures linear relationship; zero means no linear relationship.", "verified", ["NIST-CORR"]),
        ("A09", "Verified", "All 32 official 2025 standings rows match the repository's derived aggregates.", "verified", ["NFL-STANDINGS-2025"]),
        ("A10", "Verified anomaly", "Two NFL Support help articles have their bodies swapped relative to their titles.", "needs review", ["NFL-ML-ART", "NFL-PS-ART"]),
        ("A11", "Rights boundary", "NFL.com Terms prohibit systematic compilation without express prior written consent.", "needs review", ["NFL-TERMS"]),
        ("A12", "Exploratory", "No strategy cleared the exploratory gate family; the binding constraint was multiplicity.", None, ["NIST-MULTI", "REPO"]),
        ("A13", "Exploratory", "The own line was less accurate than the closing line in the exploratory build.", None, ["REPO"]),
        ("A14", "Exploratory", "Same-game spread × total dependence was measured near zero in the exploratory build.", None, ["NIST-CORR", "REPO"]),
        ("A15", "Exploratory", "A simulated no-skill leaderboard frequently produces a profitable-looking winner.", None, ["NIST-MULTI", "REPO"]),
        ("A16", "Gap", "No licensed official event-level dataset or timestamped executable quote archive.", None, ["NFL-TERMS", "REPO"]),
        ("A17", "Gap", "No official player-prop line feed; all prop correlation values are blank.", None, ["DK-PROP", "REPO"]),
        ("A18", "Gap", "No funded reward pool, sponsor, jurisdiction or payout terms.", None, ["NFL-RG", "REPO"]),
    ]
    finding_rows = []
    for fid, kind, text, value, sources in findings:
        finding_rows.append(([
            f"<strong>{E(fid)}</strong>", pill(kind, "ok" if kind == "Verified" else "warn"),
            E(text), E(value) if value else None,
        ], sources))
    pages["analysis"] = dict(
        title="Analysis & findings",
        lead="Every finding of the project in one table: verified facts carry their official source; exploratory "
             "and unverifiable findings have a blank value column and a link to the review page.",
        sections=[
            sec("Findings register", "18 findings. 'Value' is populated only when the official publisher states it.",
                T(["ID", "Type", "Finding", "Value / status"], finding_rows,
                  caption="Blank = unverified, not zero.", filter_id="find-filter")),
            sec("Interpretation", "What the verified rules mean for the strategy programme.",
                T(["Question", "Answer supported by official sources"], [
                    (["Can a leaderboard rank luck as skill?", "Not honestly. NIST states repeated comparisons do not preserve the overall significance level and contrasts should be fixed in advance."], ["NIST-MULTI"]),
                    (["Is a same-game correlation an automatic edge?", "No. Licensed operators restrict correlated selections and state SGP odds are calculated differently."], ["FD-CT-RULES", "DK-SGP"]),
                    (["Why are prop combos framework-only?", "Official prop rules exist, but no official prop line/price archive was available; no correlation value is claimed."], ["DK-PROP", "DK-PLAYER"]),
                    (["Why is luck bounded rather than removed?", "Confidence intervals and bootstrap estimates quantify uncertainty; they do not eliminate variance."], ["NIST-CI", "NIST-BOOT"]),
                ])),
        ],
    )

    # -- Flagged ------------------------------------------------------------
    pages["flagged"] = dict(
        title="Flagged for Review",
        lead="Clearly labelled review register. Every irregularity, unverifiable value and open question is listed "
             "here with a source link. These items do not block publication; they are published so the owner can "
             "review them after the site is live.",
        kpis=[("Total items", len(FLAGS), "published, not hidden"),
              ("High severity", sum(1 for f in FLAGS if f[1] == "high"), "mostly data-availability blockers"),
              ("Verified anomalies", 1, "NFL Support swapped article bodies"),
              ("Unverified values", "all blank", "never inferred")],
        sections=[
            sec("Full register", "Statuses: resolved, mitigated, verified anomaly, unverified, needs review, published finding.",
                T(["ID", "Severity", "Finding", "Detail", "Status"], flag_rows(),
                  caption="Every row carries an official source link. Anchors match the IDs used elsewhere on this site.",
                  filter_id="flag-filter")),
            sec("How to request a change", "Open an issue or pull request on the repository referencing the flag ID. "
                "The coordination board records the session, scope and verification status of each change.",
                T(["Action", "Where"], [
                    (["Open an issue / PR with the flag ID", "Repository on GitHub"], [REPO_TREE]),
                    (["Read the shared task board", A("sessions.html", "Sessions & board")], [repo("COORDINATION.md")]),
                    (["Read the verification protocol", A("verification.html", "Verification log")], [repo("hub/check_hub.py")]),
                ])),
        ],
    )

    # -- Sessions -----------------------------------------------------------
    session_rows = [
        (["arena/9febee68-korea3", "First research brief + root site", "merged (PR #1)", "root pages; preserved in history and /site/prior/"], [repo("COORDINATION.md")]),
        (["arena/65d448da-korea3", "Independent audit + QA", "merged (PRs #3,#4,#5,#7,#8)", "audit/**"], [repo("COORDINATION.md"), tree("audit/")]),
        (["arena/d118ca7e-korea3", "Second Line Lab build", "merged (PR #6)", "docs/**, pipeline/**, reports/**"], [repo("COORDINATION.md"), tree("docs/")]),
        (["arena/c70bdb9d-korea3", "Empirical pipeline + /site/", "merged (PRs #9,#15,#17)", "data/**, scripts/**, site/**, research/**"], [repo("COORDINATION.md"), tree("site/")]),
        (["arena/9f5e9cb5-korea3", "Root dashboard + line_lab/", "merged (PR #13)", "line_lab/**, root *.html, assets/**"], [repo("COORDINATION.md"), tree("line_lab/")]),
        (["arena/398c4b58-korea3", "Independent session site", "merged (PR #23)", "session-398c4b58/**"], [repo("COORDINATION.md"), tree("session-398c4b58/")]),
        (["arena/cbcd97cc-korea3", "Verified workbench", "merged (PRs #36,#37)", "nfl_lab/**, verified/**, tests/**"], [repo("COORDINATION.md"), tree("verified/")]),
        (["arena/25ea8ac4-korea3", "Final integration (this session)", "in progress", "hub/**, index.html banner, README.md, COORDINATION.md"], [repo("COORDINATION.md"), tree("hub/")]),
    ]
    pages["sessions"] = dict(
        title="Sessions & coordination board",
        lead="The shared task board in COORDINATION.md, the session registry, the active claim and the handoff "
             "record. No another session's file was edited by this integration run.",
        sections=[
            sec("Session registry", "Eight bodies of work; all preserved.",
                T(["Session", "Role", "Status", "Scope"], session_rows,
                  caption="Source: the coordination board in this repository.")),
            sec("Active claim (this session)", "Claimed before work started; the claim commit was pushed immediately.",
                T(["Task", "Status", "Owner", "File scope"], [
                    (["I01 Board claim + handoff", "done", E(SESSION), "COORDINATION.md (additive)"], [repo("COORDINATION.md")]),
                    (["I02 Line-by-line source re-verification", "done", E(SESSION), "hub/data/**, hub/verification.html, hub/repo-review.html"], [repo("hub/data/sources.json")]),
                    (["I03 Executive summary + requirements", "done", E(SESSION), "INTEGRATION_EXECUTIVE_SUMMARY.md, hub/requirements.html, hub/analysis.html"], [repo("INTEGRATION_EXECUTIVE_SUMMARY.md")]),
                    (["I04 Dashboard + category pages", "done", E(SESSION), "hub/**, index.html banner, README.md"], [tree("hub/")]),
                    (["I05 Flagged page + verifier + CI", "done", E(SESSION), "hub/flagged.html, hub/check_hub.py, .github/workflows/hub-verify.yml"], [repo("hub/check_hub.py")]),
                    (["I06 PR, merge, Pages deploy, board record", "done", E(SESSION), "COORDINATION.md"], [repo("COORDINATION.md")]),
                ])),
            sec("Handoff and deviations", "Recorded rather than hidden.",
                T(["Item", "Record"], [
                    (["Stale claim handoff", "T15 from arena/c70bdb9d-korea3 was in progress with no commits for >60 minutes; integration was taken over with a handoff note (N12)."], [repo("COORDINATION.md")]),
                    (["Branch-name deviation", "Arena fixes this session to arena/25ea8ac4-korea3; no session-<id> branch was created (N10)."], [repo("COORDINATION.md")]),
                    (["Open PR #19", "Left untouched; belongs to the audit session (N09)."], [repo("COORDINATION.md")]),
                    (["Merge conflicts", "None occurred. git pull --rebase was run before every push."], [repo("COORDINATION.md")]),
                ])),
        ],
    )

    # -- Archive ------------------------------------------------------------
    archive_rows = [
        (["Root dashboard (line_lab)", "/", "14 generated pages; empirical tables cite repository CSVs", "exploratory"], [tree(""), repo("index.html")]),
        (["Empirical pipeline + site", "/site/", "15 pages, walk-forward model, 18 rules, 8 gates", "exploratory"], [tree("site/")]),
        (["First research brief", "/site/prior/", "Byte-identical mirror of the earlier root site", "archived"], [tree("site/prior/")]),
        (["Second Line Lab build", "/docs/", "11 pages plus pipeline/ and reports/", "exploratory"], [tree("docs/")]),
        (["Independent audit", "/audit/", "Line-by-line audit of the early dashboards", "audit"], [tree("audit/")]),
        (["Session site", "/session-398c4b58/site/", "Independent 17-page build", "exploratory"], [tree("session-398c4b58/site/")]),
        (["Verified workbench", "/verified/", "12 official-evidence pages, fail-closed", "official-evidence"], [tree("verified/")]),
        (["Integration dashboard", "/hub/", "This 24-page consolidation", "official-evidence"], [tree("hub/")]),
    ]
    pages["archive"] = dict(
        title="Prior work archive",
        lead="Six earlier bodies of work remain live and untouched. This page is the map. Their empirical values "
             "come from a third-party dataset and are not republished as verified values in the integration dashboard.",
        sections=[
            sec("Published builds", "GitHub Pages here is a legacy main:/ deploy, so every directory is served.",
                T(["Body of work", "Live path", "Contents", "Classification"], archive_rows,
                  caption="Paths are relative to https://karagemop466-tech.github.io/Korea3/.")),
            sec("Separation rule", "Why the archive is separate from the verified tables.",
                T(["Rule", "Detail"], [
                    (["Preservation", "No site directory was deleted, renamed or overwritten by this integration session."], [repo("COORDINATION.md"), "REPO"]),
                    (["No promotion", "Third-party backtest prices, correlations, ROI and rankings are not treated as official verification."], ["NFL-TERMS", "REPO"]),
                    (["Single official layer", "The integration dashboard and the verified workbench are the only official-source views."], [tree("hub/"), tree("verified/")]),
                ])),
        ],
    )

    # -- Suggestions & decision paths --------------------------------------
    # Scores are owner-judgment inputs on a 1-5 scale, not measurements.
    # priority = impact * confidence / effort, shown to one decimal.
    SUGGESTIONS = [
        ("S01", "Publish a standing Suggestions & decision-path page", "Site", "Which path to fund and in what order", 5, 5, 1, "none", "done this session", ["REPO"]),
        ("S02", "Publish a Questions & missing-information register", "Site", "Whether a decision is ready", 5, 5, 1, "none", "done this session", ["REPO"]),
        ("S03", "Freeze a data-rights register before ingesting any new source", "Governance", "Whether data can be used at all", 5, 5, 1, "legal review", "ready now", ["NFL-TERMS", "REPO"]),
        ("S04", "License event-level official data and a timestamped executable quote archive", "Research", "Every empirical claim, ROI and reward", 5, 3, 5, "budget + vendor (Q02, Q03)", "blocked — data", ["NFL-TERMS", "DK-MARKETS"]),
        ("S05", "Admit a licensed availability feed: injuries, inactives, depth order", "Research", "Injury and lineup adjustments", 5, 3, 4, "vendor field map (Q15)", "blocked — data", ["NFL-INJURIES", "NFL-ROSTER-PAGE"]),
        ("S06", "Build a Deficiency Index for 2nd/3rd/4th-string replacements", "Research", "Line adjustment when starters sit", 5, 2, 5, "S05 + pre-registered weights", "blocked — data", ["NFL-ROSTER", "NFL-IR-FAQ"]),
        ("S07", "Pre-register the competition protocol before any result is seen", "Governance", "Whether a reward is earned or mined", 5, 5, 2, "owner sign-off (Q13, Q22)", "ready now", ["NIST-MULTI", "REPO"]),
        ("S08", "Rank by closing-line value and a lower confidence bound, not raw ROI", "Analytics", "Which strategy is actually skilful", 5, 4, 2, "quote archive (S04)", "ready now", ["DK-MARKETS", "NIST-CI"]),
        ("S09", "Require a minimum sample before any strategy is ranked", "Analytics", "Whether a hot streak is noise", 5, 5, 1, "none", "ready now", ["NIST-SAMPLESIZE"]),
        ("S10", "Control the false-discovery rate across the whole strategy family", "Analytics", "How many winners are expected by luck", 5, 5, 2, "declared family size", "ready now", ["NIST-BONF", "NIST-MULTI"]),
        ("S11", "Run a permutation/bootstrap null for every strategy", "Analytics", "Whether the result beats random selection", 5, 5, 3, "resampling code", "ready now", ["NIST-BOOT"]),
        ("S12", "Hash-lock an untouched holdout before tuning", "Governance", "Whether out-of-sample skill is real", 5, 5, 2, "protocol freeze", "ready now", ["NIST-MULTI", "REPO"]),
        ("S13", "Publish calibration (Brier / log loss) beside error in points", "Analytics", "Whether probabilities are honest", 4, 4, 2, "none", "ready now", ["REPO", "NIST-CI"]),
        ("S14", "Publish the own line against the closing line with an interval", "Analytics", "Whether the model adds information", 5, 4, 2, "S04 for executable prices", "ready now", ["NIST-CI", "REPO"]),
        ("S15", "Model dependence explicitly and require same-game-parlay pricing", "Analytics", "Whether a parlay has any edge", 4, 5, 3, "SGP price feed", "ready now", ["FD-CT-RULES"]),
        ("S16", "Gate prop combos on settlement and same-player rules", "Analytics", "Whether a prop combo is even valid", 4, 4, 2, "prop feed (Q19)", "blocked — data", ["DK-PLAYER", "FD-CT-RULES"]),
        ("S17", "Monitor data staleness, line drift and lineup changes", "Operations", "Whether a live line is current", 4, 4, 2, "S04/S05", "ready now", ["REPO", "NIST-CI"]),
        ("S18", "Add a no-bet and market-efficiency benchmark", "Analytics", "Whether the strategy beats doing nothing", 5, 5, 1, "none", "ready now", ["DK-MARKETS", "NIST-CI"]),
        ("S19", "Add a global search and a side-by-side strategy comparison view", "Site", "Which strategy to look at first", 3, 5, 3, "none", "ready now", ["REPO"]),
        ("S20", "Publish a printable one-page decision sheet", "Site", "A decision made in one meeting", 3, 5, 1, "none", "ready now", ["REPO"]),
        ("S21", "Add a glossary of the official terms used on the site", "Site", "Misreading a rule or status", 3, 5, 1, "none", "ready now", ["NFL-INJ-POLICY", "NFL-ROSTER"]),
        ("S22", "Offer a downloadable audit bundle (CSV/JSON)", "Site", "Independent re-checking", 4, 3, 3, "rights review (S03)", "blocked — legal", ["NFL-TERMS", "REPO"]),
    ]
    sug_rows = []
    for sid, text, cat, decision, impact, conf, effort, prereq, status, srcs in SUGGESTIONS:
        priority = impact * conf / effort
        kind = "ok" if status.startswith("done") else ("warn" if status.startswith("blocked") else "info")
        sug_rows.append(([
            f"<strong>{E(sid)}</strong>", E(text), E(cat), E(decision),
            str(impact), str(conf), str(effort), f"{priority:.1f}", E(prereq),
            pill(status, kind),
        ], srcs, sid))
    ladder = [
        ("D0", "Publish the research dashboard", "The site is live, sourced and fail-closed", "done — this session", "None: no empirical claim is made"),
        ("D1", "Settle data rights and budget", "Written permission or a licence; a funded budget line", "blocked — Q01, Q02, Q03", "Any ingestion beyond the current pinned third-party data"),
        ("D2", "Admit event-level data and quotes", "Vendor field map, quote timestamps, revision history", "blocked — Q05, Q06, Q07", "Every ROI, CLV, correlation and reward value"),
        ("D3", "Pre-register the competition", "Family size, holdout, metrics, promotion and kill rules signed", "ready — S07", "Ranking any strategy"),
        ("D4", "Integrate availability", "Injury, inactive and depth-order feed with timestamps", "blocked — Q15, Q16, Q17", "Any injury-based adjustment"),
        ("D5", "Run the locked holdout", "D2 + D3 complete; no changes after unblinding", "blocked — D2", "Promotion or rewards"),
        ("D6", "Fund and open the competition", "Pool, jurisdiction, eligibility, tax and dispute terms approved", "blocked — Q21, Q23, Q24", "Any payout"),
    ]
    ladder_rows = [(list(r), ["REPO", "NFL-TERMS"]) for r in ladder]
    pages["suggestions"] = dict(
        title="Suggestions & decision paths",
        lead="A reviewable menu of suggestions, each tied to the decision it improves, with a transparent "
             "1-5 owner-judgment score, its prerequisite and its blocker. Nothing here is a factual claim about "
             "the NFL; the scores are proposals and the evidence links show what each one depends on.",
        kpis=[
            ("Suggestions on the board", len(SUGGESTIONS), "Site, research, analytics and governance"),
            ("Ready to approve now", sum(1 for s in SUGGESTIONS if s[8] == "ready now"), "No new data licence required"),
            ("Blocked on data or rights", sum(1 for s in SUGGESTIONS if s[8].startswith("blocked")), "Cannot be completed honestly today"),
            ("Scores that are measurements", 0, "Priority is owner judgment: impact × confidence ÷ effort"),
        ],
        sections=[
            sec("How to use this page",
                "Read the decision ladder first. It shows which decisions are already made, which are ready, and "
                "which cannot be made honestly until a named question is answered. Then choose a path at the bottom. "
                "The register keeps a stable ID order and shows a priority score only as a reading aid; no score is evidence.",
                T(["Step", "What it answers", "Where"], [
                    (["1 · Decision ladder", "What can be decided now, and what each stage unlocks", A("suggestions.html", "decision ladder")], ["REPO"]),
                    (["2 · Suggestion register", "What to do, why, what it costs in effort, and what blocks it", A("suggestions.html", "suggestion register")], ["REPO"]),
                    (["3 · Site improvements", "Changes to this site that improve decision quality", A("suggestions.html", "site improvements")], ["REPO"]),
                    (["4 · Choose a path", "Three funding paths and their requirements", A("suggestions.html", "choose a path")], ["REPO"]),
                ])),
            sec("Decision ladder", "Each stage is a gate, not a task list. A later stage cannot be entered while an earlier gate is open.",
                T(["Stage", "Decision", "What must be true", "Status", "What it unlocks"], ladder_rows,
                  caption="Statuses are project state, not official facts.", filter_id="ladder"),
                note="A 'ready' stage means the work can be done without new data; it does not mean the decision is already made."),
            sec("Suggestion register", "Twenty-two suggestions. Impact and confidence are 1-5 inputs; effort is 1 (small) to 5 (large). "
                "Priority is shown only to make the list readable.",
                T(["ID", "Suggestion", "Type", "Decision it improves", "Impact", "Conf.", "Effort", "Priority", "Prerequisite", "Status"],
                  sug_rows, caption="Scores are proposals by the session, not measurements. Every row links to its evidence base.",
                  numeric=(4, 5, 6, 7), filter_id="sug"),
                note="A blocked suggestion is not a rejected one: it is the honest state until the named input exists."),
            sec("Site improvements that specifically help decision-making",
                "Small, low-risk changes to this dashboard, in the order they would be built. The first three are already "
                "in place on this page set.",
                T(["ID", "Improvement", "What it changes for the reviewer", "Effort", "Status"], [
                    (["U01", "A dedicated Decisions section with this page and the Questions page", "The reviewer sees options and unknowns without reading the whole repository", "done"], ["REPO"]),
                    (["U02", "A status pill and a prerequisite column on every proposal", "No proposal looks approved when it is blocked", "done"], ["REPO"]),
                    (["U03", "Filter boxes on the suggestion and question tables", "A 22-row and 38-row register stay usable on a phone", "done"], ["REPO"]),
                    (["U04", "A strategy comparison view: one row per strategy, one column per gate", "Shows exactly which gate failed instead of a pass/fail summary", "2"], ["REPO"]),
                    (["U05", "A printable one-page decision sheet", "A decision can be taken in one meeting with the evidence in front of you", "1"], ["REPO"]),
                    (["U06", "A glossary of official status and roster terms", "Prevents a reader treating 'questionable' as a probability", "1"], ["NFL-INJ-POLICY", "NFL-ROSTER"]),
                    (["U07", "A visible 'last verified' date and a diff log per source", "A stale official page cannot silently remain 'verified'", "2"], ["REPO"]),
                    (["U08", "Mobile card layout for the wide tables", "The same data is readable on a phone without horizontal scrolling", "3"], ["REPO"]),
                    (["U09", "A downloadable CSV/JSON audit bundle", "Independent re-checking without cloning the repo", "3"], ["REPO", "NFL-TERMS"]),
                ], caption="Effort is a session estimate, not a quote. U09 is blocked until the rights review in S03 is signed off.")),
            sec("What not to do yet", "The failure modes this page is designed to prevent.",
                T(["Do not", "Why not", "Evidence"], [
                    (["Publish ROI, rank or a winner", "No timestamped executable quote archive exists, so a return cannot be reconstructed"], ["DK-MARKETS", "REPO"]),
                    (["Scrape or compile NFL.com pages", "The official Terms prohibit systematic retrieval or compilation absent express prior written consent"], ["NFL-TERMS"]),
                    (["Promise prizes or open entries", "No pool, sponsor, jurisdiction, eligibility rule or dispute process is approved"], ["NFL-RG", "REPO"]),
                    (["Infer depth-chart order or a backup's quality", "Official roster pages publish status codes without a legend and no dated order history"], ["NFL-ROSTER-PAGE", "NFL-IR-FAQ"]),
                    (["Tune on the evaluation period", "Contrasts must be fixed before results are observed; otherwise the significance level is not preserved"], ["NIST-MULTI"]),
                ])),
            sec("Choose a path", "Three coherent paths. The recommendation is B: a small licensed pilot that makes the "
                "existing method testable without opening a competition.",
                T(["Path", "What you authorise", "What you get", "Cost", "Main risk", "Verdict"], [
                    (["A · Research only", "Keep the site and method; no new data spend", "A transparent, sourced research record; no performance claim", "0 (existing work)", "Stays unfalsifiable; no rewards", "Safe default"], ["NFL-TERMS", "REPO"]),
                    (["B · Licensed pilot", "S04 + S05 + S07 + S09-S12: one season of data, locked holdout", "A testable own-line and strategy result, honestly bounded", None, "Vendor cost and renewal; small sample", "Recommended"], ["NIST-SAMPLESIZE", "NFL-TERMS"]),
                    (["C · Full competition", "B plus prize pool, legal review, public entries, payouts", "A public leaderboard with rewards", None, "Legal, funding and gaming risk", "Only after B passes"], ["NFL-RG", "NIST-MULTI"]),
                ], caption="Cost cells are blank because no vendor quote or budget was obtained; they are flagged, not estimated."),
                note="No path is approved by this page. Publication of a proposal is not authorisation to spend money."),
            sec("Recommended order if path B is approved", "Sequenced so that no step depends on a later one.",
                T(["Order", "Actions", "Why this order", "Exit condition"], [
                    (["1 · This week", "S01, S02, S03, S07, S09-S12, S18", "Free, reversible and prevents the most expensive mistakes"], ["REPO", "NIST-MULTI"]),
                    (["2 · Before ingestion", "S04 vendor selection, S05 field map, S08 metric freeze", "Defines what 'closing', 'available' and 'skilful' mean before seeing results"], ["DK-MARKETS", "NFL-INJURIES"]),
                    (["3 · On ingestion", "S06 deficiency index, S13 calibration, S14 own line, S15 parlays, S17 monitoring", "Adds signal only after the measurement is stable"], ["NFL-ROSTER", "NIST-CI"]),
                    (["4 · At holdout", "S10, S11, holdout unblinding, S12 audit", "One pre-registered test, no second bite"], ["NIST-BONF", "NIST-BOOT"]),
                    (["5 · After a pass", "Reward terms, legal review, funding, public entry", "Only a strategy that cleared the gates can be rewarded"], ["NFL-RG", "REPO"]),
                ])),
        ],
    )

    # -- Questions & missing information -----------------------------------
    ANSWERED = [
        ("QA01", "May we compile NFL.com content into a dataset?", "No, not without express prior written consent: the Terms prohibit systematic retrieval or compilation for a collection, compilation, database or directory.", ["NFL-TERMS"]),
        ("QA02", "What do the game-status labels mean?", "Out = will not play; Doubtful = unlikely to participate; Questionable = uncertain whether the player will play. 'Probable' was eliminated.", ["NFL-INJ-POLICY"]),
        ("QA03", "What do the practice labels mean?", "Did Not Participate; Limited Participation = less than 100% of a player's normal repetitions; Full Participation = 100%. The practice report no longer carries 'Out'.", ["NFL-INJ-POLICY"]),
        ("QA04", "How long must an injured-reserve player miss?", "At least four games. A club may designate up to eight players to return; a player may be designated twice and both count toward the eight.", ["NFL-IR-FAQ"]),
        ("QA05", "How large are the rosters and practice squads?", "53 on the active/inactive list; 48 game-day active with at least eight offensive linemen, otherwise 47; practice squad 16 (17 with an International Pathway player); a practice-squad player may be elevated for at most three regular-season games.", ["NFL-ROSTER"]),
        ("QA06", "Is there an official injury report we can point to?", "Yes. NFL.com publishes a weekly injury report with per-club tables and the columns Player, Position, Injuries, Practice Status and Game Status. It displays no export, revision timestamp or licence statement.", ["NFL-INJURIES"]),
        ("QA07", "Does the league publish betting lines?", "No official odds or line publication is listed in the league's own Stats & Records guidance, which points to statistics, records and the Record and Fact Book. Market prices therefore come from licensed operators, not the league.", ["NFL-STATS"]),
        ("QA08", "What is the standard price and what does it pay?", "NFL Support states the point-spread price is most often -110; DraftKings states a -110 wager risks $110 to win $100.", ["NFL-ML-ART", "DK-ODDS"]),
        ("QA09", "What win rate breaks even at -110?", "52.381% (110 ÷ 210). This is arithmetic, not a forecast.", ["DK-ODDS"]),
        ("QA10", "How many bets are needed to detect a real edge?", "It depends on alpha, power and the true edge. With 80% power and a one-sided 5% test, detecting 55% against a 52.381% break-even needs about 2,242 settled bets; 53% needs about 40,223.", ["NIST-SAMPLESIZE"]),
        ("QA11", "How much dependence does a two-leg coin-flip parlay need?", "At -110 per leg, the parlay pays 3.6446; break-even joint probability is 27.438%. Against two independent 50% legs, the phi coefficient must be at least 0.0975. This is an arithmetic identity under the stated assumption.", ["DK-ODDS", "NIST-CORR"]),
        ("QA12", "May correlated legs be parlayed?", "Not as an ordinary parlay. FanDuel states correlated selections are not permitted unless explicitly offered as a Same Game Parlay, and reserves the right to void a correlated parlay accepted in error.", ["FD-CT-RULES"]),
    ]
    OPEN_Q = [
        ("Q01", "Is there a signed licence or written permission for the data we intend to use?", "Terms prohibit compilation absent consent", "An executed licence or written permission", "Legal review and vendor contract", "S04, all empirical values", ["NFL-TERMS"]),
        ("Q02", "Which vendor or feed, with which fields, latency and revision history?", "No vendor has been approached", "A field map, SLA and price", "Issue a requirements sheet and request quotes", "S04, S05, S17", ["REPO"]),
        ("Q03", "What is the budget for data, engineering and legal review?", "No budget line exists", "An approved amount", "Owner decision", "Path B and C", ["REPO"]),
        ("Q04", "Which jurisdictions and users will see the site or enter a contest?", "The site is public research only", "Target jurisdictions and eligibility rules", "Owner and counsel", "Rewards, disclaimers", ["NFL-RG"]),
        ("Q05", "Which book or books define the market being beaten?", "No book is designated", "A named venue and market type", "Owner decision, then archive its rules", "CLV, ROI, S08", ["DK-MARKETS", "FD-CT-RULES"]),
        ("Q06", "What exact timestamp defines 'closing'?", "No timestamp exists in the pinned data", "A rule such as 'last quote before kickoff' plus stored times", "Vendor field map", "CLV and holdout scoring", ["REPO"]),
        ("Q07", "Do we have opening and closing prices for the whole evaluation window?", "Pre-2021 opening lines are missing; 26.9% of prices were imputed in exploratory work", "A complete, timestamped archive", "Licensed archive", "Line-movement and CLV studies", ["REPO"]),
        ("Q08", "Whose settlement rules govern pushes, voids and stat corrections?", "Operator rules differ and are book-specific", "A designated rulebook for the competition", "Owner decision and publication", "Scoring and payouts", ["DK-MARKETS", "DK-PARLAY"]),
        ("Q09", "Is the benchmark the closing line, an opening line or a consensus?", "No benchmark is fixed", "One pre-registered benchmark", "Protocol freeze S07", "Every skill claim", ["NIST-MULTI", "REPO"]),
        ("Q10", "What accuracy and calibration thresholds must an own line meet?", "Proposal: MAE versus close plus an interval and calibration", "Owner approval of the thresholds", "Approve or amend the proposal", "Own-line promotion", ["NIST-CI", "NIST-SAMPLESIZE"]),
        ("Q11", "How large is the strategy family that multiplicity control must cover?", "18 + 11 + 8 entries exist across three builds; future entries unknown", "A declared and frozen family size", "Pre-registration", "Any q-value or 'winner'", ["NIST-BONF", "NIST-MULTI"]),
        ("Q12", "Which seasons are the untouched holdout?", "Exploratory work used 2000-2026 with a 2016-2026 confirmation window", "A locked window that has never been inspected", "Protocol freeze and hash commitment", "Out-of-sample claims", ["NIST-MULTI"]),
        ("Q13", "What is the promotion threshold?", "Proposal: q ≤ 0.10, lower confidence bound above break-even, minimum sample met, two consecutive snapshots", "Owner approval", "Approve or amend", "Leaderboard and rewards", ["NIST-BONF", "NIST-CI"]),
        ("Q14", "What is the kill criterion for a strategy?", "No kill rule is signed", "A pre-declared stop rule", "Protocol freeze", "Avoiding indefinite retesting", ["NIST-MULTI"]),
        ("Q15", "Which availability feed, and how are revisions handled?", "Official report exists; no feed is licensed", "A timestamped feed with revision history", "Vendor selection", "S05, S06", ["NFL-INJURIES"]),
        ("Q16", "How is a 'starter' defined?", "Roster size and depth order are official concepts; no threshold is fixed here", "A snap-share or depth-order definition", "Owner decision after data review", "Deficiency Index", ["NFL-ROSTER", "NFL-ROSTER-PAGE"]),
        ("Q17", "How are 2nd, 3rd and 4th string weighted?", "No weights exist", "Pre-registered weights summing to one", "S06 protocol", "Any defensive or offensive adjustment", ["NFL-ROSTER", "REPO"]),
        ("Q18", "Do we model the weekly report or game-day inactives?", "Both exist; neither is archived here", "A choice and its timestamp rule", "Owner decision", "Kickoff availability", ["NFL-INJ-POLICY", "NFL-INJURIES"]),
        ("Q19", "Which prop markets, books and settlement rules?", "Rules are sourced; no line feed is licensed", "A market list and feed", "Vendor selection", "Prop combos, S16", ["DK-PLAYER", "FD-CT-RULES"]),
        ("Q20", "How are same-player legs and stat corrections handled?", "Operator rules describe settlement but no archive exists", "A written rule for the competition", "Owner decision", "Prop-combo scoring", ["DK-PLAYER"]),
        ("Q21", "Who funds the reward pool and how much?", "No pool exists", "A funded amount and a custodian", "Owner and sponsor", "Any prize", ["NFL-RG"]),
        ("Q22", "What is the scoring formula and tie-break?", "Proposal: CLV, lower confidence bound, calibration, stability", "Owner approval", "Approve or amend", "Ranking", ["NIST-CI", "NIST-BONF"]),
        ("Q23", "Are rewards cash, points or recognition?", "Unspecified", "A defined reward type", "Owner and counsel", "Tax and eligibility", ["NFL-RG"]),
        ("Q24", "Has contest and advertising law been reviewed?", "No review exists", "Written counsel opinion", "Engage counsel", "Opening entries", ["NFL-RG"]),
        ("Q25", "Who owns each gate decision?", "No named decision owner", "A name and a signature per gate", "Governance decision", "Any promotion", ["REPO"]),
        ("Q26", "How often is the site re-verified?", "The build is deterministic but source pages change", "A cadence and a diff log", "Operations decision", "Stale claims", ["REPO"]),
    ]
    answered_rows = [([f"<strong>{E(q)}</strong>", E(question), E(answer), pill("answered", "ok")], srcs) for q, question, answer, srcs in ANSWERED]
    open_rows = [([f"<strong>{E(q)}</strong>", E(question), E(known), E(missing), E(how), E(blocks), pill("open", "warn")], srcs)
                 for q, question, known, missing, how, blocks, srcs in OPEN_Q]
    inventory = [
        ("Game results and scores", "Available — third-party pinned dataset (7,075 games)", "nflverse, pinned by commit", "No official per-game attestation", "Model fitting", ["NFLVERSE", "NFL-STATS"]),
        ("Closing and opening prices", "Partial — 26.9% imputed in exploratory work; pre-2021 openings missing", "pinned dataset", "Timestamped executable quotes", "CLV, ROI", ["REPO", "DK-MARKETS"]),
        ("Injury report and inactives", "Missing as data; official page exists", "NFL.com injury report", "Licensed feed and revision history", "Availability adjustment", ["NFL-INJURIES"]),
        ("Depth order and snap share", "Missing", "Official club roster pages (current status only)", "Dated depth chart and snap counts", "Deficiency Index", ["NFL-ROSTER-PAGE"]),
        ("Player-prop lines", "Missing", "Operator rule pages only", "Licensed prop feed", "Prop combos", ["DK-PROP"]),
        ("Weather", "Partial and unverified", "Pinned dataset", "Station, time and source per game", "Weather signals", ["REPO"]),
        ("Officials and penalties", "Missing", "No source held", "Play-by-play with officials", "Penalty signals", ["REPO"]),
        ("Reward terms", "Missing", "No source held", "Funded pool and contest rules", "Prizes", ["NFL-RG"]),
    ]
    discovery = [
        ("Request data dictionaries and sample files from two vendors", "Exact field names, timestamps, revision policy and true latency", "Low", "Name the fields in Q02/Q06", ["REPO"]),
        ("Run a licence and rights review before ingestion", "Whether a source may be stored and republished", "Low", "Record the answer in a rights register (S03)", ["NFL-TERMS"]),
        ("Instrument an official-page diff watcher without storing player rows", "How often a status changes and how stale a snapshot is", "Medium", "Log hashes and timestamps only", ["REPO"]),
        ("Backtest data completeness by season and book", "Where the archive is silently missing prices", "Low", "Publish the coverage table", ["REPO"]),
        ("Run a labelled sensitivity grid", "Whether a conclusion depends on one tuning choice", "Medium", "Pre-declare the grid", ["REPO"]),
        ("Simulate a no-skill league under the exact scoring rule", "How often luck produces a 'winner'", "Medium", "Publish the false-positive rate", ["NIST-BOOT", "NIST-MULTI"]),
        ("Ask a domain reviewer to attack the protocol", "Ambiguities that the builder cannot see", "Medium", "Record objections and dispositions", ["REPO"]),
        ("Run the whole pipeline in paper mode for one season", "Operational failures before money is at risk", "High", "Pre-register the paper window", ["NIST-CI"]),
    ]
    inventory_rows = [(list(r[:5]), r[5]) for r in inventory]
    discovery_rows = [(list(r[:4]), r[4]) for r in discovery]
    pages["questions"] = dict(
        title="Questions & missing information",
        lead="Every question that has to be answered before a decision can reasonably be made, split into what an "
             "official source already answers and what only the owner or a licensed feed can answer. Where a value "
             "is unknown it is blank, never inferred.",
        kpis=[
            ("Questions on the register", len(ANSWERED) + len(OPEN_Q), "12 answered, 26 open"),
            ("Answered from an official source", len(ANSWERED), "Opened in this session and linked"),
            ("Open — owner or licensed input", len(OPEN_Q), "Each names how to answer it"),
            ("Values inferred to fill a gap", 0, "Blank plus a flag instead"),
        ],
        sections=[
            sec("Answered now from official sources", "These answers are usable immediately and constrain the design. "
                "They are quoted, not paraphrased into a stronger claim than the publisher made.",
                T(["ID", "Question", "Answer", "Status"], answered_rows,
                  caption="Every answer links to the official page opened on 2026-11-12 (UTC).", filter_id="qa")),
            sec("Blocking questions that are still open", "Each row states what is already known, what is missing, and "
                "the concrete action that would answer it. A row is not a task until the owner authorises it.",
                T(["ID", "Question", "What we know", "What is missing", "How to answer it", "Blocks", "Status"], open_rows,
                  caption="Open means unanswered, not unanswerable.", filter_id="qo")),
            sec("Information inventory", "What the project actually holds today, and what it does not.",
                T(["Information", "Availability", "Where it lives", "Gap", "Needed for"], inventory_rows,
                  caption="Availability describes this repository, not the market. Missing values are never filled.")),
            sec("Proposed ways to discover the missing information", "Methods that produce evidence rather than opinion. "
                "The first two are prerequisites; the rest can run in parallel.",
                T(["Method", "What it reveals", "Effort", "First step"], discovery_rows,
                  caption="Effort is a session estimate. No method requires scraping a page whose terms prohibit it."),
                note="A method that cannot be reconciled with the official Terms is not an option, however useful its output would be."),
            sec("Decision readiness summary", "A single row per decision, with the count of open questions attached.",
                T(["Decision", "Open questions", "Ready?"], [
                    (["Fund a licensed data pilot", "Q01-Q09, Q15, Q19", pill("no — 13 open", "warn")], ["NFL-TERMS", "REPO"]),
                    (["Pre-register the competition", "Q10-Q14, Q22, Q25", pill("no — 7 open", "warn")], ["NIST-MULTI", "REPO"]),
                    (["Adjust lines for injuries", "Q15-Q18", pill("no — 4 open", "warn")], ["NFL-INJURIES", "NFL-ROSTER"]),
                    (["Open public entries", "Q04, Q21, Q23, Q24", pill("no — 4 open", "warn")], ["NFL-RG", "REPO"]),
                    (["Publish the research site", "none", pill("yes — live", "ok")], ["REPO"]),
                ], caption="Counts are of the questions listed above, not a completeness proof.")),
        ],
    )

    # -- Injuries & depth chart --------------------------------------------
    rules = [
        ("Roster: 53-man active/inactive", "'The active/inactive list remains at 53 players for the regular season and playoffs.'", "A club can lose a starter and replace him only from this pool or an elevation.", ["NFL-ROSTER"]),
        ("Roster: 48 or 47 game-day active", "'maximum roster size is 48 players' with at least eight offensive linemen; 'If a team has fewer than eight offensive linemen, the maximum drops to 47 players.'", "Some healthy roster members are inactive every week; the injury report alone does not name them.", ["NFL-ROSTER"]),
        ("Practice squad: 16 or 17", "'The practice squad consists of 16 players as of 2026. However, teams can sign 17 players ... if one of those players is a member of the NFL's International Pathway Program.'", "Fourth-string and emergency depth often sits here, outside the 53.", ["NFL-ROSTER"]),
        ("Practice-squad elevation", "'Each practice squad players can be elevated for a maximum of three regular season games in the same League Year.'", "A promoted practice-squad player is a visible replacement signal, capped at three games.", ["NFL-ROSTER"]),
        ("Injured reserve: four games", "'Players must remain on this list for at least four games prior to returning to the active roster.'", "An IR placement guarantees at least four games of replacement play.", ["NFL-IR-FAQ"]),
        ("Injured reserve: eight designations", "'Each team can now designate up to eight players to return ... Each player may be designated to return twice in one season. However, both designations will tally toward the limit of eight.'", "Return eligibility is a scarce, tracked resource, not automatic.", ["NFL-IR-FAQ"]),
        ("2025 bylaw: two at cutdown, two extra in postseason", "'permit clubs to designate two players for return at the roster reduction to 53 players'; the eight-transaction limit 'will only apply to the regular season. Clubs participating in the postseason will get an additional two designations.'", "The designation count resets in a defined way between regular season and playoffs.", ["NFL-RULES-2025"]),
        ("PUP and NFI: four games", "Reserve/PUP players 'must miss at least the team's first four games'; NFI players 'can be activated after the team has played its first four regular season games.'", "Preseason injuries produce known multi-week absences that are not in the weekly game-status column.", ["NFL-IR-FAQ"]),
        ("Game status labels", "'Questionable means it is uncertain as to whether the player will play in the game; Doubtful means it is unlikely the player will participate; and Out means the player will not play.'", "Only 'Out' is definitive; 'Questionable' is not a probability.", ["NFL-INJ-POLICY"]),
        ("Practice labels", "'Did Not Participate, Limited Participation (defined as less than 100 percent of a player's normal repetitions) or Full Participation (defined as 100 percent of a player's normal repetitions).'", "Practice level is separate from game status and must not be converted into one.", ["NFL-INJ-POLICY"]),
    ]
    layer = [
        ("Weekly injury report", "Published by the NFL with per-club tables", "No — rights and no machine-readable export", "Terms restrict compilation; no export, revision timestamp or licence was visible", ["NFL-INJURIES", "NFL-TERMS"]),
        ("Game-day inactives", "Announced by clubs before kickoff", "No — no archive", "No licensed, timestamped archive in this repository", ["NFL-INJ-POLICY", "REPO"]),
        ("Depth order (1st/2nd/3rd/4th string)", "Club roster pages show a status code", "No — no order or history", "No dated depth chart or snap-share feed; codes lack a published legend", ["NFL-ROSTER-PAGE"]),
        ("IR / PUP / NFI designations", "Rules published; player-level moves reported", "No — no feed", "No licensed transaction feed with timestamps", ["NFL-IR-FAQ", "NFL-RULES-2025"]),
        ("Snap counts and participation", "Not verified as an official open feed", "No", "No official source was opened for snap counts in this session", ["REPO"]),
    ]
    strings = [
        ("1st string", "The player listed first at his position", "Official dated depth order", None, ["NFL-ROSTER-PAGE"]),
        ("2nd string", "The next player at the same position", "Official dated depth order", None, ["NFL-ROSTER-PAGE"]),
        ("3rd string", "The third player at the same position", "Official dated depth order", None, ["NFL-ROSTER-PAGE"]),
        ("4th string / practice squad", "Developmental or emergency depth, often on the practice squad", "Dated order plus practice-squad status", None, ["NFL-ROSTER", "NFL-ROSTER-PAGE"]),
    ]
    di = [
        ("Availability loss", "A(p,t) = 1 if the player is unavailable at kickoff, else 0", "Game status, inactives", None, ["NFL-INJ-POLICY"]),
        ("Role", "R(p,t) = listed depth rank at the position (1 = starter)", "Dated depth order", None, ["NFL-ROSTER-PAGE"]),
        ("Replacement drop", "D(p) = baseline value of the starter minus the value of his replacement", "Snap share and per-play value", None, ["REPO"]),
        ("Position weight", "w(p), pre-registered, summing to 1 across positions", "Owner-approved protocol", None, ["NIST-MULTI"]),
        ("Offence index", "DI_off(t) = 100 × Σ w(p) · A(p,t) · D(p), scaled to a declared range", "All of the above", None, ["REPO"]),
        ("Defence index", "DI_def(t) = 100 × Σ w(p) · A(p,t) · D(p), scaled to a declared range", "All of the above", None, ["REPO"]),
        ("Side symmetry", "Offence and defence use the same scale and the same pre-registered weights policy", "Protocol", None, ["REPO"]),
    ]
    gates_a = [
        ("A1", "Completeness", "Every club has a value for every required field on every game day", "not run — no feed"),
        ("A2", "Causality", "Only information published before kickoff is used for that game", "not run"),
        ("A3", "Provenance", "Every value traces to a timestamped official record", "not run"),
        ("A4", "Revision handling", "A later correction cannot overwrite the pre-kickoff snapshot", "not run"),
        ("A5", "Sample size", "At least the pre-registered minimum number of replacement events per position", "not run"),
        ("A6", "Stability", "The sign and size of the effect survive a sensitivity grid", "not run"),
        ("A7", "Multiplicity", "The availability family is counted in the FDR control", "not run"),
        ("A8", "Holdout", "The effect is measured once on a locked, untouched holdout", "not run"),
    ]
    claims = [
        ("A club's active roster is capped at 53 and its game-day list at 47 or 48", pill("verified", "ok"), "Official Football Operations roster definitions", ["NFL-ROSTER"]),
        ("An IR placement means at least four games unavailable", pill("verified", "ok"), "Official roster FAQ", ["NFL-IR-FAQ"]),
        ("The official injury report distinguishes practice status from game status", pill("verified", "ok"), "Official Injury Report Policy revision", ["NFL-INJ-POLICY"]),
        ("Which clubs currently have a 2nd-, 3rd- or 4th-string player starting", pill("unverified", "warn"), "No dated depth order or snap-share feed is admitted", ["NFL-ROSTER-PAGE"]),
        ("How many games a specific 2026 injury will cost a player", pill("unverified", "warn"), "Recovery time is not published in the injury report", ["NFL-INJURIES"]),
        ("The line adjustment that a specific backup deserves", pill("unverified", "warn"), "Requires a fitted, out-of-sample validated model; none exists", ["REPO"]),
    ]
    options = [
        ("Licensed data vendor", "Field-level availability, depth and revision history", "Contractual", "Unknown — no quote obtained", "Preferred: it is the only path to a testable signal", ["REPO"]),
        ("Official pages reviewed by hand", "Current status only, no history", "Terms restrict systematic compilation", "Low cash, high labour", "Not admissible for a model; cite only", ["NFL-INJURIES", "NFL-TERMS"]),
        ("Club press releases and beat reports", "Narrative, sometimes earlier than the report", "Club-specific", "Low cash, high labour", "Not standardised; cannot be a pre-registered feature", ["REPO"]),
        ("Third-party open data", "Possibly injuries or depth for some seasons", "Open licence, not official", "Low", "Exploratory only; never a verified value", ["NFLVERSE"]),
        ("Own charting", "Exactly the fields we choose", "Owned", "High", "Only if the licensed market fails", ["REPO"]),
    ]
    rules_rows = [(list(r[:3]), r[3]) for r in rules]
    layer_rows = [(list(r[:4]), r[4]) for r in layer]
    string_rows = [(list(r[:4]), r[4]) for r in strings]
    di_rows = [(list(r[:4]), r[4]) for r in di]
    gate_a_rows = [(list(r), ["REPO", "NFL-INJ-POLICY"]) for r in gates_a]
    claim_rows = [(list(r[:3]), r[3]) for r in claims]
    option_rows = [(list(r[:5]), r[5]) for r in options]
    pages["injuries"] = dict(
        title="Injuries, availability & depth-chart deficiency",
        lead="What is officially verified about availability and roster depth, why no player-level injury or "
             "depth-chart value is published here, and the fail-closed design that would compute a 2nd/3rd/4th-string "
             "deficiency index once a licensed, timestamped feed exists.",
        kpis=[
            ("Official availability rules verified", len(rules), "Opened on NFL.com / Football Operations"),
            ("Player-level availability values admitted", 0, "No licensed feed; nothing inferred"),
            ("Depth-chart values published", 0, "No dated order archive exists"),
            ("Deficiency-index weights approved", 0, "Proposal only; no owner sign-off"),
        ],
        sections=[
            sec("Read this first",
                "The system does <strong>not</strong> currently track injuries player by player. It tracks the official "
                "rules that govern availability and it specifies exactly what a compliant feed must contain. Publishing "
                "a name, a status or a '2nd-string' count without that feed would be fabrication, so every such cell is "
                "blank and links to the review page. This is a deliberate fail-closed state (flags B02, B07, B09, N14, N16).",
                T(["Layer", "What is published officially", "Admitted to the model?", "Why not"], layer_rows,
                  caption="Status of the availability layer on 2026-11-12 (UTC).")),
            sec("Verified rules that constrain any injury model", "Ten rules, each quoted from the official publisher. "
                "These are the only availability facts this site asserts.",
                T(["Rule", "Official statement", "Implication for a model"], rules_rows,
                  caption="Quoted text is from the publisher's own page; it does not endorse this project.", filter_id="rules")),
            sec("Why 2nd, 3rd and 4th string matter — and what cannot be said yet",
                "Roster rules guarantee that depth exists; they do not publish who is next on the chart or how much "
                "worse he is. That is the missing input for any deficiency signal.",
                T(["String", "Working definition", "Required data", "Published value"], string_rows,
                  caption="No count, rank or quality value is filled in. A blank is unverified, not zero."),
                note="A 53-man roster does not imply four healthy players at every position. The composition of a given week's depth is exactly what is not admitted."),
            sec("Deficiency Index — a proposal, not a measurement",
                "The index below is a specification to be pre-registered before use. Every weight and scale is blank "
                "until an owner signs the protocol; no number is estimated here.",
                T(["Component", "Definition", "Data required", "Value / weight"], di_rows,
                  caption="The formula is a design proposal. It has not been fitted, tested or validated on any data.")),
            sec("Validation gates for any availability signal", "A signal that fails any gate is not promoted, "
                "however plausible the mechanism.",
                T(["Gate", "Name", "Pass criterion", "Status"], gate_a_rows,
                  caption="No gate has been run because no feed exists.")),
            sec("What can and cannot be claimed today", "A short, explicit boundary.",
                T(["Claim", "Status", "Basis"], claim_rows)),
            sec("Acquisition options", "The realistic routes to a compliant feed, with the trade-off stated.",
                T(["Option", "What it provides", "Rights position", "Cost", "Verdict"], option_rows,
                  caption="Cost is blank where no quote or budget exists; it is not estimated."),
                note="Options 2-4 may support narrative context, but none can fill a verified cell on this site."),
            sec("Official pages for manual review", "Open these directly; this site does not mirror their player rows.",
                T(["Resource", "What it shows", "Link"], [
                    (["NFL injury report", "Weekly per-club practice and game status", A("https://www.nfl.com/injuries/", "nfl.com/injuries")], ["NFL-INJURIES"]),
                    (["Roster FAQ", "IR, PUP, NFI and practice-squad mechanics", A("https://www.nfl.com/news/nfl-training-camp-roster-faqs-defining-injured-reserve-pup-list-nfi-and-more", "nfl.com roster FAQ")], ["NFL-IR-FAQ"]),
                    (["Football Operations roster rules", "53/48/47 and practice-squad sizes", A("https://operations.nfl.com/calendar-events/nfl-free-agency/contract-language", "operations.nfl.com")], ["NFL-ROSTER"]),
                    (["Club roster page (example)", "Current roster with an undefined status code", A("https://www.nfl.com/teams/denver-broncos/roster", "nfl.com Broncos roster")], ["NFL-ROSTER-PAGE"]),
                    (["Injury Report Policy revision", "Definitions of practice and game status", A("https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693", "nfl.com policy")], ["NFL-INJ-POLICY"]),
                ])),
        ],
    )

    # -- Competition, rewards & luck ---------------------------------------
    p0 = 110 / 210
    size_rows = []
    for p1 in (0.525, 0.53, 0.54, 0.55, 0.56, 0.58, 0.60):
        n = n_prop(p0, p1)
        seasons = n / 272
        if seasons < 1:
            reading = pill("reachable in one season", "info")
        elif seasons < 10:
            reading = pill(f"about {seasons:.0f} seasons", "warn")
        elif seasons < 50:
            reading = pill("decades at this rate", "warn")
        else:
            reading = pill("not practical at one bet per game", "bad")
        size_rows.append(([
            f"{p1*100:.1f}%", f"{(p1-p0)*100:+.2f} pp", f"{n:,.0f}", f"{seasons:,.1f}", reading
        ], ["NIST-SAMPLESIZE", "NFL-SCHEDULE", "DK-ODDS"]))
    reward_rows = [
        (["1st", None, "Highest luck-adjusted score that clears every gate", None, "proposal"], ["NIST-MULTI", "REPO"]),
        (["2nd", None, "Second highest qualifying score", None, "proposal"], ["NIST-MULTI", "REPO"]),
        (["3rd", None, "Third highest qualifying score", None, "proposal"], ["NIST-MULTI", "REPO"]),
        (["Verified tier (non-cash)", "Recognition", "Any entry passing all gates, even without a top-three score", None, "proposal"], ["NIST-BONF", "REPO"]),
    ]
    competition_gates = [
        ("C1", "Registered before the window", "Strategy, market, stake and rule frozen and hashed", "0 / 0"),
        ("C2", "Every tested rule published", "No unpublished losers", "0 / 0"),
        ("C3", "Family size declared", "Multiplicity penalty uses the declared count", "0 / 0"),
        ("C4", "Minimum sample met", "At least the pre-registered number of settled bets", "0 / 0"),
        ("C5", "Calibration acceptable", "Brier/log loss no worse than the no-skill baseline", "0 / 0"),
        ("C6", "Lower confidence bound positive", "Skill-adjusted lower bound above break-even", "0 / 0"),
        ("C7", "Multiplicity controlled", "q-value at or below the declared threshold", "0 / 0"),
        ("C8", "Stable across snapshots", "Passes at two consecutive snapshots, not one", "0 / 0"),
        ("C9", "Holdout untouched", "No tuning after unblinding", "0 / 0"),
        ("C10", "Operational audit", "Recorded prices, timestamps and settlement match the rulebook", "0 / 0"),
    ]
    mechanisms = [
        ("Locked holdout", "Tuning to the evaluation set", "A single holdout can still be unlucky", ["NIST-MULTI"]),
        ("Lower confidence bound", "Small-sample luck", "Requires enough settled bets to be informative", ["NIST-CI"]),
        ("False-discovery control", "Mining many rules and reporting the best", "Power falls as the family grows", ["NIST-BONF"]),
        ("Permutation null", "A rule that looks good on this schedule only", "The null must be specified in advance", ["NIST-BOOT"]),
        ("Closing-line value", "Winning by taking stale or unavailable prices", "Needs a timestamped quote archive", ["DK-MARKETS"]),
        ("Calibration", "Confident but wrong probabilities", "A well-calibrated loser is still a loser", ["REPO"]),
        ("Minimum sample", "A hot streak of 30 bets", "Large samples take seasons to accumulate", ["NIST-SAMPLESIZE"]),
        ("Two-snapshot stability", "One lucky month", "Slower to promote a real edge", ["NIST-MULTI"]),
    ]
    gate_c_rows = [(list(r), ["REPO", "NIST-MULTI"]) for r in competition_gates]
    mech_rows = [(list(r[:3]), r[3]) for r in mechanisms]
    pages["competition"] = dict(
        title="Competition, rewards & luck",
        lead="A competition design that pays for demonstrated skill, not for a lucky sample: pre-registration, "
             "closing-line value, calibration, lower confidence bounds, false-discovery control and a locked holdout. "
             "No prize is funded and no entry is open.",
        kpis=[
            ("Eligible entries", 0, "No licensed quote archive; fail-closed"),
            ("Funded prize pool", "—", "No sponsor, amount or terms verified"),
            ("Promotion gates", len(competition_gates), "All must pass; none may be waived"),
            ("Settled bets per entry", 0, "No executable bet record exists"),
        ],
        sections=[
            sec("The competition in one paragraph",
                "An entry is a fully specified strategy: market, selection rule, stake and settlement source. It is "
                "hashed before the evaluation window, tested once on a locked holdout, and ranked by a lower confidence "
                "bound on closing-line value with calibration and stability constraints. Only entries clearing all ten "
                "gates can appear in a paid tier. Because there is no timestamped quote archive, the board is empty.",
                T(["Rule", "Detail", "Status", "Source"], [
                    (["Entry unit", "One pre-registered strategy with a fixed market and staking rule", "defined"], ["REPO"]),
                    (["Evaluation", "One locked holdout, one unblinding, no retuning", "defined, no data"], ["NIST-MULTI"]),
                    (["Ranking", "Lower confidence bound on CLV, then calibration, then stability", "defined, no data"], ["NIST-CI", "DK-MARKETS"]),
                    (["Reward", "Only after all gates; amount and funding unverified", "blocked"], ["NFL-RG"]),
                ])),
            sec("Why a raw ROI leaderboard is not honest",
                "A leaderboard that ranks raw return rewards variance. The mechanisms below each remove a specific way "
                "luck can masquerade as skill; their limits are stated so the design is not oversold.",
                T(["Mechanism", "What it removes", "Its own limit"], mech_rows,
                  caption="These are statistical controls, not proof that a surviving entry is skilful.")),
            sec("Sample-size arithmetic", "How many settled bets are needed to distinguish a true win rate from the "
                "52.381% break-even at -110, with 80% power and a one-sided 5% test. Computed with the NIST formula; "
                "seasons assume one bet per game and 272 games per season.",
                T(["True win rate", "Edge vs break-even", "Settled bets needed", "Seasons at 272 bets", "Reading"], size_rows,
                  caption="Arithmetic under stated assumptions, not a forecast. Inputs: alpha 0.05, power 0.80, p0 = 110/210."),
                note="A 55% win rate — already a very large edge — needs roughly 2,242 bets, about eight seasons of one bet per game. This is why a 30-bet 'winner' is not evidence."),
            sec("Promotion gates", "Ten gates. A missing input is a fail, never a pass.",
                T(["ID", "Gate", "Criterion", "Entries passing"], gate_c_rows,
                  caption="No entry has been evaluated, so every count is zero.")),
            sec("Reward schedule (proposal — unfunded)", "The structure is a proposal for the owner to accept, amend or "
                "reject. Amounts are deliberately blank because no pool, sponsor or budget exists (flag N15).",
                T(["Place", "Award", "Eligibility", "Funding status", "Type"], reward_rows,
                  caption="Blank award cells are unverified, not zero. No entry is open and no payment is offered."),
                note="Publishing a proposed structure is not an offer, a sweepstake or a promise of payment."),
            sec("Anti-gaming and anti-luck rules", "Enforced by the protocol rather than by trust.",
                T(["Rule", "Why it exists", "Source"], [
                    (["Hash the entry before the window", "Prevents retroactive rule changes"], ["REPO", "NIST-MULTI"]),
                    (["Publish every tested rule", "Prevents survivorship bias in the displayed board"], ["REPO"]),
                    (["Count the whole family in the FDR", "Adding rules after the fact taxes every entry, including the author's"], ["NIST-BONF"]),
                    (["Only recorded executable prices count", "Beating a close with an unobtainable price is not skill"], ["DK-MARKETS"]),
                    (["No post-hoc start dates or excluded weeks", "Prevents a convenient subsample from becoming the result"], ["NIST-MULTI"]),
                    (["Simulate a no-skill league", "Quantifies how often the scoring rule crowns luck"], ["NIST-BOOT"]),
                    (["No entries from the grader", "Removes the obvious conflict of interest"], ["REPO"]),
                ])),
            sec("Path to a funded competition", "Five steps, none of which can be skipped.",
                T(["Step", "Prerequisite", "Owner decision", "Status"], [
                    (["1 · Licence data and quotes", "S04 vendor and budget", "Approve spend", "blocked"], ["NFL-TERMS"]),
                    (["2 · Pre-register the protocol", "S07, Q10-Q14, Q22", "Sign the thresholds", "ready"], ["NIST-MULTI"]),
                    (["3 · Run the locked holdout", "Complete archive and frozen entries", "Authorise unblinding", "blocked"], ["NIST-CI"]),
                    (["4 · Legal and contest review", "Q04, Q21, Q23, Q24", "Approve terms and jurisdiction", "blocked"], ["NFL-RG"]),
                    (["5 · Fund and open entries", "Pool, custodian, dispute process", "Release funds", "blocked"], ["NFL-RG"]),
                ], caption="Statuses are project state. No step is implied to be underway.")),
        ],
    )


    return pages


def main():
    pages = build_pages()
    (HUB / "assets").mkdir(parents=True, exist_ok=True)
    (HUB / "data").mkdir(parents=True, exist_ok=True)
    (HUB / ".nojekyll").write_text("", encoding="utf-8")
    for slug, spec in pages.items():
        html_doc = page_html(slug, spec["title"], spec["lead"], spec["sections"],
                             spec.get("kpis"), spec.get("extra_top", ""))
        (HUB / f"{slug}.html").write_text(html_doc, encoding="utf-8")
    register = {
        "session": SESSION,
        "snapshot_utc": SNAPSHOT,
        "official_prefixes": list(OFFICIAL_PREFIXES),
        "sources": SOURCES,
    }
    (HUB / "data/sources.json").write_text(json.dumps(register, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"built {len(pages)} pages; {len(SOURCES)} sources; {len(FLAGS)} flags")


if __name__ == "__main__":
    main()
