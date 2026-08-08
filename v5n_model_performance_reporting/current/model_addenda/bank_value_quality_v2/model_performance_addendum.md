# Model Performance Addendum

## Identity

- Canonical model: `bank_value_quality_v2`
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
| total_return_pct | 28.055091964999335 |
| annualized_return_pct | 5.205657156227295 |
| max_drawdown_pct | 17.0467812577062 |
| annualized_volatility_pct | 16.009628564526967 |
| sharpe_ratio | 0.39706957984563307 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 25.16129032258101 |
| benchmark_annualized_return_pct | 4.713335456647205 |
| benchmark_max_drawdown_pct | 27.27272727272715 |
| benchmark_annualized_volatility_pct | 16.892725371868856 |
| excess_return_pct_points | 2.8938016424183246 |
| annualized_excess_return_pct | 0.3245689536960115 |
| max_drawdown_delta_pct_points | -10.225946015020948 |
| volatility_ratio | 0.9477232484456005 |
| tracking_error_pct | 8.641938132686985 |
| information_ratio | 0.037557426206092884 |
| beta_zero_rf | 0.818233911029287 |
| alpha_zero_rf_annualized_pct | 1.4210488075678938 |
| benchmark_sharpe_ratio | 0.3570985380459063 |

Return source: `local_daily_backtests_v2_real_jq\bank_value_quality_v2\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
