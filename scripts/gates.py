"""gates.py — validation gates, luck removal and the leaderboard.

Eight mandatory gates. A strategy is published as PASS only if all eight pass.
Any gate that cannot be evaluated for lack of a source is reported as NEEDS REVIEW,
never as a pass.

  G1  Sample size             n >= 200 settled bets overall and >= 100 in confirmation
  G2  Positive expectation    ROI > 0 over the full window
  G3  Both-window stability   ROI > 0 in DISCOVERY (2000-2015) AND CONFIRMATION (2016-2026)
  G4  Multiplicity            Benjamini-Hochberg q <= 0.10 across the whole tested family
  G5  Concentration           no single season > 50% of total profit; >= 50% of seasons positive
  G6  Price stress            still profitable if every bet were priced at -115
  G7  Line-source robustness  still profitable scored against the second in-dataset line source
  G8  Luck-adjusted edge      empirical-Bayes shrunk ROI >= 0.5% (the economic bar)

Luck removal, in plain terms:
  * p / q values answer "could a break-even bettor have done this by chance?"
  * the coin-flip Monte Carlo answers the same question by simulation.
  * the empirical-Bayes shrinkage answers "how much of this edge survives once we
    admit we tested many rules and most edges are noise?" -- it is the number the
    leaderboard uses, because it is the only one that is not flattered by luck.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd
from scipy import stats

from lib import bh_fdr, boot_roi_ci, empirical_bayes_tau2, payout_per_unit, shrink_edge, required_n

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DER = os.path.join(ROOT, "data", "derived")
FDR_ALPHA = 0.10
MIN_N = 200
MIN_N_CONF = 100
ECON_BAR = 0.005


def _roi_at(profits: np.ndarray, fixed_odds: float) -> float:
    """Re-price the same results at a fixed American price."""
    pay = payout_per_unit(fixed_odds)
    return float(np.where(profits > 0, pay, profits).mean())


def second_source_results(bets: pd.DataFrame, data: pd.DataFrame) -> pd.DataFrame:
    """Re-score every bet against the second in-dataset line source (closing_lines.csv)."""
    cl = pd.read_csv(os.path.join(ROOT, "data", "raw", "closing_lines.csv"))
    alt = cl.pivot_table(index="alt_game_id", columns=["type", "side"], values="line", aggfunc="first")
    rows = []

    def pick(kind, side):
        try:
            return alt[(kind, side)]
        except KeyError:
            return pd.Series(dtype=float)

    sp = cl[cl.type == "SPREAD"].copy()
    home_line = {}
    for _, r in sp.iterrows():
        home_line.setdefault(r["alt_game_id"], {})[r["side"]] = r["line"]
    tot = {}
    for _, r in cl[cl.type == "TOTAL"].iterrows():
        if str(r["side"]).lower() in ("over", "under"):
            tot.setdefault(r["alt_game_id"], r["line"])
    ml = {}
    for _, r in cl[cl.type == "MONEYLINE"].iterrows():
        ml.setdefault(r["alt_game_id"], {})[r["side"]] = r["odds"]

    # alt_game_id -> game_id mapping happens through data (data has game_id)
    d = data.set_index("game_id")
    for _, b in bets.iterrows():
        g = d.loc[b["game_id"]]
        alt_id = f"{int(g['season'])}_{int(g['week']):02d}_{g['away_team']}_{g['home_team']}"
        hint = home_line.get(alt_id)
        tref = tot.get(alt_id)
        mref = ml.get(alt_id)
        res = np.nan
        try:
            if b["market"] == "spread" and hint and g["home_team"] in hint:
                hl = hint[g["home_team"]]                    # conventional home spread
                ats = g["margin"] + hl
                own = ats if b["bet"] == "home" else -ats
                res = 1 if own > 0 else (-1 if own < 0 else 0)
            elif b["market"] == "total" and tref is not None and np.isfinite(tref):
                diff = g["total_score"] - tref
                own = diff if b["bet"] == "over" else -diff
                res = 1 if own > 0 else (-1 if own < 0 else 0)
            elif b["market"] == "ml" and mref and g["home_team"] in mref:
                price = mref[g["home_team"]] if b["bet"] == "home" else mref.get(g["away_team"])
                if price is not None and np.isfinite(price):
                    mg = g["margin"] if b["bet"] == "home" else -g["margin"]
                    res = 0 if mg == 0 else (1 if mg > 0 else -1)
                    b = b.copy(); b["price"] = float(price)
        except Exception:
            res = np.nan
        if np.isfinite(res):
            pay = payout_per_unit(b["price"])
            rows.append({"game_id": b["game_id"], "signal": b["signal"],
                         "profit_alt": pay if res == 1 else (-1.0 if res == -1 else 0.0)})
    return pd.DataFrame(rows)


def main() -> None:
    bets = pd.read_csv(os.path.join(DER, "signal_bets.csv"))
    with open(os.path.join(DER, "signal_results.json"), encoding="utf-8") as fh:
        SR = json.load(fh)
    data = pd.read_csv(os.path.join(DER, "model_dataset.csv"), low_memory=False)

    alt = second_source_results(bets, data)

    # ---- family-level luck statistics --------------------------------------
    sigs = SR["signals"]
    pvals = [s["full"]["p"] for s in sigs]
    qvals, rejected = bh_fdr(pvals, FDR_ALPHA)

    rois = np.array([s["full"]["roi"] for s in sigs], float)
    ns = np.array([s["full"]["n"] for s in sigs], float)
    # standard error of ROI per signal, from the bet-level profit series
    ses = []
    for s in sigs:
        b = bets[(bets.signal == s["id"]) & (bets.result != 0)]
        ses.append(float(b["profit"].std(ddof=1) / np.sqrt(len(b))) if len(b) > 1 else np.nan)
    ses = np.array(ses, float)
    # include the alternative hypothesis of 0 edge: shrinkage is toward zero ROI
    tau2 = empirical_bayes_tau2(rois, ses)

    out_rows = []
    for i, s in enumerate(sigs):
        b_all = bets[(bets.signal == s["id"])]
        b = b_all[b_all.result != 0]
        alt_b = alt[alt.signal == s["id"]] if not alt.empty else pd.DataFrame()

        g1 = (s["full"]["n"] >= MIN_N) and (s["confirmation"]["n"] >= MIN_N_CONF)
        g2 = (s["full"]["roi"] or -1) > 0
        g3 = ((s["discovery"]["roi"] or -1) > 0) and ((s["confirmation"]["roi"] or -1) > 0)
        g4 = bool(qvals[i] <= FDR_ALPHA)
        conc_ok = (s["best_season_profit_share"] is None) or (s["best_season_profit_share"] <= 0.50)
        seas_ok = (s["seasons_tested"] > 0) and (s["seasons_positive"] / s["seasons_tested"] >= 0.50)
        g5 = conc_ok and seas_ok
        roi_115 = _roi_at(b["profit"].to_numpy(), -115.0)
        g6 = roi_115 > 0
        if len(alt_b) >= 100:
            roi_alt = float(alt_b["profit_alt"].mean())
            g7 = roi_alt > 0
            g7_status = "pass" if g7 else "fail"
        else:
            roi_alt = None
            g7 = None
            g7_status = "needs_review_insufficient_second_source"
        shrunk = shrink_edge(s["full"]["roi"], ses[i], tau2)
        g8 = shrunk >= ECON_BAR

        gates = {"G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": g5, "G6": g6, "G8": g8}
        if g7 is None:
            verdict = "NEEDS REVIEW"
        elif all(gates.values()) and g7:
            verdict = "PASS"
        else:
            verdict = "FAIL"

        failed = [k for k, v in gates.items() if not v]
        if g7 is False:
            failed.append("G7")

        # Promotion tiers. PASS is the only tier that earns a leaderboard slot.
        # PROVISIONAL = 7 of 8 gates cleared and statistically clean, waiting on sample.
        n_failed = len(failed)
        if verdict == "PASS":
            tier = "PASS"
        elif (verdict == "FAIL") and n_failed == 1 and failed == ["G4"] and g8 and (s["confirmation"]["roi"] or -1) > 0:
            tier = "PROVISIONAL"
        else:
            tier = "FAIL"

        # How much more evidence would it take? z needed for q<=0.10 with m tests is
        # approximately norm.ppf(1 - 0.10/m); converted to a bet count.
        z_need = float(stats.norm.ppf(1 - FDR_ALPHA / len(sigs)))
        sigma_bet = (ses[i] * np.sqrt(max(s["full"]["n"], 1))) if np.isfinite(ses[i]) else np.nan
        need_obs = (int(np.ceil((z_need * sigma_bet / s["full"]["roi"]) ** 2))
                    if (s["full"]["roi"] or 0) > 0 and np.isfinite(sigma_bet) else None)
        need_shrunk = (int(np.ceil((z_need * sigma_bet / shrunk) ** 2))
                       if shrunk > 0 and np.isfinite(sigma_bet) else None)

        out_rows.append({
            "id": s["id"], "name": s["name"], "market": s["market"],
            "n": s["full"]["n"], "n_conf": s["confirmation"]["n"],
            "win_rate": s["full"]["win_rate"], "roi": s["full"]["roi"],
            "roi_disc": s["discovery"]["roi"], "roi_conf": s["confirmation"]["roi"],
            "ci_low": s["full"]["ci_low"], "ci_high": s["full"]["ci_high"],
            "p": s["full"]["p"], "q": qvals[i],
            "coinflip_p": s["full"]["coinflip_p"],
            "roi_minus115": roi_115,
            "roi_second_source": roi_alt,
            "se_roi": ses[i], "shrunk_roi": shrunk,
            "best_season_share": s["best_season_profit_share"],
            "seasons_positive": s["seasons_positive"], "seasons_tested": s["seasons_tested"],
            "G1": g1, "G2": g2, "G3": g3, "G4": g4, "G5": g5, "G6": g6,
            "G7": g7_status, "G8": g8,
            "gates_failed": ",".join(failed) if failed else "",
            "verdict": verdict,
            "tier": tier,
            "n_failed_gates": n_failed,
            "n_needed_at_observed_edge": need_obs,
            "n_needed_at_shrunk_edge": need_shrunk,
            "extra_bets_needed_at_observed_edge": (need_obs - s["full"]["n"]) if need_obs else None,
            "imputed_price_share": s["full"]["imputed_share"],
            "rationale": s["rationale"], "source": s["source"],
        })

    # leaderboard order: tier first (PASS > PROVISIONAL > FAIL), then luck-adjusted edge
    order = {"PASS": 0, "PROVISIONAL": 1, "FAIL": 2}
    res = pd.DataFrame(out_rows)
    res["_o"] = res["tier"].map(order)
    res = res.sort_values(["_o", "shrunk_roi"], ascending=[True, False]).drop(columns="_o").reset_index(drop=True)
    res["rank"] = np.arange(1, len(res) + 1)
    res.to_csv(os.path.join(DER, "gates_results.csv"), index=False)

    meta = {
        "fdr_alpha": FDR_ALPHA, "min_n": MIN_N, "min_n_conf": MIN_N_CONF, "econ_bar": ECON_BAR,
        "tau2_family": tau2, "family_size": len(sigs),
        "n_signals_pass": int((res.verdict == "PASS").sum()),
        "n_signals_needs_review": int((res.verdict == "NEEDS REVIEW").sum()),
        "n_signals_fail": int((res.verdict == "FAIL").sum()),
        "n_provisional": int((res.tier == "PROVISIONAL").sum()),
        "mean_observed_edge": float(np.nanmean(rois)),
        "mean_se": float(np.nanmean(ses)),
        "mean_shrunk_edge": float(np.nanmean(res.shrunk_roi)),
        "pct_shrink": float(1 - np.nanmean(res.shrunk_roi) / np.nanmean(rois)) if np.nanmean(rois) else None,
        "discovery": SR["discovery"], "confirmation": SR["confirmation"],
        "universe": SR["n_universe"],
        "bh_rejected": int(sum(rejected)),
    }
    with open(os.path.join(DER, "gates_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2, default=float)
    print(json.dumps(meta, indent=2))
    print(res[["rank", "id", "name", "n", "roi", "roi_conf", "p", "q", "shrunk_roi", "verdict"]]
          .to_string(index=False))


if __name__ == "__main__":
    main()
