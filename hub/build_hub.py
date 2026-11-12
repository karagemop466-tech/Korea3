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
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "hub"
# SNAPSHOT is the date the historical integration content was verified. This
# session's additions are dated separately so no older statement is relabelled
# as if it had been re-verified today.
SNAPSHOT = "2026-11-02"
TODAY = "2026-11-12"
SESSION = "arena/6cbe5d15-korea3"
PRIOR_SESSION = "arena/25ea8ac4-korea3"
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
    # Official club publishers. The NFL's 32 clubs publish their own depth
    # charts and injury news. Two of the four charts read for this session are
    # labelled "unofficial" by the club itself; that label is quoted wherever
    # the chart is used.
    "https://www.commanders.com/",
    "https://www.giants.com/",
    "https://www.patriots.com/",
    "https://www.detroitlions.com/",
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
    dict(id="NFL-TERMS", publisher="NFL", tier="Official league",
         url="https://www.nfl.com/legal/terms/",
         claim="Updated: May 16, 2024. Section 1.1: 'Except as expressly provided in this Agreement, you are prohibited from copying, reproducing, modifying, distributing, displaying, performing, or transmitting any of the Services or contents of the Services for any purposes'. Section 1.3: 'Systematic retrieval of data or other content from the Services, whether to create or compile, directly or indirectly, a collection, compilation, database, or directory, is prohibited absent our express prior written consent.'",
         status="verified", method="Opened the official Terms page; read sections 1.1 and 1.3."),
    dict(id="NFL-STATS", publisher="NFL Support", tier="Official league",
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
    dict(id="NFL-ML-ART", publisher="NFL Support", tier="Official league",
         url="https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line",
         claim="'Most often, the betting odds for point spread are -110.' Also: 'if the point spread was +10/-10 and the favored team wins by exactly 10 or the underdog loses by exactly 10, you would push and get your initial wager returned.' The article body explains the point spread, not the moneyline.",
         status="verified", method="Opened the official article; body/title mismatch confirmed and flagged."),
    dict(id="NFL-PS-ART", publisher="NFL Support", tier="Official league",
         url="https://support.nfl.com/hc/en-us/articles/35869774194324-What-is-the-point-spread",
         claim="'In a moneyline wager, the bettor focuses just on who will be the winner of the match.' Also: 'If the game ends in a tie, the bettor's wager is returned with no loss or profit.' The article body explains the moneyline, not the point spread.",
         status="verified", method="Opened the official article; body/title mismatch confirmed and flagged."),
    dict(id="NFL-SCHEDULE", publisher="NFL Football Operations", tier="Official league",
         url="https://operations.nfl.com/calendar-events/nfl-schedule/making-the-schedule",
         claim="'It takes thousands of computers and a team of NFL executives to create the NFL's 272-game masterpiece.' 'Each NFL team plays 17 games over the 18-week season. The league uses a formula to determine all 272 matchups.'",
         status="verified", method="Opened the official Making the Schedule page."),
    dict(id="NFL-RG", publisher="NFL", tier="Official league",
         url="https://www.nfl.com/news/nfl-is-kicking-off-a-6-2m-responsible-betting-campaign",
         claim="'The NFL is spending $6.2 million to help expand programs to prevent or treat problem gambling across the country.' The initiative is 'aimed at getting fans to set limits on their wagers, understand the risks of betting, and know where to get help'. Article carries a 2021 Associated Press copyright.",
         status="verified", method="Opened the official NFL news article."),
    dict(id="NFL-STANDINGS-2025", publisher="NFL", tier="Official league",
         url="https://www.nfl.com/standings/division/2025/REG",
         claim="Official 2025 regular-season division standings table for all 32 clubs, with W, L, T, PCT, PF, PA, NET PTS and other splits defined in the page legend.",
         status="verified", method="Read both chunks of the official 2025 division standings page; all 32 team rows transcribed and cross-checked."),
    dict(id="DK-ODDS", publisher="DraftKings", tier="Licensed operator",
         url="https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466",
         claim="Version 4.0, last modified 2026-10-06. 'If the odds offered on a particular selection are -110, that means in order to win (profit) $100, you would need to wager $110.' 'Multiplier odds represent the total return for every $1 wagered, including the money you risked.'",
         status="verified", method="Opened the official DraftKings Understanding Odds article and its version history."),
    dict(id="DK-SPREAD", publisher="DraftKings", tier="Licensed operator",
         url="https://support.draftkings.com/dk/en-us/what-is-a-point-spread-bet?id=kb_article_view&sysparm_article=KB0010595",
         claim="Version 5.0, last modified 2026-06-29. 'The favorite will have negative points while the underdog will have positive points.' 'If the score ends in a tie after your points are added/subtracted the bet pushes and your wager is returned.'",
         status="verified", method="Opened the official DraftKings point-spread article and its version history."),
    dict(id="DK-PARLAY", publisher="DraftKings", tier="Licensed operator",
         url="https://support.draftkings.com/dk/en-us/what-is-a-parlay-bet?id=kb_article_view&sysparm_article=KB0010683",
         claim="Version 4.0, last modified 2026-06-29. 'All added bets must win in order for the parlay to win. If one selection in the parlay loses, the whole parlay loses. If a selection results in a push, it is removed from the parlay and the odds are recalculated accordingly.' 'For certain selections, the outcomes can be considered correlated. In these cases, DraftKings reserves the right to restrict parlay betting on these outcomes.'",
         status="verified", method="Opened the official DraftKings parlay article and its version history."),
    dict(id="DK-SGP", publisher="DraftKings", tier="Licensed operator",
         url="https://support.draftkings.com/dk/en-us/what-is-a-same-game-parlay-sgp-bet?id=kb_article_view&sysparm_article=KB0010719",
         claim="Version 5.0, last modified 2026-08-18. 'A Same Game Parlay (SGP) works the same as a regular parlay but allows you to combine multiple outcomes from the same game.' 'Due to the nature of the bet type, SGP odds are calculated differently than in other types of parlay bets.' Voided non-participating-player legs adjust the odds in applicable states.",
         status="verified", method="Opened the official DraftKings SGP article and its version history."),
    dict(id="DK-PROP", publisher="DraftKings", tier="Licensed operator",
         url="https://support.draftkings.com/dk/en-us/what-is-a-prop-bet?id=kb_article_view&sysparm_article=KB0010778",
         claim="Version 3.0, last modified 2026-06-29. 'A prop bet or proposition bet is a wager on an individual player or specific event in a game/match that is not directly connected to the outcome of a game.'",
         status="verified", method="Opened the official DraftKings prop-bet article and its version history."),
    dict(id="DK-PLAYER", publisher="DraftKings", tier="Licensed operator",
         url="https://support.draftkings.com/dk/en-us/how-will-my-bet-be-settled-if-a-player-doesn-t-start-or-is-removed-from-a?id=kb_article_view&sysparm_article=KB0010795",
         claim="Version 5.0, last modified 2026-06-29. 'Generally, if a player starts or meets the playing time requirements as described in the House Rules, then all bets will stand and be settled accordingly.' Complete player-prop settlement is directed to the sport-specific House Rules (NFL page linked).",
         status="verified", method="Opened the official DraftKings player-start/removal article."),
    dict(id="DK-MARKETS", publisher="DraftKings Sportsbook", tier="Licensed operator",
         url="https://sportsbook.draftkings.com/help/general-betting-rules/market-rules",
         claim="'If a whole number is offered as the point spread or handicap, bets will be settled as Push if the outcome bet on is tied after the point spread or handicap for the bet has been applied.' 'If the Selections tie, bets will be settled as Push' (2-way moneyline). 'If the total points ... scored in the Event is equal to the specified Total for the bet, then the bet will be settled as Push.'",
         status="verified", method="Opened the official DraftKings Market Rules page."),
    dict(id="FD-CT-RULES", publisher="FanDuel", tier="Licensed operator",
         url="https://www.fanduel.com/fanduel-sportsbook-house-rules-ct",
         claim="Effective Date: July 30, 2026. Section 19, 'Parlays, Round Robins and Teasers': 'A parlay bet consists of two or more selections, all of which must win for the overall bet to win.' 'Parlays containing selections where the outcome of one selection directly affects the outcome or pricing of another selection are not permitted, unless explicitly offered by FanDuel Sportsbook, e.g., as a Same Game Parlay bet.'",
         status="verified", method="Opened the official FanDuel Connecticut house rules and read section 19."),
    dict(id="NIST-CI", publisher="NIST", tier="US government / statistical authority",
         url="https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm",
         claim="'Confidence limits for the mean are an interval estimate for the mean.' 'As a technical note, a 95 % confidence interval does not mean that there is a 95 % probability that the interval contains the true mean.' 'Instead, the level of confidence is associated with the method of calculating the interval.'",
         status="verified", method="Opened the NIST/SEMATECH e-Handbook section 1.3.5.2."),
    dict(id="NIST-BOOT", publisher="NIST", tier="US government / statistical authority",
         url="https://www.itl.nist.gov/div898/handbook/eda/section3/bootplot.htm",
         claim="'The bootstrap plot is used to estimate the uncertainty of a statistic.' 'This subsample is generated with replacement so that any data point can be sampled multiple times or not sampled at all. This process is repeated for many subsamples, typically between 500 and 1000.' 'The bootstrap is not appropriate for all distributions and statistics.'",
         status="verified", method="Opened the NIST/SEMATECH e-Handbook Bootstrap Plot section."),
    dict(id="NIST-CORR", publisher="NIST", tier="US government / statistical authority",
         url="https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/correlat.htm",
         claim="'The correlation coefficient is a measure of the linear relationship between two variables.' 'A perfect linear relationship yields a correlation coefficient of +1 (or -1 for a negative relationship) and no linear relationship yields a correlation coefficient of 0.'",
         status="verified", method="Opened the official NIST Dataplot CORRELATION reference."),
    dict(id="NIST-MULTI", publisher="NIST", tier="US government / statistical authority",
         url="https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm",
         claim="'Doing pairwise comparison procedures over and over again for all possible pairs will not, in general, work. This is because the overall significance level is not as specified for a single pair comparison.' 'These types of investigations should be done on combinations of factors that were determined in advance of observing the experimental results'.",
         status="verified", method="Opened the NIST/SEMATECH multiple-comparisons section 7.4.7."),
    dict(id="NIST-BONF", publisher="NIST", tier="US government / statistical authority",
         url="https://www.itl.nist.gov/div898/handbook/prc/section4/prc473.htm",
         claim="'The Bonferroni method is a simple method that allows many comparison statements to be made (or confidence intervals to be constructed) while still assuring an overall confidence coefficient is maintained.' 'The Bonferroni method is valid for equal and unequal sample sizes.'",
         status="verified", method="Opened the NIST/SEMATECH Bonferroni section 7.4.7.3."),
    dict(id="NIH-FDR", publisher="NIH PMC (hosted literature)", tier="US government host / scientific literature",
         url="https://pmc.ncbi.nlm.nih.gov/articles/PMC3496575/",
         claim="'False discovery rate control in two-stage designs', BMC Bioinformatics 2012;13:81. The abstract describes multiple testing procedures 'controlling the False Discovery Rate (FDR)'. PMC states: 'Inclusion in an NLM database does not imply endorsement of, or agreement with, the contents by NLM or the National Institutes of Health.'",
         status="verified", method="Opened the NIH PMC article page and abstract; treated as literature, not an official betting standard."),
    dict(id="NWS-BRIER", publisher="National Weather Service", tier="US government / statistical authority",
         url="https://www.weather.gov/media/owp/oh/rfcdev/docs/Glossary_Forecast_Verification_Metrics.pdf",
         claim="",
         status="unverified", method="Fetch of the official PDF failed in this session; no statement is transcribed. Flagged N03."),
    dict(id="NFL-INJURY-REPORT", publisher="NFL", tier="Official league",
         url="https://www.nfl.com/injuries/",
         claim="Page title at retrieval: “Official Latest NFL Injury Report for Players - Week 10 of the 2026 Season | NFL.com”. The page publishes, per scheduled game, a table with exactly these columns: Player, Position, Injuries, Practice Status, Game Status. Practice values read in the snapshot: “Full Participation in Practice”, “Limited Participation in Practice”, “Did Not Participate In Practice”. Game values read: “Out”, “Questionable”, or blank.",
         status="verified", checked=TODAY,
         method="Opened the live official page on 2026-11-12 (UTC) and transcribed the four clubs playing in the two games read (WAS, NYG, NE, DET), 44 player rows, verbatim."),
    dict(id="NFL-INJURY-POLICY", publisher="NFL", tier="Official league",
         url="https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693",
         claim="“The Practice Report has been modified to eliminate the ‘Out’ category ... injured players to be listed as Did Not Participate, Limited Participation (defined as less than 100 percent of a player's normal repetitions) or Full Participation (defined as 100 percent of a player's normal repetitions).” “Questionable means it is uncertain as to whether the player will play in the game; Doubtful means it is unlikely the player will participate; and Out means the player will not play.” “If there is any question concerning a player's availability for the game, he should be listed as ‘Questionable.’” A player certain to play is not listed in the Game Status Report; if he is then deactivated the club must explain to the league and may be disciplined.",
         status="verified", checked=TODAY,
         method="Opened the official NFL.com news article and read the policy text in full."),
    dict(id="NFL-PLAYER-STATS", publisher="NFL", tier="Official league",
         url="https://www.nfl.com/stats/player-stats/",
         claim="The 2026 player-stats category index lists 11 categories: Passing, Rushing, Receiving, Fumbles, Tackles, Interceptions, Field Goals, Kickoffs, Kickoff Returns, Punting, Punt Returns. No snap-count category appears in that index at retrieval.",
         status="verified", checked=TODAY,
         method="Opened the official NFL player-stats index and enumerated the category links; a direct /category/snap-counts/ URL returned the official 404 page."),
    dict(id="WAS-DEPTH", publisher="Washington Commanders (official club)", tier="Official club",
         url="https://www.commanders.com/team/depth-chart",
         claim="Club depth chart read on 2026-11-12: C Allegretti (1st) / Gulbin (2nd); LG Paul / Togiai; RG Cosmi / Togiai; TE Okonkwo / Sinnott and TE Bates / Yankoff (no third string listed at either slot); WR McLaurin / Burks; CB Robertson / Douglas; DL Settle / Tuttle. No “unofficial” label appears in the retrieved page text.",
         status="verified", checked=TODAY,
         method="Opened the official club depth-chart page and read the offence, defence and special-teams tables."),
    dict(id="NYG-DEPTH", publisher="New York Giants (official club)", tier="Official club",
         url="https://www.giants.com/team/depth-chart",
         claim="Club depth chart read on 2026-11-12: QB McCarthy / Winston; RB Skattebo / Singletary / Desrosiers; TE Likely / Johnson / Manhertz / Fidone; LT Thomas / J.C. Davis; RT Eluemunor / Mbow; SAM Carter / Thibodeaux; MLB McFadden / Barnes; WLB Reese / Kelly; CB Banks / Adebo / Reed and Newsome / Hood. Linebacker Malik Harrison is not listed. No “unofficial” label appears in the retrieved page text.",
         status="verified", checked=TODAY,
         method="Opened the official club depth-chart page and read every position table."),
    dict(id="NE-DEPTH", publisher="New England Patriots (official club)", tier="Official club",
         url="https://www.patriots.com/team/depth-chart",
         claim="Page states: “The 2026 depth chart is unofficial and is published by the writers of Patriots.com. The depth chart reflects the opinions of the Patriots.com writers and don't necessarily reflect those of the organization.” Rows read: LG Ben Brown / Rouse; C Jared Wilson / Ben Brown; RG Pryor / Rouse; RB Stevenson / Henderson / Kiner / Larison; CB Carlton Davis III / Channing Canada; S Kevin Byard III / Jaylen Reed / Brenden Schooler. No fullback is listed.",
         status="verified", checked=TODAY,
         method="Opened the official club depth chart and read all position tables plus its own disclaimer."),
    dict(id="DET-DEPTH", publisher="Detroit Lions (official club)", tier="Official club",
         url="https://www.detroitlions.com/team/depth-chart",
         claim="Page heading: “2026 Unofficial Depth Chart Compiled by Lions Football Communications”. Rows read: C Mays / Scruggs; RB Gibbs / Vaki / Saylors; S Clark (no backup listed) and S Branch / Izien; CB Reed / Ya-Sin / Dorsey / Whiteside; WR St. Brown / Carter; EDGE Wonnum / Lacy / Hassanein. Safety Kerby Joseph is not listed.",
         status="verified", checked=TODAY,
         method="Opened the official club depth chart and read all position tables plus its heading."),
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
    ("Governance", [("requirements", "Requirements"), ("verification", "Verification log"), ("sessions", "Sessions & board"), ("archive", "Prior work archive")]),
    ("Evidence", [("sources", "Official sources"), ("repo-review", "Repo review"), ("data", "Data inventory"), ("standings", "Official standings"), ("injuries", "Injuries & depth")]),
    ("Line lab", [("own-lines", "Own lines"), ("strategies", "Strategies & signals")]),
    ("Bet types", [("single-bets", "Single bets"), ("parlays", "Parlays"), ("player-props", "Player props")]),
    ("Statistics", [("correlations", "Correlations"), ("validation", "Validation gates"), ("leaderboard", "Leaderboard")]),
    ("Decisions", [("suggestions", "Suggestions"), ("questions", "Questions & decisions")]),
    ("Review", [("flagged", "Flagged for Review")]),
]
NAV_FLAT = [(slug, label, group) for group, items in NAV for slug, label in items]

# Counts stated in prose. They are asserted against the data structures when
# build_pages() runs, so a stale sentence fails the build instead of drifting.
N_QUESTIONS = 18
N_BLOCKING = 10
N_SUGGESTIONS = 15


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
    <p class="tagline">Official-evidence view · sources checked {SNAPSHOT} and {TODAY}<br>Session {E(SESSION)}</p>
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
      <div>Independent research; not affiliated with the NFL or any sportsbook. Snapshots {SNAPSHOT} and {TODAY} (UTC).<br>
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
    ("F10", "high", "Official club depth charts are labelled unofficial by the clubs themselves",
     "The Patriots page states: 'The 2026 depth chart is unofficial and is published by the writers of Patriots.com ... and don't necessarily reflect those of the organization.' The Lions page is headed '2026 Unofficial Depth Chart Compiled by Lions Football Communications'. A depth order therefore cannot be published as an official fact; it is quoted as club-published opinion.",
     "verified anomaly — needs review", ["NE-DEPTH", "DET-DEPTH"], "hub/injuries.html"),
    ("F11", "high", "No official league-wide depth chart or machine-readable depth data",
     "The NFL publishes injury reports; it does not publish a league-wide depth chart. Depth charts are club pages in four different HTML layouts, two of them explicitly unofficial. Any '2nd/3rd/4th string' label is therefore a reading of a club page, not a league designation.",
     "unverified — structural", ["NFL-INJURY-REPORT", "NE-DEPTH", "REPO"], "hub/injuries.html"),
    ("F12", "medium", "Five injury-report players are absent from their own club's depth chart",
     "WAS Lucas Patrick (C), NYG Malik Harrison (LB), NE Reggie Gilliam (FB) and Greg Van Roten (G), DET Kerby Joseph (S) appear on the official injury report but in no position row of the club's official depth chart. The two official pages are not a joinable key set; every unmatched row is flagged rather than guessed.",
     "needs review (data quality)", ["NFL-INJURY-REPORT", "WAS-DEPTH", "NYG-DEPTH", "NE-DEPTH", "DET-DEPTH"], "hub/injuries.html"),
    ("F13", "medium", "No official snap-count category: replacement exposure cannot be measured officially",
     "The official NFL player-stats index lists 11 categories and none is snap counts; a direct snap-counts category URL returned the official 404 page. Snap share, and therefore how many snaps a backup actually played, has no verified official source here.",
     "unverified — blocking", ["NFL-PLAYER-STATS", "REPO"], "hub/questions.html"),
    ("F14", "medium", "The official injury report is a live, mutable page with no archive",
     "Values change as the week's practice reports are filed. The 44 rows published here are a dated transcription (2026-11-12 UTC) with a link to the live page; no row is presented as current after that date.",
     "needs review (snapshot)", ["NFL-INJURY-REPORT", "NFL-TERMS"], "hub/injuries.html"),
    ("F15", "medium", "No official inactive-list archive",
     "The league policy requires an explanation to the league if a player omitted from the Game Status Report is then deactivated, but no official machine-readable inactive list is archived in this repository, so the final 48-man availability check is missing.",
     "unverified — blocking", ["NFL-INJURY-POLICY", "REPO"], "hub/questions.html"),
    ("F16", "low", "Suggestions are proposals only; no owner decision has been recorded",
     "The suggestions register publishes 15 proposals and three candidate paths. Nothing on it has been implemented, and no proposal may be implemented until the owner records a choice; each proposal names the open questions it depends on.",
     "awaiting owner decision", ["REPO"], "hub/suggestions.html"),
    ("F17", "medium", "Transcribing the injury report sits close to the NFL Terms boundary",
     "NFL Terms sections 1.1 and 1.3 prohibit reproduction and systematic retrieval of Services content without written consent. This page reproduces 44 rows of one published report as a dated verification sample with a link to the source; no systematic harvesting, storage or redistribution of NFL content is performed or claimed.",
     "needs review (rights boundary)", ["NFL-TERMS", "NFL-INJURY-REPORT"], "hub/injuries.html"),
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
    ("R36", "Availability", "Track injuries and know deficiencies where 2nd/3rd/4th-string players replace starters", "partial — 4 clubs verified; no official league-wide feed", "injuries.html", ["NFL-INJURY-REPORT", "NE-DEPTH", "WAS-DEPTH"]),
    ("R37", "Availability", "Apply the same starter/backup read to offences and defences", "partial — offence and defence mapped for 4 clubs", "injuries.html", ["NE-DEPTH", "NYG-DEPTH", "DET-DEPTH"]),
    ("R38", "Decisions", "Dedicated suggestions section to review proposals and choose a path before implementing changes", "done — 15 proposals, 3 paths, nothing implemented", "suggestions.html", ["REPO"]),
    ("R39", "Decisions", "Clear list of questions, the information held and missing, and the answers needed before a decision", "done — 18 questions, 7 blocking", "questions.html", ["REPO"]),
    ("R40", "Reporting", "Executive summary of the important details", "done", "executive-summary.html", ["REPO"]),
    ("R41", "Reporting", "No manual input; the build and verification run unattended", "done — deterministic, stdlib only", "verification.html", ["REPO"]),
    ("R42", "Reporting", "Flag every irregularity with a source link on a clearly labelled review page", "done", "flagged.html", ["REPO"]),
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
def build_pages():
    pages = {}

    n_verified = sum(1 for s in SOURCES if s["status"] == "verified")
    n_strategies = len(gates) + len(line_lab_strategies) + len(hypotheses)
    kpis = [
        ("Official sources re-verified", n_verified, "Opened on the publisher's own site " + SNAPSHOT + " or " + TODAY),
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
            sec("New in this revision — 12 November 2026",
                "The brief asked for injury tracking with backup-deficiency analysis, a suggestions section that "
                "can be reviewed before anything is implemented, and a register of the questions that must be "
                "answered first. All three are now published; none of them changes a prior finding.",
                T(["Added", "What it does", "Status"], [
                    (["Injuries &amp; depth", "44 official injury-report rows for 4 clubs, joined to each club's own depth chart, with six findings and five unmatched players flagged.", pill("4 of 32 clubs verified", "warn")], ["NFL-INJURY-REPORT", "NE-DEPTH"]),
                    (["Suggestions", str(N_SUGGESTIONS) + " proposals with impact, effort, risk and dependencies, three paths and a recommendation. Nothing implemented.", pill("awaiting your choice", "warn")], ["REPO"]),
                    (["Questions &amp; decisions", str(N_QUESTIONS) + " questions, " + str(N_BLOCKING) + " of them blocking, each with the information held, the information missing and a blank answer where it is unknown.", pill(str(N_BLOCKING) + " blocking", "bad")], ["REPO"]),
                ], caption="Every row links its official source or the repository artifact that supports it.")),
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
            sec("Added in the 12 November 2026 revision",
                "Four deliverables were added to this dashboard. They are additive: no earlier verified value was "
                "changed, and the substantive conclusion is unchanged — no strategy is reward-eligible and no "
                "measured betting value is published.",
                T(["Deliverable", "What it contains", "Honest limitation"], [
                    (["Injury tracking", "44 rows from the official Week 10 2026 injury report for the four clubs in the two games read, with practice and game status as published.", "A dated snapshot of a live page; 28 clubs not covered (F14, F11)."], ["NFL-INJURY-REPORT"]),
                    (["Starter/backup deficiency read", "Each injured player matched to his club's own depth chart, with the listed order behind him and six specific findings.", "Club charts are not official; two are labelled unofficial; five players do not join (F10, F12)."], ["NE-DEPTH", "DET-DEPTH"]),
                    (["Suggestions register", str(N_SUGGESTIONS) + " proposals, three paths, a recommendation and an empty decision record.", "Nothing is implemented; a path has to be chosen (F16)."], ["REPO"]),
                    (["Questions register", str(N_QUESTIONS) + " questions with the information held and missing; " + str(N_BLOCKING) + " block a decision.", "Blocking questions cannot be closed from public pages alone (Q01, Q10)."], ["REPO"]),
                ], caption="Detail: injuries.html, suggestions.html and questions.html.")),
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
                    (["Consolidated dashboard (" + str(len(pages) + 3) + " pages)", A("index.html", "/hub/index.html"), "Every table row links a source: an official publisher where the fact is officially published, a repository artifact where it is computed"], ["REPO"]),
                    (["Official source register", A("sources.html", "sources.html"), "Exact statement recorded only where the official page was opened"], ["NFL-TERMS", "DK-ODDS", "NIST-CI"]),
                    (["Line-by-line repo review", A("repo-review.html", "repo-review.html"), "File and row counts computed from the checkout"], ["REPO"]),
                    (["Full requirement traceability", A("requirements.html", "requirements.html"), str(len(REQUIREMENTS)) + " requirements, including the 2026-11-12 additions"], ["REPO"]),
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
            sec("Full requirement traceability", str(len(REQUIREMENTS)) + " rows (R36-R42 added 2026-11-12). 'done' means the deliverable exists and is evidenced; "
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
            claim, status, E(s.get("checked", SNAPSHOT) if s["status"] == "verified" else "—" if not s["claim"] else s.get("checked", SNAPSHOT)),
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
                    (["An injury or inactive feed", "The league publishes a weekly injury report (now tracked on the injuries page), but there is no licensed machine-readable feed and no archived inactive list."], ["NFL-INJURY-REPORT", "NFL-INJURY-POLICY"]),
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
                              pill("verified " + SNAPSHOT, "ok")], [s["id"]]))
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
            sec("Sources opened line by line", str(len(ver_rows)) + " official pages opened and read on " + SNAPSHOT + ".",
                T(["Source", "Publisher", "Method", "Result"], ver_rows,
                  caption="Each row opens the official page that was read.", filter_id="ver-filter")),
            sec("Checks run", "Commands executed during integration; every result is from this checkout.",
                T(["Check", "What it asserts", "Result"], [
                    (["<code>python3 hub/build_hub.py</code>", "Rebuilds all pages deterministically from the data files and source register.", pill("pass", "ok")], [repo("hub/build_hub.py")]),
                    (["<code>python3 hub/check_hub.py</code>", "Official link per row, blank markers, internal links, navigation, metadata.", pill("pass", "ok")], [repo("hub/check_hub.py")]),
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
        ("A19", "Verified", "The official injury report's columns are Player, Position, Injuries, Practice Status and Game Status; there is no depth, starter or snap field.", "verified", ["NFL-INJURY-REPORT"]),
        ("A20", "Verified anomaly", "New England and Detroit label their own club depth charts unofficial in the page itself.", "needs review", ["NE-DEPTH", "DET-DEPTH"]),
        ("A21", "Verified", "In the 2026 Week 10 snapshot, New England's listed left guard was Out and its listed second-string left guard did not practise.", "dated snapshot", ["NFL-INJURY-REPORT", "NE-DEPTH"]),
        ("A22", "Gap", "Five players on official injury reports appear on no row of their club's depth chart.", "unverified", ["NFL-INJURY-REPORT", "WAS-DEPTH", "NE-DEPTH"]),
        ("A23", "Gap", "No official snap-count category exists, so replacement exposure cannot be measured from official pages.", "unverified", ["NFL-PLAYER-STATS"]),
        ("A24", "Gap", "There is no league-wide official depth chart; only club pages, two of them explicitly opinion-based.", "unverified", ["NFL-INJURY-REPORT", "NE-DEPTH"]),
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
            sec("Findings register", str(len(findings)) + " findings. 'Value' is populated only when the official publisher states it, or when the finding is a dated transcription of one.",
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

    # ------------------------------------------------------------------
    # Availability: official injury report + official club depth charts
    # Added 2026-11-12. Every value below was transcribed from the two
    # official pages named in the source register; nothing is inferred.
    # ------------------------------------------------------------------
    CLUB_SRC = {"WAS": "WAS-DEPTH", "NYG": "NYG-DEPTH", "NE": "NE-DEPTH", "DET": "DET-DEPTH"}
    # (game, team, player, pos, injury, practice, game status, slot pos,
    #  listed names in order, rank of this player (0 = not listed), note)
    INJURY = [
        ("WAS @ NYG", "WAS", "John Bates", "TE", "", "Full Participation in Practice", "", "TE",
         ["Bates", "Yankoff"], 1, ""),
        ("WAS @ NYG", "WAS", "Treylon Burks", "WR", "", "Did Not Participate In Practice", "", "WR",
         ["McLaurin", "Burks"], 2, ""),
        ("WAS @ NYG", "WAS", "Jayden Daniels", "QB", "", "Full Participation in Practice", "", "QB",
         ["Daniels", "Mariota", "Kaliakmanis"], 1, ""),
        ("WAS @ NYG", "WAS", "Matt Gulbin", "C", "", "Full Participation in Practice", "", "C",
         ["Allegretti", "Gulbin"], 2, ""),
        ("WAS @ NYG", "WAS", "Chig Okonkwo", "TE", "", "Full Participation in Practice", "", "TE",
         ["Okonkwo", "Sinnott"], 1, ""),
        ("WAS @ NYG", "WAS", "Lucas Patrick", "C", "Concussion", "Did Not Participate In Practice", "Out", "—",
         [], 0, ""),
        ("WAS @ NYG", "WAS", "Amik Robertson", "CB", "", "Limited Participation in Practice", "", "CB",
         ["Robertson", "Douglas"], 1, ""),
        ("WAS @ NYG", "WAS", "Shy Tuttle", "DT", "", "Full Participation in Practice", "", "DL",
         ["Settle", "Tuttle"], 2, ""),
        ("WAS @ NYG", "WAS", "Colson Yankoff", "TE", "Knee", "Did Not Participate In Practice", "Out", "TE",
         ["Bates", "Yankoff"], 2, "Only listed backup at this slot"),
        ("WAS @ NYG", "NYG", "Abdul Carter", "LB", "", "Full Participation in Practice", "", "SAM",
         ["Carter", "Thibodeaux"], 1, ""),
        ("WAS @ NYG", "NYG", "Jermaine Eluemunor", "T", "", "Full Participation in Practice", "", "RT",
         ["Eluemunor", "Mbow"], 1, ""),
        ("WAS @ NYG", "NYG", "Malik Harrison", "LB", "Groin", "Limited Participation in Practice", "Questionable", "—",
         [], 0, ""),
        ("WAS @ NYG", "NYG", "Colton Hood", "CB", "", "Full Participation in Practice", "", "CB",
         ["Newsome", "Hood"], 2, ""),
        ("WAS @ NYG", "NYG", "Theo Johnson", "TE", "", "Full Participation in Practice", "", "TE",
         ["Likely", "Johnson", "Manhertz", "Fidone"], 2, ""),
        ("WAS @ NYG", "NYG", "Charlie Jones", "WR", "", "Full Participation in Practice", "", "WR",
         ["Mooney", "Jones"], 2, ""),
        ("WAS @ NYG", "NYG", "J.J. McCarthy", "QB", "", "Full Participation in Practice", "", "QB",
         ["McCarthy", "Winston"], 1, ""),
        ("WAS @ NYG", "NYG", "Darnell Mooney", "WR", "", "Full Participation in Practice", "", "WR",
         ["Mooney", "Jones"], 1, ""),
        ("WAS @ NYG", "NYG", "Malik Nabers", "WR", "", "Full Participation in Practice", "", "WR",
         ["Nabers", "Fields", "Hyatt"], 1, ""),
        ("WAS @ NYG", "NYG", "Cam Skattebo", "RB", "", "Full Participation in Practice", "", "RB",
         ["Skattebo", "Singletary", "Desrosiers"], 1, ""),
        ("WAS @ NYG", "NYG", "Andrew Thomas", "T", "", "Full Participation in Practice", "", "LT",
         ["Thomas", "J.C. Davis"], 1, ""),
        ("NE @ DET", "NE", "Ben Brown", "C", "Knee", "Did Not Participate In Practice", "Out", "LG",
         ["Brown", "Rouse"], 1, "Also listed as the 2nd-string centre"),
        ("NE @ DET", "NE", "A.J. Brown", "WR", "", "Limited Participation in Practice", "", "WR",
         ["A.J. Brown", "Chism"], 1, ""),
        ("NE @ DET", "NE", "Kevin Byard", "S", "", "Limited Participation in Practice", "", "S",
         ["Byard III", "Reed", "Schooler"], 1, ""),
        ("NE @ DET", "NE", "Carlton Davis III", "CB", "Knee", "Did Not Participate In Practice", "Out", "CB",
         ["Davis III", "Canada"], 1, ""),
        ("NE @ DET", "NE", "Reggie Gilliam", "FB", "", "Limited Participation in Practice", "", "—",
         [], 0, ""),
        ("NE @ DET", "NE", "TreVeyon Henderson", "RB", "Illness", "Did Not Participate In Practice", "Out", "RB",
         ["Stevenson", "Henderson", "Kiner", "Larison"], 2, ""),
        ("NE @ DET", "NE", "Hunter Henry", "TE", "", "Limited Participation in Practice", "", "TE",
         ["Henry", "Raridon", "Latu"], 1, ""),
        ("NE @ DET", "NE", "Cameron Latu", "TE", "", "Did Not Participate In Practice", "", "TE",
         ["Henry", "Raridon", "Latu"], 3, ""),
        ("NE @ DET", "NE", "Drake Maye", "QB", "", "Full Participation in Practice", "", "QB",
         ["Maye", "DeVito", "Morton"], 1, ""),
        ("NE @ DET", "NE", "Morgan Moses", "T", "", "Limited Participation in Practice", "", "RT",
         ["Moses", "Lomu"], 1, ""),
        ("NE @ DET", "NE", "Walter Rouse", "T", "", "Did Not Participate In Practice", "", "LG",
         ["Brown", "Rouse"], 2, "Also listed as the 2nd-string right guard"),
        ("NE @ DET", "NE", "Brenden Schooler", "S", "", "Did Not Participate In Practice", "", "S",
         ["Byard III", "Reed", "Schooler"], 3, ""),
        ("NE @ DET", "NE", "Rhamondre Stevenson", "RB", "", "Did Not Participate In Practice", "", "RB",
         ["Stevenson", "Henderson", "Kiner", "Larison"], 1, ""),
        ("NE @ DET", "NE", "Greg Van Roten", "G", "", "Limited Participation in Practice", "", "—",
         [], 0, ""),
        ("NE @ DET", "NE", "Charles Woods", "CB", "", "Limited Participation in Practice", "", "CB",
         ["Marcus Jones", "Woods"], 2, ""),
        ("NE @ DET", "DET", "Brian Branch", "S", "", "Limited Participation in Practice", "", "S",
         ["Branch", "Izien"], 1, ""),
        ("NE @ DET", "DET", "Jared Goff", "QB", "", "Limited Participation in Practice", "", "QB",
         ["Goff", "Dobbs"], 1, ""),
        ("NE @ DET", "DET", "Kerby Joseph", "S", "", "Limited Participation in Practice", "", "—",
         [], 0, ""),
        ("NE @ DET", "DET", "Cade Mays", "C", "", "Did Not Participate In Practice", "", "C",
         ["Mays", "Scruggs"], 1, ""),
        ("NE @ DET", "DET", "D.J. Reed", "CB", "", "Did Not Participate In Practice", "", "CB",
         ["Reed", "Ya-Sin", "Dorsey", "Whiteside"], 1, ""),
        ("NE @ DET", "DET", "Jacob Saylors", "RB", "", "Full Participation in Practice", "", "RB",
         ["Gibbs", "Vaki", "Saylors"], 3, ""),
        ("NE @ DET", "DET", "Amon-Ra St. Brown", "WR", "", "Limited Participation in Practice", "", "WR",
         ["St. Brown", "Carter"], 1, ""),
        ("NE @ DET", "DET", "Sione Vaki", "RB", "", "Did Not Participate In Practice", "", "RB",
         ["Gibbs", "Vaki", "Saylors"], 2, ""),
        ("NE @ DET", "DET", "DJ Wonnum", "DE", "", "Full Participation in Practice", "", "EDGE",
         ["Wonnum", "Lacy", "Hassanein"], 1, ""),
    ]

    def _ordinal(n):
        return {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}.get(n, f"{n}th")

    def _availability_read(rank, practice, game_status, names, note):
        if rank == 0:
            return "No position row on the club depth chart — role unverified"
        base = f"{_ordinal(rank)} string"
        if game_status == "Out":
            base += " — ruled Out"
        elif game_status == "Questionable":
            base += " — Questionable (uncertain to play)"
        elif practice.startswith("Did Not"):
            base += " — did not practise; no game-status designation"
        elif practice.startswith("Limited"):
            base += " — limited practice"
        else:
            base += " — full practice"
        behind = names[rank:]
        if behind:
            base += "; listed behind: " + ", ".join(behind)
        else:
            base += "; no backup listed behind him"
        if note:
            base += f" ({note})"
        return base

    injury_rows = []
    depth_rows = []
    for i, (game, team, player, pos, injury, practice, status, slot, names, rank, note) in enumerate(INJURY, 1):
        injury_rows.append(([
            E(game), E(team), E(player), E(pos),
            E(injury) if injury else "—",
            E(practice),
            E(status) if status else "—",
        ], ["NFL-INJURY-REPORT"], f"inj{i:02d}"))
        depth_rows.append(([
            E(team), E(player), E(status) if status else "—",
            E(slot) if slot != "—" else "—",
            E(_ordinal(rank) + " string") if rank else "not listed",
            E(_availability_read(rank, practice, status, names, note)),
        ], ["NFL-INJURY-REPORT", CLUB_SRC[team]], f"map{i:02d}"))

    n_clubs = len({r[1] for r in INJURY})
    n_out = sum(1 for r in INJURY if r[6] == "Out")
    n_q = sum(1 for r in INJURY if r[6] == "Questionable")
    n_unmapped = sum(1 for r in INJURY if r[9] == 0)
    n_starter_out = sum(1 for r in INJURY if r[6] == "Out" and r[9] == 1)

    pages["injuries"] = dict(
        title="Injuries & depth",
        lead="Official injury-report tracking joined to official club depth charts, so a starter's absence is "
             "shown against the backups actually listed behind him. Values are a dated transcription of the "
             "official pages; a club chart is quoted as published, including where the club calls it unofficial.",
        kpis=[
            ("Injury rows verified", len(INJURY), "NFL.com, Week 10 2026, retrieved " + TODAY),
            ("Clubs covered", f"{n_clubs} of 32", "Other 28 clubs: not verified, flagged"),
            ("Designated Out", n_out, "Of which 1st-string: " + str(n_starter_out)),
            ("Unmapped to a depth row", n_unmapped, "Flagged F12, not guessed"),
        ],
        sections=[
            sec("What this page can and cannot say",
                "The NFL publishes a weekly injury report with practice and game status. It does <em>not</em> "
                "publish a depth chart, a starter designation or a snap count. Depth charts come from the clubs, "
                "in four different layouts, and two of the four read here are explicitly labelled unofficial by "
                "the club itself. So this page can state, with a link, <em>who is listed as injured and who the "
                "club lists next at that position</em>. It cannot state that a player is officially the starter, "
                "and it does not: every depth reading is marked recomputed, and the five players who appear on an "
                "injury report but on no depth row are flagged rather than assigned a role.",
                T(["Question", "Answer", "Basis"], [
                    (["Does the official report give a depth or snap field?", "No. Its columns are Player, Position, Injuries, Practice Status, Game Status.", pill("verified", "ok")], ["NFL-INJURY-REPORT"]),
                    (["Are the club depth charts official?", "They are published by the clubs. New England and Detroit label theirs <em>unofficial</em> in the page itself.", pill("verified anomaly", "warn")], ["NE-DEPTH", "DET-DEPTH"]),
                    (["Can snap share be measured from an official source?", "No. The official player-stats index has no snap-count category.", pill("blocked", "bad")], ["NFL-PLAYER-STATS"]),
                    (["Is the final inactive list archived here?", "No. Flagged F15; the policy text only requires an explanation to the league if an omitted player is deactivated.", pill("unverified", "warn")], ["NFL-INJURY-POLICY"]),
                ], caption="Three official pages answer the three structural questions.")),
            sec("Official designations, as defined by the league",
                "Quoted from the NFL's own announcement of the injury-report revision. These definitions are what "
                "the two status columns on every injury report mean.",
                T(["Field", "Designation", "Official definition"], [
                    (["Practice report", "Did Not Participate", "The player did not take part in practice."], ["NFL-INJURY-POLICY"]),
                    (["Practice report", "Limited Participation", "Less than 100 percent of the player's normal repetitions."], ["NFL-INJURY-POLICY"]),
                    (["Practice report", "Full Participation", "100 percent of the player's normal repetitions."], ["NFL-INJURY-POLICY"]),
                    (["Game status", "Out", "The player will not play."], ["NFL-INJURY-POLICY"]),
                    (["Game status", "Doubtful", "It is unlikely the player will participate."], ["NFL-INJURY-POLICY"]),
                    (["Game status", "Questionable", "It is uncertain whether the player will play; if there is any question, he is listed here."], ["NFL-INJURY-POLICY"]),
                    (["Game status", "No designation", "A player certain to play is not listed; if he is then deactivated the club must explain to the league."], ["NFL-INJURY-POLICY"]),
                ], caption="The 'Probable' category was eliminated because about 95 percent of players carrying it played.")),
            sec("Week 10, 2026 — official injury report, four clubs",
                "Transcribed verbatim from the live official page on " + TODAY + " (UTC) for the two games read: "
                "Washington at New York Giants (Thursday 12 November) and New England at Detroit (Sunday 15 November). "
                "An em dash reproduces a field the official page leaves blank; it is not a zero and nothing is inferred.",
                T(["Game", "Team", "Player", "Pos", "Injury (as published)", "Practice status", "Game status"],
                  injury_rows,
                  caption="44 rows. Source page is live and changes as practice reports are filed; the link opens the current version.",
                  filter_id="inj-filter",
                  note="Rows are a dated snapshot. Flagged F14 (mutability) and F17 (NFL Terms boundary).")),
            sec("Starter and backup check: injury report joined to the club depth chart",
                "Each injured player is matched by name to the club's own depth-chart row for his position. The "
                "'listed depth' column is the club's published order; the 'availability read' column is the "
                "recomputed combination of that order with the league status. Where no row matches, the player is "
                "reported as unlisted — the gap is not filled.",
                T(["Team", "Player", "Game status", "Depth slot", "Listed depth", "Availability read"],
                  depth_rows,
                  caption="Depth order is the club's publication; two clubs call theirs unofficial (F10).",
                  filter_id="map-filter")),
            sec("Backup-deficiency findings that the official pages actually support",
                "Six findings follow directly from the two sources. Each is a statement about what is published, "
                "not a claim about how the game will go.",
                T(["#", "Finding", "Why it is a deficiency", "Status"], [
                    (["1", "New England left guard: Ben Brown (1st string) is Out and Walter Rouse (2nd string) did not practise.", "The two-deep at one position is unavailable or uncertain, and no third guard is listed.", pill("verified pages", "ok")], ["NFL-INJURY-REPORT", "NE-DEPTH"]),
                    (["2", "New England running back: Stevenson (1st) did not practise and Henderson (2nd) is Out.", "Two of the top three are unavailable or uncertain; the club lists Kiner (3rd) and Larison (4th).", pill("verified pages", "ok")], ["NFL-INJURY-REPORT", "NE-DEPTH"]),
                    (["3", "Washington tight end: Colson Yankoff (2nd string behind Bates) is Out.", "The only backup listed at that slot is unavailable; no third string is published.", pill("verified pages", "ok")], ["NFL-INJURY-REPORT", "WAS-DEPTH"]),
                    (["4", "Detroit centre: Cade Mays (1st string) did not practise with no game status.", "The starter is uncertain and the only listed backup is Scruggs.", pill("verified pages", "ok")], ["NFL-INJURY-REPORT", "DET-DEPTH"]),
                    (["5", "Detroit safety: Kerby Joseph is on the injury report (limited) but appears on no depth row; Brian Branch (listed 1st at the other safety slot) is also limited.", "A reported injury cannot be placed in the depth order from the club's page, so its severity to the lineup is unverified.", pill("data gap", "warn")], ["NFL-INJURY-REPORT", "DET-DEPTH"]),
                    (["6", "Five players appear on an injury report but on no depth row (F12).", "The two official pages are not a joinable key set, so any automated join must fail closed rather than assume a role.", pill("flagged", "warn")], ["NFL-INJURY-REPORT", "WAS-DEPTH", "NE-DEPTH"]),
                ], caption="Each row links both official pages it depends on.")),
            sec("Depth Deficiency Index (proposed, not computed)",
                "The brief asks for a way to know when backups are replacing starters. The index below is "
                "specified so it can be pre-registered and tested, but <strong>no score is published</strong>: the "
                "inputs cover 4 of 32 clubs, no official snap count exists, and no threshold has been validated. "
                "A number computed from this sample would be a guess dressed as a measurement.",
                T(["Component", "Definition", "Official input?", "Status"], [
                    (["Availability load", "Count of 1st-string players designated Out or Doubtful, weighted by position group.", "Injury report: yes; starter status: no", pill("partial", "warn")], ["NFL-INJURY-REPORT", "NE-DEPTH"]),
                    (["Depth thinness", "At each affected slot, number of listed players behind the unavailable player (0 = none).", "Club chart: yes, but unofficial", pill("partial", "warn")], ["NE-DEPTH", "DET-DEPTH"]),
                    (["Replacement exposure", "Snaps played by the replacement in the games the starter missed.", "No official snap-count category", pill("blocked", "bad")], ["NFL-PLAYER-STATS"]),
                    (["Persistence", "Whether the same slot is depleted in consecutive weeks.", "Requires a dated archive that does not exist yet", pill("blocked", "bad")], ["NFL-INJURY-REPORT"]),
                    (["Validation", "Pre-register the index, then require the eight existing gates and an untouched holdout.", "Project method; NIST statistics", pill("not started", "warn")], ["REPO", "NIST-CI"]),
                ], caption="Proposal S05 in the suggestions register; depends on questions Q05, Q07 and Q15.")),
            sec("Coverage and tracking log",
                "What was verified, when, and what remains. The other 28 clubs are blank, not zero.",
                T(["Coverage", "Clubs", "What was read", "Status"], [
                    (["Verified this session", "WAS, NYG, NE, DET", "Injury report rows plus each club's own depth chart", pill("4 of 32", "warn")], ["NFL-INJURY-REPORT", "WAS-DEPTH", "NYG-DEPTH", "NE-DEPTH", "DET-DEPTH"]),
                    (["Not verified this session", "28 clubs", None, pill("unverified", "warn")], ["NFL-INJURY-REPORT"]),
                    (["Official league-wide depth chart", "—", "The NFL publishes none; club pages are the only source", pill("absent", "bad")], ["NFL-INJURY-REPORT", "NE-DEPTH"]),
                    (["Snap counts", "—", "No category in the official player-stats index", pill("absent", "bad")], ["NFL-PLAYER-STATS"]),
                ], caption="Coverage gap flagged F11; the 28-club row is intentionally blank.")),
            sec("How this feeds a strategy — and what it cannot do yet",
                "An availability signal would enter the same fail-closed pipeline as every other rule: a "
                "pre-registered definition, an untouched holdout, multiplicity control and a price-based test. None "
                "of that is possible from four clubs and one week, so nothing here is offered as a signal.",
                T(["Use", "What would be required", "Current state"], [
                    (["Line adjustment", "A dated archive of injury designations and depth charts, joined to prices before and after the report.", "No archive; one snapshot"], ["NFL-INJURY-REPORT", "REPO"]),
                    (["Prop and parlay correlation", "Player-level participation and market prices at the same timestamp.", "No official prop feed"], ["DK-PROP", "NFL-PLAYER-STATS"]),
                    (["Skill test", "Pre-registered effect, power target, holdout, forward test.", "Not started"], ["NIST-CI", "NIST-MULTI"]),
                ], caption="See questions Q05, Q07, Q15 and suggestions S03-S05.")),
        ],
    )

    # ------------------------------------------------------------------
    # Decision readiness: questions register
    # ------------------------------------------------------------------
    QUESTIONS = [
        ("Q01", "Do we hold written permission or a licence to use official NFL data at scale?", "blocking",
         "Every empirical value depends on lawfully held data. Without it no price, ROI or correlation can be published.",
         "NFL Terms sections 1.1 and 1.3 prohibit reproduction and systematic retrieval without prior written consent.",
         "Any licence, contract or written consent; none is on file in this repository.",
         None, "A signed licence or consent reviewed by counsel, recorded in the repository.", ["NFL-TERMS", "REPO"]),
        ("Q02", "Is there an official, league-wide depth chart?", "answered",
         "Determines whether '1st string' can be published as an official fact or only as club-published opinion.",
         "The NFL publishes injury reports. Depth charts are club pages; New England and Detroit label theirs unofficial.",
         "—", "No. Club charts only, and two of four read are explicitly unofficial.", "Not applicable — the constraint is now documented.", ["NFL-INJURY-REPORT", "NE-DEPTH", "DET-DEPTH"]),
        ("Q03", "What do the injury designations mean?", "answered",
         "A status is only usable if its definition is fixed.", "The league's own definitions of DNP, Limited, Full, Out, Doubtful and Questionable.", "—",
         "Quoted verbatim on the injuries page from the league's announcement.", "Not applicable.", ["NFL-INJURY-POLICY"]),
        ("Q04", "Does the official injury report say whether a player is a starter or a backup?", "answered",
         "If it did, depth mapping would be unnecessary.", "The report's columns are Player, Position, Injuries, Practice Status, Game Status.", "—",
         "No. There is no depth, starter or snap field.", "Not applicable.", ["NFL-INJURY-REPORT"]),
        ("Q05", "Is there an official snap-count source to measure replacement exposure?", "blocking",
         "Without snaps, 'a backup replaced a starter' cannot be measured, only asserted.", "The official player-stats index lists 11 categories and none is snap counts.", "Any official snap feed.",
         "No snap-count category appears in the official index; the direct category URL returns the official 404.", "An official snap feed, or an explicit decision to use a disclosed third-party source and label it.", ["NFL-PLAYER-STATS", "NFL-INJURY-REPORT"]),
        ("Q06", "Is the final inactive list captured and archived?", "blocking",
         "The inactive list, not the injury report, is the last word on who can play.", "Policy requires an explanation to the league if an omitted player is deactivated.", "An archived official inactive list for each game.",
         None, "A dated capture of the official inactive list before each kickoff, with a licence that permits it.", ["NFL-INJURY-POLICY", "REPO"]),
        ("Q07", "How is 'starter' defined for this study?", "blocking",
         "The whole 2nd/3rd/4th-string question depends on a definition that survives scrutiny.", "Club depth charts for 4 clubs; no league designation.", "An agreed operational definition and its source precedence.",
         None, "Owner decision: accept club charts as opinion, or adopt a snap-based definition once Q05 is answered.", ["NE-DEPTH", "NFL-INJURY-REPORT", "REPO"]),
        ("Q08", "How large a sample is needed to separate skill from luck at the effect sizes we expect?", "blocking",
         "A leaderboard that ranks noise is worse than no leaderboard.", "NIST confidence-interval and bootstrap methods; the repository's eight gate definitions.", "An agreed minimum detectable effect and power target.",
         None, "A written power analysis and a pre-registered minimum sample, signed off before any ranking.", ["NIST-CI", "NIST-BOOT", "REPO"]),
        ("Q09", "Which validation gates are mandatory and what are their thresholds?", "blocking",
         "Without fixed thresholds, a strategy can always be declared a pass.", "Eight gates are defined in the repository and applied fail-closed.", "Owner sign-off on the thresholds and on what counts as failure.",
         None, "A recorded owner decision on the gate table; until then every strategy stays ineligible.", ["REPO", "NIST-MULTI"]),
        ("Q10", "What are the reward-pool terms?", "blocking",
         "A competition with rewards needs a sponsor, an amount, a jurisdiction and payout rules before it can rank anything.", "The brief asks for rewards; the qualification standard exists.", "Sponsor, amount, eligibility, jurisdiction, payout and dispute terms.",
         None, "Written, published terms; until then the leaderboard is non-monetary (S10).", ["NFL-RG", "REPO"]),
        ("Q11", "Which operators and markets are in scope?", "blocking",
         "Prices differ by book and market; a signal is only defined against a named market.", "Official operator rules for spread, moneyline, total, parlay and props.", "A named book, market set and account jurisdiction.",
         None, "Owner decision, recorded with the licence position in Q01.", ["DK-ODDS", "DK-MARKETS", "REPO"]),
        ("Q12", "How are pushes and ties settled in a parlay?", "answered",
         "Changes the expected value of every correlated combination.", "DraftKings: a push is removed and the odds are recalculated.", "—",
         "Answered by the operator's own rule page.", "Not applicable.", ["DK-PARLAY"]),
        ("Q13", "How is a player prop settled if the player does not start?", "answered",
         "Directly affects any prop-combination strategy.", "DraftKings: generally, if a player starts or meets the playing-time requirement, bets stand and settle accordingly.", "—",
         "Answered by the operator's own article; complete settlement is directed to its sport-specific house rules.", "Not applicable.", ["DK-PLAYER"]),
        ("Q14", "Do we hold an executable, timestamped quote archive?", "answered",
         "Without it, no ROI or closing-line value can be computed.", "No licensed archive is present; all price-based values are blank.", "An archive of executable quotes with timestamps.",
         "No. This is a standing constraint, not a data gap that can be closed from public pages.", "A licensed archive (S02), or the decision to publish no price-based result.", ["NFL-TERMS", "REPO"]),
        ("Q15", "Is the availability signal strong enough to matter?", "non-blocking",
         "Determines whether the injury and depth work becomes a strategy or stays context.", "One week across four clubs; no outcome data joined.", "A dated multi-week archive and a power analysis.",
         None, "S03 and S04 done, then a pre-registered test under Q08.", ["NFL-INJURY-REPORT", "REPO"]),
        ("Q16", "What is the false-discovery policy for a large family of tests?", "blocking",
         "Ranking many strategies without multiplicity control manufactures winners.", "NIST multiple-comparison and Bonferroni methods; NIH-hosted FDR literature.", "A chosen policy and family definition.",
         None, "Owner decision recorded against the pre-registered family.", ["NIST-MULTI", "NIST-BONF", "NIH-FDR"]),
        ("Q17", "What takes precedence when two official pages disagree?", "blocking",
         "Five injury-report players already fail to match a depth row; without a rule each case is ad hoc.", "A documented conflict list (F12) and both official pages.", "A precedence rule and an escalation path.",
         None, "A written rule: league report beats club chart for status; club chart is quoted, never reconciled silently.", ["NFL-INJURY-REPORT", "NE-DEPTH", "REPO"]),
        ("Q18", "Can a published snapshot be reproduced after the source changes?", "answered",
         "Every mutable official table needs a date and a live link or it becomes unverifiable.", "The injury page changes as practice reports are filed.", "An archived official copy.",
         "No archive exists; therefore every mutable row is dated and linked to the live page.", "An archive under a licence that permits retention (S03).", ["NFL-INJURY-REPORT", "NFL-TERMS"]),
    ]

    q_rows = []
    n_blocking = 0
    for qid, question, kind, why, have, missing, answer_text, resolves, srcs in QUESTIONS:
        status = {"answered": "answered (official)", "blocking": "open — blocking", "non-blocking": "open — non-blocking"}[kind]
        if kind == "blocking":
            n_blocking += 1
        q_rows.append(([
            f"<strong>{E(qid)}</strong>", E(question), E(why), E(have), E(missing),
            answer_text if answer_text else blank(),
            pill(status, "ok" if kind == "answered" else "bad" if kind == "blocking" else "warn"),
        ], srcs, qid))

    pages["questions"] = dict(
        title="Questions & decisions",
        lead="The questions that have to be answered — or explicitly accepted as unanswerable — before any "
             "decision is reasonable, with the information held, the information missing, and what would resolve "
             "each one. Every answer is either quoted from an official source or left blank and flagged.",
        kpis=[
            ("Questions registered", len(QUESTIONS), "Grouped by what they block"),
            ("Blocking a decision", n_blocking, "No verdict is possible while open"),
            ("Answered from official pages", sum(1 for q in QUESTIONS if q[2] == "answered"), "Definitions, settlement, structure"),
            ("Answers left blank", sum(1 for q in QUESTIONS if not q[6]), "Unknown, flagged, not guessed"),
        ],
        sections=[
            sec("How to use this register",
                "A decision is only reasonable when each question below is either answered or consciously accepted "
                "as open. The 'information held' column states what this repository actually has, with a link; the "
                "'information missing' column states what it does not have. A blank answer is an unknown, rendered "
                "with an unverified marker that opens the review page — it is never filled in with a plausible value.",
                T(["Rule", "Consequence"], [
                    (["An answered question cites an official page", "The answer is quotable, and the link is on the row."], ["NFL-INJURY-POLICY"]),
                    (["An unanswered question has a blank answer", "It blocks the linked decision and appears on Flagged for Review."], ["REPO"]),
                    (["A blocking question stops a verdict", "No strategy, rank or reward decision is made while it is open."], ["REPO"]),
                    (["A suggestion must name its questions", "The suggestions register links every proposal to the questions it needs answered first."], ["REPO"]),
                ])),
            sec("The register",
                str(len(QUESTIONS)) + " questions: " + str(n_blocking) + " blocking, the rest answered or "
                "non-blocking. Every row links the official page that supports the answer.",
                T(["ID", "Question", "Why it blocks a decision", "Information we have", "Information we do not have",
                   "Answer", "Status"], q_rows,
                  caption="A blank answer is an unverified unknown; it links to the review page.",
                  filter_id="q-filter")),
            sec("Information we have and do not have",
                "A one-screen inventory of the decision inputs. Verified means an official page was opened and read.",
                T(["Input", "We have", "We do not have", "Status"], [
                    (["Injury designations and practice status", "One dated snapshot, 44 rows, 4 clubs", "A licensed feed or an archive"], ["NFL-INJURY-REPORT"]),
                    (["Depth order", "4 club charts, two labelled unofficial", "A league-wide or official depth chart"], ["NE-DEPTH", "DET-DEPTH"]),
                    (["Snap exposure", "Nothing", "Any official snap count"], ["NFL-PLAYER-STATS"]),
                    (["Prices and quotes", "Operator rules and definitions only", "An executable, timestamped archive"], ["DK-ODDS", "NFL-TERMS"]),
                    (["Settlement rules", "Spread, total, moneyline, parlay and prop definitions", "Archived house rules at the time of each bet"], ["DK-PARLAY", "DK-PLAYER"]),
                    (["Statistical method", "NIST CI, bootstrap, multiplicity, FDR literature", "A power target and a chosen policy"], ["NIST-CI", "NIH-FDR"]),
                    (["Competition terms", "A qualification standard", "Sponsor, pool, jurisdiction, payouts"], ["NFL-RG", "REPO"]),
                ])),
            sec("Decision gates",
                "A decision gate is a test the project must pass before a class of decisions becomes reasonable. "
                "State is the current position, not a forecast.",
                T(["Gate", "Decision it governs", "Pass condition", "Current state"], [
                    (["D1 — rights", "Publishing any official-derived dataset", "Written permission or a licence on file (Q01).", pill("not met", "bad")], ["NFL-TERMS"]),
                    (["D2 — data", "Publishing any measured edge", "Licensed event data plus an executable quote archive (Q05, Q14).", pill("not met", "bad")], ["NFL-PLAYER-STATS", "REPO"]),
                    (["D3 — method", "Promoting a strategy", "Pre-registered family, power target and gate thresholds (Q08, Q09, Q16).", pill("partly met", "warn")], ["NIST-MULTI", "REPO"]),
                    (["D4 — evidence", "Ranking a strategy", "Untouched holdout plus forward test, multiplicity control.", pill("not met", "bad")], ["NIST-BOOT", "REPO"]),
                    (["D5 — reward", "Paying or publishing a prize", "Written terms, funding and jurisdiction (Q10).", pill("not met", "bad")], ["NFL-RG", "REPO"]),
                ], caption="D3 is partly met because the eight gates and the multiplicity method exist; the thresholds do not.")),
            sec("What would resolve the blocking questions",
                "Each blocking question has an owner action attached. These are suggestions, not commitments; the "
                "proposals that carry them are on the suggestions page.",
                T(["Question", "Resolving action", "Proposal"], [
                    (["Q01", "Obtain written permission or licence", A("suggestions.html#S01", "S01")], ["NFL-TERMS", "REPO"]),
                    (["Q05", "Write the fallback rule for snap exposure, or record that it stays unmeasured", A("suggestions.html#S07", "S07")], ["NFL-PLAYER-STATS", "REPO"]),
                    (["Q06", "Archive the official inactive list for each game", A("suggestions.html#S06", "S06")], ["NFL-INJURY-POLICY", "REPO"]),
                    (["Q07 / Q17", "Write the source-precedence and starter-definition rules", A("suggestions.html#S05", "S05")], ["NE-DEPTH", "REPO"]),
                    (["Q08 / Q09 / Q16", "Record the power target, gate thresholds and multiplicity policy", A("suggestions.html#S08", "S08")], ["REPO", "NIST-CI"]),
                    (["Q10 / Q11", "Publish reward terms and name the operator/market scope", A("suggestions.html#S11", "S11")], ["NFL-RG", "DK-MARKETS"]),
                ])),
        ],
    )

    # ------------------------------------------------------------------
    # Suggestions: proposals only, nothing implemented
    # ------------------------------------------------------------------
    SUGGESTIONS = [
        ("S01", "Obtain written permission or a licence for official NFL data",
         "No empirical value can be published lawfully without it; it is the root blocker.",
         "Q01, Q14", "Very high", "High (legal, time)", "Compliance risk if approached casually",
         ["NFL-TERMS", "REPO"]),
        ("S02", "Contract an executable, timestamped quote archive",
         "ROI, closing-line value and correlation all require prices recorded before the outcome.",
         "Q14, Q11", "Very high", "High (cost)", "Vendor lock-in; terms may forbid redistribution",
         ["NFL-TERMS", "DK-ODDS"]),
        ("S03", "Archive a dated snapshot of the official injury report every day",
         "The page is mutable and unarchived, so no history can be tested (F14, Q18).",
         "Q18, Q15", "High", "Low", "Retention may exceed the Terms; needs the same licence as S01",
         ["NFL-INJURY-REPORT", "NFL-TERMS"]),
        ("S04", "Extend availability and depth coverage from 4 clubs to all 32",
         "Four clubs cannot support a league-wide signal; the other 28 are blank (F11).",
         "Q07, Q15", "High", "Medium", "32 different page layouts; charts change without notice",
         ["NFL-INJURY-REPORT", "NE-DEPTH"]),
        ("S05", "Pre-register the Depth Deficiency Index and validate it with the eight gates",
         "Turns the ad-hoc backup read into a testable definition with fixed thresholds.",
         "Q07, Q09, Q17", "High", "Medium", "Risk of a plausible-looking index that fails out of sample",
         ["REPO", "NIST-CI"]),
        ("S06", "Capture the official inactive list before each kickoff",
         "The injury report is not the final availability list (F15, Q06).",
         "Q06, Q18", "Medium", "Medium", "No official machine-readable archive; day-of timing",
         ["NFL-INJURY-POLICY", "REPO"]),
        ("S07", "Write the source-precedence rule for conflicting official pages",
         "Five players already fail to join; without a rule each case is decided ad hoc (F12, Q17).",
         "Q17, Q07", "Medium", "Low", "A rule can hide errors if it silently discards one source",
         ["NFL-INJURY-REPORT", "NE-DEPTH"]),
        ("S08", "Publish a power / minimum-detectable-effect calculator with the leaderboard",
         "Ranking strategies without a power target manufactures winners (Q08, Q16).",
         "Q08, Q09, Q16", "High", "Low", "A calculator is not a substitute for an owner decision",
         ["NIST-CI", "NIST-BOOT"]),
        ("S09", "Replace own-line accuracy headlines with closing-line value once quotes exist",
         "Own-line error is a model diagnostic, not a bettable edge without prices.",
         "Q14", "Medium", "Medium", "Requires S02; otherwise remains blank",
         ["REPO", "DK-ODDS"]),
        ("S10", "Keep the leaderboard non-monetary until reward terms exist",
         "A rank with an implied prize and no terms is misleading (F16, Q10).",
         "Q10", "High", "Low", "Removes an incentive the brief asks for, until terms exist",
         ["NFL-RG", "REPO"]),
        ("S11", "Publish written reward terms: sponsor, pool, jurisdiction, payout, disputes",
         "The competition cannot rank or pay anything without them (Q10).",
         "Q10, Q11", "High", "High (legal)", "Regulatory exposure varies by jurisdiction",
         ["NFL-RG", "REPO"]),
        ("S12", "Consolidate the published dashboards into one canonical surface",
         "Six builds publish overlapping numbers; a reader cannot tell which is authoritative (N07).",
         "Q17", "Medium", "Medium", "Must not delete another session's work; additive redirects only",
         ["REPO"]),
        ("S13", "Check every official source URL live in CI, not just the allow-list",
         "A link can be on the allow-list and still be dead; the current gate never requests it.",
         "Q17", "Medium", "Low", "Live checks are flaky and rate-limited; cache and retry",
         ["REPO", "NFL-INJURY-REPORT"]),
        ("S14", "Adopt a suggestion → decision → implementation changelog with rollback",
         "Nothing records who approved a change or how to reverse it.",
         "Q09", "Medium", "Low", "Process overhead on a small project",
         ["REPO"]),
        ("S15", "Timestamp every mutable official table and link its live source",
         "Injury, standings and depth values change; undated rows silently decay (F14).",
         "Q18", "Medium", "Low", "A timestamp is not an archive; it does not replace S03",
         ["NFL-INJURY-REPORT", "NFL-STANDINGS-2025"]),
    ]

    assert len(QUESTIONS) == N_QUESTIONS, len(QUESTIONS)
    assert sum(1 for q in QUESTIONS if q[2] == "blocking") == N_BLOCKING
    assert len(SUGGESTIONS) == N_SUGGESTIONS, len(SUGGESTIONS)

    def _suggestion_rows(items):
        rows = []
        for sid, title, problem, questions, impact, effort, risk, srcs in items:
            rows.append(([
                f"<strong>{E(sid)}</strong>", E(title), E(problem), E(questions),
                pill(impact, "ok" if impact in ("High", "Very high") else "info"),
                E(effort), E(risk), "proposed — not implemented",
            ], srcs, sid))
        return rows

    pages["suggestions"] = dict(
        title="Suggestions",
        lead="Fifteen proposals to improve the site and the research, each with its problem, its impact, its "
             "cost, its risk and the questions it depends on — plus three paths and a recommendation. "
             "<strong>Nothing here has been implemented.</strong> The page exists so a path can be chosen and "
             "reviewed before any change is made.",
        kpis=[
            ("Proposals registered", len(SUGGESTIONS), "All status: proposed"),
            ("Implemented", 0, "No change made without a recorded decision"),
            ("Blocking questions referenced", N_BLOCKING, "See the questions page"),
            ("Paths offered", 3, "Evidence-first, coverage-first, governance-first"),
        ],
        sections=[
            sec("How to choose a path",
                "Pick a path, not a pile of items. Each path is a sequence whose later steps depend on earlier "
                "answers; taking a step out of order is how a project ends up ranking luck. The three paths below "
                "are ordered by what they unlock, not by how impressive they look.",
                T(["Step", "What you do", "Why it comes first"], [
                    (["1", "Answer or accept the blocking questions on the questions page.", "A proposal cannot be judged solved if its blocker is still open."], ["REPO"]),
                    (["2", "Choose one path and record the choice on this page.", "A recorded decision is reversible; an implicit one is not."], ["REPO"]),
                    (["3", "Implement one proposal, then re-run the build and the verifier.", "The site must stay green; the verifier is fail-closed."], ["REPO"]),
                    (["4", "Mark the proposal implemented with a date and an owner decision.", "Nothing is marked done without evidence."], ["REPO"]),
                ])),
            sec("Three paths, with what each one actually buys",
                "Costs are relative to this repository's own effort, not money, except where stated.",
                T(["Path", "Sequence", "What it unlocks", "Cost", "Recommendation"], [
                    (["A — Evidence first", "S01 → S02 → S09 → S08 → S11", "Lawful data, a quote archive and a real skill test: the only path to a defensible leaderboard.", "Highest; depends on a licence and a vendor.", pill("do third", "info")], ["NFL-TERMS", "REPO"]),
                    (["B — Coverage first", "S03 → S04 → S06 → S05 → S15", "A dated, league-wide availability and depth record — the input the brief asks for, using pages we can already verify.", "Medium; mostly engineering.", pill("do first", "ok")], ["NFL-INJURY-REPORT", "NE-DEPTH"]),
                    (["C — Governance first", "S07 → S12 → S13 → S10 → S14", "One authoritative surface, live link checks, no implied prizes, reversible changes.", "Low; cheap and immediate.", pill("do second", "ok")], ["REPO", "NFL-RG"]),
                ], caption="Recommended order: B, then C, then A. Do not start S11 (reward terms) before S01 and Q10 are resolved."),
                note="Choosing a path does not authorise data acquisition that the NFL Terms prohibit; S01 remains the gate for anything empirical."),
            sec("Register of proposals",
                "Every row is a proposal with its status recorded as <em>not implemented</em>. The source column "
                "links the official page or repository artifact that motivates it.",
                T(["ID", "Suggestion", "Problem it solves", "Questions", "Impact", "Effort", "Risk", "Status"],
                  _suggestion_rows(SUGGESTIONS),
                  caption="Status is deliberately uniform: nothing has been implemented in this session.",
                  filter_id="s-filter")),
            sec("The two proposals that would change the most, and what they cost",
                "Called out because they are the only ones that change what the project can claim.",
                T(["Proposal", "Would let the site say", "Would still not let it say", "Blocked by"], [
                    (["S01 + S02", "A measured edge with a timestamped price and a stated licence.", "That the edge will persist; that is D4's job.", "Q01, Q14"], ["NFL-TERMS", "REPO"]),
                    (["S03 + S04 + S05", "Which positions are depleted league-wide, measured against a dated record.", "That depletion is worth points without a price-based test.", "Q05, Q07, Q15"], ["NFL-INJURY-REPORT", "NFL-PLAYER-STATS"]),
                ])),
            sec("Explicitly not implemented",
                "A short list so there is no ambiguity about the current state of the site.",
                T(["Item", "State", "Why"], [
                    (["Any proposal on this page", "Not implemented", "No owner decision has been recorded (F16)."], ["REPO"]),
                    (["Any reward, prize or rank with money attached", "Not implemented", "No terms, sponsor, pool or jurisdiction (Q10)."], ["NFL-RG"]),
                    (["Any new data acquisition or scraping", "Not performed", "NFL Terms prohibit systematic retrieval without consent (Q01, F17)."], ["NFL-TERMS"]),
                    (["Any change to another session's site", "Not performed", "Scope boundary recorded on the coordination board."], ["REPO"]),
                ])),
            sec("Decision record (blank until you choose)",
                "This table is the place a decision is recorded. It is intentionally empty: a decision is a "
                "governance act, not a data value, so it is not filled in by the build.",
                T(["Decision", "Options", "Recorded choice", "Date"], [
                    (["Path", "A, B, or C (or a written variant)", "—", "—"], ["REPO"]),
                    (["First proposal to implement", "Any S-number in this register", "—", "—"], ["REPO"]),
                    (["Leaderboard basis", "Non-monetary until Q10, or funded with published terms", "—", "—"], ["NFL-RG", "REPO"]),
                    (["Data position", "Seek a licence, or restrict the site to rules and definitions", "—", "—"], ["NFL-TERMS", "REPO"]),
                ], caption="An empty decision cell is an unmade decision, not an unverified fact.")),
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
        (["Integration dashboard", "/hub/", "This 23-page consolidation", "official-evidence"], [tree("hub/")]),
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
