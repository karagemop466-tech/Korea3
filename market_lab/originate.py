#!/usr/bin/env python3
"""Origination order: side first, then the total, then the moneyline.

The brief fixes the order in which the model originates its own markets:

    1. the side   (the spread)
    2. the total
    3. the moneyline

This module implements exactly that order and publishes the fair line for each market as a
separate, named value. The moneyline is originated **last** and is derived only from the
spread that step 1 already produced (and its uncertainty); it never reads the market
moneyline. That is what makes the order meaningful: the moneyline is a consequence of the
originated side, not an independent market read that could be tuned to hide a bad spread.

Fair-line definitions (all model-side, no market input):

* fair spread  = ``mu_spread``  (expected home margin, nflverse sign: + = home favoured)
* fair total   = ``mu_total``   (expected combined score)
* fair ML      = the American price implied by the model's home-win probability, which comes
  from the fair spread and its standard deviation:

      p_home = 1 - Phi((0 - mu_spread) / sd_spread) = Phi(mu_spread / sd_spread)
      fair_ml_home = -100 * p / (1 - p)   when p >= 0.5
                   =  100 * (1 - p) / p   when p <  0.5

The three fair lines are then compared to the three market lines on the
``fair_vs_market`` page; the difference is ``fair - market`` for each market.
"""
from __future__ import annotations

import math


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def fair_moneyline_from_prob(p: float) -> float:
    """American moneyline implied by a home-win probability ``p`` (no vig)."""
    p = min(max(float(p), 1e-6), 1.0 - 1e-6)
    if p >= 0.5:
        return -100.0 * p / (1.0 - p)
    return 100.0 * (1.0 - p) / p


def home_win_prob_from_spread(mu_spread: float, sd_spread: float) -> float:
    """Model home-win probability from the originated spread and its uncertainty."""
    if sd_spread is None or sd_spread <= 0:
        return 0.5
    return _phi(float(mu_spread) / float(sd_spread))


def originate_order(row: dict) -> dict:
    """Return the three fair lines in the mandated order.

    ``row`` must carry ``mu_spread``, ``sd_spread``, ``mu_total``. Missing or non-finite
    inputs yield a ``None`` fair line for that step (never a made-up number).
    """
    mu_spread = row.get("mu_spread")
    sd_spread = row.get("sd_spread")
    mu_total = row.get("mu_total")

    fair_spread = None
    fair_total = None
    fair_ml_home = None
    fair_ml_away = None
    p_home = None

    if mu_spread is not None and not (isinstance(mu_spread, float) and math.isnan(mu_spread)):
        fair_spread = float(mu_spread)
    if mu_total is not None and not (isinstance(mu_total, float) and math.isnan(mu_total)):
        fair_total = float(mu_total)

    # Step 3 depends on step 1: only originate the moneyline if the spread was originated.
    if fair_spread is not None and sd_spread is not None and not (
        isinstance(sd_spread, float) and math.isnan(sd_spread)
    ):
        p_home = home_win_prob_from_spread(fair_spread, float(sd_spread))
        fair_ml_home = fair_moneyline_from_prob(p_home)
        fair_ml_away = fair_moneyline_from_prob(1.0 - p_home)

    return {
        "step": 1,
        "order": ["side", "total", "moneyline"],
        "side": {
            "market": "SIDE",
            "fair_line": fair_spread,
            "inputs": ["mu_spread"],
        },
        "total": {
            "market": "TOTAL",
            "fair_line": fair_total,
            "inputs": ["mu_total"],
        },
        "moneyline": {
            "market": "MONEYLINE",
            "fair_line_home": fair_ml_home,
            "fair_line_away": fair_ml_away,
            "home_win_prob": p_home,
            "inputs": ["mu_spread", "sd_spread"],
            "derived_from": "side",
        },
    }


ORDER_RULE = (
    "The model originates its markets in a fixed order: (1) the side (spread), (2) the total, "
    "(3) the moneyline. The moneyline is originated last and is derived only from the spread "
    "produced in step 1 and its uncertainty; it never reads the market moneyline. Each fair line "
    "is published as a separate column and compared to the market line on the fair-vs-market page."
)
