# Model Performance Addendum

## Identity

- Canonical model: `dividend_low_vol_sector_adaptive_etf_v57b`
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
| total_return_pct | 53.873681154999844 |
| annualized_return_pct | 10.134862257887288 |
| max_drawdown_pct | 12.194607133020119 |
| annualized_volatility_pct | 15.8669294697064 |
| sharpe_ratio | 0.6879712760455893 |
| observations | 1125 |
| start_date | 2021-10-08 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 51.0118790617593 |
| benchmark_annualized_return_pct | 9.672688288937747 |
| benchmark_max_drawdown_pct | 17.871287924404477 |
| benchmark_annualized_volatility_pct | 17.63767412910389 |
| excess_return_pct_points | 2.8618020932405415 |
| annualized_excess_return_pct | 0.11787494768118673 |
| max_drawdown_delta_pct_points | -5.676680791384358 |
| volatility_ratio | 0.899604412325796 |
| tracking_error_pct | 7.37738297583854 |
| information_ratio | 0.015977881054465477 |
| beta_zero_rf | 0.8171674212917514 |
| alpha_zero_rf_annualized_pct | 2.092122481296464 |
| benchmark_sharpe_ratio | 0.6122188610288551 |

Return source: `local_daily_backtests_v57b_etf\dividend_low_vol_sector_adaptive_etf_v57b\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
