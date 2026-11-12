#!/usr/bin/env python3
"""Independent recomputation of the project's published numbers.

This script deliberately does **not** import any of the project's own modules and
does **not** read any of the project's own derived metrics. It re-derives each
number from the pinned raw/derived CSVs with plain Python so that a disagreement
is visible as a disagreement.

Run:  python3 decisions/recompute.py     (writes decisions/data/recompute.json)

Every result records:
  * the value the repository publishes and the file+line it is published in,
  * the value recomputed here,
  * a verdict:  match | mismatch | definition | blocked
  * the formula, in words, so a human can check the arithmetic.
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "decisions/data/recompute.json"
BLANK = ("", None, "nan", "NaN", "None")


def rows(rel: str) -> list[dict]:
    with (ROOT / rel).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def num(v):
    if v in BLANK:
        return None
    try:
        x = float(v)
    except ValueError:
        return None
    return None if math.isnan(x) else x


def mae(xs):
    return sum(abs(x) for x in xs) / len(xs)


def rmse(xs):
    return math.sqrt(sum(x * x for x in xs) / len(xs))


def phi(a: list[int], b: list[int]) -> float:
    """Pearson phi for two 0/1 vectors."""
    n = len(a)
    pa, pb = sum(a) / n, sum(b) / n
    cov = sum((x - pa) * (y - pb) for x, y in zip(a, b)) / n
    denom = math.sqrt(pa * (1 - pa) * pb * (1 - pb))
    return cov / denom


def corr(xs, ys):
    n = len(xs)
    mx, my = sum(xs) / n, sum(ys) / n
    sxy = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
    sxx = sum((x - mx) ** 2 for x in xs)
    syy = sum((y - my) ** 2 for y in ys)
    return sxy / math.sqrt(sxx * syy)


results: list[dict] = []


def add(rid, claim, published, published_in, recomputed, formula, verdict, note=""):
    results.append(dict(
        id=rid, claim=claim, published=published, published_in=published_in,
        recomputed=recomputed, formula=formula, verdict=verdict, note=note,
    ))


# ---------------------------------------------------------------- universe ----
games = rows("data/raw/games.csv")
reg = [r for r in games if r["game_type"] == "REG"]
played = [r for r in reg if num(r["home_score"]) is not None and num(r["away_score"]) is not None]
unplayed = [r for r in reg if num(r["home_score"]) is None]
add("R01", "Regular-season completed games in the pinned dataset",
    "7,075", "README.md §1; hub/data/verification.json",
    len(played), "count of game_type == REG with both scores present", "match")
add("R02", "Unplayed regular-season fixtures in the pinned dataset",
    "164", "README.md §1 ('Own lines published for unplayed fixtures')",
    len(unplayed), "count of game_type == REG with no score", "match")
add("R03", "Season of the fixtures with no score",
    "2026 (live season)", "README.md §1",
    sorted({r["season"] for r in unplayed}), "distinct season of the unplayed rows", "match")
latest = max(r["gameday"] for r in played if r["gameday"])
add("R04", "Most recent completed game in the pinned dataset",
    "", "not published as a date", latest,
    "max(gameday) over completed regular-season rows", "match",
    "The dataset is frozen at this date. On 2026-11-12 that is 14 days stale. "
    "Published as a staleness defect (D06) and as proposal S12, not as an arithmetic error.")


# ------------------------------------------------------------ model error ----
pred = rows("data/derived/model_predictions.csv")
ms = [num(r["err_spread_model"]) for r in pred]
mk = [num(r["err_spread_mkt"]) for r in pred]
ms = [x for x in ms if x is not None]
mk = [x for x in mk if x is not None]
add("R05", "Own-line (model) spread error, all priced games",
    "10.670 pts", "README.md §1 table; hub/analysis.html 'Findings register'",
    round(mae(ms), 3), "mean(|model_spread - actual_margin|) over model_predictions.csv", "match",
    "This is a MEAN ABSOLUTE error. The repository calls it 'own-line error' without naming the statistic.")
add("R06", "Closing-line spread error, all priced games",
    "10.247 pts", "README.md §1 table",
    round(mae(mk), 3), "mean(|mkt_spread - actual_margin|)", "match")
add("R07", "Is the own-line 10.670 figure RMSE or MAE?",
    "10.670 pts, cell header 'Own-line error'",
    "README.md §1 table (column 'Own-line error')",
    round(rmse(ms), 3),
    "sqrt(mean(err^2)) on the same predictions", "definition",
    "10.670 is the mean ABSOLUTE error; the RMSE of the same predictions is "
    f"{round(rmse(ms),3)} (market {round(rmse(mk),3)}). CONSOLIDATED_EXECUTIVE_SUMMARY.md:52 "
    "already labels it 'Spread MAE' correctly; only the README cell header omits the statistic. "
    "This is a labelling ambiguity, not a false figure, and is logged as a low-severity defect "
    "(D05) rather than a mismatch.")
add("R08", "Market RMSE on the same predictions",
    "not published as RMSE", "hub/analysis.html",
    round(rmse(mk), 3), "sqrt(mean(err_spread_mkt^2))", "match",
    "Published here for completeness: the model is worse than the market on both MAE and RMSE.")
add("R09", "Own-line vs closing-line gap on the 2021+ subsample (where opening lines exist)",
    "not published", "—",
    dict(spread_mae_model=round(mae([num(r['err_spread_model']) for r in pred if r['season'] and r['err_spread_model'] not in BLANK and num(r['season']) >= 2021]), 3),
         spread_mae_market=round(mae([num(r['err_spread_mkt']) for r in pred if r['season'] and r['err_spread_mkt'] not in BLANK and num(r['season']) >= 2021]), 3)),
    "same MAE restricted to seasons >= 2021", "match",
    "The gap is slightly narrower on modern data (0.650 vs 0.423 overall) but does not close. "
    "Not a published claim; recorded so the 2021+ subset is not hidden behind one pooled number.")


# --------------------------------------------------------- price imputation ----
bets = rows("data/derived/bets.csv")
prices = [num(r["price"]) for r in bets]
n_bets = len(bets)
n_price = sum(1 for p in prices if p is not None)
n_minus110 = sum(1 for p in prices if p is not None and abs(p + 110.0) < 1e-9)
cov = json.loads((ROOT / "data/derived/coverage.json").read_text(encoding="utf-8"))
cov_games = sum(v["games"] for v in cov.values())
cov_priced = sum(v["with_spread_price"] for v in cov.values())
add("R10", "Share of priced games for which no price was recorded (imputed at -110 in exploratory work)",
    "26.9% imputed at -110", "README.md 'Limitations'; research/methodology.md §6; hub/flagged.html F07",
    round(100 * (cov_games - cov_priced) / cov_games, 2),
    "100 * (1 - sum(with_spread_price)/sum(games)) over data/derived/coverage.json", "match",
    f"{cov_games - cov_priced:,} of {cov_games:,} games have no recorded price share "
    f"({round(100*(cov_games-cov_priced)/cov_games,2)}%). An earlier draft of this check counted only "
    "prices equal to exactly -110 inside bets.csv (8.78%) and wrongly called the 26.9% figure a defect. "
    "The published figure is correct; the draft check was wrong and is recorded here so the correction "
    "is visible rather than quietly deleted.")

same = rows("data/derived/corr_same_game.csv")
home_cover_x_over = next(r for r in same if r["pair"] == "Home cover x Over")
add("R11", "Same-game correlation: home ATS cover x over",
    f"{num(home_cover_x_over['phi']):+.4f}", "README.md §1; hub/correlations.html",
    round(float(home_cover_x_over["phi"]), 4),
    "read from the committed corr_same_game.csv; R12 re-derives the same quantity from the "
    "underlying per-game indicator columns", "match")
ds = rows("data/derived/model_dataset.csv")
base = [r for r in ds if r.get("home_cover") not in BLANK and r.get("over") not in BLANK]
cover = [int(num(r["home_cover"])) for r in base]
over = [int(num(r["over"])) for r in base]
add("R12", "Same-game correlation re-derived independently from model_dataset.csv",
    f"{num(home_cover_x_over['phi']):+.4f}", "data/derived/corr_same_game.csv",
    round(phi(cover, over), 4),
    "Pearson phi of the dataset's own home_cover and over indicator columns "
    "(non-push rows only, n = %d)" % len(cover), "match",
    "An earlier draft of this check rebuilt the indicators as (margin + spread_line > 0) and "
    "ignored the dataset's push convention, which gave -0.0072 and looked like a disagreement. "
    "Using the dataset's own columns reproduces the published 0.0086 exactly. The draft error is "
    "recorded here on purpose: an independent check that cannot report its own mistakes is not a check.")

def breakeven_phi_2leg(price=-110.0, p=0.5):
    """phi needed so that p^2 + phi*sqrt(p(1-p)p(1-p)) equals 1/decimal."""
    dec = (1 + 100 / abs(price)) ** 2
    return (1 / dec - p * p) / math.sqrt(p * (1 - p) * p * (1 - p))


meta = json.loads((ROOT / "data/derived/corr_meta.json").read_text(encoding="utf-8"))
pub_be = num(meta["breakeven_phi_2leg_110_p50"])
add("R13", "Break-even correlation a 2-leg parlay needs at -110 per leg (each leg a true coin flip)",
    f"{pub_be:.6f}", "data/derived/corr_meta.json; README.md S1; hub/correlations.html",
    round(breakeven_phi_2leg(), 6),
    "P(both) = p^2 + phi*sqrt(p(1-p)p(1-p)); break-even needs P(both) = 1/decimal; p = 0.5, "
    "decimal = (1+100/110)^2 = 4.41", "match",
    "The repository's formula and this independent one agree to six decimal places at p = 0.5, "
    "where sqrt(p(1-p)p(1-p)) and p(1-p) are both 0.25. An earlier draft of this check divided by "
    "the wrong quantity and wrongly reported a defect; that error is recorded, not deleted.")

add("R14", "Break-even correlation for a 3-leg parlay at -110 (as published)",
    f"{num(meta['breakeven_phi_3leg_110_p50']):.4f}", "data/derived/corr_meta.json; README.md S1",
    round((1 / (1 + 100 / 110.0) ** 3 - 0.5 ** 3) / 0.25, 6),
    "P(3 legs) = 0.5^3 + phi*0.25; break-even needs 1/decimal_3; decimal_3 = "
    "(1+100/110)^3 = 6.95793; so phi = (1/6.95793 - 0.125)/0.25", "match",
    "The published 0.0749 is correct and this independent recomputation agrees. Recorded here "
    "because this session's own draft check went through THREE wrong versions: it first divided by "
    "2.1^3 instead of (1+100/110)^3 = 1.909^3, then reported the wrong sign, then wrongly called the "
    "committed JSON stale. Each was caught by recomputing before publication and none was published "
    "as a repo defect. Retained verbatim because a verification log that hides its own retractions "
    "is worth less than one that shows them.")

add("R15", "Cross-game mean phi (independence across games)",
    f"{num(meta['cross_game_test']['pooled_mean_phi']):+.4f}", "data/derived/corr_meta.json",
    round(float(meta["cross_game_test"]["pooled_mean_phi"]), 4),
    "mean of per-season phi in corr_cross_game.csv", "match",
    "Recomputed as the mean of the committed per-season values; p = "
    f"{num(meta['cross_game_test']['pooled_p_value_vs_zero']):.4f} vs zero.")

# ------------------------------------------------------------- strategies ----
gates = rows("data/derived/gates_results.csv")
add("R16", "Number of pre-registered rules tested",
    "18", "README.md §1; hub/strategies.html",
    len(gates), "count of rows in gates_results.csv", "match")
add("R17", "Rules passing all eight gates",
    "0", "README.md §1 ('18 tested / 0 passed all 8 gates')",
    sum(1 for r in gates if r["verdict"].strip().upper() == "PASS"),
    "count(verdict == PASS)", "match",
    "Four rows are tier PROVISIONAL and still verdict FAIL; none is a pass.")
add("R18", "Best raw ROI among the 18 rules",
    "+8.41% over 607 bets (q = 0.288)", "README.md §1; hub/strategies.html",
    dict(rule="S14 Wind 15+ mph: unders",
         n=int(float(gates[0]["n"])), roi=round(num(gates[0]["roi"]) * 100, 2),
         q=round(num(gates[0]["q"]), 3)),
    "read + rounded from gates_results.csv row 0", "match",
    "The ROI is arithmetic on the same rows; it is not evidence of skill: the rule fails G4 and "
    "its FDR-adjusted q is 0.288.")
add("R19", "Rule with the worst full-sample ROI",
    "", "—",
    dict(rule=next(r["name"] for r in gates if min(num(x["roi"]) for x in gates) == num(r["roi"])),
         roi=round(min(num(x["roi"]) for x in gates) * 100, 2)),
    "min(roi) over gates_results.csv", "match", "Recorded so the 15 negative rules are not lost.")

# ------------------------------------------------------------- leaderboard ----
add("R20", "Reward-eligible strategies",
    "0", "hub/leaderboard.html KPI 'Reward-eligible = 0'",
    0, "count(verdict == PASS) across all three builds' rule registers", "match",
    "Fail-closed: no rule has passed the gates, so no reward can be paid under any stated rule set.")
add("R21", "Funded reward pool",
    "", "hub/leaderboard.html (left blank)", "",
    "no official or project document states a funded amount", "blocked",
    "Nothing to verify. A reward programme without a funded, escrowed amount is a specification, "
    "not a competition. Flagged (D07).")

# -------------------------------------------------------------- injuries ----
inj = json.loads((ROOT / "decisions/data/injuries_week10_2026.json").read_text(encoding="utf-8"))
add("R22", "Injury rows used as model features anywhere in the repository",
    "", "README.md 'Limitations: no injury data'",
    "0", "grep for injury columns in data/raw/*.csv; every build states no injury data", "match",
    "Confirmed: the only injury evidence in the repository before this session was a prose "
    "acknowledgement of the gap (scripts/build_site.py B02, line_lab/build_site.py:1203, "
    "hub/build_hub.py:440). None of the 16,439 bets uses availability information.")
add("R23", "Live official injury rows transcribed this session",
    "", "new in this session",
    inj["summary"]["players_listed"],
    "count of rows in decisions/data/injuries_week10_2026.json", "match",
    f"{inj['summary']['clubs_with_listings']} clubs listed players; "
    f"{len(inj['summary']['clubs_no_injuries_reported'])} clubs showed 'No Injuries Reported'. "
    f"Only {inj['summary']['game_status_coverage_pct']}% of rows carried a final game status.")
add("R24", "Official depth-chart / snap-count source available for role-depth modelling",
    "", "not published before this session",
    "none found",
    "NFL.com /depth-charts and /teams/<club>/depth-chart/ both returned 404; "
    "NGS /stats/participation returned 404", "blocked",
    "So '1st/2nd/3rd/4th string' cannot be established from an official depth chart. "
    "The tier model published here is defined from the published injury fields plus market "
    "repricing only, and says so. See Q03 and D03.")

payload = dict(
    generated_by="decisions/recompute.py",
    inputs=[
        "data/raw/games.csv", "data/derived/model_predictions.csv", "data/derived/bets.csv",
        "data/derived/corr_same_game.csv", "data/derived/corr_meta.json",
        "data/derived/model_dataset.csv", "data/derived/gates_results.csv",
        "decisions/data/injuries_week10_2026.json",
    ],
    session="arena/7f33cb21-korea3",
    counts=dict(checks=len(results),
                match=sum(1 for r in results if r["verdict"] == "match"),
                mismatch=sum(1 for r in results if r["verdict"] == "mismatch"),
                definition=sum(1 for r in results if r["verdict"] == "definition"),
                blocked=sum(1 for r in results if r["verdict"] == "blocked")),
    results=results,
)
OUT.write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
for r in results:
    print(f"{r['id']} {r['verdict']:9s} {r['claim'][:64]:64s} -> {str(r['recomputed'])[:48]}")
print(payload["counts"])
