"""Evidence admission and source registry. No fetching, scraping or guessing."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from urllib.parse import urlparse

from .contracts import ContractError, Evidence, Game, Quote, SettledBet

# Publisher-controlled hosts only.  A host match is necessary, not sufficient:
# each record still needs a human/agent content review and explicit rights.
OFFICIAL_HOSTS = {
    "nfl.com": {"www.nfl.com", "operations.nfl.com", "support.nfl.com", "static.www.nfl.com", "nextgenstats.nfl.com"},
    "draftkings.com": {"sportsbook.draftkings.com", "support.draftkings.com", "help.draftkings.com"},
    "fanduel.com": {"www.fanduel.com", "sportsbook.fanduel.com", "support.fanduel.com"},
    "nist.gov": {"www.itl.nist.gov", "tsapps.nist.gov", "www.nist.gov"},
    "weather.gov": {"www.weather.gov"},
    "nih.gov": {"pmc.ncbi.nlm.nih.gov"},
    "massgaming.com": {"massgaming.com"},
}


def official_publisher(url: str) -> str | None:
    p = urlparse(url)
    if p.scheme != "https" or p.username or p.password or not p.hostname:
        return None
    host = p.hostname.lower()
    for publisher, hosts in OFFICIAL_HOSTS.items():
        if host in hosts:
            return publisher
    return None


class EvidenceRegistry:
    def __init__(self, records: list[Evidence] | None = None):
        self.records: dict[str, Evidence] = {}
        for record in records or []:
            self.add(record)

    def add(self, record: Evidence) -> None:
        if record.evidence_id in self.records:
            raise ContractError(f"Duplicate evidence id: {record.evidence_id}")
        if official_publisher(record.url) is None:
            raise ContractError(f"Not an approved official publisher URL: {record.url}")
        self.records[record.evidence_id] = record

    @classmethod
    def load(cls, path: Path) -> "EvidenceRegistry":
        raw = json.loads(path.read_text(encoding="utf-8"))
        return cls([Evidence(**{**r, "fields": tuple(r.get("fields", []))}) for r in raw])

    def require(self, evidence_id: str, url: str, field: str | None = None,
                content: bytes | None = None, require_rights: bool = True) -> Evidence:
        record = self.records.get(evidence_id)
        if record is None:
            raise ContractError(f"Missing evidence: {evidence_id}")
        if record.url != url:
            raise ContractError(f"Evidence URL mismatch: {evidence_id}")
        if official_publisher(url) is None:
            raise ContractError(f"Unapproved source: {url}")
        if field and record.fields and field not in record.fields:
            raise ContractError(f"Evidence does not cover field {field}: {evidence_id}")
        if require_rights and record.rights not in {"licensed", "public_domain"}:
            raise ContractError(f"Link-only evidence cannot admit stored data: {evidence_id}")
        if content is not None:
            if not record.content_sha256:
                raise ContractError("No pinned content hash")
            if hashlib.sha256(content).hexdigest() != record.content_sha256:
                raise ContractError(f"Content hash mismatch: {evidence_id}")
        return record

    def audit_game(self, game: Game, content: bytes | None = None) -> None:
        self.require(game.evidence_id, game.source_url, "game_result", content)

    def audit_quote(self, quote: Quote, content: bytes | None = None) -> None:
        self.require(quote.evidence_id, quote.source_url, "quote", content)
        rules = self.records.get(quote.rules_id)
        if rules is None or official_publisher(rules.url) is None:
            raise ContractError("Missing official settlement rules")
        if urlparse(rules.url).hostname != urlparse(quote.source_url).hostname:
            # Operator help and sportsbook subdomains may differ; registrable
            # publisher must still match.
            if official_publisher(rules.url) != official_publisher(quote.source_url):
                raise ContractError("Quote and rules publisher mismatch")

    def audit_bet(self, bet: SettledBet, content: bytes | None = None) -> None:
        self.require(bet.evidence_id, bet.source_url, "settlement", content)
        if bet.rules_id not in self.records:
            raise ContractError("Missing settlement rules evidence")


def load_jsonl(path: Path, cls):
    if not path.exists():
        return []
    out = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            out.append(cls(**json.loads(line)))
        except (TypeError, ValueError, ContractError) as exc:
            raise ContractError(f"{path.name}:{number}: {exc}") from exc
    return out
