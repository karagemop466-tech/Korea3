"""Run the fail-closed verified workbench and generate its static dashboard.

Default inputs are empty.  The program never fetches NFL content, never imputes
prices, and never promotes a strategy without admitted official evidence.
Optional licensed inputs live in nfl_lab/inputs/*.jsonl and must pass the same
contracts as the synthetic unit-test fixtures.
"""
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .contracts import ContractError, Forecast, Game, Quote, SettledBet
from .evidence import EvidenceRegistry, load_jsonl
from .models import PlayerGame
from .strategies import registry as strategy_registry
from .validation import Protocol, evaluate_strategy, leaderboard

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "nfl_lab"
OUT = ROOT / "verified" / "data"
INPUTS = LAB / "inputs"

PROTOCOL = Protocol(
    protocol_id="nfl-verified-v1",
    family=tuple(s["id"] for s in strategy_registry()),
    train_seasons=tuple(range(2010, 2020)),
    tune_seasons=(2020, 2021),
    holdout_seasons=(2022, 2023, 2024),
    forward_seasons=(2025, 2026),
)


def write_json(name: str, payload) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run() -> dict:
    sources = EvidenceRegistry.load(LAB / "sources.json")
    strategies = strategy_registry()
    games = load_jsonl(INPUTS / "games.jsonl", Game)
    quotes = load_jsonl(INPUTS / "quotes.jsonl", Quote)
    bets = load_jsonl(INPUTS / "bets.jsonl", SettledBet)
    forecasts = load_jsonl(INPUTS / "forecasts.jsonl", Forecast)
    player_logs = load_jsonl(INPUTS / "player_games.jsonl", PlayerGame)

    admitted = {"games": 0, "quotes": 0, "bets": 0, "forecasts": len(forecasts), "player_games": 0}
    errors: list[str] = []
    for g in games:
        try:
            sources.audit_game(g)
            admitted["games"] += 1
        except ContractError as exc:
            errors.append(f"game {g.game_id}: {exc}")
    for q in quotes:
        try:
            sources.audit_quote(q)
            if not q.executable:
                raise ContractError("quote is not marked executable")
            admitted["quotes"] += 1
        except ContractError as exc:
            errors.append(f"quote {q.quote_id}: {exc}")
    for b in bets:
        try:
            sources.audit_bet(b)
            admitted["bets"] += 1
        except ContractError as exc:
            errors.append(f"bet {b.bet_id}: {exc}")
    for r in player_logs:
        try:
            sources.require(r.evidence_id, r.source_url, "player_game", require_rights=True)
            admitted["player_games"] += 1
        except ContractError as exc:
            errors.append(f"player_game {r.player_id}/{r.game_id}: {exc}")

    reports = []
    for s in strategies:
        sid = s["id"]
        report = evaluate_strategy(
            sid, [b for b in bets if b.strategy_id == sid],
            [f for f in forecasts if f.strategy_id == sid], PROTOCOL, sources,
            family_pvalues=None, forward_bets=None,
            protocol_frozen_digest=PROTOCOL.digest(),
            executable_quotes_verified=False if not quotes else None,
        )
        reports.append(report.to_dict())
    board = leaderboard([evaluate_strategy(
        s["id"], [b for b in bets if b.strategy_id == s["id"]],
        [f for f in forecasts if f.strategy_id == s["id"]], PROTOCOL, sources,
        protocol_frozen_digest=PROTOCOL.digest()) for s in strategies])

    status = {
        "generated_at": "2026-11-01",
        "mode": "fail-closed",
        "network_fetch": False,
        "real_money_execution": False,
        "admitted": admitted,
        "admission_errors": errors,
        "eligible_strategies": sum(r["eligible"] for r in reports),
        "verified_empirical_values": 0,
        "reward_pool": None,
        "protocol": asdict(PROTOCOL),
        "protocol_sha256": PROTOCOL.digest(),
        "notes": [
            "Empty inputs are intentional: no licensed, event-level official dataset was admitted in this session.",
            "Existing third-party backtests are preserved in their original archives and are not promoted to verified status.",
            "Synthetic unit tests exercise code paths only and are never published as NFL findings.",
        ],
    }
    write_json("status.json", status)
    write_json("strategies.json", strategies)
    write_json("gates.json", reports)
    write_json("leaderboard.json", board)
    write_json("sources.json", [r.to_dict() for r in sources.records.values()])
    write_json("correlations.json", {"verified_pairs": [], "status": "blocked: no admitted matched official leg outcomes"})
    write_json("lines.json", {"verified_lines": [], "status": "blocked: no admitted licensed official game history"})
    write_json("props.json", {"verified_props": [], "status": "blocked: no admitted licensed official player logs or operator prop quotes"})
    from .build_verified import build
    build()
    return status


if __name__ == "__main__":
    result = run()
    print(json.dumps({k: result[k] for k in ("mode", "admitted", "eligible_strategies", "verified_empirical_values")}, indent=2))
