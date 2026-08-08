# Model Performance Addendum

## Identity

- Canonical model: `dividend_low_vol_ocf_enhanced_etf_v57`
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
| total_return_pct | 81.99145290500081 |
| annualized_return_pct | 14.354016272900827 |
| max_drawdown_pct | 12.36446482537923 |
| annualized_volatility_pct | 15.06458710784634 |
| sharpe_ratio | 0.9659868358433509 |
| observations | 1125 |
| start_date | 2021-10-08 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 51.0118790617593 |
| benchmark_annualized_return_pct | 9.672688288937747 |
| benchmark_max_drawdown_pct | 17.871287924404477 |
| benchmark_annualized_volatility_pct | 17.63767412910389 |
| excess_return_pct_points | 30.97957384324151 |
| annualized_excess_return_pct | 3.7540760670769306 |
| max_drawdown_delta_pct_points | -5.506823099025247 |
| volatility_ratio | 0.8541141534635962 |
| tracking_error_pct | 8.569842110223442 |
| information_ratio | 0.43805661980615546 |
| beta_zero_rf | 0.7467144564044048 |
| alpha_zero_rf_annualized_pct | 6.4890829420931775 |
| benchmark_sharpe_ratio | 0.6122188610288551 |

Return source: `local_daily_backtests_v57_etf\dividend_low_vol_ocf_enhanced_etf_v57\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
