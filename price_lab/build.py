#!/usr/bin/env python3
"""Build the Snapshot Desk pages.

Design rules inherited from every prior session in this repository:
  * every table row carries at least one link to the page the value came from (official publisher
    where the fact is official, the pinned dataset file where it is dataset, this repository's own
    artifacts where it is recomputed);
  * a value no source states is printed as a flagged blank, never filled in;
  * the build is deterministic (stdlib only, no clock, no network) and check.py re-derives every
    published number from the committed data files.

Usage: python3 price_lab/build.py     (after python3 price_lab/data_build.py)
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE
D = HERE / "data"

PIN = "a270278f3ac4e937295fe6a27814b3c4a2b62645"
CHECKED = "2026-11-14"
REPO_CHECK_URL = "https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/check.py"
REPO_BUILD_URL = "https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/build.py"
REPO_COORD_URL = "https://github.com/karagemop466-tech/Korea3/blob/main/COORDINATION.md"

summary = json.loads((D / "summary.json").read_text())
official = json.loads((D / "official_results_2026.json").read_text())
ledger = list(csv.DictReader((D / "origination_ledger.csv").open()))
lb = list(csv.DictReader((D / "leaderboard_signal_staking.csv").open()))
feed26 = list(csv.DictReader((D / "results_feed_2026.csv").open()))

SNAP = D / "snapshots.csv"
HIST = D / "results_history.csv"

SNAP_HEAD = SNAP.open().readline().strip().split(",")
N_SNAP = sum(1 for _ in SNAP.open()) - 1
N_HIST = sum(1 for _ in HIST.open()) - 1

PAGES = [
    ("index.html", "Snapshot Desk", "Overview"),
    ("snapshots.html", "Price-snapshot store", "Snapshots"),
    ("results.html", "Verified results feed", "Results"),
    ("origination-order.html", "Origination order", "Order"),
    ("leaderboard.html", "Leaderboard: signal vs staking", "Leaderboard"),
    ("demotion.html", "Demotion gate", "Demotion"),
    ("suggestions.html", "Suggestions", "Suggestions"),
    ("open-questions.html", "Open questions", "Questions"),
    ("flagged.html", "Flagged for review", "Flagged"),
    ("sources.html", "Sources", "Sources"),
    ("executive-summary.html", "Executive summary", "Executive"),
]

MISSING_LINK: list[str] = []

CSS = """
:root{--ink:#182430;--mut:#5b6b7b;--line:#dfe6ec;--bg:#f6f8fa;--card:#fff;--ok:#127a3d;--warn:#9a5b00;--bad:#a3271e;--off:#3457d5}
*{box-sizing:border-box}body{margin:0;font:15px/1.55 -apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Arial,sans-serif;color:var(--ink);background:var(--bg)}
header.site{background:#0f2740;color:#fff;padding:18px 0 0}
.wrap{max-width:1180px;margin:0 auto;padding:0 20px}
.brand{display:flex;gap:10px;align-items:center;color:#fff;text-decoration:none}
.mark{width:34px;height:34px;border-radius:8px;background:#c8102e;color:#fff;display:inline-flex;align-items:center;justify-content:center;font-weight:800}
.brand small{display:block;color:#b9c9d9;font-weight:400}
.badge{font-size:12px;border:1px solid #3c5a78;border-radius:999px;padding:3px 10px;color:#c9d7e4}
nav.main{display:flex;flex-wrap:wrap;gap:2px;margin-top:14px}
nav.main a{color:#d7e2ec;text-decoration:none;font-size:13.5px;padding:9px 12px;border-radius:8px 8px 0 0}
nav.main a:hover{background:#1a3a5c}nav.main a.active{background:var(--bg);color:var(--ink);font-weight:600}
main{padding:26px 0 60px}
h1{font-size:30px;margin:.2em 0}h2{font-size:21px;margin:34px 0 8px}h3{font-size:16px;margin:20px 0 6px}
.eyebrow{color:var(--off);font-weight:700;font-size:12.5px;text-transform:uppercase;letter-spacing:.08em}
.lead{color:var(--mut);max-width:900px}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:14px 16px}
.grid{display:grid;gap:12px}.k4{grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}
.num{font-size:26px;font-weight:800}.tag{font-size:12px;color:var(--mut);text-transform:uppercase;letter-spacing:.06em}
.sub{font-size:12.5px;color:var(--mut)}
table{border-collapse:collapse;width:100%;background:#fff;font-size:13.5px;margin:8px 0}
th,td{border:1px solid var(--line);padding:6px 8px;text-align:left;vertical-align:top}
th{background:#eef3f7;font-size:12.5px}
.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:10px}
a{color:var(--off)}a.src{white-space:nowrap}
.pill{display:inline-block;font-size:11.5px;font-weight:700;border-radius:999px;padding:2px 9px}
.pill.ok{background:#e2f3e8;color:var(--ok)}.pill.warn{background:#fdf0dc;color:var(--warn)}
.pill.bad{background:#fbe4e2;color:var(--bad)}.pill.info{background:#e7edfb;color:var(--off)}
.blank{background:#fff7d6;border:1px dashed #d3b23c;color:#7a621a;font-size:11.5px;border-radius:6px;padding:1px 7px;white-space:nowrap}
.note{background:#eef6ff;border:1px solid #cfe0f5;border-radius:10px;padding:10px 14px;font-size:13.5px}
.warnbox{background:#fff8ec;border:1px solid #eed9ad;border-radius:10px;padding:10px 14px;font-size:13.5px}
code{background:#eef1f4;border-radius:4px;padding:1px 5px;font-size:12.5px}
footer{color:var(--mut);font-size:12.5px;padding:18px 0 40px}
"""


def e(x) -> str:
    import html
    return html.escape(str(x), quote=True)


def link(url: str, label: str = "source") -> str:
    if not url:
        MISSING_LINK.append(label)
        return '<span class="blank">no source</span>'
    return (f'<a class="src" href="{e(url)}" target="_blank" rel="noopener noreferrer" '
            f'title="{e(url)}">{e(label)} &#8599;</a>')


def ilink(url: str, label: str) -> str:
    return f'<a href="{e(url)}">{e(label)}</a>'


def blank(why: str) -> str:
    return f'<span class="blank" title="{e(why)}">blank &mdash; {e(why)}</span>'


def pill(kind: str, text: str) -> str:
    return f'<span class="pill {kind}">{e(text)}</span>'


def table(headers, rows, note=None):
    th = "".join(f"<th>{h}</th>" for h in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    n = (f'<div class="sub" style="margin:4px 0 0">{note}</div>' if note else "")
    return (f'<div class="scroll"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>{n}')


def shell(slug: str, title: str, h1: str, lead: str, body: str) -> str:
    nav = []
    for fn, t, label in PAGES:
        cls = ' class="active"' if fn == slug else ""
        nav.append(f'<a href="{fn}"{cls}>{e(label)}</a>')
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} | Snapshot Desk | NFL Line Lab</title>
<meta name="description" content="Price-snapshot store, verified results feed, origination order, signal-vs-staking leaderboard and demotion gate for the NFL line-origination research repository.">
<style>{CSS}</style>
</head>
<body>
<header class="site"><div class="wrap">
  <div style="display:flex;justify-content:space-between;align-items:center">
    <a class="brand" href="index.html"><span class="mark">N</span>
      <span><strong>Snapshot Desk</strong><small>price snapshots &middot; results feed &middot; leaderboard &middot; demotion gate</small></span></a>
    <span class="badge">Research only &middot; no betting advice</span>
  </div>
  <nav class="main" aria-label="Snapshot Desk">{''}</nav>
</div></header>
<main class="wrap">
  <div class="eyebrow">Snapshot Desk &middot; session arena/88791c5c-korea3 &middot; {CHECKED}</div>
  <h1>{e(h1)}</h1>
  <p class="lead">{lead}</p>
  {body}
</main>
<footer class="wrap">Part of the <a href="../hub/index.html">consolidated dashboard</a> &middot;
<a href="../hub/flagged.html">Flagged for Review (repository-wide)</a> &middot; built from the pinned dataset
<a href="https://github.com/nflverse/nfldata/blob/{PIN}/data/games.csv" target="_blank" rel="noopener noreferrer">nflverse/nfldata@{PIN[:7]}</a>
and official NFL.com pages opened {CHECKED}. Values with no official source are blanks, never guesses.</footer>
</body></html>"""


def inject_nav(html: str) -> str:
    nav = []
    for fn, t, label in PAGES:
        nav.append(f'<a href="{fn}">{e(label)}</a>')
    return html.replace("<nav class=\"main\" aria-label=\"Snapshot Desk\"></nav>",
                        '<nav class="main" aria-label="Snapshot Desk">' + "".join(nav) + "</nav>")


# --------------------------------------------------------------------------- #
# page: snapshots
# --------------------------------------------------------------------------- #
def page_snapshots() -> str:
    s = summary["snapshots"]
    mv_s, mv_t = s["spread_movement_2021"], s["total_movement_2021"]

    # fair/market/difference showcase: the 28 upcoming fixtures with a posted market line
    rows = []
    for r in ledger:
        if r["completed"] == "no" and r["market_close_spread"]:
            rows.append([
                e(f"{r['away_team']} @ {r['home_team']}"),
                e(f"Wk {r['week']} &middot; {r['gameday']}"),
                e(r["fair_spread"]), e(r["market_close_spread"]), e(r["diff_spread"]),
                e(r["fair_total"]), e(r["market_close_total"]), e(r["diff_total"]),
                e(r["fair_ml_home_odds"]),
                blank("no official moneyline captured for unplayed fixtures") if not r["market_close_ml_home_odds"] else e(r["market_close_ml_home_odds"]),
                link("https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/own_lines_upcoming.csv", "ledger"),
            ])

    cov = [
        ["open", "SPREAD + TOTAL", f"{s['open_rows']:,}", "2021 only (WSGT, 272 games)",
         link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/initial_lines.csv", "initial_lines.csv")],
        ["open", "MONEYLINE", blank("no official opening moneyline is published in the pinned dataset"),
         "—", link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/initial_lines.csv", "initial_lines.csv")],
        ["close", "SPREAD + TOTAL + MONEYLINE", f"{s['close_rows']:,}",
         f"{s['close_seasons_spread'][0]}–{s['close_seasons_spread'][1]} (moneylines {s['close_seasons_ml'][0]}–{s['close_seasons_ml'][1]})",
         link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/games.csv", "games.csv")],
        ["fair (ours)", "SPREAD + TOTAL + derived ML", f"{s['fair_rows']:,}",
         "2000–2026 model + 164 originated unplayed fixtures",
         link("https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/model_predictions.csv", "model_predictions.csv")],
        ["total", "all rows", f"{s['rows_total']:,}", "snapshots.csv", link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/snapshots.csv", "snapshots.csv")],
    ]

    movers = top_movers()

    body = f"""
<h2>What this store is</h2>
<div class="note">One row per originated market per snapshot: <strong>open</strong> (the earliest recorded market
number), <strong>close</strong> (the final recorded market number) and <strong>fair</strong> (this repository's own
line for the same market). Every row names its book/tier and links the file it came from. Nothing is inferred:
a snapshot that no source provides is a blank.</div>

<h2>Coverage</h2>
{table(["Snapshot", "Markets", "Rows", "Span", "Source"], cov)}

<h2>Open &rarr; close movement, 2021 (the one season with both)</h2>
<p>The pinned dataset carries WSGT opening lines for the 272 games of the 2021 regular season and closing
lines for every season, so 2021 is the only season where open &rarr; close movement can be measured inside the
pinned sources. Movement is measured on the home-margin line (positive = home favoured).</p>
{table(["Metric", "Spread", "Total", "Source"],
  [["Games with both snapshots", f"{mv_s['n']}", f"{mv_t['n']}", link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/initial_lines.csv", "initial_lines.csv") + " + " + link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/games.csv", "games.csv")],
   ["Mean |close &minus; open| (pts)", str(mv_s['mean_abs']), str(mv_t['mean_abs']), link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/snapshots.csv", "snapshots.csv")],
   ["Median |close &minus; open| (pts)", str(mv_s['median_abs']), str(mv_t['median_abs']), link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/snapshots.csv", "snapshots.csv")],
   ["Moved off the open", str(mv_s['moved_off_open']), str(mv_t['moved_off_open']), link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/snapshots.csv", "snapshots.csv")],
   ["Moved 3 pts or more", str(mv_s['moved_3pt_or_more']), str(mv_t['moved_3pt_or_more']), link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/snapshots.csv", "snapshots.csv")],
   ["Largest |move| (pts)", str(mv_s['max_abs']), str(mv_t['max_abs']), link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/snapshots.csv", "snapshots.csv")],
   ["Mean signed move (pts)", str(mv_s['mean_signed']), str(mv_t['mean_signed']), link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/snapshots.csv", "snapshots.csv")]],
  note="Recomputed from the pinned files. No official archive of 2021 opening/closing lines is reachable from this "
       "sandbox, so these movements could not be confirmed against an operator source &mdash; flagged as G02.")}

<div class="warnbox"><strong>Caution (flagged G02).</strong> Several 2021 open&rarr;close movements exceed any
plausible market range, e.g. {e(movers[0][0])} opened {e(movers[0][1])} and is recorded closing at
{e(movers[0][2])} ({e(movers[0][3])}-point move). Either the WSGT series is not a true opening line for every row
or the recorded closes contain errors. The store publishes both numbers as recorded; it does not correct them,
because no official source reachable from this environment can adjudicate. See <a href="flagged.html">Flagged</a>.</div>

<h2>Fair line, market line, difference &mdash; separate columns (requirement R4)</h2>
<p>For the {len(rows)} originated 2026 fixtures that also carry a posted market line (captured as of 2026-10-30),
the ledger publishes the model's fair line, the market line and the difference as three separate columns for each
market. The remaining {summary['origination_ledger']['upcoming_rows'] - len(rows)} originated fixtures have no
posted market line, so the market and difference columns are blanks there.</p>
{table(["Game", "When", "Fair spread", "Market spread", "Diff (pts)", "Fair total", "Market total", "Diff (pts)", "Fair ML home (derived)", "Market ML home", "Source"], rows,
  note="Sign convention: NEGATIVE spread = home favoured (the repository's pipeline convention; games.csv "
       "spread_line is the negation of it). Fair ML is derived, not independently modelled &mdash; see "
       "<a href='origination-order.html'>Origination order</a>.")}

<h2>Schema</h2>
{table(["Column", "Meaning", "Source"], [
  ["game_id, season, week, gameday, away_team, home_team", "the game (game_id equals the pinned file's id; for 2021 it is the alt format)", link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/games.csv", "games.csv")],
  ["market", "SPREAD &middot; TOTAL &middot; MONEYLINE", link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/snapshots.csv", "snapshots.csv")],
  ["side", "HOME-MARGIN-LINE / BOTH-SIDES for market rows; the named team for ML; MODEL-FAIR for our lines", link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/snapshots.csv", "snapshots.csv")],
  ["snapshot", "open &middot; close &middot; fair", link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/snapshots.csv", "snapshots.csv")],
  ["line", "the number: spread points (home-margin, positive = home favoured) or total points; fair-ML rows carry the win probability", link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/snapshots.csv", "snapshots.csv")],
  ["odds", "American price where the source provides one (moneyline closes); blank otherwise", link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/games.csv", "games.csv")],
  ["book", "what recorded it (WSGT as recorded upstream; 'closing line as recorded by the dataset'; this repository's model)", link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/initial_lines.csv", "initial_lines.csv")],
  ["tier + source_url", "dataset | official | recomputed + the exact file or page behind the row", link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/snapshots.csv", "snapshots.csv")],
], note="Full file: " + f"{N_SNAP:,} rows in <code>price_lab/data/snapshots.csv</code>.")}
"""
    return shell("snapshots.html", "Price-snapshot store", "Price-snapshot store",
                 "Opening and closing numbers for every market this repository originates, with the model's fair line alongside. Built from the pinned dataset; values no source provides are blanks.", body)


def top_movers():
    import csv as _csv
    initial = list(_csv.DictReader((HERE.parent / "data" / "raw" / "initial_lines.csv").open()))
    games_by_id = {g["game_id"]: g for g in _csv.DictReader((HERE.parent / "data" / "raw" / "games.csv").open())}
    sides: dict[str, dict[str, float]] = {}
    for r in initial:
        sides.setdefault(r["about"], {})[f"{r['type']}|{r['side']}"] = float(r["line"])
    out = []
    for about, s in sides.items():
        g = games_by_id.get(about)
        if not g or not g["spread_line"]:
            continue
        home = about.split("_")[3]
        open_home = -s[f"SPREAD|{home}"]
        close_home = float(g["spread_line"])
        out.append((about, f"{open_home:+.1f}", f"{close_home:+.1f}", f"{close_home - open_home:+.1f}",
                    abs(close_home - open_home)))
    out.sort(key=lambda t: -t[4])
    return out[:5]


# --------------------------------------------------------------------------- #
# page: results
# --------------------------------------------------------------------------- #
def page_results() -> str:
    s = summary["results_feed"]
    hist_ml = sum(1 for r in csv.DictReader(HIST.open()) if r["market_close_ml_home"].strip())
    rows = []
    pin_missing_rows = []
    for r in feed26:
        status = r["match_status"]
        sp = pill("ok", "match") if status == "match" else pill("warn", "not in pin")
        row = [
            e(r["week"]), e(f"{r['away_team']} @ {r['home_team']}"),
            e(f"{r['away_score']}&ndash;{r['home_score']}"), e(r["total"]), e(r["home_margin"]),
            ("yes" if r["in_pinned_feed"] == "yes" else blank("game finished after the 2026-11-01 pin")),
            sp, link(r["source_url"], "NFL.com week"),
            link(r["game_url"], "game page"),
        ]
        rows.append(row)
        if r["in_pinned_feed"] != "yes":
            pin_missing_rows.append(row)
    missing_only = [r for r in feed26 if r["in_pinned_feed"] != "yes"]

    body = f"""
<h2>What this feed is</h2>
<div class="note">The results side of the store: every completed game with its score, total and home margin, each
row linked to the source that states it. Two layers: (1) the <strong>history feed</strong> recomputed from the pinned
dataset &mdash; {N_HIST:,} completed rows, {summary['results_feed']['history_seasons'][0]}–{summary['results_feed']['history_seasons'][1]}, the input every backtest and ROI
number in this repository should read; and (2) the <strong>official cross-check</strong> &mdash; all
{s['official_finals_checked']} 2026 finals transcribed from the official NFL schedule pages opened {CHECKED} and
compared against the pinned feed row by row.</div>

<h2>2026 cross-check: every officially completed game, {s['official_finals_checked']} rows</h2>
{table(["Wk", "Game", "Score (away&ndash;home)", "Total", "Home margin", "In pinned feed", "Status", "Source (week page)", "Source (game page)"], rows,
  note=f"{s['official_match_pinned']} of {s['official_finals_checked']} finals are in the pinned feed and every one "
       f"matches it exactly ({pill('ok', '108/108 match')}). The other {s['official_missing_from_pin']} finished after "
       "the 2026-11-01 pin was taken (flagged G04). Week 5 includes the season's only tie: NYG 27 &ndash; 27 WAS.")}

<h2>Gap: the pin is stale by {s['official_missing_from_pin']} finals</h2>
<p>The pinned dataset was cut 2026-11-01 and ends with Week 8's Thursday game. These officially final games are in
the official cross-check above but <em>not</em> in the pinned feed:</p>
{table(["Wk", "Game", "Score", "Status", "Source"], [[r[0], r[1], r[2], r[6], r[7] + " &middot; " + r[8]] for r in pin_missing_rows],
  note="Advancing the pin is a one-line change to <code>scripts/fetch_data.sh</code> plus a re-run; it is logged as a "
       "suggestion rather than done here, because changing the shared pin re-bases every prior session's numbers. "
       "See <a href='suggestions.html'>S-G05</a>.")}

<h2>History feed</h2>
{table(["What", "Rows", "Span", "Source"],
 [["Completed games with scores, totals, margins and closing lines", f"{N_HIST:,}", f"{summary['results_feed']['history_seasons'][0]}–{summary['results_feed']['history_seasons'][1]}", link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/games.csv", "games.csv")],
  ["Of which with closing moneyline prices", f"{hist_ml:,}", "2006 onward (some early-2006 gaps)", link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/games.csv", "games.csv")],
  ["Per-side closing prices with odds (spread, total, ML)", "20,490", "2006–2018", link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/closing_lines.csv", "closing_lines.csv")],
  ["Opening lines (WSGT)", "1,088", "2021", link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/initial_lines.csv", "initial_lines.csv")]],
  note="Full file: <code>price_lab/data/results_history.csv</code>. Backtests should read this feed so that ROI is "
       "computable at all, and every ROI number should name the window it used.")}
"""
    return shell("results.html", "Verified results feed", "Verified results feed",
                 f"Every completed 2026 game cross-checked against the official NFL pages ({CHECKED}), plus the history feed backtests run on.", body)


# --------------------------------------------------------------------------- #
# page: origination order
# --------------------------------------------------------------------------- #
def page_order() -> str:
    ol = summary["origination_ledger"]
    body = f"""
<h2>The order: side &rarr; total &rarr; moneyline</h2>
<div class="note">For every game this repository originates lines for, the <strong>side</strong> (spread) is
originated first, the <strong>total</strong> second, and the <strong>moneyline</strong> third. The order is not
cosmetic: the side and the total are the two quantities the model forecasts directly, and the moneyline is derived
from the side forecast — never the other way round. A moneyline opinion must never leak into the side or the total.</div>

<h2>How it is enforced</h2>
{table(["Check", "Rule", "Status"], [
 ["Column order", "the ledger's columns run fair_spread &rarr; market_close_spread &rarr; diff_spread &rarr; fair_total &rarr; &hellip; &rarr; fair_ml, mirroring the order", pill("ok", "enforced") + " " + link(REPO_CHECK_URL, "check.py")],
 ["Row completeness", "every ledger row carries order_side=1, order_total=2, order_moneyline=3", pill("ok", "enforced") + " " + link(REPO_CHECK_URL, "check.py")],
 ["No ML without side+total", "a row with a moneyline column populated must also have the side and total columns populated", pill("ok", "enforced") + " " + link(REPO_CHECK_URL, "check.py")],
 ["Fair ML is derived", f"P(home win) = &Phi;(&minus;fair_spread / {summary['sigma_spread_rmse']:.3f}) &mdash; &sigma; is the model's own measured spread RMSE (variant {summary['sigma_spread_rmse_variant']})", pill("info", "derived, flagged") + " " + link("https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/model_metrics.json", "metrics")],
], note="The &sigma; value and its provenance are published in <code>data/derived/model_metrics.json</code> "
        "(variant B: spread MAE 10.670, RMSE 13.618, n = 6,827).")}

<h2>Sign conventions (stated once, used everywhere)</h2>
{table(["Series", "Convention", "Conversion"], [
 ["pinned <code>games.csv spread_line</code>", "home-margin line: positive = home favoured; the home side covers when result &gt; spread_line", "verified: mean(result &minus; spread_line) &asymp; 0 on every pinned season, and the spread direction agrees with the moneyline direction on all 4,456 clear-favourite rows 2006–2026 &mdash; " + link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/games.csv", "games.csv")],
 ["repository pipeline (<code>model_predictions.csv</code>, <code>own_lines_upcoming.csv</code>)", "negated: NEGATIVE = home favoured", "mkt_spread = &minus;spread_line on every row (asserted at build time) &mdash; " + link("https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/model_predictions.csv", "model_predictions.csv")],
 ["WSGT initial lines", "side-specific: each row's line is what that side gives (negative) or receives (positive)", "home-margin opening line = &minus;(home side's row); the away row is its exact negation (asserted) &mdash; " + link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/initial_lines.csv", "initial_lines.csv")],
])}

<h2>Artifacts</h2>
{table(["Artifact", "Rows", "Contents", "Source"],
 [["<code>origination_ledger.csv</code>", f"{ol['rows']:,}", f"{ol['model_rows']:,} model-priced games (2000–2026) + {ol['upcoming_rows']} originated unplayed fixtures; fair / market / diff as separate columns per market; order columns 1-2-3", link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/origination_ledger.csv", "ledger")],
  ["<code>snapshots.csv</code>", f"{N_SNAP:,}", "the price-snapshot store: open, close and fair per market", link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/snapshots.csv", "snapshots.csv")],
  ["<code>model_metrics.json</code>", "—", "the measured model error the fair-ML derivation reads", link("https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/model_metrics.json", "metrics")]])}

<div class="warnbox"><strong>Honest limit.</strong> The fair moneyline is a deterministic derivation from the fair
spread under a normal-margin assumption &mdash; it is <em>not</em> an independently modelled moneyline. It is labelled
<em>derived</em> everywhere. Whether to build a dedicated moneyline model (e.g. a binomial on the margin
distribution's actual shape, which is heavier-tailed than normal) is open question Q-P04.</div>
"""
    return shell("origination-order.html", "Origination order", "Origination order: side, then total, then moneyline",
                 "The pipeline order the desk originates markets in, the sign conventions it uses, and the checks that enforce it.", body)


# --------------------------------------------------------------------------- #
# page: leaderboard
# --------------------------------------------------------------------------- #
def page_leaderboard() -> str:
    rows = []
    for r in lb:
        roi = float(r["signal_flat_roi"])
        sig = pill("ok", f"{roi * 100:+.2f}%") if roi > 0 else pill("bad", f"{roi * 100:+.2f}%")
        rows.append([
            e(r["strategy_id"]), e(r["strategy_name"]), e(r["markets"]), e(r["n_bets"]),
            e(f"{float(r['signal_hit_rate']) * 100:.2f}%"), e(f"{float(r['signal_mean_edge']) * 100:+.2f}%"),
            sig, e(f"{float(r['signal_flat_pnl_units']):+.1f}"), e(f"{float(r['signal_flat_max_drawdown_units']):+.1f}"),
            e(f"{float(r['staking_growth_multiple']):.4f}"),
            e(f"{float(r['staking_roi_per_bet_pct_of_bankroll']) * 100:+.4f}%"),
            e(f"{float(r['staking_max_drawdown_frac']) * 100:.1f}%"),
            link(r["source_url"], "bets.csv"),
        ])
    pos = ", ".join(summary["leaderboard"]["positive_flat_roi"]) or "none"
    body = f"""
<h2>Two axes, deliberately separated</h2>
<div class="note">A staking plan can turn a negative-edge signal into a positive ledger (and a lucky staking run can
hide a bad signal). This leaderboard therefore reports <strong>signal</strong> and <strong>staking</strong> as two
independent axes with different columns and different gates:
<ul>
<li><strong>Signal axis</strong> &mdash; what the strategy knows: bets, hit rate, mean edge, and ROI at a flat 1 unit
per bet. <strong>Reward eligibility is decided on this axis only.</strong></li>
<li><strong>Staking axis</strong> &mdash; what a bankroll plan would have done on the same bets, as a documented
variant: fractional Kelly capped at {int(summary['leaderboard']['kelly_cap'] * 100)}% of bankroll per bet. It is reported for
transparency and can never promote a strategy.</li>
</ul></div>

<h2>The eleven strategies of the line_lab ledger (S1–S11)</h2>
{table(["ID", "Strategy", "Markets", "Bets", "Hit rate", "Mean edge", "Signal ROI (flat)", "Flat P&amp;L (units)", "Flat max DD (units)", "Staking: growth multiple", "Staking: ROI per bet (% bankroll)", "Staking: max DD (% bankroll)", "Source"], rows,
  note="Recomputed from <code>data/derived/bets.csv</code> (16,439 settled bets at recorded closing prices). "
       "Flat = 1 unit per bet regardless of price. Kelly variant: f = clamp((p·b &minus; (1&minus;p))/b, 0, 2%), "
       "b = decimal odds &minus; 1, p = the strategy's recorded model probability.")}

<h2>Reading it</h2>
{table(["Question", "Answer"], [
 ["Which strategies have a positive signal ROI?", f"{pos} &mdash; and positive flat ROI alone earns nothing: the reward gates (significance, multiplicity, sample size, drawdown) are defined on the canonical competition page and none of the eleven passes them.", ilink("../hub/competition.html", "Competition, rewards &amp; luck")],
 ["Could staking have rescued a bad signal?", "Look across the two axes: a positive staking growth multiple with a negative flat ROI is exactly the 'lucky staking run' the separation exists to expose; none of the eleven shows a big divergence in either direction, which is itself the finding.", link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/leaderboard_signal_staking.csv", "leaderboard.csv")],
 ["Which ledger does this read?", "The line_lab ledger S1–S11. The pipeline's separate S01–S18 ledger shares ID styling with different meanings &mdash; flagged repo-wide as X01; do not score one rule from the other ledger.", ilink("../hub/flagged.html", "Flagged (X01)")],
 ["Where is the canonical leaderboard?", "This page implements the signal/staking separation as a proposal; the canonical fail-closed leaderboard stays on the hub until the owner adopts the split.", ilink("../hub/leaderboard.html", "Hub leaderboard")],
])}
"""
    return shell("leaderboard.html", "Leaderboard: signal vs staking", "Leaderboard — signal separated from staking",
                 "Reward eligibility is decided on the signal axis (flat-unit ROI, edge, hit rate); staking is reported separately and can never promote a strategy.", body)


# --------------------------------------------------------------------------- #
# page: demotion
# --------------------------------------------------------------------------- #
def page_demotion() -> str:
    body = f"""
<h2>The demotion gate</h2>
<div class="note">Promotion gates send a paper strategy live; the demotion gate is the way back. It is defined
<em>before</em> anything is live, so that demotion is mechanical rather than negotiable.
<strong>Status: {pill('warn', 'proposed spec — nothing is live, so nothing is demoted')}</strong> — the owner
still has to adopt it alongside the promotion gates on the <a href="../hub/competition.html">competition page</a>.</div>

<h2>Automatic demotion triggers (any one, measured on the live ledger only)</h2>
{table(["#", "Trigger", "Measurement", "Window", "Why it is here", "Measurement source"], [
 ["D1", "Rolling ROI below &minus;5%", "ROI on the last 50 settled live bets at recorded closing prices", "last 50 bets", "a live strategy losing at this rate has no demonstrated edge", ilink("results.html", "results feed")],
 ["D2", "Mean closing-line value below zero", "mean CLV over the last 50 live bets, n &ge; 50", "last 50 bets", "negative CLV means the market is beating the strategy even when results flatter it", ilink("snapshots.html", "close snapshots")],
 ["D3", "Drawdown breach", "peak-to-trough bankroll drawdown &gt; 20 units or 35% of peak", "since promotion", "survival constraint independent of edge", ilink("leaderboard.html", "ledger")],
 ["D4", "Two consecutive losing windows", "two consecutive 25-bet windows each with ROI &le; &minus;10%", "last 50 bets", "rules out one bad-luck window doing the demotion alone", ilink("leaderboard.html", "ledger")],
 ["D5", "Feed integrity failure", "the verified results feed is missing or late for 2 consecutive weeks", "weekly", "a strategy whose results cannot be settled cannot stay live (this desk's feed is the settlement source)", ilink("results.html", "results feed")],
 ["D6", "Signal decay vs the market", "the model's own-line error exceeds the market's by &gt; 1 point over the last 100 originated games", "last 100 games", "the repo measured own 10.670 vs market 10.247 MAE over 2006–2025 — the gate catches that gap widening on a live book", link("https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/model_metrics.json", "model_metrics.json")],
])}

<h2>Rules that make it bite</h2>
{table(["Rule", "Statement", "Where it lives"], [
 ["Mechanical, not discretionary", "any trigger that fires demotes the strategy to paper the same day; no appeal mid-window", ilink("demotion.html", "this page")],
 ["Window restart", "a demoted strategy re-enters paper with its promotion-gate counters reset; it must re-clear every promotion gate to return", ilink("../hub/competition.html", "promotion gates")],
 ["Staking cannot save it", "demotion is evaluated on the signal axis only; a profitable staking overlay is not a defence", ilink("leaderboard.html", "signal vs staking")],
 ["Public record", "every demotion, its trigger, window and numbers are published on the leaderboard page with the settlement rows linked", ilink("results.html", "results feed")],
 ["Nothing to demote today", "zero strategies are live (" + pill("info", "0 live") + "), so the gate's current state is armed but unexercised", ilink("../hub/competition.html", "competition page")],
])}

<h2>Where its inputs come from</h2>
{table(["Input", "Source"], [
 ["Settled live bets and prices", ilink("results.html", "the verified results feed") + " + " + ilink("snapshots.html", "the price-snapshot store's close snapshots")],
 ["CLV", "close snapshot minus the price the bet was taken at, both from " + ilink("snapshots.html", "the store")],
 ["Own-line vs market error", "the origination ledger's diff columns recomputed on the rolling window — " + ilink("origination-order.html", "the order page")],
], note="Demotion thresholds are policy choices, stated here as numbers so they can be argued with and changed "
        "once, before launch, rather than improvised after it.")}
"""
    return shell("demotion.html", "Demotion gate", "Demotion gate: sending a live strategy back to paper",
                 "Six automatic triggers, measured on the live ledger, defined before anything goes live.", body)


# --------------------------------------------------------------------------- #
# page: suggestions
# --------------------------------------------------------------------------- #
def page_suggestions() -> str:
    sugg = [
        ("S-G01", "Unify the two strategy-ID ledgers", "high",
         "data/derived/bets.csv (S1–S11) and data/derived/gates_results.csv (S01–S18) reuse ID styling with different meanings (repo flag X01). Any leaderboard or reward rule that reads the wrong ledger scores the wrong strategy.",
         "Namespace the IDs (LL-S1&hellip; / PL-S01&hellip;) or merge into one registry with a source column.",
         "Owner decision &mdash; needs review"),
        ("S-G02", "Adopt the snapshot store as the settlement source", "high",
         "Backtests elsewhere in the repo read their own extracts; ROI windows are not named consistently.",
         "Point every ROI computation at price_lab/data/results_history.csv and require the window to be named in the output.",
         "Owner decision"),
        ("S-G03", "Adopt the signal/staking leaderboard split", "high",
         "The canonical hub leaderboard reports flat results only; a staking overlay could later mask a bad signal.",
         "Promote this desk's two-axis table to the canonical leaderboard.",
         "Owner decision"),
        ("S-G04", "Adopt the demotion gate", "high",
         "The promotion gates have no counterpart; without one, a strategy that decays after promotion has no mechanical way off the board.",
         "Add the six triggers on the demotion page to the competition page's gate table.",
         "Owner decision"),
        ("S-G05", "Advance the pinned dataset to a post-Week-9 commit", "high",
         "The pin (2026-11-01) is missing 29 officially final games; every 2026 number predates Week 8 Sunday.",
         "Re-pin scripts/fetch_data.sh, re-run the dataset build, and let the CI fail-closed checks re-verify. Re-bases prior numbers, so it needs an explicit go-ahead.",
         "Owner decision &mdash; changes shared numbers"),
        ("S-G06", "Record capture times for opening lines", "medium",
         "CLV is only computable against a timestamped open; the WSGT series has no timestamps.",
         "When capturing opens in future, store the capture UTC time with the row; require it in the schema.",
         "Feeds Q-P02"),
        ("S-G07", "Add movement alerts to the snapshot store", "medium",
         "The store measures movement but nothing watches it.",
         "A weekly CI step that flags any close 3+ points off the recorded open into the flagged page.",
         "Low-cost improvement"),
        ("S-G08", "Publish a decision-impact column on headline tables", "medium",
         "Tables show values; they do not say what would change if the value were wrong.",
         "For each headline number, one column: the decision it feeds and the effect of being wrong by its own error bar.",
         "Decision-support improvement"),
        ("S-G09", "Join depth-replacement states into the line model", "medium",
         "The depth lab tracks starter replacements by string depth; the line model does not consume it.",
         "Add a replacement-depth feature to the model's next refit and re-run the gates.",
         "Feeds Q-P06"),
        ("S-G10", "Blank-cell taxonomy on the flagged page", "low",
         "Blanks are flagged but not classified; reviewers cannot tell data-missing from source-refuses-to-publish.",
         "Label every blank: NOT_PUBLISHED / NOT_YET_PLAYED / SOURCE_UNREACHABLE.",
          "Review-quality improvement"),
    ]
    sugg_link = {
        "S-G01": ilink("../hub/flagged.html", "flag X01"),
        "S-G02": ilink("results.html", "results feed"),
        "S-G03": ilink("leaderboard.html", "this desk's leaderboard"),
        "S-G04": ilink("demotion.html", "demotion gate"),
        "S-G05": link("https://github.com/karagemop466-tech/Korea3/blob/main/scripts/fetch_data.sh", "fetch_data.sh"),
        "S-G06": ilink("flagged.html", "G01"),
        "S-G07": ilink("snapshots.html", "snapshot store"),
        "S-G08": ilink("executive-summary.html", "executive summary"),
        "S-G09": ilink("../depth_lab/index.html", "Depth Lab"),
        "S-G10": ilink("flagged.html", "flagged page"),
    }
    rows = [[e(i), e(t), pill("warn" if pr == "high" else "info", pr), e(p),
             e(a), pill("info", st) + " " + sugg_link[i]] for i, t, pr, p, a, st in sugg]
    body = f"""
<h2>Proposals &mdash; nothing here is implemented</h2>
<div class="note">This desk's suggestions for improving the site's decision-making. Every row is a
<strong>proposal with a decision path</strong>; nothing changes until a path is chosen. The canonical,
repository-wide suggestions board remains <a href="../hub/suggestions.html">hub/suggestions.html</a>; the rows here
are additional and scoped to this desk.</div>
{table(["ID", "Suggestion", "Priority", "Problem", "Proposed path", "Status"], rows)}
<h2>How a suggestion should be handled</h2>
{table(["Step", "What happens", "Where it is recorded"], [
 ["1. Review", "the owner (or a delegated reviewer) reads the proposal and its evidence; the reviewer may reject it without implementation", ilink("../hub/suggestions.html", "canonical suggestions board")],
 ["2. Choose a path", "adopt / adopt with changes / reject / park with a re-review date &mdash; recorded against the ID", link(REPO_COORD_URL, "COORDINATION.md")],
 ["3. Only then implement", "the implementing session claims the change on COORDINATION.md, implements, and the fail-closed checks re-verify", link(REPO_CHECK_URL, "price_lab/check.py")],
])}
"""
    return shell("suggestions.html", "Suggestions", "Suggestions — review before anything changes",
                 "Ten proposals to improve decision-making on the site, each with a decision path. None is implemented.", body)


# --------------------------------------------------------------------------- #
# page: open questions
# --------------------------------------------------------------------------- #
def page_questions() -> str:
    qs = [
        ("Q-P01", "What is 'WSGT', the recorded source of the 2021 opening lines?",
         "The pinned initial_lines.csv labels every 2021 open row WSGT; 272 games, no timestamps, no odds.",
         "The upstream dataset does not document the abbreviation and no official archive reachable from this sandbox names it.",
         "Ask the nflverse maintainers (GitHub issue on nflverse/nfldata) or find the operator's own archive.",
         "Whether the 2021 open series is a true opening line (G01/G02 hinge on it)"),
        ("Q-P02", "Can official opening/closing numbers be obtained at all?",
         "This desk has closing lines for 1999–2026 and opens for 2021 from the pinned dataset.",
         "No official operator archive of historical open/close pairs was reachable; operator pages checked in prior sessions are live-odds only.",
         "Operator archive pages or a licensed data feed; alternatively ask operators what they permit.",
         "Whether CLV (demotion gate D2) can ever be computed from official sources"),
        ("Q-P03", "Is a derived fair moneyline acceptable for origination?",
         "The desk derives P(home win) from the fair spread with the model's measured RMSE, labelled derived on every row.",
         "Whether the owner wants a dedicated moneyline model before any ML strategy is scored.",
         "Owner decision; a dedicated model would be validated by the same eight gates.",
         "Whether moneyline markets can be originated at all under R3"),
        ("Q-P04", "When should the dataset pin be advanced?",
         "The pin is 2026-11-01; 29 officially final games are missing (G04).",
         "The re-pin re-bases every prior session's published numbers.",
         "Owner decision, ideally in the week after the season ends; a standing weekly re-pin is the alternative.",
         "S-G05; the freshness of every 2026 number"),
        ("Q-P05", "Are club-published depth charts 'official'?",
         "Carried from prior sessions: the repo-wide source allow-list classifies club sites as dataset, not official, while the depth lab publishes their content with that disclosure.",
         "An owner ruling is required; both positions are published with sources.",
         "Owner decision recorded on the flagged page.",
         "Q15/S13 on the canonical board; the depth-of-replacement requirement R6"),
        ("Q-P06", "What is the reward pool, and is it funded?",
         "The competition page publishes the gate structure with the reward amounts blank.",
         "No sponsor, jurisdiction or payout terms exist in any official source.",
         "Owner decision; until then the leaderboard stays fail-closed with zero reward-eligible strategies.",
         "Whether the leaderboard competition can pay anyone (N06)"),
        ("Q-P07", "Which staking variant, if any, is in scope?",
         "The desk reports a 2%-capped fractional-Kelly overlay as a documented variant on the staking axis only.",
         "Whether the owner wants flat-only reporting, or a staking axis at all.",
         "Owner decision; the separation rule (staking never promotes) holds either way.",
         "S-G03"),
        ("Q-P08", "What n does a demotion trigger need before it is trusted?",
         "D1/D2/D4 use 25–50-bet windows; with the observed bet rates (11 strategies, 16,439 bets over 20 seasons) a live strategy may take weeks to fill a window.",
         "Whether shorter windows with wider thresholds, or longer windows, better trade speed against noise.",
         "Compute trigger operating characteristics on the existing ledger before launch.",
         "D1–D4 thresholds"),
    ]
    disc_links = {
        "Q-P01": link("https://github.com/nflverse/nfldata", "nflverse/nfldata"),
        "Q-P02": link("https://www.nfl.com/schedules/2026/by-week/week-10", "live official pages"),
        "Q-P03": link("https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/model_metrics.json", "model_metrics.json"),
        "Q-P04": link(f"https://github.com/nflverse/nfldata/commits/master/data/games.csv", "upstream commit history"),
        "Q-P05": ilink("../hub/flagged.html", "hub flagged page"),
        "Q-P06": ilink("../hub/competition.html", "competition page"),
        "Q-P07": ilink("leaderboard.html", "this desk's leaderboard"),
        "Q-P08": link("https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/bets.csv", "bets.csv"),
    }
    rows = [[e(q), f"<strong>{e(qt)}</strong>", e(held), e(missing), e(disc) + " " + disc_links[q], e(blocks)]
            for q, qt, held, missing, disc, blocks in qs]
    body = f"""
<h2>Open questions &mdash; what we have, what we lack, how to find out</h2>
<div class="note">The decisions this desk touches cannot be taken responsibly until these are answered. For each
question: the information <strong>held</strong> in this repository, the information <strong>missing</strong>, the
<strong>way to discover</strong> it, and the decision it blocks. The canonical register is
<a href="../hub/questions.html">hub/questions.html</a>; these are this desk's additions.</div>
{table(["ID", "Question", "Information held", "Information missing", "How to discover it", "Decision it blocks"], rows)}
"""
    return shell("open-questions.html", "Open questions", "Open questions before decisions",
                 "What is held, what is missing, how to discover the missing, and which decision each question blocks.", body)


# --------------------------------------------------------------------------- #
# page: flagged
# --------------------------------------------------------------------------- #
def page_flagged() -> str:
    flags = [
        ("G01", "high", "The 2021 opening-line source is recorded only as 'WSGT'",
         "The pinned initial_lines.csv labels its book 'WSGT'; the upstream dataset does not expand the abbreviation, and no official archive reachable here names it. Published as recorded, never interpreted.",
         "unverified — flagged", link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/initial_lines.csv", "initial_lines.csv")),
        ("G02", "high", "2021 open→close movements could not be confirmed and include implausible values",
         "Mean |move| 3.40 pts (spread) with a maximum of 15.0 (e.g. 2021_15_GB_BAL opens home BAL −5.5, recorded close away GB −9.5). No official archive is reachable to adjudicate; both numbers are published as recorded and left uncorrected.",
         "unverified — flagged", link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/games.csv", "games.csv")),
        ("G03", "medium", "The per-side closing file (with odds) ends at 2018",
         "data/raw/closing_lines.csv covers 2006–2018 with per-side odds; from 2019 the only closes are the summary columns in games.csv, so closing odds for spread/total are blank from 2019 onward.",
         "dataset limitation — published with blanks", link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/closing_lines.csv", "closing_lines.csv")),
        ("G04", "high", "The pinned feed is missing 29 officially final 2026 games",
         "The pin was cut 2026-11-01 and ends with Week 8's Thursday game. Weeks 8 (13 more), 9 (15) and 10 (1) are officially final per NFL.com (checked 2026-11-14) and are published on the results page with official links, but are absent from the pinned feed that backtests read.",
         "official vs pinned gap — both published", link("https://www.nfl.com/schedules/2026/by-week/week-9", "NFL.com week 9")),
        ("G05", "medium", "No official opening moneyline exists in any reachable source",
         "Open snapshots exist for spread/total (2021 only); opening moneylines are blanks in the store because no source provides them.",
         "blank — not published by any reachable source", link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/initial_lines.csv", "initial_lines.csv")),
        ("G06", "medium", "The fair moneyline is derived, not independently modelled",
         "Fair ML = Φ(−fair_spread / 13.618) with σ = the model's measured spread RMSE (variant B). A normal margin assumption understates tail probabilities; it is labelled derived on every row and should not be scored as a model output.",
         "derived — labelled", link("https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/model_metrics.json", "model_metrics.json")),
        ("G07", "medium", "X01 (carried): two ledgers share strategy-ID styling with different meanings",
         "bets.csv (S1–S11) and gates_results.csv (S01–S18). This desk's leaderboard reads bets.csv only and says so on the page.",
         "carried from hub flag X01", ilink("../hub/flagged.html", "hub flagged page")),
        ("G08", "low", "The 28 originated fixtures with posted market lines were captured as of 2026-10-30",
         "The market lines on upcoming fixtures are as-of the own-lines build date, not refreshed this session; 42 of the 164 originated fixtures are now in weeks 8–10 and several have played.",
         "staleness — dated on the page", link("https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/own_lines_meta.json", "own_lines_meta.json")),
        ("G09", "low", "Early-2006 and some 2008–2009 closing moneylines are absent",
         "games.csv moneyline coverage is partial for 2006 and 2008–2009 (e.g. 220 of 267 games in 2006); the store leaves those cells blank.",
         "blank — not in source", link(f"https://github.com/nflverse/nfldata/blob/{PIN}/data/games.csv", "games.csv")),
        ("G10", "low", "Week 1 of 2026 began on a Wednesday (Sep 9)",
         "The official week-1 page shows the opener on Wednesday, September 9th. Recorded as-is; any rest-day feature must not assume a standard Thursday opener.",
         "verified oddity", link("https://www.nfl.com/schedules/2026/by-week/week-1", "NFL.com week 1")),
    ]
    rows = [[e(i), pill("bad" if pr == "high" else ("warn" if pr == "medium" else "info"), pr), e(t), e(d), st, src]
            for i, pr, t, d, st, src in flags]
    body = f"""
<h2>Flagged for review</h2>
<div class="note">Nothing on this page blocks publication; these are the items a reviewer should look at first.
The repository-wide flagged page is <a href="../hub/flagged.html">hub/flagged.html</a>.</div>
{table(["ID", "Severity", "Irregularity", "Detail", "Status", "Source"], rows)}
"""
    return shell("flagged.html", "Flagged for review", "Flagged for review",
                 "Irregularities found while building the store and feed, each with its source and status. None blocks publication.", body)


# --------------------------------------------------------------------------- #
# page: sources
# --------------------------------------------------------------------------- #
def page_sources() -> str:
    srcs = [
        ("nflverse/nfldata @ " + PIN[:7], "games.csv — scores, closing lines, schedule (7,548 rows)", "dataset (pinned, checksummed)", "—", f"https://github.com/nflverse/nfldata/blob/{PIN}/data/games.csv"),
        ("nflverse/nfldata @ " + PIN[:7], "initial_lines.csv — 2021 WSGT opening lines (1,088 rows)", "dataset (pinned, checksummed)", "—", f"https://github.com/nflverse/nfldata/blob/{PIN}/data/initial_lines.csv"),
        ("nflverse/nfldata @ " + PIN[:7], "closing_lines.csv — per-side closes with odds, 2006–2018 (20,490 rows)", "dataset (pinned, checksummed)", "—", f"https://github.com/nflverse/nfldata/blob/{PIN}/data/closing_lines.csv"),
        ("NFL.com schedule pages", "2026 weeks 1–10 by-week pages — all 137 finals transcribed", "official", CHECKED, "https://www.nfl.com/schedules/2026/by-week/week-1"),
        ("this repository", "data/derived/model_predictions.csv — model fair lines 2000–2026", "recomputed (repo)", "—", "https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/model_predictions.csv"),
        ("this repository", "data/derived/own_lines_upcoming.csv — originated lines for unplayed fixtures", "recomputed (repo)", "—", "https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/own_lines_upcoming.csv"),
        ("this repository", "data/derived/model_metrics.json — measured model error (variant B)", "recomputed (repo)", "—", "https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/model_metrics.json"),
        ("this repository", "data/derived/bets.csv — line_lab 11-strategy ledger", "recomputed (repo)", "—", "https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/bets.csv"),
        ("canonical boards", "hub/suggestions.html · hub/questions.html · hub/competition.html · hub/leaderboard.html", "other sessions' canonical pages", "—", "https://karagemop466-tech.github.io/Korea3/hub/suggestions.html"),
    ]
    rows = [[e(a), e(b), pill("ok" if c == "official" else "info", c), e(d), link(u)] for a, b, c, d, u in srcs]
    body = f"""
<h2>Sources used by this desk</h2>
{table(["Source", "What it provided", "Tier", "Opened / checked (UTC)", "Link"], rows)}
<h2>Verification performed</h2>
{table(["Check", "Result", "Where"], [
 ["Pinned files vs manifest checksums", "games.csv, initial_lines.csv, closing_lines.csv, teams.csv, win_totals.csv all match data/raw/MANIFEST.json (sc_lines.csv is not listed in the manifest — noted)", link("https://github.com/karagemop466-tech/Korea3/blob/main/data/raw/MANIFEST.json", "MANIFEST.json")],
 ["Official transcription vs pinned feed", "108 of 108 officially final games present in the pin match exactly; the check fails the build on any disagreement", link(REPO_CHECK_URL, "check.py")],
 ["Difference-column arithmetic", "diff = fair &minus; market re-derived for every populated row of the origination ledger", link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/origination_ledger.csv", "origination_ledger.csv")],
 ["Fair-ML derivation", "&Phi; derivation recomputed for every ledger row against the recorded &sigma;", link(REPO_CHECK_URL, "check.py")],
 ["Movement arithmetic", "close &minus; open re-derived for every 2021 open/close pair", link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/snapshots.csv", "snapshots.csv")],
 ["Leaderboard arithmetic", "flat ROI, hit rate and the Kelly overlay recomputed from bets.csv for all 11 strategies", link("https://github.com/karagemop466-tech/Korea3/blob/main/price_lab/data/leaderboard_signal_staking.csv", "leaderboard_signal_staking.csv")],
 ["Row sourcing", "every table row on every page of this desk carries at least one link; rows without a source would fail check.py", link(REPO_CHECK_URL, "check.py")],
])}
"""
    return shell("sources.html", "Sources", "Sources and verification",
                 "Every source this desk reads, its tier, when it was opened, and the checks performed against it.", body)


# --------------------------------------------------------------------------- #
# page: executive summary
# --------------------------------------------------------------------------- #
def page_exec() -> str:
    s, ol, rf, lbs = summary["snapshots"], summary["origination_ledger"], summary["results_feed"], summary["leaderboard"]
    body = f"""
<h2>What this session built</h2>
<div class="note">The <strong>Snapshot Desk</strong> closes the loop the brief asked for: originate
<strong>side &rarr; total &rarr; moneyline</strong>, store the <strong>market's open and close</strong> next to the
<strong>model's fair line</strong>, settle everything against a <strong>verified results feed</strong>, and score
strategies on a leaderboard where <strong>signal and staking are separated</strong> &mdash; with a
<strong>demotion gate</strong> defined before anything goes live. Every value is sourced or blank.</div>

<h2>Headline facts (all recomputed from the committed data by check.py)</h2>
<div class="grid k4">
  <div class="card"><div class="tag">Snapshot rows</div><div class="num">{s['rows_total']:,}</div>
    <div class="sub">{s['open_rows']:,} open &middot; {s['close_rows']:,} close &middot; {s['fair_rows']:,} fair</div></div>
  <div class="card"><div class="tag">Games with open + close</div><div class="num">{s['games_with_open_and_close']}</div>
    <div class="sub">the 2021 regular season &mdash; the only season the pinned sources give both</div></div>
  <div class="card"><div class="tag">Official 2026 finals checked</div><div class="num">{rf['official_finals_checked']}</div>
    <div class="sub">{rf['official_match_pinned']} match the pinned feed exactly; {rf['official_missing_from_pin']} finished after the pin</div></div>
  <div class="card"><div class="tag">Reward-eligible strategies</div><div class="num">0</div>
    <div class="sub">signal gates unchanged; {lbs['strategies']} strategies scored on two separated axes</div></div>
</div>

<h2>Requirement coverage</h2>
{table(["Requirement", "Status", "Where", "Evidence"], [
 ["R1 Price-snapshot store (open + close per originated market)", pill("ok", "delivered"), ilink("snapshots.html", "Snapshots"), f"{s['rows_total']:,} rows; opens 2021-only (flagged G01/G02)"],
 ["R2 Verified results feed", pill("ok", "delivered"), ilink("results.html", "Results"), f"{rf['official_finals_checked']} official finals cross-checked {CHECKED}; {N_HIST:,}-row history feed"],
 ["R3 Originate side first, then total, then moneyline", pill("ok", "enforced"), ilink("origination-order.html", "Order"), "order columns + check.py completeness rules"],
 ["R4 Fair line / market line / difference as separate columns", pill("ok", "delivered"), ilink("snapshots.html", "Snapshots"), "ledger columns; populated where a market line exists (28 fixtures), blanks elsewhere"],
 ["R5 Signal separated from staking on the leaderboard", pill("ok", "delivered"), ilink("leaderboard.html", "Leaderboard"), "two axes; staking can never promote; canonical page untouched"],
 ["R6 Track the depth of replacement, not just the fact", pill("ok", "already delivered by the Depth Lab"), ilink("../depth_lab/index.html", "Depth Lab"), "43 replacement rows with the string depth of each replacement"],
 ["R7 Correlations from official numbers with n published", pill("ok", "already delivered on the hub"), ilink("../hub/correlations.html", "Correlations"), "φ with 95% CI and n on every row; X02 labelling caveat recorded"],
 ["R8 Demotion gate back to paper", pill("ok", "defined (proposed)"), ilink("demotion.html", "Demotion"), "6 automatic triggers; nothing is live so nothing is demoted"],
 ["Suggestions section for review before changes", pill("ok", "delivered"), ilink("suggestions.html", "Suggestions"), "10 proposals + the canonical hub board"],
 ["Questions / information / answers register", pill("ok", "delivered"), ilink("open-questions.html", "Questions"), "8 questions with held / missing / discovery / blocked-decision"],
])}

<h2>Findings worth the owner's attention</h2>
{table(["#", "Finding", "Severity", "Evidence"], [
 ["1", "The 2021 opening-line series is unusable for CLV until WSGT is identified and its timestamps obtained (G01, Q-P01, Q-P02)", pill("bad", "high"), ilink("flagged.html", "G01") + " &middot; " + ilink("open-questions.html", "Q-P01")],
 ["2", "Several 2021 open&rarr;close movements are implausible (max 15 pts) and no official archive can adjudicate them (G02)", pill("bad", "high"), ilink("flagged.html", "G02")],
 ["3", "The pinned feed is 29 finals stale; re-pinning is a suggestion, not an action, because it re-bases shared numbers (G04, S-G05)", pill("warn", "medium"), ilink("results.html", "results") + " &middot; " + ilink("suggestions.html", "S-G05")],
 ["4", "The fair moneyline is a labelled derivation; a dedicated ML model is an open question (G06, Q-P03)", pill("warn", "medium"), ilink("origination-order.html", "order") + " &middot; " + ilink("open-questions.html", "Q-P03")],
 ["5", "Two strategies show positive flat ROI (S4 +0.33%, S6 +0.58% over 1,084 and 600 bets) &mdash; none is reward-eligible; the hub's multiplicity analysis stands", pill("info", "info"), ilink("leaderboard.html", "leaderboard") + " &middot; " + ilink("../hub/competition.html", "gates")],
])}

<h2>Full report</h2>
<p><a href="EXECUTIVE_SUMMARY.md">EXECUTIVE_SUMMARY.md</a> in this directory holds the same summary in Markdown with
the session record, methods and verification results.</p>
"""
    return shell("executive-summary.html", "Executive summary", "Executive summary",
                 "What the Snapshot Desk delivers, the requirement coverage, and the findings that need an owner decision.", body)


# --------------------------------------------------------------------------- #
# page: index
# --------------------------------------------------------------------------- #
def page_index() -> str:
    s, ol, rf = summary["snapshots"], summary["origination_ledger"], summary["results_feed"]
    body = f"""
<div class="grid k4">
  <div class="card"><div class="tag">Snapshot store</div><div class="num">{s['rows_total']:,}</div>
    <div class="sub">open &middot; close &middot; fair rows per originated market</div></div>
  <div class="card"><div class="tag">Origination ledger</div><div class="num">{ol['rows']:,}</div>
    <div class="sub">fair / market / difference as separate columns, order 1-2-3 enforced</div></div>
  <div class="card"><div class="tag">Official finals cross-checked</div><div class="num">{rf['official_finals_checked']}</div>
    <div class="sub">2026 weeks 1–10 &middot; all 108 pinned matches exact</div></div>
  <div class="card"><div class="tag">Leaderboard axes</div><div class="num">2</div>
    <div class="sub">signal (rewards) &middot; staking (never promotes)</div></div>
</div>

<h2>Purpose</h2>
<div class="note">This desk is the settlement layer for the repository's line-origination research: it stores what
the market said (open and close) about every market we originate, settles outcomes against officially
cross-checked results, and scores strategies on a leaderboard designed so that luck in staking cannot mask a bad
signal. A demotion gate is defined before anything goes live. Nothing on these pages is a betting
recommendation.</div>

<h2>Pages</h2>
{table(["Page", "What it holds"], [
 [ilink("snapshots.html", "Price-snapshot store"), f"{s['rows_total']:,} snapshot rows; 2021 open&rarr;close movement; fair/market/difference columns"],
 [ilink("results.html", "Verified results feed"), f"all {rf['official_finals_checked']} officially final 2026 games with per-row official links; {N_HIST:,}-row history feed for backtests"],
 [ilink("origination-order.html", "Origination order"), "side &rarr; total &rarr; moneyline; conventions; enforcement"],
 [ilink("leaderboard.html", "Leaderboard"), "11 strategies scored on signal and staking axes separately"],
 [ilink("demotion.html", "Demotion gate"), "six automatic triggers that send a live strategy back to paper"],
 [ilink("suggestions.html", "Suggestions"), "ten proposals, each with a decision path &mdash; none implemented"],
 [ilink("open-questions.html", "Open questions"), "what is held, what is missing, how to discover it, what it blocks"],
 [ilink("flagged.html", "Flagged for review"), "irregularities G01–G10 with sources"],
 [ilink("sources.html", "Sources"), "the source register and the verification performed"],
 [ilink("executive-summary.html", "Executive summary"), "the one-page session summary"],
])}
"""
    return shell("index.html", "Snapshot Desk", "Snapshot Desk",
                 "The settlement layer: price snapshots, a verified results feed, the origination order, a signal-vs-staking leaderboard and a demotion gate — every value sourced or blank.", body)


# --------------------------------------------------------------------------- #
# emit
# --------------------------------------------------------------------------- #
pages = {
    "index.html": page_index(),
    "snapshots.html": page_snapshots(),
    "results.html": page_results(),
    "origination-order.html": page_order(),
    "leaderboard.html": page_leaderboard(),
    "demotion.html": page_demotion(),
    "suggestions.html": page_suggestions(),
    "open-questions.html": page_questions(),
    "flagged.html": page_flagged(),
    "sources.html": page_sources(),
    "executive-summary.html": page_exec(),
}
for name, html in pages.items():
    (OUT / name).write_text(inject_nav(html))

if MISSING_LINK:
    raise SystemExit("rows emitted without a source link: " + "; ".join(MISSING_LINK))
print(f"built {len(pages)} pages; snapshot rows {N_SNAP:,}; history rows {N_HIST:,}")
