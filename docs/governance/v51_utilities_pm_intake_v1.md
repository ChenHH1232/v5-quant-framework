# Governance Record: v51_utilities_pm_intake_v1

Date: 2026-07-16

Project:

```text
V5.1 Utilities Sector Process-Portability Test
```

Current status:

```text
preparation_started
```

Not status:

```text
research_pit_validation_started
formal_strategy_candidate
platform_replication_candidate
accepted_strategy
```

## PM Decision

Project Manager Agent approves V5.1 preparation for the A-share utilities sector.

The first cross-industry test should use a coherent industry boundary:

```text
utilities operating companies, priority electric power operators
```

Project Manager Agent rejects using broad high-dividend SOE as the first V5.1 sector because it is a style basket, not an industry test.

## Rationale

Bank V3 has reached:

```text
formal_strategy_candidate + platform_replication_passed
```

Bank V3 has also entered forward / paper-trading record keeping. Continuing to optimize the bank strategy inside the 2021-2026 platform window has low marginal value and risks overfitting. A utilities preparation phase is now useful because it tests whether V5 can replicate its research process outside bank-specific data.

## Approved Preparation Tasks

Research Agent must prepare:

- utilities universe definition;
- data-source and field-availability map;
- utilities economic logic memorandum;
- initial factor hypothesis list;
- explicit failure-mode list;
- proposed validation plan.

Quant Validation Agent must not start formal validation until Research Agent outputs are complete.

Engineering Agent must not build platform code until a research candidate is frozen.

## Boundaries

Allowed:

- PIT universe planning;
- source availability review;
- factor-hypothesis design;
- validation-plan design;
- baseline definition.

Not allowed yet:

- platform backtest;
- JoinQuant export;
- performance optimization;
- 2021-2026 parameter tuning;
- mixing utilities with high-dividend SOE style baskets.

## Success Criteria For Preparation

V5.1 preparation is complete when Project Manager Agent can answer:

1. Is the utilities universe well-defined?
2. Are required data fields collectible and point-in-time usable?
3. Are factors financially explainable for utilities?
4. Is the validation plan comparable to V3 standards?
5. Are platform-replication and research-validation layers separated?

Only then may PM approve:

```text
V5.1 Test-1 research_pit_validation
```
