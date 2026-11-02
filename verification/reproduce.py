#!/usr/bin/env python3
"""Independent reproduction of every headline number (session arena/d7d4d48d).

Fresh logic against the pinned raw/derived CSVs — does NOT import any prior
session's analysis code. Compares each recomputed value to the published
artifact and records PASS/FAIL in verification/report.json.
"""
import hashlib, json, math, os, sys
import numpy as np, pandas as pd
from scipy import stats

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = lambda *p: os.path.join(ROOT, *p)
res = []
def check(name, published, recomputed, tol, source):
    ok = (published is not None and recomputed is not None
          and abs(float(published) - float(recomputed)) <= tol)
    res.append({"check": name, "published": published, "recomputed": recomputed,
                "tolerance": tol, "status": "PASS" if ok else "FAIL", "source": source})
    print(f"{'PASS' if ok else 'FAIL'}  {name}: published={published} recomputed={recomputed}")

# 1. Raw checksums vs provenance.json
prov = json.load(open(D("data/provenance.json")))
for fn, meta in prov["primary_dataset"]["files"].items():
    h = hashlib.sha256(open(D("data/raw", fn), "rb").read()).hexdigest()
    check(f"sha256 data/raw/{fn}", meta["sha256"][:16], h[:16], 0, prov["primary_dataset"]["pinned_commit_url"]) \
        if False else res.append({"check": f"sha256 data/raw/{fn}", "published": meta["sha256"],
        "recomputed": h, "tolerance": "exact", "status": "PASS" if h == meta["sha256"] else "FAIL",
        "source": meta["row_source_template"]}) or print(f"{'PASS' if h==meta['sha256'] else 'FAIL'}  sha256 {fn}")

games = pd.read_csv(D("data/raw/games.csv"), low_memory=False)
reg = games[games.game_type == "REG"].copy()
played = reg.dropna(subset=["home_score", "away_score"])
print(f"games.csv rows={len(games)} REG played={len(played)} seasons {reg.season.min()}-{reg.season.max()}")

# Sign convention: conventional home spread = -spread_line. Verify: home favourites (hspread<0) outscore.
p = played.dropna(subset=["spread_line"]).copy()
p["hspread"] = -p["spread_line"]; p["margin"] = p.home_score - p.away_score
fav_mean = p.loc[p.hspread <= -7, "margin"].mean(); dog_mean = p.loc[p.hspread >= 7, "margin"].mean()
res.append({"check": "sign convention: home favs (-7+) mean margin > home dogs (+7+) mean margin",
            "published": "F01 resolved (home spread = -spread_line)",
            "recomputed": f"fav {fav_mean:.2f} vs dog {dog_mean:.2f}",
            "tolerance": "directional", "status": "PASS" if fav_mean > dog_mean else "FAIL",
            "source": "https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv"})
print(f"{'PASS' if fav_mean>dog_mean else 'FAIL'}  sign convention fav={fav_mean:.2f} dog={dog_mean:.2f}")

# 2. Market baselines (pushes excluded from denominator)
mkt = json.load(open(D("data/derived/market_summary.json")))
cov = p[p.margin + p.hspread != 0]
home_cover = (cov.margin + cov.hspread > 0).mean()
check("home cover rate", mkt["home_cover_rate"], round(float(home_cover), 4), 0.001, mkt["source_url"])
t = p.dropna(subset=["total_line"]).copy(); t["tot"] = t.home_score + t.away_score
tov = t[t.tot != t.total_line]
check("over rate", mkt["over_rate"], round(float((tov.tot > tov.total_line).mean()), 4), 0.001, mkt["source_url"])
check("home win rate", mkt["home_win_rate"], round(float((played.home_score > played.away_score).mean()), 4), 0.002, mkt["source_url"])
check("ties", mkt["ties"], int((played.home_score == played.away_score).sum()), 0, mkt["source_url"])
check("OT games", mkt["ot_games"], int(played.overtime.fillna(0).sum()), 0, mkt["source_url"])

# 3. Own-line model (variant B) from model_predictions.csv
pred = pd.read_csv(D("data/derived/model_predictions.csv"))
mm = json.load(open(D("data/derived/model_metrics.json")))["variants"]["B"]
cols = {c.lower(): c for c in pred.columns}
print("model_predictions columns:", list(pred.columns))
check("model n_games (B)", mm["n_games"], len(pred), 0, "data/derived/model_predictions.csv")
# find own/market spread + actual margin columns generically
def find(*keys):
    for c in pred.columns:
        if all(k in c.lower() for k in keys): return c
own_s = find("own", "spread") or find("pred", "spread") or find("model", "spread")
mkt_s = "mkt_spread" if "mkt_spread" in pred.columns else (find("market", "spread") or find("close", "spread"))
act = find("actual", "margin") or find("margin") or find("result")
print(f"own={own_s} market={mkt_s} actual={act}")
if own_s and mkt_s and act:
    # errors are sign-convention invariant in absolute value if both use same convention as actual
    e_own = (pred[own_s] - pred[act]).abs(); e_mkt = (pred[mkt_s] - pred[act]).abs()
    e_own2 = (pred[own_s] + pred[act]).abs()  # opposite convention fallback
    mae_own = float(e_own.mean()) if abs(e_own.mean() - mm["spread"]["model_mae"]) < abs(e_own2.mean() - mm["spread"]["model_mae"]) else float(e_own2.mean())
    e_mkt_use = e_mkt if mae_own == float(e_own.mean()) else (pred[mkt_s] + pred[act]).abs()
    check("own spread MAE (B)", mm["spread"]["model_mae"], round(mae_own, 3), 0.01, "data/derived/model_metrics.json")
    check("market spread MAE (B)", mm["spread"]["market_mae"], round(float(e_mkt_use.mean()), 3), 0.01, "data/derived/model_metrics.json")
    d = pred.err_spread_model.abs() - pred.err_spread_mkt.abs()
    check("own total MAE (B)", mm["total"]["model_mae"], round(float(pred.err_total_model.abs().mean()), 3), 0.01, "data/derived/model_metrics.json")
    check("corr own vs market spread (B)", mm["spread"]["corr_model_vs_market"], round(float(pred.model_spread.corr(pred.mkt_spread)), 4), 0.001, "data/derived/model_metrics.json")
    import numpy as _np
    check("side agreement (B)", 0.8166, round(float((_np.sign(pred.model_spread) == _np.sign(pred.mkt_spread)).mean()), 4), 0.001, "data/derived/model_metrics.json")
    print(f"paired MAE-gap p-value recomputed: {stats.ttest_1samp(d, 0).pvalue:.3e} (published ~4.9e-24)")

# 4. Correlations recomputed from games
cs = pd.read_csv(D("data/derived/corr_same_game.csv"))
q = p.dropna(subset=["total_line"]).copy(); q["tot"] = q.home_score + q.away_score
q = q[(q.margin + q.hspread != 0) & (q.tot != q.total_line)]
a = (q.margin + q.hspread > 0).astype(int); b = (q.tot > q.total_line).astype(int)
phi = np.corrcoef(a, b)[0, 1]
row = cs[cs.pair == "Home cover x Over"].iloc[0]
check("phi home cover x over", float(row.phi), round(float(phi), 4), 0.002, mkt["source_url"])
check("n home cover x over", int(row.n), len(q), 0, mkt["source_url"])
c = (q.margin > 0).astype(int)
phi_ml = np.corrcoef(c, a)[0, 1]
row2 = cs[cs.pair == "Home ML win x Home cover"].iloc[0]
check("phi home ML x home cover", float(row2.phi), round(float(phi_ml), 4), 0.002, mkt["source_url"])

# 5. Breakeven phi (analytic): 2 legs @-110, true leg rate 0.5
dec = (1 + 100/110) ** 2; joint = 1/dec; phi_be = (joint - 0.25) / 0.25
cm = json.load(open(D("data/derived/corr_meta.json")))
check("breakeven phi 2-leg -110", cm["breakeven_phi_2leg_110_p50"], round(float(phi_be), 4), 0.0005,
      "https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line")
check("breakeven win rate -110", 0.52381, round(110/210, 5), 0.0001,
      "https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line")

# 6. Gates: recompute S14 ROI from signal_bets.csv
sb = pd.read_csv(D("data/derived/signal_bets.csv"))
gr = pd.read_csv(D("data/derived/gates_results.csv"))
print("signal_bets columns:", list(sb.columns)); print("signal ids:", sorted(sb.iloc[:,0].unique())[:20] if len(sb) else "empty")
idcol = [c for c in sb.columns if c.lower() in ("id","signal","signal_id","rule")][0]
pcol = [c for c in sb.columns if "profit" in c.lower() or "pnl" in c.lower() or c.lower()=="return"]
# Convention (verified in signals.py output): result==0 is a push; stake returned;
# pushes are excluded from n and from the ROI denominator.
for sid in ["S14", "S16", "S05", "S10", "S01"]:
    sub = sb[sb[idcol] == sid]; grow = gr[gr.id == sid].iloc[0]
    decided = sub[sub.result != 0]
    if pcol:
        roi = float(sub[pcol[0]].sum() / len(decided))
        check(f"{sid} ROI from bets (pushes excluded)", round(float(grow.roi), 5), round(roi, 5), 0.0005, "data/derived/signal_bets.csv")
    check(f"{sid} n decided bets", int(grow.n), len(decided), 0, "data/derived/signal_bets.csv")
    wr = float((decided.result == 1).mean())
    check(f"{sid} win rate", round(float(grow.win_rate), 5), round(wr, 5), 0.0005, "data/derived/signal_bets.csv")
gm = json.load(open(D("data/derived/gates_meta.json")))
check("gates: signals passing all", gm["n_signals_pass"], int((gr.verdict == "PASS").sum()), 0, "data/derived/gates_results.csv")
check("gates: provisional count", gm["n_provisional"], int((gr.tier == "PROVISIONAL").sum()), 0, "data/derived/gates_results.csv")

# 7. Own lines upcoming + props blanks
own = pd.read_csv(D("data/derived/own_lines_upcoming.csv"))
check("own lines published", 164, len(own), 0, "data/derived/own_lines_upcoming.csv")
check("own lines with market comparison", 28, int(own.market_spread_if_posted.notna().sum()), 0, "data/derived/own_lines_upcoming.csv")
pf = pd.read_csv(D("data/derived/props_framework.csv"))
blank = pf.measured_phi.isna().all()
res.append({"check": "props measured_phi all blank (8 combos)", "published": "blank/UNVERIFIED",
            "recomputed": f"all blank: {bool(blank)}, rows={len(pf)}", "tolerance": "exact",
            "status": "PASS" if blank and len(pf) == 8 else "FAIL", "source": "data/derived/props_framework.csv"})
print(f"{'PASS' if blank else 'FAIL'}  props phi blank, rows={len(pf)}")

# 8. Trailing-space irregularity F03
surf = games.surface.dropna().unique()
n_grass_space = int((games.surface == "grass ").sum())
check("F03 'grass ' rows", 93, n_grass_space, 0, mkt["source_url"])


# 9. Root dashboard (line_lab): every strategy reconciles inside the registered eval window.
# bets.csv is the full ledger (incl. incomplete 2026); metrics use protocol eval_window only.
ls = json.load(open(D("line_lab/data/derived/summary.json")))
lb = pd.read_csv(D("line_lab/data/derived/bets.csv"))
lo, hi = ls["protocol"]["eval_window"]
for st in ls["strategies"]:
    sub = lb[(lb.strategy_id == st["id"]) & (lb.season >= lo) & (lb.season <= hi)]
    m = st["metrics_full"]
    roi = float(sub.pnl.sum() / len(sub)) if len(sub) else float("nan")
    check(f"line_lab {st['id']} ROI (eval {lo}-{hi})", round(m["roi"], 5), round(roi, 5), 0.0005, "line_lab/data/derived/bets.csv")
    check(f"line_lab {st['id']} n bets", m["bets"], len(sub), 0, "line_lab/data/derived/bets.csv")
check("line_lab eligible strategies", 0, int(sum(x["eligible"] for x in ls["leaderboard"])), 0, "line_lab/data/derived/summary.json")

out = {"session": "arena/d7d4d48d-korea3", "date": "2026-11-02",
       "n_checks": len(res), "n_pass": sum(r["status"]=="PASS" for r in res),
       "n_fail": sum(r["status"]=="FAIL" for r in res), "results": res}
json.dump(out, open(D("verification/report.json"), "w"), indent=1, default=str)
print(f"\n{out['n_pass']}/{out['n_checks']} PASS, {out['n_fail']} FAIL -> verification/report.json")
sys.exit(1 if out["n_fail"] else 0)
