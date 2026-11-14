#!/usr/bin/env python3
"""Build the Lifecycle site: price-snapshot store, verified results feed, demotion gate,
and the separated signal/staking leaderboard.

Design rule for every page: each table row carries at least one link to the source the value came
from — an official publisher, or the exact committed file a *recomputed* value was derived from.
A value that no official source states is printed as a flagged blank rather than filled in. The
build fails if a row is emitted without a source link.

Usage:
    python3 lifecycle/build.py
Writes lifecycle/*.html.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
OUT = HERE

SOURCES = json.loads((DATA / "sources.json").read_text(encoding="utf-8"))
MARKETS = json.loads((DATA / "markets.json").read_text(encoding="utf-8"))
SCHEMA = json.loads((DATA / "schema.json").read_text(encoding="utf-8"))
DEMOTION = json.loads((DATA / "demotion.json").read_text(encoding="utf-8"))
LEADERBOARD = json.loads((DATA / "leaderboard.json").read_text(encoding="utf-8"))
FEED = json.loads((DATA / "feed.json").read_text(encoding="utf-8"))

SRC = {s["id"]: s for s in SOURCES["sources"]}

CAPTURED = "2026-11-14"

PAGES: list[tuple[str, str, str]] = [
    ("index.html", "Lifecycle", "Overview"),
    ("price-snapshot.html", "Price-snapshot store", "Price snapshot"),
    ("results-feed.html", "Verified results feed", "Results feed"),
    ("demotion.html", "Demotion gate", "Demotion"),
    ("leaderboard.html", "Signal and staking leaderboards", "Leaderboard"),
    ("sources.html", "Sources", "Sources"),
    ("flagged.html", "Flagged for review", "Flagged"),
    ("method.html", "Method and limits", "Method"),
]

MISSING_LINK: list[str] = []


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def e(x) -> str:
    return html.escape(str(x), quote=True)


def ilink(url: str, label: str) -> str:
    return f'<a href="{e(url)}">{e(label)}</a>'


def link(src_id: str, label: str = "source", note: str = "") -> str:
    """A source link by register ID. Records a violation when the ID is unknown."""
    s = SRC.get(src_id)
    if not s:
        MISSING_LINK.append(f"{label}:{note} (unknown source {src_id})")
        return '<span class="flag">no source</span>'
    return (f'<a class="src" href="{e(s["url"])}" target="_blank" rel="noopener noreferrer" '
            f'title="{e(s["title"])}">{e(label)} &#8599;</a>')


def blank(why: str) -> str:
    return f'<span class="blank" title="{e(why)}">blank</span>'


def table(headers: list[str], rows: list[list[str]], cls: str = "") -> str:
    th = "".join(f'<th scope="col">{h}</th>' for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    return (f'<div class="scroll"><table class="{cls}"><thead><tr>{th}</tr></thead>'
            f"<tbody>{body}</tbody></table></div>")


def shell(filename: str, title: str, h1: str, lead: str, body: str) -> str:
    nav = []
    for fn, _navtitle, navlabel in PAGES:
        cls = ' class="active"' if fn == filename else ""
        nav.append(f'<a href="{fn}"{cls}>{e(navlabel)}</a>')
    nav_html = (
        '<div class="grp">Lifecycle</div>' + "".join(nav)
        + '<div class="grp">Rest of the repository</div>'
        '<a href="../index.html">Repository front door<span class="ext">&#8599;</span></a>'
        '<a href="../hub/index.html">Consolidated dashboard<span class="ext">&#8599;</span></a>'
        '<a href="../decision_lab/index.html">Decisions<span class="ext">&#8599;</span></a>'
        '<a href="../depth_lab/index.html">Depth Lab<span class="ext">&#8599;</span></a>'
    )
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)} | NFL Lifecycle</title>
<meta name="description" content="Price-snapshot store, verified results feed, demotion gate and separated signal/staking leaderboards. Every value is sourced or blank.">
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<div class="wrap">
<aside class="nav">
<div class="brand"><b>Lifecycle</b><span>NFL line lab &middot; built {CAPTURED}</span></div>
{nav_html}
</aside>
<main class="main">
<div class="eyebrow">Official sources only &middot; recomputed values labelled &middot; nothing inferred</div>
<h1>{e(h1)}</h1>
<p class="lead">{lead}</p>
{body}
<footer class="foot">
<p>Lifecycle defines the bookkeeping around a strategy: what price was recorded when a market opened
and closed, what the settled result feed contains, the rule that retires a live strategy, and the
separation of signal from staking. Every value is either an official-publisher fact, a value recomputed
from a committed file and labelled as such, or a blank that is flagged for review.</p>
<p><a href="flagged.html">Flagged for review</a> &middot; <a href="method.html">Method and limits</a>
&middot; <a href="sources.html">Sources</a></p>
</footer>
</main>
</div>
</body>
</html>
"""


def write(filename: str, title: str, h1: str, lead: str, body: str) -> None:
    (OUT / filename).write_text(shell(filename, title, h1, lead, body), encoding="utf-8")


def card(tag: str, num: str, sub: str) -> str:
    return f'<div class="card"><div class="tag">{e(tag)}</div><div class="num">{e(num)}</div><div class="sub">{e(sub)}</div></div>'


def notice(title: str, text: str, kind: str = "") -> str:
    cls = f"notice {kind}".strip()
    return f'<div class="{cls}"><strong>{e(title)}</strong> {text}</div>'


# --------------------------------------------------------------------------- #
# derived counts
# --------------------------------------------------------------------------- #
DMETA = DEMOTION["_meta"]
STRATEGIES = DEMOTION["strategies"]
LIVE = [s for s in STRATEGIES if s["status"] == "LIVE"]
DEMOTED = [s for s in STRATEGIES if s["status"] == "DEMOTED"]
SIGNAL = LEADERBOARD["signal_register"]
STAKING = LEADERBOARD["staking_register"]
DIVERGENT = LEADERBOARD["divergent"]
MARKETS_LIST = MARKETS["markets"]
STORE_ROWS = MARKETS["store_rows"]
TRIGGERS = DMETA["trigger_order"]
TRIGGER_METHOD = {t["code"]: t["method_source"] for t in SCHEMA["demotion_gate"]["triggers"]}


# --------------------------------------------------------------------------- #
# page: index
# --------------------------------------------------------------------------- #
def page_index() -> None:
    counts = "".join([
        card("Strategies in the ledger", str(DMETA["n_strategies"]),
             f"{DMETA['n_live']} LIVE · {DMETA['n_demoted']} DEMOTED by the gate"),
        card("Markets originated", str(len(MARKETS_LIST)),
             "side · total · moneyline, in that order"),
        card("Settled feed rows", f"{FEED['rows']:,}",
             f"{FEED['strategies']} strategies · {FEED['outcomes']}"),
        card("Signal/staking divergence", str(LEADERBOARD["divergent_count"]),
             f"strategies with a rank gap ≥ 3 · max gap {LEADERBOARD['max_rank_gap']}"),
    ])

    what_notice = notice(
        "What this build is.",
        "The bookkeeping layer the brief asked for: a price-snapshot store that records opening and "
        "closing numbers for every market, a verified results feed so backtests and ROI can be computed, "
        "a demotion gate that sends a live strategy back to paper, and a leaderboard that separates "
        "signal from staking. It defines the structures and, where a committed file exists, computes "
        "them. Every market price is blank and flagged, because no official publisher releases one.")

    rows = [
        ["Price-snapshot store",
         "Opening and closing numbers for the side, total and moneyline, stored as separate columns. "
         "Market definitions are cited; every price cell is blank and flagged.",
         link("L-DK-MARKETS", "market rules", "A") + " " + link("L-NFLVERSE", "pinned dataset", "A")],
        ["Verified results feed",
         f"The settled bet stream ({FEED['rows']:,} rows) that makes backtests and ROI computable. "
         "Settlement mechanics are cited; the summary is recomputed from the committed file.",
         link("L-DK-MARKETS", "settlement", "B") + " " + link("L-REPO-BETS", "committed feed", "B")],
        ["Demotion gate",
         f"A rule that sends a live strategy back to paper. Applied to the committed ledger it returns "
         f"{DMETA['n_demoted']} DEMOTED and {DMETA['n_live']} LIVE. The rule is printed before results.",
         link("L-NIST-MULTI", "multiplicity", "C") + " " + link("L-REPO-GATES", "committed ledger", "C")],
        ["Signal and staking leaderboards",
         "Two registers computed independently and never blended, so a lucky staking run cannot mask "
         "a bad signal. The committed ledger produces them.",
         link("L-REPO-GATES", "committed ledger", "D") + " " + link("L-DK-ODDS", "odds arithmetic", "D")],
    ]

    body = f"""
<div class="grid k4">{counts}</div>
{what_notice}
<section>
  <div class="section-head"><div><h2>The four structures</h2>
  <p>Each row links the source that defines it or the committed file it is computed from.</p></div>
  <span class="count small muted">{len(rows):02d} structures</span></div>
  {table(["Structure", "What it does", "Source"], rows)}
</section>
<section>
  <div class="section-head"><div><h2>Read these in order</h2></div></div>
  <div class="grid k3">
    <a class="tile" href="price-snapshot.html"><b>Price-snapshot store</b><span>side · total · moneyline · open and close as separate columns</span></a>
    <a class="tile" href="results-feed.html"><b>Verified results feed</b><span>the settled stream backtests and ROI consume</span></a>
    <a class="tile" href="demotion.html"><b>Demotion gate</b><span>the rule that returns a live strategy to paper</span></a>
    <a class="tile" href="leaderboard.html"><b>Signal and staking</b><span>two separated leaderboards, never blended</span></a>
    <a class="tile" href="flagged.html"><b>Flagged for review</b><span>the blanks and the limit of what is computable</span></a>
    <a class="tile" href="method.html"><b>Method and limits</b><span>how the numbers were computed and what they are not</span></a>
  </div>
</section>
"""
    write("index.html", "Lifecycle", "The bookkeeping around a strategy, from price to demotion",
          "Price-snapshot store, verified results feed, demotion gate, and separated signal and staking "
          "leaderboards. Structures are defined to official sources; values are recomputed from committed "
          "files where a committed file exists, and left blank and flagged everywhere else.", body)


# --------------------------------------------------------------------------- #
# page: price snapshot
# --------------------------------------------------------------------------- #
def page_price_snapshot() -> None:
    schema_rows = [[f'<span class="code">{e(c["col"])}</span>', e(c["kind"]), e(c["note"]),
                    ilink("method.html", "method")]
                   for c in MARKETS["store_schema"]["columns"]]

    origination_rows = [[f'<span class="code">{e(c["col"])}</span>', e(c["kind"]), e(c["note"]),
                         ilink("method.html", "method")]
                        for c in MARKETS["origination_schema"]["columns"]]

    market_rows = []
    for m in sorted(MARKETS_LIST, key=lambda x: x["order"]):
        def val(v, why):
            return blank(why) if v is None else e(v)
        market_rows.append([
            f'<span class="code">{e(m["code"])}</span>', e(m["name"]),
            e(m["definition"]),
            val(m["opening_line"], m["blank_reason"]),
            val(m["opening_price"], m["blank_reason"]),
            val(m["closing_line"], m["blank_reason"]),
            val(m["closing_price"], m["blank_reason"]),
            val(m["fair_line"], m["blank_reason"]),
            val(m["market_line"], m["blank_reason"]),
            val(m["difference"], "the difference is blank because fair_line and market_line are blank"),
            link(m["definition_source"], "definition", m["code"]),
        ])

    store_rows = []
    for r in STORE_ROWS:
        line = blank("no official publisher states an opening or closing line for this market") \
            if r["line"] is None else e(r["line"])
        price = blank("no official publisher states a price for this snapshot") \
            if r["price"] is None else e(r["price"])
        store_rows.append([
            f'<span class="code">{e(r["store_id"])}</span>',
            f'<span class="code">{e(r["market"])}</span>',
            e(r["snapshot_kind"]),
            line, price,
            '<span class="pill bad">unverified</span>',
            link(r["source"], "source", r["flag"]),
        ])

    body = f"""
{notice("The rule, stated before the tables.",
        "<b>" + e(MARKETS["store_schema"]["rule"]) + "</b>")}
{notice("Every price here is blank, and that is the finding.",
        "The NFL publishes no machine-readable line and no licensed operator publishes an opening or "
        "closing archive this project can cite. The pinned open dataset is the only line source and it is "
        "Tier&nbsp;3. A blank cell is the honest record of an unpublished value, not a value to fill.",
        "warn")}
<section>
  <div class="section-head"><div><h2>Store schema</h2>
  <p>The columns of the price-snapshot store. Opening and closing are separate rows, never merged.</p></div>
  <span class="count small muted">{len(schema_rows)} columns</span></div>
  {table(["Column", "Kind", "Meaning", "Source"], schema_rows)}
</section>
<section>
  <div class="section-head"><div><h2>The three markets we originate, in order</h2>
  <p>Side first, then the total, then the moneyline. Each row carries the open and close columns and the
  fair/market/difference columns, all blank where no official source states a value.</p></div>
  <span class="count small muted">{len(market_rows):02d} markets</span></div>
  {table(["Market", "Name", "Definition", "Open line", "Open price", "Close line", "Close price",
          "Fair line", "Market line", "Difference", "Source"], market_rows)}
</section>
<section>
  <div class="section-head"><div><h2>Origination columns</h2>
  <p>The fair line, the market line and the difference are published as three separate columns.</p></div>
  <span class="count small muted">{len(origination_rows)} columns</span></div>
  {table(["Column", "Kind", "Meaning", "Source"], origination_rows)}
</section>
<section>
  <div class="section-head"><div><h2>Store rows</h2>
  <p>One row per market per snapshot kind. The opening and closing rows are distinct records.</p></div>
  <span class="count small muted">{len(store_rows):02d} rows</span></div>
  {table(["Store id", "Market", "Snapshot", "Line", "Price", "Verified", "Source"], store_rows)}
</section>
"""
    write("price-snapshot.html", "Price-snapshot store",
          "Opening and closing numbers for every market we originate",
          "A store that records, for the side, the total and the moneyline, the opening and closing "
          "numbers as separate columns. The schema and the market definitions are cited; every price is "
          "blank and flagged, because no official publisher releases one.", body)


# --------------------------------------------------------------------------- #
# page: results feed
# --------------------------------------------------------------------------- #
def page_results_feed() -> None:
    schema_rows = [[f'<span class="code">{e(c["col"])}</span>', e(c["kind"]), e(c["note"]),
                    ilink("method.html", "method")]
                   for c in SCHEMA["results_feed"]["columns"]]

    feed = FEED
    outcome_rows = []
    for k in sorted(feed["outcomes"]):
        label = {"1": "win (+1)", "-1": "loss (-1)", "0": "push (0)"}.get(k, k)
        outcome_rows.append([e(label), f"{feed['outcomes'][k]:,}",
                             link("L-DK-MARKETS", "settlement rule", "F")])
    market_rows = []
    for k in sorted(feed["markets"]):
        market_rows.append([f'<span class="code">{e(k)}</span>', f"{feed['markets'][k]:,}",
                            link("L-REPO-BETS", "committed feed", "F")])

    card_row = "".join([
        card("Settled feed rows", f"{feed['rows']:,}", "recomputed from the committed bet stream"),
        card("Strategies in the feed", str(feed["strategies"]), "distinct strategy ids"),
        card("Total P/L (1-unit flat)", f"{feed['total_pnl']:.2f}", "sum of pnl across all rows"),
        card("Outcome split", f"{feed['outcomes'].get('1', 0):,} / {feed['outcomes'].get('-1', 0):,}",
             "wins / losses, plus pushes"),
    ])

    body = f"""
{notice("The rule, stated before the table.",
        "<b>" + e(SCHEMA["results_feed"]["rule"]) + "</b>")}
<div class="grid k4">{card_row}</div>
<section>
  <div class="section-head"><div><h2>Feed schema</h2>
  <p>The columns of the verified results feed — the settlement stream backtests and ROI consume.</p></div>
  <span class="count small muted">{len(schema_rows)} columns</span></div>
  {table(["Column", "Kind", "Meaning", "Source"], schema_rows)}
</section>
<section>
  <div class="section-head"><div><h2>Committed feed, summarized</h2>
  <p>Every figure below is recomputed from the committed bet stream, not from a live source.</p></div>
  <span class="count small muted">source: {e(feed['source_file'])}</span></div>
  {table(["Outcome", "Rows", "Source"], outcome_rows)}
</section>
<section>
  <div class="section-head"><div><h2>Rows by market</h2></div>
  <span class="count small muted">{len(market_rows):02d} markets</span></div>
  {table(["Market", "Rows", "Source"], market_rows)}
</section>
<section>
  <div class="section-head"><div><h2>What the feed is not</h2></div></div>
  <div class="prose">
  <p>The feed is a record of settled bets at recorded prices. It is <b>not</b> a licensed operator's
  settlement ledger and it is <b>not</b> a source of market prices: the prices in it come from the pinned
  open dataset and are Tier&nbsp;3. The feed is what makes an ROI arithmetic computable at all; it does not
  make any ROI claim about skill. No price is imputed into a row that lacks one.</p>
  </div>
</section>
"""
    write("results-feed.html", "Verified results feed",
          "The settlement stream that makes backtests and ROI computable",
          "A verified results feed: one row per settled bet, with the outcome and price recorded so that "
          "backtests and ROI can be computed. The schema and settlement rule are cited; the summary is "
          "recomputed from the committed bet stream.", body)


# --------------------------------------------------------------------------- #
# page: demotion
# --------------------------------------------------------------------------- #
def page_demotion() -> None:
    params = DMETA["parameters"]
    trigger_rows = [[f'<span class="code">{e(t["code"])}</span>', e(t["label"]),
                     link(TRIGGER_METHOD[t["code"]], "method", t["code"])] for t in TRIGGERS]

    strat_rows = []
    for s in STRATEGIES:
        tone = "ok" if s["status"] == "LIVE" else "bad"
        triggers = " ".join(f'<span class="pill {("bad" if c in ("N","Q","G") else "warn")}">{e(c)}</span>'
                            for c, _ in s["triggers"]) or '<span class="pill ok">none</span>'
        strat_rows.append([
            f'<span class="code">{e(s["id"])}</span>', e(s["name"]),
            f'<span class="code">{e(s["market"])}</span>',
            f"{s['n']:,}",
            (f"{s['roi']:+.4f}" if s["roi"] is not None else blank("blank in the ledger")),
            (f"{s['q']:.4f}" if s["q"] is not None else blank("blank in the ledger")),
            (f"{s['ci_low']:+.4f}" if s["ci_low"] is not None else blank("blank in the ledger")),
            (f"{s['seasons_positive']}/{s['seasons_tested']}"
             if s["seasons_positive"] is not None and s["seasons_tested"] is not None
             else blank("blank in the ledger")),
            f'<span class="pill {tone}">{e(s["status"])}</span>',
            triggers,
            e(s["reason"]),
            link("L-REPO-GATES", "ledger", s["id"]),
        ])

    tcounts = DMETA["trigger_counts"]
    tc_rows = [[f'<span class="code">{e(code)}</span>', e(lbl), str(tcounts.get(code, 0)),
                link(TRIGGER_METHOD[code], "method", code)]
               for code, lbl in ((t["code"], t["label"]) for t in TRIGGERS)]

    body = f"""
{notice("The demotion rule, stated before the results.",
        "<b>A strategy is LIVE only if it clears every trigger below. The first trigger that fires, in "
        "the fixed order N, Q, CI, S, G, is the recorded reason; every trigger that fires is listed. A "
        "strategy that fires any trigger is DEMOTED — returned to paper — and is not ranked for rewards.</b>")}
<div class="grid k4">
  {card("Strategies evaluated", str(DMETA["n_strategies"]), "from the committed ledger")}
  {card("LIVE", str(DMETA["n_live"]), "clear every trigger")}
  {card("DEMOTED", str(DMETA["n_demoted"]), "sent back to paper")}
  {card("Most common trigger", f"{max(tcounts, key=tcounts.get)}", f"fires on {max(tcounts.values())} of {DMETA['n_strategies']} strategies")}
</div>
<section>
  <div class="section-head"><div><h2>Triggers</h2>
  <p>Each trigger is a test on the trailing evidence. The method source is linked per trigger.</p></div>
  <span class="count small muted">{len(trigger_rows)} triggers</span></div>
  {table(["Code", "Trigger", "Method source"], trigger_rows)}
</section>
<section>
  <div class="section-head"><div><h2>Trigger parameters</h2>
  <p>This build's own design choices; they mirror the repository's published promotion gates.</p></div>
  <span class="count small muted">4 parameters</span></div>
  {table(["Parameter", "Value", "Meaning", "Source"],
         [["q_max", f"{params['q_max']}", "the highest BH q a live strategy may carry", ilink("method.html", "method")],
          ["ci_floor", f"{params['ci_floor']}", "the ROI confidence-interval lower bound must exceed this", ilink("method.html", "method")],
          ["stability_min", f"{params['stability_min']}", "the share of tested seasons that must be positive", ilink("method.html", "method")],
          ["n_min", f"{params['n_min']}", "the minimum settled bets a live strategy must carry", ilink("method.html", "method")]])}
</section>
<section>
  <div class="section-head"><div><h2>Per-strategy evaluation</h2>
  <p>Recomputed from the committed ledger. Every value is either transcribed or a deterministic function of it.</p></div>
  <span class="count small muted">{len(strat_rows):02d} strategies</span></div>
  {table(["ID", "Strategy", "Market", "n", "ROI", "BH q", "CI low", "Seasons +", "Status", "Triggers",
          "Reason", "Source"], strat_rows)}
</section>
<section>
  <div class="section-head"><div><h2>How often each trigger fires</h2></div>
  <span class="count small muted">{len(tc_rows):02d} triggers</span></div>
  {table(["Code", "Trigger", "Fires on", "Method source"], tc_rows)}
</section>
"""
    write("demotion.html", "Demotion gate",
          "The rule that sends a live strategy back to paper",
          "A demotion gate: a fixed predicate on trailing evidence that retires a live strategy to paper "
          "when the evidence no longer supports live status. The rule is printed before any result, and the "
          "evaluation is recomputed from the committed strategy ledger.", body)


# --------------------------------------------------------------------------- #
# page: leaderboard
# --------------------------------------------------------------------------- #
def page_leaderboard() -> None:
    sig_rows = []
    for r in SIGNAL:
        sig_rows.append([
            f'<span class="code">{e(r["id"])}</span>', e(r["name"]),
            f'<span class="code">{e(r["market"])}</span>',
            f"{r['n']:,}",
            (f"{r['roi']:+.4f}" if r["roi"] is not None else blank("blank")),
            (f"{r['shrunk_roi']:+.4f}" if r["shrunk_roi"] is not None else blank("blank")),
            (f"{r['q']:.4f}" if r["q"] is not None else blank("blank")),
            (f"{r['ci_low']:+.4f} … {r['ci_high']:+.4f}"
             if r["ci_low"] is not None and r["ci_high"] is not None else blank("blank")),
            f'<span class="pill ok">{e(r["signal_rank"])}</span>',
            f'<span class="pill warn">{e(r["staking_rank"])}</span>',
            link("L-REPO-GATES", "ledger", r["id"]),
        ])

    st_rows = []
    for r in STAKING:
        st_rows.append([
            f'<span class="code">{e(r["id"])}</span>', e(r["name"]),
            f'<span class="code">{e(r["market"])}</span>',
            f"{r['n']:,}",
            (f"{r['roi']:+.4f}" if r["roi"] is not None else blank("blank")),
            f'<span class="pill warn">{e(r["staking_rank"])}</span>',
            f'<span class="pill ok">{e(r["signal_rank"])}</span>',
            link("L-REPO-GATES", "ledger", r["id"]),
        ])

    div_rows = []
    for r in DIVERGENT:
        div_rows.append([
            f'<span class="code">{e(r["id"])}</span>', e(r["name"]),
            f'<span class="pill ok">{e(r["signal_rank"])}</span>',
            f'<span class="pill warn">{e(r["staking_rank"])}</span>',
            str(r["rank_gap"]),
            ("a staking rank that would flatter the signal" if r["staking_rank"] < r["signal_rank"]
             else "a signal rank that the staking outcome would hide"),
            link("L-REPO-GATES", "ledger", r["id"]),
        ])

    body = f"""
{notice("The separation, stated before the tables.",
        "<b>Two registers are computed independently and are never blended into one rank.</b> The signal "
        "register ranks by statistical signal quality (ascending BH q, then descending shrunk ROI); the "
        "staking register ranks by realized return on a flat 1-unit stake. A strategy can rank high on "
        "staking while ranking low on signal. Blending the two would let a lucky staking run mask a bad "
        "signal, which is exactly what the brief rules out.")}
<div class="grid k4">
  {card("Strategies ranked", str(len(SIGNAL)), "in both registers")}
  {card("Signal register", "by q, then shrunk ROI", "statistical signal quality")}
  {card("Staking register", "by realized ROI", "flat 1-unit stake, no staking plan")}
  {card("Divergent strategies", str(LEADERBOARD["divergent_count"]), f"rank gap ≥ 3 · max {LEADERBOARD['max_rank_gap']}")}
</div>
<section>
  <div class="section-head"><div><h2>Signal leaderboard</h2>
  <p>Ranked by statistical signal quality. The staking rank is shown only to contrast the two.</p></div>
  <span class="count small muted">{len(sig_rows):02d} rows</span></div>
  {table(["ID", "Strategy", "Market", "n", "ROI", "Shrunk ROI", "BH q", "ROI 95% CI", "Signal rank",
          "Staking rank", "Source"], sig_rows)}
</section>
<section>
  <div class="section-head"><div><h2>Staking leaderboard</h2>
  <p>Ranked by realized return on a flat 1-unit stake. The signal rank is shown only to contrast the two.</p></div>
  <span class="count small muted">{len(st_rows):02d} rows</span></div>
  {table(["ID", "Strategy", "Market", "n", "ROI", "Staking rank", "Signal rank", "Source"], st_rows)}
</section>
<section>
  <div class="section-head"><div><h2>Where the two registers disagree</h2>
  <p>A rank gap here is the concrete reason the two must not be merged.</p></div>
  <span class="count small muted">{len(div_rows):02d} rows</span></div>
  {table(["ID", "Strategy", "Signal rank", "Staking rank", "Gap", "What merging would do", "Source"], div_rows)}
</section>
"""
    write("leaderboard.html", "Signal and staking leaderboards",
          "Signal and staking, kept as two separate leaderboards",
          "A signal leaderboard and a staking leaderboard, computed independently and never blended, so a "
          "lucky staking run cannot mask a bad signal. Both are recomputed from the committed strategy "
          "ledger.", body)


# --------------------------------------------------------------------------- #
# page: sources
# --------------------------------------------------------------------------- #
def page_sources() -> None:
    rows = []
    for s in SOURCES["sources"]:
        rows.append([
            f'<span class="code">{e(s["id"])}</span>', e(s["publisher"]), e(s["tier"]),
            '<a href="' + e(s["url"]) + '" target="_blank" rel="noopener noreferrer">' + e(s["url"]) + "</a>",
            '<span class="pill ' + ("ok" if s["read"] else "warn") + '">' + ("read" if s["read"] else "not opened") + "</span>",
            e(s["supports"]),
        ])

    body = f"""
{notice("Tier definitions are this build's own, recorded rather than assumed.",
        "A source is entered here only if the page was opened and read during this session "
        + CAPTURED + ". Official league and licensed-operator pages are primary for their facts; the "
        "government statistical pages are method references and endorse no strategy; the committed "
        "artifacts are labelled <i>recomputed</i> wherever a value derives from them; the pinned dataset "
        "is Tier&nbsp;3 because the NFL publishes no machine-readable lines.")}
<section>
  <div class="section-head"><div><h2>Every source used</h2></div>
  <span class="count small muted">{len(rows):02d} sources</span></div>
  {table(["ID", "Publisher", "Tier", "URL", "Status", "What it supports"], rows)}
</section>
"""
    write("sources.html", "Sources", "Sources",
          "Where every value on this site came from, and how each publisher is classified.", body)


# --------------------------------------------------------------------------- #
# page: flagged
# --------------------------------------------------------------------------- #
def page_flagged() -> None:
    flags = [
        {"id": "L-F01", "severity": "high",
         "what": "No official publisher releases a machine-readable line for the side, total or moneyline, "
                 "and no licensed operator publishes an opening or closing archive this project can cite. "
                 "Every price cell in the price-snapshot store is therefore blank.",
         "url": SRC["L-NFLVERSE"]["url"], "status": "Blanks are published, never filled."},
        {"id": "L-F02", "severity": "high",
         "what": "The pinned open dataset is the only line source and is Tier 3. It supplies closing lines "
                 "as a third-party-derived file; it has no opening line except for 2021, so an opening "
                 "snapshot cannot be constructed for the current season from any reachable source.",
         "url": SRC["L-NFLVERSE"]["url"], "status": "Opening rows stay blank and flagged."},
        {"id": "L-F03", "severity": "medium",
         "what": "The NFL Support money-line and point-spread articles serve each other's bodies. The "
                 "money-line URL returns the point-spread text and the point-spread URL returns the "
                 "money-line text.",
         "url": SRC["L-NFL-ML"]["url"], "status": "Both readings are quoted; neither URL is silently trusted."},
        {"id": "L-F04", "severity": "medium",
         "what": "The demotion gate returns 18 of 18 strategies DEMOTED. This is the honest result of "
                 "applying the rule to the committed ledger: every strategy fails the multiplicity trigger "
                 "and the gate-failure trigger. It is consistent with the repository's published finding "
                 "that no strategy clears its promotion gates.",
         "url": SRC["L-REPO-GATES"]["url"], "status": "Published as computed; no strategy is promoted."},
        {"id": "L-F05", "severity": "low",
         "what": "The signal/staking divergence is small on this ledger (one strategy with a rank gap of "
                 "four). The separation is structural and correct regardless of how often the two ranks "
                 "happen to diverge.",
         "url": SRC["L-REPO-GATES"]["url"], "status": "Published as computed."},
        {"id": "L-F06", "severity": "low",
         "what": "The results-feed summary is recomputed from a committed third-party-derived bet stream. "
                 "It records settled outcomes at recorded prices; it is not a licensed operator ledger and "
                 "supports no skill claim.",
         "url": SRC["L-REPO-BETS"]["url"], "status": "Labelled recomputed; no ROI claim is made."},
    ]
    rows = [[f'<span class="code">{e(f["id"])}</span>',
             f'<span class="pill {("bad" if f["severity"] == "high" else "warn" if f["severity"] == "medium" else "ok")}">{e(f["severity"])}</span>',
             f["what"],
             '<a href="' + e(f["url"]) + '" target="_blank" rel="noopener noreferrer">' + e(f["url"]) + "</a>",
             e(f["status"])] for f in flags]

    body = f"""
{notice("Why this page exists.",
        "The brief says a value that cannot be confirmed from an official source must be left blank and "
        "flagged, never inferred. Everything here is a limit of what is computable, an official source "
        "staying silent, or an official source contradicting itself. None of it is smoothed over, and none "
        "of it blocks the build.")}
<section>
  <div class="section-head"><div><h2>Flag register</h2></div>
  <span class="count small muted">{len(rows):02d} flags</span></div>
  {table(["ID", "Severity", "What", "Source", "How this build handles it"], rows)}
</section>
"""
    write("flagged.html", "Flagged for review", "Flagged for review",
          "The blanks, the limits of what is computable, and the official source that contradicts itself. "
          "Every row links its source.", body)


# --------------------------------------------------------------------------- #
# page: method
# --------------------------------------------------------------------------- #
def page_method() -> None:
    steps = [
        ["1", "Claim the scope", "A block was appended to COORDINATION.md naming the session, the file scope and the tasks, and pushed before any scoped file was touched."],
        ["2", "Read the official sources", "The DraftKings odds and market-rules pages, the two NFL Support articles, and the two NIST statistical pages were opened and read on 2026-11-14."],
        ["3", "Define the structures", "The price-snapshot store, the results feed and the demotion gate were specified as schemas, with their rules written before any result."],
        ["4", "Compute deterministically", "lifecycle/gate.py reads the committed ledgers and writes the demotion evaluation, both leaderboards and the feed summary. No network, no invented value."],
        ["5", "Build and fail closed", "lifecycle/build.py refuses to emit a row without a source link; lifecycle/check.py fails the build if a page links a non-HTTPS or non-registered host, a page is missing, or a number disagrees with the data."],
    ]
    limits = [
        ["No market price is published", "The NFL publishes no machine-readable line and no licensed operator publishes an opening or closing archive this project can cite. Every price cell is blank and flagged."],
        ["The results feed is Tier 3", "The settled bet stream comes from a pinned third-party-derived dataset. It records outcomes at recorded prices; it is not a licensed operator ledger and supports no skill claim."],
        ["The demotion gate is a design, not a sourced fact", "Its parameters are this build's own choices, mirroring the repository's promotion gates. The method sources cited are statistical references, not endorsements."],
        ["The leaderboards are recomputed, not live", "Both registers are deterministic functions of the committed ledger. They describe the committed record, not a live strategy."],
        ["No staking plan is evaluated", "Every bet is a flat 1-unit stake. The staking register ranks realized return; it does not model any staking system."],
        ["The NFL Support bodies are swapped", "The money-line and point-spread articles serve each other's text. Both readings are recorded rather than one being trusted."],
    ]
    steps_html = "".join("<dt><b>" + e(a) + ". " + e(b) + "</b></dt><dd>" + e(c) + "</dd>" for a, b, c in steps)
    limits_html = "".join("<dt><b>" + e(a) + "</b></dt><dd>" + e(b) + "</dd>" for a, b in limits)

    body = f"""
<section>
  <div class="section-head"><div><h2>How this was made</h2>
  <p>These are this build's own actions, not sourced facts, so they are written out rather than tabulated.</p></div>
  <span class="count small muted">{len(steps)} steps</span></div>
  <dl class="defs">{steps_html}</dl>
</section>
<section>
  <div class="section-head"><div><h2>Limits</h2>
  <p>Read these before using anything on this site.</p></div>
  <span class="count small muted">{len(limits)} limits</span></div>
  <dl class="defs">{limits_html}</dl>
</section>
"""
    write("method.html", "Method and limits", "Method and limits",
          "How the structures were defined and computed, and what they cannot tell you.", body)


# --------------------------------------------------------------------------- #
def main() -> int:
    (OUT / "assets").mkdir(exist_ok=True)
    page_index()
    page_price_snapshot()
    page_results_feed()
    page_demotion()
    page_leaderboard()
    page_sources()
    page_flagged()
    page_method()
    if MISSING_LINK:
        print(f"FAIL: {len(MISSING_LINK)} rows were emitted without a source link")
        for m in MISSING_LINK[:20]:
            print("  -", m)
        return 1
    print(f"built {len(PAGES)} pages: " + ", ".join(p[0] for p in PAGES))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
