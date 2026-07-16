# Governance Record: v51e_utilities_demand_state_pm_decision_v1

Date: 2026-07-16

Layer:

```text
research_pit_validation
```

Decision:

```text
utilities_demand_state_v51e = preliminary_model_candidate
```

Not decision:

```text
formal_strategy_candidate
platform_replication
accepted_strategy
```

## PM Rationale

V5.1e uses PIT external demand state to switch between two simple baselines:

- non-strong electricity demand: operating cash-flow yield;
- strong electricity demand: low PB.

This model beats the two strongest static baselines in rolling PIT validation:

| Case | Cumulative Return |
| --- | ---: |
| demand_state_cashflow_else_low_pb | 2.6883 |
| raw_low_pb_utilities_top10 | 1.9444 |
| raw_cashflow_yield_utilities_top10 | 1.9209 |

The model also preserves a simple utilities-specific explanation:

```text
cash-flow resilience matters when demand is not strong;
asset re-rating / valuation recovery matters more when demand is strong.
```

Secondary state robustness:

```text
secondary_industry_electricity_yoy
```

also supports demand-state conditioning. The simple primary rule remains above both static baselines, while a slightly richer state rule performs better. PM keeps the simple rule as the preliminary model to avoid adding complexity before stricter validation.

## Guardrails

This result is not enough for engineering implementation.

Reasons:

- annual dominance is uneven;
- thresholds use expanding tertiles but still need robustness review;
- only electricity-demand state is populated deeply;
- coal, tariff, hydrology and gas-margin state are not yet broad enough.

## Next Required Quant Work

Quant Validation Agent should run:

- state-conditioned IC / RankIC;
- selection_count robustness;
- alternative state metric robustness;
- failure-year review;
- common-sample comparison against raw low PB and raw cash-flow yield.

Only after passing that gate may PM consider:

```text
formal_strategy_candidate
```
