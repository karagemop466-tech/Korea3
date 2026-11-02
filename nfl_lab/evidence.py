"""Evidence admission and source registry. No fetching, scraping or guessing.

A source link is not a licence and not a settlement archive. Admission resolves
the full chain: official result -> operator quote -> dated operator rules ->
accepted ticket -> official settlement -> hashed forecast artifact.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from urllib.parse import urlparse

from .contracts import ContractError, Evidence, Forecast, Game, Quote, SettledBet, sha256_hex, utc
from .pricing import american_to_decimal, remove_vig_two_way, settle_moneyline, settle_single

# Publisher-controlled hosts only. A host match is necessary, not sufficient.
OFFICIAL_HOSTS = {
    "nfl.com": {"www.nfl.com", "operations.nfl.com", "support.nfl.com", "static.www.nfl.com", "nextgenstats.nfl.com", "media.nfl.com"},
    "draftkings.com": {"sportsbook.draftkings.com", "support.draftkings.com", "help.draftkings.com"},
    "fanduel.com": {"www.fanduel.com", "sportsbook.fanduel.com", "support.fanduel.com"},
    "nist.gov": {"www.itl.nist.gov", "tsapps.nist.gov", "www.nist.gov"},
    "weather.gov": {"www.weather.gov"},
    "nih.gov": {"pmc.ncbi.nlm.nih.gov", "eutils.ncbi.nlm.nih.gov"},
    "massgaming.com": {"massgaming.com"},
}

GAME_FIELDS = {"game_result", "game_id", "season", "week", "kickoff", "home", "away", "home_score", "away_score", "status", "result_available_at"}
QUOTE_FIELDS = {"quote", "quote_id", "game_id", "market", "selection", "line", "american", "observed_at", "kickoff", "operator", "rules_id", "executable", "jurisdiction"}
BET_FIELDS = {"settlement", "bet_id", "strategy_id", "event_id", "cluster", "kickoff", "stake", "profit", "result", "quote_id", "rules_id", "forecast_id", "selection", "line", "operator", "jurisdiction", "accepted_at", "accepted_american", "settled_at"}
PLAYER_FIELDS = {"player_game", "player_id", "game_id", "kickoff", "team", "opponent", "position", "market", "value", "participated", "stats_available_at"}
BASELINE_METHOD = "proportional_two_way_conditional"


def official_publisher(url: str) -> str | None:
    p = urlparse(url)
    if p.scheme != "https" or p.username or p.password or not p.hostname:
        return None
    host = p.hostname.lower()
    for publisher, hosts in OFFICIAL_HOSTS.items():
        if host in hosts:
            return publisher
    return None


def canonical_bytes(value) -> bytes:
    from dataclasses import asdict, is_dataclass
    payload = asdict(value) if is_dataclass(value) else value
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


@dataclass
class InputBundle:
    games: list[Game] = field(default_factory=list)
    quotes: list[Quote] = field(default_factory=list)
    bets: list[SettledBet] = field(default_factory=list)
    forecasts: list[Forecast] = field(default_factory=list)
    player_games: list = field(default_factory=list)

    def indexes(self):
        return (
            {g.game_id: g for g in self.games},
            {q.quote_id: q for q in self.quotes},
            {(r.player_id, r.game_id, r.market): r for r in self.player_games},
            {f.forecast_id: f for f in self.forecasts if f.forecast_id},
        )


class EvidenceRegistry:
    def __init__(self, records: list[Evidence] | None = None):
        self.records: dict[str, Evidence] = {}
        self.artifacts: dict[str, bytes] = {}
        self.forecast_artifacts: dict[str, bytes] = {}
        for record in records or []:
            self.add(record)

    def add(self, record: Evidence) -> None:
        if record.evidence_id in self.records:
            raise ContractError(f"Duplicate evidence id: {record.evidence_id}")
        if official_publisher(record.url) is None:
            raise ContractError(f"Not an approved official publisher URL: {record.url}")
        self.records[record.evidence_id] = record

    def register_artifact(self, digest: str, content: bytes) -> None:
        sha256_hex(digest)
        if hashlib.sha256(content).hexdigest() != digest:
            raise ContractError("Artifact hash mismatch")
        self.artifacts[digest] = content

    def register_forecast_artifact(self, digest: str, content: bytes) -> None:
        sha256_hex(digest)
        if hashlib.sha256(content).hexdigest() != digest:
            raise ContractError("Forecast artifact hash mismatch")
        self.forecast_artifacts[digest] = content

    @classmethod
    def load(cls, path: Path, artifact_dir: Path | None = None, forecast_artifact_dir: Path | None = None) -> "EvidenceRegistry":
        raw = json.loads(path.read_text(encoding="utf-8"))
        records = []
        for r in raw:
            kwargs = {**r}
            for key in ("fields", "jurisdictions", "markets", "rights_scope"):
                if key in kwargs:
                    kwargs[key] = tuple(kwargs[key])
            records.append(Evidence(**kwargs))
        reg = cls(records)
        if artifact_dir and artifact_dir.exists():
            for rec in records:
                for digest in (rec.content_sha256, rec.license_sha256):
                    if digest:
                        p = artifact_dir / digest
                        if p.exists():
                            reg.register_artifact(digest, p.read_bytes())
        if forecast_artifact_dir and forecast_artifact_dir.exists():
            for p in sorted(forecast_artifact_dir.iterdir()):
                if p.is_file() and len(p.name) == 64:
                    reg.register_forecast_artifact(p.name, p.read_bytes())
        return reg

    def require(self, evidence_id: str, url: str, field: str | None = None,
                content: bytes | None = None, require_rights: bool = True,
                kind: str | None = None) -> Evidence:
        record = self.records.get(evidence_id)
        if record is None:
            raise ContractError(f"Missing evidence: {evidence_id}")
        if record.url != url:
            raise ContractError(f"Evidence URL mismatch: {evidence_id}")
        publisher = official_publisher(url)
        if publisher is None:
            raise ContractError(f"Unapproved source: {url}")
        if not require_rights:
            return record
        if record.review_status != "verified" or not record.claim:
            raise ContractError(f"Evidence claim is not verified: {evidence_id}")
        if kind is not None and record.kind != kind:
            raise ContractError(f"Evidence kind mismatch: {evidence_id} is {record.kind}, expected {kind}")
        if record.kind != "reference" and record.publisher != publisher:
            raise ContractError(f"Evidence publisher mismatch: {evidence_id}")
        if record.rights not in {"licensed", "public_domain"}:
            raise ContractError(f"Link-only evidence cannot admit stored data: {evidence_id}")
        if not field or not record.fields or field not in record.fields:
            raise ContractError(f"Evidence does not explicitly cover field {field}: {evidence_id}")
        if not record.rights_scope or not (field in record.rights_scope or record.kind in record.rights_scope or "*" in record.rights_scope):
            raise ContractError(f"Rights scope does not cover {field}: {evidence_id}")
        payload = content if content is not None else self.artifacts.get(record.content_sha256 or "")
        if payload is None:
            raise ContractError(f"Missing pinned source artifact: {evidence_id}")
        if hashlib.sha256(payload).hexdigest() != record.content_sha256:
            raise ContractError(f"Content hash mismatch: {evidence_id}")
        if record.rights == "licensed":
            if official_publisher(record.license_ref or "") != publisher:
                raise ContractError(f"Licence reference publisher mismatch: {evidence_id}")
            licence = self.artifacts.get(record.license_sha256 or "")
            if licence is None or hashlib.sha256(licence).hexdigest() != record.license_sha256:
                raise ContractError(f"Missing or changed licence artifact: {evidence_id}")
        return record

    def _require_fields(self, record: Evidence, required: set[str]) -> None:
        missing = required - set(record.fields)
        if missing:
            raise ContractError(f"Evidence {record.evidence_id} does not cover fields: {sorted(missing)}")

    def audit_game(self, game: Game, content: bytes | None = None) -> None:
        rec = self.require(game.evidence_id, game.source_url, "game_result", content, kind="game_result")
        if official_publisher(game.source_url) != "nfl.com":
            raise ContractError("Game result evidence must be NFL-published")
        if game.status != "final":
            raise ContractError("Game result is not official-final")
        if not game.result_available_at:
            raise ContractError("Game result requires an availability timestamp")
        self._require_fields(rec, GAME_FIELDS)

    def audit_rules(self, rules_id: str, operator: str, market: str, jurisdiction: str, at: str) -> Evidence:
        rules = self.records.get(rules_id)
        if rules is None:
            raise ContractError("Missing settlement rules evidence")
        self.require(rules_id, rules.url, "settlement_rules", kind="settlement_rules")
        if official_publisher(rules.url) != operator:
            raise ContractError("Rules publisher does not match the operator")
        if rules.operator != operator:
            raise ContractError("Rules operator mismatch")
        if market not in rules.markets:
            raise ContractError("Rules do not cover the quoted market")
        if jurisdiction not in rules.jurisdictions:
            raise ContractError("Rules do not cover the acceptance jurisdiction")
        if not rules.effective_from or not rules.effective_until:
            raise ContractError("Rules lack an effective interval")
        if not (utc(rules.effective_from) <= utc(at) < utc(rules.effective_until)):
            raise ContractError("Rules were not in force at acceptance")
        if not rules.version:
            raise ContractError("Rules lack a version")
        return rules

    def audit_quote(self, quote: Quote, content: bytes | None = None) -> Evidence:
        rec = self.require(quote.evidence_id, quote.source_url, "quote", content, kind="quote")
        publisher = official_publisher(quote.source_url)
        if quote.operator != publisher:
            raise ContractError("Quote operator does not match the official publisher")
        if not quote.jurisdiction:
            raise ContractError("Quote requires an acceptance jurisdiction")
        if not quote.executable:
            raise ContractError("Quote is not executable")
        required = set(QUOTE_FIELDS)
        if quote.market == "player_prop":
            required |= {"player_id", "market_stat"}
        if quote.market == "parlay":
            required |= {"legs"}
        self._require_fields(rec, required)
        self.audit_rules(quote.rules_id, quote.operator, quote.market, quote.jurisdiction, quote.observed_at)
        return rec

    def audit_player_game(self, row, content: bytes | None = None) -> None:
        rec = self.require(row.evidence_id, row.source_url, "player_game", content, kind="player_game")
        if official_publisher(row.source_url) != "nfl.com":
            raise ContractError("Player game evidence must be NFL-published")
        if not row.stats_available_at:
            raise ContractError("Player game requires a stats availability timestamp")
        self._require_fields(rec, PLAYER_FIELDS)

    def audit_forecast(self, forecast: Forecast, quote: Quote, baseline_quote: Quote,
                       opposite_quote: Quote, artifact: bytes | None = None) -> None:
        if not forecast.forecast_id or not forecast.artifact_sha256 or not forecast.code_commit or not forecast.feature_snapshot_sha256:
            raise ContractError("Forecast requires id, artifact hash, code commit and feature snapshot hash")
        payload = artifact if artifact is not None else self.forecast_artifacts.get(forecast.artifact_sha256)
        if payload is None:
            raise ContractError("Missing forecast artifact")
        if hashlib.sha256(payload).hexdigest() != forecast.artifact_sha256:
            raise ContractError("Forecast artifact hash mismatch")
        expected_payload = canonical_bytes({k: v for k, v in asdict(forecast).items() if k != "artifact_sha256"})
        if payload != expected_payload:
            raise ContractError("Forecast artifact does not match the registered forecast")
        if forecast.event_id != quote.game_id or forecast.market != quote.market or forecast.selection != quote.selection:
            raise ContractError("Forecast/quote identity mismatch")
        if forecast.line != quote.line or forecast.player_id != quote.player_id or forecast.market_stat != quote.market_stat:
            raise ContractError("Forecast/quote threshold or player mismatch")
        if utc(forecast.kickoff) != utc(quote.kickoff):
            raise ContractError("Forecast/quote kickoff mismatch")
        if utc(forecast.features_available_at) > utc(forecast.issued_at) or utc(forecast.issued_at) >= utc(quote.kickoff):
            raise ContractError("Forecast chronology violation")
        if not forecast.baseline_id or forecast.baseline_method != BASELINE_METHOD:
            raise ContractError("Forecast requires the frozen baseline method")
        if not forecast.baseline_quote_id or not forecast.opposite_quote_id:
            raise ContractError("Forecast requires paired baseline quote ids")
        if baseline_quote.quote_id != forecast.baseline_quote_id or opposite_quote.quote_id != forecast.opposite_quote_id:
            raise ContractError("Baseline quote ids do not resolve")
        for q in (baseline_quote, opposite_quote):
            expected_line = forecast.line
            if forecast.market == "spread" and q.selection != forecast.selection and expected_line is not None:
                expected_line = -expected_line
            if q.game_id != forecast.event_id or q.market != forecast.market or q.line != expected_line or q.player_id != forecast.player_id or q.market_stat != forecast.market_stat:
                raise ContractError("Baseline quote market/threshold mismatch")
            if utc(q.observed_at) > utc(forecast.issued_at) or utc(q.observed_at) >= utc(q.kickoff):
                raise ContractError("Baseline quote is later than the forecast or not pregame")
        if utc(baseline_quote.observed_at) != utc(opposite_quote.observed_at):
            raise ContractError("Baseline quotes are not contemporaneous")
        if baseline_quote.selection == opposite_quote.selection:
            raise ContractError("Baseline quotes must be opposite selections")
        p_base, p_opp = remove_vig_two_way(baseline_quote.american, opposite_quote.american)
        expected = p_base if baseline_quote.selection == forecast.selection else p_opp
        if forecast.baseline_p_win is None or abs(forecast.baseline_p_win - expected) > 1e-9:
            raise ContractError("Baseline probability does not match the frozen de-vig method")
        try:
            forecast.p_action_win
        except ContractError as exc:
            raise ContractError("Forecast has no conditional action probability") from exc

    def _single_outcome(self, quote: Quote, game: Game | None, player_game, rules: Evidence) -> str:
        if quote.market == "player_prop":
            if player_game is None:
                raise ContractError("Missing official player game for prop settlement")
            self.audit_player_game(player_game)
            if player_game.game_id != quote.game_id or player_game.player_id != quote.player_id or player_game.market != quote.market_stat:
                raise ContractError("Player game identity mismatch")
            if utc(player_game.kickoff) != utc(quote.kickoff):
                raise ContractError("Player game kickoff mismatch")
            if not player_game.participated:
                if rules.player_nonparticipation_action != "void":
                    raise ContractError("Archived rules do not explicitly void nonparticipation for this prop")
                return "void"
            return settle_single(player_game.value, quote.line, quote.selection, quote.american)[0]
        if game is None:
            raise ContractError("Missing official game for settlement")
        self.audit_game(game)
        if quote.game_id != game.game_id or utc(quote.kickoff) != utc(game.kickoff):
            raise ContractError("Quote/game identity mismatch")
        if quote.market == "spread":
            margin = game.margin if quote.selection == "home" else -game.margin
            return settle_single(margin, quote.line, quote.selection, quote.american)[0]
        if quote.market == "total":
            return settle_single(game.total, quote.line, quote.selection, quote.american)[0]
        if quote.market == "moneyline":
            selected, opponent = (game.home_score, game.away_score) if quote.selection == "home" else (game.away_score, game.home_score)
            return settle_moneyline(selected, opponent, quote.american)[0]
        raise ContractError("Unsupported single market")

    def audit_bet(self, bet: SettledBet, quotes: dict[str, Quote], games: dict[str, Game],
                  player_games: dict, forecasts: dict[str, Forecast],
                  content: bytes | None = None) -> None:
        quote = quotes.get(bet.quote_id)
        if quote is None:
            raise ContractError("Settlement quote_id does not resolve to an admitted quote")
        self.audit_quote(quote)
        rec = self.require(bet.evidence_id, bet.source_url, "settlement", content, kind="settlement")
        if rec.operator != quote.operator or official_publisher(bet.source_url) != quote.operator:
            raise ContractError("Settlement evidence operator mismatch")
        if bet.jurisdiction not in rec.jurisdictions or quote.market not in rec.markets:
            raise ContractError("Settlement evidence jurisdiction/market mismatch")
        required = set(BET_FIELDS)
        if quote.market == "player_prop":
            required |= {"player_id", "market_stat"}
        if quote.market == "parlay":
            required |= {"legs", "leg_outcomes"}
        self._require_fields(rec, required)
        if bet.rules_id != quote.rules_id:
            raise ContractError("Bet and quote rules mismatch")
        if bet.operator != quote.operator or bet.jurisdiction != quote.jurisdiction:
            raise ContractError("Bet/quote operator or jurisdiction mismatch")
        if bet.event_id != quote.game_id or bet.selection != quote.selection or bet.line != quote.line or bet.player_id != quote.player_id or bet.market_stat != quote.market_stat:
            raise ContractError("Bet/quote identity mismatch")
        if utc(bet.kickoff) != utc(quote.kickoff):
            raise ContractError("Bet/quote kickoff mismatch")
        expected_market = "parlay" if quote.market == "parlay" else "single"
        if bet.market != expected_market:
            raise ContractError("Bet ticket kind mismatch")
        if not bet.accepted_at or not bet.settled_at or bet.accepted_american is None:
            raise ContractError("Bet requires acceptance time, settlement time and accepted price")
        if not (utc(quote.observed_at) <= utc(bet.accepted_at) < utc(quote.kickoff)):
            raise ContractError("Acceptance is outside the pregame quote window")
        if utc(bet.settled_at) < utc(bet.kickoff):
            raise ContractError("Settlement precedes kickoff")
        if abs(bet.accepted_american - quote.american) > 1e-9:
            raise ContractError("Accepted price does not match the quoted price")
        rules = self.audit_rules(bet.rules_id, bet.operator, quote.market, bet.jurisdiction, bet.accepted_at)
        forecast = forecasts.get(bet.forecast_id or "")
        if forecast is None:
            raise ContractError("Settlement forecast_id does not resolve")
        if forecast.strategy_id != bet.strategy_id:
            raise ContractError("Forecast/bet strategy mismatch")
        if utc(forecast.issued_at) > utc(bet.accepted_at):
            raise ContractError("Forecast was issued after acceptance")
        baseline = quotes.get(forecast.baseline_quote_id or "")
        opposite = quotes.get(forecast.opposite_quote_id or "")
        if baseline is None or opposite is None:
            raise ContractError("Baseline quotes do not resolve")
        self.audit_quote(baseline)
        self.audit_quote(opposite)
        self.audit_forecast(forecast, quote, baseline, opposite)
        if bet.p_win is not None and abs(bet.p_win - forecast.p_win) > 1e-12:
            raise ContractError("Stored bet probability does not match the registered forecast")
        if bet.baseline_p_win is not None and forecast.baseline_p_win is not None and abs(bet.baseline_p_win - forecast.baseline_p_win) > 1e-9:
            raise ContractError("Stored baseline probability does not match the registered forecast")

        if quote.market != "parlay":
            game = games.get(quote.game_id)
            if game is None:
                raise ContractError("Missing official game")
            if bet.cluster != game.cluster:
                raise ContractError("Bet cluster does not match the official game")
            pg = player_games.get((quote.player_id, quote.game_id, quote.market_stat)) if quote.market == "player_prop" else None
            outcome = self._single_outcome(quote, game, pg, rules)
            expected_profit = 0.0 if outcome in {"push", "void"} else bet.stake * (american_to_decimal(quote.american) - 1) if outcome == "win" else -bet.stake
        else:
            if tuple(bet.legs) != tuple(quote.legs) or len(bet.leg_outcomes) != len(quote.legs):
                raise ContractError("Parlay legs/outcomes do not match the ticket quote")
            if rules.parlay_kind is None:
                raise ContractError("Parlay settlement rules are not explicit")
            leg_quotes = []
            outcomes = []
            kickoffs = []
            for qid, claimed in zip(quote.legs, bet.leg_outcomes):
                lq = quotes.get(qid)
                if lq is None or lq.market == "parlay":
                    raise ContractError("Parlay leg quote does not resolve")
                self.audit_quote(lq)
                lg = games.get(lq.game_id)
                if lg is None:
                    raise ContractError("Missing official game for parlay leg")
                if lg.cluster != bet.cluster:
                    raise ContractError("Cross-season/week parlay admission is not supported")
                lpg = player_games.get((lq.player_id, lq.game_id, lq.market_stat)) if lq.market == "player_prop" else None
                lr = self.audit_rules(lq.rules_id, lq.operator, lq.market, lq.jurisdiction, lq.observed_at)
                outcome = self._single_outcome(lq, lg, lpg, lr)
                if outcome != claimed:
                    raise ContractError("Parlay leg outcome does not match official settlement")
                leg_quotes.append(lq)
                outcomes.append(outcome)
                kickoffs.append(utc(lq.kickoff))
            if utc(quote.kickoff) != min(kickoffs):
                raise ContractError("Ticket kickoff must equal the first leg kickoff")
            dropped = False
            result = "win"
            if "loss" in outcomes:
                result = "loss"
            else:
                for outcome in outcomes:
                    action = rules.push_action if outcome == "push" else rules.void_action if outcome == "void" else None
                    if action == "loss":
                        result = "loss"
                        break
                    if action == "void_ticket":
                        result = "void"
                        break
                    if action == "drop":
                        dropped = True
                else:
                    remaining = sum(o == "win" for o in outcomes)
                    if remaining == 0:
                        result = "void"
                    elif remaining < (rules.min_remaining_legs or 1):
                        result = "void" if rules.below_min_action == "void_ticket" else "loss"
                    else:
                        result = "win"
            if result == "win":
                price = quote.american
                if dropped:
                    if bet.adjusted_american is None or "adjusted_american" not in rec.fields:
                        raise ContractError("Repriced parlay requires an officially evidenced adjusted price")
                    price = bet.adjusted_american
                expected_profit = bet.stake * (american_to_decimal(price) - 1)
            elif result == "loss":
                expected_profit = -bet.stake
            else:
                expected_profit = 0.0
        recomputed = result if quote.market == "parlay" else outcome
        if bet.result != recomputed:
            raise ContractError("Settlement result does not match recomputed official outcome")
        if abs(bet.profit - expected_profit) > 1e-8:
            raise ContractError("Settlement profit does not match the accepted price and official outcome")


def audit_bundle(registry: EvidenceRegistry, bundle: InputBundle) -> dict:
    games, quotes, player_games, forecasts = bundle.indexes()
    admitted = {"games": [], "quotes": [], "bets": [], "forecasts": [], "player_games": []}
    errors: list[str] = []
    for g in bundle.games:
        try:
            registry.audit_game(g)
            admitted["games"].append(g)
        except ContractError as exc:
            errors.append(f"game {g.game_id}: {exc}")
    for q in bundle.quotes:
        try:
            registry.audit_quote(q)
            admitted["quotes"].append(q)
        except ContractError as exc:
            errors.append(f"quote {q.quote_id}: {exc}")
    for r in bundle.player_games:
        try:
            registry.audit_player_game(r)
            admitted["player_games"].append(r)
        except ContractError as exc:
            errors.append(f"player_game {r.player_id}/{r.game_id}: {exc}")
    for f in bundle.forecasts:
        try:
            q = next((q for q in bundle.quotes if q.game_id == f.event_id and q.market == f.market and q.selection == f.selection and q.line == f.line and q.player_id == f.player_id and q.market_stat == f.market_stat), None)
            if q is None:
                raise ContractError("No matching quote for forecast")
            registry.audit_quote(q)
            b = quotes.get(f.baseline_quote_id or "")
            o = quotes.get(f.opposite_quote_id or "")
            if b is None or o is None:
                raise ContractError("Baseline quotes do not resolve")
            registry.audit_forecast(f, q, b, o)
            admitted["forecasts"].append(f)
        except ContractError as exc:
            errors.append(f"forecast {f.forecast_id}: {exc}")
    for bet in bundle.bets:
        try:
            registry.audit_bet(bet, quotes, games, player_games, forecasts)
            admitted["bets"].append(bet)
        except ContractError as exc:
            errors.append(f"bet {bet.bet_id}: {exc}")
    return {"admitted": admitted, "errors": errors}


def load_jsonl(path: Path, cls):
    if not path.exists():
        return []
    out = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            kwargs = json.loads(line)
            for key in ("legs", "leg_outcomes"):
                if key in kwargs:
                    kwargs[key] = tuple(kwargs[key])
            out.append(cls(**kwargs))
        except (TypeError, ValueError, ContractError) as exc:
            raise ContractError(f"{path.name}:{number}: {exc}") from exc
    return out
