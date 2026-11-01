#!/usr/bin/env python3
"""Count row-level links in one pinned, already-merged dashboard snapshot.

The allowlist is a conservative league/operator/government check, not a proof
that a linked source supports the values in a row. Static <tbody> rows only;
footer/page-level links and dynamically inserted rows are not counted.
"""
from __future__ import annotations

import subprocess
from html.parser import HTMLParser
from urllib.parse import urlsplit

SNAPSHOT = "f968dcdddf6f7b94ab7b2d91b37c06f1dcd7b69e"
HOSTS = ("nfl.com", "draftkings.com", "fanduel.com", "nist.gov", "weather.gov",
         "cdc.gov", "massgaming.com")


class Rows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_body = False
        self.current = None
        self.rows = []

    def handle_starttag(self, tag, attrs):
        if tag == "tbody":
            self.in_body = True
        elif tag == "tr" and self.in_body:
            self.current = []
        elif tag == "a" and self.current is not None:
            self.current.append(dict(attrs).get("href", ""))

    def handle_endtag(self, tag):
        if tag == "tr" and self.current is not None:
            self.rows.append(self.current)
            self.current = None
        elif tag == "tbody":
            self.in_body = False


def accepted(url):
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    return parsed.scheme == "https" and any(host == h or host.endswith("." + h) for h in HOSTS)


def main():
    files = subprocess.check_output(
        ["git", "ls-tree", "-r", "--name-only", SNAPSHOT, "docs"], text=True
    ).splitlines()
    total = no_links = no_accepted = 0
    for path in sorted(p for p in files if p.endswith(".html")):
        source = subprocess.check_output(["git", "show", f"{SNAPSHOT}:{path}"], text=True)
        parser = Rows()
        parser.feed(source)
        n = len(parser.rows)
        empty = sum(not row for row in parser.rows)
        unlinked = sum(not any(accepted(link) for link in row) for row in parser.rows)
        total += n
        no_links += empty
        no_accepted += unlinked
        print(f"{path}: {n} rows; {empty} with no link; {unlinked} without an allowlisted source")
    assert (total, no_links, no_accepted) == (949, 872, 879)
    print(f"REPRODUCED: {total} rows; {no_links} without links; "
          f"{no_accepted} without allowlisted sources in the pinned snapshot")
    print("Caution: an allowlisted link may still fail to support its row's values.")


if __name__ == "__main__":
    main()
