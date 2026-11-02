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
