# Governance Record: v52_coal_research_preparation_packet_v1

Date: 2026-07-16

Project:

```text
V5.2 Coal High-Dividend / Cycle-Value Process-Portability Test
```

Current status:

```text
research_preparation_packet_complete
```

Not status:

```text
research_pit_validation_started
formal_strategy_candidate
platform_replication_candidate
platform_replication_passed
accepted_strategy
```

## PM Record

Research Agent has completed the first V5.2 preparation packet for A-share coal mining and coal operating companies.

This packet is sufficient for PM review before opening limited Quant Validation Agent data-contract work.

## Completed Preparation Outputs

- `knowledge/research_agent/references/coal_universe_definition.md`
- `knowledge/research_agent/references/coal_data_field_map.md`
- `knowledge/research_agent/references/coal_source_collection_plan.md`
- `knowledge/research_agent/factor_theory/coal_value_investing_framework.md`
- `knowledge/research_agent/factor_theory/coal_core_factor_hypotheses.md`
- `knowledge/research_agent/references/coal_validation_handoff.md`

## Flow Documents

- `docs/V52_COAL_TEST_PREPARATION.md`
- `docs/V52_COAL_FULL_WORKFLOW.md`
- `docs/V52_COAL_RESEARCH_AGENT_TASK.md`
- `docs/V52_COAL_QUANT_VALIDATION_FLOW.md`

## PM Interpretation

V5.2 is ready for a limited Quant Validation Agent preparation task:

```text
research_pit_validation_data_contract_and_panel_build
```

The preparation packet does not prove any factor. It only defines:

- universe boundary;
- data collection requirements;
- external state requirements;
- coal-specific economic logic;
- candidate hypotheses;
- validation requirements.

## Guardrails Preserved

- Coal and broad high-dividend SOE baskets remain separated.
- No platform backtest has been started.
- No 2021-2026 platform result is used for tuning.
- No bank or utilities threshold is copied into coal without coal-specific logic.
- Engineering Agent remains blocked from strategy code until a formal research candidate is frozen.

## Recommended Next Action

Project Manager Agent should approve Quant Validation Agent to build:

- PIT coal universe panel;
- coal external state panel template;
- leakage audit checks;
- baseline / IC / RankIC / rolling / ablation / robustness runner compatibility.

Formal validation can run only after real PIT panel coverage passes.
