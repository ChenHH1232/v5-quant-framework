# Governance Record: v53e_insurance_research_validation_decision_v1

Date: 2026-07-17

Project:

```text
V5.3e Insurance Low PB + Solvency Guard + State Diagnostics
```

PM decision:

```text
research_pit_validation_completed_guard_rejected_state_inconclusive
```

## Research Hypothesis

After V5.3d failed, Research Agent redesigned the insurance hypothesis:

```text
Low PB remains the core alpha candidate. Solvency should work as a value-trap guard rather than a positive alpha score. Total investment return should be a state / diagnostic variable rather than a ranking factor.
```

No return tuning was allowed.

## Formal Validation Result

Spec:

```text
examples/insurance_low_pb_solvency_guard_v53e_strategy.json
```

Formal validation packet:

```text
validation_formal_v53e_insurance_low_pb_solvency_guard/insurance_low_pb_solvency_guard_v53e
```

PIT audit:

| Check | Result |
| --- | --- |
| Rows checked | 181 |
| Missing notice-date rows | 0 |
| Future notice-date violations | 0 |
| Status | pass |

Baseline comparison:

| Case | Cumulative return |
| --- | ---: |
| equal_weight_core_insurance | 91.42% |
| low_pb_core_insurance_top3 | 114.52% |
| low_pb_after_solvency_top80_guard | 94.91% |
| high_solvency_reference_top3 | 111.92% |
| v53e_low_pb_score | 83.58% |

Low PB factor evidence:

| Factor | Mean IC | Mean RankIC | Positive IC ratio |
| --- | ---: | ---: | ---: |
| low_price_to_book | 0.1203 | 0.1378 | 64.86% |

## PM Interpretation

The solvency guard hypothesis is rejected for now.

Why:

- low PB alone remains stronger than low PB after the solvency top80 guard;
- high solvency has decent standalone reference performance, but it does not improve low-PB selection when used as a simple guard;
- the guard reduces cumulative return and does not solve the major weak years;
- top2 / top3 / top4 sensitivity remains material, showing concentration risk in the tiny insurance universe.

## State Diagnostic Result

State diagnostic outputs:

```text
state_diagnostic_by_date.csv
state_diagnostic_summary.csv
weak_year_state_paths.csv
```

Important observations:

- low PB performed poorly in the high equity-return state bucket;
- low PB performed poorly in the high 10Y-yield-change bucket;
- low PB had strong returns in the low 10Y-yield-change bucket;
- 2021, 2022 and 2026 do not share one clean, stable state path.

Therefore these states are useful for failure explanation, but not enough to approve a timing rule.

## Decision

V5.3e is not promoted.

Blocked:

- no Engineering Agent handoff;
- no local daily simulation;
- no JoinQuant code;
- no paper trading;
- no state timing rule based on this result.

## Next Research Gate

Research Agent has only two reasonable paths:

1. Repair multi-year PIT EV / NBV data and test P/EV or EV-growth hypotheses.
2. Split the insurance universe into life insurance / P&C / insurance group sub-hypotheses.

If neither path is feasible, insurance should be paused as:

```text
research_signal_exists_but_not_deployable
```

