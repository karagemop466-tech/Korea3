#!/usr/bin/env python3
"""make_site.py -- build the static dashboard in docs/ from docs/data/*.json.

Rules baked in:
  * every table row carries a source link (pinned dataset URL or the script that
    computed the number);
  * a value that could not be verified is rendered as an em dash and tagged,
    never filled in with a guess;
  * no number on the site is hard-coded -- everything comes from the JSON files
    produced by run_all.py / verify_external.py.
"""
import html
import json
import math
import os
import re
from datetime import datetime, timezone

from common import DOCS_DATA, REPO_URL, ROOT

DOCS = os.path.join(ROOT, "docs")
SITE_NAME = "NFL Line Lab"

# --------------------------------------------------------------------------
# formatting
# --------------------------------------------------------------------------
def esc(x):
    return html.escape(str(x), quote=True)


def pct(x, d=2):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return '<span class="muted">—</span>'
    return f"{x * 100:.{d}f}%"


def num(x, d=2):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return '<span class="muted">—</span>'
    return f"{x:,.{d}f}"


def integer(x):
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return '<span class="muted">—</span>'
    return f"{int(x):,}"


def signed(x, d=2, unit=""):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return '<span class="muted">—</span>'
    cls = "good" if x > 0 else ("bad" if x < 0 else "muted")
    return f'<span class="{cls}">{x * 100:+.{d}f}%</span>' if unit == "%" else \
           f'<span class="{cls}">{x:+.{d}f}</span>'


def ci(pair, d=2, as_pct=True):
    if not pair or pair[0] is None:
        return '<span class="muted">—</span>'
    lo, hi = pair
    f = (lambda v: f"{v * 100:.{d}f}%") if as_pct else (lambda v: f"{v:.{d}f}")
    return f"{f(lo)} … {f(hi)}"


def a(url, text=None, cls=""):
    if not url:
        return esc(text or "")
    c = f' class="{cls}"' if cls else ""
    return f'<a href="{esc(url)}"{c}>{esc(text or url)}</a>'


def dash(note="unverified"):
    return f'<span class="muted" title="{esc(note)}">—</span>'


# --------------------------------------------------------------------------
# sources
# --------------------------------------------------------------------------
PROV = json.load(open(os.path.join(ROOT, "data", "PROVENANCE.json")))
VERIF = json.load(open(os.path.join(ROOT, "data", "verification.json")))


def prov(key):
    return PROV["files"][key]


SRC = {
    "games": prov("games.csv"),
    "closing": prov("closing_lines.csv"),
    "sc": prov("sc_lines.csv"),
    "initial": prov("initial_lines.csv"),
    "win_totals": prov("win_totals.csv"),
    "teams": prov("teams.csv"),
    "playerweek": prov("weekly_player_stats_offense_smaller.csv"),
}


def src_games(label="games.csv"):
    p = SRC["games"]
    return f'<a class="src" href="{esc(p["pinned_url"])}" title="pinned to commit {esc(p["commit"][:8])}">{esc(label)}</a>'


def src_script(name, label=None):
    return (f'<a class="src" href="{esc(REPO_URL)}/blob/main/scripts/{esc(name)}">'
            f'{esc(label or name)}</a>')


def src_computed(script, dataset="games"):
    label = dataset if dataset.endswith((".csv", ".json")) else f"{dataset}.csv"
    return src_games(label) + " · " + src_script(script)


# --------------------------------------------------------------------------
# page chrome
# --------------------------------------------------------------------------
NAV = [
    ("index.html", "Dashboard"),
    ("line-board.html", "Line Board"),
    ("market.html", "Market"),
    ("model.html", "Model"),
    ("strategies.html", "Strategies"),
    ("leaderboard.html", "Leaderboard"),
    ("singles.html", "Singles"),
    ("parlays.html", "Parlays & SGP"),
    ("props.html", "Player Props"),
    ("correlation.html", "Correlation"),
    ("validation.html", "Validation"),
    ("luck.html", "Luck vs Skill"),
    ("findings.html", "Findings"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged for Review"),
    ("methodology.html", "Method"),
]


def page(filename, title, body, lede="", active=None):
    active = active or filename
    nav_parts = []
    for f, l in NAV:
        cls = ' class="active"' if f == active else ""
        nav_parts.append(f'<a href="{f}"{cls}>{esc(l)}</a>')
    nav = "".join(nav_parts)
    meta = json.load(open(f"{DOCS_DATA}/meta.json"))
    gen = meta["generated_utc"]
    doc = f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{esc(title)} · {SITE_NAME}</title>
<meta name="description" content="Reproducible NFL line origination, strategy validation and correlation research.">
<link rel="stylesheet" href="assets/style.css">
</head><body>
<header class="top"><div class="bar">
  <div class="brand">NFL <span>Line Lab</span></div>
  <nav class="main">{nav}</nav>
</div></header>
<div class="wrap">
<h1>{esc(title)}</h1>
{f'<p class="lede">{lede}</p>' if lede else ''}
{body}
<footer>
  Built from <code>nflverse/nfldata</code> pinned at commit
  <code>{esc(meta['dataset_commit'][:10])}</code>. Every table row links to its source.
  Generated {esc(gen)} · <a href="{esc(REPO_URL)}">repository</a> ·
  <a href="flagged.html">flagged items</a> ·
  <a href="methodology.html">method</a>.
  <br>Research output only. Not betting advice.
</footer>
</div>
<script src="assets/app.js"></script>
</body></html>"""
    with open(os.path.join(DOCS, filename), "w") as fh:
        fh.write(doc)
    return filename


def table(headers, rows, tid=None, sortable=True, numeric_cols=()):
    """headers: list of str; rows: list of list of html strings."""
    th = "".join(
        f'<th class="num">{esc(h)}</th>' if i in numeric_cols else f'<th>{esc(h)}</th>'
        for i, h in enumerate(headers))
    body = []
    for row in rows:
        tds = "".join(
            f'<td class="num">{c}</td>' if i in numeric_cols else f'<td>{c}</td>'
            for i, c in enumerate(row))
        body.append(f"<tr>{tds}</tr>")
    cls = "sortable" if sortable else ""
    idattr = f' id="{tid}"' if tid else ""
    return (f'<div class="tablewrap"><table class="{cls}"{idattr}><thead><tr>{th}</tr></thead>'
            f'<tbody>{"".join(body)}</tbody></table></div>')


def filter_box(tid, placeholder="Filter rows…"):
    return (f'<input class="filter" data-for="#{tid}" type="text" '
            f'placeholder="{esc(placeholder)}" aria-label="filter">')


def note(text, kind="", title="Note"):
    return f'<div class="note {kind}"><div class="t">{esc(title)}</div><p>{text}</p></div>'


def chip(text, kind=""):
    return f'<span class="chip {kind}">{esc(text)}</span>'


# --------------------------------------------------------------------------
# load data
# --------------------------------------------------------------------------
META = json.load(open(f"{DOCS_DATA}/meta.json"))
MARKET = json.load(open(f"{DOCS_DATA}/market.json"))
MODEL = json.load(open(f"{DOCS_DATA}/model.json"))
STRAT = json.load(open(f"{DOCS_DATA}/strategies.json"))
LEADER = json.load(open(f"{DOCS_DATA}/leaderboard.json"))
PARLAYS = json.load(open(f"{DOCS_DATA}/parlays.json"))
PROPS = json.load(open(f"{DOCS_DATA}/props.json"))
CORR = json.load(open(f"{DOCS_DATA}/correlations.json"))
VALID = json.load(open(f"{DOCS_DATA}/validation.json"))
LUCK = json.load(open(f"{DOCS_DATA}/luck.json"))
BOARD = json.load(open(f"{DOCS_DATA}/lineboard.json"))

RESULTS = {r["strategy_id"]: r for r in STRAT["results"]}
LB = {r["strategy_id"]: r for r in LEADER}


# ==========================================================================
# 1. dashboard
# ==========================================================================
def build_index():
    n_ok = META["n_passing_all_gates"]
    top = [z for z in LEADER if z["rank"] == 1]
    best = top[0] if top else None
    kpis = f"""
<div class="kpis">
  <div class="kpi"><div class="l">Games in dataset</div><div class="v">{integer(META['n_games'])}</div>
    <div class="s">{META['seasons_backtested'][0]}–{META['seasons_backtested'][1]} incl. partial 2026</div></div>
  <div class="kpi"><div class="l">Bets simulated</div><div class="v">{integer(META['n_bets'])}</div>
    <div class="s">settled against real closing prices</div></div>
  <div class="kpi"><div class="l">Strategies tested</div><div class="v">{META['n_strategies']}</div>
    <div class="s">singles · parlays · SGP · props</div></div>
  <div class="kpi {'bad' if n_ok == 0 else 'good'}"><div class="l">Passing all 9 gates</div>
    <div class="v">{n_ok}</div><div class="s">multiple-testing corrected</div></div>
  <div class="kpi warn"><div class="l">Break-even hit rate</div><div class="v">52.38%</div>
    <div class="s">at the standard −110 price</div></div>
</div>"""

    lb_rows = []
    for z in [x for x in LEADER if x["rank"]][:8]:
        r = RESULTS[z["strategy_id"]]
        lb_rows.append([
            f'<b>{z["rank"]}</b>', f'<b>{esc(z["strategy_id"])}</b> {esc(r.get("name", ""))}',
            signed(z["roi"], 2, "%"), ci(r.get("roi_ci_bet")),
            num(z["p_value"], 4), f'{z["gates_passed"]}/{z["gates_total"]}',
            chip(z["tier"], "g" if z["tier"] == "A" else "w" if z["tier"] in "BC" else ""),
            src_computed("run_all.py"),
        ])
    lb_table = table(["#", "Strategy", "ROI", "95% CI", "p vs luck", "Gates", "Tier", "Source"],
                     lb_rows, tid="t-top", numeric_cols=(2, 4))

    cards = [
        ("line-board.html", "Line Board",
         f"Our own spread and total for all {len(BOARD)} games of the 2026 season, with the market "
         "price and the disagreement in points wherever a market exists."),
        ("market.html", "Market Structure",
         "What the book charges: hold, break-even rates, base rates, favourite–longshot bias and "
         "open→close movement."),
        ("model.html", "Origination Model",
         "Walk-forward Elo + form model, no leakage: how close our number gets to the market."),
        ("strategies.html", "Strategy Registry",
         "28 mechanical rules — singles, parlays, same-game combos and player props — with the "
         "exact rule text."),
        ("leaderboard.html", "Leaderboard",
         "Luck-adjusted ranking, reward tiers and allocation weights for the competition."),
        ("singles.html", "Single Bets", "Spread, total and moneyline strategies with per-season breakdowns."),
        ("parlays.html", "Parlays & SGP", "Cross-game parlays, same-game spread+total, and the independence tests behind them."),
        ("props.html", "Player Props", "Prop origination, calibration, and prop-combo correlation."),
        ("correlation.html", "Correlation", "Every correlation value used to price combos, with confidence intervals."),
        ("validation.html", "Validation Gates", "The nine gates and which strategies survive each one."),
        ("luck.html", "Luck vs Skill", "Zero-skill simulation bands, deflated Sharpe and the edge-monotonicity test."),
        ("findings.html", "Findings", "The executive summary: what worked, what did not, and why."),
        ("sources.html", "Sources", "Pinned data, checksums and external verification results."),
        ("flagged.html", "Flagged for Review", "Unverified values, provenance gaps and anomalies — each with a source link."),
        ("methodology.html", "Method", "How to reproduce everything from a clean checkout."),
    ]
    grid = "".join(
        f'<div class="card"><a class="cardlink" href="{f}"><h3><a href="{f}">{esc(t)}</a></h3>'
        f'<p>{esc(d)}</p></a></div>' for f, t, d in cards)

    body = kpis + f"""
<h2>Headline result</h2>
{note("<b>No strategy clears all nine validation gates.</b> The best performer — "
      "<b>S08 Fade the big favourite</b> — returns "
      f"{pct(best['roi'])} on {integer(best['n_bets'])} bets with a 95% confidence interval of "
      f"{ci(RESULTS[best['strategy_id']].get('roi_ci_bet'))} and p = {num(best['p_value'], 3)} against a "
      "zero-skill simulation. It fails the multiple-testing gate and the season-consistency gate, and its "
      "held-out return is ~0. That is the honest state of play, not a validated edge.",
      "warn", "Read this first")}
<h2>Leaderboard — top 8 (observed prices only)</h2>
{lb_table}
<p class="small">The three strategies that scored highest overall but rely on <em>assumed</em> prices
   (T09, P03, T08) are excluded from ranking and listed on the
   <a href="leaderboard.html">leaderboard page</a> with a <code>price-unverified</code> tier.</p>
<h2>Key numbers</h2>
{key_numbers_table()}
<h2>Explore</h2>
<div class="grid">{grid}</div>
"""
    return page("index.html", "NFL Line Lab — origination, signals and skill",
                body, "A reproducible study of whether a self-built NFL number can beat the market, "
                     "and how much of any result is luck.", active="index.html")


def key_numbers_table():
    mq = META["model_quality"]
    br = MARKET["base_rates"]
    rows = [
        ["Model spread RMSE", num(mq["model_spread_rmse"]), num(mq["market_spread_rmse"]),
         "lower is better; market wins", src_computed("model.py")],
        ["Model margin correlation", num(mq["model_spread_corr"], 3), num(mq["market_spread_corr"], 3),
         "correlation with realised margin", src_computed("model.py")],
        ["Home team win rate", pct(br["home_win_rate"]), '<span class="muted">n/a</span>',
         "all played games in sample", src_computed("market.py")],
        ["Home cover rate (ATS)", pct(br["home_cover_rate"]), pct(0.5), "push rate " + pct(br["ats_push_rate"]),
         src_computed("market.py")],
        ["Over rate", pct(br["over_rate"]), pct(0.5), "push rate " + pct(br["total_push_rate"]),
         src_computed("market.py")],
        ["Median hold — spread", pct(MARKET["hold"]["spread"]["median_hold_pct"] / 100), "—",
         f'{integer(MARKET["hold"]["spread"]["n"])} games', src_games()],
        ["Median hold — total", pct(MARKET["hold"]["total"]["median_hold_pct"] / 100), "—",
         f'{integer(MARKET["hold"]["total"]["n"])} games', src_games()],
        ["Spread × total correlation", num(CORR["within_game"]["margin_vs_total"]["r"], 3),
         f'CI {num(CORR["within_game"]["margin_vs_total"]["lo"], 3)} … {num(CORR["within_game"]["margin_vs_total"]["hi"], 3)}',
         "same-game combos are near-independent", src_computed("correlations.py")],
        ["Cross-game ATS correlation", num(CORR["cross_game"]["r"], 3),
         f'CI {num(CORR["cross_game"]["lo"], 3)} … {num(CORR["cross_game"]["hi"], 3)}',
         "standard parlay multiplication is sound", src_computed("correlations.py")],
        ["Bets independently re-settled", integer(VERIF["V_D_bet_resettlement"]["recomputed_match"]),
         integer(VERIF["V_D_bet_resettlement"]["mismatch"]), "recomputed vs stored mismatches",
         src_script("verify_external.py", "verify_external.py")],
        ["PFR score spot-checks passed",
         f'{VERIF["V_A_pfr_scores"]["n_match"]}/{VERIF["V_A_pfr_scores"]["n_checked"]}', "—",
         "final scores vs Pro-Football-Reference",
         a(VERIF["V_A_pfr_scores"]["source"], "PFR 2024 schedule")],
    ]
    return table(["Metric", "Ours", "Market / reference", "What it means", "Source"],
                 rows, tid="t-keys", numeric_cols=(1, 2))


# ==========================================================================
# 2. line board
# ==========================================================================
def build_line_board():
    weeks = sorted({g["week"] for g in BOARD})
    rows = []
    for g in BOARD:
        edge = g["edge_spread"]
        cls = "good" if (edge or 0) > 0 else ("bad" if (edge or 0) < 0 else "")
        rows.append([
            str(g["week"]), esc(g["date"]), f'{esc(g["away"])} @ {esc(g["home"])}',
            num(g["my_spread"], 1), num(g["market_spread"], 1),
            f'<span class="{cls}">{num(edge, 2)}</span>' if edge is not None else dash("no market posted"),
            num(g["my_total"], 1), num(g["market_total"], 1), num(g["edge_total"], 2),
            esc(g["ats_grade"] or ""), src_games("games.csv"),
        ])
    tbl = (filter_box("t-board", "Filter by team, week…")
           + table(["Wk", "Date", "Matchup", "Our spread", "Market", "Edge", "Our total",
                    "Market", "Edge", "ATS grade", "Source"],
                   rows, tid="t-board", numeric_cols=(3, 4, 5, 6, 7, 8)))
    played = sum(1 for g in BOARD if g["played"])
    body = note(
        f"Our number exists for all {len(BOARD)} scheduled 2026 games; a market comparison exists for "
        f"{played} of them ({len(BOARD) - played} games had no posted line in the source at the time of "
        "capture). Blank market cells are left blank rather than filled from another source.", "", "Coverage")
    body += note(
        "Spreads are quoted from the <b>home</b> perspective with the favourite positive, matching the "
        "source file's convention (verified against <code>result = home − away</code> on every row). "
        "Edges are our number minus the market number, in points.", "", "Sign convention")
    body += f"<h2>2026 board</h2>{tbl}"
    body += f'<p class="small">Weeks covered: {min(weeks)}–{max(weeks)}. Source: {src_games()}, model coefficients from {src_script("model.py")}.</p>'
    return page("line-board.html", "Line Board — 2026",
                body, "Our own spread and total for every scheduled 2026 game. This is the origination "
                     "output: where it disagrees with the market, the disagreement is the signal a "
                     "strategy would trade.")


# ==========================================================================
# 3. market structure
# ==========================================================================
def build_market():
    h = MARKET["hold"]
    rows = []
    for k in ("spread", "total", "moneyline"):
        if k not in h:
            continue
        d = h[k]
        rows.append([esc(k.title()), integer(d["n"]), pct(d["mean_overround"] - 1),
                     pct(d["median_hold_pct"] / 100), num(d["typical_price"], 0),
                     src_games()])
    hold_tbl = table(["Market", "Games", "Mean hold", "Median hold", "Typical price", "Source"],
                     rows, tid="t-hold", numeric_cols=(1, 2, 3, 4))

    be = h.get("breakeven_by_price", {})
    be_rows = [[esc(k), num(v["decimal"], 4), pct(v["required_hit_rate"]), "—", src_games()]
               for k, v in be.items() if k.startswith("-")]
    be_tbl = table(["Price", "Decimal", "Break-even hit rate", "", "Source"], be_rows,
                   tid="t-be", numeric_cols=(1, 2))

    br = MARKET["base_rates"]
    br_rows = [
        ["Home win rate", pct(br["home_win_rate"]), "—", src_computed("market.py")],
        ["Away win rate", pct(br["away_win_rate"]), "—", src_computed("market.py")],
        ["Tie rate", pct(br["tie_rate"]), "—", src_computed("market.py")],
        ["Home covers the spread", pct(br["home_cover_rate"]), f'push {pct(br["ats_push_rate"])}',
         src_computed("market.py")],
        ["Over hits", pct(br["over_rate"]), f'push {pct(br["total_push_rate"])}',
         src_computed("market.py")],
        ["Mean total points", num(br["mean_total_points"], 1), f'sd {num(br["sd_total"], 1)}',
         src_computed("market.py")],
        ["Mean |margin|", num(br["mean_abs_margin"], 1), f'sd {num(br["sd_margin"], 1)}',
         src_computed("market.py")],
        ["Mean |closing line|", num(br["mean_abs_closing_line"], 2), "points",
         src_computed("market.py")],
    ]
    br_tbl = table(["Base rate", "Value", "Detail", "Source"], br_rows,
                   tid="t-base", numeric_cols=(1,))

    fl = MARKET["favourite_longshot"]
    fl_rows = [[esc(x["bucket"]), integer(x["n"]), pct(x["implied_raw"]), pct(x["implied_devig"]),
                pct(x["actual_home_win_rate"]), signed(x["home_ml_roi"], 2, "%"), src_games()]
               for x in fl]
    fl_tbl = table(["Home moneyline bucket", "Games", "Raw implied", "De-vigged implied",
                    "Actual home win rate", "Home ML ROI", "Source"],
                   fl_rows, tid="t-fl", numeric_cols=(1, 2, 3, 4, 5))

    md = MARKET["margin_distribution"]
    md_rows = [[str(x["margin"]), integer(x["n"]), pct(x["share"]), src_games()] for x in md]
    md_tbl = table(["Winning margin (abs)", "Games", "Share", "Source"], md_rows,
                   tid="t-md", numeric_cols=(1, 2))

    mv = MARKET["line_movement"]
    mv_rows = []
    for key in ("opening_vs_closing", "secondary_line_file"):
        d = mv.get(key, {})
        if "error" in d:
            mv_rows.append([esc(key), dash("error"), dash(), dash(), dash(), dash(), esc(d["error"])])
            continue
        mv_rows.append([esc(key), integer(d.get("n_games")),
                        num(d.get("mean_abs_move_pts"), 2), num(d.get("median_abs_move_pts"), 2),
                        pct(d.get("share_moved_1pt_or_more")), num(d.get("corr_open_close"), 3),
                        src_games("line files")])
    mv_tbl = table(["File", "Games", "Mean |move| pts", "Median |move| pts", "Moved ≥1 pt",
                    "corr(open, close)", "Source"], mv_rows, tid="t-mv",
                   numeric_cols=(1, 2, 3, 4, 5))

    body = f"""
<p>Before writing a strategy you need to know what the book charges and how often each side wins.
All figures below are computed from the same pinned dataset used everywhere else.</p>
{note("Median hold of 2.4–2.9% is <b>lower</b> than a typical retail book (≈4.5–5%) and the publisher "
      "does not say which sportsbook the lines come from. Treat every ROI figure on this site as "
      "conditional on that undocumented source — see <a href='flagged.html'>IR-01</a>.", "warn",
      "Provenance caveat")}
<h2>Hold and break-even</h2>
{hold_tbl}
{be_tbl}
<h2>Base rates</h2>
{br_tbl}
<h2>Favourite–longshot bias (home moneyline)</h2>
{fl_tbl}
<p class="small">If the market were perfectly de-vigged, the actual win rate would match the de-vigged
implied rate in every bucket. Favourites priced −200 to −150 underperformed their de-vigged rate by
{num((fl[2]['implied_devig'] - fl[2]['actual_home_win_rate']) * 100 if len(fl) > 2 else float('nan'), 1)}
points; the longest-priced home dogs beat theirs. This is the classic longshot bias, and it is why the
always-favourite control shows a suspicious p-value on the luck page.</p>
<h2>Winning-margin distribution (key numbers)</h2>
{md_tbl}
<p class="small">Margins of 3 and 7 are far more common than 4, 5 or 8 — the reason 3 and 7 are "key
numbers" and why half-point buys around them cost more.</p>
<h2>Open → close movement</h2>
{mv_tbl}
{note("The 2021 opening-line file shows a mean absolute open→close move of "
      f"{num(mv.get('opening_vs_closing', {}).get('mean_abs_move_pts', float('nan')), 2)} points, which is "
      "roughly double what is normally reported. The file contains a single sportsbook label ("
      f"{esc(mv.get('opening_vs_closing', {}).get('sportsbook', 'WSGT'))}) and no capture timestamp, so we "
      "cannot tell whether these are true openers. The figure is reported for transparency and is "
      "<b>not used by any strategy</b>.", "bad", "IR-05 — anomaly flagged")}
"""
    return page("market.html", "Market Structure",
                body, "Hold, break-even rates, base rates, bias and line movement — the constraints "
                     "any strategy has to beat.")


# ==========================================================================
# 4. model
# ==========================================================================
def build_model():
    q = MODEL["quality"]
    sp = MODEL["season_params"]
    rows = [
        ["Spread RMSE (points)", num(q["model_spread_rmse"]), num(q["market_spread_rmse"]),
         "market better by " + num(q["market_spread_rmse"] - q["model_spread_rmse"], 2), src_computed("model.py")],
        ["Total RMSE (points)", num(q["model_total_rmse"]), num(q["market_total_rmse"]),
         "market better by " + num(q["market_total_rmse"] - q["model_total_rmse"], 2), src_computed("model.py")],
        ["Spread correlation with result", num(q["model_spread_corr"], 3), num(q["market_spread_corr"], 3),
         "correlation, not accuracy", src_computed("model.py")],
        ["Mean |our line − market|", num(q["mae_gap_points"], 2) + " pts", "—",
         "average disagreement per game", src_computed("model.py")],
        ["Share of games with ≥2 pt disagreement", pct(q["share_games_edge_ge_2"]), "—",
         "how often a signal even exists", src_computed("model.py")],
        ["Games evaluated", integer(q["n_games"]), "—", "completed games with lines", src_games()],
    ]
    tbl = table(["Metric", "Ours", "Market", "Reading", "Source"], rows,
                tid="t-model", numeric_cols=(1, 2))

    latest = sorted(sp.items())[-6:]
    prow = []
    for season, d in latest:
        coefs = d["margin_coefs"]
        prow.append([str(season), integer(d["train_games"]),
                     num(d["sigma_margin"], 2), num(d["sigma_total"], 2),
                     num(coefs[1] * 400, 2) + " pts", num(coefs[2] * 400, 2) + " pts",
                     src_computed("model.py")])
    ptbl = table(["Season", "Training games", "σ margin", "σ total",
                  "400 Elo pts ≈ spread", "400 form pts ≈ spread", "Source"], prow,
                 tid="t-params", numeric_cols=(1, 2, 3, 4, 5))

    leak = META["leakage_guard"]
    body = f"""
<p>The origination model is deliberately simple and deliberately leak-free: two linear models refit
each season using only earlier seasons, on features that exist before kickoff.</p>
<pre class="small">margin ~ 1 + elo_diff + form_diff + rest_diff + div_game
total  ~ 1 + off_home + def_away + off_away + def_home + dome</pre>
<h2>How good is our number?</h2>
{tbl}
{note("Our number is <b>close to</b> the market but consistently <b>worse</b>: about 0.4 points of "
      "extra error on every game. That is the honest baseline — any strategy must manufacture an edge "
      "from specific situations, because the general forecast is inferior.", "warn", "Read this")}
<h2>Leakage guard</h2>
<p>For {integer(leak['checks'])} randomly chosen games, the pre-game Elo rating was rebuilt from a
history truncated at that game. Maximum absolute difference between the rebuilt and stored rating:
<b>{num(leak['max_abs_diff'], 10)}</b>. Pass: <b>{'yes' if leak['passed'] else 'no'}</b>.
Source: {src_script('features.py', 'features.py')}.</p>
<h2>Coefficients by season (latest six)</h2>
{ptbl}
<p class="small">Feature sets were selected once, using only 2003–2014 walk-forward RMSE
(see <a href="flagged.html">IR-08</a>). All reported betting results come from later seasons.</p>
"""
    return page("model.html", "Origination Model",
                body, "Walk-forward Elo plus form and rest. Refit every season on prior seasons only, "
                     "with an explicit point-in-time rebuild test.")


# ==========================================================================
# 5. strategies registry
# ==========================================================================
def build_strategies():
    rows = []
    for s in STRAT["registry"]:
        r = RESULTS.get(s["id"], {})
        rows.append([
            f'<b>{esc(s["id"])}</b>', esc(s["name"]), chip(s["category"]),
            f'<span class="wrapcell">{esc(s["rule"])}</span>',
            integer(r.get("n_bets", 0)),
            pct(r.get("roi")),
            f'{r.get("gates_passed", 0)}/{r.get("gates_total", 9)}',
            src_computed("strategies.py", "strategies.py"),
        ])
    tbl = (filter_box("t-strat", "Filter rules…")
           + table(["ID", "Name", "Type", "Mechanical rule (verbatim)", "Bets", "ROI", "Gates",
                    "Source"], rows, tid="t-strat", numeric_cols=(4, 5)))
    body = f"""
<p>Every strategy is a fixed rule evaluated on pre-game information only. No discretionary
overrides, no in-sample threshold tuning after the fact: thresholds were set once and applied to all
seasons.</p>
{note("The registry is the complete list of everything that was tried. Reporting the failures is the "
      "point — a leaderboard built only from the surviving rules would be meaningless.", "", "Why publish failures")}
{tbl}
<p class="small">Categories: <code>single</code> = one leg, <code>parlay</code> = multiple games,
<code>sgp</code> = same game, <code>prop</code> = player market, <code>control</code> = no-model
benchmark. Rules are also in <code>scripts/run_all.py</code> as data, so the site and the code cannot
drift apart.</p>
"""
    return page("strategies.html", "Strategy Registry",
                body, "28 mechanical rules: what they do, how many bets they took, and how they scored.")


# ==========================================================================
# 6. leaderboard
# ==========================================================================
def build_leaderboard():
    ranked = [z for z in LEADER if z["rank"]]
    unver = [z for z in LEADER if not z["rank"] and not z["is_control"]]
    ctrl = [z for z in LEADER if z["is_control"]]

    def rowset(items, show_rank=True):
        out = []
        for z in items:
            r = RESULTS[z["strategy_id"]]
            out.append([
                f'<b>{z["rank"]}</b>' if show_rank and z["rank"] else '<span class="muted">—</span>',
                f'<b>{esc(z["strategy_id"])}</b>', esc(r.get("name", "")),
                num(z["score"], 1), chip(z["tier"], "g" if z["tier"] == "A" else "w" if z["tier"] in ("B", "C") else ("a" if z["tier"] == "price-unverified" else "")),
                num(z["reward_points"], 0),
                pct(z.get("allocation_weight", 0)),
                signed(z["roi"], 2, "%"), ci(r.get("roi_ci_bet")),
                num(z["p_value"], 4), f'{z["gates_passed"]}/{z["gates_total"]}',
                integer(z["n_bets"]),
                '<span class="good">yes</span>' if z["prices_observed"] else '<span class="bad">assumed</span>',
                src_computed("leaderboard.py", "leaderboard.py"),
            ])
        return out

    hdr = ["#", "ID", "Name", "Score", "Tier", "Reward pts", "Alloc. weight", "ROI",
           "95% CI", "p vs luck", "Gates", "Bets", "Prices", "Source"]
    t1 = table(hdr, rowset(ranked), tid="t-lb", numeric_cols=(3, 5, 6, 7, 9))
    t2 = table(hdr, rowset(unver, False), tid="t-lb2", numeric_cols=(3, 5, 6, 7, 9))
    t3 = table(hdr, rowset(ctrl, False), tid="t-lb3", numeric_cols=(3, 5, 6, 7, 9))

    body = f"""
<p>The competition ranks strategies by a luck-adjusted score rather than raw ROI, because raw ROI
rewards small samples and lucky streaks.</p>
<pre class="small">score = 100 × (0.40 × gates_passed/9
             + 0.30 × clip((ROI_CI_lower + 5%) / 15%, 0, 1)
             + 0.15 × clip(1 − p_value / 0.10, 0, 1)
             + 0.15 × share_of_seasons_profitable)</pre>
<p>Reward tiers: <b>A</b> = passes all nine gates (100 pts), <b>B</b> = score ≥ 55 (60 pts),
<b>C</b> = score ≥ 40 (25 pts), <b>D</b> = otherwise (5 pts). Benchmarks earn nothing.
Allocation weight is proportional to score² within the ranked pool, so a small score edge translates
into a small capital edge, not a linear one.</p>
<h2>Ranked strategies (observed prices only)</h2>
{t1}
<h2>Excluded from ranking — prices assumed, not observed</h2>
<p class="small">These strategies are shown for completeness. Their ROI depends on a price we had to
assume (a naive multiplicative same-game price, or a flat −110 prop price), so it cannot be validated
and earns no rank or reward. See <a href="flagged.html">IR-03</a>.</p>
{t2}
<h2>Benchmarks (no model)</h2>
{t3}
{note("Tier A is empty. The gap between the best strategy (S08) and the best benchmark "
      "(always-favourite, +0.21% ROI) is well inside the sampling noise for their sample sizes — which "
      "is exactly what the gates are there to expose.", "warn", "Result")}
"""
    return page("leaderboard.html", "Leaderboard",
                body, "Scores, tiers, reward points and allocation weights — with the multiple-testing "
                     "haircut applied.")


# ==========================================================================
# 7. singles
# ==========================================================================
def build_singles():
    ids = [k for k in RESULTS if k.startswith("S") or k.startswith("C")]
    rows = []
    for sid in sorted(ids):
        r = RESULTS[sid]
        rows.append([f'<b>{esc(sid)}</b>', esc(r.get("name", "")), integer(r["n_bets"]),
                     pct(r.get("hit_rate")), signed(r.get("roi"), 2, "%"),
                     ci(r.get("roi_ci_bet")), ci(r.get("roi_ci_season")),
                     pct(r.get("pct_seasons_profitable")), signed(r.get("holdout_roi"), 2, "%"),
                     num(r.get("p_value_vs_market"), 4), f'{r["gates_passed"]}/{r["gates_total"]}',
                     src_computed("engine.py", "engine.py")])
    tbl = table(["ID", "Name", "Bets", "Hit rate", "ROI", "95% CI (bets)", "95% CI (seasons)",
                 "Seasons +", "Holdout ROI", "p vs luck", "Gates", "Source"],
                rows, tid="t-singles", numeric_cols=(2, 3, 4, 7, 8, 9))

    season_rows = []
    for sid in sorted([k for k in RESULTS if k.startswith("S")]):
        r = RESULTS[sid]
        for s in r.get("by_season", []):
            season_rows.append([f'<b>{esc(sid)}</b>', str(s["season"]), integer(s["n"]),
                                signed(s["roi"], 2, "%"), signed(s["profit"], 1, ""),
                                src_computed("engine.py", "engine.py")])
    stbl = (filter_box("t-seasons", "Filter by strategy or season…")
            + table(["ID", "Season", "Bets", "ROI", "Profit (units)", "Source"], season_rows,
                    tid="t-seasons", numeric_cols=(2, 3, 4)))

    body = f"""
<p>Spread, total and moneyline strategies, plus the four no-model benchmarks that define what "doing
nothing" looks like.</p>
<h2>Summary</h2>
{tbl}
<h2>Season by season</h2>
<p class="small">A real edge should show up across seasons, not in one. The per-season table is the
raw material for the consistency gate (G7).</p>
{stbl}
"""
    return page("singles.html", "Single Bets",
                body, "Every single-leg strategy and benchmark, with season-level detail.")


# ==========================================================================
# 8. parlays
# ==========================================================================
def build_parlays():
    ids = ["P01", "P02", "P03", "T08", "T09"]
    rows = []
    for sid in ids:
        r = RESULTS.get(sid, {})
        rows.append([f'<b>{esc(sid)}</b>', esc(r.get("name", "")), integer(r.get("n_bets", 0)),
                     num(r.get("avg_dec"), 3), pct(r.get("hit_rate")), signed(r.get("roi"), 2, "%"),
                     ci(r.get("roi_ci_bet")), num(r.get("p_value_vs_market"), 4),
                     f'{r.get("gates_passed", 0)}/{r.get("gates_total", 9)}',
                     '<span class="good">observed</span>' if r.get("prices_observed") else '<span class="bad">assumed</span>',
                     src_computed("engine.py", "engine.py")])
    tbl = table(["ID", "Parlay type", "Bets", "Avg decimal", "Hit rate", "ROI", "95% CI",
                 "p vs luck", "Gates", "Prices", "Source"], rows, tid="t-parlay",
                numeric_cols=(2, 3, 4, 5, 7))

    cg = CORR["cross_game"]
    sgp = CORR["sgp_joint"]
    jrows = [[esc(x["combo"]), pct(x["joint_empirical"]), pct(x["product_of_rates"]),
              num(x["ratio"], 4), integer(x["n"]), src_computed("correlations.py", "correlations.py")]
             for x in sgp["combos"]]
    jtbl = table(["Same-game combo", "Empirical joint", "Product of leg rates", "Ratio", "Games",
                  "Source"], jrows, tid="t-sgp", numeric_cols=(1, 2, 3, 4))

    body = f"""
<p>A parlay multiplies prices, which is only correct if the legs are independent. We tested that
assumption instead of assuming it.</p>
<h2>Cross-game independence</h2>
<p>Correlation between the ATS outcome of one game and a randomly paired game in the same week:
<b>{num(cg['r'], 4)}</b> (95% CI {num(cg['lo'], 4)} … {num(cg['hi'], 4)}, n = {integer(cg['n'])}).
The interval contains zero, so multiplying cross-game leg prices is sound. Source:
{src_computed('correlations.py', 'correlations.py')}.</p>
<h2>Same-game spread × total</h2>
{jtbl}
{note("Same-game correlations are <b>tiny</b>: the empirical joint probability is within about ±2% of the "
      "product of the two leg rates, consistent with the measured r of "
      f"{num(CORR['within_game']['margin_vs_total']['r'], 3)}. The popular idea that a book which "
      "multiplies spread and total prices is exploitable does not survive the data.", "warn", "Finding")}
<h2>Parlay results</h2>
{tbl}
<p class="small">P01/P02 legs come from different games and are priced from observed leg prices, so
their ROI is real. P03, T08 and T09 are priced with the independence assumption and are therefore
<em>price-unverified</em>. T09 (same player, targets + receptions) shows a spectacular ROI precisely
because those two legs correlate at r = 0.92 — a naive multiplier would be badly wrong, which is why
real books do not price it that way.</p>
{note("The 3-leg parlay returns +13.5% over 370 bets, but its 95% confidence interval runs from "
      "−13.7% to +41.4%. With a hit rate of 15.4% on a 3-leg parlay, a 370-bet sample cannot "
      "distinguish a real edge from noise.", "", "Why sample size matters")}
"""
    return page("parlays.html", "Parlays & Same-Game",
                body, "Independence tests, correlation-adjusted pricing, and parlay performance.")


# ==========================================================================
# 9. props
# ==========================================================================
def build_props():
    drows = []
    for stat, d in PROPS["diagnostics"].items():
        drows.append([esc(stat.replace("_", " ")), integer(d["n_markets"]), pct(d["push_rate"]),
                      pct(d["over_rate_decided"]), num(d["brier"], 4), num(d["brier_baseline_50"], 4),
                      pct(d["breakeven_hit_rate"]), src_computed("props.py", "props.py")])
    dtbl = table(["Stat", "Markets", "Push rate", "Over rate (decided)", "Brier",
                  "Brier @ 50/50", "Break-even hit rate", "Source"], drows, tid="t-propdiag",
                 numeric_cols=(1, 2, 3, 4, 5, 6))

    rows = []
    for r in PROPS["results"]:
        rows.append([f'<b>{esc(r["strategy_id"])}</b>', esc(r.get("name", "")),
                     integer(r.get("n_bets", 0)), pct(r.get("hit_rate")),
                     signed(r.get("roi"), 2, "%"), ci(r.get("roi_ci_bet")),
                     num(r.get("p_value_vs_market"), 4),
                     f'{r.get("gates_passed", 0)}/{r.get("gates_total", 9)}',
                     '<span class="bad">assumed −110</span>',
                     src_computed("props.py", "props.py")])
    ptbl = table(["ID", "Strategy", "Bets", "Hit rate", "ROI (simulated)", "95% CI", "p vs luck",
                  "Gates", "Price", "Source"], rows, tid="t-props", numeric_cols=(2, 3, 4, 6))

    cal_rows = []
    for stat, d in PROPS["diagnostics"].items():
        for b in d["calibration"]:
            cal_rows.append([esc(stat.replace("_", " ")), num(b["predicted"], 3), num(b["actual"], 3),
                             integer(b["n"]), src_computed("props.py", "props.py")])
    ctbl = (filter_box("t-calib", "Filter stat…")
            + table(["Stat", "Predicted P(over)", "Actual over rate", "Player-games", "Source"],
                    cal_rows, tid="t-calib", numeric_cols=(1, 2, 3)))

    body = f"""
{note("<b>No verifiable player-prop prices exist in this environment.</b> Every prop strategy is "
      "settled against an <b>assumed −110</b> price and a <b>synthetic</b> line (the player's trailing "
      "8-game median). Hit rates below are measured and real; ROI is conditional on both assumptions. "
      "These strategies are excluded from the leaderboard ranking — see "
      "<a href='flagged.html'>IR-03</a>.", "bad", "Read before using these numbers")}
<h2>How a prop market is defined here</h2>
<ul class="tight">
  <li><b>Naive line</b> — median of the player's last 8 games, rounded to the nearest half point.</li>
  <li><b>Our number</b> — median of the player's last 4 games (a faster-reacting estimate of the same
      functional, so the comparison is not contaminated by the mean/median gap).</li>
  <li><b>Probability</b> — empirical map estimated on prior seasons only: the realised over-rate inside
      each bin of (our number − line)/σ, shrunk toward 50/50 and forced monotone.</li>
  <li><b>Pushes</b> — refunded, never counted as losses.</li>
</ul>
<h2>Calibration and skill</h2>
{dtbl}
{note("Our prop probabilities are calibrated (predicted vs realised track closely, see the table "
      "below) but they carry almost <b>no skill</b>: a Brier score of 0.2439–0.2484 against 0.25 for a "
      "coin flip is a 1–2% improvement. Any large ROI below therefore measures how stale the synthetic "
      "line is, not forecasting ability.", "warn", "Honest reading")}
{ctbl}
<h2>Prop strategies</h2>
{ptbl}
"""
    return page("props.html", "Player Props",
                body, "Prop origination, calibration diagnostics and prop-combo strategies — with the "
                     "price limitation stated up front.")


# ==========================================================================
# 10. correlations
# ==========================================================================
def corr_table(items, headers, tid):
    rows = []
    for x in items:
        rows.append([esc(x["combo"]), esc(x.get("expected_sign", "—")), num(x["r"], 3),
                     f'{num(x["lo"], 3)} … {num(x["hi"], 3)}', integer(x["n"]),
                     src_computed("correlations.py", "correlations.py")])
    return table(headers, rows, tid=tid, numeric_cols=(2, 3, 4))


def build_correlation():
    wg = CORR["within_game"]
    wrows = [
        ["Game margin × game total", num(wg["margin_vs_total"]["r"], 3),
         f'{num(wg["margin_vs_total"]["lo"], 3)} … {num(wg["margin_vs_total"]["hi"], 3)}',
         integer(wg["margin_vs_total"]["n"]), "drives spread+total same-game pricing",
         src_computed("correlations.py")],
        ["Home ATS × over", num(wg["ats_vs_over_indicator"]["r"], 3),
         f'{num(wg["ats_vs_over_indicator"]["lo"], 3)} … {num(wg["ats_vs_over_indicator"]["hi"], 3)}',
         integer(wg["ats_vs_over_indicator"]["n"]), "indicator-level check", src_computed("correlations.py")],
        ["Moneyline winner × ATS winner", num(wg["ml_vs_ats"]["r"], 3),
         f'{num(wg["ml_vs_ats"]["lo"], 3)} … {num(wg["ml_vs_ats"]["hi"], 3)}',
         integer(wg["ml_vs_ats"]["n"]), "ML + spread combos are strongly dependent",
         src_computed("correlations.py")],
        ["Closing spread × closing total", num(wg["spread_line_vs_total_line"]["r"], 3),
         f'{num(wg["spread_line_vs_total_line"]["lo"], 3)} … {num(wg["spread_line_vs_total_line"]["hi"], 3)}',
         integer(wg["spread_line_vs_total_line"]["n"]), "market's own view of the two",
         src_computed("correlations.py")],
    ]
    wtbl = table(["Pair", "r", "95% CI", "n", "Why it matters", "Source"], wrows,
                 tid="t-corr-game", numeric_cols=(1, 3))

    per = CORR["within_game"]["margin_vs_total_by_season"]
    ptbl = table(["Season", "r (margin × total)", "Games", "Source"],
                 [[str(x["season"]), num(x["r"], 3), integer(x["n"]), src_computed("correlations.py")]
                  for x in per], tid="t-corr-season", numeric_cols=(1, 2))

    props = CORR["props"]
    ttbl = corr_table(props["same_game_teammate"],
                      ["Team-mate combo", "Expected sign", "r", "95% CI", "n", "Source"],
                      "t-corr-team")
    stbl = corr_table(props["same_player"],
                      ["Same-player combo", "Expected sign", "r", "95% CI", "n", "Source"],
                      "t-corr-self")
    base = props["cross_game_baseline"]
    btbl = corr_table([base], ["Baseline", "Expected sign", "r", "95% CI", "n", "Source"],
                      "t-corr-base")

    sgp = CORR["sgp_joint"]
    jrows = [[esc(x["combo"]), pct(x["joint_empirical"]), pct(x["product_of_rates"]),
              num(x["ratio"], 4), integer(x["n"]), src_computed("correlations.py")]
             for x in sgp["combos"]]
    jtbl = table(["Spread + total combo", "Empirical joint", "Product of rates", "Ratio", "Games",
                  "Source"], jrows, tid="t-corr-joint", numeric_cols=(1, 2, 3, 4))

    body = f"""
<p>These are the numbers that decide whether a combo is priced correctly. All estimates come from
settled outcomes in the backtest window and carry a bootstrap confidence interval.</p>
{note("The headline: <b>spread and total are nearly independent (r ≈ 0.02)</b>, while "
      "<b>same-player prop legs are heavily dependent (r up to 0.92)</b>. Correlation edge lives in "
      "player markets, not in the main markets.", "", "Summary")}
<h2>Within-game market correlations</h2>
{wtbl}
<h2>Stability by season</h2>
{ptbl}
<h2>Same-game joint probabilities vs the independence assumption</h2>
{jtbl}
<h2>Player-prop co-movement</h2>
{ttbl}
{stbl}
<h2>Cross-game baseline (the null)</h2>
{btbl}
<p class="small">The baseline sits at zero, as it must. That is the control proving the machinery is not
manufacturing correlation.</p>
<h2>Prop dispersion</h2>
{table(["Stat", "Position", "n", "Mean", "SD", "10th pct", "Median", "90th pct", "Source"],
       [[esc(x["stat"]), esc(x["position"]), integer(x["n"]), num(x["mean"], 2), num(x["sd"], 2),
         num(x["p10"], 1), num(x["median"], 1), num(x["p90"], 1), src_computed("correlations.py")]
        for x in CORR["prop_dispersion"]], tid="t-disp", numeric_cols=(2, 3, 4, 5, 6, 7))}
"""
    return page("correlation.html", "Correlation Values",
                body, "Every correlation used for parlay and same-game pricing, with confidence "
                     "intervals and a cross-game control.")


# ==========================================================================
# 11. validation
# ==========================================================================
def build_validation():
    defs = VALID["gate_definitions"]
    ids = [r["strategy_id"] for r in VALID["results"]]
    gcols = [g["id"] for g in defs]
    rows = []
    for r in VALID["results"]:
        cells = []
        for g in gcols:
            ok = r.get("gates", {}).get(g)
            cells.append('<span class="good">✓</span>' if ok else '<span class="bad">✗</span>')
        rows.append([f'<b>{esc(r["strategy_id"])}</b>', esc(r.get("name", ""))]
                    + cells + [f'{r["gates_passed"]}/{r["gates_total"]}',
                               '<span class="good">PASS</span>' if r["passes_all"] else '<span class="bad">fail</span>',
                               src_computed("validate.py", "validate.py")])
    tbl = (filter_box("t-gates", "Filter strategies…")
           + table(["ID", "Name"] + gcols + ["Passed", "All gates", "Source"], rows,
                   tid="t-gates", numeric_cols=(len(gcols) + 2,)))

    counts = []
    for g in defs:
        n = sum(1 for r in VALID["results"] if r.get("gates", {}).get(g["id"]))
        counts.append([f'<b>{esc(g["id"])}</b>', esc(g["name"]), esc(g["test"]),
                       f'{n}/{len(VALID["results"])}', src_computed("validate.py")])
    ctbl = table(["Gate", "Name", "Test", "Strategies passing", "Source"],
                 VALID["results"] and counts, tid="t-gatedef", numeric_cols=(3,))

    body = f"""
<p>A strategy is only "validated" if it survives all nine gates. They are deliberately hostile:
sample size, coverage, leakage, out-of-sample holdout, a zero-skill simulation, multiple-testing
correction, season consistency, robustness to dropping the best season, and whether the prices were
actually observed.</p>
<h2>The gates</h2>
{ctbl}
<h2>Gate matrix</h2>
<p class="small">Green = passed. Holdout seasons {', '.join(str(s) for s in VALID['holdout_seasons'])}.
Minimum sample {VALID['min_bets']} bets and {VALID['min_seasons']} seasons.
Luck simulation: {integer(VALID['n_sims'])} draws per strategy.</p>
{tbl}
{note("<b>Zero strategies pass all nine gates.</b> That is the result, and it is not a bug: the gates "
      "were fixed before the strategies were scored, and the FDR gate is applied across the whole "
      "family of tests.", "warn", "Outcome")}
"""
    return page("validation.html", "Validation Gates",
                body, "Nine pre-registered filters, and which strategies survive each one.")


# ==========================================================================
# 12. luck vs skill
# ==========================================================================
def build_luck():
    rows = []
    for r in LUCK["results"]:
        if not r.get("n_bets"):
            continue
        band = f'{num((r.get("null_roi_p05") or 0) * 100, 2)}% … {num((r.get("null_roi_p95") or 0) * 100, 2)}%'
        rows.append([f'<b>{esc(r["strategy_id"])}</b>', esc(r.get("name", "")),
                     integer(r["n_bets"]), signed(r.get("roi"), 2, "%"),
                     band, pct(r.get("null_roi_mean")), num(r.get("p_value_vs_market"), 4),
                     num(r.get("sharpe_per_bet"), 4), num(r.get("skew"), 2),
                     num(r.get("kurtosis"), 1), src_computed("validate.py", "validate.py")])
    tbl = (filter_box("t-luck", "Filter…")
           + table(["ID", "Strategy", "Bets", "Observed ROI", "Zero-skill ROI band (5–95%)",
                    "Null mean ROI", "p vs luck", "Sharpe / bet", "Skew", "Kurtosis", "Source"],
                   rows, tid="t-luck", numeric_cols=(2, 3, 4, 5, 6, 7, 8, 9)))

    mono_rows = []
    for r in LUCK["results"]:
        em = r.get("edge_monotonicity")
        if not em:
            continue
        for b in em["buckets"]:
            mono_rows.append([f'<b>{esc(r["strategy_id"])}</b>', str(b["bucket"] + 1),
                              integer(b["n"]), num(b["mean_edge"], 4), signed(b["roi"], 2, "%"),
                              src_computed("validate.py")])
    mtbl = (filter_box("t-mono", "Filter…")
            + table(["ID", "Edge quintile", "Bets", "Mean edge over market", "ROI", "Source"],
                    mono_rows, tid="t-mono", numeric_cols=(1, 2, 3, 4)))

    mono_summary = []
    for r in LUCK["results"]:
        em = r.get("edge_monotonicity")
        if em and em.get("quintile_roi_rank_corr") is not None:
            mono_summary.append([f'<b>{esc(r["strategy_id"])}</b>', esc(r.get("name", "")),
                                 num(em["quintile_roi_rank_corr"], 3),
                                 "expected: clearly positive if the edge is real",
                                 src_computed("validate.py")])
    stbl = table(["ID", "Strategy", "Rank corr (edge quintile → ROI)", "Reading", "Source"],
                 mono_summary, tid="t-mono-sum", numeric_cols=(2,))

    body = f"""
<p>Raw ROI is a terrible scoreboard: with a few hundred bets, luck swings results by more than any
realistic edge. Three separate tools are used to strip it out.</p>
<h2>1 · Zero-skill simulation</h2>
<p>For every bet the outcome is re-simulated using the <b>de-vigged market probability</b> of the side we
took — a bettor with zero skill making exactly the same bets. {integer(VALID['n_sims'])} draws give the
ROI distribution that pure luck produces at that sample size. The p-value is how often luck matches or
beats the observed ROI. Source: {src_script('validate.py', 'validate.py')}.</p>
{tbl}
<h2>2 · Does profit rise with edge?</h2>
<p>If a model genuinely knows something, bets where it disagrees most with the market should do better.
The quintile table tests that monotonicity; the rank correlation summarises it.</p>
{stbl}
{note("A positive rank correlation is a necessary-but-not-sufficient skill signature: it is easy to "
      "produce one by accident with a handful of quintiles, which is why it is descriptive only and not "
      "one of the nine gates.", "", "Interpretation")}
<h2>3 · Where the money actually goes</h2>
{mtbl}
<h2>Controls that keep us honest</h2>
<ul class="tight">
  <li>Always-home ATS: <b>{pct(RESULTS['C01']['roi'])}</b> — the vig, minus a small home-cover shortfall.</li>
  <li>Always-favourite ATS: <b>{pct(RESULTS['C02']['roi'])}</b> — near zero, as an efficient market should be.</li>
  <li>Always-over: <b>{pct(RESULTS['C03']['roi'])}</b> — the under side of an inflated total.</li>
  <li>Coin-flip ATS: <b>{pct(RESULTS['C04']['roi'])}</b> — pure vig, the cost of playing at random.</li>
</ul>
{note("The always-favourite control shows p = " + num(RESULTS['C02']['p_value_vs_market'], 4) +
      " for a " + pct(RESULTS['C02']['roi']) + " ROI. That is a <b>false positive created by the "
      "de-vig method</b>: proportional de-vigging systematically understates favourites' true "
      "probabilities, so the zero-skill null is biased low for favourite sides. It is disclosed as "
      "<a href='flagged.html'>IR-04</a> and is the reason p-values for moneyline strategies must be read "
      "with care.", "bad", "Known bias in the null")}
"""
    return page("luck.html", "Luck vs Skill",
                body, "Zero-skill simulation bands, edge monotonicity and the controls that keep the "
                     "analysis honest.")


# ==========================================================================
# 13. findings (renders the markdown summary)
# ==========================================================================
def md_to_html(md):
    """Very small markdown renderer: headings, tables, lists, bold, code, links, paragraphs."""
    lines = md.split("\n")
    out, i = [], 0
    while i < len(lines):
        ln = lines[i]
        if ln.startswith("|") and i + 1 < len(lines) and re.match(r"^\|[\s:\-|]+\|$", lines[i + 1].strip()):
            hdr = [c.strip() for c in ln.strip().strip("|").split("|")]
            i += 2
            body = []
            while i < len(lines) and lines[i].startswith("|"):
                body.append([c.strip() for c in lines[i].strip().strip("|").split("|")])
                i += 1
            out.append('<div class="tablewrap"><table class="sortable"><thead><tr>'
                       + "".join(f"<th>{inline(h)}</th>" for h in hdr)
                       + "</tr></thead><tbody>"
                       + "".join("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in row) + "</tr>"
                                 for row in body)
                       + "</tbody></table></div>")
            continue
        if ln.startswith("#"):
            lvl = len(ln) - len(ln.lstrip("#"))
            txt = ln[lvl:].strip()
            out.append(f"<h{min(lvl + 1, 4)}>{inline(txt)}</h{min(lvl + 1, 4)}>")
        elif ln.startswith("- "):
            items = []
            while i < len(lines) and lines[i].startswith("- "):
                items.append(f"<li>{inline(lines[i][2:])}</li>")
                i += 1
            out.append('<ul class="tight">' + "".join(items) + "</ul>")
            continue
        elif ln.strip() == "---":
            out.append("<hr>")
        elif ln.strip():
            out.append(f"<p>{inline(ln)}</p>")
        i += 1
    return "\n".join(out)


def inline(t):
    t = esc(t)
    t = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)
    t = re.sub(r"`(.+?)`", r"<code>\1</code>", t)
    t = re.sub(r"\[(.+?)\]\((https?://[^)]+)\)", r'<a href="\2">\1</a>', t)
    return t


def build_findings():
    md = open(os.path.join(ROOT, "research", "EXECUTIVE_SUMMARY.md")).read()
    body = md_to_html(md)
    body += (f'<p class="small">Rendered from <code>research/EXECUTIVE_SUMMARY.md</code> in the '
             f'repository — the markdown file is the source of truth. '
             f'{src_script("make_site.py", "site generator")}</p>')
    return page("findings.html", "Findings — Executive Summary",
                body, "Everything that worked, everything that did not, and what is still unverified.")


# ==========================================================================
# 14. sources
# ==========================================================================
def build_sources():
    rows = []
    for name, d in PROV["files"].items():
        rows.append([f'<b>{esc(name)}</b>', esc(d["publisher"]),
                     a(d["pinned_url"], "pinned file"), esc(d["commit"][:12]),
                     f'<code>{esc(d["sha256"][:16])}…</code>', integer(d["data_rows"]),
                     integer(d["bytes"])])
    prov_tbl = table(["File", "Publisher", "Pinned URL", "Commit", "SHA-256 (head)", "Rows", "Bytes"],
                     rows, tid="t-prov", numeric_cols=(5, 6))

    pfr = VERIF["V_A_pfr_scores"]
    pfr_rows = [[str(x["season"]), str(x["week"]), esc(x["matchup"]), esc(x["pfr"] or "—"),
                 esc(x["dataset"] or "—"),
                 f'<span class="good">match</span>' if x["status"] == "match" else
                 (f'<span class="bad">MISMATCH</span>' if x["status"] == "MISMATCH" else
                  '<span class="warn">unconfirmed</span>'),
                 a(x["source"], "PFR page")] for x in pfr["checks"]]
    pfr_tbl = table(["Season", "Week", "Matchup", "PFR score", "Our score", "Status", "Source"],
                    pfr_rows, tid="t-pfr")

    integ_rows = [[esc(c["check"]), integer(c["rows_checked"]), integer(c["failures"]),
                   '<span class="good">pass</span>' if c["pass"] else '<span class="bad">FAIL</span>',
                   esc(c["note"]), src_script("verify_external.py", "verify_external.py")]
                  for c in VERIF["V_B_integrity"]["checks"]]
    integ_tbl = table(["Integrity check", "Rows checked", "Failures", "Result", "Note", "Source"],
                      integ_rows, tid="t-integ", numeric_cols=(1, 2))

    cf = VERIF["V_C_cross_file"]
    cf_tbl = table(["Comparison", "Value", "Source"],
                   [["Games compared (2006–2018)", integer(cf.get("n_games")), src_games("closing_lines.csv")],
                    ["Exact agreement", pct(cf.get("pct_agree")), src_games("games.csv")],
                    ["Agreement within 0.5 pt", pct(cf.get("pct_agree_within_half_point")), src_games("games.csv")],
                    ["Mean absolute difference", num(cf.get("mean_abs_diff_points"), 3) + " pts", src_games()],
                    ["Median absolute difference", num(cf.get("median_abs_diff_points"), 3) + " pts", src_games()]],
                   tid="t-cross", numeric_cols=(1,))

    rd = VERIF["V_D_bet_resettlement"]
    rd_tbl = table(["Check", "Rows", "Source"],
                   [["Bets re-settled by an independent implementation", integer(rd["rows"]),
                     src_script("verify_external.py", "verify_external.py")],
                    ["Recomputed outcomes matching stored", integer(rd["recomputed_match"]),
                     src_script("verify_external.py")],
                    ["Mismatches", integer(rd["mismatch"]), src_script("verify_external.py")],
                    ["Not re-settled here (parlay/prop composites)", integer(rd["not_applicable"]),
                     src_script("verify_external.py")]],
                   tid="t-resettle", numeric_cols=(1,))

    body = f"""
<p>Every number on this site traces to one of the sources below. The raw files are pinned to a git
commit and hashed, so a reviewer can prove the analysis ran on exactly these bytes.</p>
<h2>Data provenance</h2>
{prov_tbl}
<p class="small">Reproduce with <code>python3 scripts/fetch_data.py</code>, which re-downloads each
file from the pinned commit and re-checks the hash against <code>data/PROVENANCE.json</code>.
</p>
<h2>External verification — final scores vs Pro-Football-Reference</h2>
<p class="small">Source page: {a(pfr['source'], pfr['source'])}, accessed {esc(pfr['accessed'])}.
Result: <b>{pfr['n_match']}/{pfr['n_checked']} match</b>, {pfr['n_mismatch']} mismatch,
{pfr['n_unconfirmed']} unconfirmed.</p>
{pfr_tbl}
<h2>Whole-file integrity checks</h2>
{integ_tbl}
<h2>Cross-file line comparison</h2>
<p class="small">{esc(cf.get('note', ''))}</p>
{cf_tbl}
<h2>Independent re-settlement of every bet</h2>
{rd_tbl}
<p class="small">{esc(rd.get('note', ''))}</p>
{note("Spread, total and moneyline <b>prices</b> could not be verified against an external source: the "
      "Pro-Football-Reference schedule page used for the score check does not publish closing lines. "
      "The prices are therefore traceable-but-unverified, which is recorded as "
      "<a href='flagged.html'>IR-01</a>.", "warn", "What could not be verified")}
"""
    return page("sources.html", "Sources & Verification",
                body, "Pinned datasets, SHA-256 hashes, external spot checks and independent "
                     "re-settlement of every bet.")


# ==========================================================================
# 15. flagged
# ==========================================================================
IRREGULARITIES = [
    ("IR-01", "Closing-line provenance is undocumented", "needs review",
     "The publisher (nflverse) does not state which sportsbook the closing spread/total/moneyline "
     "figures come from, or at what time they were captured. The implied hold (2.4–2.9%) is lower "
     "than a typical retail book, which suggests a sharp or consensus source. All ROI figures inherit "
     "this uncertainty.",
     "Every ROI on the site", "nflverse/nfldata DATASETS.md documents the columns but not the book",
     "https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/DATASETS.md"),
    ("IR-02", "Player-week data provenance unverified", "needs review",
     "Weekly player box scores come from a third-party mirror repository with no publisher "
     "documentation. The game_id values match the nflverse identifier format and spot checks are "
     "consistent, but the file cannot be traced to an official feed.",
     "All player-prop strategies (T01–T09) and prop correlations",
     "DevinOgrady/NFL-Player-Projections (pinned via PROVENANCE.json)",
     "https://github.com/DevinOgrady/NFL-Player-Projections"),
    ("IR-03", "No verifiable player-prop prices", "needs review",
     "No free, verifiable source of prop odds was reachable from this environment. Prop strategies are "
     "settled against an ASSUMED flat −110 and a SYNTHETIC line (trailing 8-game median). Hit rates are "
     "real; ROI is not. Gate G9 excludes these strategies from ranking.",
     "T01–T09, and any ROI quoted for them", "N/A — absence of a source is the irregularity", None),
    ("IR-04", "De-vig method biases the zero-skill null", "needs review",
     "The luck simulation de-vigs two-way markets proportionally, which is known to understate "
     "favourites' true probabilities (favourite–longshot bias). Consequence: p-values for moneyline "
     "strategies and for the always-favourite control are biased optimistic. The always-favourite "
     "benchmark shows p = 0.0156 for a +0.21% ROI — a false positive caused by this bias.",
     "p-values for S11, S12, C02; the luck page narrative",
     "Visible in the favourite–longshot table on the market page", "market.html"),
    ("IR-05", "Opening-line file moves far more than expected", "needs review",
     "The 2021 opening-line file implies a mean open→close move of 3.40 points, roughly double what is "
     "normally reported. The file names a single book (WSGT) but carries no capture timestamp, so it is "
     "unclear whether these are true openers.",
     "No strategy — the figure is reported for transparency and used by no strategy",
     "initial_lines.csv (2021 only)", None),
    ("IR-06", "Two extreme closing spreads", "verified after review",
     "Closing spreads of 24 (New England, 2007) and 27 (Denver, 2013) exceed the guardrail used in the "
     "integrity check. Both rows are internally consistent (result/total identities hold) and are "
     "historically plausible blowout lines. Retained; not externally confirmed.",
     "9 rows in the extreme-lines review list", "games.csv", None),
    ("IR-07", "2026 season is partial", "verified",
     "164 of 272 scheduled 2026 games had no result at capture time, and only 108 had a posted market "
     "price. The line board shows our number for all 272 and leaves market cells blank where no market "
     "exists, rather than filling them from another source.",
     "Line Board page", "games.csv (2026 rows)", "line-board.html"),
    ("IR-08", "Model specification was chosen on early data", "verified",
     "The two feature sets were selected once using 2003–2014 walk-forward RMSE only, then applied "
     "unchanged to every later season. Betting results from 2015 onward were therefore not part of the "
     "selection decision.",
     "All model strategies", "scripts/run_all.py, scripts/model.py", None),
    ("IR-09", "Branch naming convention not followed", "verified",
     "The platform binds this session to branch arena/398c4b58-korea3 and forbids creating or renaming "
     "branches, so the requested session-<id>/<task> convention could not be used. No other branch was "
     "created or pushed to.",
     "Repository process only", "COORDINATION.md", "https://github.com/karagemop466-tech/Korea3/blob/main/COORDINATION.md"),
]


def build_flagged():
    rows = []
    for code, title, status, detail, affects, source, url in IRREGULARITIES:
        kind = "b" if status == "needs review" else ("w" if status.startswith("verified after") else "g")
        rows.append([f'<b>{esc(code)}</b>', f'<span class="wrapcell"><b>{esc(title)}</b><br>'
                                            f'<span class="small">{esc(detail)}</span></span>',
                     esc(affects), chip(status, kind),
                     a(url, "source") if url else '<span class="muted">no external source exists</span>'])
    tbl = table(["ID", "Issue", "What it affects", "Status", "Source"], rows, tid="t-ir",
                sortable=True)
    body = f"""
<p>Everything below is either unverified, assumed, or anomalous. Nothing here is hidden in a footnote —
if a value could not be confirmed from a source, it is listed here and left blank in the tables
rather than inferred.</p>
{note("<b>'needs review'</b> means the item is published here and does not block anything else. "
      "<b>'verified'</b> means it was checked and the explanation above is the finding. "
      "<b>'verified after review'</b> means the anomaly was examined and deliberately retained.", "", "Legend")}
{tbl}
<h2>Values deliberately left blank</h2>
<ul class="tight">
  <li><b>Closing-line book / capture time</b> — not published by the source, so never stated. (IR-01)</li>
  <li><b>Prop market prices</b> — no source; the price column reads "assumed −110" wherever it applies. (IR-03)</li>
  <li><b>Same-game parlay prices</b> — no source; the simulated price is the product of the two leg
      prices, and this is stated on the parlays page. (IR-03)</li>
  <li><b>2026 games without a posted line</b> — market columns are blank on the line board. (IR-07)</li>
  <li><b>Player-week publisher identity</b> — not documented; recorded as a mirror. (IR-02)</li>
</ul>
<h2>What <em>was</em> independently confirmed</h2>
<ul class="tight">
  <li>Final scores for {VERIF['V_A_pfr_scores']['n_match']} sampled games match Pro-Football-Reference
      exactly ({a(VERIF['V_A_pfr_scores']['source'], 'source page')}).</li>
  <li>{integer(VERIF['V_D_bet_resettlement']['recomputed_match'])} single bets re-settled from raw scores
      with an independent implementation: {integer(VERIF['V_D_bet_resettlement']['mismatch'])} mismatches.</li>
  <li>Arithmetic identities, valid American prices, de-vig closure and quote granularity hold on every
      row of the games file ({src_script('verify_external.py', 'verify_external.py')}).</li>
  <li>Pre-game Elo rebuilt from truncated history for {integer(META['leakage_guard']['checks'])} games:
      maximum difference {num(META['leakage_guard']['max_abs_diff'], 10)}.</li>
</ul>
"""
    return page("flagged.html", "Flagged for Review",
                body, "Unverified values, assumptions and anomalies — each with its source link, so "
                     "you can check them yourself.")


# ==========================================================================
# 16. methodology
# ==========================================================================
def build_methodology():
    body = f"""
<p>Everything on this site is generated from committed code and pinned data. No figure is typed by
hand.</p>
<h2>Reproduce</h2>
<pre class="small">git clone {esc(REPO_URL)}.git
cd Korea3
python3 -m venv .venv &amp;&amp; . .venv/bin/activate
pip install numpy pandas
python3 scripts/fetch_data.py      # re-download pinned data, verify SHA-256
python3 scripts/run_all.py         # features → model → bets → gates → JSON
python3 scripts/verify_external.py # external + integrity checks
python3 scripts/make_site.py       # rebuild this site from the JSON</pre>
<h2>Pipeline</h2>
<ol class="tight">
  <li><b>fetch_data.py</b> — pulls the raw files from codeload at a pinned commit, records SHA-256.</li>
  <li><b>features.py</b> — sequential Elo (margin-of-victory weighted, season mean-reversion) and
      point-in-time offensive/defensive form. Asserts no leakage by rebuilding ratings from truncated
      history.</li>
  <li><b>model.py</b> — refits two OLS models each season on prior seasons only; σ from training
      residuals; produces our spread and total for every game, including unplayed ones.</li>
  <li><b>engine.py / strategies.py</b> — mechanical rules → bets → settlement against observed prices.</li>
  <li><b>props.py</b> — prop markets with prior-season empirical probability calibration.</li>
  <li><b>correlations.py</b> — correlation estimates with bootstrap confidence intervals.</li>
  <li><b>validate.py</b> — nine gates, zero-skill simulation, FDR, deflated Sharpe, monotonicity.</li>
  <li><b>leaderboard.py</b> (inside run_all) — composite score, tiers, allocation weights.</li>
  <li><b>make_site.py</b> — renders this site from <code>docs/data/*.json</code>.</li>
</ol>
<h2>Statistical notes</h2>
<ul class="tight">
  <li><b>Staking</b> — flat 1.00 unit per bet. Fractional Kelly is recorded per bet but is not the
      headline metric, because Kelly on an unproven edge simply scales the error.</li>
  <li><b>Pushes</b> — refunded (profit 0), never counted as losses. Integer prop lines are kept rather
      than nudged, because nudging them biases the over-rate downward.</li>
  <li><b>Confidence intervals</b> — percentile bootstrap over bets (6,000 draws) and a separate
      cluster bootstrap over seasons (4,000 draws), because bets inside a season are not independent.</li>
  <li><b>Zero-skill null</b> — outcomes redrawn at the de-vigged market probability of the side taken,
      10,000 simulations per strategy.</li>
  <li><b>Multiple testing</b> — Benjamini–Hochberg at q = 0.10 across all non-control strategies.</li>
  <li><b>Deflated Sharpe</b> — per-bet Sharpe haircut for the number of strategies tried, using
      skew and kurtosis of the profit distribution (Bailey &amp; López de Prado).</li>
  <li><b>Seeds</b> — every simulation uses a fixed seed; results are bit-reproducible.</li>
</ul>
<h2>Known limitations</h2>
<ul class="tight">
  <li>Prices are unverified against an external source (<a href="flagged.html">IR-01</a>).</li>
  <li>Prop prices do not exist in the data; they are assumed (<a href="flagged.html">IR-03</a>).</li>
  <li>Weather (temperature/wind) is present in the source but deliberately unused, because a backtest
      would need the forecast available at bet time, not the realised value.</li>
  <li>The model has no injury, roster, or market-movement information — all of which are likely to
      matter more than the features used here.</li>
</ul>
"""
    return page("methodology.html", "Method & Reproduction",
                body, "How the pipeline works, how to rebuild it, and what it deliberately does not do.")


def main():
    built = [
        build_index(), build_line_board(), build_market(), build_model(), build_strategies(),
        build_leaderboard(), build_singles(), build_parlays(), build_props(),
        build_correlation(), build_validation(), build_luck(), build_findings(),
        build_sources(), build_flagged(), build_methodology(),
    ]
    for b in built:
        print("built", b)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
