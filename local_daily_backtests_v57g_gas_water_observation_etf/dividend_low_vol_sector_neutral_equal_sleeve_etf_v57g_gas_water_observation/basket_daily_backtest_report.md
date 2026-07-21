# Basket Daily Backtest Report

Created at UTC: `2026-07-21T04:52:30+00:00`

## PM Decision

The basket has completed a local daily engineering smoke test. This is not platform replication, paper trading approval, or strategy acceptance.

## Metrics

- `strategy_return`: `0.7006712185`
- `annualized_return`: `0.126312648`
- `benchmark_return`: `0.5300706122`
- `excess_return`: `0.1706006063`
- `max_drawdown`: `0.1214919466`
- `sharpe`: `0.8200736701`
- `information_ratio`: `0.3129940828`
- `strategy_volatility`: `0.1609168511`
- `benchmark_volatility`: `0.176304378`
- `max_drawdown_interval`: `2024-05-27,2024-09-11`

## Rebalance Order Health

- `rebalance_signal_count`: `19`
- `normal_rebalance_count`: `19`
- `no_order_rebalance_count`: `0`
- `no_order_no_position_count`: `0`
- `blocked_or_unfilled_rebalance_count`: `0`
- `leading_no_order_no_position_count`: `0`
- `first_executed_order_date`: `2021-10-08`
- `first_position_date`: `2021-10-08`
- `needs_review`: `False`

## Known Gaps

- This is a basket-level local daily simulation, not platform replication and not strategy acceptance.
- Basket sectors included in this run: bank, utilities_electricity, highway_infrastructure, port_rail_infrastructure, gas_water_operators.
- Benchmark is a same-pool equal-weight total-return proxy where net cash dividends are available; otherwise price return.
- All configured dividend files contain at least one cash-dividend event.

## Next Gate

`basket_formal_validation_and_overfit_audit`
