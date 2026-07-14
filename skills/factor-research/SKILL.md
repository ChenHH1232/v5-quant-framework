---
name: factor-research
description: Run or interpret factor research inside Bank Quant V5, including point-in-time factor construction, missing-value policy, outlier handling, cross-sectional normalization, coverage, turnover, rank stability, IC, grouped returns, and factor failure modes.
---

# Factor Research Skill

Use this skill when running or interpreting factor research inside V5.

## Responsibilities

- Compute point-in-time factor values.
- Apply missing-value and outlier policies.
- Normalize cross-sectionally using only information visible at the signal date.
- Report coverage, turnover, rank stability, IC, grouped returns, and failure modes.

## Guardrails

- Do not select factors using final test-period performance.
- Do not hide high missingness or unstable yearly behavior behind aggregate results.
