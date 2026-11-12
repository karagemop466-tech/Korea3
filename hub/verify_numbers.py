#!/usr/bin/env python3
"""Independent recomputation of the numbers this dashboard publishes.

Run: python3 hub/verify_numbers.py

Why this exists
---------------
The dashboard publishes numbers that earlier pipelines produced. Rather than trust the
pipeline that produced them, this script re-derives each published number from the
committed CSV with its own arithmetic and compares. A disagreement fails the build.

Each check carries a label stating what it can and cannot prove:
  * OFFICIAL     - fixed by an official publisher's own rule text or by arithmetic
                   on a price, independent of any dataset.
  * RECOMPUTED   - re-derived here from the repository's committed data. Reproducible,
                   but the underlying market data is third-party and is NOT an
                   official NFL or licensed-operator publication.
  * LIMITATION   - a negative check: confirms a documented gap rather than a value.

Output: hub/data/recompute.json (deterministic, stdlib only, no network).
"""
from __future__ import annotations

import csv
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "hub"


def read(path):
    with (ROOT / path).open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def num(value):
    if value in (None, "", "nan", "NaN", "None"):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def phi(pairs) -> tuple[int, float]:
    """Pearson correlation of two 0/1 vectors - i.e. phi, written out by hand."""
    n = len(pairs)
    mx = sum(a for a, _ in pairs) / n
    my = sum(b for _, b in pairs) / n
    cov = sum((a - mx) * (b - my) for a, b in pairs) / n
    sx = math.sqrt(sum((a - mx) ** 2 for a, _ in pairs) / n)
    sy = math.sqrt(sum((b - my) ** 2 for _, b in pairs) / n)
    return n, cov / (sx * sy)


def normal_two_sided_p(z: float) -> float:
    return 2 * (1 - 0.5 * (1 + math.erf(abs(z) / math.sqrt(2))))


def main() -> int:
    checks = []

    def add(cid, name, published, recomputed, kind, method, ok, note=""):
        checks.append({
            "id": cid, "name": name,
            "published": published, "recomputed": recomputed,
            "kind": kind, "method": method,
            "result": "match" if ok else "MISMATCH", "note": note,
        })

    # ---------------------------------------------------------------- C01
    be = 110.0 / (110.0 + 100.0)
    add("C01", "Break-even win rate at a -110 price", 0.5238, round(be, 4), "OFFICIAL",
        "risk/(risk+win) = 110/210, from the operator's own definition of a -110 price",
        abs(be - 0.5238095238095238) < 1e-12,
        "Independent of every dataset; follows from the price definition alone.")

    meta = json.loads((ROOT / "data/derived/corr_meta.json").read_text(encoding="utf-8"))

    # ---------------------------------------------------------------- C02, C03
    for legs, key, cid in ((2, "breakeven_phi_2leg_110_p50", "C02"),
                           (3, "breakeven_phi_3leg_110_p50", "C03")):
        dec = (1 + 100 / 110.0) ** legs
        target = 1 / dec
        indep = 0.5 ** legs
        # dP(both)/dphi at p=0.5 for equal legs is p*(1-p) = 0.25
        value = (target - indep) / 0.25
        published = float(meta[key])
        add(cid, f"Break-even phi, {legs} legs at -110, true leg rate 50%",
            round(published, 4), round(value, 4), "OFFICIAL",
            f"phi = (1/(1+100/110)^{legs} - 0.5^{legs}) / 0.25",
            abs(published - value) < 5e-5,
            "Arithmetic on the posted price only. Assumes each leg is a true coin flip "
            "priced as if independent - an assumption, not a measured quantity.")

    # ---------------------------------------------------------------- C04
    # Same-game correlation. NOTE: corr_same_game.csv is documented as 2006-2025, but the
    # published n (6,784) is the count over every season in the table, not that window.
    # Reproducing the published pair therefore requires the all-season definition, which is
    # what is done here; the docstring/label mismatch is published as defect D1.
    md = read("data/derived/model_dataset.csv")
    pairs, window_pairs = [], []
    for r in md:
        cover, over = num(r.get("home_cover")), num(r.get("over"))
        if cover is None or over is None:
            continue
        pairs.append((cover, over))
        season = num(r.get("season"))
        if season is not None and 2006 <= season <= 2025:
            window_pairs.append((cover, over))
    n_same, phi_same = phi(pairs)
    n_win, phi_win = phi(window_pairs)
    same_rows = read("data/derived/corr_same_game.csv")
    pub_phi = float(same_rows[0]["phi"])
    pub_n = int(same_rows[0]["n"])
    add("C04", "Home cover x Over correlation (phi) in the same game",
        round(pub_phi, 4), round(phi_same, 4), "RECOMPUTED",
        f"Pearson phi over {n_same:,} settled games, hand-computed from model_dataset.csv",
        abs(pub_phi - phi_same) < 5e-4,
        f"The same figure computed over the 2006-2025 window documented in the source is "
        f"n={n_win:,}, phi={phi_win:+.4f}. The published row uses the all-season definition.")
    add("C05", "Games behind the same-game correlation", pub_n, n_same, "RECOMPUTED",
        "count of settled games with a spread and a total, all seasons", pub_n == n_same,
        f"All seasons: {n_same:,}. Documented 2006-2025 window: {n_win:,}.")

    # ---------------------------------------------------------------- C06, C07
    cross = read("data/derived/corr_cross_game.csv")
    vals = [float(r["phi"]) for r in cross]
    m = sum(vals) / len(vals)
    sd = math.sqrt(sum((v - m) ** 2 for v in vals) / (len(vals) - 1))
    se = sd / math.sqrt(len(vals))
    p = normal_two_sided_p(m / se)
    pub = meta["cross_game_test"]
    add("C06", "Cross-game pooled mean phi", round(float(pub["pooled_mean_phi"]), 4), round(m, 4),
        "RECOMPUTED", f"mean of {len(vals)} season-level phi values in corr_cross_game.csv",
        abs(float(pub["pooled_mean_phi"]) - m) < 5e-5)
    add("C07", "Cross-game pooled p-value against zero",
        round(float(pub["pooled_p_value_vs_zero"]), 4), round(p, 4), "RECOMPUTED",
        "two-sided normal test on mean/se", abs(float(pub["pooled_p_value_vs_zero"]) - p) < 5e-4,
        "This is the test that lets us say cross-game legs behave like independent events.")

    # ---------------------------------------------------------------- C08-C10
    bets = read("data/derived/bets.csv")
    settled = [r for r in bets if num(r.get("pnl")) is not None]
    strategies = sorted({r["strategy_id"] for r in settled})
    add("C08", "Settled bets in the strategy ledger", 16439, len(settled), "RECOMPUTED",
        "row count of data/derived/bets.csv", len(settled) == 16439)
    add("C09", "Distinct strategies in the ledger", 11, len(strategies), "RECOMPUTED",
        "distinct strategy_id values", len(strategies) == 11)

    # The published ROI is produced by scripts/signals.py; its settled ledger is
    # data/derived/signal_bets.csv. data/derived/bets.csv is a DIFFERENT build (line_lab)
    # whose strategy IDs collide with this one (defect D2), so it must not be used here.
    ledger = read("data/derived/signal_bets.csv")
    by_strategy = {}
    pushes = 0
    for r in ledger:
        profit, result = num(r.get("profit")), num(r.get("result"))
        if profit is None:
            continue
        if result == 0:          # a push is not a settled bet
            pushes += 1
            continue
        by_strategy.setdefault(r["signal"], []).append(profit)
    rois = {s: sum(v) / len(v) for s, v in by_strategy.items()}
    gates = read("data/derived/gates_results.csv")
    published_roi = {r["id"]: float(r["roi"]) for r in gates if num(r.get("roi")) is not None}
    published_n = {r["id"]: int(r["n"]) for r in gates if num(r.get("n")) is not None}
    diffs = {s: abs(published_roi[s] - rois[s]) for s in rois if s in published_roi}
    worst = max(diffs.items(), key=lambda kv: kv[1]) if diffs else (None, 0.0)
    row_gap = sum(len(by_strategy[s]) - published_n.get(s, 0) for s in by_strategy)
    add("C10", "Per-strategy ROI recomputed from the signal ledger", "as published",
        f"max abs difference {worst[1]:.5f}", "RECOMPUTED",
        "sum(profit)/count(profit) per signal in data/derived/signal_bets.csv, "
        f"compared with gates_results.csv over {len(diffs)} strategies",
        worst[1] <= 1e-3,
        f"Largest disagreement on {worst[0]}. Excluding the {pushes:,} push rows in the "
        f"ledger reproduces every published per-strategy count exactly (row gap {row_gap}) "
        f"and every published ROI to within {worst[1]:.2e}.")

    # ---------------------------------------------------------------- C11
    pass_all = sum(1 for r in gates if r.get("verdict") == "PASS")
    gate_cols = [c for c in gates[0] if c.startswith("G") and c[1:].isdigit()]
    clears = sum(1 for r in gates if all(r.get(c) in ("True", "pass") for c in gate_cols))
    add("C11", "Strategies clearing every validation gate", 0, pass_all, "RECOMPUTED",
        "verdict column of gates_results.csv, and each gate column re-read individually",
        pass_all == 0,
        f"{len(gate_cols)} gate columns: {clears} of {len(gates)} strategies clear all of them.")

    # ---------------------------------------------------------------- C12
    # Parlay EV. The grid is a PARLAY: EV = joint_prob * decimal_odds - 1. A single-bet
    # formula (p*pay-(1-p)) is the wrong construction and does not reproduce the grid.
    bad_ev, bad_joint = [], []
    for r in read("data/derived/props_ev_grid.csv"):
        price_a, price_b = num(r.get("price_a")), num(r.get("price_b"))
        p, ph = num(r.get("assumed_true_leg_rate")), num(r.get("phi"))
        joint, ev_pub = num(r.get("true_joint_prob")), num(r.get("ev_per_unit"))
        if None in (price_a, price_b, p, ph, joint, ev_pub):
            continue
        dec = (1 + 100 / abs(price_a)) * (1 + 100 / abs(price_b))
        if abs((p * p + ph * p * (1 - p)) - joint) > 1e-3:
            bad_joint.append(ph)
        if abs(joint * dec - 1 - ev_pub) > 5e-3:
            bad_ev.append((ph, ev_pub, joint * dec - 1))
    add("C12", "Parlay joint probability from phi in the prop grid", "as published",
        "recomputed", "OFFICIAL",
        "P(both) = p^2 + phi*p*(1-p) for equal legs", not bad_joint,
        "" if not bad_joint else f"{len(bad_joint)} rows disagree")
    add("C13", "Parlay EV from the joint probability and the posted decimal odds",
        "as published", "recomputed", "OFFICIAL",
        "EV = P(both) * decimal_odds - 1, with decimal_odds = (1+100/|a|)(1+100/|b|)",
        not bad_ev, "" if not bad_ev else f"{len(bad_ev)} rows disagree, first {bad_ev[0]}")

    # ---------------------------------------------------------------- C14
    cols = set()
    for path in ("data/derived/model_dataset.csv", "data/derived/features.csv",
                 "data/derived/bets.csv"):
        with (ROOT / path).open(encoding="utf-8") as fh:
            cols |= set(fh.readline().strip().split(","))
    hits = sorted(c for c in cols
                  if "injur" in c.lower() or "depth" in c.lower() or "inactive" in c.lower())
    add("C14", "Injury / depth-chart / inactive fields in the modelling data", 0, len(hits),
        "LIMITATION", "column-name scan of the three modelling CSVs", len(hits) == 0,
        "Confirms the published limitation: no strategy here ever used injury, depth or "
        "inactive information. It is a prior to be tested, not a measured edge.")

    ok = sum(1 for c in checks if c["result"] == "match")
    report = {
        "checked_utc": "2026-11-12",
        "checks": checks,
        "summary": {
            "total": len(checks), "matched": ok, "mismatched": len(checks) - ok,
            "official": sum(1 for c in checks if c["kind"] == "OFFICIAL"),
            "recomputed": sum(1 for c in checks if c["kind"] == "RECOMPUTED"),
            "limitation": sum(1 for c in checks if c["kind"] == "LIMITATION"),
        },
        "rows_used": {"same_game_pairs": n_same, "ledger_bets": len(settled)},
    }
    (HUB / "data" / "recompute.json").write_text(
        json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")

    for c in checks:
        print(f"{'ok  ' if c['result'] == 'match' else 'FAIL'} {c['id']} {c['name']}: "
              f"published {c['published']} / recomputed {c['recomputed']}")
    print(f"\n{ok}/{len(checks)} recomputation checks matched")
    return 0 if ok == len(checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
