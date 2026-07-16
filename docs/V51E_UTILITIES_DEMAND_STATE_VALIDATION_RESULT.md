# V5.1e Utilities Demand-State Validation Result

Date: 2026-07-16

Layer:

```text
research_pit_validation
```

Status:

```text
preliminary_model_candidate
```

Not status:

```text
formal_strategy_candidate
platform_replication
accepted_strategy
```

## Objective

After V5.1a-d rejected static utilities composites, V5.1e tested whether an external demand-state variable can decide which simple utilities factor should be active.

External state:

```text
electricity_consumption_yoy
```

PIT policy:

```text
Use only the latest external state row with visible_date <= trade_date.
```

State bucket policy:

```text
Use expanding historical tertiles.
Warmup periods use operating cash-flow yield.
```

## Preliminary Model

```text
If electricity demand YoY is strong:
    select raw low-PB utilities top 10
Else:
    select raw operating-cash-flow-yield utilities top 10
```

This is intentionally simple. It does not use optimized thresholds or platform backtest tuning.

## Evidence

Coverage:

```text
panel_dates = 38
state_covered_dates = 38
```

Rolling PIT result:

| Case | Cumulative Return | Mean Period Return | Positive Ratio |
| --- | ---: | ---: | ---: |
| demand_state_cashflow_else_low_pb | 2.6883 | 0.0396 | 0.6316 |
| raw_low_pb_utilities_top10 | 1.9444 | 0.0354 | 0.5526 |
| raw_cashflow_yield_utilities_top10 | 1.9209 | 0.0329 | 0.6316 |
| raw_high_dividend_utilities_top10 | 1.3522 | 0.0267 | 0.5789 |
| equal_weight_utilities | 0.4100 | 0.0137 | 0.5526 |

Alternative state robustness:

```text
secondary_industry_electricity_yoy
```

This alternative state also supports demand-state conditioning. The simple primary rule reached cumulative return 2.0786, still above raw low PB 1.9444 and raw cash-flow yield 1.9209. The best alternative-state rule reached 2.4395 by using cash-flow yield in weak demand, subindustry cash-flow in mid demand, and low PB in strong demand.

Full-sample state read:

| Demand State | Best Read |
| --- | --- |
| weak | cash-flow yield is strongest |
| mid | cash-flow / subindustry cash-flow is stronger than low PB |
| strong | raw low PB is strongest |

## Failure Notes

The model does not dominate every year.

Weak years / caveats:

- 2017: demand-state model slightly underperformed low PB and cash-flow baseline.
- 2019: low PB beat the demand-state model.
- 2020: low PB beat the demand-state model.
- 2021: cash-flow beat the demand-state model.

This means V5.1e is an initial model candidate, not a formally accepted strategy.

## PM Decision

The evidence is enough to create a preliminary utilities model:

```text
utilities_demand_state_v51e
```

Follow-up Quant loop:

```text
utilities_demand_state_v51f
```

The Quant Agent found a stronger, more defensible rule:

```text
weak demand -> high dividend
mid demand -> cash-flow yield
strong demand -> low PB
```

This rule reached:

```text
formal_candidate_quant_ready
```

It is still not a formal strategy candidate until PM approval.

The next gate is not JoinQuant code. The next gate is stricter Quant validation:

- rolling IC / RankIC by state bucket;
- robustness across selection_count 8 / 10 / 12;
- deeper alternative state review using secondary_industry_electricity_yoy;
- failure-mode analysis for 2017, 2019, 2020, 2021;
- confirmation that the rule remains financially explainable.

Engineering Agent remains blocked from platform replication until Quant Validation promotes this to:

```text
formal_strategy_candidate
```
