---
name: rolling-validation
description: Evaluate Bank Quant V5 candidate strategies across chronological train, validation, and test windows. Use for rolling validation, walk-forward testing, out-of-sample performance, turnover, cost impact, drawdown, risk statistics, and accepted or rejected candidate reasons.
---

# Rolling Validation Skill

Use this skill when evaluating candidate strategies across train/test windows.

## Responsibilities

- Build chronological rolling windows.
- Keep training, validation, and test decisions separated.
- Report each window independently.
- Identify strategies that rely on a small number of lucky years.

## Required Outputs

- Window definitions.
- In-sample and out-of-sample performance.
- Turnover and cost impact.
- Drawdown and risk statistics.
- Accepted and rejected candidate reasons.
