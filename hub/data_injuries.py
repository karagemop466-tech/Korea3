#!/usr/bin/env python3
"""Official injury / availability / roster-move snapshot, transcribed by hand.

Every row below was read from the official NFL.com Week 10 2026 injury report that
this session opened on 2026-11-12:

    https://www.nfl.com/injuries/league/2026/reg10

Nothing is inferred. Where the official table shows no game status, the field is
empty here and is rendered blank ("not designated") rather than guessed. Where a
club is not present on the official page, the club is recorded as absent -- never
as injury-free.

The `verify()` function fails the build if a transcribed value is not one of the
official status strings, if a club code is unknown, or if a (club, player) pair is
duplicated. Run it directly:

    python3 hub/data_injuries.py
"""
from __future__ import annotations

import json
from pathlib import Path

HUB = Path(__file__).resolve().parent
ROOT = HUB.parent

SNAPSHOT = "2026-11-12"
SOURCE_URL = "https://www.nfl.com/injuries/league/2026/reg10"
LIVE_URL = "https://www.nfl.com/injuries/"
POLICY_URL = "https://www.nfl.com/news/competition-committee-approves-revisions-to-injury-report-0ap3000000688693"

PRACTICE_FULL = "Full Participation in Practice"
PRACTICE_LIMITED = "Limited Participation in Practice"
PRACTICE_DNP = "Did Not Participate In Practice"
PRACTICE_ALLOWED = (PRACTICE_FULL, PRACTICE_LIMITED, PRACTICE_DNP)
GAME_ALLOWED = ("Out", "Doubtful", "Questionable", "")

# Club code -> official club name, exactly as printed beside the table on the page.
CLUBS = {
    "WAS": "Commanders", "NYG": "Giants", "NE": "Patriots", "DET": "Lions",
    "KC": "Chiefs", "ATL": "Falcons", "MIN": "Vikings", "GB": "Packers",
    "JAX": "Jaguars", "TEN": "Titans", "BUF": "Bills", "NYJ": "Jets",
    "MIA": "Dolphins", "IND": "Colts", "CAR": "Panthers", "NO": "Saints",
    "HOU": "Texans", "CLE": "Browns", "LAR": "Rams", "AZ": "Cardinals",
    "SEA": "Seahawks", "LV": "Raiders", "SF": "49ers", "DAL": "Cowboys",
    "PIT": "Steelers", "CIN": "Bengals", "LAC": "Chargers", "BAL": "Ravens",
    "CHI": "Bears", "DEN": "Broncos", "PHI": "Eagles", "TB": "Buccaneers",
}

# Clubs that appear on the Week 10 page with the literal text "No Injuries Reported".
NO_INJURIES_REPORTED = ("SEA", "CIN", "LAC", "BAL")

# Clubs that do not appear on the Week 10 page at all. Recorded as absent, not healthy.
ABSENT_FROM_PAGE = ("CHI", "DEN", "PHI", "TB")

# (club, player, position, injury, practice status, game status)
# Transcribed row by row from the official page. Empty year = the cell was empty.
PLAYERS = [
    # ---- Washington Commanders ----
    ("WAS", "John Bates", "TE", "", PRACTICE_FULL, ""),
    ("WAS", "Treylon Burks", "WR", "", PRACTICE_DNP, ""),
    ("WAS", "Jayden Daniels", "QB", "", PRACTICE_FULL, ""),
    ("WAS", "Matt Gulbin", "C", "", PRACTICE_FULL, ""),
    ("WAS", "Chig Okonkwo", "TE", "", PRACTICE_FULL, ""),
    ("WAS", "Lucas Patrick", "C", "Concussion", PRACTICE_DNP, "Out"),
    ("WAS", "Amik Robertson", "CB", "", PRACTICE_LIMITED, ""),
    ("WAS", "Shy Tuttle", "DT", "", PRACTICE_FULL, ""),
    ("WAS", "Colson Yankoff", "TE", "Knee", PRACTICE_DNP, "Out"),
    # ---- New York Giants ----
    ("NYG", "Abdul Carter", "LB", "", PRACTICE_FULL, ""),
    ("NYG", "Jermaine Eluemunor", "T", "", PRACTICE_FULL, ""),
    ("NYG", "Malik Harrison", "LB", "Groin", PRACTICE_LIMITED, "Questionable"),
    ("NYG", "Colton Hood", "CB", "", PRACTICE_FULL, ""),
    ("NYG", "Theo Johnson", "TE", "", PRACTICE_FULL, ""),
    ("NYG", "Charlie Jones", "WR", "", PRACTICE_FULL, ""),
    ("NYG", "J.J. McCarthy", "QB", "", PRACTICE_FULL, ""),
    ("NYG", "Darnell Mooney", "WR", "", PRACTICE_FULL, ""),
    ("NYG", "Malik Nabers", "WR", "", PRACTICE_FULL, ""),
    ("NYG", "Cam Skattebo", "RB", "", PRACTICE_FULL, ""),
    ("NYG", "Andrew Thomas", "T", "", PRACTICE_FULL, ""),
    # ---- New England Patriots ----
    ("NE", "Ben Brown", "C", "Knee", PRACTICE_DNP, "Out"),
    ("NE", "A.J. Brown", "WR", "", PRACTICE_LIMITED, ""),
    ("NE", "Kevin Byard", "S", "", PRACTICE_LIMITED, ""),
    ("NE", "Carlton Davis III", "CB", "Knee", PRACTICE_DNP, "Out"),
    ("NE", "Reggie Gilliam", "FB", "", PRACTICE_LIMITED, ""),
    ("NE", "TreVeyon Henderson", "RB", "Illness", PRACTICE_DNP, "Out"),
    ("NE", "Hunter Henry", "TE", "", PRACTICE_LIMITED, ""),
    ("NE", "Cameron Latu", "TE", "", PRACTICE_DNP, ""),
    ("NE", "Drake Maye", "QB", "", PRACTICE_FULL, ""),
    ("NE", "Morgan Moses", "T", "", PRACTICE_LIMITED, ""),
    ("NE", "Walter Rouse", "T", "", PRACTICE_DNP, ""),
    ("NE", "Brenden Schooler", "S", "", PRACTICE_DNP, ""),
    ("NE", "Rhamondre Stevenson", "RB", "", PRACTICE_DNP, ""),
    ("NE", "Greg Van Roten", "G", "", PRACTICE_LIMITED, ""),
    ("NE", "Charles Woods", "CB", "", PRACTICE_LIMITED, ""),
    # ---- Detroit Lions ----
    ("DET", "Brian Branch", "S", "", PRACTICE_LIMITED, ""),
    ("DET", "Jared Goff", "QB", "", PRACTICE_LIMITED, ""),
    ("DET", "Kerby Joseph", "S", "", PRACTICE_LIMITED, ""),
    ("DET", "Cade Mays", "C", "", PRACTICE_DNP, ""),
    ("DET", "D.J. Reed", "CB", "", PRACTICE_DNP, ""),
    ("DET", "Jacob Saylors", "RB", "", PRACTICE_FULL, ""),
    ("DET", "Amon-Ra St. Brown", "WR", "", PRACTICE_LIMITED, ""),
    ("DET", "Sione Vaki", "RB", "", PRACTICE_DNP, ""),
    ("DET", "DJ Wonnum", "DE", "", PRACTICE_FULL, ""),
    # ---- Kansas City Chiefs ----
    ("KC", "Jeffrey Bassa", "LB", "", PRACTICE_FULL, ""),
    ("KC", "Mansoor Delane", "CB", "", PRACTICE_FULL, ""),
    ("KC", "Justin Fields", "QB", "", PRACTICE_FULL, ""),
    ("KC", "Jaden Hicks", "S", "", PRACTICE_FULL, ""),
    ("KC", "Travis Kelce", "TE", "", PRACTICE_FULL, ""),
    ("KC", "Patrick Mahomes", "QB", "", PRACTICE_FULL, ""),
    ("KC", "Jaylon Moore", "T", "", PRACTICE_DNP, ""),
    ("KC", "Omarr Norman-Lott", "DT", "", PRACTICE_LIMITED, ""),
    ("KC", "Rashee Rice", "WR", "", PRACTICE_FULL, ""),
    ("KC", "Peter Woods", "DT", "", PRACTICE_DNP, ""),
    ("KC", "Xavier Worthy", "WR", "", PRACTICE_FULL, ""),
    # ---- Atlanta Falcons ----
    ("ATL", "Zachariah Branch", "WR", "", PRACTICE_DNP, ""),
    ("ATL", "Divine Deablo", "LB", "", PRACTICE_LIMITED, ""),
    ("ATL", "Gervon Dexter Sr.", "DT", "", PRACTICE_DNP, ""),
    ("ATL", "James Pearce Jr.", "DE", "", PRACTICE_DNP, ""),
    ("ATL", "Za'Darius Smith", "DE", "", PRACTICE_DNP, ""),
    ("ATL", "Josh Woods", "LB", "", PRACTICE_DNP, ""),
    # ---- Minnesota Vikings ----
    ("MIN", "Blake Cashman", "LB", "", PRACTICE_DNP, ""),
    ("MIN", "T.J. Hockenson", "TE", "", PRACTICE_DNP, ""),
    ("MIN", "Tyrion Ingram-Dawkins", "DT", "", PRACTICE_DNP, ""),
    ("MIN", "Theo Jackson", "S", "", PRACTICE_FULL, ""),
    ("MIN", "Jauan Jennings", "WR", "", PRACTICE_DNP, ""),
    ("MIN", "Kyler Murray", "QB", "", PRACTICE_DNP, ""),
    ("MIN", "Kyle Van Noy", "LB", "", PRACTICE_DNP, ""),
    ("MIN", "Jay Ward", "S", "", PRACTICE_LIMITED, ""),
    ("MIN", "Carson Wentz", "QB", "", PRACTICE_LIMITED, ""),
    # ---- Green Bay Packers ----
    ("GB", "Aaron Banks", "G", "", PRACTICE_LIMITED, ""),
    ("GB", "Chris Brooks", "RB", "", PRACTICE_LIMITED, ""),
    ("GB", "Javon Bullard", "S", "", PRACTICE_DNP, ""),
    ("GB", "Zaire Franklin", "LB", "", PRACTICE_DNP, ""),
    ("GB", "Travis Glover", "G", "", PRACTICE_LIMITED, ""),
    ("GB", "Ty'Ron Hopper", "LB", "", PRACTICE_LIMITED, ""),
    ("GB", "Josh Jacobs", "RB", "", PRACTICE_DNP, ""),
    ("GB", "Bo Melton", "WR", "", PRACTICE_FULL, ""),
    ("GB", "Skyy Moore", "WR", "", PRACTICE_LIMITED, ""),
    ("GB", "Micah Parsons", "LB", "", PRACTICE_LIMITED, ""),
    ("GB", "Sean Rhyan", "C", "", PRACTICE_DNP, ""),
    ("GB", "Trey Smack", "K", "", PRACTICE_LIMITED, ""),
    ("GB", "Lukas Van Ness", "LB", "", PRACTICE_DNP, ""),
    ("GB", "Josh Whyle", "TE", "", PRACTICE_DNP, ""),
    ("GB", "Savion Williams", "WR", "", PRACTICE_LIMITED, ""),
    ("GB", "Kevin Zeitler", "G", "", PRACTICE_LIMITED, ""),
    # ---- Jacksonville Jaguars ----
    ("JAX", "Jessie Bates", "S", "", PRACTICE_DNP, ""),
    ("JAX", "Ezra Cleveland", "G", "", PRACTICE_LIMITED, ""),
    ("JAX", "Branson Combs", "LB", "", PRACTICE_LIMITED, ""),
    ("JAX", "Jordan Davis", "DT", "", PRACTICE_DNP, ""),
    ("JAX", "Robert Hainsey", "C", "", PRACTICE_LIMITED, ""),
    ("JAX", "Antonio Johnson", "S", "", PRACTICE_LIMITED, ""),
    ("JAX", "Jakobi Meyers", "WR", "", PRACTICE_DNP, ""),
    ("JAX", "Chris Rodriguez Jr.", "RB", "", PRACTICE_LIMITED, ""),
    ("JAX", "Bhayshul Tuten", "RB", "", PRACTICE_DNP, ""),
    ("JAX", "Travon Walker", "DE", "", PRACTICE_DNP, ""),
    # ---- Tennessee Titans ----
    ("TEN", "Cody Barton", "LB", "", PRACTICE_DNP, ""),
    ("TEN", "John Franklin-Myers", "DE", "", PRACTICE_FULL, ""),
    ("TEN", "Marcus Harris", "CB", "", PRACTICE_FULL, ""),
    ("TEN", "Anthony Hill Jr.", "LB", "", PRACTICE_DNP, ""),
    ("TEN", "Jaylon Jones", "CB", "", PRACTICE_FULL, ""),
    ("TEN", "JC Latham", "T", "", PRACTICE_FULL, ""),
    ("TEN", "Tony Pollard", "RB", "", PRACTICE_FULL, ""),
    ("TEN", "Peter Skoronski", "G", "", PRACTICE_DNP, ""),
    ("TEN", "Tyjae Spears", "RB", "", PRACTICE_DNP, ""),
    ("TEN", "Carnell Tate", "WR", "", PRACTICE_DNP, ""),
    ("TEN", "Tommy Townsend", "P", "", PRACTICE_FULL, ""),
    ("TEN", "Kevin Winston Jr.", "S", "", PRACTICE_FULL, ""),
    # ---- Buffalo Bills ----
    ("BUF", "Alec Anderson", "G", "", PRACTICE_LIMITED, ""),
    ("BUF", "Christian Benford", "CB", "", PRACTICE_LIMITED, ""),
    ("BUF", "Spencer Brown", "T", "", PRACTICE_LIMITED, ""),
    ("BUF", "Dion Dawkins", "T", "", PRACTICE_LIMITED, ""),
    ("BUF", "Greg Gaines", "DT", "", PRACTICE_FULL, ""),
    ("BUF", "Jordan Hancock", "CB", "", PRACTICE_FULL, ""),
    ("BUF", "Dalton Kincaid", "TE", "", PRACTICE_LIMITED, ""),
    ("BUF", "Connor McGovern", "C", "", PRACTICE_LIMITED, ""),
    ("BUF", "Ar'maj Reed-Adams", "G", "", PRACTICE_FULL, ""),
    ("BUF", "T.J. Sanders", "DE", "", PRACTICE_FULL, ""),
    ("BUF", "Tyrell Shavers", "WR", "", PRACTICE_FULL, ""),
    # ---- New York Jets ----
    ("NYJ", "Omar Cooper Jr.", "WR", "", PRACTICE_LIMITED, ""),
    ("NYJ", "Joseph Ossai", "DE", "", PRACTICE_LIMITED, ""),
    ("NYJ", "VJ Payne", "S", "", PRACTICE_FULL, ""),
    ("NYJ", "Harrison Phillips", "DT", "", PRACTICE_DNP, ""),
    ("NYJ", "Trevin Wallace", "LB", "", PRACTICE_DNP, ""),
    ("NYJ", "Garrett Wilson", "WR", "", PRACTICE_LIMITED, ""),
    ("NYJ", "Nahshon Wright", "CB", "", PRACTICE_LIMITED, ""),
    # ---- Miami Dolphins ----
    ("MIA", "Tucker Addington", "LS", "", PRACTICE_LIMITED, ""),
    ("MIA", "Kaytron Allen", "RB", "", PRACTICE_FULL, ""),
    ("MIA", "Darrell Baker Jr.", "CB", "", PRACTICE_LIMITED, ""),
    ("MIA", "Chris Bell", "WR", "", PRACTICE_LIMITED, ""),
    ("MIA", "Aaron Brewer", "C", "", PRACTICE_DNP, ""),
    ("MIA", "Malik Herring", "DE", "", PRACTICE_LIMITED, ""),
    ("MIA", "Will Kacmarek", "TE", "", PRACTICE_DNP, ""),
    ("MIA", "Michael Taaffe", "S", "", PRACTICE_FULL, ""),
    ("MIA", "Dante Trader Jr.", "S", "", PRACTICE_FULL, ""),
    ("MIA", "Jaylen Wright", "RB", "", PRACTICE_FULL, ""),
    # ---- Indianapolis Colts ----
    ("IND", "Mo Alie-Cox", "TE", "", PRACTICE_DNP, ""),
    ("IND", "Jaylon Carlies", "LB", "", PRACTICE_DNP, ""),
    ("IND", "Akeem Davis-Gaither", "LB", "", PRACTICE_DNP, ""),
    ("IND", "A.J. Haulcy", "S", "", PRACTICE_DNP, ""),
    ("IND", "Arden Key", "DE", "", PRACTICE_FULL, ""),
    ("IND", "Luke Rhodes", "LS", "", PRACTICE_DNP, ""),
    ("IND", "Jonathan Taylor", "RB", "", PRACTICE_LIMITED, ""),
    ("IND", "Jerry Tillery", "DT", "", PRACTICE_LIMITED, ""),
    ("IND", "Jalen Travis", "T", "", PRACTICE_DNP, ""),
    ("IND", "Justin Walley", "CB", "", PRACTICE_FULL, ""),
    ("IND", "Charvarius Ward", "CB", "", PRACTICE_DNP, ""),
    # ---- Carolina Panthers ----
    ("CAR", "Jonathon Brooks", "RB", "", PRACTICE_FULL, ""),
    ("CAR", "Brady Christensen", "G", "", PRACTICE_FULL, ""),
    ("CAR", "Trevor Etienne", "RB", "", PRACTICE_FULL, ""),
    ("CAR", "Chuba Hubbard", "RB", "", PRACTICE_DNP, ""),
    ("CAR", "Lee Hunter", "DT", "", PRACTICE_FULL, ""),
    ("CAR", "Mike Jackson", "CB", "", PRACTICE_FULL, ""),
    ("CAR", "Will Lee III", "CB", "", PRACTICE_FULL, ""),
    ("CAR", "Xavier Legette", "WR", "", PRACTICE_FULL, ""),
    ("CAR", "Damien Lewis", "G", "", PRACTICE_FULL, ""),
    ("CAR", "Bobby Okereke", "LB", "", PRACTICE_DNP, ""),
    ("CAR", "Jaelan Phillips", "LB", "", PRACTICE_FULL, ""),
    ("CAR", "Torricelli Simpkins III", "G", "", PRACTICE_FULL, ""),
    # ---- New Orleans Saints ----
    ("NO", "Kelvin Banks Jr.", "T", "", PRACTICE_LIMITED, ""),
    ("NO", "CJ Donaldson", "RB", "", PRACTICE_DNP, ""),
    ("NO", "David Edwards", "G", "", PRACTICE_LIMITED, ""),
    ("NO", "Martin Emerson", "CB", "", PRACTICE_LIMITED, ""),
    ("NO", "Travis Etienne", "RB", "", PRACTICE_LIMITED, ""),
    ("NO", "Noah Fant", "TE", "", PRACTICE_LIMITED, ""),
    ("NO", "Alvin Kamara", "RB", "", PRACTICE_DNP, ""),
    ("NO", "Erik McCoy", "C", "", PRACTICE_DNP, ""),
    ("NO", "Christen Miller", "DT", "", PRACTICE_LIMITED, ""),
    ("NO", "Asim Richards", "T", "", PRACTICE_FULL, ""),
    # ---- Houston Texans ----
    ("HOU", "Azeez Al-Shaair", "LB", "", PRACTICE_DNP, ""),
    ("HOU", "Reed Blankenship", "S", "", PRACTICE_LIMITED, ""),
    ("HOU", "Tank Dell", "WR", "", PRACTICE_LIMITED, ""),
    ("HOU", "Blake Fisher", "T", "", PRACTICE_FULL, ""),
    ("HOU", "Marvin Harrison Jr.", "WR", "", PRACTICE_LIMITED, ""),
    ("HOU", "Jacob Hummel", "LB", "", PRACTICE_LIMITED, ""),
    ("HOU", "Brevin Jordan", "TE", "", PRACTICE_DNP, ""),
    ("HOU", "Woody Marks", "RB", "", PRACTICE_LIMITED, ""),
    ("HOU", "David Montgomery", "RB", "", PRACTICE_DNP, ""),
    ("HOU", "Keylan Rutledge", "G", "", PRACTICE_DNP, ""),
    ("HOU", "Jaylin Smith", "CB", "", PRACTICE_LIMITED, ""),
    ("HOU", "Wyatt Teller", "G", "", PRACTICE_LIMITED, ""),
    ("HOU", "Tommy Togiai", "DT", "", PRACTICE_FULL, ""),
    # ---- Cleveland Browns ----
    ("CLE", "Austin Barber", "T", "", PRACTICE_LIMITED, ""),
    ("CLE", "Denzel Boston", "WR", "", PRACTICE_DNP, ""),
    ("CLE", "Michael Burton", "FB", "", PRACTICE_DNP, ""),
    ("CLE", "Maliek Collins", "DT", "", PRACTICE_LIMITED, ""),
    ("CLE", "Harold Fannin Jr.", "TE", "", PRACTICE_LIMITED, ""),
    ("CLE", "Ronnie Hickman Jr.", "S", "", PRACTICE_DNP, ""),
    ("CLE", "Tytus Howard", "T", "", PRACTICE_LIMITED, ""),
    ("CLE", "Elgton Jenkins", "C", "", PRACTICE_DNP, ""),
    ("CLE", "Carson Schwesinger", "LB", "", PRACTICE_LIMITED, ""),
    ("CLE", "Denzel Ward", "CB", "", PRACTICE_LIMITED, ""),
    ("CLE", "Quincy Williams", "LB", "", PRACTICE_LIMITED, ""),
    # ---- Los Angeles Rams ----
    ("LAR", "Davis Allen", "TE", "", PRACTICE_LIMITED, ""),
    ("LAR", "Steve Avila", "G", "", PRACTICE_DNP, ""),
    ("LAR", "Joe Cardona", "LS", "", PRACTICE_LIMITED, ""),
    ("LAR", "Kam Curl", "S", "", PRACTICE_DNP, ""),
    ("LAR", "Terrance Ferguson", "TE", "", PRACTICE_DNP, ""),
    ("LAR", "Myles Garrett", "LB", "", PRACTICE_LIMITED, ""),
    ("LAR", "Trent McDuffie", "CB", "", PRACTICE_DNP, ""),
    ("LAR", "Puka Nacua", "WR", "", PRACTICE_DNP, ""),
    ("LAR", "Colby Parkinson", "TE", "", PRACTICE_LIMITED, ""),
    ("LAR", "Matthew Stafford", "QB", "", PRACTICE_FULL, ""),
    # ---- Arizona Cardinals ----
    ("AZ", "Budda Baker", "S", "", PRACTICE_DNP, ""),
    ("AZ", "Zachary Carter", "DT", "", PRACTICE_LIMITED, ""),
    ("AZ", "Hjalte Froholdt", "C", "", PRACTICE_DNP, ""),
    ("AZ", "Jon Gaines II", "G", "", PRACTICE_DNP, ""),
    ("AZ", "Bam Knight", "RB", "", PRACTICE_LIMITED, ""),
    ("AZ", "Hunter Long", "TE", "", PRACTICE_LIMITED, ""),
    ("AZ", "Roy Lopez", "DT", "", PRACTICE_DNP, ""),
    ("AZ", "Max Melton", "CB", "", PRACTICE_LIMITED, ""),
    ("AZ", "Isaac Seumalo", "G", "", PRACTICE_DNP, ""),
    ("AZ", "Dante Stills", "DT", "", PRACTICE_LIMITED, ""),
    ("AZ", "Josh Sweat", "LB", "", PRACTICE_DNP, ""),
    ("AZ", "Jayden Williams", "T", "", PRACTICE_LIMITED, ""),
    ("AZ", "Mack Wilson", "LB", "", PRACTICE_DNP, ""),
    # ---- Seattle Seahawks: "No Injuries Reported" ----
    # ---- Las Vegas Raiders ----
    ("LV", "Thomas Booker", "DT", "", PRACTICE_LIMITED, ""),
    ("LV", "Foley Fatukasi", "DT", "", PRACTICE_LIMITED, ""),
    ("LV", "Ian Thomas", "TE", "", PRACTICE_FULL, ""),
    ("LV", "Trey Zuhn III", "C", "", PRACTICE_LIMITED, ""),
    # ---- San Francisco 49ers ----
    ("SF", "Mike Evans", "WR", "", PRACTICE_DNP, ""),
    ("SF", "Renardo Green", "CB", "", PRACTICE_DNP, ""),
    ("SF", "Nate Hobbs", "CB", "", PRACTICE_FULL, ""),
    ("SF", "Deommodore Lenoir", "CB", "", PRACTICE_DNP, ""),
    ("SF", "Siran Neal", "S", "", PRACTICE_LIMITED, ""),
    ("SF", "Demarcus Robinson", "WR", "", PRACTICE_FULL, ""),
    ("SF", "Deebo Samuel Sr.", "WR", "", PRACTICE_LIMITED, ""),
    ("SF", "Upton Stout", "CB", "", PRACTICE_LIMITED, ""),
    ("SF", "C.J. West", "DT", "", PRACTICE_LIMITED, ""),
    ("SF", "Trent Williams", "T", "", PRACTICE_DNP, ""),
    # ---- Dallas Cowboys ----
    ("DAL", "Jonathan Bullard", "DT", "", PRACTICE_FULL, ""),
    ("DAL", "Donovan Ezeiruaku", "LB", "", PRACTICE_DNP, ""),
    ("DAL", "Jake Ferguson", "TE", "", PRACTICE_DNP, ""),
    ("DAL", "Tyler Goodson", "RB", "", PRACTICE_DNP, ""),
    ("DAL", "Malik Hooker", "S", "", PRACTICE_DNP, ""),
    ("DAL", "Marist Liufau", "LB", "", PRACTICE_FULL, ""),
    ("DAL", "P.J. Locke", "S", "", PRACTICE_DNP, ""),
    ("DAL", "Von Miller", "LB", "", PRACTICE_DNP, ""),
    ("DAL", "Jonathan Mingo", "WR", "", PRACTICE_DNP, ""),
    ("DAL", "Devin Moore", "CB", "", PRACTICE_FULL, ""),
    ("DAL", "DeMarvion Overshown", "LB", "", PRACTICE_LIMITED, ""),
    ("DAL", "George Pickens", "WR", "", PRACTICE_LIMITED, ""),
    ("DAL", "Joey Porter Jr.", "CB", "", PRACTICE_DNP, ""),
    ("DAL", "Luke Schoonmaker", "TE", "", PRACTICE_FULL, ""),
    ("DAL", "Brevyn Spann-Ford", "TE", "", PRACTICE_FULL, ""),
    ("DAL", "KaVontae Turpin", "WR", "", PRACTICE_LIMITED, ""),
    # ---- Pittsburgh Steelers ----
    ("PIT", "Brandin Echols", "CB", "", PRACTICE_FULL, ""),
    ("PIT", "DeShon Elliott", "S", "", PRACTICE_LIMITED, ""),
    ("PIT", "Derrick Harmon", "DT", "", PRACTICE_LIMITED, ""),
    ("PIT", "Cameron Heyward", "DT", "", PRACTICE_DNP, ""),
    ("PIT", "Ben Skowronek", "WR", "", PRACTICE_FULL, ""),
    ("PIT", "Doneiko Slaughter", "CB", "", PRACTICE_FULL, ""),
    ("PIT", "Darnell Washington", "TE", "", PRACTICE_DNP, ""),
    ("PIT", "T.J. Watt", "LB", "", PRACTICE_DNP, ""),
    # ---- Cincinnati Bengals: "No Injuries Reported" ----
    # ---- Los Angeles Chargers: "No Injuries Reported" ----
    # ---- Baltimore Ravens: "No Injuries Reported" ----
]

# Official roster/reserve moves, transcribed from the durable monthly pages.
RESERVE_LIST_URL = "https://www.nfl.com/transactions/league/reserve-list/2026/11"
RESERVE_MOVES = [
    ("11/10", "LA", "Jordan Whittington", "Reserve/Injured"),
    ("11/10", "MIA", "Zach Sieler", "Reserve/Injured"),
    ("11/10", "MIA", "Malik Willis", "Reserve/Injured"),
    ("11/10", "SF", "Gracen Halton", "Reserve/Injured"),
    ("11/10", "AZ", "Gardner Minshew", "Reserve/Injured"),
    ("11/10", "AZ", "Michael Wilson", "Reserve/Injured"),
    ("11/09", "TEN", "James Williams", "Reserve/Injured"),
    ("11/09", "MIN", "Demond Claiborne", "Reserve/Injured"),
    ("11/09", "BUF", "Josh Palmer", "Reserve/Injured"),
    ("11/07", "ATL", "Brian Robinson", "Reserve/Injured"),
    ("11/07", "LA", "Jaylen Watson", "Reserve/Injured"),
    ("11/07", "DEN", "Eyioma Uwazurike", "Reserve/Injured"),
    ("11/07", "DET", "Jack Campbell", "Reserve/Injured"),
    ("11/07", "DAL", "Malachi Lawrence", "Reserve/Injured"),
    ("11/07", "WAS", "Dyami Brown", "Reserve/Injured"),
    ("11/07", "SF", "Christian Kirk", "Reserve/Injured"),
    ("11/05", "CHI", "Zavier Scott", "Reserve/Injured"),
]

TRADES_URL = "https://www.nfl.com/transactions/league/trades/2026/11"
TRADES = [
    ("11/10", "ATL", "JAX", "Jessie Bates"),
    ("11/10", "PHI", "JAX", "Jordan Davis"),
    ("11/10", "TEN", "BUF", "Amani Hooker"),
    ("11/10", "IND", "SF", "Keenan Allen"),
    ("11/10", "LV", "MIN", "Kirk Cousins"),
    ("11/10", "LAC", "DEN", "Daiyan Henley"),
    ("11/10", "IND", "KC", "Josh Downs"),
    ("11/10", "ATL", "BAL", "Ryan Neuzil"),
    ("11/10", "BAL", "ATL", "Andrew Vorhees"),
    ("11/09", "NYJ", "DET", "Andre Cisco"),
    ("11/09", "NO", "JAX", "Davon Godchaux"),
    ("11/06", "AZ", "BAL", "Jacoby Brissett"),
]

# Position -> unit. Used only for grouping; it is a football-convention mapping,
# not an NFL publication, and is declared as such on the page.
POSITION_UNIT = {
    "QB": "Offense", "RB": "Offense", "FB": "Offense", "WR": "Offense", "TE": "Offense",
    "T": "Offense", "G": "Offense", "C": "Offense", "OT": "Offense", "OL": "Offense",
    "DT": "Defense", "NT": "Defense", "DE": "Defense", "LB": "Defense",
    "OLB": "Defense", "ILB": "Defense", "CB": "Defense", "S": "Defense",
    "SAF": "Defense", "DB": "Defense",
    "K": "Special teams", "P": "Special teams", "LS": "Special teams",
}
POSITION_GROUP = {
    "QB": "Quarterback", "RB": "Backfield", "FB": "Backfield",
    "WR": "Receivers", "TE": "Receivers",
    "T": "Offensive line", "G": "Offensive line", "C": "Offensive line",
    "OT": "Offensive line", "OL": "Offensive line",
    "DT": "Defensive front", "NT": "Defensive front", "DE": "Defensive front",
    "LB": "Linebackers", "OLB": "Linebackers", "ILB": "Linebackers",
    "CB": "Secondary", "S": "Secondary", "SAF": "Secondary", "DB": "Secondary",
    "K": "Specialists", "P": "Specialists", "LS": "Specialists",
}

# ---------------------------------------------------------------------------
# Declared, disclosed weighting used for the availability-stress index.
# These numbers are THIS REPOSITORY'S publishing convention, not an NFL metric.
# They are shown on the page next to every index so the arithmetic is checkable.
# ---------------------------------------------------------------------------
GAME_WEIGHT = {"Out": 3, "Doubtful": 2, "Questionable": 1, "": 0}
PRACTICE_WEIGHT = {PRACTICE_DNP: 2, PRACTICE_LIMITED: 1, PRACTICE_FULL: 0}


def stress(player) -> int:
    """Declared 0-5 score. Out+DNP = 5, full practice with no designation = 0."""
    return GAME_WEIGHT[player[5]] + PRACTICE_WEIGHT[player[4]]


def verify() -> None:
    errors = []
    seen = set()
    for p in PLAYERS:
        club, name, pos, _inj, practice, game = p
        if club not in CLUBS:
            errors.append(f"unknown club {club} for {name}")
        if practice not in PRACTICE_ALLOWED:
            errors.append(f"practice status not official: {practice!r} ({club} {name})")
        if game not in GAME_ALLOWED:
            errors.append(f"game status not official: {game!r} ({club} {name})")
        if pos not in POSITION_UNIT:
            errors.append(f"position has no unit mapping: {pos!r} ({club} {name})")
        key = (club, name)
        if key in seen:
            errors.append(f"duplicate row {key}")
        seen.add(key)
        if len(p) != 6:
            errors.append(f"row shape {p!r}")
    clubs_with_rows = {p[0] for p in PLAYERS}
    for club in NO_INJURIES_REPORTED:
        if club in clubs_with_rows:
            errors.append(f"{club} is marked 'No Injuries Reported' but has rows")
    for club in ABSENT_FROM_PAGE:
        if club in clubs_with_rows:
            errors.append(f"{club} is marked absent but has rows")
    if errors:
        raise SystemExit("transcription check FAILED:\n  " + "\n  ".join(errors))
    print(f"transcription check OK: {len(PLAYERS)} players, "
          f"{len(clubs_with_rows)} clubs with rows, "
          f"{len(NO_INJURIES_REPORTED)} clubs 'no injuries reported', "
          f"{len(ABSENT_FROM_PAGE)} clubs absent from the page")


def club_summary() -> list[dict]:
    out = []
    for club in sorted(CLUBS):
        rows = [p for p in PLAYERS if p[0] == club]
        if not rows:
            out.append({
                "club": club, "name": CLUBS[club], "listed": 0,
                "out": 0, "doubtful": 0, "questionable": 0,
                "dnp": 0, "limited": 0, "full": 0, "stress": 0,
                "off_stress": 0, "def_stress": 0, "st_stress": 0,
                "page_state": ("no injuries reported" if club in NO_INJURIES_REPORTED
                               else "absent from page" if club in ABSENT_FROM_PAGE
                               else "no rows"),
            })
            continue
        out.append({
            "club": club, "name": CLUBS[club], "listed": len(rows),
            "out": sum(1 for p in rows if p[5] == "Out"),
            "doubtful": sum(1 for p in rows if p[5] == "Doubtful"),
            "questionable": sum(1 for p in rows if p[5] == "Questionable"),
            "dnp": sum(1 for p in rows if p[4] == PRACTICE_DNP),
            "limited": sum(1 for p in rows if p[4] == PRACTICE_LIMITED),
            "full": sum(1 for p in rows if p[4] == PRACTICE_FULL),
            "stress": sum(stress(p) for p in rows),
            "off_stress": sum(stress(p) for p in rows if POSITION_UNIT[p[2]] == "Offense"),
            "def_stress": sum(stress(p) for p in rows if POSITION_UNIT[p[2]] == "Defense"),
            "st_stress": sum(stress(p) for p in rows if POSITION_UNIT[p[2]] == "Special teams"),
            "page_state": "listed",
        })
    return out


def position_summary() -> list[dict]:
    rows = []
    for group in ("Quarterback", "Backfield", "Receivers", "Offensive line",
                  "Defensive front", "Linebackers", "Secondary", "Specialists"):
        members = [p for p in PLAYERS if POSITION_GROUP[p[2]] == group]
        rows.append({
            "group": group,
            "unit": POSITION_UNIT[members[0][2]] if members else "",
            "listed": len(members),
            "out": sum(1 for p in members if p[5] == "Out"),
            "doubtful": sum(1 for p in members if p[5] == "Doubtful"),
            "questionable": sum(1 for p in members if p[5] == "Questionable"),
            "dnp": sum(1 for p in members if p[4] == PRACTICE_DNP),
            "stress": sum(stress(p) for p in members),
            "positions": ", ".join(sorted({p[2] for p in members})),
        })
    return rows


def build() -> dict:
    verify()
    payload = {
        "snapshot_utc": SNAPSHOT,
        "season": 2026,
        "week": 10,
        "source_url": SOURCE_URL,
        "live_url": LIVE_URL,
        "policy_url": POLICY_URL,
        "clubs_total": len(CLUBS),
        "clubs_listed": len({p[0] for p in PLAYERS}),
        "clubs_no_injuries_reported": list(NO_INJURIES_REPORTED),
        "clubs_absent_from_page": list(ABSENT_FROM_PAGE),
        "players_listed": len(PLAYERS),
        "counts": {
            "out": sum(1 for p in PLAYERS if p[5] == "Out"),
            "doubtful": sum(1 for p in PLAYERS if p[5] == "Doubtful"),
            "questionable": sum(1 for p in PLAYERS if p[5] == "Questionable"),
            "not_designated": sum(1 for p in PLAYERS if p[5] == ""),
            "dnp": sum(1 for p in PLAYERS if p[4] == PRACTICE_DNP),
            "limited": sum(1 for p in PLAYERS if p[4] == PRACTICE_LIMITED),
            "full": sum(1 for p in PLAYERS if p[4] == PRACTICE_FULL),
            "injury_named": sum(1 for p in PLAYERS if p[3]),
        },
        "weights": {"game": GAME_WEIGHT, "practice": PRACTICE_WEIGHT},
        "players": [
            {"club": p[0], "club_name": CLUBS[p[0]], "player": p[1], "position": p[2],
             "injury": p[3], "practice": p[4], "game": p[5], "stress": stress(p),
             "unit": POSITION_UNIT[p[2]], "group": POSITION_GROUP[p[2]]}
            for p in PLAYERS
        ],
        "clubs": club_summary(),
        "positions": position_summary(),
        "reserve_list_url": RESERVE_LIST_URL,
        "reserve_moves": [
            {"date": d, "club": c, "player": n, "transaction": t} for d, c, n, t in RESERVE_MOVES
        ],
        "trades_url": TRADES_URL,
        "trades": [
            {"date": d, "from": f, "to": t, "player": n} for d, f, t, n in TRADES
        ],
    }
    (HUB / "data" / "injuries.json").write_text(
        json.dumps(payload, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return payload


if __name__ == "__main__":
    data = build()
    print(f"wrote hub/data/injuries.json: {data['players_listed']} players, "
          f"{len(data['clubs'])} clubs, {len(data['reserve_moves'])} reserve moves, "
          f"{len(data['trades'])} trades")
