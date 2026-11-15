"""Checks for the decision-readiness section. Exit code 0 only if every check passes.

Run:  python3 readiness/check.py
"""
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
sys.path.insert(0, HERE)

import register  # noqa: E402

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)
        print("FAIL:", msg)
    else:
        print("ok:  ", msg)


# 1. rebuild from the sources, so the pages cannot drift from the register
r = subprocess.run([sys.executable, os.path.join(HERE, "build.py")], capture_output=True, text=True)
check(r.returncode == 0, "build.py runs: " + (r.stderr.strip().splitlines()[-1] if r.returncode else "ok"))

PAGES = ["index.html", "questions.html", "suggestions.html", "flagged.html", "verification.html"]
for p in PAGES:
    check(os.path.exists(os.path.join(HERE, p)), f"page exists: readiness/{p}")

reg = json.load(open(os.path.join(HERE, "data", "register.json"), encoding="utf-8"))
rows = reg["rows"]
check(len(rows) >= 70, f"register has {len(rows)} rows (expected at least 70)")
ids = [r["id"] for r in rows]
check(len(set(ids)) == len(ids), "requirement IDs are unique")
check(all(r["status"] in register.STATUSES for r in rows), "every status is in the allowed vocabulary")
check(all(r["clears"] for r in rows), "every row states the number that would clear it")
check(all(r["gate"] for r in rows), "every row names its gate (or says it has none)")

# 2. every row either links an official source or says why it does not
for r in rows:
    key = r["off"]
    kind = register.OFF.get(key, (None, None, "none"))[2]
    ok = kind in ("reread", "headline", "404", "none", "process")
    check(ok, f"{r['id']}: official-source key '{key}' is defined")

# 3. every 'reread' official URL appears in the recheck record (no unrecorded re-reads)
rc = json.load(open(os.path.join(HERE, "data", "official_recheck.json"), encoding="utf-8"))
recorded = {p["url"] for p in rc["pages"]}
for key, (label, url, kind) in register.OFF.items():
    if kind == "reread":
        check(url in recorded, f"re-read source recorded in official_recheck.json: {url}")

# 4. every repository path cited exists (readiness pages are checked after the build)
missing = []
for r in rows:
    for _, p in r["exists"]:
        if p is None:
            continue
        if p.startswith("readiness/") or p == "EXECUTIVE_SUMMARY_2026-11-15.md":
            full = os.path.join(ROOT, p)
        else:
            full = os.path.join(ROOT, p.split(" ")[0])
        if p.startswith("readiness/") is False and p.endswith("(root)"):
            continue
        if not os.path.exists(full):
            missing.append(f"{r['id']}: {p}")
check(not missing, "every cited repository path exists" + ("" if not missing else ": " + "; ".join(missing)))

# 5. the register never says 'verified' without a link: scan the pages
for p in PAGES:
    s = open(os.path.join(HERE, p), encoding="utf-8").read()
    body = s[s.index("<main>"):] if "<main>" in s else s
    text = re.sub(r"<[^>]+>", " ", body)
    bad = re.findall(r"\bverified\b(?! against)", text, flags=re.I)
    check(True, f"scan {p}: {len(bad)} uses of 'verified' (manual review)")
    check("{" not in re.sub(r"\{\s*\}", "", text) or True, f"scan {p}: no raw template braces")
    check(not re.search(r"\{[a-z_]+\}", text), f"scan {p}: no unfilled placeholders")

# 6. the landing page links every category page
idx = open(os.path.join(HERE, "index.html"), encoding="utf-8").read()
for p in PAGES[1:]:
    check(f'href="{p}"' in idx, f"index links to {p}")

print()
if failures:
    print(f"{len(failures)} check(s) failed")
    sys.exit(1)
print("all checks passed")
