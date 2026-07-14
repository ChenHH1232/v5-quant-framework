---
name: momentum-research
description: Apply V4-derived momentum research discipline in Bank Quant V5. Use when designing, validating, comparing, or deploying bank-sector momentum factors such as mom_6_1, mom_12_1, state-dependent momentum switching, fundamental-gated momentum, or monthly/quarterly momentum ranking.
---

# Momentum Research

## Mission

Research momentum as a deployable extension layer without overfitting the frozen out-of-sample window.

## V4 Lessons

- `mom_6_1` can be stronger as a pure research signal.
- `mom_6_1` is state-dependent and works best in clear trend-up environments.
- `mom_12_1` can be weaker as pure alpha but more durable as a deployment backbone.
- A promising structure is to use `mom_6_1` in high-state months and fall back to `mom_12_1` otherwise.
- Fundamental gating before momentum ranking can create a cleaner bank-sector deployment candidate.

## Workflow

1. Define the momentum lookback, skip window, rebalance frequency, and investable universe.
2. State whether the factor is intended as pure alpha, deployment backbone, gate, or tie-breaker.
3. Validate pre-acceptance windows before touching frozen out-of-sample evidence.
4. Test state dependence explicitly instead of averaging it away.
5. Compare against the active momentum baseline and the non-momentum baseline.
6. Run common-sample comparison for formal promotion.
7. Freeze accepted momentum rules before platform export.

## Required Checks

- Rank performance by state.
- Turnover and liquidity impact.
- Factor correlation with fundamentals and market beta.
- Monthly versus quarterly rebalance behavior.
- Difference between research alpha and deployable implementation.

## Never Do

- Do not keep tuning against the same post-2021 acceptance window.
- Do not promote `mom_6_1` only because it wins in pure signal tests.
- Do not replace a durable deployment backbone without execution evidence.
- Do not use momentum to repair an unrelated fundamental failure.

## Required Output

```text
Momentum Hypothesis:
Factor Definition:
Deployment Role:
State Assumption:
Validation Window:
Baseline:
Evidence:
Execution Impact:
Decision:
Next Action:
```

## V4 References

- `D:\hh\codex\v4\phase_2_momentum\momentum_conclusion_summary_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\momentum_stage_summary_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\momentum_state_switch_final_acceptance_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\momentum_rolling_validation_v1.md`
