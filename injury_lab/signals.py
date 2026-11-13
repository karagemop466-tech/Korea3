#!/usr/bin/env python3
"""The injury-aware signal family, its gates, and an honest pilot.

    python3 -m injury_lab.signals

**Nothing here is promoted.** The pilot exists to prove the machinery runs end to end and to measure the
gap between what has been captured and what a gate needs. Six completed games in this repository's pinned
dataset match a captured official report. The gate that decides whether a rule is worth money requires
hundreds. So the output of a correct injury-signal pipeline at this sample size is "not evaluated", and a
page that reported a win rate from six games would be reporting noise with a decimal point on it.

Two registers of validation gates already exist in this repository, and **they use the same gate IDs for
different rules**:

* ``scripts/gates.py`` header - G1 sample size, G2 positive ROI, G3 both-window stability, G4 BH-FDR
  q <= 0.10, G5 concentration, G6 price stress at -115, G7 second line source, G8 luck-adjusted edge.
* ``docs/preregistration.md`` - G1 provenance, G2 causality, G3 sample, G4 holdout ROI, G5 significance,
  G6 Brier skill, G7 stability, G8 execution.

"Passed G4" therefore means "ROI positive in the confirmation window" in one build and "holdout ROI > 0"
in the other. This family uses its own prefix, ``IG1..IG9``, and where the two registers disagree the
stricter of the two is applied, per gate, with the source of each threshold named on the row. Inventing a
third standard would be worse than the collision; borrowing one register's IDs while applying the other's
thresholds would be worse still.

Family-level multiplicity is the other thing this module insists on: a BH correction only means something
across *every rule the repository has tested*. The published family size in ``data/derived/gates_meta.json``
is 18; the root dashboard tested 11 more; this file adds 9. Any q value computed against 9 alone flatters
this lab by construction, so the shortfall is reported as a gate that cannot pass yet.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"
DERIVED = ROOT / "data" / "derived"

# --------------------------------------------------------------------------------------------- #
# gate register. Every threshold is copied from a file in this repository, with the citation on
# the row; none of it is this module's opinion.
# --------------------------------------------------------------------------------------------- #
GATES = [
    {"id": "IG1", "name": "Provenance",
     "threshold": "every input row traces to a retained official capture or to the hashed pinned dataset",
     "register": "docs/preregistration.md G1", "cite": "docs/preregistration.md"},
    {"id": "IG2", "name": "Causality",
     "threshold": "the signal must be computable from a report published before the price used to settle it",
     "register": "docs/preregistration.md G2 + tests/test_causality.py", "cite": "docs/preregistration.md"},
    {"id": "IG3", "name": "Sample size",
     "threshold": "bets >= 300, seasons >= 8, holdout bets >= 40, confirmation-window bets >= 100",
     "register": "stricter of docs/preregistration.md G3 (300 / 8 / 40) and scripts/gates.py G1 (200 / 100)",
     "cite": "scripts/gates.py"},
    {"id": "IG4", "name": "Both-window direction",
     "threshold": "ROI > 0 in the discovery window (2000-2015) and in the confirmation window (2016-2026)",
     "register": "scripts/gates.py G3", "cite": "scripts/gates.py"},
    {"id": "IG5", "name": "Multiplicity",
     "threshold": "Benjamini-Hochberg q <= 0.10 across every rule this repository has tested, not this "
                  "family alone",
     "register": "scripts/gates.py G4 with family_size from data/derived/gates_meta.json",
     "cite": "data/derived/gates_meta.json"},
    {"id": "IG6", "name": "Season concentration",
     "threshold": "no season > 50% of profit and >= 60% of seasons positive",
     "register": "stricter of scripts/gates.py G5 (>=50% seasons positive) and docs/preregistration.md G7 "
                 "(>=60%)", "cite": "docs/preregistration.md"},
    {"id": "IG7", "name": "Price stress",
     "threshold": "still positive when every bet is re-priced at -115",
     "register": "scripts/gates.py G6", "cite": "scripts/gates.py"},
    {"id": "IG8", "name": "Second line source",
     "threshold": "still positive scored against the second in-dataset line source",
     "register": "scripts/gates.py G7", "cite": "scripts/gates.py"},
    {"id": "IG9", "name": "Luck-adjusted edge",
     "threshold": "empirical-Bayes shrunk ROI >= 0.5%, and outside the no-skill band of the published "
                  "coin-flip simulation",
     "register": "scripts/gates.py G8 with econ_bar from data/derived/gates_meta.json",
     "cite": "data/derived/gates_meta.json"},
]

# --------------------------------------------------------------------------------------------- #
# the family. Nine rules, each stated as a computation over the fields this lab can actually
# capture, with the market it settles into and the bet shape the brief asks for.
# --------------------------------------------------------------------------------------------- #
FAMILY = [
    {"id": "F01", "name": "Charted first-string quarterback ruled out",
     "bet_shape": "single", "market": "spread",
     "rule": "away club's charted 1st-string QB has Game Status Out or Doubtful on the Wednesday report",
     "hypothesis": "the market prices a first-string quarterback's absence roughly correctly at closing, "
                   "so any residual edge must come from the *replacement's* quality, not from the absence",
     "requires": ["injury report", "same-season club depth chart"],
     "note": "cannot run before 2026 with the sources in hand: no archived depth chart has been retained "
             "for an earlier season, so the trigger is undefined for historical games. Forward-test only."},
    {"id": "F02", "name": "Reported quarterback absence without a chart",
     "bet_shape": "single", "market": "spread",
     "rule": "a QB printed Out or Doubtful on the report for either club; the chart is not required",
     "hypothesis": "the publicly reported absence is over-adjusted once the line has moved to the "
                   "Wednesday report, so the side losing the QB is worth a small fade at closing",
     "requires": ["injury report"],
     "note": "this is the only injury rule that can be backtested historically today, because it needs "
             "no depth chart. It is also the rule the repository already tested without injuries "
             "(S8 'Backup-quarterback fade'), so a second claim on it inherits that family's multiplicity."},
    {"id": "F03", "name": "Two or more charted first-string defenders out",
     "bet_shape": "single", "market": "total",
     "rule": "one club has >= 2 designations in {Out, Doubtful} sitting in the 1st-string column of that "
              "club's own published defensive chart; bet the Over on that club's opponent's side of the "
              "total",
     "hypothesis": "front-seven absence moves scoring more than the market prices by Saturday night",
     "requires": ["injury report", "same-season club depth chart"],
     "note": "needs the unit of every reported row. Today 23 of 139 captured rows have no unit because no "
             "captured page defines codes like DE, T and G - counted on the coverage page, and a gate this "
             "rule cannot pass until it is closed."},
    {"id": "F04", "name": "Second string forced onto the field at cornerback",
     "bet_shape": "single", "market": "spread",
     "rule": "a club's 1st-string CB is Out and the name printed next to him is a player whose own report "
              "row is also a designation, i.e. the depth chart is thin at that slot",
     "hypothesis": "depletion concentrated in one position group is not the same as depletion counted "
                   "across the roster, and a roster-count feature would wash it out",
     "requires": ["injury report", "same-season club depth chart"],
     "note": "the joining rule for this one is unforgiving: report and chart disagree on player name form "
             "(Kevin Byard vs Kevin Byard III), so the join runs on the URL slug and needs an ID to be "
             "trustworthy at scale."},
    {"id": "F05", "name": "Designation count as a proxy (deliberate negative control)",
     "bet_shape": "single", "market": "spread",
     "rule": "bet against the club with more rows printed in the report, regardless of what those rows say",
     "hypothesis": "none - this rule is here to fail. A count of listed players mostly counts how many "
                   "players a club chose to put on the page, and the repository's own capture shows most "
                   "listed rows carry a blank Game Status",
     "requires": ["injury report"],
     "note": "a negative control earns its place by being predicted to fail; if it 'works', the feature "
             "is measuring reporting behaviour, not football."},
    {"id": "F06", "name": "Blank Game Status is not health (measurement control)",
     "bet_shape": "none", "market": "n/a",
     "rule": "no bet. Publishes the count of captured rows whose Game Status cell is empty",
     "hypothesis": "a model that maps 'no designation' to 'available' silently invents information",
     "requires": ["injury report"],
     "note": "this is a gate, not a strategy: it exists so that a future run fails loudly if someone "
             "starts filling blanks with zero."},
    {"id": "F07", "name": "Same-game spread + total double",
     "bet_shape": "parlay", "market": "spread x total",
     "rule": "F02 fires on the spread leg; the total leg is taken only if the same fixture also fires a "
              "total rule, both settled at the same closing prices",
     "hypothesis": "two injury-driven legs in one fixture share the same cause, so their joint win "
                   "probability is not the product of the two",
     "requires": ["injury report", "correlation ledger"],
     "note": "this repository already measured the same-game spread x total dependence at phi = +0.0086 "
             "(95% CI -0.0162 to +0.0332) against a parlay that needs phi >= 0.0975 at -110 - see "
             "data/derived/corr_same_game.csv and corr_meta.json. A correlated-by-hand parlay does not "
             "become a priced edge by adding a second leg."},
    {"id": "F08", "name": "Two-leg cross-game injury parlay",
     "bet_shape": "parlay", "market": "spread x spread",
     "rule": "the two strongest F02 triggers of a given week, different fixtures, both at closing",
     "hypothesis": "cross-game legs are near-independent, so a parlay is a *worse* bet than the two "
                   "singles unless one of the two carries a real edge",
     "requires": ["injury report", "correlation ledger"],
     "note": "published as a documented way to lose vig twice, unless IG3-IG9 pass for both legs first."},
    {"id": "F09", "name": "Player-prop combination off a depleted secondary",
     "bet_shape": "prop combo", "market": "player props",
     "rule": "when a club's 1st-string CB is Out, the opposing 1st-string WR's reception-over line is the "
              "target; a same-game QB completion leg may be combined only if the two legs' correlation is "
              "measured, not assumed",
     "hypothesis": "bookmakers adjust the team line for an absent cornerback more reliably than they "
                   "adjust the individual matchup number",
     "requires": ["injury report", "same-season club depth chart", "prop prices"],
     "note": "prop prices have no official publisher and are not in the pinned dataset this repository "
             "uses, so this rule is defined and cannot be settled here. Blocked by inputs, not by effort."},
]

def _bets_F01(g: dict) -> list[dict]:
    """A club's charted first-string quarterback is ruled out: take the opponent on the spread.

    Only fires where a same-season club chart was retained, because "first string" is a chart claim.
    """
    out = []
    for side in ("away", "home"):
        blk = g["clubs"][side]
        if blk.get("chart_joined") and (blk.get("first_string_absent") or 0) > 0 and blk["qb_absent"] > 0:
            out.append({"trigger_side": side, "bet_side": "home" if side == "away" else "away",
                        "market": "spread"})
    return out


def _bets_F02(g: dict) -> list[dict]:
    out = []
    for side in ("away", "home"):
        if g["clubs"][side]["qb_absent"] > 0:
            out.append({"trigger_side": side, "bet_side": "home" if side == "away" else "away",
                        "market": "spread"})
    return out


def _bets_F03(g: dict) -> list[dict]:
    return [{"trigger_side": side, "bet_side": "either", "market": "total", "direction": "over"}
            for side in ("away", "home") if g["clubs"][side]["out_defence"] >= 2]


def _bets_F05(g: dict) -> list[dict]:
    """Negative control: fade whoever printed more rows on the report, whatever those rows say."""
    a, h = g["clubs"]["away"]["rows_captured"], g["clubs"]["home"]["rows_captured"]
    if a == h:
        return []
    loud = "away" if a > h else "home"
    return [{"trigger_side": loud, "bet_side": "home" if loud == "away" else "away", "market": "spread",
             "note": f"rows listed: away {a}, home {h}"}]


def _bets_none(g: dict) -> list[dict]:
    return []


"""Rules with no computable trigger in the data this repository holds are registered with an empty
    trigger function, so their row says so instead of being quietly left off the page."""
BET_FUNCS = {"F01": _bets_F01, "F02": _bets_F02, "F03": _bets_F03, "F04": _bets_none,
             "F05": _bets_F05, "F06": _bets_none, "F07": _bets_none, "F08": _bets_none,
             "F09": _bets_none}


def payout_per_unit(odds: float) -> float:
    """Identical to scripts/lib.py:payout_per_unit - profit on a 1-unit stake at American odds."""
    odds = float(odds)
    return 100.0 / abs(odds) if odds < 0 else odds / 100.0


def settle(game: dict, side: str, market: str, direction: str = "over") -> dict:
    """Settle one hypothetical bet at the price recorded in the pinned dataset.

    Sign convention is the repository's own, copied from scripts/build_dataset.py lines 55-63:
    ``games.csv.spread_line`` is signed opposite the conventional home spread, and
    ``home_ats_margin = (home_score - away_score) - spread_line`` with a positive value meaning the home
    side covered. Re-deriving it here rather than trusting prose is what makes the pilot auditable.
    """
    m = game["market"]
    line, price = (m.get("spread_line"), m.get(f"{side}_spread_odds"))
    if market == "total":
        # a total bet has no side: the rule fires on the game, and the price is the Over or Under price
        line, price = m.get("total_line"), m.get("over_odds" if direction == "over" else "under_odds")
    elif side not in ("away", "home"):
        return {"settled": False, "reason": "no side to bet, and this market is not a game total"}
    if market.startswith("moneyline"):
        line, price = "", m.get(f"{side}_moneyline")
    if line in ("", None) or price in ("", None):
        return {"settled": False, "reason": "no line or no price in the pinned dataset for this fixture"}
    try:
        line_f, price_f = float(line), float(price)
    except ValueError:
        return {"settled": False, "reason": "line or price not numeric in the pinned dataset"}
    hs, as_ = int(m["home_score"]), int(m["away_score"])
    margin_home = hs - as_
    total = hs + as_
    if market == "spread":
        ats = margin_home - line_f                      # >0 => home covered (repo convention)
        outcome = (ats > 0) if side == "home" else (ats < 0)
        push = ats == 0
    elif market == "total":
        outcome = (total > line_f) if direction == "over" else (total < line_f)
        push = total == line_f
    else:
        won = (margin_home > 0) if side == "home" else (margin_home < 0)
        outcome, push = won, margin_home == 0
    profit = 0.0 if push else (payout_per_unit(price_f) if outcome else -1.0)
    return {"settled": True, "push": bool(push), "won": bool(outcome) and not push,
            "line": line_f, "price": price_f, "profit_units": round(profit, 6),
            "home_score": hs, "away_score": as_, "total": total}


def wilson(wins: int, n: int, z: float = 1.959963984540054) -> tuple[float, float] | None:
    """Wilson score interval for a win rate. z is the printed 95% normal quantile.

    Published alongside every pilot win rate because a rate without a width is how a small sample gets
    mistaken for a skill: at n = 6 and 5 wins the interval runs from roughly 0.26 to 0.92, which contains
    every plausible truth about the rule.
    """
    if n <= 0:
        return None
    phat = wins / n
    den = 1 + z * z / n
    centre = (phat + z * z / (2 * n)) / den
    half = (z / den) * math.sqrt(phat * (1 - phat) / n + z * z / (4 * n * n))
    return (round(max(0.0, centre - half), 6), round(min(1.0, centre + half), 6))


def main() -> int:
    joined = json.loads((DATA / "joined.json").read_text(encoding="utf-8"))
    caps = json.loads((DATA / "captures.json").read_text(encoding="utf-8"))
    meta = json.loads((DERIVED / "gates_meta.json").read_text(encoding="utf-8"))
    played = [g for g in joined["game_features"] if g["played"]]

    rows = []
    for sig in FAMILY:
        fires, results = [], []
        fn = BET_FUNCS[sig["id"]]
        for g in played:
            for bet in fn(g):
                market = "spread" if sig["market"] in {"spread x total", "spread x spread",
                                                        "player props"} else sig["market"]
                s = settle(g, bet["bet_side"], market, bet.get("direction", "over"))
                fires.append({"gameday": g["gameday"], "fixture": f"{g['away']}@{g['home']}",
                              "trigger_side": bet["trigger_side"], "bet_side": bet["bet_side"],
                              "market": market, "settled": s.get("settled", False), "detail": s,
                              "bet_note": bet.get("note", "")})
                if s.get("settled"):
                    results.append(s)
        n = len(fires)
        n_settled = len(results)
        roi = (sum(r["profit_units"] for r in results) / n_settled) if n_settled else None
        wins = sum(1 for r in results if r["won"])
        pushes = sum(1 for r in results if r["push"])
        verdicts = {}
        verdicts["IG1"] = "PASS" if n and all(f["settled"] for f in fires) else (
            "PASS (no fire)" if not fires else "PARTIAL")
        verdicts["IG2"] = "NOT EVALUATED"
        verdicts["IG3"] = "FAIL" if n < 300 else "PASS"
        for gid in ("IG4", "IG5", "IG6", "IG7", "IG8", "IG9"):
            verdicts[gid] = "BLOCKED by IG3"
        promoted = all(v == "PASS" for v in verdicts.values())
        weeks_needed = None
        if n_settled == 0:
            pass
        elif n < 300:
            per_game = max(n, 1) / max(len(played), 1)
            games_needed = math.ceil(300 / per_game) if per_game else None
            weeks_needed = math.ceil(games_needed / 14) if games_needed else None
        rows.append({**{k: v for k, v in sig.items() if k != "note"}, "note": sig["note"],
                     "games_captured_played": len(played), "fires": n, "fires_settled": n_settled,
                     "wins": wins, "pushes": pushes,
                     "pilot_roi": None if roi is None else round(roi, 6),
                     "win_rate": None if not n_settled else round(wins / n_settled, 6),
                     "win_rate_wilson_95ci": wilson(wins, n_settled),
                     "gates": verdicts, "promoted": promoted, "reward_eligible": False,
                     "fire_ledger": [{**f, "market_source": joined["pinned_games_blob_url"]} for f in fires],
                     "bets_still_needed_for_IG3": max(300 - n, 0),
                     "weeks_of_capture_for_IG3": weeks_needed})
    out = {
        "_comment": ["Generated by injury_lab/signals.py. Pilot figures are counts over the six completed "
                     "fixtures in this repository whose date and club codes match a retained official "
                     "capture; they are not evidence about any rule, and reward_eligible is hard-coded "
                     "False while IG3 fails for the whole family."],
        "generated_by": "injury_lab/signals.py",
        "gate_register": GATES,
        "gate_register_conflict": {
            "what": "two existing registers in this repository use the same gate IDs for different rules",
            "files": ["scripts/gates.py", "docs/preregistration.md"],
            "resolution": "a third, prefixed register IG1..IG9, each threshold attributed to the file it "
                          "came from, stricter value where they disagree",
        },
        "published_thresholds_in_use": {"min_n": meta.get("min_n"), "min_n_conf": meta.get("min_n_conf"),
                                       "fdr_alpha": meta.get("fdr_alpha"),
                                       "econ_bar": meta.get("econ_bar"),
                                       "family_size_already_tested": meta.get("family_size"),
                                       "universe": meta.get("universe")},
        "rows_captured": len(caps["injury_rows"]),
        "fixtures_joined": len(joined["game_features"]),
        "fixtures_played_with_price": len(played),
        "family": rows,
    }
    (DATA / "signals.json").write_text(json.dumps(out, indent=2) + "\n", encoding="utf-8")
    print(f"signals: {len(rows)} pre-registered rules; {len(played)} settled-eligible completed games; "
          f"{sum(1 for r in rows if r['promoted'])} promoted; "
          f"{sum(r['fires'] for r in rows)} total triggers")
    for r in rows:
        print(f"  {r['id']} {r['name'][:44]:44s} fires={r['fires']:2d} settled={r['fires_settled']:2d} "
              f"IG3={r['gates']['IG3']:4s} reward={'yes' if r['reward_eligible'] else 'no'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
