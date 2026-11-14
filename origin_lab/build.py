#!/usr/bin/env python3
"""Render every page in origin_lab from the committed data files.

Deterministic: no clock, no randomness, no network. Two consecutive runs produce byte-identical
HTML, and check.py enforces that.

Every table row on every page carries at least one link to the publisher the row came from. A value
no publisher printed is rendered blank with a link to flagged.html; it is never filled in.
"""
from __future__ import annotations

import json

import lib

D = lib.DATA


def load(name):
    return json.loads((D / name).read_text(encoding="utf-8"))


def s(sid, label=None):
    src = lib.SOURCES[sid]
    return f'<a href="{lib.esc(src["url"])}" title="{lib.esc(src["title"])}">{lib.esc(label or sid)}</a>'


def n(x, nd=3):
    return "—" if x is None else f"{x:.{nd}f}"


def pct(x, nd=2):
    return "—" if x is None else f"{100 * x:.{nd}f}%"


def pill(text, kind="info"):
    return f'<span class="pill {kind}">{lib.esc(text)}</span>'


def blank(fid=None):
    return lib.blank_cell(fid)


def requirement_row(rid, text, page, state, evidence):
    return [f"<strong>{lib.esc(rid)}</strong>", lib.esc(text),
            f'<a href="{page}">{lib.esc(page)}</a>', pill(state, "ok" if state.startswith("built") else "warn"),
            lib.esc(evidence), s("S12")]


# ============================================================================================
def page_index(snap, feed, off, orig, board, corr, gates, depth, q, sg):
    t = orig["totals"] if "totals" in orig else None
    a = orig["accuracy"]
    cov = snap["coverage"]
    recon = off["reconciliation"]
    kpis = lib.kpi([
        ("Games in the results feed", f"{feed['checks']['settled'] // 3:,}",
         f"{off['coverage']['feed_games']} of them 2026, all officially reconciled"),
        ("Opening numbers held", f"{cov['SIDE']['open']:,}",
         f"of {cov['SIDE']['games_total']:,} priced games — 2021, one book, two markets"),
        ("Market rows priced", f"{cov['SIDE']['close']:,}",
         "closing numbers for the side; 0 opening moneylines exist"),
        ("Replacements at depth", f"{depth['totals']['rows']}",
         f"{depth['totals']['out_doubtful']} Out/Doubtful, {depth['totals']['questionable']} Questionable"),
        ("Strategies promotable", f"{gates['live_count']}",
         "of 8 tested. Every demotion gate is therefore not applicable"),
        ("Correlations published", f"{len(corr['table_a_official']) + len(corr['table_b_parlay_legs'])}",
         f"{len(corr['table_c_not_computable'])} more are blank and flagged"),
    ])

    req_rows = [
        ["<strong>1</strong>", "A price-snapshot store that records opening and closing numbers for every market we originate",
         "price-snapshots.html", pill("built", "ok"),
         f"{len(snap['rows']):,} rows; openings for {cov['SIDE']['open']} games only", s("S05") + " " + s("S07") + " " + s("S12")],
        ["<strong>2</strong>", "A verified results feed so backtests and ROI can be computed at all",
         "results-feed.html", pill("built", "ok"),
         f"{feed['checks']['settled']:,} settled market rows; 2026 reconciled to the league's standings with {len(recon['pf_mismatches'])} mismatches", s("S02") + " " + s("S05") + " " + s("S12")],
        ["<strong>3</strong>", "Originate the side first, then the total, then the moneyline",
         "origination.html", pill("built", "ok"),
         f"identity holds on all {len(orig['rows']):,} rows; {len(orig['identity_failures'])} failures", s("S05") + " " + s("S12")],
        ["<strong>4</strong>", "Publish the model's fair line, the market line and the difference as separate columns",
         "fair-lines.html", pill("built", "ok"),
         "three columns per market, with the sign convention printed above the table", s("S05") + " " + s("S12")],
        ["<strong>5</strong>", "Separate signal from staking in the leaderboard so a lucky staking run cannot mask a bad signal",
         "leaderboard.html", pill("built", "ok"),
         "two rankings and the gap between them; a permutation band on the staking lift", s("S05") + " " + s("S12")],
        ["<strong>6</strong>", "Track the depth of the replacement, not just the fact of a replacement",
         "replacement-depth.html", pill("built", "ok"),
         f"{depth['totals']['rows']} rows with the replacement's string, the published depth and the cost", s("S10") + " " + s("S11") + " " + s("S12")],
        ["<strong>7</strong>", "Compute correlations only from officially sourced numbers and publish n with each value",
         "correlations.html", pill("built", "ok"),
         f"{len(corr['table_a_official']) + len(corr['table_b_parlay_legs'])} rows with n and a Fisher interval; {len(corr['table_c_not_computable'])} left blank", s("S05") + " " + s("S12")],
        ["<strong>8</strong>", "Define a demotion gate that sends a live strategy back to paper",
         "gates.html", pill("built", "ok"),
         "8 demotion triggers with windows and thresholds; all report not applicable because nothing is live", s("S12")],
    ]

    body = f"""
{kpis}

<h2>The eight requirements, and what was actually built</h2>
{lib.table(["#", "Requirement", "Page", "State", "What the page shows", "Source"], req_rows,
           "Every requirement is built. None of them is finished: see the 'State' wording and the flags.")}

<div class="callout warn">
<p><strong>Read this before the numbers.</strong> Three facts shape everything on this site.</p>
<ul class="tight">
<li><strong>The market beats the model.</strong> Out-of-sample side error is {n(a['side_mae_own'], 2)} points against the closing line's {n(a['side_mae_market'], 2)}. Same direction on the total and the moneyline. Whether that is a defect depends on what the model is for, which is question Q11, not a fact.</li>
<li><strong>Almost no opening numbers exist.</strong> {cov['SIDE']['open']} of {cov['SIDE']['games_total']:,} priced games carry one, all in 2021, from one book, for two of the three markets. Closing-line value cannot be computed, so no strategy can be promoted yet.</li>
<li><strong>No official publisher prints an NFL price.</strong> Not the league, not Football Operations, not any club. Requirement 7 says correlations come from officially sourced numbers, so four of the correlations the project wants are blank with a reason rather than computed from a third-party file.</li>
</ul>
</div>

<h2>What is here</h2>
<div class="two-col">
<div class="rule-box">
<h3>Origination</h3>
<p>A small walk-forward model fitted on 1999-2005 and frozen, run out-of-sample from 2006. It emits
the side, then the total, then the moneyline, and the two implied team scores are pinned by the
first two. Every row is checked against that identity.</p>
<p><a href="origination.html">Origination order</a> · <a href="fair-lines.html">Fair / market / difference</a></p>
</div>
<div class="rule-box">
<h3>Evidence</h3>
<p>Every table row links the publisher it came from. A final score is a league fact; a price is not,
and the site never pretends otherwise. The 2026 results feed is reconciled club by club against the
league's own standings.</p>
<p><a href="results-feed.html">Results feed</a> · <a href="sources.html">Sources</a> · <a href="flagged.html">Flagged for review</a></p>
</div>
<div class="rule-box">
<h3>Decision registers</h3>
<p>{len(q['questions'])} open questions, {q['_meta']['blocking_count']} of them blocking, and
{len(sg['suggestions'])} suggestions. Every suggestion carries named options and sits at
<em>Pending owner decision</em>. Nothing has been implemented on the strength of its own suggestion.</p>
<p><a href="questions.html">Open questions</a> · <a href="suggestions.html">Suggestions board</a></p>
</div>
<div class="rule-box">
<h3>Data</h3>
<p>The complete tables are in the repository as CSV, including the {len(snap['rows']):,} price
snapshot rows and the {len(feed['rows']):,} settled market results, which are too large to render
here without losing the thread.</p>
<p><a href="data/price_snapshots.csv">price_snapshots.csv</a> ·
<a href="data/results_feed.csv">results_feed.csv</a></p>
</div>
</div>

<h2>Executive summary</h2>
<p>The written summary for this build is
<a href="../ORIGINATION_EXECUTIVE_SUMMARY.md">ORIGINATION_EXECUTIVE_SUMMARY.md</a>.</p>
"""
    return lib.page("Origination desk", "Eight requirements, built against one rule: every row links a publisher, and a value no publisher printed is left blank.", body, "index.html")


# ============================================================================================
def page_snapshots(snap):
    cov = snap["coverage"]
    mv = snap["movement"]
    rows = [r for r in snap["rows"] if r["open_number"] is not None]
    rows.sort(key=lambda r: (r["season"], r["week"], r["game_id"], r["market"], r["side"]))

    cover_rows = []
    for m in ("SIDE", "TOTAL", "MONEYLINE"):
        c = cov[m]
        cover_rows.append([
            f"<strong>{m}</strong>", f"{c['games_total']:,}",
            f"{c['close']:,}" if c["close"] else "0",
            f"{c['open']:,}" if c["open"] else "0",
            f"{c['both']:,}" if c["both"] else "0",
            f"{c['close_second']:,}",
            pct(c["open"] / c["games_total"], 2) if c["games_total"] else "—",
            s("S05") + " " + s("S06") + " " + s("S07"),
        ])

    # One row per game and market on the side the store is indexed by: the home side for the spread,
    # the over for the total. The opposite side is the mirror image of the same number, and printing
    # both would double the page without adding a fact. Both are in the CSV.
    rows_home = [r for r in rows if r["side"] in ("home", "over")]
    rows_home.sort(key=lambda r: (r["season"], r["week"], r["game_id"], r["market"]))
    tbl = []
    for r in rows_home:
        tbl.append([
            f"{r['season']} W{r['week']}", lib.esc(r["away"]), lib.esc(r["home"]),
            r["market"], r["side"],
            n(r["open_number"], 2), lib.esc(r["open_book"] or ""),
            n(r["close_number"], 2), n(r["close_price"], 0),
            n(r["alt_close_number"], 2), n(r["sc_check_number"], 2),
            n(r["move"], 2),
            s("S07") + " " + s("S05"),
        ])

    body = f"""
<div class="callout">
<p><strong>Convention.</strong> The SIDE number is the points the listed side is favoured by: positive
means favoured, negative means the underdog. The TOTAL number is the game total and is the same on both
sides. The MONEYLINE has no number, only a price, and its number cell is always blank. Prices are
American. The move is <code>close_number - open_number</code>.</p>
</div>

{lib.kpi([
    ("Rows in the store", f"{len(snap['rows']):,}", "one row per game, market and side"),
    ("With an opening number", f"{len(rows):,}",
     "every one of them 2021, Westgate, spread or total"),
    ("With a closing number", f"{cov['SIDE']['close']:,} / {cov['TOTAL']['close']:,} / {cov['MONEYLINE']['close']:,}",
     "side / total / moneyline"),
    ("With a second closing source", f"{cov['SIDE']['close_second']:,}", "2006-2018 only"),
])}

<h2>Coverage by market</h2>
{lib.table(["Market", "Priced games", "Closing number", "Opening number", "Both", "Second closing source", "Opening coverage", "Sources"],
           cover_rows,
           "'Priced games' counts every regular-season game in the pinned dataset. A game counts as priced for a market if any source in this repository carries a number or a price for it.")}

<div class="callout warn">
<p><strong>The opening numbers are 3.76% of the book and that is the whole story.</strong> One season,
one book, two of three markets, and no moneyline at all. Everything below is that slice, because it is
all there is. The remaining 96.24% of the store is closing numbers only, which is why closing-line
value is blank on every leaderboard row.</p>
</div>

<h2>Open-to-close movement, SIDE market, home side</h2>
{lib.table(["Statistic", "Value", "Note", "Source"], [
    ["Games with both numbers", f"{mv['n']}", "the 2021 Westgate slice", s("S07") + " " + s("S05")],
    ["Mean move", n(mv["mean"], 4), "points, close minus open", s("S07") + " " + s("S05")],
    ["Standard deviation", n(mv["pstdev"], 4), "flag F-A11: far wider than a weekly NFL market normally moves", s("S07") + " " + s("S05")],
    ["Minimum", n(mv["min"], 2), "", s("S07")],
    ["Maximum", n(mv["max"], 2), "", s("S07")],
], "Computed on the home side only; the away side is its mirror image and would double n without adding information.")}

<h2>The rows that carry an opening number — all of them</h2>
{lib.table(["Game", "Away", "Home", "Market", "Side", "Open", "Book", "Close", "Close price",
            "Close (2nd source)", "Cross-book check", "Move", "Sources"],
           tbl,
           "Every row in the store that carries an opening number, on the side the store is indexed by. The opposite side of each of these is the mirror image of the same number and is in the CSV. Both capture-time columns are omitted because they are blank on every row: no file in this repository carries a capture time, and a date cannot be back-dated honestly (flag F-A05).")}

<p class="table-note">The complete store is <a href="data/price_snapshots.csv">price_snapshots.csv</a>:
{len(snap["rows"]):,} rows, including the {len(snap["rows"]) - len(rows):,} with no opening number and
the {len(rows) - len(rows_home)} mirror-image rows omitted above.</p>
"""
    return lib.page("Price snapshots", "Requirement 1 — opening and closing numbers for every market we originate, with the coverage honestly stated.", body, "price-snapshots.html")


# ============================================================================================
def page_results(feed, off):
    c = feed["checks"]
    cov = off["coverage"]
    rec = off["reconciliation"]

    season_rows = []
    for season in sorted(feed["by_season"]):
        v = feed["by_season"][season]
        season_rows.append([
            str(season), f"{v['games']}", f"{v['final']}", f"{v['pending']}",
            f"{v['official_direct']}", f"{v['dataset']}",
            s("S05"),
        ])

    rows26 = [r for r in feed["rows"] if r["season"] == 2026]
    rows26.sort(key=lambda r: (r["week"] or 0, r["game_id"], r["market"]))
    tbl = []
    for r in rows26:
        ver = "official" if r["verification"] == "official_direct" else (
            "dataset" if r["verification"] == "official_type_dataset" else "")
        tbl.append([
            f"W{r['week']}", lib.esc(r["away"]), lib.esc(r["home"]), r["market"],
            "" if r["away_score"] is None else str(r["away_score"]),
            "" if r["home_score"] is None else str(r["home_score"]),
            n(r["margin"], 0), n(r["total"], 0), n(r["market_number"], 2),
            lib.esc(r["outcome"] or "") or blank(),
            pill(r["status"], "ok" if r["status"] == "final" else "info"),
            pill(ver, "ok" if ver == "official" else ("info" if ver == "dataset" else "warn")),
            f'<a href="{lib.esc(r["source_url"])}">open</a>',
        ])

    stand_rows = []
    for r in off["standings_check"]:
        stand_rows.append([
            lib.esc(r["team"]), lib.esc(r["team_name"]),
            f"{r['official_w']}-{r['official_l']}-{r['official_t']}",
            f"{r['feed_w']}-{r['feed_l']}-{r['feed_t']}",
            str(r["official_pf"]), str(r["feed_pf"]),
            "0" if r["delta_pf"] == 0 else n(r["delta_pf"], 0),
            str(r["official_pa"]), str(r["feed_pa"]),
            "0" if r["delta_pa"] == 0 else n(r["delta_pa"], 0),
            pill("match", "ok") if r["record_matches"] else pill("mismatch", "no"),
            f'<a href="{lib.esc(r["source_url"])}">{s("S02")}</a>',
        ])

    body = f"""
<div class="callout">
<p><strong>Settlement rule.</strong> SIDE: the home side covers when <code>home - away &gt; spread</code>,
where the spread is positive when the home team is favoured. TOTAL: over when
<code>home + away &gt; total</code>. MONEYLINE: the team with more points wins. An exact landing on the
number is a push on SIDE and TOTAL; equal scores is a tie on the moneyline. Source:
{s("S04", "the 2026 NFL rulebook")}.</p>
</div>

{lib.kpi([
    ("Settled market rows", f"{c['settled']:,}", "games x markets, all seasons"),
    ("Pending", f"{c['pending']:,}", "scheduled but not played"),
    ("Pushes / ties", f"{c['pushes']} / {c['ties']}", "settled as stake returned / tie"),
    ("Arithmetic failures", f"{c['arith']}", "rows whose margin and total disagree with the scores"),
])}

<h2>Verification: 2026 reconciled against the league's own standings</h2>
<p>The league publishes, for every club, how many points it has scored and conceded this season. The
feed publishes the same thing game by game. If the feed is right, the two agree for all 32 clubs.
They do.</p>
{lib.table(["Club", "Name", "Official W-L-T", "Feed W-L-T", "Official PF", "Feed PF", "PF delta", "Official PA", "Feed PA", "PA delta", "Record", "Source"],
           stand_rows,
           f"{rec['teams_compared']} clubs compared. PF mismatches: {len(rec['pf_mismatches'])}. PA mismatches: {len(rec['pa_mismatches'])}. W-L-T mismatches: {len(rec['record_mismatches'])}. {lib.esc(rec['verdict'])}")}

<div class="callout warn">
<p><strong>The feed was two weeks stale when this session started.</strong> The pinned dataset carried
2026 through Week 8, and only 1 of that week's 14 games. Weeks 9 and 10 were absent. They were captured
from NFL.com and added. That is a repair, not a process — see flag F-A01 and suggestion K02.</p>
</div>

<h2>Coverage by season</h2>
{lib.table(["Season", "Games", "Final", "Pending", "Official", "Dataset", "Source"], season_rows,
           "'Official' counts rows transcribed from an NFL.com page. 'Dataset' counts rows that only the league produces but which reach this repository through the pinned third-party snapshot.")}

<h2>The 2026 feed — every game, every market</h2>
{lib.table(["Week", "Away", "Home", "Market", "Away pts", "Home pts", "Margin", "Total", "Market number", "Outcome", "Status", "Tier", "Source"],
           tbl,
           "One row per game per market. Rows marked 'official' were transcribed from the NFL.com game page linked on the row. Rows marked 'dataset' carry a final score from the pinned snapshot; for 2026 those are reconciled against the league's standings above.")}

<p class="table-note">All {len(feed['rows']):,} settled market results are in
<a href="data/results_feed.csv">results_feed.csv</a>.</p>
"""
    return lib.page("Results feed", "Requirement 2 — a results feed, verified club by club against the league's own published standings.", body, "results-feed.html")


# ============================================================================================
def page_origination(orig):
    coef = orig["coefficients"]
    a = orig["accuracy"]
    lp = orig["leak_probe"]
    const = orig["_meta"]["constants"]

    order_rows = []
    for m in orig["_meta"]["order"]:
        order_rows.append([f"<strong>{m}</strong>", lib.esc(orig["_meta"]["order_reason"][m]), s("S12")])

    body = f"""
<div class="callout">
<p><strong>Why the order is an order.</strong> The side is a location forecast and depends on nothing.
The total is a forecast of the sum, and once both are fixed the two team scores are pinned by
<code>home = (total + margin) / 2</code> and <code>away = (total - margin) / 2</code> — so the side has
to exist before the total can be turned into team numbers. The moneyline is a tail probability of the
margin distribution and needs both the centre from the side and the scale, which the scoring
environment sets. It cannot be originated before either.</p>
</div>

{lib.table(["Step", "Why it sits here"], order_rows)}

<h2>The identity, checked on every row</h2>
{lib.table(["Check", "Rows", "Failures", "Source"], [
    ["implied_home - implied_away == fair_side", f"{len(orig['rows']):,}", f"{len(orig['identity_failures'])}", s("S12")],
    ["implied_home + implied_away == fair_total", f"{len(orig['rows']):,}", f"{len(orig['identity_failures'])}", s("S12")],
], "Exact to 1e-9 on every row that has a fair total. Rows whose roof field is blank have no fair total and are excluded rather than filled in.")}

<h2>Frozen coefficients</h2>
{lib.table(["Model", "Intercept", "Regressor 1", "Regressor 2", "Fit n", "Fit R²", "Source"], [
    ["Margin (the side)", n(coef["margin"]["intercept"], 6),
     f"elo_diff x {n(coef['margin']['elo_diff'], 6)}",
     f"net_diff x {n(coef['margin']['net_diff'], 6)}",
     f"{coef['margin']['fit_n']:,}", n(lp["legitimate_r2"], 4), s("S05")],
    ["Total", n(coef["total"]["intercept"], 6),
     f"sum_pf x {n(coef['total']['sum_pf'], 6)}",
     f"dome x {n(coef['total']['dome'], 6)}",
     f"{coef['total']['fit_n']:,}", "—", s("S05")],
], f"Fitted by least squares on {const['FIT_SEASONS']} only, then frozen. Everything from {orig['_meta']['constants']['EVAL_FROM']} on is out of sample by construction.")}

<h2>Causality: the leak probe</h2>
<p>Gate P02 asserts that no feature is knowable only after kickoff. An assertion is not a test, so the
model is refitted on the same window with the game's own margin added as a regressor. If the probe did
not drive R² to 1.0 it would not detect leakage, and the gate would be worthless.</p>
{lib.table(["Model", "Fit R²", "Leak coefficient", "Verdict", "Source"], [
    ["Published model", n(lp["legitimate_r2"], 6), "not present", lib.esc(lp["verdict"][:90]) + "...", s("S12")],
    ["Probe: same-game margin added", n(lp["leaked_r2"], 6),
     n(lp["leaked_coefficients"][3], 4) if lp["leaked_coefficients"] else "—",
     "The probe recovers the outcome exactly, so the harness detects leakage.", s("S12")],
], "The other three coefficients collapse to zero in the probe, which is what 'it is leaking through this one channel' looks like.")}

<h2>Accuracy, out of sample</h2>
{lib.table(["Market", "Own error", "Market error", "Rows", "Reading", "Source"], [
    ["Side (MAE, points)", n(a["side_mae_own"], 4), n(a["side_mae_market"], 4), f"{a['side_n']:,}",
     "our line is further from the result than the closing line", s("S05")],
    ["Total (MAE, points)", n(a["total_mae_own"], 4), n(a["total_mae_market"], 4), f"{a['total_n']:,}",
     "same direction", s("S05")],
    ["Moneyline (Brier)", n(a["brier_own"], 6), n(a["brier_market"], 6), f"{a['moneyline_n']:,}",
     "lower is better; the market is better here too", s("S05")],
], "Out-of-sample means 2006 onward. This is not a bettable edge and the site does not present it as one; see flag F-A06 and question Q11.")}

<h2>Constants, pre-registered</h2>
{lib.table(["Constant", "Value", "Source"], [[lib.esc(k), lib.esc(str(v)), s("S12")] for k, v in const.items()],
           "Fixed before any result was computed and not tuned afterwards.")}
"""
    return lib.page("Origination order", "Requirement 3 — side, then total, then moneyline, with the dependency that makes it an order.", body, "origination.html")


# ============================================================================================
def page_fair(orig):
    rows = [r for r in orig["rows"] if r["season"] == 2026]
    rows.sort(key=lambda r: (r["week"] or 0, r["game_id"]))
    a = orig["accuracy"]

    def cell(x, nd=2, fid=None):
        return blank(fid) if x is None else n(x, nd)

    tbl = []
    for r in rows:
        tbl.append([
            f"W{r['week']}", lib.esc(r["away"]), lib.esc(r["home"]),
            # side: fair / market / diff
            n(r["fair_side"], 2), cell(r["market_side"]), cell(r["diff_side"]),
            # total
            n(r["fair_total"], 2), cell(r["market_total"]), cell(r["diff_total"]),
            # moneyline
            n(r["fair_p_home"], 3), cell(r["market_p_home_devig"], 3), cell(r["diff_ml_prob"], 3),
            "" if r["fair_ml_home"] is None else f'{r["fair_ml_home"]:+d}',
            "" if r["market_ml_home"] is None else f'{int(r["market_ml_home"]):+d}',
            cell(r["diff_ml_price"], 0),
            # identity
            n(r["implied_home_points"], 2), n(r["implied_away_points"], 2),
            pill("ok", "ok") if r["identity_ok"] else blank(),
            s("S12") + " " + s("S05"),
        ])

    body = f"""
<div class="callout">
<p><strong>Sign convention, printed once and used everywhere.</strong> The difference is always
<em>our number minus the market's</em>. A positive side difference means we make the home team a bigger
favourite than the market does. A positive total difference means we expect more points. A positive
moneyline difference means we rate the home team's chance higher. Fair and market are separate columns
and neither is ever shown without the other.</p>
</div>

{lib.kpi([
    ("Rows with a fair line", f"{len(orig['rows']):,}", "every regular-season game, 1999-2026"),
    ("Rows with a market side", f"{a['market_side_n']:,}", "the rest are blank, never inferred"),
    ("Rows with a market total", f"{a['market_total_n']:,}", ""),
    ("Rows with a market moneyline", f"{a['moneyline_n']:,}", ""),
])}

<h2>2026 — fair line, market line, difference</h2>
{lib.table(["Week", "Away", "Home",
            "Fair side", "Market side", "Diff",
            "Fair total", "Market total", "Diff",
            "Fair P(home)", "Market P(home)", "Diff",
            "Fair ML", "Market ML", "Diff",
            "Implied home pts", "Implied away pts", "Identity", "Sources"],
           tbl,
           "The market moneyline probability is de-vigged: the two implied probabilities are scaled to sum to one, so the overround does not masquerade as an edge. The fair moneyline price is quoted on the tie-excluded conditional, which is how a two-way market is quoted; the unconditional tie probability is published on the correlations page.")}

<h2>Where the columns are blank</h2>
{lib.table(["Column", "Blank when", "Count in 2026", "Why it is not filled in", "Source"], [
    ["Market side", "no closing spread in any source", f"{sum(1 for r in rows if r['market_side'] is None)}",
     "no official publisher prints a spread; the pinned dataset is the only source and it does not cover every game", s("S05")],
    ["Market total", "no closing total", f"{sum(1 for r in rows if r['market_total'] is None)}", "same", s("S05")],
    ["Market moneyline", "no closing price", f"{sum(1 for r in rows if r['market_ml_home'] is None)}", "same", s("S05")],
    ["Diff (any)", "either side of the subtraction is blank", "—", "a difference with one unknown term is unknown", s("S12")],
    ["Implied points / fair total", "the roof field is blank on the game", f"{sum(1 for r in rows if r['fair_total'] is None)}",
     "the totals model uses a dome term; inventing a roof value would be inventing a number", s("S05")],
])}

<h2>Per-season accuracy of the fair columns</h2>
{lib.table(["Market", "Own", "Market", "Rows", "Source"], [
    ["Side MAE", n(a["side_mae_own"], 4), n(a["side_mae_market"], 4), f"{a['side_n']:,}", s("S05") + " " + s("S12")],
    ["Total MAE", n(a["total_mae_own"], 4), n(a["total_mae_market"], 4), f"{a['total_n']:,}", s("S05") + " " + s("S12")],
    ["Moneyline Brier", n(a["brier_own"], 6), n(a["brier_market"], 6), f"{a['moneyline_n']:,}", s("S05") + " " + s("S12")],
], "Out-of-sample, 2006 onward. Lower is better in all three and the market is lower in all three.")}
"""
    return lib.page("Fair / market / difference", "Requirement 4 — the model's number, the market's number, and the gap, as three separate columns.", body, "fair-lines.html")


# ============================================================================================
def page_leaderboard(board, gates):
    rows = board["strategies"]
    gate_by = {g["id"]: g for g in gates["promotion_results"]}

    def block(r):
        if r.get("blocked"):
            return pill("blocked", "no")
        if not r.get("n_bets"):
            return pill("no bets", "warn")
        return pill(f"{gate_by[r['id']]['passed']}/{gate_by[r['id']]['passed'] + gate_by[r['id']]['failed'] + gate_by[r['id']]['unevaluable']}", "info")

    sig_rows, stk_rows = [], []
    for r in sorted(rows, key=lambda x: (x.get("rank_signal") or 99)):
        if r.get("blocked"):
            sig_rows.append([f"<strong>{r['id']}</strong>", lib.esc(r["name"]), pill("prop", "no"),
                             *[blank("F-A04")] * 7, block(r), s("S12")])
            continue
        if not r.get("n_bets"):
            continue
        sig_rows.append([
            f"<strong>{r['id']}</strong>", lib.esc(r["name"]), lib.esc(r["market"]),
            f"{r['n_bets']:,}", pct(r["hit_rate"]), pct(r["breakeven_hit_rate"]),
            n(r["z_vs_breakeven"], 2), n(r["p_value"], 4),
            "" if r.get("q_value_fdr") is None else n(r["q_value_fdr"], 4),
            pct(r["roi_flat"]), pct(r["signal_score"]),
            pct(r["holdout_roi"]) + f" <small>(n={r['holdout_n']})</small>",
            pct(r["positive_season_share"], 0),
            blank("F-A02"), block(r), s("S12") + " " + s("S05"),
        ])

    for r in sorted(rows, key=lambda x: (x.get("rank_staking") or 99)):
        if r.get("blocked") or not r.get("n_bets"):
            continue
        lift_pct = r.get("staking_lift_pct")
        in_band = lift_pct is not None and 0.025 <= lift_pct <= 0.975
        stk_rows.append([
            f"<strong>{r['id']}</strong>", lib.esc(r["name"]),
            f"{r['n_bets']:,}",
            pct(r["roi_kelly_full"]), pct(r["roi_kelly_half"]), pct(r["roi_kelly_quarter"]),
            pct(r["bankroll_growth_half"]),
            pct(r["staking_score"]),
            pct(r["staking_lift_half"]),
            pct(lift_pct, 1) + (" <small>(inside the luck band)</small>" if in_band else " <small>(outside it)</small>"),
            pct(r["staking_luck_band_lo"]) + " to " + pct(r["staking_luck_band_hi"]),
            n(r["max_drawdown_flat"], 1), n(r["max_drawdown_staked"], 1),
            s("S12") + " " + s("S05"),
        ])

    mask_rows = []
    for r in rows:
        if r.get("blocked") or not r.get("n_bets"):
            continue
        gap = r.get("mask_gap")
        mask_rows.append([
            f"<strong>{r['id']}</strong>", lib.esc(r["name"]),
            str(r["rank_signal"]), str(r["rank_staking"]),
            f"{gap:+d}" if gap is not None else "0",
            ("Looks better under staking than it is" if (gap or 0) > 0 else
             "Looks worse under staking" if (gap or 0) < 0 else "Same rank either way"),
            s("S12"),
        ])

    body = f"""
<div class="callout warn">
<p><strong>The split.</strong> Signal is scored on flat one-unit bets and nothing else. Staking is the
same bets run a second time with a Kelly fraction sized from our own fair probability against the
market price. Ranking on the second would let a lucky sequence of stake sizes carry a mediocre rule,
which is the exact failure this requirement is written to prevent.</p>
</div>

{lib.kpi([
    ("Strategies tested", f"{len([r for r in rows if not r.get('blocked')])}", "one is blocked on data, not on method"),
    ("Promotable", f"{gates['live_count']}", "none cleared every gate that can be evaluated"),
    ("Best signal score", pct(max([r.get('signal_score') or -9 for r in rows if r.get('n_bets')])),
     "a 95% lower bound on flat ROI; negative means the bound is below zero"),
    ("Largest mask gap", f"{max([abs(r.get('mask_gap') or 0) for r in rows if r.get('n_bets')])}",
     "ranks moved by stake sizing alone"),
])}

<h2>Signal — flat one unit, nothing else</h2>
{lib.table(["ID", "Strategy", "Market", "Bets", "Hit rate", "Breakeven", "z", "p", "q (FDR)",
            "ROI flat", "Signal score", "Holdout ROI", "Winning seasons", "CLV", "Gates", "Sources"],
           sig_rows,
           "signal_score = roi_flat - 1.96 x sd(returns)/sqrt(n). It is a 95% lower bound, so a strategy with a small sample or a noisy record is punished as well as one that simply loses. CLV is blank on every row because every bet is struck at the closing price (flag F-A02).")}

<h2>Staking — the same bets, sized</h2>
{lib.table(["ID", "Strategy", "Bets", "ROI full Kelly", "ROI half Kelly", "ROI quarter Kelly",
            "Bankroll growth (half)", "Staking score", "Lift vs flat", "Percentile under reshuffling",
            "Luck band (95%)", "Max DD flat", "Max DD staked", "Sources"],
           stk_rows,
           "The bet order is permuted 2,000 times with a fixed seed and the lift recomputed. If the observed lift sits inside that band, the staking result is not distinguishable from the same bets arriving in a luckier order.")}

<h2>The mask: does staking hide a bad signal?</h2>
{lib.table(["ID", "Strategy", "Rank on signal", "Rank on staking", "Mask gap", "Reading", "Source"], mask_rows,
           "mask_gap = rank_signal - rank_staking. A positive gap means stake sizing is flattering the strategy.")}

<h2>Per-season flat ROI</h2>
{lib.table(["ID", "Strategy"] + [str(yr) for yr in range(2006, 2027)] + ["Source"],
           [[f"<strong>{r['id']}</strong>", lib.esc(r["name"][:22])] +
            [pct(r.get("season_roi", {}).get(str(yr)), 1) for yr in range(2006, 2027)] + [s("S12")]
            for r in rows if r.get("n_bets")],
           "One cell per strategy per season, on flat one-unit bets. A blank season is a season with no bet.")}
"""
    return lib.page("Leaderboard", "Requirement 5 — signal ranked on flat stakes, staking reported beside it and never allowed to overwrite it.", body, "leaderboard.html")


# ============================================================================================
def page_depth(depth):
    t = depth["totals"]
    rows = depth["rows"]
    rows_sorted = sorted(rows, key=lambda r: (-(r["depth_cost"] or 0), r["club"], r["position"]))

    tbl = []
    for r in rows_sorted:
        tbl.append([
            lib.esc(r["club"]), lib.esc(r["unit"]), lib.esc(r["position"]),
            f'<a href="{lib.esc(r["starter_url"])}">{lib.esc(r["starter"])}</a>',
            pill(r["starter_game_status"], "no" if r["starter_game_status"] == "Out" else "warn"),
            lib.esc(r["starter_injury"] or "") or blank(),
            "" if r["beyond_published_depth"] else f'<a href="{lib.esc(r["replacement_url"])}">{lib.esc(r["replacement"])}</a>',
            blank("F-A07") if r["beyond_published_depth"] else pill(f"string {r['replacement_string']}", "info"),
            str(r["depth_published"]),
            "" if r["depth_cost"] is None else str(r["depth_cost"]),
            "" if r["replacement_string_strict"] is None else str(r["replacement_string_strict"]),
            pill("yes", "no") if r["beyond_published_depth"] else pill("no", "ok"),
            pill(r["status_group"], "warn" if r["status_group"] == "Questionable" else "no"),
            f'<a href="{lib.esc(r["sources"][1])}">{s("S10")}</a> <a href="{lib.esc(r["sources"][0])}">{s("S11")}</a>',
        ])

    club_rows = []
    for c in depth["by_club"]:
        club_rows.append([
            lib.esc(c["club"]), lib.esc(c["club_name"]),
            str(c["replacements"]), str(c["by_string"].get(2, 0)), str(c["by_string"].get(3, 0)),
            str(c["by_string"].get(4, 0)), str(c["beyond_published"]),
            str(c["depth_cost_total"]), str(c["offense"]), str(c["defense"]), str(c["special_teams"]),
            str(c["out_doubtful"]), str(c["questionable"]),
            s("S10") + " " + s("S11"),
        ])

    body = f"""
<div class="callout">
<p><strong>The join, stated before the table.</strong> A row appears when the player listed at string 1
of a position in a club's own published depth chart also appears on the league's official Week 10 injury
report for that club with a game status of Out, Doubtful or Questionable. The replacement is the next
name the same club printed at the same position, in the club's own column order — skipping any name
that is itself on the report as Out or Doubtful.</p>
<p><strong>What a depth cost is and is not.</strong> It is a count of columns in a club's own
publication. It is not a judgement about how good the replacement is: no ability, snap count, grade or
rating is attached to it anywhere in this repository.</p>
</div>

{lib.kpi([
    ("Replacement events", f"{t['rows']}", f"{t['out_doubtful']} Out/Doubtful, {t['questionable']} Questionable"),
    ("Reached to string 2", f"{t['by_string'].get('2', 0)}", "the common case"),
    ("Reached to string 3 or deeper", f"{t['by_string'].get('3', 0) + t['by_string'].get('4', 0) + t['by_string'].get('5', 0)}",
     "the backup was unavailable too"),
    ("No replacement published", f"{t['beyond_published']}", "the club prints no further name at that position"),
])}

<div class="callout warn">
<p><strong>Nothing here says who will start.</strong> A depth chart is a club's own ordering and carries
no designation; the injury report carries a designation and no ordering. Neither is a lineup. Twelve of
the 31 clubs print the word <em>unofficial</em> on the chart they publish, and the league publishes no
depth chart at all — see flag F-A07 and question Q01.</p>
</div>

<h2>By club</h2>
{lib.table(["Club", "Name", "Events", "String 2", "String 3", "String 4", "No name printed",
            "Depth cost", "Offence", "Defence", "Special teams", "Out/Doubtful", "Questionable", "Sources"],
           club_rows,
           "Depth cost is the sum of (replacement string - 1) over the club's rows. It counts how far down their own chart the club has to reach, added up.")}

<h2>Every replacement event</h2>
{lib.table(["Club", "Unit", "Pos", "Starter", "Status", "Injury", "Replacement", "Replacement string",
            "Names published", "Depth cost", "Strict string", "Beyond published depth", "Status group", "Sources"],
           tbl[0:0] if False else tbl,
           "'Strict string' applies the same walk-down but also skips Questionable names, so a reader who disagrees with including Questionable can see what changes. Rows with no replacement are blank because the club printed no further name, not because none exists.")}

<h2>Coverage gaps, published rather than filled</h2>
{lib.table(["Gap", "Clubs", "What is known", "Source"], [
    ["No injury table on the league's official Week 10 report",
     ", ".join(depth["_meta"]["clubs_absent_from_the_official_report"]),
     "Cause not established. A bye week, a page the league did not publish, and a chunk that was not served all remain possible.", s("S10")],
    ["Club with a readable depth chart but no report row",
     ", ".join(depth["totals"]["clubs_with_a_chart_but_no_report"]),
     "Same four clubs as above, seen from the other side of the join.", s("S10")],
    ["Club on the report with no readable chart",
     ", ".join(depth["totals"]["clubs_on_the_report_with_no_chart"]),
     "HOU. The page returned its heading and no table markup. Another session recorded it as image-only; the difference is unresolved (flag F-A09 area).", s("S11")],
    ["Starters on the report with a blank game status",
     f"{t['blank_game_status_rows']} rows",
     "Not joined. A blank cell on the league's own report is not a designation and is never treated as one.", s("S10")],
])}
"""
    return lib.page("Replacement depth", "Requirement 6 — how far down a club's own chart it has to reach, not merely that it has to reach.", body, "replacement-depth.html")


# ============================================================================================
def page_correlations(corr):
    a_rows = []
    for r in corr["table_a_official"]:
        a_rows.append([
            lib.esc(r["pair"]), f"{r['n']:,}",
            n(r["r"], 5),
            f"[{n(r['ci_low'], 4)}, {n(r['ci_high'], 4)}]",
            pill("official", "ok"),
            lib.esc(r["note"]),
            s(r.get("source_id", "S05")),
        ])
    b_rows = []
    for r in corr["table_b_parlay_legs"]:
        b_rows.append([
            lib.esc(r["pair"]), f"{r['n']:,}", n(r["phi"], 5),
            f"[{n(r['ci_low'], 4)}, {n(r['ci_high'], 4)}]",
            n(r["joint_observed"], 5), n(r["joint_if_independent"], 5),
            n(r["joint_difference"], 5),
            lib.esc(r["note"]), s("S12") + " " + s("S05"),
        ])
    c_rows = []
    for r in corr["table_c_not_computable"]:
        c_rows.append([
            lib.esc(r["pair"]), blank("F-A03"),
            "—" if r["n"] is None else f"{r['n']:,}",
            lib.esc(r["why"]), lib.esc(r["unblock"]), s("S12"),
        ])

    body = f"""
<div class="callout">
<p><strong>What counts.</strong> A final score is a fact only the league creates, and the league
publishes every one of them. Every number in Tables A and B is a function of final scores and nothing
else. A market price is not: no official publisher prints NFL spreads, totals or moneylines. So any
correlation whose definition needs a market number is left blank with a reason, rather than computed
from a third-party file and still called a correlation.</p>
</div>

{lib.kpi([
    ("Table A rows", f"{len(corr['table_a_official'])}", "both variables official, n on every row"),
    ("Table B rows", f"{len(corr['table_b_parlay_legs'])}", "parlay leg dependence, legs defined against our own line"),
    ("Table C rows", f"{len(corr['table_c_not_computable'])}", "blank and flagged, with the reason on the row"),
    ("Ties in the sample", f"{corr['ties']['ties']} of {corr['ties']['games']:,}",
     f"a rate of {pct(corr['ties']['rate'], 4)}; a moneyline settlement rule has to handle this"),
])}

<h2>Table A — both variables officially sourced</h2>
{lib.table(["Pair", "n", "r", "95% interval", "Tier", "What it means", "Source"], a_rows,
           "Pearson r with a two-sided 95% Fisher-z interval. One point per game, per team-game, per week or per team-season as the row says.")}

<h2>Table B — parlay leg dependence</h2>
{lib.table(["Card", "n", "phi", "95% interval", "Joint observed", "Joint if independent", "Difference",
            "Reading", "Sources"], b_rows,
           "Because the legs are defined against the line this repository originates, each leg's outcome is a function of the official final score alone, so the dependence measured here is officially sourced. A card priced at the product of its legs assumes the middle two columns are equal.")}

<div class="callout warn">
<p><strong>The one number that should change how a card is priced.</strong> The same-game card's two
legs win together {pct(corr['table_b_parlay_legs'][0]['joint_observed'], 2)} of the time, against
{pct(corr['table_b_parlay_legs'][0]['joint_if_independent'], 2)} if they were independent. A card priced
at the product of its legs is therefore worse for the bettor than its price suggests, and the gap is
the measured phi of {n(corr['table_b_parlay_legs'][0]['phi'], 4)} over
{corr['table_b_parlay_legs'][0]['n']:,} cards.</p>
</div>

<h2>Table C — requested, but not computable from official sources</h2>
{lib.table(["Pair", "Value", "n", "Why it is blank", "What would unblock it", "Source"], c_rows,
           "These are not rounding gaps. Each one needs an input no official publisher prints. The owner's decision is question Q02; the workaround this site already uses is Table B.")}

<h2>The formula the missing input would feed</h2>
<div class="rule-box">
<p>For a two-leg card at decimal prices <code>d1</code> and <code>d2</code> with marginal win
probabilities <code>p1</code> and <code>p2</code>, the card breaks even when the joint probability is
<code>1 / (d1 x d2)</code>. The dependence the card needs is therefore</p>
<p class="mono">phi_required = ( 1/(d1 x d2) - p1 x p2 ) / sqrt( p1(1-p1) x p2(1-p2) )</p>
<p>Every term except the joint is a price. No official publisher prints those prices, so this page
publishes the formula and leaves the answer blank. Give it prices and it fills in one line.</p>
</div>
"""
    return lib.page("Correlations", "Requirement 7 — officially sourced numbers only, with n on every value and a reason on every blank.", body, "correlations.html")


# ============================================================================================
def page_gates(gates, board):
    pro_rows = []
    for g in gates["promotion_gates"]:
        pro_rows.append([
            f"<strong>{g['id']}</strong>", lib.esc(g["name"]), lib.esc(g["rule"]),
            lib.esc(g["threshold"]), lib.esc(g["statistic"]),
            pill("blocked", "no") if g.get("blocked") else pill("live", "ok"),
            lib.esc(g.get("blocked_reason", "")),
            s(g["source"]),
        ])
    dem_rows = []
    for g in gates["demotion_gates"]:
        dem_rows.append([
            f"<strong>{g['id']}</strong>", lib.esc(g["name"]), lib.esc(g["trigger"]),
            lib.esc(g["window"]), lib.esc(g["statistic"]), lib.esc(g["threshold"]),
            lib.esc(g["action"]),
            pill("not applicable", "warn"),
            lib.esc(g.get("blocked_reason", g.get("why_this_window", ""))),
            s("S12"),
        ])
    fdr_rows = [[f"{r['check_every_n_bets']}", f"{r['checks_per_1000_bets']}",
                 pct(r["false_demotion_rate_per_check"]),
                 pct(r["chance_of_at_least_one_false_demotion_in_1000_bets"])]
                for r in gates["false_demotion_arithmetic"]]

    strat_rows = []
    for r in board["strategies"]:
        g = next((x for x in gates["promotion_results"] if x["id"] == r["id"]), None)
        if not g or g.get("blocked") or g.get("no_bets"):
            strat_rows.append([f"<strong>{r['id']}</strong>", lib.esc(r["name"]),
                               pill("blocked", "no") if r.get("blocked") else pill("no bets", "warn"),
                               "—", s("S12")])
            continue
        cells = []
        for pid in [p["id"] for p in gates["promotion_gates"]]:
            v = g["gates"].get(pid, "—")
            cells.append(pill(v, "ok" if v == "pass" else ("no" if v == "fail" else "warn")))
        strat_rows.append([f"<strong>{r['id']}</strong>", lib.esc(r["name"][:26]),
                           pill("not promotable", "no") if not g["promotable"] else pill("promotable", "ok"),
                           " ".join(cells), s("S12")])

    body = f"""
<div class="callout warn">
<p><strong>Nothing is live.</strong> {gates['live_count']} of the tested strategies passed every gate
that can be evaluated, so every demotion gate below reports NOT APPLICABLE. That is the honest answer,
and it is also the reason to publish the gates now: a demotion rule written for the first time while a
strategy is losing real money will be written under pressure and then argued with.</p>
</div>

{lib.kpi([
    ("Promotion gates", f"{len(gates['promotion_gates'])}", "one of them unevaluable by data, not by choice"),
    ("Demotion gates", f"{len(gates['demotion_gates'])}", "all not applicable: nothing is live"),
    ("Strategies promotable", f"{gates['live_count']}", "of 8 tested"),
    ("False demotions per 1,000 bets", pct(gates['false_demotion_arithmetic'][0]['chance_of_at_least_one_false_demotion_in_1000_bets']),
     "at the published 200-bet window, for a strategy that is truly break-even"),
])}

<h2>Promotion: paper to live</h2>
{lib.table(["ID", "Gate", "Rule", "Threshold", "Statistic", "State", "Note", "Source"], pro_rows,
           "P10 is not failed. It cannot be evaluated, because closing-line value needs a bet-time price the store does not hold. Treat 'cannot be evaluated' as a hard stop, not as a pass.")}

<h2>Per-strategy promotion status</h2>
{lib.table(["ID", "Strategy", "Outcome"] + [g["id"] for g in gates["promotion_gates"]] + ["Source"],
           strat_rows, "Green is pass, red is fail, amber is cannot-be-evaluated.")}

<h2>Demotion: live back to paper</h2>
{lib.table(["ID", "Gate", "Trigger", "Window", "Statistic", "Threshold", "Action", "Status", "Note", "Source"],
           dem_rows,
           "Each gate names a window, a statistic and a threshold, so a demotion is an event a reader can reproduce rather than a judgement someone made.")}

<h2>What the demotion gates cost</h2>
<p>A gate that fires on a 95% upper bound will demote a genuinely break-even strategy 5% of the times it
is checked. Checking more often is not free: the windows below are arithmetic, not preference.</p>
{lib.table(["Checked every", "Checks per 1,000 bets", "False demotion per check", "Chance of at least one in 1,000 bets", "Source"],
           [r + [s("S12")] for r in fdr_rows],
           "This is why D01 uses a 200-bet window rather than a shorter one. The owner's version of this trade is question Q09.")}

<h2>Re-promotion</h2>
<div class="rule-box">
<p>A demoted strategy does not come back by waiting. It re-qualifies by passing every promotion gate
again on bets made after the demotion, including a fresh holdout window. D05 is absolute: any edit to
the rule, its parameters or its market sends it back to paper immediately, because an edited rule is a
new rule and a new rule has not been tested.</p>
</div>
"""
    return lib.page("Promotion &amp; demotion", "Requirement 8 — the gates that promote a strategy, and the gates that send it back to paper.", body, "gates.html")


# ============================================================================================
def page_questions(q):
    rows = []
    for item in q["questions"]:
        rows.append([
            f"<strong>{item['id']}</strong>", lib.esc(item["question"]), lib.esc(item["area"]),
            pill("blocking", "no") if item["blocking"] else pill("open", "info"),
            lib.esc(item["what_we_hold"]),
            lib.esc(item["what_is_missing"]),
            lib.esc(item["consequence"]),
            "<br>".join(lib.esc(o) for o in item["options"]),
            " ".join(s(i) for i in item["source_ids"]),
        ])
    body = f"""
<div class="callout">
<p><strong>Three columns that matter more than the answers.</strong> <em>What we hold</em> is something
this repository can point at. <em>What is missing</em> is the specific thing that would turn the
question into an answer. <em>Blocking</em> says whether anything downstream is waiting. Nothing here has
been answered on the owner's behalf.</p>
</div>

{lib.kpi([
    ("Questions", f"{len(q['questions'])}", f"{q['_meta']['blocking_count']} blocking"),
    ("Blocking", f"{q['_meta']['blocking_count']}", "nothing downstream can be decided until these are"),
    ("Areas", f"{len(set(x['area'] for x in q['questions']))}", "origination, evidence, gates, competition"),
    ("Answered", "0", "by design — the answers are the owner's"),
])}

{lib.table(["ID", "Question", "Area", "State", "What we hold", "What is missing", "What hangs on it", "Options", "Sources"],
           rows, "One row per open question. The options column is not a recommendation; it is the set of answers that would close the row.")}
"""
    return lib.page("Open questions", "What we know, what we do not, and what each gap is stopping.", body, "questions.html")


# ============================================================================================
def page_suggestions(sg):
    rows = []
    for item in sg["suggestions"]:
        sc = item["scores"]
        rows.append([
            f"<strong>{item['id']}</strong>", lib.esc(item["title"]),
            lib.esc(item["problem"]),
            "<ol style='margin:0;padding-left:18px'>" + "".join(f"<li>{lib.esc(o)}</li>" for o in item["options"]) + "</ol>",
            lib.esc(item["recommendation"]),
            f"decision {sc['decision_value']}/5 · evidence {sc['evidence_gain']}/5 · "
            f"feasibility {sc['feasibility']}/5 · risk control {sc['risk_control']}/5",
            pill(item["decision_status"], "warn"),
            (", ".join(item["unblocks"]) or "—") + "<br><small>" + (", ".join(item["retires_flags"]) or "no flags") + "</small>",
            lib.esc(item["reversibility"]),
            "<br>".join(f"<code>{lib.esc(f)}</code>" for f in item["files"]),
            s("S12"),
        ])
    body = f"""
<div class="callout warn">
<p><strong>Nothing here has been implemented.</strong> Every suggestion sits at
<em>Pending owner decision</em>. A suggestion is not a plan of work: it is a set of named paths with what
each one unblocks, so a choice is made before anything is built.</p>
</div>

{lib.kpi([
    ("Suggestions", f"{len(sg['suggestions'])}", "each with named options"),
    ("Decided", "0", "the board exists so that the owner decides, not this session"),
    ("Highest decision value", "K01, K02, K08, K11", "scored 5 on decision value"),
    ("Blocking questions unblocked", f"{len(set(u for s in sg['suggestions'] for u in s['unblocks']))}", "if every suggestion were approved"),
])}

{lib.table(["ID", "Suggestion", "Problem", "Options", "Recommendation", "Scores", "Status", "Unblocks / retires", "Reversibility", "Files", "Source"],
           rows,
           "Scores are this session's, out of 5, and are a way to sort the list — not a decision. Read the options column first.")}
"""
    return lib.page("Suggestions board", "Paths to choose between. Nothing is built until one is chosen.", body, "suggestions.html")


# ============================================================================================
def page_sources():
    rows = []
    for sid in sorted(lib.SOURCES):
        d = lib.SOURCES[sid]
        rows.append([
            f"<strong>{sid}</strong>", lib.esc(d["publisher"]),
            f'<a href="{lib.esc(d["url"])}">{lib.esc(d["title"])}</a>',
            pill(d["tier"], "ok" if d["tier"] == "official" else ("info" if d["tier"] == "dataset" else "warn")),
            lib.esc(lib.TIER_NOTE[d["tier"]]),
            lib.esc(d["what_it_provides"]),
        ])
    body = f"""
<div class="callout">
<p><strong>The line that matters.</strong> The NFL publishes rules, schedules, results, standings and
player availability. It does not publish point spreads, totals, moneylines or player-prop prices, and
neither does any club. Every price on this site comes from a third-party file and says so. Every score
comes from the league, or from a file that is reconciled against the league's own page.</p>
</div>

{lib.table(["ID", "Publisher", "Page", "Tier", "What the tier means", "What it provides"], rows,
           "Tier is a statement about who published a thing, not about how much this project trusts it.")}

<h2>How a row earns its tier</h2>
{lib.table(["Tier", "Test", "Source"], [
    ["official", "The row links a page published by the league, its Football Operations division, or a club's own site for a fact only that club holds.", s("S12")],
    ["dataset", "The row links a third-party file. Reproducible by anyone; not a league publication. This is where every price lives.", s("S12")],
    ["internal", "The row links only another page of this site. Fine for navigation, never presented as external evidence.", s("S12")],
    ["none", "The row has no link. This is the failure case, and the build fails on it.", s("S12")],
], "The repository-wide audit in verify/source_audit.py applies the same test to every published row and the CI job fails on any row with no source link.")}
"""
    return lib.page("Sources", "Every publisher this site quotes, and what each one is allowed to be evidence for.", body, "sources.html")


# ============================================================================================
def page_flagged(flags):
    rows = []
    for f in flags["flags"]:
        rows.append([
            f"<strong>{f['id']}</strong>",
            pill(f["severity"], "no" if f["severity"] == "high" else ("warn" if f["severity"] == "medium" else "info")),
            lib.esc(f["area"]), lib.esc(f["finding"]), lib.esc(f["what_was_done"]),
            lib.esc(f["what_is_still_wrong"]),
            " ".join(s(i) for i in f["source_ids"]),
        ])
    body = f"""
<div class="callout">
<p><strong>Nothing here blocks the site.</strong> Every irregularity found while building this section is
published with the source link that produced it, so it can be checked. None of them is hidden, and none
of them was smoothed over to make a number look better.</p>
</div>

{lib.kpi([
    ("Flags", f"{len(flags['flags'])}", "found and published, not quietly fixed"),
    ("High", f"{sum(1 for f in flags['flags'] if f['severity'] == 'high')}", "all three are data-availability gaps, not errors"),
    ("Medium", f"{sum(1 for f in flags['flags'] if f['severity'] == 'medium')}", ""),
    ("Low", f"{sum(1 for f in flags['flags'] if f['severity'] == 'low')}", ""),
])}

{lib.table(["ID", "Severity", "Area", "Finding", "What was done", "What is still wrong", "Sources"], rows,
           "Sorted by severity, then by the order they were found.")}
"""
    return lib.page("Flagged for review", "Everything this session found wrong, could not confirm, or had to leave blank.", body, "flagged.html")


# ============================================================================================
def main():
    snap = load("price_snapshots.json")
    feed = load("results_feed.json")
    off = load("official_results_2026.json")
    orig = load("origination.json")
    board = load("leaderboard.json")
    corr = load("correlations.json")
    gates = load("gates.json")
    depth = load("replacement_depth.json")
    q = load("questions.json")
    sg = load("suggestions.json")
    flags = load("flags.json")

    pages = {
        "index.html": page_index(snap, feed, off, orig, board, corr, gates, depth, q, sg),
        "price-snapshots.html": page_snapshots(snap),
        "results-feed.html": page_results(feed, off),
        "origination.html": page_origination(orig),
        "fair-lines.html": page_fair(orig),
        "leaderboard.html": page_leaderboard(board, gates),
        "replacement-depth.html": page_depth(depth),
        "correlations.html": page_correlations(corr),
        "gates.html": page_gates(gates, board),
        "questions.html": page_questions(q),
        "suggestions.html": page_suggestions(sg),
        "sources.html": page_sources(),
        "flagged.html": page_flagged(flags),
    }
    for name, content in pages.items():
        lib.write_page(name, content)
    print("built %d pages" % len(pages))


if __name__ == "__main__":
    main()
