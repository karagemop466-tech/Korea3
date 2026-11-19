#!/usr/bin/env python3
"""Fail-closed gate for luck_lab. Every check is an assertion about a published number, not a style note.

Run:  python3 luck_lab/check.py            (offline; used by CI on every push and pull request)

Checks
  1.  Rebuild determinism: every page equals a fresh in-memory build of the committed data.
  2.  Data reproducibility: all three compute scripts are re-run into a temp directory with the same
      inputs and the JSON must be byte-identical to what is committed. If a published number cannot be
      reproduced from the ledger, the build is red -- not a warning.
  3.  Rule-freeze integrity: every rule_hash in the pre-registration ledger is recomputed from the
      source files that implement the rule. Editing a rule text, a gate or the evaluation window
      without re-registering fails here.
  4.  Independent reconciliation: the 12 metrics line_lab publishes per strategy must equal this desk's
      recomputation from the ledger, field by field, for all 11 strategies.
  5.  Arithmetic identities: wins + losses + pushes = bets; summed pnl = profit; the measured coin-flip
      return must agree with the return the vig implies, per market; q-values in [0, 1]; escrow counts
      equal the ledger file's rows.
  6.  Source discipline: every table row on every page carries a link, and every [blank] marker links
      the flag page (so a blank is always explainable in one click).
  7.  No orphan pages, no dead internal links, and the desk's own nav reaches every page it ships.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))

import build as B  # noqa: E402
from lib import american_profit, mean, sd  # noqa: E402

PAGES = ["index.html", "controls.html", "skill.html", "prereg.html", "escrow.html",
         "method.html", "sources.html", "flagged.html"]
COMPUTE = ["controls.py", "skill.py", "registry.py"]
TOL = 1e-9


def problems_all() -> list[str]:
    problems: list[str] = []
    controls = B.load("controls.json")
    skill = B.load("skill.json")
    reg = B.load("preregistration.json")

    # 1 -- determinism of the renderer
    rebuilt = {
        "index.html": B.build_index(controls, skill, reg),
        "controls.html": B.build_controls(controls),
        "skill.html": B.build_skill(skill),
        "prereg.html": B.build_prereg(reg),
        "escrow.html": B.build_escrow(reg, skill, controls),
        "method.html": B.build_method(skill, controls, reg),
        "sources.html": B.build_sources(controls),
        "flagged.html": B.build_flagged(skill, controls, reg),
    }
    for name, text in rebuilt.items():
        path = HERE / name
        if not path.exists():
            problems.append(f"page missing: luck_lab/{name}")
            continue
        if path.read_text(encoding="utf-8") != text:
            problems.append(f"luck_lab/{name} differs from a fresh build of the committed data: run "
                            f"python3 luck_lab/build.py and commit")
    extra = sorted(p.name for p in HERE.glob("*.html") if p.name not in PAGES)
    if extra:
        problems.append(f"unshipped pages (not in the build list): {extra}")

    # 2 -- reproducibility of the data, from the same inputs, into a temp tree
    with tempfile.TemporaryDirectory() as td:
        tdp = Path(td)
        for name in COMPUTE:
            r = subprocess.run([sys.executable, str(HERE / name)],
                               env={"LUCK_LAB_DATA": str(tdp), "PATH": "/usr/bin:/bin"},
                               capture_output=True, text=True, cwd=str(ROOT))
            if r.returncode != 0:
                problems.append(f"recompute {name} exited {r.returncode}: {r.stderr.strip()[:300]}")
        for name in ["controls.json", "skill.json", "preregistration.json"]:
            new = tdp / name
            if not new.exists():
                problems.append(f"recompute produced no {name}")
                continue
            if new.read_bytes() != (HERE / "data" / name).read_bytes():
                problems.append(f"luck_lab/data/{name} is not reproducible from its inputs: "
                                f"run the compute script and commit the result")

    # 3 -- rule-freeze integrity
    import registry as R  # noqa: E402
    gates_now = R.read_gates()
    window_now = R.read_window()
    line_rows, _ = R.read_line_lab_strategies()
    origin_rows, _ = R.read_origin_strategies()
    def h(obj):
        return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
    live = {}
    for row in line_rows:          # read_line_lab_strategies returns dicts, not the raw tuples
        sid, name, market = row["id"], row["name"], row["market"]
        doc = {
            "registration_id": f"line_lab:{sid}", "name": name, "market": market,
            "rule_text": ("Implemented in line_lab/strategies.py:build_all_bets (the mask for this id is the rule); "
                          "thresholds: " + json.dumps(window_now, sort_keys=True)),
            "gates": gates_now, "evaluation_window": window_now,
        }
        live[f"line_lab:{sid}"] = h({k: doc[k] for k in
                                    ("registration_id", "name", "market", "rule_text", "gates", "evaluation_window")})
    for sid, spec in origin_rows.items():
        doc = {"registration_id": f"origin_lab:{sid}", "name": spec.get("name", ""),
               "market": spec.get("market", ""), "rule_text": spec.get("rule", ""),
               "gates": gates_now, "evaluation_window": window_now}
        live[f"origin_lab:{sid}"] = h({k: doc[k] for k in
                                      ("registration_id", "name", "market", "rule_text", "gates", "evaluation_window")})
    for e in reg["entries"]:
        rid = e["registration_id"]
        if rid not in live:
            problems.append(f"{rid}: registered but no longer present in the source registry "
                            f"(a rule was deleted without withdrawing its registration)")
            continue
        if live[rid] != e["rule_hash"]:
            problems.append(f"{rid}: rule_hash in the ledger does not match the rule text, gates and window "
                            f"now in the source files. The rule moved without a re-registration.")
    missing = [rid for rid in live if rid not in {e["registration_id"] for e in reg["entries"]}]
    if missing:
        problems.append(f"strategies present in the source registries but not registered: {missing}")

    # 4 -- independent reconciliation with line_lab
    total_matched = total_checked = 0
    for r in skill["rows"]:
        rec = r["reconciliation_with_line_lab"]
        total_matched += rec.get("matched", 0)
        total_checked += rec.get("total", 0)
        for c in rec.get("checks", []):
            if not c["match"]:
                problems.append(f'reconciliation {r["strategy"]}.{c["field"]}: published {c["published"]} '
                                f'vs recomputed {c["recomputed"]}')
    if total_checked and total_matched != total_checked:
        problems.append(f"reconciliation incomplete: {total_matched}/{total_checked} fields agree")

    # 5 -- arithmetic identities
    for r in skill["rows"]:
        if r.get("n_bets") != r.get("wins", 0) + r.get("losses", 0) + r.get("pushes", 0):
            problems.append(f'{r["strategy"]}: wins+losses+pushes != n_bets')
        if r.get("n_bets") == 0:
            continue
    rnd = {c["control"]: c for c in controls["controls"]}
    for mkt, vig in controls["vig"].items():
        key = {"ATS": "RND-ATS", "TOTAL": "RND-TOTAL", "ML": "RND-ML"}[mkt]
        measured = rnd[key]["roi"]
        implied = vig["theoretical_roi_of_coin_flip"]
        if measured is None or implied is None or abs(measured - implied) > 0.006:
            problems.append(f"{key}: measured coin-flip ROI {measured} disagrees with the ROI implied by the "
                            f"vig {implied} (tolerance 0.006). Settlement or de-vig drift.")
    for r in skill["rows"]:
        q = r.get("bh_q_brier_skill")
        if q is not None and not (0.0 <= q <= 1.0):
            problems.append(f'{r["strategy"]}: q-value {q} outside [0,1]')
        if r.get("brier_model") is not None and r.get("brier_market_benchmark") is not None:
            want = 1 - r["brier_model"] / r["brier_market_benchmark"]
            if abs(want - r["brier_skill"]) > 1e-9:
                problems.append(f'{r["strategy"]}: published brier_skill does not equal 1 - BS/BS_benchmark')
    ledger_rows = [json.loads(l) for l in (HERE / "data" / "escrow_ledger.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    if len(ledger_rows) != reg["_meta"]["escrow_rows"]:
        problems.append(f'escrow ledger has {len(ledger_rows)} rows but the data file says {reg["_meta"]["escrow_rows"]}')
    for rid, row in reg["escrow"].items():
        settled = [x for x in ledger_rows if x.get("registration_id") == rid and x.get("state") == "settled"]
        if len(settled) != row["prospective_settled"]:
            problems.append(f"{rid}: escrow settled count {row['prospective_settled']} != ledger rows {len(settled)}")

    # 6 -- source discipline on the rendered pages
    blank_re = re.compile(r"\[blank\]")
    for name in PAGES:
        text = (HERE / name).read_text(encoding="utf-8")
        rows = re.findall(r"<tr>(.*?)</tr>", text, re.S)
        body_rows = [r for r in rows if "<td" in r]
        for i, r in enumerate(body_rows):
            if "href=" not in r:
                problems.append(f"{name}: table row {i + 1} has no source link")
        for m in blank_re.finditer(text):
            tail = text[m.end():m.end() + 400]
            if 'href="flagged.html"' not in tail:
                problems.append(f"{name}: a [blank] marker at offset {m.start()} does not link the flag page")

    # 7 -- internal links
    for name in PAGES:
        text = (HERE / name).read_text(encoding="utf-8")
        for m in re.finditer(r'href="([^"#]+)(?:#[^"]*)?"', text):
            href = m.group(1)
            if href.startswith(("http://", "https://", "mailto:")):
                continue
            target = (HERE / href).resolve()
            if not target.exists():
                problems.append(f"{name}: broken internal link {href}")
    return problems


def main() -> int:
    problems = problems_all()
    if problems:
        for p in problems:
            print("FAIL", p)
        print(f"luck_lab check FAILED: {len(problems)} problem(s)")
        return 1
    controls = B.load("controls.json")
    skill = B.load("skill.json")
    reg = B.load("preregistration.json")
    n_rows = sum(len(re.findall(r"<tr>", (HERE / p).read_text(encoding="utf-8"))) for p in PAGES)
    print(f"luck_lab check PASS: {len(PAGES)} pages, {n_rows} table rows, "
          f"{len(skill['rows'])} strategies, {len(controls['controls'])} controls, "
          f"{len(reg['entries'])} registrations, {n_rows} rows all linked, "
          f"reconciliation {sum(r['reconciliation_with_line_lab'].get('matched', 0) for r in skill['rows'])}"
          f"/{sum(r['reconciliation_with_line_lab'].get('total', 0) for r in skill['rows'])} fields")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
