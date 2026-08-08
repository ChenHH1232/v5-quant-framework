# Model Performance Addendum

## Identity

- Canonical model: `bank_value_15y`
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
| total_return_pct | 51.01249673000012 |
| annualized_return_pct | 8.963745438796433 |
| max_drawdown_pct | 17.184236890455562 |
| annualized_volatility_pct | 17.093586516548864 |
| sharpe_ratio | 0.5877694719662523 |
| observations | 1210 |
| start_date | 2021-05-06 |
| end_date | 2026-04-30 |
| benchmark_total_return_pct | 28.225806451613302 |
| benchmark_annualized_return_pct | 5.314324586299768 |
| benchmark_max_drawdown_pct | 27.27272727272715 |
| benchmark_annualized_volatility_pct | 16.959574270658326 |
| excess_return_pct_points | 22.78669027838682 |
| annualized_excess_return_pct | 3.4309534638459906 |
| max_drawdown_delta_pct_points | -10.088490382271587 |
| volatility_ratio | 1.0079018637939745 |
| tracking_error_pct | 8.26508436017165 |
| information_ratio | 0.41511414939444563 |
| beta_zero_rf | 0.8891827895396488 |
| alpha_zero_rf_annualized_pct | 4.1641350727277135 |
| benchmark_sharpe_ratio | 0.39011208367664785 |

Return source: `local_daily_backtests\bank_value_15y\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
