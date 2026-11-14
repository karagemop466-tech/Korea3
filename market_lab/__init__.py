"""Markets Ledger: price snapshots, verified results, origination order,
fair-vs-market, signal/staking separation and the demotion gate.

This package is additive. It reads the pinned inputs produced by ``line_lab`` and the
consolidated ``data/derived`` artifacts; it never edits them. Every value it publishes is
either recomputed here from a pinned input or left blank and flagged when no official or
pinned source can confirm it.
"""
