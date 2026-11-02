#!/usr/bin/env bash
# Rebuild every generated artifact and run every gate, in dependency order.
#
# The site embeds verification results (page counts, broken-link counts, row provenance), and the
# verification results are measured from the built site, so the build is a fixed point rather than a
# one-way pipeline. This script iterates the render/measure cycle until the outputs stop changing,
# then runs the gates with set -e.
#
#   bash verify/run_all.sh            # rebuild everything and gate it
#   bash verify/run_all.sh --check    # measure only (no rebuild), then gate
#
# Requires: numpy pandas scipy scikit-learn pytest
set -uo pipefail
cd "$(dirname "$0")/.."

MODE="${1:-build}"

report() { printf '\n=== %s ===\n' "$1"; }

if [ "$MODE" != "--check" ]; then
  report "1/5 rebuild dashboard data (line_lab)"
  python3 -m line_lab.run_all > /tmp/line_lab_run.log 2>&1 || { tail -20 /tmp/line_lab_run.log; exit 1; }
  tail -3 /tmp/line_lab_run.log

  report "2/5 rebuild reports/ and docs/"
  bash pipeline/run_all.sh > /tmp/pipeline_run.log 2>&1 || { tail -20 /tmp/pipeline_run.log; exit 1; }
  tail -2 /tmp/pipeline_run.log

  report "3/5 converge render/measure cycle"
  prev=""
  for pass in 1 2 3; do
    python3 -m line_lab.build_site > /dev/null || exit 1
    python3 scripts/build_site.py > /dev/null 2>&1 || exit 1
    python3 verify/recompute_claims.py --json > /dev/null 2>&1
    python3 verify/linkcheck_all.py --json  > /dev/null 2>&1
    python3 verify/source_audit.py  --json  > /dev/null 2>&1
    now=$(find . -path ./.git -prune -o -name '*.html' -print | sort | xargs sha256sum 2>/dev/null | sha256sum)
    echo "  pass $pass fingerprint ${now:0:16}"
    if [ "$now" = "$prev" ]; then echo "  converged after $pass passes"; break; fi
    prev="$now"
  done
fi

report "4/5 independent verification"
set -e
python3 verify/recompute_claims.py | tail -3
python3 verify/linkcheck_all.py    | tail -5
# 36 unsourced rows are a documented, published defect in the session-398c4b58 archive
# (non-numeric inventory and flag rows). The budget makes growth of that number fail the build.
python3 verify/source_audit.py --max-unsourced 36 | sed -n '1,6p' 

report "5/5 repository gates"
python3 line_lab/check_site.py
python3 scripts/verify_site.py | tail -2
python3 pipeline/link_check.py | tail -22
python3 -m nfl_lab.check_verified
python3 line_lab/tests/test_causality.py
python3 audit/check_audit_page.py | head -1
python3 -m pytest tests/test_lab_*.py -q 2>&1 | tail -2
printf '\nALL GATES PASSED\n'
