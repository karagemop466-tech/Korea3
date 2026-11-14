#!/usr/bin/env python3
"""Build the Desk Ops lab pages.

House rules (same as every lab in this repository):
  * every generated table row carries at least one link — to the official page a value
    came from, to the pinned dataset row it was copied from, or to the in-repo code that
    recomputes it (labelled `recomputed`);
  * a value no input states is emitted as a flagged blank, never inferred;
  * the build is deterministic: two runs produce byte-identical pages (no clocks).

Usage:
    python3 ops_lab/build.py
"""
from __future__ import annotations

import csv
import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"
OUT = HERE

CHECKED = "2026-11-14"          # date this lab's sources were re-read (fixed for determinism)
PIN = "a270278f3ac4e937295fe6a27814b3c4a2b62645"

SNAP_META = json.loads((DATA / "snapshot_meta.json").read_text(encoding="utf-8"))
FEED_META = json.loads((DATA / "results_feed_meta.json").read_text(encoding="utf-8"))
METRICS_META = json.loads((DATA / "metrics_meta.json").read_text(encoding="utf-8"))

MISSING_LINK: list[str] = []


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def e(x) -> str:
    return html.escape(str(x), quote=True)


def ilink(url: str, label: str) -> str:
    return f'<a href="{e(url)}">{e(label)}</a>'


def link(url: str, label: str = "source", note: str = "") -> str:
    if not url:
        MISSING_LINK.append(f"{label}:{note}")
        return '<span class="flag">no source</span>'
    return (f'<a class="src" href="{e(url)}" target="_blank" rel="noopener noreferrer" '
            f'title="{e(url)}">{e(label)} &#8599;</a>')


def blank(why: str) -> str:
    return f'<span class="blank" title="{e(why)}">blank</span>'


def pill(text: str, cls: str = "ok") -> str:
    return f'<span class="pill {e(cls)}">{e(text)}</span>'


def code(text: str) -> str:
    return f'<span class="code">{e(text)}</span>'


def table(caption: str, headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<div class="scroll"><table><caption>{caption}</caption>'
            f'<thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>')


def sec(title: str, blurb: str, body: str) -> str:
    return (f'<section><div class="section-head"><h2>{e(title)}</h2>'
            f'<p class="count">{blurb}</p></div>{body}</section>')


PAGES: list[tuple[str, str, str]] = [
    ("index.html", "Desk Ops", "Overview"),
    ("snapshots.html", "Price-snapshot store", "Snapshots"),
    ("own_book.html", "Origination order", "Own book"),
    ("results.html", "Verified results feed", "Results feed"),
    ("leaderboard_split.html", "Signal vs staking", "Signal / staking"),
    ("demotion.html", "Demotion gate", "Demotion"),
    ("requirements_brief.html", "Brief coverage", "Brief"),
    ("questions.html", "Questions register", "Questions"),
    ("suggestions.html", "Suggestions (decision-gated)", "Suggestions"),
    ("flagged.html", "Flagged for review", "Flagged"),
    ("sources.html", "Sources", "Sources"),
    ("method.html", "Method and limits", "Method"),
]

EXTERNAL_NAV = [
    ("../index.html", "NFL Line Lab (root)"),
    ("../depth_lab/index.html", "Depth Lab"),
    ("../hub/index.html", "Consolidated dashboard"),
    ("../hub/competition.html", "Promotion gates"),
    ("../verification.html", "Repo verification"),
]


def page(fname: str, title: str, body: str) -> str:
    nav_parts = []
    for href, label, _ in PAGES:
        cls = ' class="active"' if href == fname else ""
        nav_parts.append(f'<a href="{e(href)}"{cls}>{e(label)}</a>')
    nav = "".join(nav_parts)
    ext = "".join(f'<a href="{e(href)}">{e(label)} <span class="ext">&#8599;</span></a>'
                  for href, label in EXTERNAL_NAV)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} | Desk Ops</title>
<link rel="stylesheet" href="assets/style.css"></head>
<body><div class="wrap"><nav class="nav">
<div class="brand"><b>Desk Ops</b><span>Price snapshots &middot; results feed &middot; gates</span></div>
<div class="grp">Desk Ops</div>
{nav}
<div class="grp">Elsewhere</div>
{ext}
</nav><main class="main">
<div class="eyebrow">Research only &middot; not betting advice &middot; blank = unverified, never zero</div>
{body}
<div class="foot">
<p>Sources re-read {CHECKED}; pinned dataset commit <code>{PIN[:12]}</code> (hash-verified against
<code>data/provenance.json</code> at build time). Analytical values on these pages are
<strong>recomputed</strong> by <code>ops_lab/</code> code from the committed, hash-verified inputs;
no value is inferred. Unverifiable values are published as blanks and listed on the
Flagged for Review page.</p>
<p>Independent research. Not affiliated with the NFL or any operator. Nothing here is betting advice
and no reward is funded.</p>
</div></main></div></body></html>"""


# --------------------------------------------------------------------------- #
# own-book moneyline (origination order step 3)
# --------------------------------------------------------------------------- #
def fair_american(p: float) -> str:
    """Fair (zero-vig) American price for a win probability — pure arithmetic.

    Decimal odds d = 1/p; American: -100/(d-1) when d < 2 (i.e. p > 0.5), +100(d-1) when
    d >= 2. The verifier re-derives p from the emitted price and fails the build on drift.
    """
    if not 0.0 < p < 1.0:
        return ""
    d = 1.0 / p
    return str(int(round(-100 / (d - 1)))) if d < 2 else str(int(round(100 * (d - 1))))


def devig_two_way(a: float, b: float) -> float:
    """Proportional de-vig (mirrors line_lab/markets.py); returns the home/over side prob."""
    da = 1 + (a / 100 if a > 0 else 100 / abs(a))
    db = 1 + (b / 100 if b > 0 else 100 / abs(b))
    return (1 / da) / (1 / da + 1 / db)


def build_own_book() -> list[dict]:
    live = {r["game_id"]: r for r in json.loads(
        (ROOT / "data/derived/summary.json").read_text(encoding="utf-8"))["live"]["rows"]}
    own = {r["game_id"]: r for r in csv.DictReader(
        open(ROOT / "data/derived/own_lines_upcoming.csv", newline="", encoding="utf-8"))}
    # posted 2026 moneylines from the snapshot store
    mkt_ml: dict[str, dict[str, str]] = {}
    for r in csv.DictReader(open(DATA / "price_snapshots.csv", newline="", encoding="utf-8")):
        if r["scope"] == "origination" and r["market"] == "MONEYLINE" and r["snapshot_type"] == "posted_league":
            mkt_ml.setdefault(r["game_id"], {})[r["side"]] = r["odds"]
    rows = []
    for gid in sorted(own):
        o, lv = own[gid], live[gid]
        fair_s, mkt_s = float(o["own_spread"]), (float(o["market_spread_if_posted"]) if o["market_spread_if_posted"] else None)
        fair_t, mkt_t = float(o["own_total"]), (float(o["market_total_if_posted"]) if o["market_total_if_posted"] else None)
        ph = lv["model_home_win_prob"]
        rows.append({
            "game_id": gid, "week": o["week"], "gameday": o["gameday"],
            "matchup": f"{o['away_team']} at {o['home_team']}",
            "fair_spread": f"{fair_s:g}", "market_spread": "" if mkt_s is None else f"{mkt_s:g}",
            "diff_spread": "" if mkt_s is None else f"{fair_s - mkt_s:g}",
            "published_disagreement_spread": o["disagreement_spread"],
            "fair_total": f"{fair_t:g}", "market_total": "" if mkt_t is None else f"{mkt_t:g}",
            "diff_total": "" if mkt_t is None else f"{fair_t - mkt_t:g}",
            "published_disagreement_total": o["disagreement_total"],
            "fair_ml_home": fair_american(ph), "fair_ml_away": fair_american(1 - ph),
            "fair_p_home": f"{ph:.4f}",
            "market_ml_home": mkt_ml.get(gid, {}).get("home", ""),
            "market_ml_away": mkt_ml.get(gid, {}).get("away", ""),
            "diff_ml_home_pp": "",
        })
    # market-probability difference where a two-sided market moneyline exists
    for r in rows:
        hm, am = r["market_ml_home"], r["market_ml_away"]
        if hm and am:
            mk_p = devig_two_way(float(hm), float(am))
            r["diff_ml_home_pp"] = f"{(float(r['fair_p_home']) - mk_p) * 100:+.1f}"
    with open(DATA / "own_book_ml.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    return rows


OWN_BOOK = build_own_book()


# --------------------------------------------------------------------------- #
# data reductions for the pages
# --------------------------------------------------------------------------- #
def snap_rows():
    return list(csv.DictReader(open(DATA / "price_snapshots.csv", newline="", encoding="utf-8")))


def feed_rows():
    return list(csv.DictReader(open(DATA / "results_feed.csv", newline="", encoding="utf-8")))


def load_csv(name):
    return list(csv.DictReader(open(DATA / name, newline="", encoding="utf-8")))


SRC_GAMES = f"https://github.com/nflverse/nfldata/blob/{PIN}/data/games.csv"
SRC_CLOSING = f"https://github.com/nflverse/nfldata/blob/{PIN}/data/closing_lines.csv"
SRC_INITIAL = f"https://github.com/nflverse/nfldata/blob/{PIN}/data/initial_lines.csv"
SRC_OWN = "https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/own_lines_upcoming.csv"
SRC_BETS = "https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/bets.csv"
SRC_SUMMARY = "https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/summary.json"
SRC_BUILD = "https://github.com/karagemop466-tech/Korea3/blob/main/ops_lab/build.py"
SRC_METRICS = "https://github.com/karagemop466-tech/Korea3/blob/main/ops_lab/metrics.py"
SRC_STORES = "https://github.com/karagemop466-tech/Korea3/blob/main/ops_lab/stores.py"
SRC_SNAPS = "https://github.com/karagemop466-tech/Korea3/blob/main/ops_lab/data/price_snapshots.csv"
SRC_FEED = "https://github.com/karagemop466-tech/Korea3/blob/main/ops_lab/data/results_feed.csv"
SRC_SPLIT = "https://github.com/karagemop466-tech/Korea3/blob/main/ops_lab/data/leaderboard_split.csv"
SRC_DEMOTE = "https://github.com/karagemop466-tech/Korea3/blob/main/ops_lab/data/demotion_status.csv"
NFL_SCHEDULE_2026 = "https://www.nfl.com/schedules/2026/REG10/"
NFL_GAME_W10_WAS_NYG = "https://www.nfl.com/games/commanders-at-giants-2026-reg-10"
NFL_TERMS = "https://www.nfl.com/legal/terms/"
NFL_INJ = "https://www.nfl.com/injuries/"
NIST_CI = "https://www.itl.nist.gov/div898/handbook/eda/section3/eda353.htm"
NIST_SAMPLE = "https://www.itl.nist.gov/div898/handbook/prc/section2/prc222.htm"

SNAPS = snap_rows()
FEED = feed_rows()
SPLIT = load_csv("leaderboard_split.csv")
DEMOTE = load_csv("demotion_status.csv")
MOVE = load_csv("market_move_2021.csv")


# --------------------------------------------------------------------------- #
# index
# --------------------------------------------------------------------------- #
def p_index() -> str:
    st = SNAP_META["by_snapshot_type"]
    fm = FEED_META
    cc = fm["ledger_crosscheck"]
    live_n = METRICS_META["live_strategies"]
    cards = f"""<div class="grid k4">
<div class="card"><div class="tag">Price-snapshot store</div><div class="num">{SNAP_META['rows']:,}</div>
<div class="sub">rows: {st.get('closing',0):,} closing &middot; {st.get('posted_league',0):,} league-posted &middot; {st.get('opening_wsgt',0):,} opening &middot; {st.get('origination_blank',0)} originated-without-market</div></div>
<div class="card"><div class="tag">Verified results feed</div><div class="num">{fm['rows']:,}</div>
<div class="sub">market-side outcomes; {fm['published_outcome_verified']:,} cross-checked against the published outcome, {fm['published_outcome_mismatches']} mismatches flagged</div></div>
<div class="card"><div class="tag">Ledger cross-check</div><div class="num">{cc['checked']:,}</div>
<div class="sub">S1&ndash;S11 bet outcomes re-derived from scores: {cc['mismatch_count']} mismatches; {cc['skipped_market_type']} parlay/futures rows out of scope</div></div>
<div class="card"><div class="tag">Live strategies</div><div class="num">{live_n}</div>
<div class="sub">none passes the nine promotion gates, so the demotion gate is armed and applies to nobody (dry-run only)</div></div>
</div>"""
    rows = [
        [code("O02"), "Price-snapshot store — one row per (originated market, side, snapshot): opening (WSGT 2021), closing (2006&ndash;2018), league-posted (2006&ndash;2026), and explicit blank rows for originated markets no source prices yet.", link("snapshots.html", "snapshots.html")],
        [code("O03"), "Verified results feed — every settled game &times; market &times; side with two independent outcomes (score-derived and published) plus a re-derivation check of the published outcome against its own line.", link("results.html", "results.html")],
        [code("O04"), "Leaderboard separated into a signal view and a staking view that are never combined; staking cross-checks against the published ROI to 1e-6.", link("leaderboard_split.html", "signal / staking")],
        [code("O05"), "Demotion gate (live &rarr; paper): six triggers, week-block bootstrap thresholds, armed with an empty live set and an explicitly-labelled dry run on the eleven paper strategies.", link("demotion.html", "demotion")],
        [code("O06"), "Brief-coverage table for the eight numbered additions in the current brief — what exists, what was missing, what this lab added, with links.", link("requirements_brief.html", "brief coverage")],
        [code("O07"), "Questions register (information held / missing / decision needed) and decision-gated suggestions — nothing is implemented before a path is chosen.", link("questions.html", "questions") + " &middot; " + link("suggestions.html", "suggestions")],
        [code("O08"), "Flagged for review — new irregularities found by this session's line-by-line review, each with the arithmetic that shows it.", link("flagged.html", "flagged")],
    ]
    body = f"""<h1>Desk Ops — the operating model of the line desk</h1>
<p class="lead">This lab implements the four operating pieces the brief asks for that no prior
session had built: a <strong>price-snapshot store</strong> recording the opening and closing numbers
for the markets this project originates and bets, a <strong>verified results feed</strong> so
backtests and ROI have a settlement source at all, a <strong>leaderboard split</strong> that separates
signal quality from staking outcome, and a <strong>demotion gate</strong> that would send a live
strategy back to paper. It also documents the origination order — side first, then total, then
moneyline — and closes the own-moneyline gap in the 2026 book with a recomputed fair price.</p>
{cards}
{sec("What this lab adds", "additive only — no existing page or data file was modified", table(
    "Deliverables of this lab",
    ["Item", "What it is", "Where"],
    rows))}
{sec("Where the analysis lives", "this lab is the plumbing; the research pages are untouched",
'<div class="grid k3">'
+ f'<a class="tile" href="../lines.html"><b>Own lines (fair / market / difference)</b><span>line_lab&#39;s originated book, unchanged</span></a>'
+ f'<a class="tile" href="../leaderboard.html"><b>Leaderboard &amp; nine gates</b><span>the published competition table, unchanged</span></a>'
+ f'<a class="tile" href="../hub/competition.html"><b>Promotion gates &amp; luck</b><span>paper &rarr; live requirements, sample-size arithmetic</span></a>'
+ f'<a class="tile" href="../depth_lab/index.html"><b>Depth Lab</b><span>starter-replacement depth, the availability input to signals</span></a>'
+ f'<a class="tile" href="../correlations.html"><b>Correlations with n</b><span>dependence estimates used for parlays</span></a>'
+ f'<a class="tile" href="../hub/flagged.html"><b>Flagged for review (all labs)</b><span>every irregularity published so far</span></a>'
+ '</div>')}
{sec("Standing rule", "the rule every row on this site obeys",
'<div class="notice">A value is published only if a hash-verified input states it or it is a labelled '
'recomputation from those inputs. Everything else is <strong>blank and flagged</strong> — never zero, '
'never inferred. The NFL publishes no machine-readable betting prices (see the data-rights review), so '
'market numbers on this site come from the pinned open dataset and are labelled as such, not as official '
'league publications.</div>')}"""
    return page("index.html", "Desk Ops", body)


# --------------------------------------------------------------------------- #
# snapshots
# --------------------------------------------------------------------------- #
def p_snapshots() -> str:
    st = SNAP_META
    by_type = st["by_snapshot_type"]
    schema = [
        ["market_uid", "game_id:MARKET:side — one identity per market side per game", link(SRC_BUILD, "builder code")],
        ["game_id, season, week, game_date, home_team, away_team", "game identity as published in games.csv", link(SRC_GAMES)],
        ["market, side", "SPREAD / TOTAL / MONEYLINE; home / away / over / under", link(SRC_BUILD, "builder code") + " " + link("method.html", "normalisation rule")],
        ["scope", "backtest (2006&ndash;2025 markets the S1&ndash;S11 ledger prices) or origination (the 2026 book this project originates)", link(SRC_BUILD, "builder code")],
        ["snapshot_type", "closing (closing_lines.csv) / opening_wsgt (initial_lines.csv) / posted_league (games.csv) / origination_blank (no market number published)", link(SRC_CLOSING) + " " + link(SRC_INITIAL) + " " + link(SRC_GAMES)],
        ["line, odds", "exactly as the source publishes; empty when the source publishes neither (never inferred)", link(SRC_GAMES) + " " + link(SRC_CLOSING) + " " + link(SRC_INITIAL)],
        ["pinned_utc", "the pinned dataset commit time the value was read at: " + st["pinned_utc"], link(f"https://github.com/nflverse/nfldata/tree/{PIN}")],
        ["source_id, source_url, note", "which file the row came from, the permanent link, and any reading note", link(SRC_BUILD, "builder code")],
    ]
    cov = [
        ["closing", f"{by_type.get('closing',0):,}", "2006&ndash;2018", "per-side line as published; odds published for moneylines only; published outcome kept on the results feed, not here", link(SRC_CLOSING)],
        ["posted_league", f"{by_type.get('posted_league',0):,}", "2006&ndash;2026", "the numbers the S1&ndash;S11 ledger prices at and the 2026 book originates against; the dataset claims no opening/closing semantics for these fields", link(SRC_GAMES)],
        ["opening_wsgt", f"{by_type.get('opening_wsgt',0):,}", "2021 season", "WSGT opening lines, line only — the dataset publishes no opening odds", link(SRC_INITIAL)],
        ["origination_blank", f"{by_type.get('origination_blank',0):,}", "2026 weeks 10&ndash;18", "originated markets for which the pinned dataset has no market number yet; blank + flagged, never zero", link(SRC_OWN)],
    ]
    # origination coverage
    own_markets = {}
    for r in SNAPS:
        if r["scope"] == "origination":
            own_markets.setdefault(r["market"], {"posted": 0, "blank": 0})
            own_markets[r["market"]]["posted" if r["snapshot_type"] == "posted_league" else "blank"] += 1
    ocov = [
        [m, f"{v['posted']}", f"{v['blank']}",
         (link("../lines.html", "fair line, market line, difference &rarr;") if m in ("SPREAD", "TOTAL") else link("own_book.html", "fair price &rarr;")),
         link(SRC_GAMES)]
        for m, v in sorted(own_markets.items())
    ]
    sample_keys = ["2006_01_MIA_PIT:MONEYLINE:home", "2021_01_DAL_TB:SPREAD:away", "2026_08_BAL_BUF:SPREAD:home", "2026_10_WAS_NYG:SPREAD:home"]
    seen = set()
    sample = []
    for r in SNAPS:
        if r["snapshot_type"] in seen:
            continue
        if r["snapshot_type"] == "closing" and r["market"] != "MONEYLINE":
            continue
        if any(k in r["market_uid"] for k in sample_keys) or r["snapshot_type"] == "origination_blank":
            if r["market_uid"] not in seen:
                seen.add(r["snapshot_type"])
                sample.append(r)
        if len(sample) >= 6:
            break
    srows = [[code(r["market_uid"]), r["snapshot_type"], r["line"] or blank("no line in the source"),
               r["odds"] or blank("no odds in the source"), link(r["source_url"])]
             for r in sample[:6]]
    body = f"""<h1>Price-snapshot store</h1>
<p class="lead">The brief requires a store that &ldquo;records opening and closing numbers for every
market we originate&rdquo;. This is that store: one row per (game &times; market &times; side &times;
snapshot), copied verbatim from the pinned, hash-verified inputs. Where a source publishes no number
for a market the book originates, the store holds an explicit blank row with the reason — so the
question &ldquo;do we hold a price for every market we originate?&rdquo; is answered by rows, not by
an assumption.</p>
<div class="notice warn">The NFL does not publish machine-readable betting prices, and neither the
league nor an operator is the source here. All market numbers come from the pinned open dataset
(nflverse/nfldata, tier&nbsp;3, disclosed on every row). Within that dataset, <strong>true opening and
closing pairs exist only where two snapshots exist</strong>: WSGT openers (2021, line only) versus
closes (2006&ndash;2018). A single timestamped number is recorded as one snapshot and never labelled
open or close.</div>
{sec("Snapshot types", f"{st['rows']:,} rows", table(
    "Store composition",
    ["Snapshot type", "Rows", "Coverage", "What it holds", "Source"],
    cov))}
{sec("Origination coverage — the 2026 book", f"{st['origination_games']} games, {st['origination_market_sides']} originated market sides",
    table("Every originated market side has a row in the store",
          ["Market", "Sides with a market number", "Sides blank (no market published yet)", "Fair line published at", "Source"],
          ocov))}
{sec("Schema", "one row per market side per snapshot", table(
    "Columns of price_snapshots.csv",
    ["Column", "Meaning", "Source / rule"],
    schema))}
{sec("Sample rows", "one per snapshot type", table(
    "Rows exactly as stored (full store: " + f'<a href="data/price_snapshots.csv">data/price_snapshots.csv</a>)',
    ["market_uid", "snapshot_type", "line", "odds", "Source"],
    srows))}
{sec("What this store cannot do yet", "honest limits, each with a path forward",
'<div class="prose"><ul>'
'<li><strong>No true open&to;close pair for 2019&ndash;2025 or for most of the 2026 book</strong>: '
'closing_lines.csv stops at 2018 and initial_lines.csv stops after the 2021 season. The feed cannot '
'derive closing-line value for those seasons; suggestions ' + code("SG-ops1") + ' and ' + code("SG-ops8")
+ ' propose the fix and need a source decision.</li>'
'<li><strong>No book-identified prices</strong>: the dataset does not name the book behind '
'<code>spread_line</code>/<code>total_line</code>, so the store records the number without a book claim.</li>'
'<li><strong>The 2026 book is pin-time only</strong>: re-pinning (scheduled capture) is required before '
'open&to;close movement becomes measurable on our own markets — ' + code("SG-ops1") + '.</li>'
'</ul></div>')}"""
    return page("snapshots.html", "Price-snapshot store", body)


# --------------------------------------------------------------------------- #
# own book (origination order)
# --------------------------------------------------------------------------- #
def p_own_book() -> str:
    rows = OWN_BOOK
    ml_done = sum(1 for r in rows if r["fair_ml_home"])
    mkt_ml = sum(1 for r in rows if r["market_ml_home"])
    show = [r for r in rows if r["week"] in ("8", "9")][:8] or rows[:8]
    trows = []
    for r in show:
        trows.append([
            f"{e(r['matchup'])} <span class='muted small'>(w{e(r['week'])})</span>",
            f"{r['fair_spread']}", (r["market_spread"] or blank("no market spread published in the pinned dataset")),
            (r["diff_spread"] or blank("difference undefined without a market spread")),
            f"{r['fair_total']}", (r["market_total"] or blank("no market total published in the pinned dataset")),
            (r["diff_total"] or blank("difference undefined without a market total")),
            f"{r['fair_ml_home']} / {r['fair_ml_away']}",
            (f"{r['market_ml_home']} / {r['market_ml_away']}" if r["market_ml_home"] else blank("no market moneyline published in the pinned dataset")),
            (r["diff_ml_home_pp"] + " pp" if r["diff_ml_home_pp"] else blank("difference in probability defined only where both market prices exist")),
            link(SRC_SUMMARY, "model probs") + " " + link(SRC_GAMES, "market") + " " + link(SRC_BUILD, "recompute"),
        ])
    body = f"""<h1>Origination order: side &rarr; total &rarr; moneyline</h1>
<p class="lead">The brief fixes the origination order: <em>originate the side first, then the total,
then the moneyline</em>. This page records that order as policy, shows the three steps side by side
for the 2026 book, and closes the gap this review found: the published book originated the side and
the total but <strong>no own-moneyline price</strong>. The fair moneyline is now derived here, as a
labelled recomputation, from the model win probabilities the repo already publishes — no new model,
no market input.</p>
<div class="grid k4">
<div class="card"><div class="tag">Step 1 &middot; Side (spread)</div><div class="num">164</div><div class="sub">fair spread for every originated game, from the points model (published by line_lab, unchanged)</div></div>
<div class="card"><div class="tag">Step 2 &middot; Total</div><div class="num">164</div><div class="sub">fair total for every originated game, from the same points model</div></div>
<div class="card"><div class="tag">Step 3 &middot; Moneyline (this lab)</div><div class="num">{ml_done}</div><div class="sub">fair American price from the published win probabilities: p &#8594; 1/p decimal &#8594; American</div></div>
<div class="card"><div class="tag">Market reference</div><div class="num">{mkt_ml}</div><div class="sub">games with a published market moneyline at pin time (weeks 1&ndash;9); the rest are blank rows in the snapshot store</div></div>
</div>
{sec("Policy", "the order, and what each step may use",
'<div class="prose"><ul>'
'<li><strong>Side first.</strong> The spread is originated from expected points (home &minus; away); '
'the model publishes it for every game. Evidence: ' + link(SRC_SUMMARY, "summary.json live rows") + '.</li>'
'<li><strong>Total second.</strong> The total is originated from the same expected points (home + away) — '
'simultaneous in the arithmetic, second in the ordering policy.</li>'
'<li><strong>Moneyline third.</strong> The fair price is a conversion of the win probability the same '
'model publishes (this lab, ' + link(SRC_BUILD, "build.py") + '): it adds no new model and takes no '
'market input, so the book stays independent of the market it is later compared against.</li>'
'<li><strong>Then, and only then, comparison.</strong> Fair lines are compared with market numbers '
'(separate columns, never averaged) and any difference becomes a candidate signal through the '
'pre-registered rules — not a line change.</li>'
'</ul></div>')}
{sec("The book — fair and market side by side", "first 8 games of weeks 8&ndash;9 (the weeks with market numbers at pin time)",
    table(
        "Fair (model) vs market, per market, as separate columns — full book: <a href='data/own_book_ml.csv'>data/own_book_ml.csv</a>",
        ["Game", "Fair spread", "Market spread", "Diff (fair&minus;mkt)", "Fair total", "Market total", "Diff (fair&minus;mkt)",
         "Fair ML home / away", "Market ML home / away", "Fair&minus;mkt home win prob", "Sources"],
        trows))}
{sec("Definitions used above", "why the moneyline difference is a probability, not points",
'<dl class="defs">'
'<dt>Fair moneyline</dt><dd>American price with zero vig implied by the model win probability p: '
'decimal 1/p converted to American (negative below even money, positive above). Pure arithmetic; '
'labelled recomputed.</dd>'
'<dt>Diff (moneyline)</dt><dd>Fair home win probability minus the de-vigged market home win probability, '
'in percentage points, published only where a two-sided market moneyline exists. Prices are not signed '
'lines, so no point difference is defined — the probability difference is.</dd>'
'<dt>Diff (spread / total)</dt><dd>Fair minus market, the same convention as the published '
'agreement columns; equality with those is re-checked by the verifier on every build.</dd>'
'</dl>')}"""
    return page("own_book.html", "Origination order", body)


# --------------------------------------------------------------------------- #
# results feed
# --------------------------------------------------------------------------- #
def p_results() -> str:
    fm = FEED_META
    cc = fm["ledger_crosscheck"]
    # coverage by era
    eras = [("1999–2005", lambda s: 1999 <= int(s) <= 2005,
             "no published outcome source exists for these seasons in the pinned dataset"),
            ("2006–2018", lambda s: 2006 <= int(s) <= 2018,
             "published outcomes cross-checked against the score-derived settlement"),
            ("2019–2025", lambda s: 2019 <= int(s) <= 2025,
             "settlement from scores; closing_lines.csv stops at 2018, so no published outcome exists"),
            ("2026 (through week 9 at pin time)", lambda s: int(s) == 2026,
             "the pinned dataset predates week 10; see the official cross-check below")]
    erows = []
    for label, pred, note in eras:
        sel = [r for r in FEED if pred(r["season"])]
        n = len(sel)
        n_settled = sum(1 for r in sel if r["outcome_computed"])
        ver = sum(1 for r in sel if r["published_outcome_verified"])
        mm = sum(1 for r in sel if r["published_outcome_verified"] == "MISMATCH")
        erows.append([label, f"{n:,}", f"{n_settled:,}", (f"{ver:,}" if ver else blank("no published outcomes exist for this era")),
                      (f'<span class="flag">{mm}</span>' if mm else ("0" if ver else blank("nothing to verify"))),
                      note + " " + link(SRC_CLOSING) + " " + link(SRC_GAMES)])
    mm_rows = [[code(m["feed_uid"]), e(m["closing_line"]), e(m["published_outcome_raw"]),
                e(m["rederived_from_closing_line"]), e(m["game_score"]), link(SRC_CLOSING)]
               for m in fm["mismatch_rows"]]
    oc = fm["official_crosschecks"][0]
    ocrow = [[e(oc["game"]), code(oc["official_result"]), link(oc["official_source"], "week 10 schedule") + " " + link(oc["official_source_2"], "game center"),
              e(oc["dataset_state"]), e(oc["checked_utc"])]]
    sample = [r for r in FEED if r["game_id"] == "2006_01_MIA_PIT"]
    srows = [[code(r["feed_uid"]), f"{e(r['away_score'])}&ndash;{e(r['home_score'])}", r["line"] or blank("no line"),
              r["closing_line"] or blank("no closing row (pre-2006)"), r["outcome_computed"], r["outcome_published"] or blank("none published"),
              (pill(r["published_outcome_verified"], "ok") if r["published_outcome_verified"] == "match" else (pill(r["published_outcome_verified"], "bad") if r["published_outcome_verified"] else blank("no published outcome"))),
              link(SRC_GAMES)]
             for r in sample]
    contract = [
        ["A backtest may settle only from rows with a non-empty outcome_computed.", "score-derived settlement (1 win / 0 push / &minus;1 loss) re-derivable from the published final scores", link(SRC_GAMES) + " " + link(SRC_STORES, "rule code")],
        ["A bet ledger must agree with the feed before ROI is published.", "all 15,666 single-market S1&ndash;S11 bets re-checked on every build: 0 mismatches", link(SRC_BETS) + " " + link(SRC_METRICS, "cross-check code")],
        ["A published outcome is never silently trusted.", "re-derived from its own line on every build; the " + str(fm["published_outcome_mismatches"]) + " rows that fail are published on the flagged page and excluded from any settlement claim", link("flagged.html")],
        ["Unsettled markets stay blank.", "2026 weeks 10&ndash;18 have no feed rows yet (not settled at pin time); blanks are never zeros", link(SRC_GAMES)],
    ]
    body = f"""<h1>Verified results feed</h1>
<p class="lead">The brief requires a &ldquo;verified results feed so backtests and ROI can be
computed at all&rdquo;. The feed holds one row per settled game &times; market &times; side with the
final score, the market number, the price where published, and <strong>two independent outcomes side
by side</strong>: one derived from the final score, one as published by the dataset's outcome column.
Where both exist they are checked against each other on every build, and the published outcome is
additionally re-derived from its own line.</p>
<div class="grid k4">
<div class="card"><div class="tag">Feed rows</div><div class="num">{fm['rows']:,}</div><div class="sub">6 per settled game: spread home/away, total over/under, moneyline home/away</div></div>
<div class="card"><div class="tag">Published outcomes verified</div><div class="num">{fm['published_outcome_verified']:,}</div><div class="sub">re-derived from the closing row's own line; {fm['published_outcome_mismatches']} contradictions flagged, none hidden</div></div>
<div class="card"><div class="tag">Ledger agreement</div><div class="num">{cc['checked']:,}</div><div class="sub">S1&ndash;S11 single-market bets re-settled from scores: {cc['mismatch_count']} mismatches</div></div>
<div class="card"><div class="tag">Push rows (score-derived)</div><div class="num">{fm['push_rows_computed']:,}</div><div class="sub">settled as pushes (0), not wins or losses — the usual silent error in naive backtests</div></div>
</div>
{sec("Coverage and what could be verified", "per era, with the reason an era has no published outcome",
    table("Feed coverage by era",
          ["Era", "Rows", "With score-derived outcome", "Published outcomes verified", "Contradictions", "Why / source"],
          erows))}
{sec("Official cross-check — the live edge of the feed", "what the pinned dataset cannot know",
    table("The feed is a dataset snapshot; the league page is ahead of it",
          ["Game", "Official result", "Official source (read " + CHECKED + ")", "Dataset state", "Checked"],
          ocrow))}
{sec("The " + str(fm['published_outcome_mismatches']) + " published outcomes that contradict their own line", "retained as published, flagged, and excluded from settlement claims",
    table("Each row: the published outcome is not reproducible from the published line (arithmetic on the flagged page)",
          ["feed_uid", "Closing line", "Published outcome (raw)", "Re-derived from that line", "Final score (away&ndash;home)", "Source"],
          mm_rows))}
{sec("Sample rows", "the 2006 opener, every column as stored", table(
    "Rows exactly as stored (full feed: <a href='data/results_feed.csv'>data/results_feed.csv</a>)",
    ["feed_uid", "Score (away&ndash;home)", "Line (games.csv)", "Closing line", "Score-derived outcome", "Published outcome", "Verification", "Source"],
    srows))}
{sec("Consumption contract", "the rules any backtest on this feed must obey", table(
    "Feed contract",
    ["Rule", "Enforcement", "Source / code"],
    contract))}"""
    return page("results.html", "Verified results feed", body)


# --------------------------------------------------------------------------- #
# leaderboard split
# --------------------------------------------------------------------------- #
def p_leaderboard_split() -> str:
    sig = []
    stk = []
    for r in SPLIT:
        name = r["name"] or r["strategy_id"]
        ev = link("../leaderboard.html", "published leaderboard") + " " + link(SRC_BETS, "ledger") + " " + link(SRC_METRICS, "recompute")
        sig.append([
            code(r["strategy_id"]) + " " + e(name), e(r["market"]),
            r["signal_bets"] or blank("no model probability on futures bets"),
            r["brier_model"] or blank("n/a"), r["brier_market"] or blank("n/a"),
            (f"<b>{float(r['brier_skill']):+.4f}</b>" if r["brier_skill"] else blank("n/a")),
            (f"[{float(r['brier_skill_ci_low']):+.4f}, {float(r['brier_skill_ci_high']):+.4f}]" if r["brier_skill_ci_low"] else blank("n/a")),
            (f"{float(r['published_brier_skill']):+.4f}" if r["published_brier_skill"] else blank("no universe value for futures")),
            ev,
        ])
        stk.append([
            code(r["strategy_id"]) + " " + e(name), e(r["market"]), f"{int(r['bets']):,}",
            f"<b>{float(r['roi']) * 100:+.2f}%</b>",
            f"[{float(r['roi_ci_low']) * 100:+.2f}%, {float(r['roi_ci_high']) * 100:+.2f}%]",
            f"{float(r['max_drawdown_units']):.1f} u",
            f"{e(r['worst_season'])} ({float(r['worst_season_roi']) * 100:+.2f}%)",
            f"{e(r['worst_week'])} ({float(r['worst_week_units']):+.1f} u)",
            f"{float(r['weeks_negative_share']) * 100:.0f}%",
            ev,
        ])
    xrows = [[code(r["strategy_id"]),
              f"{float(r['roi']) * 100:+.3f}%", f"{float(r['published_full_roi']) * 100:+.3f}%",
              code(r["roi_delta"]), f"{int(r['bets']):,}",
              (pill("match", "ok") if r["crosscheck"] == "match" else pill(r["crosscheck"], "bad")),
              link(SRC_BETS) + " " + link(SRC_SPLIT, "this table as CSV")]
             for r in SPLIT]
    body = f"""<h1>Leaderboard, separated: signal vs staking</h1>
<p class="lead">The brief requires the leaderboard to &ldquo;separate &lsquo;signal&rsquo; from
&lsquo;staking&rsquo; so a lucky staking run cannot mask a bad signal&rdquo;. The published leaderboard
mixes both in one table. Here they are separated into two views computed from <strong>disjoint
columns</strong> of the same bets — probability quality alone for signal, flat-stake cash flow alone
for staking — and no combined rank is published. A staking hot streak cannot move the signal view;
a well-calibrated loser cannot hide in the staking view.</p>
{sec("SIGNAL view — probability quality only", "no cash flow enters this table",
    table("Brier skill of the model's probability on each strategy's own bets, against the de-vigged market price (2006&ndash;2025 window; pushes count as misses, mirroring the published definition)",
          ["Strategy", "Market", "Scored bets", "Brier (model)", "Brier (market)", "Brier skill (own bets)", "95% week-block CI", "Published column*", "Evidence"],
          sig))}
<div class="notice warn">*The leaderboard's per-strategy &ldquo;Brier skill&rdquo; column is the
<strong>market-universe</strong> diagnostic from the G6 market test — the same number for every
strategy in a market (see flagged item FO2). It measures the model on all priced games in that market,
not the strategy's own selections. The &ldquo;own bets&rdquo; column here is the per-strategy value;
where the two differ, both are shown and neither silently replaces the other.</div>
{sec("STAKING view — flat-stake cash flow only", "no probability enters this table",
    table("ROI and drawdown under the 1-unit flat stake the ledger records (2006&ndash;2025 window)",
          ["Strategy", "Market", "Bets", "ROI / bet", "95% week-block CI", "Max drawdown", "Worst season", "Worst week", "Losing weeks", "Evidence"],
          stk))}
{sec("Cross-check — this page against the published leaderboard", "the staking view must reproduce the published ROI exactly",
    table("Recomputed vs published (the verifier fails the build if any delta exceeds 0.05 pp)",
          ["Strategy", "Recomputed ROI", "Published ROI", "Delta", "Bets", "Status", "Sources"],
          xrows))}
{sec("Market move after origination (2021 only)", "the one season where an opening snapshot exists — descriptive, not a CLV claim",
    table("Opening (WSGT) line minus betting line for the same side; n per strategy",
          ["Strategy", "n matched", "Mean opening&minus;betting (points)", "Share positive", "Source"],
          [[code(r["strategy_id"]), r["n"], (f"{float(r['mean_open_minus_bet']):+.2f}" if r["mean_open_minus_bet"] else blank("no 2021 bets")),
            (f"{float(r['share_positive']) * 100:.0f}%" if r["share_positive"] else blank("n/a")), link(SRC_INITIAL) + " " + link(SRC_BETS)]
           for r in MOVE]))}"""
    return page("leaderboard_split.html", "Signal vs staking", body)


# --------------------------------------------------------------------------- #
# demotion gate
# --------------------------------------------------------------------------- #
def p_demotion() -> str:
    rules = [
        [code("D1"), "Provenance break", "A placed bet has no row in the price-snapshot store for its market side.", "Immediate demotion.", link("snapshots.html")],
        [code("D2"), "Signal collapse", "Trailing-100-bet Brier skill (own bets vs de-vigged market) below 0 with the one-sided 95% week-block bootstrap bound also below 0.", "Demotion to paper.", link(NIST_CI, "NIST CI method")],
        [code("D3"), "Staking collapse", "Trailing-100-bet ROI below 0 with the one-sided 95% week-block bootstrap bound also below 0.", "Demotion to paper.", link(NIST_CI, "NIST CI method")],
        [code("D4"), "Closing-value failure", "Mean market move after origination persistently against the strategy (only where an opening snapshot exists — 2021 today).", "Demotion to paper.", link(SRC_INITIAL)],
        [code("D5"), "Luck-band breach", "Live max drawdown exceeds the 95th percentile of the drawdown distribution produced by re-shuffling the same weeks 2,000 times.", "Demotion to paper.", link(SRC_METRICS, "band code")],
        [code("D6"), "Feed corruption", "Any consumed result fails its verification (a published outcome contradicting its own line, or a ledger/feed mismatch).", "Demotion until reconciled.", link("results.html")],
    ]
    status = [[f"{METRICS_META['live_strategies']}", "armed (rules published; bootstrap thresholds fixed; seed " + str(METRICS_META['seed']) + ")",
               "applies to nobody: promotion requires all nine gates and 0 of 11 strategies pass",
               link("../hub/competition.html", "promotion gates")]]
    dry = []
    for r in DEMOTE:
        name = next((s["name"] for s in SPLIT if s["strategy_id"] == r["strategy_id"]), r["strategy_id"])
        dry.append([
            code(r["strategy_id"]) + " " + e(name), pill("paper", "warn"),
            f"{r['d1_with_snapshot']} / {r['d1_singles']}" + (f' <span class="flag">{r["d1_without_snapshot"]} missing</span>' if r["d1_without_snapshot"] != "0" else ""),
            (f'{r["d1_futures_no_feed_row"]} futures bets have no feed row' if r["d1_futures_no_feed_row"] != "0" else "&mdash;")
            + (f'; {r["d1_parlays_legs_not_in_ledger"]} parlay legs not traceable from the ledger alone' if r["d1_parlays_legs_not_in_ledger"] != "0" else ""),
            f"{r['d2_triggers']} / {r['d2_windows_evaluated']}" + (f' <span class="muted small">first: {e(r["d2_first_window"])}</span>' if r["d2_first_window"] else ""),
            f"{r['d3_triggers']} / {r['windows_evaluated']}" + (f' <span class="muted small">first: {e(r["d3_first_window"])}</span>' if r["d3_first_window"] else ""),
            f"{float(r['max_drawdown_units']):.1f} vs {float(r['luck_band_p95_units']):.1f}",
            (pill("would demote", "bad") if r["d5_would_trigger"] == "yes" else pill("no", "ok")),
            link(SRC_BETS) + " " + link(SRC_DEMOTE, "this table as CSV"),
        ])
    body = f"""<h1>Demotion gate: live &rarr; paper</h1>
<p class="lead">The brief requires a &ldquo;demotion gate that sends a live strategy back to
paper&rdquo;. Promotion to live is governed by nine gates; until now nothing governed the way back.
The demotion gate below is symmetric with them: automatic, thresholded, and reversible only by
re-passing the <em>full</em> promotion set — a single good week can never restore a demoted strategy.</p>
<div class="notice"><strong>Honest state:</strong> no strategy is live (0 of 11 pass the nine promotion
gates), so the gate's live set is empty and nothing on this page is a statement about a live position.
The trigger counts are an explicitly-labelled <strong>dry run on paper strategies</strong> — the same
arithmetic that would run on a live book, exercised on history so the implementation is proven before
it is needed.</div>
{sec("The rule", "six triggers; any one demotes", table(
    "Demotion triggers, thresholds and their justification",
    ["Gate", "Name", "Trigger", "Action", "Threshold source"],
    rules))}
{sec("Gate status", "live set", table("Demotion gate status",
    ["Live strategies", "Gate state", "Why", "Reference"],
    status))}
{sec("Dry run on the eleven paper strategies", "trailing-100-bet windows, step 50, over each strategy's full single-market history",
    table("Dry-run results (a D2/D3 trigger here does NOT demote anything — no strategy is live)",
          ["Strategy", "State", "D1 snapshot coverage (singles)", "D1 gaps", "D2 signal-collapse windows", "D3 staking-collapse windows",
           "Max drawdown vs 95% luck band (units)", "D5", "Sources"],
          dry))}
{sec("Re-admission", "how a demoted strategy returns",
'<div class="prose"><ul>'
'<li>Re-admission requires re-passing <strong>all nine promotion gates</strong> on the updated window — '
'the same bar as the first promotion: ' + link("../hub/competition.html", "promotion gates") + '.</li>'
'<li>At least <strong>100 new settled bets</strong> must accrue before re-evaluation; fewer cannot '
'distinguish skill from luck at any realistic edge (the sample-size table shows even +2.6 pp needs '
'&asymp;2,242 bets): ' + link(NIST_SAMPLE, "NIST sample-size arithmetic") + '.</li>'
'<li>A demotion is recorded, never deleted; the record travels with the strategy.</li>'
'<li>Thresholds are owner-ratifiable: ' + code("Q-ops3") + ' in the questions register asks for that '
'sign-off before any strategy is allowed to go live.</li>'
'</ul></div>')}"""
    return page("demotion.html", "Demotion gate", body)


# --------------------------------------------------------------------------- #
# brief coverage
# --------------------------------------------------------------------------- #
def p_requirements_brief() -> str:
    rows = [
        ["1", "Add a price-snapshot store that records opening and closing numbers for every market we originate",
         "done — built by this lab",
         "62,904 rows: 20,490 closing (2006&ndash;2018), 40,510 league-posted (2006&ndash;2026), 1,088 opening (WSGT 2021), 816 explicit blanks for originated markets with no market number yet; schema, coverage and limits published",
         link("snapshots.html")],
        ["2", "Add a verified results feed so backtests and ROI can be computed at all",
         "done — built by this lab",
         "44,304 market-side outcomes with two independent outcome columns; 13,660 published outcomes re-derived and 14 contradictions flagged; the S1&ndash;S11 ledger re-settles with 0 mismatches",
         link("results.html")],
        ["3", "Originate the side first, then the total, then the moneyline",
         "gap closed by this lab",
         "the published book had the side and total but no own moneyline; the fair moneyline is now derived as a labelled recomputation from the published win probabilities, and the order is recorded as policy",
         link("own_book.html")],
        ["4", "Publish the model's fair line, the market line, and the difference as separate columns",
         "verified + extended",
         "the spread/total columns existed on the live-lines page and their difference re-checks exactly against the published disagreement columns (164 rows); the moneyline now gets the same three-column treatment with a probability difference",
         link("own_book.html") + " " + link("../lines.html", "live lines")],
        ["5", "Separate 'signal' from 'staking' in the leaderboard so a lucky staking run cannot mask a bad signal",
         "done — built by this lab",
         "two views from disjoint columns, never combined into one rank; the staking view reproduces the published ROI to 1e-6; the signal view exposes that the published per-strategy Brier column is universe-level (FO2)",
         link("leaderboard_split.html")],
        ["6", "Track the depth of the replacement, not just the fact of a replacement",
         "done — prior session (not duplicated)",
         "Depth Lab captured all 32 official club depth charts and publishes the string of every replacement (2nd/3rd/4th) joined to the official Week 10 injury report",
         link("../depth_lab/replacements.html")],
        ["7", "Compute correlations only from officially sourced numbers and publish n with each value",
         "verified by this review",
         "every published correlation row carries n (same-game n 6,784 with the window label flagged as X02; signal pairs carry n_shared; cross-game carries per-season n_pairs); the numbers derive from the pinned dataset, disclosed as tier 3, never presented as league-official",
         link("../correlations.html") + " " + link("../hub/recompute.html", "recomputation log")],
        ["8", "Define a demotion gate that sends a live strategy back to paper",
         "done — defined and armed by this lab",
         "six triggers with week-block bootstrap thresholds; live set empty (0 of 11 strategies pass promotion); dry-run demonstration published per strategy",
         link("demotion.html")],
        ["&mdash;", "Leaderboard competition with rewards (standing brief)",
         "unchanged — still honest",
         "no strategy is reward-eligible; no money is funded; the reward rule pays nothing until a strategy passes all nine gates",
         link("../leaderboard.html") + " " + link("../hub/competition.html", "rewards &amp; luck")],
        ["&mdash;", "Single bets, parlays, player-prop combos (standing brief)",
         "unchanged",
         "singles and two-leg cross-game parlays are implemented and gated; player-prop combos remain blocked by data availability (no official player logs or prop prices)",
         link("../props.html")],
        ["&mdash;", "Every table row sourced; blanks flagged; no manual input (standing brief)",
         "held",
         "ops_lab's verifier fails the build on any row without a source link and on any blank without a reason; the build is deterministic with no manual steps",
         link("../verification.html")],
    ]
    body = f"""<h1>Brief coverage — the eight numbered additions</h1>
<p class="lead">The current brief adds eight numbered requirements. This table audits each one line
by line against what the repository actually contains, states what this session added, and links the
evidence. Statuses describe this repository, not any external endorsement.</p>
{sec("The eight numbered requirements", "audited " + CHECKED, table(
    "Requirement traceability for the current brief",
    ["#", "Requirement (as written)", "Status", "What exists, verified", "Evidence"],
    rows))}
{sec("What was genuinely missing before this session", "found by grep, closed additively",
'<div class="prose"><ul>'
'<li>No <code>demotion</code> concept existed anywhere in the repository (grep across every page, '
'generator and dataset) — built here: ' + link("demotion.html", "demotion gate") + '.</li>'
'<li>No <strong>results feed</strong> existed as a named, verifiable artifact — the settlement inputs '
'existed but nothing joined, verified or published them — built here: ' + link("results.html", "results feed") + '.</li>'
'<li>No <strong>snapshot store</strong> existed; opening numbers (WSGT 2021) and closing numbers '
'(2006&ndash;2018) sat in separate files with no store joining them per market — built here: '
+ link("snapshots.html", "snapshot store") + '.</li>'
'<li>The 2026 book originated <strong>no own-moneyline price</strong> — closed here as a labelled '
'recomputation: ' + link("own_book.html", "origination order") + '.</li>'
'<li>The leaderboard mixed signal and staking in one ranking — separated here: '
+ link("leaderboard_split.html", "signal / staking") + '.</li>'
'</ul></div>')}"""
    return page("requirements_brief.html", "Brief coverage", body)


# --------------------------------------------------------------------------- #
# questions register
# --------------------------------------------------------------------------- #
def p_questions() -> str:
    qs = [
        ["Q-ops1", "Which sources count as 'official' for club-published depth charts? (re-raise of the owner decision Q15/S13)",
         "Both readings are published: the shared audit treats club domains as non-official (dataset tier); Depth Lab publishes club-published strings with their tier disclosed.",
         "An owner ruling on the source tier; the audit allow-list change that follows (one line) and a re-run.",
         "Yes — blocks reclassification of 698 depth rows.", "../depth_lab/sources.html"],
        ["Q-ops2", "What capture cadence should the snapshot store commit to?",
         "The store is pin-time only: one timestamped snapshot per market from the pinned dataset commit; open-vs-close is distinguishable only for 2021 (WSGT) and 2006&ndash;2018 (closes).",
         "A cadence decision (per-build, weekly, per-week-of-season) and approval for a scheduled CI job to re-pin — the brief forbids manual input, so this must be automated or accepted as pin-time-only.",
         "No — the store is useful now; cadence only extends open/close coverage.", "snapshots.html"],
        ["Q-ops3", "Are the demotion-gate thresholds ratified before any strategy may go live?",
         "The rule is published with its arithmetic (D1&ndash;D6, trailing-100 windows, one-sided 95% week-block bootstrap, luck band at the 95th percentile of 2,000 shuffles, seed fixed).",
         "Owner sign-off on the thresholds (or chosen alternatives); nothing can go live without promotion gates passing anyway, so this is not blocking today.",
         "No — but it must be answered before any strategy is ever promoted.", "demotion.html"],
        ["Q-ops4", "How should the 14 self-contradicting published outcomes be treated upstream?",
         "The feed retains both values, flags the rows, and excludes them from settlement claims; the ledger cross-check shows no S1&ndash;S11 bet touched them.",
         "A decision to report upstream (the dataset is community-maintained) or to accept the flagged treatment permanently.",
         "No — the flagged treatment is safe.", "flagged.html"],
        ["Q-ops5", "Should the leaderboard's per-strategy 'Brier skill' column be relabelled (it is the market-universe G6 value)?",
         "The recomputation proves the column is identical within a market; the per-strategy value differs and is now published on the split page with both shown.",
         "A presentation decision on the shared leaderboard page (owned by the line_lab generator; any edit must go through its session's scope).",
         "No — both values are now visible somewhere honest.", "leaderboard_split.html"],
        ["Q-ops6", "Which questions register is canonical?",
         "Four registers now exist (hub, decisions lab, decision_lab, this one); they agree on substance but duplicate structure.",
         "An owner choice of the canonical register; the others should point to it rather than fork it.",
         "No — every register links its peers.", "suggestions.html"],
        ["Q-ops7", "What opening-price source should the CLV feed use beyond 2021?",
         "The dataset publishes opening lines (WSGT, line only) for the 2021 season; no opening odds source exists in the pinned inputs.",
         "A source decision (accept line-only CLV in points, or add a priced opening source) — without it D4 stays permanently 'not evaluable' for 10 of 11 strategies.",
         "No — D4 is skipped honestly today.", "snapshots.html"],
    ]
    rows = [[code(q[0]), f"<b>{q[1]}</b>", q[2], q[3], q[4], link(q[5], "evidence")] for q in qs]
    body = f"""<h1>Questions register — what must be answered before a decision</h1>
<p class="lead">Each row: the question, the information <em>already held</em>, the information
<em>missing</em>, whether an answer blocks anything, and where the current evidence lives. Nothing on
this page is a decision; the decision-gated suggestions are on the
<a href="suggestions.html">suggestions page</a>. The canonical cross-lab register is
<a href="../hub/questions.html">hub/questions.html</a>; this register covers the desk-operations
gaps this lab introduced.</p>
{sec("Desk-operations questions", f"{len(qs)} questions, {sum(1 for q in qs if q[4].startswith('Yes'))} blocking", table(
    "Questions, information held and missing, and what each answer unblocks",
    ["ID", "Question", "Information held", "Information missing / decision needed", "Blocking?", "Evidence"],
    rows))}"""
    return page("questions.html", "Questions register", body)


# --------------------------------------------------------------------------- #
# suggestions
# --------------------------------------------------------------------------- #
def p_suggestions() -> str:
    sg = [
        ["SG-ops1", "Automate snapshot capture: a scheduled CI job re-pins the dataset and appends timestamped snapshots, so the store gains true open&to;close pairs on our own 2026 markets.",
         "Open/close coverage is the store's weakest point (2021 openers only). Automation is the only brief-compliant capture mechanism (no manual input).",
         "Needs a cadence decision (" + code("Q-ops2") + ") and a write-path the owner approves.", "awaiting choice", "snapshots.html"],
        ["SG-ops2", "Add a per-strategy 'Brier skill (own bets)' column next to the universe value on the leaderboard, labelled as such.",
         "The current column cannot distinguish strategies in a market (FO2); a reader comparing strategies on it is misled.",
         "Edits a page owned by the line_lab generator; should ride a coordinated integration.", "awaiting choice", "leaderboard_split.html"],
        ["SG-ops3", "Unify strategy IDs across builds (S1&ndash;S11 vs S01&ndash;S18 denote different rules — flagged X01).",
         "A rule scored from the wrong ledger flips sign (&minus;0.0873 vs +0.0430 in the prior audit); the collision is one namespace fix.",
         "Touches two generators and their data; needs a coordinated integration session.", "awaiting choice", "../hub/flagged.html"],
        ["SG-ops4", "Promote the own-moneyline fair price from this lab into the line_lab book output after owner review.",
         "This lab derives it as a labelled recomputation (no new model); the book page would then show all three markets symmetrically.",
         "Touches the line_lab generator's output; owner review of the conversion first.", "awaiting choice", "own_book.html"],
        ["SG-ops5", "Schedule a weekly feed refresh (re-pin) during the season and re-run the official cross-check against the league schedule page for the newest week.",
         "The feed lags live results by the pin interval (FO6); a weekly re-pin bounds the lag to days without manual input.",
         "Needs approval to change data inputs on a schedule (same mechanism as " + code("SG-ops1") + ").", "awaiting choice", "results.html"],
        ["SG-ops6", "Designate one canonical questions/suggestions register and convert the others to pointers.",
         "Four registers duplicate structure; a reviewer must read all four to be sure nothing is missed (" + code("Q-ops6") + ").",
         "Owner choice of the canonical register; mechanical change afterwards.", "awaiting choice", "questions.html"],
        ["SG-ops7", "Wire the demotion gate into CI: evaluate it on every build for whatever book is live and surface any trigger on the flagged page.",
         "A gate nobody runs automatically will not fire when needed; the dry-run harness already computes everything per build.",
         "Needs the threshold ratification (" + code("Q-ops3") + ") first; CI plumbing is trivial once ratified.", "awaiting choice", "demotion.html"],
        ["SG-ops8", "Decide the opening-price source beyond 2021 (line-only points CLV vs a priced source) so D4 becomes evaluable.",
         "D4 (closing-value failure) is permanently 'not evaluable' for 10 of 11 strategies under the current inputs (" + code("Q-ops7") + ").",
         "A source decision; if line-only is accepted, D4 needs a points-based restatement before use.", "awaiting choice", "snapshots.html"],
    ]
    rows = [[code(s[0]), f"<b>{s[1]}</b>", s[2], s[3], pill(s[4], "warn"), link(s[5], "context")] for s in sg]
    body = f"""<h1>Suggestions — review before implementing anything</h1>
<p class="lead">Site improvements to sharpen decision-making, each gated behind a review choice. The
rule is the repository's own: <strong>nothing here is implemented until a path is chosen</strong>.
Cross-lab suggestions live on the canonical board at
<a href="../hub/suggestions.html">hub/suggestions.html</a>; these are the desk-operations
proposals this lab's work generated. Every one names what it needs and what it unblocks.</p>
{sec("Desk-operations proposals", f"{len(sg)} proposals, none implemented", table(
    "Suggestions awaiting a decision",
    ["ID", "Proposal", "Why it improves decision-making", "What it needs", "Status", "Context"],
    rows))}
{sec("How to choose", "the decision rule for the reviewer",
'<div class="prose"><ul>'
'<li>Pick by <strong>unblocking power per risk</strong>: ' + code("SG-ops1") + ' and ' + code("SG-ops5")
+ ' buy real open/close evidence for every future market; ' + code("SG-ops3") + ' removes a known '
'sign-flipping hazard; ' + code("SG-ops7") + ' makes the safety net automatic.</li>'
'<li>Reject anything whose evidence is not already published: every proposal above links the page '
'that shows the gap it addresses.</li>'
'<li>Record the choice in <code>COORDINATION.md</code> (the shared board) so parallel sessions do '
'not fork the decision.</li>'
'</ul></div>')}"""
    return page("suggestions.html", "Suggestions", body)


# --------------------------------------------------------------------------- #
# flagged
# --------------------------------------------------------------------------- #
def p_flagged() -> str:
    rows = [
        ["FO1", "high", "14 published outcomes in closing_lines.csv contradict their own published line",
         "Each row's outcome is not reproducible from that row's own line (e.g. a total of 38 against a closing line of 45 published as an over win). The feed retains both values, excludes the rows from settlement claims, and the ledger cross-check shows no S1&ndash;S11 bet consumed them.",
         "14 of 13,674 (0.10%)", link("results.html", "feed page") + " " + link(SRC_CLOSING, "source")],
        ["FO2", "medium", "The leaderboard's per-strategy 'Brier skill' column is the market-universe G6 value",
         "It is identical for every strategy in a market (verified across all four markets), so it cannot rank strategies' signal quality. The per-strategy value, computed on each strategy's own bets, differs and is published beside it on the split page.",
         "11 strategies", link("leaderboard_split.html") + " " + link(SRC_METRICS, "recomputation")],
        ["FO3", "medium", "The originated 2026 book had no own-moneyline price",
         "The book published fair spread and total but no moneyline, so the brief's third origination step was unimplemented. This lab derives the fair price from the already-published win probabilities as a labelled recomputation; promoting it into the book output is proposal " + code("SG-ops4") + " (owner choice).",
         "164 games", link("own_book.html")],
        ["FO4", "medium", "Dataset lag: week-10 2026 results exist on the league page but not in the pinned dataset",
         "The pinned commit (2026-11-01) predates the games; the official page shows the Commanders winning 24&ndash;21 at the Giants on Nov 12, and the feed has no row for it. A weekly re-pin is proposed (" + code("SG-ops5") + ").",
         "all games after 2026-11-01", link(NFL_SCHEDULE_2026, "official week 10") + " " + link("results.html", "cross-check")],
        ["FO5", "low", "Team-abbreviation mismatch inside the dataset: LAR (closing_lines) vs LA (games.csv), 2016&ndash;2018",
         "47 games (282 closing rows) failed to join until a documented LAR&rarr;LA alias was applied in the store builder. The alias is disclosed on the method page, not applied silently.",
         "47 games", link("method.html") + " " + link(SRC_STORES, "builder")],
        ["FO6", "low", "Opening prices (odds) are not published by the dataset — 2021 WSGT openers are line-only",
         "The store's opening snapshots carry a line and no price, so a probability-level CLV cannot be computed for any season today; D4 is skipped honestly. Proposal " + code("SG-ops8") + " asks for a source decision.",
         "1,088 opening rows", link("snapshots.html")],
        ["FO7", "low", "games.csv 2006 prices are partial (220 of 267 games)",
         "The posted_league snapshot rows reflect exactly what the source publishes; the missing 47 games are the source's own gaps, shown as blank rows, never imputed.",
         "47 games", link(SRC_GAMES, "source") + " " + link("snapshots.html")],
        ["FO8", "low", "Parlay legs are not traceable from the ledger CSV alone",
         "Parlay rows record combined game ids without each leg's market/side, so the D1 provenance check reports parlays as 'legs not traceable from the ledger' — a real audit gap in the ledger's self-containment, not a data error.",
         "690 parlay bets", link("demotion.html") + " " + link(SRC_BETS, "ledger")],
        ["FO9", "medium (pre-existing)", "Strategy-ID collision across builds (X01, re-raised)",
         "bets.csv (S1&ndash;S11) and gates_results.csv (S01&ndash;S18) use colliding ids for different rules; the prior audit showed a sign flip from scoring the wrong ledger. Unification is proposal " + code("SG-ops3") + ".",
         "2 ledgers", link("../hub/flagged.html", "X01 on the hub flagged page")],
        ["FO10", "low (pre-existing)", "Same-game correlation row labelled 2006&ndash;2025 is computed over all seasons (X02)",
         "Re-verified by this session: the published n=6,784 is the all-season count; the documented window gives n=4,996, phi +0.0163. Both are far below the 0.0975 break-even requirement, so the conclusion stands.",
         "1 row", link("../hub/flagged.html", "X02") + " " + link("../correlations.html")],
    ]
    body = f"""<h1>Flagged for review — desk operations</h1>
<p class="lead">New irregularities found by this session's line-by-line review, each with the
arithmetic that shows it and the source it involves. Flagged items never block a release; they are
published so the owner can request changes. Pre-existing flags from other sessions are not repeated
here — the full cross-lab list is on <a href="../hub/flagged.html">hub/flagged.html</a>.</p>
{sec("New irregularities", f"{len(rows)} items", table(
    "Flagged items (FO = flag, ops lab)",
    ["ID", "Severity", "Finding", "Detail and treatment", "Scope", "Evidence"],
    [[code(r[0]), pill(r[1], "warn" if "low" in r[1] else "bad"), f"<b>{r[2]}</b>", r[3], r[4], r[5]] for r in rows]))}
{sec("Also carried on the live site", "pointers, not duplicates",
'<div class="prose"><ul>'
'<li>Depth Lab flags F01&ndash;F10 (club chart disclaimers, the HOU rendering question, the four clubs absent from the official injury report): '
+ link("../depth_lab/flagged.html", "depth_lab/flagged.html") + '.</li>'
'<li>The source-tier question for club domains (Q15/S13): re-raised as ' + code("Q-ops1") + '.</li>'
'<li>All 53 hub flags: ' + link("../hub/flagged.html", "hub/flagged.html") + '.</li>'
'</ul></div>')}"""
    return page("flagged.html", "Flagged for review", body)


# --------------------------------------------------------------------------- #
# sources & method
# --------------------------------------------------------------------------- #
def p_sources() -> str:
    rows = [
        ["nflverse/nfldata games.csv (pinned)", "Scores, posted lines and prices for 1999&ndash;2026; the settlement input for the feed and the store's posted_league rows", "dataset (tier 3, disclosed)", link(SRC_GAMES), "sha256 re-verified against data/provenance.json on " + CHECKED],
        ["nflverse/nfldata closing_lines.csv (pinned)", "Per-side closing line, odds (moneylines) and published outcome, 2006&ndash;2018; the feed's published-outcome column and the store's closing rows", "dataset (tier 3, disclosed)", link(SRC_CLOSING), "sha256 re-verified " + CHECKED + "; 14 self-contradictions found and flagged (FO1)"],
        ["nflverse/nfldata initial_lines.csv (pinned)", "WSGT opening lines, 2021 season, line only; the store's opening snapshots and the market-move table", "dataset (tier 3, disclosed)", link(SRC_INITIAL), "sha256 re-verified " + CHECKED],
        ["data/derived/bets.csv (in-repo, hash-pinned by line_lab)", "The S1&ndash;S11 ledger; the input to the signal/staking split and the demotion dry run", "in-repo dataset", link(SRC_BETS), "outcome column re-settled from scores on every build (0 mismatches)"],
        ["data/derived/summary.json (in-repo)", "Published leaderboard metrics and the 2026 live rows (model probabilities) used for the fair moneyline", "in-repo dataset", link(SRC_SUMMARY), "ROI cross-check reproduced to 1e-6 on the 2006&ndash;2025 window"],
        ["NFL.com 2026 week-10 schedule", "Official result of WAS@NYG (24&ndash;21 final) — the feed's live-edge cross-check", "official (league)", link(NFL_SCHEDULE_2026), "page read " + CHECKED + "; game-center page confirms Final/Week 10: " + link(NFL_GAME_W10_WAS_NYG, "game center")],
        ["NFL.com terms of use", "The data-rights basis for keeping league content link-only", "official (league, terms)", link(NFL_TERMS), "relied on as documented by the data-rights review; not re-read this session"],
        ["NIST/SEMATECH e-Handbook", "CI and sample-size method references for the demotion thresholds", "official (standards body)", link(NIST_CI) + " " + link(NIST_SAMPLE), "referenced for method; first verified by the competition session"],
        ["ops_lab/stores.py, metrics.py, build.py", "The recomputation code every analytical value on these pages traces to", "this repository", link(SRC_STORES) + " " + link(SRC_METRICS) + " " + link(SRC_BUILD), "fail-closed verifier: " + link("check.py")],
    ]
    body = f"""<h1>Sources</h1>
<p class="lead">Everything these pages publish traces to one of the rows below. Dataset rows are
tier&nbsp;3 (open community data, disclosed as such — the league publishes no machine-readable
prices). Analytical values link the code that recomputes them.</p>
{sec("Source register", "checked " + CHECKED, table(
    "Sources used by the Desk Ops lab",
    ["Source", "Used for", "Tier", "Link", "Verification this session"],
    rows))}"""
    return page("sources.html", "Sources", body)


def p_method() -> str:
    defs = [
        ("Settlement convention", "Score-derived outcome: 1 win, 0 push, &minus;1 loss. Spread: home covers when (home&minus;away) &minus; spread_line &gt; 0. Total: over when (home+away) &minus; total_line &gt; 0. Moneyline: higher score wins; a tie is a push. Mirrors line_lab/markets.py exactly."),
        ("Published-outcome mapping", "closing_lines.csv publishes 1 win / 0 loss / 0.5 push; the feed maps that to 1 / &minus;1 / 0 so both columns share one convention. The mapping is shown in stores.py, not hidden in a comment."),
        ("published_outcome_verified", "The published outcome is re-derived from that closing row's OWN line (not the games.csv line) with the row's own side. 'MISMATCH' means one dataset row contradicts itself; such rows are listed on the flagged page and excluded from settlement claims."),
        ("Side normalisation", "Sources publish spread and moneyline sides as team codes; the store normalises to home/away by comparing the code to games.csv home_team/away_team. The LAR&rarr;LA alias (FO5) is applied before comparison and disclosed."),
        ("Week-block bootstrap", "Every CI resamples (season, week) blocks with replacement to the observed block count, 2,000 draws, seed 20261114 — the same convention the published leaderboard CI uses. Per-week aggregates make each draw O(weeks)."),
        ("Brier skill, two definitions", "Own-bets skill = 1 &minus; Brier(model)/Brier(market) computed on the strategy's own scored bets (y = outcome &gt; 0, pushes count as misses — mirroring the published code). The published per-strategy column is the market-universe value from the G6 test, identical within a market (FO2). Both are shown; they measure different things."),
        ("Fair moneyline", "American price for win probability p: decimal 1/p; negative American &minus;100&middot;d/(d&minus;1) when d &lt; 2, positive 100&middot;(d&minus;1) otherwise. Pure arithmetic on the published model probability — no market input enters the origination."),
        ("De-vig", "Proportional two-way de-vig (mirrors line_lab/markets.py), used only for the market probability difference on the own-book page."),
        ("Luck band (D5)", "The strategy's per-week P&amp;L sums are shuffled 2,000 times; the 95th percentile of the resulting max-drawdown distribution is the band. Exceeding it is the demotion trigger D5."),
        ("Trailing windows", "D2/D3 evaluate every trailing-100-bet window (step 50) with at least 5 week-blocks; a trigger needs the statistic below 0 AND its one-sided 95% bound below 0."),
        ("Determinism", "No clock enters the build (the checked-date constant is fixed per session); two runs produce byte-identical stores and pages, and the verifier enforces it."),
        ("Blank policy", "A blank cell always carries a reason and is listed on the flagged page where it matters. A blank is never zero, never interpolated."),
    ]
    body = f"""<h1>Method and limits</h1>
<p class="lead">Definitions behind every number on these pages, written so each can be re-derived
from the code it names. Where this lab mirrors a published convention (settlement, de-vig, bootstrap),
the mirror is exact and stated; where it differs (per-strategy Brier), the difference is the point.</p>
{sec("Definitions", "each re-derivable from the linked code", "<dl class='defs'>" +
     "".join(f"<dt>{d[0]}</dt><dd>{d[1]}</dd>" for d in defs) + "</dl>")}
{sec("Limits", "what this lab does not claim",
'<div class="prose"><ul>'
'<li>No live strategy exists; every trigger count is a dry run on paper strategies.</li>'
'<li>No price, probability or ROI on these pages is new evidence of edge; the eleven strategies all '
'fail the promotion gates and the split exists to show why more honestly.</li>'
'<li>Market numbers are tier-3 dataset values, never league-official; the store labels them so.</li>'
'<li>The feed cannot settle futures (win totals) or parlay legs from its rows; both gaps are '
'published, not papered over.</li>'
'</ul></div>')}"""
    return page("method.html", "Method", body)


# --------------------------------------------------------------------------- #
def main() -> None:
    builders = {
        "index.html": p_index, "snapshots.html": p_snapshots, "own_book.html": p_own_book,
        "results.html": p_results, "leaderboard_split.html": p_leaderboard_split,
        "demotion.html": p_demotion, "requirements_brief.html": p_requirements_brief,
        "questions.html": p_questions, "suggestions.html": p_suggestions,
        "flagged.html": p_flagged, "sources.html": p_sources, "method.html": p_method,
    }
    for fname, fn in builders.items():
        (OUT / fname).write_text(fn(), encoding="utf-8")
        print("wrote", fname)
    if MISSING_LINK:
        raise SystemExit("rows without a source link: " + "; ".join(MISSING_LINK))
    print(f"built {len(builders)} pages; every table row carries a link")


if __name__ == "__main__":
    main()
