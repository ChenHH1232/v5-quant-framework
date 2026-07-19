# Basket Daily Backtest Report

Created at UTC: `2026-07-19T05:51:19+00:00`

## PM Decision

The basket has completed a local daily engineering smoke test. This is not platform replication, paper trading approval, or strategy acceptance.

## Metrics

- `strategy_return`: `0.0455562738`
- `annualized_return`: `1.37160385`
- `benchmark_return`: `0.004781900707`
- `excess_return`: `0.04077437309`
- `max_drawdown`: `0.01271461172`
- `sharpe`: `7.24887543`
- `information_ratio`: `6.826730284`
- `strategy_volatility`: `0.1203341829`
- `benchmark_volatility`: `0.1429711834`
- `max_drawdown_interval`: `2026-07-06,2026-07-10`

## Known Gaps

- This is a basket-level local daily simulation, not platform replication and not strategy acceptance.
- Basket sectors included in this run: bank, utilities_electricity, highway_infrastructure, port_rail_infrastructure.
- Benchmark is a same-pool equal-weight total-return proxy where net cash dividends are available; otherwise price return.
- All configured dividend files contain at least one cash-dividend event.

## Next Gate

`basket_formal_validation_and_overfit_audit`
