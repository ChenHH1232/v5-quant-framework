# Model Performance Addendum

## Identity

- Canonical model: `v5c_defense_overlay_formal_validation`
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
| total_return_pct | 84.17473203999977 |
| annualized_return_pct | 14.659892549813902 |
| max_drawdown_pct | 11.74890935360361 |
| annualized_volatility_pct | 15.74747102266115 |
| sharpe_ratio | 0.9478112406424722 |
| observations | 1125 |
| start_date | 2021-10-08 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 51.0118790617593 |
| benchmark_annualized_return_pct | 9.672688288937747 |
| benchmark_max_drawdown_pct | 17.871287924404477 |
| benchmark_annualized_volatility_pct | 17.63767412910389 |
| excess_return_pct_points | 33.162852978240466 |
| annualized_excess_return_pct | 4.1275132804517565 |
| max_drawdown_delta_pct_points | -6.122378570800867 |
| volatility_ratio | 0.8928314984953873 |
| tracking_error_pct | 8.642692621317567 |
| information_ratio | 0.47757261090959907 |
| beta_zero_rf | 0.778517588691314 |
| alpha_zero_rf_annualized_pct | 6.519106219492933 |
| benchmark_sharpe_ratio | 0.6122188610288551 |

Return source: `v5c_defense_overlay_formal_validation\current\reproducibility_rerun\v5c_defense_erc_weak_portfolio_equal_fallback_63d\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
