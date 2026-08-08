# Model Performance Addendum

## Identity

- Canonical model: `highway_dividend_reviewed_operating_v54h_repaired_2021`
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
| total_return_pct | 106.61232162500025 |
| annualized_return_pct | 16.057644399251856 |
| max_drawdown_pct | 14.910373998488103 |
| annualized_volatility_pct | 17.559213843280137 |
| sharpe_ratio | 0.9360986826677815 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 58.10407689999985 |
| benchmark_annualized_return_pct | 9.856422146060485 |
| benchmark_max_drawdown_pct | 14.167320629065294 |
| benchmark_annualized_volatility_pct | 18.675728440795673 |
| excess_return_pct_points | 48.508244725000395 |
| annualized_excess_return_pct | 5.2884389084021395 |
| max_drawdown_delta_pct_points | 0.7430533694228085 |
| volatility_ratio | 0.9402157403897244 |
| tracking_error_pct | 8.093680589929233 |
| information_ratio | 0.653403460841093 |
| beta_zero_rf | 0.8480938602351145 |
| alpha_zero_rf_annualized_pct | 6.981997629029866 |
| benchmark_sharpe_ratio | 0.5969629551166936 |

Return source: `local_daily_backtests_highway_v54h_repaired_2021_final\highway_dividend_reviewed_operating_v54h_repaired_2021\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
