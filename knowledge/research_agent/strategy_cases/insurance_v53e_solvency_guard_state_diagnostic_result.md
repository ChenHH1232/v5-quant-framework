# Insurance V5.3e Solvency Guard And State Diagnostic Result

Date: 2026-07-17

Project:

```text
V5.3e Insurance Research Reset
```

Status:

```text
research_pit_validation_completed_guard_rejected_state_inconclusive
```

## What Changed From V5.3d

V5.3d treated total investment return and solvency as positive score factors. That failed.

V5.3e changed the research structure:

- low PB is the only score factor;
- solvency is tested as a value-trap guard;
- total investment return, 10Y yield, 10Y yield change and equity-market state are diagnostics;
- no weight tuning is allowed.

## Result

PIT audit passed, but the solvency guard did not improve the low-PB baseline.

| Case | Cumulative return |
| --- | ---: |
| equal_weight_core_insurance | 91.42% |
| low_pb_core_insurance_top3 | 114.52% |
| low_pb_after_solvency_top80_guard | 94.91% |
| high_solvency_reference_top3 | 111.92% |
| v53e_low_pb_score | 83.58% |

Interpretation:

```text
Solvency is economically relevant, but a simple top80 guard does not improve low-PB selection in the current PIT sample.
```

## State Diagnostic

State buckets were built with expanding history only.

Findings:

- equity high-state periods were weak for low PB;
- 10Y-yield-change high-state periods were weak for low PB;
- investment-return mid-state periods were weak, but the pattern is sparse;
- weak years do not share one consistent state path.

Weak-year state paths:

| Year | Summary |
| --- | --- |
| 2021 | high investment return, high rate-change, high equity state for most quarters |
| 2022 | low rate level, mixed investment return, weak equity state |
| 2026 | low investment return, low rate level, high-to-mid rate/equity state |

Research interpretation:

```text
State variables help explain stress, but they are not yet a validated timing rule.
```

## Research Lesson

Insurance cannot be repaired by adding generic quality variables to low PB.

The next real insurance-specific test needs either:

- PIT EV / NBV / P/EV valuation data; or
- subgroup models for life insurance and P&C insurance.

## Handoff

Quant Agent should not receive another low-PB + simple guard variant unless Research Agent supplies new evidence.

Allowed next work:

- EV / NBV PIT data repair;
- P/EV hypothesis after data repair;
- life-only / P&C-only subgroup hypothesis;
- documentation of why insurance should be paused if data repair is not feasible.

