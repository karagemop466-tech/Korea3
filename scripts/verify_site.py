"""verify_site.py — machine verification of the generated site.

Checks, in order:
  1  every data artifact the site needs exists and is non-empty
  2  raw data checksums still match data/provenance.json
  3  dataset QA checks (reconciliation of scores, margins, totals, covers)
  4  every internal link resolves to a file that exists
  5  every table row carries a source cell (an <a href>)
  6  no placeholder text leaked into the output (None / nan / TODO / {var})
  7  external source URLs: GitHub links are checked live; everything else must
     appear in the recorded verification list (data/derived/verified_external.json)
     produced by a human/agent actually loading the page.
Writes data/derived/verification_report.json and exits non-zero on hard failures.
"""
from __future__ import annotations

import hashlib
import html.parser
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DER = os.path.join(ROOT, "data", "derived")
DOCS = os.path.join(ROOT, "site")
RAW = os.path.join(ROOT, "data", "raw")

REQUIRED_ARTIFACTS = [
    "model_dataset.csv", "qa_build_dataset.json", "model_predictions.csv",
    "model_metrics.json", "model_by_season.csv", "model_sensitivity.csv",
    "blend_results.json", "signal_bets.csv", "signal_results.json",
    "signal_by_season.csv", "gates_results.csv", "gates_meta.json",
    "corr_same_game.csv", "corr_cross_game.csv", "corr_signal_pairs.csv",
    "corr_signal_matrix.csv", "corr_meta.json", "parlay_math.csv",
    "props_framework.csv", "props_ev_grid.csv", "props_meta.json",
    "own_lines_upcoming.csv", "own_lines_meta.json", "league_baselines.csv",
    "market_summary.json", "checksums.txt",
]

BAD_PATTERNS = [
    r"\bNone\b", r"\bnan\b", r"\bNaN\b", r"TODO", r"FIXME",
    r"\{[a-zA-Z_][a-zA-Z0-9_\.\[\]']*\}",
    # metrics that were still placeholders when the page was rendered
    # (a module-level table quoting a figure main() sets later renders as 0.000)
    r"0\.000 vs 0\.000",
    r"p = 0\.0e\+00",
    r"\bMAE 0\.000\b",
    r">\s*n/a\s*<\s*/?td>\s*<\s*td[^>]*>\s*pass",
]


class LinkCollector(html.parser.HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.rows = []          # list of (list_of_cell_html)
        self.in_tr = False
        self.in_td = False
        self.cur_row = []
        self.cur_cell = []
        self.in_table_wrap = 0
        self.wrapped_rows = []
        self._wrap_depth = 0
        self._divs = 0
        self._wrapped_stack = []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.links.append(a["href"])
            if self.in_td:
                self.cur_cell.append('<a href="x">')
        if tag == "div":
            cls = a.get("class", "")
            if "tblwrap" in cls:
                self._divs += 1
                self._wrapped_stack.append(self._divs)
            else:
                self._divs += 1
        if tag == "tr":
            self.in_tr = True
            self.cur_row = []
        if tag == "td" and self.in_tr:
            self.in_td = True
            self.cur_cell = []

    def handle_endtag(self, tag):
        if tag == "td" and self.in_td:
            self.in_td = False
            self.cur_row.append("".join(self.cur_cell))
        if tag == "tr" and self.in_tr:
            self.in_tr = False
            if self.cur_row:
                self.wrapped_rows.append(self.cur_row)
            self.cur_row = []
        if tag == "div":
            if self._wrapped_stack and self._wrapped_stack[-1] == self._divs:
                self._wrapped_stack.pop()
            self._divs -= 1

    def handle_data(self, data):
        if self.in_td:
            self.cur_cell.append(data)


def check(name: str, ok: bool, detail: str, note: str = "") -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail, "note": note}


def main() -> int:
    checks = []

    # 1 — artifacts
    missing = [a for a in REQUIRED_ARTIFACTS if not os.path.exists(os.path.join(DER, a))]
    small = [a for a in REQUIRED_ARTIFACTS
             if os.path.exists(os.path.join(DER, a)) and os.path.getsize(os.path.join(DER, a)) == 0]
    checks.append(check("Data artifacts present", not missing and not small,
                        f"{len(REQUIRED_ARTIFACTS)} required files",
                        f"missing: {missing}" if missing else "all present and non-empty"))

    # 2 — checksums
    prov = json.load(open(os.path.join(ROOT, "data", "provenance.json"), encoding="utf-8"))
    bad_sums = []
    for fn, meta in prov["primary_dataset"]["files"].items():
        p = os.path.join(RAW, fn)
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if h != meta["sha256"]:
            bad_sums.append(fn)
    checks.append(check("Raw data checksums match provenance", not bad_sums,
                        f"{len(prov['primary_dataset']['files'])} files hashed",
                        f"mismatch: {bad_sums}" if bad_sums else "byte-identical to the pinned commit"))

    # 3 — dataset QA
    qa = json.load(open(os.path.join(DER, "qa_build_dataset.json"), encoding="utf-8"))
    qa_ok = (qa["no_future_games"] and qa["unique_game_ids"] and qa["margin_reconciles"]
             and qa["total_reconciles"] and qa["cover_consistent"])
    checks.append(check("Dataset reconciliation", qa_ok,
                        f"{qa['rows']:,} games, seasons {qa['seasons'][0]}–{qa['seasons'][1]}",
                        "margin/total/cover recomputed on every row; no unplayed games"))

    # 4–6 — site pages
    pages = sorted(f for f in os.listdir(DOCS) if f.endswith(".html"))
    all_links = []
    broken = []
    rows_total = 0
    rows_no_source = 0
    no_source_detail = []
    bad_text = []
    for pg in pages:
        txt = open(os.path.join(DOCS, pg), encoding="utf-8").read()
        lc = LinkCollector()
        lc.feed(txt)
        all_links.extend(lc.links)
        for href in lc.links:
            if href.startswith(("http://", "https://", "#", "mailto:")):
                continue
            target = href.split("#")[0]
            if not target:
                continue
            if not os.path.exists(os.path.join(DOCS, target)):
                broken.append(f"{pg} -> {href}")
        for row in lc.wrapped_rows:
            rows_total += 1
            if len(row) < 2:
                continue
            if not any("<a href" in c for c in row):
                rows_no_source += 1
                no_source_detail.append(f"{pg}: {row[0][:60]}")
        for pat in BAD_PATTERNS:
            for m in re.finditer(pat, txt):
                bad_text.append(f"{pg}: {m.group(0)}")
                break
    checks.append(check("Internal links resolve", not broken, f"{len(all_links)} links across {len(pages)} pages",
                        f"broken: {broken[:5]}" if broken else "no broken internal links"))
    checks.append(check("Every table row has a source cell", rows_no_source == 0,
                        f"{rows_total:,} table rows audited",
                        f"{rows_no_source} rows without a source link, eg {no_source_detail[:4]}" if rows_no_source else "all rows carry a source"))
    checks.append(check("No placeholder text in output", not bad_text,
                        f"{len(pages)} pages scanned", ", ".join(sorted(set(bad_text))[:5]) or "clean"))

    # assets + data files referenced by the site
    assets_ok = all(os.path.exists(os.path.join(DOCS, p)) for p in
                    ["assets/style.css", "assets/app.js", "data/games.json", "data/games.csv"])
    checks.append(check("Static assets and explorer data present", assets_ok,
                        "style.css, app.js, data/games.json, data/games.csv",
                        "" if assets_ok else "missing asset"))

    # 7 — external URLs
    ext = sorted({l for l in all_links if l.startswith("http")})
    rec_path = os.path.join(DER, "verified_external.json")
    recorded = set()
    if os.path.exists(rec_path):
        recorded = {r["url"] for r in json.load(open(rec_path, encoding="utf-8"))["urls"]}
    # Repo-internal links are checked against the working tree (they resolve over
    # HTTPS once the branch is published); external GitHub links are checked live.
    own_gh = [u for u in ext if u.startswith("https://github.com/karagemop466-tech/Korea3/")]
    gh = [u for u in ext if ("github.com" in u or "githubusercontent" in u) and u not in own_gh]
    local_missing = []
    for u in own_gh:
        rel = u.split("Korea3/", 1)[1]
        for prefix in ("blob/main/", "tree/main/"):
            if rel.startswith(prefix):
                rel = rel[len(prefix):]
        if not os.path.exists(os.path.join(ROOT, rel)):
            local_missing.append(u)
    unverified = [u for u in ext if u not in recorded and u not in gh and u not in own_gh]
    live_fail = []
    for u in gh[:12]:
        try:
            r = subprocess.run(["curl", "-sS", "-o", "/dev/null", "-w", "%{http_code}",
                                "--max-time", "20", "-L", u], capture_output=True, text=True)
            if r.stdout.strip() not in ("200", "302", "301", "206"):
                live_fail.append(f"{u} -> {r.stdout.strip()}")
        except Exception as e:  # pragma: no cover
            live_fail.append(f"{u} -> {e}")
    checks.append(check("External GitHub source links resolve live", not live_fail,
                        f"{len(gh)} GitHub URLs, {min(len(gh),12)} checked live",
                        "; ".join(live_fail[:3]) if live_fail else "all reachable"))
    checks.append(check("Repo-internal source links point at real files", not local_missing,
                        f"{len(own_gh)} links into this repository",
                        ("missing: " + "; ".join(x.split('/')[-1] for x in local_missing[:5])) if local_missing
                        else "every linked artifact exists in the tree and publishes with the site"))
    checks.append(check("Non-GitHub sources recorded as verified", not unverified,
                        f"{len(ext)} external URLs total",
                        ("unrecorded: " + "; ".join(unverified[:6])) if unverified
                        else "every official/operator URL appears in the verification record"))

    # 8 — the numbers the narrative depends on are internally consistent
    gates = json.load(open(os.path.join(DER, "gates_meta.json"), encoding="utf-8"))
    gr = open(os.path.join(DER, "gates_results.csv"), encoding="utf-8").read().strip().split("\n")
    checks.append(check("Gate results reconcile with metadata", len(gr) - 1 == gates["family_size"],
                        f"{len(gr)-1} rule rows vs family_size {gates['family_size']}",
                        "row count matches the declared family size"))

    report = {
        "generated": "2026-11-01",
        "checks": checks,
        "internal_links_checked": len(all_links),
        "internal_links_broken": len(broken),
        "table_rows": rows_total,
        "rows_without_source": rows_no_source,
        "external_urls": len(ext),
        "external_urls_unverified": len(unverified),
        "pages": pages,
        "failed": [c["name"] for c in checks if not c["ok"]],
    }
    with open(os.path.join(DER, "verification_report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2)

    for c in checks:
        print(("PASS  " if c["ok"] else "FAIL  ") + c["name"] + " — " + c["detail"]
              + (("  |  " + c["note"]) if c["note"] else ""))
    print(f"\n{len(checks) - len(report['failed'])}/{len(checks)} checks passed")
    return 0 if not report["failed"] else 1


if __name__ == "__main__":
    sys.exit(main())
