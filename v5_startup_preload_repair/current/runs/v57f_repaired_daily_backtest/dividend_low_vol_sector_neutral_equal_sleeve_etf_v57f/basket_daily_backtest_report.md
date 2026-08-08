# Basket Daily Backtest Report

Created at UTC: `2026-07-28T06:24:38+00:00`

## PM Decision

The basket has completed a local daily engineering smoke test. This is not platform replication, paper trading approval, or strategy acceptance.

## Metrics

- `strategy_return`: `0.8141640295`
- `annualized_return`: `0.1300130572`
- `benchmark_return`: `0.7868231032`
- `excess_return`: `0.02734092633`
- `max_drawdown`: `0.1174890935`
- `sharpe`: `0.8916812506`
- `information_ratio`: `-0.01223922724`
- `strategy_volatility`: `0.1497063742`
- `benchmark_volatility`: `0.1756604699`
- `max_drawdown_interval`: `2022-03-03,2022-03-15`

## Startup Preload

- `configured_start_date`: `2021-05-01`
- `effective_first_signal_date`: `2021-10-08`
- `first_daily_row_date`: `2021-05-06`
- `startup_gap_days`: `160`
- `start_date_was_silently_lifted_to_first_signal`: `False`

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
- Basket sectors included in this run: bank, utilities_electricity, highway_infrastructure, port_rail_infrastructure.
- Benchmark is a same-pool equal-weight total-return proxy where net cash dividends are available; otherwise price return.
- All configured dividend files contain at least one cash-dividend event.

## Next Gate

`basket_formal_validation_and_overfit_audit`
