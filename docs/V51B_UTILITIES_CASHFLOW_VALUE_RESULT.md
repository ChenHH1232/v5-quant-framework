# V5.1b Utilities Cashflow Value Result

Date: 2026-07-16

Layer:

```text
research_pit_validation
```

Strategy spec:

```text
examples/utilities_cashflow_value_v51b_strategy.json
```

Panel:

```text
数据库/processed/utilities_cashflow_value_v51b_panel/panel.csv
```

Validation output:

```text
validation_formal_v51b/utilities_cashflow_value_v51b/
```

## Purpose

V5.1b retests utilities after adding sector-specific logic:

- sub-industry-aware scoring;
- cash-flow value as the main signal;
- low PB and high dividend retained as baselines;
- dividend treated as cash-flow-supported, not standalone;
- capex and leverage treated as controls rather than pure alpha.

## Initial Result

V5.1b improves factor clarity but still does not pass the formal candidate gate.

```text
formal_candidate_gate = rejected_for_now
```

## Factor Evidence

| Factor | Mean IC | Mean RankIC | Positive IC Ratio | Initial read |
| --- | ---: | ---: | ---: | --- |
| cashflow_yield_subindustry_score | 0.0598 | 0.0806 | 0.7105 | useful main factor |
| low_pb_subindustry_score | 0.0494 | 0.0947 | 0.7105 | useful value factor |
| dividend_cashflow_support_score | 0.0462 | 0.0802 | 0.6053 | useful support factor |
| capex_control_score | 0.0238 | 0.0246 | 0.5263 | weak control |
| leverage_control_score | -0.0156 | -0.0149 | 0.5000 | not useful in this form |

## Baseline Evidence

| Case | Cumulative Return | Mean Period Return | Positive Ratio |
| --- | ---: | ---: | ---: |
| equal_weight_utilities | 0.4099 | 0.0137 | 0.5526 |
| raw_low_pb_utilities_top10 | 1.9448 | 0.0354 | 0.5526 |
| raw_high_dividend_utilities_top10 | 1.3529 | 0.0267 | 0.5789 |
| raw_cashflow_yield_utilities_top10 | 1.9223 | 0.0330 | 0.6316 |
| cashflow_value_composite_v51b | 1.1414 | 0.0245 | 0.6579 |

## Interpretation

The V5.1b model has better statistical cleanliness than V5.1 Test-1:

- all main derived factors have full coverage;
- cash-flow, PB and dividend support all have positive IC;
- rolling performance is less dependent on one explosive year.

But the current composite remains inferior to simpler raw baselines:

- raw low PB remains strongest;
- raw operating cash-flow yield is nearly as strong;
- adding capex and leverage controls reduces performance;
- dropping low-PB subindustry score improves the composite, suggesting the current weighting is still not right;
- dropping capex and leverage controls also improves the composite.

## PM Decision

V5.1b should not move to Engineering Agent.

The next research direction should be a simpler candidate:

```text
utilities_low_pb_cashflow_v51c
```

Suggested design:

- two-factor main model:
  - raw or sub-industry low PB;
  - raw or sub-industry operating cash-flow yield;
- high dividend remains a benchmark, not a forced composite input;
- capex and leverage remain diagnostics / filters only after separate validation;
- add official external variables before another complex composite:
  - coal price / fuel-cost proxy;
  - utilization hours;
  - electricity tariff / market-price proxy;
  - hydropower water condition proxy where available.

## Governance

V5.1b is research evidence only.

It is not a formal strategy candidate and must not trigger JoinQuant code generation.
