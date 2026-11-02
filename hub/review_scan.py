#!/usr/bin/env python3
"""Scan the repository once and produce a frozen review snapshot.

Used by hub/make_review_snapshot.py. The dashboard itself reads the committed
snapshot (hub/data/review_snapshot.json) rather than the live filesystem, so an
edit by another concurrent session cannot change generated output and fail the
CI drift gate. Re-run make_review_snapshot.py deliberately to refresh it.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

TR_FIND = re.compile(r"<tr\b[^>]*>(.*?)</tr>", re.S | re.I)
HREF_FIND = re.compile(r'href="([^"]+)"')

STABLE_DIRS = [
    "hub", "site", "docs", "verified", "audit", "data", "scripts", "pipeline",
    "reports", "line_lab", "nfl_lab", "research", "qa", "verification",
    "session-398c4b58", "assets", "tests",
]
AUDIT_DIRS = [
    ("", ""), ("site", "site/"), ("docs", "docs/"), ("verified", "verified/"),
    ("audit", "audit/"), ("qa", "qa/"), ("verification", "verification/"),
    ("session-398c4b58/site", "session-398c4b58/site/"), ("hub", "hub/"),
]


def file_count(root: Path, name: str) -> int:
    p = root / name
    if not p.is_dir():
        return 0
    return sum(1 for f in p.rglob("*") if f.is_file() and ".git" not in f.parts)


def audit_page(root: Path, rel: str, official_prefixes) -> dict | None:
    p = root / rel
    if not p.is_file():
        return None
    text = p.read_text(encoding="utf-8", errors="replace")
    rows = TR_FIND.findall(text)
    if not rows:
        return None
    official = 0
    for segment in rows:
        if any(u.startswith(official_prefixes) for u in HREF_FIND.findall(segment)):
            official += 1
    return {"page": rel, "rows": len(rows), "official_rows": official}


def scan(root: Path, official_prefixes, captured_utc: str, base_commit: str) -> dict:
    directories = [
        {"name": name, "files": file_count(root, name)}
        for name in STABLE_DIRS if (root / name).is_dir()
    ]
    pages = []
    for directory, prefix in AUDIT_DIRS:
        base = root / directory if directory else root
        for p in sorted(base.glob("*.html")):
            rel = prefix + p.name
            result = audit_page(root, rel, official_prefixes)
            if result:
                pages.append(result)
    return {
        "captured_utc": captured_utc,
        "base_commit": base_commit,
        "note": "Frozen snapshot produced by hub/make_review_snapshot.py; refresh deliberately.",
        "directories": directories,
        "pages": pages,
    }
