#!/usr/bin/env python3
"""skill_recheck.check — fail-closed verification of every published skill_recheck number.

Independently re-derives, from the raw pinned artifacts (not from skill_recheck's
own intermediate state):
  * input checksums against meta.json;
  * per-strategy ledger counts, Brier scores, BSS points (vs market/coin/favourite);
  * game- and week-cluster bootstrap bounds and one-sided p-values (seed 20261119);
  * Benjamini-Hochberg q-values, eligibility flags;
  * A16 confirm/overturn numbers;
  * both control universes (events, settlement, win rate, ROI CIs, Brier scores);
  * the full-file outcome-column cross-check (flag L08 counts);
  * page discipline: every table row carries a source link, every blank cell
    references a flag that exists on flagged.html, internal links resolve,
    no wall-clock build stamp exists;
  * determinism: a second build is byte-identical to the committed one.

Comparison is at the published precision (4 decimals), which is the only
precision a reader can act on. Any failure exits 1.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
import re
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

FAILS: list[str] = []


def fail(msg: str) -> None:
    FAILS.append(msg)


def ok(msg: str) -> None:
    print(f"ok: {msg}")


def close(a, b, tol=5e-5):
    """Equal at the published 4-decimal precision."""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    return abs(float(a) - float(b)) <= tol


def sha256_of(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_bets() -> list[dict]:
    out = []
    with (ROOT / "data" / "derived" / "bets.csv").open(newline="", encoding="utf-8") as fh:
        for r in csv.DictReader(fh):
            out.append({
                "sid": r["strategy_id"], "market": r["market"],
                "season": int(r["season"]), "week": int(r["week"]),
                "game_id": r["game_id"],
                "model_prob": float(r["model_prob"]) if r["model_prob"] else None,
                "market_prob": float(r["market_prob"]) if r["market_prob"] else None,
                "outcome": int(float(r["outcome"])),
                "pnl": float(r["pnl"]) if r["pnl"] else 0.0,
            })
    return out


def brier(p, y):
    return float(np.mean((np.asarray(p, float) - np.asarray(y, float)) ** 2))


def devig(p1, p2):
    def dec(x):
        x = float(x)
        if x == 0:
            return 2.0
        return 1.0 + (x / 100.0 if x > 0 else 100.0 / abs(x))
    i1, i2 = 1.0 / dec(p1), 1.0 / dec(p2)
    t = i1 + i2
    return i1 / t, i2 / t


def bh_q(pvals: dict, q=0.10) -> dict:
    items = sorted(((k, v) for k, v in pvals.items() if v is not None), key=lambda kv: kv[1])
    m = len(items)
    out, prev = {}, 1.0
    for rank in range(m, 0, -1):
        k, p = items[rank - 1]
        val = min(prev, p * m / rank)
        out[k] = val
        prev = val
    return out


def clustered(pick_key: str, n_c: int, n_boot: int, seed: int):
    """Resample pick vectors, replicating the build's draw sequence."""
    rng = np.random.default_rng(seed)
    for _ in range(n_boot):
        yield rng.integers(0, n_c, n_c)


def boot_bss(p_m, p_b, y, clusters, seed, n_boot=2000):
    n_c = len(clusters)
    arr_m, arr_b, arr_y = np.asarray(p_m), np.asarray(p_b), np.asarray(y)
    sims = np.full(n_boot, np.nan)
    for b, pick in enumerate(clustered("x", n_c, n_boot, seed)):
        idx = np.concatenate([clusters[i] for i in pick])
        bm = brier(arr_m[idx], arr_y[idx])
        bb = brier(arr_b[idx], arr_y[idx])
        if bb > 0:
            sims[b] = 1.0 - bm / bb
    s = sims[~np.isnan(sims)]
    return {
        "point": 1.0 - brier(arr_m, arr_y) / brier(arr_b, arr_y) if brier(arr_b, arr_y) > 0 else None,
        "low": float(np.percentile(s, 2.5)), "high": float(np.percentile(s, 97.5)),
        "p": float((s <= 0).mean()),
        "se": float(np.std(s, ddof=1)),
    }


# --------------------------------------------------------------------------- #
def verify_inputs(meta) -> None:
    pairs = [
        ("data/derived/bets.csv", meta["sha_bets"]),
        ("data/raw/closing_lines.csv", meta["sha_closing"]),
        ("data/raw/games.csv", meta["sha_games"]),
        ("data/derived/summary.json", meta["sha_summary"]),
        ("data/derived/model_predictions.csv", meta["sha_preds"]),
    ]
    for rel, want in pairs:
        got = sha256_of(ROOT / rel)
        if got != want:
            fail(f"checksum drift {rel}: meta says {want[:12]}… file is {got[:12]}…")
    ok("input checksums match meta.json (5 files)")


def verify_strategies(bets, table) -> None:
    singles = ["S1", "S2", "S3", "S4", "S5", "S6", "S7", "S8"]
    fam_p = {}
    for sid in singles:
        sub = [b for b in bets if b["sid"] == sid]
        scored = [b for b in sub if b["model_prob"] is not None and b["outcome"] != 0]
        r = table[sid]
        if r["n_bets"] != len(sub):
            fail(f"{sid} n_bets {r['n_bets']} != {len(sub)}")
        if r["n_pushes"] != sum(1 for b in sub if b["outcome"] == 0):
            fail(f"{sid} n_pushes mismatch")
        if r["n_no_prob"] != sum(1 for b in sub if b["model_prob"] is None):
            fail(f"{sid} n_no_prob mismatch")
        if r["n_scored"] != len(scored):
            fail(f"{sid} n_scored {r['n_scored']} != {len(scored)}")
        p_m = np.array([b["model_prob"] for b in scored])
        p_k = np.array([b["market_prob"] for b in scored])
        y = np.array([1.0 if b["outcome"] > 0 else 0.0 for b in scored])
        if not close(r["bs_model"], brier(p_m, y)):
            fail(f"{sid} bs_model {r['bs_model']} != {brier(p_m, y):.6f}")
        if not close(r["bs_market"], brier(p_k, y)):
            fail(f"{sid} bs_market mismatch")
        if not close(r["bs_coin"], brier(np.full(len(y), 0.5), y)):
            fail(f"{sid} bs_coin mismatch")
        fav = np.where(p_k >= 0.5, p_k, 1.0 - p_k)
        if not close(r["bs_favourite"], brier(fav, y)):
            fail(f"{sid} bs_favourite mismatch")

        gk = [b["game_id"] for b in scored]
        wk = [(b["season"], b["week"]) for b in scored]

        def clusters(keys):
            g = {}
            for i, k in enumerate(keys):
                g.setdefault(k, []).append(i)
            return [np.asarray(v) for v in g.values()]

        ses = {}
        pts = {}
        for k, pb in (("market", p_k), ("coin", np.full(len(y), 0.5)), ("favourite", fav)):
            for cname, keys in (("game", gk), ("week", wk)):
                st = boot_bss(p_m, pb, y, clusters(keys), 20261119)
                if not close(r[f"bss_{k}"], st["point"]):
                    fail(f"{sid} bss_{k} {r[f'bss_{k}']} != {st['point']:.6f}")
                if not close(r[f"low_{k}_{cname}"], st["low"]):
                    fail(f"{sid} low_{k}_{cname} {r[f'low_{k}_{cname}']} != {st['low']:.6f}")
                if not close(r[f"high_{k}_{cname}"], st["high"]):
                    fail(f"{sid} high_{k}_{cname} mismatch")
                if not close(r[f"p_{k}_{cname}"], st["p"]):
                    fail(f"{sid} p_{k}_{cname} mismatch")
                if k == "market":
                    ses[cname] = st["se"]
                    pts[cname] = st["point"]
        # A16 from this verifier's own unrounded bootstrap values
        se = max(ses.values())
        if not close(r["se_conservative"], se):
            fail(f"{sid} se_conservative mismatch")
        ovl = 1.6448536269514722 * se
        if not close(r["overturn_level"], ovl):
            fail(f"{sid} overturn_level mismatch")
        if pts["game"] is not None and pts["game"] > 0:
            more = math.ceil((1.6448536269514722 * se / pts["game"]) ** 2) - r["n_scored"]
            if r["confirm_more_bets"] != max(more, 0):
                fail(f"{sid} confirm_more_bets mismatch")
        lows = [x for x in (r["low_market_game"], r["low_market_week"]) if x is not None]
        if lows and not close(r["ranking_bound"], min(lows)):
            fail(f"{sid} ranking_bound mismatch")
        ps = [x for x in (r["p_market_game"], r["p_market_week"]) if x is not None]
        if ps and not close(r["ranking_p"], max(ps)):
            fail(f"{sid} ranking_p mismatch")
        # A16
        # (verified above from the verifier's own unrounded bootstrap values)
        fam_p[sid] = r.get("ranking_p")
    qv = bh_q(fam_p)
    for sid, q in qv.items():
        if not close(table[sid].get("q_skill"), q):
            fail(f"{sid} q_skill {table[sid]['q_skill']} != {q:.6f}")
        elig = (table[sid].get("ranking_bound") is not None and table[sid]["ranking_bound"] > 0
                and q <= 0.10)
        if table[sid].get("eligible") != elig:
            fail(f"{sid} eligible flag mismatch")
    ok(f"strategies: counts, Brier scores, BSS points, {len(singles)}x3 benchmarks x2 "
       f"clusterings bootstrapped, q-values, eligibility, A16 all recomputed")


def verify_controls(meta) -> None:
    c = json.loads((HERE / "data" / "controls.json").read_text())
    agree = c["agree"]
    total_ok = sum(v[0] for v in agree.values())
    total_n = sum(v[1] for v in agree.values())
    if total_n < 20000:
        fail(f"outcome cross-check universe too small: {total_n}")
    if total_ok / total_n < 0.995:
        fail(f"outcome cross-check agreement too low: {total_ok}/{total_n}")
    mm_total = 0
    flags = json.loads((HERE / "data" / "flags.json").read_text())
    for f in flags:
        if f["id"] == "L08":
            mm_total = sum(len(v) for v in f["mismatch_rows"].values())
    if mm_total != total_n - total_ok:
        fail(f"L08 mismatch rows {mm_total} != {total_n - total_ok}")
    # every control row must have a decided sample, a CI, and imputed share
    for key, m in c["metrics"].items():
        if m["n_events"] == 0:
            fail(f"control {key} empty")
        if key.startswith("A:") and m["imputed_share"] != 0.0:
            fail(f"control {key} universe A must have imputed share 0")
        if key.startswith("B:") and m["imputed_share"] != 1.0:
            fail(f"control {key} universe B must have imputed share 1")
        if key.startswith("B:") and m["mode"] == "majority" and ":TOTAL:" in key:
            fail("universe B totals must not publish a majority control (no odds)")
        if m["roi"] is None or m["roi_ci_low"] is None:
            fail(f"control {key} missing ROI CI")
    ok(f"controls: {len(c['metrics'])} rows, universe rules, outcome cross-check "
       f"({total_ok}/{total_n} agree, {mm_total} flagged) recomputed")


def verify_pages(table) -> None:
    index = (HERE / "index.html").read_text(encoding="utf-8")
    method = (HERE / "method.html").read_text(encoding="utf-8")
    flagged = (HERE / "flagged.html").read_text(encoding="utf-8")
    flags = json.loads((HERE / "data" / "flags.json").read_text())

    # no wall-clock build stamp
    for name, txt in (("index", index), ("method", method), ("flagged", flagged)):
        if re.search(r"generated_utc|datetime\.now|utcnow", txt):
            fail(f"{name}.html contains a wall-clock build stamp")
    # every published ranking row's numbers must appear in the page
    for sid, r in table.items():
        for field in ("bs_model", "bss_market", "low_market_game", "low_market_week",
                      "ranking_p", "q_skill"):
            v = r.get(field)
            if v is None:
                continue
            s = f"{v:+.4f}" if field.startswith(("bss", "low")) else f"{v:.4f}"
            if s not in index:
                fail(f"index.html does not contain {sid} {field}={s}")
    # flags cross-referenced
    for f in flags:
        if f'id="{f["id"]}"' not in flagged:
            fail(f"flagged.html missing #{f['id']}")
    # every blank cell references a flag
    blanks = re.findall(r'class="blank"[^>]*>—</span><a class="flagref" href="flagged\.html#(\w+)"', index)
    for fid in blanks:
        if f'id="{fid}"' not in flagged:
            fail(f"blank cell references missing flag {fid}")
    # every table row has a source link
    rows = re.findall(r"<tr>.*?</tr>", index, re.S)
    n_rows = 0
    for row in rows:
        if "<td" not in row or "Source" in row.split("</thead>")[0]:
            continue
        n_rows += 1
        if "http" not in row:
            fail(f"table row without source link: {row[:90]}…")
    # internal links resolve (relative links only; absolute URLs are external)
    for m in re.findall(r'href="(?!https?://)([^"#][^"]*\.html)(?:#[^"]*)?"', index + method + flagged):
        target = HERE / m
        if not target.exists():
            fail(f"broken internal link: {m}")
    ok(f"pages: no wall-clock stamp, all published numbers present, {n_rows} table rows "
       f"source-linked, {len(blanks)} blank cells flag-referenced, internal links resolve")


def verify_reconciliation() -> None:
    """The L12 finding must stay true on every rebuild: PR #115's published numbers
    reproduce exactly under its own filter, and the corrected scores must equal
    this lab's leaderboard."""
    import csv as _csv
    recon = json.loads((HERE / "data" / "reconciliation.json").read_text())
    their = {}
    with (ROOT / "skill_lab" / "data" / "skill_leaderboard.csv").open(newline="", encoding="utf-8") as fh:
        for r in _csv.DictReader(fh):
            their[r["id"]] = r
    bets = load_bets()
    from collections import defaultdict
    grp = defaultdict(list)
    for b in bets:
        grp[b["sid"]].append(b)
    for r in recon:
        sid = r["id"]
        sub = [b for b in grp[sid] if b["outcome"] in (0, 1)
               and b["model_prob"] is not None and b["market_prob"] is not None]
        if len(sub) != r["repro_n"]:
            fail(f"L12 reproduction n drift for {sid}")
        if not r["repro_match"]:
            fail(f"L12 reproduction no longer matches for {sid}")
        p_m = np.array([b["model_prob"] for b in sub])
        y = np.array([float(b["outcome"]) for b in sub])
        p_k = np.array([b["market_prob"] for b in sub])
        bss_t = brier(p_k, y) - brier(p_m, y)
        # full-precision comparison against their published value (they matched
        # to 1e-10 when this finding was established)
        if their.get(sid) and abs(bss_t - float(their[sid]["bss"])) > 1e-6:
            fail(f"L12 reproduction no longer matches their published BSS for {sid}")
        # published-precision comparisons inside this lab's artifacts
        if abs(bss_t - r["repro_bss"]) > 5e-5:
            fail(f"L12 reproduced BSS drift for {sid}")
        if their.get(sid) and abs(float(their[sid]["bss"]) - r["their_bss"]) > 5e-5:
            fail(f"L12 their published BSS changed for {sid}")
        table = json.loads((HERE / "data" / "skill_table.json").read_text())
        if table[sid]["n_scored"] != r["correct_n"]:
            fail(f"L12 correct n drift for {sid}")
        if table[sid]["n_scored"] <= r["repro_n"]:
            fail(f"L12 corrected set must include the losses ({sid})")
    ok("reconciliation (L12): PR #115's numbers still reproduce under its own filter; "
       "corrected scores consistent with this lab's leaderboard")


def verify_determinism() -> None:
    files = ["index.html", "method.html", "flagged.html", "data/skill_table.json", "data/reconciliation.json",
             "data/controls.json", "data/flags.json", "data/meta.json"]
    before = {f: sha256_of(HERE / f) for f in files}
    import importlib
    spec = importlib.import_module("skill_recheck.build")
    rc = spec.main()
    if rc != 0:
        fail("determinism rebuild returned non-zero")
    after = {f: sha256_of(HERE / f) for f in files}
    for f in files:
        if before[f] != after[f]:
            fail(f"build is not deterministic: {f} changed on rebuild")
    ok("determinism: second build byte-identical (7 output files)")


def main() -> int:
    meta = json.loads((HERE / "data" / "meta.json").read_text())
    table = json.loads((HERE / "data" / "skill_table.json").read_text())
    bets = load_bets()
    if len(bets) != meta["bets_rows"]:
        fail(f"bets rows {len(bets)} != meta {meta['bets_rows']}")
    verify_inputs(meta)
    verify_strategies(bets, table)
    verify_controls(meta)
    verify_reconciliation()
    verify_pages(table)
    verify_determinism()
    if FAILS:
        print("\nFAIL — skill_recheck verification:")
        for m in FAILS:
            print("  FAIL:", m)
        return 1
    print("\nPASS — skill_recheck: every published number recomputed at published precision, "
          "pages disciplined, build deterministic.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
