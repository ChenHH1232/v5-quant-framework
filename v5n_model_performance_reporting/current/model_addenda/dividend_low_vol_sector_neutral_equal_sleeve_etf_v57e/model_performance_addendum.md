# Model Performance Addendum

## Identity

- Canonical model: `dividend_low_vol_sector_neutral_equal_sleeve_etf_v57e`
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
| total_return_pct | 83.066216125 |
| annualized_return_pct | 14.504943797711721 |
| max_drawdown_pct | 11.748909353603587 |
| annualized_volatility_pct | 15.587517413627069 |
| sharpe_ratio | 0.9472385561690945 |
| observations | 1125 |
| start_date | 2021-10-08 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 51.0118790617593 |
| benchmark_annualized_return_pct | 9.672688288937747 |
| benchmark_max_drawdown_pct | 17.871287924404477 |
| benchmark_annualized_volatility_pct | 17.63767412910389 |
| excess_return_pct_points | 32.054337063240695 |
| annualized_excess_return_pct | 3.966980722626629 |
| max_drawdown_delta_pct_points | -6.12237857080089 |
| volatility_ratio | 0.8837626378359117 |
| tracking_error_pct | 8.511777469109196 |
| information_ratio | 0.466057851843934 |
| beta_zero_rf | 0.7740713091179562 |
| alpha_zero_rf_annualized_pct | 6.406585107677511 |
| benchmark_sharpe_ratio | 0.6122188610288551 |

Return source: `local_daily_backtests_v57e_etf\dividend_low_vol_sector_neutral_equal_sleeve_etf_v57e\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
