# Governance Record: v52b_coal_formal_data_repair_pm_decision_v1

Date: 2026-07-16

Project:

```text
V5.2b Coal Cash-Flow Cycle Value / Capex Policy
```

Current status:

```text
research_pit_validation_improved_but_business_tag_and_state_history_blocked
```

## PM Decision

Project Manager Agent does not promote V5.2b to formal strategy candidate.

The capex-policy variant is the preferred research branch, but required data evidence is incomplete.

## Completed

- Added official NBS seed rows for raw-coal output state and coal price state.
- Merged official seed rows into the coal external state panel.
- Rebuilt an enriched coal PIT panel.
- Collected Tushare annual / semiannual report disclosure dates for 37 coal companies.
- Generated a coal business-tag visible-date evidence template.
- Downgraded FCF from primary to auxiliary until capex review passes.
- Created V5.2b capex-policy strategy specification.
- Reran formal validation, state bucket validation, and overfit audit.

## Evidence

V5.2b capex-policy improved the original V5.2b research result:

- cumulative return improved from 646.02% to 689.75%;
- 2024 improved from 4.59% to 7.44%;
- 2025 improved from 6.38% to 8.61%;
- FCF downweighting is consistent with the capex audit.

However:

- 2018 remains a failure year;
- external official state data is seed-level, not full-history coverage;
- business tags have report timing but no segment evidence;
- overfit audit remains `needs_review` because platform-style daily inputs do not exist yet.

## Agent Instructions

Research Agent:

- Continue collecting official or licensed historical coal state rows.
- Fill segment evidence for core coal, coal-power, and coal-chemical business tags.

Quant Validation Agent:

- Treat `coal_cashflow_cycle_value_v52b_capex_policy` as the preferred research branch.
- Do not accept it until state history and business-tag evidence are complete.

Engineering Agent:

- Maintain import and validation runners.
- Do not generate JoinQuant strategy code.
- Do not start platform replication until PM promotes the strategy.

## Next Gate

Promotion requires:

```text
formal external state history coverage + business segment PIT evidence + capex-policy formal validation pass + 2018 failure review
```
