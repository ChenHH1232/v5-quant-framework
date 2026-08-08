# Model Performance Addendum

## Identity

- Canonical model: `v5d_l4_rebalance_neighborhood_order_completion`
- Family: `execution_or_platform`
- Role: `current_artifact`
- Parent: `v57f_startup_preload_repaired_baseline`
- Report status: `archived_or_superseded`
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
| total_return_pct | 79.12861239500037 |
| annualized_return_pct | 13.948588905623538 |
| max_drawdown_pct | 11.679482725028478 |
| annualized_volatility_pct | 15.682158462355664 |
| sharpe_ratio | 0.9114037564877644 |
| observations | 1125 |
| start_date | 2021-10-08 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 51.0118790617593 |
| benchmark_annualized_return_pct | 9.672688288937747 |
| benchmark_max_drawdown_pct | 17.871287924404477 |
| benchmark_annualized_volatility_pct | 17.63767412910389 |
| excess_return_pct_points | 28.116733333241072 |
| annualized_excess_return_pct | 3.494661365909245 |
| max_drawdown_delta_pct_points | -6.191805199375999 |
| volatility_ratio | 0.8891284841507854 |
| tracking_error_pct | 8.463979469677223 |
| information_ratio | 0.412886323558452 |
| beta_zero_rf | 0.7801319858547298 |
| alpha_zero_rf_annualized_pct | 5.868821855872324 |
| benchmark_sharpe_ratio | 0.6122188610288551 |

Return source: `v5d_l4_rebalance_neighborhood_order_completion\current\runs\v57f_frozen\l4_d0_d1_completion\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
