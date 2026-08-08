# Model Performance Addendum

## Identity

- Canonical model: `home_appliances_ocf_quality_v5a5c`
- Family: `governance_or_research_artifact`
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
| total_return_pct | 106.37364557999973 |
| annualized_return_pct | 16.030119356517414 |
| max_drawdown_pct | 30.18167637542778 |
| annualized_volatility_pct | 23.430220439680372 |
| sharpe_ratio | 0.7516496439509227 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | -3.339156155159262 |
| benchmark_annualized_return_pct | -0.6945127819630081 |
| benchmark_max_drawdown_pct | 40.85662188674719 |
| benchmark_annualized_volatility_pct | 17.544375773533368 |
| excess_return_pct_points | 109.71280173515899 |
| annualized_excess_return_pct | 16.771878851472575 |
| max_drawdown_delta_pct_points | -10.674945511319411 |
| volatility_ratio | 1.3354832763572082 |
| tracking_error_pct | 19.07167671089325 |
| information_ratio | 0.8794129171607082 |
| beta_zero_rf | 0.8009150343488002 |
| alpha_zero_rf_annualized_pct | 16.93899833681012 |
| benchmark_sharpe_ratio | 0.04784655838089968 |

Return source: `local_daily_backtests_home_appliances_v5a5e\home_appliances_ocf_quality_v5a5c\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
