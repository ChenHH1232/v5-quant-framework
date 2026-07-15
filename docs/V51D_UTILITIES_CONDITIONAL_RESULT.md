# V5.1d Utilities Conditional Low PB Cashflow Result

Date: 2026-07-16

Layer:

```text
research_pit_validation
```

Strategy spec:

```text
examples/utilities_conditional_low_pb_cashflow_v51d_strategy.json
```

Validation output:

```text
validation_formal_v51d/utilities_conditional_low_pb_cashflow_v51d/
```

## Purpose

V5.1d tested whether low PB and operating cash-flow yield work better as conditional rules instead of a static weighted composite.

Main questions:

- Does low PB work better only among utilities with stronger cash-flow yield?
- Does cash-flow yield work better only among lower-PB utilities?
- Do sub-industry percentile versions improve the result?

## Result

V5.1d does not pass formal candidate promotion.

```text
formal_candidate_gate = rejected_for_now
```

## Baseline And Conditional Evidence

| Case | Cumulative Return | Mean Period Return | Positive Ratio |
| --- | ---: | ---: | ---: |
| equal_weight_utilities | 0.4099 | 0.0137 | 0.5526 |
| raw_low_pb_utilities_top10 | 1.9448 | 0.0354 | 0.5526 |
| raw_cashflow_yield_utilities_top10 | 1.9223 | 0.0330 | 0.6316 |
| low_pb_with_top_half_cashflow | 1.6409 | 0.0320 | 0.6316 |
| cashflow_with_top_half_low_pb | 1.7446 | 0.0320 | 0.6053 |
| subindustry_low_pb_with_top_half_cashflow | 0.6160 | 0.0175 | 0.5526 |
| subindustry_cashflow_with_top_half_low_pb | 1.1056 | 0.0243 | 0.5789 |
| reference_static_composite_v51d | 0.7539 | 0.0198 | 0.5526 |

## Interpretation

Conditional rules improve over the static composite, but they still do not beat raw low PB or raw operating cash-flow yield.

The current evidence says:

- raw low PB is still the strongest utilities baseline;
- raw operating cash-flow yield is nearly as strong and has a better positive-period ratio;
- conditioning low PB on cash-flow quality helps but does not add enough;
- sub-industry percentile conditioning is weaker than raw factor conditioning;
- forcing these two factors into a composite remains unjustified.

## PM Decision

Do not move V5.1d to Engineering Agent.

Keep these as official V5.1 utilities research baselines:

```text
raw_low_pb_utilities_top10
raw_cashflow_yield_utilities_top10
```

Next research should not be another static financial composite. It should add external utilities state variables:

- coal price / fuel-cost proxy;
- thermal utilization hours;
- hydropower utilization or water-condition proxy;
- tariff / marketized electricity price proxy;
- gas tariff / margin proxy.

## Governance

V5.1d remains research evidence only.

No JoinQuant strategy code should be generated.
