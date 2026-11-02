"""Run the fail-closed verified workbench and generate its static dashboard.

Default inputs are empty. The program never fetches NFL content, never imputes
prices, and never promotes a strategy without a fully admitted evidence chain.
Optional licensed inputs live in nfl_lab/inputs/*.jsonl with pinned artifacts in
nfl_lab/inputs/evidence/ and forecast artifacts in
nfl_lab/inputs/forecast_artifacts/. Parsing a record is not admission.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from pathlib import Path

from .contracts import ContractError, Forecast, Game, Quote, SettledBet
from .evidence import EvidenceRegistry, InputBundle, audit_bundle, load_jsonl
from .models import PlayerGame
from .strategies import registry as strategy_registry
from .validation import Protocol, ProtocolFreeze, evaluate_family, leaderboard

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "nfl_lab"
OUT = ROOT / "verified" / "data"
INPUTS = LAB / "inputs"

PROTOCOL = Protocol(
    protocol_id="nfl-verified-v2",
    family=tuple(s["id"] for s in strategy_registry()),
    train_seasons=tuple(range(2010, 2020)),
    tune_seasons=(2020, 2021),
    holdout_seasons=(2022, 2023, 2024),
    forward_seasons=(2025, 2026),
)

CODE_FILES = ("contracts.py", "evidence.py", "models.py", "pricing.py", "strategies.py", "validation.py")


def code_fingerprint() -> str:
    h = hashlib.sha256()
    for name in CODE_FILES:
        h.update(name.encode())
        h.update((LAB / name).read_bytes())
    return h.hexdigest()


def load_freeze() -> ProtocolFreeze | None:
    path = LAB / "protocol_freeze.json"
    if not path.exists():
        return None
    raw = json.loads(path.read_text(encoding="utf-8"))
    freeze = ProtocolFreeze(**{**raw, "family": tuple(raw["family"]), "model_versions": tuple(raw["model_versions"])})
    if freeze.protocol_digest != PROTOCOL.digest() or freeze.code_fingerprint != code_fingerprint():
        return None
    return freeze


def write_json(name: str, payload) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(json.dumps(payload, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run() -> dict:
    sources = EvidenceRegistry.load(LAB / "sources.json", INPUTS / "evidence", INPUTS / "forecast_artifacts")
    strategies = strategy_registry()
    bundle = InputBundle(
        games=load_jsonl(INPUTS / "games.jsonl", Game),
        quotes=load_jsonl(INPUTS / "quotes.jsonl", Quote),
        bets=load_jsonl(INPUTS / "bets.jsonl", SettledBet),
        forecasts=load_jsonl(INPUTS / "forecasts.jsonl", Forecast),
        player_games=load_jsonl(INPUTS / "player_games.jsonl", PlayerGame),
    )
    audit = audit_bundle(sources, bundle)
    admitted = {k: len(v) for k, v in audit["admitted"].items()}
    errors = audit["errors"]
    freeze = load_freeze()
    reports = evaluate_family(PROTOCOL, sources, bundle, freeze)
    board = leaderboard(reports)
    status = {
        "generated_at": "2026-11-02",
        "mode": "fail-closed",
        "input_contract_version": 2,
        "network_fetch": False,
        "real_money_execution": False,
        "admitted": admitted,
        "admission_errors": errors,
        "eligible_strategies": sum(r.eligible for r in reports),
        "verified_empirical_values": 0,
        "reward_pool": None,
        "protocol": asdict(PROTOCOL),
        "protocol_sha256": PROTOCOL.digest(),
        "protocol_freeze_loaded": freeze is not None,
        "code_fingerprint": code_fingerprint(),
        "notes": [
            "Empty inputs are intentional: no licensed, event-level official dataset was admitted in this session.",
            "Admission resolves official result, operator quote, dated operator rules, accepted ticket, settlement and hashed forecast artifact.",
            "Existing third-party backtests are preserved in their original archives and are not promoted to verified status.",
            "Synthetic unit tests exercise code paths only and are never published as NFL findings.",
            "Rewards are disabled until funding, sponsor, jurisdiction and payout terms are verified.",
        ],
    }
    write_json("status.json", status)
    write_json("strategies.json", strategies)
    write_json("gates.json", [r.to_dict() for r in reports])
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
