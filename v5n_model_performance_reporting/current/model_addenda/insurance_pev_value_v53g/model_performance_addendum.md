# Model Performance Addendum

## Identity

- Canonical model: `insurance_pev_value_v53g`
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
| total_return_pct | 29.88786031499957 |
| annualized_return_pct | 5.512909984711856 |
| max_drawdown_pct | 34.19615990892812 |
| annualized_volatility_pct | 30.16721030426085 |
| sharpe_ratio | 0.32737786423343557 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | -3.0243054613836695 |
| benchmark_annualized_return_pct | -0.62821972236633 |
| benchmark_max_drawdown_pct | 42.43261392518046 |
| benchmark_annualized_volatility_pct | 24.49339200404453 |
| excess_return_pct_points | 32.91216577638324 |
| annualized_excess_return_pct | 7.524130999569631 |
| max_drawdown_delta_pct_points | -8.236454016252345 |
| volatility_ratio | 1.2316468988566147 |
| tracking_error_pct | 9.840292935826549 |
| information_ratio | 0.7646246965042847 |
| beta_zero_rf | 1.1777743180533964 |
| alpha_zero_rf_annualized_pct | 7.106015424703882 |
| benchmark_sharpe_ratio | 0.09602368995408249 |

Return source: `local_daily_backtests_insurance_v53g\insurance_pev_value_v53g\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
