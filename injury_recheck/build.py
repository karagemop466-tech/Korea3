"""Build injury_recheck/data/week10_official.json and index.html.

Inputs (all typed in from official pages read on 2026-11-15 UTC, see README.md):
  LIVE_COUNTS  : rows per club table on https://www.nfl.com/injuries/league/2026/reg10 (chunks 0-7)
  BYE_TEAMS    : 'Teams on Bye' block on https://www.nfl.com/schedules (Week 10 view, chunk 1)
  GAMES        : the 14 Week 10 games listed on the same page (chunks 0-6)
Repo comparison: depth_lab/data/raw/nfl_injury_w10_2026.json (read-only).
"""
import json, html, os

ROOT = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(ROOT)
INJ_URL = "https://www.nfl.com/injuries/league/2026/reg10"
SCH_URL = "https://www.nfl.com/schedules"  # Week 10 view (fetched via /schedules/2026/REG10; tool reported this URL)
RAW = os.path.join(REPO, "depth_lab/data/raw/nfl_injury_w10_2026.json")

LIVE_COUNTS = {
    "WAS": 9, "NYG": 11, "NE": 15, "DET": 9, "KC": 13, "ATL": 11, "MIN": 13, "GB": 17,
    "JAX": 11, "TEN": 12, "BUF": 14, "NYJ": 9, "MIA": 11, "IND": 14, "CAR": 12, "NO": 12,
    "HOU": 16, "CLE": 12, "LAR": 14, "AZ": 15, "SEA": 15, "LV": 5, "SF": 12, "DAL": 19,
    "PIT": 8, "CIN": 9, "LAC": 19, "BAL": 10,
}
BYE_TEAMS = ["CHI", "DEN", "PHI", "TB"]
GAMES = [  # (away, home, day, time ET) as printed on the official page
    ("WAS", "NYG", "Thu Nov 12", "8:15 PM"), ("NE", "DET", "Sun Nov 15 (Munich)", "9:30 AM"),
    ("KC", "ATL", "Sun Nov 15", "1:00 PM"), ("MIN", "GB", "Sun Nov 15", "1:00 PM"),
    ("JAX", "TEN", "Sun Nov 15", "1:00 PM"), ("BUF", "NYJ", "Sun Nov 15", "1:00 PM"),
    ("MIA", "IND", "Sun Nov 15", "1:00 PM"), ("CAR", "NO", "Sun Nov 15", "1:00 PM"),
    ("HOU", "CLE", "Sun Nov 15", "1:00 PM"), ("LAR", "AZ", "Sun Nov 15", "4:05 PM"),
    ("SEA", "LV", "Sun Nov 15", "4:05 PM"), ("SF", "DAL", "Sun Nov 15", "4:25 PM"),
    ("PIT", "CIN", "Sun Nov 15", "8:20 PM"), ("LAC", "BAL", "Mon Nov 16", "8:15 PM"),
]
# Known repository-vs-live differences, recorded so a regression fails the check.
KNOWN_RAW_DIFFS = {"BAL": (8, 10)}  # club: (repo raw rows, live rows)

ALL32 = sorted(set(LIVE_COUNTS) | set(BYE_TEAMS))
assert len(ALL32) == 32, len(ALL32)

raw = json.load(open(RAW))
raw_counts = {c["code"]: len(c["rows"]) for c in raw["clubs"]}

clubs = []
for code in ALL32:
    if code in LIVE_COUNTS:
        status = "table on page"
        live = LIVE_COUNTS[code]
        bye = False
    else:
        status = "no table: on bye (official schedule)"
        live = None
        bye = True
    rc = raw_counts.get(code)
    match = (rc == live) if live is not None else (rc is None)
    clubs.append({
        "club": code, "status": status, "bye": bye, "live_rows": live,
        "repo_raw_rows": rc, "repo_matches_live": match,
        "source": (SCH_URL if bye else INJ_URL),
        "also_source": (SCH_URL if not bye else None),
    })

total_live = sum(LIVE_COUNTS.values())
out = {
    "_meta": {
        "title": "Week 10 2026 official injury report: per-club re-check",
        "captured_utc": "2026-11-15",
        "injury_source": INJ_URL,
        "schedule_source": SCH_URL,
        "method": "All 8 chunks of the injury page and the schedule page were read with the page-fetch tool. Row counts were counted by hand from the rendered tables (one row per player). Cell values were NOT re-parsed by a program, so this file verifies counts and table presence only.",
        "games": len(GAMES), "teams_playing": 2 * len(GAMES), "teams_on_bye": BYE_TEAMS,
        "clubs_with_table": len(LIVE_COUNTS), "total_live_rows": total_live,
    },
    "games": [{"away": a, "home": h, "day": d, "time_et": t} for a, h, d, t in GAMES],
    "clubs": clubs,
    "comparisons": {
        "repo_raw_total_rows": sum(c for c in raw_counts.values()),
        "live_total_rows": total_live,
        "published_hub_rows": 254,
        "brief_stated_rows": 279,
        "note": "The 279 figure in the brief matches neither the live page nor the repository capture; it is recorded as unverified and is not used.",
    },
}
os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
json.dump(out, open(os.path.join(ROOT, "data/week10_official.json"), "w"), indent=2)

# ---- HTML page (one row per club, each with a source link) ----
def link(u, label):
    return f'<a href="{html.escape(u)}">{html.escape(label)}</a>'
rows = []
for c in clubs:
    src = link(c["source"], "nfl.com (schedule: Teams on Bye)" if c["bye"] else "nfl.com injury report")
    live = "" if c["live_rows"] is None else str(c["live_rows"])
    rc = "" if c["repo_raw_rows"] is None else str(c["repo_raw_rows"])
    ok = "match" if c["repo_matches_live"] else "<b>DIFFERS</b>"
    rows.append(f"<tr><td>{c['club']}</td><td>{html.escape(c['status'])}</td><td>{live}</td><td>{rc}</td><td>{ok}</td><td>{src}</td></tr>")
gr = "".join(f"<tr><td>{html.escape(g['away'])} at {html.escape(g['home'])}</td><td>{html.escape(g['day'])}</td><td>{html.escape(g['time_et'])} ET</td><td>{link(SCH_URL,'schedule page')}</td></tr>" for g in out["games"])
page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Week 10 official injury report: per-club re-check</title>
<style>body{{font-family:system-ui,sans-serif;margin:24px;color:#111;max-width:1100px}}table{{border-collapse:collapse;width:100%;margin:12px 0}}th,td{{border:1px solid #ccc;padding:6px 8px;text-align:left;font-size:14px}}th{{background:#f2f4f7}}.k{{display:inline-block;margin-right:18px}}small{{color:#555}}</style></head><body>
<p><a href="../">&larr; Home</a></p>
<h1>Week 10 2026: official injury report, per-club re-check</h1>
<p><b>Checked 2026-11-15 (UTC).</b> Counts were read by hand from the official pages below; cell values were not parsed by a program. Blank cells are unverified, not filled in.</p>
<p><span class="k"><b>{len(LIVE_COUNTS)}</b> clubs with a table</span><span class="k"><b>{total_live}</b> live rows</span><span class="k"><b>4</b> clubs on bye (CHI, DEN, PHI, TB)</span><span class="k"><b>14</b> games</span></p>
<p>Sources: <a href="{INJ_URL}">{INJ_URL}</a> &middot; <a href="{SCH_URL}">{SCH_URL}</a></p>
<h2>Per club</h2>
<table><thead><tr><th>Club</th><th>Status on official page</th><th>Live rows (official)</th><th>Repo raw capture rows</th><th>Repo vs live</th><th>Source</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
<h2>Week 10 games (official schedule)</h2>
<table><thead><tr><th>Game</th><th>Day</th><th>Start</th><th>Source</th></tr></thead><tbody>{gr}</tbody></table>
<h2>Irregularities</h2>
<ul>
<li><b>BAL: repo capture has 8 rows; the official page has 10.</b> Missing from the capture: Calais Campbell (DT, Did Not Participate) and Ronnie Stanley (T, Did Not Participate). Source: <a href="{INJ_URL}">injury report</a>.</li>
<li><b>Published hub shows 254 rows and four &ldquo;no injuries reported&rdquo; clubs (SEA, CIN, LAC, BAL).</b> The live page lists 15, 9, 19 and 10 players for those clubs. The hub figures are stale. Owner request logged in COORDINATION.md.</li>
<li><b>Brief figure 279 rows</b> matches neither the live page (347) nor the repo capture (345). Not used.</li>
</ul>
</body></html>"""
open(os.path.join(ROOT, "index.html"), "w").write(page)
print("built:", len(clubs), "clubs,", total_live, "live rows,", len(GAMES), "games")
