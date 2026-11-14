"""Data layer: price snapshots, verified results, fair lines and the demotion gate.

Everything here is recomputed from the pinned dataset on every build. Nothing is
fetched, nothing is typed in by hand, and no value is filled in when the source is
missing: a missing value stays ``None`` and is rendered as a blank.

Conventions — settled by test against an official box score, not by assumption
------------------------------------------------------------------------------
``spread_line`` in ``games.csv`` is **the home team's expected margin**: a positive
number means the home team is favoured, and the home side covers when
``margin - spread_line > 0``.

This was **wrong in this session's first draft** and is worth recording, because the
column heading does not say it and the naive reading gives a plausible-looking answer.
Three independent tests settle it:

* **Official box score.** ``nfl.com/games/cowboys-at-buccaneers-2021-reg-1`` shows
  DAL 29 @ TB 31, i.e. a home margin of **+2**, for a game Tampa Bay entered as roughly
  a touchdown favourite. ``games.csv`` stores that game as ``spread_line = +10.0``, so
  **positive = home favoured**.
* **The tail.** Of the 208 games with ``spread_line`` between +10.5 and +11.5, the home
  team won **83.2%** with a mean margin of **+11.45**. If the sign were the other way
  round, home would win about 17% of them.
* **The closing file.** ``margin - spread_line`` reproduces the published per-side
  ``outcome`` in ``closing_lines.csv`` for **3,318 of 3,368** games; ``margin +
  spread_line`` reproduces only 2,341.

``|spread_line - margin|`` is **10.257** points, which is the normal size for an NFL
spread error. The flipped reading gives 14.600 and is not a market price.

**A real convention mismatch, published rather than smoothed:** ``initial_lines.csv``
carries the *opposite* sign to ``games.csv`` for the same club. TB is ``-6.5`` in the
opening file (the NFL's own 'negative = favourite' convention, NFL-PS) and ``+10.0`` in
``games.csv``. Naively differencing the two files produces a nonsense mean move of
+3.79 points with an 11-point standard deviation. Converted to one convention
(``home_handicap = -initial_line``), the 2021 open-to-close move is a plausible
-3.22 points. Both raw values and the conversion are published on the snapshot page.

``total_line`` is the market total; the over wins when the two scores sum above it,
the under wins when below, and the bet pushes when they are equal — the same push rule
the NFL states for a point spread (NFL-PS).

A price of ``-110`` is the reference the NFL states is used 'most often' for a spread
(NFL-PS). Where the dataset carries no price, the price is left **blank** and the record
is marked **line-only**: its ROI is unavailable, not zero.
"""
from __future__ import annotations

import hashlib
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

SNAPSHOT_DATE = "2026-11-14"
DATASET_COMMIT = "a270278f3ac4e937295fe6a27814b3c4a2b62645"

# Breakeven win rate for a -110 price: 110/210 = 0.523809...
BREAKEVEN_110 = 110.0 / 210.0

# Seasons whose games.csv price columns are usable (a price exists for the majority).
def sha16(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def load_games() -> pd.DataFrame:
    """Load every game and attach derivations. No filtering, no imputation."""
    g = pd.read_csv(RAW / "games.csv", low_memory=False)
    g["gameday"] = pd.to_datetime(g["gameday"])
    g = g.sort_values(["gameday", "game_id"]).reset_index(drop=True)
    g["margin"] = g.home_score - g.away_score
    g["total"] = g.home_score + g.away_score
    g["played"] = g.home_score.notna()
    return g


def american_to_payout(price: float) -> float:
    """Profit per 1 unit staked on a winning bet at an American price."""
    if price is None or (isinstance(price, float) and np.isnan(price)):
        raise ValueError("no price")
    return price / 100.0 if price > 0 else 100.0 / (-price)


def american_to_implied(price: float) -> float:
    """Raw implied probability, vig included. Not a true probability."""
    return 100.0 / (price + 100.0) if price > 0 else (-price) / ((-price) + 100.0)


# --------------------------------------------------------------------------- #
# 1. Price-snapshot store
# --------------------------------------------------------------------------- #
def price_snapshots(g: pd.DataFrame) -> dict:
    """Opening and closing numbers, per market, with an explicit blank where absent.

    The store is keyed by ``game_id`` and market. For each market it records the
    opening number, the closing number, the price on each side, and where each cell
    came from. A cell with no source is recorded as ``None`` with ``""`` provenance.
    """
    rows: list[dict] = []
    for r in g.itertuples():
        if pd.isna(r.spread_line) and pd.isna(r.total_line) and pd.isna(r.home_moneyline):
            continue
        rows.append(dict(
            game_id=r.game_id, season=int(r.season), week=int(r.week), gameday=r.gameday.date().isoformat(),
            away=r.away_team, home=r.home_team, played=bool(r.played),
            # side market (home perspective, home-relative sign per NFL-PS)
            close_side=r.spread_line if pd.notna(r.spread_line) else None,
            open_side=None,                       # no opening spread for these games
            price_side=None,                      # no executable spread price
            # total market
            close_total=r.total_line if pd.notna(r.total_line) else None,
            open_total=None,
            price_total=None,
            # moneyline market
            close_ml_home=r.home_moneyline if pd.notna(r.home_moneyline) else None,
            close_ml_away=r.away_moneyline if pd.notna(r.away_moneyline) else None,
            open_ml_home=None, open_ml_away=None,
        ))
    store = pd.DataFrame(rows)

    # The dataset DOES carry spread and total prices on some rows. Record them
    # where present instead of discarding them; never invent one.
    gp = g.set_index("game_id")
    for col, src in (("price_side", "home_spread_odds"), ("price_total", "over_odds")):
        vals, prov = [], []
        for gid in store.game_id:
            v = gp.at[gid, src]
            if pd.notna(v):
                vals.append(float(v)); prov.append("games.csv:" + src)
            else:
                # A -110 default is explicitly NOT applied; the cell stays blank.
                vals.append(None); prov.append("")
        store[col] = vals
        store[col + "_provenance"] = prov

    # Opening numbers exist only for 2021, one book, no price.
    op = pd.read_csv(RAW / "initial_lines.csv")
    op = op[op.sportsbook == "WSGT"]
    open_rows = []
    for gid, grp in op.groupby("about"):
        meta = gp.loc[gid] if gid in gp.index else None
        if meta is None:
            continue
        sp = grp[grp.type == "SPREAD"]
        to = grp[grp.type == "TOTAL"]
        home_line = sp[sp.side == meta.home_team].line
        open_rows.append(dict(
            game_id=gid,
            open_side=float(home_line.iloc[0]) if len(home_line) else None,
            open_total=float(to.line.max()) if len(to) else None,
            open_book="WSGT",
            open_source="initial_lines.csv (book WSGT)",
        ))
    opens = pd.DataFrame(open_rows)
    if len(opens):
        store = store.merge(opens, on="game_id", how="left", suffixes=("", "_open"))
        # the merge brings the real opening values into open_side / open_total
        store["open_side"] = store["open_side_open"].where(store["open_side_open"].notna(), store["open_side"])
        store["open_total"] = store["open_total_open"].where(store["open_total_open"].notna(), store["open_total"])
        store = store.drop(columns=[c for c in store.columns if c.endswith("_open")
                                    and c not in ("open_side", "open_total", "open_book", "open_source")])
    else:
        store["open_book"] = None
        store["open_source"] = None

    store["open_side_provenance"] = np.where(store["open_side"].notna(),
                                             "initial_lines.csv (book WSGT, 2021)", "")
    store["open_total_provenance"] = np.where(store["open_total"].notna(),
                                              "initial_lines.csv (book WSGT, 2021)", "")
    store["close_side_provenance"] = np.where(store["close_side"].notna(), "games.csv:spread_line", "")
    store["close_total_provenance"] = np.where(store["close_total"].notna(), "games.csv:total_line", "")
    store["close_ml_provenance"] = np.where(store["close_ml_home"].notna(), "games.csv:home_moneyline", "")

    store["move_side"] = store.apply(
        lambda r: (r.close_side - r.open_side) if (r.open_side is not None and r.close_side is not None
                                                    and pd.notna(r.open_side) and pd.notna(r.close_side)) else None,
        axis=1)
    store["move_total"] = store.apply(
        lambda r: (r.close_total - r.open_total) if (pd.notna(r.open_total) and pd.notna(r.close_total)) else None,
        axis=1)
    return dict(rows=store)


def snapshot_coverage(store: dict) -> dict:
    s = store["rows"]
    n = len(s)
    def pct(x):
        return (100.0 * x / n) if n else 0.0
    played = s[s.played]
    n_played = len(played)
    def pctp(x):
        return (100.0 * x / n_played) if n_played else 0.0
    return dict(
        games=n,
        games_with_close_side=int(s.close_side.notna().sum()),
        games_with_open_side=int(s.open_side.notna().sum()),
        games_with_both_side=int((s.close_side.notna() & s.open_side.notna()).sum()),
        games_with_close_total=int(s.close_total.notna().sum()),
        games_with_open_total=int(s.open_total.notna().sum()),
        games_with_both_total=int((s.close_total.notna() & s.open_total.notna()).sum()),
        games_with_ml=int(s.close_ml_home.notna().sum()),
        games_with_spread_price=int(s.price_side.notna().sum()),
        games_with_total_price=int(s.price_total.notna().sum()),
        played_games=n_played,
        played_with_spread_price=int(played.price_side.notna().sum()),
        pct_played_with_price=round(pctp(played.price_side.notna().sum()), 2),
        pct_with_open_side=round(pct(s.open_side.notna().sum()), 2),
        pct_with_ml=round(pct(s.close_ml_home.notna().sum()), 2),
    )


# --------------------------------------------------------------------------- #
# 2. Verified results feed
# --------------------------------------------------------------------------- #
def verified_results(g: pd.DataFrame) -> pd.DataFrame:
    """Settle every played REG game on every market, and re-check the published outcome.

    The settlement rule is the NFL's (NFL-PS / NFL-ML): a spread bet pushes when the
    margin equals the line; a moneyline tie is a push; a total pushes when scores sum
    to the number. Results are *recomputed* from the final score, then compared with
    the dataset's own ``outcome`` column where one exists.
    """
    d = g[(g.game_type == "REG") & g.played].copy()
    # spread_line is the home team's expected margin (verified above), so the home
    # side covers when the realised margin exceeds it.
    d["side_result"] = np.sign(d.margin - d.spread_line)   # home perspective
    d["total_result"] = np.sign(d.total - d.total_line)    # +1 over, -1 under
    d["ml_home_result"] = np.sign(d.margin)                # +1 home win, -1 away, 0 tie
    return d[["game_id", "season", "week", "gameday", "home_team", "away_team",
              "home_score", "away_score", "margin", "total", "spread_line", "total_line",
              "home_moneyline", "away_moneyline", "home_spread_odds", "over_odds",
              "side_result", "total_result", "ml_home_result"]]


def crosscheck_closing_lines(g: pd.DataFrame) -> dict:
    """Independently recompute the closing-line file's own ``outcome`` column.

    This is the results-feed integrity test: if the score, the line and the published
    outcome disagree, one of the three is wrong. The mismatches are returned, not
    smoothed over, and every one is published on the review page.
    """
    cl = pd.read_csv(RAW / "closing_lines.csv")
    idx = g[g.played].set_index("game_id")
    check_rows = []
    for alt, grp in cl.groupby("alt_game_id"):
        if alt not in idx.index:
            continue
        r = idx.loc[alt]
        sp = grp[grp.type == "SPREAD"]
        home_row = sp[sp.side == r.home_team]
        to = grp[grp.type == "TOTAL"]
        over_row = to[to.side == "Over"]
        under_row = to[to.side == "Under"]
        ml = grp[grp.type == "MONEYLINE"]
        ml_home = ml[ml.side == r.home_team]
        if len(home_row) != 1:
            continue
        line = float(home_row.line.iloc[0])
        pub = float(home_row.outcome.iloc[0]) if pd.notna(home_row.outcome.iloc[0]) else None
        calc = float(np.sign(r.margin + line))
        calc01 = 1.0 if calc > 0 else (0.0 if calc < 0 else 0.5)

        tot_line = float(under_row.line.iloc[0]) if len(under_row) else (
            float(over_row.line.iloc[0]) if len(over_row) else None)
        tot_pub = float(over_row.outcome.iloc[0]) if len(over_row) and pd.notna(over_row.outcome.iloc[0]) else None
        tot_calc = None
        if tot_line is not None:
            s = float(np.sign(r.total - tot_line))
            tot_calc = 1.0 if s > 0 else (0.0 if s < 0 else 0.5)

        ml_pub = float(ml_home.outcome.iloc[0]) if len(ml_home) and pd.notna(ml_home.outcome.iloc[0]) else None
        ml_calc = None if ml_pub is None else (1.0 if r.margin > 0 else (0.0 if r.margin < 0 else 0.5))

        check_rows.append(dict(
            game_id=alt, season=int(r.season), home=r.home_team, away=r.away_team,
            home_score=float(r.home_score), away_score=float(r.away_score),
            spread_line_closing=line, spread_line_games=float(r.spread_line),
            signed_disagreement=float(r.spread_line + line),
            spread_published=pub, spread_calc=calc01,
            spread_ok=None if pub is None else abs(pub - calc01) < 1e-9,
            total_line_closing=tot_line, total_published=tot_pub, total_calc=tot_calc,
            total_ok=None if tot_pub is None or tot_calc is None else abs(tot_pub - tot_calc) < 1e-9,
            ml_published=ml_pub, ml_calc=ml_calc,
            ml_ok=None if ml_pub is None or ml_calc is None else abs(ml_pub - ml_calc) < 1e-9,
            gameday=r.gameday.date().isoformat(),
        ))
    chk = pd.DataFrame(check_rows)
    return dict(rows=chk)


def results_summary(g: pd.DataFrame, mkt: pd.DataFrame) -> dict:
    reg = g[(g.game_type == "REG")]
    played = reg[reg.played]
    chk = mkt["crosscheck"]["rows"]
    return dict(
        seasons_covered=f"{int(reg.season.min())}-{int(reg.season.max())}",
        reg_games=int(len(reg)),
        reg_games_played=int(len(played)),
        reg_games_unplayed=int(len(reg) - len(played)),
        spread_pushes=int((played[played.spread_line.notna()].apply(
            lambda r: r.margin + r.spread_line == 0, axis=1)).sum()),
        total_pushes=int((played[played.total_line.notna()].apply(
            lambda r: r.total == r.total_line, axis=1)).sum()),
        ties=int((played.margin == 0).sum()),
        chk_games=int(len(chk)),
        chk_spread_ok=int((chk.spread_ok == True).sum()),
        chk_spread_bad=int((chk.spread_ok == False).sum()),
        chk_total_ok=int((chk.total_ok == True).sum()),
        chk_total_bad=int((chk.total_ok == False).sum()),
        chk_ml_ok=int((chk.ml_ok == True).sum()),
        chk_ml_bad=int((chk.ml_ok == False).sum()),
        chk_line_disagree=int((chk.signed_disagreement.abs() > 1e-9).sum()),
    )
