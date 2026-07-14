---
name: execution-consistency
description: Check consistency between local Bank Quant V5 strategy logic and JoinQuant, QMT, or other execution platform exports. Use when comparing signal dates, factor values, ranks, selected securities, target weights, defensive states, constraints, and platform backtest readiness.
---

# Execution Consistency Skill

Use this skill when exporting a V5 strategy to JoinQuant, QMT, or another execution platform.

## Responsibilities

- Ensure platform code reads or reproduces the same strategy specification.
- Compare local and platform signal dates, factor values, ranks, selected securities, target weights, defensive state, and trading constraints.
- Record differences as artifacts.

## Guardrails

- Do not accept platform backtest results until signal consistency checks pass.
- Platform adapters may differ in data and order APIs, but not in ranking, weighting, or risk-control logic.
