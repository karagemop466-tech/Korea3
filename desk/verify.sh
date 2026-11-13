#!/bin/sh
# Everything the desk claims, verified in one command, in the order CI runs it.
#
#   ./desk/verify.sh
#
# Exits non-zero on the first failure and prints the last lines of the command that failed,
# so this is usable as a pre-push hook: `./desk/verify.sh || exit 1`.
set -e
cd "$(dirname "$0")/.."          # run from the repository root, like every CI step does
LOG=$(mktemp)
trap 'rm -f "$LOG"' EXIT

run() {
    name=$1
    shift
    printf '== %s\n' "$name"
    if "$@" > "$LOG" 2>&1; then
        tail -2 "$LOG"
    else
        status=$?
        printf 'FAILED (%s) - %s\n' "$name" "$status"
        tail -14 "$LOG"
        exit "$status"
    fi
}

run "desk: re-derive the ledger from the repository artifacts" python3 desk/build_ledger.py
run "desk: rebuild the pages"                                   python3 desk/build.py
run "desk: verifier (R1-R18)"                                   python3 desk/check.py
run "site: every published row links a registered source" \
    python3 verify/source_audit.py --max-unsourced 0 --allow-dirs session-398c4b58,qa
run "site: link integrity across the whole tree"                python3 verify/linkcheck_all.py
run "site: hub dashboard"                                       python3 hub/check_hub.py
run "site: decision lab"                                        python3 decision_lab/check.py

printf '== desk: rebuild determinism\n'
python3 - <<'PY'
import pathlib, subprocess, sys
before = {p: p.read_bytes() for p in sorted(pathlib.Path("desk").glob("*.html"))}
subprocess.run([sys.executable, "desk/build.py"], check=True, capture_output=True)
after = {p: p.read_bytes() for p in sorted(pathlib.Path("desk").glob("*.html"))}
drift = [str(p) for p in before if before[p] != after[p]]
if drift:
    print("FAIL - a rebuild changed bytes:", ", ".join(drift))
    raise SystemExit(1)
print(f"determinism ok: {len(after)} pages, byte-identical across two builds")
PY
echo "PASS - desk verifier and every repository audit that covers it"
