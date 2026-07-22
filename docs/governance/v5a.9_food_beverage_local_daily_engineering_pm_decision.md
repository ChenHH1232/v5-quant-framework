# V5a.9 Food/Beverage Local Daily Engineering PM Decision

Date: 2026-07-22

Layer: `engineering_smoke_test`

Owner: Project Manager Agent

## Decision

Engineering Agent ran the local JoinQuant-like daily simulation for the frozen V5a.9 candidate:

`food_beverage_packaged_food_ocf_quality_v5a9a`

The run is complete, but the candidate is **not promoted**.

Current status:

`engineering_local_daily_simulation_needs_review`

Next gate:

`repair_signal_coverage_or_rebalance_order_health_before_any_promotion`

## Flow Table

| Stage | Owner | Input | Action | Output | Gate | Status |
| ---: | --- | --- | --- | --- | --- | --- |
| 1 | Project Manager Agent | V5a.9 Research repair packet | Confirm only `food_beverage_packaged_food_ocf_quality_v5a9a` may enter Engineering | Engineering scope | `no_tuning_no_joinquant` | completed |
| 2 | Engineering Agent | Frozen spec, PIT panel, real daily prices, cash-dividend file, benchmark | Run local daily JoinQuant-like simulation | Daily NAV, holdings, trades, dividends, signals | `engineering_smoke_test` | completed |
| 3 | Engineering Agent | Rebalance signals + trades + holdings | Generate `rebalance_order_health` | Order-health packet | every signal checked | completed |
| 4 | Project Manager Agent | Local daily summary and order-health packet | Apply promotion gate | PM decision | no promotion if partial skipped orders exist | blocked |

## Inputs

- Spec: `validation_formal_v5a9_food_beverage_research_repair/specs/food_beverage_packaged_food_ocf_quality_v5a9a.json`
- PIT panel: `validation_formal_v5a9_food_beverage_research_repair/panels/food_beverage_packaged_food_ocf_quality_v5a9a.csv`
- Real daily prices: `数据库/processed/food_beverage_v5a5_joinquant_real_daily_prices.csv`
- Cash dividends: `数据库/processed/food_beverage_v5a5_joinquant_cash_dividends.csv`
- Benchmark: `数据库/processed/food_beverage_v5a5_joinquant_real_benchmark_prices.csv`

## Outputs

`local_daily_backtests_food_beverage_v5a9/food_beverage_packaged_food_ocf_quality_v5a9a/`

Required files were generated:

- `summary.json`
- `daily_returns.csv`
- `holdings.csv`
- `trades.csv`
- `dividends.csv`
- `rebalance_signals.csv`
- `rebalance_order_health.csv`
- `engineering_local_daily_simulation_report.md`

## Local Daily Result

Headline metrics:

| Metric | Value |
| --- | ---: |
| Strategy return | 4.65% |
| Benchmark return | -3.34% |
| Excess return | 7.99% |
| Max drawdown | 45.06% |
| Sharpe | 0.162 |

These metrics are not acceptance evidence.

## Execution Health

Order-health summary:

| Check | Result |
| --- | --- |
| Rebalance signals | 18 |
| Missing daily rebalance rows | 0 |
| No-order / no-position rebalance dates | 0 |
| Leading no-order / no-position dates | 0 |
| First executed order date | 2022-01-04 |
| First position date | 2022-01-04 |
| Partial skipped-order rebalance count | 1 |
| Partial skipped-order date | 2024-10-08 |

The 2024-10-08 rebalance had three skipped buy orders due to price-limit constraints:

- `600305.XSHG`
- `002847.XSHE`
- `002495.XSHE`

Therefore the run is not a clean Engineering pass.

## 2021 Startup Gap

The requested simulation window starts on 2021-05-01, but the candidate PIT signal panel first has rebalance rows on 2022-01-04.

PM classification:

`panel_has_no_pit_rebalance_rows_before_first_signal`

This is a Research data-window limitation, not an order execution failure. Engineering must not synthesize missing 2021 signals.

## PM Interpretation

This run proves:

- the frozen V5a.9a candidate can be simulated locally;
- real daily open / close execution data are available;
- the runner can output cash, holdings, trades, dividends, rebalance signals and order health;
- there is no “signal exists but no order” failure;
- 2021 absence is caused by the PIT panel start date.

This run does not prove:

- the strategy is deployable;
- the candidate can enter V57f;
- the candidate can start JoinQuant platform replication;
- the 2024-10-08 partial-limit issue can be ignored.

## Blocked Actions

- Do not tune factor weights.
- Do not change selection count.
- Do not change subindustry membership.
- Do not use 2021-2026 returns as strategy acceptance evidence.
- Do not start JoinQuant replication before PM resolves the partial skipped-order policy.
- Do not add food/beverage to V57f.

## Next Step

Return to PM / Engineering contract review:

`repair_signal_coverage_or_rebalance_order_health_before_any_promotion`

Allowed next work:

- document whether partial price-limit skips are acceptable in local sleeve observation;
- if not acceptable, keep food/beverage as `engineering_needs_review`;
- if acceptable, PM may create a separate observation-only paper tracking gate without changing the strategy.
