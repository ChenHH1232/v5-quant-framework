# Model Performance Addendum

## Identity

- Canonical model: `v5c_risk_budget_overlay_engineering_comparison`
- Family: `governance_or_research_artifact`
- Role: `current_artifact`
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
| total_return_pct | 81.41640295000003 |
| annualized_return_pct | 14.272978567948712 |
| max_drawdown_pct | 11.748909353603587 |
| annualized_volatility_pct | 15.64564902248629 |
| sharpe_ratio | 0.9313269875494081 |
| observations | 1125 |
| start_date | 2021-10-08 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 51.0118790617593 |
| benchmark_annualized_return_pct | 9.672688288937747 |
| benchmark_max_drawdown_pct | 17.871287924404477 |
| benchmark_annualized_volatility_pct | 17.63767412910389 |
| excess_return_pct_points | 30.404523888240732 |
| annualized_excess_return_pct | 3.773098405849408 |
| max_drawdown_delta_pct_points | -6.12237857080089 |
| volatility_ratio | 0.8870585150833147 |
| tracking_error_pct | 8.495671125298829 |
| information_ratio | 0.4441201113133592 |
| beta_zero_rf | 0.7774297881665941 |
| alpha_zero_rf_annualized_pct | 6.176437541975191 |
| benchmark_sharpe_ratio | 0.6122188610288551 |

Return source: `v5c_risk_budget_overlay_engineering_comparison\runs\v5c_risk_budget_equal_reference\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
