# V5.7b Gas / Water Coverage Policy Freeze V1

Date: 2026-07-19

Strategy:

```text
gas_water_value_serviceability_v57b
```

## PM Decision

Freeze V5.7b with the conservative coverage rule:

```text
minimum_rebalance_coverage_ratio = 0.80
```

This means:

```text
2021-07-01 is skipped.
The first actual local daily rebalance is 2021-10-08.
```

## Why Not Adopt 70%

A diagnostic run with:

```text
minimum_rebalance_coverage_ratio = 0.70
```

included 2021-07-01 and materially improved the backtest result.

PM interpretation:

```text
Because we observed that performance difference before freezing the rule,
upgrading 70% into the official rule now would create post-hoc selection risk.
```

Therefore, the 70% run is retained only as:

```text
coverage_sensitivity_diagnostic
```

It must not be used as:

```text
formal strategy evidence
platform replication script setting
paper trading setting
accepted strategy support
```

## Frozen Engineering Baseline

Use:

```text
local_daily_backtests_v57_gas_water/gas_water_value_serviceability_v57b/
```

Frozen inputs:

| Input | Path |
| --- | --- |
| Strategy spec | `examples/gas_water_value_serviceability_v57b_strategy.json` |
| PIT panel | `数据库/processed/gas_water_financial_evidence_v57/panel_with_direct_financial_evidence.csv` |
| Daily execution price | `数据库/processed/gas_water_v57b_joinquant_real_daily_prices.csv` |
| Cash dividends | `数据库/processed/gas_water_v57b_joinquant_cash_dividends.csv` |
| Benchmark | `数据库/processed/gas_water_v57b_same_pool_equal_weight_benchmark.csv` |
| Benchmark id | `gas_water_same_pool_equal_weight` |
| Coverage ratio | `0.80` |
| Value-trap guard mode | `disabled` |
| Experiment layer | `engineering_smoke_test` |

Frozen result:

| Metric | Value |
| --- | ---: |
| Strategy return | 27.85% |
| Annualized return | 5.17% |
| Same-pool benchmark return | 32.69% |
| Excess return | -4.85% |
| Max drawdown | 26.55% |
| Signal count | 19 |

## Governance Status

```text
coverage_policy_frozen_conservative_80
local_joinquant_style_simulation_ready
not_platform_replication_ready
not_formal_strategy_candidate
not_accepted_strategy
```

## What Would Be Needed To Revisit 70%

The startup-repair rule can only be reconsidered if Research Agent supplies an ex-ante data-quality argument independent of returns, for example:

1. 2021-07 had enough PIT-visible operator evidence to form a stable top10.
2. Missing operator-purity rows were missing because of data-source coverage, not because of unknown business exposure.
3. The same startup rule is pre-registered and applied to future sectors, not only to V5.7b.
4. Formal validation and overfit audit are rerun after the rule is frozen.

Until then, 70% remains diagnostic only.

Hard rule:

```text
Historical performance alone is never sufficient evidence for accepting a strategy.
```
