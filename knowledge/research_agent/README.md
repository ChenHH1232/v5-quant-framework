# Research Agent Knowledge Base

This folder stores reusable research knowledge for Bank Quant V5.

It is not a strategy report and not a final decision log. It is the Research Agent's working memory: hypotheses, observed evidence, data caveats, market-structure lessons, factor notes, and reusable research conclusions.

## Purpose

- Preserve knowledge extracted from experiments, audits, platform comparisons, and failed attempts.
- Help the Research Agent avoid repeating old mistakes.
- Make future strategy research faster, more explainable, and easier to validate.
- Separate research knowledge from implementation artifacts, logs, credentials, and raw data.

## Rules

- Do not store credentials, tokens, account numbers, passwords, or private API keys.
- Do not store large raw datasets.
- Every claim should include evidence, source files, or experiment context.
- Distinguish facts, hypotheses, decisions, and open questions.
- Historical performance alone is not sufficient evidence.
- Knowledge should be reusable across strategies when possible, not only tied to one backtest.
- A new sector cannot enter formal validation until Research Agent has produced a sector knowledge packet.

## Structure

- `INDEX.md`: searchable map of knowledge cards.
- `templates/knowledge_card.md`: standard card template.
- `market_structure/`: trading rules, platform behavior, data mechanics, execution lessons.
- `data_sources/`: data-source reliability, field definitions, source caveats.
- `factor_theory/`: factor logic and economic interpretation.
- `strategy_cases/`: strategy-specific lessons that may generalize later.

## Suggested Workflow

1. Research Agent studies the sector and creates the required knowledge packet.
2. Project Manager Agent checks the research knowledge gate and data availability gate.
3. Research Agent proposes or reviews a hypothesis.
4. Quant Validation Agent tests it.
5. If validation fails, Quant Validation Agent returns a failure packet to Research Agent.
6. Research Agent revises, replaces, or archives the hypothesis.
7. Engineering Agent implements or compares execution only after the research and validation gates pass.
8. Research Agent records reusable knowledge here.
9. Project Manager Agent may promote stable knowledge into formal docs or skills.

## New Sector Knowledge Packet

Before Quant Validation Agent starts a new sector, Research Agent must create:

- `factor_theory/{sector}_value_investing_framework.md`
- `factor_theory/{sector}_core_factor_hypotheses.md`
- `references/{sector}_universe_definition.md`
- `references/{sector}_data_field_map.md`
- `references/{sector}_source_collection_plan.md`
- `references/{sector}_validation_handoff.md`

The gate definition is recorded in `docs/governance/sector_research_knowledge_gate_v1.md`.
