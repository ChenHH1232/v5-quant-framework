# Model Performance Addendum

## Identity

- Canonical model: `insurance_low_pb_only_v53c`
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
| total_return_pct | 42.027341434999684 |
| annualized_return_pct | 7.465363616451892 |
| max_drawdown_pct | 33.01671224901054 |
| annualized_volatility_pct | 26.463573993738148 |
| sharpe_ratio | 0.4031996295111 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | -3.0243054613836695 |
| benchmark_annualized_return_pct | -0.62821972236633 |
| benchmark_max_drawdown_pct | 42.43261392518046 |
| benchmark_annualized_volatility_pct | 24.49339200404453 |
| excess_return_pct_points | 45.05164689638335 |
| annualized_excess_return_pct | 8.318157350094625 |
| max_drawdown_delta_pct_points | -9.415901676169923 |
| volatility_ratio | 1.0804372864880571 |
| tracking_error_pct | 8.447401534627156 |
| information_ratio | 0.9847001253577519 |
| beta_zero_rf | 1.0241995610967467 |
| alpha_zero_rf_annualized_pct | 8.261241292082097 |
| benchmark_sharpe_ratio | 0.09602368995408249 |

Return source: `local_daily_backtests_insurance_v53c\insurance_low_pb_only_v53c\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
