# Model Performance Addendum

## Identity

- Canonical model: `port_rail_cashflow_value_operating_diagnostic_v55g_repaired_2021`
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
| total_return_pct | 78.52228130999977 |
| annualized_return_pct | 12.629002466052563 |
| max_drawdown_pct | 20.200479055136345 |
| annualized_volatility_pct | 20.09727683149384 |
| sharpe_ratio | 0.6922465115932003 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 17.69464105156686 |
| benchmark_annualized_return_pct | 3.3998960718200966 |
| benchmark_max_drawdown_pct | 38.23109843081313 |
| benchmark_annualized_volatility_pct | 24.149928630603902 |
| excess_return_pct_points | 60.82764025843291 |
| annualized_excess_return_pct | 7.658820099408968 |
| max_drawdown_delta_pct_points | -18.030619375676782 |
| volatility_ratio | 0.8321878353721363 |
| tracking_error_pct | 19.182001639845147 |
| information_ratio | 0.3992711627914759 |
| beta_zero_rf | 0.5308214803290265 |
| alpha_zero_rf_annualized_pct | 10.592804362974805 |
| benchmark_sharpe_ratio | 0.25894278096502643 |

Return source: `local_daily_backtests_port_rail_v55g_repaired_2021\port_rail_cashflow_value_operating_diagnostic_v55g_repaired_2021\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
