---
name: state-routing-research
description: Design and validate state-routing logic for Bank Quant V5. Use when building observable market or fundamental states, deterioration warnings, annual-entry monthly-exit rules, slow-fundamental fast-exit state machines, high-state momentum switching, or risk-on/risk-off routing.
---

# State Routing Research

## Mission

Turn observable conditions into auditable routing rules without leaking future information or overreacting to noise.

## Core Rule

State routing must separate warning, confirmation, action, and review. A warning is not automatically a trade.

## Workflow

1. Define the state variable and data timestamp.
2. Label the state purpose: entry gate, exit trigger, sleeve switch, factor switch, or risk overlay.
3. Specify warning and confirmation thresholds separately.
4. Define action timing: annual entry, monthly exit, quarterly review, or event-driven.
5. Validate state transitions inside rolling folds.
6. Compare state-routed behavior against fixed allocation or fixed factor baselines.
7. Audit look-ahead risk, stale data, and execution lag.

## Design Patterns

- Slow fundamental, fast exit: use low-frequency fundamentals for entry quality but allow faster observable warnings for exit.
- Annual entry, monthly exit: avoid noisy frequent entry while still allowing deterioration control.
- State-dependent momentum: use shorter momentum only when state support exists, otherwise fall back to durable momentum.

## Never Do

- Do not build states from future-period returns or revised data.
- Do not let state routing change factor definitions silently.
- Do not treat fewer invested months as better without cash/exposure attribution.
- Do not optimize thresholds against the final acceptance window.

## Required Output

```text
State Hypothesis:
State Inputs:
Timestamp Assumptions:
Warning Rule:
Confirmation Rule:
Action Rule:
Baseline:
Rolling Evidence:
Leakage Risks:
Decision:
```

## V4 References

- `D:\hh\codex\v4\phase_2_momentum\momentum_state_switch_final_acceptance_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\formal_candidate_rolling_comparison_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\allocation_vs_selection_framework_note_v1.md`
