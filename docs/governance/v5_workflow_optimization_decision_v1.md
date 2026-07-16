# Governance Record: v5_workflow_optimization_decision_v1

Date: 2026-07-17

PM decision:

```text
optimize_workflow_first_then_small_sector_tests
```

## Decision

Project Manager Agent freezes the next V5 priority order:

1. Productize the utilities / electricity path as the golden workflow template.
2. Harden workflow gates before opening more sector tests.
3. Suspend coal strategy optimization until its manual research data gate is repaired.
4. Diagnose insurance failure years, but do not tune returns.
5. After the workflow is stable, test only one or two nearby clean-data sectors.

## Why

The most important current finding is not a single return number.

It is that V5 can separate:

- a successful reusable workflow case: utilities / electricity;
- a data-gate failure: coal;
- a statistically visible but not yet deployable signal: insurance.

This is the behavior V5 was designed to enforce.

## Utilities Becomes The Golden Template

Utilities / electricity is now the first workflow productization target.

It should be documented and reused as the standard path for:

- research preparation;
- PIT data and external-state construction;
- formal validation;
- local daily simulation;
- platform replication;
- overfit audit;
- forward / paper-trading signal logging;
- PM decision records.

This does not mean the strategy is accepted.

It means the process is valuable enough to become the first repeatable template.

## Workflow Hardening Priorities

Before broad sector expansion, V5 must harden:

- shared scoring logic between formal validation and backtests;
- machine-readable strategy status registry;
- data availability gate before formal validation;
- strict separation of `research_pit_validation`, `engineering_smoke_test`, `platform_replication`, and `paper_trading`;
- PM blocks for mixed-layer interpretation;
- runner output packets that can be compared across sectors.

## Coal Status

Coal is suspended as a strategy optimization project.

New status:

```text
blocked_by_manual_research_data
```

Coal can continue only as data-engineering work if the project owner chooses to build a manual research-data pipeline for:

- commodity price state;
- production / inventory state;
- coal-power and coal-chemical spread state;
- PIT company business segment exposure from annual reports, interim reports, exchange filings, or reviewed vendor data.

Until then, no new coal factor tuning, JoinQuant code, platform replication, or paper trading is allowed.

## Insurance Status

Insurance remains a research candidate with engineering daily simulation completed.

The next allowed work is:

```text
failure_attribution_only_no_return_tuning
```

Allowed:

- diagnose 2021, 2022, and 2026;
- review interest-rate state, equity-market state, EV / NBV availability, solvency data, and liability-side pressure;
- decide whether insurance needs a richer data model.

Blocked:

- selection-count tuning;
- weight tuning;
- return-driven defensive overlay;
- JoinQuant code export before PM approves platform replication.

## New Sector Test Policy

Do not launch broad sector tests.

After workflow hardening, choose at most one or two clean-data nearby sectors:

1. Telecom operators.
2. Transportation infrastructure: toll roads, ports, rail operators.
3. Gas / water / environmental utilities, possibly as utilities-line expansion.

Avoid strong-cycle sectors until the cyclical-sector data gate is mature.

## Next Gate

```text
utilities_golden_template_productization
```

After that:

```text
one_small_clean_sector_replication_test
```
