---
name: strategy-spec
description: Convert natural-language quantitative strategy ideas into structured Bank Quant V5 strategy specifications. Use when creating or updating V5 JSON specs, defining required sections, factor metadata, portfolio rules, execution assumptions, validation settings, or output requirements.
---

# Strategy Spec Skill

Use this skill to convert natural-language strategy ideas into V5 strategy specifications.

## Required Sections

- `meta`
- `universe`
- `data`
- `signals`
- `schedule`
- `portfolio`
- `risk`
- `validation`
- `execution`
- `outputs`

## Rules

- Mark unknown values explicitly instead of silently choosing important parameters.
- Every factor must include direction, definition, data source, as-of policy, disclosure lag, missing-value policy, winsorization, and normalization.
- Portfolio rules must define selection count, weighting, and maximum position weight.
- Execution rules must include costs, suspension handling, and limit-up/limit-down handling.
