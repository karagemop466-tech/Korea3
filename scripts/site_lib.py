"""site_lib.py — tiny static-site toolkit (no framework, no build step, no JS deps)."""
from __future__ import annotations

import html
import os

NAV = [
    ("Dashboard", "index.html", "Overview and headline numbers"),
    ("Executive Summary", "executive-summary.html", "Findings in one page"),
    ("Our Own Line", "own-line.html", "The line we originate"),
    ("Signal Library", "signals.html", "All 18 tested rules"),
    ("Validation Gates", "gates.html", "The 8 gates, per strategy"),
    ("Single Bets", "single-bets.html", "Straight-bet strategies"),
    ("Parlays", "parlays.html", "Leg correlation and pricing"),
    ("Player Props", "player-props.html", "Prop-combo framework"),
    ("Correlation Lab", "correlation.html", "Measured correlations"),
    ("Leaderboard", "leaderboard.html", "Competition and standings"),
    ("Market Data", "market-data.html", "League baselines + explorer"),
    ("Methodology", "methodology.html", "How every number was made"),
    ("Sources", "sources.html", "Tiered source registry"),
    ("Flagged for Review", "flagged.html", "Irregularities and gaps"),
    ("Verification Log", "verification.html", "What was checked"),
]

CSS = r"""
:root{
  --bg:#f6f7f9; --panel:#ffffff; --ink:#14181f; --muted:#5b6472; --line:#e3e7ec;
  --brand:#123a63; --brand-2:#1d5b94; --accent:#0f766e;
  --pass:#0f7a4d; --pass-bg:#e6f5ee; --warn:#8a5a00; --warn-bg:#fdf3e0;
  --fail:#a3242b; --fail-bg:#fdecec; --info:#1f4e8c; --info-bg:#eaf1fb;
  --radius:12px; --shadow:0 1px 2px rgba(16,24,40,.06),0 1px 3px rgba(16,24,40,.10);
}
*{box-sizing:border-box}
html,body{margin:0;padding:0}
body{background:var(--bg);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;-webkit-font-smoothing:antialiased}
a{color:var(--brand-2);text-decoration:none}
a:hover{text-decoration:underline}
code{background:#eef1f5;padding:.12em .38em;border-radius:5px;font-size:.9em}
.wrap{display:flex;min-height:100vh}
/* sidebar */
aside{width:262px;flex:0 0 262px;background:var(--brand);color:#dbe6f2;padding:22px 0;position:sticky;top:0;height:100vh;overflow-y:auto}
aside .brand{padding:0 22px 16px;border-bottom:1px solid rgba(255,255,255,.12);margin-bottom:12px}
aside .brand b{display:block;color:#fff;font-size:16px;letter-spacing:.2px}
aside .brand span{display:block;color:#9db4cd;font-size:11.5px;line-height:1.45;margin-top:5px}
aside nav a{display:block;padding:7px 22px;color:#c9d8e8;font-size:13.5px;border-left:3px solid transparent}
aside nav a:hover{background:rgba(255,255,255,.07);color:#fff;text-decoration:none}
aside nav a.on{background:rgba(255,255,255,.13);color:#fff;border-left-color:#7fd1c3;font-weight:600}
aside .foot{padding:14px 22px;color:#8ba3bd;font-size:11px;line-height:1.5;border-top:1px solid rgba(255,255,255,.12);margin-top:14px}
/* main */
main{flex:1;min-width:0;padding:30px 38px 70px;max-width:1500px}
h1{font-size:25px;margin:0 0 6px;letter-spacing:-.3px}
h2{font-size:18.5px;margin:34px 0 10px;letter-spacing:-.2px;scroll-margin-top:16px}
h3{font-size:15px;margin:22px 0 8px}
p{margin:0 0 12px;max-width:95ch}
.lede{color:var(--muted);font-size:15px;max-width:95ch;margin-bottom:18px}
.crumb{color:var(--muted);font-size:12px;text-transform:uppercase;letter-spacing:.08em;margin-bottom:8px}
/* cards */
.grid{display:grid;gap:14px;margin:16px 0 6px}
.g4{grid-template-columns:repeat(auto-fit,minmax(210px,1fr))}
.g3{grid-template-columns:repeat(auto-fit,minmax(280px,1fr))}
.g2{grid-template-columns:repeat(auto-fit,minmax(340px,1fr))}
.card{background:var(--panel);border:1px solid var(--line);border-radius:var(--radius);padding:16px 18px;box-shadow:var(--shadow)}
.card h3{margin:0 0 6px;font-size:12.5px;text-transform:uppercase;letter-spacing:.07em;color:var(--muted);font-weight:700}
.kpi{font-size:27px;font-weight:700;letter-spacing:-.5px;line-height:1.15}
.kpi.small{font-size:20px}
.sub{color:var(--muted);font-size:12.5px;margin-top:5px}
.note{background:var(--info-bg);border-left:4px solid var(--info);padding:12px 15px;border-radius:0 8px 8px 0;margin:14px 0;font-size:13.5px}
.note.warn{background:var(--warn-bg);border-left-color:var(--warn)}
.note.bad{background:var(--fail-bg);border-left-color:var(--fail)}
.note.good{background:var(--pass-bg);border-left-color:var(--pass)}
/* badges */
.b{display:inline-block;padding:2px 8px;border-radius:999px;font-size:11px;font-weight:700;letter-spacing:.03em;white-space:nowrap}
.b-pass{background:var(--pass-bg);color:var(--pass)}
.b-warn{background:var(--warn-bg);color:var(--warn)}
.b-fail{background:var(--fail-bg);color:var(--fail)}
.b-info{background:var(--info-bg);color:var(--info)}
.b-mut{background:#eef1f5;color:#4a5260}
/* tables */
.tblwrap{overflow-x:auto;border:1px solid var(--line);border-radius:var(--radius);background:var(--panel);box-shadow:var(--shadow);margin:14px 0}
table{border-collapse:collapse;width:100%;font-size:13px}
th,td{padding:8px 11px;text-align:left;border-bottom:1px solid var(--line);vertical-align:top}
th{background:#f0f3f7;font-size:11.5px;text-transform:uppercase;letter-spacing:.05em;color:#46505f;font-weight:700;position:sticky;top:0;z-index:1}
tbody tr:hover{background:#fafbfc}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}
caption{caption-side:top;text-align:left;padding:12px 13px 4px;font-weight:700;font-size:13.5px}
caption .src{display:block;font-weight:400;color:var(--muted);font-size:11.5px;margin-top:3px}
.src{color:var(--muted);font-size:11.5px}
td a.src{font-size:11.5px}
.pos{color:var(--pass);font-weight:600}
.neg{color:var(--fail);font-weight:600}
.mono{font-variant-numeric:tabular-nums}
ul,ol{margin:0 0 12px;padding-left:22px}
li{margin:4px 0}
.small{font-size:12.5px;color:var(--muted)}
hr{border:0;border-top:1px solid var(--line);margin:26px 0}
/* toolbar for explorer */
.tools{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin:12px 0}
input[type=search],select{padding:8px 10px;border:1px solid #cfd6df;border-radius:8px;font-size:13px;background:#fff;color:var(--ink)}
input[type=search]{min-width:240px}
button{padding:8px 13px;border:1px solid var(--brand-2);background:var(--brand-2);color:#fff;border-radius:8px;font-size:13px;cursor:pointer}
button.ghost{background:#fff;color:var(--brand-2)}
footer{margin-top:44px;padding-top:16px;border-top:1px solid var(--line);color:var(--muted);font-size:12px}
@media(max-width:900px){
  .wrap{display:block}
  aside{position:static;width:auto;height:auto;flex:none}
  main{padding:20px 16px 50px}
}
"""


def esc(x) -> str:
    if x is None:
        return ""
    return html.escape(str(x))


def badge(text: str, kind: str = "mut") -> str:
    return f'<span class="b b-{kind}">{esc(text)}</span>'


def verdict_badge(v: str) -> str:
    v = str(v).upper()
    if v == "PASS":
        return badge("PASS", "pass")
    if v == "PROVISIONAL":
        return badge("PROVISIONAL", "warn")
    if v.startswith("NEEDS"):
        return badge(v.replace("_", " "), "info")
    return badge("FAIL", "fail")


def link(url: str, text: str | None = None) -> str:
    if not url:
        return '<span class="src">no source</span>'
    return f'<a href="{esc(url)}" target="_blank" rel="noopener">{esc(text or shorten(url))}</a>'


def shorten(url: str, n: int = 46) -> str:
    u = url.replace("https://", "").replace("http://", "")
    return u if len(u) <= n else u[: n - 1] + "…"


def table(headers: list, rows: list, caption: str = "", source: str = "",
          num_cols: list | None = None, cls: str = "", tbody_id: str = "") -> str:
    """rows: list of lists of already-rendered HTML strings."""
    num_cols = set(num_cols or [])
    cap = ""
    if caption:
        cap = f'<caption>{esc(caption)}'
        if source:
            cap += f'<span class="src">Source: {source}</span>'
        cap += "</caption>"
    th = "".join(
        f'<th class="{"num" if i in num_cols else ""}">{h}</th>' for i, h in enumerate(headers)
    )
    body = []
    for r in rows:
        tds = "".join(
            f'<td class="{"num" if i in num_cols else ""}">{c}</td>' for i, c in enumerate(r)
        )
        body.append(f"<tr>{tds}</tr>")
    idattr = f' id="{tbody_id}"' if tbody_id else ""
    return (f'<div class="tblwrap"><table class="{cls}">{cap}<thead><tr>{th}</tr></thead>'
            f'<tbody{idattr}>' + "".join(body) + "</tbody></table></div>")


def raw_table(headers: list, rows: list, caption: str = "", source: str = "",
              attrs: str = "") -> str:
    """Table kept open (no wrapper) so an explorer can inject <tr> rows into it."""
    th = "".join(f"<th>{h}</th>" for h in headers)
    cap = f"<caption>{esc(caption)}</caption>" if caption else ""
    return (f'<table {attrs}>{cap}<thead><tr>{th}</tr></thead><tbody></tbody></table>')


def card(title: str, value: str, sub: str = "", small: bool = False) -> str:
    cls = "kpi small" if small else "kpi"
    s = f'<div class="sub">{sub}</div>' if sub else ""
    return f'<div class="card"><h3>{title}</h3><div class="{cls}">{value}</div>{s}</div>'


def page(name: str, title: str, body: str, current: str, footer_extra: str = "") -> str:
    nav = []
    for label, href, desc in NAV:
        on = " class=\"on\"" if href == current else ""
        nav.append(f'<a href="{href}"{on} title="{esc(desc)}">{esc(label)}</a>')
    return f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)} · NFL Line Lab</title>
<meta name="description" content="Reproducible NFL line origination, signal testing, validation gates and correlation research.">
<link rel="stylesheet" href="assets/style.css">
</head><body><div class="wrap">
<aside>
  <div class="brand"><b>NFL Line Lab</b><span>Own lines, tested signals,<br>validation gates, measured correlation</span></div>
  <nav>{''.join(nav)}</nav>
  <div class="foot">Data pinned to nflverse/nfldata<br>commit a270278f · 2026-11-01<br><br>Every figure is reproducible from <code>scripts/</code>.</div>
</aside>
<main>
{body}
<footer>
<p><b>NFL Line Lab</b> — built for review, not for staking. Nothing on this site is betting advice.
Market data is community-sourced (open dataset, pinned by commit); rules and settlement mechanics are cited to official NFL and licensed-operator sources.
Every table states its source; anything unconfirmed is blank and listed on <a href="flagged.html">Flagged for Review</a>.</p>
{footer_extra}
</footer>
</main></div>
<script src="assets/app.js"></script>
</body></html>
"""


def write(path: str, content: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(content)
