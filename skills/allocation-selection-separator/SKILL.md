---
name: allocation-selection-separator
description: Separate allocation framework decisions from stock-selection decisions in Bank Quant V5. Use when evaluating whether performance comes from sector/cash/risk allocation, factor ranking, stock selection, overlays, state machines, or execution timing, especially before ranking candidates or accepting a strategy improvement.
---

# Allocation Selection Separator

## Mission

Prevent V5 from mistaking allocation effects for stock-selection alpha.

## Core Distinction

- Allocation answers: how much capital should be invested, in cash, in defensive assets, or in each sleeve.
- Selection answers: which securities should be held inside the approved investable pool.

These two layers can both improve returns, but they must be diagnosed separately.

## Workflow

1. Decompose the candidate into allocation, selection, risk-control, and execution layers.
2. Hold all non-tested layers fixed where possible.
3. Compare allocation-only changes against the same stock-selection rule.
4. Compare selection-only changes against the same allocation rule.
5. Report exposure, cash, sleeve weights, selected names, turnover, and return contribution.
6. Label the improvement source before any promotion decision.

## Diagnostic Questions

- Did the candidate hold more or less cash than the baseline?
- Did the candidate change which stocks were selected?
- Did the candidate change when the portfolio entered or exited?
- Did the candidate benefit from defensive allocation rather than better alpha?
- Did the candidate improve return while increasing hidden exposure?

## Never Do

- Do not call a higher-return allocation candidate a better factor model without selection evidence.
- Do not let a defensive overlay rewrite factor conclusions.
- Do not compare full-investment and high-cash candidates without reporting exposure.
- Do not collapse allocation, selection, and execution into a single unexplained score.

## Required Output

```text
Candidate:
Baseline:
Allocation Layer:
Selection Layer:
Risk Layer:
Execution Layer:
Fixed Layers:
Changed Layers:
Attribution:
Conclusion:
```

## V4 References

- `D:\hh\codex\v4\phase_2_momentum\allocation_vs_selection_framework_note_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\dual_engine_incremental_attribution_v1.md`
- `D:\hh\codex\v4\phase_2_momentum\formal_candidate_rolling_comparison_v1.md`
