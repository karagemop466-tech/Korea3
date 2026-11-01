#!/usr/bin/env python3
"""Market mechanics: odds conversion, de-vigging, model probabilities, settlement.

All formulas here are the pre-registered ones from docs/preregistration.md.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

EDGE_MIN = 0.03
PRICE_MIN = -125.0
PRICE_MAX = 400.0
EVAL_START, EVAL_END = 2006, 2025
HOLDOUT = (2023, 2024, 2025)


def american_to_decimal(price: float) -> float:
    price = float(price)
    return 1.0 + (price / 100.0 if price > 0 else 100.0 / abs(price))


def american_profit(price: float, stake: float = 1.0) -> float:
    price = float(price)
    return stake * (price / 100.0 if price > 0 else 100.0 / abs(price))


def price_ok(price: float) -> bool:
    return price is not None and not math.isnan(price) and PRICE_MIN <= price <= PRICE_MAX


def devig_two_way(p1: float, p2: float) -> tuple[float, float]:
    """Proportional (multiplicative) de-vig of two American prices."""
    i1, i2 = 1.0 / american_to_decimal(p1), 1.0 / american_to_decimal(p2)
    total = i1 + i2
    return i1 / total, i2 / total


def norm_cdf(x):
    return 0.5 * (1.0 + np.vectorize(math.erf)(x / math.sqrt(2.0)))


def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def spread_probs(mu: float, sigma: float, line: float, side: str) -> tuple[float, float, float]:
    """Win/loss/push probabilities for an ATS bet. `line` follows nflverse sign
    (positive = home favoured), home covers when result > line."""
    p_home = 1.0 - _phi((line - mu) / sigma)
    if float(line).is_integer():
        p_push = _phi((line + 0.5 - mu) / sigma) - _phi((line - 0.5 - mu) / sigma)
    else:
        p_push = 0.0
    p_home = max(min(p_home, 1.0), 0.0)
    p_push = max(min(p_push, 1.0), 0.0)
    p_fail = max(1.0 - p_home - p_push, 0.0)
    if side == "home":
        return p_home, p_fail, p_push
    return p_fail, p_home, p_push


def total_probs(mu: float, sigma: float, line: float, side: str) -> tuple[float, float, float]:
    p_over = 1.0 - _phi((line - mu) / sigma)
    if float(line).is_integer():
        p_push = _phi((line + 0.5 - mu) / sigma) - _phi((line - 0.5 - mu) / sigma)
    else:
        p_push = 0.0
    p_over = max(min(p_over, 1.0), 0.0)
    p_push = max(min(p_push, 1.0), 0.0)
    p_under = max(1.0 - p_over - p_push, 0.0)
    return (p_over, p_under, p_push) if side == "over" else (p_under, p_over, p_push)


def moneyline_probs(mu: float, sigma: float, side: str) -> tuple[float, float, float]:
    p_home = 1.0 - _phi((0.0 - mu) / sigma)
    p_home = max(min(p_home, 1.0), 0.0)
    return (p_home, 1.0 - p_home, 0.0) if side == "home" else (1.0 - p_home, p_home, 0.0)


def settle(row: pd.Series, market: str, side: str) -> int:
    """Return 1 win, 0 push/void, -1 loss using only the recorded final score."""
    if market == "ATS":
        m = row["result"] - row["spread_line"]
        if m == 0:
            return 0
        home_won = m > 0
        return 1 if (home_won and side == "home") or ((not home_won) and side == "away") else -1
    if market == "TOTAL":
        m = row["total"] - row["total_line"]
        if m == 0:
            return 0
        over = m > 0
        return 1 if (over and side == "over") or ((not over) and side == "under") else -1
    if market == "ML":
        if row["result"] == 0:
            return 0
        home_won = row["result"] > 0
        return 1 if (home_won and side == "home") or ((not home_won) and side == "away") else -1
    raise ValueError(market)


def market_prob(row: pd.Series, market: str) -> tuple[float, float]:
    """De-vigged (home/over, away/under) probabilities for the recorded market."""
    if market == "ATS":
        return devig_two_way(row["home_spread_odds"], row["away_spread_odds"])
    if market == "TOTAL":
        return devig_two_way(row["over_odds"], row["under_odds"])
    if market == "ML":
        return devig_two_way(row["home_moneyline"], row["away_moneyline"])
    raise ValueError(market)


def side_price(row: pd.Series, market: str, side: str) -> float:
    if market == "ATS":
        return row["home_spread_odds"] if side == "home" else row["away_spread_odds"]
    if market == "TOTAL":
        return row["over_odds"] if side == "over" else row["under_odds"]
    if market == "ML":
        return row["home_moneyline"] if side == "home" else row["away_moneyline"]
    raise ValueError(market)


def line_for(row: pd.Series, market: str) -> float:
    return row["spread_line"] if market == "ATS" else row["total_line"]


def pnl_for(price: float, outcome: int, stake: float = 1.0) -> float:
    if outcome == 0:
        return 0.0
    if outcome > 0:
        return american_profit(price, stake)
    return -stake
