---
name: defensive-overlay-research
description: Research defensive overlays and short-bond or cash risk-control layers in Bank Quant V5. Use when testing drawdown control, defensive allocation, shortbond overlays, cash routing, risk-off states, or separating alpha generation from portfolio protection.
---

# Defensive Overlay Research

## Mission

Evaluate defensive overlays as independent risk-control layers, not as substitutes for alpha evidence.

## Core Rule

A defensive overlay can improve portfolio behavior by changing exposure. That does not prove the stock-selection model is better.

## Workflow

1. Define the defensive asset, cash rule, or exposure reduction rule.
2. State the trigger: valuation, fundamentals, momentum state, drawdown, volatility, or calendar.
3. Keep the selection model fixed during overlay tests.
4. Compare against a no-overlay baseline and a cash-only baseline where possible.
5. Report return, drawdown, exposure, cash/defensive weight, turnover, and trigger frequency.
6. Diagnose whether benefit comes from crash protection, smoother exposure, or missed upside.
7. Approve only as a risk-control layer unless selection evidence also improves.

## Required Checks

- Does the overlay reduce drawdown consistently?
- Does it reduce return too much?
- Does it rely on unavailable or delayed data?
- Is the defensive asset executable on the target platform?
- Does it create hidden market-timing exposure?

## Never Do

- Do not use a defensive overlay to justify weak factor evidence.
- Do not compare overlay and non-overlay candidates without reporting exposure.
- Do not mix defensive weights into alpha ranks.
- Do not accept a risk-off rule without trigger audit.

## Required Output

```text
Overlay Hypothesis:
Trigger:
Defensive Asset or Cash Rule:
Fixed Selection Model:
Baseline:
Exposure Impact:
Return and Drawdown Impact:
Execution Feasibility:
Decision:
```

## V4 References

- `D:\hh\codex\v4\phase_1_fundamental\balanced_corelevel_shortbond_overlay_rolling_validation_v1.md`
- `D:\hh\codex\v4\safebox_2026-06-24_v4_finalization_v1\v4_final_candidate_ranking_2026-06-23.md`
