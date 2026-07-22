# V5a.9 Food/Beverage Local Daily Engineering Simulation

## Decision

Engineering gate: `engineering_local_daily_simulation_needs_review`

Next gate: `repair_signal_coverage_or_rebalance_order_health_before_any_promotion`

This is a local daily Engineering smoke test only. It does not promote the strategy into V57f, platform replication, or accepted strategy status.

## Execution Health

- Rebalance signals: 18
- Normal rebalance count: 18
- Needs review: True
- First executed order date: 2022-01-04
- First position date: 2022-01-04
- Partial skipped-order rebalance count: 1
- Partial skipped-order dates: 2024-10-08
- Startup gap classification: `panel_has_no_pit_rebalance_rows_before_first_signal`

## Local Metrics

- Strategy return: 4.65%
- Benchmark return: -3.34%
- Excess return: 7.99%
- Max drawdown: 45.06%
- Sharpe: 0.162

## PM Rules

- This is a local Engineering smoke test, not JoinQuant platform replication.
- Only food_beverage_packaged_food_ocf_quality_v5a9a is allowed into this runner.
- Do not tune factor weights, selection count, timing or packaged-food subindustry membership.
- No V57f inclusion can be made from this run.
- 2021-2026 remains a platform-confirmation and engineering window, not clean out-of-sample acceptance evidence.
- If a rebalance signal exists but no order or no holding appears, stop before any platform replication.
- Partial skipped orders from price-limit, suspension or lot/cash constraints must be explained before any promotion.
