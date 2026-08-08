# Model Performance Addendum

## Identity

- Canonical model: `port_rail_cashflow_value_operating_diagnostic_v55c`
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
| total_return_pct | 63.8572741699998 |
| annualized_return_pct | 10.665151236121972 |
| max_drawdown_pct | 20.197683956099187 |
| annualized_volatility_pct | 19.16820551119892 |
| sharpe_ratio | 0.6245408008288242 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 17.69464105156686 |
| benchmark_annualized_return_pct | 3.3998960718200966 |
| benchmark_max_drawdown_pct | 38.23109843081313 |
| benchmark_annualized_volatility_pct | 24.149928630603902 |
| excess_return_pct_points | 46.162633118432936 |
| annualized_excess_return_pct | 5.717876740700166 |
| max_drawdown_delta_pct_points | -18.03341447471394 |
| volatility_ratio | 0.7937168595565988 |
| tracking_error_pct | 19.832282538061012 |
| information_ratio | 0.28831158136874746 |
| beta_zero_rf | 0.47779622594394616 |
| alpha_zero_rf_annualized_pct | 8.983451764317214 |
| benchmark_sharpe_ratio | 0.25894278096502643 |

Return source: `local_daily_backtests_port_rail_v55c\port_rail_cashflow_value_operating_diagnostic_v55c\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
