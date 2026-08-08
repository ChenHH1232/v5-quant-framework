# Model Performance Addendum

## Identity

- Canonical model: `gas_water_v57b_text_debt_state_guard_v59b`
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
| total_return_pct | 33.29134592499954 |
| annualized_return_pct | 6.074458716157394 |
| max_drawdown_pct | 26.55291703499999 |
| annualized_volatility_pct | 17.389732062533188 |
| sharpe_ratio | 0.42616622344406646 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 32.69423389999997 |
| benchmark_annualized_return_pct | 5.976770676966292 |
| benchmark_max_drawdown_pct | 28.18884289524115 |
| benchmark_annualized_volatility_pct | 21.743814266147574 |
| excess_return_pct_points | 0.5971120249995678 |
| annualized_excess_return_pct | -0.7695016635300717 |
| max_drawdown_delta_pct_points | -1.6359258602411622 |
| volatility_ratio | 0.7997553625909529 |
| tracking_error_pct | 15.338088330268523 |
| information_ratio | -0.05016933316334605 |
| beta_zero_rf | 0.5710096833236812 |
| alpha_zero_rf_annualized_pct | 2.739818489159598 |
| benchmark_sharpe_ratio | 0.37621817419862413 |

Return source: `local_daily_backtests_v59b_gas_water_state_guard\gas_water_v57b_text_debt_state_guard_v59b\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
