#!/usr/bin/env python3
"""Page builders for the decision register, the suggestions board, the injury /
availability view and the recomputation log.

These are kept out of build_hub.py so the existing 20 pages stay untouched and the
new work is reviewable in isolation. build_hub.py imports `build_new_pages` and merges
the result.
"""
from __future__ import annotations

import json
from pathlib import Path

from content_decisions import DECISIONS, SUGGESTIONS

ROOT = Path(__file__).resolve().parents[1]
HUB = ROOT / "hub"


def _load(name):
    return json.loads((HUB / "data" / name).read_text(encoding="utf-8"))


STATUS_PILL = {
    "answered": "ok", "partly answered": "warn", "cannot be answered yet": "bad",
    "blocked": "bad", "unverified": "bad",
}
PRIORITY_PILL = {"P1": "bad", "P2": "warn", "P3": "info"}


def build_new_pages(ctx):
    """ctx: dict with E, A, T, sec, cards, pill, blank, repo, tree, SRC, source_url."""
    E, A, T, sec, cards, pill, repo, tree = (
        ctx["E"], ctx["A"], ctx["T"], ctx["sec"], ctx["cards"], ctx["pill"], ctx["repo"], ctx["tree"])
    SRC = ctx["SRC"]
    src = lambda sid: [sid]  # noqa: E731

    pages = {}
    inj = _load("injuries.json")
    rec = _load("recompute.json")
    # NOTE: the decision register and the suggestions board are owned by the parallel
    # sessions' pages (hub/questions.html and hub/suggestions.html). This module only
    # contributes the two pages that did not exist: the 32-club official availability
    # view and the independent recomputation log.

    # ==================================================================== DECISIONS
    rows = []
    for d in DECISIONS:
        answer = d["answer"] if d["answer"] else None
        rows.append((
            [
                f'<strong>{E(d["id"])}</strong>',
                E(d["category"]),
                f'<strong>{E(d["question"])}</strong><div class="small muted" style="margin-top:4px">'
                f'Why it matters: {E(d["matters"])}</div>',
                E(d["have"]),
                E(d["lack"]),
                answer,
                pill(d["status"], STATUS_PILL.get(d["status"], "info")),
                E(d["changes"]),
                E(d["discovery"]),
            ],
            list(d["sources"]), d["id"],
        ))
    open_count = sum(1 for d in DECISIONS if d["status"] != "answered")
    decided_count = sum(1 for d in DECISIONS if d["status"] == "answered")
    _unused_decisions = dict(
        title="Decision register — what must be settled first",
        lead="Twenty questions that have to be answered before any decision about this project is "
             "reasonable. Each row states the question, why it matters, what the repository already "
             "has, what it is missing, the provisional answer if there is one, and the cheapest way to "
             "discover what is missing. A blank answer is a real answer here: it means nobody has "
             "established it yet, and no value has been invented to close the gap.",
        kpis=[
            ("Questions in the register", len(DECISIONS), "Each with a source on the row"),
            ("Answered from an official source", decided_count, "Settled, not provisional"),
            ("Still open", open_count, "Partly answered, blocked, or unanswerable today"),
            ("Suggestions raised", len(SUGGESTIONS), "On the Suggestions page, each with a decision"),
        ],
        sections=[
            sec("How to read this page",
                "The register is deliberately uncomfortable. A 'cannot be answered yet' row is not a "
                "failure of the work; it is the list of things that must be discovered before money, "
                "effort or a public claim is committed. The <em>What would change the answer</em> column "
                "names the cheapest evidence that would move each row, so a path can be chosen before "
                "anything is built.",
                note="Statuses: answered = settled from an official source or a stated internal rule; "
                     "partly answered = a provisional position that needs an owner decision; "
                     "cannot be answered yet = the evidence does not exist in this repository; "
                     "blocked = a dependency outside this repository must move first."),
            sec("The register", "Filter by category, status or keyword.",
                T(["#", "Area", "Question and why it matters", "What we have",
                   "What we are missing", "Answer / position", "Status",
                   "What would change it", "How to discover it"],
                  rows, filter_id="decisions")),
            sec("The short version",
                "If only three things are read, read these.",
                T(["Point", "Position"], [
                    (["Rights", "Bulk redistribution of NFL injury data is not permitted by the official "
                                "terms. This site therefore cites and transcribes the minimum needed and "
                                "never presents itself as a substitute for the official report."],
                     src("NFL-TERMS")),
                    (["Depth charts", "No official depth chart could be reached on 2026-11-12, so the "
                                      "2nd/3rd/4th-string half of the brief cannot be verified and is left "
                                      "blank. The availability half is built from official injury data."],
                     [SRC["NFL-DEPTH-404"], SRC["NFL-INJURY-W10"]]),
                    (["Credibility", "Every published summary statistic reproduces independently, and no "
                                     "strategy has cleared the validation gates. The honest headline is "
                                     "'no demonstrated edge', not a ranked list of winners."],
                     [SRC["REPO"], SRC["NIST-MULTI"]]),
                ])),
        ],
    )

    # ==================================================================== SUGGESTIONS
    srows = []
    for s in SUGGESTIONS:
        srows.append((
            [
                f'<strong>{E(s["id"])}</strong>',
                pill(s["priority"], PRIORITY_PILL.get(s["priority"], "info")),
                E(s["category"]),
                f'<strong>{E(s["title"])}</strong>',
                E(s["problem"]),
                E(s["proposal"]),
                E(s["effort"]),
                E(s["effect"]),
                E(s["risk"]),
                E(s["evidence"]),
                f'<span class="blank">—</span> <span class="small muted">to be chosen</span>',
                E(s["decision"]),
            ],
            list(s["sources"]), s["id"],
        ))
    _unused_suggestions = dict(
        title="Suggestions — choose a path before anything is implemented",
        lead="Twelve concrete improvements, each written so that it can be accepted or rejected on its "
             "own. Nothing on this page has been implemented as a change to another session's work; each "
             "suggestion names the problem, the proposed change, the effort, the effect, the risk, the "
             "evidence, and the decision the reviewer has to make. The decision column is intentionally "
             "empty so the choice is made here, before any code is written.",
        kpis=[
            ("Suggestions", len(SUGGESTIONS), "Each with an explicit decision to take"),
            ("Integrity first (P1)", sum(1 for s in SUGGESTIONS if s["priority"] == "P1"),
             "Fix before adding features"),
            ("High value (P2)", sum(1 for s in SUGGESTIONS if s["priority"] == "P2"), "Next"),
            ("Optional (P3)", sum(1 for s in SUGGESTIONS if s["priority"] == "P3"), "When capacity allows"),
        ],
        sections=[
            sec("How to use this page",
                "Read the problem, then the evidence, then the decision. The decision column is the only "
                "thing that needs an answer: accept, reject, or defer. Implementation should follow that "
                "choice and nothing else. P1 items are integrity fixes that make later work trustworthy; "
                "they are cheap and should not wait for the rest.",
                note="Every suggestion is sourced. Suggestions that depend on data this repository does "
                     "not have say so explicitly and propose acquiring it, rather than assuming it."),
            sec("The board", "Filter by priority, category or keyword.",
                T(["#", "Priority", "Area", "Suggestion", "Problem it fixes", "Proposed change",
                   "Effort", "Effect if adopted", "Main risk", "Evidence",
                   "Reviewer decision", "Decision needed"],
                  srows, filter_id="suggestions")),
            sec("The four that matter most",
                "If the list has to be cut, these are the ones that change what is possible.",
                cards([
                    ("Separate the strategy ID spaces (S01)",
                     "Two builds share S01..S18 with different meanings. Any join mixes them, and this "
                     "session measured a 13-point ROI error from exactly that join. Cheap to fix, and it "
                     "prevents silent wrong numbers for good.", "suggestions.html#S01"),
                    ("Pre-register the injury hypothesis (S04)",
                     "Testing injury news without a pre-registered rule and pass bar would repeat the "
                     "eighteen failures already in this repository. Write the rule first, then buy data.",
                     "suggestions.html#S04"),
                    ("Ship the official availability layer (S03)",
                     "Delivers the half of the brief that official data actually supports, instead of "
                     "fabricating a depth index that cannot be verified.", "suggestions.html#S03"),
                    ("Decide the reward scheme, or drop it (S06)",
                     "A reward promise creates obligations that are currently unbacked. Either fund it "
                     "with written terms or remove the word.", "suggestions.html#S06"),
                ])),
            sec("What this page deliberately does not do",
                "To keep the choice real, this session has not implemented any suggestion that would "
                "change another session's files. The only changes made are additive: new pages, new data "
                "files, new sources and new review flags, all listed in the verification log.",
                T(["Not done", "Why"], [
                    (["Renaming strategy IDs", "It would change data/derived/*, which belongs to the "
                                               "pipelines that generate it. Proposed as S01 instead."],
                     src("REPO")),
                    (["Adding a licensed data feed", "No feed was available and none was purchased. "
                                                     "Proposed as S04 and S09 instead."],
                     src("NFLVERSE")),
                    (["Promising a reward", "No funded pool exists. Proposed as S06 instead."],
                     src("NFL-RG")),
                ])),
        ],
    )

    # ==================================================================== INJURIES
    counts = inj["counts"]
    w = inj["weights"]
    club_rows = []
    for c in inj["clubs"]:
        if c["listed"] == 0:
            club_rows.append((
                [f'<strong>{E(c["club"])}</strong>', E(c["name"]), "0", None, None, None,
                 None, None, None, None, E(c["page_state"])],
                src("NFL-INJURY-W10"), f'club-{c["club"]}'))
        else:
            club_rows.append((
                [f'<strong>{E(c["club"])}</strong>', E(c["name"]), str(c["listed"]),
                 str(c["out"]), str(c["doubtful"]), str(c["questionable"]),
                 f'{c["off_stress"]}', f'{c["def_stress"]}', f'{c["st_stress"]}',
                 f'<strong>{c["stress"]}</strong>', E(c["page_state"])],
                src("NFL-INJURY-W10"), f'club-{c["club"]}'))
    pos_rows = [
        ([E(p["group"]), E(p["unit"]), E(p["positions"]), str(p["listed"]), str(p["out"]),
          str(p["doubtful"]), str(p["questionable"]), str(p["dnp"]), str(p["stress"])],
         src("NFL-INJURY-W10"))
        for p in inj["positions"]
    ]
    player_rows = []
    for p in inj["players"]:
        anchor = "p-" + p["club"] + "-" + "".join(
            ch for ch in p["player"].lower().replace(" ", "-").replace(".", "")
            if ch.isalnum() or ch == "-")
        player_rows.append((
            [f'<strong>{E(p["player"])}</strong>', E(p["club"]), E(p["position"]), E(p["unit"]),
             p["injury"] if p["injury"] else None,
             E(p["practice"]), p["game"] if p["game"] else None, str(p["stress"])],
            src("NFL-INJURY-W10"), anchor))
    reserve_rows = [
        ([E(r["date"]), E(r["club"]), E(r["player"]), E(r["transaction"])],
         [SRC["NFL-RESERVE"]], None) for r in inj["reserve_moves"]
    ]
    pages["injuries"] = dict(
        title="Injuries, availability and depth — official data only",
        lead=f"An official snapshot of who is available: {inj['players_listed']} players from the NFL's "
             f"own Week 10 2026 injury report, read on {inj['snapshot_utc']}, grouped by club and by unit. "
             f"Depth-chart strings (2nd, 3rd, 4th) are <strong>blank throughout</strong>, because no "
             f"official depth chart could be reached and a string-level number would have to be invented.",
        kpis=[
            ("Players on the official report", counts["out"] + counts["doubtful"] + counts["questionable"]
             + counts["not_designated"], "Week 10, 2026"),
            ("Ruled Out", counts["out"], "Official game status 'Out'"),
            ("Did not practise", counts["dnp"], "Official practice status"),
            ("Clubs with a depth chart verified", 0, "No official source reachable"),
        ],
        sections=[
            sec("What is official here, and what is not",
                "Three separate things are being published, and they must not be confused. "
                "<strong>Game status</strong> and <strong>practice status</strong> are official: they are "
                "the NFL's own columns with the NFL's own vocabulary. "
                "<strong>The availability-stress index</strong> is this repository's arithmetic on top of "
                "those official values, with the weights printed in full below so anyone can redo it. "
                "<strong>Depth order</strong> — who is second or third string — is <em>not</em> official "
                "here and is left blank.",
                T(["Layer", "What it is", "Source", "Status"], [
                    (["Game status", "Out = will not play; Doubtful = unlikely; Questionable = uncertain; "
                                     "blank = the club has not designated the player."],
                     [SRC["NFL-INJURY-POLICY"], SRC["NFL-INJURY-W10"]]),
                    (["Practice status", "Did Not Participate; Limited Participation (less than 100% of "
                                        "normal repetitions); Full Participation (100%)."],
                     [SRC["NFL-INJURY-POLICY"], SRC["NFL-INJURY-W10"]]),
                    (["Availability-stress index", "0-5 per player. A publishing convention of this "
                                                  "repository, not an NFL metric. Weights below."],
                     [SRC["REPO"], SRC["NFL-INJURY-W10"]]),
                    (["Depth / string", "2nd, 3rd and 4th string. Not available: the official depth-chart "
                                       "URL returned HTTP 404 on 2026-11-12."],
                     [SRC["NFL-DEPTH-404"], SRC["NFL-ROSTER"]]),
                ])),
            sec("The index, with its arithmetic shown",
                f"Each listed player scores <strong>game-status weight + practice weight</strong>. "
                f"Game status: Out {w['game']['Out']}, Doubtful {w['game']['Doubtful']}, "
                f"Questionable {w['game']['Questionable']}, not designated {w['game']['']}. "
                f"Practice: {w['practice']['Did Not Participate In Practice']} for did not participate, "
                f"{w['practice']['Limited Participation in Practice']} for limited, "
                f"{w['practice']['Full Participation in Practice']} for full. "
                "A player ruled Out after missing practice therefore scores 5; a player practising fully "
                "with no designation scores 0. The index measures <em>reported unavailability</em>, not "
                "player quality and not depth.",
                T(["Weight", "Official value", "Scores"], [
                    (["Game status", "Out", "3"], src("NFL-INJURY-POLICY")),
                    (["Game status", "Doubtful", "2"], src("NFL-INJURY-POLICY")),
                    (["Game status", "Questionable", "1"], src("NFL-INJURY-POLICY")),
                    (["Game status", "not designated on the report", "0"], src("NFL-INJURY-W10")),
                    (["Practice", "Did Not Participate In Practice", "2"], src("NFL-INJURY-POLICY")),
                    (["Practice", "Limited Participation in Practice", "1"], src("NFL-INJURY-POLICY")),
                    (["Practice", "Full Participation in Practice", "0"], src("NFL-INJURY-POLICY")),
                ])),
            sec("By club", "Sorted alphabetically. Offence, defence and special-teams stress are split so "
                          "that a defensive deficiency is visible separately from an offensive one.",
                T(["Club", "Name", "Listed", "Out", "Doubtful", "Questionable",
                   "Offence stress", "Defence stress", "Special teams stress", "Total stress",
                   "Official page state"],
                  club_rows, filter_id="clubs",
                  numeric=(2, 3, 4, 5, 6, 7, 8, 9))),
            sec("By position group", "The unit split uses a football-convention mapping shown in the "
                                    "source column; it is not an NFL publication.",
                T(["Group", "Unit", "Positions present", "Listed", "Out", "Doubtful", "Questionable",
                   "Did not practise", "Stress"], pos_rows, numeric=(3, 4, 5, 6, 7, 8),
                  note="Positions are the official labels transcribed from the report. Groups are this "
                       "repository's grouping.")),
            sec("Why four clubs have no rows",
                "Chicago, Denver, Philadelphia and Tampa Bay do not appear on the Week 10 injury report. "
                "The official week 10 schedule page lists exactly those four clubs under "
                "<em>Teams on Bye</em>, so the absence is explained by an official source and is recorded "
                "as 'absent from page' rather than as 'no injuries'. Two further clubs, Seattle and "
                "Cincinnati, appear on the report with the literal text 'No Injuries Reported'.",
                T(["Club", "State on the official page", "Official explanation"], [
                    (["CHI, DEN, PHI, TB", "absent from the injury page", "listed under 'Teams on Bye' "
                                                                         "on the official week 10 schedule"],
                     [SRC["NFL-SCHEDULE-W10"], SRC["NFL-INJURY-W10"]]),
                    (["SEA, CIN, LAC, BAL", "'No Injuries Reported'", "the report states it directly"],
                     src("NFL-INJURY-W10")),
                ])),
            sec("Roster moves that change availability",
                "Injured-reserve placements and trades remove or add players independently of the injury "
                "report. Both are official and dated.",
                T(["Date", "Club", "Player", "Transaction"], reserve_rows,
                  caption="Official reserve-list transactions, November 2026")),
            sec("The full official report, row by row",
                "Every player on the official page, with the official values unchanged. The Injury column "
                "is blank where the official page is blank; it is free text and supports no severity "
                "score. Stress is this repository's declared index.",
                T(["Player", "Club", "Position", "Unit", "Injury (official, often blank)",
                   "Practice status (official)", "Game status (official)", "Stress"],
                  player_rows, filter_id="players", numeric=(7,))),
            sec("What cannot be claimed from this page",
                "This is the part that matters for the brief. The brief asks for 2nd/3rd/4th-string "
                "deficiency analysis. That requires a depth chart, and no official depth chart was "
                "reachable, so the answer is 'not verifiable yet', not a number.",
                T(["Question from the brief", "Can it be answered from official data?", "Position"], [
                    (["Which players are ruled out or doubtful for the coming game?", "Yes: official game status."],
                     src("NFL-INJURY-POLICY")),
                    (["Which units are thinnest by reported unavailability?", "Yes, as the index above, "
                                                                             "with declared weights."],
                     src("NFL-INJURY-W10")),
                    (["Is a starter being replaced by a backup?", "No: there is no official depth order."],
                     src("NFL-DEPTH-404")),
                    (["Which specific backup is 2nd, 3rd or 4th string?", "No: not published officially."],
                     src("NFL-DEPTH-404")),
                    (["Does the announcement of an injury move the closing line?", "Not yet: no historical "
                                                                                  "injury archive here."],
                     src("REPO")),
                ])),
        ],
    )

    # ==================================================================== RECOMPUTE
    rrows = []
    for c in rec["checks"]:
        rrows.append((
            [f'<strong>{E(c["id"])}</strong>', E(c["name"]), E(str(c["published"])),
             E(str(c["recomputed"])), E(c["kind"]),
             pill("match" if c["result"] == "match" else "MISMATCH",
                  "ok" if c["result"] == "match" else "bad"),
             E(c["method"]), E(c["note"])],
            [SRC["REPO"]], c["id"]))
    pages["recompute"] = dict(
        title="Recomputation log — every published number, re-derived",
        lead=f"{rec['summary']['matched']} of {rec['summary']['total']} published numbers were re-derived "
             f"in this session with hand-written arithmetic instead of the pipeline that produced them. "
             f"Every one reproduces. Two data-layout defects were found in the process and are published "
             f"on the review page.",
        kpis=[
            ("Checks run", rec["summary"]["total"], "Arithmetic rewritten, not re-called"),
            ("Matched", rec["summary"]["matched"], "No disagreements"),
            ("Official-kind checks", rec["summary"]["official"], "Fixed by price or rule text"),
            ("Recomputed-kind checks", rec["summary"]["recomputed"], "Reproducible, not official"),
        ],
        sections=[
            sec("Why this page exists",
                "A number is not evidence because a pipeline printed it. Each published figure is "
                "re-derived here from the committed CSV with independent arithmetic, and the method is "
                "printed next to it so it can be checked again. The honest limit is stated on every row: "
                "a value can be <strong>reproducible</strong> without being <strong>official</strong>, "
                "because the market data behind it is third-party.",
                note="Run it yourself: python3 hub/verify_numbers.py. The build fails if any check "
                     "stops matching."),
            sec("The checks", "Official = fixed by a price or a rule; Recomputed = re-derived from the "
                              "repository's data; Limitation = a negative result confirming a gap.",
                T(["#", "Number checked", "Published", "Recomputed", "Kind", "Result", "Method", "Note"],
                  rrows, filter_id="recompute")),
            sec("What this does and does not prove",
                "It is easy to over-read a page like this.",
                T(["It proves", "It does not prove"], [
                    (["The summary statistics in this repository can be regenerated from the committed "
                      "files by someone who does not trust the original code.",
                      "The model that produced the input table is correct, or that the third-party "
                      "market data is accurate. Both remain open."],
                     src("REPO")),
                    (["The price arithmetic is internally consistent and matches the operators' published "
                      "settlement rules for the two market types checked.",
                      "That any strategy has an edge. None does: all 18 rules fail their gates."],
                     [SRC["DK-MARKETS"], SRC["REPO"]]),
                ])),
        ],
    )
    return pages
