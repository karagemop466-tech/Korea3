#!/usr/bin/env python3
"""Count row-local sources in a pinned PR #13 integration snapshot.

This observes static tbody rows only. The conservative official-domain
allowlist is a structural filter, not evidence that a linked source supports a
value. Fetch the named commit first if a fresh clone does not have it.
"""
from __future__ import annotations

import subprocess

from check_merged_rows import Rows, accepted

SNAPSHOT = "ca21d3a78042c9cb7b17632784bf9e65600a8864"


def main():
    files = subprocess.check_output(
        ["git", "ls-tree", "--name-only", SNAPSHOT], text=True
    ).splitlines()
    totals = [0, 0, 0]
    for path in sorted(p for p in files if p.endswith(".html")):
        source = subprocess.check_output(["git", "show", f"{SNAPSHOT}:{path}"], text=True)
        parser = Rows()
        parser.feed(source)
        counts = [len(parser.rows), sum(not row for row in parser.rows),
                  sum(not any(accepted(link) for link in row) for row in parser.rows)]
        totals = [a + b for a, b in zip(totals, counts)]
        print(f"{path}: {counts[0]} rows; {counts[1]} with no link; "
              f"{counts[2]} without an allowlisted source")
    assert totals == [773, 0, 767], totals
    print("REPRODUCED: 767 of 773 rows lack a conservative official-domain link "
          "in the pinned PR #13 snapshot")
    print("Caution: an allowlisted link may still fail to support its row's values.")


if __name__ == "__main__":
    main()
