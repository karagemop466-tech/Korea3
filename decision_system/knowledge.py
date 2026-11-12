"""The knowledge register: every fact this project is allowed to use, with its status.

This is the single place the brief's "clear list of questions, information and answers"
is satisfied mechanically.  A fact is only used by the site if it appears here, and each
fact carries one of four statuses:

``official``
    A verbatim quote from a league, operator or standards-body page that was opened and
    read in this session.  The source id must exist in :mod:`decision_system.sources` and
    must be in an official tier.  ``value`` is the *quoted* wording, never a paraphrase
    dressed up as a number.

``reproduced``
    A number this repository re-computes from committed data or from an arithmetic
    identity.  The ``reproduce`` command is printed on the page so a reviewer can rerun it.

``dataset``
    A measured number from the pinned open dataset.  Reproducible, but explicitly NOT an
    official statistic.

``blank``
    The answer is not known.  ``value`` is ``""``, ``why`` says what is missing and ``flag``
    names the review-page anchor.  Blanks are never filled by inference anywhere in this
    package — :mod:`decision_system.build` refuses to publish one without a flag.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Fact:
    id: str
    question: str
    status: str            # official | reproduced | dataset | blank
    value: str
    why: str               # how the answer was obtained, or why it is blank
    source: str = ""       # source id from sources.py (official) / dataset id
    reproduce: str = ""    # shell command that reproduces a computed number
    flag: str = ""         # flag anchor when status == blank

    def __post_init__(self) -> None:
        if self.status not in {"official", "reproduced", "dataset", "blank"}:
            raise ValueError(f"{self.id}: bad status {self.status}")
        if self.status == "blank":
            if self.value != "":
                raise ValueError(f"{self.id}: a blank must have an empty value")
            if not self.flag:
                raise ValueError(f"{self.id}: a blank must name a flag anchor")
        else:
            if not self.value.strip():
                raise ValueError(f"{self.id}: a non-blank must carry a value")
            if not self.source:
                raise ValueError(f"{self.id}: a non-blank must carry a source id")


F = Fact

FACTS: tuple[Fact, ...] = (
    # ------------------------------------------------------------ what a status means
    F("K01", "What do 'Out', 'Doubtful' and 'Questionable' officially mean in the 2026 season?",
      "official",
      "Out = will not play; Doubtful = unlikely to participate; Questionable = uncertain whether "
      "the player will play. The league attaches no percentage to Doubtful or Questionable.",
      "Read verbatim in the 2016 Competition Committee release that created the current policy; "
      "still the wording used by the live 2026 report.",
      "NFL-INJ-POLICY-2016"),
    F("K02", "Does the league publish a probability for Questionable?",
      "official",
      "No. The policy language is qualitative only ('uncertain', 'unlikely'). The old 50%/25% "
      "figures were informal and were attached to a policy that no longer exists.",
      "The policy text defines the terms without percentages; the same release explains the "
      "removal of 'Probable'.",
      "NFL-INJ-POLICY-2016-PROB"),
    F("K03", "Why is there no 'Probable' row in a 2026 injury report?",
      "official",
      "Because the category was eliminated for the 2016 season.",
      "League release: 'The \"Probable\" category was eliminated ... because approximately 95 "
      "percent of the players who were listed as \"Probable\" in prior years did in fact play'.",
      "NFL-INJ-POLICY-2016-PROB"),
    F("K04", "What are the three practice-report codes?",
      "official",
      "Did Not Participate; Limited Participation (less than 100 percent of normal repetitions); "
      "Full Participation (100 percent of normal repetitions).",
      "League release, Practice Report section.",
      "NFL-INJ-POLICY-2016"),
    F("K05", "Can a player have a practice status and no game status?",
      "official",
      "Yes. A player certain to play is not listed on the Game Status Report even if he appeared "
      "on the practice report; if he is then deactivated the club must explain to the league.",
      "League release, Game Status Report section. The live 2025 week-9 page shows exactly this "
      "pattern (e.g. a quarterback with three full practices and a blank game status).",
      "NFL-INJ-POLICY-2016-CERTAIN"),
    F("K06", "Does NFL.com publish a numbered depth chart for each club?",
      "blank", "",
      "NFL.com publishes club rosters (name, number, position, ACT status) but the club depth-chart "
      "route returned HTTP 404 when opened on 2026-11-12. No official numbered depth order was "
      "found, so no official depth order is published anywhere on this site.",
      flag="DS-F01"),
    F("K07", "Where does the depth order used for the starter/backup analysis come from?",
      "dataset",
      "nflverse depth charts (2001-2026; the 2025+ schema carries pos_rank) and nflverse snap "
      "counts (2012-2026). Both are labelled UNOFFICIAL everywhere they appear.",
      "Pinned release assets, SHA-256 recorded in data/injury_lab/manifest.json and re-verified by "
      "CI on every run.",
      "DS-DEPTH"),
    F("K08", "How many players can dress for a game, and when is the inactive list final?",
      "blank", "",
      "Widely reported as 48 active with an offensive-line condition and a 90-minute deadline, but "
      "the official rulebook/operations page carrying that wording was NOT opened in this session, "
      "and this site does not publish a rule it has not read at the source.",
      flag="DS-F02"),
    # ------------------------------------------------------ data we do have
    F("K09", "Which injury-report seasons are available to measure?",
      "dataset", "2009-2026 weekly reports (regular season and postseason), 18 seasons.",
      "nflverse 'injuries' release; file list and SHA-256 per file in the manifest.",
      "DS-INJURIES"),
    F("K10", "Which snap-count seasons are available?",
      "dataset", "2012-2026 per-game snap counts by player.",
      "nflverse 'snap_counts' release.",
      "DS-SNAPS"),
    F("K11", "Is there an official player-level game log?",
      "official",
      "NFL Support points readers to the NFL.com Player Statistics pages and the Player Index for "
      "player stats; this project does not scrape them (NFL Terms 1.3) and uses nflverse instead, "
      "labelled as unofficial.",
      "Read on the official NFL Support Stats & Records article; the data boundary is the NFL "
      "Terms section 1.3.",
      "NFL-STATS", reproduce="python3 -m decision_system.sources"),
    F("K12", "How is American odds priced?",
      "official",
      "-110 means a $110 stake returns $100 profit; +110 means a $100 stake returns $110 profit. "
      "A -110/-110 two-way market implies a 52.381% break-even on each side.",
      "Operator odds explainer (readable in full this session) plus the arithmetic identity "
      "recomputed by this package.",
      "DK-ODDS"),
    F("K13", "What does settlement require on a parlay?",
      "official",
      "Every leg must win; a push removes that leg and recalculates the price. A losing leg loses "
      "the whole parlay.",
      "Operator parlay FAQ, read in full this session.",
      "DK-PARLAY"),
    F("K14", "Does an operator treat correlated legs as a pricing problem?",
      "official",
      "Yes: 'For certain selections, the outcomes can be considered correlated. In these cases, "
      "DraftKings reserves the right to restrict parlay betting on these outcomes.'",
      "Operator parlay FAQ. The operator states that correlation matters; it publishes no value "
      "for any NFL leg, so every correlation number here is measured.",
      "DK-CORRELATED"),
    F("K15", "What are the house rules that govern a void or a non-starter?",
      "blank", "",
      "The operator's settlement clauses for non-starters are published per market and per "
      "jurisdiction and were not readable in this session (the help-centre article body is "
      "rendered client-side). No settlement assumption is published for props.",
      flag="DS-F03"),
    F("K16", "Do we have licensed player-prop prices?",
      "blank", "",
      "No. No reachable source provides dated, licensed NFL player-prop quotes. Every prop price "
      "on this site is blank, and every prop edge/ROI is therefore blank.",
      flag="DS-F05"),
    F("K17", "Do we have opening lines for every season?",
      "dataset", "2019-2026 only (nflverse initial_lines); earlier seasons have closing prices only.",
      "Pinned nfldata commit; the coverage table on the Data page shows the exact counts.",
      "DS-GAMES"),
    # ------------------------------------------------------- known unknowns
    F("K18", "Which players were injured *during* games?",
      "blank", "",
      "The weekly injury report is a pre-game document. In-game injuries are not in it, and no "
      "official in-game injury feed is available to this project, so in-game attrition is not "
      "modelled.",
      flag="DS-F06"),
    F("K19", "Is a club's win-loss record on the injury page a final record?",
      "blank", "",
      "No. Opening the 2025 week-9 page on 2026-11-12 showed records that differ from final 2025 "
      "records (e.g. 8-9 next to Baltimore), so the page's record column is point-in-time. Not used "
      "in any calculation here.",
      flag="DS-F07"),
    F("K20", "Is the nflverse injury data identical to the official report?",
      "blank", "",
      "Unknown. The dataset is an independent transcription; it has not been reconciled against "
      "the official pages for any season. Spot checks are published; agreement is not claimed.",
      flag="DS-F08"),
    F("K21", "Do we know the reward budget for the leaderboard?",
      "blank", "",
      "No funded reward terms exist. The leaderboard is a scoring competition with published "
      "pass/fail gates; no money is promised or modelled.",
      flag="DS-F09"),
    F("K22", "Do we have enough history to test a prop strategy?",
      "blank", "",
      "No. Without dated licensed prop prices there is no price to bet against, so a prop strategy "
      "cannot be evaluated; only the line-side (over/under) difficulty can be measured from stats.",
      flag="DS-F05"),
)

BY_ID = {f.id: f for f in FACTS}


def by_status(status: str) -> list[Fact]:
    return [f for f in FACTS if f.status == status]


def counts() -> dict[str, int]:
    return {s: len(by_status(s)) for s in ("official", "reproduced", "dataset", "blank")}


if __name__ == "__main__":  # pragma: no cover
    print(counts())
    for f in FACTS:
        print(f"{f.id} [{f.status:<10}] {f.question}")
