"""summary.py — league baselines and market summary tables for the site."""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from lib import BREAKEVEN_110, row_source_url

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DER = os.path.join(ROOT, "data", "derived")


def main() -> None:
    d = pd.read_csv(os.path.join(DER, "model_dataset.csv"), low_memory=False)
    rows = []
    for s, g in d.groupby("season"):
        rows.append({
            "season": int(s),
            "games": int(len(g)),
            "mean_total_points": round(float(g.total_score.mean()), 2),
            "mean_closing_total": round(float(g.total_line.mean()), 2),
            "mean_abs_margin": round(float(g.margin.abs().mean()), 2),
            "mean_margin_home": round(float(g.margin.mean()), 2),
            "home_cover_rate": round(float(g.home_cover.dropna().mean()), 4),
            "over_rate": round(float(g.over.dropna().mean()), 4),
            "push_rate_spread": round(float(g.push.mean()), 4),
            "push_rate_total": round(float(g.total_push.mean()), 4),
            "ot_rate": round(float(g.overtime.mean()), 4),
            "tie_rate": round(float(g.tie.mean()), 4),
            "priced_games": int(g.home_spread_odds.notna().sum()),
            "row_source": row_source_url("games.csv"),
        })
    per = pd.DataFrame(rows)
    per.to_csv(os.path.join(DER, "league_baselines.csv"), index=False)

    summary = {
        "n_games": int(len(d)),
        "seasons": [int(d.season.min()), int(d.season.max())],
        "breakeven_win_rate_110": round(BREAKEVEN_110, 6),
        "home_cover_rate": round(float(d.home_cover.dropna().mean()), 4),
        "home_cover_n": int(d.home_cover.notna().sum()),
        "over_rate": round(float(d.over.dropna().mean()), 4),
        "over_n": int(d.over.notna().sum()),
        "home_win_rate": round(float(d.home_win.mean()), 4),
        "push_rate_spread": round(float(d.push.mean()), 4),
        "push_rate_total": round(float(d.total_push.mean()), 4),
        "ot_rate": round(float(d.overtime.mean()), 4),
        "ot_games": int(d.overtime.sum()),
        "tie_rate": round(float(d.tie.mean()), 4),
        "ties": int(d.tie.sum()),
        "mean_total_points": round(float(d.total_score.mean()), 2),
        "mean_margin_home": round(float(d.margin.mean()), 2),
        "mean_abs_margin": round(float(d.margin.abs().mean()), 2),
        "games_with_all_prices": int((d.home_spread_odds.notna() & d.over_odds.notna()).sum()),
        "pct_prices_imputed": round(1 - float(d.home_spread_odds.notna().mean()), 4),
        "neutral_site_games": int((d.location == "Neutral").sum()),
        "dome_games": int((d.is_dome == 1).sum()),
        "divisional_games": int((d.div_game == 1).sum()),
        "thursday_games": int(d.is_thursday.sum()),
        "source_url": row_source_url("games.csv"),
    }
    with open(os.path.join(DER, "market_summary.json"), "w", encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2)
    print(json.dumps(summary, indent=2))
    print(per.tail(6).to_string(index=False))


if __name__ == "__main__":
    main()
