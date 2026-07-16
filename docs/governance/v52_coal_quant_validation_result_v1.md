# Governance Record: v52_coal_quant_validation_result_v1

Date: 2026-07-16

Project:

```text
V5.2 Coal High-Dividend / Cycle-Value Process-Portability Test
```

Current status:

```text
research_pit_validation_completed_data_gap_not_formal_candidate
```

Not status:

```text
formal_strategy_candidate
platform_replication_candidate
platform_replication_passed
accepted_strategy
```

## PM Decision

Project Manager Agent does not approve V5.2 as a formal strategy candidate.

Quant Validation Agent produced useful preliminary evidence, but the evidence packet is blocked by external-state and PIT business-classification gaps.

## Evidence Accepted For Research Memory

- PIT coal stock panel created.
- Coal external-state panel created.
- Formal validation runner executed:
  - baseline;
  - IC / RankIC;
  - rolling;
  - ablation;
  - robustness;
  - failure-year analysis.
- Coal cycle-state bucket runner executed for:
  - coking coal state;
  - thermal coal state.

## Main Findings

The initial high-dividend framing is not supported as the primary standalone signal.

Stronger evidence currently belongs to:

- operating cash-flow yield;
- free cash-flow yield, subject to capex audit;
- low PB;
- low PE, subject to cycle-peak trap review.

Dividend yield should be downgraded to:

```text
support_or_filter_candidate
```

not:

```text
primary_alpha_candidate
```

## Blocking Gaps

- `coal_inventory_or_output_state` has no usable rows.
- `thermal_coal_price_state` is a futures proxy and does not properly cover 2023-2026.
- `coal_power_spread_state` is only a derived proxy.
- `coal_business_tag` is manual and still lacks company-report visible-date audit.
- 2018 and 2024 weak-year failure modes remain unresolved.
- Top-5 selection robustness is too strong relative to wider counts and may indicate concentration risk.

## Approved Next State

V5.2 may continue as:

```text
research_revision_v52b
```

The next Research + Quant loop should test:

```text
Coal Cash-Flow Value / Cycle-Aware Value V5.2b
```

with dividend downgraded from primary alpha to support/filter.

## Blocked

Engineering Agent must not generate JoinQuant strategy code yet.

Platform replication remains blocked.

Paper trading remains blocked.
