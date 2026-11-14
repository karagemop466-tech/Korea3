#!/usr/bin/env python3
"""Deterministic lifecycle engine: the demotion gate and the separated leaderboards.

This module is pure arithmetic over two committed files:

    data/derived/gates_results.csv   one row per pre-registered strategy
    data/derived/bets.csv            the settled bet stream those strategies produced

It writes:

    lifecycle/data/demotion.json     the demotion-gate evaluation, one row per strategy
    lifecycle/data/leaderboard.json  the signal leaderboard and the staking leaderboard,
                                     kept as two separate registers

Nothing here reads the network, invents a value, or re-derives a price. Every number is either
transcribed from a committed CSV or a deterministic function of one. The two output files are
byte-reproducible: run this twice and the bytes are identical.

The demotion gate is this build's own design. Its rule is printed on the generated page *before*
any result, so a reader can see the predicate before reading what it produced.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
GATES_CSV = ROOT / "data" / "derived" / "gates_results.csv"
BETS_CSV = ROOT / "data" / "derived" / "bets.csv"
OUT = HERE / "data"

# --------------------------------------------------------------------------- #
# Demotion-gate parameters.
#
# These are this build's own design choices, not facts from an official publisher. They mirror the
# promotion gates the repository already publishes so that the same evidence that blocks a strategy
# from going live is what sends a live strategy back to paper. Each is printed on the page.
# --------------------------------------------------------------------------- #
Q_MAX = 0.10          # multiplicity ceiling: a BH q above this is not a live edge
CI_FLOOR = 0.0        # the lower bound of the ROI confidence interval must be positive
STABILITY_MIN = 0.5   # at least half of the tested seasons must have been positive
N_MIN = 200           # a live strategy needs at least this many settled bets (gate G1)

TRIGGER_ORDER = [
    ("N", "Sample size below the live floor"),
    ("Q", "Multiplicity q above the ceiling"),
    ("CI", "ROI confidence-interval lower bound not positive"),
    ("S", "Season stability below the floor"),
    ("G", "A mandatory gate not met"),
]


def _f(value, default=None):
    """Parse a CSV cell as float, returning default on an empty/invalid cell."""
    if value is None:
        return default
    value = str(value).strip()
    if value == "" or value.lower() in ("nan", "none", "null"):
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _i(value, default=None):
    if value is None:
        return default
    value = str(value).strip()
    if value == "" or value.lower() in ("nan", "none", "null"):
        return default
    try:
        return int(float(value))
    except ValueError:
        return default


def evaluate_demotion(row: dict, q_max: float = Q_MAX, ci_floor: float = CI_FLOOR,
                      stability_min: float = STABILITY_MIN, n_min: int = N_MIN) -> dict:
    """Return the demotion-gate verdict for one strategy row.

    A strategy is LIVE only if it clears every trigger. The first trigger that fires (in a fixed
    order) is recorded as the reason, and every trigger that fires is listed, so the page can show
    why a strategy is where it is rather than only the final label.
    """
    n = _i(row.get("n"))
    q = _f(row.get("q"))
    ci_low = _f(row.get("ci_low"))
    seasons_pos = _i(row.get("seasons_positive"))
    seasons_tested = _i(row.get("seasons_tested"))
    gates_failed = _i(row.get("gates_failed"))

    triggers = []
    if n is None or n < n_min:
        triggers.append(("N", f"n={n if n is not None else 'blank'} is below the live floor of {n_min}"))
    if q is not None and q > q_max:
        triggers.append(("Q", f"BH q={q:.4f} exceeds the ceiling of {q_max}"))
    if ci_low is not None and ci_low <= ci_floor:
        triggers.append(("CI", f"ROI 95% CI lower bound {ci_low:.4f} is not positive"))
    if seasons_pos is not None and seasons_tested and seasons_tested > 0:
        share = seasons_pos / seasons_tested
        if share < stability_min:
            triggers.append(("S", f"{seasons_pos}/{seasons_tested} seasons positive "
                                  f"({share:.2f}) is below the floor of {stability_min:.2f}"))
    elif seasons_pos is None or not seasons_tested:
        triggers.append(("S", "season stability is blank in the committed ledger"))
    if gates_failed is None or gates_failed > 0:
        gf = gates_failed if gates_failed is not None else "blank"
        triggers.append(("G", f"gates_failed={gf} (a mandatory gate is not met)"))

    status = "LIVE" if not triggers else "DEMOTED"
    first = triggers[0] if triggers else None
    return {
        "id": row.get("id", ""),
        "name": row.get("name", ""),
        "market": row.get("market", ""),
        "n": n,
        "roi": _f(row.get("roi")),
        "ci_low": ci_low,
        "ci_high": _f(row.get("ci_high")),
        "q": q,
        "p": _f(row.get("p")),
        "shrunk_roi": _f(row.get("shrunk_roi")),
        "seasons_positive": seasons_pos,
        "seasons_tested": seasons_tested,
        "gates_failed": gates_failed,
        "tier": row.get("tier", ""),
        "status": status,
        "triggers": triggers,
        "reason_code": first[0] if first else "",
        "reason": first[1] if first else "clears every demotion trigger",
    }


def _signal_key(row):
    """Signal quality: lower multiplicity q first, then higher shrunk ROI, then higher ROI."""
    q = _f(row.get("q"))
    shrunk = _f(row.get("shrunk_roi"))
    roi = _f(row.get("roi"))
    return (q if q is not None else 9.99,
            -(shrunk if shrunk is not None else -9.99),
            -(roi if roi is not None else -9.99),
            row.get("id", ""))


def _staking_key(row):
    """Realized staking outcome under flat 1-unit staking: higher realized ROI first."""
    roi = _f(row.get("roi"))
    n = _i(row.get("n"))
    return (-(roi if roi is not None else -9.99),
            -(n if n is not None else 0),
            row.get("id", ""))


def build_leaderboard(rows: list[dict]) -> dict:
    """Two separate registers: a signal leaderboard and a staking leaderboard."""
    signal = sorted(rows, key=_signal_key)
    staking = sorted(rows, key=_staking_key)
    sig_rank = {r.get("id"): i + 1 for i, r in enumerate(signal)}
    st_rank = {r.get("id"): i + 1 for i, r in enumerate(staking)}

    entries = []
    for r in rows:
        rid = r.get("id", "")
        entries.append({
            "id": rid,
            "name": r.get("name", ""),
            "market": r.get("market", ""),
            "n": _i(r.get("n")),
            "roi": _f(r.get("roi")),
            "shrunk_roi": _f(r.get("shrunk_roi")),
            "q": _f(r.get("q")),
            "ci_low": _f(r.get("ci_low")),
            "ci_high": _f(r.get("ci_high")),
            "signal_rank": sig_rank.get(rid),
            "staking_rank": st_rank.get(rid),
            "rank_gap": abs((sig_rank.get(rid) or 0) - (st_rank.get(rid) or 0)),
        })

    entries.sort(key=lambda e: e["signal_rank"])
    divergent = [e for e in entries if e["rank_gap"] >= 3]
    max_gap = max((e["rank_gap"] for e in entries), default=0)
    return {
        "signal_register": entries,
        "staking_register": sorted(entries, key=lambda e: e["staking_rank"]),
        "divergent_count": len(divergent),
        "max_rank_gap": max_gap,
        "divergent": divergent,
    }


def feed_summary() -> dict:
    """A deterministic summary of the committed settled bet stream (the results feed)."""
    if not BETS_CSV.exists():
        return {"available": False, "reason": "committed bets.csv not found"}
    with BETS_CSV.open(encoding="utf-8", newline="") as fh:
        rows = list(csv.DictReader(fh))
    outcomes: dict[str, int] = {}
    markets: dict[str, int] = {}
    strategies = set()
    total_pnl = 0.0
    for r in rows:
        strategies.add(r.get("strategy_id", ""))
        m = r.get("market", "")
        markets[m] = markets.get(m, 0) + 1
        o = (r.get("outcome") or "").strip().lower() or "blank"
        outcomes[o] = outcomes.get(o, 0) + 1
        pnl = _f(r.get("pnl"))
        if pnl is not None:
            total_pnl += pnl
    return {
        "available": True,
        "rows": len(rows),
        "strategies": len(strategies),
        "markets": markets,
        "outcomes": outcomes,
        "total_pnl": round(total_pnl, 6),
        "source_file": str(BETS_CSV.relative_to(ROOT)),
    }


def main() -> int:
    with GATES_CSV.open(encoding="utf-8", newline="") as fh:
        gate_rows = list(csv.DictReader(fh))

    demotion = [evaluate_demotion(r) for r in gate_rows]
    demotion.sort(key=lambda d: d["id"])
    live = [d for d in demotion if d["status"] == "LIVE"]
    demoted = [d for d in demotion if d["status"] == "DEMOTED"]
    trigger_counts: dict[str, int] = {}
    for d in demotion:
        for code, _ in d["triggers"]:
            trigger_counts[code] = trigger_counts.get(code, 0) + 1

    demotion_out = {
        "_meta": {
            "generated_by": "lifecycle/gate.py",
            "input_file": str(GATES_CSV.relative_to(ROOT)),
            "parameters": {
                "q_max": Q_MAX,
                "ci_floor": CI_FLOOR,
                "stability_min": STABILITY_MIN,
                "n_min": N_MIN,
            },
            "trigger_order": [{"code": c, "label": lbl} for c, lbl in TRIGGER_ORDER],
            "n_strategies": len(demotion),
            "n_live": len(live),
            "n_demoted": len(demoted),
            "trigger_counts": trigger_counts,
        },
        "strategies": demotion,
    }

    leaderboard = build_leaderboard(gate_rows)
    leaderboard["_meta"] = {
        "generated_by": "lifecycle/gate.py",
        "signal_rank_rule": "ascending BH q, then descending shrunk ROI, then descending ROI",
        "staking_rank_rule": "descending realized ROI under flat 1-unit staking, then descending n",
        "note": "The two registers are computed independently and are never blended into one rank.",
    }

    feed = feed_summary()

    (OUT / "demotion.json").write_text(json.dumps(demotion_out, indent=2, sort_keys=False) + "\n",
                                       encoding="utf-8")
    (OUT / "leaderboard.json").write_text(json.dumps(leaderboard, indent=2, sort_keys=False) + "\n",
                                          encoding="utf-8")
    (OUT / "feed.json").write_text(json.dumps(feed, indent=2, sort_keys=False) + "\n", encoding="utf-8")

    print(f"demotion: {len(demotion)} strategies, {len(live)} LIVE, {len(demoted)} DEMOTED")
    print(f"leaderboard: {len(leaderboard['signal_register'])} rows, "
          f"{leaderboard['divergent_count']} with a rank gap >= 3, max gap {leaderboard['max_rank_gap']}")
    if feed.get("available"):
        print(f"feed: {feed['rows']} rows, {feed['strategies']} strategies, "
              f"outcomes {feed['outcomes']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
