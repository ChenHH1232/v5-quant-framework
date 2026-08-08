# Model Performance Addendum

## Identity

- Canonical model: `v57f_startup_preload_repaired_baseline`
- Family: `v57f_baseline`
- Role: `baseline`
- Parent: `self`
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
| total_return_pct | 109.2546259710054 |
| annualized_return_pct | 16.36068902681651 |
| max_drawdown_pct | 11.930340749658752 |
| annualized_volatility_pct | 15.627727473639597 |
| sharpe_ratio | 1.0481050073941274 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 109.2546259710054 |
| benchmark_annualized_return_pct | 16.36068902681651 |
| benchmark_max_drawdown_pct | 11.930340749658752 |
| benchmark_annualized_volatility_pct | 15.627727473639597 |
| excess_return_pct_points | 0.0 |
| annualized_excess_return_pct | 0.0 |
| max_drawdown_delta_pct_points | 0.0 |
| volatility_ratio | 1.0 |
| tracking_error_pct | 0.0 |
| information_ratio | not_available |
| beta_zero_rf | 1.0 |
| alpha_zero_rf_annualized_pct | 0.0 |
| benchmark_sharpe_ratio | 1.0481050073941274 |

Return source: `v5f_structural_rough_screen\current\v5f_structural_rough_screen_daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
