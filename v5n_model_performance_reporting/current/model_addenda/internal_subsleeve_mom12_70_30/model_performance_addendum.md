# Model Performance Addendum

## Identity

- Canonical model: `internal_subsleeve_mom12_70_30`
- Family: `momentum_overlay`
- Role: `primary_forward_paper_candidate_not_accepted`
- Parent: `v57f_startup_preload_repaired_baseline`
- Report status: `report_complete_validation_not_independent`
- Accepted/live/deployment: `false / false / false`
- Formal scope: `2021-05-01` to `2026-05-31`

## Benchmark

- Primary: `v57f_startup_preload_repaired_baseline` (primary_benchmark_is_parent_strategy)
- Economic exposure: `static_proxy_basket_not_separately_available`
- Coverage: `100.0`; `coverage_pass`

## Validation

- Type: `historical_artifact_reuse`
- Independent: `False`
- Result: `validation_not_independent_or_overlapping`

## Formal Backtest

| Metric | Value |
|---|---:|
| total_return_pct | 120.68673469806517 |
| annualized_return_pct | 17.637805267950224 |
| max_drawdown_pct | 11.881865312548435 |
| annualized_volatility_pct | 15.683565261388917 |
| sharpe_ratio | 1.1145687285879482 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 109.2546259710054 |
| benchmark_annualized_return_pct | 16.36068902681651 |
| benchmark_max_drawdown_pct | 11.930340749658752 |
| benchmark_annualized_volatility_pct | 15.627727473639597 |
| excess_return_pct_points | 11.43210872705977 |
| annualized_excess_return_pct | 1.1009119737999238 |
| max_drawdown_delta_pct_points | -0.04847543711031754 |
| volatility_ratio | 1.003572994720026 |
| tracking_error_pct | 1.5118980331136311 |
| information_ratio | 0.7281654911162793 |
| beta_zero_rf | 0.9988996203525417 |
| alpha_zero_rf_annualized_pct | 1.1189356415964908 |
| benchmark_sharpe_ratio | 1.0481050073941274 |

Return source: `v5f_structural_rough_screen\current\v5f_structural_rough_screen_daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
