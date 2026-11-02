#!/usr/bin/env python3
"""Compatibility entry point for the causal / provenance checks.

Run: ``python3 tests/test_causality.py`` (or ``python3 line_lab/tests/test_causality.py``).

This path held a stale second copy of the suite whose imports pointed at
``pipeline.core`` and ``pipeline.markets`` — modules that do not exist, because that stack
moved into ``line_lab/``. The file therefore failed at import and tested nothing. Rather than
maintain two copies that can drift, this entry point runs the canonical suite in
``line_lab/tests/test_causality.py`` unchanged.

Verified: ``python3 tests/test_causality.py`` reproduces the same report
(``line_lab/data/derived/tests.json``) and the same pass/fail flag as the canonical path.
"""
from __future__ import annotations

import runpy
import sys
from pathlib import Path

CANONICAL = Path(__file__).resolve().parents[1] / "line_lab" / "tests" / "test_causality.py"

if not CANONICAL.is_file():  # pragma: no cover - guards a moved file
    sys.exit(f"canonical test suite not found at {CANONICAL}")

runpy.run_path(str(CANONICAL), run_name="__main__")
