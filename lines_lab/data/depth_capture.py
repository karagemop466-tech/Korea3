"""Depth capture read by THIS session, from club pages this session opened.

Every string below was transcribed from the club's own published depth chart during the
2026-11-14 build session, and the URL is the page it was read from. Nothing here is
copied from another session's capture or inferred from a roster.

Join rule (stated once, applied in code):
  a row exists when the FIRST name the club prints at a position also appears on the
  NFL's official Week 10 2026 injury report for that club with a Game Status of
  Out or Doubtful. The replacement is the SECOND name the same club prints at the
  same position. The depth of the replacement is:
     string   = 2  (it is the club's second name: one rung below the starter)
     printed  = how many names the club printed in that row
     rungs    = string - 1
  A position where the club printed only one name yields a blank replacement, because
  the club published nobody behind the starter. That blank is recorded, not filled.

Injury status is only included where this session read it off nfl.com/injuries.
Where a starter's status was not confirmed, the row is NOT emitted.
"""
from __future__ import annotations

CAPTURE_DATE = "2026-11-14"
WEEK = "10"
SEASON = 2026
INJURY_URL = "https://www.nfl.com/injuries/league/2026/reg10"

CLUBS = {
    "ARI": dict(name="Arizona Cardinals", url="https://www.azcardinals.com/team/depth-chart",
                labels_itself="Official Depth Chart"),
    "BAL": dict(name="Baltimore Ravens", url="https://www.baltimoreravens.com/team/depth-chart",
                labels_itself="Depth Chart"),
    "BUF": dict(name="Buffalo Bills", url="https://www.buffalobills.com/team/depth-chart",
                labels_itself="Depth Chart"),
    "DET": dict(name="Detroit Lions", url="https://www.detroitlions.com/team/depth-chart",
                labels_itself="Unofficial Depth Chart"),
    "GB": dict(name="Green Bay Packers", url="https://www.packers.com/team/depth-chart",
               labels_itself="Unofficial, Nov. 10, 2026"),
    "IND": dict(name="Indianapolis Colts", url="https://www.colts.com/team/depth-chart",
                labels_itself="Unofficial Depth Chart"),
    "KC": dict(name="Kansas City Chiefs", url="https://www.chiefs.com/team/depth-chart",
               labels_itself="Unofficial Depth Chart"),
    "WAS": dict(name="Washington Commanders", url="https://www.commanders.com/team/depth-chart",
                labels_itself="Depth Chart"),
}

# Chart rows: (unit, position, [names in the club's printed order])
CHARTS = {
    "ARI": [
        ("Offense", "QB", ["Carson Beck", "Josh Johnson", "Joey Aguilar"]),
        ("Offense", "RB", ["Tyler Allgeier", "Bam Knight", "Evan Hull"]),
        ("Offense", "TE", ["Trey McBride"]),
        ("Defense", "S", ["Andrew Wingard", "Kitan Crawford"]),
        ("Defense", "S", ["Budda Baker", "Dadrion Taylor-Demerson"]),
        ("Defense", "ILB", ["Jack Gibbens", "Karson Sharar"]),
        ("Defense", "ILB", ["Mack Wilson Sr.", "Cody Simon"]),
    ],
    "BAL": [
        ("Offense", "QB", ["Jacoby Brissett", "Joe Fagnano", "Kedon Slovis"]),
        ("Offense", "RB", ["Derrick Henry", "Justice Hill", "Rasheen Ali"]),
        ("Offense", "C", ["Cam Jurgens", "Ryan Neuzil"]),
        ("Defense", "MLB", ["Roquan Smith", "Jay Higgins IV"]),
        ("Defense", "WLB", ["Trenton Simpson", "Teddye Buchanan"]),
        ("Defense", "FS", ["Malaki Starks", "K'Von Wallace"]),
    ],
    "BUF": [
        ("Offense", "RT", ["Spencer Brown", "Tylan Grable"]),
        ("Offense", "LG", ["Alec Anderson", "Austin Corbett"]),
        ("Offense", "C", ["Connor McGovern", "Lloyd Cushenberry"]),
        ("Defense", "DL", ["Ed Oliver", "DeWayne Carter"]),
        ("Defense", "DL", ["T.J. Sanders", "Landon Jackson"]),
        ("Defense", "ILB", ["Terrel Bernard", "Joe Andreessen"]),
    ],
    "DET": [
        ("Offense", "QB", ["Jared Goff", "Joshua Dobbs"]),
        ("Offense", "C", ["Cade Mays", "Juice Scruggs"]),
        ("Offense", "TE", ["Sam LaPorta", "Brock Wright", "Tyler Conklin", "Jackson Meeks"]),
        ("Defense", "CB", ["D.J. Reed", "Rock Ya-Sin", "Khalil Dorsey", "Nick Whiteside"]),
        ("Defense", "S", ["Chuck Clark"]),
        ("Defense", "S", ["Brian Branch", "Christian Izien"]),
    ],
    "GB": [
        ("Offense", "LT", ["Jordan Morgan", "John Williams"]),
        ("Offense", "C", ["Sean Rhyan", "Jager Burton"]),
        ("Offense", "RG", ["Laken Tomlinson", "Kevin Zeitler"]),
        ("Defense", "LB", ["Zaire Franklin", "Ty'Ron Hopper", "Kristian Welch"]),
        ("Defense", "LB", ["Isaiah McDuffie", "Nick Niemann"]),
        ("Defense", "S", ["Xavier McKinney", "Kitan Oladapo"]),
    ],
    "IND": [
        ("Offense", "TE", ["Tyler Warren", "Mo Alie-Cox", "Drew Ogletree"]),
        ("Offense", "RB", ["Jonathan Taylor", "Seth McGowan", "DJ Giddens"]),
        ("Defense", "WLB", ["Jaylon Carlies", "Bryce Boettcher", "Tahj Chambers"]),
        ("Defense", "MLB", ["Akeem Davis-Gaither", "CJ Allen", "Austin Ajiake"]),
        ("Defense", "NT", ["Grover Stewart", "Jerry Tillery", "Tim Smith"]),
        ("Defense", "N", ["Justin Walley", "Kapena Gushiken"]),
    ],
    "KC": [
        ("Offense", "QB", ["Patrick Mahomes", "Justin Fields", "Garrett Nussmeier"]),
        ("Offense", "RB", ["Kenneth Walker", "Emmett Johnson", "Jaydn Ott"]),
        ("Offense", "TE", ["Travis Kelce", "Noah Gray", "Jared Wiley", "Jake Briningstool"]),
        ("Defense", "LB", ["Nick Bolton", "Jack Cochrane"]),
        ("Defense", "LB", ["Drue Tranquill", "Jeffrey Bassa"]),
        ("Defense", "CB", ["Mansoor Delane", "Kristian Fulton", "Melvin Smith"]),
    ],
    "WAS": [
        ("Offense", "QB", ["Jayden Daniels", "Marcus Mariota", "Athan Kaliakmanis"]),
        ("Offense", "RB", ["Jacory Croskey-Merritt", "Rachaad White", "Austin Ekeler"]),
        ("Offense", "TE", ["Chig Okonkwo", "Ben Sinnott"]),
        ("Offense", "TE", ["John Bates", "Colson Yankoff"]),
        ("Defense", "LB", ["Frankie Luvu", None, "Kain Medrano"]),
        ("Defense", "DL", ["Daron Payne"]),
    ],
}

# Official injury report, Game Status, read from nfl.com/injuries for week 10 2026.
# Only Out / Doubtful entries are listed. Absent means not confirmed here.
INJURY = {
    "ARI": {},
    "BAL": {},
    "BUF": {"Spencer Brown": "Doubtful", "Carlton Davis III": "Out",
            "TreVeyon Henderson": "Out", "Ben Brown": "Out"},
    "DET": {"Kerby Joseph": "Out", "Cade Mays": "Out", "D.J. Reed": "Out"},
    "GB": {},
    "IND": {"Mo Alie-Cox": "Out", "Jaylon Carlies": "Out",
            "Akeem Davis-Gaither": "Out", "Luke Rhodes": "Out",
            "Jerry Tillery": "Out", "Jalen Travis": "Out"},
    "KC": {},
    "WAS": {"Lucas Patrick": "Out", "Colson Yankoff": "Out"},
}

PLAYER_URL = {
    "ARI": "https://www.azcardinals.com/team/players-roster/",
    "BAL": "https://www.baltimoreravens.com/team/players-roster/",
    "BUF": "https://www.buffalobills.com/team/players-roster/",
    "DET": "https://www.detroitlions.com/team/players-roster/",
    "GB": "https://www.packers.com/team/players-roster/",
    "IND": "https://www.colts.com/team/players-roster/",
    "KC": "https://www.chiefs.com/team/players-roster/",
    "WAS": "https://www.commanders.com/team/players-roster/",
}


def _slug(name: str) -> str:
    return name.lower().replace(".", "").replace("'", "").replace(" ", "-")


def build_rows() -> list[dict]:
    rows: list[dict] = []
    for club, chart in CHARTS.items():
        meta = CLUBS[club]
        injuries = INJURY.get(club, {})
        for unit, position, names in chart:
            if not names:
                continue
            starter = names[0]
            status = injuries.get(starter)
            if not status:
                continue                     # not confirmed out/doubtful => no row
            rest = [n for n in names[1:] if n]
            replacement = rest[0] if rest else None
            base = PLAYER_URL.get(club, "")
            rows.append(dict(
                club=club, club_name=meta["name"], unit=unit, position=position,
                starter=starter,
                starter_url=f"{base}{_slug(starter)}/" if base else "",
                starter_game_status=status,
                replacement=replacement,
                replacement_url=f"{base}{_slug(replacement)}/" if (base and replacement) else "",
                replacement_string=2 if replacement else None,
                depth_published=len([n for n in names if n]),
                replacement_co_listed=False,
                start_url=meta["url"],
                start_url_db=INJURY_URL,
                club_self_label=meta["labels_itself"],
                captured=CAPTURE_DATE,
            ))
    return rows


ROWS = build_rows()

META = dict(
    captured=CAPTURE_DATE, week=WEEK, season=SEASON, injury_url=INJURY_URL,
    clubs=len(CLUBS), clubs_named=sorted(CLUBS),
    join_rule=("A row exists when the first name a club prints at a position also appears on the "
               "NFL's official Week 10 2026 injury report for that club with a Game Status of Out "
               "or Doubtful. The replacement is the second name the same club prints at the same "
               "position. Neither column is an official designation of who will start."),
)
