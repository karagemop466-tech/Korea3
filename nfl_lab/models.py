"""Causal line-origination and player-prop distribution models.

These are research specifications.  They emit nothing unless admitted, licensed,
officially evidenced inputs exist.  Synthetic tests exercise the code only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import numpy as np
from sklearn.linear_model import Ridge

from .contracts import ContractError, Game, finite, probability, utc


@dataclass(frozen=True)
class LineDistribution:
    game_id: str
    as_of: str
    home: str
    away: str
    margin_mean: float
    margin_sd: float
    total_mean: float
    total_sd: float
    fair_home_spread: float
    fair_total: float
    p_home_win: float
    p_tie: float
    n_train: int
    model_version: str

    def to_dict(self):
        return self.__dict__.copy()


class TeamLineModel:
    """Expanding-window ridge rating with empirical residual distributions.

    Features are one-hot home/away team identities plus a home intercept.  The
    same design predicts margin and total.  Residuals from the training window
    form an empirical predictive distribution; no future game enters the fit.
    """
    version = "team-ridge-empirical-v1"

    def __init__(self, alpha: float = 10.0, min_games: int = 160):
        if alpha <= 0 or min_games < 20:
            raise ContractError("Invalid model settings")
        self.alpha = alpha
        self.min_games = min_games

    def _design(self, games: list[Game], teams: list[str]) -> np.ndarray:
        index = {t: i for i, t in enumerate(teams)}
        x = np.zeros((len(games), 2 * len(teams) + 1))
        x[:, -1] = 1.0
        for i, g in enumerate(games):
            x[i, index[g.home]] = 1.0
            x[i, len(teams) + index[g.away]] = 1.0
        return x

    def originate(self, history: list[Game], home: str, away: str, as_of: str, game_id: str) -> LineDistribution:
        cutoff = utc(as_of)
        train = sorted([g for g in history if utc(g.kickoff) < cutoff], key=lambda g: (utc(g.kickoff), g.game_id))
        if len(train) < self.min_games:
            raise ContractError(f"Need >= {self.min_games} admitted historical games")
        teams = sorted({g.home for g in train} | {g.away for g in train} | {home, away})
        x = self._design(train, teams)
        y_margin = np.array([g.margin for g in train], float)
        y_total = np.array([g.total for g in train], float)
        margin_model = Ridge(alpha=self.alpha, fit_intercept=False).fit(x, y_margin)
        total_model = Ridge(alpha=self.alpha, fit_intercept=False).fit(x, y_total)
        idx = {t: i for i, t in enumerate(teams)}
        z = np.zeros((1, 2 * len(teams) + 1))
        z[0, idx[home]] = 1.0
        z[0, len(teams) + idx[away]] = 1.0
        z[0, -1] = 1.0
        mu_m = float(margin_model.predict(z)[0])
        mu_t = float(total_model.predict(z)[0])
        resid_m = y_margin - margin_model.predict(x)
        resid_t = y_total - total_model.predict(x)
        sd_m = float(np.std(resid_m, ddof=1))
        sd_t = float(np.std(resid_t, ddof=1))
        if sd_m <= 0 or sd_t <= 0:
            raise ContractError("Degenerate residual distribution")
        # Empirical residual quantiles preserve discrete score structure better
        # than a normal approximation for push-heavy integer lines.
        margin_samples = mu_m + resid_m
        total_samples = np.maximum(0.0, mu_t + resid_t)
        fair_spread = -float(np.quantile(margin_samples, 0.5))
        fair_total = float(np.quantile(total_samples, 0.5))
        p_home = float(np.mean(margin_samples > 0))
        p_tie = float(np.mean(margin_samples == 0))
        return LineDistribution(game_id, as_of, home, away, mu_m, sd_m, mu_t, sd_t,
                                fair_spread, fair_total, p_home, p_tie, len(train), self.version)

    def cover_probability(self, distribution_samples: Iterable[float], home_spread: float) -> dict:
        samples = np.asarray(list(distribution_samples), float)
        if samples.size == 0:
            raise ContractError("Empty predictive distribution")
        adjusted = samples + finite(home_spread, "home_spread")
        return {"win": float(np.mean(adjusted > 0)), "push": float(np.mean(adjusted == 0)),
                "loss": float(np.mean(adjusted < 0))}


@dataclass(frozen=True)
class PlayerGame:
    player_id: str
    game_id: str
    kickoff: str
    team: str
    opponent: str
    position: str
    market: str
    value: float
    participated: bool
    evidence_id: str
    source_url: str

    def __post_init__(self):
        finite(self.value, "value")
        if self.value < 0:
            raise ContractError("Counting stat cannot be negative")
        utc(self.kickoff)
        if not self.player_id or not self.market or not self.evidence_id:
            raise ContractError("Player log requires identity, market and evidence")


class PlayerPropModel:
    """Participation mixture plus recency-weighted empirical production.

    P(over) = P(participates) * P(over | participates).  Non-participation is
    routed to the operator's void rule, not silently treated as an under.
    Shrinkage toward the position pool stabilizes small player samples.
    """
    version = "player-mixture-empirical-v1"

    def __init__(self, half_life_games: float = 8.0, prior_weight: float = 4.0, min_player_games: int = 3):
        if half_life_games <= 0 or prior_weight < 0 or min_player_games < 1:
            raise ContractError("Invalid player model settings")
        self.half_life = half_life_games
        self.prior_weight = prior_weight
        self.min_player_games = min_player_games

    def forecast(self, logs: list[PlayerGame], player_id: str, market: str, line: float,
                 as_of: str, position: str | None = None) -> dict:
        cutoff = utc(as_of)
        prior = [r for r in logs if utc(r.kickoff) < cutoff and r.market == market]
        player = sorted([r for r in prior if r.player_id == player_id], key=lambda r: (utc(r.kickoff), r.game_id))
        if len(player) < self.min_player_games:
            raise ContractError("Insufficient admitted player history")
        if position:
            pool = [r for r in prior if r.position == position]
            if not pool:
                raise ContractError("No position pool")
        else:
            pool = prior
        # Beta(1,1) participation prior; production prior from position pool.
        played = [r for r in player if r.participated]
        p_part = (1 + len(played)) / (2 + len(player))
        if not played:
            return {"player_id": player_id, "market": market, "line": line, "as_of": as_of,
                    "p_participate": p_part, "p_over": 0.0, "p_under": 0.0, "p_push": 0.0,
                    "p_void": 1 - p_part, "n_player": len(player), "model_version": self.version}
        ages = np.arange(len(played) - 1, -1, -1)
        weights = 0.5 ** (ages / self.half_life)
        values = np.array([r.value for r in played])
        pool_values = np.array([r.value for r in pool if r.participated])
        if pool_values.size == 0:
            raise ContractError("No participated production in pool")
        # Mixture empirical CDF: weighted player outcomes plus position prior.
        w = weights / weights.sum()
        prior_w = self.prior_weight / (self.prior_weight + 1.0)
        cdf_over = (1 - prior_w) * float(np.sum(w * (values > line))) + prior_w * float(np.mean(pool_values > line))
        cdf_push = (1 - prior_w) * float(np.sum(w * (values == line))) + prior_w * float(np.mean(pool_values == line))
        cdf_under = (1 - prior_w) * float(np.sum(w * (values < line))) + prior_w * float(np.mean(pool_values < line))
        return {"player_id": player_id, "market": market, "line": line, "as_of": as_of,
                "p_participate": p_part, "p_over": p_part * cdf_over, "p_under": p_part * cdf_under,
                "p_push": p_part * cdf_push, "p_void": 1 - p_part,
                "n_player": len(player), "n_pool": len(pool), "model_version": self.version}


def joint_from_scenarios(scenarios: np.ndarray, thresholds: list[float]) -> dict:
    """Joint over probability from aligned scenario samples.

    Rows are joint game/player scenarios; columns are leg statistics.  This
    preserves empirical dependence instead of multiplying marginal probabilities.
    """
    x = np.asarray(scenarios, float)
    if x.ndim != 2 or x.shape[0] < 2 or x.shape[1] != len(thresholds) or len(thresholds) < 2:
        raise ContractError("Need aligned scenarios for at least two legs")
    if not np.all(np.isfinite(x)):
        raise ContractError("Non-finite scenario")
    hits = x > np.asarray(thresholds, float)
    marginals = hits.mean(axis=0)
    joint = hits.all(axis=1).mean()
    return {"n_scenarios": int(x.shape[0]), "marginals": marginals.tolist(),
            "joint_over": float(joint), "independent_over": float(np.prod(marginals)),
            "dependence_lift": float(joint - np.prod(marginals))}
