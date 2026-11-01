#!/usr/bin/env python3
"""Append this session's integration record to COORDINATION.md exactly once.

Merges take `COORDINATION.md` from `main` (`-X theirs`) so concurrent sessions keep their board
entries; this script restores our own record afterwards. It is idempotent: re-running it is a no-op.
"""
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
BOARD = ROOT / "COORDINATION.md"
RECORD = BASE / "docs" / "integration_record.md"
MARKER = "Session `arena/9f5e9cb5-korea3` — integration record"


def main() -> int:
    body = RECORD.read_text()
    text = BOARD.read_text()
    if MARKER in text:
        print("record already present")
        return 0
    BOARD.write_text(text.rstrip("\n") + "\n\n---\n\n" + body)
    print("record appended to COORDINATION.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
