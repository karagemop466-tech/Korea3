#!/usr/bin/env python3
"""Repo-wide internal-link audit: every *.html, every href/src that is local
must resolve to an existing file (relative to the page). External links are
inventoried by domain, not fetched (sandbox egress is restricted; official
sources were re-opened separately via the web-fetch tool on 2026-11-02)."""
import json, os, re, sys
from collections import Counter
from urllib.parse import urlparse, unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pages, broken, ext = [], [], Counter()
for dp, dns, fns in os.walk(ROOT):
    if ".git" in dp or ".venv" in dp: continue
    for fn in fns:
        if fn.endswith(".html"): pages.append(os.path.join(dp, fn))
for pg in sorted(pages):
    html = open(pg, encoding="utf-8", errors="ignore").read()
    _base = re.search(r'<base[^>]+href="([^"]+)"', html)
    base_root = _base.group(1).strip("/") if _base else None  # e.g. "Korea3" -> resolve vs repo root
    for m in re.finditer(r'(?:href|src)="([^"]+)"', html):
        u = m.group(1).strip()
        if not u or u.startswith(("#", "mailto:", "tel:", "javascript:", "data:")): continue
        if u.startswith(("http://", "https://", "//")):
            ext[urlparse(u if not u.startswith("//") else "https:" + u).netloc] += 1; continue
        if u.startswith("/Korea3/"):  # Pages serves the repo under /Korea3/
            u = u[len("/Korea3/"):] or "index.html"
            target = os.path.normpath(os.path.join(ROOT, unquote(urlparse(u).path)))
            if os.path.isdir(target): target = os.path.join(target, "index.html")
            if not os.path.exists(target):
                broken.append({"page": os.path.relpath(pg, ROOT), "href": m.group(1).strip()})
            continue
        path = unquote(urlparse(u).path)
        if not path: continue
        _from = ROOT if base_root else os.path.dirname(pg)  # <base href="/Korea3/"> semantics on Pages
        target = os.path.normpath(os.path.join(_from, path))
        if os.path.isdir(target): target = os.path.join(target, "index.html")
        if not os.path.exists(target):
            broken.append({"page": os.path.relpath(pg, ROOT), "href": u})
def _cat(b):
    if b["page"].startswith("site/prior/") or b["page"].startswith("site/prior-d118ca7e/"):
        return "archive_mirror_preservation_copy"
    if b["page"].startswith("audit/"):
        return "audit_owned_open_pr_19"
    return "live_surface"
for b in broken: b["category"] = _cat(b)
live = [b for b in broken if b["category"] == "live_surface"]
out = {"pages_scanned": len(pages), "broken_internal_links": broken, "live_surface_broken": live,
       "external_link_domains": dict(ext.most_common()),
       "status": "PASS" if not live else "FAIL"}
json.dump(out, open(os.path.join(ROOT, "verification/link_audit.json"), "w"), indent=1)
print(f"{len(pages)} pages, {len(broken)} broken internal links, {sum(ext.values())} external links across {len(ext)} domains")
for b in broken[:30]: print("BROKEN:", b)
sys.exit(1 if live else 0)
