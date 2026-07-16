# Sector Research Knowledge Gate V1

Date: 2026-07-17

Owner:

```text
Research Agent
```

Experiment layer:

```text
data_availability_gate
```

## Rule

No new sector may enter formal validation before Research Agent builds a sector knowledge packet.

This is now a hard PM gate.

## Why

The utilities / electricity case worked partly because Research Agent first learned the sector:

- electricity demand matters;
- cash-flow stability matters;
- high capex and debt are normal but must be serviceable;
- dividend signals need to be interpreted with cash-flow coverage;
- external state can change which factor is economically meaningful.

Without this knowledge layer, Quant Agent may validate statistical artifacts and Engineering Agent may faithfully implement a weak idea.

## Required Knowledge Packet

For every new sector, Research Agent must create:

| Artifact | Required Path Pattern | Purpose |
| --- | --- | --- |
| Sector value investing framework | `knowledge/research_agent/factor_theory/{sector}_value_investing_framework.md` | Explain how the sector creates value. |
| Core factor hypothesis list | `knowledge/research_agent/factor_theory/{sector}_core_factor_hypotheses.md` | Define candidate factors and expected direction. |
| Universe definition | `knowledge/research_agent/references/{sector}_universe_definition.md` | Define inclusion / exclusion boundaries. |
| Data field map | `knowledge/research_agent/references/{sector}_data_field_map.md` | Map theory to fields, sources, visible dates, and missing risks. |
| Source collection plan | `knowledge/research_agent/references/{sector}_source_collection_plan.md` | List official, vendor, article, report, and manual sources. |
| Validation handoff | `knowledge/research_agent/references/{sector}_validation_handoff.md` | Tell Quant Agent what to test and what would falsify the thesis. |

## Source Priority

Research Agent should collect sources in this order:

1. Official definitions, exchange filings, regulator publications, index methodology.
2. Annual reports, interim reports, prospectuses, and company announcements.
3. Academic papers and textbooks where relevant.
4. Brokerage research and industry reports with source and date recorded.
5. High-quality investor articles or community analysis only as hypothesis material, not as verified data.

## Anti-Crawling And Source Rules

- Do not force-crawl websites that block automation.
- If a site blocks automation, create a manual import template and record the source.
- Paid data permissions must be respected.
- Every non-obvious claim must cite source name, publication date, and access route.
- Community articles can inspire hypotheses but cannot by themselves approve factors.

## PM Gate Statuses

Allowed statuses:

```text
sector_knowledge_gate_passed
sector_knowledge_gate_needs_more_sources
sector_knowledge_gate_blocked
```

Only `sector_knowledge_gate_passed` can move into:

```text
research_pit_validation
```

## Required PM Check

Before approving Quant Agent work, Project Manager Agent must confirm:

- the knowledge packet exists;
- the core economic mechanism is clear;
- the proposed factor directions are financially explainable;
- the data field map includes PIT visibility;
- at least one falsification condition exists;
- source quality is sufficient for the sector.

## Validation Failure Loop

If Quant Validation Agent rejects or weakens the hypothesis, the workflow must return to Research Agent.

Research Agent must then choose one:

- revise the hypothesis using additional sector knowledge;
- propose a different hypothesis;
- archive the direction as currently unsupported.

Quant Validation Agent must not tune the hypothesis into success.
