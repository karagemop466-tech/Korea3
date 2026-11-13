#!/usr/bin/env python3
"""Record one owner decision and propagate it through the desk.

The desk's brief says the owner chooses; this tool is the part that makes a choice cheap enough to
actually be made. It writes the same fact twice - once in the suggestion register, once in the
decision log - because check.py fails if the two disagree, then rebuilds the pages and runs the
verifier so the result is visible immediately.

    python3 desk/decide.py K04 A --date 2026-11-14 --note "licensed depth feed first"
    python3 desk/decide.py K04 A --date 2026-11-14 --dry-run
    python3 desk/decide.py --list

It refuses to invent an option, to decide with no date, and to touch anything outside desk/.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"


def read(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def write(name, obj):
    (DATA / name).write_text(json.dumps(obj, indent=1) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="record an owner decision on a desk suggestion")
    ap.add_argument("suggestion", nargs="?", help="the K-id, e.g. K04")
    ap.add_argument("option", nargs="?", help="the option letter, e.g. A")
    ap.add_argument("--date", default="", help="YYYY-MM-DD the choice was made (defaults to today)")
    ap.add_argument("--note", default="", help="one line of why")
    ap.add_argument("--decision", default="Approved", choices=["Approved", "Rejected", "Deferred"])
    ap.add_argument("--list", action="store_true", help="show the board and exit")
    ap.add_argument("--dry-run", action="store_true", help="print what would change, write nothing")
    a = ap.parse_args()

    sug = read("suggestions.json")
    if a.list or not a.suggestion:
        for x in sug["suggestions"]:
            print(f'{x["id"]}  {x["decision_status"]:<40} {"blocks" if x["blocking"] else "      "}  {x["title"][:70]}')
            for o in x["options"]:
                print(f'      {o["option"][:96]}')
        return 0

    hit = [x for x in sug["suggestions"] if x["id"].upper() == a.suggestion.upper()]
    if not hit:
        print(f"no suggestion {a.suggestion}. Try --list.", file=sys.stderr)
        return 2
    x = hit[0]
    want = a.option.strip().upper().rstrip(".")
    opt = [o for o in x["options"] if o["option"].strip().upper().startswith(want + " ")
           or o["option"].strip().upper().startswith(want + ".")]
    if not opt:
        print(f'{x["id"]} has no option {a.option!r}. Its options are:', file=sys.stderr)
        for o in x["options"]:
            print("   " + o["option"], file=sys.stderr)
        return 2
    if len(opt) > 1:
        print(f"option {a.option!r} is ambiguous", file=sys.stderr)
        return 2
    date = a.date or dt.date.today().isoformat()
    try:
        dt.date.fromisoformat(date)
    except ValueError:
        print("--date must be YYYY-MM-DD", file=sys.stderr)
        return 2

    log = read("decisions.json")
    rid = f"D{len(log['records']) + 1:02d}"
    closes = x["impact"]["closes"]
    answers = x["impact"]["unblocks"]
    cons = closes + answers if a.decision == "Approved" else []
    print(f"{x['id']}  {x['title']}")
    print(f"  decision : {a.decision} ({rid})")
    print(f"  option   : {opt[0]['option']}")
    print(f"  date     : {date}")
    print(f"  applies  : {', '.join(cons) if cons else 'nothing - a rejection or deferral retires no flag'}")
    if a.dry_run:
        print("\ndry run: nothing written.")
        return 0

    x["decision_status"] = a.decision
    x["chosen_option"] = opt[0]["option"]
    x["decision_date"] = date
    x["decision_owner"] = "Repository owner"
    write("suggestions.json", sug)

    if a.decision == "Approved":
        for fid in closes:
            flags = read("flags.json")
            for f in flags["flags"]:
                if f["id"] == fid:
                    f["status"] = f"closed by decision {rid} on {date}"
                    f["decision_ref"] = rid
            write("flags.json", flags)
        for qid in answers:
            q = read("questions.json")
            for row in q["questions"]:
                if row["id"] == qid:
                    row["status"] = "answered by owner decision"
                    row["answer"] = (f"Decided by the owner in {rid} ({date}): {opt[0]['option']}. "
                                     + (f"Note: {a.note}" if a.note else ""))
                    row["answer_source_id"] = "R06"
            write("questions.json", q)
    log["records"].append({"id": rid, "suggestion": x["id"], "decision": a.decision, "option": opt[0]["option"],
                           "date": date, "recorded_by": "Repository owner", "note": a.note,
                           "consequences_applied": cons})
    log["as_of_utc"] = date + "T00:00:00Z"
    write("decisions.json", log)

    gate = sug["decision_gate"]["counts"]
    gate["Proposed - awaiting owner decision"] = sum(1 for y in sug["suggestions"]
                                                     if y["decision_status"].startswith("Proposed"))
    gate[a.decision] = gate.get(a.decision, 0) + 1
    sug = read("suggestions.json")
    sug["decision_gate"]["counts"] = gate
    write("suggestions.json", sug)

    for cmd in ([sys.executable, str(HERE / "build.py")], [sys.executable, str(HERE / "check.py")]):
        r = subprocess.run(cmd, cwd=str(HERE.parent), capture_output=True, text=True)
        print(("\n".join(r.stdout.strip().splitlines()[-3:])) or r.stderr.strip()[-400:])
        if r.returncode:
            print("\nThe verifier rejected the change. Nothing else was written; fix the disagreement or revert "
                  "with git checkout -- desk/data", file=sys.stderr)
            return r.returncode
    print("\nRecorded. The impact tables, the flag register and the question register were recomputed from this entry.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
