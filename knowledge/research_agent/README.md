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

## Structure

- `INDEX.md`: searchable map of knowledge cards.
- `templates/knowledge_card.md`: standard card template.
- `market_structure/`: trading rules, platform behavior, data mechanics, execution lessons.
- `data_sources/`: data-source reliability, field definitions, source caveats.
- `factor_theory/`: factor logic and economic interpretation.
- `strategy_cases/`: strategy-specific lessons that may generalize later.

## Suggested Workflow

1. Research Agent proposes or reviews a hypothesis.
2. Quant Validation Agent tests it.
3. Engineering Agent implements or compares execution.
4. Research Agent records reusable knowledge here.
5. Project Manager Agent may promote stable knowledge into formal docs or skills.
