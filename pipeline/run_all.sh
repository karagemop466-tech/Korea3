#!/usr/bin/env bash
# Regenerate every report and the site from data/. Deterministic, no network, no manual input.
set -euo pipefail
cd "$(dirname "$0")"
python3 verify.py
python3 build_model.py > /dev/null
python3 run_strategies.py > /dev/null
python3 scan.py > /dev/null
python3 correlations.py > /dev/null
python3 props.py > /dev/null
python3 build_site.py
python3 link_check.py
echo "pipeline complete: reports/ and docs/ regenerated"
