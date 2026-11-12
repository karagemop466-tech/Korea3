"""Pinned-data acquisition and coverage accounting.

Why this file exists
--------------------
The analysis sandbox can reach ``github.com`` / ``codeload.github.com`` / ``api.github.com``
but **not** ``release-assets.githubusercontent.com``, which is where nflverse's release CSVs
actually live.  Instead of pretending, the fetcher below:

1. downloads each asset over HTTPS using ``GITHUB_TOKEN`` when present (CI) or anonymously;
2. verifies the SHA-256 against ``manifest.json`` when a digest is pinned, and otherwise
   records the first digest observed and refuses to accept a *different* file later;
3. writes ``data/injury_lab/manifest_observed.json`` with byte counts, row counts and hashes so
   a reviewer can audit exactly what the numbers were computed from;
4. prints an explicit coverage report — what was obtained, what was not, and why.  A missing
   asset is never imputed; the dependent analysis is reported as *blocked* on the site.

Run:  python3 -m decision_system.fetch            # fetch + verify
      python3 -m decision_system.fetch --check    # verify only, no network
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = Path(__file__).with_name("data") / "manifest.json"
OUT_DIR = ROOT / "data" / "injury_lab"
OBSERVED = OUT_DIR / "manifest_observed.json"
RELEASE_BASE = "https://github.com/nflverse/nflverse-data/releases/download"


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def _open(url: str, token: str | None):
    req = urllib.request.Request(url, headers={"User-Agent": "korea3-decision-system/1.0"})
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    req.add_header("Accept", "application/octet-stream")
    return urllib.request.urlopen(req, timeout=120)


def download(url: str, dest: Path, token: str | None, retries: int = 3) -> str | None:
    """Fetch ``url`` to ``dest``. Returns an error string on failure."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    last = ""
    for attempt in range(1, retries + 1):
        try:
            with _open(url, token) as resp, dest.open("wb") as fh:
                while True:
                    block = resp.read(1 << 20)
                    if not block:
                        break
                    fh.write(block)
            if dest.stat().st_size == 0:
                last = "empty response"
                continue
            return None
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            last = f"{type(exc).__name__}: {exc}"
    if dest.exists():
        dest.unlink(missing_ok=True)
    return last


def row_count(path: Path) -> int | None:
    try:
        with path.open("rb") as fh:
            n = sum(1 for _ in fh)
        return max(n - 1, 0)
    except OSError:
        return None


def load_manifest() -> dict:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def expected_hashes() -> dict[str, str]:
    """Digests read from the publisher's release API when available (see manifest)."""
    return json.loads(MANIFEST.read_text(encoding="utf-8")).get("expected_sha256", {})


def fetch_all(check_only: bool = False, quiet: bool = False) -> dict:
    manifest = load_manifest()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    observed = json.loads(OBSERVED.read_text(encoding="utf-8")) if OBSERVED.exists() else {}
    observed.setdefault("files", {})
    observed["checked_utc"] = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    seed = expected_hashes()
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    report = {"obtained": [], "missing": [], "mismatch": [], "reused": []}

    for group in manifest["assets"]:
        lib = group["id"]
        for entry in group["files"]:
            name = entry["name"]
            dest = OUT_DIR / lib / name
            rel = f"{lib}/{name}"
            prev = observed["files"].get(rel, {})
            digest = sha256(dest) if dest.exists() else ""
            if check_only:
                if not dest.exists():
                    report["missing"].append({"file": rel, "reason": "not downloaded (check mode)"})
                elif prev.get("sha256") and prev["sha256"] != digest:
                    report["mismatch"].append({"file": rel, "expected": prev["sha256"], "got": digest})
                else:
                    report["obtained"].append({"file": rel, "sha256": digest})
                continue

            err = download(f"{RELEASE_BASE}/{lib}/{name}", dest, token)
            if err:
                report["missing"].append({"file": rel, "reason": err,
                                          "url": f"{RELEASE_BASE}/{lib}/{name}"})
                continue
            digest = sha256(dest)
            want = seed.get(name) or prev.get("sha256")
            if want and want != digest:
                report["mismatch"].append({"file": rel, "expected": want, "got": digest})
                continue
            observed["files"][rel] = {
                "sha256": digest,
                "bytes": dest.stat().st_size,
                "rows": row_count(dest),
                "season": entry.get("season"),
                "url": f"{RELEASE_BASE}/{lib}/{name}",
                "release": group["release"],
                "tier": group["tier"],
            }
            report["obtained"].append({"file": rel, "sha256": digest})

    # in-repo pinned inputs: hash what is already there so the report is complete
    for entry in manifest["in_repo"]:
        p = ROOT / entry["path"]
        rel = entry["path"]
        if p.exists():
            observed["files"][rel] = {
                "sha256": sha256(p),
                "bytes": p.stat().st_size,
                "rows": row_count(p) if p.suffix == ".csv" else None,
                "url": entry.get("note", ""),
                "release": entry["tier"],
                "in_repo": True,
            }
            report["reused"].append({"file": rel, "sha256": observed["files"][rel]["sha256"]})
        else:
            report["missing"].append({"file": rel, "reason": "not present in repository"})

    observed["token_used"] = bool(token)
    observed["summary"] = {
        "obtained": len(report["obtained"]),
        "missing": len(report["missing"]),
        "mismatch": len(report["mismatch"]),
        "in_repo": len(report["reused"]),
    }
    OBSERVED.write_text(json.dumps(observed, indent=1, sort_keys=True), encoding="utf-8")
    if not quiet:
        print(json.dumps(observed["summary"], indent=1))
        for m in report["missing"]:
            print("MISSING", m["file"], "—", m["reason"])
        for m in report["mismatch"]:
            print("MISMATCH", m["file"], m["expected"], "!=", m["got"])
    return report


def coverage() -> dict:
    """Summarise what the analysis can actually use, by library and season."""
    manifest = load_manifest()
    observed = json.loads(OBSERVED.read_text(encoding="utf-8")) if OBSERVED.exists() else {"files": {}}
    present = set(observed.get("files", {}))
    out: dict[str, dict] = {}
    for group in manifest["assets"]:
        have, lack = [], []
        for entry in group["files"]:
            (have if f"{group['id']}/{entry['name']}" in present else lack).append(entry["season"])
        out[group["id"]] = {"have": sorted(have), "missing": sorted(lack)}
    return out


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="verify downloaded files only")
    args = ap.parse_args(argv)
    rep = fetch_all(check_only=args.check)
    if rep["mismatch"]:
        print("hash mismatch — refusing to continue", file=sys.stderr)
        return 1
    if args.check and rep["missing"]:
        print(f"check: {len(rep['missing'])} pinned files absent", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv[1:]))
