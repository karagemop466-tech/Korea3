#!/usr/bin/env python3
"""Fetch the pinned nflverse/nfldata snapshot and write a provenance manifest.

Why this source
---------------
The nflverse `games.csv` file in the `nflverse/nfldata` repository is the dataset
that the nflverse `nflreadr::load_schedules()` function loads (see
nflreadr/R/load_schedules.R, which reads
https://github.com/nflverse/nfldata/raw/master/data/games.rds). It is the
canonical open distribution of NFL game results and closing lines that the
nflverse project maintains, and its fields are documented in
nflverse/nflreadr/data-raw/dictionary_schedules.csv.

Every input is pinned to one commit, hashed, and counted so that any published
number can be traced back to a byte-identical file.

Only files that matter for the analysis are copied into data/raw/.
Nothing is inferred: if a field is missing in the source, it stays missing.
"""
from __future__ import annotations

import hashlib
import io
import json
import shutil
import tarfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

REPO = "nflverse/nfldata"
COMMIT = "a270278f3ac4e937295fe6a27814b3c4a2b62645"  # Automated data update, 2026-11-01T13:05:15Z
TARBALL = f"https://codeload.github.com/{REPO}/tar.gz/{COMMIT}"
BLOB = f"https://github.com/{REPO}/blob/{COMMIT}/data/"

FILES = [
    "games.csv",           # schedules, results, closing spread/total/moneyline prices
    "closing_lines.csv",   # 2006-2018 closing lines incl. moneyline prices (cross-check input)
    "initial_lines.csv",   # 2021 opening lines (single book) for closing-line-value study
    "win_totals.csv",      # preseason season win-total futures, 2003-2020
    "teams.csv",           # nflverse team metadata (names, ids)
]

BASE = Path(__file__).resolve().parent
ROOT = BASE.parent
RAW = BASE / "data" / "raw"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def count_rows(path: Path) -> int:
    with path.open("rb") as fh:
        return max(sum(1 for _ in fh) - 1, 0)


def main() -> int:
    RAW.mkdir(parents=True, exist_ok=True)
    print(f"fetching {TARBALL}")
    with urllib.request.urlopen(TARBALL, timeout=300) as resp:  # noqa: S310 - fixed host
        payload = resp.read()
    print(f"  {len(payload):,} bytes")

    entries = []
    with tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz") as tar:
        prefix = tar.getnames()[0].split("/")[0] + "/data/"
        for name in FILES:
            member = tar.getmember(prefix + name)
            dest = RAW / name
            with tar.extractfile(member) as src, dest.open("wb") as out:  # type: ignore[union-attr]
                shutil.copyfileobj(src, out)
            entries.append(
                {
                    "file": f"data/raw/{name}",
                    "source_url": BLOB + name,
                    "pinned_commit": COMMIT,
                    "sha256": sha256(dest),
                    "bytes": dest.stat().st_size,
                    "rows": count_rows(dest),
                }
            )
            print(f"  {name:<20} {dest.stat().st_size:>9,} bytes  {entries[-1]['rows']:>6,} rows")

    manifest = {
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repository": f"https://github.com/{REPO}",
        "pinned_commit": COMMIT,
        "commit_url": f"https://github.com/{REPO}/commit/{COMMIT}",
        "tarball_url": TARBALL,
        "license_note": (
            "nflverse data is released by the nflverse project (MIT-licensed code; data "
            "collected from NFL public sources). It is an independent open-source "
            "distribution, not an NFL-operated service. See the repository LICENSE and "
            "README for terms."
        ),
        "files": entries,
    }
    (RAW / "MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {RAW / 'MANIFEST.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
