# Governance Record: v53d_insurance_formal_validation_decision_v1

Date: 2026-07-17

Project:

```text
V5.3d Insurance Value + Investment Quality + Solvency Formal Validation
```

PM decision:

```text
research_pit_validation_completed_composite_rejected
```

## Research Hypothesis

Research Agent proposed that low PB should remain useful in insurance stocks only when supported by insurance-specific investment quality and solvency evidence.

Core V5.3d score:

| Factor | Role | Direction | Weight |
| --- | --- | --- | ---: |
| low_price_to_book | balance-sheet value | lower is better | 0.50 |
| total_investment_rate_of_return | investment quality | higher is better | 0.25 |
| solvency_adequacy_ratio | balance-sheet safety | higher is better | 0.25 |

EV / NBV are kept as reviewed enhancement data, but not used in the rolling core model because historical PIT coverage is not complete enough.

Net investment yield is downgraded to optional enhancement. The required investment-quality field for V5.3d is total investment yield / total investment rate of return.

## Formal Validation Result

Quant Validation Agent completed formal PIT validation.

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
| high_total_investment_return_top3 | 52.16% |
| high_solvency_top3 | 111.92% |
| v53d_composite | 67.24% |

Single-factor evidence:

| Factor | Mean IC | Mean RankIC | Positive IC ratio |
| --- | ---: | ---: | ---: |
| low_price_to_book | 0.1203 | 0.1378 | 64.86% |
| total_investment_rate_of_return | -0.1062 | -0.1254 | 43.24% |
| solvency_adequacy_ratio | 0.0472 | 0.0216 | 54.05% |

Weak-year results:

| Year | V5.3d cumulative return | Interpretation |
| --- | ---: | --- |
| 2018 | -14.71% | weak rolling year |
| 2021 | -24.17% | absolute loss, only slightly better than low PB |
| 2022 | -2.43% | underperformed universe and low PB |
| 2026 | -28.43% | underperformed universe, same weak selection as low PB |

## PM Interpretation

V5.3d should not be promoted to Engineering Agent.

The research idea is financially reasonable, but the statistical evidence does not support the composite:

- low PB remains the strongest insurance factor in this sample;
- total investment return hurts ranking evidence rather than improving it;
- solvency has weak positive evidence, but not enough to improve the low-PB baseline;
- V5.3d composite materially underperforms low-PB-only and high-solvency baselines;
- weak years remain unresolved, especially 2022 and 2026.

This is a good V5 process outcome: the PIT data gate passed, but the hypothesis gate failed.

## Validation Caveat

The ablation and common-sample interaction outputs include zero-return rows after dropping factors because the strategy spec requires:

```text
min_factor_count = 3
```

When one factor is removed, the current formal-validation runner selects no stocks instead of relaxing the required factor count for the ablation case. These rows must not be interpreted as true factor-ablation evidence.

Engineering backlog:

```text
formal_validation_runner_ablation_min_factor_count_policy
```

## Next Research Direction

Research Agent must return to hypothesis design. No return tuning is allowed.

Allowed directions:

- test solvency as a filter or guard instead of a weighted positive score;
- treat total investment return as a state or risk diagnostic rather than a positive ranking factor;
- test EV/PB or P/EV only after multi-year PIT EV/NBV coverage is repaired;
- split life insurance and P&C insurance if the combined insurance universe keeps mixing different economics;
- add real interest-rate and equity-market state as explanatory variables, not as tuned timing rules.

Blocked actions:

- no JoinQuant code;
- no platform replication;
- no paper trading;
- no weight or selection-count tuning based on 2021-2026 outcomes.

## Next Gate

```text
research_return_to_hypothesis_design
```
