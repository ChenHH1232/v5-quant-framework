# Model Performance Addendum

## Identity

- Canonical model: `bank_high_dividend_sustainability_v3`
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
| total_return_pct | 61.76096459000051 |
| annualized_return_pct | 10.373124844376825 |
| max_drawdown_pct | 17.23813687023211 |
| annualized_volatility_pct | 16.33482528356165 |
| sharpe_ratio | 0.6860339939671231 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 25.16129032258101 |
| benchmark_annualized_return_pct | 4.713335456647205 |
| benchmark_max_drawdown_pct | 27.27272727272715 |
| benchmark_annualized_volatility_pct | 16.892725371868856 |
| excess_return_pct_points | 36.5996742674195 |
| annualized_excess_return_pct | 5.173877896131585 |
| max_drawdown_delta_pct_points | -10.034590402495038 |
| volatility_ratio | 0.9669739443443349 |
| tracking_error_pct | 7.718269447340995 |
| information_ratio | 0.67034170437183 |
| beta_zero_rf | 0.8631409532375741 |
| alpha_zero_rf_annualized_pct | 5.999461966542478 |
| benchmark_sharpe_ratio | 0.3570985380459063 |

Return source: `local_daily_backtests_v3_formal_candidate\bank_high_dividend_sustainability_v3\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
