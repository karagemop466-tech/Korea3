"""Pre-registered strategy hypotheses. No empirical edge is asserted."""
from __future__ import annotations

STRATEGIES = [
    {
        "id": "V01", "name": "Single-game spread distribution", "category": "Single bet",
        "hypothesis": "A causal team-rating distribution may identify spread mispricing after vig and execution costs.",
        "signal": "Model cover probability minus de-vigged market probability at the same timestamp and line.",
        "model": "Expanding-window ridge team ratings; empirical residual distribution; no market features in the origination model.",
        "required": ["Licensed official game results", "Timestamped executable spread quotes", "Archived spread settlement rules"],
        "failure_modes": ["Market already prices the information", "Residual distribution misses key-number mass", "Quote is not executable"],
        "status": "unvalidated", "source_id": "nfl_stats",
    },
    {
        "id": "V02", "name": "Single-game total distribution", "category": "Single bet",
        "hypothesis": "Pace and scoring-efficiency distributions may improve total forecasts relative to a timestamped market baseline.",
        "signal": "Model over probability minus de-vigged market over probability at the same total.",
        "model": "Team total ridge ratings plus empirical residual distribution; later extensions may add verified pace, weather and availability.",
        "required": ["Licensed official game results", "Timestamped executable total quotes", "Archived total settlement rules"],
        "failure_modes": ["Weather timestamp leakage", "Overtime distribution shift", "Total line movement after forecast"],
        "status": "unvalidated", "source_id": "dk_market_rules",
    },
    {
        "id": "V03", "name": "Moneyline calibration", "category": "Single bet",
        "hypothesis": "A calibrated win/tie/loss distribution may reveal moneyline price errors after accounting for pushes.",
        "signal": "Expected net return at the executable two-way price, with tie probability modeled explicitly.",
        "model": "Empirical margin distribution from the team model; three-way prices require a separate draw selection.",
        "required": ["Licensed official game results", "Timestamped executable moneyline quotes", "Archived moneyline settlement rules"],
        "failure_modes": ["Tie handling differs by market", "Favorite-longshot bias is not stable", "Vig removal assumption is wrong"],
        "status": "unvalidated", "source_id": "dk_market_rules",
    },
    {
        "id": "V04", "name": "Player participation mixture", "category": "Player prop",
        "hypothesis": "Separating participation from conditional production may reduce prop calibration error.",
        "signal": "Participation-weighted over/under/push probabilities compared with the operator's line and void rule.",
        "model": "Beta participation prior; recency-weighted empirical production; position-pool shrinkage.",
        "required": ["Licensed official player game logs", "Timestamped executable prop quotes", "Archived player participation and void rules"],
        "failure_modes": ["Inactive status released after forecast", "Early exit settles differently from nonparticipation", "Small player sample"],
        "status": "unvalidated", "source_id": "dk_player_settlement",
    },
    {
        "id": "V05", "name": "Cross-game parlay joint price", "category": "Parlay",
        "hypothesis": "Aligned joint outcomes may differ from the product of marginals even across different games.",
        "signal": "Joint win probability from aligned outcomes versus the full ticket price, after push/void rules.",
        "model": "Empirical joint outcomes by season-week; cluster bootstrap; no independence assumption without evidence.",
        "required": ["Licensed official game results", "Timestamped executable parlay ticket prices", "Archived parlay push/void rules"],
        "failure_modes": ["Shared slate conditions", "Ticket price not equal to product of leg prices", "Selection bias in leg pairing"],
        "status": "unvalidated", "source_id": "dk_parlay",
    },
    {
        "id": "V06", "name": "Same-game player combination", "category": "Player prop combo",
        "hypothesis": "Shared game scenarios create dependence between player legs that must be priced jointly.",
        "signal": "Scenario-simulated joint probability versus the operator's SGP-specific price.",
        "model": "Aligned game-scenario simulation preserving player usage dependence; threshold-specific phi reported with uncertainty.",
        "required": ["Licensed official player game logs", "Timestamped executable SGP prices", "Archived SGP repricing and participation rules"],
        "failure_modes": ["Operator already prices correlation", "SGP odds differ from traditional parlay odds", "Void leg reprices the ticket"],
        "status": "unvalidated", "source_id": "dk_sgp",
    },
    {
        "id": "V07", "name": "Market-baseline residual", "category": "Benchmark",
        "hypothesis": "A model should be promoted only if it improves probability scores and net returns versus a timestamped market baseline.",
        "signal": "Paired Brier/log-loss improvement and executable net ROI, not raw win rate.",
        "model": "Compare every forecast with the contemporaneous de-vigged market probability; report the vig-removal assumption.",
        "required": ["Timestamped executable two-sided quotes", "Licensed official outcomes", "Frozen baseline definition"],
        "failure_modes": ["Baseline uses a later price", "Proportional de-vig is misspecified", "Only one-sided quote is available"],
        "status": "unvalidated", "source_id": "nist_bootstrap",
    },
    {
        "id": "V08", "name": "Correlation stability filter", "category": "Risk filter",
        "hypothesis": "Only threshold-specific dependence estimates that are stable out of sample should enter joint pricing.",
        "signal": "Phi with cluster uncertainty, sample size, missingness and season stability; no causal claim.",
        "model": "Binary leg outcomes at matched quoted thresholds; aligned season-week clusters; sensitivity to threshold and snapshot.",
        "required": ["Licensed official outcomes", "Timestamped executable leg thresholds", "Archived settlement rules"],
        "failure_modes": ["Phi changes with threshold", "Small sample", "Correlation is not causation", "Pairwise phi does not determine multi-leg joint probability"],
        "status": "unvalidated", "source_id": "nist_correlation",
    },
]


def registry() -> list[dict]:
    return [dict(s) for s in STRATEGIES]
