# Research-Quant Iteration Protocol V1

Date: 2026-07-17

Owner:

```text
Project Manager Agent
```

Operating protocol:

```text
docs/governance/agent_operating_protocol_v1.md
```

Research-Quant loops follow the 30-minute default timebox and the two-loop no-new-evidence stop rule. A failed validation returns to Research Agent through a failure packet; it does not require user confirmation unless it changes direction, opens a new sector, needs external/manual data, or asks for strategy-state promotion.

Participating agents:

```text
Research Agent
Quant Validation Agent
```

## Core Rule

Research Agent learns the sector and proposes financially explainable hypotheses.

Quant Validation Agent tests those hypotheses with PIT statistical evidence.

If validation fails, the result returns to Research Agent. Quant Validation Agent must not rewrite the financial theory, tune factors for returns, or invent a new explanation after seeing results.

## Loop

```text
Research Agent learns domain knowledge
        |
        v
Research Agent proposes hypothesis
        |
        v
Quant Validation Agent validates
        |
        +--> evidence supports hypothesis -> PM may approve next gate
        |
        +--> evidence rejects / weakens hypothesis
                 |
                 v
          Research Agent reviews failure
                 |
                 +--> revise hypothesis with new knowledge
                 +--> propose a different hypothesis
                 +--> mark direction as temporarily failed
```

## Research Agent Responsibilities

Research Agent must provide:

- sector knowledge packet;
- economic mechanism;
- factor direction;
- expected regime behavior;
- falsification conditions;
- required data fields;
- source citations and source confidence;
- what result would count as failure.

Research Agent must not:

- tune weights based on backtest return;
- ask Engineering Agent to implement an unvalidated idea;
- treat community articles or market opinions as verified evidence;
- change the theory after seeing Quant results without recording the change.

## Quant Validation Agent Responsibilities

Quant Validation Agent must test:

- PIT leakage;
- IC / RankIC;
- baseline;
- rolling validation;
- ablation;
- robustness;
- weak-year or regime failure;
- sample coverage and data availability.

Quant Validation Agent must output:

- `validation_status`;
- statistical evidence;
- failed tests;
- whether failure is data-related or hypothesis-related;
- what part of the hypothesis was not supported;
- whether more research knowledge is needed.

Quant Validation Agent must not:

- invent financial explanations;
- adjust factor weights to improve returns;
- promote a statistically weak hypothesis because cumulative return looks good;
- rewrite Research Agent's hypothesis.

## Validation Statuses

Allowed statuses:

```text
hypothesis_supported_for_pm_review
hypothesis_needs_research_revision
hypothesis_rejected
data_gate_failed_return_to_pm
```

## Failure Return Packet

When validation fails, Quant Validation Agent must return a packet to Research Agent:

| Field | Required |
| --- | --- |
| hypothesis_id | yes |
| rejected_or_weak_claim | yes |
| failed_tests | yes |
| affected_years_or_regimes | yes |
| data_quality_issues | yes |
| suspected_reason | yes, but marked as statistical inference |
| recommended_research_questions | yes |
| allowed_next_action | revise / replace / archive |

## PM Enforcement

Project Manager Agent must block:

- direct transition from failed validation to Engineering;
- return-based parameter tuning after failed validation;
- relabeling a failed hypothesis as accepted by adding a post-hoc story;
- mixed interpretation between research evidence and platform replication.

## Purpose

The goal is not to make every sector produce a strategy.

The goal is to make V5 reliably distinguish:

- a true explainable signal;
- a data-source illusion;
- a weak but interesting hypothesis;
- a failed hypothesis;
- an engineering replication issue.
