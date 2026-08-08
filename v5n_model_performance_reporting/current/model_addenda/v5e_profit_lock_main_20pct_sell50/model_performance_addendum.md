# Model Performance Addendum

## Identity

- Canonical model: `v5e_profit_lock_main_20pct_sell50`
- Family: `governance_or_research_artifact`
- Role: `historical_closeout_forward_only`
- Parent: `v57f_startup_preload_repaired_baseline`
- Report status: `archived_or_superseded`
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
| total_return_pct | 109.27997033599985 |
| annualized_return_pct | 16.363580997611106 |
| max_drawdown_pct | 11.32306593274266 |
| annualized_volatility_pct | 14.58551644438483 |
| sharpe_ratio | 1.1124075139262397 |
| observations | 1228 |
| start_date | 2021-05-06 |
| end_date | 2026-05-29 |
| benchmark_total_return_pct | 79.0073152516487 |
| benchmark_annualized_return_pct | 12.691730794800037 |
| benchmark_max_drawdown_pct | 17.85070536080258 |
| benchmark_annualized_volatility_pct | 17.563658250923016 |
| excess_return_pct_points | 30.272655084351143 |
| annualized_excess_return_pct | 2.7241502675945375 |
| max_drawdown_delta_pct_points | -6.527639428059919 |
| volatility_ratio | 0.8304372720084281 |
| tracking_error_pct | 8.38951600560598 |
| information_ratio | 0.32470887066360277 |
| beta_zero_rf | 0.730731888856191 |
| alpha_zero_rf_annualized_pct | 6.35950882955181 |
| benchmark_sharpe_ratio | 0.7686831311992974 |

Return source: `v5e_limited_engineering_loop\current\runs\v5e_profit_lock_main_20pct_sell50\daily_returns.csv`.

## Execution Evidence

Any local price/NAV series is separate from a complete target-to-order-to-fill-to-position-to-cash contract. QMT no-order evidence is not treated as fill evidence.

## Current Conclusion

`reporting_only_not_strategy_promotion`
