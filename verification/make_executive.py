NAV = [("index.html","Overview"),("executive.html","Executive summary"),("leaderboard.html","Leaderboard"),
("strategies.html","Strategies"),("validation.html","Validation"),("correlations.html","Correlations"),
("parlays.html","Parlays"),("props.html","Player props"),("lines.html","Live lines"),("data.html","Data"),
("sources.html","Sources"),("flagged.html","Flagged for review"),("methodology.html","Method"),
("requirements.html","Requirements"),("sessions.html","All sessions"),("verified/index.html","Verified workbench")]
parts = []
for u, t in NAV:
    act = ' class="active"' if u == "executive.html" else ""
    parts.append('<a href="' + u + '"' + act + '>' + t + '</a>')
nav = "".join(parts)
PIN = "https://github.com/nflverse/nfldata/blob/a270278f3ac4e937295fe6a27814b3c4a2b62645/data/games.csv"
NFL110 = "https://support.nfl.com/hc/en-us/articles/35869703876244-What-is-a-money-line"
DK = "https://support.draftkings.com/dk/en-us/understanding-odds?id=kb_article_view&sysparm_article=KB0010466"
FD = "https://www.fanduel.com/fanduel-sportsbook-house-rules-ct"
TERM = "https://www.nfl.com/legal/terms/"
REPO = "https://github.com/karagemop466-tech/Korea3/blob/main/"
def src(url, label="source ↗"): return f'<a href="{url}" target="_blank" rel="noopener noreferrer">{label}</a>'
def table(headers, rows, caption=""):
    th = "".join(f'<th scope="col">{h}</th>' for h in headers)
    tb = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows)
    cap = f"<caption>{caption}</caption>" if caption else ""
    return f'<div class="scroll"><table>{cap}<thead><tr>{th}</tr></thead><tbody>{tb}</tbody></table></div>'

findings = table(["#","Finding","Value (recomputed 2026-11-02)","Source"], [
 ["1","Own line vs closing line (spread MAE, n=6,827)","10.670 vs 10.247 pts · p ≈ 4.9×10⁻²⁴", src(PIN)],
 ["2","Strategies passing all gates","0 / 18 (8 gates) · 0 / 11 (9 gates) · 0 / 8 verified (10 gates)", src(NFL110, "−110 break-even ↗")],
 ["3","Spread × total correlation φ (n=6,784)","+0.0086 · 95% CI −0.0162 … +0.0332", src(PIN)],
 ["4","Break-even φ, 2-leg parlay @ −110","0.0975 (measured spread×total φ is ~0)", src(DK)],
 ["5","Moneyline × spread φ (same team)","0.6724 — already re-priced as SGP", src(FD, "house rules ↗")],
 ["6","Player-prop measured correlations",'<a class="flag" href="flagged.html">unverified — blank</a> (8 combos, framework only)', src(REPO+"data/derived/props_framework.csv","framework ↗")],
 ["7","Verified empirical values (official-evidence layer)","0 · reward-eligible strategies 0", '<a href="verified/index.html">verified workbench</a>'],
], "Headline findings. Market numbers come from the pinned Tier-3 dataset (the NFL publishes no lines); rules/prices cite Tier-1/2 official sources.")

gates = table(["Gate","Requirement (18-rule family)","Pass","Source"], [
 ["G1","Sample size n ≥ 200 (≥100 confirmation)","17/18", src(REPO+"data/derived/gates_results.csv","results ↗")],
 ["G2","Positive expectation ROI &gt; 0","5/18", src(NFL110)],
 ["G3","ROI &gt; 0 in 2000–15 and 2016–26","5/18", src(REPO+"data/derived/gates_results.csv","results ↗")],
 ["G4","Multiplicity BH q ≤ 0.10","<strong>0/18</strong>", src(REPO+"data/derived/gates_meta.json","meta ↗")],
 ["G5","Concentration / season stability","13/18", src(REPO+"data/derived/gates_results.csv","results ↗")],
 ["G6","Profitable at −115 stress price","5/18", src(DK)],
 ["G7","Profitable vs second line source","9/18 (2 n/a)", src(PIN)],
 ["G8","Luck-adjusted (shrunk) ROI ≥ 0.5%","6/18", src(REPO+"data/derived/gates_meta.json","meta ↗")],
], "G4 binds every serious candidate: searching 18 rules is itself the reason nothing can be promoted yet.")

prov = table(["Rank","Provisional strategy (7/8 gates)","Bets","ROI","Luck-adj. ROI","q","Source"], [
 ["1","S14 · Wind 15+ mph: unders (weather field unverified)",'607','<span class="pos">+8.41%</span>','+2.48%','0.288', src(REPO+"data/derived/signal_bets.csv","bets ↗")],
 ["2","S16 · Week 1 unders",'425','<span class="pos">+5.42%</span>','+1.22%','0.971', src(REPO+"data/derived/signal_bets.csv","bets ↗")],
 ["3","S05 · Away team off a bye",'346','<span class="pos">+4.71%</span>','+0.90%','0.971', src(REPO+"data/derived/signal_bets.csv","bets ↗")],
 ["4","S10 · Rest edge 4+ days to away team",'372','<span class="pos">+4.30%</span>','+0.86%','0.971', src(REPO+"data/derived/signal_bets.csv","bets ↗")],
], "Provisional = tracked, not staked, not rewarded. All four fail only G4.")

corr = table(["Pair","n","phi","95% CI","Reading","Source"], [
 ["Home cover × Over","6,784","+0.0086","−0.0162 … +0.0332","Independent", src(PIN)],
 ["Favourite cover × Over","6,784","−0.0011","−0.0259 … +0.0237","Independent", src(PIN)],
 ["Home ML win × Home cover","6,784","+0.6724","+0.6553 … +0.6894","Strong — priced as SGP", src(FD,"house rules ↗")],
 ["Home ML win × Over","6,784","−0.0139","−0.0380 … +0.0094","Independent", src(PIN)],
 ["Cross-game (pooled, 28 seasons)","—","−0.0239","p = 0.10 vs 0","Independent", src(REPO+"data/derived/corr_meta.json","meta ↗")],
 ["EV at phi = 0, legs @ −110","2 legs / 3 legs","−8.88% / −13.03%","—","Vig compounds", src(DK)],
], "Pushes excluded. Break-even phi: 0.0975 (2 legs), 0.0749 (3 legs) at −110.")

verify = table(["Check (2026-11-02)","Result","Source"], [
 ["Independent reproduction (fresh code)","<strong>66/66 PASS</strong>", src(REPO+"verification/report.json","report ↗")],
 ["scripts/verify_site.py","11/11 PASS", src(REPO+"scripts/verify_site.py","code ↗")],
 ["line_lab/check_site.py","OK · 14 pages", src(REPO+"line_lab/check_site.py","code ↗")],
 ["Verified workbench checker","OK · 12 pages · 131 sourced rows", '<a href="verified/index.html">workbench</a>'],
 ["Unit tests (synthetic fixtures)","24 passed", src(REPO+"tests/test_lab_pricing.py","tests ↗")],
 ["Link audit (109 pages)","0 broken internal links", src(REPO+"verification/link_audit.json","audit ↗")],
 ["Docs pipeline rebuild","Byte-identical", src(REPO+"pipeline/run_all.sh","pipeline ↗")],
 ["NFL Terms §§1.1/1.3 re-opened","No-scraping basis confirmed verbatim", src(TERM,"NFL Terms ↗")],
], "Full line-by-line detail: verification/REPORT.md in the repository.")

html = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Executive summary | NFL Line Lab</title>
<meta name="description" content="Consolidated executive summary: NFL line origination, tested signals, validation gates, correlations, parlays, player props and leaderboard — independently re-verified 2026-11-02.">
<link rel="stylesheet" href="assets/style.css">
<script src="assets/app.js" defer></script>
</head>
<body>
<header class="site">
  <div class="wrap">
    <div class="topbar">
      <a class="brand" href="index.html"><span class="mark">N</span><span><strong>NFL Line Lab</strong><small>Independent line origination research</small></span></a>
      <span class="badge">Research only · no betting advice</span>
    </div>
    <nav class="main" aria-label="Main navigation">""" + nav + """</nav>
  </div>
</header>
<main class="wrap">
  <div class="eyebrow">Executive summary · consolidated 2026-11-02</div>
  <h1>Executive summary</h1>
  <p class="lead">One page for the whole project: own NFL lines, 29 tested strategies across two
  pre-registered families, three gate systems, measured correlations, parlay arithmetic, a
  player-prop framework with honestly blank values, and a leaderboard that has correctly paid
  nobody. Every number here was independently recomputed on 2026-11-02 (66/66 checks pass).</p>
  <div class="notice"><strong>Bottom line.</strong> Origination works as research; nothing tested
  works as edge. The own line loses to the close by 0.42 pts/game, the best raw signal
  (+8.41%, 607 bets) dies on multiplicity, same-game spread×total correlation is zero where a
  parlay needs φ ≥ 0.0975, and the official-evidence layer publishes zero verified values
  because no licensed dataset exists. That is the finding — measurement, not picks.
  Full text: <a href=\"""" + REPO + """CONSOLIDATED_EXECUTIVE_SUMMARY.md\">CONSOLIDATED_EXECUTIVE_SUMMARY.md ↗</a></div>

<section><div class="section-head"><div><h2>Headline findings</h2></div></div>""" + findings + """</section>
<section><div class="section-head"><div><h2>Validation gates</h2><p>Eight mandatory gates (18-rule family). The root dashboard runs nine; the verified workbench ten, fail-closed. Zero strategies pass any complete set.</p></div></div>""" + gates + """</section>
<section><div class="section-head"><div><h2>Leaderboard — provisional tier only</h2><p>Rewards pay only gate-clearing tiers, split evenly (never return-weighted). Eligible today: <strong>0</strong>. <a href="leaderboard.html">Full leaderboard →</a></p></div></div>""" + prov + """</section>
<section><div class="section-head"><div><h2>Correlations &amp; parlays</h2><p><a href="correlations.html">Correlation lab →</a> · <a href="parlays.html">Parlays →</a> · <a href="props.html">Player props (blank by design) →</a></p></div></div>""" + corr + """</section>
<section><div class="section-head"><div><h2>Verification performed</h2><p>Session <code>arena/d7d4d48d-korea3</code>, 2026-11-02. Irregularities (incl. this session's I-01…I-05) are on <a href="flagged.html">Flagged for review</a> and in the consolidated summary §7.</p></div></div>""" + verify + """</section>

<section><div class="grid k3">
  <div class="card"><h3><a href="lines.html">Live own lines</a></h3><p class="small muted">164 unplayed fixtures priced; 28 with a market line to compare.</p></div>
  <div class="card"><h3><a href="verified/index.html">Verified workbench</a></h3><p class="small muted">Official-evidence only. Unverified prices, correlations, ROI and rewards stay blank.</p></div>
  <div class="card"><h3><a href="sessions.html">All sessions</a></h3><p class="small muted">Seven bodies of work, kept separate and reachable. Nothing deleted.</p></div>
</div></section>
</main>
</body>
</html>
"""
open("executive.html", "w", encoding="utf-8").write(html)
print("executive.html written", len(html), "bytes")
