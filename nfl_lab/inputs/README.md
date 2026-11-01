# Verified workbench inputs

Default: **empty**. The workbench publishes no empirical NFL value unless licensed, event-level official evidence is admitted.

Optional files (JSON Lines):

| File | Contract | Required evidence |
|---|---|---|
| `games.jsonl` | `nfl_lab.contracts.Game` | Official game result source, licensed/public-domain rights, pinned hash when stored. |
| `quotes.jsonl` | `nfl_lab.contracts.Quote` | Official operator quote source, timestamp before kickoff, executable flag, archived settlement rules. |
| `bets.jsonl` | `nfl_lab.contracts.SettledBet` | Official settlement evidence, quote id, rules id, source URL. |
| `forecasts.jsonl` | `nfl_lab.contracts.Forecast` | Model version, issue time, kickoff, feature availability time, optional timestamped baseline. |
| `player_games.jsonl` | `nfl_lab.models.PlayerGame` | Official player game log source, licensed/public-domain rights. |

Rules:

1. No NFL.com scraping or systematic compilation without express prior written consent.
2. No imputed lines or prices. Missing values are rejected, not filled.
3. A source URL is not a redistribution licence. Stored content requires `rights=licensed` or `rights=public_domain` and a matching SHA-256 hash in `nfl_lab/sources.json` or an admitted evidence registry.
4. Synthetic fixtures belong in `tests/`, never in this directory.
5. Current operator help pages do not prove historical settlement rules; archive the exact operator/date/jurisdiction/market rule.
