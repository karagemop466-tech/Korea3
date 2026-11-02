#!/usr/bin/env python3
"""Causality, settlement and provenance tests. Run: python3 tests/test_causality.py

These are hard checks. If any assert fires, no strategy may be marked G2-pass.

Compatibility entry point. The maintained implementation lives in
``line_lab/tests/test_causality.py``: PR #13 moved the ``pipeline.markets`` and
``pipeline.core`` modules into ``line_lab/``, but this documented entry point
kept importing the deleted ``pipeline.*`` modules and failed on import (CI never
caught it because the workflows only collect ``tests/test_lab_*.py``). This
wrapper executes the maintained implementation so the command printed on the
root dashboard keeps working and the two copies cannot drift apart.

After a run it also mirrors ``tests.json`` (and the flag, present or absent)
from ``line_lab/data/derived/`` to ``data/derived/``, restoring the only writer
for the root copy of the report — the copy the QA session flagged as having
"no writer anywhere in the repo".
"""
from __future__ import annotations

import runpy
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "line_lab" / "tests" / "test_causality.py"


def main() -> int:
    sys.path.insert(0, str(ROOT))
    sys.argv[0] = str(TARGET)
    code = 0
    try:
        runpy.run_path(str(TARGET), run_name="__main__")
    except SystemExit as exc:  # the maintained script ends with SystemExit(main())
        raw = exc.code
        if raw is None:
            code = 0
        elif isinstance(raw, int):
            code = raw
        else:
            code = 1

    src = ROOT / "line_lab" / "data" / "derived"
    dst = ROOT / "data" / "derived"
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(src / "tests.json", dst / "tests.json")
    if (src / "causality_ok.flag").exists():
        shutil.copyfile(src / "causality_ok.flag", dst / "causality_ok.flag")
    else:
        (dst / "causality_ok.flag").unlink(missing_ok=True)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
