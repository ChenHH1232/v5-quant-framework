# Model Performance Addendum

## Identity

- Canonical model: `coal_cashflow_cycle_value_v52b_capex_policy`
- Family: `sector_strategy_or_research`
- Role: `example_strategy`
- Parent: `v57f_startup_preload_repaired_baseline`
- Report status: `report_complete_validation_not_independent`
- Accepted/live/deployment: `false / false / false`
- Formal scope: `2021-05-01` to `2026-05-31`

## Benchmark

- Primary: `local_same_pool_or_embedded_benchmark` (primary_benchmark_is_market_exposure_proxy)
- Economic exposure: `local_same_pool_or_embedded_benchmark`
- Coverage: `100.0`; `coverage_pass`

## Validation

- Type: `historical_artifact_reuse`
- Independent: `False`
- Result: `validation_not_independent_or_overlapping`

## Formal Backtest

| Metric | Value |
|---|---:|
| total_return_pct | 133.6935555750006 |
| annualized_return_pct | 19.028410250785367 |
| max_drawdown_pct | 28.113093475664662 |
| annualized_volatility_pct | 28.34383427335399 |
| sharpe_ratio | 0.7565896433079342 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 94.8406676783018 |
| benchmark_annualized_return_pct | 14.668901657533496 |
| benchmark_max_drawdown_pct | 33.18584070796457 |
| benchmark_annualized_volatility_pct | 31.856658652447646 |
| excess_return_pct_points | 38.8528878966988 |
| annualized_excess_return_pct | 2.6835258589296793 |
| max_drawdown_delta_pct_points | -5.0727472322999105 |
| volatility_ratio | 0.8897302941460952 |
| tracking_error_pct | 19.772784909212547 |
| information_ratio | 0.1357181535757955 |
| beta_zero_rf | 0.7031882835342357 |
| alpha_zero_rf_annualized_pct | 8.252047752260879 |
| benchmark_sharpe_ratio | 0.5889232078168668 |

Return source: `local_daily_backtests_coal_v52b\coal_cashflow_cycle_value_v52b_capex_policy\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
