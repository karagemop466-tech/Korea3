#!/usr/bin/env python3
"""Independent re-verification of the committed NFL Line Lab numbers.

Session `arena/1cd638e3-korea3`. This script is deliberately **self-contained**: it reads the
committed raw/derived CSV and JSON artefacts directly and **does not import `line_lab`, `scripts`,
`pipeline`, `hub` or `decision_lab`**. A bug in the producing pipeline therefore cannot certify its
own output. Each check recomputes a published value from first principles and compares it to the
committed value, recording the source it used.

Classes of evidence used here
---------------------------
``dataset``   Re-derived from the pinned open dataset (nflverse/nfldata) or a committed file that is
              itself computed from it. Not an NFL official publication; the NFL publishes no
              machine-readable lines. Linked to the pinned GitHub commit / committed file.
``arithmetic`` A deterministic identity that must hold by definition (break-even prices, parlay
              odds). No external data required.

Usage:
    python3 reverify_1cd638e3/verify.py            # deterministic: committed files only
    python3 reverify_1cd638e3/verify.py --live     # also re-download the pinned commit

The default run is fully deterministic (committed files only) so the committed results.json is
reproducible byte-for-byte in CI. The live dataset re-download is a one-time, environment-dependent
check enabled explicitly with --live; its result is recorded in results.json only when it is run.

Writes reverify_1cd638e3/results.json and prints a summary. Exit 0 if every check passes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.request
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(__file__).resolve().parent
PINNED_COMMIT = "a270278f3ac4e937295fe6a27814b3c4a2b62645"
DATASET_URL = (f"https://codeload.github.com/nflverse/nfldata/tar.gz/{PINNED_COMMIT}")
COMMIT_URL = f"https://github.com/nflverse/nfldata/commit/{PINNED_COMMIT}"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check(name, method, expected, actual, tol=1e-4, source="", note=""):
    ok = False
    if isinstance(expected, (int, float)) and isinstance(actual, (int, float)):
        ok = abs(float(actual) - float(expected)) <= tol
    else:
        ok = expected == actual
    return {
        "check": name, "method": method, "class": "dataset" if source else "arithmetic",
        "expected": expected, "recomputed": actual, "pass": ok,
        "source": source, "note": note,
    }


def verify_dataset_checksums(results):
    """Confirm every committed raw CSV matches the SHA-256 recorded in provenance.json."""
    prov = json.load(open(ROOT / "data" / "provenance.json"))
    files = prov["primary_dataset"]["files"]
    for name, meta in files.items():
        p = ROOT / "data" / "raw" / name
        if not p.exists():
            results.append(check("dataset:" + name, "sha256 of committed data/raw file",
                                 meta["sha256"], "MISSING", source=meta.get("row_source_template", "")))
            continue
        actual = sha256(p)
        results.append(check(
            "dataset:" + name,
            "sha256 of committed data/raw file vs provenance.json",
            meta["sha256"], actual, tol=0,
            source=meta.get("row_source_template", ""),
            note=f"rows recorded {meta['rows_including_header']}; actual "
                 f"{sum(1 for _ in open(p, newline='', encoding='utf-8'))}"))


def verify_dataset_live(results):
    """Best-effort: re-download the pinned commit and confirm the five checksums byte-for-byte."""
    import tarfile
    import tempfile
    prov = json.load(open(ROOT / "data" / "provenance.json"))
    files = prov["primary_dataset"]["files"]
    try:
        with tempfile.TemporaryDirectory() as td:
            tar_path = Path(td) / "nfldata.tar.gz"
            with urllib.request.urlopen(DATASET_URL, timeout=60) as r, open(tar_path, "wb") as f:
                f.write(r.read())
            with tarfile.open(tar_path, "r:gz") as tf:
                tf.extractall(td)
            base = next(Path(td).glob("nfldata-*")) / "data"
            for name, meta in files.items():
                p = base / name
                if not p.exists():
                    results.append(check("dataset-live:" + name, "re-download from codeload.github.com",
                                         meta["sha256"], "MISSING", source=COMMIT_URL))
                    continue
                actual = sha256(p)
                results.append(check(
                    "dataset-live:" + name,
                    "re-download pinned commit from codeload.github.com, sha256 vs provenance.json",
                    meta["sha256"], actual, tol=0, source=COMMIT_URL))
    except Exception as exc:  # network egress may be restricted
        results.append({
            "check": "dataset-live:download", "method": "re-download pinned commit",
            "class": "dataset", "expected": "5/5 checksums match",
            "recomputed": f"skipped: {exc}", "pass": None,
            "source": COMMIT_URL, "note": "live download unavailable from this environment; "
                                           "committed-file checksums above still verify the pin."})


def verify_correlation(results):
    """Recompute the same-game Home-cover x Over phi from the committed model_dataset.csv."""
    md = pd.read_csv(ROOT / "data" / "derived" / "model_dataset.csv")
    base = md.dropna(subset=["home_cover", "over"])
    hc = base["home_cover"].to_numpy(float)
    ov = base["over"].to_numpy(float)
    n = int(hc.size)
    p1, p2 = float(hc.mean()), float(ov.mean())
    joint = float(((hc == 1) & (ov == 1)).mean())
    r = float(np.corrcoef(hc, ov)[0, 1])
    tab = np.array([[((hc == 1) & (ov == 1)).sum(), ((hc == 1) & (ov == 0)).sum()],
                    [((hc == 0) & (ov == 1)).sum(), ((hc == 0) & (ov == 0)).sum()]])
    chi2, p, _, _ = stats.chi2_contingency(tab, correction=False)
    src = (f"{COMMIT_URL} (via committed data/derived/model_dataset.csv)")
    # published row in data/derived/corr_same_game.csv
    pub = pd.read_csv(ROOT / "data" / "derived" / "corr_same_game.csv")
    row = pub[pub["pair"] == "Home cover x Over"].iloc[0]
    results.append(check("corr:home_cover x over n", "count of model_dataset rows with both legs",
                         int(row["n"]), n, tol=0, source=src,
                         note="resolves F-06/X02: value is computed from model_dataset.csv, not raw games.csv"))
    results.append(check("corr:home_cover rate", "mean of home_cover", float(row["rate_a"]), p1, source=src))
    results.append(check("corr:over rate", "mean of over", float(row["rate_b"]), p2, source=src))
    results.append(check("corr:joint win rate", "P(cover and over)", float(row["joint_win_rate"]), joint, source=src))
    results.append(check("corr:phi", "Pearson correlation of the two binary legs",
                         float(row["phi"]), r, source=src))
    results.append(check("corr:chi2", "chi-square of independence (no correction)",
                         float(row["chi2"]), float(chi2), tol=0.0006, source=src,
                         note="published to 3 decimals; recomputed full precision"))
    results.append(check("corr:p_value", "chi-square p-value", float(row["p_value"]), float(p), source=src))


def verify_arithmetic(results):
    """Deterministic identities that must hold by definition."""
    be110 = 110.0 / 210.0
    results.append(check("arith:-110 break-even", "110/(110+100)", 0.52381, be110, tol=1e-5))
    dec2 = (1 + 100.0 / 110.0) ** 2
    results.append(check("arith:2-leg -110 parlay decimal", "(1+100/110)^2", 3.6446, dec2, tol=1e-4))
    be_joint = 1.0 / dec2
    phi_needed = (be_joint - 0.25) / 0.25  # at p=0.5 each leg: joint = 0.25 + phi*0.25
    meta = json.load(open(ROOT / "data" / "derived" / "corr_meta.json"))
    results.append(check("arith:2-leg break-even phi", "phi at p=0.5 for a 2-leg -110 parlay",
                         meta["breakeven_phi_2leg_110_p50"], phi_needed, tol=1e-6,
                         note="the phi a 2-leg -110 parlay needs to break even"))


def verify_own_line(results):
    """Recompute the own-line MAE and paired-test p-values for variant B."""
    mp = pd.read_csv(ROOT / "data" / "derived" / "model_predictions_B.csv")
    metrics = json.load(open(ROOT / "data" / "derived" / "model_metrics.json"))
    b = metrics["variants"]["B"]
    src = (f"{COMMIT_URL} (via committed data/derived/model_predictions_B.csv)")
    for kind, ec, mc, pub_model, pub_mkt, pub_diff, pub_p in [
        ("spread", "err_spread_model", "err_spread_mkt",
         b["spread"]["model_mae"], b["spread"]["market_mae"],
         b["mae_diff_spread_model_minus_market"], b["mae_diff_spread_pvalue"]),
        ("total", "err_total_model", "err_total_mkt",
         b["total"]["model_mae"], b["total"]["market_mae"],
         b["mae_diff_total_model_minus_market"], b["mae_diff_total_pvalue"]),
    ]:
        model_mae = float(mp[ec].abs().mean())
        mkt_mae = float(mp[mc].abs().mean())
        results.append(check(f"ownline:{kind} model MAE", "mean |error| of model", pub_model, model_mae, tol=0.0006, source=src,
                             note="published to 3 decimals; recomputed full precision"))
        results.append(check(f"ownline:{kind} market MAE", "mean |error| of closing line", pub_mkt, mkt_mae, tol=0.0006, source=src))
        d = mp[ec].abs() - mp[mc].abs()
        t = d.mean() / (d.std(ddof=1) / np.sqrt(len(d)))
        p = float(2 * stats.t.cdf(-abs(t), len(d) - 1))
        results.append(check(f"ownline:{kind} MAE diff", "paired |err_model|-|err_mkt| mean", pub_diff, float(d.mean()), tol=0.0006, source=src,
                             note="published to 3 decimals; recomputed full precision"))
        results.append(check(f"ownline:{kind} diff p-value", "paired t-test on |error| difference", pub_p, p, tol=1e-6, source=src))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true",
                    help="also re-download the pinned commit from codeload.github.com (environment-"
                         "dependent; omit for the deterministic, CI-reproducible run)")
    args = ap.parse_args()
    results = []
    verify_dataset_checksums(results)
    if args.live:
        verify_dataset_live(results)
    verify_correlation(results)
    verify_arithmetic(results)
    verify_own_line(results)
    n_pass = sum(1 for r in results if r["pass"] is True)
    n_fail = sum(1 for r in results if r["pass"] is False)
    n_skip = sum(1 for r in results if r["pass"] is None)
    out = {
        "session": "arena/1cd638e3-korea3",
        "generated_utc": "2026-11-13",
        "pinned_commit": PINNED_COMMIT,
        "commit_url": COMMIT_URL,
        "dataset_url": DATASET_URL,
        "checks": results,
        "summary": {"total": len(results), "pass": n_pass, "fail": n_fail, "skipped": n_skip},
        "status": "PASS" if n_fail == 0 else "FAIL",
    }
    (OUT / "results.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"reverify: {n_pass} pass · {n_fail} fail · {n_skip} skipped of {len(results)} checks")
    for r in results:
        if r["pass"] is False:
            print(f"  FAIL {r['check']}: expected {r['expected']} got {r['recomputed']}")
    print(f"status {out['status']}  ->  {OUT / 'results.json'}")
    return 0 if n_fail == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
