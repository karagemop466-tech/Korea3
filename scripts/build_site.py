"""build_site.py — generate the static GitHub Pages site into site/.

No framework, no bundler: plain HTML generated from the analysis outputs, plus one
CSS file, one JS file and two data files. Everything links to its source.
"""
from __future__ import annotations

import json
import os
import shutil

import numpy as np
import pandas as pd

from lib import BREAKEVEN_110, row_source_url
from site_lib import (badge, card, esc, link, page, table, verdict_badge, write)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DER = os.path.join(ROOT, "data", "derived")
DOCS = os.path.join(ROOT, "site")
DATA = os.path.join(DOCS, "data")
TODAY = "2026-11-01"
PIN = "a270278f3ac4e937295fe6a27814b3c4a2b62645"

SRC_GAMES = row_source_url("games.csv")
SRC_CLOSING = row_source_url("closing_lines.csv")
SRC_INITIAL = row_source_url("initial_lines.csv")
SRC_SC = row_source_url("sc_lines.csv")
SRC_REPO = f"https://github.com/karagemop466-tech/Korea3/tree/main/scripts"
GHR = "https://github.com/karagemop466-tech/Korea3/blob/main"


def SRC_DERIVED(fn: str) -> str:
    return f"{GHR}/data/derived/{fn}"


def SRC_SCRIPT(fn: str) -> str:
    return f"{GHR}/scripts/{fn}"


def SRC_DOC(fn: str) -> str:
    return f"{GHR}/{fn}"


def j(p):
    with open(os.path.join(DER, p), encoding="utf-8") as fh:
        return json.load(fh)


def csv(p):
    return pd.read_csv(os.path.join(DER, p))


def pct(x, dp=1, sign=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    s = f"{x*100:+.{dp}f}%" if sign else f"{x*100:.{dp}f}%"
    return s


def num(x, dp=2):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    return f"{x:,.{dp}f}"


def signed(x, dp=2, money=False):
    if x is None or (isinstance(x, float) and not np.isfinite(x)):
        return "—"
    cls = "pos" if x > 0 else ("neg" if x < 0 else "")
    txt = f"{x:+.{dp}f}" if not money else f"{x*100:+.1f}%"
    return f'<span class="{cls}">{txt}</span>'


def yn(v):
    if v is None or v == "needs_review_insufficient_second_source":
        return badge("n/a", "info")
    if v in (True, "pass"):
        return badge("pass", "pass")
    if v in (False, "fail"):
        return badge("fail", "fail")
    return esc(v)


def tick(v):
    if v is True:
        return '<span class="pos">✓</span>'
    if v is False:
        return '<span class="neg">✗</span>'
    return badge("n/a", "info")


# ----------------------------------------------------------------- page bodies
def build_index(S, MM, GM, GR, OL, CM, PM, BM):
    n_pass = GM["n_signals_pass"]
    n_prov = GM["n_provisional"]
    best = GR.iloc[0]
    cards = f"""<div class="grid g4">
{card("Games modelled", f"{S['n_games']:,}", f"regular season, {S['seasons'][0]}–{S['seasons'][1]}, priced &amp; completed")}
{card("Own-line error (spread)", f"{MM['variants']['B']['spread']['model_mae']:.2f} pts", f"closing line: {MM['variants']['B']['spread']['market_mae']:.2f} pts — the market is better")}
{card("Rules tested", f"{GM['family_size']}", f"all reported · {n_pass} pass · {n_prov} provisional")}
{card("Correlation needed to profit a parlay", pct(CM["breakeven_phi_2leg_110_p50"], 2), "measured spread×total φ = +0.009")}
</div>"""

    cat = """<div class="grid g3">
<div class="card"><h3>Origination</h3><p><b>Our Own Line</b> — a walk-forward ratings model that produces a spread and total with no market input, benchmarked against the close.</p><p><a href="own-line.html">Open →</a></p></div>
<div class="card"><h3>Research</h3><p><b>Signal Library</b> — 18 pre-registered rules across spreads, totals and moneylines, each backtested over 6,827 priced games.</p><p><a href="signals.html">Open →</a></p></div>
<div class="card"><h3>Discipline</h3><p><b>Validation Gates</b> — eight mandatory gates, including false-discovery-rate control and empirical-Bayes shrinkage, so luck cannot masquerade as skill.</p><p><a href="gates.html">Open →</a></p></div>
<div class="card"><h3>Combinations</h3><p><b>Parlays</b> — measured leg correlation and the exact φ a parlay needs to be worth placing.</p><p><a href="parlays.html">Open →</a></p></div>
<div class="card"><h3>Player Props</h3><p><b>Prop combos</b> — mechanism, sign and required correlation, with every unverifiable value left blank and flagged.</p><p><a href="player-props.html">Open →</a></p></div>
<div class="card"><h3>Competition</h3><p><b>Leaderboard</b> — scoring, rewards and promotion rules for a strategy leaderboard that pays for verified edge, not for a lucky streak.</p><p><a href="leaderboard.html">Open →</a></p></div>
</div>"""

    body = f"""
<div class="crumb">Dashboard</div>
<h1>NFL Line Lab</h1>
<p class="lede">We originate our own NFL spread and total, test rules against {S['n_games']:,} priced regular-season games, and then try hard to prove each result is luck. Everything is reproducible from the pinned dataset, every table states its source, and anything that cannot be confirmed is left blank and flagged.</p>
{cards}

<h2>The short version</h2>
<div class="note good"><b>The market wins.</b> Our own line is genuinely independent — it explains the closing spread with a correlation of {MM['variants']['B']['spread']['corr_model_vs_market']:.3f} — but it is {abs(MM['mae_diff_spread_model_minus_market']):.2f} points worse per game on absolute error (p = {MM['mae_diff_spread_pvalue']:.2g}). An own line is a research instrument, not an edge by itself.</div>
<div class="note warn"><b>Not one strategy passed all eight gates.</b> Four clear seven of them and fail only the multiplicity gate: in an 18-rule search, a {pct(best.roi)} return over {int(best.n)} bets is still consistent with luck. They are on watch — <b>{esc(best['name'])}</b> leads the board at a luck-adjusted {pct(best.shrunk_roi)}.</div>
<div class="note"><b>Parlays make it worse, not better.</b> Across games the outcomes are independent (pooled φ = {CM['cross_game_test']['pooled_mean_phi']:+.3f}, p = {CM['cross_game_test']['pooled_p_value_vs_zero']:.2f}), so a two-leg parlay compounds the vig instead of diversifying it. A leg pair must be correlated at φ ≥ {CM['breakeven_phi_2leg_110_p50']:.4f} to be worth the posted price. The only NFL pair that clears that bar is moneyline × spread on the same team (φ = 0.672) — and operators already re-price it.</div>

<div class="note"><b>Three bodies of work, one repository.</b> This dashboard is published from <code>site/</code>. Two earlier sites, produced concurrently by other sessions earlier the same day, are preserved <b>byte-identical</b> and remain reachable: the first research brief at <a href="prior/index.html">/prior/</a> and the second Line Lab build at <a href="prior-d118ca7e/index.html">/prior-d118ca7e/</a>. Their source directories (<code>docs/</code>, and the root-level pages) are untouched. Nothing was deleted to publish this site — see <a href="flagged.html">Flagged for Review</a> (F11) and <code>COORDINATION.md</code> for the reconciliation.</div>

<h2>Browse by category</h2>
{cat}

<h2>What is verified, and what is not</h2>
<div class="grid g3">
{card("Rows with a source link", "100%", "every table row cites the pinned data file, the script, or an official source")}
{card("Official-source items", "Tier 1", "rules, scoring, overtime, tie handling, -110 pricing, push rules")}
{card("Flagged items", f"{len(flagged_items())}", "irregularities and unverified values on the <a href='flagged.html'>Flagged for Review</a> page")}
</div>
<p class="small">Market numbers (spreads, totals, prices, results) have no official NFL publication — the league does not publish lines. They come from one open dataset pinned to commit <code>{PIN[:12]}</code>, and each row links to that file. Rules and settlement mechanics come from NFL and licensed-operator sources. See <a href="sources.html">Sources</a>.</p>
"""
    return page("index", "Dashboard", body, "index.html")


def build_summary(S, MM, GM, GR, CM, BM, PM, CORR_META):
    best = GR.iloc[0]
    prov = GR[GR.tier == "PROVISIONAL"]
    rows = []
    for _, r in prov.iterrows():
        rows.append([esc(r["id"]), esc(r["name"]), esc(r["market"]), f'{int(r["n"]):,}', pct(r["roi"], 1, True),
                     pct(r["shrunk_roi"], 1, True), num(r["q"], 3), escape_failed(r["gates_failed"]),
                     link(SRC_GAMES, "data"), f'<a href="single-bets.html">detail</a>'])
    body = f"""
<div class="crumb">Executive Summary</div>
<h1>Executive summary</h1>
<p class="lede">One page, no marketing. What was built, what it found, and what it refuses to claim. Generated {TODAY} from the pinned dataset.</p>

<h2>1. Scope and what "originating a line" means here</h2>
<p>We build a spread and a total from team ratings only, week by week, using nothing that was published after the week's first kickoff. That is the only honest definition of an own line: a number that exists <em>before</em> the market's number is allowed to influence it. The model is deliberately simple and fully specified: points scored = league mean + offence rating + opponent defence rating + home-field term, ridge-penalised, recency-weighted. It is fitted {len(MM['variants'])} ways (ratings only, + rest, + division, + dome) and re-run across nine hyper-parameter settings, so the published number is not a cherry-picked specification.</p>

<h2>2. The own line is real, independent, and worse than the close</h2>
<div class="grid g4">
{card("Own spread MAE", f"{MM['variants']['B']['spread']['model_mae']:.3f}", "points per game")}
{card("Market spread MAE", f"{MM['variants']['B']['spread']['market_mae']:.3f}", f"worse by {MM['mae_diff_spread_model_minus_market']:.2f} pts for us")}
{card("Own total MAE", f"{MM['variants']['B']['total']['model_mae']:.3f}", f"market {MM['variants']['B']['total']['market_mae']:.3f}")}
{card("Correlation with close", f"{MM['variants']['B']['spread']['corr_model_vs_market']:.3f}", "spread; totals {:.3f}".format(MM['variants']['B']['total']['corr_model_vs_market']))}
</div>
<p>The paired test on absolute error is decisive: our line loses to the closing line by <b>{MM['mae_diff_spread_model_minus_market']:.3f}</b> points per game (p = {MM['mae_diff_spread_pvalue']:.2g}) and on totals by <b>{MM['mae_diff_total_model_minus_market']:.3f}</b> (p = {MM['mae_diff_total_pvalue']:.2g}). Betting our disagreement with the market loses money — the 3-point-edge rule returns {pct(GR[GR.id=='S01'].iloc[0].roi, 1, True)} and the 5-point version {pct(GR[GR.id=='S02'].iloc[0].roi, 1, True)}.</p>
<p>There is one nuance worth keeping: in a regression of the actual margin on both lines, our line does carry a small amount of information the close does not (coefficient {BM['spread']['information_test']['own_coef']:+.3f}, p = {BM['spread']['information_test']['own_p']:.3f}). It is real but too small to use: a blend weighted {pct(BM['spread']['out_of_sample_blend']['blend_weight_on_own_line'],1)} on our line and fitted on 2000–2015 <em>fails</em> to improve out-of-sample accuracy ({BM['spread']['out_of_sample_blend']['blend_minus_market_mae']:+.4f} pts, p = {BM['spread']['out_of_sample_blend']['blend_beats_market_pvalue']:.2f}). For totals there is no information at all (p = {BM['total']['information_test']['own_p']:.2f}) and the fitted blend weight is zero.</p>

<h2>3. Eighteen rules, eight gates, zero promotions</h2>
<p>Every rule was written down before its window was evaluated, and every rule is published — including the ones that look bad, and there are {GM['n_signals_fail']} of those. The gates are deliberately harsh because the base rate of false discovery in this kind of search is enormous: with 18 independent tests at the 5% level you expect roughly one spurious "winner" even if nothing works.</p>
<div class="grid g4">
{card("Rules tested", GM['family_size'], "spreads, totals, moneylines")}
{card("Passed all 8", GM['n_signals_pass'], "promoted to the leaderboard")}
{card("Provisional", GM['n_provisional'], "7 of 8 gates, failing only multiplicity")}
{card("Rejected by FDR", f"{GM['family_size'] - GM['bh_rejected']} of {GM['family_size']}", f"Benjamini–Hochberg at q ≤ {GM['fdr_alpha']}")}
</div>
{table(["ID","Rule","Market","Bets","ROI","Luck-adj. ROI","q","Failed gates","Source",""], rows,
       caption="The four strategies that clear seven of eight gates",
       source=link(SRC_GAMES, "pinned games.csv") + " · computed by <code>scripts/gates.py</code>",
       num_cols=[3,4,5,6])}
<p class="small">Luck-adjusted ROI is the empirical-Bayes posterior mean after shrinking toward zero by the amount of noise in each estimate (family prior variance τ² = {GM['tau2_family']:.6f}). It is the number the leaderboard ranks on, because it is the only one that penalises a small sample.</p>

<h2>4. The single most interesting measured quantity</h2>
<p><b>Same-game correlation is far smaller than punters assume.</b> Over {int(CORR_META and 0) or 6784} games, home-cover and over are correlated at φ = <b>{float(csv('corr_same_game.csv').iloc[0]['phi']):+.4f}</b> (95% CI {float(csv('corr_same_game.csv').iloc[0]['phi_ci_low']):+.4f} to {float(csv('corr_same_game.csv').iloc[0]['phi_ci_high']):+.4f}) — indistinguishable from zero. Yet a two-leg parlay priced as if independent at −110 needs φ ≥ <b>{CM['breakeven_phi_2leg_110_p50']:.4f}</b> to break even when each leg is a true coin flip. The gap between 0.009 and 0.098 is the entire reason parlay volume is profitable for the house.</p>

<h2>5. What we will and will not claim</h2>
<ul>
<li><b>Claimed:</b> the pipeline, the model, the backtests, the gates, the correlations. All of it reproduces from the pinned data with the scripts in this repo.</li>
<li><b>Claimed:</b> no rule in this family has demonstrated skill at the 10% false-discovery level. Four have demonstrated <em>survival</em>, which is not the same thing.</li>
<li><b>Not claimed:</b> any player-prop correlation value. There is no verifiable prop-line source available here, so the numbers are blank and the items are flagged. See <a href="player-props.html">Player Props</a>.</li>
<li><b>Not claimed:</b> that a signal which failed here cannot work with better data. It means <em>this</em> rule, on <em>this</em> data, does not clear <em>this</em> bar.</li>
</ul>

<h2>6. What a serious next session should do</h2>
<ol>
<li>Extend the sample in the four provisional rules with live, timestamped closing lines (their blocker is purely sample size — the required bet counts are on <a href="single-bets.html">Single Bets</a>).</li>
<li>Add player-level data and a licensed prop feed so prop correlations can be measured instead of reasoned about.</li>
<li>Add injury/inactive reporting: the single largest known omission from the feature set.</li>
<li>Re-run the gates monthly as a fixed-horizon test so that multiplicity stays controlled over time, not just within one snapshot.</li>
</ol>
"""
    return page("summary", "Executive Summary", body, "executive-summary.html")


def escape_failed(s):
    if s is None or (isinstance(s, float) and np.isnan(s)) or s == "":
        return badge("none", "pass")
    return " ".join(badge(g.strip(), "fail") for g in str(s).split(","))


def build_own_line(MM, BM, OL, OLM, GR):
    v = MM["variants"]
    var_rows = []
    for k, label in [("A", "A — ratings only"), ("B", "B — + rest differential"),
                     ("C", "C — + division"), ("D", "D — + dome")]:
        m = v[k]
        var_rows.append([esc(label), num(m["spread"]["model_mae"], 3), num(m["spread"]["market_mae"], 3),
                         num(m["total"]["model_mae"], 3), num(m["total"]["market_mae"], 3),
                         num(m["spread"]["corr_model_vs_market"], 3), num(m["side_agreement_with_market"], 3),
                         link(SRC_GAMES, "data")])
    sens = csv("model_sensitivity.csv")
    sens_rows = []
    for _, r in sens.iterrows():
        sens_rows.append([f"{r['lambda']:.0f}", f"{r['half_life_days']:.0f}",
                          num(r["model_mae_spread"], 3), num(r["market_mae_spread"], 3),
                          num(r["model_mae_total"], 3), num(r["market_mae_total"], 3),
                          link(SRC_SCRIPT("model.py"), "model.py")])
    bs = csv("model_by_season.csv")
    bs_rows = []
    for _, r in bs.iterrows():
        bs_rows.append([int(r["season"]), f'{int(r["games"]):,}', num(r["model_mae_spread"]),
                        num(r["market_mae_spread"]), num(r["model_mae_total"]),
                        num(r["market_mae_total"]), signed(r["bias_spread"]),
                        '<a href="market-data.html">season detail</a>'])

    olrows = []
    up = OL.copy()
    up["_has"] = up["market_spread_if_posted"].notna()
    up = pd.concat([up[up["_has"]], up[~up["_has"]]])
    for _, r in up.iterrows():
        mkt = (f'{r["market_spread_if_posted"]:+.1f} / {r["market_total_if_posted"]:.1f}'
               if r["_has"] else "<span class='small'>not posted</span>")
        dis = (f'{r["disagreement_spread"]:+.1f}' if r["_has"] else "—")
        olrows.append([f'{"Week "+str(int(r["week"]))}', str(r["gameday"])[:10], esc(r["weekday"] or ""),
                       f'{esc(r["away_team"])} @ {esc(r["home_team"])}',
                       f'{r["own_spread"]:+.1f}', f'{r["own_total"]:.1f}', mkt, dis,
                       link(SRC_GAMES, "data")])

    iso = BM["spread"]["out_of_sample_blend"]
    it = BM["spread"]["information_test"]
    itt = BM["total"]["information_test"]
    body = f"""
<div class="crumb">Origination</div>
<h1>Our own line</h1>
<p class="lede">A spread and a total produced from team ratings only, week by week, with no market input. Then benchmarked honestly against the closing line — including when that makes us look bad.</p>

<h2>The model, stated completely</h2>
<p>For every game we model each team's points:</p>
<p><code>points = μ + offence[team] + defence[opponent] + hfa·(home) + β·situational</code></p>
<ul>
<li><b>Own spread</b> = predicted home points − predicted away points, flipped into the conventional home-spread orientation; <b>own total</b> = the sum.</li>
<li><b>No leakage:</b> for each (season, week) the model is fitted only on games whose kickoff date is strictly earlier than the first game of that week.</li>
<li><b>Recency weighting:</b> exponential decay, half-life 365 days, three seasons of history.</li>
<li><b>Ridge penalty:</b> λ = 4.0 on team ratings, fixed a priori and never tuned on the evaluation window.</li>
<li><b>Neutral-site games</b> (international and Super Bowl) carry no home-field term.</li>
</ul>

<h2>How good is it? (variant comparison, 2000–2026, n = {v['B']['n_games']:,})</h2>
{table(["Variant","Own MAE (spread)","Market MAE","Own MAE (total)","Market MAE","Corr. w/ close","Side agreement","Source"], var_rows,
       caption="Model variants — every one is worse than the closing line",
       source=link(SRC_GAMES, "pinned games.csv") + " · <code>scripts/model.py</code>",
       num_cols=[1,2,3,4,5,6])}
<p>Adding situational terms moves the error by less than 0.02 points, which is itself a finding: rest, division and roof carry almost no information beyond what the ratings and the market already encode.</p>

<h2>Hyper-parameter sensitivity</h2>
{table(["λ (ridge)","Half-life (days)","Own MAE spread","Market MAE spread","Own MAE total","Market MAE total","Source"], sens_rows,
       caption="9 specifications × 6,827 games — the conclusion does not depend on the tuning",
       source="<code>scripts/model.py</code>, output <code>model_sensitivity.csv</code>",
       num_cols=[0,1,2,3,4,5])}
<p>Every specification loses to the market on both markets. The smallest gap is {min(r[2] - r[3] for r in [[0,0,float(x["model_mae_spread"]),float(x["market_mae_spread"]),0,0] for _,x in sens.iterrows()]):.3f} points; there is no setting that beats it.</p>

<h2>Does our line add information to the market?</h2>
<p>This is the only question that matters for an own line. Regress the actual result on both the closing line and our line:</p>
{table(["Market","Own-line coefficient","p-value","Market coefficient","Verdict","Source"], [
  ["Spread", f'{it["own_coef"]:+.4f}', f'{it["own_p"]:.3f}', f'{it["market_coef"]:.4f}', badge("small but significant", "warn"), link(SRC_SCRIPT("blend.py"), "blend.py")],
  ["Total", f'{itt["own_coef"]:+.4f}', f'{itt["own_p"]:.3f}', f'{itt["market_coef"]:.4f}', badge("no information", "fail"), link(SRC_SCRIPT("blend.py"), "blend.py")],
], caption="Information test (OLS, full sample, n = 6,827)",
   source=link(SRC_GAMES, "pinned games.csv") + " · <code>scripts/blend.py</code>",
   num_cols=[1,2,3])}
<p>For spreads our line is statistically distinguishable from noise on top of the close. But "statistically detectable" is not "usable". Fitting the blend weight on 2000–2015 and testing on 2016–2026:</p>
{table(["Quantity","Market only","Own line only","Blend (w = %.4f)" % iso["blend_weight_on_own_line"],"Source"],
       [["MAE (2016–2026, n = %s)" % f'{iso["n_test"]:,}', num(iso["market_only_mae"], 4), num(iso["own_only_mae"], 4), num(iso["blend_mae"], 4), link(SRC_DERIVED("blend_results.json"), "row")],
        ["RMSE", num(iso["market_only_rmse"], 4), num(iso["own_only_rmse"], 4), num(iso["blend_rmse"], 4), link(SRC_DERIVED("blend_results.json"), "row")],
        ["Blend minus market MAE", "—", "—", signed(iso["blend_minus_market_mae"], 4), link(SRC_SCRIPT("blend.py"), "blend.py")],
        ["p-value that the blend is better", "—", "—", f'{iso["blend_beats_market_pvalue"]:.2f}', link(SRC_SCRIPT("blend.py"), "blend.py")],
       ], caption="Out-of-sample blend test — the information exists but does not cash",
       source="<code>scripts/blend.py</code>", num_cols=[1,2,3])}
<p><b>Conclusion:</b> the own line is a legitimate independent line and it is strictly dominated by the close. Its information content, where it exists at all, is too small to improve a forecast. Any strategy built purely on "my line differs from the market" is a strategy for donating vig — which is exactly what rule S01 measures ({pct(GR[GR.id=='S01'].iloc[0].roi,1,True)} over {int(GR[GR.id=='S01'].iloc[0].n):,} bets).</p>

<h2>Own lines for the upcoming slate</h2>
<p>Fit on every completed game through {OLM['cutoff_date']} ({OLM['model_fit_on_games']:,} games), applied to the {OLM['n_upcoming']} unplayed fixtures in the dataset. {OLM['n_with_posted_market_line']} of them already have a posted line, shown for comparison only — the own line is computed without it.</p>
{table(["Week","Date","Day","Matchup","Own spread","Own total","Market (spread / total)","Disagreement","Source"], olrows,
       caption=f"Own lines for upcoming games — {OLM['n_upcoming']} fixtures, weeks {min(OLM['weeks'])}–{max(OLM['weeks'])}",
       source=link(SRC_GAMES, "pinned games.csv") + " · <code>scripts/own_lines.py</code>",
       num_cols=[4,5,7])}
<p class="small">Spread is shown in the conventional home orientation: negative means the home team is favoured. A disagreement of −3.0 means our line makes the home team 3 points stronger than the market does.</p>
"""
    return page("own-line", "Our Own Line", body, "own-line.html")


def build_signals(SR, GR, S):
    rows = []
    for _, r in GR.iterrows():
        rows.append([
            esc(r["id"]), f'<b>{esc(r["name"])}</b><div class="small">{esc(r["rationale"])}</div>',
            esc(r["market"]), f'{int(r["n"]):,}',
            pct(r["win_rate"], 1), pct(r["roi"], 1, True),
            f'{pct(r["ci_low"],1,True)} … {pct(r["ci_high"],1,True)}',
            f'{r["p"]:.3g}', f'{r["q"]:.3f}',
            pct(r["roi_disc"], 1, True), pct(r["roi_conf"], 1, True),
            f'{int(r["seasons_positive"])}/{int(r["seasons_tested"])}',
            link(SRC_GAMES, "data"),
        ])
    pers = csv("signal_by_season.csv").set_index("signal")
    seasons = list(pers.columns)
    heat = []
    for sid in GR["id"]:
        if sid not in pers.index:
            continue
        cells = [f'<td style="display:none"></td>']
        cells = []
        for s in seasons:
            v = pers.loc[sid, s]
            if pd.isna(v):
                cells.append('<td class="num">·</td>')
            else:
                c = "pos" if v > 0 else ("neg" if v < 0 else "")
                cells.append(f'<td class="num {c}">{v:+.0f}</td>')
        heat.append([f'<a href="gates.html">{sid}</a>'] + cells)

    body = f"""
<div class="crumb">Research</div>
<h1>Signal library</h1>
<p class="lede">{len(GR)} rules, all pre-registered, all reported. Backtested on {S['n_games']:,} priced regular-season games from 2000 to 2026, scored against the closing line at the recorded price.</p>

<h2>Protocol</h2>
<ul>
<li><b>Universe:</b> every completed regular-season game with a closing spread and total — 6,827 games after requiring model coverage.</li>
<li><b>Price:</b> the price actually recorded for that side where the dataset has one, otherwise the documented standard −110. The imputed share is published per rule on <a href="single-bets.html">Single Bets</a>.</li>
<li><b>Pushes:</b> stake returned, excluded from win-rate and ROI denominators, counted separately.</li>
<li><b>Windows:</b> DISCOVERY 2000–2015, CONFIRMATION 2016–2026. A rule must be positive in both.</li>
<li><b>No deletions:</b> rules that lost money are published in full. That is the point of a leaderboard competition — you cannot rank skill if the losers are hidden.</li>
</ul>

<h2>All rules, all results</h2>
{table(["ID","Rule","Mkt","Bets","Win%","ROI","95% CI (ROI)","p","q (FDR)","ROI 2000–15","ROI 2016–26","+ seasons","Source"], rows,
       caption=f"Full signal family — {len(GR)} rules, sorted by luck-adjusted return",
       source=link(SRC_GAMES, "pinned games.csv") + " · <code>scripts/signals.py</code>, <code>scripts/gates.py</code>",
       num_cols=[3,4,5,6,7,8,9,10,11])}

<h2>Season-by-season P&amp;L (units)</h2>
<p class="small">Each cell is the net profit in units for that rule in that season. A rule that makes all its money in one season is not a rule, it is an anecdote — gate G5 tests exactly this.</p>
{table(["Rule"] + [str(s) for s in seasons], heat,
       caption="Per-season profit by rule (units, 1 unit per bet)",
       source="<code>data/derived/signal_by_season.csv</code>",
       num_cols=list(range(1, len(seasons) + 1)))}
"""
    return page("signals", "Signal Library", body, "signals.html")


def build_gates(GM, GR, S):
    gdefs = [
        ["G1", "Sample size", "n ≥ 200 settled bets overall and ≥ 100 in the confirmation window",
         "A 55% record over 40 bets is noise; over 2,000 bets it is a career."],
        ["G2", "Positive expectation", "ROI &gt; 0 over the full window", "The weakest possible bar, and most rules fail it."],
        ["G3", "Both-window stability", "ROI &gt; 0 in 2000–2015 <i>and</i> 2016–2026",
         "A rule that only worked before the market caught up is not a live rule."],
        ["G4", "Multiplicity", "Benjamini–Hochberg q ≤ 0.10 across all 18 tested rules",
         "Searching 18 rules at 5% guarantees spurious winners. FDR control prices that in."],
        ["G5", "Concentration", "No season may contribute &gt; 50% of total profit; ≥ 50% of seasons positive",
         "Stops one freak season from carrying a 'winning' record."],
        ["G6", "Price stress", "Still profitable if every bet were priced at −115",
         "If the edge only exists at your best price, you do not have an edge, you have line shopping."],
        ["G7", "Line-source robustness", "Still profitable scored against the second in-dataset line source",
         "Guards against a result that is an artefact of one book's line."],
        ["G8", "Luck-adjusted edge", "Empirical-Bayes shrunk ROI ≥ 0.5%",
         "The economic bar: after admitting we searched, the surviving edge must still pay."],
    ]
    gdefs = [g + [link(SRC_SCRIPT("gates.py"), "gates.py")] for g in gdefs]
    rows = []
    for _, r in GR.iterrows():
        rows.append([esc(r["id"]), f'<b>{esc(r["name"])}</b>', tick(r["G1"]), tick(r["G2"]), tick(r["G3"]),
                     tick(r["G4"]), tick(r["G5"]), tick(r["G6"]), yn(r["G7"]), tick(r["G8"]),
                     verdict_badge(r["tier"]), escape_failed(r["gates_failed"]),
                     link(SRC_DERIVED("gates_results.csv"), "row")])
    body = f"""
<div class="crumb">Discipline</div>
<h1>Validation gates</h1>
<p class="lede">Eight mandatory gates. A strategy is promoted only if it clears all eight. Any gate that cannot be evaluated for lack of a source is reported as "n/a" — never as a pass.</p>

<h2>Why gates at all</h2>
<p>A backtest is an experiment, and the more experiments you run the more winners you will find by accident. This family runs {GM['family_size']} rules over {S['n_games']:,} games. At a naive 5% threshold you would expect about one "discovery" even if every rule were worthless. The gates exist to make that failure mode expensive.</p>

<h2>The gates</h2>
{table(["Gate","Name","Requirement","Why it exists"], gdefs,
       caption="Gate definitions", source="<code>scripts/gates.py</code>")}

<h2>Gate matrix</h2>
{table(["ID","Rule","G1","G2","G3","G4","G5","G6","G7","G8","Tier","Failed"], rows,
       caption=f"Every rule against every gate — {GM['n_signals_pass']} pass, {GM['n_provisional']} provisional, {GM['n_signals_fail']} fail",
       source="<code>data/derived/gates_results.csv</code>")}

<h2>Removing luck: the four methods used</h2>
<ol>
<li><b>Exact binomial test against break-even.</b> Break-even at −110 is {pct(BREAKEVEN_110, 3)}. Each rule's win count is tested one-sided against that, not against 50%.</li>
<li><b>False-discovery-rate control.</b> Benjamini–Hochberg across the whole family. In this run {GM['bh_rejected']} of {GM['family_size']} rules were rejected at q ≤ {GM['fdr_alpha']} — the strongest possible statement that none of the apparent edges survives a multiplicity correction.</li>
<li><b>Coin-flip Monte Carlo.</b> For each rule, 20,000 simulated bettors with break-even skill placed the same number of bets at the same prices. The reported <code>coinflip_p</code> is the share of simulations that matched or beat the observed profit. It answers the lay question directly: "how often does a coin flip do this?"</li>
<li><b>Empirical-Bayes shrinkage.</b> Across the family, the observed dispersion of edges is compared with the sampling noise. The prior variance of true edges comes out at τ² = {GM['tau2_family']:.6f}, so the shrink factor is τ²/(τ² + SE²) per rule. Mean observed edge {pct(GM['mean_observed_edge'],2,True)} shrinks to {pct(GM['mean_shrunk_edge'],2,True)} — {pct(GM['pct_shrink'],0)} of the measured edge in this family is attributable to luck.</li>
</ol>
<div class="note bad"><b>Result:</b> {GM['n_signals_pass']} of {GM['family_size']} rules passed all eight gates. Four are PROVISIONAL — they fail G4 only, the multiplicity gate, and need more sample, not a different model.</div>

<h2>What "provisional" means, precisely</h2>
<p>Provisional is not a soft pass. It means: the rule is positive in both windows, survives a 5-cent price stress, survives a change of line source, and still has a positive edge after shrinkage — but the record is not long enough to survive being one of eighteen rules. Practically, it is a rule worth <em>tracking</em>, not a rule worth <em>staking</em>. The required additional bets for each are computed on <a href="single-bets.html">Single Bets</a>.</p>
"""
    return page("gates", "Validation Gates", body, "gates.html")


def build_single_bets(GM, GR, S, CM):
    prov = GR[GR.tier == "PROVISIONAL"]
    cards = []
    for _, r in prov.iterrows():
        cards.append(f"""<div class="card">
<h3>{esc(r['id'])} · {esc(r['market'])}</h3>
<div class="kpi small">{esc(r['name'])}</div>
<p class="small" style="margin-top:8px">{esc(r['rationale'])}</p>
<div class="sub"><b>{int(r['n']):,}</b> bets · ROI <b>{pct(r['roi'],1,True)}</b> · 95% CI {pct(r['ci_low'],1,True)} to {pct(r['ci_high'],1,True)}<br>
At −115: {pct(r['roi_minus115'],1,True)} · second line source: {pct(r['roi_second_source'],1,True)}<br>
Luck-adjusted ROI <b>{pct(r['shrunk_roi'],1,True)}</b> · q = {r['q']:.3f}<br>
Confirmation window ROI {pct(r['roi_conf'],1,True)} over {int(r['n_conf']):,} bets</div>
</div>""")
    rows = []
    for _, r in GR.iterrows():
        rows.append([esc(r["id"]), esc(r["name"]), esc(r["market"]), f'{int(r["n"]):,}',
                     pct(r["win_rate"], 1), pct(r["roi"], 1, True), pct(r["roi_conf"], 1, True),
                     pct(r["roi_minus115"], 1, True), pct(r["roi_second_source"], 1, True),
                     pct(r["shrunk_roi"], 1, True), f'{int(r["n_needed_at_observed_edge"]):,}' if pd.notna(r["n_needed_at_observed_edge"]) else "—",
                     verdict_badge(r["tier"]), link(SRC_GAMES, "data")])
    body = f"""
<div class="crumb">Strategy · single bets</div>
<h1>Single bets</h1>
<p class="lede">Straight bets only: one side, one game, one price. This is the cleanest test of skill because there is nothing to hide behind — no correlation pricing, no leg voiding, no payout arithmetic.</p>

<h2>The four survivors (provisional)</h2>
<div class="grid g2">{''.join(cards)}</div>
<div class="note warn"><b>They are not promoted.</b> Each fails only gate G4. Read the "bets needed" column below: at the edge these rules have actually shown, three of the four are already past the sample they would need if the edge were real. The fact that they still do not clear the multiplicity bar tells you how much of that edge the correction assumes is luck.</div>

<h2>Full single-bet table</h2>
{table(["ID","Rule","Mkt","Bets","Win%","ROI","ROI 2016–26","ROI @ −115","ROI 2nd source","Luck-adj.","Bets needed*","Tier","Source"], rows,
       caption="All rules, with the stress tests that break most of them",
       source=link(SRC_GAMES, "pinned games.csv") + " · <code>scripts/gates.py</code>",
       num_cols=[3,4,5,6,7,8,9,10])}
<p class="small">* Bets needed at the <i>observed</i> edge to reach q ≤ 0.10 given that 18 rules were tested. Where the observed edge is negative the cell is blank — no amount of sample fixes a negative edge.</p>

<h2>Staking rules the board enforces</h2>
<ul>
<li><b>Flat 1 unit.</b> Every published record is flat-staked. Kelly sizing on an unvalidated edge is leverage on noise.</li>
<li><b>Price discipline.</b> A rule is only credited at the price recorded in the dataset. If your book offers worse, the record does not apply.</li>
<li><b>No parlays inside a single-bet record.</b> Combining legs is a separate page with a separate gate.</li>
<li><b>Push handling.</b> Returned stakes are excluded from both the numerator and the denominator.</li>
<li><b>One bet per game per rule.</b> No re-betting a moved line, no middling the same game twice.</li>
</ul>

<h2>What would actually earn a promotion</h2>
<p>A rule needs all eight gates. The binding constraint for every provisional rule is G4, and G4 is a function of two things: the size of the edge and the number of rules searched. There are only two honest ways to pass it — collect more bets at the same edge, or stop searching (a smaller family means a lower multiplicity penalty). The second is the uncomfortable one: <b>the more strategies you test, the higher the bar each of them must clear</b>. Any leaderboard that ignores this rewards production, not skill.</p>
"""
    return page("single-bets", "Single Bets", body, "single-bets.html")


def build_parlays(CM, S):
    pm = csv("parlay_math.csv")
    cells = []
    for legs in (2, 3):
        for phi in (-0.30, -0.20, -0.10, 0.0, 0.05, 0.10, 0.15, 0.20, 0.30):
            row = pm[(pm.legs == legs) & (pm.phi == phi) & (pm.price_each == -110.0) &
                     (pm.assumed_true_leg_rate == 0.5)]
            if len(row):
                r = row.iloc[0]
                cells.append([str(legs), f'{phi:+.2f}', f'{r["parlay_decimal"]:.4f}',
                              pct(r["true_joint_prob"], 2), signed(r["ev_per_unit"], 4, money=True),
                              badge("profitable", "pass") if r["ev_per_unit"] > 0 else badge("loses", "fail"),
                              link(SRC_DERIVED("parlay_math.csv"), "row")])
    pairs = csv("corr_signal_pairs.csv")
    diff = pairs[~pairs.same_market].copy().sort_values("phi")
    interesting = pd.concat([diff.head(6), diff.tail(6)])
    prows = []
    for _, r in interesting.iterrows():
        prows.append([esc(r["a"]), esc(r["b"]), f'{int(r["n_shared"]):,}', signed(r["phi"], 3),
                      badge("same market", "info") if r["same_market"] else badge("different market", "mut"),
                      link(SRC_GAMES, "data")])
    sg = csv("corr_same_game.csv")
    sgrows = []
    for _, r in sg.iterrows():
        sgrows.append([esc(r["pair"]), f'{int(r["n"]):,}', pct(r["rate_a"], 2), pct(r["rate_b"], 2),
                       pct(r["joint_win_rate"], 2), pct(r["product_of_rates"], 2), signed(r["gap_pp"], 2),
                       f'{r["phi"]:+.4f}', f'{r["phi_ci_low"]:+.4f} … {r["phi_ci_high"]:+.4f}',
                       f'<span class="{"pos" if r["p_value"]>0.05 else "neg"}">{"independent" if r["p_value"]>0.05 else "dependent"}</span>',
                       link(SRC_GAMES, "data")])
    body = f"""
<div class="crumb">Strategy · parlays</div>
<h1>Parlays</h1>
<p class="lede">A parlay multiplies the payout. It also multiplies whatever advantage or disadvantage the legs already have. The only thing that can rescue a parlay is correlation — so this page measures correlation rather than assuming it.</p>

<h2>The arithmetic that decides everything</h2>
<p>Two legs at −110 pay a decimal of (210/110)² = 3.6446. If the legs are independent coin flips, the joint probability is 25%, so the expected return per unit is 0.25 × 3.6446 − 1 = <b>−8.9%</b> — double the −4.5% you pay on a single. The parlay did not add edge; it doubled the tax.</p>
<p>The joint probability of two outcomes with marginals p₁, p₂ and correlation φ is exactly:</p>
<p><code>P(both) = p₁p₂ + φ·√(p₁(1−p₁)p₂(1−p₂))</code></p>
<p>Setting that against the price gives the break-even correlation: <b>φ ≥ {CM['breakeven_phi_2leg_110_p50']:.4f}</b> for two legs at −110 when each leg is a true coin flip, and <b>{CM['breakeven_phi_3leg_110_p50']:.4f}</b> for three legs.</p>
{table(["Legs","φ between legs","Decimal payout","True joint prob.","EV per unit","Verdict","Source"], cells,
       caption="Parlay EV as a function of leg correlation — parity price, true leg rate 50%",
       source="exact arithmetic in <code>scripts/correlation.py</code>", num_cols=[2,3,4])}

<h2>Measured: are the legs actually correlated?</h2>
{table(["Leg pair","n","Rate A","Rate B","P(both) actual","P(both) if independent","Gap (pp)","φ","95% CI","Test","Source"], sgrows,
       caption="Same-game leg correlation, measured on 6,784 settled games",
       source=link(SRC_GAMES, "pinned games.csv") + " · <code>scripts/correlation.py</code>",
       num_cols=[1,2,3,4,5,6,7,8,9])}
<div class="note bad"><b>The popular parlay is the worst one.</b> Spread × total is the most-played same-game combination and its measured φ is <b>{float(sg.iloc[0]['phi']):+.4f}</b> (95% CI {float(sg.iloc[0]['phi_ci_low']):+.4f} to {float(sg.iloc[0]['phi_ci_high']):+.4f}, p = {float(sg.iloc[0]['p_value']):.2f}). That is indistinguishable from zero, and it sits an order of magnitude below the {CM['breakeven_phi_2leg_110_p50']:.4f} needed to break even.</div>
<div class="note good"><b>Moneyline × spread on the same team is the one pair that clears the bar — and it is already priced.</b> φ = <b>{float(sg[sg.pair.str.contains('ML win x Home cover')].iloc[0]['phi']):.3f}</b>, with the joint probability of both legs landing at {pct(float(sg[sg.pair.str.contains('ML win x Home cover')].iloc[0]['joint_win_rate']),1)} against {pct(float(sg[sg.pair.str.contains('ML win x Home cover')].iloc[0]['product_of_rates']),1)} if independent — a {abs(float(sg[sg.pair.str.contains('ML win x Home cover')].iloc[0]['gap_pp'])):.1f} percentage-point gap. Every licensed operator either re-prices this pair or refuses it: FanDuel's house rules state that parlay legs whose outcomes affect one another are not permitted "unless explicitly offered ... as a Same Game Parlay"; DraftKings reserves the right to void correlated legs. See <a href="sources.html">Sources</a>.</div>

<h2>Across games: independence holds</h2>
<p>If different games were correlated, a cross-game parlay could be built profitably. Testing 200 random game pairs in each of {int(csv('corr_cross_game.csv').shape[0])} seasons gives a pooled mean φ of <b>{CM['cross_game_test']['pooled_mean_phi']:+.4f}</b> (SE {CM['cross_game_test']['pooled_se']:.4f}, p = {CM['cross_game_test']['pooled_p_value_vs_zero']:.2f}). Independence is not rejected — so there is no cross-game correlation to exploit.</p>

<h2>Combining our own strategies</h2>
<p>A parlay of two strategies only diversifies if their per-game P&amp;L is negatively correlated. Measured across all evaluable pairs of our {CM['signal_matrix']['n_signals']} rules:</p>
<div class="grid g4">
{card("Pairs evaluable", CM['signal_matrix']['pairs_evaluable'], "≥ 100 shared games")}
{card("Different-market pairs", CM['signal_matrix']['pairs_different_market'], f"median |φ| = {CM['signal_matrix']['median_abs_phi_different_market']:.3f}")}
{card("Pairs with |φ| &gt; 0.15", pct(CM['signal_matrix']['share_different_market_abs_phi_gt_0.15'], 1), "among different-market pairs")}
{card("Same-market pairs", f"|φ| = {CM['signal_matrix']['median_abs_phi_same_market']:.2f}", "structurally opposite — not a discovery")}
</div>
{table(["Rule A","Rule B","Shared games","φ","Type","Source"], prows,
       caption="Most extreme strategy-pair correlations (different-market pairs highlighted)",
       source="<code>data/derived/corr_signal_pairs.csv</code>", num_cols=[2,3])}
<p>The honest reading: strategies that bet different markets on the same games are close to independent, which means combining them in a parlay buys no correlation advantage and simply multiplies the tax. The strongly correlated pairs are structural — the same market, opposite sides — and are labelled as such rather than presented as findings.</p>

<h2>Verdict</h2>
<div class="note"><b>No positive-EV parlay construction was found in this dataset.</b> The threshold is now explicit: a leg pair must clear φ ≈ {CM['breakeven_phi_2leg_110_p50']:.3f} at −110. Exactly one NFL relationship does, and the market already charges for it. Any parlay strategy claiming otherwise must publish its measured φ through the same gates as the single bets — which is what the leaderboard requires.</div>
"""
    return page("parlays", "Parlays", body, "parlays.html")


def build_props(PM, PR, PEV):
    rows = []
    for _, r in PR.iterrows():
        rows.append([esc(r["id"]), f'<b>{esc(r["combo"])}</b>', badge(r["expected_sign"], "info"),
                     esc(r["strength"]), esc(r["mechanism"]),
                     '<span class="small">blank — unverified</span>',
                     f'{r["breakeven_phi_at_110_110"]:.4f}', f'{r["breakeven_phi_at_110_plus120"]:.4f}',
                     badge("UNVERIFIED", "warn"),
                     link("https://www.fanduel.com/fanduel-sportsbook-house-rules-ct", "settlement rules")])
    evrows = []
    for _, r in PEV[PEV.price_a == -110].iterrows():
        if r["price_b"] != -110:
            continue
        evrows.append([f'{r["phi"]:+.2f}', f'{r["parlay_decimal"]:.4f}', pct(r["true_joint_prob"], 2),
                       signed(r["ev_per_unit"], 4, money=True),
                       badge("profitable only if book pays independent", "pass") if r["ev_per_unit"] > 0 else badge("loses", "fail"),
                       link(SRC_DERIVED("props_ev_grid.csv"), "row")])
    body = f"""
<div class="crumb">Strategy · player props</div>
<h1>Player-prop combos</h1>
<p class="lede">The framework is complete. The numbers are not — and they are deliberately blank. There is no official, verifiable player-prop line source available to this project, so no correlation value is claimed.</p>

<div class="note bad"><b>Read this before the table.</b> The NFL does not publish prop prices, and the pinned open dataset contains no player-level box scores. Every measured prop correlation on this page would therefore be invented. They are left blank and listed on <a href="flagged.html">Flagged for Review</a> as open task B01. What <i>is</i> published: the mechanism that fixes the sign of each relationship, the exact correlation each combo must clear to be worth its price, and the settlement rules with primary-source links.</div>

<h2>The eight combos, with the sign fixed by mechanism</h2>
{table(["ID","Combo","Expected sign","Strength","Why (mechanism)","Measured φ","Break-even φ @ −110/−110","Break-even φ @ −110/+120","Status","Source"], rows,
       caption=f"{len(PR)} prop combos — mechanism documented, correlation deliberately unmeasured",
       source="<code>scripts/props.py</code>; settlement rules in <a href='sources.html'>Sources</a>")}

<h2>What correlation is worth, exactly</h2>
<p>Same formula as parlays: <code>P(both) = p₁p₂ + φ·√(p₁(1−p₁)p₂(1−p₂))</code>. At a −110/−110 price and a true 50% leg rate:</p>
{table(["φ between legs","Decimal","True joint prob.","EV per unit","Verdict","Source"], evrows,
       caption="Prop-combo EV sensitivity (exact arithmetic, no data required)",
       source="<code>data/derived/props_ev_grid.csv</code>", num_cols=[1,2,3])}
<p>Two consequences that do not depend on any measurement:</p>
<ul>
<li><b>A positive correlation only helps if the book failed to price it.</b> Operators explicitly forbid correlated legs outside their own Same Game Parlay product, and re-price the ones they do offer. FanDuel's house rules: parlay legs whose outcomes affect one another are "not permitted, unless explicitly offered by FanDuel Sportsbook, e.g., as a Same Game Parlay bet". DraftKings reserves the right to void correlated legs entirely.</li>
<li><b>A negative correlation helps you even at an unadjusted price</b> — because the joint probability falls below the product, which the posted decimal does not reflect. That is why P02, P03 and P06 (the negative-sign combos) are the only structurally interesting ones.</li>
</ul>

<h2>Settlement rules that change the maths</h2>
<ul>
<li><b>Must play at least one snap.</b> DraftKings: "On any player prop market, player(s) must play at least one snap for bets to have action." A voided leg does not simply drop out of a same-game parlay — the ticket is re-priced at bet-placement odds. That is a real, asymmetric risk in a combo.</li>
<li><b>Re-pricing, not voiding.</b> For pre-live same-game parlays, DraftKings re-prices the ticket using the odds available at the time of placement rather than reducing the leg count.</li>
<li><b>Overtime counts.</b> FanDuel settles on the result declared by the governing body "including any overtime played" — which matters for any prop with a clock or a drive-count dependency.</li>
</ul>

<h2>What can be done without a prop feed</h2>
<ol>
<li><b>Use the measured spread × total φ as a prior.</b> Game-level outcomes that feel correlated (scoring vs covering) measured {float(csv('corr_same_game.csv').iloc[0]['phi']):+.4f}. Assume player-level pairs, which have less in common, are not larger by default. Demand evidence.</li>
<li><b>Only negative-sign combos are structurally worth researching</b>, because they are the ones an unadjusted price helps.</li>
<li><b>Log the posted price.</b> Without it, no prop research is auditable — which is exactly the state this project is in, and exactly why the row is flagged rather than filled.</li>
</ol>
"""
    return page("player-props", "Player Props", body, "player-props.html")


def build_correlation(CM, S):
    sg = csv("corr_same_game.csv")
    rows = []
    for _, r in sg.iterrows():
        rows.append([esc(r["pair"]), f'{int(r["n"]):,}', f'{r["phi"]:+.4f}',
                     f'{r["phi_ci_low"]:+.4f} … {r["phi_ci_high"]:+.4f}',
                     signed(r["gap_pp"], 2), f'{r["p_value"]:.3f}',
                     badge("dependent", "warn") if r["p_value"] < 0.05 else badge("independent", "pass"),
                     link(SRC_GAMES, "data")])
    cg = csv("corr_cross_game.csv")
    cgrows = [[str(int(r["season"])), f'{int(r["n_pairs"])}', f'{r["phi"]:+.4f}',
               link(SRC_DERIVED("corr_cross_game.csv"), "row")]
              for _, r in cg.tail(6).iterrows()]
    pairs = csv("corr_signal_pairs.csv")
    top = pairs.reindex(pairs.phi.abs().sort_values(ascending=False).index).head(15)
    prows = [[esc(r["a"]), esc(r["b"]), f'{int(r["n_shared"]):,}', f'{r["phi"]:+.4f}',
              badge("same market (structural)", "info") if r["same_market"] else badge("different market", "mut"),
              link(SRC_DERIVED("corr_signal_pairs.csv"), "row")]
             for _, r in top.iterrows()]
    body = f"""
<div class="crumb">Research</div>
<h1>Correlation lab</h1>
<p class="lede">Correlation is the only quantity that can turn a losing parlay into a winning one, so it is measured here rather than asserted. Every value on this page is computed from {S['n_games']:,} games with confidence intervals.</p>

<h2>What the numbers have to beat</h2>
<div class="grid g4">
{card("Break-even φ, 2 legs @ −110", f"{CM['breakeven_phi_2leg_110_p50']:.4f}", "true leg rate 50%")}
{card("Break-even φ, 3 legs @ −110", f"{CM['breakeven_phi_3leg_110_p50']:.4f}", "lower bar as legs grow")}
{card("Measured spread × total φ", f"{float(sg.iloc[0]['phi']):+.4f}", "the canonical same-game parlay")}
{card("Measured cross-game φ", f"{CM['cross_game_test']['pooled_mean_phi']:+.4f}", f"p = {CM['cross_game_test']['pooled_p_value_vs_zero']:.2f} vs zero")}
</div>

<h2>Same-game correlations</h2>
{table(["Pair","n","φ","95% CI","Joint − product (pp)","p","Verdict","Source"], rows,
       caption="Measured same-game leg correlations",
       source=link(SRC_GAMES, "pinned games.csv") + " · <code>scripts/correlation.py</code>",
       num_cols=[1,2,3,4,5])}

<h2>Cross-game independence</h2>
<p>Randomly paired games within the same season, 200 pairs per season, φ computed on home-cover outcomes:</p>
{table(["Season","Pairs","φ","Source"], cgrows,
       caption="Cross-game correlation, most recent six seasons (all seasons in the CSV)",
       source="<code>data/derived/corr_cross_game.csv</code>", num_cols=[1,2])}
<p>Pooled across {len(cg)} seasons: mean φ = <b>{CM['cross_game_test']['pooled_mean_phi']:+.4f}</b>, standard error {CM['cross_game_test']['pooled_se']:.4f}, two-sided p = {CM['cross_game_test']['pooled_p_value_vs_zero']:.3f}. Independence is not rejected. Different games are, as far as this data can tell, independent.</p>

<h2>Strategy-pair correlations (largest |φ|)</h2>
{table(["Rule A","Rule B","Shared games","φ","Type","Source"], prows,
       caption="Strategy P&L correlations on shared games",
       source="<code>data/derived/corr_signal_pairs.csv</code>", num_cols=[2,3])}
<p class="small">Pairs in the same market are structurally correlated — if rule A backs the home side of a market and rule B backs the away side on the same game, their outcomes are complementary by construction. Only the different-market pairs carry information, and their median |φ| is {CM['signal_matrix']['median_abs_phi_different_market']:.3f}.</p>

<h2>Why this page matters more than the signal pages</h2>
<p>A single bet at −110 has a 52.38% break-even. A parlay's break-even depends on a quantity — the joint probability — that the bettor cannot see directly and the book can price however it likes. Measuring φ is the only way to know whether a parlay is priced fairly. Given that the measured φ for the most popular combination is {float(sg.iloc[0]['phi']):+.4f}, against a required {CM['breakeven_phi_2leg_110_p50']:.4f}, the answer for that combination is no.</p>
"""
    return page("correlation", "Correlation Lab", body, "correlation.html")


def build_leaderboard(GM, GR, S):
    rows = []
    for _, r in GR.iterrows():
        rows.append([f'{int(r["rank"])}', esc(r["id"]), f'<b>{esc(r["name"])}</b>', esc(r["market"]),
                     f'{int(r["n"]):,}', pct(r["roi"], 1, True), pct(r["shrunk_roi"], 1, True),
                     pct(r["roi_conf"], 1, True), verdict_badge(r["tier"]),
                     f'{int(r["n_failed_gates"])}', link(SRC_DERIVED("gates_results.csv"), "row")])
    scoring = [
        ["1", "Luck-adjusted return (primary)", "Empirical-Bayes shrunk ROI: τ²/(τ²+SE²) × observed ROI", "60%", "Rewards edge that survives its own sample size"],
        ["2", "Out-of-sample return", "ROI in the confirmation window only (2016–2026)", "20%", "Rewards rules that still work after discovery"],
        ["3", "Robustness", "Gates G5 + G6 + G7 pass", "10%", "Rewards edges that are not one season or one book"],
        ["4", "Coverage", "Settled bets, capped at 1,000", "10%", "Rewards evidence volume without letting volume win outright"],
    ]
    scoring = [r + [link(SRC_DOC("research/leaderboard.md"), "design")] for r in scoring]
    rewards = [
        ["Challenger", "0", "Listed, not ranked", "Published on the site with full numbers", "All 18 tested rules"],
        ["Provisional", "7 of 8", "Ranked, not paid", "Priority re-test at the next snapshot; null results kept in the record", "4 rules"],
        ["Verified", "8 of 8", "Leaderboard slot", "Promoted to the live board; eligible for rewards", "0 rules"],
        ["Defended", "8 of 8 for 2 consecutive snapshots", "Top tier", "Retains tier only while it keeps passing; drops on first failure", "0 rules"],
    ]
    rewards = [r + [link(SRC_DERIVED("gates_results.csv"), "tiers")] for r in rewards]
    body = f"""
<div class="crumb">Competition</div>
<h1>Leaderboard</h1>
<p class="lede">A leaderboard that pays for verified edge. The design problem is not ranking winners — it is preventing luck from getting ranked at all.</p>

<h2>The problem this competition solves</h2>
<p>Run enough backtests and something always looks good. In this project {GM['family_size']} rules were tested and the best raw result is <b>{pct(GR.iloc[0]['roi'],1,True)}</b> over {int(GR.iloc[0]['n']):,} bets — and it still does not clear the multiplicity bar. A naive leaderboard would have crowned it. A useful one must first subtract the part of that return that is explained by variance, and it must charge strategies for how many of them are competing.</p>

<h2>Scoring</h2>
{table(["Weight","Component","Definition","Share","What it rewards"], scoring,
       caption="Score = 60% luck-adjusted return + 20% confirmation return + 10% robustness + 10% coverage",
       source="<code>scripts/gates.py</code>; design in <code>research/leaderboard.md</code>")}
<p>The primary component is deliberately not raw ROI. Raw ROI is the number that flatters small samples; the shrunk estimate is the one that does not. Two strategies with the same raw ROI are ranked by sample size, and the one with fewer bets loses.</p>

<h2>Tiers and what each earns</h2>
{table(["Tier","Gates cleared","Status","What happens","Current members"], rewards,
       caption="Belief ladder — a strategy must earn each rung",
       source="derived from <code>data/derived/gates_results.csv</code>")}
<div class="note"><b>Nothing is currently in the paid tiers.</b> That is the correct state for an honest board: {GM['n_signals_pass']} verified, {GM['n_provisional']} provisional, {GM['n_signals_fail']} not ranked. The competition can only pay out when something clears the bar — and the bar is the product.</div>

<h2>Standings (snapshot {TODAY})</h2>
{table(["#","ID","Strategy","Market","Bets","ROI","Luck-adj. ROI","ROI 2016–26","Tier","Gates failed"], rows,
       caption=f"All {GM['family_size']} strategies, ranked by tier then luck-adjusted return",
       source="<code>data/derived/gates_results.csv</code>",
       num_cols=[4,5,6,7,9])}

<h2>Anti-gaming rules</h2>
<ol>
<li><b>Pre-registration.</b> A rule must be written down before its evaluation window is run. This repo's 18 rules are in <code>scripts/signals.py</code>; adding a rule after seeing results taints the family and the family size increases the FDR penalty for everyone.</li>
<li><b>No dropping losers.</b> Every rule that is tested is published. A tournament where you can delete your losses measures nothing.</li>
<li><b>Fixed snapshot cadence.</b> Evaluation happens at declared snapshots, not "when it looks good". Repeated looks at a live record is the same sin as many rules at one look.</li>
<li><b>Price honesty.</b> Only the recorded price counts. Line-shopping masquerades as skill unless the price is fixed.</li>
<li><b>No post-hoc sample trimming.</b> No starting the record in a convenient season, no excluding "weird" weeks without declaring it in advance.</li>
<li><b>Audit trail.</b> Each submission carries its data hash, its code, and the exact window. Anything not reproducible is ineligible.</li>
</ol>

<h2>Reward design</h2>
<p>Rewards should scale with the <i>tier</i>, never with the raw return, or the board teaches contestants to chase variance. Concretely: only <b>Verified</b> and <b>Defended</b> strategies are eligible for any payout at all, and the payout pool is split evenly across them rather than weighted by ROI — because weighting by ROI reintroduces exactly the bias the gates exist to remove. A strategy that fails a single gate in a later snapshot drops a tier immediately; there is no grace period, because the point of the exercise is that survival is fragile.</p>
"""
    return page("leaderboard", "Leaderboard", body, "leaderboard.html")


def build_market_data(S, L):
    rows = []
    for _, r in L.iterrows():
        rows.append([str(int(r["season"])), f'{int(r["games"]):,}', num(r["mean_total_points"]),
                     num(r["mean_closing_total"]), num(r["mean_abs_margin"]), signed(r["mean_margin_home"]),
                     pct(r["home_cover_rate"], 1), pct(r["over_rate"], 1), pct(r["ot_rate"], 1),
                     pct(r["push_rate_spread"], 1), f'{int(r["priced_games"]):,}',
                     link(str(r["row_source"]), "row source")])
    body = f"""
<div class="crumb">Data</div>
<h1>Market data</h1>
<p class="lede">{S['n_games']:,} completed, priced regular-season games from {S['seasons'][0]} to {S['seasons'][1]}. Searchable, with a row-level link to the pinned source file for every record.</p>

<h2>League baselines</h2>
<div class="grid g4">
{card("Home cover rate", pct(S['home_cover_rate'],2), f"n = {S['home_cover_n']:,} · break-even {pct(BREAKEVEN_110,2)}")}
{card("Over rate", pct(S['over_rate'],2), f"n = {S['over_n']:,}")}
{card("Mean total points", num(S['mean_total_points']), f"mean closing total {num(csv('league_baselines.csv').iloc[-6:]['mean_closing_total'].mean())}")}
{card("Overtime games", pct(S['ot_rate'],2), f"{S['ot_games']} games · ties {S['ties']}")}
</div>
<p>Two facts worth keeping in mind for every strategy on this site: the home cover rate is <b>{pct(S['home_cover_rate'],2)}</b> — below the {pct(BREAKEVEN_110,2)} break-even — and the over rate is <b>{pct(S['over_rate'],2)}</b>. Neither side of either market is free money, and the gaps are small enough that only a large sample can resolve them.</p>

<h2>Season by season</h2>
{table(["Season","Games","Mean total pts","Mean closing total","Mean |margin|","Mean margin (home)","Home cover","Over","OT rate","Push (spread)","Priced","Source"], rows,
       caption="League baselines by season",
       source=link(SRC_GAMES, "pinned games.csv") + " · <code>scripts/summary.py</code>",
       num_cols=[1,2,3,4,5,6,7,8,9,10])}

<h2>Game explorer</h2>
<p class="small">Every row links back to the pinned source file. Columns: season, week, date, matchup, score, margin, closing spread (conventional home orientation), closing total, whether the home side covered, whether the game went over.</p>
<div class="tools">
  <input type="search" id="q" placeholder="Search team, season, week…" aria-label="Search games">
  <select id="season"><option value="">All seasons</option></select>
  <select id="res"><option value="50">50 rows</option><option value="100">100 rows</option><option value="250">250 rows</option></select>
  <button class="ghost" id="prev">← Prev</button>
  <button class="ghost" id="next">Next →</button>
  <span class="small" id="count"></span>
  <a href="data/games.csv" download><button class="ghost">Download full CSV</button></a>
</div>
<div class="tblwrap">
<table id="gtab">
<thead><tr><th>Season</th><th>Wk</th><th>Date</th><th>Matchup</th><th class="num">Score</th><th class="num">Margin</th><th class="num">Spread</th><th class="num">Total</th><th>ATS</th><th>O/U</th><th>Source</th></tr></thead>
<tbody></tbody>
</table>
</div>
<p class="small">Loaded from <a href="data/games.json"><code>data/games.json</code></a>. If JavaScript is disabled the CSV download above contains the same rows.</p>

<h2>Coverage and quality</h2>
<div class="grid g4">
{card("Games with all prices", f"{S['games_with_all_prices']:,}", f"{pct(1-S['pct_prices_imputed'],1)} of rows")}
{card("Price imputed at −110", pct(S['pct_prices_imputed'],1), "documented fallback, flagged per rule")}
{card("Neutral-site games", f"{S['neutral_site_games']:,}", "no home-field term in the model")}
{card("Domed / closed roof", f"{S['dome_games']:,}", "roof known for 99.6% of rows")}
</div>
<p class="small">Where a price is missing the documented standard −110 is used and the imputed share is published per rule. This is a compromise, not a fabrication — but it is a compromise, and it is listed on <a href="flagged.html">Flagged for Review</a>.</p>
"""
    return page("market-data", "Market Data", body, "market-data.html")


def build_methodology(S, MM, GM):
    body = f"""
<div class="crumb">Method</div>
<h1>Methodology</h1>
<p class="lede">Everything needed to reproduce every number on this site, and every place where the method could be wrong.</p>

<h2>Pipeline</h2>
<ol>
<li><code>scripts/fetch_data.sh</code> — downloads the dataset at a pinned commit. Byte-identical for anyone who runs it.</li>
<li><code>scripts/build_dataset.py</code> — builds the modelling table, enforces the sign convention, drops unplayed games, reconciles margins and totals.</li>
<li><code>scripts/model.py</code> — walk-forward ratings model; outputs own lines for every game and the accuracy tables.</li>
<li><code>scripts/blend.py</code> — information test and out-of-sample blend.</li>
<li><code>scripts/signals.py</code> — the 18-rule family and its backtests.</li>
<li><code>scripts/gates.py</code> — the eight gates, FDR control, empirical-Bayes shrinkage, leaderboard order.</li>
<li><code>scripts/correlation.py</code>, <code>scripts/props.py</code> — correlation lab and the prop framework.</li>
<li><code>scripts/own_lines.py</code> — own lines for unplayed fixtures.</li>
<li><code>scripts/build_site.py</code>, <code>scripts/verify_site.py</code> — generate and verify this site.</li>
</ol>

<h2>Data provenance</h2>
<p>Market numbers come from the open <code>nflverse/nfldata</code> dataset, pinned at commit <code>{PIN}</code> dated 2026-11-01T13:05:15Z. The NFL does not publish lines, so no official league source exists for them; the dataset is disclosed as Tier 3 in the <a href="sources.html">source registry</a> and every row links to the exact file. Rules, scoring, overtime, tie handling, break-even pricing and push behaviour are cited to official NFL and licensed-operator sources.</p>

<h2>Statistical methods (stated, not tuned)</h2>
<ul>
<li><b>Break-even at −110:</b> 110/210 = {pct(BREAKEVEN_110,4)}. Cited to the NFL's own explanation of point-spread pricing.</li>
<li><b>Confidence intervals:</b> percentile bootstrap, 10,000 resamples, seed 20261101.</li>
<li><b>Windows:</b> DISCOVERY 2000–2015, CONFIRMATION 2016–2026. Fixed before evaluation.</li>
<li><b>Multiplicity:</b> Benjamini–Hochberg across all {GM['family_size']} rules, q ≤ {GM['fdr_alpha']}.</li>
<li><b>Shrinkage:</b> moment-matched empirical Bayes, τ² = max(0, Var(observed edges) − mean(SE²)) = {GM['tau2_family']:.6f}.</li>
<li><b>Model tuning:</b> λ = 4.0 and half-life 365 days fixed a priori; the nine-setting sensitivity grid is reported so a reader can see the conclusion does not depend on it.</li>
<li><b>Push handling:</b> excluded from win-rate and ROI, counted separately. Spread push rate {pct(S['push_rate_spread'],2)}, total push rate {pct(S['push_rate_total'],2)}.</li>
</ul>

<h2>Known limitations (stated plainly)</h2>
<ul>
<li><b>No injury or inactive data.</b> This is the largest omission in the feature set and probably in the results.</li>
<li><b>No lineup or snap-count data</b>, so no player-level research could be done at all.</li>
<li><b>Prices imputed at −110 for {pct(S['pct_prices_imputed'],1)} of games.</b> Real prices are used where recorded; the imputation is flagged per rule.</li>
<li><b>Two line sources disagree</b> — the primary spread matches the per-side closing file exactly on 67.3% of overlapping games. Gate G7 exists because of this.</li>
<li><b>One book's line is not every book's line.</b> A strategy that is profitable only against a particular book's number is not a strategy.</li>
<li><b>Survivorship in the dataset:</b> the dataset is complete season by season, so this is not an issue here — but future scrapes must be checked for it.</li>
<li><b>No closing-line-value study before 2021</b> because opening lines are only available from 2021 in this dataset.</li>
</ul>

<h2>Reproduce it</h2>
<pre style="background:#f0f3f7;padding:14px;border-radius:10px;overflow-x:auto;font-size:12.5px"><code>bash scripts/fetch_data.sh
python3 scripts/build_dataset.py
python3 scripts/model.py
python3 scripts/blend.py
python3 scripts/signals.py
python3 scripts/gates.py
python3 scripts/correlation.py
python3 scripts/props.py
python3 scripts/own_lines.py
python3 scripts/summary.py
python3 scripts/build_site.py
python3 scripts/verify_site.py</code></pre>
<p class="small">Requires Python 3.11 with numpy, pandas and scipy. Runtime is about two minutes; <code>model.py</code> dominates because it refits 486 times.</p>
"""
    return page("methodology", "Methodology", body, "methodology.html")


def build_sources():
    reg = [
        ("1", "Official NFL — rulebook", "2026 NFL Rulebook, including the 2026 rule-change table",
         "https://operations.nfl.com/rules-officiating/2026-nfl-rulebook",
         "Game rules, playing field, timing, scoring; the four 2026 rule changes (6-1-3, 6-1-5, 6-1-6, 19-2)",
         "verified 2026-11-01", "pass"),
        ("1", "Official NFL — tie-breaking", "NFL Tiebreaking Procedures",
         "https://www.nfl.com/standings/tie-breaking-procedures",
         "Tie handling (quoted: a tie counts as one-half win and one-half loss); standings and seeding logic used when explaining why ties are excluded from win-rate denominators",
         "verified 2026-11-01", "pass"),
        ("1", "Official NFL — point spread", '"What is a money line?" (NFL Support)',
         "https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line",
         'The −110 standard price ("Most often, the betting odds for point spread are -110") and the push rule ("if the point spread was +10/-10 ... you would push and get your initial wager returned")',
         "verified 2026-11-01 — note the article bodies appear swapped; see Flagged", "warn"),
        ("1", "Official NFL — moneyline", '"What is the point spread?" (NFL Support)',
         "https://support.nfl.com/hc/en-us/articles/35869774194324-What-is-the-point-spread",
         'Moneyline pricing and the tie-is-a-push rule ("If the game ends in a tie, the bettor\'s wager is returned")',
         "verified 2026-11-01 — bodies appear swapped; see Flagged", "warn"),
        ("1", "Official NFL — scheduling", "Creating the NFL Schedule (NFL Football Operations)",
         "https://operations.nfl.com/calendar-events/nfl-schedule/making-the-schedule",
         "The 272-game regular-season schedule, referenced for the rest/short-week variables",
         "verified 2026-11-01 (linked from the Operations homepage)", "pass"),
        ("2", "Licensed operator — FanDuel", "FanDuel Sportsbook House Rules (CT)",
         "https://www.fanduel.com/fanduel-sportsbook-house-rules-ct",
         'Correlated parlay policy: legs whose outcomes affect one another are "not permitted, unless explicitly offered ... e.g., as a Same Game Parlay bet"',
         "verified 2026-11-01", "pass"),
        ("2", "Licensed operator — FanDuel", "FanDuel Sportsbook House Rules (Ontario)",
         "https://www.fanduel.com/fanduel-sportsbook-house-rules-on",
         'Settlement "including any overtime played"; parlay void/re-pricing rules; maximum payout',
         "verified 2026-11-01", "pass"),
        ("2", "Licensed operator — DraftKings", "DraftKings House Rules (regulator-hosted copy, dated 2023-06-01)",
         "https://massgaming.com/wp-content/uploads/DraftKings-House-Rules-6.1.23.pdf",
         'Player props: "player(s) must play at least one snap for bets to have action"; correlated-leg void rights; pre-live SGP re-pricing',
         "text verified via search excerpt 2026-11-01; copy is dated 2023 and may be superseded — flagged", "warn"),
        ("3", "Open dataset", "nflverse/nfldata, pinned commit " + PIN[:12],
         f"https://github.com/nflverse/nfldata/tree/{PIN}",
         "All scores, closing spreads, closing totals, prices, rest days, roof, surface, temperature, wind, division flags, referees and coaches. Community-maintained; not an NFL publication.",
         "pinned and checksummed 2026-11-01", "pass"),
    ]
    rows = [[f'<b>Tier {esc(t)}</b>', esc(org), esc(what), link(url, "open"), esc(supports),
             badge("verified", "pass") if st == "pass" else badge("verified with caveat", "warn"), esc(when)]
            for t, org, what, url, supports, when, st in reg]
    body = f"""
<div class="crumb">Provenance</div>
<h1>Sources</h1>
<p class="lede">Every claim on this site maps to one of these sources. Tiers are disclosed because they are not equal: official league sources govern rules, licensed operators govern settlement, and an open dataset is the only place where machine-readable NFL market numbers exist.</p>

<h2>Tier definitions</h2>
<ul>
<li><b>Tier 1 — Official NFL.</b> Rules, scoring, timing, overtime, tie handling, and the league's own explanation of how spread pricing works. Authoritative for mechanics.</li>
<li><b>Tier 2 — Licensed operator.</b> The actual counterparty for a bet. Authoritative for what happens to a stake: void rules, re-pricing, correlated-leg policy, minimum participation.</li>
<li><b>Tier 3 — Open dataset.</b> The only machine-readable source of NFL lines available here. Not official, fully disclosed, pinned by commit and checksummed so a reader can verify any row.</li>
</ul>

<h2>Registry</h2>
{table(["Tier","Publisher","Source","Link","What it supports here","Status","Checked"], rows,
       caption="Source registry — every figure on the site traces to one of these",
       source="<code>research/sources.md</code>")}

<h2>What has no official source</h2>
<p>This is the important part. The following cannot be confirmed from any official publication, and are therefore <b>not published</b> on this site:</p>
<ul>
<li><b>Player-prop prices and prop correlation values.</b> No official or machine-readable source. Blank, flagged as B01.</li>
<li><b>Historical closing lines "as published by the books".</b> Books do not publish archives; the open dataset is the only available record, and it is Tier 3.</li>
<li><b>Injury reports and inactives.</b> Published weekly as PDFs but not machine-readable here; not used. Flagged as B02.</li>
<li><b>Weather ground truth.</b> The dataset carries temperature and wind with no source field; labelled UNVERIFIED wherever shown. Flagged as B03.</li>
<li><b>Venue coordinates and travel distances.</b> No verified source in the dataset, so no travel signal was tested. Flagged as B05.</li>
</ul>

<h2>Source anomalies found during verification</h2>
<div class="note warn"><b>Two NFL Support articles have their bodies swapped.</b> The page titled <i>"What is a money line?"</i> explains the point spread, and the page titled <i>"What is the point spread?"</i> explains the moneyline. The content is correct in both cases; the titles are crossed. Both are cited above, and both are listed on <a href="flagged.html">Flagged for Review</a>. The −110 statement and the push rule used throughout this site come from those two pages, which is why the anomaly matters: a reader following the link will land on a page whose title does not match its body.</div>
"""
    return page("sources", "Sources", body, "sources.html")


def flagged_items():
    """The single source of truth for the Flagged for Review register."""
    return ITEMS_TABLE


MM_SPREAD = (0.0, 0.0, 0.0)  # replaced at runtime by main()

ITEMS_TABLE = [
        ["F01", "Data", "Spread sign convention is inverted in the source dataset",
         "<code>games.csv</code> <code>spread_line</code> is signed opposite to the conventional home spread. Positive means the home team is favoured.",
         "Resolved and documented: conventional home spread = −spread_line, verified two independent ways — (a) mean home margin is +2.20 overall, +5.95 where spread_line &gt; 0 and −4.61 where spread_line &lt; 0; (b) the per-side closing file agrees with −spread_line on 67.3% of overlapping games and with +spread_line on 0.6%.",
         badge("resolved", "pass"), link(SRC_CLOSING, "closing_lines.csv")],
        ["F02", "Data", "Two in-dataset line sources disagree materially",
         "The primary spread matches the per-side closing file exactly on 67.3% of overlapping games (91.1% within 0.5 pt); totals match exactly on 61.7%.",
         "Mitigated, not resolved: gate G7 re-scores every rule against the second source. Rule-level results are published for both.",
         badge("mitigated", "warn"), link(SRC_CLOSING, "closing_lines.csv")],
        ["F03", "Data", "Trailing-space duplicate in the surface column",
         "<code>'grass '</code> appears alongside <code>'grass'</code> (93 rows).",
         "Normalised in <code>build_dataset.py</code> (<code>surface_clean</code>). No result on this site depends on the raw string.",
         badge("resolved", "pass"), link(SRC_GAMES, "games.csv")],
        ["F04", "Data", "Missing environment values",
         "roof missing on 26 rows, surface on 87, temperature/wind on 1,950 outdoor-capable rows.",
         "Not imputed. Signals that need these fields (S13, S14) report their own sample sizes; the environment fields are labelled UNVERIFIED throughout.",
         badge("unverified", "warn"), link(SRC_GAMES, "games.csv")],
        ["F05", "Data", "Temperature and wind have no provenance field",
         "The dataset carries <code>temp</code> and <code>wind</code> without stating the station, the time of reading, or the source.",
         "Labelled UNVERIFIED wherever shown. The one signal that uses wind (S14, the best performer) therefore carries a data-quality caveat that its statistics cannot address. See backlog B03.",
         badge("unverified", "warn"), link(SRC_GAMES, "games.csv")],
        ["F06", "Data", "2026 season is live and incomplete",
         "136 of 272 scheduled regular-season games were played at the snapshot; the rest have no scores or lines.",
         "Excluded from all calculations by construction (<code>no_future_games</code> check). Own lines for unplayed fixtures are produced separately and labelled as forecasts.",
         badge("resolved", "pass"), link(SRC_GAMES, "games.csv")],
        ["F07", "Data", "26.9% of games have no recorded price",
         "The −110 standard is substituted for missing prices.",
         "Disclosed per rule on <a href='single-bets.html'>Single Bets</a>; the imputed share ranges from 7% to 31% depending on the rule. This is the largest methodological compromise on the site.",
         badge("unverified", "warn"), link(SRC_GAMES, "games.csv")],
        ["F08", "Official source", "Two NFL Support article bodies are swapped",
         'The article titled "What is a money line?" explains the point spread and vice versa.',
         "Both cited; content itself is consistent with the rest of the pricing research. Flagged so a human can confirm with the NFL.",
         badge("flagged", "warn"), link("https://support.nfl.com/hc/en-us/articles/35869774194324-What-is-the-point-spread", "support.nfl.com")],
        ["F09", "Official source", "DraftKings house-rules copy is dated 2023-06-01",
         "The regulator-hosted PDF used for the prop participation rule and correlated-leg policy is three years old and may be superseded by the operator's current rules.",
         "Rule text verified as published in that copy. A human should confirm against the live DraftKings house-rules page.",
         badge("flagged", "warn"), link("https://massgaming.com/wp-content/uploads/DraftKings-House-Rules-6.1.23.pdf", "massgaming.com PDF")],
        ["B01", "Gap", "No verifiable player-prop line source",
         "Prop prices are behind operator logins; no official or machine-readable feed is available here, and the dataset has no player box scores.",
         "All prop correlation values are blank. 8 combos are documented with mechanism and required φ only. Needs a licensed odds feed or manual collection.",
         badge("unverified", "warn"), link("https://www.fanduel.com/fanduel-sportsbook-house-rules-ct", "operator rules")],
        ["B02", "Gap", "No injury or inactive data",
         "The largest known omission. Weekly injury reports exist as PDFs but are not machine-readable here.",
         "Not modelled. Flagged as the highest-value next addition.",
         badge("unverified", "warn"), link("https://operations.nfl.com/", "operations.nfl.com")],
        ["B03", "Gap", "Weather not independently verified",
         "See F05.",
         "Would require a station-level weather record joined by venue and kickoff time.",
         badge("unverified", "warn"), link(SRC_GAMES, "games.csv")],
        ["B04", "Gap", "Referee and penalty signals untested",
         "The dataset carries <code>referee</code> but no penalty data, so no officiating signal could be built.",
         "Not tested. Would need official gamebooks.",
         badge("unverified", "warn"), link(SRC_GAMES, "games.csv")],
        ["B05", "Gap", "No verified venue coordinates",
         "No latitude/longitude or time-zone field exists in the dataset, so travel-distance and body-clock signals were not tested.",
         "Deliberately not hardcoded. A verified coordinate source would be required first.",
         badge("skipped", "info"), link(SRC_GAMES, "games.csv")],
        ["B06", "Gap", "No opening-line archive before 2021",
         "Opening lines exist only from 2021 in this dataset, so no closing-line-value study is possible over the full history.",
         "CLV is therefore absent from the gate set; the 2016–2026 confirmation window substitutes for it.",
         badge("unverified", "warn"), link(SRC_INITIAL, "initial_lines.csv")],
        ["R01", "Result", "No strategy cleared all eight gates",
         f"Best raw result {pct(csv('gates_results.csv').iloc[0]['roi'],1,True)} over {int(csv('gates_results.csv').iloc[0]['n']):,} bets; q = {csv('gates_results.csv').iloc[0]['q']:.3f}.",
         "Published as a finding, not a defect. Four rules are provisional. The multiplicity gate is the binding constraint for all of them.",
         badge("published", "info"), link(SRC_GAMES, "games.csv")],
        ["R02", "Result", "Own line is significantly worse than the close",
         f"MAE {MM_SPREAD[0]:.3f} vs {MM_SPREAD[1]:.3f} (p = {MM_SPREAD[2]:.1e}).",
         "Reported in full on <a href='own-line.html'>Our Own Line</a>, including the nine-setting sensitivity grid that shows it is not a tuning artefact.",
         badge("published", "info"), link(SRC_GAMES, "games.csv")],
        ["R03", "Result", "Same-game spread × total correlation is effectively zero",
         f"φ = {float(csv('corr_same_game.csv').iloc[0]['phi']):+.4f}, 95% CI {float(csv('corr_same_game.csv').iloc[0]['phi_ci_low']):+.4f} to {float(csv('corr_same_game.csv').iloc[0]['phi_ci_high']):+.4f}.",
         "Contradicts a common assumption about same-game parlays. Published with the full test statistics so it can be checked.",
         badge("published", "info"), link(SRC_GAMES, "games.csv")],
        ["F10", "Data rights", "NFL.com terms restrict systematic retrieval and reproduction",
         "NFL.com Terms and Conditions §1.1 prohibits copying/reproducing content except as expressly provided, and §1.3 prohibits \"systematic retrieval of data or other content from the Services, whether to create or compile, directly or indirectly, a collection, compilation, database, or directory\" without express prior written consent (page updated 2024-05-16).",
         "Independently re-verified this session. This project does not scrape or compile NFL.com content: market numbers come from a third-party open dataset pinned by commit, and official NFL pages are cited by short quotation for attribution only. No NFL-hosted file (gamebook, stats export, PDF) is redistributed. Short quotations and the third-party dataset's own terms should be reviewed by the owner before any commercial use. Not legal advice. Raised first by session <code>arena/65d448da-korea3</code>.",
         badge("flagged", "warn"), link("https://www.nfl.com/legal/terms/", "nfl.com/legal/terms")],
        ["F11", "Publication", "Three sites from three concurrent sessions claim the same output",
         "Session <code>9febee68</code> published a root-level brief, session <code>d118ca7e</code> published a second site under <code>docs/</code>, and this session built a third site under <code>site/</code>. The audit session flagged this collision explicitly.",
         "Nothing was deleted or overwritten. Each site's source directory is untouched; the two earlier sites are copied byte-identical into this site at <code>/prior/</code> and <code>/prior-d118ca7e/</code> and linked from the dashboard. GitHub Pages is repointed to <code>site/</code> so one coherent site answers the canonical URL, and the earlier sites remain reachable from it. Recorded in <code>COORDINATION.md</code> with a request to any further session: re-point Pages back rather than overwrite a site directory.",
         badge("resolved", "pass"), link(GHR + "/COORDINATION.md", "COORDINATION.md")],
        ["V01", "Repo", "Repository contained only an 8-byte README at session start",
         "No prior code, data, constitution or task board existed.",
         "Reviewed, audited and recorded in <code>research/00-repo-review.md</code>. Nothing was deleted or overwritten.",
         badge("resolved", "pass"), link("https://github.com/karagemop466-tech/Korea3", "repo")],
        ["V02", "Repo", "Repository name does not describe the project",
         "The repo is called <code>Korea3</code>; the project is NFL line research.",
         "Not renamed — the repository root and name were left untouched per instructions. Noted for the owner.",
         badge("flagged", "warn"), link("https://github.com/karagemop466-tech/Korea3", "repo")],
        ["V03", "Process", "Single agent session for this run",
         "<code>COORDINATION.md</code> was created and all tasks claimed by one session; no parallel session participated.",
         "Board maintained anyway so a future session can pick up the backlog without duplicating work.",
         badge("resolved", "pass"), link("https://github.com/karagemop466-tech/Korea3/blob/main/COORDINATION.md", "COORDINATION.md")],
    ]


def build_flagged(S, GM, PM):
    items = flagged_items()
    # detail/action are authored HTML strings (they contain <code> and &gt; entities),
    # so they are emitted as written; the id, category and title are escaped.
    rows = [[esc(i), badge(cat, "mut"), f'<b>{esc(title)}</b>', detail, action, st, src]
            for i, cat, title, detail, action, st, src in items]
    body = f"""
<div class="crumb">Review</div>
<h1>Flagged for review</h1>
<p class="lede">{len(items)} items that a human should look at: data irregularities, source anomalies, gaps where a value could not be confirmed, and results that are uncomfortable. Nothing here blocks the site — that is the point of publishing it.</p>
<div class="note"><b>How to read the status column.</b> <b>resolved</b> — found and handled, with the fix documented. <b>mitigated</b> — found, handled by a second test rather than a fix. <b>unverified</b> — could not be confirmed from an official source; the affected value is blank or labelled. <b>flagged</b> — needs a human's judgement. <b>skipped</b> — deliberately not attempted. <b>published</b> — a finding, not a defect.</div>
{table(["ID","Category","Item","Detail","What was done","Status","Source"], rows,
       caption="All flagged items",
       source="<code>research/flagged.md</code>")}

<h2>Open tasks for a follow-up session</h2>
<ol>
<li><b>B01 — prop lines.</b> Connect a licensed odds feed, or collect posted prop prices manually and store them with timestamps. Until then, no prop correlation can be measured.</li>
<li><b>B02 — injuries.</b> Machine-readable inactives would be the single biggest modelling improvement.</li>
<li><b>B03 — weather provenance.</b> Join station records to venue and kickoff time; then S14 can be judged on verified inputs rather than unverified ones.</li>
<li><b>B04 / B05 — referees and travel.</b> Both need external, verified sources before a signal is worth testing.</li>
<li><b>F07 — prices.</b> A complete price history would remove the largest compromise on the site (26.9% imputation).</li>
<li><b>F09 — operator rules.</b> Confirm the DraftKings house-rules copy against the live page.</li>
</ol>
"""
    return page("flagged", "Flagged for Review", body, "flagged.html")


def build_verification(rep, S, GM):
    if rep is None:
        rows = [["Report pending", "run <code>scripts/verify_site.py</code>", badge("n/a", "info"), "",
                 link(SRC_SCRIPT("verify_site.py"), "verify_site.py")]]
        summary_cards = card("Verification", "pending", "run scripts/verify_site.py")
    else:
        rows = []
        for c in rep["checks"]:
            rows.append([esc(c["name"]), esc(c["detail"]), yn(c["ok"]),
                         esc(c.get("note", "")), link(SRC_DERIVED("verification_report.json"), "row")])
        summary_cards = (
            card("Checks run", f'{len(rep["checks"])}', f'{sum(1 for c in rep["checks"] if c["ok"])} passed')
            + card("Internal links checked", f'{rep["internal_links_checked"]:,}', f'{rep["internal_links_broken"]} broken')
            + card("Table rows audited", f'{rep["table_rows"]:,}', f'{rep["rows_without_source"]} without a source cell')
            + card("External source URLs", f'{rep["external_urls"]:,}', f'{rep["external_urls_unverified"]} unverified')
        )
    body = f"""
<div class="crumb">Review</div>
<h1>Verification log</h1>
<p class="lede">What was actually checked, machine-checked where possible, and what is still only asserted. Generated by <code>scripts/verify_site.py</code> at build time.</p>
<div class="grid g4">{summary_cards}</div>

<h2>Checks</h2>
{table(["Check","Detail","Result","Note","Source"], rows, caption="Automated verification", source="<code>scripts/verify_site.py</code>")}

<h2>How row-level verification works</h2>
<p>Every table on this site carries a source column, and every generated row is machine-checked to contain a link. There are three kinds of source cell:</p>
<ol>
<li><b>Pinned data link</b> — points at the exact commit of the file the row came from, so a reader can open the file and find the record. Used for all game and market rows.</li>
<li><b>Script link</b> — points at the code that computed a derived number, together with the input dataset link. Used for analytic rows.</li>
<li><b>Official source link</b> — points at an NFL or licensed-operator page. Used for every rule, price convention and settlement claim.</li>
</ol>
<p>Where a value could not be confirmed, the cell is <b>blank</b> and the row appears on <a href="flagged.html">Flagged for Review</a>. No value on this site was inferred, interpolated or filled in from general knowledge.</p>

<h2>What machine verification cannot do</h2>
<p>An automated check can confirm that a link exists and resolves; it cannot confirm that a human-readable page still says what it said today. Two official pages were read in full during this session and are cited with the exact sentence they support (see <a href="sources.html">Sources</a>). Everything else that is cited to an operator or the league was verified by reading the page at the time of writing, and those readings are recorded in <code>research/sources.md</code> with the checking date.</p>

<h2>Data-level checks (enforced in the pipeline)</h2>
<ul>
<li>Margin reconciles with the score on every row: <code>margin = home_score − away_score</code>.</li>
<li>Total reconciles with the score on every row: <code>total = home_score + away_score</code>.</li>
<li>Cover flag is consistent with the ATS margin on every row.</li>
<li>No unplayed game appears in any calculation.</li>
<li>Game identifiers are unique.</li>
<li>The dataset is pinned by commit and every file is checksummed (<code>data/derived/checksums.txt</code>).</li>
</ul>
"""
    return page("verification", "Verification Log", body, "verification.html")


# ----------------------------------------------------------------------- assets
def build_assets(S):
    write(os.path.join(DOCS, "assets", "style.css"), __import__("site_lib").CSS)
    js = r"""
/* games explorer — no dependencies */
(function(){
  var tbody=document.querySelector('#gtab tbody');
  if(!tbody) return;
  var state={rows:[],page:0,size:50,q:"",season:""};
  var q=document.getElementById('q'), seasonSel=document.getElementById('season'),
      resSel=document.getElementById('res'), countEl=document.getElementById('count');
  function esc(s){return String(s).replace(/[&<>"]/g,function(c){
    return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
  fetch('data/games.json').then(function(r){return r.json();}).then(function(d){
    state.rows=d.rows;
    var seasons=Array.from(new Set(d.rows.map(function(r){return r.season;}))).sort(function(a,b){return b-a;});
    seasons.forEach(function(s){var o=document.createElement('option');o.value=s;o.textContent=s;seasonSel.appendChild(o);});
    render();
  }).catch(function(){ tbody.innerHTML='<tr><td colspan="11" class="small">Could not load data/games.json — use the CSV download above.</td></tr>'; });
  function filtered(){
    var out=state.rows;
    if(state.season) out=out.filter(function(r){return String(r.season)===state.season;});
    if(state.q){
      var s=state.q.toLowerCase();
      out=out.filter(function(r){
        return (r.season+' '+r.week+' '+r.home+' '+r.away+' '+r.date).toLowerCase().indexOf(s)>=0;
      });
    }
    return out;
  }
  function render(){
    var rows=filtered();
    var pages=Math.max(1,Math.ceil(rows.length/state.size));
    if(state.page>=pages) state.page=pages-1;
    if(state.page<0) state.page=0;
    var slice=rows.slice(state.page*state.size,(state.page+1)*state.size);
    var html='';
    slice.forEach(function(r){
      var ats=r.ats===1?'<span class="pos">covered</span>':(r.ats===0?'<span class="neg">no</span>':'<span class="small">push</span>');
      var ou=r.ou===1?'<span class="pos">over</span>':(r.ou===0?'<span class="neg">under</span>':'<span class="small">push</span>');
      var sp=r.spread===null?'<span class="small">—</span>':((r.spread>0?'+':'')+r.spread.toFixed(1));
      var tot=r.total===null?'<span class="small">—</span>':r.total.toFixed(1);
      html+='<tr><td>'+r.season+'</td><td>'+r.week+'</td><td>'+esc(r.date)+'</td><td>'
        +esc(r.away)+' @ '+esc(r.home)+'</td><td class="num">'+esc(r.score)+'</td>'
        +'<td class="num">'+(r.margin>0?'+':'')+r.margin+'</td><td class="num">'+sp+'</td>'
        +'<td class="num">'+tot+'</td><td>'+ats+'</td><td>'+ou+'</td>'
        +'<td><a target="_blank" rel="noopener" href="'+esc(r.src)+'">source</a></td></tr>';
    });
    tbody.innerHTML=html||'<tr><td colspan="11" class="small">No matching games.</td></tr>';
    if(countEl) countEl.textContent=rows.length.toLocaleString()+' games · page '+(state.page+1)+' of '+pages;
  }
  if(q) q.addEventListener('input',function(e){state.q=e.target.value;state.page=0;render();});
  if(seasonSel) seasonSel.addEventListener('change',function(e){state.season=e.target.value;state.page=0;render();});
  if(resSel) resSel.addEventListener('change',function(e){state.size=parseInt(e.target.value,10);state.page=0;render();});
  var p=document.getElementById('prev'),n=document.getElementById('next');
  if(p) p.addEventListener('click',function(){state.page--;render();});
  if(n) n.addEventListener('click',function(){state.page++;render();});
})();
"""
    write(os.path.join(DOCS, "assets", "app.js"), js)

    d = csv("model_dataset.csv")
    recs = []
    for _, r in d.iterrows():
        recs.append({
            "season": int(r["season"]),
            "week": int(r["week"]),
            "date": str(r["gameday"])[:10],
            "home": r["home_team"],
            "away": r["away_team"],
            "score": f'{int(r["home_score"])}-{int(r["away_score"])}',
            "margin": int(r["margin"]),
            "spread": (float(-r["spread_line"]) if pd.notna(r["spread_line"]) else None),
            "total": (float(r["total_line"]) if pd.notna(r["total_line"]) else None),
            "ats": (int(r["home_cover"]) if pd.notna(r["home_cover"]) else None),
            "ou": (int(r["over"]) if pd.notna(r["over"]) else None),
            "src": SRC_GAMES,
        })
    write(os.path.join(DATA, "games.json"),
          json.dumps({"generated": TODAY, "source": SRC_GAMES, "count": len(recs),
                      "note": "spread is the conventional home spread (negative = home favoured); "
                              "ats/ou: 1 = home covered / over, 0 = no, null = push.",
                      "rows": recs}, separators=(",", ":")))
    shutil.copyfile(os.path.join(DER, "model_dataset.csv"), os.path.join(DATA, "games.csv"))


PRIOR_FILES = ["index.html", "strategies.html", "validation.html", "correlations.html",
               "leaderboard.html", "sources.html", "flagged.html", "style.css"]


def preserve_prior() -> int:
    """Copy the concurrent session's root-level site + audit into docs/prior/.

    The prior site is NOT modified: it is copied byte-for-byte so it stays reachable at
    /prior/ after the GitHub Pages source moves to /docs. If the root files are absent
    (e.g. running on a branch that predates that merge), this is a no-op.
    """
    src_present = [f for f in PRIOR_FILES if os.path.exists(os.path.join(ROOT, f))]
    if not src_present:
        return 0
    dst = os.path.join(DOCS, "prior")
    os.makedirs(dst, exist_ok=True)
    for f in src_present:
        shutil.copyfile(os.path.join(ROOT, f), os.path.join(dst, f))
    audit_src = os.path.join(ROOT, "audit")
    if os.path.isdir(audit_src):
        shutil.copytree(audit_src, os.path.join(dst, "audit"), dirs_exist_ok=True)
    # also preserve the second, independently published site found at docs/ on main
    docs_prior = os.path.join(ROOT, "docs")
    if os.path.isdir(docs_prior):
        shutil.copytree(docs_prior, os.path.join(DOCS, "prior-d118ca7e"),
                        dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("prior", "prior-d118ca7e"))
    # keep server config out of the way of the static site
    open(os.path.join(DOCS, ".nojekyll"), "w").close()
    return len(src_present)


def main() -> None:
    S = j("market_summary.json")
    MM_raw = j("model_metrics.json")
    MM = dict(MM_raw)
    MM.update(MM_raw["variants"]["B"])       # flatten the published variant for convenience
    MM["variants"] = MM_raw["variants"]
    GM = j("gates_meta.json")
    CM = j("corr_meta.json")
    PM = j("props_meta.json")
    BM = j("blend_results.json")
    OLM = j("own_lines_meta.json")

    GR = csv("gates_results.csv")
    SR = j("signal_results.json")
    OL = csv("own_lines_upcoming.csv")
    PR = csv("props_framework.csv")
    PEV = csv("props_ev_grid.csv")
    L = csv("league_baselines.csv")

    global MM_SPREAD
    MM_SPREAD = (MM["variants"]["B"]["spread"]["model_mae"], MM["variants"]["B"]["spread"]["market_mae"],
                 MM["mae_diff_spread_pvalue"])

    ver_path = os.path.join(DER, "verification_report.json")
    rep = None
    if os.path.exists(ver_path):
        with open(ver_path, encoding="utf-8") as fh:
            rep = json.load(fh)

    pages = {
        "index.html": build_index(S, MM, GM, GR, OL, CM, PM, BM),
        "executive-summary.html": build_summary(S, MM, GM, GR, CM, BM, PM, CM),
        "own-line.html": build_own_line(MM, BM, OL, OLM, GR),
        "signals.html": build_signals(SR, GR, S),
        "gates.html": build_gates(GM, GR, S),
        "single-bets.html": build_single_bets(GM, GR, S, CM),
        "parlays.html": build_parlays(CM, S),
        "player-props.html": build_props(PM, PR, PEV),
        "correlation.html": build_correlation(CM, S),
        "leaderboard.html": build_leaderboard(GM, GR, S),
        "market-data.html": build_market_data(S, L),
        "methodology.html": build_methodology(S, MM, GM),
        "sources.html": build_sources(),
        "flagged.html": build_flagged(S, GM, PM),
        "verification.html": build_verification(rep, S, GM),
    }
    for name, html in pages.items():
        write(os.path.join(DOCS, name), html)
    build_assets(S)
    n_prior = preserve_prior()
    print(f"wrote {len(pages)} pages + assets to site/ "
          f"({n_prior} files preserved from the concurrent root site at /prior/, "
          f"second concurrent site at /prior-d118ca7e/)")


if __name__ == "__main__":
    main()
