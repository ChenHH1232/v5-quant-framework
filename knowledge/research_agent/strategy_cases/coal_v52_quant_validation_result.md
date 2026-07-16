# Coal V5.2 Quant Validation Result

Date: 2026-07-16

Status:

```text
research_memory_not_accepted_strategy
```

## Reusable Lesson

The first V5.2 coal test did not support a simple "high-dividend coal" thesis.

The stronger preliminary evidence was:

- operating cash-flow yield;
- free cash-flow yield, if capex data is reliable;
- low PB;
- low PE, with cycle-peak caution.

Dividend yield was weak as a standalone signal and should be treated as a support or filter candidate until better evidence appears.

## External State Lesson

Coal external state cannot be handled like a normal stock-level factor because every stock shares the same state value on a rebalance date.

The correct validation route is:

```text
state bucket -> factor behavior within bucket
```

not:

```text
cross-sectional IC of the state variable itself
```

## Data Gaps

- Official or licensed inventory/output state is still missing.
- Thermal coal futures proxy ends in 2022, so it cannot support 2023-2026 formal validation.
- Coal-power spread proxy is not yet a real economic spread.
- Coal-business tags need company-report visible-date audit.

## Research Implication

V5.2 should continue as V5.2b:

```text
Coal Cash-Flow Value / Cycle-Aware Value
```

The next model should test cash-flow value and low valuation first, then use dividend as a coverage or shareholder-return support variable.
