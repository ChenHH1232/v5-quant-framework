---
name: strategy-attribution
description: Attribute Bank Quant V5 strategy changes into selection, allocation, overlap, cash, turnover, execution, and risk contributions. Use when a candidate improves or worsens performance and Codex must explain what changed, whether improvement is real alpha, and whether two engines are redundant or complementary.
---

# Strategy Attribution

## Mission

Explain why a strategy changed before deciding whether the change is an improvement.

## Attribution Layers

- Selection: which securities are chosen.
- Allocation: how much capital is assigned to each sleeve, cash, or defensive asset.
- Overlap: whether two engines hold the same names.
- Cash: invested ratio and drag.
- Turnover: trading frequency and replacement intensity.
- Execution: delay, slippage, cost, platform behavior.
- Risk: drawdown, concentration, state exposure.

## Workflow

1. Compare candidate and baseline at each rebalance date.
2. Record selected names, weights, cash, sleeve labels, and target changes.
3. Compute overlap or Jaccard where two selection engines are compared.
4. Decompose return differences by changed layer where possible.
5. Explain whether the candidate is additive, redundant, defensive, or simply higher exposure.
6. Feed attribution into candidate governance before promotion.

## Required Checks

- Does improvement remain after controlling for cash or exposure?
- Are engines selecting distinct names or duplicating the same signal?
- Is turnover higher, and is the return enough to pay for it?
- Is the result concentrated in one rebalance, fold, or state?

## Never Do

- Do not accept "better return" as an explanation.
- Do not call a candidate diversified without overlap evidence.
- Do not ignore cash drag or exposure differences.
- Do not merge engines before checking incremental contribution.

## Required Output

```text
Candidate:
Baseline:
Changed Layers:
Selection Overlap:
Exposure and Cash:
Turnover:
Incremental Return:
Risk Impact:
Interpretation:
Decision Input:
```

## V4 References

- `D:\hh\codex\v4\phase_2_momentum\dual_engine_incremental_attribution_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\dual_engine_overlap_confirmation_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\formal_candidate_rolling_comparison_v1.md`
