"""Injury, depth-chart and replacement-quality measurements.

Answers, with numbers rather than adjectives:

A. When the official report says Out / Doubtful / Questionable, how often did the
   player actually take an offensive or defensive snap that week?  (The only way to
   know what a status is *worth*, given the league publishes no probability.)
B. What does a blank game status mean in practice?
C. When a team's starting quarterback changes, how far does the closing spread move,
   and is the move bigger or smaller than the result justifies?
D. Which "string" was lost — starter, 2nd, 3rd, 4th — and does losing a deeper player
   move the number less?  (Depth string is measured from the player's own snap share in
   his previous game, not from an official depth chart, because no official numbered
   depth chart is published — see fact K06.)
E. Does the market already price the depletion?  Measured as the residual (result minus
   closing line) against the share of snaps lost, on offence and defence separately.

Everything is computed from pinned nflverse releases (see manifest.json) and every
table carries its own denominator.  Nothing is imputed: a season without snap counts
is reported as blocked instead of being filled in.
"""
from __future__ import annotations

import json
import math
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LAB = ROOT / "data" / "injury_lab"

QB_STATUSES = ("Out", "Doubtful", "Questionable", "")
PRACTICE = ("Did Not Participate In Practice", "Limited Participation in Practice",
            "Full Participation in Practice", "")

OFF_GROUPS = {"QB": "QB", "RB": "RB", "FB": "RB", "WR": "WR", "TE": "TE",
              "T": "OL", "G": "OL", "C": "OL", "OT": "OL", "OG": "OL", "OL": "OL"}
DEF_GROUPS = {"DE": "DL", "DT": "DL", "NT": "DL", "DL": "DL", "EDGE": "DL",
              "LB": "LB", "ILB": "LB", "OLB": "LB", "MLB": "LB",
              "CB": "DB", "S": "DB", "FS": "DB", "SS": "DB", "DB": "DB",
              "SAF": "DB", "SAFETY": "DB"}


def norm_name(s: str) -> str:
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    s = s.lower().replace(".", "").replace("'", "").replace("-", " ")
    return " ".join(s.split())


def wilson(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    if n == 0:
        return (float("nan"), float("nan"))
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))


# --------------------------------------------------------------------------- loading
def load_injuries() -> pd.DataFrame:
    frames = []
    for p in sorted((LAB / "injuries").glob("injuries_*.csv")):
        df = pd.read_csv(p, low_memory=False)
        df["source_file"] = p.name
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    for col in ("report_status", "practice_status", "position", "team", "game_type"):
        if col in df:
            df[col] = df[col].fillna("").astype(str).str.strip()
    df["season"] = df["season"].astype(int)
    df["week"] = df["week"].astype(int)
    df["name_key"] = df["full_name"].map(norm_name)
    return df


def load_snaps() -> pd.DataFrame:
    frames = []
    for p in sorted((LAB / "snap_counts").glob("snap_counts_*.csv")):
        df = pd.read_csv(p, low_memory=False)
        frames.append(df)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df["season"] = df["season"].astype(int)
    df["week"] = df["week"].astype(int)
    df["game_type"] = df.get("game_type", "REG").fillna("REG").astype(str).str.strip()
    df = df[df.game_type == "REG"] if "game_type" in df else df
    df["name_key"] = df["player"].map(norm_name)
    for c in ("offense_snaps", "defense_snaps", "st_snaps"):
        df[c] = pd.to_numeric(df.get(c, 0), errors="coerce").fillna(0)
    return df


def load_games() -> pd.DataFrame:
    g = pd.read_csv(ROOT / "data" / "raw" / "games.csv", low_memory=False)
    g = g[(g.game_type == "REG") & g.home_score.notna() & g.away_score.notna()].copy()
    g["total"] = g.home_score + g.away_score
    g["margin"] = g.home_score - g.away_score  # positive = home won
    return g


def load_depth_current() -> pd.DataFrame:
    p = LAB / "depth_charts" / "depth_charts_2026.csv"
    if not p.exists():
        p = LAB / "depth_charts" / "depth_charts_2025.csv"
    if not p.exists():
        return pd.DataFrame()
    d = pd.read_csv(p, low_memory=False)
    d["name_key"] = d["player_name"].map(norm_name)
    return d


# ------------------------------------------------------------------ A / B: status value
def status_value_table(joined: pd.DataFrame) -> list[dict]:
    """P(played at least one snap) by published game status."""
    rows = []
    n_all = len(joined)
    for status in QB_STATUSES:
        sub = joined[joined.report_status == status]
        n = len(sub)
        k = int(sub.played.sum()) if n else 0
        lo, hi = wilson(k, n)
        rows.append({
            "status": status or "(blank — no game status reported)",
            "n": n,
            "played": k,
            "rate": round(k / n, 4) if n else None,
            "ci95": [round(lo, 4), round(hi, 4)] if n else None,
            "share_of_rows": round(n / n_all, 4) if n_all else None,
        })
    return rows


def practice_value_table(joined: pd.DataFrame) -> list[dict]:
    rows = []
    for st in PRACTICE:
        sub = joined[joined.practice_status == st]
        n = len(sub)
        k = int(sub.played.sum()) if n else 0
        lo, hi = wilson(k, n)
        rows.append({
            "practice": st or "(blank)",
            "n": n,
            "played": k,
            "rate": round(k / n, 4) if n else None,
            "ci95": [round(lo, 4), round(hi, 4)] if n else None,
        })
    return rows


def build_status_join(inj: pd.DataFrame, snaps: pd.DataFrame) -> pd.DataFrame:
    """Join each report row to whether that player recorded any snap that season-week."""
    if inj.empty or snaps.empty:
        return pd.DataFrame()
    played = (snaps.groupby(["season", "week", "team", "name_key"])
              .agg(off=("offense_snaps", "sum"), dfn=("defense_snaps", "sum"),
                   st=("st_snaps", "sum")).reset_index())
    played["played"] = ((played.off + played.dfn + played.st) > 0).astype(int)
    reg = inj[(inj.game_type.isin(["REG", ""]))]
    j = reg.merge(played, on=["season", "week", "team", "name_key"], how="left")
    # A report row with no snap-count row at all is a non-participant *only* when that
    # team-week exists in the snap data; otherwise the join is blocked for that week.
    weeks_present = set(map(tuple, snaps[["season", "week"]].drop_duplicates().values))
    j["week_covered"] = [tuple(x) in weeks_present for x in j[["season", "week"]].values]
    j["played"] = j["played"].fillna(0).astype(int)
    return j[j.week_covered]


# ------------------------------------------------------------------- C: quarterback change
def qb_change_table(games: pd.DataFrame, feats: pd.DataFrame) -> list[dict]:
    """Closing-spread movement and result residual when the starting QB changes."""
    g = games.merge(feats[["game_id", "qb_change_home", "qb_change_away"]], on="game_id", how="left")
    g = g[g.spread_line.notna()].copy()
    # closing spread is stored home-perspective (negative = home favoured)
    g["cover_margin"] = g.margin + g.spread_line
    rows = []
    for side, flag in (("home", "qb_change_home"), ("away", "qb_change_away")):
        for changed in (1, 0):
            sub = g[g[flag] == changed]
            if sub.empty:
                continue
            rows.append({
                "side": side,
                "qb_changed": bool(changed),
                "n_games": int(len(sub)),
                "mean_abs_close_spread": round(float(sub.spread_line.abs().mean()), 3),
                "mean_cover_margin_pts": round(float(sub.cover_margin.mean()), 3),
                "cover_margin_sd": round(float(sub.cover_margin.std()), 3),
                "home_win_rate": round(float((sub.margin > 0).mean()), 4),
                "mean_total_vs_line": round(float((sub.total - sub.total_line).mean()), 3)
                                     if sub.total_line.notna().any() else None,
            })
    return rows


def qb_change_edge(bets: pd.DataFrame) -> dict:
    """The pre-registered S8 'backup-quarterback fade' as it was actually settled."""
    s8 = bets[bets.strategy_id == "S8"]
    if s8.empty:
        return {}
    r = s8.pnl.to_numpy(dtype=float)
    return {
        "strategy": "S8 Backup-quarterback fade",
        "n": int(r.size),
        "roi_pct": round(100 * float(r.mean()), 3),
        "seasons": [int(s8.season.min()), int(s8.season.max())],
    }


# -------------------------------------------------------- D: which string was lost
def add_depth_string(snaps: pd.DataFrame) -> pd.DataFrame:
    """Rank each player's snap share within his team / position group / game."""
    s = snaps.copy()
    s["group"] = s["position"].map(lambda p: OFF_GROUPS.get(str(p).upper(), ""))
    s["dgroup"] = s["position"].map(lambda p: DEF_GROUPS.get(str(p).upper(), ""))
    out = []
    for grp_col, snap_col, tag in (("group", "offense_snaps", "off"), ("dgroup", "defense_snaps", "def")):
        sub = s[s[grp_col] != ""].copy()
        sub = sub[sub[snap_col] > 0]
        if sub.empty:
            continue
        sub["rank"] = (sub.groupby(["season", "week", "team", grp_col])[snap_col]
                       .rank(ascending=False, method="first").astype(int))
        sub["share"] = sub[snap_col] / sub.groupby(["season", "week", "team"])[snap_col].transform("sum")
        out.append(sub[["season", "week", "team", "name_key", "player", grp_col, snap_col,
                        "rank", "share", tag]])
    if not out:
        return pd.DataFrame()
    return pd.concat(out, ignore_index=True)


def string_loss_table(inj: pd.DataFrame, depth: pd.DataFrame, games: pd.DataFrame) -> list[dict]:
    """Residual (result minus closing line) when a team's 1st/2nd/3rd/4th string is Out."""
    if depth.empty or inj.empty:
        return []
    # previous appearance of each player before this season-week
    d = depth.sort_values(["season", "week"])
    key = ["season", "week", "team", "name_key"]
    parts = []
    for tag in ("off", "def"):
        dd = d[d.get(tag).notna()] if tag in d else pd.DataFrame()
        if dd.empty:
            continue
        dd = dd[["season", "week", "team", "name_key", "rank", "share", tag]].copy()
        dd["for_season"] = dd["season"]
        dd["for_week"] = dd["week"] + 1
        parts.append(dd.rename(columns={"rank": f"{tag}_rank", "share": f"{tag}_share"}))
    if not parts:
        return []
    prev = pd.concat(parts, ignore_index=True)
    outs = inj[inj.report_status == "Out"][key + ["position"]].copy()
    m = outs.merge(prev, left_on=["season", "week", "team", "name_key"],
                   right_on=["for_season", "for_week", "team", "name_key"], how="inner")
    if m.empty:
        return []
    # attach to game residuals from the injured team's perspective
    home = games[["season", "week", "home_team", "home_score", "away_score", "spread_line"]].copy()
    home["team"] = home.home_team
    home["pts_for"] = home.home_score
    home["pts_against"] = home.away_score
    home["residual"] = (home.home_score - home.away_score) + home.spread_line
    away = games[["season", "week", "away_team", "home_score", "away_score", "spread_line"]].copy()
    away["team"] = away.away_team
    away["pts_for"] = away.away_score
    away["pts_against"] = away.home_score
    away["residual"] = (away.away_score - away.home_score) + away.spread_line
    side = pd.concat([home, away], ignore_index=True)
    m = m.merge(side[["season", "week", "team", "residual", "pts_for", "pts_against"]],
                on=["season", "week", "team"], how="inner")
    rows = []
    for tag, label in (("off", "Offence"), ("def", "Defence")):
        col = f"{tag}_rank"
        if col not in m:
            continue
        for string in (1, 2, 3, 4):
            sub = m[m[col] == string]
            if len(sub) < 30:
                rows.append({"side": label, "string": string, "n": int(len(sub)),
                             "residual_mean": None, "ci95": None,
                             "note": "fewer than 30 observations — reported, not used"})
                continue
            r = sub.residual.to_numpy(dtype=float)
            se = r.std(ddof=1) / math.sqrt(r.size)
            rows.append({
                "side": label, "string": string, "n": int(r.size),
                "residual_mean": round(float(r.mean()), 3),
                "ci95": [round(float(r.mean() - 1.96 * se), 3),
                         round(float(r.mean() + 1.96 * se), 3)],
                "pts_for_mean": round(float(sub.pts_for.mean()), 2),
                "pts_against_mean": round(float(sub.pts_against.mean()), 2),
                "position_mix": sub.position.value_counts().head(3).to_dict(),
            })
    return rows


# ----------------------------------------------------- E: does the market price depletion
def depletion_index(inj: pd.DataFrame, snaps: pd.DataFrame) -> pd.DataFrame:
    """Share of a unit's previous-game snaps that is listed Out or Questionable this week."""
    if snaps.empty or inj.empty:
        return pd.DataFrame()
    prev = snaps.groupby(["season", "week", "team"]).agg(
        off_total=("offense_snaps", "sum"), def_total=("defense_snaps", "sum")).reset_index()
    prev["for_week"] = prev["week"] + 1
    key = ["season", "week", "team", "name_key"]
    stat = inj[key + ["report_status"]].copy()
    m = snaps.merge(stat, on=key, how="left")
    m["report_status"] = m["report_status"].fillna("")
    agg = m.groupby(["season", "week", "team"]).apply(
        lambda d: pd.Series({
            "off_snaps": d.offense_snaps.sum(),
            "def_snaps": d.defense_snaps.sum(),
            "out_off": d.loc[d.report_status == "Out", "offense_snaps"].sum(),
            "out_def": d.loc[d.report_status == "Out", "defense_snaps"].sum(),
            "q_off": d.loc[d.report_status == "Questionable", "offense_snaps"].sum(),
            "q_def": d.loc[d.report_status == "Questionable", "defense_snaps"].sum(),
            "d_off": d.loc[d.report_status == "Doubtful", "offense_snaps"].sum(),
            "d_def": d.loc[d.report_status == "Doubtful", "defense_snaps"].sum(),
        }), include_groups=False).reset_index()
    for tag in ("off", "def"):
        agg[f"out_share_{tag}"] = agg[f"out_{tag}"] / agg[f"{tag}_snaps"].replace(0, np.nan)
        agg[f"q_share_{tag}"] = agg[f"q_{tag}"] / agg[f"{tag}_snaps"].replace(0, np.nan)
    return agg


def depletion_effect(dep: pd.DataFrame, games: pd.DataFrame) -> list[dict]:
    """OLS of the result residual on Out/Q shares, offence and defence, with a
    season-clustered standard error.  A coefficient whose CI contains zero is
    published as 'no measurable effect' rather than as a signal."""
    if dep.empty:
        return []
    home = games[["season", "week", "home_team", "home_score", "away_score", "spread_line"]].copy()
    home["team"] = home.home_team
    home["residual"] = (home.home_score - home.away_score) + home.spread_line
    away = games[["season", "week", "away_team", "home_score", "away_score", "spread_line"]].copy()
    away["team"] = away.away_team
    away["residual"] = (away.away_score - away.home_score) + away.spread_line
    side = pd.concat([home, away], ignore_index=True)
    d = side.merge(dep, on=["season", "week", "team"], how="inner").dropna(
        subset=["out_share_off", "out_share_def", "q_share_off", "q_share_def", "residual"])
    if len(d) < 200:
        return []
    X = np.column_stack([np.ones(len(d)), d.out_share_off, d.out_share_def,
                         d.q_share_off, d.q_share_def])
    y = d.residual.to_numpy(dtype=float)
    beta, *_ = np.linalg.lstsq(X, y, rcond=None)
    resid = y - X @ beta
    # cluster by season
    meat = np.zeros((5, 5))
    for _, idx in d.groupby("season").indices.items():
        Xg = X[idx]
        eg = resid[idx]
        s = Xg.T @ eg
        meat += np.outer(s, s)
    bread = np.linalg.inv(X.T @ X)
    cov = bread @ meat @ bread
    se = np.sqrt(np.clip(np.diag(cov), 0, None))
    names = ["intercept", "out_share_offence", "out_share_defence",
             "questionable_share_offence", "questionable_share_defence"]
    rows = []
    for nm, b, s in zip(names, beta, se):
        rows.append({
            "term": nm,
            "coef_points": round(float(b), 3),
            "se": round(float(s), 3),
            "ci95": [round(float(b - 1.96 * s), 3), round(float(b + 1.96 * s), 3)],
            "measurable": bool(abs(b) > 1.96 * s),
        })
    rows.append({"term": "n_team_weeks", "coef_points": int(len(d)), "se": None, "ci95": None,
                 "measurable": None})
    return rows


# ------------------------------------------------------------------------- current tracker
def current_tracker(inj: pd.DataFrame, depth: pd.DataFrame) -> dict:
    """Latest season-week: who is Out/Questionable/Doubtful, and who is next on the
    unofficial depth chart.  Published as 'unofficial depth order' on every row."""
    if inj.empty:
        return {}
    latest_season = int(inj.season.max())
    season_rows = inj[inj.season == latest_season]
    latest_week = int(season_rows.week.max())
    cur = season_rows[season_rows.week == latest_week]
    rows = []
    dmap: dict[tuple[str, str], list[dict]] = {}
    if not depth.empty:
        for (team, pos), g in depth.groupby(["team", "pos_abb"]):
            g = g.sort_values("pos_rank")
            dmap[(str(team).upper(), str(pos).upper())] = g[["player_name", "pos_rank"]].to_dict("records")
    for _, r in cur[cur.report_status.isin(["Out", "Doubtful", "Questionable"])].iterrows():
        nxt = dmap.get((str(r.team).upper(), str(r.position).upper()), [])
        rank = next((x["pos_rank"] for x in nxt
                     if norm_name(x["player_name"]) == r.name_key), None)
        replacement = ""
        if rank is not None:
            deeper = [x for x in nxt if x["pos_rank"] == rank + 1]
            replacement = deeper[0]["player_name"] if deeper else ""
        rows.append({
            "team": r.team, "week": latest_week, "player": r.full_name,
            "position": r.position, "game_status": r.report_status,
            "practice_status": r.practice_status or "",
            "depth_rank_unofficial": rank if rank is not None else "",
            "next_on_unofficial_chart": replacement,
        })
    return {"season": latest_season, "week": latest_week, "rows": rows,
            "depth_source": "depth_charts_2026.csv (nflverse, unofficial)" if not depth.empty else ""}


# ------------------------------------------------------------------------------- run
def run() -> dict:
    inj = load_injuries()
    snaps = load_snaps()
    games = load_games()
    feats = pd.read_csv(ROOT / "data" / "derived" / "features.csv")
    bets = pd.read_csv(ROOT / "line_lab" / "data" / "derived" / "bets.csv")
    depth_current = load_depth_current()

    out: dict = {
        "coverage": {
            "injury_rows": int(len(inj)),
            "injury_seasons": [int(inj.season.min()), int(inj.season.max())] if len(inj) else None,
            "snap_seasons": [int(snaps.season.min()), int(snaps.season.max())] if len(snaps) else None,
            "snap_rows": int(len(snaps)),
            "games": int(len(games)),
        },
        "blocked": [],
    }
    if inj.empty:
        out["blocked"].append("injuries: release assets not downloaded (see fetch report)")
    if snaps.empty:
        out["blocked"].append("snap_counts: release assets not downloaded (see fetch report)")
    if inj.empty or snaps.empty:
        (LAB / "injury_results.json").write_text(json.dumps(out, indent=1), encoding="utf-8")
        return out

    joined = build_status_join(inj, snaps)
    out["status_value"] = status_value_table(joined)
    out["practice_value"] = practice_value_table(joined)
    out["join_n"] = int(len(joined))

    out["qb_change"] = qb_change_table(games, feats)
    out["qb_edge"] = qb_change_edge(bets)
    depth = add_depth_string(snaps)
    out["string_loss"] = string_loss_table(inj, depth, games)
    dep = depletion_index(inj, snaps)
    out["depletion_effect"] = depletion_effect(dep, games)
    out["current"] = current_tracker(inj, depth_current)

    (LAB / "injury_results.json").write_text(json.dumps(out, indent=1, sort_keys=True),
                                             encoding="utf-8")
    return out


if __name__ == "__main__":  # pragma: no cover
    r = run()
    print(json.dumps({k: (v if not isinstance(v, list) else f"{len(v)} rows")
                      for k, v in r.items()}, indent=1)[:2000])
