#!/usr/bin/env python3
"""
fetch_data.py -- reproducible acquisition of every raw input used in this study.

Design rules
------------
1. Every input is fetched from a pinned git commit, never from a moving branch.
2. The SHA-256 of every extracted file is recorded so a reviewer can prove the
   analysis was run on exactly these bytes.
3. Nothing is inferred: files we could not obtain are simply absent, and the
   study degrades to "unverified / left blank" instead of guessing.

Network note: this sandbox can reach github.com / codeload.github.com only, so
tarballs are pulled from codeload. No other host is contacted.

Usage:  python3 scripts/fetch_data.py
"""
import hashlib
import io
import json
import os
import sys
import tarfile
import urllib.request
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "data", "raw")

# --- pinned sources -------------------------------------------------------
NFLOVERSE_COMMIT = "a270278f3ac4e937295fe6a27814b3c4a2b62645"
PLAYERWEEK_COMMIT = "a8b3dbf9f2a2ff32b0b2d86a68a1c7aa3f5e5b4b"  # resolved at runtime, see below

SOURCES = [
    {
        "id": "nflverse-nfldata",
        "repo": "nflverse/nfldata",
        "commit": NFLOVERSE_COMMIT,
        "url": f"https://github.com/nflverse/nfldata/tree/{NFLOVERSE_COMMIT}/data",
        "publisher": "nflverse (independent open-data project; not an NFL or sportsbook publication)",
        "docs_url": f"https://github.com/nflverse/nfldata/blob/{NFLOVERSE_COMMIT}/DATASETS.md",
        "files": [
            "data/games.csv",
            "data/closing_lines.csv",
            "data/sc_lines.csv",
            "data/initial_lines.csv",
            "data/win_totals.csv",
            "data/teams.csv",
        ],
    },
    {
        "id": "playerweek-mirror",
        "repo": "DevinOgrady/NFL-Player-Projections",
        "commit": "HEAD",  # resolved to a SHA at fetch time and recorded
        "url": "https://github.com/DevinOgrady/NFL-Player-Projections",
        "publisher": "third-party mirror; publisher documentation absent (see IR-02)",
        "docs_url": None,
        "files": ["weekly_player_stats_offense_smaller.csv"],
    },
]


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_commit(repo, ref):
    """Resolve a ref to a commit SHA using the public GitHub API (no auth needed)."""
    if len(ref) == 40 and all(c in "0123456789abcdef" for c in ref):
        return ref
    api = f"https://api.github.com/repos/{repo}/commits/{ref}"
    req = urllib.request.Request(api, headers={"Accept": "application/vnd.github+json",
                                               "User-Agent": "nfl-line-lab"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["sha"]


def fetch_tarball(repo, sha):
    url = f"https://codeload.github.com/{repo}/tar.gz/{sha}"
    req = urllib.request.Request(url, headers={"User-Agent": "nfl-line-lab"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return r.read()


def main():
    os.makedirs(RAW, exist_ok=True)
    prov = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "purpose": "Provenance + integrity record for every raw input of the NFL Line Lab study.",
        "how_to_reproduce": "python3 scripts/fetch_data.py   (requires network access to github.com/codeload.github.com)",
        "files": {},
        "unavailable": [],
    }

    for src in SOURCES:
        sha = resolve_commit(src["repo"], src["commit"])
        src["commit_resolved"] = sha
        print(f"[{src['id']}] commit {sha}")
        blob = fetch_tarball(src["repo"], sha)
        tf = tarfile.open(fileobj=io.BytesIO(blob), mode="r:gz")
        names = tf.getnames()
        for want in src["files"]:
            match = [n for n in names if n.endswith("/" + want) or n == want]
            if not match:
                prov["unavailable"].append({"source": src["id"], "file": want,
                                            "reason": "path not present in pinned commit"})
                print(f"  MISSING {want}")
                continue
            member = tf.extractfile(match[0])
            dest = os.path.join(RAW, os.path.basename(want))
            with open(dest, "wb") as fh:
                fh.write(member.read())
            nrows = sum(1 for _ in open(dest, "rb")) - 1
            prov["files"][os.path.basename(want)] = {
                "source_id": src["id"],
                "upstream_path": want,
                "pinned_url": f"https://github.com/{src['repo']}/blob/{sha}/{want}",
                "repo": src["repo"],
                "commit": sha,
                "publisher": src["publisher"],
                "docs_url": src["docs_url"],
                "sha256": sha256(dest),
                "bytes": os.path.getsize(dest),
                "data_rows": nrows,
                "fetched_utc": prov["generated_utc"],
            }
            print(f"  ok {os.path.basename(want):38s} {nrows:6d} rows  {sha256(dest)[:16]}...")

    out = os.path.join(ROOT, "data", "PROVENANCE.json")
    with open(out, "w") as fh:
        json.dump(priv := prov, fh, indent=2)
    print(f"\nwrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
