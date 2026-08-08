# Model Performance Addendum

## Identity

- Canonical model: `v5j_momentum_daily_price_volume_sell`
- Family: `momentum_overlay`
- Role: `current_artifact`
- Parent: `v57f_startup_preload_repaired_baseline`
- Report status: `report_complete_validation_not_independent`
- Accepted/live/deployment: `false / false / false`
- Formal scope: `2021-05-01` to `2026-05-31`

## Benchmark

- Primary: `not_available` (benchmark_data_unavailable)
- Economic exposure: `not_available`
- Coverage: `0.0`; `benchmark_coverage_insufficient`

## Validation

- Type: `historical_artifact_reuse`
- Independent: `False`
- Result: `validation_not_independent_or_overlapping`

## Formal Backtest

| Metric | Value |
|---|---:|
| total_return_pct | not_available |
| annualized_return_pct | not_available |
| max_drawdown_pct | not_available |
| annualized_volatility_pct | not_available |
| sharpe_ratio | not_available |
| observations | not_available |
| start_date | not_available |
| end_date | not_available |
| benchmark_total_return_pct | not_available |
| benchmark_annualized_return_pct | not_available |
| benchmark_max_drawdown_pct | not_available |
| benchmark_annualized_volatility_pct | not_available |
| excess_return_pct_points | not_available |
| annualized_excess_return_pct | not_available |
| max_drawdown_delta_pct_points | not_available |
| volatility_ratio | not_available |
| tracking_error_pct | not_available |
| information_ratio | not_available |
| beta_zero_rf | not_available |
| alpha_zero_rf_annualized_pct | not_available |

Return source: `v5j_momentum_daily_price_volume_sell\current\v5j_daily_pv_momentum_formal_daily_nav.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
