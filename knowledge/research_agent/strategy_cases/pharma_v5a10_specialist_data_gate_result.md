# Pharma V5a.10 Specialist Data Gate Result

Date: 2026-07-21

Status:

```text
specialist_data_gate_blocked
not_quant_ready
not_engineering_handoff
```

## Research Memory

Pharma / medical services should not be treated as a generic dividend low-volatility OCF/FCF sector.

The local PIT panel can support basic cash-flow diagnostics, but it lacks the specialist fields required to explain the economic mechanism:

- R&D expense intensity;
- capitalized R&D ratio;
- policy / reimbursement pressure;
- centralized procurement pressure.

## What Passed

- PIT subsector panel exists.
- Core cash-flow fields have high coverage.
- Low-volatility fields are available.
- Real daily price data exists.
- Report-search seed exists for industry logic.

## What Failed

- `rd_expense_to_revenue`: missing.
- `capitalized_rd_ratio`: missing.
- `procurement_pressure_state`: missing.
- `policy_state`: missing.
- Cash dividend events are not repaired for Engineering.

## Research Implication

The useful future route is not another low-PB/OCF/low-vol weight variant.

Research Agent must first repair specialist data:

```text
R&D intensity + procurement/policy state + subsector split + dividend repair
```

Only then can Quant Agent validate a pharma specialist model.

Historical performance alone is never sufficient evidence for accepting a strategy.
