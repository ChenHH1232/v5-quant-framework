# Model Performance Addendum

## Identity

- Canonical model: `port_rail_cashflow_value_operating_diagnostic_v55i_business_purity_gate`
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
| total_return_pct | 56.67056658999987 |
| annualized_return_pct | 9.651279528555335 |
| max_drawdown_pct | 20.447924685713993 |
| annualized_volatility_pct | 19.140986668905715 |
| sharpe_ratio | 0.576970668797196 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 17.69464105156686 |
| benchmark_annualized_return_pct | 3.3998960718200966 |
| benchmark_max_drawdown_pct | 38.23109843081313 |
| benchmark_annualized_volatility_pct | 24.149928630603902 |
| excess_return_pct_points | 38.97592553843301 |
| annualized_excess_return_pct | 4.790338200081256 |
| max_drawdown_delta_pct_points | -17.783173745099134 |
| volatility_ratio | 0.7925897820107581 |
| tracking_error_pct | 19.725162978652943 |
| information_ratio | 0.24285417592064903 |
| beta_zero_rf | 0.4805350290223478 |
| alpha_zero_rf_annualized_pct | 8.038786256464869 |
| benchmark_sharpe_ratio | 0.25894278096502643 |

Return source: `local_daily_backtests_port_rail_v55i_business_purity_gate\port_rail_cashflow_value_operating_diagnostic_v55i_business_purity_gate\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
