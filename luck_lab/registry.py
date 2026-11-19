#!/usr/bin/env python3
"""Pre-registration ledger, the two-sided "what would change our mind" field, and escrow.

Three requirements from the brief, one artifact:

  "Pre-register every strategy; forbid backtest numbers from ever appearing on the leaderboard"
  "Freeze a rule before it sees data: commit the rule text, the sample window and the gates to git
   before the evaluation window opens. The commit hash is the registration."
  "Add a two-sided 'what would change our mind' field to every strategy entry"

How the freeze is enforced without a time machine
-------------------------------------------------
`rule_hash` is the SHA-256 of a canonical JSON document holding the rule text, the evaluation
window and the gate list, all of them read out of the *source files that implement the strategy*
(`line_lab/strategies.py`, `line_lab/evaluation.py`, `origin_lab/leaderboard.py`) with `ast`, so
there is no hand-copied prose to drift. `luck_lab/check.py` recomputes that hash from the source
on every run: edit a rule and the gate goes red, which is the only way a "frozen" rule can be
given teeth after the fact.

The honest status column: any rule already scored on 2006-2025 cannot be pre-registered against
that window -- the data has been seen. Those rows are `RETRO_FROZEN_BACKTEST_ONLY`, which means
the hash is real, the backtest may be published, and *promotion is not available from it*. A rule
whose prospective sample has not started is `FROZEN_PROSPECTIVE`. Nothing here claims a rule was
frozen before a window it has already been evaluated on, because it was not.

Escrow (the second stage of the two-stage leaderboard)
------------------------------------------------------
`data/escrow_ledger.jsonl` is append-only and starts empty by design: promotion needs
`prospective_settled >= MIN_PROSPECTIVE` games recorded *after* the registration, at the frozen
thresholds. The page shows the count and the shortfall; it cannot show a promotion until the
ledger contains rows, and the check gate recomputes the count from the ledger every time.
"""
from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
import os

DATA_DIR = Path(os.environ.get("LUCK_LAB_DATA", str(HERE / "data")))
sys.path.insert(0, str(HERE))

OUT = DATA_DIR / "preregistration.json"
LEDGER = DATA_DIR / "escrow_ledger.jsonl"

# Registration date of this ledger: the date this file entered the repository. Not a clock read.
FROZEN_UTC = "2026-11-19"
MIN_PROSPECTIVE = 500          # settled prospective bets before a stage can advance
MIN_PROSPECTIVE_GAMES = 300    # distinct games, in case a run concentrates in few weeks
Q_MAX = 0.10

SOURCES = {
    "line_lab_strategies": ROOT / "line_lab" / "strategies.py",
    "line_lab_evaluation": ROOT / "line_lab" / "evaluation.py",
    "origin_leaderboard": ROOT / "origin_lab" / "leaderboard.py",
    "protocol": ROOT / "data" / "derived" / "summary.json",
}


def literal_from_source(path: Path, name: str):
    """Return the value of a module-level assignment `name = <literal>` parsed with ast."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name) and t.id == name:
                    try:
                        return ast.literal_eval(node.value), (node.lineno, node.end_lineno or node.lineno)
                    except (ValueError, TypeError):
                        return None, (node.lineno, node.end_lineno or node.lineno)
    return None, (0, 0)


def canonical_hash(obj) -> str:
    blob = json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def sha256_text(text: str) -> str:
    """Hash of a source file exactly as committed -- the byte-for-byte identity of the rule."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def read_window() -> dict:
    doc = json.loads(SOURCES["protocol"].read_text(encoding="utf-8"))
    p = doc.get("protocol", {})
    return {
        "eval_window": p.get("eval_window"),
        "holdout": p.get("holdout"),
        "edge_min": p.get("edge_min"),
        "price_band": [p.get("price_min"), p.get("price_max")],
        "bootstrap_resamples": p.get("bootstrap_resamples"),
        "permutation_resamples": p.get("permutation_resamples"),
        "seed": p.get("seed"),
        "fdr_level": p.get("fdr_level"),
        "source_file": "data/derived/summary.json",
    }


def read_gates() -> list[dict]:
    vals, span = literal_from_source(SOURCES["line_lab_evaluation"], "GATES")
    out = []
    if vals:
        for gid, title, text in vals:
            out.append({"id": gid, "title": title, "text": text})
    return out


def read_line_lab_strategies() -> tuple[list[dict], tuple]:
    vals, span = literal_from_source(SOURCES["line_lab_strategies"], "STRATEGIES")
    rows = []
    if vals:
        for sid, name, market in vals:
            rows.append({"id": sid, "name": name, "market": market})
    return rows, span


def read_origin_strategies() -> tuple[dict, tuple]:
    vals, span = literal_from_source(SOURCES["origin_leaderboard"], "STRATEGIES")
    return (vals or {}), span


def mind_fields(market: str, division: str, blocked: bool = False) -> dict:
    """The two-sided 'what would change our mind'. Written before any prospective result exists,
    so the answer cannot be fitted to it. Each side names the statistic and the threshold."""
    if blocked:
        return {
            "would_support": ("An official publisher prints prices for this market and a settlement log for the "
                               "statistic it is judged on, and a joint probability for the combination is validated "
                               "directly rather than multiplied from marginals."),
            "would_refute": ("Continued absence of an official price source, or a validated joint probability whose "
                             "interval covers zero, keeps this market blocked. Multiplying marginal probabilities "
                             "under dependence is not evidence."),
            "note": "Blocked by the joint-evidence gate; no number is ranked here.",
        }
    joint = market.upper() in {"PARLAY", "PARLAY_2_SAME_GAME", "PARLAY_2_CROSS_GAME", "PLAYER_PROP"}
    support = [
        "the game-cluster lower bound on the Brier skill score against the closing line clears 0",
        f"the Benjamini-Hochberg q over the tested family stays below {Q_MAX}",
        f"at least {MIN_PROSPECTIVE} prospective bets over {MIN_PROSPECTIVE_GAMES} distinct games are settled after the registration date",
        "the residual against the closing consensus is positive with the same bound (so the result is not a price race)",
    ]
    refute = [
        "the prospective lower bound on skill covers 0 at that sample size",
        "the calibration gap keeps the same sign and exceeds 0.03 (a level shift, not a signal)",
        "the profit from the single best game exceeds 20% of the total once the sample is large enough to judge",
        "another strategy in the family clears the bar and this one does not, at the same window",
    ]
    if joint:
        support.insert(0, "a directly validated joint probability for the legs, with the operator's void and push rules")
        refute.insert(0, "the joint probability, when measured, is not materially above the product of the marginals")
    return {
        "would_support": "Reclassify from shadow only if all of these hold: " + "; ".join(support) + ".",
        "would_refute": "Treat the signal as absent if any of these hold: " + "; ".join(refute) + ".",
        "note": ("Both sides are pre-committed from the gate definitions; the sample-size arithmetic is in "
                 "luck_lab/data/skill.json and the interval method is stated on the method page."),
    }


def main() -> int:
    window = read_window()
    gates = read_gates()
    line_rows, line_span = read_line_lab_strategies()
    origin_rows, origin_span = read_origin_strategies()
    skill = json.loads((HERE / "data" / "skill.json").read_text(encoding="utf-8"))
    skill_by_id = {r["strategy"]: r for r in skill["rows"]}

    entries: list[dict] = []
    for r in line_rows:
        sid = r["id"]
        sk = skill_by_id.get(sid, {})
        doc = {
            "registration_id": f"line_lab:{sid}",
            "ledger": "line_lab (data/derived/bets.csv)",
            "name": r["name"],
            "market": r["market"],
            "rule_text": ("Implemented in line_lab/strategies.py:build_all_bets (the mask for this id is the rule); "
                          "thresholds: " + json.dumps(window, sort_keys=True)),
            "rule_source": {"file": "line_lab/strategies.py", "assignment": "STRATEGIES",
                            "line_span": list(line_span)},
            "gates": gates,
            "evaluation_window": window,
            "implementation_sha256": {
                "line_lab/strategies.py": sha256_text(SOURCES["line_lab_strategies"].read_text(encoding="utf-8")),
                "line_lab/evaluation.py": sha256_text(SOURCES["line_lab_evaluation"].read_text(encoding="utf-8")),
            },
        }
        doc["rule_hash"] = canonical_hash({k: doc[k] for k in
                                          ("registration_id", "name", "market", "rule_text", "gates",
                                           "evaluation_window")})
        doc["frozen_utc"] = FROZEN_UTC
        doc["status"] = "RETRO_FROZEN_BACKTEST_ONLY"
        doc["status_reason"] = ("Scored on 2006-2025 before this ledger existed. The backtest may be published; "
                               "promotion from it is not available, because the window was seen before the freeze.")
        doc["prospective_window_opens"] = f"{window['eval_window'][1] + 1} season onward"
        doc["what_would_change_our_mind"] = mind_fields(r["market"], "")
        doc["backtest_skill_lb95"] = sk.get("brier_skill_lb95")
        doc["qualified_on_backtest_only"] = False
        entries.append(doc)

    for sid, spec in sorted(origin_rows.items()):
        doc = {
            "registration_id": f"origin_lab:{sid}",
            "ledger": "origin_lab (origin_lab/data/leaderboard.json)",
            "name": spec.get("name", ""),
            "market": spec.get("market", ""),
            "kind": spec.get("kind", ""),
            "rule_text": spec.get("rule", ""),
            "rule_source": {"file": "origin_lab/leaderboard.py", "assignment": "STRATEGIES",
                            "line_span": list(origin_span)},
            "gates": gates,
            "evaluation_window": window,
            "implementation_sha256": {
                "origin_lab/leaderboard.py": sha256_text(SOURCES["origin_leaderboard"].read_text(encoding="utf-8")),
            },
        }
        doc["rule_hash"] = canonical_hash({k: doc[k] for k in
                                          ("registration_id", "name", "market", "rule_text", "gates",
                                           "evaluation_window")})
        doc["frozen_utc"] = FROZEN_UTC
        blocked = sid == "S8" or spec.get("kind") in {"prop"}
        doc["status"] = "BLOCKED_NO_SOURCE" if blocked else "RETRO_FROZEN_BACKTEST_ONLY"
        doc["status_reason"] = ("No official publisher prints the prices or the settlement log this market needs, so "
                               "the rule is registered and every value stays blank." if blocked else
                               "The 2006-2025 window is already in the leaderboard file; the freeze is real but "
                               "retroactive, so promotion must come from the prospective ledger.")
        doc["prospective_window_opens"] = f"{window['eval_window'][1] + 1} season onward"
        doc["what_would_change_our_mind"] = mind_fields(spec.get("market", ""), spec.get("kind", ""), blocked=blocked)
        doc["backtest_skill_lb95"] = None
        doc["qualified_on_backtest_only"] = False
        entries.append(doc)

    # escrow: counts come from the ledger file, which is empty until a real prospective run appends
    ledger_rows = []
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8").splitlines():
            if line.strip():
                ledger_rows.append(json.loads(line))
    esc: dict[str, dict] = {}
    for e in entries:
        rid = e["registration_id"]
        mine = [r for r in ledger_rows if r.get("registration_id") == rid]
        settled = [r for r in mine if r.get("state") == "settled"]
        esc[rid] = {
            "prospective_entries": len(mine),
            "prospective_settled": len(settled),
            "prospective_games": len({r.get("game_id") for r in settled if r.get("game_id")}),
            "stage": ("shadow" if e["status"] != "BLOCKED_NO_SOURCE" else "blocked"),
            "advance_requires": f"{MIN_PROSPECTIVE} settled bets over {MIN_PROSPECTIVE_GAMES} games, "
                                f"game-cluster Brier-skill lower bound > 0, BH q <= {Q_MAX}",
            "shortfall_bets": max(0, MIN_PROSPECTIVE - len(settled)),
        }
    doc = {
        "_meta": {
            "generated_by": "luck_lab/registry.py",
            "session": "arena/fcac3e4f-korea3",
            "frozen_utc": FROZEN_UTC,
            "how_to_find_the_registration_commit": "git log --oneline -- luck_lab/data/preregistration.json",
            "rule_hash_definition": ("sha256 of the canonical (sorted-keys, compact) JSON of registration_id, name, "
                                     "market, rule_text, gates and evaluation_window. The implementation files are "
                                     "hashed beside it so a code change is visible even if the prose is not."),
            "teeth": "luck_lab/check.py recomputes every rule_hash from the source files and fails if one differs.",
            "entries": len(entries),
            "escrow_ledger": "luck_lab/data/escrow_ledger.jsonl",
            "escrow_rows": len(ledger_rows),
        },
        "entries": entries,
        "escrow": esc,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    if not LEDGER.exists():
        LEDGER.write_text("", encoding="utf-8")
    print(f"registry: {len(entries)} pre-registered strategies, escrow rows {len(ledger_rows)} "
          f"-> luck_lab/data/preregistration.json")
    for e in entries:
        print(f"  {e['registration_id']:16s} {e['status']:28s} hash {e['rule_hash'][:12]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
