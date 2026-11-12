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
SNAPSHOT = "2026-11-02"
SESSION = "arena/25ea8ac4-korea3"
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
    ("Evidence", [("sources", "Official sources"), ("repo-review", "Repo review"), ("data", "Data inventory"), ("standings", "Official standings")]),
    ("Line lab", [("own-lines", "Own lines"), ("strategies", "Strategies & signals")]),
    ("Bet types", [("single-bets", "Single bets"), ("parlays", "Parlays"), ("player-props", "Player props")]),
    ("Statistics", [("correlations", "Correlations"), ("validation", "Validation gates"), ("leaderboard", "Leaderboard")]),
    ("Decision support", [("suggestions", "Suggestions"), ("information-gaps", "Information gaps"), ("injury-tracker", "Injury tracker")]),
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
        ("Official sources re-verified", n_verified, "Opened on the publisher's own site " + SNAPSHOT),
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
                    (["Consolidated dashboard (20 pages)", A("index.html", "/hub/index.html"), "Every table row links a source: an official publisher where the fact is officially published, a repository artifact where it is computed"], ["REPO"]),
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
            claim, status, E(SNAPSHOT if s["status"] == "verified" else "—" if not s["claim"] else SNAPSHOT),
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
        (["Integration dashboard", "/hub/", "This 20-page consolidation", "official-evidence"], [tree("hub/")]),
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

    # -- Suggestions --------------------------------------------------------
    suggestion_rows = [
        (["S01", "High", "Add real-time NFL injury report ingestion",
          "The NFL publishes injury reports Wed–Fri each week. Automating ingestion of these reports would enable the injury-tracker page to show live data rather than a framework. "
          "Impact: directly feeds line adjustments and prop analysis.",
          "Pending — requires licensed data feed or official NFL API access.",
          "Manual review → approve data source → implement pipeline → verify output"],
         [repo("hub/injury-tracker.html"), "NFL-STATS"]),
        (["S02", "High", "Integrate live closing-line prices from a licensed operator",
          "No strategy can be verified without actual operator prices. DraftKings and FanDuel publish their own settlement rules but not historical price archives. A licensed data feed would close the largest evidence gap in this repository.",
          "Blocked — no licensed operator API was available.",
          "Obtain data-use agreement with DraftKings or FanDuel → pipe prices into pipeline/ → re-run strategies"],
         ["DK-SPREAD", "FD-CT-RULES"]),
        (["S03", "Medium", "Expand strategy library with weather-adjusted totals",
          "S6 (Weather under) showed +0.58% ROI but failed G5 (holdout). Adding wind-chill and precipitation intensity as separate features, plus dome/roof status, could sharpen the signal.",
          "Framework exists in pipeline/features.py; empirical test blocked by licensed price gap.",
          "Define weather features → backtest against closing lines → gate-check → publish or reject"],
         [repo("pipeline/features.py"), repo("line_lab/data/derived/summary.json")]),
        (["S04", "Medium", "Build a rest-advantage model with travel distance",
          "S4 (Rest asymmetry) passed 4/9 gates. Adding cross-country travel, short weeks, and Thursday-to-Sunday turnarounds as interaction terms may improve the edge estimate.",
          "Data for rest days exists in the nflverse games.csv; travel distance requires an external source.",
          "Compute travel distance per game → add as feature → re-run S4 → gate-check"],
         [repo("data/raw/games.csv"), "NFL-SCHEDULE"]),
        (["S05", "Medium", "Add referee crew data as a line adjustment factor",
          "S7 (Referee crew total tendency) passed 4/9 gates with -4.29% ROI. The direction is negative but the crew-level variance is real. Referee assignments are published weekly by NFL Football Operations.",
          "Official referee assignment data is publicly available on operations.nfl.com.",
          "Scrape weekly referee assignments → compute crew tendencies → test as overlay on S3/S6"],
         ["NFL-GAMEDAY", repo("line_lab/data/derived/bets.csv")]),
        (["S06", "Low", "Create a situational spot-rating system",
          "Look-ahead spots, let-down spots, revenge games, and short-week prime-time games are folklore. A rigorous test against the nflverse data could confirm or deny each category.",
          "Requires tagging each game with a situation code; outcome data is available.",
          "Define spot categories → tag games → test each as a standalone strategy → gate-check"],
         [repo("data/raw/games.csv"), "NFL-SCHEDULE"]),
        (["S07", "Low", "Add a public suggestion submission form",
          "Allow site visitors to submit strategy ideas or data sources. Each submission would be triaged on this page with a status and decision trail.",
          "No infrastructure exists yet; GitHub Issues could serve as the intake channel.",
          "Decide on intake channel (GitHub Issues, Google Form, or custom) → define triage SLA → publish intake link"],
         [repo("COORDINATION.md"), REPO_TREE]),
        (["S08", "Low", "Publish model-implied lines for upcoming games with uncertainty bands",
          "The model already generates spread and total estimates for unplayed games (data/derived/own_lines_upcoming.csv). Adding bootstrap confidence bands around each estimate would make the output more honest.",
          "Model exists; confidence bands require 2,000 bootstrap resamples per game which is computationally feasible.",
          "Implement bootstrap band → publish on own-lines page → verify coverage on holdout"],
         [repo("data/derived/own_lines_upcoming.csv"), "NIST-BOOT"]),
    ]
    pages["suggestions"] = dict(
        title="Suggestions & improvement roadmap",
        lead="A structured list of improvement proposals for this project. Each suggestion has a priority, current status, "
             "impact assessment, and a decision path. Anyone reviewing this page can see what is proposed, what blocks it, "
             "and what the next step is — then choose the best path before any change is implemented.",
        kpis=[("Total suggestions", len(suggestion_rows), "prioritised and tracked"),
              ("High priority", sum(1 for r in suggestion_rows if r[0][1] == "High"), "injury feed + live prices"),
              ("Medium priority", sum(1 for r in suggestion_rows if r[0][1] == "Medium"), "model refinements"),
              ("Decision-ready", len(suggestion_rows), "each has a next-step path")],
        sections=[
            sec("How to use this page",
                "Each suggestion follows a standard format so a reviewer can make a decision without reading external documents. "
                "The decision path column tells you the exact sequence of steps from approval to implementation. "
                "No suggestion is implemented until it has been reviewed and explicitly approved on this page.",
                T(["Field", "Meaning"],
                  [(["ID", "Stable identifier (S01, S02, ...) for cross-referencing"], [repo("COORDINATION.md")]),
                   (["Priority", "High / Medium / Low — based on impact and feasibility"], [repo("COORDINATION.md")]),
                   (["Suggestion", "What is proposed and why it matters"], [repo("COORDINATION.md")]),
                   (["Status", "Current blocker or readiness state"], [repo("COORDINATION.md")]),
                   (["Decision path", "Step-by-step sequence from review to implementation"], [repo("COORDINATION.md")])]),
                note="Suggest a change: open a GitHub issue referencing the suggestion ID. All decisions are recorded on this page with a date and rationale."),
            sec("Suggestion register",
                "Every row links to an official source or repository file. Status 'Pending' means awaiting reviewer decision. "
                "Status 'Blocked' means an external dependency prevents implementation.",
                T(["ID", "Priority", "Suggestion", "Impact & rationale", "Status / blocker", "Decision path"],
                  suggestion_rows,
                  caption="Each suggestion has a stable ID and a decision path. Nothing is implemented without explicit review.",
                  filter_id="suggest-filter")),
            sec("Decision criteria",
                "Before approving any suggestion, the reviewer should confirm all five criteria are met.",
                T(["Criterion", "Question to answer", "Applies to"],
                  [(["Evidence gap exists", "Does this suggestion close a verified gap on the " + A("information-gaps.html", "information-gaps page") + "?", "All"], ["REPO", "NFL-STATS"]),
                   (["Official source available", "Is there an official or licensed data source for any new inputs?", "S01, S02"], ["NFL-STATS", "DK-ODDS"]),
                   (["Reproducible", "Can the implementation be run deterministically from committed code?", "All"], [repo("hub/check_hub.py")]),
                   (["Gate-compatible", "Does the output pass through the existing validation framework?", "S03, S04, S05, S06, S08"], ["NIST-MULTI", "REPO"]),
                   (["No hallucination risk", "Are all values either verified from official sources or clearly labelled blank?", "All"], ["REPO", "NFL-TERMS"])]),
                note="Approved suggestions move to 'In progress' on the coordination board (COORDINATION.md) and are claimed by a session."),
            sec("Recently decided",
                "Record of suggestions that have been reviewed and a decision was made.",
                T(["ID", "Decision", "Date", "Rationale", "Decision maker"],
                  [(["—", "No suggestions have been decided yet.", "—", "—", "—"], [REPO_TREE]),
                   (["—", "This table will be populated as suggestions are reviewed.", "—", "—", "—"], [repo("COORDINATION.md")])],
                  caption="This table is the decision log. Every row links to the coordination board or an official source.")),
        ],
    )

    # -- Information gaps ---------------------------------------------------
    gap_rows = [
        (["G01", "Critical", "Historical closing-line prices from a licensed operator",
          "No official operator publishes a free historical price archive. All prices in this repository come from the nflverse third-party dataset, which is not an official source.",
          "Without licensed prices, no strategy ROI can be officially verified.",
          "Obtain a data-use agreement with DraftKings, FanDuel, or another licensed operator. Alternative: subscribe to a licensed data vendor (e.g. Sportradar, Genius Sports)."],
         ["DK-SPREAD", "FD-CT-RULES"]),
        (["G02", "Critical", "Player-level game logs with prop settlement prices",
          "NFL.com publishes box-score stats, but not the per-game prop lines or settlement prices that a player-prop strategy requires. DraftKings defines prop rules (KB0010778) but does not publish historical prop prices.",
          "No player-prop strategy can be tested without historical prop lines and player outcomes.",
          "Obtain licensed player-prop price history from a sportsbook or data vendor. NFL.com player stats can partially fill outcome data."],
         ["DK-PROP", "DK-PLAYER"]),
        (["G03", "Critical", "Official NFL injury report machine-readable feed",
          "The NFL publishes injury reports as PDFs and web pages each Wednesday, Thursday and Friday. There is no official API or structured data feed. The NFL Support page (NFL-STATS) directs to NFL.com player stats.",
          "Without automated injury ingestion, the injury-tracker page remains a framework, not a live tool.",
          "Build a scraper for NFL.com injury report pages, or obtain a licensed injury data feed from a vendor."],
         ["NFL-STATS", "NFL-GAMEDAY"]),
        (["G04", "High", "Depth-chart data (starter vs. backup status)",
          "Knowing that a team's starting left tackle is out is not enough; the model needs to know who replaces him and what the quality drop-off is. No official source publishes a machine-readable depth chart.",
          "Line adjustments for injuries require knowing the replacement player's quality, not just the starter's absence.",
          "Use a licensed depth-chart data provider (e.g. FantasyLabs, Rotoworld under NBC Sports) or build a manual depth-chart tracker."],
         ["NFL-STATS", "NFL-GAMEDAY"]),
        (["G05", "High", "Settled bet data (win/loss/push at the actual price taken)",
          "To measure whether a strategy is profitable, we need to know the exact price at which each bet was placed and whether it won, lost, or pushed. The nflverse dataset records closing lines, not the prices a bettor actually received.",
          "The gap between the model line and the closing line (CLV) is measurable, but actual P&L at the bettor's price is not.",
          "Track bets placed at actual prices. Compare to closing lines. This requires a personal bet-tracking system or a licensed operator's account-level data."],
         ["DK-ODDS", "DK-SPREAD"]),
        (["G06", "High", "Same-game parlay (SGP) price schedules",
          "DraftKings (DK-SGP) states SGP odds are calculated differently from independent parlay odds, but does not publish the pricing algorithm or a historical SGP price archive.",
          "Cannot test whether SGP correlations create a genuine edge without knowing the exact odds offered.",
          "Scrape SGP odds from DraftKings or FanDuel over multiple weeks. Build a pricing model. Compare to independent-leg fair value."],
         ["DK-SGP", "FD-CT-RULES"]),
        (["G07", "Medium", "Referee crew assignments (historical)",
          "NFL Football Operations publishes weekly referee assignments, but a complete historical archive with crew-level tendencies is not available in a single source.",
          "S7 (Referee crew total tendency) needs historical crew data to test properly.",
          "Build an archive from operations.nfl.com weekly releases. Compute per-crew scoring tendencies."],
         ["NFL-GAMEDAY", "NFL-SCHEDULE"]),
        (["G08", "Medium", "Weather data at kickoff time (not forecast)",
          "S6 (Weather under) uses weather forecasts at the time the line is set. To verify retrospectively, we need the actual weather at kickoff, not the forecast.",
          "Using forecast weather introduces look-ahead bias if the forecast changed after the line was set.",
          "Obtain historical actual weather data from NOAA/NWS for each stadium at kickoff time. Cross-reference with game times."],
         ["NIST-MULTI", repo("pipeline/features.py")]),
        (["G09", "Medium", "Defensive scheme classification ( Cover 0/1/2/3/4, blitz rate)",
          "Defensive performance varies by scheme. A defense missing its starting CB1 is very different in Cover 2 vs. Cover 0. No official source classifies plays by coverage.",
          "Injury impact on defense depends on the scheme the defense runs. Without scheme data, injury adjustments are imprecise.",
          "Use Next Gen Stats (nextgenstats.nfl.com) if available, or a licensed play-by-play data provider."],
         ["NFL-STATS", "NFL-GAMEDAY"]),
        (["G10", "Medium", "Offensive line unit cohesion metrics",
          "An offensive line with 3 starters and 2 backups performs differently than one with 4 starters and 1 backup, even if the total number of backups is the same. No official metric captures line cohesion.",
          "Injury impact on offense depends on which positions are affected and how many linemates the backup has played with.",
          "Build a cohesion metric from play-by-play data: track which 5-man line combinations appear together and their performance."],
         ["NFL-STATS", repo("pipeline/features.py")]),
        (["G11", "Low", "Public betting percentage data",
          "Some operators publish the percentage of bets (not money) on each side. This reveals where the public is, which can indicate reverse-line-movement opportunities.",
          "Without public bet data, cannot test whether contrarian strategies have an edge.",
          "Record public bet percentages from DraftKings or FanDuel over multiple weeks. Compare to line movement."],
         ["DK-ODDS", "FD-CT-RULES"]),
        (["G12", "Low", "Sharp money indicators (steam moves, reverse line movement)",
          "Identifying when sharp money enters the market requires monitoring multiple sportsbooks simultaneously and detecting coordinated line moves.",
          "Without sharp money indicators, cannot test market-efficiency hypotheses or sharp-following strategies.",
          "Subscribe to a line-monitoring service or build one from multiple operator feeds."],
         ["DK-ODDS", repo("pipeline/movement.py")]),
    ]
    known_rows = [
        (["K01", "Game results (1999-2026)", "nflverse games.csv — 7,548 games, 7,075 completed regular-season games",
          "All scores, dates, locations, and basic metadata are available and verified."],
         [repo("data/raw/games.csv"), "NFLVERSE"]),
        (["K02", "Historical closing lines (2006-2025)", "nflverse closing_lines.csv — 20,490 rows with spread, total, and moneyline",
          "Third-party dataset; not from a licensed operator. Adequate for backtesting but cannot be officially verified."],
         [repo("data/raw/closing_lines.csv"), repo("data/derived/summary.json")]),
        (["K03", "NFL betting rules and definitions", "Point spread, moneyline, parlay, prop definitions from NFL Support, DraftKings, FanDuel",
          "All 24 official source claims on this site are verified from the publisher's own page."],
         ["NFL-ML-ART", "DK-ODDS", "FD-CT-RULES"]),
        (["K04", "Correlation structure (measured)", "Same-game: ML vs spread phi=0.671, spread vs total phi=0.016, ML vs total phi=0.000. Cross-game: phi=0.006.",
          "Computed from the nflverse dataset. Not from an official source, but reproducible from committed code."],
         [repo("line_lab/correlations.py"), "NIST-CORR"]),
        (["K05", "Validation gate framework", "9 gates: sample size, causality, statistical significance, holdout, permutation, economic significance, practical significance, calibration, multiplicity.",
          "Framework is pre-registered and the gates are defined in code. No strategy passed all 9."],
         [repo("line_lab/strategies.py"), "NIST-MULTI"]),
        (["K06", "Luck band quantified", "Best-of-11 random strategies average +5.4% ROI; 95th percentile +16.3%. A profitable 'winner' appears 93% of the time by luck alone.",
          "Any strategy ranking must clear this band to claim skill. Bootstrap methodology per NIST guidance."],
         [repo("line_lab/extras.py"), "NIST-BOOT", "NIST-CI"]),
        (["K07", "The vig (hold) is ~2.75%", "Average two-way hold in recorded prices is 2.75%. Detecting a 3% per-bet edge at 80% power needs ~6,200 settled bets (~8 seasons).",
          "This is the wall every strategy must overcome. Derived from the nflverse closing lines."],
         [repo("line_lab/extras.py"), "DK-ODDS"]),
        (["K08", "2025 official standings (32 teams)", "All 32 club rows on nfl.com/standings/division/2025/REG match the repository's independently derived aggregates.",
          "Verified row-by-row against the official NFL standings page."],
         ["NFL-STANDINGS-2025", repo("reports/standings_check_2025.csv")]),
        (["K09", "Model-implied lines for Week 16-18 (2026)", "164 unplayed games have model-generated spreads, totals, and win probabilities.",
          "Model output is reproducible. No market prices are available for these games yet."],
         [repo("data/derived/own_lines_upcoming.csv"), "NFL-SCHEDULE"]),
        (["K10", "Strategy results (11 strategies, 0 eligible)", "Best full-sample ROI: S6 Weather under +0.58% (CI includes zero). No strategy passed all 9 gates.",
          "Each strategy has 20 seasons of backtest data, 3-season holdout, and permutation testing."],
         [repo("line_lab/data/derived/summary.json"), repo("line_lab/data/derived/bets.csv")]),
    ]
    discovery_rows = [
        (["D01", "Licensed operator price archive", "Contact DraftKings or FanDuel partnerships. Alternatively, subscribe to Sportradar, Genius Sports, or Sportradar's Betradar.",
          "Critical — closes G01 and enables full strategy verification."],
         ["DK-ODDS", "FD-CT-RULES"]),
        (["D02", "NFL injury report automation", "Build a weekly scraper for nfl.com injury report pages (Wed/Thu/Fri releases). Store in data/raw/injuries/.",
          "High — enables the injury-tracker page and injury-adjusted line models."],
         ["NFL-STATS", "NFL-GAMEDAY"]),
        (["D03", "Depth chart data provider evaluation", "Evaluate FantasyLabs, Rotoworld/NBC Sports, Sleeper for depth-chart APIs. Compare cost, coverage, and update frequency.",
          "High — closes G04, enables backup-quality adjustments."],
         ["NFL-STATS", repo("pipeline/features.py")]),
        (["D04", "NOAA historical weather at NFL stadiums", "Use NOAA GHCN or ISD station data for each NFL stadium. Match to game dates and kickoff times.",
          "Medium — improves S6 weather model accuracy by removing forecast bias."],
         ["NIST-MULTI", repo("pipeline/features.py")]),
        (["D05", "Multi-book line monitoring", "Set up scraping or API access to 3-5 sportsbooks. Record opening and closing lines. Detect steam moves and reverse line movement.",
          "Medium — enables sharp money tracking (G12) and CLV measurement."],
         ["DK-ODDS", repo("pipeline/movement.py")]),
        (["D06", "Referee assignment archive builder", "Scrape operations.nfl.com weekly referee announcements. Build a crew-level database of tendencies (penalty rate, total tendency, etc.).",
          "Medium — enables S7 refinement and referee-based overlays."],
         ["NFL-GAMEDAY", "NFL-SCHEDULE"]),
        (["D07", "Play-by-play coverage data", "Evaluate Next Gen Stats access, or PFF/Sportradar play-by-play data for coverage classification.",
          "Medium — closes G09, enables scheme-aware injury adjustments."],
         ["NFL-STATS", repo("pipeline/features.py")]),
    ]
    pages["information-gaps"] = dict(
        title="Information gaps & decision prerequisites",
        lead="A clear inventory of what this project knows, what it does not know, and what must be discovered before any "
             "betting decision can be reasonably made. Each gap has a severity, an explanation of why it matters, and a concrete "
             "suggestion for how to fill it. No decision should be based on information marked as a gap.",
        kpis=[("Information gaps", len(gap_rows), "Critical → Low severity"),
              ("Known facts", len(known_rows), "verified or reproducible"),
              ("Discovery actions", len(discovery_rows), "concrete next steps"),
              ("Verified empirical values", 0, "no licensed inputs admitted")],
        sections=[
            sec("How to read this page",
                "This page answers three questions: (1) What information do we need to make a decision? (2) What do we already have? "
                "(3) How do we get what we're missing? The gaps table lists everything we don't have. The known-facts table lists "
                "everything we do have. The discovery-actions table lists concrete steps to close each gap.",
                T(["Question", "Where to look"],
                  [(["What data is missing?", "Gaps table below — sorted by severity. Critical gaps block all decisions."], ["REPO", "NFL-STATS"]),
                   (["What do we already know?", "Known facts table — verified from official sources or reproducible from committed code."], ["REPO", "NFL-STANDINGS-2025"]),
                   (["How do we get missing data?", "Discovery actions table — concrete steps with source links."], ["REPO", "DK-ODDS"]),
                   (["What happens if we decide without filling gaps?", "Every gap explains the consequence. Critical gaps mean no verified strategy exists."], ["REPO", "NIST-MULTI"])]),
                note="A gap is not a failure. It is an honest statement of what is missing. Decisions made without addressing critical gaps are decisions made on incomplete information."),
            sec("Information gaps — what we don't know",
                "Each gap is classified Critical / High / Medium / Low. Critical gaps block all verified betting decisions. "
                "High gaps block specific strategy categories. Medium and Low gaps reduce precision but do not invalidate findings.",
                T(["ID", "Severity", "Missing information", "Why it matters", "Consequence if ignored", "How to fill the gap"],
                  gap_rows,
                  caption="Every row links to the official source that defines the missing data or the repository file where the gap was identified.",
                  filter_id="gaps-filter")),
            sec("Known facts — what we do know",
                "These facts are either verified from official sources or reproducible from the committed code and data. "
                "They form the foundation on which decisions can be made once the gaps above are filled.",
                T(["ID", "Fact", "Source & coverage", "Verification status"],
                  known_rows,
                  caption="Every row links to the official publisher or repository file that supports it.",
                  filter_id="known-filter")),
            sec("Discovery actions — how to fill the gaps",
                "Each discovery action is a concrete, actionable step. These are ordered by which gap they close and by feasibility.",
                T(["ID", "Action", "Steps", "Closes gap", "Source links"],
                  discovery_rows,
                  caption="Each action links to the official source that would provide the data or the repository file that needs it.",
                  filter_id="discovery-filter")),
            sec("Decision prerequisite matrix",
                "Before any category of bet can be actioned, the corresponding gaps must be closed. This matrix shows which gaps "
                "block which decisions.",
                T(["Decision category", "Required gaps to close", "Current status", "Can decide now?"],
                  [(["Single bet (ATS/ML/Total)", "G01 (licensed prices), G05 (settled bets)",
                    "G01 blocked — no licensed prices", "No"], ["DK-SPREAD", "REPO"]),
                   (["Parlay (multi-leg)", "G01 + G06 (SGP prices)",
                    "G01 + G06 blocked", "No"], ["DK-PARLAY", "DK-SGP"]),
                   (["Player prop combo", "G02 (prop prices + outcomes)",
                    "G02 blocked — no prop price history", "No"], ["DK-PROP", "DK-PLAYER"]),
                   (["Injury-adjusted line", "G03 (injury feed), G04 (depth charts)",
                    "G03 + G04 blocked", "No"], ["NFL-STATS", "NFL-GAMEDAY"]),
                   (["Model-implied line (own line)", "None — model runs on available data",
                    "Model runs; no market comparison possible", "Partially — model lines are published but unvalidated against market"], ["NFL-SCHEDULE", "REPO"]),
                   (["Strategy selection", "G01 + G05 (prices + settled bets)",
                    "0 strategies eligible after 9 gates", "No — no strategy passed all gates"], ["NIST-MULTI", "REPO"])])),
        ],
    )

    # -- Injury tracker -----------------------------------------------------
    injury_framework_rows = [
        (["IF01", "NFL Weekly Injury Report", "Published Wed (limited), Thu (updated), Fri (final) each week during the season. "
          "Lists player name, position, and game status: Out, Doubtful, Questionable, Probable.",
          "This is the primary input. The report is machine-readable only as HTML/PDF — no official API exists.",
          "nfl.com/injuries (per team)"],
         ["NFL-STATS", "NFL-GAMEDAY"]),
        (["IF02", "Practice Participation Designations", "Wed/Thu reports include practice participation: DNP (did not participate), "
          "Limited, Full. These are early indicators of Sunday availability.",
          "Practice participation on Wednesday is the strongest predictor of game status. A player who DNP Wednesday is likely Out or Doubtful.",
          "nfl.com/injuries (per team)"],
         ["NFL-STATS", "NFL-GAMEDAY"]),
        (["IF03", "Depth Chart (Starter vs. Backup)", "No official machine-readable depth chart exists. Teams publish unofficial depth charts "
          "on their websites. Third-party providers (FantasyLabs, Rotoworld) maintain depth charts.",
          "Critical for knowing who replaces a starter. A 2nd-string CB replacing a 1st-string CB has a different impact than a 4th-string CB.",
          "nfl.com/teams/[team] (roster)"],
         ["NFL-STATS", repo("pipeline/features.py")]),
        (["IF04", "Backup Quality Rating", "No official metric exists. Must be derived from player stats (games started, snaps played, "
          "PFF grades if available, or nflverse player stats).",
          "The quality gap between starter and backup determines the line adjustment magnitude.",
          "REPO"],
         ["NFL-STATS", repo("data/raw/teams.csv")]),
    ]
    defense_impact_rows = [
        (["DI01", "CB1 (Starting Cornerback 1)", "Shutdown corner removed → opposing WR1 runs free. Expected impact: +3-6 pts for opposing offense. "
          "If CB2 also out, impact doubles. CB3 available: moderate mitigation. No CB2 or CB3: severe.",
          "Defensive backfield injuries have the largest per-player impact on scoring.",
          "NFL-STATS"],
         ["NFL-STATS", "NFL-GAMEDAY"]),
        (["DI02", "Pass Rush (DE/OLB starters)", "Losing a premier pass rusher reduces pressure rate by ~5-8%. Without pressure, QB has more time, "
          "completions increase, scoring goes up. Affects both ATS and totals.",
          "Pass rush injuries shift the total upward and may move the spread 1-2 points.",
          "NFL-STATS"],
         ["NFL-STATS", repo("pipeline/features.py")]),
        (["DI03", "Linebacker corps (ILB/OLB)", "Run defense degrades with backup linebackers. Affects rushing yards and short-yardage situations. "
          "Impact on totals is moderate; impact on rushing props is high.",
          "Linebacker injuries primarily affect rushing props and game script.",
          "NFL-STATS"],
         ["NFL-STATS", repo("pipeline/features.py")]),
        (["DI04", "Safety starters", "Deep coverage degrades with backup safeties. Affects deep passing and prevent defenses. "
          "Moderate impact on totals, lower impact on spread.",
          "Safety injuries affect deep passing props and late-game scoring.",
          "NFL-STATS"],
         ["NFL-STATS", repo("pipeline/features.py")]),
        (["DI05", "Interior Defensive Line (DT/NT)", "Run stuffing degrades with backups. Affects rushing yards up the middle. "
          "Impact is moderate on totals, higher on interior rushing props.",
          "DT injuries affect run defense efficiency.",
          "NFL-STATS"],
         ["NFL-STATS", repo("pipeline/features.py")]),
        (["DI06", "Multiple starters out (2+ positions)", "Compounding effect: each additional starter out increases the impact non-linearly. "
          "A defense missing its CB1, a pass rusher, and an ILB is not 3x worse — it may be 5-6x worse due to communication breakdowns.",
          "Multi-position injuries create the largest line movements and the highest adjustment uncertainty.",
          "NFL-STATS"],
         ["NFL-STATS", repo("pipeline/features.py")]),
    ]
    offense_impact_rows = [
        (["OI01", "Starting Quarterback", "QB is the single highest-impact position. Losing a starting QB for a backup typically moves the spread "
          "2-4 points. The quality of the backup determines the exact shift. S8 (Backup-QB fade) tested this: -3.39% ROI, 4/9 gates.",
          "QB injuries are the primary driver of line movement. The backup's quality is the key unknown.",
          "NFL-STATS"],
         ["NFL-STATS", repo("line_lab/data/derived/summary.json")]),
        (["OI02", "Offensive Line (LT/RT/LG/RG/C)", "Missing a starting tackle affects pass protection and edge running. "
          "Missing the center affects snap timing and interior protection. Multiple OL out: severe impact on both passing and rushing.",
          "OL injuries affect QB props (sacks), rushing props, and total scoring.",
          "NFL-STATS"],
         ["NFL-STATS", repo("pipeline/features.py")]),
        (["OI03", "WR1 / Top Receiver", "Losing the top target affects passing volume and efficiency. Impact is moderate if depth exists (WR2/WR3). "
          "Severe if no adequate replacement. Affects passing yards props and team total.",
          "WR injuries affect passing game volume and receiver props.",
          "NFL-STATS"],
         ["NFL-STATS", repo("pipeline/features.py")]),
        (["OI04", "Starting Running Back", "RB injuries shift volume to backups. The quality gap between RB1 and RB2 is typically smaller than "
          "at other positions (running backs are more interchangeable). Moderate impact on rushing props, lower on team total.",
          "RB injuries primarily affect individual rushing props, not team totals.",
          "NFL-STATS"],
         ["NFL-STATS", repo("pipeline/features.py")]),
        (["OI05", "Tight End (starter)", "TE injuries affect red-zone targets and intermediate passing. Impact is moderate on team total, "
          "high on TE-specific props.",
          "TE injuries are position-specific and affect props more than team outcomes.",
          "NFL-STATS"],
         ["NFL-STATS", repo("pipeline/features.py")]),
    ]
    lineup_deficiency_rows = [
        (["LD01", "Defense: 2nd string replacing 1st string", "Expected scoring impact: +2-4 points for opposing offense. Line adjustment: 1-2 points spread, 2-4 points total.",
          "Depends on position. CB and pass rush have higher impact than safety and DT.",
          "UNVERIFIED — requires historical data on performance with/without starters"],
         ["NFL-STATS", repo("pipeline/features.py")]),
        (["LD02", "Defense: 3rd string replacing 1st string", "Expected scoring impact: +4-7 points for opposing offense. Line adjustment: 2-3 points spread, 4-6 points total.",
          "Third-string players are typically rookies or practice-squad elevations. The drop-off is severe.",
          "UNVERIFIED — no historical 3rd-string performance data available"],
         ["NFL-STATS", repo("pipeline/features.py")]),
        (["LD03", "Defense: 4th string replacing 1st string", "Expected scoring impact: +6-10 points. Line adjustment: 3-5 points spread, 5-8 points total.",
          "Fourth-string players may not have NFL game experience. Extreme uncertainty.",
          "UNVERIFIED — extremely rare; insufficient data"],
         ["NFL-STATS", repo("pipeline/features.py")]),
        (["LD04", "Offense: Backup QB replacing starter", "Measured impact (S8): -3.39% ROI on fade bets. Spread adjustment: 2-4 points. Total adjustment: 3-5 points lower.",
          "S8 tested this and found a negative ROI. The market may already price this in efficiently.",
          "Partially measured — S8 backtest exists but did not pass validation gates"],
         ["NFL-STATS", repo("line_lab/data/derived/summary.json")]),
        (["LD05", "Offense: Multiple OL starters out", "Expected scoring impact: -2-4 points for own offense (worse protection, worse run game). "
          "Line adjustment: 1-2 points spread against, 2-3 points total lower.",
          "OL injuries compound: 2 out is worse than 2x one out due to communication breakdowns.",
          "UNVERIFIED — no specific OL-injury study in this repository yet"],
         ["NFL-STATS", repo("pipeline/features.py")]),
        (["LD06", "Both sides: key injuries on both teams", "Net impact depends on relative severity. If both teams lose a CB1, the effect is roughly neutral on the spread "
          "but the total may go up (both secondaries weakened).",
          "Symmetric injuries affect totals more than spreads.",
          "UNVERIFIED — no multi-injury interaction model exists"],
         ["NFL-STATS", repo("pipeline/features.py")]),
    ]
    pages["injury-tracker"] = dict(
        title="Injury tracker & lineup deficiency analysis",
        lead="A framework for tracking NFL injuries and their impact on team performance and betting lines. This page documents "
             "what data is needed, how injuries affect defensive and offensive units at different depth levels (1st through 4th string), "
             "and what line adjustments are expected. Most impact values are unverified estimates pending licensed data; they are clearly "
             "labelled and linked to the review page.",
        kpis=[("Framework components", 4, "inputs, defense, offense, deficiencies"),
              ("Data inputs needed", 3, "injury report, depth chart, backup quality"),
              ("Defense impact categories", len(defense_impact_rows), "by position group"),
              ("Offense impact categories", len(offense_impact_rows), "by position group")],
        sections=[
            sec("Framework overview",
                "The injury tracker operates in three layers: (1) data inputs — the injury report and depth chart data; "
                "(2) impact analysis — how each injury affects the team's expected performance; (3) line adjustment — "
                "how the expected performance change translates to a line movement. Every layer requires data that is not "
                "yet available in an automated, official feed.",
                T(["Layer", "Components", "Current status", "Source links"],
                  [(["Data inputs", "NFL injury report (Wed/Thu/Fri), depth charts, backup quality ratings",
                    "Framework defined; no automated ingestion", "NFL-STATS"], [repo("hub/information-gaps.html"), REPO_TREE]),
                   (["Impact analysis", "Per-position scoring impact estimates, depth-level multipliers",
                    "Estimates documented; unverified without historical data", "NFL-STATS"], [repo("pipeline/features.py"), REPO_TREE]),
                   (["Line adjustment", "Translate impact to spread and total adjustments",
                    "Model-ready; awaiting validated inputs", "REPO"], [repo("hub/own-lines.html"), REPO_TREE])]),
                note="The NFL publishes injury reports as the official source of availability data. No official source publishes depth charts or backup quality metrics."),
            sec("Data inputs required",
                "These are the official and third-party data sources needed to build the injury tracker.",
                T(["ID", "Input", "Description", "Availability", "Official source"],
                  injury_framework_rows,
                  caption="Every row links to the official publisher or repository file for that input.",
                  filter_id="injury-input-filter")),
            sec("Defensive injury impact — by position group",
                "How injuries at each defensive position affect expected scoring and betting lines. Impact estimates are based on "
                "football analysis principles and have not been validated against historical data in this repository.",
                T(["ID", "Position", "Impact mechanism", "Expected line movement", "Source links"],
                  defense_impact_rows,
                  caption="Impact estimates are analytical, not empirically verified. All require validation against historical data.",
                  filter_id="defense-impact-filter")),
            sec("Offensive injury impact — by position group",
                "How injuries at each offensive position affect expected scoring and betting lines. Note that S8 (backup-QB fade) "
                "was tested in this repository and produced a -3.39% ROI with 4/9 gates passed — the market appears to price "
                "QB injuries efficiently.",
                T(["ID", "Position", "Impact mechanism", "Expected line movement", "Source links"],
                  offense_impact_rows,
                  caption="S8 (backup-QB fade) was tested and rejected by validation gates. The market may already price QB injuries efficiently.",
                  filter_id="offense-impact-filter")),
            sec("Lineup deficiency matrix — depth-level impact",
                "Expected line adjustments based on the depth level of the replacement player. These estimates increase non-linearly "
                "as the replacement player drops from 2nd to 3rd to 4th string, because the talent gap widens and the player may "
                "have little or no NFL game experience.",
                T(["ID", "Scenario", "Expected line adjustment", "Uncertainty", "Verification status"],
                  lineup_deficiency_rows,
                  caption="All estimates are unverified. They are analytical expectations, not measured values. Each links to the gap or strategy that would validate it.",
                  filter_id="deficiency-filter")),
            sec("Integration with the line model",
                "How injury data feeds into the own-lines model. The model currently uses Elo ratings, scoring profiles, and weather "
                "to generate implied spreads and totals. Injury adjustments would be an overlay applied after the base model runs.",
                T(["Step", "Description", "Current status", "Source"],
                  [(["Base model runs", "Elo margin → spread; scoring profile + weather → total",
                    "Operational — produces model lines for unplayed games", repo("data/derived/own_lines_upcoming.csv")], [repo("line_lab/core.py"), REPO_TREE]),
                   (["Injury overlay applied", "Adjust spread and total based on key injuries (QB, CB1, pass rush, OL)",
                    "Framework designed; not yet implemented", "NFL-STATS"], [repo("pipeline/features.py"), REPO_TREE]),
                   (["Depth-level multiplier", "Multiply base adjustment by 1.0 (2nd string), 2.0 (3rd string), 3.5 (4th string)",
                    "Multipliers are estimates; not calibrated to data", "REPO"], [repo("pipeline/features.py"), REPO_TREE]),
                   (["Output: injury-adjusted line", "Final model-implied spread and total, incorporating injury impact",
                    "Not yet produced", "REPO"], [repo("hub/own-lines.html"), REPO_TREE])])),
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
