# Model Performance Addendum

## Identity

- Canonical model: `gas_water_value_serviceability_v57b`
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
| total_return_pct | 27.849083199999527 |
| annualized_return_pct | 5.1709029046660415 |
| max_drawdown_pct | 26.55291703499999 |
| annualized_volatility_pct | 20.094683506022843 |
| sharpe_ratio | 0.3517303908253093 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 32.69423389999997 |
| benchmark_annualized_return_pct | 5.976770676966292 |
| benchmark_max_drawdown_pct | 28.18884289524115 |
| benchmark_annualized_volatility_pct | 21.743814266147574 |
| excess_return_pct_points | -4.8451507000004455 |
| annualized_excess_return_pct | -1.112507220239725 |
| max_drawdown_delta_pct_points | -1.6359258602411622 |
| volatility_ratio | 0.9241563260272958 |
| tracking_error_pct | 11.086068852423002 |
| information_ratio | -0.10035182308980269 |
| beta_zero_rf | 0.7970592944489028 |
| alpha_zero_rf_annualized_pct | 0.5476326013518236 |
| benchmark_sharpe_ratio | 0.37621817419862413 |

Return source: `local_daily_backtests_v57_gas_water\gas_water_value_serviceability_v57b\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
