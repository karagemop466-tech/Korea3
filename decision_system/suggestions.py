"""The suggestions register: proposals, the evidence for them, and the choice.

The brief asks for a section "dedicated for suggestions so someone can review
suggestions and choose the best path before implementing any changes".  This module is
that section's data.  Each suggestion is:

* scored on eight 1-5 criteria (value, evidence, cost, risk, decision dependency,
  data availability, reversibility, time to signal);
* placed in exactly one decision path (P1-P5) so the reviewer is choosing between
  coherent bundles, not an unbounded menu;
* given an explicit "decide first" gate naming the questions (K-ids from
  :mod:`decision_system.knowledge`) that must be answered before implementation;
* given a status that can only change by a recorded human decision.  This package
  NEVER sets ``status`` to ``approved`` — the whole point is that implementation waits.

Scoring arithmetic is done in :func:`scored`, so the ranking on the site is computed,
never hand-written.
"""
from __future__ import annotations

from dataclasses import dataclass, field, asdict

CRITERIA = ("value", "evidence", "cost", "risk", "dependency", "data",
            "reversibility", "time_to_signal")
CRITERIA_LABEL = {
    "value": "Value to a decision (1-5)",
    "evidence": "Evidence already in hand (1-5)",
    "cost": "Build cost, inverted (5 = cheap)",
    "risk": "Risk, inverted (5 = safest)",
    "dependency": "Unblocks other work (1-5)",
    "data": "Data available today (1-5)",
    "reversibility": "Reversibility (5 = easy to undo)",
    "time_to_signal": "Speed to a measurable signal (5 = fast)",
}
WEIGHTS = {"value": 0.20, "evidence": 0.20, "risk": 0.15, "data": 0.15,
           "cost": 0.10, "dependency": 0.10, "reversibility": 0.05,
           "time_to_signal": 0.05}


@dataclass(frozen=True)
class Suggestion:
    id: str
    title: str
    path: str                 # P1..P5
    problem: str              # what is wrong today
    proposal: str             # what to do
    gate: str                 # what must be decided/known before implementation
    depends: tuple[str, ...]  # K-ids that gate it
    score: dict = field(default_factory=dict)
    status: str = "awaiting decision"   # awaiting decision | blocked | proposed
    owner_file: str = ""      # where the change would land, if approved
    effort: str = ""          # rough size, stated in days of one agent session

    def __post_init__(self) -> None:
        missing = [c for c in CRITERIA if c not in self.score]
        if missing:
            raise ValueError(f"{self.id}: missing criteria {missing}")
        for k, v in self.score.items():
            if not 1 <= v <= 5:
                raise ValueError(f"{self.id}: {k}={v} outside 1-5")
        if self.status == "approved":
            raise ValueError(
                f"{self.id}: a suggestion can only be approved by a recorded human decision; "
                "this package must never set it")


def _s(sid, title, path, problem, proposal, gate, depends, score, status="awaiting decision",
       owner_file="", effort="") -> Suggestion:
    return Suggestion(sid, title, path, problem, proposal, gate, tuple(depends), dict(score),
                      status, owner_file, effort)


SUGGESTIONS: tuple[Suggestion, ...] = (
    # ------------------------------------------------------------------ P1 evidence first
    _s("SG01", "Buy dated, licensed player-prop prices before writing any prop model",
       "P1",
       "No licensed prop price exists anywhere in the repository, so every prop edge and ROI on "
       "the site is blank and the prop section cannot answer the brief's 'player prop bet combos'.",
       "Obtain a licensed, timestamped prop-price feed for at least 2022-2025, store it under "
       "decision_system/ with per-file SHA-256, and only then score prop strategies.",
       "Decide the data budget and the licensed vendor. Until then the prop page stays blank.",
       ["K15", "K16", "K22"],
       {"value": 5, "evidence": 2, "cost": 2, "risk": 3, "dependency": 5, "data": 1,
        "reversibility": 4, "time_to_signal": 2},
       status="blocked", owner_file="decision_system/data/ (new licensed feed)",
       effort="external dependency, not an agent task"),
    _s("SG02", "Reconcile the nflverse injury transcription against official NFL pages, week by week",
       "P1",
       "The injury dataset is an independent transcription; it has never been reconciled with the "
       "official report for any season, so an error in it would silently move every injury number.",
       "Sample 20 club-weeks per season, open the official page, and compare player-by-player; "
       "publish the agreement rate and every disagreement as a flag.",
       "Choose the sampling budget; the comparison itself is mechanical once chosen.",
       ["K20"],
       {"value": 5, "evidence": 4, "cost": 3, "risk": 4, "dependency": 5, "data": 4,
        "reversibility": 5, "time_to_signal": 4},
       owner_file="decision_system/injury_engine.py", effort="2 sessions"),
    _s("SG03", "Read the official rulebook/operations pages for roster and inactive mechanics",
       "P1",
       "The 48-active / 90-minute-inactive rules are widely repeated but were not read at an "
       "official source in this session, so they are blank on the site (K08).",
       "Open operations.nfl.com rulebook pages, quote the exact clauses, add them to the source "
       "register, and only then use them in any availability calculation.",
       "None beyond finding the page; this is pure verification.",
       ["K08"],
       {"value": 4, "evidence": 4, "cost": 4, "risk": 5, "dependency": 4, "data": 3,
        "reversibility": 5, "time_to_signal": 5},
       owner_file="decision_system/sources.py", effort="< 1 session"),
    _s("SG04", "Extend start/backup identification past 2019 with weekly rosters",
       "P1",
       "Historical rosters with starts end in 2019, so starter-vs-backup status for 2020-2026 "
       "rests only on snap rank, which is a proxy.",
       "Add the nflverse weekly-rosters release, join it to snap counts, and publish both the "
       "proxy and the roster-based measure side by side so the proxy can be validated.",
       "Confirm the roster release licence and that weekly rosters carry a starter field.",
       ["K07"],
       {"value": 4, "evidence": 3, "cost": 3, "risk": 4, "dependency": 4, "data": 4,
        "reversibility": 4, "time_to_signal": 4},
       owner_file="decision_system/fetch.py, data/injury_lab/", effort="1-2 sessions"),
    # ---------------------------------------------------------------- P2 measurement rigour
    _s("SG05", "Pre-register every future strategy in a signed, timestamped file before it is run",
       "P2",
       "Eleven strategies were tested; the leaderboard correction depends on knowing exactly how "
       "many were tried, and a family that grows after the fact invalidates its own p-values.",
       "Write each hypothesis to decision_system/preregistered/<id>.json with a commit hash and "
       "UTC timestamp before the first backtest; the leaderboard reads the count from those files.",
       "Agree the freeze format and the rule for amending a pre-registration.",
       ["K21"],
       {"value": 5, "evidence": 5, "cost": 4, "risk": 4, "dependency": 5, "data": 5,
        "reversibility": 5, "time_to_signal": 5},
       owner_file="decision_system/preregistered/ (new)", effort="< 1 session"),
    _s("SG06", "Replace 'best ROI' ranking with a deflated, multiplicity-aware score",
       "P2",
       "A raw ROI leaderboard rewards the luckiest of k tries: the simulated best-of-11 no-skill "
       "ROI is +6.2% with a +10.1% 95th percentile.",
       "Score = deflated Sharpe probability, with the no-skill band and BH q-values shown beside "
       "it, and no reward badge until all seven gates pass.",
       "Decide whether the reward is per-strategy or per-portfolio.",
       ["K21"],
       {"value": 5, "evidence": 5, "cost": 3, "risk": 4, "dependency": 4, "data": 5,
        "reversibility": 5, "time_to_signal": 3},
       status="proposed", owner_file="decision_system/pages/leaderboard.html", effort="done in this build"),
    _s("SG07", "Publish a weekly walk-forward paper-trading ledger instead of backtest rankings",
       "P2",
       "Every number on the site today is a backtest; none is a forward record, so the strongest "
       "possible evidence — live, pre-committed picks — is missing.",
       "Each week, before kickoff, commit the model's picks and prices; settle them after the "
       "games and publish the running forward ROI with its CI.",
       "Confirm the project may publish pre-kickoff picks without it being betting advice; the "
       "site's disclaimer currently forbids advice.",
       ["K21"],
       {"value": 5, "evidence": 1, "cost": 2, "risk": 2, "dependency": 5, "data": 3,
        "reversibility": 2, "time_to_signal": 2},
       status="blocked", owner_file="decision_system/weekly/ (new)", effort="ongoing"),
    _s("SG08", "Quantify price uncertainty: replace the single closing price with a book range",
       "P2",
       "One price per game means every ROI is conditional on a book the project cannot name, and "
       "26.9% of prices were imputed at -110 in an earlier build.",
       "Store at least three books' closing prices where obtainable, report ROI at the worst and "
       "best price, and treat the worst-price ROI as the only reward-eligible number.",
       "Decide the maximum acceptable data cost; no free multi-book history was found.",
       ["K16"],
       {"value": 4, "evidence": 2, "cost": 2, "risk": 4, "dependency": 3, "data": 2,
        "reversibility": 4, "time_to_signal": 3},
       owner_file="decision_system/data/ (new)", effort="external dependency"),
    # ----------------------------------------------------------------- P3 injury/depth depth
    _s("SG09", "Model in-game attrition, not just pre-game status",
       "P3",
       "The only injury evidence is the pre-game report; a starter who is hurt on the first drive "
       "is invisible to every model here.",
       "Ingest play-by-play participation for the seasons available, detect mid-game exits of "
       "high-snap players, and measure the scoring effect of losing a starter mid-game.",
       "Decide whether low-resolution participation data (2016-2023) is precise enough to identify "
       "the player who left.",
       ["K18"],
       {"value": 5, "evidence": 2, "cost": 2, "risk": 3, "dependency": 4, "data": 3,
        "reversibility": 3, "time_to_signal": 2},
       owner_file="decision_system/injury_engine.py", effort="3+ sessions"),
    _s("SG10", "Publish a per-club depletion index with an explicit uncertainty band",
       "P3",
       "The site reports the measured coefficient of result residual on the share of snaps listed "
       "Out, but a reviewer cannot see which clubs are most and least depleted right now.",
       "Rank clubs by out-share of previous-game snaps, offence and defence separately, with the "
       "Wilson band and the number of contributing players.",
       "Choose whether a coach-decision (rest) designation should be excluded before ranking.",
       ["K07", "K18"],
       {"value": 4, "evidence": 4, "cost": 4, "risk": 4, "dependency": 3, "data": 5,
        "reversibility": 5, "time_to_signal": 4},
       status="proposed", owner_file="decision_system/pages/injuries.html", effort="done in this build"),
    _s("SG11", "Separate 'Out' from 'Questionable' in every model input",
       "P3",
       "Collapsing statuses into 'injured' throws away the measured difference between them "
       "(the status-value table shows the gap explicitly).",
       "Use three indicator columns plus the practice code, and test whether the practice trend "
       "adds information beyond the final status.",
       "None; the data is already present. This is a modelling choice to confirm.",
       ["K01", "K05"],
       {"value": 4, "evidence": 5, "cost": 4, "risk": 4, "dependency": 3, "data": 5,
        "reversibility": 4, "time_to_signal": 4},
       owner_file="decision_system/injury_engine.py", effort="1 session"),
    # --------------------------------------------------------------- P4 product/site
    _s("SG12", "Add a reviewer decision log with signed choices to the site",
       "P4",
       "Suggestions can be read but a reviewer's choice leaves no auditable trace, so 'choose "
       "before implementing' is a convention rather than a control.",
       "Add a decisions.json whose entries carry who/what/when/rationale, render it as the last "
       "section of the Suggestions page, and refuse to mark a suggestion implemented without one.",
       "Agree who may sign a decision and where it is recorded (repo commit is the proposal).",
       ["K21"],
       {"value": 5, "evidence": 5, "cost": 4, "risk": 4, "dependency": 4, "data": 5,
        "reversibility": 5, "time_to_signal": 5},
       status="proposed", owner_file="decision_system/decisions.json", effort="< 1 session"),
    _s("SG13", "Make every published number one click from its computation",
       "P4",
       "Rows link a source, but not always the exact script and line that produced the value.",
       "For each table, render a 'how this number is made' link to the function and the input "
       "manifest entry, generated from the same JSON the table is built from.",
       "None; this is presentation of existing provenance.",
       ["K20"],
       {"value": 4, "evidence": 5, "cost": 3, "risk": 5, "dependency": 3, "data": 5,
        "reversibility": 5, "time_to_signal": 4},
       status="proposed", owner_file="decision_system/build.py", effort="done in this build"),
    _s("SG14", "Keep one dashboard instead of six parallel ones",
       "P4",
       "The repository now serves six dashboards (root, hub, docs, site, verified, decision_system) "
       "and a reviewer has to know which one is current.",
       "Make the newest dashboard the single navigation surface and turn the others into archived "
       "links with a dated banner; never delete another session's build.",
       "Owner decision: which build is canonical for the long term.",
       ["K21"],
       {"value": 4, "evidence": 5, "cost": 3, "risk": 3, "dependency": 3, "data": 5,
        "reversibility": 4, "time_to_signal": 4},
       owner_file="root navigation (additive only)", effort="1 session"),
    # ------------------------------------------------------------- P5 competition design
    _s("SG15", "Define the reward rule before any strategy can qualify",
       "P5",
       "The brief asks for rewards for top-performing strategies but no budget, eligibility rule "
       "or forfeiture rule exists, so 'top performing' is currently undefined.",
       "Publish a rules page: entry requires a pre-registration commit, a minimum settled-bet "
       "count, all seven gates, and a forward paper-trading period; rewards are paid on the "
       "forward record, never the backtest.",
       "The reviewer must set the budget and the minimum forward period.",
       ["K21"],
       {"value": 5, "evidence": 3, "cost": 4, "risk": 3, "dependency": 5, "data": 4,
        "reversibility": 4, "time_to_signal": 3},
       status="proposed", owner_file="decision_system/pages/leaderboard.html", effort="done in this build"),
    _s("SG16", "Score combinations (single, parlay, prop) on the same skill bus",
       "P5",
       "Singles, parlays and props are currently judged by different arithmetic, so a parlay can "
       "look better than its legs.",
       "Score every ticket — single, parlay, same-game parlay, prop combo — on per-unit return "
       "through the same seven gates, and publish the leg-level correlation used to price it.",
       "Confirm the operator's push rule is the settlement rule used for combinations (K13).",
       ["K13", "K14"],
       {"value": 5, "evidence": 5, "cost": 4, "risk": 4, "dependency": 4, "data": 5,
        "reversibility": 5, "time_to_signal": 4},
       status="proposed", owner_file="decision_system/strategies.py", effort="done in this build"),
)

PATHS: tuple[dict, ...] = (
    {"id": "P1", "name": "Evidence first — close the verification gaps before modelling",
     "thesis": "Six of the nine blanks on this site are verification gaps, not modelling gaps. "
               "Closing them is cheap, reversible and it protects every later number.",
     "why_not": "It produces no new predictive signal this week.", "risks": "Low."},
    {"id": "P2", "name": "Measurement rigour — make the competition honest",
     "thesis": "The leaderboard already refuses to reward luck; the remaining weakness is that "
               "the current family of strategies was not frozen with a signed pre-registration.",
     "why_not": "It cannot create an edge; it can only stop a false one being rewarded.",
     "risks": "Low; mostly process."},
    {"id": "P3", "name": "Availability depth — push the injury work further",
     "thesis": "The status-to-participation measurement is the newest evidence in the repository "
               "and it is where an unexploited information edge, if one exists, would live.",
     "why_not": "Needs in-game participation data and a modelling choice; highest build cost.",
     "risks": "Medium: a weak effect can be over-read as a signal."},
    {"id": "P4", "name": "Product — make the site easier to decide from",
     "thesis": "A decision is easier when the provenance is one click away and there is a single "
               "canonical dashboard.",
     "why_not": "Improves usability, not the evidence.", "risks": "Low."},
    {"id": "P5", "name": "Competition — turn the leaderboard into a rules-based contest",
     "thesis": "The brief's reward structure can be defined now, without a budget, so that "
               "entry criteria exist before anyone can qualify.",
     "why_not": "A rules page with no funded reward may read as a promise; wording must be exact.",
     "risks": "Medium: reputational if a reward is implied and not paid."},
)


def scored() -> list[Suggestion]:
    """Rank by weighted score.  Computed, so the site cannot drift from the register."""
    def total(s: Suggestion) -> float:
        return sum(WEIGHTS[k] * s.score[k] for k in CRITERIA)
    return sorted(SUGGESTIONS, key=lambda s: (-total(s), s.id))


def totals() -> dict[str, float]:
    return {s.id: round(sum(WEIGHTS[k] * s.score[k] for k in CRITERIA), 3) for s in SUGGESTIONS}


def recommendation() -> dict:
    ranked = scored()
    return {
        "order": [s.id for s in ranked],
        "top": ranked[0].id,
        "rationale": (
            f"{ranked[0].id} ranks first on the weighted score ({totals()[ranked[0].id]:.2f}/5) "
            "because it is high value, fully evidenced by work already in the repository, cheap, "
            "and reversible. It does not touch any settled number, so approving it cannot invalidate "
            "a published result."
        ),
        "path_totals": _path_totals(),
    }


def _path_totals() -> dict[str, dict]:
    t = totals()
    out: dict[str, dict] = {}
    for p in PATHS:
        members = [s for s in SUGGESTIONS if s.path == p["id"]]
        out[p["id"]] = {
            "suggestions": [s.id for s in members],
            "mean_score": round(sum(t[s.id] for s in members) / max(len(members), 1), 3),
            "blocked": [s.id for s in members if s.status == "blocked"],
        }
    return out


def as_dicts() -> list[dict]:
    ranked = scored()
    order = {s.id: i + 1 for i, s in enumerate(ranked)}
    t = totals()
    return [{**asdict(s), "weighted_score": t[s.id], "rank": order[s.id]} for s in SUGGESTIONS]


if __name__ == "__main__":  # pragma: no cover
    t = totals()
    for s in scored():
        print(f"{s.id} {t[s.id]:>5.2f}  {s.path}  {s.title}")
