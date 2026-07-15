# V5.1c Utilities Low PB Cashflow Result

Date: 2026-07-16

Layer:

```text
research_pit_validation
```

Strategy spec:

```text
examples/utilities_low_pb_cashflow_v51c_strategy.json
```

Panel:

```text
数据库/processed/utilities_cashflow_value_v51b_panel/panel.csv
```

Validation output:

```text
validation_formal_v51c/utilities_low_pb_cashflow_v51c/
```

## Purpose

V5.1c tests the simplest follow-up to V5.1b:

```text
low PB + operating cash-flow yield
```

The aim is to verify whether two strong individual utilities signals combine into a better model.

## Result

V5.1c does not pass formal candidate promotion.

```text
formal_candidate_gate = rejected_for_now
```

## Factor Evidence

| Factor | Mean IC | Mean RankIC | Positive IC Ratio |
| --- | ---: | ---: | ---: |
| low_pb_subindustry_score | 0.0494 | 0.0947 | 0.7105 |
| cashflow_yield_subindustry_score | 0.0598 | 0.0806 | 0.7105 |

Both factors are individually useful.

## Baseline Evidence

| Case | Cumulative Return | Mean Period Return | Positive Ratio |
| --- | ---: | ---: | ---: |
| equal_weight_utilities | 0.4099 | 0.0137 | 0.5526 |
| raw_low_pb_utilities_top10 | 1.9448 | 0.0354 | 0.5526 |
| raw_cashflow_yield_utilities_top10 | 1.9223 | 0.0330 | 0.6316 |
| subindustry_low_pb_only | 1.5954 | 0.0311 | 0.6316 |
| subindustry_cashflow_only | 1.7884 | 0.0323 | 0.6053 |
| low_pb_cashflow_composite_v51c | 0.7539 | 0.0198 | 0.5526 |

## Interpretation

The two-factor composite is weaker than both single-factor baselines.

This means:

- low PB and operating cash-flow yield are useful utilities signals;
- equal-weight combination is not automatically better;
- the two signals may select different types of companies whose interaction is unstable;
- ranking within sub-industry improves interpretability but does not beat raw factor baselines;
- further progress likely requires external utilities state variables or conditional models rather than a static composite.

## PM Decision

Do not move V5.1c to Engineering Agent.

Recommended next research choices:

1. Keep `raw_low_pb_utilities_top10` and `raw_cashflow_yield_utilities_top10` as official baselines.
2. Test conditional rules instead of weighted composites:
   - low PB within positive cash-flow-yield universe;
   - cash-flow yield within low-PB universe;
   - sub-industry-specific rules.
3. Add external state variables before another composite:
   - coal price / fuel-cost proxy;
   - utilization hours;
   - electricity tariff / marketized power price;
   - hydropower water condition proxy.

## Governance

V5.1c remains research evidence only.

No JoinQuant strategy code should be generated from V5.1c.
