# Model Performance Addendum

## Identity

- Canonical model: `v5c_50w_execution_optimization_test`
- Family: `execution_or_platform`
- Role: `current_artifact`
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
| total_return_pct | 79.7899508999999 |
| annualized_return_pct | 14.042689985765344 |
| max_drawdown_pct | 11.658599446086072 |
| annualized_volatility_pct | 15.53969234098883 |
| sharpe_ratio | 0.9236332174728749 |
| observations | 1125 |
| start_date | 2021-10-08 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 51.0118790617593 |
| benchmark_annualized_return_pct | 9.672688288937747 |
| benchmark_max_drawdown_pct | 17.871287924404477 |
| benchmark_annualized_volatility_pct | 17.63767412910389 |
| excess_return_pct_points | 28.778071838240592 |
| annualized_excess_return_pct | 3.5548592689280145 |
| max_drawdown_delta_pct_points | -6.212688478318405 |
| volatility_ratio | 0.8810511083968161 |
| tracking_error_pct | 8.464873125655876 |
| information_ratio | 0.4199542292197766 |
| beta_zero_rf | 0.7729584673788955 |
| alpha_zero_rf_annualized_pct | 6.006480249019926 |
| benchmark_sharpe_ratio | 0.6122188610288551 |

Return source: `v5c_50w_execution_optimization_test\runs\top7_50w_retry_3d\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
