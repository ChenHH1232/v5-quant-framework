# Model Performance Addendum

## Identity

- Canonical model: `v5c_p0_local_data_gate`
- Family: `governance_or_research_artifact`
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
| total_return_pct | 109.25462597100073 |
| annualized_return_pct | 16.360689026815976 |
| max_drawdown_pct | 11.930340749658807 |
| annualized_volatility_pct | 15.627727473639649 |
| sharpe_ratio | 1.0481050073941298 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 79.0073152516487 |
| benchmark_annualized_return_pct | 12.691730794800037 |
| benchmark_max_drawdown_pct | 17.85070536080258 |
| benchmark_annualized_volatility_pct | 17.563658250923016 |
| excess_return_pct_points | 30.24731071935203 |
| annualized_excess_return_pct | 2.878611599678651 |
| max_drawdown_delta_pct_points | -5.920364611143771 |
| volatility_ratio | 0.8897763353382472 |
| tracking_error_pct | 8.599632838388848 |
| information_ratio | 0.3347365700112801 |
| beta_zero_rf | 0.7759838997421432 |
| alpha_zero_rf_annualized_pct | 5.903027839051835 |
| benchmark_sharpe_ratio | 0.7686831311992974 |

Return source: `v5c_p0_local_data_gate\current\v5c_p0_daily_nav_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
