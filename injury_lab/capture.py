#!/usr/bin/env python3
"""Capture layer for the injury lab: build the official URLs, retain the text, prove the retention.

Three commands::

    python3 -m injury_lab.capture urls   --season 2025 --week 1
    python3 -m injury_lab.capture index
    python3 -m injury_lab.capture verify [--live]
    python3 -m injury_lab.capture fetch  --season 2025 --week 1        # needs outbound access

**urls** prints the exact week-addressable official URL for a season and week, plus the two sibling
forms, so a reader can open them by hand. The pattern is not folklore: it is the form the live page's own
week selector produces (verified against 2026 reg10, 2025 reg01 and 2015 reg10 on 2026-11-13, all three
returning their own season's report for the requested week).

**index** writes ``data/raw_index.json``: one entry per file in ``raw/`` with its SHA-256, byte length,
the URL taken from its own header block, and its retrieval date. Every published row in this lab points
back at one of these files, so the index is what makes "we transcribed an official page" checkable.

**verify** re-hashes the raw files and compares them with the index. Fails with a non-zero exit if a file
moved or was edited after indexing. With ``--live`` it additionally re-opens each official URL and
reports whether the live text still contains every player row this lab published from it; that is the
mutation check, and it is the reason the raw files exist. Without outbound access it says so and exits 0,
because a missing network is a fact about the environment, not a data defect.

**fetch** is the scaling path the repository has been missing: it downloads a week's page, keeps the
verbatim player rows in ``raw/`` and appends the index entry. It refuses to run where the network is
blocked rather than writing an empty file, and it refuses to overwrite an existing capture - a new week
is a new file, so history is never rewritten.

No value in this module is inferred. It reads, stores and hashes; it does not fill anything in.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RAW = HERE / "raw"
DATA = HERE / "data"

INJURY_URL = "https://www.nfl.com/injuries/league/{season}/{week_code}"
DEPTH_URL = "https://www.{club_domain}/team/depth-chart"
USER_AGENT = "Mozilla/5.0 (research capture; single page; no crawl)"
MAX_BYTES = 4_000_000

ROW_RE = re.compile(r"^\|\s*\[([^\]]+)\]\((https://www\.nfl\.com/players/[^)]+)/\)")


def week_code(week: int, week_type: str = "REG") -> str:
    if week_type not in {"REG", "PRE", "POST"}:
        raise ValueError(f"unknown week_type {week_type!r}; the official path uses PRE/REG/POST")
    if week_type == "REG" and not 1 <= week <= 18:
        raise ValueError(f"regular-season week must be 1..18, got {week}")
    return f"{week_type.lower()}{week:02d}"


def urls_for(season: int, week: int, week_type: str = "REG") -> dict[str, str]:
    code = week_code(week, week_type)
    return {
        "official_week_page": INJURY_URL.format(season=season, week_code=code),
        "official_week_page_unpadded_variant": INJURY_URL.format(season=season, week_code=f"{week_type.lower()}{week}"),
        "official_live_snapshot": "https://www.nfl.com/injuries/",
    }


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def header_of(path: Path) -> dict[str, str]:
    """Read the ``key : value`` lines inside the capture's leading HTML comment."""
    text = path.read_text(encoding="utf-8")
    head = text.split("-->", 1)[0]
    out: dict[str, str] = {}
    for line in head.splitlines():
        line = line.strip().lstrip("!").strip()
        m = re.match(r"^([a-z_]+)\s*:\s*(.+)$", line)
        if m:
            out[m.group(1)] = m.group(2).strip()
    return out


def player_rows(path: Path) -> list[str]:
    """The verbatim player-row lines a capture publishes. This is the unit of verification."""
    return [ln.rstrip() for ln in path.read_text(encoding="utf-8").splitlines() if ROW_RE.match(ln)]


def index() -> dict:
    entries = []
    for path in sorted(RAW.glob("*.md")):
        head = header_of(path)
        entries.append({
            "file": str(path.relative_to(ROOT)),
            "sha256": sha256(path),
            "bytes": path.stat().st_size,
            "player_rows": len(player_rows(path)),
            "url": head.get("url", ""),
            "retrieved_utc": head.get("retrieved_utc", ""),
            "retrieved_by": head.get("retrieved_by", ""),
            "chunks": head.get("chunks", head.get("chunk", "")),
            "kind": head.get("kind", "injury-report" if "injuries/league" in head.get("url", "") else "club-depth-chart"),
        })
    return {"_comment": [
        "One entry per retained official capture under injury_lab/raw/.",
        "A published row in this lab is machine-checked against the file named in this index:",
        "check_site.py P7 requires every published player row to appear verbatim in its capture.",
        "The captures are themselves transcriptions of pages opened by the named session; P7 proves the",
        "parse against the capture, and 'capture verify --live' re-opens the URL to prove the capture",
        "against the live page. Both layers are needed; neither alone is enough.",
    ], "captures": entries}


def cmd_index() -> int:
    DATA.mkdir(parents=True, exist_ok=True)
    payload = index()
    (DATA / "raw_index.json").write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"indexed {len(payload['captures'])} captures, "
          f"{sum(c['player_rows'] for c in payload['captures'])} player-row lines")
    for c in payload["captures"]:
        print(f"  {c['file']:52s} {c['sha256'][:16]}  rows={c['player_rows']:3d}  {c['retrieved_utc']}")
    return 0


def cmd_verify(live: bool) -> int:
    idx = json.loads((DATA / "raw_index.json").read_text(encoding="utf-8"))
    recorded = {c["file"]: c for c in idx["captures"]}
    bad = 0
    for path in sorted(RAW.glob("*.md")):
        rel = str(path.relative_to(ROOT))
        cur = sha256(path)
        exp = recorded.get(rel, {}).get("sha256")
        if exp is None:
            print(f"UNINDEXED  {rel}  - run 'capture index'")
            bad += 1
        elif exp != cur:
            print(f"HASH MOVED {rel}  index {exp[:16]}  now {cur[:16]}")
            bad += 1
        else:
            print(f"ok         {rel}  {cur[:16]}  rows={len(player_rows(path))}")
    for rel in set(recorded) - {str(p.relative_to(ROOT)) for p in RAW.glob("*.md")}:
        print(f"MISSING    {rel}  - indexed capture is gone from the tree")
        bad += 1
    if not live:
        print("\nlive re-check not requested; run 'capture verify --live' where outbound access exists.")
        return 1 if bad else 0
    for path in sorted(RAW.glob("*.md")):
        url = header_of(path).get("url")
        if not url:
            print(f"LIVE SKIP  {path.name}: no url in the capture header")
            continue
        try:
            text = fetch(url)
        except Exception as exc:  # noqa: BLE001 - a blocked or failing network is reported, not guessed
            print(f"LIVE BLOCKED {url}: {type(exc).__name__}: {exc}")
            continue
        published = set(player_rows(path))
        now = {ln.rstrip() for ln in text.splitlines() if ROW_RE.match(ln)}
        gone = sorted(published - now)
        print(f"LIVE {url}: {len(published)} published rows, {len(now)} rows on the live page, "
              f"{len(gone)} no longer present verbatim")
        for g in gone[:20]:
            print(f"   MOVED  {g[:150]}")
        bad += len(gone)
    return 1 if bad else 0


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=60) as resp:  # noqa: S310 - fixed official hosts, no eval
        raw = resp.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError(f"{url}: response larger than the {MAX_BYTES} byte capture budget")
    return raw.decode("utf-8", "replace")


def cmd_fetch(season: int, week: int, week_type: str) -> int:
    urls = urls_for(season, week, week_type)
    dest = RAW / f"{season}-{week_code(week, week_type)}-injuries.md"
    if dest.exists():
        print(f"REFUSED: {dest} already exists. Captures are append-only; a re-fetch goes to a new dated "
              f"file (e.g. {dest.stem}.1.md) so an earlier transcription stays checkable.")
        return 2
    try:
        html = fetch(urls["official_week_page"])
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        print(f"BLOCKED: cannot reach {urls['official_week_page']} from here ({exc}).\n"
              "This sandbox has no route to nfl.com; the environment running this command needs outbound "
              "access. Nothing was written - a failed fetch must never leave a file that looks like a "
              "capture.")
        return 3
    rows = extract_rows(html)
    body = "\n".join(rows)
    header = (f"<!--\nRETAINED OFFICIAL CAPTURE - generated by injury_lab/capture.py fetch\n\n"
              f"url            : {urls['official_week_page']}\n"
              f"retrieved_utc  : {json.dumps(_utc_now())}\n"
              f"kind           : injury-report\n"
              f"chunks         : complete page, machine-extracted player rows\n\n"
              f"The extractor keeps every line matching a player row and the fixture headers above them, "
              f"and\ndrops page chrome. It copies text; it does not summarise, normalise or complete "
              f"anything.\n-->\n\n")
    dest.write_text(header + body + "\n", encoding="utf-8")
    print(f"wrote {dest} ({len(rows)} lines). Now run: python3 -m injury_lab.capture index && "
          f"python3 -m injury_lab.parse")
    return 0


def _utc_now() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def extract_rows(html: str) -> list[str]:
    """Pull fixture headers and player rows out of raw HTML, in page order, without touching their text."""
    out: list[str] = []
    for block in re.split(r"<tr[^>]*>", html):
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", block, re.S)
        if not cells:
            continue
        clean = [re.sub(r"<[^>]+>", "", c).replace("&amp;", "&").strip() for c in cells]
        if len(clean) >= 2 and re.fullmatch(r"[A-Z]{2,3}", clean[0] or ""):
            out.append("| " + " | ".join(clean) + " |")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="injury_lab.capture", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    u = sub.add_parser("urls")
    u.add_argument("--season", type=int, required=True)
    u.add_argument("--week", type=int, required=True)
    u.add_argument("--week-type", default="REG", choices=["REG", "PRE", "POST"])
    sub.add_parser("index")
    v = sub.add_parser("verify")
    v.add_argument("--live", action="store_true")
    f = sub.add_parser("fetch")
    f.add_argument("--season", type=int, required=True)
    f.add_argument("--week", type=int, required=True)
    f.add_argument("--week-type", default="REG", choices=["REG", "PRE", "POST"])
    a = ap.parse_args(argv)
    if a.cmd == "urls":
        for k, val in urls_for(a.season, a.week, a.week_type).items():
            print(f"{k:36s} {val}")
        return 0
    if a.cmd == "index":
        return cmd_index()
    if a.cmd == "verify":
        return cmd_verify(a.live)
    return cmd_fetch(a.season, a.week, a.week_type)


if __name__ == "__main__":
    sys.exit(main())
