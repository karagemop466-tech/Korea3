#!/usr/bin/env python3
"""Rebuild origin_lab end to end, then run the gate.

Order matters: each stage writes the file the next stage reads. Nothing here touches the network and
nothing here writes outside origin_lab/.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent

STAGES = [
    "parse_official.py",     # official 2026 capture -> verified results feed + standings reconciliation
    "build_snapshots.py",    # requirement 1 price snapshots + requirement 2 results feed
    "originate.py",          # requirements 3 and 4: origination order, fair / market / difference
    "leaderboard.py",        # requirement 5: signal vs staking
    "build_depth.py",        # requirement 6: depth of the replacement
    "correlations.py",       # requirement 7: officially sourced correlations with n
    "build_gates.py",        # requirement 8: promotion and demotion gates
    "registers.py",          # questions, suggestions and flags
    "build.py",              # pages
    "check.py",              # the gate
]


def main() -> int:
    for stage in STAGES:
        print("=" * 74)
        print("origin_lab/" + stage)
        print("=" * 74)
        r = subprocess.run([sys.executable, stage], cwd=str(BASE))
        if r.returncode != 0:
            print(f"\nFAILED at {stage} (exit {r.returncode})")
            return r.returncode
    print("\norigin_lab: all stages completed and the gate passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
