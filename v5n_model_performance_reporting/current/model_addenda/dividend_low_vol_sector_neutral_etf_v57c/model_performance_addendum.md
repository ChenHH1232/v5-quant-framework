# Model Performance Addendum

## Identity

- Canonical model: `dividend_low_vol_sector_neutral_etf_v57c`
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
| total_return_pct | 70.80325113999932 |
| annualized_return_pct | 12.74028641028131 |
| max_drawdown_pct | 11.586706783114076 |
| annualized_volatility_pct | 15.649192267695009 |
| sharpe_ratio | 0.8447901827996358 |
| observations | 1125 |
| start_date | 2021-10-08 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 51.0118790617593 |
| benchmark_annualized_return_pct | 9.672688288937747 |
| benchmark_max_drawdown_pct | 17.871287924404477 |
| benchmark_annualized_volatility_pct | 17.63767412910389 |
| excess_return_pct_points | 19.791372078240016 |
| annualized_excess_return_pct | 2.4221672299746206 |
| max_drawdown_delta_pct_points | -6.284581141290401 |
| volatility_ratio | 0.8872594058120344 |
| tracking_error_pct | 7.813944651101023 |
| information_ratio | 0.3099800853635847 |
| beta_zero_rf | 0.7954786978749915 |
| alpha_zero_rf_annualized_pct | 4.630612131560787 |
| benchmark_sharpe_ratio | 0.6122188610288551 |

Return source: `local_daily_backtests_v57c_etf\dividend_low_vol_sector_neutral_etf_v57c\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
