# Model Performance Addendum

## Identity

- Canonical model: `v5c_topx_capital_rigorous_test`
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
| total_return_pct | 34.33718419999976 |
| annualized_return_pct | 6.835591285333464 |
| max_drawdown_pct | 7.90530772529785 |
| annualized_volatility_pct | 9.804195163969458 |
| sharpe_ratio | 0.7234983464233142 |
| observations | 1125 |
| start_date | 2021-10-08 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 51.0118790617593 |
| benchmark_annualized_return_pct | 9.672688288937747 |
| benchmark_max_drawdown_pct | 17.871287924404477 |
| benchmark_annualized_volatility_pct | 17.63767412910389 |
| excess_return_pct_points | -16.67469486175954 |
| annualized_excess_return_pct | -3.7047977773747305 |
| max_drawdown_delta_pct_points | -9.965980199106628 |
| volatility_ratio | 0.555866668825204 |
| tracking_error_pct | 10.509271190075388 |
| information_ratio | -0.35252661296564697 |
| beta_zero_rf | 0.4769798916833634 |
| alpha_zero_rf_annualized_pct | 1.94283442346525 |
| benchmark_sharpe_ratio | 0.6122188610288551 |

Return source: `v5c_topx_capital_rigorous_test\runs\v5c_top3_per_sleeve_capital_50w_open_execution\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
