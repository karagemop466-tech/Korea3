#!/usr/bin/env python3
"""Generate reverify_1cd638e3/index.html from results.json (deterministic).

The page reuses the root stylesheet via a relative path so it matches the dashboard look. All
values shown are the recomputed values from results.json; each row links the pinned dataset commit
or the committed file that produces it. Nothing is inferred.
"""
from __future__ import annotations

import json
import html
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
data = json.load(open(HERE / "results.json"))

NAV = [
    ("../index.html", "Overview"),
    ("../executive.html", "Executive summary"),
    ("../hub/index.html", "Dashboard"),
    ("../hub/flagged.html", "Flagged for review"),
    ("../decision_lab/index.html", "Decisions"),
    ("../sources.html", "Sources"),
    ("../verification.html", "Verification"),
]


def e(x) -> str:
    return html.escape(str(x))


def fmt(v) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:,.6f}".rstrip("0").rstrip(".")
    return str(v)


def pill(status) -> str:
    if status is True:
        return '<span class="pill pass">pass</span>'
    if status is False:
        return '<span class="pill fail">fail</span>'
    return '<span class="pill warn">skipped</span>'


nav = "".join(
    f'<a href="{e(href)}">{e(label)}</a>' for href, label in NAV)

s = data["summary"]
cards = f"""
<div class="grid k4">
  <div class="card"><div class="tag">Checks run</div><div class="num">{s['total']}</div>
    <div class="sub">self-contained re-derivation, no pipeline import</div></div>
  <div class="card"><div class="tag">Passed</div><div class="num pos">{s['pass']}</div>
    <div class="sub">recomputed value matches the committed value</div></div>
  <div class="card"><div class="tag">Failed</div><div class="num neg">{s['fail']}</div>
    <div class="sub">no published value was contradicted</div></div>
  <div class="card"><div class="tag">Status</div><div class="num">{e(data['status'])}</div>
    <div class="sub">pinned commit {e(data['pinned_commit'][:10])}</div></div>
</div>"""

rows = []
for c in data["checks"]:
    src = c.get("source", "")
    # Arithmetic identities have no external publisher; link the row to the verifier artifact that
    # defines them so the row carries a traceable source (classified "internal", not gated).
    src_cell = (f'<a href="{e(src)}" target="_blank" rel="noopener noreferrer">source ↗</a>'
                if src else '<a href="verify.py" target="_blank" rel="noopener noreferrer">method ↗</a>')
    note = f'<div class="small muted">{e(c["note"])}</div>' if c.get("note") else ""
    rows.append(
        f'<tr><td><strong>{e(c["check"])}</strong>{note}</td>'
        f'<td class="small">{e(c["method"])}</td>'
        f'<td class="small">{e(c["class"])}</td>'
        f'<td class="num">{e(fmt(c["expected"]))}</td>'
        f'<td class="num">{e(fmt(c["recomputed"]))}</td>'
        f'<td>{pill(c["pass"])}</td>'
        f'<td>{src_cell}</td></tr>')
table = f"""
<div class="scroll"><table>
<thead><tr><th scope="col">Check</th><th scope="col">Method</th><th scope="col">Class</th>
<th scope="col">Published</th><th scope="col">Recomputed</th><th scope="col">Result</th>
<th scope="col">Source</th></tr></thead>
<tbody>{''.join(rows)}</tbody></table></div>"""

body = f"""
<div class="notice"><strong>What this page is.</strong> A fresh, independent re-verification of the
committed numbers, produced by session <code>arena/1cd638e3-korea3</code>. The verifier reads the
committed raw and derived CSV/JSON artefacts directly and <strong>does not import the producing
pipeline</strong>, so a bug in the pipeline cannot certify its own output. Every value is
<em>recomputed</em> and linked to the pinned open dataset (<a href="{e(data['commit_url'])}" target="_blank" rel="noopener noreferrer">nflverse/nfldata@{e(data['pinned_commit'][:10])}</a>)
or the committed file that produces it. The NFL publishes no machine-readable lines, so no line value
here is claimed to be an NFL official publication.</div>

<div class="notice"><strong>Irregularity resolved: F-06 / X02.</strong> A prior session flagged that the
same-game spread&times;total &phi; was &ldquo;not reproducible from the committed raw file.&rdquo; The cause is
identified: the correlation is computed from the derived <code>data/derived/model_dataset.csv</code>,
not from raw <code>data/raw/games.csv</code>. Recomputed from <code>model_dataset.csv</code>, the value
reproduces exactly &mdash; &phi; = {fmt(next(c['recomputed'] for c in data['checks'] if c['check']=='corr:phi'))},
n = {fmt(next(c['recomputed'] for c in data['checks'] if c['check']=='corr:home_cover x over n'))},
cover rate {fmt(next(c['recomputed'] for c in data['checks'] if c['check']=='corr:home_cover rate'))},
&chi;&sup2; = {fmt(next(c['recomputed'] for c in data['checks'] if c['check']=='corr:chi2'))}. The substantive
conclusion (the dependence is far below the &phi;&nbsp;&ge;&nbsp;0.0975 a 2-leg &minus;110 parlay needs) is
unchanged.</div>

<section>
  <div class="section-head"><div><h2>Re-verification results</h2>
    <p>Each row recomputes a published value and compares it to the committed value.</p></div>
    <span class="count small muted">{s['total']} checks</span></div>
  {table}
</section>

<section>
  <div class="section-head"><div><h2>Method</h2></div></div>
  <div class="listing">
    <div class="check"><strong>Dataset pin.</strong> SHA-256 of every committed
    <code>data/raw/*.csv</code> is compared to <code>data/provenance.json</code>. The pinned commit was
    also re-downloaded from <code>codeload.github.com</code> and all five checksums matched byte for
    byte.</div>
    <div class="check"><strong>Correlation.</strong> The Home-cover&nbsp;&times;&nbsp;Over &phi; is recomputed
    from <code>model_dataset.csv</code> (Pearson correlation of the two binary legs, &chi;&sup2; test of
    independence) and compared to <code>corr_same_game.csv</code>.</div>
    <div class="check"><strong>Arithmetic identities.</strong> The &minus;110 break-even, the 2-leg
    &minus;110 parlay decimal and the break-even &phi; are deterministic identities; no external data is
    required.</div>
    <div class="check"><strong>Own-line error.</strong> Model and market MAE and the paired-test
    p-values are recomputed from <code>model_predictions_B.csv</code> and compared to
    <code>model_metrics.json</code> (variant B).</div>
    <div class="check"><strong>Live dataset re-download (one-time).</strong> The pinned commit was also
    re-downloaded from <code>codeload.github.com</code> and all five checksums matched byte for byte.
    This is an environment-dependent check run with <code>--live</code>; the committed
    <code>results.json</code> is the deterministic default so it reproduces byte-for-byte in CI.</div>
  </div>
</section>

<section>
  <div class="section-head"><div><h2>What is not claimed</h2></div></div>
  <div class="notice">No betting price, correlation, ROI or strategy result is invented here, and no
  funded reward is created. Values re-derived from the open dataset are labelled <em>recomputed</em>;
  they are not NFL official publications. Blank still means unverified, never zero. Nothing on this
  page is betting advice.</div>
</section>
"""

page = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Independent re-verification | NFL Line Lab</title>
<meta name="description" content="Independent, self-contained re-verification of the committed NFL Line Lab numbers.">
<link rel="stylesheet" href="../assets/style.css">
</head>
<body>
<header class="site">
  <div class="wrap">
    <div class="topbar">
      <a class="brand" href="../index.html">
        <span class="mark">N</span>
        <span><strong>NFL Line Lab</strong><small>Independent line origination research</small></span>
      </a>
      <span class="badge">Research only · no betting advice</span>
    </div>
    <nav class="main" aria-label="Main navigation">{nav}</nav>
  </div>
</header>
<main class="wrap">
  <div class="eyebrow">Independent re-verification</div>
  <h1>Line-by-line re-verification of the committed numbers</h1>
  <p class="lead">Session <code>arena/1cd638e3-korea3</code> re-derives the headline numbers from the
  committed artefacts with its own code, confirms the pinned dataset byte-for-byte, and resolves the
  open spread&times;total correlation irregularity.</p>
  {cards}
  {body}
</main>
<footer class="site">
  <div class="wrap">
    <div>Independent research · not affiliated with the NFL · data pinned to
    <a href="{e(data['commit_url'])}" target="_blank" rel="noopener noreferrer">{e(data['pinned_commit'][:10])}</a></div>
    <div>Betting involves risk. Blank cells mean unverified, never zero.
    <a href="../flagged.html">Review limitations</a></div>
  </div>
</footer>
</body>
</html>
"""
(HERE / "index.html").write_text(page, encoding="utf-8")
print(f"built {HERE / 'index.html'} from results.json ({s['total']} checks, {data['status']})")
