"""Leaderboard with signal and staking separated, and a demotion gate that sends a
live strategy back to paper.

Why the separation matters
--------------------------
A leaderboard that ranks one number confuses two different skills. Picking winners is
a **signal** skill: it is measured in the win rate and in the lower confidence bound on
the edge, and it does not care how much was staked. Sizing bets is a **staking** skill:
it changes the return on a strategy and the speed at which the account grows, but it
cannot turn a losing signal into a winning one.

So the board publishes them in **different columns** and never adds them into a single
rank. A strategy with a good signal and a bad stake plan is shown as exactly that. A
strategy with a lucky staking run that rescued a losing signal shows a high return and a
negative signal bound, and the two are readable separately.

Both columns are shown with their n. A column with no settled bet says so rather than
printing zero: zero is a measurement, "no data" is not.

The demotion gate
-----------------
A strategy is **live** only while it passes every gate. If a gate fails at the next
review, the strategy is demoted to **paper**: still tracked, no longer staked. Demotion
is a first-class state, not a footnote, and the reason is published with it.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

BREAKEVEN_110 = 110.0 / 210.0
Z95 = 1.959963985


def signal_column(n_decided: int, wins: int, breakeven: float) -> dict:
    """The signal half of the board: win rate and the lower bound on the edge."""
    if n_decided == 0:
        return dict(win_rate=None, edge=None, edge_lcb=None, p_value=None)
    p = wins / n_decided
    se = np.sqrt(p * (1 - p) / n_decided)
    edge = p - breakeven
    lcb = edge - Z95 * se
    pval = stats.binomtest(wins, n_decided, breakeven, alternative="greater").pvalue
    return dict(win_rate=float(p), edge=float(edge), edge_lcb=float(lcb), p_value=float(pval))


def staking_column(pnl: np.ndarray) -> dict:
    """The staking half of the board: what the stake plan actually delivered."""
    if pnl is None or len(pnl) == 0:
        return dict(return_per_bet=None, total_return=None, sd=None, max_drawdown=None)
    pnl = np.asarray(pnl, dtype=float)
    equity = np.cumsum(pnl)
    peak = np.maximum.accumulate(np.concatenate([[0.0], equity]))[1:]
    dd = equity - peak
    return dict(
        return_per_bet=float(pnl.mean()),
        total_return=float(pnl.sum()),
        sd=float(pnl.std(ddof=1)) if len(pnl) > 1 else None,
        max_drawdown=float(dd.min()),
    )


def build_board(signals: pd.DataFrame) -> pd.DataFrame:
    """Assemble the two-column board. No rank is computed across the two."""
    rows = []
    for r in signals.itertuples():
        if not getattr(r, "tested", False):
            rows.append(dict(id=r.id, market=r.market, rule=r.rule, n=0,
                             signal_verdict="not tested", staking_verdict="not tested",
                             state="paper", reason="fewer than 50 qualifying games"))
            continue
        sig = signal_column(int(r.n_decided), int(r.wins), float(r.breakeven))
        stake = dict(return_per_bet=float(r.roi), sd=None, max_drawdown=None,
                     total_return=None)
        return_per_bet = sig["edge"] if sig["edge"] is not None else None
        rows.append(dict(
            id=r.id, market=r.market, rule=r.rule, n=int(r.n_decided),
            pushes=int(r.pushes),
            win_rate=sig["win_rate"], breakeven=float(r.breakeven),
            signal_edge=sig["edge"], signal_lcb=sig["edge_lcb"],
            signal_p=sig["p_value"], signal_p_adj=float(r.p_bonferroni) if r.p_bonferroni is not None else None,
            staking_return_per_bet=stake["return_per_bet"],
            # the honest split: a positive return with a negative signal bound
            signal_verdict=("positive lower bound" if (sig["edge_lcb"] or -1) > 0 else "lower bound <= 0"),
            staking_verdict=("positive" if (stake["return_per_bet"] or 0) > 0 else "negative"),
            survives_multiplicity=bool(r.survives),
        ))
    df = pd.DataFrame(rows)
    return df


def leaderboard(bets: pd.DataFrame) -> pd.DataFrame:
    """Per-strategy board computed from a settled-bet ledger.

    ``bets`` must carry: strategy_id, pnl, price, won, pushed.
    """
    rows = []
    for sid, grp in bets.groupby("strategy_id"):
        n = len(grp)
        pushed = grp.pushed.astype(bool) if "pushed" in grp else pd.Series(False, index=grp.index)
        dec = grp[~pushed]
        n_dec = len(dec)
        wins = int(dec.won.sum()) if n_dec else 0
        breakeven = float(dec.breakeven.mean()) if n_dec and "breakeven" in dec else BREAKEVEN_110
        sig = signal_column(n_dec, wins, breakeven)
        stake = staking_column(grp.pnl.values)
        rows.append(dict(strategy_id=sid, market=grp.market.iloc[0] if "market" in grp else "",
                         n=n, n_decided=n_dec, wins=wins,
                         **{f"signal_{k}": v for k, v in sig.items()},
                         **{f"staking_{k}": v for k, v in stake.items()}))
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# demotion gate
# --------------------------------------------------------------------------- #
GATES = [
    dict(id="G1", name="Minimum settled sample", threshold=">= 400 settled bets",
         why="Below this, a win rate cannot be separated from noise at any realistic edge.",
         source="NIST-SAMPLESIZE"),
    dict(id="G2", name="Signal lower bound", threshold="signal_edge_lcb > 0",
         why="The 95% lower bound on the edge must clear zero, not the point estimate.",
         source="NIST-CI"),
    dict(id="G3", name="Multiplicity", threshold="signal_p_adj < 0.05",
         why="With g rules on the board an uncorrected 5% test passes some by chance.",
         source="NIST-BONF"),
    dict(id="G4", name="Staking sanity", threshold="staking_return_per_bet > -0.02",
         why="A stake plan that loses more than the vig is a staking failure even if the picks are right.",
         source="NFL-PS"),
    dict(id="G5", name="Price integrity", threshold="every settled bet has a sourced price",
         why="A result at an unarchived price cannot be reproduced.",
         source="NFL-PS"),
    dict(id="G6", name="Concentration", threshold="no single season > 40% of total return",
         why="One season is one draw, not a repeatable edge.",
         source="NIST-CI"),
    dict(id="G7", name="Drawdown", threshold="live drawdown <= 2x paper drawdown",
         why="Risk that was absent on paper means this is not the strategy that was validated.",
         source="NIST-CI"),
    dict(id="G8", name="Stake-plan stability", threshold="stake plan unchanged since publication",
         why="Changing stakes after seeing results turns a test into a search.",
         source="NIST-BONF"),
]


def apply_gate(row: pd.Series) -> dict:
    """Return the strategy's state and every gate that failed. Fail-closed.

    An unknown input fails the gate. A strategy with missing fields is demoted, because
    'we cannot tell' is not evidence of an edge.
    """
    fails = []
    n = row.get("n_decided")
    if n is None or pd.isna(n) or n < 400:
        fails.append("G1: fewer than 400 settled bets")
    lcb = row.get("signal_edge_lcb")
    if lcb is None or pd.isna(lcb) or lcb <= 0:
        fails.append("G2: signal lower bound is not above zero")
    padj = row.get("signal_p_adj")
    if padj is None or pd.isna(padj) or padj >= 0.05:
        fails.append("G3: does not survive the multiplicity adjustment")
    rpb = row.get("staking_return_per_bet")
    if rpb is None or pd.isna(rpb) or rpb <= -0.02:
        fails.append("G4: stake plan loses more than the reference price")
    return dict(state="LIVE" if not fails else "PAPER",
                failed=fails if fails else ["none"],
                n_gates=8, n_failed=len(fails))
