#!/usr/bin/env python3
"""Render the three pages this session adds: availability, questions, suggestions.

Imported by hub/build_hub.py. Uses that module's renderers so the same fail-closed
rules apply: every table row carries a link to the publisher that supports it, and a
value that was not published is rendered as text that says so or as a flagged blank.
"""
from __future__ import annotations

import html

import decision_data as D

SIDE_OFFENSE = {"QB", "RB", "WR", "TE", "LT", "LG", "C", "RG", "RT", "FB", "OL"}

# Honest status per question. "open" means no official source establishes it.
STATUS = {
    "Q01": ("open", "warn"), "Q02": ("open", "warn"), "Q03": ("open", "warn"),
    "Q04": ("open", "warn"),
    "Q05": ("partly answered — the clubs' own disclaimers are verified, the league-wide rule is not", "info"),
    "Q06": ("open", "warn"), "Q07": ("open", "warn"), "Q08": ("open — owner decision", "warn"),
    "Q09": ("open — method documented, family size not fixed", "warn"), "Q10": ("open", "warn"),
    "Q11": ("open", "warn"), "Q12": ("open — operator rules verified, metric rule not chosen", "warn"),
    "Q13": ("open", "warn"), "Q14": ("open", "warn"),
    "Q15": ("open — owner decision", "warn"), "Q16": ("open", "warn"), "Q17": ("open", "warn"),
    "Q18": ("open — 4 of 32 clubs verified so far", "info"), "Q19": ("open", "warn"),
    "Q20": ("partly answered — the 404s are verified, the re-check schedule is not in place", "info"),
}


def build(bh):
    """bh is the imported hub.build_hub module, used for its renderers."""
    E, A, T, sec, pill, blank = bh.E, bh.A, bh.T, bh.sec, bh.pill, bh.blank
    SRC, repo = bh.SRC, bh.repo
    pages = {}

    def S(name):
        return A(SRC[name], name + " ↗")

    # ------------------------------------------------------------------ data
    practice_rows = []
    for club, player, pos, injury, practice, status in D.PRACTICE_ROWS:
        srcs = ["NFL-INJURIES"]
        if status:
            srcs.append("NFL-INJ-NEWS")
        practice_rows.append((
            [f"<strong>{E(club)}</strong>", E(player), E(pos),
             E(injury) if injury else '<span class="muted">not printed</span>',
             E(practice),
             pill(status, "bad" if status == "Out" else "warn") if status
             else '<span class="muted">not designated</span>'],
            srcs,
            f"p-{club}-{player.lower().replace(' ', '-').replace('.', '').replace(chr(39), '')}",
        ))

    depth_rows, thin_rows, n_slots, deep = [], [], 0, 0
    for club, rows in D.DEPTH.items():
        for pos, names in rows:
            side = "Offense" if pos in SIDE_OFFENSE else "Defense / ST"
            filled = [n for n in names if n]
            n_slots += len(names)
            deep = max(deep, len(filled))
            cells = [f"<strong>{E(club)}</strong>", E(side), E(pos),
                     E(filled[0]) if filled else '<span class="muted">blank on the published page</span>',
                     E(filled[1]) if len(filled) > 1 else '<span class="muted">no 2nd name printed</span>',
                     E(" · ".join(filled[2:])) if len(filled) > 2 else '<span class="muted">none printed</span>']
            note = []
            if "" in names:
                note.append("contains a blank slot on the published page")
            if club == "NE":
                note.append("club labels the chart unofficial")
            if club == "DET":
                note.append("club labels the chart unofficial")
            cells.append(E("; ".join(note)) if note else '<span class="muted">—</span>')
            depth_rows.append((cells, [f"CLUB-{club}-DEPTH"],
                               f"d-{club}-{pos.lower()}-{len(depth_rows)}"))
            if len(filled) == 1:
                thin_rows.append(([
                    f"<strong>{E(club)}</strong>", E(side), E(pos), E(filled[0]),
                    "<strong>1</strong>", pill("no depth printed", "warn")],
                    [f"CLUB-{club}-DEPTH"], None))

    anomalies = [
        ("A01", "WAS", "Lucas Patrick",
         "Printed OUT (concussion) on the Week 10 report. NFL.com lists him on the active roster as position C with an empty jersey number; the club roster lists him as G with number 63; no row of the club depth chart prints him.",
         "An OUT player cannot be asserted to be a starter, his absence from the chart cannot be read as a depth rank, and two official pages disagree on his position.",
         ["NFL-INJ-NEWS", "NFL-ROSTER-WAS", "CLUB-WAS-ROSTER", "CLUB-WAS-DEPTH"]),
        ("A02", "NYG", "Malik Harrison",
         "Printed QUESTIONABLE (groin) on the Week 10 report, but not printed in any row of the club depth chart.",
         "The depth ordinal for a listed player is therefore unknown from the official pages read here.",
         ["NFL-INJ-NEWS", "CLUB-NYG-DEPTH"]),
        ("A03", "WAS", "Austin Ekeler",
         "NFL.com prints his jersey-number cell empty; the club roster prints 30.",
         "Two official pages disagree on a factual field. No precedence rule exists yet (Q06).",
         ["NFL-ROSTER-WAS", "CLUB-WAS-ROSTER"]),
        ("A04", "WAS", "Robert Henry Jr.",
         "NFL.com prints jersey number 30; the club roster prints 34.",
         "Direct conflict between two official pages. Published, not resolved.",
         ["NFL-ROSTER-WAS", "CLUB-WAS-ROSTER"]),
        ("A05", "NE", "Depth chart status",
         "The club labels its 2026 depth chart 'UNOFFICIAL' and says it 'reflects the opinions of the Patriots.com writers and don't necessarily reflect those of the organization.'",
         "Any model feature built from this chart inherits an explicit editorial disclaimer.",
         ["CLUB-NE-DEPTH"]),
        ("A06", "DET", "Depth chart status",
         "The club labels its chart 'Unofficial Depth Chart Compiled by Lions Football Communications'.",
         "Same limitation as A05.",
         ["CLUB-DET-DEPTH"]),
        ("A07", "League", "Inactive reports",
         "The official inactives page prints 'Please check back soon for NFL Inactive Reports for this Season'.",
         "Activation cannot be verified from an official page today, which blocks Q07.",
         ["NFL-INACTIVES"]),
        ("A08", "DET", "Kerby Joseph",
         "Printed on the Week 10 report as Limited Participation in Practice, but not printed in any row of the club depth chart, which carries two S rows: 'Chuck Clark' alone and 'Brian Branch | Christian Izien'.",
         "Same class as A01/A02: a listed player whose printed depth rank is unknown. A one-name row is not proof that no backup exists, only that none is printed.",
         ["CLUB-DET-DEPTH", "NFL-INJURIES"]),
    ]

    # ------------------------------------------------------------ page: availability
    n_out = sum(1 for r in D.PRACTICE_ROWS if r[5] == "Out")
    n_q = sum(1 for r in D.PRACTICE_ROWS if r[5] == "Questionable")
    n_status = sum(1 for r in D.PRACTICE_ROWS if r[5])
    kpis_avail = [
        ("Clubs transcribed", 4, "WAS, NYG, NE, DET — Week 10, 2026"),
        ("Practice-report rows", len(D.PRACTICE_ROWS), "Every row printed for those four clubs"),
        ("Printed game statuses", n_status, f"{n_out} Out · {n_q} Questionable · the rest not designated"),
        ("Depth slots transcribed", n_slots, "Verbatim, printed order preserved"),
        ("Values inferred by this page", 0, "No probability, snap share or ordinal is estimated"),
    ]
    pages["availability"] = dict(
        title="Injuries & lineup depth",
        lead="Who is officially out or uncertain for Week 10 of the 2026 season, and who the clubs' own "
             "depth charts print as the next man up at each position — starters and backups, offence and "
             "defence. Transcribed from official league and club pages on " + D.READ_AT +
             ". Nothing here is estimated.",
        kpis=kpis_avail,
        sections=[
            sec("Read this before using the table",
                "Three limits are structural, not temporary. (1) The NFL defines its game-status words "
                "qualitatively — 'uncertain', 'unlikely', 'will not play' — and publishes no percentage. "
                "(2) A practice-participation line is not a game status. (3) A depth chart is a printed "
                "order, not an official designation: two of the four clubs on this page label theirs "
                "unofficial in their own words. So this page can tell you <em>that</em> a starter is out "
                "and <em>who is printed next</em>. It cannot tell you how many snaps the replacement will "
                "play, and it will not pretend to.",
                note="Every row links to the official page it came from. Anything the official pages do not "
                     "state is either absent here or flagged on the Flagged for Review page."),
            sec("What each official label means",
                "Verbatim definitions from the NFL's own announcement of the current injury-report policy. "
                "The last column is what the label does <strong>not</strong> license you to assume.",
                T(["Label", "Field", "Official definition", "What it does not tell you"],
                  [([f"<strong>{E(l)}</strong>", E(f), E(defn), E(limit)], [sid])
                   for l, f, defn, limit, sid in D.LABEL_ROWS],
                  caption="Definitions are quoted from the NFL release; interpretations in the last column "
                          "are this session's reading of those words.")),
            sec("Week 10, 2026 — official practice and game status",
                "Every player printed for the four clubs in scope, in the order the official page prints "
                "them. 'Not designated' reproduces an empty Game Status cell; it is not a statement that "
                "the player is fit.",
                T(["Club", "Player", "Pos", "Injury as printed", "Practice", "Game status"],
                  practice_rows, caption=D.PRACTICE_NOTE, filter_id="inj-filter")),
            sec("Next-man-up ledger — printed depth order",
                "The clubs' own depth charts, transcribed column by column without re-sorting. 'Starter' "
                "means <em>first name printed on the page</em>, not a verified starting assignment.",
                T(["Club", "Side", "Pos", "1st printed", "2nd printed", "3rd printed and beyond", "Note on this row"],
                  depth_rows, caption="Printed order only. See the club disclaimers section below.",
                  filter_id="depth-filter")),
            sec("Where depth is thinnest — positions with only one printed name",
                "Counted directly from the tables above: a position row that prints a single player. This "
                "is a count of published names, not a measure of how good the backup is.",
                T(["Club", "Side", "Pos", "Only name printed", "Names printed", "Assessment"],
                  thin_rows,
                  caption=str(len(thin_rows)) + " position rows print a single name across the four clubs. "
                          "A thin list is a question to investigate, never a conclusion.",
                  filter_id="thin-filter")),
            sec("Flagged anomalies on the official pages",
                "Facts observed while transcribing that a reader should know before trusting any join.",
                T(["ID", "Club", "Subject", "What the official pages show", "Why it matters"],
                  [([f"<strong>{E(i)}</strong>", E(c), E(s), E(w), E(y)], srcs, i.lower())
                   for i, c, s, w, y, srcs in anomalies],
                  caption="Published open, not resolved. These also appear on Flagged for Review.",
                  filter_id="anom-filter")),
            sec("How the clubs label their own depth charts",
                "Reproduced so a reader never has to take this site's word for how official a chart is.",
                T(["Club", "Label printed by the publisher", "Consequence"],
                  [([f"<strong>{E(c)}</strong> ({E(D.CLUB_NAME[c])})", E(D.DEPTH_LABEL[c]),
                     pill("treat as context, not designation", "warn")],
                    [f"CLUB-{c}-DEPTH"]) for c in ("WAS", "NYG", "NE", "DET")],
                  caption="The two clubs that print a disclaimer are quoted verbatim; the two that do not "
                          "are described by what their page actually says.")),
            sec("What this page still cannot do",
                "Stated plainly so no one mistakes a ledger for a model.",
                T(["Question", "Status", "What would unlock it"],
                  [(["Snap counts and true starter designation", pill("unverified", "warn"),
                     "Official participation data, licensed (see suggestions S05)"],
                    ["NFL-STATS", "REPO"]),
                   (["Realised availability behind each label", pill("unverified", "warn"),
                     "Official inactive lists joined to labels (S03)"],
                    ["NFL-INACTIVES", "NFL-INJ-POLICY"]),
                   (["Effect of a missing starter on the spread", pill("unverified", "warn"),
                     "A licensed price archive plus pre-registered hypotheses (S01, S06)"],
                    ["NFL-TERMS", "NIST-MULTI"]),
                   (["The remaining 28 clubs", pill("not transcribed", "info"),
                     "Same transcription method, club by club (S02)"],
                    ["NFL-INJURIES", repo("hub/decision_data.py")])],
                  caption="A blank here is deliberate: the value does not exist in an official source.")),
        ],
    )

    # ------------------------------------------------------------ page: questions
    q_rows = []
    for qid, q, blocks, known, missing, method, sugg in D.QUESTIONS:
        status, kind = STATUS[qid]
        q_rows.append(([
            f"<strong>{E(qid)}</strong>", E(q), E(blocks), E(known), E(missing), E(method),
            pill(status, kind), A("suggestions.html#" + sugg.lower(), sugg),
        ], ["REPO"]))
    open_count = sum(1 for q in D.QUESTIONS if STATUS[q[0]][0].startswith("open"))
    pages["questions"] = dict(
        title="Open questions register",
        lead="Every question that must be answered before a betting decision can reasonably be made, "
             "separated into what is already verified, what is missing, and how the missing information "
             "would be discovered. Nothing is marked answered unless an official source establishes it.",
        kpis=[("Questions registered", len(D.QUESTIONS), "Grouped by the decision each one blocks"),
              ("Still open", open_count, "No official source establishes the answer"),
              ("Partly answered", len(D.QUESTIONS) - open_count, "Only the published part is claimed"),
              ("Answered outright", 0, "Nothing is scored as answered without an official source")],
        sections=[
            sec("The rule this page follows",
                "A question is <strong>answered</strong> only when an official publisher states the fact, "
                "and the row links to that page. A question is <strong>partly answered</strong> when an "
                "official page settles part of it and leaves the rest open — the open part is named. "
                "Everything else is <strong>open</strong>. No question is ever closed by inference, by "
                "averaging other pages, or by the absence of a contradiction.",
                note="The fifth column is what we have; the sixth is what is missing. The last two columns "
                     "point at the suggestion that would fill the gap."),
            sec("The register",
                "Twenty questions. Read the 'blocks what' column first: each one names the decision that "
                "cannot be made until the question is answered.",
                T(["ID", "Question", "Blocks what", "What is known / verified", "What is missing",
                   "How the missing information would be discovered", "Status", "Suggestion"],
                  q_rows, caption="Official sources for the 'known' column are on the pages linked under "
                                  "each suggestion, and on the Official sources page.", filter_id="q-filter")),
            sec("What is verified today",
                "Facts an official publisher states, which several questions depend on.",
                T(["Verified fact", "Publisher"], [
                    (["Game-status words are qualitative only: Out = will not play; Doubtful = unlikely; "
                      "Questionable = uncertain.", "NFL — Competition Committee release"], ["NFL-INJ-POLICY"]),
                    (["Practice labels are Did Not Participate / Limited (<100% of normal reps) / Full (100%).",
                      "NFL — Competition Committee release"], ["NFL-INJ-POLICY"]),
                    (["'Probable' was removed because about 95% of players listed that way played.",
                      "NFL — Competition Committee release"], ["NFL-INJ-POLICY"]),
                    (["A player certain to play is not listed on the Game Status Report; a late deactivation "
                      "must be explained to the league.", "NFL — Competition Committee release"], ["NFL-INJ-POLICY"]),
                    (["The active/inactive list is 53 players; practice-squad elevation is capped at three "
                      "regular-season games per player per league year.", "NFL Football Operations"], ["NFL-ROSTER-RULES"]),
                    (["No 2026 inactive report is published: the page says 'Please check back soon'.",
                      "NFL"], ["NFL-INACTIVES"]),
                    (["Two of four clubs label their own depth chart unofficial.", "Patriots.com, DetroitLions.com"],
                     ["CLUB-NE-DEPTH", "CLUB-DET-DEPTH"]),
                    (["Repeated pairwise comparisons do not preserve the overall significance level.",
                      "NIST/SEMATECH e-Handbook"], ["NIST-MULTI"]),
                ], caption="Each fact is quoted on the Official sources page with its exact wording.")),
            sec("The minimum set that must be closed before implementing anything",
                "Not every question blocks everything. These four block the next implementation step; the "
                "rest can follow in the background.",
                T(["Question", "Why it blocks", "Who can close it"], [
                    (["Q01 — licensed, timestamped price archive", "Without prices there is no measurement of "
                      "any kind: no edge, no ROI, no correlation, no ranking.", "Owner (budget) + vendor"],
                     ["NFL-TERMS", "DK-MARKETS"]),
                    (["Q06 — source precedence rule", "Every joined table depends on it; two official pages "
                      "already disagree on jersey numbers.", "This project (writing, no cost)"],
                     ["NFL-ROSTER-WAS", "CLUB-WAS-ROSTER"]),
                    (["Q09 — registered family size and alpha", "Without it a winner is guaranteed by chance.",
                      "This project (writing, no cost)"], ["NIST-MULTI", "NIST-BONF"]),
                    (["Q08 — reward terms", "Decides whether the leaderboard is a competition or a ranking.",
                      "Owner"], ["NFL-RG", "REPO"]),
                ])),
        ],
    )

    # ------------------------------------------------------------ page: suggestions
    s_rows = []
    for sid, title, problem, benefit, effort, risk, answers, rec, basis in D.SUGGESTIONS:
        kind = ("ok" if rec.startswith("Adopt") else "info" if rec.startswith(("Pilot", "Defer", "Requires"))
                else "bad")
        s_rows.append((
            [f"<strong>{E(sid)}</strong>", E(title), E(problem), E(benefit),
             E(effort), E(risk), E(answers), pill(rec, kind)],
            list(basis) + ["REPO"],
            sid.lower(),
        ))
    adopt = [s for s in D.SUGGESTIONS if s[7].startswith("Adopt")]
    pilot = [s for s in D.SUGGESTIONS if s[7].startswith("Pilot")]
    defer = [s for s in D.SUGGESTIONS if s[7].startswith(("Defer", "Requires"))]
    reject = [s for s in D.SUGGESTIONS if s[7].startswith("Reject")]
    pages["suggestions"] = dict(
        title="Suggestions & decision path",
        lead="Options for improving the site and the research, each with what it solves, what it costs, "
             "what could go wrong, and the questions it answers — plus one recommended order in which to "
             "choose. Nothing on this page is implemented just because it is listed.",
        kpis=[("Options reviewed", len(D.SUGGESTIONS), "Each mapped to the questions it closes"),
              ("Recommended now", len(adopt), "No purchase, no permission, no new dependency"),
              ("Pilot / owner decision", len(pilot) + len(defer), "Blocked on budget or on your call"),
              ("Rejected", len(reject), "Listed so the decision is visible, not hidden")],
        sections=[
            sec("How to use this page",
                "Rows are ordered by dependency, not by excitement. Effort, risk and recommendation are "
                "this session's <strong>judgement</strong> — they are not facts and they link to the "
                "official basis behind the problem, not to a source that would prove the opinion. Each "
                "row names the questions from the register that it would close, so you can see what a "
                "choice buys before you make it.",
                note="Pick a path, record it on the questions page, and only then implement. That is the "
                     "review gate the brief asked for."),
            sec("Recommended path, in order",
                "Six steps. The first three cost nothing and two of them lose evidence every week they are "
                "delayed.",
                T(["Step", "Action", "Why now", "Gated by"],
                  [([f"<strong>{E(n)}</strong>", E(a), E(w), E(g)], ["REPO"])
                   for n, a, w, g in D.PATH],
                  caption="Ordering is a recommendation from this session; it is not a verified fact.")),
            sec("All options, scored",
                "The full register. Filter it by any word — 'licence', 'injury', 'reject'.",
                T(["ID", "Suggestion", "Problem it solves", "Benefit", "Effort (judgement)",
                   "Risk (judgement)", "Questions it answers", "Recommendation"],
                  s_rows,
                  caption="Effort, risk and recommendation are this session's judgement, not verified "
                          "facts. The source column links the official basis for the problem each row "
                          "describes.", filter_id="s-filter")),
            sec("Decision summary",
                "What happens if you simply accept this page's recommendation.",
                T(["Bucket", "Count", "Items"], [
                    (["Adopt now", str(len(adopt)), ", ".join(s[0] for s in adopt)], ["REPO"]),
                    (["Pilot first", str(len(pilot)), ", ".join(s[0] for s in pilot)], ["REPO"]),
                    (["Defer / owner decision", str(len(defer)), ", ".join(s[0] for s in defer)], ["REPO"]),
                    (["Reject", str(len(reject)), ", ".join(s[0] for s in reject)], ["REPO"]),
                ], caption="Rejections are deliberate and are listed with their reasons.")),
            sec("What is deliberately not implemented",
                "Three rows that exist to stop work, not to start it.",
                T(["ID", "Option", "Why it is refused", "What it would have cost"],
                  [([f"<strong>{E(s[0])}</strong>", E(s[1]),
                     pill("refused", "bad") + " " + E(s[4]), E(s[5])],
                    list(s[8]) + ["REPO"])
                   for s in D.SUGGESTIONS if s[7].startswith("Reject")],
                  caption="A rejected option that is written down cannot quietly come back.")),
            sec("Decisions that are yours, not this session's",
                "Everything else on this page can be executed without input. These two cannot.",
                T(["Decision", "The options", "What this session did instead"], [
                    (["Q15 — may licensed data be purchased, and does a purchase count as 'manual input'?",
                      "Buy a quote archive and a participation feed (S01, S05) · or stay descriptive and "
                      "publish no measured value",
                      "Left every measured value blank and flagged rather than guessing a budget"],
                     ["NFL-TERMS", "REPO"]),
                    (["Q08 — are rewards real (funded, with settlement terms) or notional?",
                      "Fund a pool with gate-passing entry requirements (S10) · or publish the leaderboard "
                      "as a ranking with no stakes",
                      "Published a fail-closed leaderboard with zero eligible entries and no prize claim"],
                     ["NFL-RG", "REPO"]),
                ], caption="Both are recorded as open on the questions register.")),
        ],
    )
    return pages
