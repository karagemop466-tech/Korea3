"""Decision gates and the repository review findings.

A decision gate is a bundle of questions that must be answered before a class of work may
be implemented.  Gates are evaluated here; a gate is ``closed`` unless every question it
depends on is a non-blank fact in :mod:`decision_system.knowledge`.

The review findings are the "flag any irregularities" part of the brief, checked against
the files themselves rather than assumed.  Each finding records what was checked, how, and
what a reviewer should do about it.  Findings are never deleted: a resolved finding keeps
its id and gains a resolution.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import knowledge, suggestions

ROOT = Path(__file__).resolve().parents[1]


GATES: tuple[dict, ...] = (
    {"id": "G1", "name": "Implement any new strategy",
     "needs": ["K21"],
     "rule": "A strategy may only be scored by the leaderboard if its hypothesis was frozen "
             "before its backtest. Without that, the family size is unknown and every p-value "
             "and deflated Sharpe figure is uninterpretable.",
     "owner": "repository owner"},
    {"id": "G2", "name": "Publish any player-prop edge or ROI",
     "needs": ["K15", "K16", "K22"],
     "rule": "A prop number requires a dated licensed price and the operator's settlement rule "
             "for a non-starter. Neither exists, so prop edges and ROIs stay blank.",
     "owner": "repository owner + licensed data"},
    {"id": "G3", "name": "Claim an official depth chart, or a 2nd/3rd/4th string label",
     "needs": ["K06"],
     "rule": "The string labels used here are derived from snap rank, not an official depth "
             "chart, because no official numbered depth chart was found. Any page that shows a "
     "string label must show that caveat on the same row.",
     "owner": "repository owner"},
    {"id": "G4", "name": "Use roster/inactive mechanics (48 active, 90-minute list) in a model",
     "needs": ["K08"],
     "rule": "The mechanics are blank until an official operations page is opened and quoted.",
     "owner": "repository owner"},
    {"id": "G5", "name": "Treat the injury dataset as authoritative",
     "needs": ["K20"],
     "rule": "It is a transcription and has not been reconciled. Measuring with it is fine; "
             "calling it official is not.",
     "owner": "repository owner"},
    {"id": "G6", "name": "Pay or promise a reward",
     "needs": ["K21"],
     "rule": "No budget exists. A rules page may define entry criteria; it may not imply money.",
     "owner": "repository owner"},
    {"id": "G7", "name": "Model in-game injury effects",
     "needs": ["K18"],
     "rule": "The pre-game report cannot see an in-game injury; the effect is unmeasured.",
     "owner": "repository owner"},
    {"id": "G8", "name": "Quote a club record from the injury page as final",
     "needs": ["K19"],
     "rule": "The record column is point-in-time; it is not used in any calculation.",
     "owner": "repository owner"},
)


def gate_status() -> list[dict]:
    rows = []
    for g in GATES:
        facts = [knowledge.BY_ID[k] for k in g["needs"] if k in knowledge.BY_ID]
        open_q = [f.id for f in facts if f.status == "blank"]
        rows.append({
            **g,
            "open_questions": open_q,
            "state": "open" if open_q else "closed",
            "scoreable_work_blocked": len(open_q),
        })
    return rows


# ------------------------------------------------------------------ review findings
FINDINGS: tuple[dict, ...] = (
    {"id": "DS-F01", "severity": "medium", "area": "depth charts",
     "finding": "No official numbered NFL depth chart was located. nfl.com/teams/kansas-city-chiefs/"
                "depth-chart returns a 404 page ('404 - Flag on the Play').",
     "checked": "Opened the club depth-chart route on 2026-11-12 and read the response.",
     "source": "https://www.nfl.com/teams/kansas-city-chiefs/depth-chart",
     "action": "Every string label on this site says 'derived from snap rank, unofficial'. If a "
               "reviewer has an official depth source, it replaces the proxy."},
    {"id": "DS-F02", "severity": "low", "area": "roster mechanics",
     "finding": "The 48-active / 90-minute-inactive mechanics are not published on this site "
                "because the official page was not opened in this session.",
     "checked": "Searched for an official operations page; found only secondary explainers.",
     "source": "https://operations.nfl.com/",
     "action": "Read and quote the official rulebook clause (suggestion SG03), then close the gap."},
    {"id": "DS-F03", "severity": "medium", "area": "operator settlement",
     "finding": "Two DraftKings help-centre articles return only 'Loading...' to a server-side "
                "fetch (same-game parlay definition, non-starter settlement). Their content could "
                "not be read, so they are cited for nothing.",
     "checked": "Fetched both article URLs directly; the body is rendered client-side.",
     "source": "https://support.draftkings.com/dk/en-us/what-is-a-same-game-parlay-sgp-bet",
     "action": "Do not use either article as evidence until it can be read in a browser and "
               "quoted. Correlation is supported only by the operator's parlays FAQ."},
    {"id": "DS-F04", "severity": "low", "area": "literature",
     "finding": "A peer-reviewed reference on quarterback injury value was located (PMC3496575) "
                "but its text was not read, so it supports no claim.",
     "checked": "Located the record; did not read the article.",
     "source": "https://pmc.ncbi.nlm.nih.gov/articles/PMC3496575/",
     "action": "Read it before citing it; until then it is a candidate reference only."},
    {"id": "DS-F05", "severity": "high", "area": "player props",
     "finding": "No licensed player-prop price exists in the repository or in a reachable source, "
                "so prop edges, prop ROIs and prop-combo results are blank.",
     "checked": "Searched the repository and the settled-bets file for prop markets.",
     "source": "https://support.draftkings.com/dk/en-us/what-is-a-prop-bet",
     "action": "Obtain dated licensed prop prices (SG01) or keep the section blank."},
    {"id": "DS-F06", "severity": "medium", "area": "injuries",
     "finding": "In-game injuries are invisible to this project: the official report is pre-game "
                "and no in-game injury feed is available.",
     "checked": "Read the report columns; they carry practice and game status only.",
     "source": "https://www.nfl.com/injuries/",
     "action": "Model attrition from participation data (SG09) before claiming any in-game effect."},
    {"id": "DS-F07", "severity": "medium", "area": "official page content",
     "finding": "The win-loss record beside a club on the injury page is the record at publication "
                "time, not the final record. The 2025 week-9 page read on 2026-11-12 shows 8-9 "
                "beside a club whose season had 18 weeks.",
     "checked": "Compared the record printed on the page with the season length.",
     "source": "https://www.nfl.com/injuries/league/2025/reg9",
     "action": "Never quote that column as a final record; it is not used in any calculation here."},
    {"id": "DS-F08", "severity": "high", "area": "dataset integrity",
     "finding": "The injury dataset is an independent transcription and has not been reconciled "
                "with the official report for any season-week.",
     "checked": "Read the publisher documentation and the file schema; no reconciliation exists.",
     "source": "https://github.com/nflverse/nflverse-data/releases/tag/injuries",
     "action": "Reconcile a sample and publish the agreement rate (SG02)."},
    {"id": "DS-F09", "severity": "high", "area": "competition",
     "finding": "No reward budget, eligibility rule or forfeiture rule exists, so 'top performing "
                "strategy' is undefined and no reward can be earned.",
     "checked": "Searched the repository for any funded terms.",
     "source": "https://github.com/karagemop466-tech/Korea3",
     "action": "Set the budget and the forward period, then publish the rules (SG15)."},
    {"id": "DS-F10", "severity": "medium", "area": "data provenance",
     "finding": "A prior session's combined player-stats + snap-count file is used nowhere in this "
                "build. It comes from a third-party repository (DevinOgrady/NFL-Player-Projections) "
                "with no publisher documentation, and an undocumented mirror cannot stand in for a "
                "pinned nflverse release.",
     "checked": "Traced the file to session-398c4b58/scripts/fetch_data.py and read its manifest.",
     "source": "https://github.com/karagemop466-tech/Korea3/blob/main/session-398c4b58/scripts/fetch_data.py",
     "action": "Use only the pinned nflverse releases. If a player-level fallback is ever needed, "
               "it must be documented and flagged at the point of use."},
    {"id": "DS-F11", "severity": "medium", "area": "published numbers",
     "finding": "Two published sample-size figures disagreed: an earlier page reports about 6,200 "
                "settled bets to detect a 3% edge, this build's default two-sided convention gives "
                "7,953. The difference is the one-sided vs two-sided convention, not an error, but "
                "publishing one number without the convention invites a false contradiction.",
     "checked": "Recomputed both conventions from the same formula and standard deviation.",
     "source": "https://www.itl.nist.gov/div898/handbook/prc/section4/prc47.htm",
     "action": "Both conventions are now printed side by side (6,264 one-sided / 7,953 two-sided)."},
    {"id": "DS-F12", "severity": "low", "area": "repository hygiene",
     "finding": "Six dashboards are served from one GitHub Pages root, each with its own navigation "
                "and its own idea of 'current'.",
     "checked": "Listed the HTML directories served by the Pages branch deploy.",
     "source": "https://github.com/karagemop466-tech/Korea3",
     "action": "Owner decides the canonical dashboard (SG14). Nothing is deleted."},
)


def findings_with_links() -> list[dict]:
    return [dict(f) for f in FINDINGS]


def summary() -> dict:
    gates = gate_status()
    by_sev: dict[str, int] = {}
    for f in FINDINGS:
        by_sev[f["severity"]] = by_sev.get(f["severity"], 0) + 1
    return {
        "gates": len(gates),
        "gates_open": sum(1 for g in gates if g["state"] == "open"),
        "gates_closed": sum(1 for g in gates if g["state"] == "closed"),
        "findings": len(FINDINGS),
        "by_severity": by_sev,
        "suggestions": len(suggestions.SUGGESTIONS),
        "suggestions_blocked": sum(1 for s in suggestions.SUGGESTIONS if s.status == "blocked"),
        "knowledge": knowledge.counts(),
    }


if __name__ == "__main__":  # pragma: no cover
    print(json.dumps(summary(), indent=1))
