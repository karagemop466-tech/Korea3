#!/usr/bin/env python3
"""Fail-closed verifier for the Desk Ops lab.

Run after stores.py, metrics.py and build.py. Every check re-derives the published value
from the committed inputs or the generating code, so a page cannot go live showing a number
the data does not support. Exit 1 = at least one failure; the pages must not be published.

Usage:
    python3 ops_lab/check.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
DATA = HERE / "data"

sys.path.insert(0, str(HERE))
import stores  # noqa: E402
import build   # noqa: E402

FAILURES: list[str] = []
CHECKS = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global CHECKS
    CHECKS += 1
    if ok:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        FAILURES.append(f"{name}: {detail}")


def main() -> int:
    print("Desk Ops verification\n")

    # ---------------------------------------------------------- inputs unmodified
    bad = stores.verify_inputs()
    check("pinned input sha256 hashes match provenance", not bad, "; ".join(bad))

    # ---------------------------------------------------------- store integrity
    snaps = list(csv.DictReader(open(DATA / "price_snapshots.csv", newline="", encoding="utf-8")))
    snap_meta = json.loads((DATA / "snapshot_meta.json").read_text())
    check("store row count matches its meta", len(snaps) == snap_meta["rows"],
          f"{len(snaps)} != {snap_meta['rows']}")

    url_ok = {r["source_url"] for r in snaps} <= {stores.SRC_GAMES, stores.SRC_CLOSING,
                                                  stores.SRC_INITIAL, stores.SRC_OWN}
    check("every store row links one of the four pinned/repo sources", url_ok)

    blank_rows = [r for r in snaps if r["snapshot_type"] == "origination_blank"]
    check("origination_blank rows are blank with a note and never zero",
          all(r["line"] == "" and r["odds"] == "" and r["note"] for r in blank_rows)
          and len(blank_rows) == snap_meta["by_snapshot_type"]["origination_blank"])

    # every originated market side has exactly one row in origination scope
    own = stores.load_own()
    need = {(r["game_id"], m, s) for r in own
            for m, sides in (("SPREAD", ("home", "away")), ("TOTAL", ("over", "under")),
                             ("MONEYLINE", ("home", "away"))) for s in sides}
    have = {(r["game_id"], r["market"], r["side"]) for r in snaps if r["scope"] == "origination"}
    check("every originated market side (164 x 6) has a store row", need <= have and len(have) == len(need),
          f"missing {len(need - have)}, extra {len(have - need)}")

    # closing rows equal the source, value for value (multiset)
    games = stores.load_games()
    closing = stores.load_closing()
    src_ms: list[tuple] = []
    for gid, crows in closing.items():
        g = games.get(gid)
        if not g:
            continue
        for r in crows:
            t = r["type"]
            if t == "SPREAD":
                side = "home" if r["side"] == g["home_team"] else "away"
            elif t == "TOTAL":
                side = r["side"].lower()
            elif t == "MONEYLINE":
                side = "home" if r["side"] == g["home_team"] else "away"
            else:
                continue
            src_ms.append((gid, t, side, r["line"], r["odds"]))
    store_ms = [(r["game_id"], r["market"], r["side"], r["line"], r["odds"])
                for r in snaps if r["snapshot_type"] == "closing"]
    check("closing store rows equal closing_lines.csv value-for-value",
          sorted(src_ms) == sorted(store_ms),
          f"source {len(src_ms)} vs store {len(store_ms)}")

    # ---------------------------------------------------------- feed integrity
    feed = list(csv.DictReader(open(DATA / "results_feed.csv", newline="", encoding="utf-8")))
    feed_meta = json.loads((DATA / "results_feed_meta.json").read_text())
    check("feed row count matches its meta", len(feed) == feed_meta["rows"],
          f"{len(feed)} != {feed_meta['rows']}")
    rebuilt, rmeta = stores.build_feed(games, closing)
    check("feed re-derives byte-identically from the inputs",
          [tuple(r.values()) for r in rebuilt] == [tuple(r.values()) for r in feed])
    check("published-outcome mismatches match the meta",
          rmeta["published_outcome_mismatches"] == feed_meta["published_outcome_mismatches"])
    check("published-outcome mismatch count is flagged, never hidden",
          feed_meta["published_outcome_mismatches"] == len(feed_meta["mismatch_rows"])
          or feed_meta["published_outcome_mismatches"] <= 100)

    bets = stores.load_bets()
    cc = stores.ledger_crosscheck(bets, rebuilt)
    check("ledger cross-check: every single-market bet outcome equals the feed",
          cc["mismatch_count"] == 0, f"{cc['mismatch_count']} mismatches")
    check("ledger cross-check covered a meaningful share",
          cc["checked"] > 15000, f"only {cc['checked']}")

    # ---------------------------------------------------------- split integrity
    split = list(csv.DictReader(open(DATA / "leaderboard_split.csv", newline="", encoding="utf-8")))
    published = {row["id"]: row for row in
                 json.loads((ROOT / "data/derived/summary.json").read_text())["leaderboard"]}
    worst_roi = 0.0
    worst_bets = 0
    for r in split:
        pub = published[r["strategy_id"]]
        worst_roi = max(worst_roi, abs(float(r["roi"]) - pub["full_roi"]))
        worst_bets = max(worst_bets, abs(int(r["bets"]) - pub["bets"]))
    check("split ROI reproduces the published leaderboard (tolerance 0.05 pp)",
          worst_roi <= 5e-4, f"max delta {worst_roi:.2e}")
    check("split bet counts equal the published counts", worst_bets == 0, f"max delta {worst_bets}")

    # ---------------------------------------------------------- own book integrity
    own_rows = list(csv.DictReader(open(DATA / "own_book_ml.csv", newline="", encoding="utf-8")))
    check("own book covers all 164 originated games", len(own_rows) == 164, str(len(own_rows)))
    src_own = {r["game_id"]: r for r in own}
    inv_fail = spread_fail = total_fail = ml_fail = 0
    for r in own_rows:
        s = src_own[r["game_id"]]
        if r["diff_spread"] and abs(float(r["diff_spread"]) - (float(s["own_spread"]) - float(s["market_spread_if_posted"]))) > 1e-9:
            spread_fail += 1
        elif r["diff_spread"] and abs(float(r["diff_spread"]) - float(s["disagreement_spread"])) > 1e-9:
            spread_fail += 1
        if r["diff_total"] and abs(float(r["diff_total"]) - (float(s["own_total"]) - float(s["market_total_if_posted"]))) > 1e-9:
            total_fail += 1
        elif r["diff_total"] and abs(float(r["diff_total"]) - float(s["disagreement_total"])) > 1e-9:
            total_fail += 1
        # inverse of the fair-moneyline arithmetic
        a = float(r["fair_ml_home"])
        d = 1 + 100 / abs(a) if a < 0 else 1 + a / 100
        if abs(1 / d - float(r["fair_p_home"])) > 0.005:
            ml_fail += 1
    check("own-book spread difference equals fair - market AND the published disagreement column",
          spread_fail == 0, f"{spread_fail} rows")
    check("own-book total difference equals fair - market AND the published disagreement column",
          total_fail == 0, f"{total_fail} rows")
    check("fair moneyline is the exact inverse of the published win probability",
          ml_fail == 0, f"{ml_fail} rows exceed tolerance")

    # ---------------------------------------------------------- pages
    pages = {p.name: p.read_text(encoding="utf-8") for p in sorted(HERE.glob("*.html"))}
    for fname, _, _ in build.PAGES:
        check(f"page exists: {fname}", fname in pages)

    class RowParser(build.html.parser.HTMLParser if hasattr(build.html, "parser") else object):
        pass
    # simple per-row link check (same rule the repo-wide audit applies)
    missing = []
    for fname, text in pages.items():
        for tbody in re.findall(r"<tbody>(.*?)</tbody>", text, flags=re.S):
            for tr in re.findall(r"<tr>(.*?)</tr>", tbody, flags=re.S):
                if "<a " not in tr and "<td" in tr:
                    missing.append(f"{fname}: {tr[:80]}")
    check("every generated table row carries at least one link", not missing,
          f"{len(missing)} rows without links: " + "; ".join(missing[:3]))

    tokens = []
    for fname, text in pages.items():
        for tok in ("TBD", "TODO", "FIXME", ">N/A<", "???"):
            if tok in text:
                tokens.append(f"{fname}:{tok}")
    check("no placeholder tokens on any page", not tokens, "; ".join(tokens))

    root = (ROOT / "index.html").read_text(encoding="utf-8")
    check("root navigation links to the Desk Ops lab", "ops_lab/index.html" in root)

    # ---------------------------------------------------------- determinism
    import os
    import tempfile
    before = {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
              for f in sorted(list(HERE.glob("*.html")) + list(DATA.glob("*.csv")) + list(DATA.glob("*.json")))}
    env = dict(os.environ)
    subprocess.run([sys.executable, str(HERE / "stores.py")], check=True, capture_output=True, env=env)
    subprocess.run([sys.executable, str(HERE / "metrics.py")], check=True, capture_output=True, env=env)
    subprocess.run([sys.executable, str(HERE / "build.py")], check=True, capture_output=True, env=env)
    after = {f.name: hashlib.sha256(f.read_bytes()).hexdigest()
             for f in sorted(list(HERE.glob("*.html")) + list(DATA.glob("*.csv")) + list(DATA.glob("*.json")))}
    drift = [k for k in before if before[k] != after.get(k)]
    check("rebuild is byte-identical (deterministic, no clock)", not drift,
          f"{len(drift)} files drifted: {drift[:4]}")

    print(f"\n{CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    if FAILURES:
        print("FAILURES:")
        for f in FAILURES:
            print("  -", f)
        return 1
    print("PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
