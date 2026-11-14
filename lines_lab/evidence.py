"""Evidence bundling: one place that computes every published number.

The pages are rendered from ``build()``. Nothing on a page is typed in; every figure
traces to a function in this module, which in turn traces to the pinned dataset or to
one of the registered sources. ``lines_lab/check.py`` re-derives a sample and fails the
build if a page disagrees with the data.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import data_layer as L
from . import depth_corr as D
from . import leaderboard as LB
from . import research as R

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "lines_lab" / "data"

SESSION = "arena/34cf3a80-korea3"
TODAY = "2026-11-14"


def _jsonable(o):
    if isinstance(o, dict):
        return {str(k): _jsonable(v) for k, v in o.items()}
    if isinstance(o, (list, tuple)):
        return [_jsonable(v) for v in o]
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        v = float(o)
        return None if (np.isnan(v) or np.isinf(v)) else v
    if isinstance(o, float):
        return None if (np.isnan(o) or np.isinf(o)) else o
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, pd.DataFrame):
        return _jsonable(o.to_dict(orient="records"))
    return o


def build() -> dict:
    """Compute everything once. Deterministic: no clock, no network, no randomness."""
    g = L.load_games()
    store = L.price_snapshots(g)
    cov = L.snapshot_coverage(store)
    chk = L.crosscheck_closing_lines(g)
    results = L.verified_results(g)
    res_sum = L.results_summary(g, dict(crosscheck=chk))

    feats = R.load_features(g)
    fair = R.walk_forward_fair_lines(feats)
    signals = R.test_signals(feats)
    fair_by_season = fair["by_season"]

    board = LB.build_board(signals)
    board["signal_p_adj"] = signals.p_bonferroni.values

    gate_rows = []
    for r in board.itertuples():
        v = LB.apply_gate(pd.Series({
            "n_decided": r.n,
            "signal_edge_lcb": getattr(r, "signal_lcb", None),
            "signal_p_adj": getattr(r, "signal_p_adj", None),
            "staking_return_per_bet": getattr(r, "staking_return_per_bet", None),
        }))
        gate_rows.append(v)
    board["state"] = [x["state"] for x in gate_rows]
    board["failed_gates"] = [x["failed"] for x in gate_rows]
    board["n_failed"] = [x["n_failed"] for x in gate_rows]

    # settled ledgers, so signal and staking are demonstrably different columns
    ledgers = []
    for sid in [s[0] for s in R.SIGNALS]:
        for plan in ("flat", "form"):
            b = R.staking_ledger(feats, sid, plan)
            if len(b):
                b["plan"] = plan
                ledgers.append(b)
    ledger = pd.concat(ledgers) if ledgers else pd.DataFrame()
    by_plan = {}
    if len(ledger):
        for sid in ledger.strategy_id.unique():
            sub = ledger[ledger.strategy_id == sid]
            row = {"id": sid}
            for plan in ("flat", "form"):
                p = sub[sub.plan == plan]
                row[f"return_{plan}"] = float(p.pnl.sum() / p.stake.sum()) if len(p) else None
                row[f"staked_{plan}"] = float(p.stake.sum()) if len(p) else None
            row["n"] = int(len(sub[sub.plan == "flat"]))
            by_plan[sid] = row

    depth = D.replacement_depth()
    corr = D.correlation_lab(feats)

    # parlay arithmetic, stated as arithmetic rather than as a measured edge
    parlays = []
    for pa, label in ((0.5238, "52.38% (the -110 breakeven)"), (0.55, "55%"),
                      (0.60, "60%")):
        for phi in (-0.10, -0.02, 0.0, 0.02, 0.10):
            v = D.parlay_fair_value(pa, pa, phi)
            parlays.append(dict(leg_prob=pa, break_even_note=label, phi=phi,
                                joint=v["joint_prob"], independent=v["independent_prob"],
                                decimal=v["parlay_decimal"], ev=v["ev"]))
    parlay_df = pd.DataFrame(parlays)

    sample_sizes = [dict(edge=e, bets=R.bets_needed(e)) for e in (0.01, 0.02, 0.03, 0.05, 0.08)]

    from .sources import DATASET
    files = {}
    for label, meta in DATASET["files"].items():
        p = ROOT / meta["path"]
        files[label] = dict(meta=meta, exists=p.exists(),
                            sha16_now=L.sha16(p) if p.exists() else None)

    out = dict(
        session=SESSION, today=TODAY,
        dataset=DATASET, files=files,
        coverage=cov,
        results=res_sum,
        fair_by_season=fair_by_season,
        fair_rows=fair["rows"],
        signals=signals,
        board=board,
        ledger=ledger,
        by_plan=by_plan,
        depth=depth["summary"],
        depth_rows=depth["rows"],
        corr=corr["rows"],
        parlays=parlay_df,
        sample_sizes=sample_sizes,
        crosscheck=chk["rows"],
        store_rows=store["rows"],
        gates=LB.GATES,
        demotion=R.DEMOTION_GATE,
        n_signals=int(len(R.SIGNALS)),
    )
    DATA.mkdir(parents=True, exist_ok=True)
    (DATA / "evidence.json").write_text(
        json.dumps(_jsonable({k: v for k, v in out.items()
                              if k not in ("fair_rows", "store_rows", "ledger", "depth_rows",
                                           "crosscheck", "fair_by_season", "corr")}), indent=2),
        encoding="utf-8")
    return out


if __name__ == "__main__":
    e = build()
    print("coverage:", e["coverage"])
    print("results:", e["results"])
    print("signals:", len(e["signals"]), "passing:", int(e["signals"].survives.sum()))
    print("board:", len(e["board"]), "LIVE:", int((e["board"].state == "LIVE").sum()))
    print("depth rows:", e["depth"].get("rows"))
    print("correlations:", len(e["corr"]))
