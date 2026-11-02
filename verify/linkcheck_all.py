#!/usr/bin/env python3
"""Repo-wide link integrity check for every published HTML page.

No existing checker in this repository covers the whole published surface: each session
checks only its own directory. GitHub Pages here is a legacy branch deploy from ``main:/``,
so *every* directory in this repository is served. A relative link that resolves inside one
session's folder can still 404 on the live site, and a mirrored page (``site/prior/``,
``site/prior-d118ca7e/``) inherits the navigation of the page it was copied from.

This checker walks every tracked ``*.html`` file, resolves each local ``href``/``src``
against the file's own directory, and fails if the target does not exist (case-sensitively,
as Pages does on Linux). External links are counted and grouped by host so the report can
show which claims rest on official domains and which rest on a data mirror.

Usage:
    python3 verify/linkcheck_all.py            # human-readable summary
    python3 verify/linkcheck_all.py --json     # machine-readable report to stdout
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv"}

# Domains that are the primary publisher for a fact used on this site.
OFFICIAL_HOSTS = {
    "www.nfl.com": "NFL league site (rules, standings, schedules)",
    "nfl.com": "NFL league site",
    "operations.nfl.com": "NFL football operations (rule book, game operations)",
    "support.nfl.com": "NFL support (records, stats directory)",
    "static.www.nfl.com": "NFL-hosted documents (gamebooks, rulebook PDFs)",
    "nextgenstats.nfl.com": "NFL Next Gen Stats",
    "www.weather.gov": "US National Weather Service",
    "www.itl.nist.gov": "NIST (statistical methods)",
    "tsapps.nist.gov": "NIST (statistical methods)",
    "www.ecfr.gov": "US Code of Federal Regulations",
    "www.leg.state.nv.us": "Nevada gaming statutes",
    "www.draftkings.com": "Licensed sportsbook operator",
    "sportsbook.draftkings.com": "Licensed sportsbook operator",
    "support.draftkings.com": "Licensed sportsbook operator help",
    "help.draftkings.com": "Licensed sportsbook operator help",
    "www.fanduel.com": "Licensed sportsbook operator",
    "support.fanduel.com": "Licensed sportsbook operator help",
    "www.betmgm.com": "Licensed sportsbook operator",
    "www.caesars.com": "Licensed sportsbook operator",
    "www.cdc.gov": "US Centers for Disease Control and Prevention",
    "massgaming.com": "Massachusetts Gaming Commission (regulator)",
    "pmc.ncbi.nlm.nih.gov": "US National Library of Medicine (peer-reviewed index)",
}
SECONDARY_HOSTS = {
    "www.pro-football-reference.com": "Reputable third-party reference — NOT a league or operator publication",
    "docs.github.com": "Platform documentation",
}
DATASET_HOSTS = {
    "github.com": "Open third-party dataset / code (nflverse) — not an official league publication",
    "raw.githubusercontent.com": "Open third-party dataset mirror — not an official league publication",
    "codeload.github.com": "Open third-party dataset archive — not an official league publication",
    "release-assets.githubusercontent.com": "Open third-party dataset asset host — not an official league publication",
}


PROJECT_BASE = "/Korea3/"


class LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []  # (tag-attribute, value)
        self.base: str | None = None
        self._in_style = False
        self._in_script = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "base" and d.get("href"):
            # A mirrored page can relocate every relative link with <base href>.
            # Resolving from the file's own directory would report false breakage.
            self.base = d["href"]
            return
        if tag in {"a", "link"} and d.get("href"):
            self.links.append((f"{tag}[href]", d["href"]))
        elif tag in {"img", "script", "iframe", "source"} and d.get("src"):
            self.links.append((f"{tag}[src]", d["src"]))
        elif tag == "form" and d.get("action"):
            self.links.append(("form[action]", d["action"]))
        if tag == "style":
            self._in_style = True
        if tag == "script":
            self._in_script = True

    def handle_endtag(self, tag):
        if tag == "style":
            self._in_style = False
        if tag == "script":
            self._in_script = False


def html_files() -> list[Path]:
    out = []
    for p in ROOT.rglob("*.html"):
        if any(part in SKIP_DIRS for part in p.parts):
            continue
        out.append(p)
    return sorted(out)


def analyse() -> dict:
    pages = html_files()
    broken: list[dict] = []
    external: Counter = Counter()
    external_by_page: dict[str, list[str]] = defaultdict(list)
    local_checked = 0
    official_rows = 0

    for page in pages:
        rel_page = page.relative_to(ROOT).as_posix()
        parser = LinkParser()
        try:
            parser.feed(page.read_text(encoding="utf-8", errors="replace"))
        except Exception as exc:  # pragma: no cover - defensive
            broken.append({"page": rel_page, "href": "", "attr": "parse", "reason": str(exc)})
            continue

        for attr, raw in parser.links:
            href = (raw or "").strip()
            if not href:
                continue
            low = href.lower()
            if low.startswith(("mailto:", "tel:", "javascript:", "data:")):
                continue
            # A page-level <base href> relocates every relative link on the page.
            base_dir = page.parent
            if parser.base and parser.base.startswith("/"):
                if parser.base.startswith(PROJECT_BASE):
                    base_dir = ROOT / parser.base[len(PROJECT_BASE):]
                else:
                    broken.append({"page": rel_page, "href": parser.base, "attr": "base[href]",
                                   "reason": f"base path is outside the project base {PROJECT_BASE}"})
            elif parser.base:
                base_dir = (page.parent / parser.base).resolve()
            # Strip a URL fragment before resolving; record the anchor form for reporting.
            target_part, _, fragment = href.partition("#")
            if href.startswith("#"):
                local_checked += 1
                if fragment and f'id="{fragment}"' not in page.read_text(encoding="utf-8", errors="replace"):
                    broken.append({"page": rel_page, "href": href, "attr": attr,
                                   "reason": "anchor not found on page"})
                continue
            split = urlsplit(href)
            if split.scheme in {"http", "https"}:
                host = split.netloc.lower()
                external[host] += 1
                external_by_page[rel_page].append(href)
                if host in OFFICIAL_HOSTS:
                    official_rows += 1
                continue
            if split.scheme or href.startswith("//"):
                continue  # unrelated schemes
            local_checked += 1
            rel_target = unquote(split.path)
            if not rel_target:
                continue
            if rel_target.startswith("/"):
                # Site-absolute. On a GitHub project site only /<repo>/... resolves
                # under this project; anything else points outside the deployment.
                if rel_target.startswith(PROJECT_BASE):
                    target = (ROOT / rel_target[len(PROJECT_BASE):]).resolve()
                else:
                    broken.append({"page": rel_page, "href": href, "attr": attr,
                                   "reason": f"site-absolute link outside {PROJECT_BASE}"})
                    continue
            else:
                target = (base_dir / rel_target).resolve()
            # A directory target must contain index.html (Pages serves it).
            if target.is_dir():
                target = target / "index.html"
            try:
                inside = target.is_relative_to(ROOT)
            except AttributeError:  # pragma: no cover - py<3.9
                inside = str(target).startswith(str(ROOT))
            if not inside:
                broken.append({"page": rel_page, "href": href, "attr": attr,
                               "reason": "escapes repository root"})
            elif not target.exists():
                broken.append({
                    "page": rel_page, "href": href, "attr": attr,
                    "reason": "target missing", "resolved": target.relative_to(ROOT).as_posix(),
                })

    # Missing assets referenced from CSS (url(...)) are checked too.
    for css in ROOT.rglob("*.css"):
        if any(part in SKIP_DIRS for part in css.parts):
            continue
        text = css.read_text(encoding="utf-8", errors="replace")
        for url in re.findall(r"url\(\s*['\"]?([^'\")]+)['\"]?\s*\)", text):
            if url.startswith(("http://", "https://", "data:")):
                continue
            local_checked += 1
            target = (css.parent / url.split("#")[0].split("?")[0]).resolve()
            if not target.exists():
                broken.append({"page": css.relative_to(ROOT).as_posix(), "href": url,
                               "attr": "css url()", "reason": "target missing"})

    by_dir: dict[str, int] = Counter()
    for b in broken:
        by_dir[b["page"].rsplit("/", 1)[0] if "/" in b["page"] else "."] += 1

    return {
        "pages_checked": len(pages),
        "local_links_checked": local_checked,
        "broken_count": len(broken),
        "broken": broken,
        "broken_by_directory": dict(sorted(by_dir.items())),
        "external_hosts": dict(external.most_common()),
        "external_link_count": sum(external.values()),
        "official_link_count": official_rows,
        "offsite_pages": sorted(external_by_page),
        "host_classes": {
            host: ("official" if host in OFFICIAL_HOSTS
                   else "dataset" if host in DATASET_HOSTS
                   else "secondary" if host in SECONDARY_HOSTS
                   else "other")
            for host in external
        },
        "status": "PASS" if not broken else "FAIL",
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    report = analyse()
    out = ROOT / "verify" / "linkcheck.report.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(report, indent=2))
        return 0 if report["status"] == "PASS" else 1

    print(f"pages checked            {report['pages_checked']}")
    print(f"local links checked      {report['local_links_checked']}")
    print(f"external links           {report['external_link_count']} across {len(report['external_hosts'])} hosts")
    print(f"  of which official      {report['official_link_count']}")
    print(f"broken local links       {report['broken_count']}")
    for b in report["broken"][:40]:
        print(f"  - {b['page']}: {b['attr']} '{b['href']}' — {b['reason']}"
              + (f" -> {b['resolved']}" if b.get("resolved") else ""))
    if report["broken_count"] > 40:
        print(f"  ... {report['broken_count'] - 40} more in verify/linkcheck.report.json")
    print(f"status                   {report['status']}")
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
