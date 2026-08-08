# Model Performance Addendum

## Identity

- Canonical model: `oil_gas_state_conditioned_ocf_v58g`
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
| total_return_pct | 99.79237083499972 |
| annualized_return_pct | 15.260981925332207 |
| max_drawdown_pct | 21.78184051727403 |
| annualized_volatility_pct | 23.91059926318014 |
| sharpe_ratio | 0.7133000543232177 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | -4.5158417406884315 |
| benchmark_annualized_return_pct | -0.943797992348816 |
| benchmark_max_drawdown_pct | 40.856621886747234 |
| benchmark_annualized_volatility_pct | 17.553087784035885 |
| excess_return_pct_points | 104.30821257568815 |
| annualized_excess_return_pct | 16.465805022397912 |
| max_drawdown_delta_pct_points | -19.074781369473204 |
| volatility_ratio | 1.362187642274897 |
| tracking_error_pct | 24.072974400584123 |
| information_ratio | 0.6839954526765241 |
| beta_zero_rf | 0.4873562739899921 |
| alpha_zero_rf_annualized_pct | 16.768073466696542 |
| benchmark_sharpe_ratio | 0.033591054644267385 |

Return source: `validation_daily_v58g_oil_gas\oil_gas_state_conditioned_ocf_v58g\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
