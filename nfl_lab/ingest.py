"""Collect public NFL-owned publications; never infer missing observations.

Run in CI because NFL hosts are not directly reachable from the interactive
sandbox. Every accepted row retains its NFL source URL. Source document hashes
and HTTP retrieval times are recorded separately from event kickoff times.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ALLOWED = {"www.nfl.com", "operations.nfl.com", "static.www.nfl.com"}
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "NFLResearchLab/0.2 (public-source academic research; no wagering)"})


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def fetch(url: str, binary: bool = False):
    if urlparse(url).scheme != "https" or urlparse(url).hostname not in ALLOWED:
        raise ValueError(f"Not an approved NFL publication host: {url}")
    for attempt in range(4):
        try:
            r = SESSION.get(url, timeout=60)
            if r.status_code in (429, 500, 502, 503, 504) and attempt < 3:
                time.sleep(2 ** (attempt + 1))
                continue
            r.raise_for_status()
            content = r.content
            record = {"url": url, "final_url": r.url, "retrieved_at": now(),
                      "sha256": hashlib.sha256(content).hexdigest(), "bytes": len(content),
                      "status": r.status_code, "etag": r.headers.get("ETag"),
                      "last_modified": r.headers.get("Last-Modified")}
            return (content if binary else r.text), record
        except requests.RequestException:
            if attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))
    raise RuntimeError("unreachable")


def next_data(html: str):
    soup = BeautifulSoup(html, "html.parser")
    node = soup.find("script", id="__NEXT_DATA__", type="application/json")
    return json.loads(node.string or node.get_text()) if node else None


def shape(obj, depth=0):
    if depth >= 5:
        return type(obj).__name__
    if isinstance(obj, dict):
        return {k: shape(v, depth+1) for k, v in obj.items()}
    if isinstance(obj, list):
        return [shape(obj[0], depth+1)] if obj else []
    return obj


def probe():
    out = DATA / "probe"
    out.mkdir(parents=True, exist_ok=True)
    urls = [
        "https://www.nfl.com/scores/2025/reg1",
        "https://www.nfl.com/games/cowboys-at-eagles-2025-reg-1?tab=stats",
        "https://www.nfl.com/games/cowboys-at-eagles-2025-reg-1",
    ]
    for i, url in enumerate(urls):
        html, provenance = fetch(url)
        (out / f"page-{i}.html").write_text(html)
        payload = next_data(html)
        (out / f"page-{i}.json").write_text(json.dumps(payload, indent=2))
        (out / f"shape-{i}.json").write_text(json.dumps(shape(payload), indent=2))
        (out / f"source-{i}.json").write_text(json.dumps(provenance, indent=2))
        soup = BeautifulSoup(html, "html.parser")
        links = sorted({a.get("href", "") for a in soup.find_all("a") if ".pdf" in a.get("href", "")})
        print(url, "next_data=", payload is not None, "pdfs=", links, flush=True)
        print(json.dumps(shape(payload), indent=2)[:30000], flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["probe", "collect"], default="probe")
    args = ap.parse_args()
    DATA.mkdir(exist_ok=True)
    if args.mode == "probe":
        probe()
    else:
        from nfl_lab.collect import collect
        collect()


if __name__ == "__main__":
    main()
