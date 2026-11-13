#!/usr/bin/env python3
"""Derive desk/data/ledger.json from the repository's own published artifacts.

Why this file exists
--------------------
Every strategy number on `desk/signals.html` is typed by nobody. It is read out of the CSVs and
JSONs this repository already publishes, and desk/check.py re-runs this script and fails if the
committed ledger differs from the recomputation. That is the difference between "a table of
results" and "a table of results that cannot drift from its source".

Sources of the numbers, and what they are NOT
---------------------------------------------
The market prices behind these files come from one pinned third-party dataset
(nflverse/nfldata at commit a270278f...; see line_lab/data/derived/summary.json -> files[]). The
league publishes no prices, no lines and no settlement data, so no number here is an official
figure. desk/check.py verifies the local files still hash to the pinned digests, which is the only
verification available offline; it does not certify that a book's price was real.

Standard library only, deterministic, no network, no clock.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parent
DATA = HERE / "data"

Z975 = 1.959963984540054   # two-sided 5%
Z80 = 0.8416212335729143   # 80% power
Z90 = 1.2815515655446004   # 90% power


def ncdf(z: float) -> float:
    """Standard normal CDF, from math.erf only."""
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def two_sided_p(z: float) -> float:
    return max(0.0, min(1.0, 2.0 * (1.0 - ncdf(abs(z)))))


def load_json(rel: str):
    return json.loads((REPO / rel).read_text(encoding="utf-8"))


def dig(d, *keys, default=None):
    """Walk nested containers and return whatever is there, including dicts and lists."""
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur


def jget(d, *keys, default=""):
    cur = d
    for k in keys:
        if isinstance(cur, dict) and k in cur:
            cur = cur[k]
        else:
            return default
    return cur if isinstance(cur, (int, float, str, bool)) else default


# --------------------------------------------------------------------------- #
def luck_math(n_decided: int, wins: int, breakeven: float) -> dict:
    """Everything about a row that can be recomputed from (n, wins) alone."""
    if not n_decided:
        return {"n_decided": 0}
    p = wins / n_decided
    se_null = math.sqrt(0.25 / n_decided)
    se_p = math.sqrt(max(p * (1 - p), 1e-12) / n_decided)
    z_b = (p - breakeven) / se_null if se_null else 0.0
    # n required so that a true win rate p is detected against the breakeven rate
    # at two-sided 5% with the named power (standard two-proportion normal approximation).
    def n_needed(target_p: float, z_pow: float) -> int:
        """Bets needed for a true win rate of target_p to beat `breakeven` at
        two-sided 5% with the given power (normal approximation, one-sample proportion)."""
        d = target_p - breakeven
        if d <= 0:
            return 0
        num = Z975 * math.sqrt(breakeven * (1 - breakeven)) + z_pow * math.sqrt(target_p * (1 - target_p))
        return int(math.ceil((num / d) ** 2))
    return {
        "n_decided": n_decided,
        "win_rate": round(p, 6),
        "z_vs_breakeven": round(z_b, 4),
        "p_vs_breakeven": round(two_sided_p(z_b), 6),
        "luck_band_95_pp": round(1.96 * se_null * 100, 3),
        "n_needed_at_observed_80pct": n_needed(p, Z80),
        "n_needed_at_2pp_80pct": n_needed(breakeven + 0.02, Z80),
        "n_needed_at_2pp_90pct": n_needed(breakeven + 0.02, Z90),
        "seasons_at_500_bets_80pct": round(n_needed(breakeven + 0.02, Z80) / 500.0, 2),
    }


def phi_from(joint: float, pa: float, pb: float) -> float:
    """Pearson phi for two binary events, from the marginal and joint rates alone."""
    den = math.sqrt(pa * (1 - pa) * pb * (1 - pb))
    return round((joint - pa * pb) / den, 6) if den else ""


# --------------------------------------------------------------------------- #
def main() -> None:
    out: dict = {"generated_by": "desk/build_ledger.py", "note": []}

    # ---- 1. line_lab ledger: 11 strategies, protocol, accuracy, correlations ----
    S = load_json("line_lab/data/derived/summary.json")
    rows = []
    for st in S.get("strategies", []):
        mf = st.get("metrics_full", {}) or {}
        w, l, push = int(jget(mf, "wins", default=0)), int(jget(mf, "losses", default=0)), int(jget(mf, "pushes", default=0))
        n = int(jget(mf, "bets", default=0))
        be = jget(mf, "breakeven", default="") or 0.5238
        rows.append({
            "id": st.get("id", ""), "name": st.get("name", ""), "market": str(st.get("market", "")).upper(),
            "bets": n, "wins": w, "losses": l, "pushes": push,
            "win_rate": round(jget(mf, "win_rate", default=0.0), 6),
            "roi_full": round(jget(mf, "roi", default=0.0), 6),
            "roi_ci_low": round(jget(mf, "roi_ci_low", default=0.0), 6),
            "roi_ci_high": round(jget(mf, "roi_ci_high", default=0.0), 6),
            "p_value": jget(mf, "p_value", default=""),
            "q_value_fdr": round(jget(st, "q_value", default=0.0), 6) if jget(st, "q_value", default=None) != "" else "",
            "holdout_roi": round(jget(st, "holdout", "roi", default=0.0), 6),
            "holdout_bets": jget(st, "holdout", "bets", default=""),
            "gates_passed": len([1 for k, v in (st.get("gates") or {}).items() if v is True]) if isinstance(st.get("gates"), dict) else jget(st, "gate_passes", default=""),
            "gates_total": len(st.get("gates") or []) if st.get("gates") else "",
            "eligible": bool(st.get("eligible")),
            "reward_points": st.get("reward_points") if st.get("reward_points") is not None else "",
            "permutation_percentile": jget(st, "permutation", "percentile", default=""),
            "brier_skill": round(jget(st, "brier_skill", default=0.0), 6) if jget(st, "brier_skill", default=None) not in (None, "") else "",
            "seasons": jget(mf, "seasons", default=""),
            "positive_season_share": jget(mf, "positive_season_share", default=""),
            "max_drawdown": round(jget(mf, "max_drawdown", default=0.0), 3) if jget(mf, "max_drawdown", default=None) not in (None, "") else "",
            "luck": luck_math(w + l, w, be),
            "source": "R01", "artifact": "line_lab/data/derived/summary.json",
        })
    out["line_lab"] = {
        "protocol": S.get("protocol", {}),
        "universe": S.get("universe", {}),
        "strategies": rows,
        "accuracy": S.get("accuracy", {}),
        "luck_band": dig(S, "extras", "luck_band", default={}) or {},
        "power_table": dig(S, "extras", "power", default=[]) or [],
        "hold": dig(S, "extras", "hold", default={}) or {},
        "sensitivity_rows": len((dig(S, "extras", "sensitivity", default={}) or {}).get("grid", []) or []),
    }

    # ---- 2. pipeline ledger: 18 signals x 8 gates ----
    with (REPO / "data/derived/gates_results.csv").open(encoding="utf-8") as fh:
        pipe = list(csv.DictReader(fh))
    prows = []
    for r in pipe:
        n = int(float(r.get("n") or 0))
        wr = float(r.get("win_rate") or 0.0)
        wins = round(wr * n)
        prows.append({
            "id": r.get("id", ""), "name": r.get("name", ""), "market": (r.get("market") or "").upper(),
            "n": n, "n_conf": int(float(r.get("n_conf") or 0)),
            "win_rate": round(wr, 6), "roi": round(float(r.get("roi") or 0.0), 6),
            "roi_conf": round(float(r.get("roi_conf") or 0.0), 6),
            "ci_low": round(float(r.get("ci_low") or 0.0), 6), "ci_high": round(float(r.get("ci_high") or 0.0), 6),
            "p": round(float(r.get("p") or 0.0), 6), "q_fdr": round(float(r.get("q") or 0.0), 6),
            "coinflip_p": r.get("coinflip_p", ""), "shrunk_roi": round(float(r.get("shrunk_roi") or 0.0), 6),
            "se_roi": round(float(r.get("se_roi") or 0.0), 6),
            "seasons_positive": r.get("seasons_positive", ""), "seasons_tested": r.get("seasons_tested", ""),
            "gates_passed": [k for k in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8") if (r.get(k) or "").lower() == "true"],
            "gates_failed": [k for k in ("G1", "G2", "G3", "G4", "G5", "G6", "G7", "G8") if (r.get(k) or "").lower() == "false"],
            "verdict": r.get("verdict", ""), "tier": r.get("tier", ""),
            "n_needed_at_observed_edge": r.get("n_needed_at_observed_edge", ""),
            "luck": luck_math(n, wins, 0.5238),
            "source": "R02", "artifact": "data/derived/gates_results.csv",
        })
    out["pipeline"] = {"signals": prows, "n_rows": len(prows),
                       "passed": [r["id"] for r in prows if not r["gates_failed"]]}

    # ---- 3. docs leaderboard (six-gate scoring) + verified workbench ----
    LB = load_json("reports/leaderboard.json")
    out["docs_leaderboard"] = {
        "pool_units": LB.get("pool_units", ""), "eligible": LB.get("eligible", ""),
        "generated_utc": LB.get("generated_utc", ""),
        "rows": [{"rank": r.get("rank", ""), "id": r.get("id", ""), "name": r.get("name", ""),
                  "score": r.get("score", ""), "validated": bool(r.get("validated")),
                  "reward_units": r.get("reward_units", ""), "roi_full": r.get("roi_full", ""),
                  "roi_holdout": r.get("roi_holdout", ""), "bets": r.get("bets", ""),
                  "gates_passed": r.get("gates_passed", ""), "gates_total": r.get("gates_total", ""),
                  "source": "R03", "artifact": "reports/leaderboard.json"} for r in LB.get("ranking", [])],
    }
    V = load_json("verified/data/leaderboard.json")
    out["verified_workbench"] = {
        "rows": [{"rank": v.get("rank", ""), "strategy_id": v.get("strategy_id", ""),
                  "score": v.get("score") if v.get("score") is not None else "",
                  "reward": v.get("reward") if v.get("reward") is not None else "",
                  "status": v.get("status", ""), "source": "R04", "artifact": "verified/data/leaderboard.json"}
                 for v in V],
        "all_not_eligible": all(v.get("rank") is None and v.get("score") is None for v in V),
        "n": len(V),
    }

    # ---- 4. strategy-family multiplicity (both families, recomputed q) ----
    fam = [r for r in out["pipeline"]["signals"]]
    ps = sorted((float(r["p"]) for r in fam if r["p"] != ""))
    m = len(ps)
    q_recomputed = []
    for i, p in enumerate(ps, start=1):
        q = min(1.0, p * m / i)
        q_recomputed.append(q)
    out["multiplicity"] = {
        "family_size": m, "sorted_p_head": [round(x, 6) for x in ps[:5]],
        "q_at_rank_1_by_hand": round(q_recomputed[0], 6) if q_recomputed else "",
        "q_published_rank_1": fam[0]["q_fdr"] if fam else "",
        "note": "Benjamini-Hochberg q at rank 1 recomputed from the published p-values only. It exists to show what multiplicity does to the best result in a family, not to replace the pipeline's own q.",
    }

    # ---- 5. correlation: recompute phi from the published marginals ----
    # The file publishes P(A and B), P(B), P(B|A) and P(A)P(B). P(A) is recovered from
    # joint / P(B|A); phi is then the textbook 2x2 coefficient, recomputed here rather than trusted.
    corr = []
    for pair, d in (dig(S, "correlations", "same_game", "pairs", default={}) or {}).items():
        if not isinstance(d, dict):
            continue
        joint, pb, pba = d.get("joint_rate"), d.get("p_b_marginal"), d.get("p_b_given_a")
        if None in (joint, pb, pba) or not pba:
            corr.append({"pair": pair, "phi_published": d.get("phi", ""), "recomputed": "", "status": "inputs incomplete"})
            continue
        p_a = joint / pba
        if p_a in ("", 0):
            corr.append({"pair": pair, "phi_published": d.get("phi", ""), "recomputed": "", "status": "inputs incomplete"})
            continue
        recomputed = phi_from(joint, p_a, pb)
        published = d.get("phi", "")
        ok = isinstance(published, (int, float)) and abs(recomputed - published) < 5e-4
        corr.append({"pair": pair, "n": d.get("n", ""), "phi_published": round(published, 6) if isinstance(published, (int, float)) else published,
                     "phi_recomputed": recomputed, "abs_gap": round(abs(recomputed - published), 8) if isinstance(published, (int, float)) else "",
                     "status": "MATCH" if ok else "DIFFERS",
                     "marginal_a_implied": round(p_a, 6), "marginal_b": round(pb, 6), "joint": round(joint, 6),
                     "ci_low": d.get("ci_low", ""), "ci_high": d.get("ci_high", ""),
                     "source": "R01", "artifact": "line_lab/data/derived/summary.json"})
    CM = load_json("data/derived/corr_meta.json")
    out["correlation"] = {
        "same_game_pairs": corr,
        "breakeven_phi_2leg": CM.get("breakeven_phi_2leg_110_p50", ""),
        "breakeven_phi_3leg": CM.get("breakeven_phi_3leg_110_p50", ""),
        "cross_game": dig(CM, "cross_game", default={}) or {},
        "signal_matrix": dig(CM, "signal_matrix", default={}) or {},
        "source": "R03", "artifact": "data/derived/corr_meta.json",
    }

    # ---- 6. own-line accuracy: model vs market, and the README claim ----
    MM = load_json("data/derived/model_metrics.json")
    sens = MM.get("sensitivity", [])
    prim = MM.get("primary_variant", "")
    var = (MM.get("variants", {}) or {}).get(prim, {}) if prim else {}
    out["own_lines"] = {
        "primary_variant": prim,
        "variant_metrics": {k: (round(v, 6) if isinstance(v, float) else v) for k, v in (var or {}).items()},
        "sensitivity_grid_rows": len(sens),
        "sensitivity_head": [{k: (round(x, 4) if isinstance(x, float) else x) for k, x in s.items()} for s in sens[:3]],
        "line_lab_accuracy": dig(S, "accuracy", default={}) or {},
        "unplayed_fixtures": jget(S, "universe", "unplayed_games", default=""),
        "source": "R01", "artifact": "data/derived/model_metrics.json",
        "readme_claim_check": {
            "claim": "README: own-line error 10.670 pts vs 10.247 for the closing line",
            "found_in": "data/derived/model_metrics.json sensitivity grid",
            "matched_rows": [ {k: (round(x, 4) if isinstance(x, float) else x) for k, x in s.items()}
                              for s in sens if isinstance(s.get("model_mae_spread"), (int, float))
                              and abs(s["model_mae_spread"] - 10.670) < 0.02 and abs(s["market_mae_spread"] - 10.247) < 0.02 ],
            "verdict": "",
        },
    }
    if out["own_lines"]["readme_claim_check"]["matched_rows"]:
        out["own_lines"]["readme_claim_check"]["verdict"] = "MATCH - a grid row reproduces both figures"
    else:
        out["own_lines"]["readme_claim_check"]["verdict"] = "NO EXACT ROW - the figures are near but not identical to any published grid row"

    # ---- 7. pinned-dataset integrity (offline recomputation of the digests) ----
    files = S.get("files", [])
    hashes = []
    for f in files:
        p = REPO / f.get("file", "")
        rec = f.get("sha256", "")
        if p.is_file():
            local = hashlib.sha256(p.read_bytes()).hexdigest()
            hashes.append({"file": f.get("file", ""), "recorded": rec, "recomputed": local,
                           "status": "MATCH" if local == rec else "MISMATCH",
                           "pinned_commit": f.get("pinned_commit", ""), "commit_url": S.get("commit_url", ""),
                           "bytes": f.get("bytes", ""), "local_bytes": p.stat().st_size})
        else:
            hashes.append({"file": f.get("file", ""), "recorded": rec, "recomputed": "", "status": "FILE ABSENT",
                           "pinned_commit": f.get("pinned_commit", ""), "commit_url": S.get("commit_url", ""),
                           "bytes": f.get("bytes", ""), "local_bytes": ""})
    out["pinned_dataset"] = {"files": hashes, "matched": sum(1 for h in hashes if h["status"] == "MATCH"),
                             "total": len(hashes), "commit_url": S.get("commit_url", ""),
                             "note": "SHA-256 recomputed on 2026-11-13 by this script. It proves the bundled CSVs are still the files the ledgers were computed from; it does not certify the dataset's own accuracy."}

    # ---- 8. the ID collision, made concrete ----
    ll_by = {r["id"]: r["name"] for r in out["line_lab"]["strategies"]}
    pl_by = {r["id"]: r["name"] for r in out["pipeline"]["signals"]}
    dl_by = {r["id"]: r["name"] for r in out["docs_leaderboard"]["rows"]}
    ids = sorted(set(ll_by) | set(pl_by) | set(dl_by))
    clash = []
    for i in ids:
        names = {n for n in (ll_by.get(i), pl_by.get(i), dl_by.get(i)) if n}
        if len(names) > 1:
            clash.append({"id": i, "line_lab": ll_by.get(i, ""), "pipeline": pl_by.get(i, ""), "docs_leaderboard": dl_by.get(i, "")})
    out["id_collisions"] = {
        "rows": clash, "colliding_ids": [c["id"] for c in clash],
        "note": "Flagged upstream as X01 and still unresolved in main: three ledgers reuse S1..S18 for different rules. Anything that scores a strategy by ID alone can pay the wrong ledger. The proposed fix is a namespaced key (family::id) in suggestion K06.",
    }
    out["note"] = [
        "Every figure above was read from the artifact named on its row and can be regenerated by running desk/build_ledger.py.",
        "Blank means the artifact does not publish that field for that row. It never means zero.",
        "No number in this file is official. The league publishes no lines, prices, ROI or correlation coefficients.",
    ]

    (DATA / "ledger.json").write_text(json.dumps(out, indent=1, sort_keys=False) + "\n", encoding="utf-8")
    print(f"ledger written: {len(out['line_lab']['strategies'])} line_lab strategies, "
          f"{out['pipeline']['n_rows']} pipeline signals, {len(out['docs_leaderboard']['rows'])} ranked rows, "
          f"{out['pinned_dataset']['matched']}/{out['pinned_dataset']['total']} pinned hashes, "
          f"{len(clash)} colliding ids, gates passed in pipeline ledger: {out['pipeline']['passed'] or 'none'}")


if __name__ == "__main__":
    main()
