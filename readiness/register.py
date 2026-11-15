"""The decision-readiness register: one row per requirement in the brief.

Each row states the status of the requirement in THIS repository on 2026-11-15,
the gate that blocks it, the number that would clear it, the repository artifact
that exists today, and the official source (if one exists) for its values.

Numbers written as {name} are filled from readiness/data_sources.compute().
Status vocabulary:
  BUILT      exists and is gated as described
  PARTIAL    exists for part of the scope; the gap is named in the gate column
  NOT BUILT  no artifact in the repository
  BLOCKED    cannot proceed until a named source or decision exists
  DECISION   needs an owner decision (no code can settle it)
  NOT MET    the repository contradicts the requirement today
  UNVERIFIED not checked in this session; no status is claimed
  REJECTED   the brief rejects the approach; recorded as a policy
"""

STATUSES = ["BUILT", "PARTIAL", "NOT BUILT", "BLOCKED", "DECISION",
            "NOT MET", "UNVERIFIED", "REJECTED"]

# Official sources. "reread" = the page text was read on 2026-11-15.
# "headline" = the URL was seen as a link or headline on a page that was read,
# but the target page itself was not opened. "404" = the URL did not resolve.
OFF = {
    "inj":       ("NFL injury report, Week 10 (league/2026/reg10)", "https://www.nfl.com/injuries/league/2026/reg10", "reread"),
    "trade":     ("NFL 2026 transactions: trades, November", "https://www.nfl.com/transactions/", "reread"),
    "reserve":   ("NFL 2026 reserve list, November", "https://www.nfl.com/transactions/league/reserve-list/2026/11", "reread"),
    "sched":     ("NFL 2026 schedule (by week, game-centre links)", "https://www.nfl.com/schedules/", "reread"),
    "rule":      ("NFL Football Operations: 2026 NFL Rulebook", "https://operations.nfl.com/rules-officiating/2026-nfl-rulebook", "reread"),
    "ravens":    ("Baltimore Ravens club depth chart", "https://www.baltimoreravens.com/team/depth-chart", "reread"),
    "texans":    ("Houston Texans club depth chart (image-only, 'Unofficial')", "https://www.houstontexans.com/team/depth-chart", "reread"),
    "nws":       ("National Weather Service (root page)", "https://www.weather.gov/", "reread"),
    "inactives": ("NFL Week 9 inactives article", "https://www.nfl.com/news/nfl-week-9-inactives-players-ruled-out-sunday-2026-season", "headline"),
    "willis":    ("NFL news: Malik Willis on injured reserve", "https://www.nfl.com/news/dolphins-place-qb-malik-willis-groin-on-injured-reserve-kyle-mccord-in-line-for-first-start", "headline"),
    "darnold":   ("NFL news: Darnold ruled out; Lock to start", "https://www.nfl.com/news/sam-darnold-ruled-out-for-seahawks-week-10-game-vs-raiders-drew-lock-expected-to-start-again", "headline"),
    "jackson":   ("NFL news roundup, Nov 5: Ravens place Lamar Jackson on IR", "https://www.nfl.com/news/nfl-news-roundup-latest-league-updates-from-thursday-nov-5", "headline"),
    "gamebook":  ("NFL game book path tried (operations.nfl.com/gameday/nfl-game-book)", "https://operations.nfl.com/gameday/nfl-game-book", "404"),
    "snap":      ("nfl.com/snap-counts path tried", "https://www.nfl.com/snap-counts/", "404"),
    "none":      (None, None, "none"),
    "process":   (None, None, "process"),
}


def rows(n):
    """Return the register rows. n is the dict from data_sources.compute()."""
    R = []

    def add(rid, group, req, status, exists, gate, clears, off, note=""):
        assert status in STATUSES, (rid, status)
        R.append(dict(id=rid, group=group, req=req, status=status, exists=exists,
                      gate=gate, clears=clears, off=off, note=note))

    G1 = "Pricing, origination and the leaderboard"
    add("A01", G1, "Price-snapshot store: opening and closing numbers for every market we originate",
        "PARTIAL",
        [("origin_lab/price-snapshots.html", "origin_lab/price-snapshots.html"),
         ("market_lab/snapshot.html", "market_lab/snapshot.html")],
        f"Store has {n['price_rows']:,} rows. Opening numbers exist for {n['price_open']:,} (2021 subset). "
        f"Closing numbers exist for {n['price_close']:,}. For 2026 there are {n['price_2026']:,} rows, of which "
        f"{n['price_2026_both']} have both opening and closing; {n['price_2026_blank_market']:,} have no closing number.",
        f"{n['price_2026_both']:,} of {n['price_2026']:,} 2026 originated markets with both prices",
        "none",
        "No official source publishes betting lines. Values are a dataset, not an official publication.")

    add("A02", G1, "Verified results feed so backtests and ROI can be computed",
        "PARTIAL",
        [("origin_lab/results-feed.html", "origin_lab/results-feed.html"),
         ("origin_lab/data/official_results_2026.json", "origin_lab/data/official_results_2026.json")],
        f"2026 feed has {n['results_2026_rows']} rows across {n['results_2026_games']} game ids. "
        f"Of these, {n['results_2026_official_direct']} rows are transcribed from NFL.com (official_direct), "
        f"{n['results_2026_dataset']} come from the pinned dataset (official_type_dataset) and "
        f"{n['results_2026_verification_values'].get('not_applicable', 0)} are not_applicable.",
        f"Every 2026 final scored from an official page: {n['results_2026_official_direct']} of {n['results_2026_rows']} rows have a direct official transcription",
        "sched",
        "Results come from NFL.com week pages when transcribed; the rest is a pinned dataset.")

    add("A03", G1, "Originate the side first, then the total, then the moneyline",
        "BUILT",
        [("origin_lab/origination.html", "origin_lab/origination.html"),
         ("price_lab/origination-order.html", "price_lab/origination-order.html")],
        "Written as method. The order is not measured against any outcome.",
        "Method page is published. Nothing to clear.",
        "process",
        "Process rule; no external value.")

    add("A04", G1, "Publish fair line, market line and difference as separate columns",
        "PARTIAL",
        [("market_lab/fair_vs_market.html", "market_lab/fair_vs_market.html"),
         ("origin_lab/fair-lines.html", "origin_lab/fair-lines.html")],
        f"market_lab fair-vs-market file has {n['fvm_rows']:,} rows: SIDE {n['fvm_markets'].get('SIDE', 0):,}, "
        f"TOTAL {n['fvm_markets'].get('TOTAL', 0):,}, MONEYLINE {n['fvm_markets'].get('MONEYLINE', 0):,}. "
        "The market_line column is filled on every row; the source of that market line is the dataset in A01.",
        "Three-column view for every market, with market line from a source that is not a dataset",
        "none",
        "Separate columns are present. Their market-line input is not from an official publisher.")

    add("A05", G1, "Separate signal from staking in the leaderboard so a lucky staking run cannot mask a bad signal",
        "BUILT",
        [("origin_lab/leaderboard.html", "origin_lab/leaderboard.html")],
        "Signal is flat one-unit ROI lower bound. Staking is a separate view and never promotes a strategy.",
        f"Unblocked strategies: {n['strategies_unblocked']} of {n['strategies_origin']}; none is live (see A08).",
        "none",
        "Separation is in code (leaderboard _meta). Inputs are dataset prices, not official prices.")

    add("A06", G1, "Track the depth of the replacement, not just the fact of a replacement",
        "PARTIAL",
        [("origin_lab/replacement-depth.html", "origin_lab/replacement-depth.html"),
         ("depth_lab/depth.html", "depth_lab/depth.html")],
        f"Club depth is captured for {n['depth_clubs']} of 32 clubs; {', '.join(n['depth_coverage_gaps'])} is image-only (B11). "
        f"Replacement rows: {n['replacement_rows']} across {n['replacement_clubs']} clubs.",
        "32 of 32 clubs with a verified depth order, with the Texans source authorised",
        "ravens",
        "Depth depends on club pages; The Ravens page re-read 2026-11-15 agrees with the captured QB order.")

    add("A07", G1, "Compute correlations only from officially sourced numbers and publish n with each value",
        "BLOCKED",
        [("origin_lab/correlations.html", "origin_lab/correlations.html"),
         ("correlations.html (root)", "correlations.html")],
        "Correlations use the pinned open dataset (tier 3), not an official source. No official publisher of betting lines exists.",
        "Official-source correlation rows: 0. Rows with n published: all. Clears only if an admissible source for prices is approved (see Q04).",
        "none",
        "n is published per value; the source tier is the blocker.")

    add("A08", G1, "Define a demotion gate that sends a live strategy back to paper",
        "BUILT",
        [("lifecycle/demotion.html", "lifecycle/demotion.html"),
         ("origin_lab/gates.html", "origin_lab/gates.html")],
        f"Gate is defined with thresholds n_min={n['demotion_params']['n_min']}, q_max={n['demotion_params']['q_max']}, "
        f"CI lower bound > {n['demotion_params']['ci_floor']}, stability >= {n['demotion_params']['stability_min']}. "
        f"Live strategies today: {n['live_lifecycle']}.",
        f"Applies to 0 strategies today. Armed for the first one that passes promotion.",
        "process",
        "Rule text only; no external value.")

    add("A09", G1, "Pre-register every strategy; forbid backtest numbers from ever appearing on the leaderboard",
        "NOT MET",
        [("origin_lab/leaderboard.html", "origin_lab/leaderboard.html"),
         ("origin_lab/leaderboard.py", "origin_lab/leaderboard.py")],
        f"The leaderboard metadata records the window '{n['lb_window']}', and its ROI figures are computed over it. No registration table with commit hashes was found.",
        f"Clears when backtest-derived numbers on the leaderboard are 0 and every strategy carries a registration commit hash. Currently {n['strategies_origin']} of {n['strategies_origin']} show backtest numbers, and 0 of {n['strategies_origin']} carry a hash.",
        "none",
        "Contradicts the brief today (flag F05).")

    add("A10", G1, "Freeze a rule before it sees data: commit the rule text, sample window and gates, and use the commit hash as the registration",
        "NOT BUILT",
        [],
        "No per-strategy registration hash was found in the leaderboard or gate files read this session.",
        "Strategies with a committed rule hash that predates their evaluation window: 0 of 8.",
        "process")

    add("A11", G1, "Split data into train, validation and final holdout seasons",
        "PARTIAL",
        [("origin_lab/leaderboard.html", "origin_lab/leaderboard.html")],
        "A holdout window (2023-2025) is written in the leaderboard metadata. No validation season is recorded.",
        "Holdout seasons defined: 3. Validation seasons defined: 0. Both required.",
        "process")

    add("A13", G1, "Decide the price-data policy before any backtest is published",
        "DECISION",
        [("origin_lab/questions.html (Q03, blocking)", "origin_lab/questions.html")],
        "The owner must state which price settles bets: opening, closing or executable.",
        "1 signed policy decision recorded in the questions register.",
        "process")

    add("A14", G1, "Store every model output as a probability plus its inputs, not just a pick",
        "PARTIAL",
        [("data/derived/model_predictions.csv", "data/derived/model_predictions.csv"),
         ("data/derived/own_lines_upcoming.csv", "data/derived/own_lines_upcoming.csv")],
        "Model files hold point forecasts (spread and total). They do not hold a win probability or the inputs for each row.",
        "Outputs with probability and inputs stored: 0 of the rows in own_lines_upcoming.csv.",
        "none")

    add("A15", G1, "Compute and publish the 'removal of luck' panel on the site dashboard",
        "BUILT",
        [("origin_lab/leaderboard.html", "origin_lab/leaderboard.html")],
        f"Permutation test on bet order: {n['lb_luck_test'][:120]}...",
        "Published with 2,000 permutations.",
        "process")

    add("A16", G1, "Add a two-sided 'what would change our mind' field to every strategy entry",
        "NOT BUILT",
        [],
        "No strategy record in origin_lab/data/leaderboard.json contains this field.",
        f"Strategies with both sides written: 0 of {n['strategies_origin']}.",
        "process")

    add("A17", G1, "Price a line ourselves and publish the residual against the market, on a schedule, from day one",
        "PARTIAL",
        [("data/derived/own_lines_upcoming.csv", "data/derived/own_lines_upcoming.csv"),
         ("lines_lab/data_layer.py", "lines_lab/data_layer.py")],
        f"The only scheduled workflow ({n['cron_files']}) captures official pages, not own lines. No line build is scheduled.",
        "Scheduled runs per week that publish a residual: 0. Clears at 1 per week.",
        "sched")
    add("A18", G1, "Vig-free market consensus versus originated fair-line decomposition",
        "UNVERIFIED",
        [("market_lab/fair_vs_market.html", "market_lab/fair_vs_market.html")],
        "Not checked in this session.",
        "Requires a line-by-line check of the decomposition formula.",
        "none")

    add("A19", G1, "Publish every model total twice (both estimators, gap column) until a walk-forward comparison picks one",
        "NOT BUILT",
        [],
        "No second total estimator found in origin_lab, lines_lab or market_lab build code.",
        "Totals shown with both estimators and a gap column: 0 of the total rows.",
        "none")

    G2 = "Injuries, depth charts and availability"
    add("B01", G2, "Make the injury signal a surprise, never a level",
        "NOT BUILT",
        [],
        "No surprise (change from an earlier read) is computed anywhere in the repository.",
        "Needs at least 2 timestamped reads per player-week. Currently 1 dated read is stored.",
        "inj")

    add("B02", G2, "Store every injury-hub read with its clock time and publish the delta, never the level",
        "PARTIAL",
        [("capture/capture.py", "capture/capture.py"),
         ("capture/data/manifest.jsonl", "capture/data/manifest.jsonl")],
        "Built: each fetch stores UTC start and end time, and a SHA-256 of the raw body (capture.py). Only byte-level deltas are published. Values are not parsed, so no value-level delta exists. Manifest rows: 0 (no run recorded).",
        "2 or more manifest rows for the injury source, with a published byte-level delta: 0 of 2 needed. Value-level delta: not built (see B01).",
        "inj")
    add("B03", G2, "Re-capture and republish the Week 10 injury tables",
        "PARTIAL",
        [("hub/injuries.html", "hub/injuries.html"),
         ("hub/data/injuries.json", "hub/data/injuries.json")],
        f"Published copy says {n['hub_players_listed']} players, {n['hub_clubs_listed']} clubs with rows, and "
        f"{', '.join(n['hub_no_injuries'])} as 'no injuries reported'. Live page has {n['live_rows_manual']} rows (manual count) "
        f"across {n['live_clubs_with_tables']} clubs. Repair not applied here: the hub is another build's output (see Suggestions S01).",
        "Mismatches against the live page: 0. Currently 4 clubs with no rows published but rows live, plus 3 blank cells (B04) and 2 missing rows in the raw capture (F03).",
        "inj",
        "Flags F01, F02, F03.")

    add("B04", G2, "Populate the three missing Lions game-status designations (Joseph, Mays, Reed)",
        "NOT MET",
        [("hub/injuries.html", "hub/injuries.html"),
         ("decisions/injuries.html", "decisions/injuries.html")],
        f"Published game-status cells are blank for all three: hub '{'/'.join(v or 'blank' for v in n['hub_lions_game_status'].values())}', "
        f"decisions '{'/'.join(v or 'blank' for v in n['decisions_lions_game_status'].values())}'. "
        f"The repository's own raw capture says {'/'.join(n['raw_lions_game_status'].values())}.",
        "3 of 3 published cells equal 'Out' (re-read 2026-11-15).",
        "inj",
        "Flag F01.")

    add("B05", G2, "Run the 32-team roster and IR sweep before any team-level model is trusted",
        "BLOCKED",
        [("capture/data/sources.json", "capture/data/sources.json"),
         ("depth_lab/depth.html", "depth_lab/depth.html"),
         ("hub/injuries.html", "hub/injuries.html")],
        f"Raw capture covers 32 club depth pages (capture/data/sources.json), none parsed, and no run is recorded. Injury tables: {n['live_clubs_with_tables']} clubs live; {', '.join(n['live_absent'])} have no table. Depth parsing: {n['depth_clubs']} clubs; HOU is image-only.",
        "32 of 32 clubs with a parsed injury table (or a verified no-table note) and a verified depth chart.",
        "inj")
    add("B06", G2, "Add a fixture-context feature set built only from published schedule facts",
        "PARTIAL",
        [("origin_lab/leaderboard.py", "origin_lab/leaderboard.py")],
        "Concept search found rest and fixture terms in the repository, but no feature set built from published schedule facts was found.",
        "Share of fixtures whose context comes from a published schedule page: 0 verified.",
        "sched")

    add("B07", G2, "Stadium roof, surface and NWS hourly wind and precipitation overlay tied to official roof designations",
        "NOT BUILT",
        [],
        "No stadium forecast grid and no roof designation capture exists. The NWS root page was read, but no stadium data was retrieved.",
        "32 stadiums with a roof designation and a forecast from an official source: 0 captured.",
        "nws")

    add("B08", G2, "Model depth from playing time, not jersey order",
        "BLOCKED",
        [],
        "No verified official source for playing time. nfl.com/snap-counts returned 404.",
        "Snap shares for 32 clubs for at least one season: 0 captured.",
        "snap")

    add("B09", G2, "Use snap counts as the starter proxy when the depth chart is unavailable",
        "BLOCKED",
        [],
        "Same gap as B08. No snap-count source has been verified (route b, see B15).",
        "0 of 32 clubs with a verified snap-count split.",
        "snap")

    add("B10", G2, "Capture official inactive lists and snap counts",
        "NOT BUILT",
        [],
        "The NFL publishes inactives as articles (e.g. Week 9). No inactive list is captured in the repository.",
        "Weeks of inactive lists captured: 0.",
        "inactives")

    add("B11", G2, "Fix the depth-parsing failures: the Texans image page and the jersey-number prefix",
        "PARTIAL",
        [("depth_lab/parse_depth.py", "depth_lab/parse_depth.py")],
        f"The parser strips a jersey-number prefix ({'present' if n['parser_jersey_strip'] else 'absent'}). "
        "The Texans page is image-only and labelled 'Unofficial Depth Chart'. No authorised structured source has been obtained.",
        "Texans: 0 of 1 structured source authorised. Jersey-number fix present; rows not re-verified this session.",
        "texans",
        "The Texans fix needs an authorised structured source, not transcription by eye.")

    add("B12", G2, "Model depth slots as groups, not a single starter",
        "PARTIAL",
        [("depth_lab/data/depth.json", "depth_lab/data/depth.json"),
         ("origin_lab/data/replacement_depth.json", "origin_lab/data/replacement_depth.json")],
        f"The replacement join reads only the player at string 1. The depth file flags {n['co_listed_rows']} co-listed rows.",
        f"Rank-1 slots with more than one player: {n['rank1_multi_slots']} of {n['rank1_slots']} (definition to be agreed, flag F08). Model uses groups: 0.",
        "ravens",
        "Count differs from the brief; see flag F08.")

    add("B13", G2, "Represent shared and empty depth slots faithfully",
        "PARTIAL",
        [("depth_lab/data/depth.json", "depth_lab/data/depth.json")],
        f"Flags exist: Seattle WR1 holds {', '.join(p for _, _, p in n['sea_co_listed_examples'])}; WAS Defense LB2 is an empty slot. The file holds {n['empty_slot_rows']} empty-slot rows in total.",
        "The flags are used in the model: no. Faithful rows: 2 of 2 brief examples present.",
        "sched")

    add("B14", G2, "Official depth-chart register with date and source per row",
        "PARTIAL",
        [("depth_lab/data/depth.json", "depth_lab/data/depth.json")],
        f"{n['depth_rows_with_source_url']:,} of {n['depth_rows']:,} rows carry a source URL. Capture date is set once for the whole file ({n['depth_captured_utc']}); "
        f"{n['depth_rows_with_per_row_date']} rows carry a per-row date.",
        f"Rows with a per-row date: 0 of {n['depth_rows']:,}. Clears at all rows.",
        "ravens")

    add("B15", G2, "Resolve the depth-order source (route a: club pages; route b: snap counts) before building the backup-deficiency feature",
        "BLOCKED",
        [("depth_lab/depth.html", "depth_lab/depth.html")],
        f"Route a: {n['depth_clubs']} of 32 clubs verified; HOU image-only. Route b: no verified snap-count URL (B08).",
        "Route a verified for 32 of 32 clubs. Route b: 0 sources.",
        "texans")

    add("B16", G2, "Backup-deficiency feature: 2nd to 4th string players replacing starters",
        "BLOCKED",
        [("origin_lab/replacement-depth.html", "origin_lab/replacement-depth.html")],
        f"{n['replacement_rows']} replacement rows across {n['replacement_clubs']} clubs. Built from the Out status only. "
        f"{n['replacement_blank_game_status']} blank game-status cells are excluded, which is correct but incomplete.",
        "Depends on B15 and B03. Verified replacement rows: 0 of the rows computed.",
        "inj")

    add("B17", G2, "Interactive offense versus defense matchup deficiency matrix (1st to 4th string)",
        "NOT BUILT",
        [],
        "No matrix artifact exists. It depends on B15.",
        "32 clubs by unit and position populated from verified depth: 0.",
        "ravens")

    add("B18", G2, "Add an announced-starter evidence field (not an inferred replacement)",
        "NOT BUILT",
        [],
        "No field exists. The official news pages name changes (Willis to IR, Darnold ruled out, Lock to start, Jackson on IR); none is stored.",
        "Starter changes with an official dated source stored: 0. Brissett trade 11/06 is in the transactions log.",
        "darnold")

    add("B19", G2, "Per-team view: starters out, replacements named, net injury count",
        "PARTIAL",
        [("hub/injuries.html", "hub/injuries.html"),
         ("desk/availability.html", "desk/availability.html")],
        f"Published view lists {n['hub_clubs_listed']} clubs with rows; {len(n['hub_no_injuries'])} of those show 'no injuries reported' despite live rows (F02).",
        f"Clubs in the published 'no injuries reported' list that have live rows: {len(n['hub_no_injuries'])} of {len(n['hub_no_injuries'])} (cell-level check done for SEA, CIN, BAL; LAC row-count check only).",
        "inj")

    add("B20", G2, "Flag stale depth rows against the official transactions log",
        "PARTIAL",
        [("depth_lab/data/depth.json", "depth_lab/data/depth.json")],
        f"Official log for November 2026 lists {n['trades_nov2026']} trades and reserve moves. No automated check exists. "
        f"The Ravens depth capture already shows Brissett at QB1 with no Jackson or Huntley.",
        f"Trades cross-checked against depth rows: 0 of {n['trades_nov2026']}.",
        "trade",
        "The brief's stale Ravens example is not reproduced in the current capture (flag F13).")

    add("B21", G2, "Treat roster turnover as a first-class data event: version depth, availability and lineup against the last official roster event",
        "NOT BUILT",
        [],
        "No roster-event version field. The official log shows two Colts receiver trades on 11/10 (Keenan Allen to SF; Josh Downs to KC).",
        "Official roster events in November 2026: 12 (all uncaptured as versioned events).",
        "trade")

    add("B22", G2, "Capture the reserve list so 'not listed' never means 'available'",
        "NOT BUILT",
        [],
        f"The official reserve list is public. Malik Willis (MIA, 11/10) is on Reserve/Injured and is not in MIA's injury table. Nothing is captured.",
        f"Reserve entries captured: 0. Visible on page 1 of the official list: {n['reserve_nov2026_seen']}.",
        "reserve")

    add("B23", G2, "Score injury-designation reliability (play rate per designation, with confidence intervals) before using it as a feature",
        "BLOCKED",
        [],
        "Needs several seasons of designations joined to official inactive lists. One week is captured; no inactives are captured (B10).",
        "Seasons joined: 0. Threshold for 'several' has not been set by the owner.",
        "inactives")

    add("B24", G2, "Archive weekly injury reports for past seasons (for Q06)",
        "NOT BUILT",
        [],
        "No past-season injury report is archived in the repository.",
        "Past-season weeks archived: 0. Clears at the owner's chosen span.",
        "inj")

    add("B25", G2, "Calibrate empirically what 'Questionable' means, instead of old percentages",
        "BLOCKED",
        [],
        "Official text gives no percentages. Needs B23 and B24 first.",
        "Questionable outcomes measured: 0.",
        "inj")

    add("B26", G2, "Snapshot the injury report every Wednesday, Thursday and Friday and keep a dated history",
        "PARTIAL",
        [("capture/index.html", "capture/index.html"),
         (".github/workflows/capture.yml", ".github/workflows/capture.yml")],
        f"Schedule exists: capture.yml runs at 16:20 UTC every day and at 01:20 UTC on Thu, Fri and Sat (Wed to Fri evenings in US Pacific). The cadence is this repository's choice, not an NFL rule (capture/flagged.html C-02). Scheduled rows recorded: 0 (manifest empty).",
        "Captures per week: 0 of 3 needed, with a retained hash for each. Clears at 3 recorded captures per week.",
        "inj")
    add("B27", G2, "Treat the injury report as a timestamped series: capture daily from Wednesday to kickoff with the fetch timestamp",
        "PARTIAL",
        [("capture/capture.py", "capture/capture.py")],
        "Daily schedule is set (16:20 UTC). Each fetch records a UTC time. Recorded daily captures: 0. Parsed values: none.",
        "Daily captures recorded from Wednesday to kickoff: 0 of the week's days.",
        "inj")
    add("B28", G2, "Automate immutable multi-day availability snapshots (report and club depth pages), with retained hashes",
        "PARTIAL",
        [("capture/data/sources.json", "capture/data/sources.json"),
         ("capture/data/manifest.jsonl", "capture/data/manifest.jsonl")],
        "Built: 33 sources (injury report and 32 club depth pages) are fetched on the schedule and each body gets a SHA-256 (sources.json, capture.py). Retained hash rows: 0 (manifest empty).",
        "Daily hash rows for all 33 sources: 0 of 33 per day recorded.",
        "inj")
    add("B29", G2, "Build immutable official availability snapshots: raw hashes, timestamps and conflict flags",
        "PARTIAL",
        [("capture/build.py", "capture/build.py"),
         ("capture/check.py", "capture/check.py")],
        "Built: raw hashes, UTC timestamps and byte-level deltas (capture). Not built: conflict flags between a published count and the raw capture, which is the F03 failure. The repository's existing F03 gap is not flagged by any capture check.",
        "Snapshots with hash, timestamp and a conflict flag against the published values: 0.",
        "inj")
    add("B30", G2, "Point-in-time snapshot ledger for injuries, depth charts and inactives (no lookahead)",
        "PARTIAL",
        [("capture/data/manifest.jsonl", "capture/data/manifest.jsonl")],
        "Built: an append-only manifest with a previous-hash link and a delta label per source. It covers page bytes only. Inactive lists are not among the 33 sources. Manifest rows: 0.",
        "Ledger rows per source with a fetch time: 0 of 33. Inactives source added: no.",
        "inj")
    add("B31", G2, "Store captures outside the static site and alert on source or schema change",
        "PARTIAL",
        [(".github/workflows/capture.yml", ".github/workflows/capture.yml")],
        "Raw bodies are kept as 90-day workflow artifacts, not in git. The manifest is committed to git. A failed source makes the scheduled job red (strict run). No long-term external store is configured.",
        "External store configured: no. Alert tested on a real failure: 0.",
        "process")
    add("B32", G2, "Add a drift alarm to every scraper: fail loudly when a field is missing",
        "PARTIAL",
        [("capture/check.py", "capture/check.py"),
         ("depth_lab/check.py", "depth_lab/check.py"),
         ("hub/check_hub.py", "hub/check_hub.py")],
        "capture/check.py fails on a missing marker, a non-200 status or a body under the size floor. These checks compare bytes and markers, not values, so they would not catch F01 to F03. The depth and hub checks pass on internal consistency only.",
        "Scrapers with a value-level comparison to the official page: 0 of 3.",
        "inj",
        "Flag F11.")
    add("B33", G2, "Split the site into a public analysis layer and a private data layer until the terms are read",
        "DECISION",
        [("audit/data-rights-review.md", "audit/data-rights-review.md")],
        "The owner must decide, after reading the terms. Raw official rows are currently published.",
        "1 owner decision. Private store in place: 0.",
        "process")

    add("B34", G2, "Publish a weekly 'what changed' diff instead of a static snapshot",
        "NOT BUILT",
        [],
        "One capture is stored, so no diff can be published.",
        "Weekly snapshots to diff: 0 (needs 2).",
        "process")

    add("B35", G2, "Use official NFL Game Books for actual starters and game-day status; do not infer depth rank or snaps",
        "BLOCKED",
        [],
        "The game-book path tried returned 404. No game-book URL is verified.",
        "Official game books captured: 0 of the games played in 2026.",
        "gamebook")

    add("B36", G2, "Build the availability graph as a first-class dataset: who was expected to start, who actually did",
        "NOT BUILT",
        [],
        "Needs B35 and pre-game starter evidence (B18).",
        "Expected-versus-actual starter pairs: 0.",
        "gamebook")

    add("B37", G2, "Transcribe the venue of every fixture from the official game centre and publish it",
        "NOT BUILT",
        [("origin_lab/data/price_snapshots.csv", "origin_lab/data/price_snapshots.csv")],
        "No venue column appears in the headers of the price, results or fair-vs-market files (headers read). The schedule page links to game-centre pages; venue text was not transcribed.",
        "Fixtures with a venue from the game centre: 0.",
        "sched")

    add("B38", G2, "Publish the league's dated schedule announcement beside the live schedule page",
        "NOT BUILT",
        [],
        "No dated announcement is captured.",
        "Dated announcements linked beside the schedule: 0 (needs 1 per season).",
        "sched")

    add("B39", G2, "Ingest game-level results to make the ratings opponent-aware",
        "NOT BUILT",
        [],
        "Ratings in the repository are team aggregates; no opponent-adjustment is in the build code.",
        "Rating tables adjusted for opponent: 0.",
        "sched")

    add("B40", G2, "Injury and personnel ablations instead of fixed penalties: same model with and without the features, difference with uncertainty, chronological holdouts",
        "NOT BUILT",
        [],
        "No ablation code exists. The fixed-penalty approach is not used either.",
        "Ablation pairs with a difference and interval: 0.",
        "process")

    add("B41", G2, "Pre-register a singles-only shadow baseline; freeze versions and record forecasts before kickoff",
        "NOT BUILT",
        [("data/derived/own_lines_upcoming.csv", "data/derived/own_lines_upcoming.csv")],
        "Forecasts are published by build, not frozen with a version and recorded before kickoff.",
        "Frozen versions with a pre-kickoff record: 0.",
        "process")

    add("B42", G2, "2026 kickoff and declared onside-kick regime: use as a priors filter",
        "NOT BUILT",
        [],
        "No regime flag per game. The rule is confirmed: the 2026 rulebook permits an onside kick at any time (6-1-6).",
        "Games tagged with the regime: 0 of the 2026 games.",
        "rule")

    G3 = "Model, strategy and leaderboard rules"
    add("C01", G3, "Keep parlays and prop combos behind a joint-evidence gate: rank a combo only with a validated joint probability and the operator's void and push rules",
        "NOT MET",
        [("origin_lab/leaderboard.html", "origin_lab/leaderboard.html")],
        f"The leaderboard ranks {', '.join(n['parlay_ids_ranked'])} (both parlays, blocked=False). The gate code has {n['joint_mentions_gate_code']} mentions of 'joint'.",
        f"Combos ranked without a joint probability: {len(n['parlay_ids_ranked'])}. Clears at 0 combos ranked without evidence.",
        "none",
        "Flag F06.")

    add("C02", G3, "Use proper-score leaderboard divisions: singles, game parlays, same-game parlays and prop combos",
        "PARTIAL",
        [("origin_lab/leaderboard.html", "origin_lab/leaderboard.html")],
        f"Kinds present: {n['strategy_kinds']}. The parlay group is one kind label in the data. No division has an eligible rank.",
        "4 divisions published, each with ranks: 0 eligible.",
        "none")

    add("C03", G3, "Rank with proper scores and uncertainty, not win rate: Brier skill against a benchmark, game-cluster lower bound, multiplicity adjustment",
        "NOT BUILT",
        [],
        f"The ranking metric is ROI lower bound. Brier mentions in gate code: {n['brier_mentions_gate_code']}.",
        "Strategies with a Brier skill and cluster-adjusted lower bound: 0 of 8.",
        "none")

    add("C04", G3, "Add a control baseline (random picks; favourites only) to every leaderboard run",
        "NOT BUILT",
        [],
        f"No control strategy is run. 'random' appears only in the luck permutation test ({n['control_mentions_gate_code']} matches, none a control).",
        "Strategies with a random and a favourites control: 0 of 8.",
        "none")

    add("C05", G3, "Two-stage skill leaderboard: Brier-skill qualification, then prospective CLV and ROI escrow over multi-week samples",
        "NOT BUILT",
        [],
        "No escrow and no prospective sample. Closing-line value is not recorded for any settled bet in the current store.",
        "Prospective settled bets with CLV: 0 (needs the owner's minimum).",
        "none")

    add("C06", G3, "Reject ranking strategies by season-long ROI",
        "REJECTED",
        [("origin_lab/leaderboard.py", "origin_lab/leaderboard.py")],
        "The brief rejects season-long ROI. The leaderboard still ranks on ROI lower bound, so the rule is not yet honoured in full (see C03).",
        "Season-long ROI ranks: 0.",
        "process")

    add("C07", G3, "Vig-free market consensus versus originated fair-line decomposition (separate true divergence from margin)",
        "UNVERIFIED",
        [("market_lab/fair_vs_market.html", "market_lab/fair_vs_market.html")],
        "Not checked line by line in this session.",
        "Requires a formula check.",
        "none")

    G4 = "Decision support, coordination and the site"
    add("D01", G4, "Put a decision-readiness table on the landing page: one row per requirement, with the gate that blocks it and the number that would clear it",
        "BUILT",
        [("readiness/index.html", "readiness/index.html")],
        "This table. Every row is generated from the register and checked by readiness/check.py.",
        "1 table; 1 row per requirement (see the count on the landing page).",
        "process")

    add("D02", G4, "Make suggestions for improving the site, with a section to review suggestions and choose a path before implementation",
        "BUILT",
        [("readiness/suggestions.html", "readiness/suggestions.html"),
         ("hub/suggestions.html", "hub/suggestions.html")],
        "Suggestions are listed with paths. Nothing is implemented until the owner chooses.",
        "Owner path choices recorded: 0.",
        "process")

    add("D03", G4, "A clear list of questions, information and answers needed before any decision",
        "BUILT",
        [("readiness/questions.html", "readiness/questions.html"),
         ("hub/questions.html", "hub/questions.html")],
        "Questions list what is held, what is missing, and how to discover it. None is answered on the owner's behalf.",
        "Questions answered: 0 of the open ones.",
        "process")

    add("D04", G4, "Executive summary outlining the important details",
        "BUILT",
        [("EXECUTIVE_SUMMARY_2026-11-15.md", "EXECUTIVE_SUMMARY_2026-11-15.md")],
        "Written for this session. Numbers are taken from this page.",
        "Published.",
        "process")

    add("D05", G4, "Review the repository line by line against official sources, provide links for review, and flag irregularities",
        "PARTIAL",
        [("readiness/verification.html", "readiness/verification.html"),
         ("readiness/flagged.html", "readiness/flagged.html")],
        f"Re-read this session: {n['live_rows_manual']} Week 10 injury rows (manual count, 4 clubs compared at cell level), "
        f"{n['trades_nov2026']} trades, {n['reserve_nov2026_seen']} reserve rows (page 1), 2 club depth pages, and the schedule and rulebook pages.",
        "Full line-by-line verification of the repository's ~1,840 depth rows and every published table: not done.",
        "inj")

    add("D06", G4, "Every table row carries a source link to an official site; a value that cannot be confirmed is left blank and flagged",
        "PARTIAL",
        [("verify/source_audit.py", "verify/source_audit.py"),
         ("hub/check_hub.py", "hub/check_hub.py")],
        "Existing gates check that a link is present, not that the value agrees with the linked page. They passed while B03, B04 and B19 were wrong.",
        "Rows whose value agrees with the linked page: not measured for the whole repository.",
        "inj",
        "Flag F11.")

    add("D07", G4, "Coordinate parallel sessions: claim tasks on the shared board, keep file scopes apart, log overlaps",
        "BUILT",
        [("COORDINATION.md", "COORDINATION.md")],
        f"{n['claim_headings']} claim sections are logged in COORDINATION.md; overlaps are recorded there.",
        "Overlaps resolved without deletion: all recorded.",
        "process")

    add("D08", G4, "Flagged-for-review page with source links, labelled, for later owner review",
        "BUILT",
        [("readiness/flagged.html", "readiness/flagged.html"),
         ("hub/flagged.html", "hub/flagged.html")],
        "Flags with evidence and official links. Unverified items are published here, not hidden.",
        "Open flags on this page: see the count on the page.",
        "process")

    add("D09", G4, "Create a GitHub Pages live site with a landing page and category subpages",
        "BUILT",
        [("index.html (root)", "index.html")],
        "The root site is generated and published from the repository. Live status is recorded in COORDINATION.md; this sandbox cannot curl the Pages host.",
        "Live status confirmed by a Pages build record for the merged commit.",
        "process")

    return R
