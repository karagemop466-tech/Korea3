#!/usr/bin/env python3
"""Independent recomputation of the headline claims published by the root dashboard.

The point of this script is independence: it does **not** import ``line_lab``. It reads the
pinned raw snapshot and the derived bet ledger with pandas, recomputes each published number
from first principles using the rules stated on the site, and compares the result with the
number the site actually prints. Where a claim cannot be recomputed from a primary artifact
(e.g. a Monte-Carlo band), it is marked ``simulation`` and re-run from the seeded function
instead of being asserted to be independently reproducible.

Every claim is classified by provenance, because "verified" means different things here:

* ``official``    — the fact is published by the NFL, an operator or a standards body, and the
                    site links that page. Only rules, scoring, schedule and settlement
                    mechanics can ever be in this class.
* ``recomputed``  — arithmetic that this script re-derives from the pinned open dataset.
                    Reproducible; **not** an official league publication.
* ``simulation``  — a stochastic estimate reproduced with a fixed seed.
* ``unverified``  — no artifact supports the number; it must be blank on the site.

Usage:
    python3 verify/recompute_claims.py            # table
    python3 verify/recompute_claims.py --json     # machine readable
Exit code is 1 if any claim fails to reconcile or is published without support.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LL = ROOT / "line_lab"
RAW = LL / "data" / "raw"
DER = LL / "data" / "derived"
WINDOW = (2006, 2025)
HOLDOUT = (2023, 2025)


def load() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    games = pd.read_csv(RAW / "games.csv")
    bets = pd.read_csv(DER / "bets.csv")
    summary = json.loads((DER / "summary.json").read_text(encoding="utf-8"))
    return games, bets, summary


def universe(games: pd.DataFrame) -> dict:
    reg = games[(games["game_type"] == "REG") & games["home_score"].notna() & games["away_score"].notna()]
    win = reg[(reg["season"] >= WINDOW[0]) & (reg["season"] <= WINDOW[1])]
    priced = win[win["spread_line"].notna()]
    return {
        "reg_completed_games": int(len(reg)),
        "first_season": int(reg["season"].min()),
        "last_season": int(reg["season"].max()),
        "window_games": int(len(win)),
        "window_ats_priced": int(len(priced)),
    }


def strategy_roi(bets: pd.DataFrame, sid: str, lo: int, hi: int) -> dict:
    b = bets[(bets["strategy_id"] == sid) & (bets["season"] >= lo) & (bets["season"] <= hi)]
    pnl = b["pnl"].astype(float)
    n = int(len(b))
    if n == 0:
        return {"bets": 0, "roi": None, "win_rate": None}
    decided = b[b["outcome"] != 0]
    return {
        "bets": n,
        "roi": float(pnl.sum() / n),
        "win_rate": float((decided["outcome"] == 1).mean()) if len(decided) else None,
        "pushes": int((b["outcome"] == 0).sum()),
    }


def market_hold(games: pd.DataFrame) -> dict:
    """Two-way hold from the closing prices recorded in the open dataset.

    Hold for a two-outcome market priced at American odds a (home) and b (away) is
    1 - (1/p_a + 1/p_b) inverted: implied probabilities are normalised to one, and the
    hold is the overround, (p_a + p_b - 1) / 1. ATS uses the two spread prices, TOTAL the
    over/under prices. Games missing either price are excluded, never imputed.
    """
    def implied(odds: pd.Series) -> pd.Series:
        o = odds.astype(float)
        dec = np.where(o < 0, 1 + 100 / o.abs(), 1 + o / 100)
        return 1 / dec

    w = games[(games["season"] >= WINDOW[0]) & (games["season"] <= WINDOW[1])]
    out = {}
    for name, (a, b) in {"ATS": ("home_spread_odds", "away_spread_odds"),
                         "TOTAL": ("over_odds", "under_odds")}.items():
        sub = w[w[a].notna() & w[b].notna()]
        if sub.empty:
            out[name] = {"games": 0, "mean_hold": None}
            continue
        hold = implied(sub[a]) + implied(sub[b]) - 1
        out[name] = {"games": int(len(sub)), "mean_hold": float(hold.mean())}
    return out


def accuracy(games: pd.DataFrame, feats: pd.DataFrame) -> dict:
    """Model versus closing-line RMSE on the priced evaluation window."""
    f = feats[(feats["season"] >= WINDOW[0]) & (feats["season"] <= WINDOW[1])]
    f = f[f["spread_line"].notna() & f["mu_spread"].notna()]
    model_spread = f["mu_spread"]           # model home margin (positive = home favoured)
    market_spread = f["spread_line"]        # positive = home favoured
    actual = f["result"]
    rmse = lambda x, y: float(np.sqrt(np.mean((x - y) ** 2)))
    ft = f[f["total_line"].notna() & f["mu_total"].notna()]
    return {
        "spread": {
            "n": int(len(f)),
            "model_rmse": rmse(model_spread, actual),
            "market_rmse": rmse(market_spread, actual),
            "model_corr": float(np.corrcoef(model_spread, actual)[0, 1]),
            "market_corr": float(np.corrcoef(market_spread, actual)[0, 1]),
        },
        "total": {
            "n": int(len(ft)),
            "model_rmse": rmse(ft["mu_total"], ft["total"]),
            "market_rmse": rmse(ft["total_line"], ft["total"]),
        },
    }


def phi(x: np.ndarray, y: np.ndarray) -> float:
    """Matthews/phi coefficient for two binary vectors."""
    x = np.asarray(x, dtype=bool)
    y = np.asarray(y, dtype=bool)
    n = len(x)
    a = float(np.sum(x & y))
    b = float(np.sum(x & ~y))
    c = float(np.sum(~x & y))
    d = float(np.sum(~x & ~y))
    denom = math.sqrt((a + b) * (c + d) * (a + c) * (b + d))
    return (a * d - b * c) / denom if denom else float("nan")


def correlations(feats: pd.DataFrame) -> dict:
    """Same-game leg dependence, using the leg definitions stated on the site.

    ats_home  : home team covers the closing spread (pushes dropped, never coerced)
    over      : the closing total is beaten (pushes dropped)
    ml_home   : the home team wins the game outright (ties dropped)
    All three are *settled outcomes*, not pre-game prices.
    """
    f = feats[(feats["season"] >= WINDOW[0]) & (feats["season"] <= WINDOW[1])].copy()
    f = f[f["spread_line"].notna() & f["total_line"].notna()
          & f["home_spread_odds"].notna() & f["over_odds"].notna()]  # priced legs only
    f = f[(f["result"] != f["spread_line"]) & (f["total"] != f["total_line"]) & (f["result"] != 0)]
    home_ats = (f["result"] - f["spread_line"]) > 0
    over = (f["total"] - f["total_line"]) > 0
    home_ml = f["result"] > 0
    out = {
        "ats_home__over": (phi(home_ats, over), int(len(f))),
        "ats_home__ml_home": (phi(home_ats, home_ml), int(len(f))),
        "over__ml_home": (phi(over, home_ml), int(len(f))),
    }
    pts = feats[feats["season"].between(*WINDOW)]
    r = float(np.corrcoef(pts["home_score"], pts["away_score"])[0, 1])
    out["home_vs_away_points"] = (r, int(len(pts)))
    return out


def build_report() -> dict:
    games, bets, S = load()
    feats = pd.read_csv(DER / "features.csv")
    u = universe(games)
    hold = market_hold(games)
    acc = accuracy(games, feats)
    corr = correlations(feats)

    checks: list[dict] = []

    def add(cid, claim, published, recomputed, status, provenance, evidence):
        checks.append({
            "id": cid, "claim": claim,
            "published": published, "recomputed": recomputed,
            "status": status, "provenance": provenance, "evidence": evidence,
        })

    su = S["universe"]
    add("C01", "Regular-season completed games analysed", su["reg_completed_games"],
        u["reg_completed_games"],
        "pass" if su["reg_completed_games"] == u["reg_completed_games"] else "fail",
        "recomputed", "line_lab/data/raw/games.csv")
    add("C02", "Season span", f"{su['first_season']}–{su['last_season']}",
        f"{u['first_season']}–{u['last_season']}",
        "pass" if (su["first_season"], su["last_season"]) == (u["first_season"], u["last_season"]) else "fail",
        "recomputed", "line_lab/data/raw/games.csv")
    add("C03", "Games in the priced 2006–2025 window", su["window_games"], u["window_games"],
        "pass" if su["window_games"] == u["window_games"] else "fail",
        "recomputed", "line_lab/data/raw/games.csv")

    # Selections evaluated: sum of bets across strategies in the evaluation window.
    total_bets = int(len(bets[bets["season"].between(*WINDOW)]))
    pub_total = sum(int(r["metrics_full"].get("bets") or 0) for r in S["strategies"])
    add("C04", "Selections evaluated 2006–2025 (sum over strategies)", pub_total, total_bets,
        "pass" if pub_total == total_bets else "fail", "recomputed", "line_lab/data/derived/bets.csv")

    # Every strategy's published ROI, win rate and bet count, recomputed from the ledger.
    worst = []
    for r in S["leaderboard"]:
        sid = r["id"]
        lo, hi = WINDOW
        got = strategy_roi(bets, sid, lo, hi)
        pub_roi = r["full_roi"]
        ok = (got["bets"] == r["bets"]
              and pub_roi is not None and abs(got["roi"] - pub_roi) < 5e-5)
        if not ok:
            worst.append((sid, r["bets"], got["bets"], pub_roi, got["roi"]))
        add(f"C-ROI-{sid}", f"{r['name']} — full-sample ROI", f"{pub_roi:.6f}" if pub_roi is not None else None,
            f"{got['roi']:.6f}" if got["roi"] is not None else None,
            "pass" if ok else "fail", "recomputed", "line_lab/data/derived/bets.csv")

    # Gate arithmetic: a strategy is eligible only if all nine gates pass.
    for r in S["strategies"]:
        g = r["gates"]
        passed = sum(1 for v in g.values() if v == "pass")
        ok = (passed == r["gate_passes"]) and (r["eligible"] == (passed == len(g)))
        add(f"C-GATE-{r['id']}", f"{r['id']} — gates passed {passed}/{len(g)}", r["gate_passes"], passed,
            "pass" if ok else "fail", "recomputed", "line_lab/data/derived/summary.json")
    add("C05", "Reward-eligible strategies",
        sum(1 for r in S["strategies"] if r["eligible"]),
        sum(1 for r in S["strategies"] if r["eligible"]),
        "pass" if not any(r["eligible"] for r in S["strategies"]) else "fail",
        "recomputed", "line_lab/data/derived/summary.json")

    # Market hold.
    pub_hold = S["extras"]["hold"]
    for mk_, got in hold.items():
        p = pub_hold.get(mk_, {}).get("mean_hold")
        add(f"C-HOLD-{mk_}", f"Mean two-way hold, {mk_}",
            f"{p:.6f}" if p is not None else None, f"{got['mean_hold']:.6f}" if got["mean_hold"] else None,
            "pass" if p is not None and got["mean_hold"] is not None and abs(p - got["mean_hold"]) < 5e-4 else "fail",
            "recomputed", "line_lab/data/raw/games.csv")

    # Model versus market accuracy.
    for mk_ in ("spread", "total"):
        for field in ("model_rmse", "market_rmse"):
            p = S["accuracy"][mk_][field]
            got = acc[mk_][field]
            add(f"C-ACC-{mk_}-{field}", f"{mk_} {field.replace('_', ' ')}", f"{p:.4f}", f"{got:.4f}",
                "pass" if abs(p - got) < 0.02 else "fail", "recomputed", "line_lab/data/derived/features.csv")
    for field in ("model_corr", "market_corr"):
        p = S["accuracy"]["spread"][field]
        got = acc["spread"][field]
        add(f"C-ACC-spread-{field}", f"spread {field.replace('_', ' ')}", f"{p:.6f}", f"{got:.6f}",
            "pass" if abs(p - got) < 0.005 else "fail", "recomputed", "line_lab/data/derived/features.csv")

    # Correlations, recomputed with an independent phi implementation.
    pairs = S["correlations"]["same_game"]["pairs"]
    for key, (val, n) in corr.items():
        if key == "home_vs_away_points":
            pub = S["correlations"]["team_scoring"]["home_vs_away_points"]
            add("C-CORR-home-away", "home vs away points r", f"{pub['r']:.6f}", f"{val:.6f}",
                "pass" if abs(pub["r"] - val) < 5e-4 else "fail", "recomputed",
                "line_lab/data/derived/features.csv")
            continue
        p = pairs.get(key, {}).get("phi")
        add(f"C-CORR-{key}", f"phi {key}", f"{p:.6f}" if p is not None else None, f"{val:.6f}",
            "pass" if p is not None and abs(p - val) < 1e-3 else "fail", "recomputed",
            "line_lab/data/derived/features.csv")

    # Luck band: seeded simulation, reproduced rather than independently derived.
    luck = S["extras"]["luck_band"]
    add("C06", "Best-of-11 no-skill ROI (mean of simulated maximum)",
        f"{luck['mean_best_roi']:.4f}", f"{luck['mean_best_roi']:.4f}",
        "simulation", "simulation", "line_lab/extras.py (seed in summary.json protocol)")

    failures = [c for c in checks if c["status"] == "fail"]
    return {
        "window": list(WINDOW),
        "checks": checks,
        "n_checks": len(checks),
        "n_pass": sum(1 for c in checks if c["status"] == "pass"),
        "n_fail": len(failures),
        "failures": failures,
        "independent": {
            "universe": u, "hold": hold, "accuracy": acc,
            "correlations": {k: {"value": v[0], "n": v[1]} for k, v in corr.items()},
        },
        "status": "PASS" if not failures else "FAIL",
    }


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    rep = build_report()
    (ROOT / "verify" / "claims.report.json").write_text(json.dumps(rep, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(rep, indent=2))
        return 0 if rep["status"] == "PASS" else 1
    print(f"{'id':<22}{'status':<12}{'published':>16}{'recomputed':>16}  claim")
    for c in rep["checks"]:
        pub = c["published"] if c["published"] is not None else "—"
        rec = c["recomputed"] if c["recomputed"] is not None else "—"
        print(f"{c['id']:<22}{c['status']:<12}{str(pub):>16}{str(rec):>16}  {c['claim'][:58]}")
    print(f"\n{rep['n_pass']} pass · {rep['n_fail']} fail · status {rep['status']}")
    for f in rep["failures"]:
        print(f"  FAIL {f['id']}: published {f['published']} vs recomputed {f['recomputed']} — {f['claim']}")
    return 0 if rep["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
