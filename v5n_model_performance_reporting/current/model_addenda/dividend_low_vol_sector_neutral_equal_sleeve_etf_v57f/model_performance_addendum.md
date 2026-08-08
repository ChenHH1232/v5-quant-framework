# Model Performance Addendum

## Identity

- Canonical model: `dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f`
- Family: `v57f_baseline`
- Role: `example_strategy`
- Parent: `v57f_startup_preload_repaired_baseline`
- Report status: `duplicate_or_alias_of_canonical_model`
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
| total_return_pct | 81.41640295000003 |
| annualized_return_pct | 13.001305719749068 |
| max_drawdown_pct | 11.748909353603587 |
| annualized_volatility_pct | 14.976736686516515 |
| sharpe_ratio | 0.8913181142516612 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 78.68231031660487 |
| benchmark_annualized_return_pct | 12.649713607781932 |
| benchmark_max_drawdown_pct | 17.87128792440442 |
| benchmark_annualized_volatility_pct | 17.573203663678644 |
| excess_return_pct_points | 2.7340926333951643 |
| annualized_excess_return_pct | -0.11627495352364593 |
| max_drawdown_delta_pct_points | -6.122378570800834 |
| volatility_ratio | 0.8522485127439419 |
| tracking_error_pct | 9.504058011001192 |
| information_ratio | -0.012234242824386666 |
| beta_zero_rf | 0.7169169958606469 |
| alpha_zero_rf_annualized_pct | 3.695525921331245 |
| benchmark_sharpe_ratio | 0.766241142611016 |

Return source: `v5_startup_preload_repair\current\runs\v57f_repaired_daily_backtest\dividend_low_vol_sector_neutral_equal_sleeve_etf_v57f\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
