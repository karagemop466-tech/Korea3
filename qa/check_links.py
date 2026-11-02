#!/usr/bin/env python3
"""Repository-wide link and asset integrity check for every deployed page.

Why this exists
---------------
Six independently built sites are published from this repository (`/`, `/site/`,
`/docs/`, `/audit/`, `/verified/`, `/session-398c4b58/`). Each build has its own
checker that validates *its own* pages. Nothing validated the links that cross a
build boundary, and nothing validated `<link rel=stylesheet>` / `<script src>` /
image assets at all. On 2026-11-02 that gap was hiding a broken stylesheet on a live
page: `audit/flagged.html` pointed at `../style.css`, a file deleted when the root
was regenerated as the `line_lab` dashboard.

What it checks
--------------
1. Every `href`/`src` in every tracked `*.html` file (all six deployments).
2. Internal targets must exist on disk, with exact case (GitHub Pages is
   case-sensitive; macOS/Windows filesystems are not).
3. Fragments (`page.html#id`, `#id`) must resolve to a real `id=`/`name=` target.
4. Directory-style targets (`/site/`) must resolve to an `index.html`.
5. GitHub links into this repository (`.../blob/<ref>/<path>`, `.../tree/<ref>/<path>`)
   must point at files or directories that exist here.
6. A per-deployment census: pages, internal links, external links, distinct hosts.

What it deliberately does not do
--------------------------------
It does not fetch non-GitHub external URLs. The sandbox this ran in can reach
github.com but not nfl.com, nist.gov or an operator help centre, so those links are
counted and listed as UNVERIFIED-OFFLINE rather than guessed at. Nothing is marked
verified without evidence.

Exit status is non-zero if any link is broken, so this can be used as a build gate.

Run:  python3 qa/check_links.py [--json qa/links.json]
"""

from __future__ import annotations

import argparse
import html.parser
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent.parent

# Deployment roots, so the report can say which live URL a broken link affects.
DEPLOYMENTS = {
    "root dashboard": "",
    "empirical pipeline": "site",
    "second build": "docs",
    "independent audit": "audit",
    "verified workbench": "verified",
    "session-398c4b58": "session-398c4b58",
}

REPO_BLOB = re.compile(
    r"^https?://github\.com/karagemop466-tech/Korea3/(blob|tree|raw)/[^/]+/(?P<path>.*)$"
)


class LinkParser(html.parser.HTMLParser):
    """Collect href/src attributes and the ids defined on the page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []  # (kind, value)
        self.ids: set[str] = set()
        self.base: str | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        d = dict(attrs)
        if "id" in d and d["id"]:
            self.ids.add(d["id"])
        if tag == "a" and d.get("name"):
            self.ids.add(d["name"])
        if tag == "base" and d.get("href"):
            self.base = d["href"]
        if tag == "a":
            if d.get("href"):
                self.links.append(("href", d["href"]))
        elif tag == "link":
            if d.get("href"):
                self.links.append(("asset", d["href"]))
        elif tag in ("script", "img", "source", "iframe", "video", "audio"):
            if d.get("src"):
                self.links.append(("asset", d["src"]))
            if tag == "img" and d.get("srcset"):
                for part in d["srcset"].split(","):
                    url = part.strip().split(" ")[0]
                    if url:
                        self.links.append(("asset", url))
        elif tag == "form" and d.get("action"):
            self.links.append(("href", d["action"]))


SKIP_DIRS = {".git", ".venv", "node_modules", "__pycache__", ".pytest_cache"}


def tracked_html() -> list[Path]:
    """Every HTML file that would be published from this tree.

    Walks the working tree rather than `git ls-files` so a page that exists but is not
    yet committed is still checked (that is how the qa/ pages were missed on the first run).
    """
    out = []
    for path in ROOT.rglob("*.html"):
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        out.append(path)
    return sorted(out)


PAGES_ROOT = "/Korea3/"  # GitHub Pages serves this repository under this path


def resolve(page_rel: str, base: str | None, path_part: str) -> Path:
    """Resolve an internal reference the way a browser on GitHub Pages would.

    - `<base href="/Korea3/">` on a page makes every relative link resolve against the
      repository root, not the page's own directory.
    - A path starting with `/Korea3/` is repository-root relative.
    - Any other leading `/` is also treated as repository-root relative (Pages serves
      the repo below its own path; a bare `/x` would 404 live, which is reported).
    """
    if path_part.startswith(PAGES_ROOT):
        return (ROOT / path_part[len(PAGES_ROOT) :]).resolve()
    if path_part.startswith("/"):
        return (ROOT / path_part.lstrip("/")).resolve()
    anchor = ROOT / page_rel
    anchor = anchor.parent
    if base:
        b = urlsplit(base)
        bpath = b.path
        if bpath.startswith(PAGES_ROOT):
            anchor = ROOT / bpath[len(PAGES_ROOT) :]
        elif bpath.startswith("/"):
            anchor = ROOT / bpath.lstrip("/")
        else:
            anchor = (ROOT / page_rel).parent / bpath
    return (anchor / path_part).resolve()


def deployment_of(rel: str) -> str:
    first = rel.split("/")[0]
    for name, prefix in DEPLOYMENTS.items():
        if prefix and first == prefix:
            return name
    if "/" not in rel:
        return "root dashboard"
    return f"other: {first}"


def exists_exact(path: Path) -> bool:
    """Path must exist with exact case, as GitHub Pages serves it."""
    if not path.exists():
        return False
    # Walk the components to enforce case sensitivity.
    cur = ROOT
    for part in path.relative_to(ROOT).parts:
        try:
            names = {p.name for p in cur.iterdir()}
        except (NotADirectoryError, FileNotFoundError):
            return False
        if part not in names:
            return False
        cur = cur / part
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="qa/links.json")
    args = ap.parse_args()

    pages = tracked_html()
    parsed: dict[str, LinkParser] = {}
    for page in pages:
        p = LinkParser()
        p.feed(page.read_text(encoding="utf-8", errors="replace"))
        parsed[page.relative_to(ROOT).as_posix()] = p

    broken: list[dict] = []
    external: Counter = Counter()
    hosts: Counter = Counter()
    by_deploy: dict[str, dict] = defaultdict(
        lambda: {"pages": 0, "internal_links": 0, "external_links": 0, "assets": 0}
    )
    github_repo_links: list[dict] = []

    for rel, parser in sorted(parsed.items()):
        deploy = deployment_of(rel)
        by_deploy[deploy]["pages"] += 1
        base = (ROOT / rel).parent

        for kind, raw in parser.links:
            value = raw.strip()
            if not value or value.startswith(("javascript:", "mailto:", "tel:", "data:")):
                continue
            parts = urlsplit(value)
            if parts.scheme in ("http", "https"):
                external[value] += 1
                hosts[parts.netloc] += 1
                by_deploy[deploy]["external_links"] += 1
                m = REPO_BLOB.match(value)
                if m:
                    target = unquote(m.group("path")).split("#")[0].split("?")[0]
                    ok = (ROOT / target).exists() if target else True
                    github_repo_links.append({"page": rel, "url": value, "path": target, "exists": ok})
                    if not ok:
                        broken.append(
                            {
                                "page": rel,
                                "deployment": deploy,
                                "link": value,
                                "kind": kind,
                                "reason": "GitHub path does not exist in this repository",
                            }
                        )
                continue
            if parts.scheme:
                continue  # unknown scheme, ignore

            # Internal reference.
            path_part = unquote(parts.path)
            frag = unquote(parts.fragment)
            if kind == "asset":
                by_deploy[deploy]["assets"] += 1
            else:
                by_deploy[deploy]["internal_links"] += 1

            if path_part in ("", ".") and frag:
                # Same-page anchor.
                if frag not in parser.ids:
                    broken.append(
                        {
                            "page": rel,
                            "deployment": deploy,
                            "link": value,
                            "kind": kind,
                            "reason": f"missing anchor #{frag} on the same page",
                        }
                    )
                continue

            target = resolve(rel, parser.base, path_part)
            # Directory-style link -> index.html
            if path_part.endswith("/") or target.is_dir():
                target = target / "index.html"
            try:
                target.relative_to(ROOT)
            except ValueError:
                broken.append(
                    {
                        "page": rel,
                        "deployment": deploy,
                        "link": value,
                        "kind": kind,
                        "reason": "resolves outside the published repository root",
                    }
                )
                continue

            if not exists_exact(target):
                broken.append(
                    {
                        "page": rel,
                        "deployment": deploy,
                        "link": value,
                        "kind": kind,
                        "reason": f"target does not exist: {target.relative_to(ROOT).as_posix()}",
                    }
                )
                continue

            if frag and target.suffix == ".html":
                trel = target.relative_to(ROOT).as_posix()
                ids = parsed[trel].ids if trel in parsed else set()
                if frag not in ids:
                    broken.append(
                        {
                            "page": rel,
                            "deployment": deploy,
                            "link": value,
                            "kind": kind,
                            "reason": f"anchor #{frag} not found in {trel}",
                        }
                    )

    # A page must be reachable: at least one internal in-link from another page,
    # or be a deployment index.
    inbound: Counter = Counter()
    for rel, parser in parsed.items():
        for _kind, raw in parser.links:
            parts = urlsplit(raw.strip())
            if parts.scheme or not parts.path or parts.path.startswith(("mailto:", "tel:")):
                continue
            target = resolve(rel, parser.base, unquote(parts.path))
            if parts.path.endswith("/") or target.is_dir():
                target = target / "index.html"
            if target.exists() and target.suffix == ".html":
                try:
                    t = target.relative_to(ROOT).as_posix()
                except ValueError:
                    continue
                if t != rel:
                    inbound[t] += 1

    orphans = [
        rel
        for rel in parsed
        if inbound[rel] == 0
        and Path(rel).name != "index.html"
        and deployment_of(rel) != "other: audit"  # audit pages are linked from flagged.html
    ]

    report = {
        "generated_by": "qa/check_links.py",
        "pages_checked": len(parsed),
        "internal_links_checked": sum(v["internal_links"] for v in by_deploy.values()),
        "assets_checked": sum(v["assets"] for v in by_deploy.values()),
        "external_links": len(external),
        "external_link_instances": sum(external.values()),
        "distinct_hosts": sorted(hosts),
        "github_repo_links_checked": len(github_repo_links),
        "broken": broken,
        "status": "PASS" if not broken else "FAIL",
        "by_deployment": dict(sorted(by_deploy.items())),
        "orphan_pages": sorted(orphans),
        "external_note": (
            "Non-GitHub external URLs are counted, not fetched: this sandbox can reach "
            "github.com only. They are listed in qa/sources.json and remain unverified."
        ),
    }

    out = ROOT / args.json
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n")

    print(f"pages checked            : {report['pages_checked']}")
    print(f"internal links checked   : {report['internal_links_checked']}")
    print(f"assets (css/js/img)      : {report['assets_checked']}")
    print(f"external links           : {report['external_link_instances']} instances / "
          f"{len(hosts)} hosts")
    print(f"GitHub repo links        : {report['github_repo_links_checked']}")
    print(f"broken links             : {len(broken)}")
    for b in broken:
        print(f"  FAIL {b['page']}: {b['link']} -> {b['reason']}")
    if orphans:
        print(f"orphan pages (no in-link): {len(orphans)}")
        for o in orphans:
            print(f"  ORPHAN {o}")
    print(f"status                   : {report['status']}")
    print(f"report                   : {args.json}")
    return 0 if not broken else 1


if __name__ == "__main__":
    sys.exit(main())
