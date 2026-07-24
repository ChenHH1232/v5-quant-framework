# Basket Daily Backtest Report

Created at UTC: `2026-07-24T15:14:22+00:00`

## PM Decision

The basket has completed a local daily engineering smoke test. This is not platform replication, paper trading approval, or strategy acceptance.

## Metrics

- `strategy_return`: `0.801175475`
- `annualized_return`: `0.1408920387`
- `benchmark_return`: `0.5144830597`
- `excess_return`: `0.2866924153`
- `max_drawdown`: `0.1110630053`
- `sharpe`: `0.9499813522`
- `information_ratio`: `0.4002346725`
- `strategy_volatility`: `0.1507725877`
- `benchmark_volatility`: `0.175062804`
- `max_drawdown_interval`: `2023-05-08,2024-01-22`

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
- Basket sectors included in this run: bank, utilities_electricity, highway_infrastructure, port_rail_infrastructure, telecom_operators.
- Benchmark is a same-pool equal-weight total-return proxy where net cash dividends are available; otherwise price return.
- All configured dividend files contain at least one cash-dividend event.

## Next Gate

`basket_formal_validation_and_overfit_audit`
