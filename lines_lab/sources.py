"""Source register for the Line Origination lab.

Every claim that appears on a page under ``lines_lab/`` names one of these IDs and links
the page itself. A source is registered only after this session opened the page and read
the sentence quoted here. Nothing is registered from memory, from a search snippet, or
from another session's page.

Tiers used throughout the section
---------------------------------
``official``   the governing body (the NFL), a licensed operator for its own rules, or a
               US government / standards body for a statistical or regulatory definition.
               **No official source publishes an NFL point spread, total, moneyline,
               opening line or player-prop price.** So no market number anywhere in this
               section can be ``official``, and none is labelled so.
``dataset``    the pinned open dataset (nflverse/nfldata at a fixed commit, checksummed)
               or this repository's own code and committed artefacts. Reproducible by
               anyone; not a league or operator publication.
``secondary``  a reputable third-party reference that is explicitly NOT a league or
               operator publication. Used only for cross-checking, never to fill a value.

``BLANK``      a value that could not be confirmed from a source in the first two tiers.
               It is rendered blank with a link to the review page. Never inferred, never
               filled with a plausible number, never averaged over.
"""
from __future__ import annotations

# Checked by this session on 2026-11-14 (UTC) unless a different date is shown.
SOURCES: list[dict] = [
    # ---------------------------------------------------------------- official rules
    dict(id="NFL-PS", tier="official", publisher="NFL Support",
         url="https://support.nfl.com/hc/en-us/articles/35869774194324-What-is-the-point-spread",
         checked="2026-11-14", title="What is the point spread?",
         quote=("'Point spread is a way for oddsmakers to make a matchup between two unbalanced "
                "teams more even by giving points to or taking points away from each team. "
                "Similar to the money line, a negative point spread indicates which team is "
                "favored to win and a positive spread indicates the underdog.' "
                "'Most often, the betting odds for point spread are -110.' "
                "'if the point spread was +10/-10 and the favored team wins by exactly 10 or the "
                "underdog loses by exactly 10, you would push and get your initial wager returned.'"),
         used_for="Sign convention for a spread; the -110 reference price; the definition of a push."),
    dict(id="NFL-ML", tier="official", publisher="NFL Support",
         url="https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line",
         checked="2026-11-14", title="What is a money line?",
         quote=("'The team with a plus sign in front of the odds is the underdog ... odds with a "
                "minus sign reflect teams that are favored to win and reflect the amount that "
                "needs to be wagered in order to win $100.' "
                "'Tie | Push | If the game ends in a tie, the bettor's wager is returned with no "
                "loss or profit.'"),
         used_for="Moneyline sign convention and the settlement of a tied game on the moneyline."),
    dict(id="DK-PARLAY", tier="official", publisher="DraftKings (licensed operator)",
         url="https://support.draftkings.com/dk/en-us/what-is-a-parlay-bet?id=kb_article_view&sysparm_article=KB0010683",
         checked="2026-11-14", title="What is a parlay bet? (KB0010683, v4.0)",
         quote=("'All added bets must win in order for the parlay to win. If one selection in the "
                "parlay loses, the whole parlay loses. If a selection results in a push, it is "
                "removed from the parlay and the odds are recalculated accordingly.' "
                "'For certain selections, the outcomes can be considered correlated. In these "
                "cases, DraftKings reserves the right to restrict parlay betting on these "
                "outcomes.'"),
         used_for="Parlay settlement, push handling and why correlated legs are priced jointly."),
    dict(id="DK-PROP", tier="official", publisher="DraftKings (licensed operator)",
         url="https://support.draftkings.com/dk/en-us/what-is-a-prop-bet?id=kb_article_view&sysparm_article=KB0010778",
         checked="2026-11-14", title="What is a prop bet? (KB0010778, v3.0)",
         quote=("'A prop bet or proposition bet is a wager on an individual player or specific "
                "event in a game/match that is not directly connected to the outcome of a game.'"),
         used_for="Defining a prop bet, so the absence of player-level market data can be stated "
                 "precisely rather than assumed."),
    dict(id="DK-SGP", tier="official", publisher="DraftKings (licensed operator)",
         url="https://support.draftkings.com/dk/en-us/what-is-a-same-game-parlay-sgp-bet?id=kb_article_view&sysparm_article=KB0010719",
         checked="2026-11-14", title="What is a Same Game Parlay (SGP) bet? (KB0010719)",
         quote=("Linked directly from the verified parlay article as the same-game-parlay "
                "definition. The page body is client-rendered and returned 'Loading...' when "
                "fetched, so NO sentence is quoted from it here; only its existence and title "
                "were confirmed."),
         used_for="Pointer only. No claim in this section rests on this page."),
    dict(id="NFL-TERMS", tier="official", publisher="NFL",
         url="https://www.nfl.com/legal/terms/",
         checked="2026-11-14", title="NFL Terms and Conditions",
         quote=("Section 1.1 prohibits copying, reproducing or distributing the Services or their "
                "contents; Section 1.3 prohibits 'Systematic retrieval of data or other content "
                "from the Services ... absent our express prior written consent.'"),
         used_for="The licence question: why no official NFL page may be scraped at scale."),
    dict(id="NFL-INJURY", tier="official", publisher="NFL",
         url="https://www.nfl.com/injuries/",
         checked="2026-11-14", title="Official NFL Injury Report",
         quote="The league publishes a weekly injury report with practice participation and a game status per player.",
         used_for="The only official, league-wide availability publication; used to source a starter's status."),
    dict(id="NFL-RESERVE", tier="official", publisher="NFL",
         url="https://www.nfl.com/transactions/league/reserve-list/2026/11",
         checked="2026-11-14", title="NFL transactions — reserve list",
         quote="The league lists players placed on a reserve list, by month.",
         used_for="A second official signal that a player is unavailable, independent of the injury report."),
    dict(id="NFL-DEPTH-404", tier="official", publisher="NFL",
         url="https://www.nfl.com/depth-charts/",
         checked="2026-11-14", title="NFL depth charts (probed)",
         quote="The league-wide depth-chart address does not return a chart. Depth charts are club publications.",
         used_for="Establishes that there is no league-wide official depth chart."),
    dict(id="NFL-SCHEDULE", tier="official", publisher="NFL",
         url="https://www.nfl.com/schedules/",
         checked="2026-11-14", title="NFL schedules",
         quote="The league publishes the season schedule, including each game's date, kickoff time and bye weeks.",
         used_for="Rest-day arithmetic and the identification of a bye."),

    # ------------------------------------------------------------- official statistics
    dict(id="NIST-BONF", tier="official", publisher="NIST/SEMATECH e-Handbook of Statistical Methods",
         url="https://www.itl.nist.gov/div898/handbook/prc/section4/prc473.htm",
         checked="2026-11-14", title="7.4.7.3 Bonferroni's method",
         quote=("'the Bonferroni method states that the confidence coefficient is at least 1-alpha "
                "that simultaneously all the following confidence limits for the g linear "
                "combinations are correct' — each interval is built at (1 - alpha/g)."),
         used_for="Family-wise error control when many candidate signals are tested at once."),
    dict(id="NIST-SAMPLESIZE", tier="official", publisher="NIST/SEMATECH e-Handbook of Statistical Methods",
         url="https://www.itl.nist.gov/div898/handbook/prc/section2/prc222.htm",
         checked="2026-11-14", title="7.2.2.2 Sample sizes required",
         quote=("'N = (z(1-alpha) + z(1-beta))^2 (sigma/delta)^2  -> one-sided test'. "
                "For alpha = 0.05 and beta = 0.10 the page gives (1.645 + 1.282)^2 = 8.567."),
         used_for="How many settled bets a strategy needs before its edge can be distinguished from noise."),
    dict(id="NIST-CI", tier="official", publisher="NIST/SEMATECH e-Handbook of Statistical Methods",
         url="https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm",
         checked="2026-11-14", title="1.3.5.2 Confidence interval for the mean",
         quote="A confidence interval for a mean is the estimate plus and minus a critical value times the standard error.",
         used_for="The lower confidence bound used to rank and to demote a strategy."),
    dict(id="NIST-CORR", tier="official", publisher="NIST/SEMATECH e-Handbook of Statistical Methods",
         url="https://www.itl.nist.gov/div898/software/dataplot/refman2/auxillar/correlat.htm",
         checked="2026-11-14", title="Correlation coefficient (Dataplot reference)",
         quote="The correlation coefficient measures the linear association between two variables and lies in [-1, 1].",
         used_for="Definition of the phi coefficient reported for correlated legs."),

    # ---------------------------------------------------------------- secondary sources
    dict(id="PFR-SCORES", tier="secondary", publisher="Pro-Football-Reference",
         url="https://www.pro-football-reference.com/years/2026/games.htm",
         checked="2026-11-14", title="2026 NFL Scores & Schedule",
         quote="A third-party game log with final scores. Explicitly NOT a league or operator publication.",
         used_for="Cross-check only. A value is never filled from this source."),
]

BY_ID = {s["id"]: s for s in SOURCES}
OFFICIAL = tuple(s["url"] for s in SOURCES if s["tier"] == "official")

# The pinned dataset. Every market number in this section comes from here, and here only.
DATASET = dict(
    repo="nflverse/nfldata",
    commit="a270278f3ac4e937295fe6a27814b3c4a2b62645",
    license_note=("Released by the nflverse project. An independent open-source distribution "
                  "of data collected from public sources — not an NFL publication."),
    files={
        "games.csv": dict(
            path="data/raw/games.csv",
            sha16="ba34f3619067eb44",
            rows="7548 rows incl. header",
            provides="One row per game 1999-2026: final scores, spread_line, total_line, "
                     "moneylines, spread/total prices, rest days, roof, surface, temperature, "
                     "wind, neutral-site flag, division flag.",
            url="https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv"),
        "closing_lines.csv": dict(
            path="data/raw/closing_lines.csv",
            sha16="3571e1c9fc8d7396",
            rows="20490 rows incl. header",
            provides="Per-side closing line, price and outcome, 2006-2018.",
            url="https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/closing_lines.csv"),
        "initial_lines.csv": dict(
            path="data/raw/initial_lines.csv",
            sha16="654770173d11fdb2",
            rows="1088 rows incl. header",
            provides="Opening spread and total, one book (WSGT), 2021 only. No price column.",
            url="https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/initial_lines.csv"),
        "sc_lines.csv": dict(
            path="data/raw/sc_lines.csv",
            sha16="384039e92630831e",
            rows="4092 rows incl. header",
            provides="A second book's spread lines, 2013 onward. Cross-book sanity check only.",
            url="https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/sc_lines.csv"),
        "win_totals.csv": dict(
            path="data/raw/win_totals.csv",
            sha16="6228fe8c2cf41b34",
            rows="576 rows incl. header",
            provides="Season win-total market, by book and season.",
            url="https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/win_totals.csv"),
    },
)

REPO_TREE = "https://github.com/karagemop466-tech/Korea3/tree/main/"
REPO_BLOB = "https://github.com/karagemop466-tech/Korea3/blob/main/"
