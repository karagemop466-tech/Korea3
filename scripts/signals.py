"""signals.py — the tested signal family, backtested against real closing lines.

Protocol
--------
* Universe: every completed regular-season game 2000-2026 in model_dataset.csv
  (n = 6,827). A signal is a deterministic rule that names a side; it never uses
  information published after the closing line.
* Price: the actual recorded price for that side when the dataset has one,
  otherwise the documented standard -110 (see research/sources.md). The number of
  imputed prices is reported per signal so a reader can judge exposure.
* Push: stake returned; excluded from win-rate and ROI denominators, counted separately.
* Split: DISCOVERY = 2000-2015, CONFIRMATION = 2016-2026. Rules were written before
  either window was evaluated; a signal only becomes eligible for the leaderboard
  if it is positive in BOTH windows (gate G3).
* Multiplicity: every signal in this file is tested and reported, including the ones
  that look bad. The false-discovery-rate correction in gates.py runs across this
  entire family. Nothing is dropped for being unflattering.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from lib import (BREAKEVEN_110, boot_roi_ci, coinflip_pvalue, binom_pvalue_wrap,
                 payout_per_unit, skill_z, wilson_ci)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DER = os.path.join(ROOT, "data", "derived")

DISCOVERY = (2000, 2015)
CONFIRMATION = (2016, 2026)


def _prices(d: pd.DataFrame, market: str, side_is_home: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (price, imputed_flag) for each bet."""
    if market == "spread":
        a = d["home_spread_odds"].to_numpy(float)
        b = d["away_spread_odds"].to_numpy(float)
    elif market == "total":
        a = d["over_odds"].to_numpy(float)
        b = d["under_odds"].to_numpy(float)
    else:  # ml
        a = d["home_moneyline"].to_numpy(float)
        b = d["away_moneyline"].to_numpy(float)
    price = np.where(side_is_home, a, b)
    imputed = ~np.isfinite(price)
    price = np.where(imputed, -110.0, price)
    return price, imputed, a, b


def build_bets(d: pd.DataFrame, name: str, market: str, mask: np.ndarray,
               side: str, price_side: str | None = None) -> pd.DataFrame:
    """side: 'home' | 'away' | 'over' | 'under'. mask selects games."""
    g = d[mask].copy()
    if g.empty:
        return pd.DataFrame(columns=["signal", "game_id", "season", "week", "bet", "market",
                                     "price", "imputed_price", "stake", "profit", "result"])
    if side in ("home", "away"):
        side_is_home = np.full(len(g), side == "home")
    else:
        side_is_home = np.full(len(g), side == "over")   # over uses column a
    price, imputed, a, b = _prices(g, market, side_is_home)

    if market == "spread":
        ats = g["home_ats_margin"].to_numpy(float)
        own = ats if side == "home" else -ats
    elif market == "total":
        diff = g["total_score"].to_numpy(float) - g["total_line"].to_numpy(float)
        own = diff if side == "over" else -diff
    else:
        mg = g["margin"].to_numpy(float)
        own = mg if side == "home" else -mg
        # moneyline: any positive margin for your side wins; zero is a push
        own = np.where(own == 0, 0, own)

    result = np.where(own > 0, 1, np.where(own < 0, -1, 0))
    payout = np.array([payout_per_unit(p) for p in price])
    profit = np.where(result == 1, payout, np.where(result == -1, -1.0, 0.0))

    out = pd.DataFrame({
        "signal": name,
        "game_id": g["game_id"].to_numpy(),
        "season": g["season"].to_numpy(),
        "week": g["week"].to_numpy(),
        "bet": side,
        "market": market,
        "price": price,
        "imputed_price": imputed,
        "payout": payout,
        "profit": profit,
        "result": result,
    })
    return out


def _mask(d: pd.DataFrame, cond: pd.Series) -> np.ndarray:
    return cond.fillna(False).to_numpy(bool)


def signal_rules(d: pd.DataFrame) -> list[dict]:
    """The family. Each entry is written once, before evaluation."""
    S = []
    # ---- model-relative signals (our own line vs the closing line) -------------
    S.append(dict(id="S01", name="Own line vs close: 3+ pt edge", market="spread",
                  rule=lambda: (d["edge_spread"].abs() >= 3.0,
                                np.where(d["edge_spread"] > 0, "home", "away")),
                  rationale="Bet the side our own line rates 3+ points better than the closing spread.",
                  source="Our walk-forward model (scripts/model.py) + closing spread from the pinned dataset."))
    S.append(dict(id="S02", name="Own line vs close: 5+ pt edge", market="spread",
                  rule=lambda: (d["edge_spread"].abs() >= 5.0,
                                np.where(d["edge_spread"] > 0, "home", "away")),
                  rationale="Stricter version of S01; tests whether edge size carries information.",
                  source="Our walk-forward model + closing spread from the pinned dataset."))
    S.append(dict(id="S03", name="Own total vs close: 3+ pt edge", market="total",
                  rule=lambda: (d["edge_total"].abs() >= 3.0,
                                np.where(d["edge_total"] > 0, "home", "away")),
                  rationale="Bet over when our own total exceeds the closing total by 3+.",
                  source="Our walk-forward model + closing total from the pinned dataset."))
    # ---- situational signals --------------------------------------------------
    S.append(dict(id="S04", name="Home underdog in a divisional game", market="spread",
                  rule=lambda: ((d["div_game"] == 1) & (d["home_spread"] > 0), "home"),
                  rationale="Familiarity plus a short number; the classic 'division dogs bark' angle.",
                  source="div_game and spread from the pinned dataset."))
    S.append(dict(id="S05", name="Away team off a bye", market="spread",
                  rule=lambda: ((d["away_rest"] >= 13) & (d["home_rest"] < 13), "away"),
                  rationale="Extra preparation week for the road team.",
                  source="away_rest/home_rest from the pinned dataset (rest days, not an NFL publication)."))
    S.append(dict(id="S06", name="Fade the home team on a short week", market="spread",
                  rule=lambda: (d["home_short_week"] == 1, "away"),
                  rationale="6 or fewer rest days for the host.",
                  source="home_rest from the pinned dataset."))
    S.append(dict(id="S07", name="Bet large underdogs (7+)", market="spread",
                  rule=lambda: (d["abs_spread"] >= 7.0,
                                np.where(d["home_spread"] > 0, "home", "away")),
                  rationale="Whether big numbers are systematically shaded too far.",
                  source="Closing spread from the pinned dataset."))
    S.append(dict(id="S08", name="Bet small favourites (3 or less)", market="spread",
                  rule=lambda: (d["abs_spread"] <= 3.0,
                                np.where(d["home_spread"] < 0, "home", "away")),
                  rationale="Whether near-pick'em favourites are efficiently priced.",
                  source="Closing spread from the pinned dataset."))
    S.append(dict(id="S09", name="Rest edge of 4+ days to the home team", market="spread",
                  rule=lambda: (d["rest_diff"] >= 4, "home"),
                  rationale="Scheduling-rest differential, the most-cited situational factor.",
                  source="home_rest/away_rest from the pinned dataset."))
    S.append(dict(id="S10", name="Rest edge of 4+ days to the away team", market="spread",
                  rule=lambda: (d["rest_diff"] <= -4, "away"),
                  rationale="Mirror of S09 - reported so the family is not one-sided.",
                  source="home_rest/away_rest from the pinned dataset."))
    S.append(dict(id="S11", name="Divisional game: bet home", market="spread",
                  rule=lambda: (d["div_game"] == 1, "home"),
                  rationale="Base-rate check on divisional hosts.",
                  source="div_game from the pinned dataset."))
    # ---- totals signals -------------------------------------------------------
    S.append(dict(id="S12", name="Divisional unders", market="total",
                  rule=lambda: (d["div_game"] == 1, "under"),
                  rationale="Familiarity suppressing scoring.",
                  source="div_game and total_line from the pinned dataset."))
    S.append(dict(id="S13", name="Dome overs", market="total",
                  rule=lambda: (d["is_dome"] == 1, "over"),
                  rationale="Controlled environment, no wind.",
                  source="roof field from the pinned dataset (UNVERIFIED environment data)."))
    S.append(dict(id="S14", name="Wind 15+ mph: unders", market="total",
                  rule=lambda: ((d["outdoor"] == 1) & (d["wind"] >= 15), "under"),
                  rationale="Wind suppressing passing and kicking.",
                  source="wind field from the pinned dataset (UNVERIFIED, no source field)."))
    S.append(dict(id="S15", name="High totals (50+): unders", market="total",
                  rule=lambda: (d["total_line"] >= 50.0, "under"),
                  rationale="Whether the market overshoots on expected shoot-outs.",
                  source="Closing total from the pinned dataset."))
    S.append(dict(id="S16", name="Week 1 unders", market="total",
                  rule=lambda: (d["week"] == 1, "under"),
                  rationale="Offseason rust / vanilla game plans.",
                  source="week and total_line from the pinned dataset."))
    S.append(dict(id="S17", name="Thursday games: unders", market="total",
                  rule=lambda: (d["is_thursday"] == 1, "under"),
                  rationale="Short-week offenses.",
                  source="weekday and total_line from the pinned dataset."))
    # ---- moneyline signal -----------------------------------------------------
    S.append(dict(id="S18", name="Own line 5+ edge: moneyline the dog", market="ml",
                  rule=lambda: ((d["edge_spread"] * np.sign(-d["home_spread"]) <= -5.0) &
                                (d["home_spread"] != 0),
                                np.where(d["edge_spread"] > 0, "home", "away")),
                  rationale="When our line disagrees strongly with the market, take the whole price on the underdog side of that disagreement.",
                  source="Our walk-forward model + closing moneyline from the pinned dataset."))
    return S


def evaluate(bets: pd.DataFrame) -> dict:
    if bets.empty:
        return dict(n=0, wins=0, losses=0, pushes=0, win_rate=None, roi=None, avg_price=None,
                    breakeven=None, z=None, p=None, ci_low=None, ci_high=None,
                    coinflip_p=None, imputed_share=None, profit=None)
    b = bets[bets["result"] != 0]
    wins = int((b["result"] == 1).sum())
    losses = int((b["result"] == -1).sum())
    n = wins + losses
    profit = float(bets["profit"].sum())
    win_rate = wins / n if n else None
    be = float(np.mean([1 / (1 + p) for p in b["payout"]])) if n else None
    roi = float(b["profit"].mean()) if n else None
    ci = boot_roi_ci(b["profit"].to_numpy()) if n > 1 else (None, None)
    return dict(
        n=int(n), wins=wins, losses=losses, pushes=int((bets["result"] == 0).sum()),
        win_rate=win_rate,
        roi=roi,
        profit=profit,
        avg_price=float(b["price"].mean()) if n else None,
        breakeven=be,
        z=skill_z(wins, n, be) if n else None,
        p=binom_pvalue_wrap(wins, n, be) if n else None,
        ci_low=ci[0], ci_high=ci[1],
        coinflip_p=coinflip_pvalue(b["profit"].to_numpy()) if n else None,
        imputed_share=float(bets["imputed_price"].mean()),
    )


def main() -> None:
    d = pd.read_csv(os.path.join(DER, "model_dataset.csv"), low_memory=False)
    preds = pd.read_csv(os.path.join(DER, "model_predictions.csv"))
    key = ["game_id"]
    cols = ["game_id", "model_spread", "model_total", "edge_spread", "edge_total"]
    d = d.merge(preds[cols], on=key, how="inner")
    d = d[d["season"] >= DISCOVERY[0]].reset_index(drop=True)

    all_bets, rows, rules_meta = [], [], []
    for spec in signal_rules(d):
        mask, side = spec["rule"]()
        mask = np.asarray(mask, dtype=bool)
        side = np.asarray(side)
        # some rules return a single side string
        bet_rows = []
        sub = d[mask]
        sides = side[mask] if side.shape == mask.shape else np.full(len(sub), str(side))
        if len(sub) == 0:
            continue
        # build per-row with heterogeneous sides
        parts = []
        for s in pd.unique(sides):
            m2 = np.zeros(len(d), dtype=bool)
            idx = np.where(mask)[0]
            m2[idx[sides == s]] = True
            parts.append(build_bets(d, spec["id"], spec["market"], m2, s))
        frame = pd.concat(parts, ignore_index=True)
        all_bets.append(frame)

        full = evaluate(frame)
        disc = evaluate(frame[(frame.season >= DISCOVERY[0]) & (frame.season <= DISCOVERY[1])])
        conf = evaluate(frame[(frame.season >= CONFIRMATION[0]) & (frame.season <= CONFIRMATION[1])])
        per_season = frame[frame.result != 0].groupby("season")["profit"].agg(["sum", "count"])
        pos_years = int((per_season["sum"] > 0).sum())
        best_year_share = (float(per_season["sum"].max() / per_season["sum"].sum())
                           if per_season["sum"].sum() > 0 else None)

        row = {
            "id": spec["id"], "name": spec["name"], "market": spec["market"],
            "rationale": spec["rationale"], "source": spec["source"],
            "full": full, "discovery": disc, "confirmation": conf,
            "seasons_tested": int(per_season.shape[0]),
            "seasons_positive": pos_years,
            "best_season_profit_share": best_year_share,
            "mean_abs_edge_at_entry": (float((d.loc[mask, "edge_spread"].abs().mean()))
                                       if spec["market"] == "spread" and mask.any() else None),
        }
        rows.append(row)
        print(f"{spec['id']} {spec['name'][:44]:44s} n={full['n']:5d} win={full['win_rate']:.4f} "
              f"roi={full['roi']:+.4f} p={full['p']:.4g} disc={disc['roi'] if disc['roi'] is not None else float('nan'):+.4f} "
              f"conf={conf['roi'] if conf['roi'] is not None else float('nan'):+.4f}")

    bets = pd.concat(all_bets, ignore_index=True)
    bets.to_csv(os.path.join(DER, "signal_bets.csv"), index=False)
    with open(os.path.join(DER, "signal_results.json"), "w", encoding="utf-8") as fh:
        json.dump({"discovery": DISCOVERY, "confirmation": CONFIRMATION,
                   "n_universe": int(len(d)), "signals": rows}, fh, indent=2, default=float)

    # per-season profit matrix for the stability gate + site heat table
    per = (bets[bets.result != 0]
           .pivot_table(index="signal", columns="season", values="profit", aggfunc="sum")
           .round(2))
    per.to_csv(os.path.join(DER, "signal_by_season.csv"))
    print("\nuniverse:", len(d), "signals:", len(rows))


if __name__ == "__main__":
    main()
