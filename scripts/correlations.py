"""Correlation estimates.

Parlay and same-game-parlay pricing depends entirely on how the legs co-move.
Everything here is estimated from settled outcomes in the same data used for
the backtests, and every estimate carries a bootstrap confidence interval.

Three families:
  A. Within-game market correlations (spread vs total, spread vs moneyline)
  B. Cross-game independence (legs of a standard parlay)
  C. Player-prop co-movement (team-mate props, same-player props, cross-game)
"""
import numpy as np
import pandas as pd

from common import bootstrap_mean_ci, cluster_bootstrap_ci


def pearson_ci(x, y, n_boot=4000, seed=5):
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    if len(x) < 30:
        return None
    r = float(np.corrcoef(x, y)[0, 1])
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(x), size=(n_boot, len(x)))
    rs = np.array([np.corrcoef(x[i], y[i])[0, 1] for i in idx])
    rs = rs[np.isfinite(rs)]
    return dict(r=r, lo=float(np.quantile(rs, 0.025)), hi=float(np.quantile(rs, 0.975)), n=int(len(x)))


# --------------------------------------------------------------------------
# A. within-game
# --------------------------------------------------------------------------
def within_game(pred):
    d = pred[pred.result.notna() & pred.spread_line.notna() & pred.total_line.notna()].copy()
    out = {}
    out["margin_vs_total"] = pearson_ci(d.result, d.total)

    # per-season stability of the same correlation
    per = []
    for s, g in d.groupby("season"):
        if len(g) > 100:
            per.append({"season": int(s), "r": float(np.corrcoef(g.result, g.total)[0, 1]),
                        "n": int(len(g))})
    out["margin_vs_total_by_season"] = per

    # ATS outcome vs total outcome (the two legs of a spread+total SGP)
    d["ats_home"] = (d.result > d.spread_line).astype(int)
    d["over"] = (d.total > d.total_line).astype(int)
    out["ats_vs_over_indicator"] = pearson_ci(d.ats_home, d.over)

    # moneyline vs spread: how often does the ATS winner also win outright
    m = d[d.home_moneyline.notna()]
    out["ml_vs_ats"] = pearson_ci((m.result > 0).astype(int), (m.result > m.spread_line).astype(int))

    # implied probability correlation (market's own view of the two legs)
    out["spread_line_vs_total_line"] = pearson_ci(d.spread_line, d.total_line)
    return out


def sgp_joint(pred, rho_override=None):
    """Empirical joint probabilities for spread+total combos vs the independence
    assumption used by the book."""
    d = pred[pred.result.notna() & pred.spread_line.notna() & pred.total_line.notna()].copy()
    d = d[(d.result != d.spread_line) & (d.total != d.total_line)]
    n = len(d)
    if rho_override is None:
        from math import erf, sqrt

        def Phi(x):
            return 0.5 * (1.0 + erf(x / sqrt(2.0)))

        # implied probabilities from a normal fitted to MARKET lines / sigmas
        z_m = d.spread_line / d.sigma_margin
        p_home_ats = np.array([Phi(v) for v in z_m])
        z_t = (d.total_line - d.mu_total) / d.sigma_total
        p_over = np.array([Phi(-v) for v in z_t])
    rows = []
    combos = [
        ("home ATS + over", d.result > d.spread_line, d.total > d.total_line),
        ("home ATS + under", d.result > d.spread_line, d.total < d.total_line),
        ("away ATS + over", d.result < d.spread_line, d.total > d.total_line),
        ("away ATS + under", d.result < d.spread_line, d.total < d.total_line),
    ]
    for name, a, b in combos:
        joint = float(np.mean(a.values & b.values))
        indep = float(np.mean(a.values) * np.mean(b.values))
        rows.append({"combo": name, "joint_empirical": joint, "product_of_rates": indep,
                     "ratio": joint / indep if indep else None, "n": int(n)})
    return {"combos": rows, "n_games": int(n),
            "note": "product_of_rates uses the unconditional rate of each leg, i.e. exactly "
                    "the independence assumption a book makes when it multiplies prices."}


# --------------------------------------------------------------------------
# B. cross-game independence
# --------------------------------------------------------------------------
def cross_game(pred, n_pairs=20000, seed=17):
    d = pred[pred.result.notna() & pred.spread_line.notna()].copy()
    d["cover_home"] = (d.result != d.spread_line) & (d.result > d.spread_line)
    d["decided"] = d.result != d.spread_line
    d = d[d.decided]
    rng = np.random.default_rng(seed)
    xs, ys = [], []
    for _, g in d.groupby(["season", "week"]):
        if len(g) < 2:
            continue
        a = g.cover_home.values
        i = rng.integers(0, len(a), len(a))
        j = rng.integers(0, len(a), len(a))
        mask = i != j
        xs.extend(a[i[mask]])
        ys.extend(a[j[mask]])
    if len(xs) > n_pairs:
        idx = rng.choice(len(xs), n_pairs, replace=False)
        xs = [xs[k] for k in idx]
        ys = [ys[k] for k in idx]
    return pearson_ci(np.array(xs, float), np.array(ys, float))


# --------------------------------------------------------------------------
# C. player props
# --------------------------------------------------------------------------
def _teamgame(d, stat, min_val=0):
    """Aggregate player-weeks into team-games with per-player columns."""
    g = (d.groupby(["game_id", "team", "player_name"])[stat].sum()
           .unstack("player_name"))
    return g.dropna(axis=1, how="all")


def prop_correlations(pw):
    """Empirical co-movement between prop outcomes on the same team-game."""
    d = pw.copy()
    out = {"same_game_teammate": [], "same_player": [], "cross_game_baseline": None}

    # --- team-mate pair correlations: top-2 receivers by volume -------------
    rng = np.random.default_rng(23)
    wr = d[d.position.isin(["WR", "TE"])]
    pairs_pos, pairs_neg = [], []
    for (gid, team), g in wr.groupby(["game_id", "team"]):
        g2 = g[g.targets >= 1]
        if len(g2) < 2:
            continue
        s = g2.sort_values("receiving_yards", ascending=False)
        pairs_pos.append((s.receiving_yards.iloc[0], s.receiving_yards.iloc[1]))

    # rank-based (pair within team-game is anti-correlated by construction if we
    # sort, so use the raw two highest-usage players instead)
    usage = []
    for (gid, team), g in wr.groupby(["game_id", "team"]):
        g2 = g.sort_values("targets", ascending=False)
        if len(g2) >= 2:
            usage.append((g2.player_name.iloc[0], g2.receiving_yards.iloc[0],
                          g2.player_name.iloc[1], g2.receiving_yards.iloc[1]))
    if usage:
        a = np.array([u[1] for u in usage], float)
        b = np.array([u[3] for u in usage], float)
        out["same_game_teammate"].append({
            "combo": "WR/TE #1 rec yds x WR/TE #2 rec yds (same team, same game)",
            "expected_sign": "negative (target competition)", **pearson_ci(a, b)})

    # --- QB attempts vs lead receiver --------------------------------------
    qb = d[(d.position == "QB") & (d.pass_attempts >= 10)][["game_id", "team", "pass_attempts"]]
    lead = []
    for (gid, team), g in wr.groupby(["game_id", "team"]):
        g2 = g.sort_values("targets", ascending=False)
        if len(g2):
            lead.append({"game_id": gid, "team": team, "wr_yds": g2.receiving_yards.iloc[0],
                         "wr_targets": g2.targets.iloc[0]})
    lead = pd.DataFrame(lead)
    if len(lead) and len(qb):
        m = lead.merge(qb, on=["game_id", "team"])
        out["same_game_teammate"].append({
            "combo": "QB pass attempts x lead receiver rec yds (same team, same game)",
            "expected_sign": "positive", **pearson_ci(m.pass_attempts, m.wr_yds)})

    # --- lead RB carries vs lead receiver yards ----------------------------
    rb = []
    for (gid, team), g in d[d.position == "RB"].groupby(["game_id", "team"]):
        g2 = g.sort_values("rush_attempts", ascending=False)
        if len(g2):
            rb.append({"game_id": gid, "team": team, "rb_carries": g2.rush_attempts.iloc[0]})
    rb = pd.DataFrame(rb)
    if len(rb) and len(lead):
        m = rb.merge(lead, on=["game_id", "team"])
        out["same_game_teammate"].append({
            "combo": "Lead RB carries x lead receiver rec yds (same team, same game)",
            "expected_sign": "negative (competing volume)", **pearson_ci(m.rb_carries, m.wr_yds)})

    # --- same player, two props -------------------------------------------
    out["same_player"].append({
        "combo": "player targets x player receptions (same game)",
        "expected_sign": "positive", **pearson_ci(d.targets, d.receptions)})
    out["same_player"].append({
        "combo": "player rush attempts x player rushing yards (same game)",
        "expected_sign": "positive",
        **pearson_ci(d[d.rush_attempts > 0].rush_attempts, d[d.rush_attempts > 0].rushing_yards)})
    out["same_player"].append({
        "combo": "player rush attempts x player receiving yards (same game)",
        "expected_sign": "weak / negative", **pearson_ci(d.rush_attempts, d.receiving_yards)})

    # --- cross-game baseline ----------------------------------------------
    g = d.groupby(["game_id", "player_name"]).receiving_yards.sum().reset_index()
    if len(g) > 100:
        v = g.receiving_yards.values
        i = rng.integers(0, len(v), 20000)
        j = rng.integers(0, len(v), 20000)
        msk = i != j
        out["cross_game_baseline"] = {
            "combo": "receiving yards: random player-game vs random other player-game",
            "expected_sign": "zero", **pearson_ci(v[i[msk]], v[j[msk]])}
    return out


def prop_dispersion(pw):
    """Over/under dispersion of prop markets -- needed to price prop parlays."""
    rows = []
    for stat in ["receiving_yards", "receptions", "rush_attempts"]:
        for pos in ["WR", "RB", "TE", "QB"]:
            s = pw[(pw.position == pos)][stat]
            if len(s) > 500:
                rows.append({"stat": stat, "position": pos, "n": int(len(s)),
                             "mean": float(s.mean()), "sd": float(s.std(ddof=1)),
                             "p10": float(s.quantile(0.1)), "median": float(s.median()),
                             "p90": float(s.quantile(0.9))})
    return rows
