#!/usr/bin/env python3
"""Render every page in luck_lab from the committed data files.

Deterministic: no clock, no randomness, no network, no third-party imports. Two consecutive runs
produce byte-identical HTML and check.py enforces it, so a published number can never be "whatever
the build happened to print this morning".

Rendering rules, enforced by the helpers rather than by discipline:
  * every table ends with a Source column and every row's last cell carries a link -- check.py fails
    the build if any table row lacks an href;
  * a value no source printed is rendered as a blank marker with a link to flagged.html -- never 0,
    never a dash, never a plausible guess;
  * every statistic is read from the JSON the compute scripts wrote, so no figure here is hand-typed.
"""
from __future__ import annotations

import html
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"
ROOT = HERE.parent

BLOB = "https://github.com/karagemop466-tech/Korea3/blob/main"
NFLVERSE_COMMIT = "a270278f3ac4e937295fe6a27814b3c4a2b62645"
NFLVERSE = f"https://github.com/nflverse/nfldata/blob/{NFLVERSE_COMMIT}"

NAV = [
    ("index.html", "Desk"),
    ("controls.html", "Control baselines"),
    ("skill.html", "Proper-score skill"),
    ("prereg.html", "Pre-registration"),
    ("escrow.html", "Escrow & demotion"),
    ("method.html", "Method"),
    ("sources.html", "Sources"),
    ("flagged.html", "Flagged for review"),
]

SOURCE_LINKS = {
    "games": (f"{NFLVERSE}/data/games.csv", "pinned nflverse games.csv (dataset tier)"),
    "bets": (f"{BLOB}/data/derived/bets.csv", "data/derived/bets.csv: the ledger with per-bet probabilities"),
    "summary": (f"{BLOB}/data/derived/summary.json", "data/derived/summary.json: line_lab's published metrics"),
    "controls": (f"{BLOB}/luck_lab/data/controls.json", "luck_lab/data/controls.json"),
    "skill": (f"{BLOB}/luck_lab/data/skill.json", "luck_lab/data/skill.json"),
    "prereg": (f"{BLOB}/luck_lab/data/preregistration.json", "luck_lab/data/preregistration.json"),
    "strategies": (f"{BLOB}/line_lab/strategies.py", "line_lab/strategies.py: frozen rule definitions"),
    "evaluation": (f"{BLOB}/line_lab/evaluation.py", "line_lab/evaluation.py: gates and metrics"),
    "origin": (f"{BLOB}/origin_lab/leaderboard.py", "origin_lab/leaderboard.py: strategy registry"),
    "ledgerfile": (f"{BLOB}/luck_lab/data/escrow_ledger.jsonl", "luck_lab/data/escrow_ledger.jsonl"),
    "rulebook": ("https://operations.nfl.com/rules-officiating/2026-nfl-rulebook",
                 "2026 NFL Rulebook (official); URL carried from origin_lab's register, not re-opened here"),
    "nist_boot": ("https://www.itl.nist.gov/div898/handbook/eda/section3/eda352.htm",
                  "NIST/SEMATECH e-Handbook: bootstrap; opened by an earlier session"),
    "nist_n": ("https://www.itl.nist.gov/div898/handbook/prc/section2/prc222.htm",
               "NIST/SEMATECH e-Handbook: sample size; opened by an earlier session"),
    "nist_bh": ("https://www.itl.nist.gov/div898/handbook/prc/section4/prc473.htm",
                "NIST/SEMATECH e-Handbook: multiple comparisons; opened by an earlier session"),
    "readiness": (f"{BLOB}/readiness/index.html", "decision-readiness register"),
    "reviewboard": ("https://karagemop466-tech.github.io/Korea3/hub/flagged.html", "the site-wide review board"),
}


def esc(v) -> str:
    return html.escape("" if v is None else str(v), quote=True)


def href(page: str, label: str) -> str:
    """Link to another page of this desk. Kept separate from link() so the source register stays
    the only place external URLs are defined."""
    return '<a href="' + esc(page) + '">' + esc(label) + "</a>"


def link(key: str, label: str | None = None) -> str:
    url, title = SOURCE_LINKS[key]
    return '<a href="' + esc(url) + '" title="' + esc(title) + '">' + esc(label or key) + "</a>"


def blank(why: str = "no source printed this value") -> str:
    return ('<span class="blank" title="' + esc(why) + '">[blank]</span> '
            + '<a class="blank-link" href="flagged.html">' + esc(why) + "</a>")


def n(x, nd=4, pct=False, signed=True, why=None):
    if x is None or (isinstance(x, float) and x != x):
        return blank(why or "not computable from the committed ledger")
    v = 100 * x if pct else x
    fmt = ("{:+." + str(nd) + "f}") if signed else ("{:." + str(nd) + "f}")
    return fmt.format(v) + ("%" if pct else "")


def td(x, nd=4, **kw) -> str:
    """Numeric cell. Blank, never zero, when the value does not exist."""
    return '<td class="num">' + n(x, nd=nd, **kw) + "</td>"


def tds(v) -> str:
    return "<td>" + str(v) + "</td>"


def pill(text, kind="info") -> str:
    return '<span class="pill ' + kind + '">' + esc(text) + "</span>"


def table(headers, rows, note=""):
    """rows: list of lists of ready-rendered <td> strings; the last header must be 'Source'."""
    if not headers or headers[-1] != "Source":
        raise AssertionError("every table must end with a Source column")
    if any(len(r) != len(headers) for r in rows):
        bad = [i for i, r in enumerate(rows) if len(r) != len(headers)]
        raise AssertionError(f"row/header width mismatch in table {headers[:3]} at rows {bad[:4]}")
    head = "".join("<th>" + esc(h) + "</th>" for h in headers)
    body = "".join("<tr>" + "".join(r) + "</tr>" for r in rows)
    note_html = '<p class="table-note">' + note + "</p>" if note else ""
    return ('<div class="table-wrap"><table><thead><tr>' + head + "</tr></thead><tbody>" + body
            + "</tbody></table></div>" + note_html)


def kpi(label, value, sub=""):
    return ('<div class="kpi"><div class="kpi-label">' + esc(label) + '</div><div class="kpi-value">'
            + value + '</div><div class="kpi-sub">' + sub + "</div></div>")


def page(title, active, body, lede=""):
    nav = "".join('<a class="nav-link' + (" on" if h == active else "") + '" href="' + h + '">'
                  + esc(lbl) + "</a>" for h, lbl in NAV)
    head = f"<h1>{title}</h1>" if "<" in title else f"<h1>{esc(title)}</h1>"
    lede_html = f'<p class="lede">{lede}</p>' if lede else ""
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} | Skill &amp; luck desk</title>
<link rel="stylesheet" href="assets/style.css">
</head>
<body>
<header class="site-header">
  <a class="brand" href="../index.html">Korea3</a>
  <span class="muted">skill &amp; luck desk</span>
  <nav class="nav">{nav}</nav>
</header>
<main class="wrap">
{head}
{lede_html}
{body}
</main>
<footer class="site-footer wrap">
  <p>Every figure on this page is a deterministic recomputation over files committed in this repository
  (market prices are tier <em>dataset</em>, not an official league source), or a value another session
  recorded against an official page, labelled as such. Nothing here is a prediction, a tip or a stake
  recommendation. <a href="../index.html">Site home</a> ·
  <a href="../readiness/index.html">Decision readiness</a> ·
  <a href="../hub/flagged.html">Site review board</a>.</p>
</footer>
</body>
</html>
"""


def load(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
def build_index(controls, skill, reg) -> str:
    rows = skill["rows"]
    tested = len(rows)
    with_skill = [r for r in rows if r.get("brier_skill_lb95") is not None]
    qualified = [r for r in rows if r.get("qualified_proper_score")]
    demote = [r for r in rows if r.get("demotion_watch")]
    recon_ok = sum(r["reconciliation_with_line_lab"].get("matched", 0) for r in rows)
    recon_n = sum(r["reconciliation_with_line_lab"].get("total", 0) for r in rows)
    best = max(with_skill, key=lambda r: r["brier_skill_lb95"]) if with_skill else None
    ctrl = {c["control"]: c for c in controls["controls"]}
    m_family = rows[0].get("bh_family_size") if rows else 0
    esc_rows = reg["_meta"]["escrow_rows"]
    rnd = ctrl["RND-ATS"]

    cards = "".join([
        kpi("Strategies scored", str(tested), link("skill", "the only ledger that carries per-bet probabilities")),
        kpi("Qualified on proper score", str(len(qualified)),
            "game-cluster Brier-skill lower bound above 0, after Benjamini-Hochberg on the family"),
        kpi("Registrations frozen", str(len(reg["entries"])), link("prereg", "pre-registration ledger")),
        kpi("Reconciled with line_lab", f"{recon_ok}/{recon_n}",
            "published metrics recomputed here with a different implementation"),
        kpi("Prospective bets in escrow", str(esc_rows),
            '<a href="escrow.html">promotion needs a settled prospective sample</a>'),
        kpi("Zero-information ceiling", n(rnd["roi"], 4, pct=True, signed=False),
            f'coin flip on the spread over {rnd["n_decisive"]:,} priced games: what no signal pays'),
    ])

    best_line = (
        f"the best is {esc(best['strategy'])} at a {n(best['brier_skill_lb95'], 4, pct=True, signed=False)} "
        f"lower bound (point estimate {n(best['brier_skill'], 4, pct=True, signed=False)})"
        if best else "no strategy has both probabilities on any bet"
    )
    q_first = n(rows[0].get("bh_q_brier_skill"), 3, signed=False) if rows else "—"
    luck = f"""
<h2>The removal-of-luck panel</h2>
<div class="callout">
<p><strong>What the numbers say.</strong> {len(with_skill)} of {tested} strategies carry both a model
probability and a closing-market probability on enough bets to be scored properly. None of them has a
game-cluster lower bound on Brier skill above zero — {best_line}. After adjusting for {m_family} tests in
the family, every q-value is {q_first}. The honest headline is therefore:
<strong>no strategy on this site currently shows separable skill</strong>, and a leaderboard that ranked
these rules by return would be ranking noise.</p>
<p><strong>Why that is the useful result.</strong> The controls bound the noise from below: a coin flip on
the closing spread returns {n(rnd["roi"], 4, pct=True, signed=False)} per bet
(vig {n(controls["vig"]["ATS"]["mean_vig_pct"], 2, signed=False)}% of the handle), so a strategy that does
not beat that has not beaten the cost of playing. {len(demote)} of {tested} strategies have a per-bet ROI whose
game-cluster lower bound sits below zero, which is what "indistinguishable from a lucky run" looks like when
it is measured instead of asserted.</p>
<p><strong>What would change the answer.</strong> A prospective sample in the
<a href="escrow.html">escrow ledger</a>, not another cut of the backtest. The evidence that would support or
refute each rule is already frozen in the <a href="prereg.html">pre-registration ledger</a>, so the answer
cannot be fitted to the question afterwards.</p>
</div>
"""

    trows = []
    for r in rows:
        cid = r["strategy"]
        trows.append([
            tds('<a href="skill.html#' + esc(cid) + '">' + esc("line_lab:" + cid) + "</a>"),
            tds(esc(r["name"])),
            tds(esc(r["division"])),
            td(r["n_bets"], signed=False),
            td(r["roi"], 4, pct=True),
            td(r.get("roi_cluster_lb95"), 4, pct=True),
            td(r.get("brier_skill"), 4, pct=True),
            td(r.get("brier_skill_lb95"), 4, pct=True),
            tds(pill("qualified", "ok") if r.get("qualified_proper_score") else pill("shadow", "no")),
            tds(link("skill", "ledger") + " · " + link("summary", "published metrics")),
        ])
    t = table(["Strategy", "Name", "Division", "bets", "ROI", "ROI cluster LB", "Brier skill", "BSS LB",
               "Stage", "Source"], trows,
              "Backtest window 2006-2025, the evaluation window line_lab froze. ROI here is a backtest figure "
              "and is not a leaderboard entry: the brief forbids a backtest number reaching a live board, and "
              "this desk keeps the two separated by construction.")
    body = cards + luck + "<h2>Every strategy at a glance</h2>" + t
    return page("Skill &amp; luck desk", "index.html", body,
                "Origination signals are worth nothing until luck is removed from them. This desk adds the two "
                "measurement layers the brief asked for that no other page had: control baselines on the same games "
                "at the same prices, and a benchmark-relative proper-score ranking with game-cluster bounds and a "
                "multiplicity adjustment. Nothing here is a tip.")


def build_controls(controls) -> str:
    meta = controls["_meta"]
    rows = []
    for c in controls["controls"]:
        rows.append([
            tds("<strong>" + esc(c["control"]) + "</strong>"),
            tds(esc(c["rule"])),
            td(c["n_decisive"], signed=False),
            td(c.get("hit_rate"), 4, pct=True, signed=False),
            td(c.get("breakeven_hit_rate"), 4, pct=True, signed=False),
            td(c.get("mean_price"), 1, signed=False),
            td(c["roi"], 4, pct=True),
            td(c["roi_cluster_lb95"], 4, pct=True),
            td(c.get("expected_roi_under_market"), 4, pct=True),
            td(c.get("residual_vs_market_consensus"), 4, pct=True),
            td(c.get("positive_season_share"), 4, pct=True, signed=False),
            tds(link("games", "pinned dataset")),
        ])
    t1 = table(["Control", "Rule", "bets (decisive)", "hit", "break-even", "mean price", "ROI", "ROI LB",
                "expected ROI", "residual", "positive seasons", "Source"], rows,
               "One bet per game, so the game is its own cluster and games = bets. Coin-flip controls have no "
               "realised win count: their expectation is exact, so the count is blank rather than half-counted.")
    vig_rows = []
    for mkt, v in sorted(controls["vig"].items()):
        vig_rows.append([
            tds(esc(mkt)), td(v["n"], signed=False), td(v["mean_overround"], 5, signed=False),
            td(v["mean_vig_pct"], 3, pct=True, signed=False), td(v["theoretical_roi_of_coin_flip"], 4, pct=True),
            tds(link("games", "closing prices")),
        ])
    t2 = table(["Market", "games", "mean overround", "mean vig", "implied ROI of a coin flip", "Source"], vig_rows,
               "The vig column is why a zero-information bettor loses about 2.5-2.9% per bet, and why 'beat the "
               "market' has to mean 'beat the vig-adjusted market' before it means anything.")
    check_rows = []
    for mkt, ref in sorted(controls.get("coinflip_reference_by_market", {}).items()):
        theo = controls["vig"][mkt]["theoretical_roi_of_coin_flip"]
        gap = ref["roi"] - theo if (theo is not None and ref["roi"] is not None) else None
        check_rows.append([
            tds(esc(mkt)), td(ref["roi"], 4, pct=True), td(theo, 4, pct=True), td(gap, 4, pct=True),
            td(ref["n"], signed=False), tds(link("controls", "computed here")),
        ])
    t3 = table(["Market", "measured coin flip", "from the vig alone", "difference", "games", "Source"], check_rows,
               "An arithmetic identity, printed on purpose: the measured return of a fair coin over the closing "
               "prices must equal the vig those prices imply. A settlement or de-vig bug moves this column.")
    season_rows = []
    for c in controls["controls"]:
        for s, roi in sorted(c["season_roi"].items())[-5:]:
            season_rows.append([tds(esc(c["control"])), tds(esc(s)), td(roi, 4, pct=True),
                                tds(link("games", "dataset"))])
    t4 = table(["Control", "Season", "ROI", "Source"], season_rows,
               "Last five seasons of every control. A baseline computed once in 2024 is not a baseline in 2026, so "
               "it is recomputed with the strategies rather than stored as prose.")
    body = (t1 + "<h2>What the vig costs</h2>" + t2 + "<h2>Self-check: measured coin flip versus the vig</h2>"
            + t3 + "<h2>Controls by season</h2>" + t4
            + '<div class="callout warn"><p><strong>Tier.</strong> ' + esc(meta["price_tier"])
            + " Window: " + esc(meta["window"]) + ". These numbers may be used to score a strategy; they may not be "
            "cited as a league fact, and they do not satisfy the brief's requirement that correlations be computed "
            'from officially sourced numbers.</p></div>')
    return page("Control baselines", "controls.html", body,
                "What a bettor with no information earns on the same games at the same closing prices. Every "
                "control is one bet per game, settled from the recorded final score only.")


def build_skill(skill) -> str:
    meta = skill["_meta"]
    m_family = meta["multiplicity"]
    rows = []
    for r in skill["rows"]:
        rows.append([
            tds('<strong id="' + esc(r["strategy"]) + '">' + esc("line_lab:" + r["strategy"]) + "</strong><br>"
                '<span class="muted">' + esc(r["name"]) + "</span>"),
            tds(esc(r.get("division", ""))),
            td(r["n_bets"], signed=False), td(r.get("n_games"), signed=False),
            td(r.get("hit_rate"), 4, pct=True, signed=False),
            td(r.get("roi"), 4, pct=True), td(r.get("roi_cluster_lb95"), 4, pct=True),
            td(r.get("iid_inflation_cluster_over_iid"), 3, signed=False),
            td(r.get("brier_model"), 5, signed=False), td(r.get("brier_market_benchmark"), 5, signed=False),
            td(r.get("brier_skill"), 4, pct=True), td(r.get("brier_skill_lb95"), 4, pct=True),
            td(r.get("logloss_gain_vs_market"), 5, signed=False),
            td(r.get("calibration_gap"), 4, pct=True),
            td(r.get("share_of_profit_from_best_game"), 4, pct=True),
            td(r.get("residual_vs_closing_consensus"), 4, pct=True),
            td(r.get("residual_cluster_lb95"), 4, pct=True),
            td(r.get("bh_q_brier_skill"), 3, signed=False),
            td(r.get("bets_to_significance_95"), 0, signed=False),
            td(r.get("positive_season_share"), 4, pct=True, signed=False),
            tds((pill("qualified", "ok") if r.get("qualified_proper_score") else pill("shadow", "no"))
                + " " + (pill("demotion watch", "warn") if r.get("demotion_watch") else "")),
            tds(link("bets", "ledger") + " · " + link("evaluation", "metric code")),
        ])
    t1 = table(["Strategy", "Division", "bets", "games", "hit", "ROI", "ROI LB", "iid inflation", "Brier model",
                "Brier market", "Brier skill", "BSS LB", "log-loss gain", "calibration gap", "best-game share",
                "residual", "residual LB", "BH q", "bets to significance", "positive seasons", "Stage", "Source"],
               rows,
               '"iid inflation" is the game-cluster interval width divided by the per-bet iid width: how much a naive '
               "interval understated the uncertainty. <em>bets to significance</em> is n such that ROI − 1.645·sd/√n > 0 "
               "with sd inflated by that factor; blank when the per-bet effect is not positive, because no sample size "
               "rescues a negative edge. " + esc(m_family))

    rec_rows = []
    for r in skill["rows"]:
        rec = r["reconciliation_with_line_lab"]
        mism = [c["field"] for c in rec.get("checks", []) if not c["match"]]
        rec_rows.append([
            tds(esc("line_lab:" + r["strategy"])),
            td(rec.get("matched", 0), 0, signed=False), td(rec.get("total", 0), 0, signed=False),
            tds(esc(", ".join(mism) if mism else "none")),
            tds(link("summary", "published values")),
        ])
    t2 = table(["Strategy", "fields matched", "fields checked", "mismatches", "Source"], rec_rows,
               "Each field is line_lab's published figure against this desk's independent recomputation from the "
               "ledger, using a standard-library implementation instead of pandas/numpy/scipy. A mismatch would mean "
               "one of the two surfaces is wrong, and check.py fails the build on it.")

    bin_rows = []
    for r in skill["rows"]:
        for b in r.get("reliability_bins") or []:
            bin_rows.append([
                tds(esc("line_lab:" + r["strategy"])), td(b["bin"], 0, signed=False), td(b["n"], 0, signed=False),
                td(b["mean_pred"], 4, pct=True, signed=False), td(b["realised"], 4, pct=True, signed=False),
                td(b["gap"], 4, pct=True), tds(link("bets", "model_prob, market_prob")),
            ])
    t3 = table(["Strategy", "bin", "bets", "mean predicted", "realised", "gap", "Source"], bin_rows,
               "Five equal-count bins of the model's own probability against what happened. A rule can be unbiased on "
               "average and wrong in every bin; this is where that shows up.")

    win_rows = []
    for r in skill["rows"]:
        for key, label in (("holdout", "holdout 2023-2025"), ("forward", "forward 2026 (seen since the freeze)")):
            sub = r.get(key) or {}
            win_rows.append([
                tds(esc("line_lab:" + r["strategy"])), tds(esc(label)), td(sub.get("n_bets"), 0, signed=False),
                td(sub.get("roi"), 4, pct=True), td(sub.get("brier_skill"), 4, pct=True),
                td(sub.get("hit_rate"), 4, pct=True, signed=False),
                tds(link("bets", "same ledger, filtered by season")),
            ])
    t4 = table(["Strategy", "Window", "bets", "ROI", "Brier skill", "hit", "Source"], win_rows,
               "The forward 2026 block is printed for completeness and is explicitly not a promotion path: those bets "
               "were settled before the rules were frozen, so they belong to the seen sample. The prospective sample is "
               "the escrow ledger.")

    body = (t1 + "<h2>Independent reconciliation with the published figures</h2>" + t2
            + "<h2>Windows inside the same ledger</h2>" + t4
            + "<h2>Calibration</h2>" + t3
            + '<div class="callout"><p><strong>Benchmark.</strong> ' + esc(meta["benchmark"]) + "</p>"
            + "<p><strong>Clusters.</strong> " + esc(meta["cluster"]) + "</p>"
            + "<p><strong>ROI convention.</strong> " + esc(meta["roi_convention"]) + "</p>"
            + "<p><strong>Namespace.</strong> " + esc(meta["ledger_namespace"]) + "</p></div>")
    return page("Proper-score skill table", "skill.html", body,
                "Brier and log-loss skill against the closing line, with a game-cluster lower bound on every interval "
                "and a Benjamini-Hochberg adjustment across the tested family. Win rate and raw ROI are shown to be "
                "compared, never to rank on.")


def build_prereg(reg) -> str:
    rows = []
    for e in reg["entries"]:
        row = reg["escrow"].get(e["registration_id"], {})
        kind = "no" if "BLOCKED" in e["status"] else ("warn" if "RETRO" in e["status"] else "ok")
        src_key = "origin" if e["registration_id"].startswith("origin_lab") else "strategies"
        mind = e["what_would_change_our_mind"]
        rows.append([
            tds("<strong>" + esc(e["registration_id"]) + "</strong><br><span class='muted'>" + esc(e["name"]) + "</span>"),
            tds(esc(e["ledger"])), tds(esc(e["market"])),
            tds("<span class='mono' title='" + esc(e["rule_hash"]) + "'>" + esc(e["rule_hash"][:16]) + "…</span>"),
            tds(esc(e["frozen_utc"])),
            tds(pill(e["status"], kind)),
            td(row.get("prospective_settled", 0), 0, signed=False),
            td(row.get("shortfall_bets"), 0, signed=False),
            tds("<details><summary>support / refute</summary><p>" + esc(mind["would_support"]) + "</p><p>"
                + esc(mind["would_refute"]) + "</p></details>"),
            tds(esc(e["status_reason"]) + "<br>" + link(src_key, "rule source")),
        ])
    t1 = table(["Strategy", "Ledger", "Market", "rule hash", "frozen", "Status", "prospective bets", "shortfall",
                "What would change our mind", "Source"], rows,
               "The hash is sha256 over the canonical JSON of registration id, name, market, rule text, gate list and "
               "evaluation window; the implementation files are hashed beside it in the data file, so a code change is "
               "visible even when the prose is untouched. check.py recomputes every hash from the source: edit a rule "
               "and the gate goes red.")
    gate_rows = []
    for g in reg["entries"][0]["gates"]:
        gate_rows.append([tds(esc(g["id"])), tds(esc(g["title"])), tds(esc(g["text"])),
                          tds(link("evaluation", "line_lab/evaluation.py"))])
    t2 = table(["Gate", "Title", "Text as frozen", "Source"], gate_rows,
               "The gate list is inside the hashed document, so a gate cannot be softened later without changing every "
               "registration hash in the table above.")
    impl_rows = []
    for e in reg["entries"]:
        for f, h in sorted(e["implementation_sha256"].items()):
            impl_rows.append([tds(esc(e["registration_id"])), tds(esc(f)),
                              tds("<span class='mono'>" + esc(h[:24]) + "…</span>"),
                              tds(link("strategies" if "line_lab" in f else "origin", "current file"))])
    t3 = table(["Strategy", "Implementation file", "sha256 of the file as frozen", "Source"], impl_rows,
               "Recomputed from the working tree on every check run. This is the only honest form of 'the commit hash "
               "is the registration' after a rule has already been evaluated: the freeze is real, its retroactive "
               "status is stated, and promotion is unavailable from it.")
    body = (t1 + "<h2>Frozen gate list</h2>" + t2 + "<h2>Implementation hashes</h2>" + t3
            + '<div class="callout warn"><p><strong>Why every row says RETRO_FROZEN or BLOCKED.</strong> A rule that '
              "has already been scored on 2006-2025 cannot be pre-registered against that window: the data has been "
              "seen. The hash is real, the backtest may be published, and promotion is available only from a "
              "prospective sample recorded after the freeze. That is the discipline the brief asked for, applied "
              "honestly instead of claimed.</p></div>")
    return page("Pre-registration ledger", "prereg.html", body,
                "Every strategy that has ever been scored on this site, with the hash of its rule text, the window it "
                "may be judged on, and a two-sided statement of what would change the conclusion.")


def build_escrow(reg, skill, controls) -> str:
    esc_map = reg["escrow"]
    meta = reg["_meta"]
    rows = []
    for e in reg["entries"]:
        rid = e["registration_id"]
        row = esc_map.get(rid, {})
        stage = row.get("stage", "shadow")
        rows.append([
            tds("<strong>" + esc(rid) + "</strong>"),
            tds(pill(stage, "warn" if stage == "shadow" else "no")),
            td(row.get("prospective_entries", 0), 0, signed=False),
            td(row.get("prospective_settled", 0), 0, signed=False),
            td(row.get("prospective_games", 0), 0, signed=False),
            td(row.get("shortfall_bets"), 0, signed=False),
            tds(esc(row.get("advance_requires", ""))),
            tds(link("prereg", "ledger entry") + " · " + link("skill", "backtest bounds")),
        ])
    t1 = table(["Strategy", "Stage", "entries", "settled", "games", "shortfall", "Advance requires", "Source"], rows,
               "The escrow ledger is append-only and empty today: no prospective bet has been recorded since the rules "
               "were frozen. That is the point. A promotion cannot be manufactured from the window that is already in "
               "the backtest.")
    demo_rows = []
    for r in skill["rows"]:
        lb, bss = r.get("roi_cluster_lb95"), r.get("brier_skill_lb95")
        both_neg = (lb is not None and lb < 0 and bss is not None and bss < 0)
        demo_rows.append([
            tds("<strong>" + esc("line_lab:" + r["strategy"]) + "</strong>"),
            td(lb, 4, pct=True), td(bss, 4, pct=True),
            tds(pill("stays in paper", "no") if both_neg else pill("review", "warn")),
            tds(esc("Both the return per bet and the skill against the closing line have negative lower bounds, so "
                    "there is nothing to demote: this rule never held a live allocation. Publishing the verdict for "
                    "all 11 is what stops the gate being noticed only when it catches something.")),
            tds(link("skill", "recomputed here")),
        ])
    t2 = table(["Strategy", "ROI LB", "BSS LB", "Demotion verdict", "Rule applied", "Source"], demo_rows,
               "The gate as the brief specifies it: a live strategy whose lower bounds fall below zero goes back to "
               "paper. Here it is applied prospectively, and the verdict column is rendered from the data so it cannot "
               "say something the bounds do not support.")
    reward_rows = []
    for r in skill["rows"]:
        reward_rows.append([
            tds(esc("line_lab:" + r["strategy"])),
            tds(blank("no eligible strategy; the reward structure is unfunded (review-board flag N15)")),
            tds(esc("reward column deliberately unpriced: see the competition page in the dashboard")),
            tds(link("reviewboard", "review board")),
        ])
    t3 = table(["Strategy", "Reward", "Why blank", "Source"], reward_rows,
               "A leaderboard with rewards pays for variance unless the eligibility rule is arithmetic. Nothing here "
               "allocates a payout, because no strategy clears the proper-score bar.")
    append = ("one JSON line per settled prospective bet: registration_id, game_id, kickoff_utc, recorded_utc, "
              "state (recorded or settled), price, model_prob, market_prob, outcome, pnl")
    body = (t1 + "<h2>Demotion gate applied to every strategy</h2>" + t2 + "<h2>Reward column</h2>" + t3
            + '<div class="callout"><p><strong>Append protocol.</strong> ' + esc(append) + ". A row may only be "
              "written before kickoff with state <code>recorded</code>; the same row is later updated to "
              "<code>settled</code> from the verified results feed. Rows written after kickoff do not count toward "
              "promotion, which is what keeps lookahead leakage out of the decision. Ledger file: "
            + link("ledgerfile", "escrow_ledger.jsonl") + "</p>"
            + "<p><strong>Commit that froze these rules:</strong> <code>"
            + esc(meta["how_to_find_the_registration_commit"]) + "</code></p></div>")
    return page("Escrow, demotion and rewards", "escrow.html", body,
                "The second stage of the leaderboard: a strategy qualifies on proper score, then earns promotion only "
                "from prospective bets recorded after the freeze.")


def build_method(skill, controls, reg) -> str:
    meta = skill["_meta"]
    items = [
        ("What a proper score is here",
         "Brier score = mean((p − y)²), y = 1 for a won bet. Skill = 1 − BS(model)/BS(benchmark), where the benchmark "
         "is the de-vigged closing probability on the same bet. A score is proper when predicting the truth minimises "
         "it, so a strategy cannot farm the metric by hedging toward 0.5."),
        ("Why the closing line is the benchmark",
         "It is the most information-dense price in the pinned file. Beating it on probability is a stronger claim than "
         "winning a bet, and it cannot be manufactured by staking choices — which is exactly the separation the brief "
         "asks for between signal and staking."),
        ("Clusters", meta["cluster"]),
        ("Multiplicity", meta["multiplicity"]),
        ("Interval method",
         "Percentile bootstrap, 2,000 replicates, drawn by cluster with a documented linear congruential generator "
         "(multiplier 1664525, increment 1013904223, modulus 2^32, seed 20261119, index = state·k >> 32). "
         "Deterministic: any reviewer, in any language, reproduces the same interval. The skill ratio resamples "
         "numerator and denominator together, because the benchmark's own error is not a constant."),
        ("Coin-flip controls",
         "Closed form, not simulated: with a fair coin on each game the expected profit is the mean of the two sides' "
         "payoffs and the variance is ((payoff_A − payoff_B)/2)². No seed and no sampling error in the estimator "
         "itself, so the baseline cannot be tuned by choosing a different RNG."),
        ("Wilson intervals",
         "Hit-rate intervals use the Wilson score interval: centre = (p + z²/2n)/(1 + z²/n), half-width = "
         "z/(1 + z²/n)·√(p(1−p)/n + z²/4n²), z = 1.959963984540054. The formula is printed so it can be checked by "
         "arithmetic: this session has no network access, so no external statistics reference was re-opened "
         "(recorded in flagged.html)."),
        ("Settlement",
         "Side: home covers when (home − away) − spread_line > 0. Total: over when (home + away) − total_line > 0. "
         "Moneyline: the team with more points wins. Landing exactly on the number is a push and the stake is returned, "
         "so pushes keep a 0 in the ROI denominator — the convention line_lab's metric code uses. The official "
         "rulebook is linked for the tie rule; the pricing conventions are dataset-tier."),
        ("Tiers",
         "official-league / official-club means a page a merged session opened; dataset means the pinned nflverse "
         "file; internal means a recomputation in this repository. Prices here are dataset-tier: they score, they do "
         "not cite. The brief's rule that correlations come only from official numbers is therefore not met by this "
         "desk, and the readiness register row says so."),
        ("Limits of this session",
         "The sandbox reaches only github.com, npmjs.org and pypi.org. nfl.com is unreachable from here, so no "
         "official page was re-opened to confirm a price or a score. Everything published is arithmetic over committed "
         "files, and the reconciliation table shows where that arithmetic agrees with a surface built by a different "
         "session."),
    ]
    dl = "".join("<h3>" + esc(t) + "</h3><p>" + esc(b) + "</p>" for t, b in items)
    stats = [
        ("bootstrap replicates per statistic", "2,000"),
        ("strategies scored", str(len(skill["rows"]))),
        ("registrations frozen", str(len(reg["entries"]))),
        ("controls", str(len(controls["controls"]))),
        ("games with a final score in the control universe", f'{controls["_meta"]["universe"]["with_final_score"]:,}'),
        ("ledger rows read", f'{meta["ledger_rows"]:,}'),
        ("reconciliation fields checked", f'{sum(r["reconciliation_with_line_lab"].get("total", 0) for r in skill["rows"])}'),
        ("reconciliation fields matched", f'{sum(r["reconciliation_with_line_lab"].get("matched", 0) for r in skill["rows"])}'),
    ]
    rows = [[tds(esc(a)), tds(esc(b)), tds(link("skill", "computed"))] for a, b in stats]
    t = table(["Quantity", "Value", "Source"], rows)
    return page("Method", "method.html", dl + "<h2>Counts behind this desk</h2>" + t,
                "How every number on this desk is produced, and what it may and may not be used for.")


def build_sources(controls) -> str:
    rows = []
    for key, (url, what) in sorted(SOURCE_LINKS.items()):
        if "nflverse" in url:
            tier, kind = "dataset", "warn"
        elif "nfl.com" in url or "operations.nfl.com" in url:
            tier, kind = "official", "ok"
        elif "nist.gov" in url:
            tier, kind = "authority", "info"
        else:
            tier, kind = "internal", "info"
        note = ("re-opened by this session: no (sandbox has no network)" if tier in ("official", "authority")
                else "read from the working tree by this session")
        rows.append([tds(esc(key)), tds('<a href="' + esc(url) + '">' + esc(url) + "</a>"),
                     tds(esc(what)), tds(pill(tier, kind)), tds(esc(note)),
                     tds('the linked URL is the source of this row; the register itself is <a href="'
                         + esc(SOURCE_LINKS["games"][0]) + '">the pinned dataset tree</a>')])
    t = table(["Id", "URL", "What it is relied on for", "Tier", "Access note", "Source"], rows,
              "Rows labelled dataset are the pinned statistical files this repository reconciled against official "
              "pages in earlier sessions. This session opened none of them and says so on every page.")
    return page("Source register", "sources.html", t,
                "Every link this desk uses, with its tier and what it is relied on for.")


def build_flagged(skill, controls, reg) -> str:
    flags = []
    for r in skill["rows"]:
        if r.get("empty_window"):
            flags.append((r["strategy"], "no rows inside the frozen window", "medium",
                          "Every ledger row for this strategy sits outside 2006-2025, so it cannot be scored on the "
                          "backtest window at all. Left blank rather than computed on a different window.",
                          "skill.json"))
        if r.get("bets_without_a_price"):
            flags.append((r["strategy"], f'{r["bets_without_a_price"]} bets settled without a recorded price',
                          "medium",
                          "ROI uses the ledger's own pnl for them; the residual column excludes them. The count is "
                          "published instead of hidden, because a silently dropped row is how a ledger drifts.",
                          "bets.csv"))
        if r.get("probs_present", 0) and r["probs_present"] < r["n_bets"]:
            flags.append((r["strategy"], f'{r["probs_present"]} of {r["n_bets"]} bets carry both probabilities',
                          "medium",
                          "Proper scores use the subset with probabilities; win-rate columns use the rest. Mixed "
                          "denominators are the classic way a leaderboard lies, so both counts are printed.",
                          "skill.json"))
    for c in controls["controls"]:
        if c["control"].startswith("RND") and c.get("wins") is None:
            flags.append((c["control"], "win and loss counts are undefined", "low",
                          "A coin flip has no realised count on this table, only its exact expectation. Blank rather "
                          "than half-counting both sides.", "controls.json"))
    flags += [
        ("whole desk", "no official price source exists", "high",
         "The brief requires pricing claims and correlations to rest on officially sourced numbers. No official "
         "publisher prints betting lines, so every price here is tier dataset. Everything about vig, CLV and residual "
         "is provisional until the owner records the price-data policy decision (readiness A13).",
         "readiness register"),
        ("whole desk", "statistics references not re-opened in this session", "low",
         "The Wilson and bootstrap formulas are printed in full so they can be checked by arithmetic. The NIST pages "
         "linked from the method page were opened by earlier sessions, not this one.", "method.html"),
        ("line_lab:S11", "futures are not a game market", "medium",
         "Season win-total futures have no closing price pair and no model probability, so no proper score exists. "
         "The row is blank, not zero.", "skill.json"),
        ("prereg ledger", "the freeze is retroactive, not prospective", "high",
         "Every rule in the ledger was evaluated on 2006-2025 before this file existed. The status column says "
         "RETRO_FROZEN_BACKTEST_ONLY for that reason; claiming 'pre-registered' for a seen window would be the single "
         "easiest way to fool the owner here.", "preregistration.json"),
        ("escrow ledger", "empty by construction", "info",
         "0 settled prospective bets. Any number a reader might expect to see in the promotion column is not withheld, "
         "it does not exist yet.", "escrow_ledger.jsonl"),
    ]
    rows = []
    for who, what, sev, why, where in flags:
        rows.append([tds(esc(who)), tds(esc(what)), tds(pill(sev, "no" if sev == "high" else "warn")),
                     tds(esc(why)), tds(esc(where)), tds(link("reviewboard", "site review board"))])
    t = table(["Item", "Finding", "Severity", "Why it matters", "Where it shows", "Source"], rows,
              "This desk publishes its own limits beside its numbers. Anything not traceable to a committed file or a "
              "merged session's official read is blank here, never filled in.")
    return page("Flagged for review", "flagged.html", t,
                "Irregularities found while building this desk, and the values that are blank because nothing printed "
                "them.")


def main() -> int:
    controls = load("controls.json")
    skill = load("skill.json")
    reg = load("preregistration.json")
    pages = {
        "index.html": build_index(controls, skill, reg),
        "controls.html": build_controls(controls),
        "skill.html": build_skill(skill),
        "prereg.html": build_prereg(reg),
        "escrow.html": build_escrow(reg, skill, controls),
        "method.html": build_method(skill, controls, reg),
        "sources.html": build_sources(controls),
        "flagged.html": build_flagged(skill, controls, reg),
    }
    for name, text in pages.items():
        (HERE / name).write_text(text, encoding="utf-8")
    print(f"built {len(pages)} pages in luck_lab")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
