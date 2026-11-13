#!/usr/bin/env python3
"""Cross-capture audit: this lab's parse versus the repository's earlier injury transcription.

    python3 -m injury_lab.transcribe

`decision_lab/data/injuries.json` is the only earlier transcription of the same official Week 10 2026
injury report anywhere in this repository. It was captured 2026-11-12 from the same URL this lab captured
on 2026-11-13, and it is committed, so it is auditable - but it retained no raw page text, which is the
whole reason this lab exists.

Comparing the two is the strongest check available on the parser, and it separates three things that a
single capture cannot tell apart:

* **agree** - the same row, the same fields, two captures, two days.
* **designation appeared** - the row is in both captures, but only one of them shows a game status.
  Because the earlier session split its rows into "designated" and "blank on the page", a row it filed as
  blank and this capture shows as Out is evidence the *page* changed, not that a parser missed something.
* **one-sided** - a row in only one capture. This lab does not call that a correction: the earlier session
  read a different set of chunks, so absence is uninformative, and saying so is the point.

Nothing here infers a cause when the data does not show one.
"""
from __future__ import annotations

import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EARLIER = ROOT / "decision_lab" / "data" / "injuries.json"

def codes_by_name() -> dict[str, str]:
    """Printed club name -> club code, read off the report's own fixture headers.

    The earlier transcription keys its rows by code and this lab's parser keys rows by the name the page
    prints, so a crosswalk is needed. It is taken from the pages themselves - each fixture header prints
    both - rather than from a table this lab invents, and a row whose club name is not in the crosswalk is
    reported, never guessed.
    """
    caps = json.loads((HERE / "data" / "captures.json").read_text(encoding="utf-8"))
    out: dict[str, str] = {}
    for cap in caps["captures"]:
        for fx in cap["fixtures"]:
            for c in fx["clubs"]:
                out.setdefault(c["name"], c["code"])
    return out


def norm(name: str) -> str:
    """Whitespace and punctuation only. Suffixes are kept: 'Carlton Davis III' is not 'Carlton Davis'."""
    return " ".join((name or "").replace("\xa0", " ").split()).strip()


def key(player: str, club: str) -> tuple[str, str]:
    return (club, norm(player).lower())


def load_mine() -> tuple[list[dict], list[str]]:
    caps = json.loads((HERE / "data" / "captures.json").read_text(encoding="utf-8"))
    xwalk = codes_by_name()
    out, unmapped = [], []
    for r in caps["injury_rows"]:
        if r["season"] != 2026 or r["week"] != 10:
            continue
        club = xwalk.get(r["club"], "")
        if not club:
            unmapped.append(r["club"])
        out.append({
            "club_code": club or r["club"], "club_name": r["club"], "player": norm(r["player"]),
            "position": r["position_code"], "injury": norm(r["injury_text"]),
            "practice_status": norm(r["practice_status"]), "game_status": norm(r["game_status"]),
            "player_url": r["player_url"], "fixture": f'{r["away"]}@{r["home"]}',
            "capture": "injury_lab/raw/2026-reg10-injuries.md", "retrieved": "2026-11-13",
        })
    return out, unmapped


def load_theirs() -> tuple[list[dict], str]:
    inj = json.loads(EARLIER.read_text(encoding="utf-8"))
    rows = []
    for bucket, kind in (("designations", "designated"), ("practice_participation", "blank-on-page")):
        for r in inj[bucket]["rows"]:
            rows.append({
                "club_code": r["team"], "club_name": r.get("team_name", ""), "player": norm(r["player"]),
                "position": r.get("position", ""), "injury": norm(r.get("injury", "")),
                "practice_status": norm(r.get("practice_status", "")),
                "game_status": norm(r.get("game_status", "")),
                "player_url": r.get("player_url", ""), "bucket": bucket, "kind": kind,
            })
    return rows, inj["captured_utc"]


def main() -> int:
    mine, unmapped_names = load_mine()
    theirs, theirs_date = load_theirs()

    t_index = {key(r["player"], r["club_code"]): r for r in theirs}
    m_index = {key(r["player"], r["club_code"]): r for r in mine}
    shared_clubs = sorted({r["club_code"] for r in mine} & {r["club_code"] for r in theirs})

    agree, changed, designation_appeared, only_mine, only_theirs = [], [], [], [], []
    for k, m in sorted(m_index.items()):
        t = t_index.get(k)
        if t is None:
            only_mine.append({k2: m[k2] for k2 in
                              ("club_code", "player", "position", "injury", "practice_status", "game_status")}
                             | {"why": "no row for this player in the earlier file; that file covers "
                                       f'{len(theirs)} rows across {len({r["club_code"] for r in theirs})} '
                                       "clubs and does not retain raw text, so absence here is not "
                                       "evidence of absence on the page"})
            continue
        same = all(m[f] == t[f] for f in ("position", "injury", "practice_status", "game_status", "player_url"))
        rec = {"club_code": m["club_code"], "player": m["player"], "fields_compared": 5,
               "mine": {f: m[f] for f in ("position", "injury", "practice_status", "game_status")},
               "theirs": {f: t[f] for f in ("position", "injury", "practice_status", "game_status")},
               "earlier_bucket": t["bucket"]}
        if same:
            agree.append(rec)
        elif not t["game_status"] and m["game_status"]:
            rec["what_changed"] = ("the earlier capture filed this row as blank-on-the-page and this one "
                                   "shows a designation")
            designation_appeared.append(rec)
        else:
            rec["what_changed"] = "at least one compared field differs; see the two values side by side"
            changed.append(rec)
    for k, t in sorted(t_index.items()):
        if k not in m_index and t["game_status"]:
            only_theirs.append({"club_code": t["club_code"], "player": t["player"],
                                "game_status": t["game_status"], "injury": t["injury"],
                                "why": "designated in the earlier capture, no row in this one; this "
                                       "capture is chunk-truncated (flag H04), so this is a gap in "
                                       "retrieval, not a contradiction"})

    field_counts: dict[str, int] = {"position": 0, "injury": 0, "practice_status": 0, "game_status": 0,
                                    "player_url": 0}
    for m in mine:
        t = t_index.get(key(m["player"], m["club_code"]))
        if t is None:
            continue
        for f in field_counts:
            if m[f] != t[f]:
                field_counts[f] += 1

    fixture_diff = []
    inj = json.loads(EARLIER.read_text(encoding="utf-8"))
    caps = json.loads((HERE / "data" / "captures.json").read_text(encoding="utf-8"))
    for g in inj["games"]:
        if not (g["away"] in {m["club_code"] for m in mine} and g["home"] in {m["club_code"] for m in mine}):
            continue
        for cap in caps["captures"]:
            for fx in cap["fixtures"]:
                codes = [c["code"] for c in fx["clubs"]]
                if len(codes) != 2 or set(codes) != {g["away"], g["home"]}:
                    continue
                for i, side in enumerate(("away", "home")):
                    mine_rec = fx["records"][i] if i < len(fx["records"]) else ""
                    theirs_rec = g[f"{side}_record"]
                    if mine_rec != theirs_rec:
                        fixture_diff.append({
                            "fixture": f'{g["away"]}@{g["home"]}', "club": codes[i], "field": f"{side} record",
                            "earlier": theirs_rec, "this_capture": mine_rec,
                            "note": "records as printed on the report; the two captures are one day apart "
                                    "and this fixture was played between them. This lab publishes the "
                                    "difference and the dates, and does not state a result - neither "
                                    "capture contains one",
                        })

    out = {
        "_comment": [
            "Generated by injury_lab/transcribe.py - do not hand-edit.",
            "Two captures of the same official URL, one day apart. 'agree' is a check on this lab's parser;",
            "'designation_appeared' is a finding about the source: the same fixture carries different inputs",
            "depending on the day you read it. Neither is evidence about football outcomes.",
        ],
        "this_capture": {"retrieved_utc": "2026-11-13", "rows_2026_w10": len(mine),
                         "file": "injury_lab/data/captures.json"},
        "earlier_capture": {"retrieved_utc": theirs_date, "rows": len(theirs),
                            "file": "decision_lab/data/injuries.json",
                            "retained_raw_text": False,
                            "consequence": "the earlier rows can be compared but not re-verified against a "
                                           "page capture, because none was retained"},
        "clubs_in_both_captures": shared_clubs,
        "rows_compared": len(m_index),
        "club_names_with_no_code_on_the_page": sorted(set(unmapped_names)),
        "agree_field_for_field": agree,
        "designation_appeared_after_the_earlier_capture": designation_appeared,
        "other_field_differences": changed,
        "only_in_this_capture": only_mine,
        "designated_only_in_the_earlier_capture": only_theirs,
        "fixture_level_differences": fixture_diff,
        "field_level_counts": field_counts,
        "reading_of_the_differences": {
            "what_is_certain": "two records of one URL, one day apart, differ on "
                               f'{len(designation_appeared) + len(changed)} of {len(m_index)} rows; only '
                               "this lab's version can be re-checked against retained page text",
            "reading_a_the_page_changed": "the report is updated through the week, so the cells that "
                                          "carry a designation and an injury on the later day were blank on "
                                          "the earlier one. This is the reading the earlier file's own "
                                          "split supports: a row it filed under practice_participation is a "
                                          "row it saw with both the Injuries and Game Status cells blank.",
            "reading_b_the_earlier_split_differs": "the earlier transcription bucketed these rows by hand "
                                                   "and a designation was missed. It cannot be excluded, "
                                                   "because that session retained no raw page text - which "
                                                   "is the argument for retention, not an accusation.",
            "what_would_separate_them": "a second dated capture of the same URL in one week, retained as "
                                        "raw text, or the official practice-schedule page naming the day "
                                        "designations are published. Registered as question Q23.",
        },
        "counts": {
            "agree": len(agree), "designation_appeared": len(designation_appeared),
            "other_differences": len(changed), "only_in_this_capture": len(only_mine),
            "designated_only_in_earlier": len(only_theirs),
            "rows_in_common": len(agree) + len(designation_appeared) + len(changed),
        },
    }
    (HERE / "data" / "transcribe_diff.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    c = out["counts"]
    print(f"rows in common {c['rows_in_common']}: {c['agree']} agree field for field, "
          f"{c['designation_appeared']} gained a designation between captures, {c['other_differences']} other "
          f"differences; {c['only_in_this_capture']} rows only in this capture, "
          f"{c['designated_only_in_earlier']} designated only in the earlier one; "
          f"{len(fixture_diff)} fixture-level differences")
    for r in designation_appeared:
        print(f"  designation appeared: {r['club_code']} {r['player']} -> {r['mine']['game_status']}"
              f" (earlier: practice '{r['theirs']['practice_status']}', no designation)")
    for r in changed:
        print(f"  field difference: {r['club_code']} {r['player']} mine={r['mine']} theirs={r['theirs']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
