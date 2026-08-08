# Model Performance Addendum

## Identity

- Canonical model: `highway_dividend_reviewed_operating_v54g`
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
| total_return_pct | 26.510685879999606 |
| annualized_return_pct | 6.067555909904931 |
| max_drawdown_pct | 10.789605232292576 |
| annualized_volatility_pct | 11.709661942961088 |
| sharpe_ratio | 0.5618572703908284 |
| observations | 1006 |
| start_date | 2022-04-01 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 46.68238701731742 |
| benchmark_annualized_return_pct | 10.072082973914576 |
| benchmark_max_drawdown_pct | 13.942051135184563 |
| benchmark_annualized_volatility_pct | 18.630333146394385 |
| excess_return_pct_points | -20.17170113731781 |
| annualized_excess_return_pct | -4.757514777037259 |
| max_drawdown_delta_pct_points | -3.152445902891987 |
| volatility_ratio | 0.6285267070077764 |
| tracking_error_pct | 15.040544863885497 |
| information_ratio | -0.3163126615486341 |
| beta_zero_rf | 0.37164426617374213 |
| alpha_zero_rf_annualized_pct | 2.3659490025579966 |
| benchmark_sharpe_ratio | 0.6085062131968788 |

Return source: `local_daily_backtests_highway_v54g\highway_dividend_reviewed_operating_v54g\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
