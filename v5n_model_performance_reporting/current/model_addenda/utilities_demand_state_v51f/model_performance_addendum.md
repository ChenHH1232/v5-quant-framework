# Model Performance Addendum

## Identity

- Canonical model: `utilities_demand_state_v51f`
- Family: `governance_or_research_artifact`
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
| total_return_pct | 230.70306241499966 |
| annualized_return_pct | 27.818822731911432 |
| max_drawdown_pct | 26.765719482392893 |
| annualized_volatility_pct | 24.178445073235803 |
| sharpe_ratio | 1.1366713411934342 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 15.855785719669967 |
| benchmark_annualized_return_pct | 3.0662956309662315 |
| benchmark_max_drawdown_pct | 20.25487948610978 |
| benchmark_annualized_volatility_pct | 16.607654281025432 |
| excess_return_pct_points | 214.8472766953297 |
| annualized_excess_return_pct | 23.08205635877346 |
| max_drawdown_delta_pct_points | 6.510839996283114 |
| volatility_ratio | 1.4558615361387999 |
| tracking_error_pct | 16.280853885650355 |
| information_ratio | 1.4177423690975792 |
| beta_zero_rf | 1.079250497711373 |
| alpha_zero_rf_annualized_pct | 22.733283696876327 |
| benchmark_sharpe_ratio | 0.26499162109975727 |

Return source: `local_daily_backtests_utilities_v51f\utilities_demand_state_v51f\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
