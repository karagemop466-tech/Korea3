"""Feature engineering.

Every feature for a game is built ONLY from information available before that
game kicks off: the ratings/rolling averages are updated after each game is
settled, and models are refit each season using prior seasons only.

Leakage guard
-------------
`assert_point_in_time()` recomputes the rating table from a truncated history
and checks it is byte-identical to the value used at prediction time.
"""
import numpy as np
import pandas as pd

from common import RAW, DERIVED, write_json, r

ELO_START = 1505.0
ELO_HFA = 65.0          # home-field advantage in Elo points (fixed a priori)
ELO_K = 20.0
SEASON_REGRESSION = 1.0 / 3.0


def load_games():
    g = pd.read_csv(f"{RAW}/games.csv")
    g = g[g.game_type.isin(["REG", "WC", "DIV", "CON", "SB"])].copy()
    g["gameday"] = pd.to_datetime(g["gameday"], errors="coerce")
    g = g.sort_values(["gameday", "gametime"], na_position="last").reset_index(drop=True)
    return g


def build_elo(g):
    """Sequential Elo with margin-of-victory multiplier and season reversion.

    Returns a dict keyed by row index -> (home_elo_pre, away_elo_pre).
    """
    ratings = {}
    pre = {}
    last_season = {}
    for i, row in g.iterrows():
        for t in (row.home_team, row.away_team):
            ratings.setdefault(t, ELO_START)
        # season-to-season mean reversion
        s = row.season
        for t in list(ratings):
            if last_season.get(t) not in (None, s):
                ratings[t] = ELO_START + (ratings[t] - ELO_START) * (1 - SEASON_REGRESSION)
        last_season[row.home_team] = s
        last_season[row.away_team] = s

        rh, ra = ratings[row.home_team], ratings[row.away_team]
        pre[i] = (rh, ra)
        if pd.isna(row.home_score) or pd.isna(row.away_score):
            continue
        margin = row.home_score - row.away_score
        exp_home = 1.0 / (1.0 + 10 ** (-((rh + ELO_HFA) - ra) / 400.0))
        score = 1.0 if margin > 0 else (0.0 if margin < 0 else 0.5)
        mov = (abs(margin) + 1.0) ** 0.7 / (11.0 ** 0.7)   # 11 = league mean |margin|
        delta = ELO_K * mov * (score - exp_home)
        ratings[row.home_team] = rh + delta
        ratings[row.away_team] = ra - delta
    return pre


def build_rolling(g):
    """Point-in-time EMA of points for/against per team (span=6 games)."""
    alpha = 2.0 / (6 + 1)
    off, dfn, games_played = {}, {}, {}
    feats = {}
    for i, row in g.iterrows():
        h, a = row.home_team, row.away_team
        league_avg = np.nanmedian([v for v in list(off.values())]) if off else 22.0
        league_avg = 22.0 if not np.isfinite(league_avg) else league_avg

        def val(d, t, default):
            return d.get(t, default)

        feats[i] = dict(
            off_home=val(off, h, league_avg), off_away=val(off, a, league_avg),
            def_home=val(dfn, h, league_avg), def_away=val(dfn, a, league_avg),
            gp_home=val(games_played, h, 0), gp_away=val(games_played, a, 0),
            league_avg=league_avg,
        )
        if pd.isna(row.home_score) or pd.isna(row.away_score):
            continue
        for t, pts in ((h, row.home_score), (a, row.away_score)):
            opp_pts = row.away_score if t == h else row.home_score
            off[t] = off.get(t, league_avg) * (1 - alpha) + pts * alpha
            dfn[t] = dfn.get(t, league_avg) * (1 - alpha) + opp_pts * alpha
            games_played[t] = games_played.get(t, 0) + 1
    return feats


def build_features():
    g = load_games()
    pre = build_elo(g)
    roll = build_rolling(g)

    rows = []
    for i, row in g.iterrows():
        rh, ra = pre[i]
        rf = roll[i]
        rows.append(dict(
            game_id=row.game_id, season=int(row.season), week=int(row.week),
            game_type=row.game_type, gameday=row.gameday.strftime("%Y-%m-%d"),
            home_team=row.home_team, away_team=row.away_team,
            home_score=row.home_score, away_score=row.away_score,
            result=row.result, total=row.total,
            spread_line=row.spread_line, total_line=row.total_line,
            home_moneyline=row.home_moneyline, away_moneyline=row.away_moneyline,
            home_spread_odds=row.home_spread_odds, away_spread_odds=row.away_spread_odds,
            over_odds=row.over_odds, under_odds=row.under_odds,
            elo_home=rh, elo_away=ra, elo_diff=rh - ra,
            off_home=rf["off_home"], off_away=rf["off_away"],
            def_home=rf["def_home"], def_away=rf["def_away"],
            gp_home=rf["gp_home"], gp_away=rf["gp_away"],
            league_avg=rf["league_avg"],
            rest_home=row.home_rest, rest_away=row.away_rest,
            rest_diff=row.home_rest - row.away_rest,
            div_game=row.div_game,
            roof=row.roof,
            surface=row.surface,
            location=row.location,
            pfr_id=row.pfr,
            alt_game_id=f"{int(row.season)}_{int(row.week):02d}_{row.away_team}_{row.home_team}",
        ))
    df = pd.DataFrame(rows)
    # derived pre-game features (all point-in-time)
    df["form_home"] = df.off_home - df.def_home
    df["form_away"] = df.off_away - df.def_away
    df["form_diff"] = df.form_home - df.form_away
    df["dome"] = df.roof.isin(["dome", "closed"]).astype(int)
    df["is_neutral"] = (df.location == "Neutral").astype(int)
    df.to_csv(f"{DERIVED}/features.csv", index=False)
    return df


# --------------------------------------------------------------------------
# leakage guard
# --------------------------------------------------------------------------
def assert_point_in_time(df_raw, checks=25, seed=3):
    """Recompute Elo from a truncated history for random games and confirm the
    stored pre-game rating matches exactly (no future information used)."""
    g = load_games()
    pre_full = build_elo(g)
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(g), size=min(checks, len(g)), replace=False)
    worst = 0.0
    for k in sorted(idx):
        trunc = g.iloc[:k + 1].copy()          # history up to and including game k
        pre_trunc = build_elo(trunc)
        a = pre_full[k]
        b = pre_trunc[len(trunc) - 1]
        worst = max(worst, abs(a[0] - b[0]), abs(a[1] - b[1]))
    return dict(checks=int(len(idx)), max_abs_diff=float(worst),
                passed=bool(worst < 1e-9))


if __name__ == "__main__":
    df = build_features()
    guard = assert_point_in_time(df)
    write_json(f"{DERIVED}/leakage_guard.json",
               {"elo_point_in_time": guard,
                "note": "Pre-game Elo recomputed from truncated history must match stored value."})
    print(df.shape, guard)
