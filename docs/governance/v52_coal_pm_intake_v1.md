# Governance Record: v52_coal_pm_intake_v1

Date: 2026-07-16

Project:

```text
V5.2 Coal High-Dividend / Cycle-Value Process-Portability Test
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

Project Manager Agent approves V5.2 preparation for A-share coal mining and coal operating companies.

The test is intended to check whether V5 can transfer from:

```text
bank balance-sheet value
electricity-utility demand state
```

to:

```text
strong-cycle high-dividend commodity value
```

## Initial Boundary

Approved universe:

```text
A-share coal mining and coal operating companies
```

Include:

- coal mining;
- coal washing;
- integrated coal operators where coal mining is the dominant economic exposure;
- thermal coal and coking coal producers.

Exclude:

- pure coal chemical companies;
- coal machinery and mining equipment;
- non-coal mining;
- broad high-dividend SOE style baskets;
- diversified companies where coal is not the core profit driver.

## Required External State

V5.2 must introduce external coal-cycle state before any formal candidate can be promoted:

- thermal coal price;
- coking coal price;
- coal inventory or port inventory;
- coal output / production;
- coal-power spread or coal-electricity margin proxy.

These state variables must carry:

- state date;
- visible date;
- source publication date;
- source name and URL;
- PIT usability flag.

## Approved Preparation Tasks

Research Agent must prepare:

- coal universe definition;
- data-source and field-availability map;
- coal value-investing framework;
- initial factor hypothesis list;
- coal-cycle state variable map;
- failure-mode list;
- validation handoff plan.

Quant Validation Agent must not start formal validation until Research Agent outputs are complete.

Engineering Agent may do only:

- data availability probes;
- PIT source template design;
- reusable runner planning.

Engineering Agent must not build JoinQuant strategy code until a research candidate is frozen.

## Success Criteria For Preparation

Preparation is complete when PM can answer:

1. Is the coal universe an industry universe rather than a style basket?
2. Are coal price, inventory/output, and spread state variables collectible with visible dates?
3. Are static factors financially explainable for coal cyclicality?
4. Does the validation plan include baseline, IC/RankIC, rolling, ablation, and robustness?
5. Are 2021-2026 platform windows excluded from tuning and acceptance?

Only then may PM approve:

```text
V5.2 Test-1 research_pit_validation
```
