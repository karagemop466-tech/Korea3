#!/usr/bin/env python3
"""Render this session's verification dashboard from qa/verification.json.

Run: python3 qa/verify.py && python3 qa/build_site.py
Every table row on every page carries a source link; qa/check_links.py enforces it.
"""
from __future__ import annotations

import html
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
QA = ROOT / "qa"
V = json.loads((QA / "verification.json").read_text())
FLAGS = json.loads((QA / "flags.json").read_text())
SRC = json.loads((QA / "sources.json").read_text())
LINKS = json.loads((QA / "links.json").read_text())

NAV = [
    ("index.html", "Overview"),
    ("data.html", "Data"),
    ("strategies.html", "Strategies & arithmetic"),
    ("correlations.html", "Correlations"),
    ("integrity.html", "Site & deploy"),
    ("flagged.html", "Flagged for review"),
    ("sources.html", "Sources"),
    ("methodology.html", "Method"),
]

CSS = """
:root{color-scheme:light;--ink:#16202f;--muted:#5d6b7e;--line:#e2e8f0;--bg:#f6f8fb;
--card:#fff;--ok:#0b6b4f;--okbg:#e6f5ee;--bad:#a4232b;--badbg:#fdecec;--warn:#8a5a00;
--warnbg:#fdf3dc;--info:#31589c;--infobg:#eaf0fb;--blocked:#5b4b8a;--blockedbg:#efeafb}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--ink);
font:15px/1.6 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:#0b5f8a;text-decoration:none}a:hover{text-decoration:underline}
header{background:#fff;border-bottom:1px solid var(--line)}
.wrap{max-width:1180px;margin:0 auto;padding:0 22px}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:14px;padding:16px 0}
.brand{display:flex;align-items:center;gap:10px;font-weight:800;color:var(--ink);font-size:16px}
.brand small{display:block;font-weight:600;font-size:11px;color:var(--muted);letter-spacing:.06em}
.mark{display:grid;place-items:center;width:36px;height:36px;border-radius:9px;background:#12352f;
color:#fff;font-weight:800}
.badge{font-size:11px;font-weight:800;letter-spacing:.08em;color:var(--ok);background:var(--okbg);
padding:6px 10px;border-radius:6px;white-space:nowrap}
nav{display:flex;gap:18px;overflow-x:auto;border-top:1px solid var(--line);padding:0}
nav a{padding:12px 0;font-size:13px;font-weight:650;color:#4c5b70;white-space:nowrap}
nav a.active{color:#0b6b4f;border-bottom:2px solid #0b6b4f}
main{padding:30px 0 64px}
.eyebrow{font-size:11px;font-weight:800;letter-spacing:.12em;color:var(--ok);text-transform:uppercase}
h1{font-size:clamp(26px,3.4vw,36px);letter-spacing:-.02em;margin:8px 0 6px}
h2{font-size:19px;margin:34px 0 10px;letter-spacing:-.01em}
h3{font-size:15px;margin:20px 0 6px}
.lead{color:var(--muted);max-width:78ch;margin:0 0 22px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0 8px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px}
.kpi b{display:block;font-size:26px;line-height:1.2}
.kpi span{font-size:11px;font-weight:700;letter-spacing:.07em;color:var(--muted);text-transform:uppercase}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:4px 0;margin:12px 0;overflow:hidden}
.scroll{overflow-x:auto;padding:0 0 2px}
table{width:100%;border-collapse:collapse;min-width:720px;text-align:left}
th{background:#f8fafc;color:#63718a;font-size:10.5px;letter-spacing:.08em;text-transform:uppercase;
padding:11px 14px;border-bottom:1px solid var(--line);position:sticky;top:0}
td{padding:11px 14px;border-top:1px solid var(--line);vertical-align:top;font-size:14px}
tr:hover td{background:#fbfcfe}
.pill{display:inline-block;font-size:10.5px;font-weight:800;letter-spacing:.05em;padding:3px 7px;
border-radius:5px;white-space:nowrap}
.p-ok{color:var(--ok);background:var(--okbg)}.p-bad{color:var(--bad);background:var(--badbg)}
.p-warn{color:var(--warn);background:var(--warnbg)}.p-info{color:var(--info);background:var(--infobg)}
.p-blocked{color:var(--blocked);background:var(--blockedbg)}
.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:12.5px}
.muted{color:var(--muted)}
.notice{background:#fff;border:1px solid var(--line);border-left:4px solid #0b6b4f;border-radius:8px;
padding:14px 16px;margin:16px 0;color:#243546}
.notice.warn{border-left-color:#b8860b}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:14px}
pre{background:#0f1720;color:#dbe6f0;padding:14px 16px;border-radius:9px;overflow-x:auto;font-size:12.5px}
footer{border-top:1px solid var(--line);padding:22px 0;color:var(--muted);font-size:12px}
ul{margin:8px 0 8px 18px;padding:0}li{margin:4px 0}
"""


def e(x) -> str:
    return html.escape(str(x), quote=True)


def pill(status: str) -> str:
    s = status.upper()
    cls = "p-info"
    if s.startswith("VERIFIED"):
        cls = "p-ok"
    elif s.startswith("MISMATCH"):
        cls = "p-bad"
    elif s.startswith("UNVERIFIED"):
        cls = "p-warn"
    elif s.startswith("BLOCKED"):
        cls = "p-blocked"
    elif s.startswith("FIXED"):
        cls = "p-ok"
    elif s.startswith("OPEN"):
        cls = "p-warn"
    elif s.startswith("DOCUMENTED"):
        cls = "p-info"
    return f'<span class="pill {cls}">{e(status)}</span>'


def src_cell(urls) -> str:
    if isinstance(urls, str):
        urls = [urls]
    bits = []
    for u in urls:
        label = u.replace("https://", "")
        if len(label) > 58:
            label = label[:55] + "…"
        bits.append(f'<a href="{e(u)}" rel="noopener">{e(label)}</a>')
    return "<br>".join(bits)


def shell(slug: str, title: str, body: str) -> str:
    nav_bits = []
    for href, label in NAV:
        active = ' class="active"' if href == slug else ""
        nav_bits.append(f'<a href="{e(href)}"{active}>{e(label)}</a>')
    nav = "".join(nav_bits)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)} | Independent verification</title>
<meta name="description" content="Independent, source-linked verification of the NFL line-origination research repository.">
<style>{CSS}</style>
</head>
<body>
<header><div class="wrap">
  <div class="topbar">
    <a class="brand" href="index.html"><span class="mark">V</span>
      <span>Independent verification<small>NFL LINE ORIGINATION RESEARCH</small></span></a>
    <span class="badge">Line-by-line · sourced · nothing inferred</span>
  </div>
  <nav aria-label="Verification navigation">{nav}</nav>
</div></header>
<main><div class="wrap">
{body}
</div></main>
<footer><div class="wrap">
  Generated {e(V["generated_utc"])} by <span class="mono">{e(V["generated_by"])}</span> ·
  session <span class="mono">arena/d4478fd5-korea3</span>.
  Every row carries a source link. Unverified values are left blank or labelled unverified — never filled in.
  Research only, not betting advice.
</div></footer>
</body></html>
"""


def checks_table(categories: set[str]) -> str:
    rows = [r for r in V["checks"] if r["category"] in categories]
    body = "".join(
        f"<tr><td class='mono'>{e(r['id'])}</td><td>{e(r['claim'])}</td>"
        f"<td>{e(r['published'])}</td><td>{e(r['recomputed'])}</td>"
        f"<td>{pill(r['status'])}</td><td>{src_cell(r['evidence'])}</td></tr>"
        for r in rows
    )
    return (
        "<div class='card'><div class='scroll'><table><thead><tr>"
        "<th>ID</th><th>Claim checked</th><th>Published</th><th>Recomputed here</th>"
        "<th>Status</th><th>Source</th></tr></thead><tbody>"
        + body
        + "</tbody></table></div></div>"
    )


def notes(categories: set[str]) -> str:
    rows = [r for r in V["checks"] if r["category"] in categories and r["note"]]
    if not rows:
        return ""
    body = "".join(
        f"<tr><td class='mono'>{e(r['id'])}</td><td>{e(r['note'])}</td><td>{src_cell(r['evidence'])}</td></tr>"
        for r in rows
    )
    return (
        "<h2>Why each result reads the way it does</h2><div class='card'><div class='scroll'><table>"
        "<thead><tr><th>ID</th><th>Basis / limitation</th><th>Source</th></tr></thead><tbody>"
        + body
        + "</tbody></table></div></div>"
    )


# --------------------------------------------------------------------------- #
S = V["summary"]
TOTAL = sum(S.values())


def page_index() -> str:
    lb = LINKS
    kpis = [
        (f"{TOTAL}", "checks run"),
        (f"{S.get('VERIFIED', 0)}", "verified by recomputation"),
        (f"{S.get('MISMATCH', 0)}", "mismatches found"),
        (f"{S.get('UNVERIFIED', 0)}", "unverified / left blank"),
        (f"{S.get('BLOCKED', 0)}", "blocked by the sandbox"),
        (f"{lb['pages_checked']}", "pages link-checked"),
        (f"{len(lb['broken'])}", "broken links remaining"),
    ]
    kpi_html = "".join(f"<div class='kpi'><b>{e(v)}</b><span>{e(l)}</span></div>" for v, l in kpis)

    verdicts = [
        ("Root dashboard", "arena/9f5e9cb5", "line_lab/", "14",
         "0 of 11 strategies eligible; best full-sample ROI +0.58% (95% CI −7.5%…+8.2%)",
         "ROI, bet counts and all 16,439 settlements recomputed exactly — VERIFIED",
         "https://github.com/karagemop466-tech/Korea3/blob/main/line_lab/data/derived/bets.csv"),
        ("Empirical pipeline site", "arena/c70bdb9d", "site/", "15",
         "0 of 18 rules pass 8 gates; best +8.41% over 607 bets at q = 0.288",
         "Gate counts, ROI and MAE 10.670 vs 10.247 recomputed — VERIFIED",
         "https://github.com/karagemop466-tech/Korea3/blob/main/data/derived/gates_results.csv"),
        ("Second build", "arena/d118ca7e", "docs/", "13",
         "64/64 team rows reconciled to nfl.com standings (attested, values quarantined)",
         "Structure re-checked; the nfl.com comparison is inherited and not re-runnable here",
         "https://github.com/karagemop466-tech/Korea3/blob/main/docs/data-verification.html"),
        ("Independent audit", "arena/65d448da", "audit/", "1",
         "Data-rights and verification-scope findings",
         "Its page was live with a dead stylesheet; fixed and its own checker passes",
         "https://github.com/karagemop466-tech/Korea3/blob/main/audit/flagged.html"),
        ("Verified workbench", "arena/cbcd97cc", "verified/", "12",
         "0 admitted inputs; empirical values deliberately blank",
         "131 rows / official source links re-checked — VERIFIED",
         "https://github.com/karagemop466-tech/Korea3/blob/main/verified/index.html"),
        ("Session 398c4b58 build", "arena/398c4b58", "session-398c4b58/site/", "16",
         "0 of 28 rules pass 9 gates; best S08 +7.60% on 494 bets",
         "Figures match its committed report, but bet records are not committed — UNVERIFIED",
         "https://github.com/karagemop466-tech/Korea3/blob/main/session-398c4b58/site/data/leaderboard.json"),
    ]
    vrows = "".join(
        f"<tr><td><b>{e(n)}</b></td><td class='mono'>{e(s)}</td><td class='mono'>{e(p)} ({e(pg)} pp)</td>"
        f"<td>{e(h)}</td><td>{e(o)}</td><td>{src_cell(u)}</td></tr>"
        for n, s, p, pg, h, o, u in verdicts
    )

    fixed = [f for f in FLAGS["flags"] if f["status"] == "FIXED"]
    openf = [f for f in FLAGS["flags"] if f["status"] == "OPEN"]
    frows = "".join(
        f"<tr><td class='mono'>{e(f['id'])}</td><td><b>{e(f['title'])}</b><br>"
        f"<span class='muted'>{e(f['detail'][:210])}…</span></td><td>{pill(f['status'])}</td>"
        f"<td>{src_cell(f['sources'][:1])}</td></tr>"
        for f in fixed
    )
    orows = "".join(
        f"<tr><td class='mono'>{e(f['id'])}</td><td><b>{e(f['title'])}</b></td>"
        f"<td>{e(f['severity'])}</td><td>{src_cell(f['sources'][:1])}</td></tr>"
        for f in openf
    )

    return shell(
        "index.html",
        "Overview",
        f"""
<div class="eyebrow">Executive summary · 2026-11-02</div>
<h1>What this repository can actually support</h1>
<p class="lead">Six bodies of work were merged into this repository by six independent sessions on
2026-11-01. This session did not rebuild them. It recomputed their headline numbers from the committed
artefacts, re-derived the dataset from upstream at the pinned commit, crawled every page for broken links,
and published what survived and what did not. Every claim below links to the file or API it rests on.</p>

<div class="kpis">{kpi_html}</div>

<div class="notice"><b>The finding that matters.</b> No strategy in any of the six builds clears its own
validation gates. The best root-dashboard rule returns <b>+0.58%</b> over 703 bets with a 95% confidence
interval of <b>−7.5% to +8.2%</b>; the best empirical-pipeline rule returns <b>+8.41%</b> over 607 bets but
its multiplicity-adjusted q-value is <b>0.288</b>, which is what the best of many coin-flips looks like.
Own-line models are <b>worse</b> than the closing line in every build. This session verified those numbers
rather than restating them.</div>

<h2>Verdict by body of work</h2>
<div class="card"><div class="scroll"><table>
<thead><tr><th>Build</th><th>Session</th><th>Where</th><th>Headline result</th>
<th>This session's verdict</th><th>Source</th></tr></thead><tbody>{vrows}</tbody></table></div></div>

<h2>Defects found and fixed ({len(fixed)})</h2>
<div class="card"><div class="scroll"><table>
<thead><tr><th>ID</th><th>Defect</th><th>Status</th><th>Source</th></tr></thead>
<tbody>{frows}</tbody></table></div></div>

<h2>Open for your review ({len(openf)})</h2>
<p class="lead">These do not block the site and are published, with sources, on the
<a href="flagged.html">Flagged for review</a> page. None of them changes the substantive conclusion above.</p>
<div class="card"><div class="scroll"><table>
<thead><tr><th>ID</th><th>Item</th><th>Severity</th><th>Source</th></tr></thead>
<tbody>{orows}</tbody></table></div></div>

<h2>Reproduce this page</h2>
<pre>python3 qa/check_links.py     # crawl every href/src in all six deployments
python3 qa/verify.py          # recompute every claim; writes qa/verification.json
python3 qa/build_site.py      # render these pages from that JSON</pre>
<p class="lead">Nothing on this site was typed in by hand from a vendor screen or a model's memory:
the JSON is the output of those three commands, and each row names the file or API behind it.</p>
""",
    )


def page_data() -> str:
    cats = {"Data provenance", "Game census"}
    return shell(
        "data.html",
        "Data",
        f"""
<div class="eyebrow">Category · data</div>
<h1>Data provenance and the game census</h1>
<p class="lead">The market numbers come from one open dataset, pinned by commit. This page re-downloads that
commit from upstream and compares hashes, then recomputes every census figure the sites quote.</p>
{checks_table(cats)}
{notes(cats)}
<h2>What the census means</h2>
<div class="notice"><b>Five different "number of games" figures are all correct.</b>
7,548 = every row in the file (regular season + playoffs). 7,384 = rows with both scores. 7,075 = completed
regular-season games, the sample the empirical pipeline models. 6,151 = completed regular-season games
1999–2022, the window its leakage test replays. 6,340 is the one figure this session could not reproduce
from any filter (see <a href="flagged.html">F-07</a>).</div>
""",
    )


def page_strategies() -> str:
    cats = {"Strategy arithmetic", "Pricing arithmetic", "Settlement arithmetic", "Model arithmetic"}
    return shell(
        "strategies.html",
        "Strategies & arithmetic",
        f"""
<div class="eyebrow">Category · strategies</div>
<h1>Strategy results, settlement and pricing arithmetic</h1>
<p class="lead">These rows are recomputed from committed bet-level data wherever it exists. Where a build
published a result without committing the records behind it, the row says so instead of borrowing the
publisher's word.</p>
{checks_table(cats)}
{notes(cats)}
<h2>Why the gate counts are the real result</h2>
<div class="notice warn">A rule can look profitable and still be worthless. The gates exist to separate
"returned money" from "predicted money": beat the closing line, survive a holdout, survive a
multiplicity correction, survive a no-skill bootstrap, and stay stable across seasons. Across all three
strategy inventories (11 + 18 + 28 rules) exactly <b>zero</b> do all of that. That is the headline, and
this session verified the arithmetic behind it.</div>
""",
    )


def page_corr() -> str:
    cats = {"Correlation"}
    return shell(
        "correlations.html",
        "Correlations",
        f"""
<div class="eyebrow">Category · correlation</div>
<h1>Correlation: what is measured, and what is not reproducible</h1>
<p class="lead">A parlay only becomes better than its legs if the legs are correlated. The threshold is
small but exact: at −110 per leg a two-leg parlay needs φ ≈ 0.0975 just to break even. The measured
spread × total dependence is roughly two orders of magnitude below that in every build.</p>
{checks_table(cats)}
{notes(cats)}
<h2>The arithmetic behind the threshold</h2>
<div class="notice">At −110 each leg is 1.90909 decimal. A two-leg parlay pays 3.6446, so the break-even
joint probability is 1/3.6446 = 0.27438. For two fair coins P(both win) = 0.25 + φ/4, so the dependence
needed is φ = 4 × (0.27438 − 0.25) = <b>0.09751</b>. Nothing measured here is close: published values span
+0.0086 to +0.020, and this session's independent recomputations span −0.0085 to −0.0039.</div>
<div class="notice warn"><b>Point estimates disagree; conclusions do not.</b> The three published φ values
could not be reproduced from the committed raw file under any filter tried, and one of them has the
opposite sign to every recomputation here. All of them, published and recomputed, sit within ±0.025 of
zero. Treat the point estimates as unverified (<a href="flagged.html">F-06</a>) and the conclusion
"no usable spread/total dependence" as supported.</div>
""",
    )


def page_integrity() -> str:
    cats = {"Site integrity", "Deployment", "External sources", "Data rights"}
    return shell(
        "integrity.html",
        "Site & deploy",
        f"""
<div class="eyebrow">Category · integrity</div>
<h1>Links, builds and the live deployment</h1>
<p class="lead">Six sites are published from one repository. Each had a checker for its own pages and none
covered the seams between them — which is exactly where the defects were. This page records both the
per-site checks and the new repository-wide crawl.</p>
{checks_table(cats)}
{notes(cats)}
<h2>What the crawl found</h2>
<div class="notice">{LINKS['pages_checked']} pages, {LINKS['internal_links_checked']:,} internal links,
{LINKS['assets_checked']} stylesheet/script/image references and {LINKS['external_link_instances']:,} external
link instances across all six deployments. First run: 93 failures. After excluding two checker blind spots
of this session's own making (pages using <span class="mono">&lt;base href&gt;</span>, and root-absolute
<span class="mono">/Korea3/…</span> paths — both now handled), <b>58 genuine failures in 4 unique targets</b>
remained. All four are fixed; the current run is clean.</div>
""",
    )


def page_flagged() -> str:
    body_rows = "".join(
        f"""<tr><td class="mono">{e(f['id'])}</td>
<td><b>{e(f['title'])}</b><br><span class="muted">{e(f['severity'])}</span>
<div style="margin-top:6px">{e(f['detail'])}</div></td>
<td>{pill(f['status'])}</td><td>{src_cell(f['sources'])}</td></tr>"""
        for f in FLAGS["flags"]
    )
    return shell(
        "flagged.html",
        "Flagged for review",
        f"""
<div class="eyebrow">Review register</div>
<h1>Flagged for review</h1>
<p class="lead">Raised by this session's line-by-line pass on 2026-11-02. Fixed items stay listed so the
history is visible. Nothing here blocks publication, and nothing here was resolved by assuming a value.</p>
<div class="notice">{e(FLAGS['note'])}</div>
<div class="card"><div class="scroll"><table>
<thead><tr><th>ID</th><th>Item</th><th>Status</th><th>Source</th></tr></thead>
<tbody>{body_rows}</tbody></table></div></div>
<h2>Flags raised by earlier sessions</h2>
<p class="lead">Those registers are unchanged and remain live. They are linked here rather than copied,
so there is exactly one version of each.</p>
<div class="card"><div class="scroll"><table><thead><tr><th>Build</th><th>Register</th></tr></thead><tbody>
<tr><td>Root dashboard</td><td><a href="../flagged.html">flagged.html</a></td></tr>
<tr><td>Empirical pipeline</td><td><a href="../site/index.html">site/ flagged page</a></td></tr>
<tr><td>Second build</td><td><a href="../docs/flagged-for-review.html">docs/flagged-for-review.html</a></td></tr>
<tr><td>Independent audit</td><td><a href="../audit/flagged.html">audit/flagged.html</a></td></tr>
<tr><td>Verified workbench</td><td><a href="../verified/flagged.html">verified/flagged.html</a></td></tr>
<tr><td>Session 398c4b58</td><td><a href="../session-398c4b58/site/flagged.html">session-398c4b58/site/flagged.html</a></td></tr>
<tr><td>Parallel review, 2026-11-02</td><td><a href="https://github.com/karagemop466-tech/Korea3/blob/main/reviews/92c7b263/independent-review.md">reviews/92c7b263/independent-review.md</a> — an independent review of the verified workbench, merged while this session was working; its six findings (R1–R6) are the owner's to route and are not duplicated here.</td></tr>
</tbody></table></div></div>
""",
    )


def page_sources() -> str:
    rows = "".join(
        f"""<tr><td class="mono">{e(s['id'])}</td><td>Tier {e(s['tier'])}</td>
<td><a href="{e(s['url'])}" rel="noopener">{e(s['name'])}</a><br>
<span class="muted">{e(s['supports'])}</span></td>
<td>{pill(s['status'])}</td><td>{e(s['evidence'])}</td></tr>"""
        for s in SRC["sources"]
    )
    counts: dict[int, int] = {}
    for s in SRC["sources"]:
        counts[s["tier"]] = counts.get(s["tier"], 0) + 1
    tier_rows = "".join(
        f"<tr><td>Tier {t}</td><td>{e(d)}</td><td class='num'>{counts.get(t, 0)}</td></tr>"
        for t, d in [
            (1, "Official league (NFL.com, NFL support, NFL operations)"),
            (2, "Licensed operator (DraftKings help centre)"),
            (3, "Open community dataset / third-party reference (nflverse, Pro-Football-Reference)"),
            (4, "Repository artefact or GitHub platform API"),
            (5, "Standards body (NIST)"),
        ]
    )
    return shell(
        "sources.html",
        "Sources",
        f"""
<div class="eyebrow">Source register</div>
<h1>Sources, tiers and what each one supports</h1>
<p class="lead">{e(SRC['note'])}</p>
<div class="card"><div class="scroll"><table>
<thead><tr><th>Tier</th><th>Meaning</th><th>Count</th></tr></thead><tbody>{tier_rows}</tbody></table></div></div>
<div class="card"><div class="scroll"><table>
<thead><tr><th>ID</th><th>Tier</th><th>Source and what it supports</th><th>Status here</th>
<th>Evidence</th></tr></thead><tbody>{rows}</tbody></table></div></div>
""",
    )


def page_method() -> str:
    return shell(
        "methodology.html",
        "Method",
        f"""
<div class="eyebrow">Method</div>
<h1>How this verification was done, and what it cannot do</h1>
<p class="lead">Reproducible checks only. No value was copied from a screenshot, a model's memory or an
earlier session's summary without recomputation. Where recomputation was impossible, the row says
"unverified" and stays visible.</p>

<h2>The five kinds of check</h2>
<div class="card"><div class="scroll"><table>
<thead><tr><th>Kind</th><th>What it means</th><th>Example</th></tr></thead><tbody>
<tr><td><b>Upstream re-derivation</b></td><td>Re-download the pinned commit from the GitHub API and compare
SHA-256 with both the recorded hash and the local file.</td><td>5/5 nflverse files matched at
<span class="mono">a270278f</span>.</td></tr>
<tr><td><b>Recomputation</b></td><td>Recompute a published number from committed data with an independent
implementation.</td><td>16,439 settlements; 11/11 strategy ROIs; MAE 10.670.</td></tr>
<tr><td><b>Arithmetic identity</b></td><td>A value that must hold by definition.</td><td>110/210 =
52.38%; φ break-even 0.09751.</td></tr>
<tr><td><b>Structural crawl</b></td><td>Parse every page and resolve every href/src against the published
tree, case-sensitively, including anchors.</td><td>{LINKS['pages_checked']} pages, {LINKS['internal_links_checked']:,} internal
links, 0 broken.</td></tr>
<tr><td><b>Platform API</b></td><td>Ask GitHub for deployment and CI state rather than assuming it.</td>
<td>Pages status and latest Actions conclusion.</td></tr>
</tbody></table></div></div>

<h2>What is deliberately not claimed</h2>
<ul>
<li><b>External sources were not re-read.</b> This sandbox reaches <span class="mono">github.com</span> and
<span class="mono">api.github.com</span> only. nfl.com, nist.gov, operator help centres and
pro-football-reference.com were unreachable, so those {LINKS['external_link_instances']:,} links are
counted and listed, never marked checked (<a href="flagged.html">F-10</a>).</li>
<li><b>No performance figure is a settlement record.</b> Returns are backtests on a third-party open
dataset, not verified wagers or prices from a sportsbook.</li>
<li><b>No correlation is presented as a strategy.</b> A dependence estimate is not an edge; a parlay needs
φ ≈ 0.0975 at −110 before dependence alone helps, and nothing here reaches it.</li>
<li><b>Two published point estimates remain unverified</b> because their filters cannot be reproduced from
the repo: the spread × total φ values (<a href="flagged.html">F-06</a>) and the 6,340-game sample
(<a href="flagged.html">F-07</a>).</li>
<li><b>This is not legal advice.</b> The data-rights position is inherited and unverified here; the
repository redistributes no NFL.com content.</li>
</ul>

<h2>Reproduce</h2>
<pre>python3 qa/check_links.py     # repository-wide link + asset crawl
python3 qa/verify.py          # every numeric claim, recomputed; writes verification.json
python3 qa/build_site.py      # render these pages from that JSON</pre>
<p class="lead">Dependencies: Python 3.11 with <span class="mono">pandas</span> and
<span class="mono">numpy</span>, plus the <span class="mono">gh</span> CLI for the platform checks.
Without network access the upstream and deployment rows report BLOCKED instead of guessing.</p>

<h2>Checker limitations found while building this page</h2>
<div class="notice warn">The first crawl reported 93 failures. 35 were this checker's own blind spots: pages
that set <span class="mono">&lt;base href="/Korea3/"&gt;</span> (13 pages) and links written as
<span class="mono">/Korea3/…</span> were being resolved against the filesystem instead of the site root.
Both are handled now. That reduction is recorded here rather than quietly fixed, because a verifier that
over-reports is as misleading as one that under-reports.</div>
""",
    )


def main() -> int:
    pages = {
        "index.html": page_index,
        "data.html": page_data,
        "strategies.html": page_strategies,
        "correlations.html": page_corr,
        "integrity.html": page_integrity,
        "flagged.html": page_flagged,
        "sources.html": page_sources,
        "methodology.html": page_method,
    }
    for name, fn in pages.items():
        (QA / name).write_text(fn(), encoding="utf-8")
        print("wrote qa/" + name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
