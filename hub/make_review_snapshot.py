#!/usr/bin/env python3
"""Refresh hub/data/review_snapshot.json from the current checkout.

Run deliberately (not part of the deterministic build):
    python3 hub/make_review_snapshot.py
The commit hash and date are arguments so the snapshot is reproducible:
    python3 hub/make_review_snapshot.py 2026-11-02 <commit>
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "hub"
sys.path.insert(0, str(HUB))
from review_scan import scan  # noqa: E402

register = json.loads((HUB / "data/sources.json").read_text(encoding="utf-8"))
prefixes = tuple(register["official_prefixes"])

captured_utc = sys.argv[1] if len(sys.argv) > 1 else "2026-11-02"
base_commit = sys.argv[2] if len(sys.argv) > 2 else subprocess.check_output(
    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()

data = scan(ROOT, prefixes, captured_utc, base_commit)
(HUB / "data/review_snapshot.json").write_text(
    json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
print(f"snapshot: {len(data['directories'])} directories, {len(data['pages'])} HTML pages, "
      f"{sum(p['rows'] for p in data['pages'])} table rows, base {base_commit[:12]}")
