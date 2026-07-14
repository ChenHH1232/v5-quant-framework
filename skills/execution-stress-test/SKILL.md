---
name: execution-stress-test
description: Stress-test Bank Quant V5 strategy execution assumptions. Use when evaluating transaction costs, delayed fills, slippage, turnover, terminal liquidation cost, sparse rebalance timing, platform execution differences, or whether a candidate is too fragile to realistic trading.
---

# Execution Stress Test

## Mission

Check whether a validated strategy still works under realistic execution pressure.

## Core Rule

Hold the signal layer fixed. Stress only the execution layer unless the research question explicitly asks otherwise.

## Standard Scenarios

Start with these unless the target market requires different assumptions:

- immediate fill with 10 bps one-way cost;
- 1 trading day delay with 10 bps one-way cost;
- 3 trading day delay with 10 bps one-way cost;
- immediate fill with 30 bps one-way cost.

Include terminal liquidation cost for conservative comparability when measuring full-period returns.

## Workflow

1. Freeze target weights from the approved signal logic.
2. Rebuild returns using delayed execution dates.
3. Charge one-way transaction cost on realized turnover.
4. Report gross and net period returns.
5. Compare scenario deltas against the base execution case.
6. Identify whether fragility comes from delay, cost, turnover, or rebalance timing.
7. Block promotion if the strategy only works under unrealistic fills.

## Never Do

- Do not change factor ranks while testing execution.
- Do not improve weights after seeing execution stress results.
- Do not omit turnover or cost assumptions.
- Do not compare delayed and immediate scenarios with different signals.

## Required Output

```text
Strategy:
Frozen Signal Source:
Execution Scenarios:
Turnover:
Gross Return:
Net Return:
Scenario Deltas:
Fragility Diagnosis:
Decision:
```

## V4 References

- `D:\hh\codex\v4\phase_2_momentum\dual_engine_execution_stress_test_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\dual_engine_incremental_attribution_v1.md`
