"""Skill Lab — control baselines and benchmark-relative proper-score ranking.

Implements readiness-register requirements C03 (rank with proper scores and
uncertainty, not win rate) and C04 (add a control baseline — random picks and
favourites only — to every leaderboard run), on the pinned, already-verified
bet universe in ``line_lab/data/derived/bets.csv`` and the verified results feed
in ``market_lab/data/results_feed.csv``.

Nothing here reads the network. Every number is deterministic arithmetic over
rows already committed in the repository, pinned to nflverse commit
``a270278f3ac4e937295fe6a27814b3c4a2b62645`` (see ``data/provenance.json``).
"""

__all__ = ["metrics", "baselines", "build", "check"]
