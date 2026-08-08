# Basket Daily Backtest Report

Created at UTC: `2026-07-28T08:53:31+00:00`

## PM Decision

The basket has completed a local daily engineering smoke test. This is not platform replication, paper trading approval, or strategy acceptance.

## Metrics

- `strategy_return`: `1.094361013`
- `annualized_return`: `0.163813905`
- `benchmark_return`: `0.7900731525`
- `excess_return`: `0.30428786`
- `max_drawdown`: `0.1193034075`
- `sharpe`: `1.05548698`
- `information_ratio`: `0.326958141`
- `strategy_volatility`: `0.1552049579`
- `benchmark_volatility`: `0.1755650547`
- `max_drawdown_interval`: `2021-09-23,2021-11-05`

## Startup Preload

- `configured_start_date`: `2021-05-01`
- `effective_first_signal_date`: `2021-05-06`
- `first_daily_row_date`: `2021-05-06`
- `startup_gap_days`: `5`
- `start_date_was_silently_lifted_to_first_signal`: `False`

## Rebalance Order Health

- `rebalance_signal_count`: `21`
- `normal_rebalance_count`: `21`
- `no_order_rebalance_count`: `0`
- `no_order_no_position_count`: `0`
- `blocked_or_unfilled_rebalance_count`: `0`
- `leading_no_order_no_position_count`: `0`
- `first_executed_order_date`: `2021-05-06`
- `first_position_date`: `2021-05-06`
- `needs_review`: `False`

## Known Gaps

- This is a basket-level local daily simulation, not platform replication and not strategy acceptance.
- Basket sectors included in this run: bank, utilities_electricity, highway_infrastructure, port_rail_infrastructure.
- Benchmark is a same-pool equal-weight total-return proxy where net cash dividends are available; otherwise price return.
- All configured dividend files contain at least one cash-dividend event.

## Next Gate

`basket_formal_validation_and_overfit_audit`
