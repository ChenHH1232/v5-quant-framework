# V5.2 Coal Full Workflow

Date: 2026-07-16

Owner:

Project Manager Agent

Project:

```text
V5.2 Coal High-Dividend / Cycle-Value Process-Portability Test
```

Current status:

```text
research_preparation_packet_in_progress
```

## Purpose

V5.2 tests whether the V5 process can be reused in a strong-cycle commodity industry.

The purpose is process portability and disciplined rejection when evidence is weak, not immediate strategy acceptance.

## Experiment Separation

Every V5.2 result must be tagged as exactly one of:

```text
research_pit_validation
platform_replication
engineering_smoke_test
paper_trading
```

Project Manager Agent must block any report that mixes research validation, platform replication, and paper trading.

## Full Workflow

```mermaid
flowchart TD
    A["PM Intake: coal mining and coal operators"] --> B["Research Agent: preparation packet"]
    B --> B1["Universe definition"]
    B --> B2["Data field map"]
    B --> B3["Coal value framework"]
    B --> B4["Factor hypotheses"]
    B --> B5["External state source register"]
    B --> B6["Validation handoff"]
    B6 --> C{"PM Gate 1: preparation complete?"}
    C -- "No" --> B
    C -- "Yes" --> D["Quant Validation Agent: research_pit_validation"]
    D --> D1["PIT leakage audit"]
    D --> D2["Baseline comparison"]
    D --> D3["IC / RankIC"]
    D --> D4["Rolling validation"]
    D --> D5["Ablation"]
    D --> D6["Robustness checks"]
    D --> D7["Down-cycle / weak-year analysis"]
    D7 --> E{"PM Gate 2: formal candidate?"}
    E -- "No: weak or unstable evidence" --> F["Research archive: revise or reject"]
    E -- "Yes: stable evidence" --> G["Engineering Agent: local daily simulation"]
    G --> G1["Execution assumptions"]
    G --> G2["Transactions / cash / holdings"]
    G --> G3["Dividend and corporate-action handling"]
    G3 --> H{"PM Gate 3: platform replication candidate?"}
    H -- "No" --> G
    H -- "Yes" --> I["JoinQuant script generation"]
    I --> J["Platform replication attribution"]
    J --> J1["Daily return diff"]
    J --> J2["Trade diff"]
    J --> J3["Position diff"]
    J --> J4["Cash / dividend diff"]
    J4 --> K{"PM Gate 4: platform replication passed?"}
    K -- "No" --> L["Engineering attribution / contract fix"]
    K -- "Yes" --> M["Paper trading record"]
    M --> N["Future signal log"]
    N --> O{"PM Gate 5: accepted strategy?"}
    O -- "No" --> M
    O -- "Yes" --> P["Accepted strategy registry"]
```

## Agent Responsibilities

| Stage | Owner | Output | Not allowed |
| --- | --- | --- | --- |
| Intake | Project Manager Agent | scope, gates, status | factor tuning |
| Research preparation | Research Agent | universe, data map, coal economics, hypotheses | code and platform backtest |
| PIT validation | Quant Validation Agent | leakage audit, IC, RankIC, baseline, rolling, ablation, robustness | inventing theory after seeing returns |
| Data tooling | Engineering Agent | source templates, panel builders, validation hooks | changing research conclusions |
| Local simulation | Engineering Agent | daily runner, execution logs | starting before formal candidate |
| Platform replication | Engineering Agent + PM | local vs JoinQuant attribution | treating platform return as research validation |
| Paper trading | PM + Engineering Agent | future signal record | retroactive parameter changes |

## Gate 1: Preparation Complete

Required files:

- `knowledge/research_agent/references/coal_universe_definition.md`
- `knowledge/research_agent/references/coal_data_field_map.md`
- `knowledge/research_agent/references/coal_source_collection_plan.md`
- `knowledge/research_agent/factor_theory/coal_value_investing_framework.md`
- `knowledge/research_agent/factor_theory/coal_core_factor_hypotheses.md`
- `knowledge/research_agent/references/coal_validation_handoff.md`

PM may approve `research_pit_validation` only when all six files exist and explicitly exclude non-core coal businesses.

## Gate 2: Formal Candidate

Quant Validation Agent must provide:

- PIT leakage audit;
- baseline comparison;
- IC / RankIC;
- rolling validation;
- ablation by module;
- robustness checks;
- weak-year / down-cycle analysis;
- mixed-business exclusion sensitivity.

Research evidence must remain independent from 2021-2026 platform replication results.

## Gate 3: Platform Replication Candidate

Engineering Agent may start platform replication only after PM freezes a formal research candidate.

Required engineering artifacts:

- frozen strategy specification;
- local daily simulation;
- transaction, position, cash, dividend logs;
- external state panel snapshot;
- execution-price assumptions;
- benchmark definition;
- JoinQuant script generated from the frozen spec.

## Gate 4: Platform Replication Passed

PM must judge local vs JoinQuant alignment with:

- daily strategy return attribution;
- benchmark return attribution;
- transaction comparison;
- holding comparison on rebalance dates;
- cash and dividend comparison;
- explanation of residual differences.

## Gate 5: Accepted Strategy

A strategy cannot be accepted only because platform replication passes. It must also survive forward / paper trading and retain financial and statistical explanation.

## Initial Decision

V5.2 is approved for preparation and research packet generation.

V5.2 is not approved for engineering backtest or platform replication yet.
