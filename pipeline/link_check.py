"""T7b — Link and integrity check for the generated site.

Fails (exit 1) if:
  * an internal link or asset points at a file that does not exist,
  * a page is missing from the navigation,
  * an external source link is not registered in data/sources.json or data/official/*.csv,
  * a page contains an unclosed HTML tag (structural sanity).
Writes reports/linkcheck.json for the record.
"""
from __future__ import annotations

import csv
import glob
import html.parser
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
DATA = os.path.join(ROOT, "data")
REPORTS = os.path.join(ROOT, "reports")

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class Checker(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack = []
        self.errors = []

    def handle_starttag(self, tag, attrs):
        if tag not in VOID:
            self.stack.append(tag)

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.errors.append(f"stray </{tag}>")
            return
        if self.stack[-1] == tag:
            self.stack.pop()
        elif tag in self.stack:
            while self.stack and self.stack[-1] != tag:
                self.errors.append(f"unclosed <{self.stack.pop()}> before </{tag}>")
            if self.stack:
                self.stack.pop()
        else:
            self.errors.append(f"unexpected </{tag}>")


def registered_external_urls():
    urls = set()
    with open(os.path.join(DATA, "sources.json"), encoding="utf-8") as fh:
        doc = json.load(fh)
        for s in doc["primary_sources"]:
            urls.add(s["url"])
        # blocked sources are documented (not used as evidence) and are registered here too
        for s in doc.get("blocked_sources_documented", []):
            urls.add(s["url"])
    for path in glob.glob(os.path.join(DATA, "official", "*.csv")):
        with open(path, newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                if row.get("source_url"):
                    urls.add(row["source_url"])
    return urls


def main():
    pages = sorted(glob.glob(os.path.join(DOCS, "*.html")))
    registered = registered_external_urls()
    internal_targets = {os.path.basename(p) for p in pages} | {"assets/style.css", "assets/app.js"}
    broken, unregistered, structural = [], [], []
    ext_seen = set()

    for page in pages:
        name = os.path.basename(page)
        with open(page, encoding="utf-8") as fh:
            text = fh.read()
        for href in re.findall(r'(?:href|src)="([^"]+)"', text):
            if href.startswith(("http://", "https://")):
                ext_seen.add(href)
                if href not in registered:
                    unregistered.append((name, href))
                continue
            if href.startswith(("mailto:", "#", "data:")):
                continue
            target = href.split("#")[0]
            if target and target not in internal_targets:
                broken.append((name, href))
        checker = Checker()
        checker.feed(text)
        if checker.errors or checker.stack:
            structural.append({"page": name, "errors": checker.errors[:5],
                               "unclosed_at_end": checker.stack[:5]})

    # the repository-root redirect used by the legacy branch-based Pages deploy
    root_index = os.path.join(ROOT, "index.html")
    if os.path.exists(root_index):
        with open(root_index, encoding="utf-8") as fh:
            rtext = fh.read()
        for href in re.findall(r'(?:href|content)="([^"]+)"', rtext):
            target = href.split("url=")[-1].split("#")[0]
            if target.startswith(("http", "mailto:", "#", "data:")) or not target:
                continue
            if not os.path.exists(os.path.join(ROOT, target)):
                broken.append(("index.html (root redirect)", target))

    # every page must be reachable from the navigation bar on every page
    nav_pages = set()
    if pages:
        with open(os.path.join(DOCS, "index.html"), encoding="utf-8") as fh:
            idx = fh.read()
        m = re.search(r'<nav class="main">(.*?)</nav>', idx, re.S)
        if m:
            nav_pages = set(re.findall(r'href="([^"]+)"', m.group(1)))
    unreachable = sorted({os.path.basename(p) for p in pages} - nav_pages)

    result = {
        "generated_utc": "2026-11-01",
        "pages_checked": len(pages),
        "internal_links_checked": len(internal_targets),
        "broken_internal_links": broken,
        "external_links_checked": len(ext_seen),
        "unregistered_external_links": unregistered,
        "structural_errors": structural,
        "pages_not_in_navigation": unreachable,
        "status": "PASS" if not (broken or unregistered or structural or unreachable) else "FAIL",
    }
    os.makedirs(REPORTS, exist_ok=True)
    with open(os.path.join(REPORTS, "linkcheck.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=1)
    print(json.dumps({k: v for k, v in result.items() if k != "generated_utc"}, indent=1)[:2000])
    if result["status"] != "PASS":
        sys.exit(1)


if __name__ == "__main__":
    main()
