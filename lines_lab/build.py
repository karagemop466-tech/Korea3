#!/usr/bin/env python3
"""Build every page under lines_lab/.

Run:   python3 lines_lab/build.py
Then:  python3 lines_lab/check.py

Deterministic: the same checkout produces byte-identical output. No clock is read, no
network is touched, no randomness is used, and no value is typed in by hand.
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from lines_lab import evidence as EV          # noqa: E402
from lines_lab import pages_body as PB        # noqa: E402
from lines_lab.pages import OUT, PAGES        # noqa: E402

BUILDERS = [
    ("index.html", PB.overview),
    ("executive.html", PB.executive),
    ("findings.html", PB.findings),
    ("snapshots.html", PB.snapshots),
    ("results.html", PB.results),
    ("fair-vs-market.html", PB.fair_vs_market),
    ("signals.html", PB.signals_page),
    ("leaderboard.html", PB.leaderboard_page),
    ("demotion.html", PB.demotion_page),
    ("correlations.html", PB.correlations_page),
    ("parlays.html", PB.parlays_page),
    ("depth.html", PB.depth_page),
    ("sources.html", PB.sources_page),
    ("verification.html", PB.verification_page),
    ("suggestions.html", PB.suggestions_page),
    ("questions.html", PB.questions_page),
    ("flagged.html", PB.flagged_page),
]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    e = EV.build()
    written = []
    for name, fn in BUILDERS:
        html_text = fn(e)
        (OUT / name).write_text(html_text, encoding="utf-8")
        written.append((name, len(html_text)))
    # .nojekyll so GitHub Pages serves the directory verbatim
    (OUT / ".nojekyll").write_text("", encoding="utf-8")
    total = sum(n for _, n in written)
    print(f"built {len(written)} pages, {total:,} bytes")
    for name, n in written:
        print(f"  {name:<24}{n:>9,}")
    missing = sorted(set(PAGES) - {n for n, _ in written})
    if missing:
        print(f"  ERROR: navigation lists pages that were not built: {missing}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
