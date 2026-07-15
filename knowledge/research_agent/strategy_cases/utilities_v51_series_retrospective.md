# Utilities V5.1 Series Retrospective

Date: 2026-07-16

Status:

```text
research_reset_required
```

## Main Lesson

V5.1 proved that the V5 process can move outside bank-specific indicators, but it also proved that utilities need sector-state information before a formal strategy candidate can be justified.

## Repeated Pattern

- Low PB worked.
- Operating cash-flow yield worked.
- High dividend was a useful benchmark.
- Static composites failed.
- Conditional variants improved over static composites but still failed to beat raw baselines.

## Research Reset

Do not continue by adding more generic accounting factors.

Next research must add PIT-visible utilities state variables:

- coal / fuel-cost proxy;
- utilization hours;
- tariff / marketized power price;
- hydropower water-condition proxy;
- gas tariff / margin proxy.

## Baselines To Keep

```text
raw_low_pb_utilities_top10
raw_cashflow_yield_utilities_top10
raw_high_dividend_utilities_top10
equal_weight_utilities
```

## PM Rule

Any future utilities model must beat raw low PB and raw cashflow yield before Engineering Agent can build platform code.
