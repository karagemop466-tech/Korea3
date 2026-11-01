"""props.py — player-prop combo framework.

HONEST SCOPE NOTE
-----------------
This project has NO verified player-prop line data. The NFL does not publish prop
prices; operators publish them behind their own accounts/apps. The pinned open
dataset contains no player-level box scores either. Therefore:

  * no measured prop correlation value is published here. Those cells stay blank.
  * what IS published is (a) the mechanism that forces a correlation sign,
    (b) the exact arithmetic that says how large a correlation has to be to beat
    the price, and (c) the settlement rule with a primary-source link.
  * every prop row is flagged UNVERIFIED on the site's Flagged for Review page.

The arithmetic below is exact and reproducible; the correlation values are not
claimed because they cannot be verified from an official source in this environment.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DER = os.path.join(ROOT, "data", "derived")


def breakeven_phi(price_a: float, price_b: float, p_a: float = 0.5, p_b: float = 0.5) -> float:
    """Smallest phi at which a 2-leg parlay priced off independent legs is EV-neutral."""
    dec = (1 + 100 / abs(price_a)) * (1 + 100 / abs(price_b))
    target = 1 / dec
    return float((target - p_a * p_b) / np.sqrt(p_a * (1 - p_a) * p_b * (1 - p_b)))


PROP_PAIRS = [
    {
        "id": "P01", "combo": "QB passing yards OVER + team total OVER",
        "leg_a": "QB passing yards over", "leg_b": "team total over",
        "expected_sign": "positive", "strength": "very strong",
        "mechanism": "Passing volume is the main driver of team scoring; the two legs share the same underlying possession-level cause.",
        "pricing_risk": "Operators bundle this as a same-game parlay and price the correlation in. The posted SGP price is normally worse than the independent calc.",
    },
    {
        "id": "P02", "combo": "RB rushing yards OVER + QB passing yards UNDER",
        "leg_a": "RB rushing yards over", "leg_b": "QB passing yards under",
        "expected_sign": "negative", "strength": "moderate",
        "mechanism": "Game script: a team protecting a lead runs and stops passing. Volume is split between the two legs.",
        "pricing_risk": "If a book prices these independently, a negative phi works FOR the bettor.",
    },
    {
        "id": "P03", "combo": "Two receivers on the SAME team, both OVER",
        "leg_a": "WR/TE A receiving yards over", "leg_b": "WR/TE B receiving yards over",
        "expected_sign": "negative", "strength": "weak to moderate",
        "mechanism": "Target and air-yard competition inside one passing offence; a big day for one tends to cap the other.",
        "pricing_risk": "Common in 'stack' style tickets. Books generally adjust; verify the posted price.",
    },
    {
        "id": "P04", "combo": "QB passing TDs OVER + own WR receiving TDs OVER",
        "leg_a": "QB passing TDs over", "leg_b": "same-team WR receiving TDs over",
        "expected_sign": "positive", "strength": "very strong",
        "mechanism": "One leg is literally a subset of the other's event stream.",
        "pricing_risk": "Redundant-leg tickets are usually either refused or heavily re-priced.",
    },
    {
        "id": "P05", "combo": "Team A total OVER + Team B total OVER (same game)",
        "leg_a": "away team total over", "leg_b": "home team total over",
        "expected_sign": "positive", "strength": "moderate",
        "mechanism": "Shared pace and weather environment; a fast game lifts both.",
        "pricing_risk": "This is the closest prop analogue to the spread x total pair we did measure, which was phi = +0.009 (indistinguishable from zero). Do not assume it is large.",
    },
    {
        "id": "P06", "combo": "Sacks or turnovers OVER + opponent QB passing yards UNDER",
        "leg_a": "team sacks over", "leg_b": "opponent QB passing yards under",
        "expected_sign": "negative", "strength": "moderate",
        "mechanism": "Pressure ends drives early; sack volume and passing volume trade off.",
        "pricing_risk": "Defensive props are thinner markets, so mispricing is more plausible - and so is being limited.",
    },
    {
        "id": "P07", "combo": "Kicker points OVER + game total OVER",
        "leg_a": "kicker points over", "leg_b": "game total over",
        "expected_sign": "positive", "strength": "weak",
        "mechanism": "More scoring means more kicking chances, but touchdowns bypass the kicker.",
        "pricing_risk": "Direction is right, magnitude is small and easily swallowed by vig.",
    },
    {
        "id": "P08", "combo": "Same player, two different props (e.g. yards + receptions)",
        "leg_a": "player market A over", "leg_b": "same player market B over",
        "expected_sign": "positive", "strength": "strong",
        "mechanism": "Same player, same opportunity set.",
        "pricing_risk": "Most operators reject or restrict correlated same-player legs.",
    },
]


def main() -> None:
    rows = []
    for p in PROP_PAIRS:
        be110 = breakeven_phi(-110, -110)
        be_plus = breakeven_phi(-110, 120)
        rows.append({**p,
                     "breakeven_phi_at_110_110": round(be110, 4),
                     "breakeven_phi_at_110_plus120": round(be_plus, 4),
                     "measured_phi": "",          # deliberately blank: no verifiable source
                     "verification_status": "UNVERIFIED",
                     "source": "Settlement rules: see research/sources.md (operator house rules). "
                               "Correlation value: no official source available in this environment."})
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(DER, "props_framework.csv"), index=False)

    # EV sensitivity grid: exact arithmetic, no data required
    grid = []
    for price_pair in [(-110, -110), (-120, -110), (-110, 120)]:
        for phi in (-0.30, -0.20, -0.10, 0.0, 0.05, 0.10, 0.15, 0.20, 0.30, 0.50, 0.67):
            for p in (0.5,):
                dec = (1 + 100 / abs(price_pair[0])) * (1 + 100 / abs(price_pair[1]))
                joint = p * p + phi * p * (1 - p)
                ev = joint * dec - 1
                grid.append({"price_a": price_pair[0], "price_b": price_pair[1],
                             "assumed_true_leg_rate": p, "phi": phi,
                             "parlay_decimal": round(dec, 4),
                             "true_joint_prob": round(float(joint), 5),
                             "ev_per_unit": round(float(ev), 4),
                             "ev_pct": round(float(ev) * 100, 2)})
    pd.DataFrame(grid).to_csv(os.path.join(DER, "props_ev_grid.csv"), index=False)

    meta = {
        "n_pairs_documented": len(PROP_PAIRS),
        "measured_values_published": 0,
        "reason": "No official or machine-readable player-prop line source is available in this environment.",
        "breakeven_phi_110_110": round(breakeven_phi(-110, -110), 4),
        "breakeven_phi_110_plus120": round(breakeven_phi(-110, 120), 4),
        "status": "UNVERIFIED - flagged for review",
    }
    with open(os.path.join(DER, "props_meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    print(df[["id", "combo", "expected_sign", "breakeven_phi_at_110_110"]].to_string(index=False))
    print(json.dumps(meta, indent=2))


if __name__ == "__main__":
    main()
