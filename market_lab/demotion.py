#!/usr/bin/env python3
"""The demotion gate: a live strategy is sent back to paper when its edge stops being real.

The existing gates G1–G9 are *promotion* gates: they decide whether a paper strategy may go
live. Nothing in the repository decides the reverse — whether a strategy that is already live
has stopped earning and must return to paper. This module defines that demotion gate.

Lifecycle
---------
    paper --(all G1–G9 pass)--> live --(demotion gate fails)--> paper

Demotion rule (a live strategy returns to paper if ANY condition fails)
-----------------------------------------------------------------------
Each condition is measured on the strategy's latest full evaluation window and is traceable to
a published number with a source. A strategy that is not currently live is still scored against
the same rule so the check is visible and auditable for every strategy.

    D1  Holdout ROI > 0            recent out-of-sample profit is positive
    D2  Bootstrap CI low > 0       profitability is significant, not a lucky run
    D3  Permutation percentile >= 95   result beats random selection at the same counts
    D4  Brier skill >= 0           the model beats the de-vigged market on calibration

A strategy is ``live`` only if it passed every promotion gate (G1–G9) **and** the demotion gate
is not triggered. Because no strategy in the current family has passed the promotion gates,
every strategy is ``paper`` today; the demotion check is still published so the rule and its
inputs are auditable and so a live strategy would be caught the moment its edge decays.
"""
from __future__ import annotations

# Each condition: id, name, the published metric it reads, the pass rule, and the source page.
DEMOTION_CONDITIONS = [
    ("D1", "Holdout profit", "holdout_roi", "holdout_roi > 0", "line_lab leaderboard"),
    ("D2", "Significance", "full_ci_low", "full_ci_low > 0", "line_lab leaderboard"),
    ("D3", "Luck control", "permutation_percentile", "permutation_percentile >= 95", "line_lab leaderboard"),
    ("D4", "Market skill", "brier_skill", "brier_skill >= 0", "line_lab leaderboard"),
]

DEMOTION_RULE = (
    "A live strategy is demoted to paper if any demotion condition fails on its latest full "
    "evaluation: D1 holdout ROI > 0, D2 bootstrap CI low > 0, D3 permutation percentile >= 95, "
    "D4 Brier skill >= 0. A strategy is live only if it passed every promotion gate (G1–G9) and "
    "the demotion gate is not triggered. The check is published for every strategy, live or not, "
    "so the rule and its inputs are auditable."
)


def _num(v):
    if v is None:
        return None
    try:
        f = float(v)
    except (TypeError, ValueError):
        return None
    if f != f:  # NaN
        return None
    return f


def demotion_check(strategy: dict) -> dict:
    """Score one strategy against the demotion rule.

    ``strategy`` is a leaderboard row carrying ``holdout_roi``, ``full_ci_low``,
    ``permutation_percentile`` and ``brier_skill``. Returns each condition's value, pass/fail,
    an ``unverified`` flag for a missing input, and the overall ``status``.
    """
    conditions = []
    all_pass = True
    any_unverified = False
    for cid, name, key, rule, source in DEMOTION_CONDITIONS:
        val = _num(strategy.get(key))
        if val is None:
            conditions.append({
                "id": cid, "name": name, "key": key, "value": None,
                "rule": rule, "result": "unverified", "source": source,
            })
            any_unverified = True
            all_pass = False
            continue
        ok = (val > 0) if cid in ("D1", "D2") else (val >= 95 if cid == "D3" else val >= 0)
        conditions.append({
            "id": cid, "name": name, "key": key, "value": val,
            "rule": rule, "result": "pass" if ok else "fail", "source": source,
        })
        if not ok:
            all_pass = False

    # A strategy is live only if it also cleared the promotion gates.
    promotion_ok = bool(strategy.get("eligible", False))
    if not promotion_ok:
        status = "paper"
    elif all_pass:
        status = "live"
    else:
        status = "demoted"

    return {
        "id": strategy.get("id"),
        "name": strategy.get("name"),
        "market": strategy.get("market"),
        "promotion_gates_passed": strategy.get("gates_passed"),
        "promotion_eligible": promotion_ok,
        "conditions": conditions,
        "demotion_all_pass": all_pass,
        "any_unverified": any_unverified,
        "status": status,
    }
