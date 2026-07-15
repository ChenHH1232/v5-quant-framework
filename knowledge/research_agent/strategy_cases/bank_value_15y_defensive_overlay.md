# Bank Value 15Y Defensive Overlay

## Type

Decision / Caveat

## Summary

Bank Value 15Y originally had no executable stop-loss, take-profit, or defensive overlay. A portfolio-level bank-sector moving-average overlay is more consistent with value investing than fixed individual stock stops.

## Context

The user asked whether the Bank Value 15Y strategy lacked stop-loss/take-profit and defensive logic. The strategy spec already described a defensive rule, but the executable local and JoinQuant paths did not implement it.

## Evidence

- Baseline real JoinQuant-price local return: about `33.89%`.
- Baseline max drawdown: about `17.69%`.
- MA252 defensive overlay return: about `31.29%`.
- MA252 max drawdown: about `13.03%`.
- MA252 risk-off days: about `28.7%`.

## Implications

- Treat the overlay as risk control, not as evidence that the selection model is stronger.
- Prefer sector-level exposure control before individual stop-loss/take-profit for value strategies.
- Use fixed economic parameters such as 12-month/252-day moving average rather than choosing the best-performing window after the fact.

## Limits

The overlay was researched after seeing near-5-year platform results, so it should be marked as an improvement hypothesis rather than a clean out-of-sample acceptance result.

## Related Files

- `docs/BANK_VALUE_15Y_DEFENSIVE_OVERLAY_RESEARCH.md`
- `src/v5/daily_backtest.py`
- `exports/joinquant/bank_value_15y_joinquant_frozen_signals_near5y.py`

## Last Updated

2026-07-15
