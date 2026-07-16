# Governance Record: v53_insurance_pm_intake_v1

Date: 2026-07-16

Project:

```text
V5.3 Insurance Value / Quality Process-Portability Test
```

Current status:

```text
research_preparation_started
```

Not status:

```text
research_pit_validation_started
formal_strategy_candidate
platform_replication_candidate
accepted_strategy
```

## PM Decision

Project Manager Agent approves V5.3 preparation for A-share listed insurance companies.

The test is intended to check whether V5 can transfer from bank balance-sheet value to another financial sector with different business economics.

## Initial Boundary

Approved universe:

```text
A-share insurance operating companies and insurance-led holding companies
```

Include:

- life insurers;
- property and casualty insurers;
- insurance groups where insurance is the dominant economic exposure.

Exclude:

- banks;
- brokers;
- asset managers;
- non-insurance financial holdings;
- insurance technology vendors.

## Required State Variables

V5.3 must introduce insurance-relevant external state before any formal candidate can be promoted:

- long-term government bond yield;
- yield-curve slope;
- equity-market state;
- credit spread or bond-market risk proxy;
- industry premium growth where available.

## Approved Preparation Tasks

Research Agent must prepare:

- insurance universe definition;
- data-source and field-availability map;
- insurance value / quality framework;
- initial factor hypothesis list;
- source collection plan;
- validation handoff.

Quant Validation Agent must not start formal validation until Research Agent outputs are complete.

Engineering Agent may do only:

- data availability probes;
- PIT source template design;
- reusable runner planning.

Engineering Agent must not build JoinQuant strategy code until a research candidate is frozen.

## Success Criteria For Preparation

Preparation is complete when PM can answer:

1. Is the universe truly insurance-led?
2. Are life and P&C economics separated?
3. Are embedded value, solvency, investment yield and underwriting fields collectible with visible dates?
4. Are interest-rate and equity-market states available?
5. Does the validation plan include baseline, IC / RankIC, rolling, ablation and robustness?
6. Are 2021-2026 platform windows excluded from tuning and acceptance?

Only then may PM approve:

```text
V5.3 Test-1 research_pit_validation
```

