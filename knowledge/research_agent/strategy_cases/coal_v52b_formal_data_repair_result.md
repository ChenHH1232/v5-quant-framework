# Coal V5.2b Formal Data Repair Result

Date: 2026-07-16

Status:

```text
research_memory_not_accepted_strategy
```

## Core Lesson

V5.2b should continue through the capex-policy branch:

```text
coal_cashflow_cycle_value_v52b_capex_policy
```

The reason is not performance chasing. It is evidence alignment:

- capex audit showed many FCF rows are noisy;
- OCF is cleaner and should be primary;
- FCF should remain auxiliary until expansion capex and negative FCF cases are reviewed.

## Data Repair Progress

Completed:

- official NBS seed rows for raw-coal output and coal prices;
- enriched coal external state panel;
- Tushare annual / semiannual report disclosure dates for 37 coal companies;
- business-tag visible-date evidence template;
- capex-policy panel and strategy specification.

Still blocked:

- full-history official coal state coverage;
- business segment revenue / profit evidence;
- 2018 failure repair.

## Quant Result

Capex-policy variant improved:

- composite cumulative return: 689.75%;
- 2024 rolling return: 7.44%;
- 2025 rolling return: 8.61%;

But 2018 remained negative:

```text
-35.07%
```

## Research Rule

Do not turn this into a JoinQuant strategy yet.

The correct next research task is:

```text
fill historical state data and segment evidence, then rerun formal validation
```

Only PM can promote it to:

```text
formal_strategy_candidate
```
