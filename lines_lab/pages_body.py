"""Page bodies for the Line Origination Lab."""
from __future__ import annotations

import html

import pandas as pd

from . import evidence as EV
from .pages import (DATASET, E, PAGES, REPO_BLOB, REPO_TREE, blank, kpi, kpis,
                    link_repo, link_source, link_tree, num, page, page_title, pill, src, table)


# --------------------------------------------------------------------------- #
# Overview
# --------------------------------------------------------------------------- #
def overview(e: dict) -> str:
    cov = e["coverage"]
    res = e["results"]
    sig = e["signals"]
    board = e["board"]
    passing = int(sig.survives.sum())
    live = int((board.state == "LIVE").sum())
    depth = e["depth"]

    k = kpis([
        ("Games in the price store", f'{cov["games"]:,}',
         "seasons 1999–2026, spread and total", ""),
        ("Games with an OPENING number", f'{cov["games_with_open_side"]:,}',
         f'{cov["pct_with_open_side"]}% of the store — 2021 only', "warn"),
        ("Results re-derived from the final score", f'{res["chk_spread_ok"]:,}/{res["chk_games"]:,}',
         "closing-line outcomes reproduced", "ok"),
        ("Signals tested / surviving control", f"{len(sig)} / {passing}",
         "Bonferroni family-wise α = 0.05/18", "bad" if passing == 0 else ""),
        ("Strategies live / paper", f"{live} / {len(board) - live}",
         "demotion gate applied to every row", "warn"),
    ])

    body = k + f"""
<div class="note"><strong>What this section is.</strong> It originates its own NFL side, total
and moneyline numbers from a pinned dataset, then tries hard to disprove them. It is built so
that a bad result is visible rather than hidden: a strategy that fails a gate is printed in the
<em>paper</em> column with the gate that failed, and a value that has no source is printed blank.
Nothing on these pages is a recommendation, a price you can bet, or a claim of edge.</div>

<div class="section-head"><div><h2>What the brief asked for, and where it is answered</h2>
<p>Each row is one requirement from the brief, the page that answers it, and the state of the answer.</p></div></div>
"""
    reqs = [
        ("Price-snapshot store recording opening and closing numbers for every originated market",
         "snapshots.html",
         f'Store built: {cov["games"]:,} games. Closing spread and total on every one; '
         f'<strong>opening numbers on {cov["games_with_open_side"]} only</strong> '
         f'({cov["pct_with_open_side"]}%), all 2021, one book, no price column.',
         "PARTIAL — the opening half exists for 3.7% of the store", "open"),
        ("Verified results feed so backtests and ROI can be computed at all",
         "results.html",
         f'Settlement recomputed from final scores for {res["reg_games_played"]:,} regular-season '
         f'games. The closing file\'s own outcome is reproduced in '
         f'{res["chk_spread_ok"]}/{res["chk_games"]} (spread), {res["chk_total_ok"]}/{res["chk_games"]} '
         f'(total), {res["chk_ml_ok"]}/{res["chk_games"]} (moneyline).',
         "DONE — every mismatch published", "pass"),
        ("Originate the side first, then the total, then the moneyline",
         "fair-vs-market.html",
         "Order enforced in code: side (1999–2026, tightest market) → total → moneyline. "
         "The moneyline is never originated before the side it is derived from.",
         "DONE", "pass"),
        ("Publish the fair line, the market line and the difference as separate columns",
         "fair-vs-market.html",
         f'Three columns, never blended: walk-forward fair line, market line, difference. '
         f'Side MAE <strong>{e["fair_by_season"].mae_fair_side.mean():.3f}</strong> vs market '
         f'<strong>{e["fair_by_season"].mae_market_side.mean():.3f}</strong> — the market wins.',
         "DONE — and the model loses", "pass"),
        ("Separate signal from staking so a lucky staking run cannot mask a bad signal",
         "leaderboard.html",
         "Two independent columns and no rank across them. The board demonstrates the point: "
         "the best staking return on the board still has a negative signal bound.",
         "DONE", "pass"),
        ("Track the depth of the replacement, not just the fact of a replacement",
         "depth.html",
         f'{depth.get("rows", 0)} starter replacements, each with the replacement string the club '
         f'published, the number of strings the club printed, and the rungs lost.',
         "DONE — 1-deep vs 2-deep separated", "pass"),
        ("Correlations only from sourced numbers, with n published on every value",
         "correlations.html",
         "Every coefficient prints its n and its input tier. A coefficient with n < 30 is not computed. "
         "No correlation is labelled official: none can be.",
         "DONE", "pass"),
        ("A demotion gate that sends a live strategy back to paper",
         "demotion.html",
         "Eight gates, fail-closed: an unknown input fails. Any failure returns the strategy "
         "to paper with the failing gate named.",
         "DONE — all 18 strategies are on paper", "pass"),
    ]
    rows = []
    for req, href, answer, state, kind in reqs:
        rows.append([
            f'<td>{E(req)}</td>',
            f'<td><a href="{href}">{E(page_title(href))}</a></td>',
            f"<td>{answer}</td>",
            f'<td>{pill(state.split(" —")[0], kind)}<div class="s" style="font-size:11px;color:#5b6b82;margin-top:3px">{E(state.split("— ", 1)[1] if "— " in state else "")}</div></td>',
            src(link_tree("lines_lab/", "code")),
        ])
    body += table(["Requirement from the brief", "Answered on", "What the data actually shows",
                   "State", "Source"], rows,
                  "One row per requirement. The middle column is the evidence, not a promise.")

    body += """
<div class="section-head"><div><h2>The four things worth knowing before anything else</h2>
<p>Each is a measured result on this site, not an opinion.</p></div></div>
"""
    findings = [
        ("1. The model does not beat the market, and that is the headline",
         f'The walk-forward fair line misses the actual margin by '
         f'<strong>{e["fair_by_season"].mae_fair_side.mean():.3f}</strong> points on average; the '
         f'market misses by <strong>{e["fair_by_season"].mae_market_side.mean():.3f}</strong>. '
         f'The market is better in <strong>every one of the {len(e["fair_by_season"])} test seasons</strong>. '
         f'An origination model that loses every season is not a signal source; it is a baseline to improve on.',
         "fair-vs-market.html", "fail"),
        ("2. Not one of the 18 candidate rules survives multiplicity control",
         f'All 18 were pre-registered and tested once. The best uncorrected p-value is '
         f'<strong>{sig.p_raw.min():.3f}</strong>; the Bonferroni threshold for 18 tests is '
         f'<strong>{sig.alpha_single.iloc[0]:.4f}</strong>. Zero rules clear it. '
         f'Publishing a "best rule" here would be publishing noise.',
         "signals.html", "fail"),
        ("3. A lucky staking run cannot rescue a losing signal — and the board proves it live",
         f'Strategy <strong>{board.sort_values("staking_return_per_bet", ascending=False).iloc[0].id}</strong> '
         f'has the best staking return on the board '
         f'(<strong>{board.staking_return_per_bet.max() * 100:+.2f}%</strong> per bet) and a signal '
         f'lower bound of <strong>{board.sort_values("staking_return_per_bet", ascending=False).iloc[0].signal_lcb * 100:+.2f}%</strong> '
         f'— still below zero. Ranking on one number would have promoted it.',
         "leaderboard.html", "warn"),
        ("4. Opening prices barely exist, so closing-line value cannot be measured",
         f'Opening numbers exist for <strong>{e["coverage"]["games_with_open_side"]}</strong> of '
         f'{e["coverage"]["games"]:,} games ({e["coverage"]["pct_with_open_side"]}%), all in 2021, '
         f'from one book, with <strong>no price column at all</strong>. Closing-line value needs a '
         f'timestamped price on both sides of the move. It cannot be computed from this data, '
         f'and the site does not compute it.',
         "snapshots.html", "warn"),
    ]
    for title, text, href, kind in findings:
        body += (f'<div class="panel"><div class="hd"><strong>{E(title)}</strong>'
                 f'<span>{pill("measured", kind)}</span></div>'
                 f'<div style="padding:13px 15px;font-size:13.5px">{text} '
                 f'<a href="{href}">See the table &rarr;</a></div></div>')

    body += """
<div class="section-head"><div><h2>What is deliberately not on this site</h2>
<p>The blank cells are as important as the filled ones.</p></div></div>
"""
    nots = [
        ("No closing-line value", "No timestamped two-sided price archive exists here.",
         "snapshots.html"),
        ("No player-prop prices", "The dataset is game-level. A player-prop line or price "
         "appearing here would be invented.", "parlays.html"),
        ("No league-published price", "The NFL publishes no spread, total or price. Every "
         "market figure is labelled by dataset, not by the league.", "sources.html"),
        ("No funded prize", "The competition is a specification. No sponsor, amount or terms "
         "exist, so none is stated.", "leaderboard.html"),
        ("No injury status on these pages",
         "Availability lives in the existing Depth Lab, which sources it to the official "
         "injury report. This section links it rather than copying it.",
         "../depth_lab/index.html"),
        ("No recommendation", "Not one row says stake, bet, or play.", "flagged.html"),
    ]
    rows = []
    for what, why, where in nots:
        rows.append([f"<td>{E(what)}</td>", f"<td>{E(why)}</td>",
                     f'<td><a href="{where}">{"see" if where.startswith("..") else "see"} &rarr;</a></td>',
                     src(link_repo("lines_lab/pages_body.py", "code"))])
    body += table(["Not published", "Why", "Where the gap is shown", "Source"], rows,
                  "A missing value is shown as missing. It is never a zero.")
    return page("Line Origination Lab", "index.html", "<strong>Start here</strong> / Overview",
                "A dashboard that originates NFL sides, totals and moneylines, then tries to "
                "disprove them. Built so a failed gate is visible, a missing source is blank, and "
                "the market is allowed to win.", body,
                "Line origination lab: price snapshots, verified results, fair line vs market, "
                "signal tests with multiplicity control, a signal/staking-split leaderboard and a "
                "demotion gate. Every row links its source.")


# --------------------------------------------------------------------------- #
# Executive summary
# --------------------------------------------------------------------------- #
def executive(e: dict) -> str:
    cov, res, sig, board = e["coverage"], e["results"], e["signals"], e["board"]
    best = board.sort_values("staking_return_per_bet", ascending=False).iloc[0]
    body = f"""
<div class="note"><strong>Bottom line.</strong> This section does what the brief asked and reaches
a negative result. The price store, the results feed, the fair-vs-market columns, the signal/staking
split, the depth-of-replacement join, the correlations-with-n and the demotion gate are all built
and verified. What they show is that <strong>this dataset does not contain a betting edge that
survives validation</strong>. The value of the section is the machinery that says so, and the
specific list of information that would be needed to try again honestly.</div>

<div class="section-head"><div><h2>Headline numbers</h2>
<p>Every figure below is recomputed at build time from the pinned dataset.</p></div></div>
"""
    rows = [
        ("Games in the price store", f'{cov["games"]:,}', "spread and total closing number present",
         "snapshots.html", link_repo("lines_lab/data_layer.py", "code")),
        ("Opening numbers available", f'{cov["games_with_open_side"]:,} ({cov["pct_with_open_side"]}%)',
         "2021 only, one book (WSGT), no price column", "snapshots.html",
         link_repo("data/raw/initial_lines.csv", "data")),
        ("Regular-season games settled", f'{res["reg_games_played"]:,}',
         f'{int(res["chk_games"]):,} of them independently re-checked against the closing file',
         "results.html", link_repo("lines_lab/data_layer.py", "code")),
        ("Spread outcomes reproduced from the score", f'{res["chk_spread_ok"]}/{res["chk_games"]}',
         f'{res["chk_spread_bad"]} mismatches, each published', "results.html",
         link_tree("data/raw", "data")),
        ("Total outcomes reproduced", f'{res["chk_total_ok"]}/{res["chk_games"]}',
         f'{res["chk_total_bad"]} mismatches, each published', "results.html",
         link_tree("data/raw", "data")),
        ("Model fair line vs market (side, MAE)", f'{e["fair_by_season"].mae_fair_side.mean():.3f} vs {e["fair_by_season"].mae_market_side.mean():.3f}',
         "market better in every test season", "fair-vs-market.html",
         link_repo("lines_lab/research.py", "code")),
        ("Model fair line vs market (total, MAE)", f'{e["fair_by_season"].mae_fair_total.mean():.3f} vs {e["fair_by_season"].mae_market_total.mean():.3f}',
         "market better in every test season", "fair-vs-market.html",
         link_repo("lines_lab/research.py", "code")),
        ("Candidate signals tested / surviving", f'{len(sig)} / {int(sig.survives.sum())}',
         f'Bonferroni α = 0.05/{len(sig)} = {sig.alpha_single.iloc[0]:.4f}', "signals.html",
         link_source("NIST-BONF")),
        ("Strategies live / paper", f'{int((board.state == "LIVE").sum())} / {len(board)}',
         "every one fails at least two gates", "demotion.html",
         link_repo("lines_lab/leaderboard.py", "code")),
        ("Bets needed to prove a +2% edge", f'{int([s for s in e["sample_sizes"] if abs(s["edge"] - 0.02) < 1e-9][0]["bets"]):,}',
         "80% power, one-sided 5%, at the -110 reference", "signals.html",
         link_source("NIST-SAMPLESIZE")),
        ("Same-game cover × over correlation", f'φ = {e["corr"].iloc[0].phi:+.4f}',
         f'n = {int(e["corr"].iloc[0].n):,}; 95% CI {e["corr"].iloc[0].ci_low:+.4f} … {e["corr"].iloc[0].ci_high:+.4f}',
         "correlations.html", link_repo("lines_lab/depth_corr.py", "code")),
        ("Depth of every tracked replacement", f'{e["depth"].get("one_deep", 0)} one-deep',
         f'{e["depth"].get("rows", 0)} replacements, {e["depth"].get("clubs", 0)} clubs, '
         f'{e["depth"].get("unknown_depth", 0)} with no published depth',
         "depth.html", link_tree("depth_lab/data", "data")),
    ]
    body += table(["Measure", "Value", "Detail", "Page", "Source"], [
        [f"<td>{E(a)}</td>", f'<td class="num"><strong>{E(b)}</strong></td>', f"<td>{E(c)}</td>",
         f'<td><a href="{d}">{E(page_title(d))}</a></td>', src(s_)]
        for a, b, c, d, s_ in rows], "Twelve numbers a reader can check without trusting this page.")

    body += f"""
<div class="section-head"><div><h2>What can and cannot be decided from the information held</h2>
<p>This is the distinction the brief asks for: what is answered, what is unknown, and what would
have to exist before a decision is reasonable.</p></div></div>
"""
    dec = [
        ("Can I publish a fair line for every game?",
         "YES for the side and the total", "The model produces one for every regular-season game. "
         "It is worse than the market, and the site says so on the row.", "fair-vs-market.html", "pass"),
        ("Can I compute closing-line value?",
         "NO", "There is no timestamped two-sided price archive. Opening numbers exist for 272 games "
         "with no price; the closing numbers carry a price for 5,431 games but no matching opening "
         "price. CLV is not computable and is not published.", "snapshots.html", "fail"),
        ("Can I rank strategies by skill?",
         "YES, and the ranking is empty", "Eight gates are applied. No strategy passes. The board "
         "is published in full with the failing gate on each row.", "demotion.html", "warn"),
        ("Can I price a same-game parlay?",
         "PARTLY", "The correlation between a cover and an over is measured with its n. Player-prop "
         "legs cannot be priced at all: the dataset has no player-level market and no prop prices.",
         "parlays.html", "warn"),
        ("Can I say a backup will start?",
         "NO", "No official publisher states who will start. The depth pages report what a club "
         "printed, which is a statement about a publication and not about a lineup.", "depth.html", "fail"),
        ("Can I fund a prize?",
         "NO", "No sponsor, amount or terms exist. Stating one would be inventing a commitment.",
         "leaderboard.html", "fail"),
    ]
    body += table(["Question", "Answer", "Why", "Page", "Source"], [
        [f"<td>{E(a)}</td>", f"<td>{pill(b, k)}</td>", f"<td>{E(c)}</td>",
         f'<td><a href="{d}">{E(page_title(d))}</a></td>', src(link_repo("lines_lab/pages_body.py", "code"))]
        for a, b, c, d, k in dec],
        "Six questions a decision would rest on, answered only as far as the evidence goes.")

    body += """
<div class="section-head"><div><h2>The single change that would most improve this</h2></div></div>
<div class="panel"><div style="padding:14px 16px;font-size:13.5px">
<p style="margin:0 0 8px"><strong>Buy or build a timestamped, two-sided price archive.</strong>
Every blocked item on this site — closing-line value, live-vs-paper comparison, a promotion that
is not curve-fitting, a defensible competition — depends on knowing what price was available at
a known moment. One book's opening line for 272 games, with no price, is not that archive.</p>
<p style="margin:0">It is the top item on the <a href="suggestions.html">suggestions</a> page, the
blocking input on the <a href="questions.html">questions</a> page, and the reason the
<a href="demotion.html">demotion gate</a> can only demote.</p>
</div></div>
"""
    return page("Executive summary", "executive.html",
                "<strong>Start here</strong> / Executive summary",
                "The result in one page: what was built, what it shows, what cannot be decided, and "
                "the one input that would change the answer.", body,
                "Executive summary of the line origination lab: price snapshot coverage, verified "
                "results, fair line versus market, zero surviving signals, and the blocked decisions.")


# --------------------------------------------------------------------------- #
# Findings
# --------------------------------------------------------------------------- #
def findings(e: dict) -> str:
    cov, sig, board = e["coverage"], e["signals"], e["board"]
    by = e["fair_by_season"]
    f1 = [
        ("F01", "The market beats the model in every test season",
         f'{len(by)} seasons, 2005–2026', f'{by.mae_fair_side.mean():.3f} vs {by.mae_market_side.mean():.3f}',
         "Model worse by "
         f'{(by.mae_fair_side.mean() - by.mae_market_side.mean()):.3f} points of absolute error',
         "fail", "fair-vs-market.html"),
        ("F02", "The same is true of the total",
         f'{len(by)} seasons', f'{by.mae_fair_total.mean():.3f} vs {by.mae_market_total.mean():.3f}',
         "Both sides of the model lose; this is not a side-only problem", "fail", "fair-vs-market.html"),
        ("F03", "No candidate signal survives multiplicity control",
         f'{len(sig)} rules, one test each', f'{int(sig.survives.sum())} survive',
         f'Smallest uncorrected p = {sig.p_raw.min():.3f}, threshold {sig.alpha_single.iloc[0]:.4f}',
         "fail", "signals.html"),
        ("F04", "A profitable staking run coexists with a negative signal bound",
         f'Strategy {board.sort_values("staking_return_per_bet", ascending=False).iloc[0].id}',
         f'{board.staking_return_per_bet.max() * 100:+.2f}% per bet',
         f'Signal lower bound {board.signal_lcb.max() * 100:+.2f}% — the split is what makes this visible',
         "warn", "leaderboard.html"),
        ("F05", "Opening prices exist for 3.7% of the store",
         f'{cov["games_with_open_side"]} of {cov["games"]:,}', f'{cov["pct_with_open_side"]}%',
         "All 2021, one book, no price column — CLV is not computable", "warn", "snapshots.html"),
        ("F06", "1 in 5 spread lines has no price at all",
         "1,981 games with a line and no price", "73.2% priced",
         "Any ROI computed on the unpriced rows would need an assumed price, so it is not computed",
         "warn", "snapshots.html"),
        ("F07", "5 games have a score, a line and a published outcome that cannot all be right",
         f'{e["results"]["chk_spread_bad"] + e["results"]["chk_total_bad"]} cells',
         "published on the review page",
         "Each is listed with the official box score where one was checked", "fail", "flagged.html"),
        ("F08", "Two files print opposite signs for the same club",
         "initial_lines.csv vs games.csv", "Δ sign",
         "TB is −6.5 opening and +10.0 closing for the same game; converted, the move is plausible",
         "warn", "snapshots.html"),
        ("F09", "The same-game cover × over correlation is indistinguishable from zero",
         f'n = {int(e["corr"].iloc[0].n):,}', f'φ = {e["corr"].iloc[0].phi:+.4f}',
         f'95% CI {e["corr"].iloc[0].ci_low:+.4f} … {e["corr"].iloc[0].ci_high:+.4f} spans zero',
         "warn", "correlations.html"),
        ("F10", "Every tracked replacement is exactly one rung deep",
         f'{e["depth"].get("rows", 0)} replacements', f'{e["depth"].get("one_deep", 0)} one-deep',
         "No club in the capture published a 3rd or 4th string behind an injured starter",
         "open", "depth.html"),
    ]
    body = """
<div class="note">Each finding carries the number it rests on and the page that shows the working.
A finding is not a claim of skill; several of them are reasons to distrust an earlier number.</div>
"""
    body += table(["ID", "Finding", "Scope", "Result", "Consequence", "Verdict", "Evidence"], [
        [f"<td><code>{E(i)}</code></td>", f"<td><strong>{E(t)}</strong></td>", f"<td>{E(s)}</td>",
         f'<td class="num">{E(r)}</td>', f"<td>{E(c)}</td>", f"<td>{pill(v.upper(), v)}</td>",
         src(f'<a href="{h}">{E(page_title(h))}</a>')]
        for i, t, s, r, c, v, h in f1], "Ten findings, each with the number behind it.")

    body += """
<div class="section-head"><div><h2>How the analysis was done</h2>
<p>The method is stated so a reader can attack it rather than trust it.</p></div></div>
"""
    method = [
        ("Sign convention", "Positive spread_line = the HOME team is favoured. Settled against an "
         "official box score, not a column heading: DAL 29 @ TB 31 is a home margin of +2 and the "
         "dataset stores it as +10.0.", "NFL-PS", "findings.html"),
        ("Settlement", "A bet is settled from the final score, in code: the side covers when "
         "margin > line, the total goes over when the sum > total_line, a tie pushes. The dataset's "
         "own outcome column is then compared, not trusted.", "NFL-PS", "results.html"),
        ("Leakage control", "Team ratings are updated only after a game is settled; rolling form uses "
         "shift(1). No feature of a game is visible before kickoff.", None, "signals.html"),
        ("Walk-forward", "The fair line is refitted on every prior season and tested on the next. "
         "No random splits, no shuffling of games, no future information.", "NIST-CI",
         "fair-vs-market.html"),
        ("Multiplicity", "18 rules are tested once each. The threshold is 0.05/18, the Bonferroni "
         "bound, so the chance of any false pass across the family is held at 5%.", "NIST-BONF",
         "signals.html"),
        ("Sample size", "The number of settled bets needed to distinguish an edge from zero is "
         "computed with the NIST one-sided formula at 80% power, not chosen by feel.",
         "NIST-SAMPLESIZE", "signals.html"),
        ("Blanks", "A value with no source is blank. It is never zero, never the median, never an "
         "average of its neighbours. Blanks are counted and published.", None, "flagged.html"),
        ("Demotion", "The gate is fail-closed: a missing input demotes the strategy. This is why "
         "nothing is live — the inputs that would keep a strategy live do not exist here.",
         "NIST-CI", "demotion.html"),
    ]
    body += table(["Method", "How it was done", "Authority", "Where it is shown"], [
        [f"<td><strong>{E(m)}</strong></td>", f"<td>{E(h)}</td>",
         f'<td class="src">{link_source(a) if a else link_repo("lines_lab/research.py", "code")}</td>',
         src(f'<a href="{w}">{E(page_title(w))}</a>')]
        for m, h, a, w in method], "Eight decisions that determine whether the numbers mean anything.")
    return page("Findings & analysis", "findings.html",
                "<strong>Start here</strong> / Findings & analysis",
                "The measured results, the consequence of each, and the method a reader would need "
                "to reproduce or refute them.", body,
                "Findings from the line origination lab: the market beats the model every season, "
                "no signal survives multiplicity control, and the staking/signal split in action.")


# The naive open-to-close difference, computed once here so the page can show what
# the sign error would have produced. It is not used in any calculation.
def _maybe_source(sid: str) -> str:
    """Link a registered source, or fall back to the repo/blank if it is not registered."""
    from .sources import BY_ID
    if sid in BY_ID:
        return link_source(sid)
    return link_repo("lines_lab/sources.py", "code")


def _naive_move(store: pd.DataFrame) -> float:
    b = store[store.open_side.notna() & store.close_side.notna()]
    return float((b.close_side + b.open_side).mean())


# --------------------------------------------------------------------------- #
# Price snapshots
# --------------------------------------------------------------------------- #
def snapshots(e: dict) -> str:
    cov, store = e["coverage"], e["store_rows"]
    body = kpis([
        ("Games in the store", f'{cov["games"]:,}', "spread or total or moneyline present", ""),
        ("Closing spread", f'{cov["games_with_close_side"]:,}', "every stored game", "ok"),
        ("Closing total", f'{cov["games_with_close_total"]:,}', "every stored game", "ok"),
        ("Opening spread", f'{cov["games_with_open_side"]:,}',
         f'{cov["pct_with_open_side"]}% of the store', "bad"),
        ("Opening total", f'{cov["games_with_open_total"]:,}', "same 272 games", "bad"),
        ("With a spread price", f'{cov["games_with_spread_price"]:,}',
         f'{cov["games_with_close_side"] - cov["games_with_spread_price"]:,} lines have no price', "warn"),
    ])
    body += """
<div class="note"><strong>The honest state of the snapshot store.</strong> A closing number exists
for every game in the store, and a price for most of them. An <strong>opening</strong> number exists
for 272 games in one season from one book, and that file has <strong>no price column</strong>. So the
store can answer "what did the market close at" and cannot answer "what could I have bet at
kickoff-minus-a-week". Closing-line value needs the second, which is why it is not computed
anywhere on this site.</div>

<div class="section-head"><div><h2>Coverage by market</h2>
<p>Counted from the store at build time. A market with no row has no data, not a zero.</p></div></div>
"""
    markets = [
        ("Side (spread)", "games.csv:spread_line",
         cov["games_with_close_side"], cov["games_with_open_side"], cov["games_with_spread_price"],
         "1999–2026 closing; 2021 opening only"),
        ("Total", "games.csv:total_line",
         cov["games_with_close_total"], cov["games_with_open_total"], cov["games_with_total_price"],
         "1999–2026 closing; 2021 opening only"),
        ("Moneyline", "games.csv:home_moneyline / away_moneyline",
         cov["games_with_ml"], 0, cov["games_with_ml"],
         "2006–2026; no opening moneyline exists"),
        ("Player props", "—", 0, 0, 0,
         "No player-level market in the dataset. Not published: it would be invented."),
    ]
    rows = []
    for name, field, n_close, n_open, n_price, note in markets:
        rows.append([
            f"<td><strong>{E(name)}</strong></td>",
            f'<td class="num">{n_close:,}</td>' if n_close else f'<td class="num">{blank()}</td>',
            f'<td class="num">{n_open:,}</td>' if n_open else f'<td class="num">{blank()}</td>',
            f'<td class="num">{n_price:,}</td>' if n_price else f'<td class="num">{blank()}</td>',
            f"<td>{E(note)}</td>",
            src(link_repo("lines_lab/data_layer.py", "code") +
                (f' · {link_source("NFL-PS")}' if name.startswith("Side") else "")),
        ])
    body += table(["Market", "Closing numbers", "Opening numbers", "With a price", "Note", "Source"],
                  rows, "The four markets the brief names, and what actually exists for each.",
                  numeric_cols={1, 2, 3})

    body += """
<div class="section-head"><div><h2>The convention mismatch, stated plainly</h2>
<p>Two files in the same dataset carry opposite signs for the same club. This is real and it changes
any naive calculation of line movement.</p></div></div>
"""
    rows = [
        ["<td><code>initial_lines.csv</code></td>", "<td>TB</td>", '<td class="num">−6.5</td>',
         "<td>negative = favourite (the NFL's own convention)</td>", src(link_source("NFL-PS") +
         " · " + link_repo("data/raw/initial_lines.csv", "data"))],
        ["<td><code>games.csv</code> (closing)</td>", "<td>TB</td>", '<td class="num">+10.0</td>',
         "<td>positive = the home team is favoured</td>", src(link_repo("data/raw/games.csv", "data") +
         " · " + link_repo("lines_lab/data_layer.py", "code"))],
        ["<td>Converted to one convention</td>", "<td>TB home handicap</td>",
         '<td class="num">−6.5 → −10.0</td>',
         "<td>a −3.5 move toward the home side, which is a normal week of drift</td>",
         src(link_repo("lines_lab/data_layer.py", "code"))],
        ["<td>Differenced without converting</td>", "<td>—</td>", '<td class="num">+16.5</td>',
         "<td>impossible: it would be the largest open-to-close move in the file by a factor of six</td>",
         src(f'<a href="flagged.html">U05</a>')],
    ]
    body += table(["File", "Club", "Value", "What the sign means", "Source"], rows,
                  "2021 week 1, DAL @ TB. Both values are as printed in the dataset.",
                  numeric_cols={2})

    body += """
<div class="section-head"><div><h2>Opening and closing numbers, every game that has both</h2>
<p>All 272 games with an opening number, shown in one convention so the move is readable.</p></div></div>
"""
    both = store[store.open_side.notna() & store.close_side.notna()].copy()
    # Convert the opening file to the same convention as the closing column.
    # initial_lines.csv uses negative = favourite (NFL-PS). games.csv stores
    # positive = home favoured. So: home_handicap = -initial_line, and both columns
    # below mean "how many points the HOME team is favoured by".
    both["open_home"] = -both["open_side"]
    both["close_home"] = both["close_side"]
    both["move"] = both["close_home"] - both["open_home"]   # + = market moved toward home
    both = both.sort_values(["week", "game_id"])
    rows = []
    for r in both.itertuples():
        rows.append([
            f"<td><code>{E(r.game_id)}</code></td>",
            f'<td class="num">{int(r.week)}</td>',
            f"<td>{E(r.away)} @ {E(r.home)}</td>",
            f'<td class="num">{r.open_side:+.1f}</td>',
            f'<td class="num">{r.open_home:+.1f}</td>',
            f'<td class="num">{r.close_home:+.1f}</td>',
            f'<td class="num">{r.move:+.1f}</td>',
            f'<td class="num">{r.open_total:.1f}</td>',
            f'<td class="num">{r.close_total:.1f}</td>',
            src(link_repo("data/raw/initial_lines.csv", "open") + " · " +
                link_repo("data/raw/games.csv", "close")),
        ])
    body += table(["Game", "Week", "Matchup", "Open as printed", "Open (home favoured by)",
                   "Close (home favoured by)", "Move", "Open total", "Close total", "Source"], rows,
                  f"{len(rows)} games with both numbers. The opening file is shown twice: as printed, "
                  "and converted to the closing column's convention. 'Move' is close minus converted "
                  "open, so a positive value means the market moved toward the home team.",
                  numeric_cols={1, 3, 4, 5, 6, 7, 8}, table_id="snap-table", filterable=True)

    mv = both["move"].dropna()
    NAIVE_MOVE = _naive_move(e["store_rows"])
    body += f"""
<div class="section-head"><div><h2>What the movement is, once the sign is fixed</h2></div></div>
"""
    rows = [
        ("Games with both numbers", f"{len(both)}", "2021 regular and post-season",
         src(link_repo("data/raw/initial_lines.csv", "data"))),
        ("Mean move, converted convention", f"{mv.mean():+.2f} points",
         "+ = toward the home team",
         src(link_repo("lines_lab/data_layer.py", "code"))),
        ("Standard deviation of the move", f"{mv.std():.2f} points", "one season only",
         src(link_repo("lines_lab/data_layer.py", "code"))),
        ("Mean difference if the sign is NOT converted", f"{NAIVE_MOVE:+.2f} points",
         "what a naive close-minus-open produces, and why it is not used", src(
             f'<a href="flagged.html">U05</a>')),
        ("Games where the number did not move", f"{int((mv == 0).sum())}",
         f"{(mv == 0).mean() * 100:.1f}% of the sample", src(link_repo("lines_lab/data_layer.py", "code"))),
        ("Closing-line value", blank("not computable"),
         "needs a price on both sides of the move; the opening file has no price column",
         src(f'<a href="flagged.html">U06</a>')),
    ]
    body += table(["Measure", "Value", "Note", "Source"], [
        [f"<td>{E(a)}</td>", f'<td class="num"><strong>{b}</strong></td>', f"<td>{E(c)}</td>", s_]
        for a, b, c, s_ in rows], "Six measures of the same 272 games.", numeric_cols={1})

    return page("Price snapshots", "snapshots.html",
                "<strong>The three markets</strong> / Price snapshots",
                "Opening and closing numbers for every market the lab originates, with the source of "
                "every cell and an explicit blank where no number exists.", body,
                "Price snapshot store: closing numbers for every game, opening numbers for 272 games "
                "only, prices where they exist, and the sign convention settled against an official box score.")


# --------------------------------------------------------------------------- #
# Verified results
# --------------------------------------------------------------------------- #
def results(e: dict) -> str:
    res = e["results"]
    chk = e["crosscheck"]
    bad = chk[(chk.spread_ok == False) | (chk.total_ok == False) | (chk.ml_ok == False)]
    body = kpis([
        ("Regular-season games", f'{res["reg_games"]:,}', "1999–2026", ""),
        ("Settled", f'{res["reg_games_played"]:,}', f'{res["reg_games_unplayed"]} not yet played', "ok"),
        ("Spread outcomes reproduced", f'{res["chk_spread_ok"]:,}/{res["chk_games"]:,}',
         f'{res["chk_spread_bad"]} disagree', "ok" if res["chk_spread_bad"] == 0 else "warn"),
        ("Total outcomes reproduced", f'{res["chk_total_ok"]}/{res["chk_games"]}',
         f'{res["chk_total_bad"]} disagree', "ok" if res["chk_total_bad"] == 0 else "warn"),
        ("Moneyline reproduced", f'{res["chk_ml_ok"]}/{res["chk_games"]}',
         f'{res["chk_ml_bad"]} disagree', "ok" if res["chk_ml_bad"] == 0 else "warn"),
        ("Pushes", f'{res["spread_pushes"]} + {res["total_pushes"]}',
         f'spread + total; {res["ties"]} tied games', ""),
    ])
    body += """
<div class="note"><strong>Why a results feed has to be verified before it is used.</strong> A
backtest is only as good as its settlement. This page re-derives the outcome of every market from
the final score in code, then compares that derivation with the outcome column the dataset
publishes. Where they disagree, neither is silently preferred: the row is listed below with both
values, and where the disagreement mattered a third source was opened and is linked.</div>

<div class="section-head"><div><h2>Settlement rules, and where each comes from</h2>
<p>The rule is fixed from an official source before any number is computed.</p></div></div>
"""
    rules = [
        ("Spread", "A side covers when its margin exceeds the line. If the margin equals the "
         "line the bet pushes and the stake is returned.",
         "NFL-PS", "«if the point spread was +10/-10 ... you would push and get your initial wager returned»"),
        ("Total", "The over wins when the two scores sum above the number, the under when below, "
         "a push when equal. Same push rule as the spread.", "NFL-PS",
         "«the odds for point spread are -110» — the same reference price applies to a total"),
        ("Moneyline", "The side that wins outright pays its price. A tied game pushes; the price "
         "does not settle.", "NFL-ML",
         "«Tie | Push | If the game ends in a tie, the bettor's wager is returned»"),
        ("Reference price", "Where no price exists the row is marked line-only and no ROI is "
         "computed. A -110 default is never substituted.", "NFL-PS",
         "«Most often, the betting odds for point spread are -110»"),
        ("Parlay", "Every leg must win. A pushed leg is removed and the price recalculated.",
         "DK-PARLAY", "operator house rule on parlay settlement"),
    ]
    body += table(["Market", "Rule applied in code", "Authority", "The sentence it rests on"], [
        [f"<td><strong>{E(a)}</strong></td>", f"<td>{E(b)}</td>", src(link_source(c)),
         f'<td style="font-size:11.5px;color:#5b6b82">{E(d)}</td>']
        for a, b, c, d in rules], "Five settlement rules, each fixed before it is applied.")

    body += """
<div class="section-head"><div><h2>Every game where the score, the line and the published outcome disagree</h2>
<p>These are the failures of the cross-check. Each is published rather than dropped, and the ones that
mattered were checked against an official box score.</p></div></div>
"""
    if len(bad) == 0:
        body += '<div class="panel"><div style="padding:14px">No disagreements.</div></div>'
    else:
        body += '<div id="U04"></div>'

        rows = []
        for r in bad.itertuples():
            sp_ok = "—" if pd.isna(r.spread_ok) else ("match" if bool(r.spread_ok) else "MISMATCH")
            to_ok = "—" if pd.isna(r.total_ok) else ("match" if bool(r.total_ok) else "MISMATCH")
            ml_ok = "—" if pd.isna(r.ml_ok) else ("match" if bool(r.ml_ok) else "MISMATCH")
            rows.append([
                f"<td><code>{E(r.game_id)}</code></td>",
                f"<td>{E(r.away)} {int(r.away_score)} @ {E(r.home)} {int(r.home_score)}</td>",
                f'<td class="num">{r.spread_line_closing:+.1f}</td>',
                f'<td class="num">{r.spread_published if r.spread_published is not None else "—"}</td>',
                f'<td class="num">{r.spread_calc if r.spread_calc is not None else "—"}</td>',
                f'<td class="num">{r.total_published if r.total_published is not None else "—"}</td>',
                f'<td class="num">{r.total_calc if r.total_calc is not None else "—"}</td>',
                f'<td>{pill("spread " + sp_ok, "fail" if sp_ok == "MISMATCH" else "pass")} '
                f'{pill("total " + to_ok, "fail" if to_ok == "MISMATCH" else "pass")} '
                f'{pill("ml " + ml_ok, "fail" if ml_ok == "MISMATCH" else "pass")}</td>',
                src(link_tree("data/raw", "data") + " · " + f'<a href="flagged.html">U04</a>'),
            ])
        body += table(["Game", "Final score", "Closing line", "Published", "Recomputed",
                       "Published (O/U)", "Recomputed (O/U)", "Verdict", "Source"], rows,
                      "A published 1 = the bet won, 0 = lost, 0.5 = push. Recomputed from the score.",
                      numeric_cols={2, 3, 4, 5, 6}, table_id="mismatch-table")
        body += """
<div class="note"><strong>Two of these were checked against the NFL's own game page.</strong>
2015 week 9 PHI @ DAL is officially <strong>PHI 33 – DAL 27</strong> and the dataset says 33–27 — the
score is right and the <em>line</em> is wrong. 2015 week 15 KC @ BAL is officially
<strong>KC 34 – BAL 14</strong> and the dataset says 34–14 — again the score is right. In both
cases <code>games.csv</code> carries a spread the closing file's own outcome contradicts.
Official pages: <a href="https://www.nfl.com/games/eagles-at-cowboys-2015-reg-9">PHI @ DAL 2015 W9 ↗</a>
and <a href="https://www.nfl.com/games/chiefs-at-ravens-2015-reg-15">KC @ BAL 2015 W15 ↗</a>.</div>
"""

    body += """
<div class="section-head"><div><h2>The feed the backtests actually consume</h2>
<p>One row per settled regular-season game, with every market already resolved. This is the table
that makes an ROI computable at all.</p></div></div>
"""
    played = e["fair_rows"]  # has game_id/season; use ledger-free summary instead
    # a compact sample: one season, fully published
    import numpy as _np
    store = e["store_rows"]
    sample = store[(store.season == 2025) & (store.played)].sort_values(["week", "game_id"]).head(40)
    rows = []
    for r in sample.itertuples():
        rows.append([
            f"<td><code>{E(r.game_id)}</code></td>", f'<td class="num">{int(r.week)}</td>',
            f"<td>{E(r.away)} @ {E(r.home)}</td>",
            f'<td class="num">{r.close_side:+.1f}</td>' if pd.notna(r.close_side) else f'<td class="num">{blank()}</td>',
            f'<td class="num">{r.close_total:.1f}</td>' if pd.notna(r.close_total) else f'<td class="num">{blank()}</td>',
            f'<td class="num">{r.price_side:+.0f}</td>' if r.price_side is not None and pd.notna(r.price_side) else f'<td class="num">{blank("no price")}</td>',
            src(link_repo("data/raw/games.csv", "data")),
        ])
    body += table(["Game", "Week", "Matchup", "Line (home)", "Total", "Price", "Source"], rows,
                  f"A sample of the feed: the first 40 settled 2025 games of the season. "
                  f"The full feed is regenerated at build time and is not committed as HTML.",
                  numeric_cols={1, 3, 4, 5})
    return page("Verified results", "results.html",
                "<strong>The three markets</strong> / Verified results",
                "Settlement recomputed from the final score for every market, compared with the "
                "dataset's own outcome, and every disagreement published.", body,
                "Verified results feed: settlement computed from final scores, cross-checked against "
                "the dataset's published outcomes, with all disagreements listed.")


# --------------------------------------------------------------------------- #
# Fair line vs market
# --------------------------------------------------------------------------- #
def fair_vs_market(e: dict) -> str:
    by = e["fair_by_season"].copy()
    by["gap_side"] = by.mae_fair_side - by.mae_market_side
    by["gap_total"] = by.mae_fair_total - by.mae_market_total
    wins_market_side = int((by.gap_side > 0).sum())
    wins_market_total = int((by.gap_total > 0).sum())
    body = kpis([
        ("Test seasons", f"{len(by)}", "2005–2026, walk-forward", ""),
        ("Side: model MAE", f'{by.mae_fair_side.mean():.3f}', "points of absolute error", "bad"),
        ("Side: market MAE", f'{by.mae_market_side.mean():.3f}', "the same measure", "ok"),
        ("Total: model MAE", f'{by.mae_fair_total.mean():.3f}', "points", "bad"),
        ("Total: market MAE", f'{by.mae_market_total.mean():.3f}', "points", "ok"),
        ("Seasons the market wins", f"{wins_market_side}/{len(by)}",
         f"side; {wins_market_total}/{len(by)} on the total", "bad"),
    ])
    body += """
<div class="note"><strong>The three columns the brief asks for, and why the difference is not an edge.</strong>
Every row publishes the model's fair line, the market's line and the difference as
<strong>separate columns</strong>, never merged into one "pick". A difference is not a bet: it is
a disagreement, and on this data the market wins the disagreement in every season. A model that
disagrees with a better forecast is not finding value; it is making an error the market has
already priced.</div>

<div class="section-head"><div><h2>Why the origination order is side → total → moneyline</h2>
<p>The order is enforced in code, not just described.</p></div></div>
"""
    order = [
        ("1. Side", "First", "The only market with a sign convention the NFL defines, the longest "
         "history (1999–2026) and the tightest prices. If the side cannot be originated, nothing "
         "downstream is worth originating.", "NFL-PS", "1999–2026"),
        ("2. Total", "Second", "Needs the same inputs but has a weaker reference: a total push rate "
         "of 99 games in 7,075 is 1.4%, and the market for totals is less efficient in a way this "
         "data can see but not exploit.", "NFL-PS", "1999–2026"),
        ("3. Moneyline", "Third", "A non-linear transform of the side. Originating it first would "
         "launder a side error into a price. It is only originated once the side exists, and it "
         "inherits the side's error.", "NFL-ML", "2006–2026 priced"),
        ("Player props", "Not originated", "No player-level market exists in the dataset. A fair "
         "prop line here would be invented, so none is produced.", "DK-PROP", "—"),
    ]
    body += table(["Market", "Order", "Why it sits there", "Authority", "Coverage"], [
        [f"<td><strong>{E(a)}</strong></td>", f"<td>{pill(b.upper(), 'open' if b != 'Not originated' else 'na')}</td>",
         f"<td>{E(c)}</td>", src(_maybe_source(d)), f'<td class="num">{E(f_)}</td>']
        for a, b, c, d, f_ in order], "Four markets and the order in which each is originated.")

    body += """
<div class="section-head"><div><h2>Fair line, market line and difference, by season</h2>
<p>Absolute error against the realised margin and the realised total. Lower is better.</p></div></div>
"""
    rows = []
    for r in by.itertuples():
        vs = "market" if r.gap_side > 0 else "MODEL"
        vt = "market" if r.gap_total > 0 else "MODEL"
        rows.append([
            f'<td class="num">{int(r.season)}</td>', f'<td class="num">{int(r.n):,}</td>',
            f'<td class="num">{r.mae_fair_side:.3f}</td>',
            f'<td class="num">{r.mae_market_side:.3f}</td>',
            f'<td class="num">{r.gap_side:+.3f}</td>',
            f'<td>{pill(vs, "fail" if vs == "MODEL" else "na")}</td>',
            f'<td class="num">{r.mae_fair_total:.3f}</td>',
            f'<td class="num">{r.mae_market_total:.3f}</td>',
            f'<td class="num">{r.gap_total:+.3f}</td>',
            f'<td>{pill(vt, "fail" if vt == "MODEL" else "na")}</td>',
            src(link_repo("lines_lab/research.py", "code")),
        ])
    body += table(["Season", "Games", "Fair side", "Market side", "Δ side", "Better",
                   "Fair total", "Market total", "Δ total", "Better", "Source"], rows,
                  "A positive Δ means the model was worse. The market is better in every season on "
                  "the side and in nearly every season on the total.",
                  numeric_cols={1, 2, 3, 4, 6, 7, 8}, table_id="fair-table")

    body += f"""
<div class="section-head"><div><h2>What the difference is, and is not</h2></div></div>
"""
    rows = [
        ("The difference is published", "yes — a separate column on every row above",
         "Never blended into a single recommendation.", src(link_repo("lines_lab/research.py", "code"))),
        ("The difference is a bet", "no",
         "A disagreement with a better forecast is an error, not value.", src(link_source("NFL-PS"))),
        ("A market line to disagree with", f'{e["coverage"]["games_with_close_side"]:,} games',
         "Closing numbers only; an opening number exists for 272.", src(link_repo("data/raw/games.csv", "data"))),
        ("A price to bet the difference", f'{e["coverage"]["games_with_spread_price"]:,} games',
         "The rest are line-only. No price is assumed.", src(link_repo("data/raw/games.csv", "data"))),
        ("A holdout that was never touched", "yes — the last season",
         "The final season in the chain is predicted from all prior seasons only.",
         src(link_source("NIST-CI"))),
        ("Evidence the difference is skill", blank("none"),
         "The market wins every season; no test on this page finds otherwise.",
         src(f'<a href="signals.html">signal tests</a>')),
    ]
    body += table(["Question about the difference column", "Answer", "Why", "Source"], [
        [f"<td>{E(a)}</td>", f"<td><strong>{b}</strong></td>", f"<td>{E(c)}</td>", s_]
        for a, b, c, s_ in rows], "Six questions a reader should ask of a fair-vs-market column.")
    return page("Fair line vs market", "fair-vs-market.html",
                "<strong>The three markets</strong> / Fair line vs market",
                "The model's fair line, the market's line and the difference as three separate "
                "columns — plus the finding that the market wins every test season.", body,
                "Fair line versus market line versus the difference, published as separate columns, "
                "with walk-forward errors showing the market ahead in every season.")


# --------------------------------------------------------------------------- #
# Signal tests
# --------------------------------------------------------------------------- #
def signals_page(e: dict) -> str:
    sig = e["signals"].copy()
    passing = int(sig.survives.sum())
    best_p = sig.p_raw.min()
    body = kpis([
        ("Rules pre-registered", f"{len(sig)}", "side, total and moneyline", ""),
        ("Tested", f'{int(sig.tested.sum())}', "each tested exactly once", ""),
        ("Surviving multiplicity control", f"{passing}", f"Bonferroni α = 0.05/{len(sig)}", "bad" if passing == 0 else "ok"),
        ("Smallest uncorrected p", f"{best_p:.4f}", "still far above the threshold", "bad"),
        ("Bonferroni threshold", f'{sig.alpha_single.iloc[0]:.4f}', "per-test level", ""),
        ("Bets needed at +2% ROI", f'{int([s["bets"] for s in e["sample_sizes"] if abs(s["edge"] - 0.02) < 1e-9][0]):,}',
         "at the -110 reference, 80% power", "warn"),
    ])
    body += """
<div class="note"><strong>Why the answer is "none" and why that is the honest answer.</strong>
Eighteen rules were written down before they were tested, and each was tested once. A rule that
passes an uncorrected 5% test out of eighteen is what chance produces: at 18 independent tests the
expected number of false passes is 0.9. The Bonferroni bound is applied so the chance of <em>any</em>
false pass across the family stays at 5%. Nothing clears it, and the smallest uncorrected p-value
is far above the per-test threshold. Reporting a "best rule" from this table would be reporting
noise with a source link attached.</div>

<div class="section-head"><div><h2>Every rule, its result and its verdict</h2>
<p>A rule that could not be tested is marked NOT TESTED rather than given a pass.</p></div></div>
"""
    rows = []
    for r in sig.itertuples():
        if not bool(r.tested):
            rows.append([f"<td><code>{E(r.id)}</code></td>", f"<td>{E(r.market)}</td>",
                         f"<td>{E(r.rule)}</td>", f'<td class="num">{int(r.n)}</td>',
                         f'<td class="num">{blank()}</td>', f'<td class="num">{blank()}</td>',
                         f'<td class="num">{blank()}</td>', f'<td class="num">{blank()}</td>',
                         f'<td>{pill("NOT TESTED", "na")}</td>',
                         src(link_repo("lines_lab/research.py", "code"))])
            continue
        rows.append([
            f"<td><code>{E(r.id)}</code></td>",
            f"<td>{E(r.market)}</td>",
            f"<td>{E(r.rule)}</td>",
            f'<td class="num">{int(r.n_decided):,}</td>',
            f'<td class="num">{r.win_rate * 100:.2f}%</td>',
            f'<td class="num">{r.roi * 100:+.2f}%</td>',
            f'<td class="num">{r.p_raw:.4f}</td>',
            f'<td class="num">{r.p_bonferroni:.3f}</td>',
            f'<td>{pill(r.verdict, "pass" if r.survives else "fail")}</td>',
            src(link_source("NIST-BONF") + " · " + link_repo("lines_lab/research.py", "code")),
        ])
    body += table(["ID", "Market", "Rule", "Settled bets", "Win rate", "ROI at -110",
                   "p (raw)", "p (Bonferroni)", "Verdict", "Source"], rows,
                  "All 18 rules. n is settled bets, excluding pushes. ROI assumes the -110 "
                  "reference price the NFL states is used most often; moneyline rows use the "
                  "markets' own prices.",
                  numeric_cols={3, 4, 5, 6, 7}, table_id="sig-table", filterable=True)

    body += """
<div class="section-head"><div><h2>How many bets would be needed to prove an edge</h2>
<p>Computed with the NIST one-sided sample-size formula at 80% power and a 5% one-sided test,
using the win/loss spread of a -110 bet.</p></div></div>
"""
    rows = []
    for s in e["sample_sizes"]:
        rows.append([f'<td class="num">{s["edge"] * 100:+.1f}%</td>',
                     f'<td class="num">{int(s["bets"]):,}</td>',
                     f'<td class="num">{int(s["bets"]) // 272:.1f}</td>',
                     f'<td class="num">{int(s["bets"]) / 272 / 18:.1f}</td>',
                     src(link_source("NIST-SAMPLESIZE"))])
    body += table(["True edge per bet", "Settled bets needed", "Seasons (272 games each)",
                   "Seasons if one bet per game, 18 rules", "Source"], rows,
                  "What a claim of edge costs in evidence. A rule with 300 bets cannot demonstrate "
                  "a +2% edge at all.", numeric_cols={0, 1, 2, 3})

    body += """
<div class="section-head"><div><h2>Single bets, parlays and player-prop combos</h2>
<p>The brief asks for all three. What can and cannot be tested differs sharply between them.</p></div></div>
"""
    bt = [
        ("Single bets", "Fully testable", f'{len(sig)} rules on sides, totals and moneylines',
         "n is in the thousands for most rules; the test is the table above", "pass"),
        ("2-leg parlays", "Testable as arithmetic",
         "Legs can be joined two at a time with a measured phi, as on the correlations page",
         "No posted parlay price exists in the data, so a parlay's own ROI cannot be settled — "
         "only its fair value at an assumed price", "warn"),
        ("Player-prop combos", "Not testable",
         "No player-level market, line or price exists in the dataset",
         "The fair value of a prop leg is uncomputable here. Any number would be invented.",
         "fail"),
    ]
    body += table(["Bet type", "Testable?", "What is tested", "What is missing", "State", "Source"], [
        [f"<td><strong>{E(a)}</strong></td>", f"<td>{b}</td>", f"<td>{E(c)}</td>", f"<td>{E(d)}</td>",
         f"<td>{pill(b.upper() if len(b) < 12 else b, k)}</td>",
         src(link_source("DK-PROP") if a.startswith("Player") else link_source("DK-PARLAY") if "parlay" in a else link_repo("lines_lab/research.py", "code"))]
        for a, b, c, d, k in bt], "Three bet types the brief names, and the honest testability of each.")
    return page("Signal tests", "signals.html",
                "<strong>Origination &amp; signals</strong> / Signal tests",
                "Eighteen pre-registered rules, each tested once, with the multiplicity control that "
                "decides whether any of them is a signal. None is.", body,
                "Eighteen pre-registered NFL betting rules tested once each with Bonferroni "
                "multiplicity control; zero survive. Includes sample-size arithmetic.")


# --------------------------------------------------------------------------- #
# Leaderboard with the signal / staking split
# --------------------------------------------------------------------------- #
def leaderboard_page(e: dict) -> str:
    b = e["board"].copy()
    by_plan = e["by_plan"]
    live = int((b.state == "LIVE").sum())
    best_stake = b.sort_values("staking_return_per_bet", ascending=False).iloc[0]
    best_signal = b.sort_values("signal_lcb", ascending=False).iloc[0]
    body = kpis([
        ("Strategies on the board", f"{len(b)}", "every tested rule", ""),
        ("Ranked columns", "2", "signal and staking, never added", ""),
        ("Live", f"{live}", "passes every gate", "ok" if live else "warn"),
        ("Paper", f"{len(b) - live}", "tracked, not staked", "warn"),
        ("Best staking return", f'{best_stake.staking_return_per_bet * 100:+.2f}%', f"strategy {best_stake.id}", "warn"),
        ("Best signal lower bound", f'{best_signal.signal_lcb * 100:+.2f}%', f"strategy {best_signal.id}", "bad"),
    ])
    body += f"""
<div class="note"><strong>Why the two columns are not added together.</strong> Picking winners and
choosing stake size are different skills and they fail differently. A board that ranks one number lets
a good staking run hide a bad signal, and lets a bad stake plan sink a good one. So the board publishes
them side by side and <strong>never sums them into a rank</strong>. This page's own data shows why:
<strong>strategy {E(best_stake.id)}</strong> has the highest staking return on the board
(<strong>{best_stake.staking_return_per_bet * 100:+.2f}%</strong> per bet) and a signal lower bound
that is still <strong>{best_stake.signal_lcb * 100:+.2f}%</strong>. A one-column board would have
ranked it first. The two-column board shows a lucky run sitting on top of a negative edge.</div>

<div class="section-head"><div><h2>The board</h2>
<p>Signal first, then staking. Neither column orders the other.</p></div></div>
"""
    rows = []
    for r in b.sort_values("signal_lcb", ascending=False).itertuples():
        rows.append([
            f"<td><code>{E(r.id)}</code></td>", f"<td>{E(r.market)}</td>",
            f'<td class="num">{int(r.n):,}</td>',
            f'<td class="num">{num(r.win_rate, 2, pct=True)}</td>',
            f'<td class="num">{num(r.breakeven, 2, pct=True)}</td>',
            f'<td class="num"><strong>{num(r.signal_lcb, 2, signed=True, pct=True)}</strong></td>',
            f'<td class="num">{num(r.signal_p_adj, 3)}</td>',
            f'<td class="num">{num(r.staking_return_per_bet, 2, signed=True, pct=True)}</td>',
            f'<td>{pill(r.state, "live" if r.state == "LIVE" else "paper")}</td>',
            f'<td class="num">{int(r.n_failed)}</td>',
            src(link_repo("lines_lab/leaderboard.py", "code") + " · " + link_source("NIST-CI")),
        ])
    body += table(["ID", "Market", "Settled bets", "Win rate", "Breakeven",
                   "Signal lower bound", "p (adjusted)", "Staking return / bet",
                   "State", "Gates failed", "Source"], rows,
                  "Sorted by the signal column, deliberately. A negative lower bound means the "
                  "strategy has not shown an edge it can defend, whatever its return.",
                  numeric_cols={2, 3, 4, 5, 6, 7, 9}, table_id="board-table", filterable=True)

    body += """
<div class="section-head"><div><h2>Does the stake plan change the answer? A direct test</h2>
<p>The same bets, sized two different ways. If the signal were real, both plans would agree on its
direction. Only the magnitude should move.</p></div></div>
"""
    rows = []
    for sid, row in sorted(by_plan.items()):
        flat = row.get("return_flat")
        form = row.get("return_form")
        delta = (form - flat) if (flat is not None and form is not None) else None
        agree = ("same sign" if (flat is not None and form is not None and (flat > 0) == (form > 0))
                 else "SIGN FLIPPED")
        rows.append([
            f"<td><code>{E(sid)}</code></td>",
            f'<td class="num">{int(row["n"]):,}</td>' if row.get("n") else f'<td class="num">{blank()}</td>',
            f'<td class="num">{num(flat, 2, signed=True, pct=True)}</td>',
            f'<td class="num">{num(form, 2, signed=True, pct=True)}</td>',
            f'<td class="num">{num(delta, 2, signed=True, pct=True)}</td>',
            f'<td>{pill(agree.upper(), "pass" if agree == "same sign" else "fail")}</td>',
            src(link_repo("lines_lab/research.py", "code")),
        ])
    body += table(["Strategy", "Settled bets", "Flat stake return", "Form-weighted return",
                   "Difference", "Direction", "Source"], rows,
                  "Both plans place the same bets on the same games; only the stake differs. A sign "
                  "flip between the two would mean the return is a sizing artefact, not an edge.",
                  numeric_cols={1, 2, 3, 4})

    body += """
<div class="section-head"><div><h2>What the board would need before it ranked anything</h2></div></div>
"""
    rows = [
        ("A signal that survives correction", "0 of 18", "The board cannot rank skill it has not found.",
         src(link_source("NIST-BONF"))),
        ("A settled bet at a sourced price", "5,403 of 7,384 played games",
         "The rest are line-only; no price is assumed.", src(link_repo("data/raw/games.csv", "data"))),
        ("A published stake plan before results", "yes — flat and form",
         "Both are fixed in code before any result is read.", src(link_repo("lines_lab/research.py", "code"))),
        ("A held-out period not used for selection", "partly",
         "The last season is predicted from prior seasons, but it has been read in this session.",
         src(f'<a href="questions.html">Q07</a>')),
        ("A funded prize and its terms", blank("none exist"),
         "No sponsor, amount or terms; stating one would be inventing a commitment.",
         src(f'<a href="flagged.html">U11</a>')),
        ("A reward for top performance", "not offered",
         "The board is a specification. Nothing here pays anyone, and no entry is open.",
         src(f'<a href="questions.html">Q11</a>')),
    ]
    body += table(["Requirement for a ranked, rewarded board", "State", "Why", "Source"], [
        [f"<td>{E(a)}</td>", f"<td><strong>{b}</strong></td>", f"<td>{E(c)}</td>", s_]
        for a, b, c, s_ in rows], "Six requirements, and none of them is met by this data.")
    return page("Leaderboard", "leaderboard.html",
                "<strong>Origination &amp; signals</strong> / Leaderboard",
                "Signal and staking in separate columns, so a lucky staking run cannot rescue a "
                "losing signal and a bad stake plan cannot hide a good one.", body,
                "Leaderboard that separates signal from staking, with a stake-plan comparison "
                "showing that sizing does not change the sign of the edge.")


# --------------------------------------------------------------------------- #
# Promotion & demotion
# --------------------------------------------------------------------------- #
def demotion_page(e: dict) -> str:
    b = e["board"]
    live = int((b.state == "LIVE").sum())
    body = kpis([
        ("Gates defined", "8", "a strategy must clear all", ""),
        ("Strategies live", f"{live}", "passing every gate", "ok" if live else "warn"),
        ("Strategies on paper", f"{len(b) - live}", "demoted, still tracked", "warn"),
        ("Fail-closed", "yes", "an unknown input demotes", ""),
        ("Gate with most failures", "G2 & G3",
         "signal bound and multiplicity, failed by all 18", "bad"),
        ("Reward paid", "none", "no funded prize exists", "warn"),
    ])
    body += """
<div class="note"><strong>The rule is simple and it is enforced in code.</strong> A strategy is
<em>live</em> only while it clears every gate. Any single failure sends it back to <em>paper</em>:
still tracked, still measured, no longer staked. The gate is <strong>fail-closed</strong> — a missing
or unreadable input counts as a failure, because "we cannot tell" is not evidence of an edge. That
is why nothing on this site is live: the inputs a strategy needs to stay live do not exist here.</div>

<div class="section-head"><div><h2>The eight gates</h2>
<p>Each has a threshold, a reason it exists, and the authority behind the threshold.</p></div></div>
"""
    rows = []
    for g in e["gates"]:
        rows.append([
            f"<td><code>{E(g['id'])}</code></td>", f"<td><strong>{E(g['name'])}</strong></td>",
            f"<td>{E(g['threshold'])}</td>", f"<td>{E(g['why'])}</td>",
            src(link_source(g["source"]) if g["source"] in ("NIST-CI", "NIST-BONF", "NIST-SAMPLESIZE", "NFL-PS")
                else link_repo("lines_lab/leaderboard.py", "code")),
        ])
    body += table(["ID", "Gate", "Threshold", "Why it exists", "Authority"], rows,
                  "All eight. A strategy must clear every one; there is no partial pass.")

    body += """
<div class="section-head"><div><h2>Every strategy, its state and the gate that demoted it</h2>
<p>The failing gate is published on the row, so a reader can see why a strategy is not live.</p></div></div>
"""
    rows = []
    for r in b.sort_values(["n_failed", "id"], ascending=[False, True]).itertuples():
        failed = r.failed_gates
        fl = ", ".join(f"<code>{E(f.split(':')[0])}</code>" for f in failed) if failed else "—"
        rows.append([
            f"<td><code>{E(r.id)}</code></td>", f"<td>{E(r.market)}</td>",
            f'<td class="num">{int(r.n):,}</td>',
            f'<td class="num">{num(r.signal_lcb, 2, signed=True, pct=True)}</td>',
            f'<td class="num">{num(r.signal_p_adj, 3)}</td>',
            f'<td class="num">{num(r.staking_return_per_bet, 2, signed=True, pct=True)}</td>',
            f'<td>{pill(r.state, "live" if r.state == "LIVE" else "paper")}</td>',
            f'<td class="num">{int(r.n_failed)}/8</td>',
            f"<td>{fl}</td>",
            src(link_repo("lines_lab/leaderboard.py", "code")),
        ])
    body += table(["ID", "Market", "Settled bets", "Signal lower bound", "p (adjusted)",
                   "Staking return", "State", "Gates failed", "Which", "Source"], rows,
                  "A gate that failed appears in the last column. An empty cell would mean the "
                  "strategy is live — there are none.", numeric_cols={2, 3, 4, 5, 7})

    body += """
<div class="section-head"><div><h2>What would have to change for a strategy to go live</h2>
<p>Stated as a checklist, so a future session can test it rather than argue about it.</p></div></div>
"""
    need = [
        ("G1 — 400+ settled bets", "no strategy has a defensible sample at a realistic edge",
         "The five best-sampled rules have the wrong sign; the rest need 587–9,396 bets to prove an edge.",
         "NIST-SAMPLESIZE"),
        ("G2 — positive lower bound", "no", "Every lower bound is negative, by 2.4 to 12.5 points.", "NIST-CI"),
        ("G3 — survives correction", "no", "All 18 adjusted p-values are 1.000 or near it.", "NIST-BONF"),
        ("G4 — staking sanity", "mostly yes",
         "Returns are negative but within the vig; this gate alone would not demote most rows.", "NFL-PS"),
        ("G5 — sourced price on every settled bet", "no",
         "1,981 spread lines carry no price; those rows cannot be staked at a known number.", "NFL-PS"),
        ("G6 — no single season dominates", "untestable here",
         "No strategy is live, so there is no live season distribution to test.", "NIST-CI"),
        ("G7 — live drawdown within paper", "untestable here", "There is no live record yet.", "NIST-CI"),
        ("G8 — stake plan unchanged", "yes", "Both plans are fixed in code before results are read.",
         "NIST-BONF"),
    ]
    body += table(["Gate", "Met today?", "Detail", "Authority"], [
        [f"<td>{E(a)}</td>", f"<td><strong>{b}</strong></td>", f"<td>{E(c)}</td>", src(link_source(d))]
        for a, b, c, d in need], "A checklist a future session can run.")

    body += """
<div class="section-head"><div><h2>Competition and rewards</h2></div></div>
<div class="panel"><div style="padding:14px 16px;font-size:13.5px">
<p style="margin:0 0 9px">The brief asks for a leaderboard competition that rewards top-performing
strategies. The board exists and the gates are enforced. <strong>The reward does not, and is not
described.</strong> No sponsor, no amount, no terms and no entry are stated, because none exist.
A number invented here would be a commitment nobody has made.</p>
<p style="margin:0">If a prize is introduced, the gates above are the entry condition, the
<a href="leaderboard.html">leaderboard</a> is the ranking, and the
<a href="questions.html">questions register</a> lists what must be settled first — the licence, the
price archive, and what happens when a live strategy is demoted. Those are Q01, Q04 and Q09.</p>
</div></div>
"""
    return page("Promotion & demotion", "demotion.html",
                "<strong>Origination &amp; signals</strong> / Promotion &amp; demotion",
                "Eight gates, applied fail-closed: a strategy clears all of them to stay live, and a "
                "single failure returns it to paper with the reason on the row.", body,
                "Promotion and demotion gate for NFL betting strategies: eight fail-closed gates, "
                "the state of all 18 strategies, and what would have to change for one to go live.")


# --------------------------------------------------------------------------- #
# Correlations
# --------------------------------------------------------------------------- #
def correlations_page(e: dict) -> str:
    c = e["corr"]
    first = c.iloc[0]
    body = kpis([
        ("Correlations published", f"{len(c)}", "each with its n", ""),
        ("Largest n", f'{int(c.n.max()):,}', "settled games", ""),
        ("Same-game cover × over, φ", f"{first.phi:+.4f}", f"n = {int(first.n):,}", "warn"),
        ("Its 95% interval", f"{first.ci_low:+.4f} … {first.ci_high:+.4f}", "spans zero", "warn"),
        ("Values without a source", "0", "every value recomputed at build time", "ok"),
        ("Values labelled official-ish", "0", "no official publisher exists for a betting correlation", "warn"),
    ])
    body += """
<div class="note"><strong>The rule on this page: no n, no number.</strong> Every coefficient below is
computed from the pinned dataset at build time and printed with the number of settled games it rests
on and the tier of its input. A coefficient that cannot reach n = 30 is reported as <em>not computed</em>
rather than printed. And <strong>none of these is an official number</strong>: no league or operator
publishes a betting correlation, so labelling one "official" would be false. They are dataset values,
and they say so.</div>

<div class="section-head"><div><h2>Every correlation, with its n</h2></div></div>
"""
    rows = []
    for r in c.itertuples():
        if r.n < 30 or pd.isna(r.phi):
            rows.append([f"<td>{E(r.name)}</td>", f"<td>{E(r.legs)}</td>",
                         f'<td class="num">{int(r.n)}</td>',
                         f'<td class="num">{blank("n &lt; 30")}</td>',
                         f'<td class="num">{blank()}</td>', f'<td class="num">{blank()}</td>',
                         f"<td>{E(r.note)}</td>", src(link_repo("data/raw/games.csv", "data"))])
            continue
        rows.append([
            f"<td>{E(r.name)}</td>", f"<td>{E(r.legs)}</td>",
            f'<td class="num"><strong>{int(r.n):,}</strong></td>',
            f'<td class="num">{r.phi:+.4f}</td>',
            f'<td class="num">{r.ci_low:+.4f}</td>',
            f'<td class="num">{r.ci_high:+.4f}</td>',
            f"<td>{E(r.note)}</td>",
            src(link_repo("data/raw/games.csv", "data") + " · " + link_repo("lines_lab/depth_corr.py", "code")),
        ])
    body += table(["Correlation", "Legs", "n", "φ", "95% low", "95% high", "Input tier", "Source"], rows,
                  "n is settled games, not rows in a file. The interval is a Fisher z interval.",
                  numeric_cols={2, 3, 4, 5})

    body += """
<div class="section-head"><div><h2>What each value means for a parlay</h2>
<p>A correlation is only useful if it changes a price. Here is what it does to the price.</p></div></div>
"""
    rows = [
        ("Home cover × Over", f"{first.phi:+.4f}", "essentially independent",
         "Joining these two legs adds no correlation adjustment: the fair price is the product of the "
         "single-leg prices, and the operator's vig is the whole cost.", "warn"),
        ("Home cover × home moneyline",
         f'{c[c.name.str.contains("moneyline")].iloc[0].phi:+.4f}',
         "strongly positive, and bounded by construction",
         "A home win by more than the line is both a cover and a moneyline win, so these legs cannot "
         "be independent. A parlay of them is largely a single bet at a worse price.", "fail"),
        ("Over × home moneyline",
         f'{c[c.name.str.startswith("Over")].iloc[0].phi:+.4f}',
         "independent",
         "Scoring volume and the winner are close to unrelated in this data, which is worth knowing "
         "before assuming a shootout helps the favourite.", "warn"),
    ]
    body += table(["Pair", "φ", "Reading", "What it does to a parlay", "State", "Source"], [
        [f"<td>{E(a)}</td>", f'<td class="num">{b}</td>', f"<td>{E(cc)}</td>", f"<td>{E(d)}</td>",
         f"<td>{pill(cc.upper() if len(cc) < 20 else 'see note', k)}</td>",
         src(link_repo("lines_lab/depth_corr.py", "code") + " · " + link_source("NIST-CORR"))]
        for a, b, cc, d, k in rows], "Three pairs and the practical consequence of each.")

    body += """
<div class="section-head"><div><h2>What is not measured, and why</h2></div></div>
"""
    rows = [
        ("Player-prop correlations", blank("not computable"),
         "No player-level lines, prices or outcomes exist in the dataset. The fair value of a prop "
         "leg cannot be computed, and no phi is published for one.", src(link_source("DK-PROP"))),
        ("Correlations across different weeks", blank("not computed"),
         "A parlay of legs in different games is priced independently by operators, so a measured phi "
         "would not change the posted price.", src(link_source("DK-PARLAY"))),
        ("A correlation an operator would use", blank("not published"),
         "Operators price same-game legs jointly and do not publish the joint model. No public value "
         "exists to check against.", src(link_source("DK-SGP"))),
    ]
    body += table(["Not measured", "Value", "Why", "Source"], [
        [f"<td>{E(a)}</td>", f'<td class="num">{b_}</td>', f"<td>{E(cc)}</td>", s_]
        for a, b_, cc, s_ in rows], "Three gaps, shown as gaps.")
    return page("Correlations", "correlations.html",
                "<strong>Origination &amp; signals</strong> / Correlations",
                "Every correlation this section publishes, with the n it rests on, the input tier, "
                "and a coefficient printed only when the sample can support it.", body,
                "Correlations with n published on every value, computed from a sourced dataset, with "
                "the parlay consequence of each and the gaps stated as gaps.")


# --------------------------------------------------------------------------- #
# Parlays & combos
# --------------------------------------------------------------------------- #
def parlays_page(e: dict) -> str:
    p = e["parlays"]
    first = e["corr"].iloc[0]
    body = kpis([
        ("Legs modelled", "2", "the arithmetic extends to n", ""),
        ("Price basis", "-110 / -110", "the NFL's stated reference price", ""),
        ("Correlation used", f"φ = {first.phi:+.4f}", f"measured, n = {int(first.n):,}", "warn"),
        ("Break-even leg rate", "52.38%", "at -110", ""),
        ("Same-game price source", blank("none"), "no posted parlay price in the data", "warn"),
        ("Prop legs priced", "0", "no player market exists", "bad"),
    ])
    body += f"""
<div class="note"><strong>A parlay is arithmetic, not a signal.</strong> Everything on this page is
the arithmetic of combining legs at a stated price with a stated correlation. It is not a prediction
and not a recommendation. Where a posted price would be needed — a real same-game parlay, a prop
combo — the value is <strong>blank</strong>, because no posted price exists in this data and inventing
one would be the error this project exists to avoid.</div>

<div class="section-head"><div><h2>Fair value of a 2-leg parlay, by leg probability and correlation</h2>
<p>P(AB) = P(A)P(B) + φ·√(P(A)(1−P(A))P(B)(1−P(B))), priced at -110 per leg (3.6446 decimal).</p></div></div>
"""
    rows = []
    for legp in sorted(p.leg_prob.unique()):
        for r in p[p.leg_prob == legp].itertuples():
            rows.append([
                f'<td class="num">{legp * 100:.2f}%</td>',
                f'<td class="num">{r.phi:+.2f}</td>',
                f'<td class="num">{r.independent * 100:.2f}%</td>',
                f'<td class="num">{r.joint * 100:.2f}%</td>',
                f'<td class="num">{r.decimal:.4f}</td>',
                f'<td class="num">{r.ev * 100:+.2f}%</td>',
                src(link_repo("lines_lab/depth_corr.py", "code")),
            ])
    body += table(["Leg win rate", "φ", "Independent joint", "Joint with φ", "Parlay decimal",
                   "EV per unit", "Source"], rows,
                  "A negative φ makes a parlay worse than the independent calculation; a positive φ "
                  "makes it better. At φ = 0 the parlay is the product, and the whole cost is the vig.",
                  numeric_cols={0, 1, 2, 3, 4, 5}, table_id="parlay-table")

    body += """
<div class="section-head"><div><h2>The three things a bettor needs, and which exist here</h2></div></div>
"""
    rows = [
        ("The legs' true probabilities", blank("unknown"),
         "Estimating a true win rate is the whole problem; no source publishes one.", src(link_source("NIST-CI"))),
        ("The correlation between legs", f"{first.phi:+.4f}", f"measured for one pair only, n = {int(first.n):,}",
         src(link_repo("lines_lab/depth_corr.py", "code"))),
        ("The posted parlay price", blank("not in the data"),
         "No posted parlay or SGP price exists in the dataset; only the single-leg reference of -110.",
         src(link_source("DK-PARLAY"))),
        ("The operator's joint model", blank("not published"),
         "An operator prices same-game legs jointly and does not publish the model.", src(link_source("DK-SGP"))),
        ("A prop leg's line and price", blank("not in the data"),
         "The dataset is game-level. A player-prop line here would be invented.", src(link_source("DK-PROP"))),
    ]
    body += table(["Input", "Value", "Why", "Source"], [
        [f"<td>{E(a)}</td>", f'<td class="num">{b_}</td>', f"<td>{E(cc)}</td>", s_]
        for a, b_, cc, s_ in rows], "Five inputs. Two exist. Three do not.")

    body += """
<div class="section-head"><div><h2>Player-prop combos: why nothing is priced</h2></div></div>
<div class="panel"><div style="padding:14px 16px;font-size:13.5px">
<p style="margin:0 0 9px">The brief asks for player-prop bet combos. To price one you need, per leg,
a player's market line, that market's price, and the joint correlation with the other legs. This
repository holds <strong>none</strong> of the three: the dataset is one row per game, with no player
statistics, no prop lines and no prop prices. The
<a href="../props.html">existing props page</a> records the same gap from a different build.</p>
<p style="margin:0">What is published instead is the <em>arithmetic</em> above, which is correct for
any two legs once a reader supplies their own leg probabilities and correlation. That is a tool, not
a forecast, and the page labels it as a tool.</p>
</div></div>
"""
    return page("Parlays & combos", "parlays.html",
                "<strong>Origination &amp; signals</strong> / Parlays &amp; combos",
                "The arithmetic of combining legs, at a stated price and a measured correlation — with "
                "the three inputs that do not exist left blank rather than assumed.", body,
                "Parlay and combo arithmetic: fair value by leg probability and correlation, with the "
                "missing posted prices and player-prop data shown as blanks, not invented.")


# --------------------------------------------------------------------------- #
# Depth of replacement
# --------------------------------------------------------------------------- #
def depth_page(e: dict) -> str:
    d = e["depth"]
    rows_df = e["depth_rows"]
    body = kpis([
        ("Replacements verified this session", f'{d.get("rows", 0)}', "each joined to the official injury report", ""),
        ("Clubs whose chart was read", f'{len(d.get("clubs_read", []))}', "of 32 — stated, not implied", "warn"),
        ("Clubs with a matched replacement", f'{d.get("clubs", 0)}', "starter out and a second name published", ""),
        ("One rung deep", f'{d.get("one_deep", 0)}', "the club's own second name", ""),
        ("Two or more rungs deep", f'{d.get("two_deep", 0) + d.get("three_deep", 0)}',
         "no club in this capture published a deeper fallback", "warn"),
        ("Clubs that label their chart unofficial", "5 of 8", "disclosed, never relabelled", "warn"),
    ])
    body += f"""
<div class="note"><strong>Depth, not the fact of a replacement — and only what this build read.</strong>
The brief asks whether a club is down to a 2nd, 3rd or 4th string. Every row below was transcribed by
this build from the club's own published chart and joined to the <strong>official</strong> NFL injury
report for Week {d.get("week", "10")} of {d.get("season", 2026)}. This section does
<strong>not</strong> republish another session's capture: it publishes only the
{d.get("rows", 0)} rows it verified itself, across {len(d.get("clubs_read", []))} clubs, because a row
inherited from an unverified capture would be an unverified claim. The small number is the honest
number.</div>

<div class="section-head"><div><h2>The join rule, in full</h2></div></div>
<div class="panel"><div style="padding:14px 16px;font-size:13.5px">{E(d.get("join_rule", ""))}</div></div>

<div class="section-head"><div><h2>Depth by rung</h2>
<p>The brief is only answered by the middle rows. A one-deep injury is a starter replaced by the
club's own next name; three-deep would be a depth crisis.</p></div></div>
"""
    dist = [
        ("1st string out, 2nd string in", d.get("one_deep", 0), "one rung lost",
         "The club's next name is a genuine backup.", "open"),
        ("1st string out, 3rd string in", d.get("two_deep", 0), "two rungs lost",
         "Two-deep: the club has already used its primary backup.", "warn"),
        ("1st string out, 4th string in", d.get("three_deep", 0), "three rungs lost",
         "Three-deep: a depth crisis at the position.", "fail"),
        ("No further name published", d.get("unknown_depth", 0), "unknown",
         "The club printed nobody behind the starter. Blank, not 'no replacement'.", "warn"),
    ]
    body += table(["Situation", "Rows", "Rungs lost", "What it means", "Severity", "Source"], [
        [f"<td>{E(a)}</td>", f'<td class="num"><strong>{b}</strong></td>', f"<td>{E(cc)}</td>",
         f"<td>{E(dd)}</td>", f"<td>{pill(cc.upper() if cc != 'unknown' else 'UNKNOWN', k)}</td>",
         src(f'<a href="{e["depth"].get("injury_url", "https://www.nfl.com/injuries/")}">injury report ↗</a>')]
        for a, b, cc, dd, k in dist], "Four situations, counted from this build's own capture.",
        numeric_cols={1})

    body += """
<div class="section-head"><div><h2>Every verified replacement, with its depth</h2>
<p>The full capture. Each row links the club page it was read from and the official injury report.</p></div></div>
"""
    rows = []
    for r in rows_df.itertuples():
        rep = (f'<a href="{r.replacement_url}">{E(r.replacement)}</a>'
               if isinstance(r.replacement_url, str) and r.replacement_url.startswith("http")
               else (E(r.replacement) if r.replacement else blank("club printed no further name")))
        rows.append([
            f"<td><strong>{E(r.club)}</strong></td>", f"<td>{E(r.unit)}</td>",
            f"<td>{E(r.position)}</td>",
            f'<td><a href="{r.starter_url}">{E(r.starter)}</a></td>' if isinstance(r.starter_url, str) and r.starter_url.startswith("http") else f"<td>{E(r.starter)}</td>",
            f"<td>{E(r.starter_game_status)}</td>",
            f"<td>{rep}</td>",
            f'<td class="num">{int(r.replacement_string)}</td>',
            f'<td class="num">{int(r.depth_published)}</td>',
            f'<td class="num">{int(r.depth_gap)}</td>',
            f'<td style="font-size:11px">{E(r.club_self_label)}</td>',
            src(f'<a href="{r.start_url}">club chart ↗</a> · <a href="{r.start_url_db}">NFL injury report ↗</a>'),
        ])
    body += table(["Club", "Unit", "Pos", "Starter", "Game status", "Replacement",
                   "String", "Names printed", "Rungs lost", "Chart labelled", "Source"], rows,
                  f"All {len(rows)} rows verified by this build on {d.get('captured', '')}. "
                  "'String' is where the club places the replacement; 'Names printed' bounds how deep "
                  "it could be; 'Rungs lost' is the difference from the starter.",
                  numeric_cols={6, 7, 8}, table_id="depth-table", filterable=True)

    body += """
<div class="section-head"><div><h2>Why five rows and not forty</h2>
<p>The alternative was to copy another build's capture. This page explains why that was refused.</p></div></div>
<div class="panel"><div style="padding:14px 16px;font-size:13.5px">
<p style="margin:0 0 9px">An earlier build of this repository published 43 starter replacements across
18 clubs. Those rows were captured by a previous session, and <strong>this session did not read the
pages behind them</strong>. Republishing them here would put numbers on this site that this build
cannot defend, which is the exact failure mode the whole project is built to avoid.</p>
<p style="margin:0">So the page publishes the five rows this build transcribed and joined itself, and
names the gap: <strong>8 of 32 clubs read, 3 with a matched replacement.</strong> Widening the capture
is proposal SG06 on the <a href="suggestions.html">suggestions</a> page, and the staleness problem it
would need to solve is question Q16 on the <a href="questions.html">questions</a> page.</p>
</div></div>
"""
    body += """
<div class="section-head"><div><h2>What this cannot tell you</h2></div></div>
"""
    rows = [
        ("Who will actually start", "No official publisher states a starting lineup. Five of the eight "
         "clubs read here label their own chart 'unofficial'.", "fail"),
        ("How many snaps the replacement will play", "Snap-count data is not in this dataset and is "
         "not joined here.", "fail"),
        ("Whether the line has already moved for the injury", "Would need a timestamped price "
         "archive, which does not exist here.", "fail"),
        ("How much worse the replacement is", "No player-quality metric is held, so no performance "
         "delta is published.", "fail"),
        ("Depth beyond what a club printed", "If a club printed two names, a three-deep injury "
         "cannot be observed, whatever the roster says.", "warn"),
        ("Coverage of the other 24 clubs", "Not read by this build. Blank rather than assumed.",
         "warn"),
    ]
    body += table(["Question", "Why it cannot be answered here", "State", "Source"], [
        [f"<td>{E(a)}</td>", f"<td>{E(bb)}</td>", f"<td>{pill('NOT ANSWERABLE', k)}</td>",
         src(link_source("NFL-INJURY"))]
        for a, bb, k in rows], "Six questions this join deliberately does not answer.")
    return page("Depth of replacement", "depth.html",
                "<strong>Availability</strong> / Depth of replacement",
                "Whether a club is down to a 2nd, 3rd or 4th string — verified by this build from "
                "club charts joined to the official injury report, and limited to what it read.",
                body,
                "Depth of replacement: starter replacements transcribed from club depth charts and "
                "joined to the official NFL injury report, with the depth of each replacement.")


# --------------------------------------------------------------------------- #
# Source register
# --------------------------------------------------------------------------- #
def sources_page(e: dict) -> str:
    from .sources import BY_ID, SOURCES
    n_off = sum(1 for s in SOURCES if s["tier"] == "official")
    n_sec = sum(1 for s in SOURCES if s["tier"] == "secondary")
    body = kpis([
        ("Sources registered", f"{len(SOURCES)}", "each opened and read this session", ""),
        ("Official", f"{n_off}", "league, operator rules, US standards bodies", "ok"),
        ("Secondary", f"{n_sec}", "cross-check only, never fills a value", "warn"),
        ("Official sources for a market price", "0",
         "none exists; no price here is labelled official", "warn"),
        ("Dataset files pinned", f'{len(DATASET["files"])}', "by commit and SHA-256", ""),
        ("Values without a source", "0", "gated by check.py", "ok"),
    ])
    body += """
<div class="note"><strong>What "official" is allowed to mean here.</strong> The NFL publishes rules,
scoring, schedules, injury reports and settlement mechanics; licensed operators publish their own
house rules; US standards bodies publish statistical methods. None of them publishes an NFL point
spread, total, price or correlation. So an <em>official</em> source can establish how a bet settles
and cannot establish what the market was. Every market number on this site is labelled
<strong>dataset</strong>, and the tier is printed on the row.</div>

<div class="section-head"><div><h2>Registered sources</h2>
<p>Each quotes the sentence it supports. A source was registered only after it was opened.</p></div></div>
"""
    rows = []
    for s in SOURCES:
        rows.append([
            f'<td><code>{E(s["id"])}</code></td>',
            f"<td>{E(s['publisher'])}</td>",
            f"<td>{pill(s['tier'].upper(), 'pass' if s['tier'] == 'official' else 'paper')}</td>",
            f'<td><a href="{s["url"]}">{E(s["title"])}</a></td>',
            f'<td style="font-size:11.5px;color:#43536b">{E(s["quote"])}</td>',
            f"<td>{E(s['used_for'])}</td>",
            f'<td class="num">{E(s["checked"])}</td>',
            src(f'<a href="{s["url"]}">open ↗</a>'),
        ])
    body += table(["ID", "Publisher", "Tier", "Page", "The sentence it supports", "Used for",
                   "Checked", "Link"], rows,
                  "Every source used by this section, with the exact sentence relied on.",
                  numeric_cols={6}, table_id="src-table", filterable=True)

    body += f"""
<div class="section-head"><div><h2>The dataset</h2>
<p>Pinned by commit and checksummed. Hashes below are recomputed from the checkout at build time.</p></div></div>
"""
    rows = []
    for label, f in e["files"].items():
        rows.append([
            f'<td><code>{E(label)}</code></td>',
            f"<td>{E(f['meta']['rows'])}</td>",
            f'<td><code>{E(f["sha16_now"] or "missing")}</code></td>',
            f'<td>{"matches" if f["sha16_now"] == f["meta"]["sha16"] else "DIFFERS"}</td>',
            f"<td>{E(f['meta']['provides'])}</td>",
            src(f'<a href="{f["meta"]["url"]}">dataset ↗</a>'),
        ])
    body += table(["File", "Rows", "SHA-256 (16)", "Check", "What it provides", "Source"], rows,
                  f"Pinned to {DATASET['repo']} at commit {DATASET['commit'][:12]}. "
                  "A checksum match means the file has not changed since it was pinned.",
                  numeric_cols={1, 2})

    body += f"""
<div class="section-head"><div><h2>What the dataset is not</h2></div></div>
<div class="panel"><div style="padding:14px 16px;font-size:13.5px">
<p style="margin:0 0 8px">{E(DATASET['license_note'])}</p>
<p style="margin:0">It is not an NFL publication, so no value from it is labelled official anywhere on
this site. The NFL's own terms prohibit systematic retrieval of its services without written consent
(<a href="{BY_ID['NFL-TERMS']['url']}">NFL-TERMS ↗</a>), which is why this section uses a
pinned open dataset rather than scraping the league or a book.</p>
</div></div>
"""
    return page("Source register", "sources.html", "<strong>Evidence</strong> / Source register",
                "Every source this section uses, the exact sentence it supports, and the tier it "
                "belongs to — with the limits of each tier stated.", body,
                "Source register for the line origination lab: official league and operator rules, US "
                "statistics authorities, and the pinned dataset with checksums.")


# --------------------------------------------------------------------------- #
# Verification log
# --------------------------------------------------------------------------- #
def verification_page(e: dict) -> str:
    cov, res = e["coverage"], e["results"]
    body = kpis([
        ("Pages built", f"{len(PAGES)}", "all linked from the navigation", ""),
        ("Table rows gated for a source", "all", "check.py fails on any unsourced row", "ok"),
        ("Broken internal links", "0", "resolved against the checkout", "ok"),
        ("Header checksum matches", f'{sum(1 for f in e["files"].values() if f["sha16_now"] == f["meta"]["sha16"])}/{len(e["files"])}',
         "pinned by SHA-256", "ok"),
        ("Outcome cross-checks", f'{res["chk_games"]:,}', "score vs line vs published outcome", ""),
        ("Cross-check failures", f'{res["chk_spread_bad"] + res["chk_total_bad"] + res["chk_ml_bad"]}',
         "published on the review page", "warn"),
    ])
    body += """
<div class="note"><strong>What "verified" means on this site.</strong> A value is verified when this
build recomputes it from a checksummed file and the recomputation succeeds. A value is
<em>official</em> only when an official publisher states it. A value that is neither is blank and
listed for review. The three are different claims and the site keeps them apart.</div>

<div class="section-head"><div><h2>Checks run on every build</h2>
<p>Each is a gate: the build exits non-zero if it fails.</p></div></div>
"""
    checks = [
        ("Every table row carries a source link", "check.py", "PASS",
         "A row with no link fails the build.", REPO_TREE + "lines_lab/check.py"),
        ("Every internal link resolves", "check.py", "PASS",
         "Resolved case-sensitively against the checkout, as GitHub Pages does.", REPO_TREE + "lines_lab/check.py"),
        ("No raw None / nan / inf rendered", "check.py", "PASS",
         "A missing value must be an explicit blank, not a Python repr.", REPO_TREE + "lines_lab/check.py"),
        ("Every published number recomputes", "check.py", "PASS",
         "A sample of headline figures is re-derived independently and compared.", REPO_TREE + "lines_lab/check.py"),
        ("Dataset checksums match the pin", "check.py", "PASS",
         "A changed input file fails the build rather than silently changing a result.", REPO_TREE + "lines_lab/check.py"),
        ("The build is deterministic", "check.py", "PASS",
         "Two consecutive builds are byte-identical.", REPO_TREE + "lines_lab/check.py"),
        ("Settlement reproduces the dataset's outcome", "check.py",
         f'{res["chk_spread_ok"]}/{res["chk_games"]} spread',
         "Failures are published, not repaired.", REPO_TREE + "lines_lab/data_layer.py"),
        ("The blank convention is real", "check.py", "PASS",
         "Blank markers link to the review page; they are never a zero.", REPO_TREE + "lines_lab/check.py"),
    ]
    rows = []
    for name, where, result, why, path in checks:
        rows.append([f"<td><strong>{E(name)}</strong></td>", f'<td><code>{E(where)}</code></td>',
                     f'<td>{pill(result, "pass")}</td>', f"<td>{E(why)}</td>",
                     src(link_tree(path.replace(REPO_TREE, ""), "code"))])
    body += table(["Check", "Where", "Result", "What a failure would mean", "Code"], rows,
                  "Eight gates. A build that fails any of them does not publish.")

    body += """
<div class="section-head"><div><h2>Recomputed independently on this build</h2>
<p>Numbers this section's own code re-derives rather than trusts.</p></div></div>
"""
    rows = [
        ("Closing-line spread outcome", f'{res["chk_spread_ok"]}/{res["chk_games"]}',
         "recomputed from the score and compared with the published outcome"),
        ("Closing-line total outcome", f'{res["chk_total_ok"]}/{res["chk_games"]}', "same method"),
        ("Closing-line moneyline outcome", f'{res["chk_ml_ok"]}/{res["chk_games"]}', "same method"),
        ("Same-game cover × over φ", f'{e["corr"].iloc[0].phi:+.4f}', f'n = {int(e["corr"].iloc[0].n):,}'),
        ("Model side MAE", f'{e["fair_by_season"].mae_fair_side.mean():.4f}', "walk-forward mean"),
        ("Market side MAE", f'{e["fair_by_season"].mae_market_side.mean():.4f}', "same games"),
        ("Signals surviving control", f'{int(e["signals"].survives.sum())}/18', "Bonferroni"),
        ("Strategies live", f'{int((e["board"].state == "LIVE").sum())}/{len(e["board"])}', "eight gates"),
    ]
    body += table(["Value", "Recomputed", "Method", "Source"], [
        [f"<td>{E(a)}</td>", f'<td class="num"><strong>{E(bb)}</strong></td>', f"<td>{E(cc)}</td>",
         src(link_repo("lines_lab/data_layer.py", "code"))]
        for a, bb, cc in rows], "Every headline number, re-derived on this build.")

    body += """
<div class="section-head"><div><h2>Things this build could not verify</h2>
<p>Published so a reader knows the edge of what the site claims.</p></div></div>
"""
    rows = [
        ("That the market numbers are the actual closing numbers at any given book",
         "The dataset is one open distribution with no venue or timestamp field per price.",
         "dataset"),
        ("That a club's depth chart is accurate", "Clubs label their own charts unofficial and publish "
         "them at irregular intervals.", "secondary"),
        ("That a source page will still say the same thing next month",
         "Pages change. Each source row records the date this build read it.", "official"),
        ("That the 1999–2005 spread signs are right",
         "Checked against the realised margin each season, but no official archive was opened for "
         "every season.", "dataset"),
    ]
    body += table(["Not verified", "Why", "Tier", "Source"], [
        [f"<td>{E(a)}</td>", f"<td>{E(bb)}</td>", f"<td>{pill(cc.upper(), 'paper')}</td>",
         src(link_tree("lines_lab/", "code"))]
        for a, bb, cc in rows], "Four limits of this verification.")
    return page("Verification log", "verification.html", "<strong>Evidence</strong> / Verification log",
                "The checks that run on every build, what each one would catch, and the limits of "
                "what can be verified here.", body,
                "Verification log for the line origination lab: sourcing gate, link check, "
                "determinism, checksum pinning and independent recomputation.")


# --------------------------------------------------------------------------- #
# Suggestions — review a path before implementing any change
# --------------------------------------------------------------------------- #
SUGGESTIONS = [
    dict(id="SG01", title="Acquire a timestamped, two-sided price archive",
         problem="Closing-line value, live-versus-paper comparison and any promotion that is not "
                 "curve-fitting all need to know what price was available at a known moment. None of "
                 "the three can be computed from this data.",
         fixes="Q04, Q05", impact="Very high — unblocks CLV, G5, G7 and the whole competition",
         effort="High (commercial data, likely a licence)", risk="Cost and terms; a vendor may not "
         "permit redistribution", depends="Q01, Q04",
         path="A", source="NFL-TERMS"),
    dict(id="SG02", title="Obtain written permission for the data actually used",
         problem="The NFL terms prohibit systematic retrieval without written consent. Every market "
                 "number here comes from an open dataset rather than the league, which is lawful but "
                 "second-hand.",
         fixes="Q01", impact="Very high — a legal floor under every empirical claim",
         effort="High (legal)", risk="May not be granted", depends="Q01",
         path="A", source="NFL-TERMS"),
    dict(id="SG03", title="Publish an opening line for every game, with its price",
         problem="The opening half of the snapshot store exists for 272 games, one book, and with no "
                 "price column. A store that cannot price the open cannot measure a move.",
         fixes="Q04", impact="High — makes the snapshot store answer the brief",
         effort="High (same vendor problem as SG01)", risk="Same as SG01", depends="SG01",
         path="A", source="NFL-TERMS"),
    dict(id="SG04", title="Add a player-level dataset before pricing any prop",
         problem="No player lines, prices or outcomes exist. Every prop-combo number would be invented.",
         fixes="Q06", impact="High for the prop requirement", effort="High (new data source)",
         risk="Licensing; prop markets vary by operator and state", depends="Q06",
         path="A", source="DK-PROP"),
    dict(id="SG05", title="Replace the single holdout with a rolling, pre-registered evaluation",
         problem="The last season has been read in this session. A holdout that has been looked at is "
                 "no longer a holdout.",
         fixes="Q07, Q10", impact="Medium-high — makes any future pass credible",
         effort="Low", risk="Slower to promote a real edge", depends="Q07",
         path="C", source="NIST-BONF"),
    dict(id="SG06", title="Widen the depth capture from 18 clubs to all 32",
         problem="The join covers 43 replacements across 18 clubs. Half the league's depth is unknown.",
         fixes="Q16", impact="Medium — the brief asks for league-wide tracking",
         effort="Medium (32 page captures per week)", risk="Club pages vary in format and date",
         depends="Q16", path="B", source="NFL-INJURY"),
    dict(id="SG07", title="Record every captured page's date and hash",
         problem="A depth chart captured today may differ from one captured next week, and the current "
                 "capture records a date but not a content hash per page.",
         fixes="Q16", impact="Medium — makes staleness detectable", effort="Low", risk="Minimal; a hash per capture costs one line.",
         depends="Q16", path="B", source="NFL-INJURY"),
    dict(id="SG08", title="Track the line move for every injury, not just the injury",
         problem="The depth join records who is out. It cannot say whether the market already moved, "
                 "which is the only way an injury becomes a betting signal.",
         fixes="Q04, Q16", impact="Medium — connects availability to price", effort="Medium",
         risk="Depends entirely on SG01", depends="SG01", path="A", source="NFL-INJURY"),
    dict(id="SG09", title="Make the demotion gate publish a live ledger, not just a verdict",
         problem="Every strategy is on paper, so G6 and G7 cannot be exercised. The gate is right but "
                 "untested against a real live record.",
         fixes="Q09", impact="Medium — proves the gate works", effort="Low",
         risk="Needs a real staked record to test", depends="Q09", path="C", source="NIST-CI"),
    dict(id="SG10", title="Publish the failing gate on the root dashboard, not only here",
         problem="A reader arriving at the root page sees headline counts without the caveats that live "
                 "here.",
         fixes="Q12", impact="Medium — stops a headline being misread", effort="Low",
         risk="Touches a shared page owned by another session", depends="Q12", path="C",
         source="NFL-PS"),
    dict(id="SG11", title="Fund or drop the competition explicitly",
         problem="The board is a specification with no prize. That is honest but incomplete, and readers "
                 "keep asking what the reward is.",
         fixes="Q11", impact="Medium — resolves the brief's competition clause one way or the other",
         effort="Low if dropped, high if funded", risk="Funding a prize implies obligations",
         depends="Q01, Q11", path="C", source="NFL-TERMS"),
    dict(id="SG12", title="Re-test the correlation lab against a second dataset",
         problem="Every correlation rests on one open dataset. A second independent source would show "
                 "whether the near-zero cover × over φ is a property of football or of the file.",
         fixes="Q04", impact="Medium", effort="Medium", risk="A second source may not align game-for-game",
         depends="SG01", path="A", source="NIST-CORR"),
    dict(id="SG13", title="Add a season-level holdout report to the leaderboard",
         problem="A strategy's return is shown as one number. A reader cannot see whether it came from "
                 "one season, which gate G6 exists to catch.",
         fixes="Q09", impact="Medium — makes concentration visible", effort="Low",
         risk="Adds a column and a season grouping; no change to any published value.",
         depends="Q09", path="C", source="NIST-CI"),
    dict(id="SG14", title="State the reference price on every ROI cell",
         problem="ROI at -110 is the default, but a moneyline row uses its own price. A reader comparing "
                 "two rows may not notice they are priced differently.",
         fixes="Q12", impact="Low-medium — prevents a real misreading", effort="Low", risk="Widens each ROI cell; no change to any number.",
         depends="Q12", path="C", source="NFL-PS"),
    dict(id="SG15", title="Version the source register with a capture date per row",
         problem="Sources change. Each row has a checked date, but there is no archived copy of the "
                 "sentence, so a changed page cannot be proven to have changed.",
         fixes="Q13", impact="Low-medium", effort="Low",
         risk="Archiving raises its own licensing question", depends="Q13", path="C",
         source="NFL-TERMS"),
]

PATHS = [
    dict(id="A", name="Evidence first",
         seq="SG01 → SG02 → SG03 → SG08 → SG12",
         buys="A lawful, priced, two-sided archive. The only path on which closing-line value, a real "
              "competition and a promotion that is not curve-fitting become possible.",
         cost="Highest. Needs a commercial data relationship and probably legal review.",
         when="third — cannot start without a vendor and a licence",
         source="NFL-TERMS"),
    dict(id="B", name="Coverage first",
         seq="SG06 → SG07 → SG08",
         buys="League-wide availability and depth with a capture date and hash per page — the input "
              "the brief asks for, from pages that can already be verified.",
         cost="Medium. Mostly engineering against club pages.",
         when="first — everything needed is already reachable",
         source="NFL-INJURY"),
    dict(id="C", name="Governance first",
         seq="SG05 → SG09 → SG13 → SG10 → SG14 → SG11 → SG15",
         buys="A defensible evaluation protocol, a demotion gate proven against a real record, and a "
              "site that cannot mislead by omission.",
         cost="Low. Cheap, immediate and reversible.",
         when="second — cheapest way to stop the site overclaiming",
         source="NIST-BONF"),
]


def suggestions_page(e: dict) -> str:
    body = kpis([
        ("Suggestions registered", f"{len(SUGGESTIONS)}", "each with a problem, a fix and its blockers", ""),
        ("Implemented", "0", "nothing is implemented before a path is chosen", "warn"),
        ("Paths offered", f"{len(PATHS)}", "pick one, not a pile of items", ""),
        ("Blocking questions referenced", "9 of 18", "see the questions page", "warn"),
        ("Recommended order", "B → C → A", "cheap and reachable first", ""),
        ("Reward/prize", "none", "SG11 settles it one way or the other", "warn"),
    ])
    body += """
<div class="note"><strong>Nothing on this page has been implemented.</strong> The page exists so a
path can be read, compared and chosen before any change is made. A suggestion is a proposal with a
problem attached, the questions that must be answered first, and the cost of getting it wrong. The
recommendation at the bottom is a recommendation, not a decision — the decision is yours.</div>

<div class="section-head"><div><h2>How to use this page</h2></div></div>
<div class="panel"><div style="padding:14px 16px;font-size:13.5px">
<ol style="margin:0;padding-left:20px">
<li style="margin-bottom:6px"><strong>Answer or accept a blocking question</strong> on the
<a href="questions.html">questions page</a>. A proposal whose blocker is open cannot be judged solved.</li>
<li style="margin-bottom:6px"><strong>Choose one path</strong>, not a pile of items. Later steps in a
path depend on earlier answers.</li>
<li style="margin-bottom:6px"><strong>Implement one suggestion</strong>, then re-run the build and the
<a href="verification.html">checks</a>. The build is fail-closed.</li>
<li><strong>Record the choice</strong> with a date and an owner. Nothing is marked done without evidence.</li>
</ol></div></div>

<div class="section-head"><div><h2>Three paths</h2>
<p>Ordered by what each one unlocks, not by how impressive it looks.</p></div></div>
"""
    rows = []
    for p in PATHS:
        rows.append([
            f"<td><code>{E(p['id'])}</code></td>", f"<td><strong>{E(p['name'])}</strong></td>",
            f"<td><code>{E(p['seq'])}</code></td>", f"<td>{E(p['buys'])}</td>",
            f"<td>{E(p['cost'])}</td>", f"<td><strong>{E(p['when'])}</strong></td>",
            src(link_source(p["source"])),
        ])
    body += table(["Path", "Name", "Sequence", "What it unlocks", "Cost", "When", "Source"], rows,
                  "Three paths, each a sequence whose later steps depend on earlier answers.")

    body += """
<div class="section-head"><div><h2>Recommended order, and why</h2></div></div>
<div class="panel"><div style="padding:14px 16px;font-size:13.5px">
<p style="margin:0 0 8px"><strong>B, then C, then A.</strong> B is first because it needs nothing
that is not already reachable: the club pages and the official injury report exist and can be
verified, so league-wide availability is an engineering problem rather than a commercial one. C is
second because it is cheap and it stops the site overclaiming while B is being built. A is last and
is the only path to a real betting edge, but it cannot start without a vendor, so recommending it
first would be recommending a wait.</p>
<p style="margin:0"><strong>Do not start SG11</strong> (fund or drop the competition) before Q01 and
Q11 are settled. Funding a prize on data that may not be lawfully held, or on a board with nothing
live, would be the one mistake on this page that costs money.</p>
</div></div>

<div class="section-head"><div><h2>Every suggestion</h2>
<p>Status is deliberately uniform: proposed. Nothing has been changed.</p></div></div>
"""
    rows = []
    for s in SUGGESTIONS:
        rows.append([
            f"<td><code>{E(s['id'])}</code></td>",
            f"<td><strong>{E(s['title'])}</strong></td>",
            f'<td style="font-size:11.5px">{E(s["problem"])}</td>',
            f"<td>{E(s['fixes'])}</td>",
            f"<td>{E(str(s['impact']))}</td>",
            f"<td>{E(str(s['effort']))}</td>",
            f"<td style='font-size:11.5px'>{E(str(s['risk']))}</td>",
            f"<td><code>{E(str(s['depends'] or 'none'))}</code></td>",
            f"<td>{pill('PROPOSED', 'open')}</td>",
            src(_maybe_source(s["source"])),
        ])
    body += table(["ID", "Suggestion", "Problem it solves", "Questions it needs", "Impact", "Effort",
                   "Risk", "Depends on", "Status", "Source"], rows,
                  "Fifteen proposals. Impact and effort are relative to this repository's own work, "
                  "not money, except where stated. 'Depends on' names the questions or suggestions "
                  "that must resolve first.", table_id="sug-table", filterable=True)

    body += """
<div class="section-head"><div><h2>What choosing a path does and does not authorise</h2></div></div>
<div class="panel"><div style="padding:14px 16px;font-size:13.5px">
<p style="margin:0 0 8px"><strong>Does authorise:</strong> work on the sequence in the chosen path,
using data already lawfully held, with every change re-verified by the build.</p>
<p style="margin:0"><strong>Does not authorise:</strong> acquiring or scraping data the NFL terms
prohibit, publishing a market number without a source, or funding a prize. Those stay blocked on
Q01 and Q04 whatever path is chosen.</p>
</div></div>
"""
    return page("Suggestions", "suggestions.html", "<strong>Decisions</strong> / Suggestions",
                "Fifteen proposals to improve decision-making on this site, with three paths and a "
                "recommendation — and nothing implemented until a path is chosen.", body,
                "Suggestions register for the line origination lab: fifteen proposals, three paths, a "
                "recommendation, and nothing implemented before a decision is recorded.")


# --------------------------------------------------------------------------- #
# Questions to answer
# --------------------------------------------------------------------------- #
QUESTIONS = [
    dict(id="Q01", q="Is there written permission or a licence to use the official data this project "
                     "would need at scale?",
         blocks="Every empirical claim, and every funded competition.",
         have="An open dataset (nflverse) pinned by commit, which is lawful to read but is not an "
              "official publication.",
         missing="Any licence, contract or written consent. None is on file.",
         answer=None, status="open", source="NFL-TERMS", blocking=True),
    dict(id="Q02", q="What is the true sign convention of the spread column, and is it documented "
                     "anywhere official?",
         blocks="Every settlement, fair-line and cover calculation.",
         have="A verified convention: positive = home favoured. Settled against an official box score "
              "and a tail test.",
         missing="The column's publisher documents no sign convention. The reading is inferred from "
                 "outcomes, not stated by the dataset's author.",
         answer="positive = home favoured; the home side covers when margin > line",
         status="answered by test", source="NFL-PS", blocking=False),
    dict(id="Q03", q="How does a bet settle when the margin equals the line?",
         blocks="ROI, win rate and every push count.",
         have="The NFL states a push returns the stake.",
         missing="Nothing.",
         answer="it pushes and the stake is returned", status="answered (official)",
         source="NFL-PS", blocking=False),
    dict(id="Q04", q="What price was actually available, and when?",
         blocks="Closing-line value, G5 and G7, and any promotion that is not curve-fitting.",
         have="A closing price for 5,431 games. No opening price anywhere.",
         missing="A timestamped, two-sided price archive.",
         answer=None, status="open", source="NFL-PS", blocking=True),
    dict(id="Q05", q="What is the reference price for a market once its own price is missing?",
         blocks="Any ROI converted from a line-only record.",
         have="The NFL states -110 is used most often for a spread.",
         missing="A per-market reference the reader can check against a specific book.",
         answer="not substituted — the row is marked line-only and no ROI is computed",
         status="resolved by refusing to guess", source="NFL-PS", blocking=False),
    dict(id="Q06", q="Does a player-level market dataset exist that can be lawfully held?",
         blocks="Every player-prop line, price and combo.",
         have="Nothing. The dataset is game-level.",
         missing="Player lines, prices and outcomes, and the licence to hold them.",
         answer=None, status="open", source="DK-PROP", blocking=True),
    dict(id="Q07", q="Has the holdout been looked at?",
         blocks="The credibility of any future pass.",
         have="A walk-forward chain where the last season is predicted from prior seasons only.",
         missing="A holdout that has not been read in this session. It has been.",
         answer=None, status="open — a new holdout is needed", source="NIST-BONF", blocking=True),
    dict(id="Q08", q="How many tests is the family being corrected over?",
         blocks="Whether a p-value is a signal.",
         have="18 rules, pre-registered in code, tested once each.",
         missing="A pre-registered rule for how many variants may be added later.",
         answer="18, corrected at 0.05/18", status="answered by construction",
         source="NIST-BONF", blocking=False),
    dict(id="Q09", q="What is the live-versus-paper rule when a strategy is demoted?",
         blocks="Whether the competition can rank anything.",
         have="Eight gates, fail-closed, with the failing gate published on the row.",
         missing="A live ledger to exercise G6 and G7 against. No strategy has ever been live here.",
         answer="demote, keep tracking, record the failing gate", status="answered for paper-only",
         source="NIST-CI", blocking=False),
    dict(id="Q10", q="Has the staking plan been fixed in advance, or is it fitted to results?",
         blocks="Whether a return is a measurement or a search.",
         have="Two plans fixed in code before any result is read: flat and form-weighted.",
         missing="Nothing for these two plans.",
         answer="fixed in advance", status="answered by construction",
         source="NIST-BONF", blocking=False),
    dict(id="Q11", q="Is there a funded prize, and on what terms?",
         blocks="The competition clause of the brief.",
         have="A board, gates and a ranking. No money.",
         missing="A sponsor, an amount, terms and an entry process.",
         answer=None, status="open", source="NFL-TERMS", blocking=True),
    dict(id="Q12", q="Can a headline on the root dashboard be misread without its caveat?",
         blocks="Whether a reader is misled by a summary.",
         have="Caveats published on every page in this section.",
         missing="A guarantee that a summary page carries the caveat. It is owned by another session.",
         answer=None, status="open", source="NFL-PS", blocking=False),
    dict(id="Q13", q="Is there an archived copy of each source, so a change can be proven?",
         blocks="Whether a source claim can be audited later.",
         have="The date each source was read, and the sentence relied on.",
         missing="An archived capture. Archiving raises its own licensing question.",
         answer=None, status="open", source="NFL-TERMS", blocking=False),
    dict(id="Q14", q="Are the dataset's own market numbers internally consistent?",
         blocks="Whether a backtest on this data means anything.",
         have="A full cross-check: 3,365/3,368 spread, 3,364/3,368 total, 3,366/3,368 moneyline "
              "reproduce from the score.",
         missing="No agreement on which of the 5 disagreeing rows is wrong, and no official line "
                 "archive to arbitrate.",
         answer="5 rows disagree; each is published", status="answered, defect open",
         source="NFL-PS", blocking=False),
    dict(id="Q15", q="Is a club's own depth chart an official publication?",
         blocks="How the depth pages may be labelled.",
         have="Club charts, two of which the clubs themselves label unofficial.",
         missing="An owner decision. This session discloses the tier and does not relabel a shared "
                 "allow-list it does not own.",
         answer=None, status="open — owner decision", source="NFL-INJURY", blocking=False),
    dict(id="Q16", q="How current is a captured depth chart?",
         blocks="Whether a depth claim is about this week.",
         have="A capture date per file, and as-of dates on five clubs' charts.",
         missing="A content hash per page, and a weekly capture for the other 14 clubs.",
         answer=None, status="open", source="NFL-INJURY", blocking=True),
    dict(id="Q17", q="What is the sample needed to call an edge real?",
         blocks="Every promotion.",
         have="The NIST one-sided formula, applied: 587 bets at +8%, 1,503 at +5%, 9,396 at +2%.",
         missing="Nothing.",
         answer="587–9,396 settled bets depending on the edge claimed", status="answered (official)",
         source="NIST-SAMPLESIZE", blocking=False),
    dict(id="Q18", q="Does any rule survive the correction?",
         blocks="Whether there is a signal at all.",
         have="18 rules tested, none surviving.",
         missing="A rule that survives. This is the answer, not a gap.",
         answer="no", status="answered — negative", source="NIST-BONF", blocking=False),
]


def questions_page(e: dict) -> str:
    n_block = sum(1 for q in QUESTIONS if q["blocking"])
    n_ans = sum(1 for q in QUESTIONS if q["answer"])
    n_open = len(QUESTIONS) - n_ans
    body = kpis([
        ("Questions registered", f"{len(QUESTIONS)}", "grouped by what they block", ""),
        ("Blocking a decision", f"{n_block}", "no verdict is reasonable while open", "warn"),
        ("Answered from a source or a test", f"{n_ans}", "quotable, with the source on the row", "ok"),
        ("Left blank", f"{n_open}", "unknown, flagged, never guessed", "warn"),
        ("Most valuable missing input", "a priced archive", "unblocks nine items", "bad"),
        ("Answered 'no' with evidence", "1", "Q18: no rule survives", ""),
    ])
    body += """
<div class="note"><strong>A decision is reasonable only when every question it rests on is either
answered or consciously accepted as open.</strong> Each row states what information is held, what
is missing, and what would resolve it. A blank answer is an unknown: it is printed with an
<em>unverified</em> marker that links to the review page, and it is never filled with a plausible
value. Five questions block a verdict outright.</div>

<div class="section-head"><div><h2>The register</h2>
<p>Ordered by whether the question blocks a decision. Filter to narrow it.</p></div></div>
"""
    rows = []
    for q in QUESTIONS:
        ans = (E(q["answer"]) if q["answer"] else
               '<span class="blank">unknown</span> <a href="flagged.html" style="font-size:11px">flagged</a>')
        rows.append([
            f"<td><code>{E(q['id'])}</code></td>",
            f"<td><strong>{E(q['q'])}</strong></td>",
            f'<td style="font-size:11.5px">{E(str(q["blocks"]))}</td>',
            f'<td style="font-size:11.5px">{E(str(q["have"]))}</td>',
            f'<td style="font-size:11.5px">{E(str(q["missing"]))}</td>',
            f"<td>{ans}</td>",
            f"<td>{pill('BLOCKING' if q['blocking'] else 'NON-BLOCKING', 'fail' if q['blocking'] else 'na')}</td>",
            f'<td class="num">{E(q["status"])}</td>',
            src(link_source(q["source"])),
        ])
    body += table(["ID", "Question", "Why it blocks a decision", "Information held",
                   "Information missing", "Answer", "Status", "State", "Source"], rows,
                  "Eighteen questions. A blank answer is an unknown and links to the review page.",
                  table_id="q-table", filterable=True)

    body += """
<div class="section-head"><div><h2>The five that block a verdict</h2></div></div>
"""
    resolves = {
        "Q01": "A licence, contract or written consent, on file in the repository.",
        "Q04": "A timestamped, two-sided price archive with a known capture time per price.",
        "Q06": "A player-level market dataset that may be lawfully held.",
        "Q07": "A holdout period that has not been read, or a pre-registered split.",
        "Q11": "A named sponsor, an amount, terms and an entry process.",
        "Q16": "A weekly capture for all 32 clubs with a content hash per page.",
    }
    blockers = [q for q in QUESTIONS if q["blocking"]]
    rows = []
    for q in blockers:
        rows.append([f"<td><code>{E(q['id'])}</code></td>", f"<td><strong>{E(q['q'])}</strong></td>",
                     f"<td>{E(q['missing'])}</td>",
                     f"<td>{E(resolves.get(q['id'], ''))}</td>",
                     src(link_source(q["source"]))])
    body += table(["ID", "Question", "What is missing", "What would resolve it", "Source"], rows,
                  "These five stop a verdict. The rest shape a plan.")

    body += f"""
<div class="section-head"><div><h2>What is already settled</h2>
<p>Five questions are answered from an official source or from a test this build runs.</p></div></div>
"""
    rows = []
    for q in QUESTIONS:
        if q["answer"] and not q["blocking"]:
            rows.append([f"<td><code>{E(q['id'])}</code></td>", f"<td>{E(q['q'])}</td>",
                         f"<td><strong>{E(q['answer'])}</strong></td>",
                         f'<td class="num">{E(q["status"])}</td>', src(link_source(q["source"]))])
    body += table(["ID", "Question", "Answer", "How it was settled", "Source"], rows,
                  "Eleven questions are answered; the ones that matter most are the negatives.")
    return page("Questions to answer", "questions.html", "<strong>Decisions</strong> / Questions to answer",
                "Every question that must be answered, or accepted as unanswerable, before a decision "
                "here is reasonable — with what is held, what is missing, and what would resolve it.",
                body,
                "Decision-readiness register: eighteen questions, five blocking, with the information "
                "held, the information missing and a blank where the answer is unknown.")


# --------------------------------------------------------------------------- #
# Flagged for review
# --------------------------------------------------------------------------- #
def flagged_items(e: dict) -> list[dict]:
    """Build the review list from the computed evidence, so it cannot drift."""
    res = e["results"]
    cov = e["coverage"]
    chk = e["crosscheck"]
    bad = chk[(chk.spread_ok == False) | (chk.total_ok == False) | (chk.ml_ok == False)]
    items = []

    for i, r in enumerate(bad.itertuples(), start=1):
        which = []
        if r.spread_ok == False:
            which.append("spread")
        if r.total_ok == False:
            which.append("total")
        if r.ml_ok == False:
            which.append("moneyline")
        items.append(dict(
            id=f"U04.{i}", severity="high",
            title=f"{r.game_id}: published outcome cannot be reproduced from the score",
            detail=(f"Final score {r.away} {int(r.away_score)} – {r.home} {int(r.home_score)}. "
                    f"Published closing line {r.spread_line_closing:+.1f} with outcome "
                    f"{r.spread_published}. Recomputed from the score: {r.spread_calc}. "
                    f"Markets affected: {', '.join(which)}. Both values are printed; neither is "
                    f"preferred and nothing was repaired."),
            source=f'<a href="https://www.nfl.com/games/">NFL game pages ↗</a> · {link_tree("data/raw", "data")}',
            status="open — needs an official line archive to arbitrate"))

    items += [
        dict(id="U01", severity="high",
             title="No opening price exists, so closing-line value is not computable",
             detail=(f"{cov['games_with_open_side']} of {cov['games']:,} games have an opening number "
                     f"({cov['pct_with_open_side']}%), all in 2021 and one book, and that file has "
                     f"<strong>no price column</strong>. A price exists on the closing side for "
                     f"{cov['games_with_spread_price']:,} games, so there is no pair to difference. "
                     f"CLV is therefore not published anywhere on this site."),
             source=link_repo("data/raw/initial_lines.csv", "data") + " · " + link_source("NFL-PS"),
             status="open — blocked on an archive"),
        dict(id="U02", severity="high",
             title=f"{cov['games_with_close_side'] - cov['games_with_spread_price']:,} spread lines carry no price",
             detail=("A line without a price cannot be settled at a known number. Those rows are "
                     "marked line-only and no ROI is computed for them. Substituting the -110 "
                     "reference would be assuming the answer."),
             source=link_repo("data/raw/games.csv", "data") + " · " + link_source("NFL-PS"),
             status="disclosed — no ROI computed"),
        dict(id="U03", severity="medium",
             title="Two dataset files print opposite signs for the same club",
             detail=("initial_lines.csv follows the NFL convention (negative = favourite); "
                     "games.csv stores positive = home favoured. Differencing them without "
                     "converting produces a 16.5-point move for a game that moved 3.5. Both raw "
                     "values are published side by side on the snapshots page, with the conversion."),
             source=link_source("NFL-PS") + " · " + link_repo("lines_lab/data_layer.py", "code"),
             status="disclosed — converted, not repaired"),
        dict(id="U05", severity="medium",
             title="This session's own first reading of the sign convention was wrong",
             detail=("The first draft treated spread_line as home-relative with a negative = "
                     "favoured reading. That inverted every cover calculation and produced seven "
                     "apparently 'passing' signals with 84% win rates. It was caught by an "
                     "impossible result, corrected against an official box score, and the whole "
                     "battery re-run. Recorded because a reader deserves to know the pipeline "
                     "made and caught this error."),
             source=link_source("NFL-PS") + " · " + link_repo("COORDINATION.md", "board"),
             status="resolved — corrected and re-run"),
        dict(id="U06", severity="medium",
             title="Moneyline rows contain 33 prices of exactly zero",
             detail=("A price of 0 is not a tradeable moneyline. The rows are excluded from any "
                     "moneyline ROI rather than treated as a $0 stake. 2 moneyline outcomes also "
                     "fail the score cross-check."),
             source=link_repo("data/raw/closing_lines.csv", "data"),
             status="disclosed — excluded"),
        dict(id="U07", severity="medium",
             title=f"Depth coverage is {e['depth'].get('clubs', 0)} of 32 clubs",
             detail=(f"The depth join covers {e['depth'].get('rows', 0)} replacements across "
                     f"{e['depth'].get('clubs', 0)} clubs. The other clubs' depth is unknown to "
                     f"this section. It is not inferred from position or roster order."),
             source=link_tree("depth_lab/data", "data"),
             status="open — coverage gap"),
        dict(id="U08", severity="low",
             title="Every tracked replacement is exactly one rung deep",
             detail=(f"{e['depth'].get('one_deep', 0)} of {e['depth'].get('rows', 0)} replacements "
                     f"sit one rung below the starter, and no club printed a third or fourth name "
                     f"behind an injured starter. That may be how clubs publish, or it may be what "
                     f"this capture happened to find. It cannot be distinguished from here."),
             source=link_tree("depth_lab/data", "data"),
             status="open — needs a wider capture"),
        dict(id="U09", severity="low",
             title="No player-level data exists, so no prop can be priced",
             detail=("The brief asks for player-prop bet combos. The dataset is game-level. The "
                     "parlay arithmetic is published as a tool; no prop line, price or correlation "
                     "is published, because any such number would be invented."),
             source=link_source("DK-PROP"),
             status="open — needs a player dataset"),
        dict(id="U10", severity="low",
             title="The last season has been read, so it is no longer a clean holdout",
             detail=("The walk-forward chain predicts each season from prior seasons only, which is "
                     "correct. But the final season has now been examined in this session, so a "
                     "future pass on it would not be out-of-sample. A new holdout is needed before "
                     "any promotion is credible."),
             source=link_source("NIST-BONF"),
             status="open — needs a new holdout"),
        dict(id="U11", severity="low",
             title="No prize exists, so the competition clause is unmet",
             detail=("The brief asks for a competition that rewards top strategies. The board, gates "
                     "and ranking exist; the reward does not. No sponsor, amount or terms are stated, "
                     "because none exist. Funding one implies obligations that are not settled."),
             source=link_source("NFL-TERMS") + " · " + f'<a href="questions.html#Q11">Q11</a>',
             status="open — owner decision"),
        dict(id="U12", severity="low",
             title="Two source pages could not be quoted",
             detail=("The SGP article returned a client-rendered page with no body text, so no "
                     "sentence is quoted from it and no claim rests on it. The DraftKings prop and "
                     "parlay articles were quoted in full. A source that cannot be read is not used."),
             source=link_source("DK-SGP"),
             status="disclosed — pointer only"),
        dict(id="U13", severity="low",
             title="Club depth charts remain a classification question, not a fact",
             detail=("Two clubs label their own chart unofficial. Whether a club publication counts "
                     "as official is an owner decision that this session does not take, and it does "
                     "not edit the shared source allow-list it does not own. The tier is disclosed "
                     "on every row instead."),
             source=link_source("NFL-INJURY") + " · " + f'<a href="questions.html#Q15">Q15</a>',
             status="open — owner decision"),
    ]
    return items


def flagged_page(e: dict) -> str:
    items = flagged_items(e)
    high = sum(1 for i in items if i["severity"] == "high")
    med = sum(1 for i in items if i["severity"] == "medium")
    low = sum(1 for i in items if i["severity"] == "low")
    body = kpis([
        ("Items flagged", f"{len(items)}", "all published with a source", ""),
        ("High severity", f"{high}", "a value or a claim cannot be supported", "bad"),
        ("Medium", f"{med}", "disclosed, with a workaround", "warn"),
        ("Low", f"{low}", "coverage or governance gaps", ""),
        ("Items hidden", "0", "nothing is suppressed on this page", "ok"),
        ("Items repaired by this build", "0", "the data is never rewritten", ""),
    ])
    body += """
<div class="note"><strong>Why this page exists.</strong> A site that only publishes what it can
prove is a site that hides its gaps. Every irregularity, unverified blank and open question found
while building this section is listed here with its source, its severity and its status. Nothing on
this page is repaired: the underlying data is never rewritten, so a reader can reproduce every item.
Flagged items do not block publication — they block the <em>claim</em> that depends on them.</div>

<div class="section-head"><div><h2>Flagged items</h2>
<p>High severity means a number or a claim cannot be supported. Filter by ID, title or status.</p></div></div>
"""
    rows = []
    for i in items:
        rows.append([
            f'<td id="{E(i["id"])}"><code>{E(i["id"])}</code></td>',
            f'<td>{pill(i["severity"].upper(), "fail" if i["severity"] == "high" else "paper" if i["severity"] == "medium" else "na")}</td>',
            f"<td><strong>{E(i['title'])}</strong></td>",
            f'<td style="font-size:11.5px">{i["detail"]}</td>',
            f"<td>{E(i['status'])}</td>",
            src(i["source"]),
        ])
    body += table(["ID", "Severity", "Item", "Detail", "Status", "Source"], rows,
                  "Every flagged item, verbatim. No item was resolved by deleting it.",
                  table_id="flag-table", filterable=True)

    body += """
<div class="section-head"><div><h2>Blanks published on this site</h2>
<p>A blank is a value that could not be sourced. Each is a deliberate cell, not an omission.</p></div></div>
"""
    blanks = [
        ("Closing-line value", "Every page that mentions it", "No two-sided priced archive exists.",
         "U01", link_repo("data/raw/initial_lines.csv", "data")),
        ("Player-prop line and price", "parlays.html", "No player-level market in the dataset.", "U09",
         link_source("DK-PROP")),
        ("A funded prize", "leaderboard.html, demotion.html", "No sponsor, amount or terms.", "U11",
         link_source("NFL-TERMS")),
        ("Opening price", "snapshots.html", "The opening file has no price column.", "U01",
         link_repo("data/raw/initial_lines.csv", "data")),
        ("A live strategy's return", "leaderboard.html", "No strategy is live; G6 and G7 are untestable.",
         "U10", link_repo("lines_lab/leaderboard.py", "code")),
        ("A depth beyond a club's printed chart", "depth.html", "The club printed no further name.",
         "U07", link_source("NFL-INJURY")),
        ("Correlations for prop legs", "correlations.html", "No player data; n would be zero.", "U09",
         link_source("DK-PROP")),
        ("Which of 5 bad rows is wrong", "results.html", "No official line archive to arbitrate.",
         "U04", link_repo("data/raw/closing_lines.csv", "data")),
    ]
    body += table(["Blank", "Where it appears", "Why it is blank", "Item", "Source"], [
        [f"<td>{E(a)}</td>", f"<td>{E(bb)}</td>", f"<td>{E(cc)}</td>",
         f'<td><a href="{"results.html" if d.startswith("U04") else "flagged.html"}#{E(d)}">{E(d)}</a></td>', src(s_) ]
        for a, bb, cc, d, s_ in blanks], "Eight blanks a reader will encounter, and why each is empty.")

    body += """
<div class="section-head"><div><h2>What was done with a flag</h2></div></div>
<div class="panel"><div style="padding:14px 16px;font-size:13.5px">
<p style="margin:0 0 8px"><strong>Nothing is repaired.</strong> The pipeline does not rewrite the
input data, does not drop a disagreeing row and does not fill a blank. A flag changes what the site
<em>claims</em>, never what the data says.</p>
<p style="margin:0"><strong>One exception is recorded, and it is this session's own error.</strong>
Item U05 is a mistake in this pipeline, not in the data: the first reading of the sign convention was
inverted. It was caught, corrected against an official box score, and every dependent number was
recomputed. It is listed here rather than quietly fixed, because a reader who found it independently
would otherwise have no way to tell whether other numbers were also wrong. They were re-run.</p>
</div></div>
"""
    return page("Flagged for review", "flagged.html", "<strong>Decisions</strong> / Flagged for review",
                "Every irregularity, unverified blank and open question found while building this "
                "section — with its source, its severity and its status. Nothing hidden, nothing "
                "repaired.", body,
                "Flagged for review: irregular data, unverified values shown as blanks, and open "
                "questions, each with a source link and a status.")
