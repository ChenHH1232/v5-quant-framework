# Model Performance Addendum

## Identity

- Canonical model: `v5c_sleeve_weighting_diagnostic`
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
| total_return_pct | 5231.917954291955 |
| annualized_return_pct | 16.003292463742547 |
| max_drawdown_pct | 12.714247651474897 |
| annualized_volatility_pct | 16.570968581196475 |
| sharpe_ratio | 0.9788797890347737 |
| observations | 6750 |
| start_date | 2021-10-08 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 1085.9507921313468 |
| benchmark_annualized_return_pct | 9.672688288937724 |
| benchmark_max_drawdown_pct | 17.871287924404477 |
| benchmark_annualized_volatility_pct | 17.631139478763227 |
| excess_return_pct_points | 4145.967162160608 |
| annualized_excess_return_pct | 5.4228694623453775 |
| max_drawdown_delta_pct_points | -5.15704027292958 |
| volatility_ratio | 0.9398694055569277 |
| tracking_error_pct | 9.1329063847508 |
| information_ratio | 0.5937725882529503 |
| beta_zero_rf | 0.8075159509071571 |
| alpha_zero_rf_annualized_pct | 7.501334700142095 |
| benchmark_sharpe_ratio | 0.6124457684385323 |

Return source: `v5c_sleeve_weighting_diagnostic\current\v5c_sleeve_weighting_daily_nav.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
