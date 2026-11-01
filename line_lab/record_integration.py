#!/usr/bin/env python3
"""Keep this session's entry and record on the shared board in sync with `docs/integration_record.md`.

Merges take `COORDINATION.md` from `main` (`-X theirs`) so concurrent sessions keep their board
entries, and a later merge can drop our section again. Running this script restores both:
the registry row for `arena/9f5e9cb5-korea3` and the integration record section at the end of
the file. It is idempotent and touches no other session's text.
"""
from pathlib import Path

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
BOARD = ROOT / "COORDINATION.md"
RECORD = BASE / "docs" / "integration_record.md"

ROW_KEY = "| `arena/9f5e9cb5-korea3` |"
ROW = (
    "| `arena/9f5e9cb5-korea3` | root dashboard + `line_lab/` pipeline | "
    "`line_lab/**`, root `*.html`, `assets/**`, this board | "
    "merged (PR #13, `5eddec4b`); dashboard live at `/`, deploy verified |\n"
)


def sync_row(text: str) -> str:
    lines = text.splitlines(keepends=True)
    for i, line in enumerate(lines):
        if line.startswith(ROW_KEY):
            lines[i] = ROW
            break
    else:
        print("warning: registry row not found; board left unchanged")
    return "".join(lines)


def sync_record(text: str, body: str) -> str:
    heading = body.splitlines()[0]
    if heading not in text:
        return text.rstrip("\n") + "\n\n---\n\n" + body
    head = text[: text.index(heading)].rstrip("\n")
    if head.endswith("---"):
        head = head[:-3].rstrip("\n")
    return head + "\n\n---\n\n" + body


def main() -> int:
    body = RECORD.read_text()
    before = BOARD.read_text()
    after = sync_record(sync_row(before), body)
    if after != before:
        BOARD.write_text(after)
        print("COORDINATION.md synced from line_lab/docs/integration_record.md")
    else:
        print("COORDINATION.md already in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
